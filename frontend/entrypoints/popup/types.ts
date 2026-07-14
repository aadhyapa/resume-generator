import type { ReactNode } from 'react';

export type GenerationStatus = 'idle' | 'scraping' | 'scraped' | 'generating' | 'success' | 'error';

export interface GenerateResumeResponse {
  message: string;
  resume: Resume;
}

export type ResumePrimitive = string | number | boolean | null | undefined;
export type ResumeFieldValue = ResumePrimitive | ResumePrimitive[] | Record<string, unknown>;

export interface ResumeHeader {
  [key: string]: ResumeFieldValue;
}

export interface ResumeSkills {
  [key: string]: ResumeFieldValue;
}

export interface ResumeBullet {
  bullet_id: string;
  sub_section_id: string;
  text: string;
  bold_words?: string[];
  edited?: boolean;
  [key: string]: unknown;
}

export interface ResumeSubSection {
  sub_section_id: string;
  section_id: string;
  bullets?: ResumeBullet[];
  [key: string]: unknown;
}

export interface ResumeSection {
  section_id: string;
  title?: string;
  name?: string;
  sub_sections: Record<string, ResumeSubSection>;
  [key: string]: unknown;
}

export interface Resume {
  header?: ResumeHeader;
  skills?: ResumeSkills | string[] | string;
  sections?: Record<string, unknown>;
  [sectionId: string]: unknown;
}

export interface GenerationState {
  jobDescription?: string;
  status?: GenerationStatus;
  resumeData?: Resume | null;
  errorMsg?: string;
}

export type HighlightedText = string | ReactNode[];
