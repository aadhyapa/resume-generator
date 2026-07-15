import type {
  Resume,
  ResumeHeader,
  ResumeSection,
  ResumeSubSection,
} from "../types";
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

// CSS mirrors frontend/assets/Templates/resume1.html so the popup preview matches the exported resume template.
const RESUME_1_STYLES = `
  body {
    margin: 0;
    padding: 20px;
    min-height: 100vh;
    display: flex;
    justify-content: flex-start;
    flex-direction: column;
    align-items: center;
    background-color: #f6f6f3;
    font-family: 'Latin Modern Roman', Garamond, 'Times New Roman', Times, serif;
    box-sizing: border-box;
  }

  .page {
    width: 8.5in;
    height: 11in;
    max-width: 100%;
    padding: 0.5in;
    position: relative;
    overflow: visible;
    background: white;
    border: 1px solid #9ca3af;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);
    box-sizing: border-box;
  }

  .container {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 15px;
  }

  .page.overflowing {
    border-color: #ef4444;
    box-shadow: 0 8px 24px rgba(239, 68, 68, 0.24);
  }

  .page.overflowing::after {
    content: "PDF page 1 ends here — overflowing content will continue on page 2";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    border-top: 2px dashed #ef4444;
    color: #b91c1c;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 11px;
    font-weight: 700;
    line-height: 1;
    padding-top: 4px;
    text-align: center;
    transform: translateY(100%);
  }

  .header {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
  }

  .name {
    margin: 0 0 10px 0;
    font-variant-caps: small-caps;
    font-size: 3rem;
  }

  .contact {
    color: #4b5563;
    text-align: center;
    overflow-wrap: anywhere;
  }

  .contact a {
    color: inherit;
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .section {
    width: 100%;
  }

  .section-name {
    border-bottom: 1px solid #4b5563;
    font-weight: bold;
    font-variant-caps: small-caps;
    font-size: 1.5rem;
  }

  .sub-section {
    width: 100%;
    margin-top: 10px;
  }

  .sub-section-header {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    grid-template-rows: repeat(2, auto);
    justify-content: space-between;
  }

  .sub-section-name {
    grid-row-start: 1;
    grid-row-end: 2;
    grid-column-start: 1;
    grid-column-end: 2;
    font-weight: bold;
  }

  .sub-section-date {
    grid-row-start: 1;
    grid-row-end: 2;
    grid-column-start: 2;
    grid-column-end: 3;
    text-align: right;
    font-weight: bold;
  }

  .sub-section-role {
    grid-row-start: 2;
    grid-row-end: 3;
    grid-column-start: 1;
    grid-column-end: 2;
    font-style: italic;
  }

  .sub-section-location {
    grid-row-start: 2;
    grid-row-end: 3;
    grid-column-start: 2;
    grid-column-end: 3;
    font-style: italic;
    text-align: right;
  }

  .sub-section-description {
    margin-top: 0px;
    margin-left: 5px;
  }

  .sub-section-description ul {
    margin-top: 2px;
    margin-bottom: 0px;
    padding-left: 20px;
  }

  .skill-used {
    font-style: italic;
    font-weight: normal;
  }

  .skill-category {
    font-weight: bold;
  }

  @page {
    size: letter;
    margin: 0;
  }

  @media print {
    body {
      padding: 0;
      background: white;
    }

    .page {
      width: auto;
      height: auto;
      padding: 0.5in;
      overflow: visible;
      border: none;
      box-shadow: none;
    }

    .page.overflowing::after {
      content: none;
    }
  }
`;

export function renderResumeHtml(resume: Resume) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tailored Resume Preview</title>
  <style>${RESUME_1_STYLES}</style>
</head>
<body>
  <div class="page">
    <div class="container">
      ${renderHeader(resume.header)}
      ${renderEducationSections(resume)}
      ${renderSkills(resume.skills)}
      ${renderSections(resume)}
      ${renderLeadershipSections(resume)}
    </div>
  </div>
