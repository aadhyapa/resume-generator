def selector(ranked_bullets, total_limit, per_experience_limit):
    """
    Greedily fills bullets into a final selection, respecting both a global
    cap and a per-experience cap, walking the bullets in rank order (best
    first) and skipping any bullet whose experience is already full.

    :param ranked_bullets: list of dicts, already sorted by relevance score
                            descending. Each dict must have at least:
                            {"bullet_id": ..., "experience_id": ..., "score": ...}
    :param total_limit: max total bullets allowed across the whole resume
    :param per_experience_limit: max bullets allowed per experience
    :return: dict {experience_id: [bullets sorted by score desc]}
    """
    buckets = {}
    total_count = 0

    for bullet in ranked_bullets:
        if total_count >= total_limit:
            break

        exp_id = bullet["experience_id"]

        if exp_id not in buckets:
            buckets[exp_id] = []

        if len(buckets[exp_id]) >= per_experience_limit:
            continue

        buckets[exp_id].append(bullet)
        total_count += 1

    return dict(buckets)