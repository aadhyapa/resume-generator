# Resume Generator Implementation Spec

## Purpose

Build a resume generator in two phases:

1. **Prototype:** a bare-bones Chrome extension that scrapes a job description from the active webpage, sends it to the existing backend, and returns a tailored resume generated from a test resume JSON.
2. **Production:** a scalable, authenticated application where users submit structured experience, generate tailored resumes, review/edit them, approve final output, and are protected by cost controls, caching, encryption, observability, and deployment safeguards.

## Current Codebase Audit

### Existing Structure

- `backend/app.py` exposes a FastAPI app with a single `POST /generate_resume` endpoint.
- `backend/agents/job_description_chunker.py` uses Gemini to split a job description into requirement, responsibility, bonus, and soft-skill chunks.
- `backend/agents/embedder.py` uses Gemini embeddings for text chunks.
- `backend/algorithms/matchmaker.py` ranks resume bullets against embedded job-description chunks and currently expects a local `backend/agents/test_data/resume.json` file.
- `backend/algorithms/selector.py` selects the highest-ranked bullets while enforcing total and per-experience limits.
- `backend/agents/editor.py` rewrites selected bullets against job-description chunks.
- `backend/agents/validator.py` checks edited bullets for length and fabrication.

### Gaps and Risks

#### Functional Gaps

- No Chrome extension exists yet.
- No frontend resume preview/editor exists.
- No structured API request/response models exist.
- No test resume JSON is present in the repository, even though `matchmaker.py` depends on `backend/agents/test_data/resume.json`.
- `job_description_chunker.py` prompt says it returns a JSON array, while the app expects a JSON object with category keys.
- No PDF/DOCX/HTML resume rendering pipeline exists.
- No authentication, user accounts, saved resumes, or job records exist.
- No persistence layer exists.
- No deployment configuration exists.

#### Reliability Gaps

- Broad exception handling in `backend/app.py` converts all failures into HTTP 500 responses and can mask user-input errors.
- External LLM calls are synchronous and unbounded from an application-cost perspective.
- No retries, timeouts, circuit breakers, or fallback models are defined.
- No input-size limits are enforced for job descriptions.
- No JSON schema validation is enforced on LLM responses.
- No automated tests exist.
- Dependencies are unpinned.

#### Security and Privacy Gaps

- No authentication or authorization.
- No rate limiting or abuse prevention.
- No encryption strategy for user resumes, job descriptions, or generated artifacts.
- No secret-management strategy beyond local `.env` loading.
- No PII handling policy.
- No audit logs or data-retention policy.

#### Scalability and Cost Gaps

- Embeddings and generation results are not cached.
- The backend recomputes job-description chunks and embeddings for repeated inputs.
- No token accounting, quotas, budget alerts, or per-user limits.
- No background jobs for long-running resume generation.
- No queue, worker, or asynchronous processing architecture.

## Target Architecture

### Prototype Architecture

```text
Chrome Extension
  ├─ content script scrapes job page text
  ├─ popup UI lets user trigger generation
  └─ background/service worker calls backend

FastAPI Backend
  ├─ /generate_resume accepts job_description
  ├─ loads test resume JSON
  ├─ chunks job description
  ├─ embeds chunks
  ├─ ranks/selects bullets
  ├─ edits/validates bullets
  └─ returns structured resume JSON
```

### Production Architecture

```text
Chrome Extension / Web App
  ├─ authenticated user session
  ├─ job-description capture
  ├─ resume generation request
  ├─ resume preview/editor
  └─ approval/export workflow

API Gateway / Backend
  ├─ auth middleware
  ├─ request validation
  ├─ rate limiting
  ├─ token budget enforcement
  ├─ job/resume CRUD APIs
  ├─ generation orchestration APIs
  └─ admin/observability APIs

Worker Layer
  ├─ chunk job descriptions
  ├─ embed jobs and user experiences
  ├─ retrieve cached computations
  ├─ generate tailored resume drafts
  ├─ validate outputs
  └─ render approved files

Data Layer
  ├─ relational database for users, jobs, resumes, versions, approvals
  ├─ vector store or pgvector for embeddings
  ├─ Redis for cache, idempotency keys, and rate limits
  ├─ object storage for rendered PDFs/DOCX files
  └─ secrets/KMS for encryption keys
```

