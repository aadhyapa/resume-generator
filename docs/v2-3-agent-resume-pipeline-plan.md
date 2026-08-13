# V2 3-Agent Resume Customization Pipeline Plan

## Inspection summary

This repository currently has a Python/FastAPI backend and a TypeScript/React WXT browser-extension frontend. The backend package manager is `pip` via `backend/requirements.txt`; the frontend package manager is npm via `frontend/package.json` and `frontend/package-lock.json`.

### Current backend request flow

`POST /generate_resume` in `backend/app.py` currently performs the full customization flow inline:

1. Validate and size-limit the raw job description.
2. Run `agents.job_description_chunker.job_description_chunker` to split the raw JD into verbatim categories.
3. Generate Gemini embeddings for each JD chunk category via `agents.embedder.embed`.
4. Load the master resume fixture from `backend/test_data/resume_data_embedded.json`.
5. Rank embedded resume bullets with `algorithms.matchmaker.matchmaker` using cosine similarity and category weights.
6. Select a fixed number of bullets with `algorithms.selector.selector` using a greedy global/per-subsection cap.
7. Rewrite selected bullets using the Claude-backed `agents.editor.editor`.
8. Validate rewritten bullets with `agents.validator.validate_resume`.
9. Assemble the final resume object with `algorithms.formatter.formater`.
10. Return `{ "message": ..., "resume": ... }` to the extension.

### Current resume representation and data models

There are no explicit Pydantic resume models today. The master resume is a JSON object stored in `backend/test_data/resume_data_embedded.json` with these top-level fields:

- `header`: contact metadata.
- `sections`: a list of section descriptors containing stable `section_id` values.
- `sub_sections`: a list of subsection descriptors containing stable `sub_section_id` and `section_id` values.
- `bullets`: a flat list of bullet descriptors containing stable `bullet_id`, `sub_section_id`, `text`, optional `bold_words`, and currently persisted `embedding` arrays.
- `skills`: grouped skill metadata.

`algorithms.formatter.formater` transforms this flat master-resume representation into the nested frontend/LaTeX shape by copying `header`, `skills`, each section, and each selected subsection's bullets into `resume[section_id].sub_sections[sub_section_id].bullets`.

### Current job-description processing

`agents.job_description_chunker.job_description_chunker` uses Gemini (`google.genai`) with `backend/agents/prompts/job_description_chunker.txt` and `backend/agents/formats/job_description_chunker.json`. It outputs four verbatim chunk buckets: `requirement`, `responsibility`, `bonus`, and `soft-skills`. This is useful for the V1 embedding flow but does not produce the conceptual structured JD required for V2.

### Current LLM integrations

Existing LLM calls are direct client calls, not centralized behind one provider abstraction:

- `agents.job_description_chunker` uses `google.genai.Client(...).models.generate_content(...)` with model `gemini-3.1-flash-lite`.
- `agents.embedder` uses `google.genai.Client(...).models.embed_content(...)` with model `gemini-embedding-001`.
- `agents.editor` uses `anthropic.Anthropic(...).messages.create(...)` with model `claude-sonnet-5`.
- `agents.validator` uses `anthropic.Anthropic(...).messages.create(...)` with model `claude-haiku-4-5`.

V2 should introduce a small shared LLM client/configuration layer rather than adding more hard-coded model strings.

### Current embedding/vector database usage

The live backend generates embeddings through Gemini in `agents.embedder`. The master resume fixture stores embeddings inline on bullets. There is no active database adapter or runtime pgvector query path in the inspected code. Pgvector/Supabase appears in planning/tutorial material and in one sample resume bullet describing the project, but not as an active backend dependency or query implementation.

### Current bullet retrieval/ranking logic

`algorithms.matchmaker` computes cosine similarity between each JD chunk embedding and each resume bullet embedding, weighted by category. It mutates bullets by adding a cumulative `score`, sorts the flat bullet list descending, and returns the sorted list. `algorithms.selector` then greedily selects bullets from that flat ranking with only a global bullet cap and per-subsection cap. It does not model section priority, subsection coverage, marginal value, redundancy, unsupported requirements, or page-fit loss.

### Current rewriting and validation logic

