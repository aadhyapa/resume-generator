import re
from collections.abc import Iterable, Mapping
from typing import Any

PRIMARY_NAME_KEYS = ("name", "full_name", "fullName")
SUB_SECTION_RESERVED_KEYS = {"sub_section_id", "section_id", "bullets"}

LATEX_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

PREAMBLE = r"""%-------------------------
% Resume in Latex
% Based off of: https://github.com/sb2nov/resume
% License : MIT
%------------------------

\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage[english]{babel}
\usepackage{tabularx}
\usepackage{fontawesome5}
\usepackage{multicol}
\setlength{\multicolsep}{-3.0pt}
\setlength{\columnsep}{-1pt}
\input{glyphtounicode}

%----------FONT OPTIONS----------
% sans-serif
% \usepackage[sfdefault]{FiraSans}
% \usepackage[sfdefault]{roboto}
% \usepackage[sfdefault]{noto-sans}
% \usepackage[default]{sourcesanspro}

% serif
% \usepackage{CormorantGaramond}
% \usepackage{charter}

\pagestyle{fancy}
\fancyhf{} % clear all header and footer fields
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Adjust margins
\addtolength{\oddsidemargin}{-0.6in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1.19in}
\addtolength{\topmargin}{-.7in}
\addtolength{\textheight}{1.4in}

\urlstyle{same}

\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Sections formatting
\titleformat{\section}{
\vspace{-4pt}\scshape\raggedright\large\bfseries
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

% Ensure that generate pdf is machine readable/ATS parsable
\pdfgentounicode=1

%-------------------------
% Custom commands
\newcommand{\resumeItem}[1]{
\item\small{
{#1 \vspace{-2pt}}
}
}

\newcommand{\classesList}[4]{
\item\small{
{#1 #2 #3 #4 \vspace{-2pt}}
}
}

\newcommand{\resumeSubheading}[4]{
\vspace{-2pt}\item
\begin{tabular*}{1.0\textwidth}[t]{l@{\extracolsep{\fill}}r}
\textbf{#1} & \textbf{\small #2} \\
\textit{\small#3} & \textit{\small #4} \\
\end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubSubheading}[2]{
\item
\begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
\textit{\small#1} & \textit{\small #2} \\
\end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeProjectHeading}[2]{
\item
\begin{tabular*}{1.001\textwidth}{l@{\extracolsep{\fill}}r}
\small#1 & \textbf{\small #2}\\
\end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}

\renewcommand\labelitemi{$\vcenter{\hbox{\tiny$\bullet$}}$}
\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.0in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

%-------------------------------------------
%%%%%%  RESUME STARTS HERE  %%%%%%%%%%%%%%%%%%%%%%%%%%%%
"""


def render_resume_latex(resume: Mapping[str, Any]) -> str:
    parts = [PREAMBLE, "\\begin{document}\n", render_header(resume.get("header"))]
    parts.extend(render_section(section) for section in get_ordered_sections(resume, include_skills=False))
    skills = render_skills(resume.get("skills"))
    if skills:
        parts.append(skills)
    parts.append("\\end{document}\n")
    return "\n".join(part for part in parts if part)


def get_ordered_sections(resume: Mapping[str, Any], include_skills: bool = True) -> list[Mapping[str, Any]]:
    sections = [value for key, value in resume.items() if key not in {"header", "skills", "sections"} and is_resume_section(value)]
    if not include_skills:
        sections = [section for section in sections if not is_skills_section(section)]
    return sorted(sections, key=get_section_sort_order)


def render_header(header: Any) -> str:
    if not isinstance(header, Mapping):
        return ""
    name_key = next((key for key in PRIMARY_NAME_KEYS if isinstance(header.get(key), str)), None)
    name = escape_latex(header[name_key]) if name_key else ""
    contacts = dedupe(render_contact_item(key, value) for key, value in get_header_contact_entries(header, name_key))
    contact_line = r" \textasciitilde{} ".join(item for item in contacts if item)
    name_line = rf"{{\Huge \scshape {name}}} \\ \vspace{{1pt}}" if name else ""
    contact_line = f"\\small {contact_line}" if contact_line else ""
    return "\n".join(
        [
            "%----------HEADING----------",
            r"\begin{center}",
            name_line,
            contact_line,
            r"\vspace{-8pt}",
            r"\end{center}",
            "",
        ]
    )


