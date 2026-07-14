import type { ResumeHeader } from '../types';
import { formatUnknownValue, prettifyIdentifier } from '../utils/resume';

interface ResumeHeaderProps {
  header?: ResumeHeader;
}

const PRIMARY_NAME_KEYS = ['name', 'full_name', 'fullName'];

export function ResumeHeader({ header }: ResumeHeaderProps) {
  if (!header) return null;

  const nameEntry = PRIMARY_NAME_KEYS.find((key) => typeof header[key] === 'string');
  const name = nameEntry ? String(header[nameEntry]) : null;
  const details = Object.entries(header)
    .filter(([key]) => key !== nameEntry)
    .map(([key, value]) => [key, formatUnknownValue(value)] as const)
    .filter(([, value]) => value);

  return (
    <section className="bg-white/10 rounded-xl border border-white/10 p-3 text-left">
      {name && <h2 className="text-lg font-bold text-white">{name}</h2>}
      {details.length > 0 && (
        <dl className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-white/80">
          {details.map(([key, value]) => (
            <div key={key} className="flex gap-1">
              <dt className="font-semibold">{prettifyIdentifier(key)}:</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}