`agents.editor.editor` rewrites selected bullets only after selection. It trims each bullet to `bullet_id`, `text`, and `bold_words`, injects JSON into `backend/agents/prompts/editor.txt`, calls Claude, parses JSON, and merges edited `text`/`bold_words` back onto the original selected bullets. `agents.validator.validate_resume` checks character limits programmatically and uses Claude to detect fabrication in edited bullets.

### Current LaTeX/PDF flow

`services.latexter.render_resume_latex` renders the nested resume object into a LaTeX resume. `services.pdf_compiler.compile_resume_with_length_check` compiles rendered LaTeX to PDF and counts pages, retrying with deterministic spacing/font profiles. It currently does not remove resume content when the page count remains too high after spacing attempts.

### Current API/frontend integration

The extension calls the backend from `frontend/entrypoints/background.ts` by posting `{ job_description }` to `/generate_resume` and stores `data.resume` on success. The frontend already expects the full nested resume object through TypeScript types and runtime guards under `frontend/entrypoints/popup`.

### Existing tests

Current tests are minimal:

- `backend/tests/test_latexter.py` covers LaTeX escaping, rendering order/project formatting, bold rendering, and the PDF spacing retry loop with fake compiler/page-counter functions.
- `backend/test_pipeline.py` is a manual script that calls the FastAPI endpoint function directly and is not a robust automated test.

## Where V2 should plug in

V2 should be added behind a feature flag in the backend generation path, not integrated as the default yet. The clean plug-in point is after `generate_resume` validates the raw job description and loads the master resume, replacing the current V1 sequence of JD chunking → embeddings → matchmaker → fixed selector → editor. The route should delegate to a pipeline service selected by configuration:

- `RESUME_PIPELINE=v1`: keep current behavior.
- `RESUME_PIPELINE=v2`: run JD Preprocessor → Resume Ranker → deterministic selector/trimmer → Bullet Rewriter.

Because the user requested not to integrate into the main workflow yet, this document only plans the changes. The implementation should be introduced as isolated modules, tests, and documentation first, then wired into the route in a later change.

## Proposed V2 module layout

```text
backend/
  config.py
  llm/
    __init__.py
    client.py
    json_utils.py
  models/
    __init__.py
    resume.py
    jd.py
    ranking.py
    rewriting.py
    selection.py
    trace.py
  serializers/
    __init__.py
    resume_compact.py
  agents/
    v2/
      __init__.py
      jd_preprocessor.py
      resume_ranker.py
      bullet_rewriter.py
      prompts/
        jd_preprocessor.txt
        resume_ranker.txt
        bullet_rewriter.txt
        bullet_compressor.txt
  algorithms/
    v2_selector.py
    v2_trimmer.py
  services/
    v2_pipeline.py
    resume_repository.py
    pipeline_router.py
  tests/
    test_v2_jd_preprocessor.py
    test_v2_resume_ranker_validation.py
    test_v2_selector.py
    test_v2_trimmer.py
    test_v2_bullet_rewriter_validation.py
    test_v2_pipeline.py
```

## Configuration plan

Add a backend configuration module that reads environment variables once and exposes typed settings:

- `RESUME_PIPELINE`, default `v1` until the V2 rollout is explicitly enabled.
- `JD_PREPROCESSOR_MODEL`, default to a cheap/fast model such as the existing Gemini flash-lite model.
- `RESUME_RANKER_MODEL`, default to a Claude Sonnet-class model.
- `BULLET_REWRITER_MODEL`, default to a Claude Sonnet-class model.
- `BULLET_REWRITER_MAX_COMPRESSION_ITERATIONS`, default `2`.
- `RESUME_V2_DEBUG_TRACE`, default false.
- `RESUME_V2_TRACE_DIR`, default a non-public backend-local debug directory.

Avoid hard-coded model names in agent implementations. Keep provider-specific details in `backend/llm/client.py` or equivalent.

## Strong schema/model plan

Use Pydantic for runtime validation. If adding Pydantic is undesirable, use dataclasses plus explicit validators; however, Pydantic is preferred because FastAPI already commonly uses it and it gives strict schema validation for LLM JSON.

### Master resume model

Create typed models matching the existing flat master resume shape:

- `MasterResume`
- `ResumeHeader`
- `ResumeSection`
- `ResumeSubSection`
- `ResumeBullet`
- `ResumeSkills`

Validation requirements:

- Every `section_id` is unique.
- Every `sub_section_id` is unique.
- Every `bullet_id` is unique.
- Every subsection references an existing section.
- Every bullet references an existing subsection.
- Embeddings are accepted but ignored by V2 serialization/ranking.

### Agent 1 structured JD model

Create `StructuredJobDescription` with fields similar to:

- `role: str | None`
- `company: str | None`
- `seniority: str | None`
- `summary: str`
- `requirements: list[JobRequirement]`
- `skills: list[JobSkill]`
- `responsibilities: list[JobResponsibility]`
- `domain_knowledge: list[WeightedConcept]`
- `system_design_requirements: list[WeightedConcept]`
- `soft_skills: list[WeightedConcept]`
- `leadership_requirements: list[WeightedConcept]`
- `education_requirements: list[WeightedConcept]`
- `certifications: list[WeightedConcept]`
- `important_keywords: list[WeightedConcept]`
- `important_concepts: list[WeightedConcept]`
- `overall_priorities: dict[str, int]`
- `ambiguities: list[str]`

Validation requirements:

- Importance scores are integers from 0 to 100.
- Requirement IDs are present and unique.
- Requirement categories are from a controlled enum.
- Empty/missing JD information is represented as `None`, empty lists, and `ambiguities`, not fabricated values.

### Agent 2 ranking model

Create `ResumeRanking` with:

- `job_fit_summary`
- `section_rankings: list[SectionRanking]`
- `subsection_rankings: list[SubsectionRanking]`
- `skills_analysis`
- `unsupported_requirements: list[UnsupportedRequirement]`

Validation requirements:

- Every referenced section ID exists in the master resume.
- Every referenced subsection ID exists and is attached to the stated section.
- Every referenced bullet ID exists and is attached to the stated subsection.
- Every rankable bullet is ranked exactly once.
- No duplicate section/subsection/bullet IDs.
- Every score is in `[0, 100]`.
- Agent 2 output cannot include rewritten bullet text.

### Selection model

Create `SelectedResumeContent` that stores stable IDs only:

- `sections: dict[section_id, SelectedSection]`
- `subsections: dict[sub_section_id, SelectedSubsection]`
- `skills: SelectedSkills`
- `removed_items: list[SelectionRemoval]`
- `selection_reason_trace: list[str]`

The model should support conversion into the existing nested resume object through the existing formatter path or a V2-specific formatter adapter.

### Agent 3 rewriting model

Create `BulletRewriteResponse` with:

- `rewritten_bullets: list[RewrittenBullet]`

Validation requirements:

- Every selected bullet ID appears exactly once.
- No unselected bullet IDs appear.
- `original_text` exactly matches the selected source bullet text.
- Numeric tokens from `original_text` are preserved in `rewritten_text` unless an explicit deterministic allowance is added later.
- Known employers, dates, and technologies from subsection metadata/source text are not changed.

## Agent prompt plan

### Agent 1 prompt: JD Preprocessor

Create `backend/agents/v2/prompts/jd_preprocessor.txt`.

Required instructions:

- Understand what the employer wants from the raw JD.
- Normalize conceptual requirements beyond literal keywords.
- Distinguish required vs preferred evidence.
- Assign importance based on the JD, not on a candidate resume.
- Do not see or reference the resume.
- Do not recommend resume content.
- Return only JSON conforming to the schema.

### Agent 2 prompt: Resume Ranker

Create `backend/agents/v2/prompts/resume_ranker.txt`.

Required instructions:

- Consume only the structured JD and compact master-resume serialization.
- Rank section → subsection → bullet hierarchically.
- Evaluate section priority, subsection priority, coverage value, bullet relevance, impact, technical relevance, evidence strength, uniqueness, redundancy, and overall value.
- Return only stable IDs from the master resume.
- Never rewrite bullets.
- Never invent IDs, technologies, metrics, employers, dates, or responsibilities.
- Mark unsupported requirements instead of filling gaps.
- Return only JSON conforming to the schema.

### Agent 3 prompt: Bullet Rewriter

Create `backend/agents/v2/prompts/bullet_rewriter.txt` and a compression variant or mode.

Required instructions:

- Consume the structured JD and only selected bullet content with enough factual context from the master resume.
- Rewrite only selected bullets.
- Preserve selected IDs and order.
- Preserve factual claims, numbers, dates, employers, technologies, and accomplishments.
- Do not add, remove, reorder, or select bullets.
- Optimize clarity, concision, impact, technical specificity, and JD-aligned wording.
- Return only JSON keyed by bullet IDs.