## Phase 1: Prototype

### Goals

- Prove end-to-end flow with a test resume JSON.
- Prove that a Chrome extension can scrape a job description from a webpage.
- Prove that the backend can ingest the scraped text and return tailored resume content.
- Keep implementation simple and intentionally non-production.

### Non-Goals

- No authentication.
- No persistence.
- No billing or payments.
- No full resume editor.
- No multi-user scaling guarantees.
- No deployment hardening beyond local development.

### Deliverables

#### 1. Test Resume JSON

Create `backend/agents/test_data/resume.json` with normalized bullet objects:

```json
[
  {
    "bullet_id": "exp_001_b001",
    "experience_id": "exp_001",
    "company": "Example Company",
    "title": "Software Engineer",
    "start_date": "2022-01",
    "end_date": "2024-01",
    "text": "Built internal APIs that improved operational reporting for customer support teams."
  }
]
```

Required fields:

- `bullet_id`
- `experience_id`
- `company`
- `title`
- `start_date`
- `end_date`
- `text`

Optional fields:

- `skills`
- `metrics`
- `projects`
- `embedding`

#### 2. Backend Request/Response Contracts

Replace primitive `job_description: str` input with Pydantic models.

Example request:

```json
{
  "job_description": "Full job description text...",
  "options": {
    "total_bullets": 20,
    "per_experience_limit": 4,
    "min_chars": 50,
    "max_chars": 300
  }
}
```

Example response:

```json
{
  "resume": {
    "experiences": [
      {
        "experience_id": "exp_001",
        "company": "Example Company",
        "title": "Software Engineer",
        "bullets": [
          {
            "bullet_id": "exp_001_b001",
            "text": "Built internal APIs that improved operational reporting for customer support teams.",
            "score": 0.83,
            "bold_words": ["internal APIs", "operational reporting"]
          }
        ]
      }
    ]
  },
  "metadata": {
    "model": "gemini-3.1-flash-lite",
    "validation_passed": true,
    "warnings": []
  }
}
```

#### 3. Fix Job Chunker Contract

Make `job_description_chunker.py` and `job_description_chunker.txt` agree on one format:

```json
{
  "requirement": [],
  "responsibility": [],
  "bonus": [],
  "soft-skills": []
}
```

Acceptance criteria:

- Missing categories default to empty arrays.
- Invalid LLM JSON is surfaced as a typed backend error.
- Markdown-fenced JSON is stripped safely.

#### 4. Chrome Extension MVP

Create a `chrome-extension/` directory with:

- `manifest.json`
- `popup.html`
- `popup.js`
- `contentScript.js`
- `background.js` or Manifest V3 service worker
- `styles.css`

MVP behavior:

1. User opens a job posting.
2. User clicks the extension icon.
3. Popup shows a button: `Generate Resume`.
4. Content script extracts likely job-description text from the page.
5. Extension sends text to local backend.
6. Popup displays returned resume bullets grouped by experience.
7. User can copy the generated resume JSON or plain text.

Scraping approach:

- First try known semantic containers: `main`, `article`, `[class*=job]`, `[id*=job]`, `[class*=description]`, `[id*=description]`.
- Fallback to cleaned `document.body.innerText`.
- Remove repeated whitespace.
- Enforce max character length before sending to backend.

#### 5. Local Development Setup

Add developer commands to `README.md`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload
```

Add Chrome extension loading instructions:

1. Open `chrome://extensions`.
2. Enable Developer Mode.
3. Click `Load unpacked`.
4. Select `chrome-extension/`.

#### 6. Prototype Tests

Add minimal tests:

- Unit test for `selector`.
- Unit test for chunker JSON cleanup/parsing helper.
- Unit test for job-description text cleanup in the extension if using a testable helper.
- Backend route test with LLM calls mocked.

