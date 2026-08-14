import logging
from pathlib import Path
from time import perf_counter

from agents.v2.bullet_rewriter import rewrite_selected_bullets
from agents.v2.jd_preprocessor import preprocess_job_description
from agents.v2.resume_ranker import rank_resume_content
from algorithms.v2_selector import select_resume_content
from algorithms.v2_trimmer import render_selected_resume, trim_to_page_limit
from config import ResumePipelineSettings, get_settings
from models.trace import AgentTrace, PipelineTrace
from services.resume_repository import load_master_resume

logger = logging.getLogger(__name__)


def _elapsed_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)


def _write_trace(settings: ResumePipelineSettings, trace: PipelineTrace) -> None:
    if not settings.v2_debug_trace:
        return
    trace_dir = Path(settings.v2_trace_dir)
    trace_dir.mkdir(parents=True, exist_ok=True)
    path = trace_dir / "latest-v2-pipeline-trace.json"
    path.write_text(trace.model_dump_json(indent=2), encoding="utf-8")


def generate_resume_v2(job_description: str, *, master_resume_path=None, llm_client=None, compiler=None, page_counter=None) -> dict:
    logger.info("Starting generate_resume_v2. Input Job Description length: %d characters. Master Resume Path: %s", len(job_description), master_resume_path)
    logger.debug("Input Job Description: %s", job_description)
    settings = get_settings()
    trace = PipelineTrace(raw_job_description=job_description if settings.v2_debug_trace else None)
    master_resume = load_master_resume(master_resume_path) if master_resume_path else load_master_resume()
    logger.info("Loaded master resume: %d subsections, %d bullets", len(master_resume.sub_sections), len(master_resume.bullets))

    started = perf_counter()
    logger.info("Running jd_preprocessor agent...")
    structured_jd = preprocess_job_description(job_description, llm_client=llm_client, model=settings.jd_preprocessor_model)
    logger.info("jd_preprocessor completed in %d ms", _elapsed_ms(started))
    logger.debug("Preprocessed Structured JD: %s", structured_jd)
    trace.structured_jd = structured_jd.model_dump(mode="python")
    trace.agents.append(AgentTrace(name="jd_preprocessor", model=settings.jd_preprocessor_model, latency_ms=_elapsed_ms(started)))

    started = perf_counter()
    logger.info("Running resume_ranker agent...")
    ranking = rank_resume_content(structured_jd, master_resume, llm_client=llm_client, model=settings.resume_ranker_model)
    logger.info("resume_ranker completed in %d ms", _elapsed_ms(started))
    logger.debug("Resume Rankings: %s", ranking)
    trace.ranking = ranking.model_dump(mode="python")
    trace.agents.append(AgentTrace(name="resume_ranker", model=settings.resume_ranker_model, latency_ms=_elapsed_ms(started)))

    logger.info("Running select_resume_content algorithm...")
    selected = select_resume_content(master_resume, ranking)
    logger.info("select_resume_content completed. Selected bullet count: %d", len(selected.selected_bullet_ids()))
    logger.debug("Selected Content: %s", selected)
    trace.selected_content = selected.model_dump(mode="python")

    logger.info("Running trim_to_page_limit...")
    trimmed, compile_res = trim_to_page_limit(master_resume, selected, ranking, compiler=compiler, page_counter=page_counter)
    logger.info("trim_to_page_limit completed. Fits limit: %s. Page count: %d. Trimmed bullet count: %d", compile_res.fits_page_limit, compile_res.page_count, len(trimmed.selected_bullet_ids()))
    logger.debug("Trimmed Content: %s", trimmed)
    trace.trimmed_content = trimmed.model_dump(mode="python")

    started = perf_counter()
    logger.info("Running rewrite_selected_bullets agent...")
    rewrites = rewrite_selected_bullets(structured_jd, master_resume, trimmed, llm_client=llm_client, model=settings.bullet_rewriter_model)
    logger.info("rewrite_selected_bullets completed in %d ms. Rewritten count: %d", _elapsed_ms(started), len(rewrites.rewritten_bullets))
    logger.debug("Bullet Rewrites: %s", rewrites)
    trace.rewrite_output = rewrites.model_dump(mode="python")
    trace.agents.append(AgentTrace(name="bullet_rewriter", model=settings.bullet_rewriter_model, latency_ms=_elapsed_ms(started)))

    logger.info("Rendering selected resume...")
    final_resume = render_selected_resume(master_resume, trimmed, rewrites)
    from services.pdf_compiler import compile_resume_with_length_check
    logger.info("Compiling resume with length check...")
    final_compile = compile_resume_with_length_check(final_resume, compiler=compiler, page_counter=page_counter)
    logger.info("Initial compilation completed. Page count: %d. Fits: %s", final_compile.page_count, final_compile.fits_page_limit)

    compression_attempts = 0
    while not final_compile.fits_page_limit and compression_attempts < settings.bullet_rewriter_max_compression_iterations:
        compression_attempts += 1
        logger.info("Resume exceeds page limit. Attempting bullet rewriting compression (iteration %d/%d)...", compression_attempts, settings.bullet_rewriter_max_compression_iterations)
        started = perf_counter()
        rewrites = rewrite_selected_bullets(structured_jd, master_resume, trimmed, llm_client=llm_client, model=settings.bullet_rewriter_model, compression=True)
        logger.info("Compression rewriting completed in %d ms", _elapsed_ms(started))
        logger.debug("Compression Bullet Rewrites: %s", rewrites)
        trace.agents.append(AgentTrace(name="bullet_rewriter_compression", model=settings.bullet_rewriter_model, latency_ms=_elapsed_ms(started)))
        final_resume = render_selected_resume(master_resume, trimmed, rewrites)
        final_compile = compile_resume_with_length_check(final_resume, compiler=compiler, page_counter=page_counter)
        logger.info("Compression iteration %d result: Page count: %d. Fits: %s", compression_attempts, final_compile.page_count, final_compile.fits_page_limit)

    if not final_compile.fits_page_limit:
        logger.warning("Resume still exceeds page limit after compression iterations. Forcing fallback trim...")
        trimmed, compile_res = trim_to_page_limit(master_resume, trimmed, ranking, compiler=compiler, page_counter=page_counter)
        logger.info("Fallback trim completed. Fits limit: %s. Page count: %d. New bullet count: %d", compile_res.fits_page_limit, compile_res.page_count, len(trimmed.selected_bullet_ids()))
        trace.trimmed_content = trimmed.model_dump(mode="python")
        remaining = set(trimmed.selected_bullet_ids())
        rewrites.rewritten_bullets = [bullet for bullet in rewrites.rewritten_bullets if bullet.bullet_id in remaining]
        trace.rewrite_output = rewrites.model_dump(mode="python")
        logger.debug("Updated Bullet Rewrites: %s", rewrites)
        final_resume = render_selected_resume(master_resume, trimmed, rewrites)
        final_compile = compile_resume_with_length_check(final_resume, compiler=compiler, page_counter=page_counter)
        logger.info("Final fallback compile result: Page count: %d. Fits: %s", final_compile.page_count, final_compile.fits_page_limit)

    trace.final_page_count = final_compile.page_count
    logger.info("Writing pipeline trace...")
    _write_trace(settings, trace)
    logger.info("generate_resume_v2 completed successfully. Returning final output with page count %d", final_compile.page_count)
    return {
        "resume": final_resume,
        "structured_jd": structured_jd,
        "ranking": ranking,
        "selected_content": trimmed,
        "rewrite_output": rewrites,
        "page_count": final_compile.page_count,
    }
