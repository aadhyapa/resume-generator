from pydantic import BaseModel, Field


class SelectedSubsection(BaseModel):
    sub_section_id: str
    section_id: str
    bullet_ids: list[str] = Field(default_factory=list)


class SelectionRemoval(BaseModel):
    item_type: str
    item_id: str
    reason: str
    loss: float


class SelectedResumeContent(BaseModel):
    sections: dict[str, list[str]] = Field(default_factory=dict)
    subsections: dict[str, SelectedSubsection] = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    removed_items: list[SelectionRemoval] = Field(default_factory=list)
    selection_reason_trace: list[str] = Field(default_factory=list)

    def selected_bullet_ids(self) -> list[str]:
        ids: list[str] = []
        for subsection in self.subsections.values():
            ids.extend(subsection.bullet_ids)
        return ids
