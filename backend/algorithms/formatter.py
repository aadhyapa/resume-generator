import copy
import logging

logger = logging.getLogger(__name__)


def formater(edited_bullets, resume):
    logger.info("Entering formater")
    final_resume = {}

    try:
        final_resume["header"] = resume["header"]
        final_resume["skills"] = resume["skills"]

        final_resume["sections"] = {}

        sectioned_bullets = {}
        for bullet in edited_bullets:
            if bullet["sub_section_id"] not in sectioned_bullets:
                sectioned_bullets[bullet["sub_section_id"]] = []
            sectioned_bullets[bullet["sub_section_id"]].append(bullet)

        for section in resume["sections"]:
            section_id = section["section_id"]
            final_resume[section_id] = copy.deepcopy(section)
            final_resume[section_id]["sub_sections"] = {}

        for sub_section in resume["sub_sections"]:
            sub_section_id = sub_section["sub_section_id"]
            section_id = sub_section["section_id"]
            should_keep_sub_section = (
                sub_section_id in sectioned_bullets
                or section_id in {"sec_education", "sec_leadership"}
            )

            if should_keep_sub_section:
                final_resume[section_id]["sub_sections"][sub_section_id] = copy.deepcopy(
                    sub_section
                )
                final_resume[section_id]["sub_sections"][sub_section_id][
                    "bullets"
                ] = sectioned_bullets.get(sub_section_id, [])

        logger.info("Exiting formater")
        return final_resume

    except Exception as e:
        logger.error(f"Error during resume formatting: {e}", exc_info=True)
        raise e