### Prototype Milestones

#### Milestone 1.1: Backend Stabilization

- Add Pydantic schemas.
- Add test resume JSON.
- Fix chunker schema mismatch.
- Add basic backend tests.

#### Milestone 1.2: Chrome Extension Skeleton

- Add manifest and popup.
- Add content script scraper.
- Add local backend call.

#### Milestone 1.3: End-to-End Prototype

- Run backend locally.
- Load extension locally.
- Scrape a job page.
- Generate resume bullets from test JSON.
- Copy output.

### Prototype Acceptance Criteria

- From a real job posting webpage, the extension can generate a resume draft from the test JSON.
- Backend returns structured JSON with selected and edited bullets.
- Empty job descriptions return HTTP 400.
- Oversized job descriptions are rejected or trimmed before LLM calls.
- At least one automated backend route test passes with mocked LLM calls.

## Phase 2: Production

### Goals

- Add authentication and user-specific experience storage.
- Let users submit experience in job-application-style forms.
- Generate tailored resumes from user data.
- Let users review, edit, approve, and export resumes.
- Add safeguards to prevent runaway token cost.
- Add caching, encryption, observability, and scalable infrastructure.

### Non-Goals for Initial Production Launch

- No marketplace integrations unless explicitly prioritized.
- No fully automated job applications.
- No unsupported claims that generated resumes guarantee interviews.
- No training on user data without explicit consent.

## Production Functional Requirements

### 1. Authentication and Authorization

Implement one of:

- Managed auth provider such as Auth0, Clerk, Firebase Auth, or Supabase Auth.
- First-party auth using OAuth/OIDC plus secure session cookies.

Requirements:

- Email/password and Google OAuth.
- Email verification.
- Password reset if using password auth.
- Session expiration and refresh.
- Per-user authorization on every resume, job, and generation request.
- Admin-only endpoints guarded by role checks.

### 2. User Experience Intake

Create a structured form similar to job-application work-history forms.

Entities:

- Profile
- Work experience
- Education
- Projects
- Certifications
- Skills
- Awards
- Publications
- Volunteer experience

Work experience fields:

- Company
- Title
- Location
- Start date
- End date
- Current role flag
- Employment type
- Description
- Bullet achievements
- Skills/tools used
- Metrics/results

Validation:

- Require title, company, dates, and at least one bullet for each experience.
- Encourage metrics but do not require them.
- Prevent impossible date ranges.
- Allow importing from existing resume later as a separate enhancement.

### 3. Resume Generation Workflow

Workflow states:

1. `draft_requested`
2. `queued`
3. `processing`
4. `needs_review`
5. `edited_by_user`
6. `approved`
7. `exported`
8. `failed`

Generation steps:

1. Normalize scraped or pasted job description.
2. Deduplicate job description by content hash.
3. Chunk job description.
4. Embed chunks.
5. Retrieve or embed user experience bullets.
6. Score and select relevant bullets.
7. Generate tailored resume draft.
8. Validate for fabrication, length, and formatting.
9. Store versioned draft.
10. Present editable draft to user.
11. Require explicit user approval before export.

### 4. Resume Preview and Editing

The production app must include a resume editor with:

- Section reordering.
- Bullet editing.
- Bullet approval/rejection.
- Highlighted changes from original experience.
- Warnings for possible fabrication.
- Resume template selection.
- One-page/two-page layout hints.
- Save draft.
- Approve final version.
- Export PDF and DOCX.

### 5. Chrome Extension Production Behavior

- User must be authenticated before generation.
- Extension sends job text to production API with an auth token or secure session flow.
- Extension should display generation status rather than blocking indefinitely.
- Extension opens the web app for editing/approval.
- Extension should never store raw user resume data in Chrome local storage unless encrypted and necessary.

## Production Data Model

### Core Tables

#### users

- `id`
- `email`
- `name`
- `auth_provider`
- `created_at`
- `updated_at`
- `deleted_at`

