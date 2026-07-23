import type { ReactNode } from 'react';

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function highlightText(text: string, boldWords?: string[]): ReactNode {
  const cleanText = text.replace(/<\/?[bB]>/g, '');
  const normalizedWords = (boldWords ?? [])
    .map((word) => word.trim())
    .filter(Boolean);
  const escapedWords = normalizedWords.map(escapeRegExp);

  if (escapedWords.length === 0) {
    return cleanText;
  }

  const pattern = new RegExp(`\\b(${escapedWords.join('|')})\\b`, 'gi');
  const highlightedWords = new Set(normalizedWords.map((word) => word.toLowerCase()));

  return cleanText.split(pattern).map((part, index) => {
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
