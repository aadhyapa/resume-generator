import type { Resume } from '../types';
import { getRenderableSections } from '../utils/resume';
import { ResumeHeader } from './ResumeHeader';
import { ResumeSection } from './ResumeSection';
import { ResumeSkills } from './ResumeSkills';

interface ResumePreviewProps {
  resume: Resume;
}

export function ResumePreview({ resume }: ResumePreviewProps) {
  const sections = getRenderableSections(resume);

  return (
    <div className="space-y-4 text-left">
      <ResumeHeader header={resume.header} />
      <ResumeSkills skills={resume.skills} />
      {sections.length > 0 ? (
        sections.map((section) => <ResumeSection key={section.section_id} section={section} />)
      ) : (
        <p className="text-xs text-white/70 bg-black/20 rounded-xl border border-white/10 p-3">
          The backend returned a resume, but no renderable sections were found.
        </p>
      )}
    </div>
  );
}