#### profiles

- `id`
- `user_id`
- `full_name`
- `headline`
- `location`
- `phone_encrypted`
- `email_encrypted`
- `links_encrypted`
- `created_at`
- `updated_at`

#### experiences

- `id`
- `user_id`
- `company`
- `title`
- `location`
- `start_date`
- `end_date`
- `is_current`
- `description_encrypted`
- `created_at`
- `updated_at`

#### experience_bullets

- `id`
- `experience_id`
- `user_id`
- `text_encrypted`
- `normalized_text_hash`
- `embedding_id`
- `skills_json_encrypted`
- `metrics_json_encrypted`
- `created_at`
- `updated_at`

#### jobs

- `id`
- `user_id`
- `source_url`
- `company`
- `title`
- `description_encrypted`
- `description_hash`
- `chunk_cache_key`
- `created_at`
- `updated_at`

#### resume_generations

- `id`
- `user_id`
- `job_id`
- `status`
- `request_options_json`
- `input_token_count`
- `output_token_count`
- `estimated_cost_cents`
- `model`
- `error_code`
- `error_message`
- `created_at`
- `updated_at`

#### resume_versions

- `id`
- `generation_id`
- `user_id`
- `version_number`
- `resume_json_encrypted`
- `validation_report_json`
- `approved_at`
- `created_at`

#### exports

- `id`
- `resume_version_id`
- `user_id`
- `format`
- `storage_url_encrypted`
- `created_at`

#### usage_events

- `id`
- `user_id`
- `event_type`
- `model`
- `input_tokens`
- `output_tokens`
- `cost_cents`
- `request_hash`
- `created_at`

## Production API Plan

### Auth

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

If using managed auth, these may be handled by the provider and replaced by middleware.

### Profile and Experience

- `GET /profile`
- `PUT /profile`
- `GET /experiences`
- `POST /experiences`
- `PUT /experiences/{experience_id}`
- `DELETE /experiences/{experience_id}`
- `POST /experiences/{experience_id}/bullets`
- `PUT /experience-bullets/{bullet_id}`
- `DELETE /experience-bullets/{bullet_id}`

### Jobs

- `POST /jobs` to submit scraped or pasted job description.
- `GET /jobs`
- `GET /jobs/{job_id}`

### Resume Generation

- `POST /resume-generations`
- `GET /resume-generations/{generation_id}`
- `GET /resume-generations/{generation_id}/status`
- `GET /resume-generations/{generation_id}/versions`

### Resume Editing and Approval

- `GET /resume-versions/{version_id}`
- `PUT /resume-versions/{version_id}`
- `POST /resume-versions/{version_id}/approve`
- `POST /resume-versions/{version_id}/export`

## Cost-Control Safeguards

### Hard Limits

- Maximum job-description length.
- Maximum number of generations per user per day.
- Maximum number of retries per generation.
- Maximum input tokens per generation.
- Maximum output tokens per generation.
- Maximum monthly cost per user.
- Maximum global daily spend.

### Soft Controls

- Warn users before regenerating if a recent generation exists for the same job.
- Prefer cached chunks and embeddings.
- Use lower-cost models for extraction and validation.
- Reserve expensive models only for final editing if quality requires it.
- Batch embedding requests where supported.

### Abuse Prevention

- Per-IP and per-user rate limits.
- CAPTCHA or additional verification for suspicious signups.
- Idempotency keys for generation requests.
- Request hashing to prevent repeated identical expensive calls.
- Queue-level throttles.
- Admin kill switch for LLM generation.

### Cost Observability

Track per request:

- User ID.
- Model.
- Prompt version.
- Input tokens.
- Output tokens.
- Embedding count.
- Estimated cost.
- Cache hit/miss.
- Retry count.

Alert on:

- Daily spend threshold.
- User-level abnormal usage.
- Error-rate spikes.
- Cache hit-rate drops.
- Token usage anomalies.

## Caching Strategy

### Cache Keys

