import json
import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from algorithms.v2_selector import select_resume_content
from algorithms.v2_trimmer import remove_lowest_loss_item, trim_to_page_limit
from llm.client import LLMResponse
from llm.json_utils import LLMJSONParseError, parse_json_object
from models.jd import StructuredJobDescription
from models.ranking import ResumeRanking
from models.resume import MasterResume
from models.rewriting import BulletRewriteResponse
from models.selection import SelectedResumeContent, SelectedSubsection
from serializers.resume_compact import serialize_selected_content_for_rewriter
from services.v2_pipeline import generate_resume_v2


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate_json(self, *, model, prompt, temperature=0.1, max_tokens=4000):
        self.calls.append({"model": model, "prompt": prompt})
        return LLMResponse(text=json.dumps(self.responses.pop(0)), model=model, latency_ms=1)


def sample_master_resume():
    return MasterResume.model_validate(
        {
            "header": {"name": "Ada"},
            "sections": [
                {"section_id": "sec_education", "name": "Education"},
                {"section_id": "sec_experience", "name": "Experience"},
                {"section_id": "sec_projects", "name": "Projects"},
                {"section_id": "sec_leadership", "name": "Leadership"},
            ],
            "sub_sections": [
                {"sub_section_id": "edu1", "section_id": "sec_education", "school": "MSU", "dates": "May 2027", "degree": "BS CS"},
                {"sub_section_id": "exp1", "section_id": "sec_experience", "name": "QA Engineer", "company": "Hudl", "dates": "2025"},
                {"sub_section_id": "exp2", "section_id": "sec_experience", "name": "Software Engineer", "company": "Waggoner", "dates": "2024"},
                {"sub_section_id": "proj1", "section_id": "sec_projects", "name": "Resume Tool", "tools": "FastAPI, React"},
                {"sub_section_id": "lead1", "section_id": "sec_leadership", "organization": "Club", "position": "Lead"},
            ],
            "bullets": [
                {"bullet_id": "edu_b1", "sub_section_id": "edu1", "text": "Data Structures and Algorithms"},
                {"bullet_id": "exp1_b1", "sub_section_id": "exp1", "text": "Improved CI reliability by 30% using Python"},
                {"bullet_id": "exp2_b1", "sub_section_id": "exp2", "text": "Built scalable Go backend services"},
                {"bullet_id": "exp2_b2", "sub_section_id": "exp2", "text": "Designed PostgreSQL schema for backend data"},
                {"bullet_id": "proj1_b1", "sub_section_id": "proj1", "text": "Built React and FastAPI resume customizer"},
                {"bullet_id": "lead1_b1", "sub_section_id": "lead1", "text": "Led 5 members and coordinated weekly delivery"},
            ],
            "skills": {"languages": ["Python", "Go"]},
        }
    )


def valid_structured_jd():
    return {
        "role": "Backend Engineer",
        "company": None,
        "seniority": "Entry Level",
        "summary": "Backend engineering role",
        "requirements": [
            {"id": "req_1", "category": "technical", "description": "Build scalable backend systems", "importance": 95, "required": True, "skills": ["Go"], "concepts": ["scalability"]},
            {"id": "req_2", "category": "soft_skill", "description": "Communicate clearly", "importance": 60, "required": False},
        ],
        "skills": [{"name": "Go", "importance": 95, "required": True}],
        "responsibilities": [{"name": "Backend development", "importance": 90, "required": True}],
        "domain_knowledge": [],
        "system_design_requirements": [{"name": "Scalability", "importance": 95, "required": True}],
        "soft_skills": [{"name": "Communication", "importance": 60, "required": False}],
        "leadership_requirements": [],
        "education_requirements": [],
        "certifications": [],
        "important_keywords": [{"name": "Go", "importance": 95, "required": True}],
        "important_concepts": [{"name": "distributed backend systems", "importance": 90, "required": True}],
        "overall_priorities": {"technical": 95, "leadership": 20},
        "ambiguities": ["Company not listed"],
    }


