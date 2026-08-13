from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

RequirementCategory = Literal["technical", "responsibility", "domain", "system_design", "soft_skill", "leadership", "education", "certification", "other"]


class WeightedConcept(BaseModel):
    name: str
    importance: int = Field(ge=0, le=100)
    required: bool = False


class JobRequirement(BaseModel):
    id: str
    category: RequirementCategory
    description: str
    importance: int = Field(ge=0, le=100)
    required: bool
    skills: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)


class JobSkill(BaseModel):
    name: str
    importance: int = Field(ge=0, le=100)
    required: bool = False
    aliases: list[str] = Field(default_factory=list)


class StructuredJobDescription(BaseModel):
    role: str | None = None
    company: str | None = None
    seniority: str | None = None
    summary: str = ""
    requirements: list[JobRequirement] = Field(default_factory=list)
    skills: list[JobSkill] = Field(default_factory=list)
    responsibilities: list[WeightedConcept] = Field(default_factory=list)
    domain_knowledge: list[WeightedConcept] = Field(default_factory=list)
    system_design_requirements: list[WeightedConcept] = Field(default_factory=list)
    soft_skills: list[WeightedConcept] = Field(default_factory=list)
    leadership_requirements: list[WeightedConcept] = Field(default_factory=list)
    education_requirements: list[WeightedConcept] = Field(default_factory=list)
    certifications: list[WeightedConcept] = Field(default_factory=list)
    important_keywords: list[WeightedConcept] = Field(default_factory=list)
    important_concepts: list[WeightedConcept] = Field(default_factory=list)
    overall_priorities: dict[str, int] = Field(default_factory=dict)
    ambiguities: list[str] = Field(default_factory=list)

    @field_validator("overall_priorities")
    @classmethod
    def validate_priorities(cls, value):
        for key, score in value.items():
            if not isinstance(score, int) or score < 0 or score > 100:
                raise ValueError(f"overall_priorities.{key} must be an integer from 0 to 100")
        return value

    @model_validator(mode="after")
    def validate_requirement_ids(self):
        ids = [requirement.id for requirement in self.requirements]
        if any(not req_id for req_id in ids) or len(ids) != len(set(ids)):
            raise ValueError("Requirement IDs must be present and unique")
        return self
