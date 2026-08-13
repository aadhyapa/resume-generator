# V2 3-Agent Resume Pipeline

Set `RESUME_PIPELINE=v2` to use the new pipeline behind the existing `/generate_resume` response contract.

Flow:

1. Agent 1 (`backend/agents/v2/jd_preprocessor.py`) converts the raw job description into a validated `StructuredJobDescription` without seeing the resume.
2. Agent 2 (`backend/agents/v2/resume_ranker.py`) receives the structured JD plus a compact master-resume serialization and returns validated section, subsection, and bullet rankings using only existing stable IDs.
3. Deterministic code (`backend/algorithms/v2_selector.py` and `backend/algorithms/v2_trimmer.py`) selects ID-based content, compiles through the existing LaTeX/PDF services, and trims the lowest-loss removable content until the resume fits one page.
4. Agent 3 (`backend/agents/v2/bullet_rewriter.py`) rewrites only selected bullets. If the rewritten PDF exceeds one page, a bounded compression mode runs before deterministic trimming fallback.

Environment variables:

- `RESUME_PIPELINE`: `v1` or `v2`; defaults to `v1`.
- `JD_PREPROCESSOR_MODEL`: defaults to `gemini-3.1-flash-lite`.
- `RESUME_RANKER_MODEL`: defaults to `claude-sonnet-5`.
- `BULLET_REWRITER_MODEL`: defaults to `claude-sonnet-5`.
- `BULLET_REWRITER_MAX_COMPRESSION_ITERATIONS`: defaults to `2`.
- `RESUME_V2_DEBUG_TRACE`: write inspectable traces when set to true.
- `RESUME_V2_TRACE_DIR`: trace directory; defaults to `backend/pipeline_traces`.

V2 does not use embeddings or vector search for bullet retrieval. The old V1 chunker/embedder/matchmaker/editor path remains available while V2 is validated.
