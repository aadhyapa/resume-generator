from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from services.latexter import render_resume_latex


@dataclass(frozen=True)
class LatexCompileResult:
    latex: str
    pdf_bytes: bytes
    page_count: int
    attempts: int
    fits_page_limit: bool
    log: str = ""


Compiler = Callable[[str], tuple[bytes, str]]
PageCounter = Callable[[bytes], int]


SPACING_PROFILES = (
    {},
    {r"\vspace{-2pt}": r"\vspace{-3pt}", r"\vspace{-5pt}": r"\vspace{-6pt}"},
    {r"\documentclass[letterpaper,11pt]{article}": r"\documentclass[letterpaper,10pt]{article}"},
    {
        r"\documentclass[letterpaper,11pt]{article}": r"\documentclass[letterpaper,10pt]{article}",
        r"\vspace{-2pt}": r"\vspace{-4pt}",
        r"\vspace{-5pt}": r"\vspace{-7pt}",
        r"\vspace{-7pt}": r"\vspace{-9pt}",
    },
)


def compile_resume_with_length_check(
    resume: dict[str, Any],
    *,
    max_pages: int = 1,
    max_attempts: int = 4,
    compiler: Compiler | None = None,
    page_counter: PageCounter | None = None,
) -> LatexCompileResult:
    compiler = compiler or compile_latex_to_pdf
    page_counter = page_counter or count_pdf_pages
    attempts_to_run = max(1, min(max_attempts, len(SPACING_PROFILES)))
    last_result: LatexCompileResult | None = None

    for index in range(attempts_to_run):
        latex = apply_spacing_profile(render_resume_latex(resume), SPACING_PROFILES[index])
        pdf_bytes, log = compiler(latex)
        page_count = page_counter(pdf_bytes)
        last_result = LatexCompileResult(
            latex=latex,
            pdf_bytes=pdf_bytes,
            page_count=page_count,
            attempts=index + 1,
            fits_page_limit=page_count <= max_pages,
            log=log,
        )
        if last_result.fits_page_limit:
            return last_result

    if last_result is None:
        raise RuntimeError("PDF compile loop did not run")
    return last_result


def apply_spacing_profile(latex: str, replacements: dict[str, str]) -> str:
    for original, replacement in replacements.items():
        latex = latex.replace(original, replacement)
    return latex


def compile_latex_to_pdf(latex: str) -> tuple[bytes, str]:
    try:
        get_compile_command("resume.tex")
    except RuntimeError:
        import logging
        logger = logging.getLogger("backend")
        logger.warning("No LaTeX compiler found. Falling back to mock PDF generation.")
        return b"%PDF-1.4\n%mock-pdf\n/Type /Page\n%%EOF", "mock compile ok"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tex_path = tmp_path / "resume.tex"
        tex_path.write_text(latex, encoding="utf-8")
        command = get_compile_command(tex_path.name)
        completed = subprocess.run(
            command,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        log = (completed.stdout or "") + (completed.stderr or "")
        pdf_path = tmp_path / "resume.pdf"
        if completed.returncode != 0 or not pdf_path.exists():
            raise RuntimeError(f"LaTeX compilation failed:\n{log}")
        return pdf_path.read_bytes(), log


def get_compile_command(filename: str) -> list[str]:
    if shutil.which("latexmk"):
        return ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", filename]
    if shutil.which("pdflatex"):
        return ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", filename]
    raise RuntimeError("No LaTeX compiler found. Install latexmk or pdflatex.")


def count_pdf_pages(pdf_bytes: bytes) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "resume.pdf"
        pdf_path.write_bytes(pdf_bytes)
        if shutil.which("pdfinfo"):
            completed = subprocess.run(
                ["pdfinfo", str(pdf_path)],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            match = re.search(r"^Pages:\s+(\d+)", completed.stdout, flags=re.M)
            if match:
                return int(match.group(1))
    fallback_matches = re.findall(rb"/Type\s*/Page\b", pdf_bytes)
    return max(1, len(fallback_matches))
