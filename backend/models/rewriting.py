import re
from pydantic import BaseModel, Field
from models.resume import MasterResume


class RewrittenBullet(BaseModel):
    bullet_id: str
    original_text: str
    rewritten_text: str
    bold_words: list[str] = Field(default_factory=list)


class BulletRewriteResponse(BaseModel):
    rewritten_bullets: list[RewrittenBullet]
    model_config = {"extra": "forbid"}

    def validate_against_selection(self, master_resume: MasterResume, selected_bullet_ids: list[str]) -> "BulletRewriteResponse":
        selected = list(selected_bullet_ids)
        selected_set = set(selected)
        ids = [bullet.bullet_id for bullet in self.rewritten_bullets]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate rewritten bullet IDs")
        if set(ids) != selected_set:
            raise ValueError("Rewriter output must include exactly the selected bullet IDs")
        source = master_resume.bullets_by_id()
        for bullet in self.rewritten_bullets:
            if bullet.bullet_id not in source:
                raise ValueError(f"Unknown rewritten bullet ID {bullet.bullet_id}")
            original = source[bullet.bullet_id].text
            if bullet.original_text != original:
                raise ValueError(f"original_text for {bullet.bullet_id} does not match master resume")
            original_numbers = re.findall(r"\d+(?:\.\d+)?%?|→|->", bullet.original_text)
            rewritten_numbers = re.findall(r"\d+(?:\.\d+)?%?|→|->", bullet.rewritten_text)
            if original_numbers != rewritten_numbers:
                raise ValueError(f"Numeric/date-like facts changed for {bullet.bullet_id}")
        return self
