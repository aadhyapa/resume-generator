from models.ranking import BulletRanking, ResumeRanking, SectionRanking, SubsectionRanking
from models.resume import MasterResume
from models.selection import SelectedResumeContent, SelectedSubsection

SECTION_RECOMMENDED_THRESHOLD = 45
SUBSECTION_RECOMMENDED_THRESHOLD = 50
DEFAULT_TOTAL_BULLET_LIMIT = 10


def _order_maps(master_resume: MasterResume):
    section_order = {section.section_id: index for index, section in enumerate(master_resume.sections)}
    subsection_order = {subsection.sub_section_id: index for index, subsection in enumerate(master_resume.sub_sections)}
    bullet_order = {bullet.bullet_id: index for index, bullet in enumerate(master_resume.bullets)}
    return section_order, subsection_order, bullet_order


def bullet_marginal_value(section: SectionRanking, subsection: SubsectionRanking, bullet: BulletRanking, selected_sibling_bullets: list[BulletRanking] | None = None) -> float:
    selected_sibling_bullets = selected_sibling_bullets or []
    sibling_penalty = 0.0
    selected_ids = {selected.bullet_id for selected in selected_sibling_bullets}
    if selected_ids.intersection(bullet.redundant_with):
        sibling_penalty += 8.0
    sibling_penalty += min(10.0, len(selected_sibling_bullets) * (bullet.redundancy / 25.0))
    return (
        0.45 * bullet.overall
        + 0.20 * bullet.relevance
        + 0.15 * subsection.priority
        + 0.10 * section.priority
        + 0.10 * bullet.uniqueness
        - 0.20 * bullet.redundancy
        - sibling_penalty
    )


def select_resume_content(master_resume: MasterResume, ranking: ResumeRanking, total_bullet_limit: int = DEFAULT_TOTAL_BULLET_LIMIT) -> SelectedResumeContent:
    ranking.validate_against_master_resume(master_resume)
    section_rankings = {section.section_id: section for section in ranking.section_rankings}
    subsection_rankings = {sub.sub_section_id: sub for sub in ranking.subsection_rankings}
    _, subsection_order, bullet_order = _order_maps(master_resume)
    selected = SelectedResumeContent()

    eligible_subsections = [
        sub for sub in ranking.subsection_rankings
        if section_rankings[sub.section_id].recommended or section_rankings[sub.section_id].priority >= SECTION_RECOMMENDED_THRESHOLD or sub.recommended or sub.priority >= SUBSECTION_RECOMMENDED_THRESHOLD or sub.minimum_bullets > 0
    ]
    eligible_subsections.sort(key=lambda sub: (-section_rankings[sub.section_id].priority, -sub.priority, subsection_order[sub.sub_section_id]))

    selected_bullet_rankings: dict[str, list[BulletRanking]] = {}

    def add_bullet(sub: SubsectionRanking, bullet: BulletRanking, reason: str) -> bool:
        if len(selected.selected_bullet_ids()) >= total_bullet_limit:
            return False
        existing = selected.subsections.setdefault(sub.sub_section_id, SelectedSubsection(sub_section_id=sub.sub_section_id, section_id=sub.section_id, bullet_ids=[]))
        if bullet.bullet_id in existing.bullet_ids or len(existing.bullet_ids) >= max(0, sub.maximum_bullets):
            return False
        existing.bullet_ids.append(bullet.bullet_id)
        selected.sections.setdefault(sub.section_id, [])
        if sub.sub_section_id not in selected.sections[sub.section_id]:
            selected.sections[sub.section_id].append(sub.sub_section_id)
        selected_bullet_rankings.setdefault(sub.sub_section_id, []).append(bullet)
        selected.selection_reason_trace.append(f"Selected {bullet.bullet_id}: {reason}")
        return True

    # Coverage pass: protect important subsections first.
    for sub in eligible_subsections:
        target = min(sub.minimum_bullets, sub.maximum_bullets, len(sub.bullets))
        ordered = sorted(sub.bullets, key=lambda bullet: (-bullet_marginal_value(section_rankings[sub.section_id], sub, bullet, selected_bullet_rankings.get(sub.sub_section_id, [])), bullet_order[bullet.bullet_id]))
        for bullet in ordered[:target]:
            add_bullet(sub, bullet, "coverage minimum")

    # Recommended pass.
    candidates: list[tuple[float, int, int, SubsectionRanking, BulletRanking]] = []
    for sub in eligible_subsections:
        section = section_rankings[sub.section_id]
        current = selected_bullet_rankings.get(sub.sub_section_id, [])
        for bullet in sub.bullets:
            candidates.append((bullet_marginal_value(section, sub, bullet, current), subsection_order[sub.sub_section_id], bullet_order[bullet.bullet_id], sub, bullet))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))

    for value, _, _, sub, bullet in candidates:
        existing_count = len(selected.subsections.get(sub.sub_section_id, SelectedSubsection(sub_section_id=sub.sub_section_id, section_id=sub.section_id)).bullet_ids)
        if existing_count >= sub.recommended_bullets and len(selected.selected_bullet_ids()) >= max(1, total_bullet_limit // 2):
            continue
        add_bullet(sub, bullet, f"marginal value {value:.2f}")
        if len(selected.selected_bullet_ids()) >= total_bullet_limit:
            break

    # Preserve master resume bullet order inside each subsection.
    for subsection in selected.subsections.values():
        subsection.bullet_ids.sort(key=lambda bullet_id: bullet_order[bullet_id])
    return selected
