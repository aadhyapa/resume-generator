import type { ResumeSection } from '../types';
import { getSectionTitle, getSubSections } from '../utils/resume';
import { ResumeSubSection } from './ResumeSubSection';

interface EducationSectionProps {
  section: ResumeSection;
}

export function EducationSection({ section }: EducationSectionProps) {
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
