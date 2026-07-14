import type { ResumeSubSection } from '../types';
import { formatUnknownValue, prettifyIdentifier } from '../utils/resume';
import { highlightText } from '../utils/highlightText';

const SUB_SECTION_RESERVED_KEYS = new Set(['sub_section_id', 'section_id', 'bullets']);

interface ResumeSubSectionProps {
  subSection: ResumeSubSection;
}

export function ResumeSubSection({ subSection }: ResumeSubSectionProps) {
  const title = getSubSectionTitle(subSection);
  const metadata = Object.entries(subSection)
    .filter(([key]) => !SUB_SECTION_RESERVED_KEYS.has(key))
    .map(([key, value]) => [key, formatUnknownValue(value)] as const)
    .filter(([, value]) => value);

  return (
    <article className="bg-black/25 p-4 rounded-xl border border-white/10 backdrop-blur-md">
      <div className="mb-2 border-b border-pink-500/20 pb-2">
        <h3 className="text-pink-300 font-semibold text-xs uppercase tracking-wider">
          {title}
        </h3>
        {metadata.length > 0 && (
          <dl className="mt-1 space-y-0.5 text-[11px] text-white/70">
            {metadata.map(([key, value]) => (
              <div key={key} className="flex gap-1">
                <dt className="font-semibold text-white/80">{prettifyIdentifier(key)}:</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      {subSection.bullets && subSection.bullets.length > 0 ? (
        <ul className="space-y-2">
          {subSection.bullets.map((bullet) => (
            <li
              key={bullet.bullet_id}
              className="text-xs text-white/95 leading-relaxed relative pl-3 before:content-['•'] before:absolute before:left-0 before:text-pink-400"
            >
              {highlightText(bullet.text, bullet.bold_words)}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-white/60">No tailored bullets returned for this entry.</p>
      )}
    </article>
  );
}

function getSubSectionTitle(subSection: ResumeSubSection) {
  const explicitTitle = formatUnknownValue(subSection.title) || formatUnknownValue(subSection.name);
  return explicitTitle || prettifyIdentifier(subSection.sub_section_id);
}