- Job description normalized text hash.
- Prompt version.
- Model version.
- Chunker schema version.
- User bullet normalized text hash.
- Generation options hash.

### Cache Layers

#### Redis

Use for:

- Rate limits.
- Idempotency keys.
- Short-lived job-description chunk cache.
- Generation status.
- Session-related transient state if needed.

#### Database

Use for:

- Persistent job-description chunks keyed by hash.
- Persistent embeddings keyed by normalized text hash and model.
- Resume generation metadata.

#### Vector Store

Use for:

- User bullet embeddings.
- Job chunk embeddings.
- Similarity retrieval at scale.

Initial production recommendation: Postgres with `pgvector` to reduce operational complexity. Move to a dedicated vector database only if scale or performance requires it.

## Encryption and Data Protection

### In Transit

- Enforce HTTPS everywhere.
- Use secure cookies with `HttpOnly`, `Secure`, and `SameSite` settings.
- Use HSTS in production.

### At Rest

- Encrypt database volumes.
- Encrypt object storage.
- Encrypt sensitive fields at the application layer:
  - Phone numbers.
  - Email addresses.
  - Links if private.
  - Raw resume text.
  - Experience descriptions.
  - Job descriptions.
  - Generated resume JSON.

### Key Management

- Use managed KMS in production.
- Use envelope encryption for sensitive user data.
- Rotate keys on a defined schedule.
- Separate production, staging, and development keys.
- Never log decrypted resume content.

### Privacy Controls

- Let users delete their data.
- Define retention policy for generated resumes and job descriptions.
- Provide export of user data.
- Add consent text explaining AI processing.
- Avoid using user data for model training unless explicitly opted in.

## Scalability Plan

### Backend

- Keep API stateless.
- Move LLM generation to background workers.
- Use queue-based processing with retries and dead-letter queues.
- Horizontally scale API and worker pools independently.

### Recommended Stack

- FastAPI for API.
- Postgres for relational data.
- pgvector for embeddings.
- Redis for cache/rate limits.
- Celery, RQ, Dramatiq, or a managed queue for workers.
- S3-compatible object storage for exports.
- OpenTelemetry for traces and metrics.

### Queue Design

Queues:

- `default`
- `embeddings`
- `generation`
- `exports`
- `validation`

Retry policy:

- Retry transient provider errors with exponential backoff.
- Do not retry validation/schema errors indefinitely.
- Send repeated failures to a dead-letter queue.

## Safety and Quality Validation

### Programmatic Validation

- Character limits.
- Section ordering.
- Required fields.
- JSON schema validity.
- No empty bullets.
- No duplicate bullets.
- No unsupported date modifications.

### AI-Based Validation

- Fabrication detection.
- Tone check.
- Job relevance check.
- ATS keyword coverage.

### User-Facing Safeguards

- Show changed bullets compared to originals.
- Flag statements that may be unsupported.
- Require user approval before export.
- Add disclaimer that the user is responsible for truthfulness.

## Prompt and Model Governance

- Version every prompt.
- Store prompt version in generation metadata.
- Store model name and model parameters.
- Add golden test cases for prompts.
- Require schema validation on every model response.
- Prefer structured output modes when available.
- Track quality regressions across prompt versions.

## Deployment Plan

### Environments

- Local
- Staging
- Production

### CI/CD Requirements

- Linting.
- Unit tests.
- API contract tests.
- Migration checks.
- Dependency vulnerability scanning.
- Secret scanning.
- Build Chrome extension artifact.

### Production Readiness Checklist

- Auth enabled.
- Rate limits enabled.
- Daily spend cap enabled.
- Provider keys stored in secret manager.
- Database backups enabled.
- Encryption enabled.
- Centralized logs enabled with PII redaction.
- Metrics and alerts configured.
- Error monitoring configured.
- Data deletion flow tested.
- Terms/privacy policy published.

## Suggested Implementation Order

## Estimated Timeline

These estimates assume one experienced full-stack engineer working primarily on this project, starting from the current codebase state. Calendar time can shrink with parallel engineering work, but only if responsibilities are split cleanly across backend, extension/frontend, infrastructure, and product/security review.

