import type { Resume, ResumeSection, ResumeSubSection } from "../types";
import {
  formatUnknownValue,
  getRenderableSections,
  getSectionTitle,
  getSubSections,
  isRecord,
  prettifyIdentifier,
} from "./resume";

const PRIMARY_NAME_KEYS = ["name", "full_name", "fullName"];
const SUB_SECTION_RESERVED_KEYS = new Set([
  "sub_section_id",
  "section_id",
  "bullets",
]);

const LATEX_SPECIAL_CHARS: Record<string, string> = {
  "\\": String.raw`\textbackslash{}`,
  "&": String.raw`\&`,
  "%": String.raw`\%`,
  "$": String.raw`\$`,
  "#": String.raw`\#`,
  "_": String.raw`\_`,
  "{": String.raw`\{`,
  "}": String.raw`\}`,
  "~": String.raw`\textasciitilde{}`,
  "^": String.raw`\textasciicircum{}`,
};

const PREAMBLE = String.raw`%-------------------------
% Resume in Latex
% Based off of: https://github.com/sb2nov/resume
% License : MIT
%------------------------

\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage[english]{babel}
\usepackage{tabularx}
\usepackage{fontawesome5}
\usepackage{multicol}
\setlength{\multicolsep}{-3.0pt}
\setlength{\columnsep}{-1pt}
\input{glyphtounicode}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.6in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1.19in}
\addtolength{\topmargin}{-.7in}
\addtolength{\textheight}{1.4in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
\vspace{-4pt}\scshape\raggedright\large\bfseries
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

\pdfgentounicode=1

\newcommand{\resumeItem}[1]{
\item\small{
{#1 \vspace{-2pt}}
}
}

\newcommand{\resumeSubheading}[4]{
\vspace{-2pt}\item
\begin{tabular*}{1.0\textwidth}[t]{l@{\extracolsep{\fill}}r}
\textbf{#1} & \textbf{\small #2} \\
\textit{\small#3} & \textit{\small #4} \\
\end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeProjectHeading}[2]{
\item
\begin{tabular*}{1.001\textwidth}{l@{\extracolsep{\fill}}r}
\small#1 & \textbf{\small #2}\\
\end{tabular*}\vspace{-7pt}
}

\renewcommand\labelitemi{$\vcenter{\hbox{\tiny$\bullet$}}$}
\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.0in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

%-------------------------------------------
%%%%%%  RESUME STARTS HERE  %%%%%%%%%%%%%%%%%%%%%%%%%%%%
`;

export function renderResumeLatex(resume: Resume): string {
  const parts = [PREAMBLE, "\\begin{document}\n", renderHeader(resume.header)];
  parts.push(...getRenderableSections(resume).filter((section) => !isSkillsSection(section)).map(renderSection));
  parts.push(renderSkills(resume.skills));
  parts.push("\\end{document}\n");
  return parts.filter(Boolean).join("\n");
}

function renderHeader(header: unknown): string {
  if (!isRecord(header)) return "";
  const nameKey = PRIMARY_NAME_KEYS.find((key) => typeof header[key] === "string");
  const name = nameKey ? escapeLatex(header[nameKey]) : "";
  const contacts = dedupe(getHeaderContactEntries(header, nameKey).map(([key, value]) => renderContactItem(key, value))).filter(Boolean);
  return [
    "%----------HEADING----------",
    String.raw`\begin{center}`,
    name ? `{\\Huge \\scshape ${name}} \\ \\vspace{1pt}` : "",
    contacts.length ? `\\small ${contacts.join(String.raw` \textasciitilde{} `)}` : "",
    String.raw`\vspace{-8pt}`,
    String.raw`\end{center}`,
    "",
  ].join("\n");
}

function getHeaderContactEntries(header: Record<string, unknown>, excludedKey?: string): [string, unknown][] {
  return Object.entries(header).flatMap(([key, value]) => {
    if (key === excludedKey) return [];
    if (isRecord(value)) return [[key, value.label ?? value.url] as [string, unknown]];
    if (Array.isArray(value)) return value.map((item) => [key, item] as [string, unknown]);
    if (typeof value === "string" && value.includes("|")) return value.split("|").map((item) => [key, item.trim()] as [string, unknown]).filter(([, item]) => Boolean(item));
    return [[key, value] as [string, unknown]];
  });
}