The compression mode should state that the rewritten resume exceeded one page and ask only for shorter wording while preserving all selected content and facts.

## Compact resume serialization plan

Create `serializers.resume_compact.serialize_master_resume_for_ranking(master_resume)` that emits compact text such as:

```text
EDUCATION [sec_education]
[edu1] Michigan State University | Bachelor of Science in Computer Science, 3.98 | May 2027 | East Lansing, MI
[e_edu1_b1] Data Structures and Algorithms, Operating Systems, Database Systems, Computer Networks

EXPERIENCE [sec_experience]
[exp1] Quality Assurance Engineer — Hudl | May 2025 - Current | Lincoln, NE
[e_exp1_b1] Improved CI reliability ...
```

Rules:

- Preserve `section_id`, `sub_section_id`, and `bullet_id`.
- Exclude embeddings and other internal metadata.
- Include subsection title/company/role/date/location/tools fields when present.
- Keep stable ordering from the master resume.

Create `serialize_selected_content_for_rewriter(master_resume, selected_ids)` that includes only selected bullet IDs and concise subsection context.

## Deterministic selector plan

Create `algorithms.v2_selector.select_resume_content(master_resume, ranking, options)`.

Selection should be deterministic and ID-based:

1. Normalize each bullet's marginal value:
   - `base = bullet.overall`
   - Add weighted section and subsection priority.
   - Penalize redundancy.
   - Preserve uniqueness.
   - Apply a small deterministic tie-breaker using original resume order.
2. Include recommended sections whose priority exceeds a configurable threshold or whose minimum content is positive.
3. Preserve important subsection coverage by selecting up to `minimum_bullets` for high-priority recommended subsections before adding extras.
4. Add bullets up to each subsection's `recommended_bullets`, then optional extras up to `maximum_bullets` by marginal value.
5. Treat skills as a section-level selection using `skills_analysis`, not an LLM rewriting target.
6. Return only stable IDs and a trace explaining each deterministic inclusion/exclusion.

Avoid top-N global bullet selection. Coverage should be explicit, especially for high-priority experiences/projects.

## Marginal-value calculation plan

Create a pure function such as:

```python
def bullet_marginal_value(section, subsection, bullet, selected_sibling_bullets) -> float:
    return (
        0.45 * bullet.overall
        + 0.20 * bullet.relevance
        + 0.15 * subsection.priority
        + 0.10 * section.priority
        + 0.10 * bullet.uniqueness
        - 0.20 * bullet.redundancy
        - sibling_redundancy_penalty(selected_sibling_bullets, bullet)
    )
```

The exact weights should be constants covered by tests. Scores are ranking signals, not mathematically precise claims.

## Page fitting/trimming plan

Create `algorithms.v2_trimmer.trim_to_page_limit(...)` that works with existing LaTeX/PDF services:

1. Convert `SelectedResumeContent` to the nested resume object.
2. Compile with `services.pdf_compiler.compile_resume_with_length_check`.
3. If it fits, return the selection and compile result.
4. If not, remove one deterministic lowest-loss removable item.
5. Recompile and repeat until it fits or no removable item remains.

Removal loss should consider:

- Bullet marginal value.
- Section priority.
- Subsection priority.
- Whether the bullet is the only selected bullet in an important subsection.
- Whether removal would violate subsection `minimum_bullets`.
- Whether removal would eliminate an important section.
- Redundancy, where highly redundant bullets are easier to remove.

Low-priority whole sections can be removed when their section priority/recommended status permits and when doing so has lower total loss than removing important experience coverage.

This loop must not call Agent 2 or any LLM.

## Agent 3 page-length safety plan

After final selection is rewritten:

1. Render/compile the rewritten resume.
2. If it fits, finish.
3. If it exceeds one page, call Agent 3 in compression mode up to the configured iteration limit.
4. Recompile after each compression response.
5. If it still does not fit, fallback to deterministic trimming using existing rankings without rerunning Agent 2.

Agent 3 compression cannot alter selection, reorder bullets, or remove bullets.

## Observability plan

Create a `PipelineTrace` model and write debug traces only when enabled. The trace should include:

