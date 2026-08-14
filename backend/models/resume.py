from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, model_validator


class ResumeSection(BaseModel):
    section_id: str
    name: str | None = None
    title: str | None = None
    model_config = {"extra": "allow"}


class ResumeSubSection(BaseModel):
    sub_section_id: str
    section_id: str
    model_config = {"extra": "allow"}


class ResumeBullet(BaseModel):
    bullet_id: str
    sub_section_id: str
    text: str
    bold_words: list[str] = Field(default_factory=list)
    model_config = {"extra": "allow"}


class MasterResume(BaseModel):
    header: dict[str, Any] = Field(default_factory=dict)
    sections: list[ResumeSection] = Field(default_factory=list)
    sub_sections: list[ResumeSubSection] = Field(default_factory=list)
    bullets: list[ResumeBullet] = Field(default_factory=list)
    skills: Any = Field(default_factory=dict)
    model_config = {"extra": "allow"}

    @model_validator(mode="after")
    def validate_references(self):
        section_ids = [s.section_id for s in self.sections]
        subsection_ids = [s.sub_section_id for s in self.sub_sections]
        bullet_ids = [b.bullet_id for b in self.bullets]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("Duplicate section_id in master resume")
        if len(subsection_ids) != len(set(subsection_ids)):
            raise ValueError("Duplicate sub_section_id in master resume")
        if len(bullet_ids) != len(set(bullet_ids)):
            raise ValueError("Duplicate bullet_id in master resume")
        section_set = set(section_ids)
        for subsection in self.sub_sections:
            if subsection.section_id not in section_set:
                raise ValueError(f"Subsection {subsection.sub_section_id} references unknown section {subsection.section_id}")
        subsection_set = set(subsection_ids)
        for bullet in self.bullets:
            if bullet.sub_section_id not in subsection_set:
                raise ValueError(f"Bullet {bullet.bullet_id} references unknown subsection {bullet.sub_section_id}")
        return self

    @property
    def section_ids(self) -> set[str]:
        return {section.section_id for section in self.sections}

    @property
    def subsection_ids(self) -> set[str]:
        return {subsection.sub_section_id for subsection in self.sub_sections}

    @property
    def bullet_ids(self) -> set[str]:
        return {bullet.bullet_id for bullet in self.bullets}

    def subsection_by_id(self) -> dict[str, ResumeSubSection]:
        return {subsection.sub_section_id: subsection for subsection in self.sub_sections}

    def bullets_by_id(self) -> dict[str, ResumeBullet]:
        return {bullet.bullet_id: bullet for bullet in self.bullets}

    def to_raw_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
