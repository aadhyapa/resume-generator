import { useState } from 'react';
import type { ResumeSubSection } from '../types';
import { formatUnknownValue, prettifyIdentifier } from '../utils/resume';
import { highlightText } from '../utils/highlightText';

const SUB_SECTION_RESERVED_KEYS = new Set(['sub_section_id', 'section_id', 'bullets']);

interface ResumeSubSectionProps {
  subSection: ResumeSubSection;
}

export function ResumeSubSection({ subSection }: ResumeSubSectionProps) {
  const [copied, setCopied] = useState(false);
  const title = getSubSectionTitle(subSection);
  const metadata = Object.entries(subSection)
    .filter(([key]) => !SUB_SECTION_RESERVED_KEYS.has(key))
    .map(([key, value]) => [key, formatUnknownValue(value)] as const)
    .filter(([, value]) => value);

  const handleCopy = () => {
    const textParts = (subSection.bullets || []).map((bullet) => `• ${bullet.text}`);
    const textToCopy = textParts.join('\n');
    navigator.clipboard.writeText(textToCopy).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <article className="bg-black/25 p-4 rounded-xl border border-white/10 backdrop-blur-md">
      <div className="mb-2 border-b border-pink-500/20 pb-2 flex justify-between items-start">
        <div>
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
        <button
          onClick={handleCopy}
          className="text-[10px] px-2 py-0.5 ml-2 hover:opacity-80 transition-opacity duration-200 flex items-center gap-1 font-semibold text-white/95 shrink-0"
          title="Copy experience to clipboard"
        >
          {copied ? (
            <>
              <svg className="w-3 h-3 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Copied
            </>
          ) : (
            <>
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
              Copy
            </>
          )}
        </button>
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
