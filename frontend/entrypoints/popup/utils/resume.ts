import type { Resume, ResumeSection } from '../types';

export const RESERVED_RESUME_KEYS = new Set(['header', 'skills', 'sections']);

export type SectionKind = 'experience' | 'projects' | 'education' | 'generic';

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isResume(value: unknown): value is Resume {
  return isRecord(value);
}

export function isResumeSection(value: unknown): value is ResumeSection {
  return (
    isRecord(value) &&
    typeof value.section_id === 'string' &&
    isRecord(value.sub_sections)
  );
}

export function getRenderableSections(resume: Resume): ResumeSection[] {
  return Object.entries(resume)
    .filter(([key]) => !RESERVED_RESUME_KEYS.has(key))
    .map(([, value]) => value)
    .filter(isResumeSection);
}

export function getSectionTitle(section: ResumeSection) {
  return section.title || section.name || prettifyIdentifier(section.section_id);
}

export function getSectionKind(section: ResumeSection): SectionKind {
  const label = `${section.section_id} ${section.title ?? ''} ${section.name ?? ''}`.toLowerCase();

  if (label.includes('project')) return 'projects';
  if (label.includes('education') || label.includes('school') || label.includes('degree')) return 'education';
  if (label.includes('experience') || label.includes('work') || label.includes('employment')) return 'experience';

  return 'generic';
}

export function getSubSections(section: ResumeSection) {
  return Object.values(section.sub_sections ?? {});
}

export function prettifyIdentifier(identifier: string) {
  return identifier
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function formatUnknownValue(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    return value.map(formatUnknownValue).filter(Boolean).join(' • ');
  }
  return null;
}