### Prototype Estimate

Expected duration: **2 to 4 weeks**.

| Workstream | Estimate | Notes |
| --- | ---: | --- |
| Backend stabilization | 3 to 5 days | Add schemas, test resume JSON, chunker parsing fixes, input limits, and mocked tests. |
| Chrome extension MVP | 4 to 7 days | Build Manifest V3 extension, page scraping, popup flow, backend call, and output display/copy behavior. |
| End-to-end integration | 2 to 4 days | Exercise the extension against real job pages, fix scraping edge cases, and stabilize local developer setup. |
| Buffer | 2 to 5 days | Covers LLM output-format issues, Chrome extension permission friction, and basic UX polish. |

Prototype completion means the extension can scrape a real job posting, call the local backend, generate a tailored draft from test JSON, and show copyable output.

### Production MVP Estimate

Expected duration after prototype: **10 to 16 weeks** for a focused production MVP.

| Workstream | Estimate | Notes |
| --- | ---: | --- |
| Product and UX decisions | 1 to 2 weeks | Choose auth provider, resume templates, export formats, pricing/free-tier assumptions, and extension-vs-web-app ownership. |
| Auth and user data foundation | 2 to 3 weeks | Add auth, database migrations, user/profile/experience CRUD, authorization checks, and encrypted sensitive fields. |
| Scalable generation pipeline | 2 to 4 weeks | Add queues/workers, generation statuses, cached chunks/embeddings, idempotency keys, retries, and provider error handling. |
| Resume editor and approval workflow | 2 to 3 weeks | Build preview, edit-in-place, versioning, approval, diff/warning UI, and draft persistence. |
| Export pipeline | 1 to 2 weeks | Render approved resumes to PDF and optionally DOCX, store artifacts, and expose downloads. |
| Cost controls and observability | 1 to 2 weeks | Add rate limits, token accounting, spend caps, metrics, alerts, logs with PII redaction, and admin kill switches. |
| Security and launch hardening | 1 to 2 weeks | Backups, secret management, production configuration, privacy/data-deletion flows, and deployment checklist. |

Production MVP completion means authenticated users can enter experience, generate tailored resumes from captured job descriptions, edit and approve drafts, export final files, and operate under rate limits, token budgets, caching, encryption, and monitoring.

### Realistic Total Timeline

- **Prototype only:** 2 to 4 weeks.
- **Prototype plus production MVP:** 3 to 5 months.
- **More polished SaaS launch:** 5 to 8 months if adding billing, multiple resume templates, better import flows, stronger analytics, support tooling, and extensive browser/job-board compatibility.

### Main Schedule Risks

- Chrome scraping quality varies widely across job boards.
- LLM JSON/schema adherence may require structured-output wrappers and robust retry logic.
- Resume editor/export quality can take longer than expected because layout and PDF/DOCX fidelity are product-critical.
- Security and privacy work should not be compressed because the app handles sensitive career and contact data.
- Cost controls must be implemented before broad launch, not after, because uncontrolled retries and repeated generations can become expensive quickly.

## Recommended Weekend Goal

For one weekend, the goal should be: **finish a local end-to-end prototype path, not the whole prototype**.

By the end of the weekend, aim to prove this single flow:

1. A known test resume JSON exists in the backend.
2. A pasted or scraped job description can be sent to the backend.
3. The backend returns selected resume bullets without crashing.
4. The result can be viewed or copied from a minimal Chrome extension popup or, if the extension takes too long, from a simple local API test/client.

### Weekend Scope

Prioritize the smallest path that reduces uncertainty:

| Priority | Task | Target Outcome |
| --- | --- | --- |
| 1 | Add `backend/agents/test_data/resume.json` | The existing `matchmaker.py` has real local data to rank. |
| 2 | Fix the chunker contract mismatch | The backend expects a dictionary with `requirement`, `responsibility`, `bonus`, and `soft-skills` arrays. |
| 3 | Add basic request validation | Empty or oversized job descriptions fail cleanly before expensive model calls. |
| 4 | Add a smoke-test script or mocked route test | You can verify the backend path repeatedly without relying on manual clicking. |
| 5 | Create the Chrome extension shell | A popup button can scrape or collect job text and send it to the local backend. |

