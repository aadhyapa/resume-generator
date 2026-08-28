# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

RezMaker: a Chrome extension (`frontend/`) that scrapes a job description off the active tab and a FastAPI backend (`backend/`) that tailors a master resume to it (rank/select/rewrite relevant bullets, then render to PDF via LaTeX). The two halves are independent projects (separate dependency managers, no root build tooling) that only touch through the HTTP API defined by `backend/app.py`.

`implementation.spec.md` is a large aspirational two-phase (prototype → production) spec; treat it as a roadmap, not a description of current state — most of "Phase 2" (auth, DB, queues, billing) is not implemented. `docs/v2-3-agent-resume-pipeline.md` and `docs/frontend-backend-schema-plan.md` describe the actual current pipeline and response schema and are more reliable.

## File structure

```
resume-generator/
├── CLAUDE.md
├── README.md
├── implementation.spec.md
├── docs/
│   ├── v2-3-agent-resume-pipeline.md       # v2 pipeline design (current, reliable)
│   ├── v2-3-agent-resume-pipeline-plan.md
│   └── frontend-backend-schema-plan.md     # resume JSON response contract
├── backend/                     # FastAPI, cwd for all backend commands
│   ├── app.py                   # entrypoint, /generate_resume + /render_resume_pdf, branches v1/v2
│   ├── config.py                # env-driven settings (models, guardrails)
│   ├── security.py              # X-API-Key auth + rate limiting
│   ├── conftest.py               # pytest sys.path wiring
│   ├── agents/                  # v1 pipeline agents + shared v1 test fixtures
│   │   ├── job_description_chunker.py
│   │   ├── embedder.py
│   │   ├── editor.py
│   │   ├── validator.py
│   │   ├── formats/             # JSON schemas for structured LLM output
│   │   ├── prompts/              # prompt text files
│   │   ├── test_data/            # v1 flat bullet-list fixtures (gitignored)
│   │   └── v2/                   # v2 pipeline agents
│   │       ├── jd_preprocessor.py    # JD -> StructuredJobDescription
│   │       ├── resume_ranker.py      # JD + resume -> ResumeRanking
│   │       └── bullet_rewriter.py    # rewrites selected bullets
│   ├── algorithms/
│   │   ├── matchmaker.py         # v1: cosine similarity scoring
│   │   ├── selector.py           # v1: greedy bullet selection
│   │   ├── formatter.py          # shared: assembles final resume dict (both pipelines)
│   │   ├── v2_selector.py         # v2: marginal-value greedy selection
│   │   └── v2_trimmer.py          # v2: trims to page limit via real PDF compile
│   ├── models/                  # Pydantic schemas (jd, ranking, resume, rewriting, selection, trace)
│   ├── serializers/
│   │   └── resume_compact.py     # compact resume serialization fed to resume_ranker
│   ├── services/
│   │   ├── v2_pipeline.py         # v2 orchestration
│   │   ├── resume_repository.py   # selected content -> resume dict
│   │   ├── pdf_compiler.py        # -> latexter
│   │   └── latexter.py            # LaTeX generation, latexmk/pdflatex + pdfinfo
│   ├── llm/
│   │   ├── client.py              # ProviderLLMClient (Claude vs Gemini dispatch)
│   │   ├── json_utils.py          # best-effort JSON repair for non-Claude models
│   │   ├── schema_utils.py
│   │   └── retry.py
│   ├── scripts/
│   │   ├── generate_resume_data.py  # builds v1 fixture
│   │   └── smoke_pipeline.py        # manual e2e smoke test, real LLM providers
│   ├── tests/
│   │   ├── test_v2_pipeline_components.py
│   │   └── test_latexter.py
│   └── test_data/
│       └── resume_data_embedded.json  # v2 MasterResume fixture, hand-authored (gitignored)
└── frontend/                    # WXT + React + TS Chrome extension (MV3), cwd for frontend commands
    ├── wxt.config.ts
    ├── entrypoints/
    │   ├── background.ts         # service worker: fetch to backend, writes generationState
    │   ├── content.ts            # unused starter-template leftover
    │   ├── popup/                # main UI: does the scraping + rendering work
    │   │   ├── App.tsx
    │   │   ├── Preview.tsx
    │   │   ├── types.ts           # Resume type mirrors backend's flat section-keyed shape
    │   │   └── utils/
    │   │       ├── renderResumeHtml.ts   # client reimpl of algorithms/formatter.py
    │   │       └── renderResumeLatex.ts  # client reimpl of services/latexter.py
    │   └── resume-preview/        # popup window for previewing rendered resume
    ├── lib/
    │   ├── scraper.tsx            # getJobDescription(), injected into active tab
    │   └── utils.ts
    ├── components/
    └── assets/
        └── Templates/             # legacy resume HTML/TSX templates
```

