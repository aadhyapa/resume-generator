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
    settings = get_settings()
    trace = PipelineTrace(raw_job_description=job_description if settings.v2_debug_trace else None)
    master_resume = load_master_resume(master_resume_path) if master_resume_path else load_master_resume()

    started = perf_counter()
    structured_jd = preprocess_job_description(job_description, llm_client=llm_client, model=settings.jd_preprocessor_model)
    trace.structured_jd = structured_jd.model_dump(mode="python")
    trace.agents.append(AgentTrace(name="jd_preprocessor", model=settings.jd_preprocessor_model, latency_ms=_elapsed_ms(started)))

    started = perf_counter()
    ranking = rank_resume_content(structured_jd, master_resume, llm_client=llm_client, model=settings.resume_ranker_model)
    trace.ranking = ranking.model_dump(mode="python")
    trace.agents.append(AgentTrace(name="resume_ranker", model=settings.resume_ranker_model, latency_ms=_elapsed_ms(started)))

    selected = select_resume_content(master_resume, ranking)
    trace.selected_content = selected.model_dump(mode="python")

    trimmed, _ = trim_to_page_limit(master_resume, selected, ranking, compiler=compiler, page_counter=page_counter)
    trace.trimmed_content = trimmed.model_dump(mode="python")

    started = perf_counter()
    rewrites = rewrite_selected_bullets(structured_jd, master_resume, trimmed, llm_client=llm_client, model=settings.bullet_rewriter_model)
    trace.rewrite_output = rewrites.model_dump(mode="python")
    trace.agents.append(AgentTrace(name="bullet_rewriter", model=settings.bullet_rewriter_model, latency_ms=_elapsed_ms(started)))

    final_resume = render_selected_resume(master_resume, trimmed, rewrites)
    from services.pdf_compiler import compile_resume_with_length_check
    final_compile = compile_resume_with_length_check(final_resume, compiler=compiler, page_counter=page_counter)

    compression_attempts = 0
    while not final_compile.fits_page_limit and compression_attempts < settings.bullet_rewriter_max_compression_iterations:
        compression_attempts += 1
        started = perf_counter()
        rewrites = rewrite_selected_bullets(structured_jd, master_resume, trimmed, llm_client=llm_client, model=settings.bullet_rewriter_model, compression=True)
        trace.agents.append(AgentTrace(name="bullet_rewriter_compression", model=settings.bullet_rewriter_model, latency_ms=_elapsed_ms(started)))
        final_resume = render_selected_resume(master_resume, trimmed, rewrites)
        final_compile = compile_resume_with_length_check(final_resume, compiler=compiler, page_counter=page_counter)

    if not final_compile.fits_page_limit:
        trimmed, _ = trim_to_page_limit(master_resume, trimmed, ranking, compiler=compiler, page_counter=page_counter)
        final_resume = render_selected_resume(master_resume, trimmed, rewrites)
        final_compile = compile_resume_with_length_check(final_resume, compiler=compiler, page_counter=page_counter)

    trace.final_page_count = final_compile.page_count
    _write_trace(settings, trace)
    return {
        "resume": final_resume,
        "structured_jd": structured_jd,
        "ranking": ranking,
        "selected_content": trimmed,
        "rewrite_output": rewrites,
        "page_count": final_compile.page_count,
    }
