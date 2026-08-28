# RezMaker

RezMaker tailors a master resume to a specific job description. It's two independent projects that only talk over HTTP:

- **`frontend/`** — a Chrome extension (WXT + React + TypeScript, MV3) that scrapes the job description off the active tab and drives generation from a popup.
- **`backend/`** — a FastAPI service that ranks/selects/rewrites resume bullets for the scraped job description and renders the result to PDF via LaTeX.

> `implementation.spec.md` is an aspirational two-phase (prototype → production) spec — treat it as a roadmap, not a description of current state. [`docs/v2-3-agent-resume-pipeline.md`](docs/v2-3-agent-resume-pipeline.md) and [`docs/frontend-backend-schema-plan.md`](docs/frontend-backend-schema-plan.md) describe the actual current pipeline and response schema and are more reliable.

## How it works

1. The extension popup scrapes the job description from the active tab (`frontend/lib/scraper.tsx`) and posts it to `POST /generate_resume`.
2. The backend runs one of two pipelines (selected by `RESUME_PIPELINE`) to pick and rewrite the most relevant bullets from a master resume, then assembles a resume JSON.
3. `POST /render_resume_pdf` renders that resume JSON to a PDF via LaTeX (`latexmk`/`pdflatex`, with `pdfinfo` for page-count checks).

Both pipelines converge on the same resume JSON shape and rendering path. See [`docs/frontend-backend-schema-plan.md`](docs/frontend-backend-schema-plan.md) for the response contract.

### Two resume-generation pipelines

- **v1 (legacy, default)** — inline in `backend/app.py`: chunk the JD into requirement/responsibility/bonus/soft-skill buckets, embed and cosine-match against resume bullets, greedily select under per-experience caps, then rewrite selected bullets with an LLM.
- **v2 (opt-in via `RESUME_PIPELINE=v2`)** — three LLM agents plus deterministic selection/trimming, documented in [`docs/v2-3-agent-resume-pipeline.md`](docs/v2-3-agent-resume-pipeline.md): a JD preprocessor, a resume ranker, and a bullet rewriter, with deterministic greedy selection and page-fit trimming in between.

## Getting started

### Backend (`backend/`, Python, FastAPI)

All commands assume `cwd = backend/`.

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env` (gitignored) with at least:

```bash
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...       # or GOOGLE_API_KEY
RESUME_PIPELINE=v1        # or v2
GENERATE_RESUME_API_KEYS=replace-with-a-long-random-secret
```

Then run the server:

```bash
python app.py            # reads PORT env, defaults to 8000
# or, for autoreload:
uvicorn app:app --reload
```

Run tests:

```bash
pytest
pytest tests/test_v2_pipeline_components.py             # one file
pytest tests/test_v2_pipeline_components.py::V2ComponentTest::test_trim_loop_reaches_one_page_deterministically  # one test
```

PDF rendering shells out to `latexmk`/`pdflatex` and `pdfinfo` (poppler). Without them installed, PDF compilation silently falls back to a stub mock PDF — fine for tests, not for a real resume.

### Frontend (`frontend/`, WXT + React + TypeScript)

```bash
cd frontend
npm install
npm run dev        # WXT dev server, loads unpacked into Chrome (MV3)
npm run build       # production build to .output/
npm run zip           # packaged .zip for distribution
npm run compile       # tsc --noEmit type check
```

`frontend/.env` / `frontend/.env.development` set `WXT_API_URL` (the backend's `/generate_resume` URL; defaults to `http://localhost:8000/generate_resume` if unset).

## Backend generate-resume protection

`POST /generate_resume` and `POST /render_resume_pdf` are guarded because they can spend external AI API credits. Set at least one API key before running or deploying the backend:

```bash
export GENERATE_RESUME_API_KEYS="replace-with-a-long-random-secret"
```

Clients can authenticate with either header format:

```http
X-API-Key: replace-with-a-long-random-secret
```

or:

```http
Authorization: Bearer replace-with-a-long-random-secret
```

Optional guardrail settings:

| Environment variable | Default | Purpose |
| --- | ---: | --- |
| `GENERATE_RESUME_API_KEYS` | none | Comma-separated list of valid API keys. If unset, `/generate_resume` fails closed with `503`. |
| `GENERATE_RESUME_RATE_LIMIT_REQUESTS` | `10` | Maximum authenticated generate requests per key/IP identity. |
| `GENERATE_RESUME_RATE_LIMIT_WINDOW_SECONDS` | `3600` | Sliding-window duration for the in-memory rate limit. |
| `GENERATE_RESUME_MAX_JOB_DESCRIPTION_CHARS` | `12000` | Maximum accepted job-description length before AI providers are called. |

The current limiter is intentionally isolated behind `InMemoryRateLimiter` in `backend/security.py` so it can be replaced with Redis or another shared store when the backend runs with multiple workers or instances.

## Repo layout

```
backend/    FastAPI app, both generation pipelines, LaTeX/PDF rendering, tests
frontend/   Chrome extension (popup, background worker, resume preview)
docs/       Pipeline and schema docs reflecting current backend/frontend behavior
data/       Supporting data
tutorial/   Walkthrough material
implementation.spec.md  Aspirational two-phase spec (roadmap, not current state)
```

## Data files

Resume content under `backend/test_data/` and `backend/agents/test_data/` is gitignored — it holds real personal resume content and is not checked in. You'll need to supply your own master resume data in the shape described in `docs/v2-3-agent-resume-pipeline.md` (v2) or generate the v1 fixture via `backend/scripts/generate_resume_data.py`.