### Weekend Non-Goals

Do not spend the weekend on:

- Authentication.
- Database design.
- PDF/DOCX export.
- Billing.
- Full resume editing.
- Perfect Chrome scraping across every job board.
- Production-grade encryption, queues, or caching.

Those are production-phase concerns. This weekend should answer one question: **can this concept work end-to-end with local test data?**

### Suggested Weekend Breakdown

#### Friday Evening

- Re-read the current backend flow.
- Create the test resume JSON.
- Run the backend locally.
- Confirm where the current `/generate_resume` path fails.

#### Saturday

- Fix schema/contract issues.
- Add validation for empty and oversized job descriptions.
- Add a mocked backend route test or smoke script.
- Get one successful backend response from a realistic pasted job description.

#### Sunday

- Add the Chrome extension shell.
- Implement basic job-text scraping and backend submission.
- Display returned bullets in the popup.
- Write down the top three next blockers for the following week.

### Weekend Definition of Done

- A test resume JSON is committed.
- The backend can generate a resume-like response from one realistic job description.
- There is at least one repeatable check, test, or script for the backend flow.
- A minimal extension shell exists, even if scraping is imperfect.
- Any known limitations are documented for the next sprint.

### Sprint 1: Stabilize Existing Backend

1. Add schemas.
2. Add test resume JSON.
3. Fix chunker output parsing.
4. Add mocked tests.
5. Update README.

### Sprint 2: Build Chrome Extension Prototype

1. Add Manifest V3 extension.
2. Add content scraper.
3. Add popup generation flow.
4. Add copy-to-clipboard output.
5. Run manual end-to-end test.

### Sprint 3: Resume Preview Foundation

1. Add simple web preview page or extension preview.
2. Group bullets by experience.
3. Add basic edit-in-place behavior.
4. Add export-to-plain-text or print-to-PDF.

### Sprint 4: Production Data Foundation

1. Add database.
2. Add migrations.
3. Add user and experience models.
4. Add CRUD APIs.
5. Add encryption helpers.

### Sprint 5: Auth and Secure User Flows

1. Add auth provider.
2. Protect APIs.
3. Add user-specific data access checks.
4. Update extension auth flow.

### Sprint 6: Scalable Generation Pipeline

1. Add queue and workers.
2. Add generation statuses.
3. Add cache keys and Redis.
4. Add token accounting.
5. Add spend limits.

### Sprint 7: Review, Approval, and Export

1. Add resume editor.
2. Add versioning.
3. Add approval flow.
4. Add PDF/DOCX export.

### Sprint 8: Production Hardening

1. Add monitoring.
2. Add alerts.
3. Add backup/restore tests.
4. Add abuse prevention.
5. Run load tests.
6. Complete privacy and compliance checklist.

## Open Decisions

- Which auth provider should be used?
- Should the main user interface be extension-first, web-app-first, or both?
- Which LLM provider should be primary in production?
- Should generated resumes be exported as PDF only initially, or PDF and DOCX?
- What is the acceptable cost per successful resume generation?
- What monthly free-tier quota, if any, should users receive?
- What resume templates are required for launch?

## Definition of Done

### Prototype Done

- Chrome extension scrapes a job page.
- Backend generates a tailored resume from test JSON.
- Output is visible and copyable.
- Basic backend tests pass with LLM calls mocked.
- README explains local setup.

### Production Done

- Users can sign up, submit experience, generate resumes, edit drafts, approve final versions, and export files.
- Per-user authorization is enforced.
- Sensitive data is encrypted.
- Generation requests are cached where appropriate.
- Token usage and costs are tracked.
- Rate limits and spend caps are active.
- Monitoring and alerts are configured.
- Deployment process is repeatable through CI/CD.