</body>
</html>`;
}

function renderHeader(header?: ResumeHeader) {
  if (!header) return "";

  const nameKey = PRIMARY_NAME_KEYS.find(
    (key) => typeof header[key] === "string",
  );
  const name = nameKey ? escapeHtml(header[nameKey]) : "";
  const contact = dedupeContactItems(
    getHeaderContactEntries(header, nameKey)
      .map(([key, value]) => renderContactItem(key, value))
      .filter(Boolean),
  ).join(" | ");

  return `
    <div class="section header">
      ${name ? `<h1 class="name">${name}</h1>` : ""}
      ${contact ? `<div class="contact">${contact}</div>` : ""}
    </div>`;
}

function getHeaderContactEntries(
  header: Record<string, unknown>,
  excludedKey?: string,
): [string, unknown][] {
  return Object.entries(header).flatMap(([key, value]) => {
    if (key === excludedKey) return [];
    if (isRecord(value)) return getHeaderContactEntries(value, undefined);
    if (Array.isArray(value))
      return value.map((item) => [key, item] as [string, unknown]);
    if (typeof value === "string" && value.includes("|")) {
      return value
        .split("|")
        .map((item) => item.trim())
        .filter(Boolean)
        .map((item) => [key, item] as [string, unknown]);
    }
    return [[key, value] as [string, unknown]];
  });
}

function dedupeContactItems(items: string[]) {
  return Array.from(new Set(items));
}

function renderEducationSections(resume: Resume) {
  return getRenderableSections(resume)
    .filter(isEducationSection)
    .map(renderSection)
    .join("");
}

function renderSections(resume: Resume) {
  return getRenderableSections(resume)
    .filter(
      (section) =>
        !isEducationSection(section) &&
        !isSkillsSection(section) &&
        !isLeadershipSection(section),
    )
    .sort(compareResumeSections)
    .map(renderSection)
    .join("");
}

function renderLeadershipSections(resume: Resume) {
  return getRenderableSections(resume)
    .filter(isLeadershipSection)
    .map(renderSection)
    .join("");
}

function renderSection(section: ResumeSection) {
  const subSections = getSubSections(section).map(renderSubSection).join("");
  return `
    <div class="section">
      <div class="section-name">${escapeHtml(getSectionTitle(section))}</div>
      ${subSections}
    </div>`;
}

function getSectionId(section: { section_id: string }) {
  return section.section_id.toLowerCase();
}

function isEducationSection(section: { section_id: string }) {
  return getSectionId(section).includes("education");
}

function isSkillsSection(section: { section_id: string }) {
  return (
    getSectionId(section) === "sec_skills" ||
    getSectionId(section).includes("skill")
  );
}

function isLeadershipSection(section: { section_id: string }) {
  return getSectionId(section).includes("leadership");
}

function compareResumeSections(
  left: { section_id: string },
  right: { section_id: string },
) {
  return getSectionSortOrder(left) - getSectionSortOrder(right);
}

function getSectionSortOrder(section: { section_id: string }) {
  const sectionId = getSectionId(section);
  if (sectionId.includes("education")) return 10;
  if (sectionId.includes("experience")) return 20;
  if (sectionId.includes("project")) return 30;
  if (sectionId.includes("leadership")) return 90;
  return 40;
}

function renderSubSection(subSection: ResumeSubSection) {
  const metadata = getSubSectionMetadata(subSection);
  const title = getSubSectionTitle(subSection, metadata);
  const role = getSubSectionRole(metadata);
  const bullets = subSection.bullets ?? [];

  return `
      <div class="sub-section">
        <div class="sub-section-header">
          <div class="sub-section-name">${title}</div>
          <div class="sub-section-date">${escapeHtml(metadata.date || metadata.dates || "")}</div>
          <div class="sub-section-role">${escapeHtml(role)}</div>
          <div class="sub-section-location">${escapeHtml(metadata.location || "")}</div>
        </div>
        ${
          bullets.length > 0
            ? `
        <div class="sub-section-description">
          <ul>
            ${bullets.map((bullet) => `<li>${renderBulletText(bullet.text, bullet.bold_words)}</li>`).join("\n            ")}
          </ul>
        </div>`
            : ""
        }
      </div>`;
}

function getSubSectionTitle(
  subSection: ResumeSubSection,
  metadata: Record<string, string>,
) {
  const title =
    metadata.name ||
    metadata.title ||
    metadata.school ||
    metadata.company ||
    metadata.organization ||
    metadata.employer ||
    metadata.project ||
    prettifyIdentifier(subSection.sub_section_id);

  if (metadata.tools && (metadata.name || metadata.project)) {
    return `${escapeHtml(title)} | <span class="skill-used">${escapeHtml(metadata.tools)}</span>`;
  }

  return escapeHtml(title);
}

function getSubSectionRole(metadata: Record<string, string>) {
  return (
    metadata.company ||
    metadata.employer ||
    metadata.role ||
    metadata.degree ||
    metadata.position ||
    metadata.major ||
    ""
  );
}

function renderContactItem(key: string, value: unknown) {
  const formatted = formatUnknownValue(value);
  if (!formatted) return "";

  const normalizedKey = key.toLowerCase();
  const escapedValue = escapeHtml(formatted);

  if (normalizedKey.includes("email") || formatted.includes("@")) {
    return `<a href="mailto:${escapeHtml(formatted)}">${escapedValue}</a>`;
  }

  if (isLinkedInContact(normalizedKey, formatted)) {
    return `<a href="${escapeHtml(formatExternalUrl(formatted))}">LinkedIn</a>`;
  }

  if (isGitHubContact(normalizedKey, formatted)) {
    return `<a href="${escapeHtml(formatExternalUrl(formatted))}">GitHub</a>`;
  }

  if (/^https?:\/\//i.test(formatted) || formatted.includes(".")) {
    return `<a href="${escapeHtml(formatExternalUrl(formatted))}">${escapedValue}</a>`;
  }

  return escapedValue;
}

function isLinkedInContact(key: string, value: string) {
  const normalizedValue = value.toLowerCase();
  return key.includes("linkedin") || normalizedValue.includes("linkedin.com");
}

function isGitHubContact(key: string, value: string) {
  const normalizedValue = value.toLowerCase();
  return key.includes("github") || normalizedValue.includes("github.com");
}

function formatExternalUrl(value: string) {
  const trimmedValue = value.trim();
  const url = /^https?:\/\//i.test(trimmedValue)
    ? trimmedValue
    : `https://${trimmedValue}`;
  return url.replace(/\/+$/, "");
}

