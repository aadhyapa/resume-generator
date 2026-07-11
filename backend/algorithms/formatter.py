
def formater(edited_bullets, resume):
    final_resume = {}

    final_resume["header"] = resume["header"]
    final_resume["skills"] = resume["skills"]

    final_resume["sections"] = {}

    sectioned_bullets = {}
    for bullet in edited_bullets:
        if bullet["sub_section_id"] not in sectioned_bullets:
            sectioned_bullets[ bullet["sub_section_id"]] = []
        sectioned_bullets[ bullet["sub_section_id"]].append(bullet)
    
    for section in resume["sections"]:
        final_resume[section["section_id"]] = {}
        final_resume[section["section_id"]]["section_name"] = section["section_name"]
        final_resume[section["section_id"]]["sub_sections"] = {}

    for sub_section in resume["sub_sections"]:
        if sub_section["sub_section_id"] in sectioned_bullets:
            final_resume[sub_section["section_id"]]["sub_sections"][sub_section["sub_section_id"]] = sub_section
            final_resume[sub_section["section_id"]]["sub_sections"][sub_section["sub_section_id"]]["bullets"] = sectioned_bullets["sub_section_id"]

    return final_resume