def valid_ranking(leadership_priority=30, project_priority=70):
    return {
        "job_fit_summary": {"overall_fit": 82, "summary": "Strong backend fit", "strongest_evidence": ["exp2_b1"], "biggest_gaps": ["AWS"]},
        "section_rankings": [
            {"section_id": "sec_education", "priority": 45, "recommended": True, "minimum_content": 0, "maximum_content": 1, "reason": "new grad signal"},
            {"section_id": "sec_experience", "priority": 95, "recommended": True, "minimum_content": 2, "maximum_content": 4, "reason": "best evidence"},
            {"section_id": "sec_projects", "priority": project_priority, "recommended": project_priority >= 50, "minimum_content": 0, "maximum_content": 1, "reason": "project evidence"},
            {"section_id": "sec_leadership", "priority": leadership_priority, "recommended": leadership_priority >= 50, "minimum_content": 0, "maximum_content": 1, "reason": "JD dependent"},
        ],
        "subsection_rankings": [
            {"sub_section_id": "edu1", "section_id": "sec_education", "priority": 45, "relevance": 45, "career_value": 50, "recency": 80, "uniqueness": 20, "recommended": True, "minimum_bullets": 0, "recommended_bullets": 1, "maximum_bullets": 1, "reason": "coursework", "bullets": [
                {"bullet_id": "edu_b1", "relevance": 45, "impact": 30, "technical_relevance": 60, "evidence_strength": 45, "uniqueness": 20, "redundancy": 10, "overall": 45, "reason": "CS coursework"}
            ]},
            {"sub_section_id": "exp1", "section_id": "sec_experience", "priority": 78, "relevance": 75, "career_value": 85, "recency": 95, "uniqueness": 60, "recommended": True, "minimum_bullets": 1, "recommended_bullets": 1, "maximum_bullets": 2, "reason": "professional experience", "bullets": [
                {"bullet_id": "exp1_b1", "relevance": 76, "impact": 85, "technical_relevance": 70, "evidence_strength": 80, "uniqueness": 60, "redundancy": 10, "overall": 78, "reason": "CI evidence"}
            ]},
            {"sub_section_id": "exp2", "section_id": "sec_experience", "priority": 96, "relevance": 98, "career_value": 80, "recency": 80, "uniqueness": 90, "recommended": True, "minimum_bullets": 1, "recommended_bullets": 2, "maximum_bullets": 2, "reason": "backend evidence", "bullets": [
                {"bullet_id": "exp2_b1", "relevance": 98, "impact": 90, "technical_relevance": 100, "evidence_strength": 95, "uniqueness": 90, "redundancy": 5, "overall": 97, "reason": "Go backend"},
                {"bullet_id": "exp2_b2", "relevance": 90, "impact": 80, "technical_relevance": 92, "evidence_strength": 88, "uniqueness": 50, "redundancy": 80, "overall": 89, "reason": "some redundant backend data", "redundant_with": ["exp2_b1"]},
            ]},
            {"sub_section_id": "proj1", "section_id": "sec_projects", "priority": project_priority, "relevance": project_priority, "career_value": 65, "recency": 70, "uniqueness": 70, "recommended": project_priority >= 50, "minimum_bullets": 0, "recommended_bullets": 1, "maximum_bullets": 1, "reason": "project", "bullets": [
                {"bullet_id": "proj1_b1", "relevance": 85, "impact": 85, "technical_relevance": 85, "evidence_strength": 80, "uniqueness": 75, "redundancy": 15, "overall": 84, "reason": "full stack"}
            ]},
            {"sub_section_id": "lead1", "section_id": "sec_leadership", "priority": leadership_priority, "relevance": leadership_priority, "career_value": 60, "recency": 80, "uniqueness": 70, "recommended": leadership_priority >= 50, "minimum_bullets": 1 if leadership_priority >= 80 else 0, "recommended_bullets": 1, "maximum_bullets": 1, "reason": "leadership", "bullets": [
                {"bullet_id": "lead1_b1", "relevance": leadership_priority, "impact": 70, "technical_relevance": 10, "evidence_strength": 65, "uniqueness": 70, "redundancy": 0, "overall": leadership_priority, "reason": "team leadership"}
            ]},
        ],
        "skills_analysis": {"priority": 90, "recommended_skills": ["Go", "Python"], "missing_skills": ["AWS"], "reason": "skill match"},
        "unsupported_requirements": [{"requirement_id": "req_aws", "description": "AWS", "importance": 60, "reason": "not shown"}],
    }