def get_header_contact_entries(header: Mapping[str, Any], excluded_key: str | None = None) -> list[tuple[str, Any]]:
    entries = []
    for key, value in header.items():
        if key == excluded_key:
            continue
        if isinstance(value, Mapping):
            label = value.get("label") or value.get("url")
            entries.append((key, label))
        elif isinstance(value, list):
            entries.extend((key, item) for item in value)
        elif isinstance(value, str) and "|" in value:
            entries.extend((key, item.strip()) for item in value.split("|") if item.strip())
        else:
            entries.append((key, value))
    return entries


def render_contact_item(key: str, value: Any) -> str:
    formatted = format_unknown_value(value)
    if not formatted:
        return ""
    normalized_key = key.lower()
    escaped = escape_latex(formatted)
    if "email" in normalized_key or "@" in formatted:
        return rf"\href{{mailto:{escape_latex(formatted)}}}{{\raisebox{{-0.2\height}}\faEnvelope\  \underline{{{escaped}}}}}"
    if "phone" in normalized_key or "mobile" in normalized_key:
        return rf"\raisebox{{-0.1\height}}\faPhone\ {escaped}"
    if "linkedin" in normalized_key or "linkedin.com" in formatted.lower():
        return rf"\href{{{escape_latex(format_external_url(formatted))}}}{{\raisebox{{-0.2\height}}\faLinkedin\ \underline{{{escaped}}}}}"
    if "github" in normalized_key or "github.com" in formatted.lower():
        return rf"\href{{{escape_latex(format_external_url(formatted))}}}{{\raisebox{{-0.2\height}}\faGithub\ \underline{{{escaped}}}}}"
    if re.match(r"^https?://", formatted, re.I) or "." in formatted:
        return rf"\href{{{escape_latex(format_external_url(formatted))}}}{{\underline{{{escaped}}}}}"
    return escaped


def render_section(section: Mapping[str, Any]) -> str:
    title = escape_latex(get_section_title(section))
    subsections = "\n".join(render_subsection(section, subsection) for subsection in get_subsections(section))
    if not subsections:
        return ""
    return f"""%-----------{title.upper()}-----------
\\section{{{title}}}
\\resumeSubHeadingListStart
{subsections}
\\resumeSubHeadingListEnd
"""


def render_subsection(section: Mapping[str, Any], subsection: Mapping[str, Any]) -> str:
    metadata = get_subsection_metadata(subsection)
    bullets = subsection.get("bullets") if isinstance(subsection.get("bullets"), list) else []
    bullet_block = render_bullets(bullets)
    if is_project_section(section):
        tools = metadata.get("tools") or metadata.get("technologies") or ""
        name = escape_latex(get_subsection_title(subsection, metadata))
        heading = rf"\textbf{{{name}}}"
        if tools:
            heading += rf" $|$ \emph{{{escape_latex(tools)}}}"
        return f"""\\resumeProjectHeading
{{{heading}}}{{}}
{bullet_block}"""
    return f"""\\resumeSubheading
{{{escape_latex(get_subsection_title(subsection, metadata))}}}{{{escape_latex(metadata.get('date') or metadata.get('dates') or '')}}}
{{{escape_latex(get_subsection_role(metadata))}}}{{{escape_latex(metadata.get('location') or '')}}}
{bullet_block}"""


def render_bullets(bullets: Iterable[Any]) -> str:
    rendered = []
    for bullet in bullets:
        if not isinstance(bullet, Mapping) or not bullet.get("text"):
            continue
        rendered.append(rf"\resumeItem{{{render_bullet_text(str(bullet['text']), bullet.get('bold_words'))}}}")
    if not rendered:
        return ""
    return "\\resumeItemListStart\n" + "\n".join(rendered) + "\n\\resumeItemListEnd"


def render_skills(skills: Any) -> str:
    if not skills:
        return ""
    if isinstance(skills, str):
        groups = [("Skills", skills)]
    elif isinstance(skills, list):
        groups = [("Skills", ", ".join(str(item) for item in skills))]
    elif isinstance(skills, Mapping):
        groups = [(prettify_identifier(key), format_unknown_value(value)) for key, value in skills.items() if key.lower() != "section_id"]
    else:
        return ""
    lines = [rf"\textbf{{{escape_latex(category)}}}{{: {escape_latex(value)}}} \\" for category, value in groups if value]
    if not lines:
        return ""
    return "%-----------PROGRAMMING SKILLS-----------\n" + "\\section{Technical Skills}\n" + r"\begin{itemize}[leftmargin=0.15in, label={}]" + "\n\\small{\\item{\n" + "\n".join(lines) + "\n}}\n\\end{itemize}\n\\vspace{-16pt}\n"