function renderContactItem(key: string, value: unknown): string {
  const formatted = formatUnknownValue(value);
  if (!formatted) return "";
  const escaped = escapeLatex(formatted);
  const normalizedKey = key.toLowerCase();
  if (normalizedKey.includes("email") || formatted.includes("@")) return String.raw`\href{mailto:${escapeLatex(formatted)}}{\raisebox{-0.2\height}\faEnvelope\  \underline{${escaped}}}`;
  if (normalizedKey.includes("phone") || normalizedKey.includes("mobile")) return String.raw`\raisebox{-0.1\height}\faPhone\ ${escaped}`;
  if (normalizedKey.includes("linkedin") || formatted.toLowerCase().includes("linkedin.com")) return String.raw`\href{${escapeLatex(formatExternalUrl(formatted))}}{\raisebox{-0.2\height}\faLinkedin\ \underline{${escaped}}}`;
  if (normalizedKey.includes("github") || formatted.toLowerCase().includes("github.com")) return String.raw`\href{${escapeLatex(formatExternalUrl(formatted))}}{\raisebox{-0.2\height}\faGithub\ \underline{${escaped}}}`;
  if (/^https?:\/\//i.test(formatted) || formatted.includes(".")) return String.raw`\href{${escapeLatex(formatExternalUrl(formatted))}}{\underline{${escaped}}}`;
  return escaped;
}

function renderSection(section: ResumeSection): string {
  const title = escapeLatex(getSectionTitle(section));
  const subsections = getSubSections(section).map((subsection) => renderSubsection(section, subsection)).filter(Boolean).join("\n");
  if (!subsections) return "";
  return `%-----------${title.toUpperCase()}-----------\n\\section{${title}}\n\\resumeSubHeadingListStart\n${subsections}\n\\resumeSubHeadingListEnd\n`;
}

function renderSubsection(section: ResumeSection, subsection: ResumeSubSection): string {
  const metadata = getSubsectionMetadata(subsection);
  const bulletBlock = renderBullets(Array.isArray(subsection.bullets) ? subsection.bullets : []);
  if (isProjectSection(section)) {
    const tools = metadata.tools || metadata.technologies || "";
    let heading = String.raw`\textbf{${escapeLatex(getSubsectionTitle(subsection, metadata))}}`;
    if (tools) heading += String.raw` $|$ \emph{${escapeLatex(tools)}}`;
    return `\\resumeProjectHeading\n{${heading}}{}\n${bulletBlock}`;
  }
  return `\\resumeSubheading\n{${escapeLatex(getSubsectionTitle(subsection, metadata))}}{${escapeLatex(metadata.date || metadata.dates || "")}}\n{${escapeLatex(getSubsectionRole(metadata))}}{${escapeLatex(metadata.location || "")}}\n${bulletBlock}`;
}

function renderBullets(bullets: unknown[]): string {
  const rendered = bullets.flatMap((bullet) => isRecord(bullet) && bullet.text ? [String.raw`\resumeItem{${renderBulletText(String(bullet.text), bullet.bold_words)}}`] : []);
  return rendered.length ? `\\resumeItemListStart\n${rendered.join("\n")}\n\\resumeItemListEnd` : "";
}

function renderSkills(skills: Resume["skills"]): string {
  if (!skills) return "";
  const groups = typeof skills === "string" ? [["Skills", skills]] : Array.isArray(skills) ? [["Skills", skills.map(String).join(", ")]] : Object.entries(skills).filter(([key]) => key.toLowerCase() !== "section_id").map(([key, value]) => [prettifyIdentifier(key), formatUnknownValue(value) || ""]);
  const lines = groups.flatMap(([category, value]) => value ? [String.raw`\textbf{${escapeLatex(category)}}{: ${escapeLatex(value)}} \\`] : []);
  return lines.length ? `%-----------PROGRAMMING SKILLS-----------\n\\section{Technical Skills}\n\\begin{itemize}[leftmargin=0.15in, label={}]\n\\small{\\item{\n${lines.join("\n")}\n}}\n\\end{itemize}\n\\vspace{-16pt}\n` : "";
}

function renderBulletText(text: string, boldWords: unknown): string {
  const protectedBold: string[] = [];
  const escaped = escapeLatex(text.replace(/<b>(.*?)<\/b>/gi, (_match, content) => {
    protectedBold.push(String.raw`\textbf{${escapeLatex(content)}}`);
    return `@@BOLD${protectedBold.length - 1}@@`;
  }));
  let output = escaped;
  const words = Array.isArray(boldWords) ? boldWords : [];
  words.forEach((word) => {
    if (!word) return;
    const escapedWord = escapeLatex(String(word));
    output = output.replace(new RegExp(escapeRegExp(escapedWord), "gi"), String.raw`\textbf{${escapedWord}}`);
  });
  protectedBold.forEach((value, index) => {
    output = output.replace(escapeLatex(`@@BOLD${index}@@`), value);
  });
  return output;
}

function getSubsectionMetadata(subsection: ResumeSubSection): Record<string, string> {
  return Object.fromEntries(Object.entries(subsection).flatMap(([key, value]) => {
    if (SUB_SECTION_RESERVED_KEYS.has(key)) return [];
    const formatted = formatUnknownValue(value);
    return formatted ? [[key.toLowerCase(), formatted]] : [];
  }));
}

function getSubsectionTitle(subsection: ResumeSubSection, metadata: Record<string, string>): string {
  return metadata.name || metadata.title || metadata.school || metadata.company || metadata.organization || metadata.employer || metadata.project || prettifyIdentifier(String(subsection.sub_section_id || ""));
}

function getSubsectionRole(metadata: Record<string, string>): string {
  return metadata.company || metadata.employer || metadata.role || metadata.degree || metadata.position || metadata.major || "";
}

function isProjectSection(section: ResumeSection): boolean {
  const label = `${section.section_id} ${section.title || ""} ${section.name || ""}`.toLowerCase();
  return label.includes("project");
}

function isSkillsSection(section: ResumeSection): boolean {
  const sectionId = section.section_id.toLowerCase();
  return sectionId === "sec_skills" || sectionId.includes("skill");
}

function escapeLatex(value: unknown): string {
  return String(value).replace(/[\\&%$#_{}~^]/g, (char) => LATEX_SPECIAL_CHARS[char]);
}

function formatExternalUrl(value: string): string {
  const trimmed = value.trim().replace(/\/$/, "");
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

function dedupe(items: string[]): string[] {
  return Array.from(new Set(items.filter(Boolean)));
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
