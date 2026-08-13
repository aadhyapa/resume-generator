import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ResumePipelineSettings:
    resume_pipeline: str = "v1"
    jd_preprocessor_model: str = "gemini-3.1-flash-lite"
    resume_ranker_model: str = "claude-sonnet-5"
    bullet_rewriter_model: str = "claude-sonnet-5"
    bullet_rewriter_max_compression_iterations: int = 2
    v2_debug_trace: bool = False
    v2_trace_dir: str = "backend/pipeline_traces"


def _int_from_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def get_settings() -> ResumePipelineSettings:
    return ResumePipelineSettings(
        resume_pipeline=os.environ.get("RESUME_PIPELINE", "v1").strip().lower() or "v1",
        jd_preprocessor_model=os.environ.get("JD_PREPROCESSOR_MODEL", "gemini-3.1-flash-lite"),
        resume_ranker_model=os.environ.get("RESUME_RANKER_MODEL", "claude-sonnet-5"),
        bullet_rewriter_model=os.environ.get("BULLET_REWRITER_MODEL", "claude-sonnet-5"),
        bullet_rewriter_max_compression_iterations=max(0, _int_from_env("BULLET_REWRITER_MAX_COMPRESSION_ITERATIONS", 2)),
        v2_debug_trace=os.environ.get("RESUME_V2_DEBUG_TRACE", "false").lower() in {"1", "true", "yes"},
        v2_trace_dir=os.environ.get("RESUME_V2_TRACE_DIR", "backend/pipeline_traces"),
    )