- Raw JD or a redacted/hash-only representation when production logging is disabled.
- Structured JD.
- Agent 2 ranking.
- Initial selected content.
- Trimmed selected content.
- Agent 3 output.
- Final page count.
- Model names.
- Token usage, if provider responses expose it.
- Latency per agent and compile/trim step.

Avoid adding raw JD/resume content to normal production logs.

## Tests to add

### Agent 1 tests

Use fake LLM responses to validate:

- Raw JD produces a valid structured JD.
- Required vs preferred requirements are distinguished.
- Technical vs soft requirements are separated.
- Missing/ambiguous title/company/seniority is handled without fabrication.
- Importance scores outside `[0, 100]` fail validation.

### Agent 2 tests

Use deterministic fake ranker JSON to validate:

- Correct section, subsection, and bullet ID references pass.
- Fabricated section/subsection/bullet IDs fail.
- Every rankable bullet must be accounted for.
- Duplicate bullet IDs fail.
- Section-level ranking exists for every section.
- Subsection-level ranking exists for every rankable subsection.
- Bullet-level score ranges are enforced.
- Leadership and project rankings are accepted as JD-dependent, not hard-coded.
- Unsupported JD requirements are preserved.

### Selector tests

Use fixtures to prove:

- Important experiences receive coverage.
- High-value bullets are selected.
- Redundant bullets are deprioritized.
- Section priority affects selection.
- Leadership can be included for leadership-heavy JDs.
- Leadership can be dropped for purely technical JDs.
- Projects can outrank leadership when appropriate.
- The same ranking always produces the same selected IDs.

### Trimming tests

Use fake compiler/page-counter functions to prove:

- A two-page initial resume becomes one page.
- The lowest-value removable bullet is removed first.
- Important experience coverage is preserved.
- Entire low-priority sections can be removed when appropriate.
- The same input produces the same trimmed IDs.

### Agent 3 tests

Use fake LLM responses to validate:

- Only selected bullets are rewritten.
- No new IDs are accepted.
- Missing selected IDs fail.
- Numbers remain unchanged.
- Technologies are not invented.
- Dates and employers are not changed.
- Output schema validates.

### Pipeline tests

Use fake agents and fake PDF compiler to validate the full V2 sequence without spending API credits:

1. Agent 1 called once with raw JD only.
2. Agent 2 called once with structured JD and compact full master resume.
3. Selector/trimmer run deterministically.
4. Agent 3 called only after trimming.
5. Compression calls are bounded.
6. Agent 2 is never rerun during trimming/compression.

## Documentation plan

Update README or add dedicated docs after implementation to cover:

- `RESUME_PIPELINE=v2` feature flag.
- V2 environment variables and model configuration.
- High-level architecture and agent responsibility boundaries.
- Debug trace settings and privacy cautions.
- How to run V2 tests.
- How the old V1 embedding flow remains available during migration.

## Migration and obsolete components

Do not delete V1 components in the first implementation. Once V2 is implemented, tested, and enabled by default, these components become obsolete for resume bullet retrieval/customization and can be safely removed after a separate cleanup:

- `backend/agents/embedder.py` for JD/resume bullet retrieval embeddings.
- The embedded `embedding` arrays in `backend/test_data/resume_data_embedded.json`.
- `backend/algorithms/matchmaker.py` for vector/cosine bullet ranking.
- `backend/algorithms/selector.py` for flat greedy V1 selection.
- `backend/agents/job_description_chunker.py`, `backend/agents/prompts/job_description_chunker.txt`, and `backend/agents/formats/job_description_chunker.json` for V1 verbatim chunking.
- `backend/agents/editor.py` and `backend/agents/prompts/editor.txt` once Agent 3 fully replaces V1 bullet editing.
- The LLM fabrication path in `backend/agents/validator.py` may be replaced or reduced once Agent 3 schema/fact preservation validators cover the same safety guarantees.
- Any future pgvector/Supabase retrieval code if it is added only for V1-style semantic retrieval.

## Explicit non-goals for this change

- Do not enable V2 by default; keep it behind the `RESUME_PIPELINE=v2` feature flag.
- Do not remove embeddings, matchmaker, selector, chunker, editor, or validator yet.
- Do not change the frontend API contract yet.
- Do not call external LLMs in tests.
- Do not let an LLM decide page fitting or content selection.
