import type { ResumeSection as ResumeSectionType } from '../types';
import { getSectionKind, getSectionTitle, getSubSections } from '../utils/resume';
import { EducationSection } from './EducationSection';
import { ExperienceSection } from './ExperienceSection';
import { ProjectsSection } from './ProjectsSection';
import { ResumeSubSection } from './ResumeSubSection';

interface ResumeSectionProps {
  section: ResumeSectionType;
}

export function ResumeSection({ section }: ResumeSectionProps) {
  const kind = getSectionKind(section);

  if (kind === 'experience') return <ExperienceSection section={section} />;
  if (kind === 'projects') return <ProjectsSection section={section} />;
  if (kind === 'education') return <EducationSection section={section} />;

  return (
    <section className="space-y-3 text-left">
      <h2 className="text-sm font-bold uppercase tracking-wide text-white/90">
        {getSectionTitle(section)}
      </h2>
      {getSubSections(section).map((subSection) => (
        <ResumeSubSection key={subSection.sub_section_id} subSection={subSection} />
      ))}
    </section>
  );
}