## Commands

### Backend (`backend/`, Python, FastAPI)

All commands assume `cwd = backend/` — the code imports as top-level packages (`from agents...`, `from algorithms...`), not `backend.agents...`.

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run the API server (reads PORT env, defaults to 8000)
python app.py
# or, for autoreload:
uvicorn app:app --reload

# Tests (unittest-style, run via pytest; conftest.py wires sys.path)
pytest
pytest tests/test_v2_pipeline_components.py            # one file
pytest tests/test_v2_pipeline_components.py::V2ComponentTest::test_trim_loop_reaches_one_page_deterministically  # one test

# Manual end-to-end smoke test against real LLM providers (needs API keys + a job description fixture)
python scripts/smoke_pipeline.py
```

Required env vars live in `backend/.env` (gitignored, load via `python-dotenv`): `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`/`GOOGLE_API_KEY`, `RESUME_PIPELINE` (`v1`|`v2`), and the `GENERATE_RESUME_*` guardrails documented in `README.md`. PDF rendering additionally shells out to `latexmk`/`pdflatex` and `pdfinfo` (poppler) — without them installed, `compile_latex_to_pdf` silently falls back to a stub mock PDF, which is enough for tests but not for a real-looking resume.

### Frontend (`frontend/`, WXT + React + TypeScript Chrome extension)

```bash
cd frontend
npm install
npm run dev            # WXT dev server, loads unpacked into Chrome (MV3)
npm run build           # production build to .output/
npm run zip              # packaged .zip for distribution
npm run compile          # tsc --noEmit type check
```

There is no wired-up lint script (`eslint`/`prettier` are devDependencies but no config file or `lint` script exists) — `npm run compile` is the closest thing to a static check. `frontend/.env` / `frontend/.env.development` set `WXT_API_URL` (the backend's `/generate_resume` URL; defaults to `http://localhost:8000/generate_resume` if unset).

## Architecture

### Two resume-generation pipelines behind one endpoint

`POST /generate_resume` in `backend/app.py` branches on `get_settings().resume_pipeline` (env `RESUME_PIPELINE`, default `v1`):

- **v1 (legacy, inline in `app.py`)**: `job_description_chunker` (Gemini) splits the JD into requirement/responsibility/bonus/soft-skill buckets → `embedder.embed` embeds each bucket → `matchmaker` scores resume bullets against those embeddings by cosine similarity → `selector` greedily picks top bullets under global/per-experience caps → `editor` (Claude) rewrites selected bullets, with a second pass that only retries bullets `validator.validate_resume` flagged (length/fabrication), falling back to the original text if still failing → `formatter.formater` reassembles the final resume dict. This path loads bullets from `test_data/resume_data_embedded.json`.
- **v2 (`backend/services/v2_pipeline.py`, opt in via `RESUME_PIPELINE=v2`)**: three LLM agents plus deterministic selection, documented in `docs/v2-3-agent-resume-pipeline.md`:
  1. `agents/v2/jd_preprocessor.py` — JD → `StructuredJobDescription` (`models/jd.py`), without ever seeing the resume.
  2. `agents/v2/resume_ranker.py` — structured JD + compact master-resume serialization (`serializers/resume_compact.py`) → `ResumeRanking` (`models/ranking.py`): per-section/subsection/bullet scores, referencing only existing stable IDs.
  3. Deterministic code: `algorithms/v2_selector.py` (`select_resume_content`, a marginal-value greedy pass with a coverage minimum pass first and a same-subsection redundancy penalty) then `algorithms/v2_trimmer.py` (`trim_to_page_limit`, which recompiles the resume through the real LaTeX/PDF pipeline and repeatedly removes the single lowest-`removal_loss` bullet until it fits one page).
  4. `agents/v2/bullet_rewriter.py` rewrites only the selected bullets; if the rewritten PDF still overflows, it's retried in a bounded "compression" mode (`bullet_rewriter_max_compression_iterations`) before falling back to further deterministic trimming.
  Every agent call is Pydantic-validated end to end; there is no embedding/vector search anywhere in v2. Set `RESUME_V2_DEBUG_TRACE=true` to dump a full `PipelineTrace` (`models/trace.py`) of every intermediate stage to `RESUME_V2_TRACE_DIR`.