class V2ComponentTest(unittest.TestCase):
    def test_agent1_schema_accepts_required_preferred_technical_soft_and_ambiguity(self):
        jd = StructuredJobDescription.model_validate(valid_structured_jd())
        self.assertEqual(jd.requirements[0].category, "technical")
        self.assertTrue(jd.requirements[0].required)
        self.assertEqual(jd.requirements[1].category, "soft_skill")
        self.assertFalse(jd.requirements[1].required)
        self.assertIn("Company not listed", jd.ambiguities)

    def test_agent2_validation_rejects_fabricated_ids_and_requires_complete_bullets(self):
        master = sample_master_resume()
        ResumeRanking.model_validate(valid_ranking()).validate_against_master_resume(master)
        bad = valid_ranking()
        bad["subsection_rankings"][2]["bullets"][0]["bullet_id"] = "fake"
        with self.assertRaises(ValueError):
            ResumeRanking.model_validate(bad).validate_against_master_resume(master)

    def test_selector_preserves_coverage_and_deprioritizes_redundancy(self):
        master = sample_master_resume()
        ranking = ResumeRanking.model_validate(valid_ranking()).validate_against_master_resume(master)
        selected = select_resume_content(master, ranking, total_bullet_limit=4)
        self.assertIn("exp1_b1", selected.selected_bullet_ids())
        self.assertIn("exp2_b1", selected.selected_bullet_ids())
        self.assertIn("proj1_b1", selected.selected_bullet_ids())
        self.assertNotIn("lead1_b1", selected.selected_bullet_ids())
        self.assertEqual(selected.model_dump(), select_resume_content(master, ranking, total_bullet_limit=4).model_dump())

    def test_selector_can_include_leadership_for_leadership_heavy_jd(self):
        master = sample_master_resume()
        ranking = ResumeRanking.model_validate(valid_ranking(leadership_priority=90, project_priority=40)).validate_against_master_resume(master)
        selected = select_resume_content(master, ranking, total_bullet_limit=4)
        self.assertIn("lead1_b1", selected.selected_bullet_ids())

    def test_trimmer_removes_lowest_loss_and_preserves_important_coverage(self):
        master = sample_master_resume()
        ranking = ResumeRanking.model_validate(valid_ranking()).validate_against_master_resume(master)
        selected = select_resume_content(master, ranking, total_bullet_limit=5)
        self.assertTrue(remove_lowest_loss_item(selected, ranking))
        self.assertIn("exp1_b1", selected.selected_bullet_ids())
        self.assertIn("exp2_b1", selected.selected_bullet_ids())

    def test_trim_loop_reaches_one_page_deterministically(self):
        master = sample_master_resume()
        ranking = ResumeRanking.model_validate(valid_ranking()).validate_against_master_resume(master)
        selected = select_resume_content(master, ranking, total_bullet_limit=5)
        calls = []

        def fake_compiler(latex):
            calls.append(latex)
            return b"%PDF", "ok"

        def fake_counter(_pdf):
            return 2 if len(calls) <= 4 else 1

        trimmed, result = trim_to_page_limit(master, selected, ranking, compiler=fake_compiler, page_counter=fake_counter)
        self.assertTrue(result.fits_page_limit)
        self.assertEqual(result.page_count, 1)
        self.assertLess(len(trimmed.selected_bullet_ids()), len(selected.selected_bullet_ids()))

    def test_agent3_schema_rejects_extra_ids_reordered_ids_and_changed_numbers(self):
        master = sample_master_resume()
        selected_ids = ["exp1_b1", "exp2_b1"]
        ok = BulletRewriteResponse.model_validate({"rewritten_bullets": [
            {"bullet_id": "exp1_b1", "original_text": "Improved CI reliability by 30% using Python", "rewritten_text": "Using Python, improved CI reliability by 30%"},
            {"bullet_id": "exp2_b1", "original_text": "Built scalable Go backend services", "rewritten_text": "Built scalable Go backend services"},
        ]})
        ok.validate_against_selection(master, selected_ids)
        bad_order = BulletRewriteResponse.model_validate({"rewritten_bullets": [
            {"bullet_id": "exp2_b1", "original_text": "Built scalable Go backend services", "rewritten_text": "Built scalable Go backend services"},
            {"bullet_id": "exp1_b1", "original_text": "Improved CI reliability by 30% using Python", "rewritten_text": "Improved CI reliability by 30% with Python"},
        ]})
        with self.assertRaises(ValueError):
            bad_order.validate_against_selection(master, selected_ids)
        bad_number = BulletRewriteResponse.model_validate({"rewritten_bullets": [
            {"bullet_id": "exp1_b1", "original_text": "Improved CI reliability by 30% using Python", "rewritten_text": "Improved CI reliability by 40% with Python"},
            {"bullet_id": "exp2_b1", "original_text": "Built scalable Go backend services", "rewritten_text": "Built scalable Go backend services"},
        ]})
        with self.assertRaises(ValueError):
            bad_number.validate_against_selection(master, selected_ids)
        bad_id = BulletRewriteResponse.model_validate({"rewritten_bullets": [{"bullet_id": "fake", "original_text": "x", "rewritten_text": "x"}]})
        with self.assertRaises(ValueError):
            bad_id.validate_against_selection(master, selected_ids)

    def test_selected_content_for_rewriter_serializes_in_master_resume_order(self):
        master = sample_master_resume()
        selected = SelectedResumeContent(
            subsections={
                "exp2": SelectedSubsection(sub_section_id="exp2", section_id="sec_experience", bullet_ids=["exp2_b1"]),
                "exp1": SelectedSubsection(sub_section_id="exp1", section_id="sec_experience", bullet_ids=["exp1_b1"]),
            }
        )
        serialized = serialize_selected_content_for_rewriter(master, selected)
        self.assertLess(serialized.index("[exp1]"), serialized.index("[exp2]"))


    def test_v2_json_parse_error_identifies_agent_and_nearby_lines(self):
        malformed_response = """{
  "rewritten_bullets": [
    {"bullet_id": "exp1_b1"}
    {"bullet_id": "exp2_b1"}
  ]
}"""
        with self.assertRaises(LLMJSONParseError) as ctx:
            parse_json_object(malformed_response, source="v2 bullet_rewriter")
        message = str(ctx.exception)
        self.assertIn("Invalid JSON from v2 bullet_rewriter", message)
        self.assertIn("line 4", message)
        self.assertIn('3:     {"bullet_id": "exp1_b1"}', message)
        self.assertIn('4:     {"bullet_id": "exp2_b1"}', message)


    def test_v2_json_parse_error_rejects_unescaped_control_characters(self):
        malformed_response = '{"summary": "first line\nsecond line"}'
        with self.assertRaises(LLMJSONParseError) as ctx:
            parse_json_object(malformed_response, source="v2 jd_preprocessor")
        self.assertIn("Invalid control character", str(ctx.exception))

    def test_v2_json_parse_error_truncates_nearby_lines(self):
        long_value = "x" * 250
        malformed_response = f'{{\n  "summary": "{long_value}"\n  "role": "Backend"\n}}'
        with self.assertRaises(LLMJSONParseError) as ctx:
            parse_json_object(malformed_response, source="v2 jd_preprocessor")
        message = str(ctx.exception)
        self.assertIn("...", message)
        self.assertNotIn("x" * 225, message)

    def test_pipeline_sequence_uses_three_agents_once_before_compression(self):
        master_path = Path(__file__).with_name("tmp_master_resume.json")
        master_path.write_text(json.dumps(sample_master_resume().model_dump(mode="python")), encoding="utf-8")
        fake_llm = FakeLLM([
            valid_structured_jd(),
            valid_ranking(),
            {"rewritten_bullets": [
                {"bullet_id": "edu_b1", "original_text": "Data Structures and Algorithms", "rewritten_text": "Data Structures and Algorithms"},
                {"bullet_id": "exp1_b1", "original_text": "Improved CI reliability by 30% using Python", "rewritten_text": "Improved CI reliability by 30% using Python"},
                {"bullet_id": "exp2_b1", "original_text": "Built scalable Go backend services", "rewritten_text": "Built scalable Go backend services"},
                {"bullet_id": "exp2_b2", "original_text": "Designed PostgreSQL schema for backend data", "rewritten_text": "Designed PostgreSQL schema for backend data"},
                {"bullet_id": "proj1_b1", "original_text": "Built React and FastAPI resume customizer", "rewritten_text": "Built React and FastAPI resume customizer"},
            ]},
        ])

        def fake_compiler(_latex):
            return b"%PDF", "ok"

        def fake_counter(_pdf):
            return 1

        try:
            result = generate_resume_v2("Backend role", master_resume_path=master_path, llm_client=fake_llm, compiler=fake_compiler, page_counter=fake_counter)
        finally:
            master_path.unlink(missing_ok=True)
        self.assertEqual(len(fake_llm.calls), 3)
        self.assertEqual(result["page_count"], 1)
        self.assertIn("resume", result)


if __name__ == "__main__":
    unittest.main()
