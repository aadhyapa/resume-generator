import copy
from typing import Any

from models.ranking import ResumeRanking
from models.resume import MasterResume
from models.selection import SelectedResumeContent, SelectionRemoval
from services.pdf_compiler import LatexCompileResult, compile_resume_with_length_check
from services.resume_repository import selected_content_to_resume


def apply_selected_rewrites(master_resume: MasterResume, selected: SelectedResumeContent, rewrites=None) -> list[dict[str, Any]]:
    rewrite_map = {item.bullet_id: item for item in rewrites.rewritten_bullets} if rewrites else {}
    selected_ids = set(selected.selected_bullet_ids())
    bullets = []
    for bullet in master_resume.bullets:
        if bullet.bullet_id not in selected_ids:
            continue
        data = bullet.model_dump(mode="python")
        if bullet.bullet_id in rewrite_map:
            rewritten = rewrite_map[bullet.bullet_id]
            data["text"] = rewritten.rewritten_text
            if rewritten.bold_words:
                data["bold_words"] = rewritten.bold_words
            data["edited"] = data["text"] != bullet.text
        bullets.append(data)
    return bullets


def render_selected_resume(master_resume: MasterResume, selected: SelectedResumeContent, rewrites=None) -> dict[str, Any]:
    return selected_content_to_resume(master_resume, apply_selected_rewrites(master_resume, selected, rewrites))


def _ranking_maps(ranking: ResumeRanking):
    sections = {section.section_id: section for section in ranking.section_rankings}
    subsections = {sub.sub_section_id: sub for sub in ranking.subsection_rankings}
    bullets = {bullet.bullet_id: (sub, bullet) for sub in ranking.subsection_rankings for bullet in sub.bullets}
    return sections, subsections, bullets


def removal_loss(selected: SelectedResumeContent, ranking: ResumeRanking, bullet_id: str) -> float:
    sections, subsections, bullets = _ranking_maps(ranking)
    sub, bullet = bullets[bullet_id]
    section = sections[sub.section_id]
    selected_count = len(selected.subsections[sub.sub_section_id].bullet_ids)
    protected_penalty = 1000 if selected_count <= sub.minimum_bullets and section.priority >= 60 else 0
    only_subsection_penalty = 250 if selected_count == 1 and sub.priority >= 70 else 0
    return protected_penalty + only_subsection_penalty + (0.40 * bullet.overall) + (0.20 * sub.priority) + (0.20 * section.priority) + (0.20 * bullet.uniqueness) - (0.30 * bullet.redundancy)


def remove_lowest_loss_item(selected: SelectedResumeContent, ranking: ResumeRanking) -> bool:
    candidates = []
    for subsection_id, subsection in selected.subsections.items():
        for bullet_id in subsection.bullet_ids:
            candidates.append((removal_loss(selected, ranking, bullet_id), subsection_id, bullet_id))
    if not candidates:
        return False
    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    loss, subsection_id, bullet_id = candidates[0]
    selected.subsections[subsection_id].bullet_ids.remove(bullet_id)
    if not selected.subsections[subsection_id].bullet_ids:
        section_id = selected.subsections[subsection_id].section_id
        del selected.subsections[subsection_id]
        if section_id in selected.sections and subsection_id in selected.sections[section_id]:
            selected.sections[section_id].remove(subsection_id)
        if section_id in selected.sections and not selected.sections[section_id]:
            del selected.sections[section_id]
    selected.removed_items.append(SelectionRemoval(item_type="bullet", item_id=bullet_id, reason="lowest deterministic page-fit loss", loss=loss))
    return True


def trim_to_page_limit(master_resume: MasterResume, selected: SelectedResumeContent, ranking: ResumeRanking, *, max_pages: int = 1, max_trim_iterations: int = 20, compiler=None, page_counter=None) -> tuple[SelectedResumeContent, LatexCompileResult]:
    current = copy.deepcopy(selected)
    last_result = None
    for _ in range(max_trim_iterations + 1):
        resume = render_selected_resume(master_resume, current)
        last_result = compile_resume_with_length_check(resume, max_pages=max_pages, compiler=compiler, page_counter=page_counter)
        if last_result.fits_page_limit:
            return current, last_result
        if not remove_lowest_loss_item(current, ranking):
            return current, last_result
    return current, last_result
