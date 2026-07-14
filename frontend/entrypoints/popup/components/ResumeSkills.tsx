import type { Resume } from '../types';
import { formatUnknownValue, isRecord, prettifyIdentifier } from '../utils/resume';

interface ResumeSkillsProps {
  skills?: Resume['skills'];
}

export function ResumeSkills({ skills }: ResumeSkillsProps) {
  if (!skills) return null;

  if (Array.isArray(skills)) {
    return <SkillCard title="Skills" value={skills.join(' • ')} />;
  }

  if (typeof skills === 'string') {
    return <SkillCard title="Skills" value={skills} />;
  }

  if (!isRecord(skills)) return null;

  const groups = Object.entries(skills)
    .map(([key, value]) => [key, formatUnknownValue(value)] as const)
    .filter(([, value]) => value);

  if (groups.length === 0) return null;

  return (
    <section className="bg-white/10 rounded-xl border border-white/10 p-3 text-left space-y-2">
      <h2 className="text-sm font-bold uppercase tracking-wide text-white/90">Skills</h2>
      <div className="space-y-1.5">
        {groups.map(([key, value]) => (
          <SkillCard key={key} title={prettifyIdentifier(key)} value={value ?? ''} compact />
        ))}
      </div>
    </section>
  );
}

function SkillCard({ title, value, compact = false }: { title: string; value: string; compact?: boolean }) {
  return (
    <div className={compact ? 'text-xs text-white/85' : 'bg-white/10 rounded-xl border border-white/10 p-3 text-left text-xs text-white/85'}>
      <span className="font-semibold text-pink-200">{title}: </span>
      <span>{value}</span>
    </div>
  );
}
