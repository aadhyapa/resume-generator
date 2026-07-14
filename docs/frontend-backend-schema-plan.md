# Frontend Alignment Plan for Backend Resume Response Schema

## Backend response contract observed

The `/generate_resume` endpoint returns an envelope with this shape:

```ts
type GenerateResumeResponse = {
  message: string;
  resume: Resume;
};
```

The `resume` payload is assembled by `backend/algorithms/formatter.py` and currently has this effective shape:

```ts
type Resume = {
  header: ResumeHeader;
  skills: ResumeSkills;
  sections: {}; // initialized but not populated by the formatter today
  [sectionId: string]: ResumeSection | ResumeHeader | ResumeSkills | {};
};

type ResumeSection = {
  section_id: string;
  title?: string;
  name?: string;
  sub_sections: Record<string, ResumeSubSection>;
  [key: string]: unknown;
};

type ResumeSubSection = {
  sub_section_id: string;
  section_id: string;
  bullets: ResumeBullet[];
  [key: string]: unknown;
};

type ResumeBullet = {
  bullet_id: string;
  sub_section_id: string;
  text: string;
  bold_words?: string[];
  edited?: boolean;
  [key: string]: unknown;
};
```

Important frontend implications:

- The popup currently treats `data.resume` as either `Record<string, Bullet[]>` or `Bullet[]`, but the backend now returns a full resume object containing `header`, `skills`, and section objects keyed by `section_id`.
- Bullets are grouped under `resume[sectionId].sub_sections[subSectionId].bullets`, not directly under top-level experience IDs.
- The formatter initializes `resume.sections` as an empty object while also placing actual sections at dynamic top-level keys, so the frontend should skip reserved top-level keys (`header`, `skills`, `sections`) when rendering dynamic sections.
- Education, projects, experience, and similar resume areas should be rendered from the same section/sub-section shape instead of bespoke top-level arrays.

## Proposed frontend file organization

Mirror the existing separation intent for projects and experience by moving each resume display concern into focused files under `frontend/entrypoints/popup/`:

```txt
frontend/entrypoints/popup/
  App.tsx
  types.ts
  utils/
    resume.ts
    highlightText.tsx
  components/
    ResumePreview.tsx
    ResumeHeader.tsx
    ResumeSkills.tsx
    ResumeSection.tsx
    ResumeSubSection.tsx
    ExperienceSection.tsx
    ProjectsSection.tsx
    EducationSection.tsx
```

Responsibilities:

1. `types.ts`
   - Define `GenerateResumeResponse`, `Resume`, `ResumeHeader`, `ResumeSkills`, `ResumeSection`, `ResumeSubSection`, and `ResumeBullet` based on the backend formatter output.
   - Keep index signatures for backend fields that are not fully standardized yet.

2. `utils/resume.ts`
   - Add `RESERVED_RESUME_KEYS = new Set(['header', 'skills', 'sections'])`.
   - Add `getRenderableSections(resume)` to return only dynamic section objects that have `section_id` and `sub_sections`.
   - Add `getSectionKind(section)` to map section titles/IDs to `experience`, `projects`, `education`, or `generic`.
   - Add normalization helpers so components do not need to know about backend quirks like the empty `sections` object.

3. `utils/highlightText.tsx`
   - Move `highlightText` out of `App.tsx`.
   - Implement the existing TODO with safe regex escaping and case-insensitive matching for `bold_words`.

4. `components/ResumePreview.tsx`
   - Accept a `Resume` and orchestrate rendering of header, skills, and dynamic sections.
   - Use `getRenderableSections` and delegate each section to a section-specific component.

5. `components/ResumeHeader.tsx`
   - Render the backend `header` object defensively.
   - Support likely fields such as name, email, phone, location, links, and unknown string fields.

6. `components/ResumeSkills.tsx`
   - Render `skills` as grouped categories when the backend sends an object.
   - Support arrays and string fallback values for early schema flexibility.

7. `components/ResumeSection.tsx`
   - Generic dispatcher that chooses `ExperienceSection`, `ProjectsSection`, `EducationSection`, or a fallback `ResumeSubSection` layout.

8. `components/ExperienceSection.tsx`, `ProjectsSection.tsx`, `EducationSection.tsx`
   - Keep each major resume area in its own file, matching the requested structure.
   - Share `ResumeSubSection` for common bullet-list rendering unless custom metadata layout is needed.

9. `components/ResumeSubSection.tsx`
   - Render sub-section metadata and bullets.
   - Use `bullet.sub_section_id` instead of `experience_id`, because the backend response bullets are keyed by `sub_section_id` after formatting.

## Implementation steps

1. Add frontend schema types in `types.ts` and replace the current `ResumeResponse = Record<string, Bullet[]> | Bullet[]` type.
2. Update `frontend/entrypoints/background.ts` to parse the full `GenerateResumeResponse` envelope and store `data.resume`, with optional shape checks before writing success state.
3. Update popup state in `App.tsx` so `resumeData` is typed as `Resume | null`.
4. Remove the inline `renderBullets` and `highlightText` functions from `App.tsx`.
5. Add `ResumePreview` and section components, then render `<ResumePreview resume={resumeData} />` in the success panel.
6. Ensure section rendering skips the backend's reserved `header`, `skills`, and empty `sections` keys.
7. Add specific files for education, skills, header, projects, and experience so the popup code no longer grows as one large component.
8. Build and type-check the frontend.
9. If the backend schema is stabilized later, replace the defensive index signatures with stricter generated/shared API types.

## Risks and follow-ups

- The backend does not currently expose explicit Pydantic response models, so TypeScript types must reflect observed formatter behavior until the backend contract is formalized.
- The formatter's top-level dynamic section keys plus empty `sections` object are awkward for clients; a future backend cleanup should return `sections: ResumeSection[]` or `sections: Record<string, ResumeSection>` consistently.
- Existing frontend storage may contain older `Bullet[]` or `Record<string, Bullet[]>` data. Add a one-time guard or clear stale state on schema mismatch to avoid rendering crashes after deployment.