Both pipelines converge on the same resume JSON shape and the same `POST /render_resume_pdf` → `services/pdf_compiler.py` → `services/latexter.py` rendering path (LaTeX generation, then `latexmk`/`pdflatex` + `pdfinfo`). Compilation retries through progressively tighter `SPACING_PROFILES` (smaller vspace, then 10pt font) before giving up on fitting one page.

### The LLM client is provider-agnostic by convention, not by model choice

`llm/client.py`'s `ProviderLLMClient` picks Anthropic vs Gemini per call based on whether `model` starts with `"claude"`. `generate_structured` (strict tool-use, schema-enforced, no free-text JSON to parse) only actually enforces the schema for Claude models; non-Claude models fall through to `generate_json` + best-effort repair via `llm/json_utils.py`. Every agent/model choice is env-configurable per role (`config.py`: `JD_PREPROCESSOR_MODEL`, `RESUME_RANKER_MODEL`, `BULLET_REWRITER_MODEL`), so swapping a step to a different provider is a config change, not a code change — but only Claude gets the stronger structured-output guarantee.

### Resume data files are gitignored, and there are two incompatible schemas

Nothing under `backend/test_data/` or `backend/agents/test_data/` is committed (`backend/.gitignore`) — they hold real personal resume content. `backend/test_data/resume_data_embedded.json` is the v2 `MasterResume` shape (`models/resume.py`: `header`/`sections`/`sub_sections`/`bullets`/`skills`, all cross-referenced by stable IDs and validated for referential integrity in `MasterResume.validate_references`). `backend/agents/test_data/*.json` holds the older v1 flat bullet-list shape consumed by `matchmaker.py`. `scripts/generate_resume_data.py` builds the v1 fixture (via `agents/embedder.py`); there's no equivalent generator script for the v2 fixture — it's hand-authored/exported. The v2 pipeline's own unit tests don't need either file since they construct a `MasterResume` in memory.

### The response resume shape has a non-obvious quirk

`algorithms/formatter.py` (used by both pipelines, via `services/resume_repository.selected_content_to_resume` for v2) always emits `resume["sections"] = {}` — empty and unused — and instead attaches each real section directly on the top-level resume dict, keyed by its `section_id` (e.g. `resume["sec_experience"]`), each holding a `sub_sections` map keyed by `sub_section_id`. `frontend/entrypoints/popup/types.ts`'s `Resume` type mirrors this with a `[sectionId: string]: unknown` index signature. Anything that walks a `Resume`/resume dict — new formatting code, new preview components — needs to iterate the dict's own keys, not `resume.sections`. See `docs/frontend-backend-schema-plan.md` for the full contract.

### Frontend: the popup does the work, the content script doesn't

Despite `frontend/entrypoints/content.ts` existing, job-description scraping is **not** done by a persistent content script — `lib/scraper.tsx`'s `getJobDescription()` is called directly from the popup and injects `findJobDescription` into the active tab via `browser.scripting.executeScript` on demand (selection text → job-board-specific selectors → generic containers → `document.body.innerText` fallback). `content.ts` is unused starter-template leftover (matches `google.com`, logs to console).

Generation state (`status`, JD text, company/role, result, error) lives in `browser.storage.local` under `generationState`, written by the background service worker (`entrypoints/background.ts`, which does the actual `fetch` to the backend) and read reactively by the popup via a `browser.storage.onChanged` listener — not component state — so progress survives the popup closing. The auth token (sent as `X-API-Key`) is stored the same way, under `authToken`.

`entrypoints/popup/utils/renderResumeHtml.ts` and `renderResumeLatex.ts` are client-side reimplementations of the backend's rendering (`algorithms/formatter.py` + `services/latexter.py`), used for the in-extension preview window (`entrypoints/resume-preview/`) and to build the payload for `POST /render_resume_pdf`. Changing how a resume renders on one side (new field, new section type, spacing) generally needs a matching change on the other side, or the popup preview and the server-rendered PDF will disagree.

### Auth and cost guardrails sit in front of both generation endpoints

`security.py`'s `require_generate_resume_access` (a FastAPI dependency on both `/generate_resume` and `/render_resume_pdf`) fails closed with 503 if `GENERATE_RESUME_API_KEYS` isn't set, otherwise checks `X-API-Key`/`Authorization: Bearer` with constant-time comparison and applies an in-memory sliding-window rate limit keyed by `sha256(key)[:12] + client_ip`. `InMemoryRateLimiter` is deliberately isolated so it can be swapped for a shared store (Redis) if the backend ever runs multi-process/multi-instance — it currently won't coordinate across workers.
