import type { ReactNode } from 'react';

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function highlightText(text: string, boldWords?: string[]): ReactNode {
  const normalizedWords = (boldWords ?? [])
    .map((word) => word.trim())
    .filter(Boolean);
  const escapedWords = normalizedWords.map(escapeRegExp);

  if (escapedWords.length === 0) {
    return text;
  }

  const pattern = new RegExp(`\\b(${escapedWords.join('|')})\\b`, 'gi');
  const highlightedWords = new Set(normalizedWords.map((word) => word.toLowerCase()));

  return text.split(pattern).map((part, index) => {
    if (highlightedWords.has(part.toLowerCase())) {
      return (
        <strong key={`${part}-${index}`} className="text-yellow-200 font-bold">
          {part}
        </strong>
      );
    }

    return part;
  });
}
