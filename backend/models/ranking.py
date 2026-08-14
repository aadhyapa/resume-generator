from __future__ import annotations

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
        import logging
        logger = logging.getLogger("backend")
        
        # 1. Align Section Rankings
        existing_section_rankings = {r.section_id: r for r in self.section_rankings}
        new_section_rankings = []
        for section in master_resume.sections:
            if section.section_id in existing_section_rankings:
                new_section_rankings.append(existing_section_rankings[section.section_id])
            else:
                logger.warning(f"Section {section.section_id} not ranked by LLM, using default ranking.")
                new_section_rankings.append(SectionRanking(
                    section_id=section.section_id,
                    priority=0,
                    recommended=False,
                    minimum_content=0,
                    maximum_content=0,
                    reason="Not ranked by LLM (defaulted)"
                ))
        self.section_rankings = new_section_rankings

        # 2. Align Subsection and Bullet Rankings
        subsection_map = master_resume.subsection_by_id()
        existing_sub_rankings = {r.sub_section_id: r for r in self.subsection_rankings}
        new_sub_rankings = []
        
        # Helper to get default bullet rankings
        def default_bullet_ranking(bullet_id: str) -> BulletRanking:
            return BulletRanking(
                bullet_id=bullet_id,
                relevance=0,
                impact=0,
                technical_relevance=0,
                evidence_strength=0,
                uniqueness=0,
                redundancy=0,
                overall=0,
                reason="Not ranked by LLM (defaulted)",
                redundant_with=[]
            )

        for subsection in master_resume.sub_sections:
            sub_id = subsection.sub_section_id
            subsection_bullets = [b for b in master_resume.bullets if b.sub_section_id == sub_id]
            
            if sub_id in existing_sub_rankings:
                sub_rank = existing_sub_rankings[sub_id]
                # Check section ID alignment
                sub_rank.section_id = subsection.section_id
                
                # Check and align bullets within this subsection
                existing_bullets = {b.bullet_id: b for b in sub_rank.bullets}
                new_bullets = []
                for b in subsection_bullets:
                    if b.bullet_id in existing_bullets:
                        new_bullets.append(existing_bullets[b.bullet_id])
                    else:
                        logger.warning(f"Bullet {b.bullet_id} in subsection {sub_id} not ranked by LLM, using default ranking.")
                        new_bullets.append(default_bullet_ranking(b.bullet_id))
                sub_rank.bullets = new_bullets
                new_sub_rankings.append(sub_rank)
            else:
                logger.warning(f"Subsection {sub_id} not ranked by LLM, using default ranking.")
                bullets_ranking = [default_bullet_ranking(b.bullet_id) for b in subsection_bullets]
                new_sub_rankings.append(SubsectionRanking(
                    sub_section_id=sub_id,
                    section_id=subsection.section_id,
                    priority=0,
                    relevance=0,
                    career_value=0,
                    recency=0,
                    uniqueness=0,
                    recommended=False,
                    minimum_bullets=0,
                    recommended_bullets=0,
                    maximum_bullets=0,
                    reason="Not ranked by LLM (defaulted)",
                    bullets=bullets_ranking
                ))
        self.subsection_rankings = new_sub_rankings

        # 3. Clean up and validate redundant references
        for sub_ranking in self.subsection_rankings:
            for bullet in sub_ranking.bullets:
                clean_redundant = []
                for redundant_id in bullet.redundant_with:
                    if redundant_id in master_resume.bullet_ids:
                        clean_redundant.append(redundant_id)
                    else:
                        logger.warning(f"Bullet {bullet.bullet_id} referenced unknown redundant bullet {redundant_id}, removing.")
                bullet.redundant_with = clean_redundant

        return self
