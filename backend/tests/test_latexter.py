import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.latexter import escape_latex, render_bullet_text, render_resume_latex
from services.pdf_compiler import compile_resume_with_length_check


class LatexterTest(unittest.TestCase):
    def sample_resume(self):
        return {
            "header": {
                "name": "Ada Lovelace",
                "phone": "555-0100",
                "email": "ada_lovelace@example.com",
                "github": {"label": "github.com/ada", "url": "https://github.com/ada"},
            },
            "skills": {"technologies": ["Python", "C++", "SQL"]},
            "sec_projects": {
                "section_id": "sec_projects",
                "name": "Projects",
                "sub_sections": {
                    "proj1": {
                        "sub_section_id": "proj1",
                        "section_id": "sec_projects",
                        "name": "Compiler Tool",
                        "tools": "Python, FastAPI",
                        "bullets": [
                            {"bullet_id": "b1", "sub_section_id": "proj1", "text": "Improved runtime by 10% with Python", "bold_words": ["Python"]}
                        ],
                    }
                },
            },
            "sec_education": {
                "section_id": "sec_education",
                "name": "Education",
                "sub_sections": {
                    "edu1": {
                        "sub_section_id": "edu1",
                        "section_id": "sec_education",
                        "school": "Michigan State University",
                        "dates": "May 2027",
                        "degree": "B.S. Computer Science",
                        "location": "East Lansing, MI",
                    }
                },
            },
        }

    def test_escape_latex_special_characters(self):
        self.assertEqual(escape_latex("50% C++ & SQL_1"), r"50\% C++ \& SQL\_1")

    def test_render_resume_latex_uses_template_sections_and_project_format(self):
        latex = render_resume_latex(self.sample_resume())
        self.assertIn(r"\documentclass[letterpaper,11pt]{article}", latex)
        self.assertLess(latex.index(r"\section{Education}"), latex.index(r"\section{Projects}"))
        self.assertIn(r"\resumeProjectHeading", latex)
        self.assertIn(r"\textbf{Compiler Tool} $|$ \emph{Python, FastAPI}", latex)
        self.assertIn(r"\section{Technical Skills}", latex)

    def test_render_bullet_text_bolds_words_and_escapes_percent(self):
        rendered = render_bullet_text("Cut failures by 10% with Vitest", ["Vitest"])
        self.assertIn(r"10\%", rendered)
        self.assertIn(r"\textbf{Vitest}", rendered)

    def test_compile_loop_retries_until_pdf_fits_page_limit(self):
        calls = []

        def fake_compiler(latex):
            calls.append(latex)
            return b"%PDF", "ok"

        def fake_page_counter(_pdf_bytes):
            return 2 if len(calls) == 1 else 1

        result = compile_resume_with_length_check(
            self.sample_resume(), compiler=fake_compiler, page_counter=fake_page_counter
        )
        self.assertTrue(result.fits_page_limit)
        self.assertEqual(result.page_count, 1)
        self.assertEqual(result.attempts, 2)


if __name__ == "__main__":
    unittest.main()
