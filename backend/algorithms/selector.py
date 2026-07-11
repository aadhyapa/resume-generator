import logging

logger = logging.getLogger(__name__)

def selector(ranked_bullets: list, total_limit: int, per_experience_limit: int) -> dict:
    """
    Greedily fills bullets into a final selection, respecting both a global
    cap and a per-experience cap, walking the bullets in rank order (best
    first) and skipping any bullet whose experience is already full.

    :param ranked_bullets: list of dicts, already sorted by relevance score
                            descending. Each dict must have at least:
                            {"bullet_id": ..., "sub_section_id": ..., "score": ...}
    :param total_limit: max total bullets allowed across the whole resume
    :param per_experience_limit: max bullets allowed per experience
    :return: dict {sub_section_id: [bullets sorted by score desc]}
    """
    logger.info("Entering selector")
    selected = []
    experience_counts = {}
    total_count = 0

    for bullet in ranked_bullets:
        if total_count >= total_limit:
            break

        exp_id = bullet["sub_section_id"]

        if exp_id not in experience_counts:
            experience_counts[exp_id] = 0

        if experience_counts[exp_id] >= per_experience_limit:
            continue

        selected.append(bullet)
        experience_counts[exp_id] += 1
        total_count += 1

    logger.info("Exiting selector")
    return selected