function renderSkills(skills: Resume["skills"]) {
  if (!skills) return "";

  if (typeof skills === "string" || Array.isArray(skills)) {
    const value = Array.isArray(skills) ? skills.join(", ") : skills;
    return renderSkillSection([["Skills", value]]);
  }

  if (!isRecord(skills)) return "";

  const groups = Object.entries(skills)
    .filter(([key]) => key.toLowerCase() !== "section_id")
    .map(
      ([key, value]) =>
        [prettifyIdentifier(key), formatUnknownValue(value)] as const,
    )
    .filter(([, value]) => value);

  return renderSkillSection(groups);
}

function renderSkillSection(
  groups: readonly (readonly [string, string | null])[],
) {
  if (groups.length === 0) return "";

  return `
    <div class="section">
      <div class="section-name">Technical Skills</div>
      <div class="sub-section">
        ${groups
          .map(
            ([category, value]) => `
        <span class="skill-category sub-section-description">${escapeHtml(category)}:</span>
        <span class="skill-item sub-section-description">${escapeHtml(value ?? "")}</span>
        <br />`,
          )
          .join("")}
      </div>
    </div>`;
}

function getSubSectionMetadata(subSection: ResumeSubSection) {
  return Object.entries(subSection).reduce<Record<string, string>>(
    (metadata, [key, value]) => {
      if (SUB_SECTION_RESERVED_KEYS.has(key)) return metadata;
      const formatted = formatUnknownValue(value);
      if (formatted) metadata[key.toLowerCase()] = formatted;
      return metadata;
    },
    {},
  );
}

function renderBulletText(text: string, boldWords?: string[]) {
  const escapedText = escapeHtml(text);
  if (!boldWords || boldWords.length === 0) return escapedText;

  return boldWords.reduce((result, word) => {
    const escapedWord = escapeRegExp(escapeHtml(word));
    if (!escapedWord) return result;
    return result.replace(new RegExp(`(${escapedWord})`, "gi"), "<b>$1</b>");
  }, escapedText);
}

function escapeHtml(value: unknown) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
