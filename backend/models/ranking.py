from typing import Any
from pydantic import BaseModel, Field, model_validator
from models.resume import MasterResume


class JobFitSummary(BaseModel):
    overall_fit: int = Field(ge=0, le=100)
    summary: str
    strongest_evidence: list[str] = Field(default_factory=list)
    biggest_gaps: list[str] = Field(default_factory=list)


class SectionRanking(BaseModel):
    section_id: str
    priority: int = Field(ge=0, le=100)
    recommended: bool
    minimum_content: int = Field(ge=0)
    maximum_content: int = Field(ge=0)
    reason: str


class BulletRanking(BaseModel):
    bullet_id: str
    relevance: int = Field(ge=0, le=100)
    impact: int = Field(ge=0, le=100)
    technical_relevance: int = Field(ge=0, le=100)
    evidence_strength: int = Field(ge=0, le=100)
    uniqueness: int = Field(ge=0, le=100)
    redundancy: int = Field(ge=0, le=100)
    overall: int = Field(ge=0, le=100)
    reason: str
    redundant_with: list[str] = Field(default_factory=list)


class SubsectionRanking(BaseModel):
    sub_section_id: str
    section_id: str
    priority: int = Field(ge=0, le=100)
    relevance: int = Field(ge=0, le=100)
    career_value: int = Field(ge=0, le=100)
    recency: int = Field(ge=0, le=100)
    uniqueness: int = Field(ge=0, le=100)
    recommended: bool
    minimum_bullets: int = Field(ge=0)
    recommended_bullets: int = Field(ge=0)
    maximum_bullets: int = Field(ge=0)
    reason: str
    bullets: list[BulletRanking] = Field(default_factory=list)


class SkillsAnalysis(BaseModel):
    priority: int = Field(ge=0, le=100)
    recommended_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    reason: str = ""
    model_config = {"extra": "allow"}


class UnsupportedRequirement(BaseModel):
    requirement_id: str | None = None
    description: str
    importance: int = Field(ge=0, le=100)
    reason: str


class ResumeRanking(BaseModel):
    job_fit_summary: JobFitSummary
    section_rankings: list[SectionRanking]
    subsection_rankings: list[SubsectionRanking]
    skills_analysis: SkillsAnalysis
    unsupported_requirements: list[UnsupportedRequirement] = Field(default_factory=list)
    model_config = {"extra": "forbid"}

    def validate_against_master_resume(self, master_resume: MasterResume) -> "ResumeRanking":
        section_ids = [ranking.section_id for ranking in self.section_rankings]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("Duplicate section_id in section rankings")
        if set(section_ids) != master_resume.section_ids:
            raise ValueError("Section rankings must include exactly every master resume section_id")

        subsection_map = master_resume.subsection_by_id()
        ranked_subsection_ids = [ranking.sub_section_id for ranking in self.subsection_rankings]
        if len(ranked_subsection_ids) != len(set(ranked_subsection_ids)):
            raise ValueError("Duplicate sub_section_id in subsection rankings")
        if set(ranked_subsection_ids) != master_resume.subsection_ids:
            raise ValueError("Subsection rankings must include exactly every master resume sub_section_id")

        ranked_bullet_ids: list[str] = []
        for subsection_ranking in self.subsection_rankings:
            subsection = subsection_map.get(subsection_ranking.sub_section_id)
            if subsection is None:
                raise ValueError(f"Unknown subsection ID {subsection_ranking.sub_section_id}")
            if subsection.section_id != subsection_ranking.section_id:
                raise ValueError(f"Subsection {subsection_ranking.sub_section_id} belongs to {subsection.section_id}, not {subsection_ranking.section_id}")
            subsection_bullet_ids = {bullet.bullet_id for bullet in master_resume.bullets if bullet.sub_section_id == subsection_ranking.sub_section_id}
            bullet_ids = [bullet.bullet_id for bullet in subsection_ranking.bullets]
            if len(bullet_ids) != len(set(bullet_ids)):
                raise ValueError(f"Duplicate bullet IDs in subsection {subsection_ranking.sub_section_id}")
            if set(bullet_ids) != subsection_bullet_ids:
                raise ValueError(f"Subsection {subsection_ranking.sub_section_id} must rank exactly its master resume bullets")
            ranked_bullet_ids.extend(bullet_ids)
            for bullet in subsection_ranking.bullets:
                for redundant_id in bullet.redundant_with:
                    if redundant_id not in master_resume.bullet_ids:
                        raise ValueError(f"Bullet {bullet.bullet_id} references unknown redundant bullet {redundant_id}")
        if set(ranked_bullet_ids) != master_resume.bullet_ids or len(ranked_bullet_ids) != len(master_resume.bullet_ids):
            raise ValueError("Rankings must account for every master resume bullet exactly once")
        return self