def render_bullet_text(text: str, bold_words: Any = None) -> str:
    protected: list[str] = []

    def protect(match: re.Match[str]) -> str:
        protected.append(rf"\textbf{{{escape_latex(match.group(1))}}}")
        return f"@@BOLD{len(protected) - 1}@@"

    escaped = escape_latex(re.sub(r"<b>(.*?)</b>", protect, text, flags=re.I))
    words = bold_words if isinstance(bold_words, list) else []
    for word in words:
        if not word:
            continue
        escaped_word = escape_latex(str(word))
        escaped = re.sub(re.escape(escaped_word), rf"\\textbf{{{escaped_word}}}", escaped, flags=re.I)
    for index, value in enumerate(protected):
        escaped = escaped.replace(escape_latex(f"@@BOLD{index}@@"), value)
    return escaped


def get_subsection_metadata(subsection: Mapping[str, Any]) -> dict[str, str]:
    metadata = {}
    for key, value in subsection.items():
        if key in SUB_SECTION_RESERVED_KEYS:
            continue
        formatted = format_unknown_value(value)
        if formatted:
            metadata[key.lower()] = formatted
    return metadata


def get_subsection_title(subsection: Mapping[str, Any], metadata: Mapping[str, str]) -> str:
    return metadata.get("name") or metadata.get("title") or metadata.get("school") or metadata.get("company") or metadata.get("organization") or metadata.get("employer") or metadata.get("project") or prettify_identifier(str(subsection.get("sub_section_id", "")))


def get_subsection_role(metadata: Mapping[str, str]) -> str:
    return metadata.get("company") or metadata.get("employer") or metadata.get("role") or metadata.get("degree") or metadata.get("position") or metadata.get("major") or ""


def is_resume_section(value: Any) -> bool:
    return isinstance(value, Mapping) and isinstance(value.get("section_id"), str) and isinstance(value.get("sub_sections"), Mapping)


def get_subsections(section: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [value for value in section.get("sub_sections", {}).values() if isinstance(value, Mapping)]


def get_section_title(section: Mapping[str, Any]) -> str:
    return str(section.get("title") or section.get("name") or prettify_identifier(str(section.get("section_id", ""))))


def get_section_id(section: Mapping[str, Any]) -> str:
    return str(section.get("section_id", "")).lower()


def is_project_section(section: Mapping[str, Any]) -> bool:
    section_id = get_section_id(section)
    label = f"{section_id} {section.get('title', '')} {section.get('name', '')}".lower()
    return "project" in label


def is_skills_section(section: Mapping[str, Any]) -> bool:
    section_id = get_section_id(section)
    return section_id == "sec_skills" or "skill" in section_id


def get_section_sort_order(section: Mapping[str, Any]) -> int:
    section_id = get_section_id(section)
    if "education" in section_id:
        return 10
    if "experience" in section_id:
        return 20
    if "project" in section_id:
        return 30
    if "leadership" in section_id:
        return 90
    return 40


def format_unknown_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bool | int | float):
        return str(value)
    if isinstance(value, list):
        return " • ".join(item for item in (format_unknown_value(item) for item in value) if item)
    if isinstance(value, Mapping):
        label = value.get("label") or value.get("url")
        return format_unknown_value(label)
    return None


def prettify_identifier(identifier: str) -> str:
    return re.sub(r"\b\w", lambda match: match.group(0).upper(), re.sub(r"\s+", " ", re.sub(r"[_-]+", " ", identifier)).strip())


def escape_latex(value: Any) -> str:
    return "".join(LATEX_SPECIAL_CHARS.get(char, char) for char in str(value))


def format_external_url(value: str) -> str:
    trimmed = value.strip().rstrip("/")
    return trimmed if re.match(r"^https?://", trimmed, re.I) else f"https://{trimmed}"


def dedupe(items: Iterable[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item and item not in seen:
            unique.append(item)
            seen.add(item)
    return unique
