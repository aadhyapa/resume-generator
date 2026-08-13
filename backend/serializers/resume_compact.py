from typing import Any
from models.resume import MasterResume, ResumeSubSection
from models.selection import SelectedResumeContent

_METADATA_KEYS = ("name", "title", "school", "company", "employer", "organization", "role", "position", "degree", "dates", "date", "location", "tools", "technologies")


def _section_title(section: Any) -> str:
    return (getattr(section, "name", None) or getattr(section, "title", None) or section.section_id).upper()


def _metadata_line(subsection: ResumeSubSection) -> str:
    data = subsection.model_dump(exclude={"sub_section_id", "section_id"}, exclude_none=True)
    values = []
    for key in _METADATA_KEYS:
        value = data.get(key)
        if value:
            values.append(str(value))
    return " | ".join(values)


def serialize_master_resume_for_ranking(master_resume: MasterResume) -> str:
    bullets_by_subsection: dict[str, list] = {}
    for bullet in master_resume.bullets:
        bullets_by_subsection.setdefault(bullet.sub_section_id, []).append(bullet)
    lines: list[str] = []
    for section in master_resume.sections:
        lines.append(f"{_section_title(section)} [{section.section_id}]")
        for subsection in master_resume.sub_sections:
            if subsection.section_id != section.section_id:
                continue
            metadata = _metadata_line(subsection)
            lines.append(f"[{subsection.sub_section_id}] {metadata}".rstrip())
            for bullet in bullets_by_subsection.get(subsection.sub_section_id, []):
                lines.append(f"[{bullet.bullet_id}] {bullet.text}")
        lines.append("")
    if master_resume.skills:
        lines.append("TECHNICAL SKILLS [skills]")
        if isinstance(master_resume.skills, dict):
            for key, value in master_resume.skills.items():
                lines.append(f"{key}: {value}")
        else:
            lines.append(str(master_resume.skills))
    return "\n".join(lines).strip()


def serialize_selected_content_for_rewriter(master_resume: MasterResume, selected: SelectedResumeContent) -> str:
    bullets = master_resume.bullets_by_id()
    subsections = master_resume.subsection_by_id()
    lines: list[str] = []
    for subsection_id, selected_subsection in selected.subsections.items():
        subsection = subsections[subsection_id]
        lines.append(f"[{subsection.sub_section_id}] {_metadata_line(subsection)}".rstrip())
        for bullet_id in selected_subsection.bullet_ids:
            bullet = bullets[bullet_id]
            lines.append(f"[{bullet.bullet_id}] {bullet.text}")
        lines.append("")
    return "\n".join(lines).strip()
