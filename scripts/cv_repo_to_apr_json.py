#!/usr/bin/env python3

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
from collections import OrderedDict


def run(args: list[str], cwd: pathlib.Path | None = None) -> str:
    completed = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return completed.stdout


def sync_repo(repo_source: str, checkout_dir: pathlib.Path) -> pathlib.Path:
    checkout_dir.parent.mkdir(parents=True, exist_ok=True)

    if checkout_dir.exists() and (checkout_dir / ".git").exists():
        run(["git", "fetch", "--all", "--prune"], cwd=checkout_dir)
        run(["git", "pull", "--ff-only"], cwd=checkout_dir)
        return checkout_dir

    if checkout_dir.exists():
        raise RuntimeError(f"Checkout directory exists but is not a git repo: {checkout_dir}")

    run(["git", "clone", "--depth=1", repo_source, str(checkout_dir)])
    return checkout_dir


def extract_brace_block(text: str, start_index: int) -> tuple[str, int]:
    depth = 0
    i = start_index
    chars: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
            if depth > 1:
                chars.append(ch)
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(chars), i + 1
            chars.append(ch)
        else:
            chars.append(ch)
        i += 1
    raise ValueError("Unbalanced braces while parsing.")


def extract_entry_body(text: str, start_index: int) -> tuple[str, int]:
    depth = 1
    i = start_index
    chars: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(chars), i + 1
        chars.append(ch)
        i += 1
    raise ValueError("Unbalanced entry braces while parsing bib file.")


def strip_latex(text: str) -> str:
    text = text.replace("\\\\", " ")
    text = text.replace("\\&", "&")
    text = text.replace("\\%", "%")
    text = text.replace("\\$", "$")
    text = text.replace("\\_", "_")
    text = text.replace("\\times", "x")
    text = text.replace("$", "")
    text = re.sub(r"\\textbf\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\textit\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\emph\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\href\{[^{}]*\}\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\extlink\{[^{}]*\}\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z@]+", "", text)
    text = text.replace("{", "").replace("}", "")
    text = text.replace("~", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_bib_entries(bib_text: str) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = OrderedDict()
    i = 0
    while True:
        match = re.search(r"@([A-Za-z]+)\{([^,]+),", bib_text[i:])
        if not match:
            break
        entry_type = match.group(1).lower()
        key = match.group(2).strip()
        absolute_match_start = i + match.start()
        start = i + match.end()
        body, end = extract_entry_body(bib_text, start)
        fields: dict[str, str] = {"ENTRYTYPE": entry_type, "ID": key}
        for field_match in re.finditer(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body):
            field_name = field_match.group(1).lower()
            value_start = field_match.end()
            while value_start < len(body) and body[value_start].isspace():
                value_start += 1
            if value_start >= len(body):
                continue
            if body[value_start] == "{":
                value, _ = extract_brace_block(body, value_start)
            elif body[value_start] == '"':
                value_end = value_start + 1
                while value_end < len(body) and body[value_end] != '"':
                    if body[value_end] == "\\":
                        value_end += 1
                    value_end += 1
                value = body[value_start + 1:value_end]
            else:
                value_end = value_start
                while value_end < len(body) and body[value_end] not in ",\n":
                    value_end += 1
                value = body[value_start:value_end]
            fields[field_name] = strip_latex(value)
        entries[key] = fields
        i = end
    return entries


def parse_category_map(tex: str) -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {}
    for match in re.finditer(r"\\addtocategory\{([^}]+)\}\s*\{", tex):
        category = match.group(1).strip()
        block, _ = extract_brace_block(tex, match.end() - 1)
        keys = [key.strip() for key in block.replace("\n", " ").split(",") if key.strip()]
        categories[category] = keys
    return categories


def extract_section(tex: str, start_marker: str, end_marker: str) -> str:
    start = tex.find(start_marker)
    if start == -1:
        return ""
    end = tex.find(end_marker, start + len(start_marker))
    if end == -1:
        end = len(tex)
    return tex[start:end]


def extract_item_block(tex: str, header: str, next_headers: list[str]) -> list[str]:
    start = tex.find(header)
    if start == -1:
        return []
    end = len(tex)
    for next_header in next_headers:
        pos = tex.find(next_header, start + len(header))
        if pos != -1 and pos < end:
            end = pos
    block = tex[start:end]
    items = re.findall(r"\\item\[\]\s*(.+)", block)
    return [strip_latex(item) for item in items if strip_latex(item)]


def extract_line_value(tex: str, label: str) -> str:
    pattern = rf"{re.escape(label)}\s*(.+)"
    match = re.search(pattern, tex)
    return strip_latex(match.group(1)) if match else ""


def extract_same_line_after_marker(tex: str, marker: str) -> str:
    index = tex.find(marker)
    if index == -1:
        return ""
    remainder = tex[index + len(marker):]
    line = remainder.splitlines()[0]
    return strip_latex(line)


def extract_following_text(tex: str, marker: str) -> str:
    index = tex.find(marker)
    if index == -1:
        return ""
    remainder = tex[index + len(marker):]
    for line in remainder.splitlines():
        cleaned = strip_latex(line)
        if cleaned:
            return cleaned
    return ""


def parse_employment_rank(tex: str) -> str:
    section = extract_section(tex, r"\textbf{EMPLOYMENT HISTORY:}", r"\textbf{ACADEMIC AWARDS AND DISTINCTIONS:}")
    rows = re.findall(r"([0-9]{4}[^&\n]*)\s*&\s*([^&\n]+)\s*&\s*([^\\\n]+)", section)
    if not rows:
        return ""
    return strip_latex(rows[0][1])


def parse_supervision(tex: str) -> tuple[list[dict[str, str]], dict[str, str], list[str]]:
    section = extract_section(tex, r"\textbf{GRADUATE STUDENT SUPERVISION}", r"\textbf{A Note on Service in Human")
    level = None
    graduate_rows: list[dict[str, str]] = []
    committee_lines: list[str] = []
    committee_counts: dict[str, str] = {"total": "", "completed": "", "in_progress": ""}

    lines = [line.strip() for line in section.splitlines()]
    in_committee = False
    for line in lines:
        level_match = re.search(r"\\item\[(PDF|PhD|MSc|MMath|MHI|MSW)\]", line)
        if level_match:
            level = level_match.group(1)
            continue
        if r"\item[b)] \textbf{As Committee Member}" in line:
            in_committee = True
            level = None
            continue
        if in_committee and line.startswith(r"\item[]"):
            committee_lines.append(strip_latex(line.replace(r"\item[]", "", 1)))
            continue
        student_match = re.match(r"\\item\s+(.+)", line)
        if student_match and level:
            text = strip_latex(student_match.group(1))
            name = text.split(",", 1)[0].strip()
            status = ""
            year_match = re.search(r"\b(19|20)\d{2}\b", text)
            if "In progress" in text or "In Progress" in text:
                status = "In progress"
            elif year_match:
                status = year_match.group(0)
            graduate_rows.append({
                "student_name": name,
                "level": level,
                "start_date": "",
                "completion_status": status,
                "co_supervisor": "",
            })
    return graduate_rows, committee_counts, committee_lines


def years_for_item(text: str) -> list[int]:
    years = [int(year) for year in re.findall(r"\b(19|20)\d{2}\b", text)]
    # regex above with group returns only 19/20; fix with non-capturing
    if years:
        return years
    return [int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", text)]


def overlaps_review_years(text: str, review_years: list[int]) -> bool:
    item_years = [int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", text)]
    if not item_years:
        return False
    min_year = min(item_years)
    max_year = max(item_years)
    return any(min_year <= year <= max_year for year in review_years)


def filter_items_by_year(items: list[str], review_years: list[int], keep_undated: bool = False) -> list[str]:
    filtered = []
    for item in items:
        years = [int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", item)]
        if years:
            if overlaps_review_years(item, review_years):
                filtered.append(item)
        elif keep_undated and item.strip():
            filtered.append(item)
    return filtered


def citation_summary(entry: dict[str, str], category_label: str) -> str:
    year = entry.get("year", "")
    title = entry.get("title", "")
    venue = entry.get("journal") or entry.get("booktitle") or entry.get("institution") or entry.get("publisher") or ""
    pieces = [f"[{category_label}]"]
    if year:
        pieces.append(year + ":")
    if title:
        pieces.append(title)
    if venue:
        pieces.append(f"({venue})")
    return " ".join(piece for piece in pieces if piece).strip()


def entries_for_category(entries: dict[str, dict[str, str]], categories: dict[str, list[str]], category: str, review_years: list[int]) -> list[dict[str, str]]:
    keys = categories.get(category, [])
    selected = []
    for key in keys:
        entry = entries.get(key)
        if not entry:
            continue
        year_text = entry.get("year", "")
        year_match = re.search(r"\b(?:19|20)\d{2}\b", year_text)
        if not year_match:
            continue
        if int(year_match.group(0)) in review_years:
            selected.append(entry)
    return selected


def build_report_from_repo(repo_dir: pathlib.Path, review_years: list[int]) -> dict:
    main_tex = (repo_dir / "main.tex").read_text(encoding="utf-8")
    bib_text = (repo_dir / "scholar.bib").read_text(encoding="utf-8")

    entries = parse_bib_entries(bib_text)
    categories = parse_category_map(main_tex)

    name_line = extract_same_line_after_marker(main_tex, r"\textbf{NAME/DATE:}")
    faculty_name = name_line.split(",")[0].strip() if name_line else "Your Name"
    rank = parse_employment_rank(main_tex)

    award_items = extract_item_block(
        main_tex,
        r"\textbf{ACADEMIC AWARDS AND DISTINCTIONS:}",
        [r"\textbf{SCHOLARLY AND PROFESSIONAL ACTIVITIES:}", "Grant Referee:"],
    )
    grant_referee = extract_item_block(main_tex, "Grant Referee:", ["Journal Referee:"])
    journal_referee = extract_item_block(main_tex, "Journal Referee:", ["Conference Organizing Committee:"])
    org_committee = extract_item_block(main_tex, "Conference Organizing Committee:", ["Conference Program Committee:"])
    prog_committee = extract_item_block(main_tex, "Conference Program Committee:", ["Conference Referee:"])
    conf_referee = extract_item_block(main_tex, "Conference Referee:", [r"\newpage", r"\textbf{A Note on Evaluating Human-Computer Interaction Research}"])
    service_section = extract_section(main_tex, r"\textbf{SERVICE}", r"\textbf{AREAS OF TEACHING EXPERTISE}")
    service_items = [strip_latex(item) for item in re.findall(r"\\item\[\]\s*(.+)", service_section)]
    teaching_expertise = extract_following_text(main_tex, r"\textbf{AREAS OF TEACHING EXPERTISE}")
    research_interests = extract_following_text(main_tex, r"\textbf{CURRENT RESEARCH INTERESTS}")

    graduate_rows, committee_counts, committee_lines = parse_supervision(main_tex)

    journal_entries = entries_for_category(entries, categories, "journal", review_years)
    conference_entries = entries_for_category(entries, categories, "conference", review_years)
    technical_entries = entries_for_category(entries, categories, "technicalreports", review_years)
    patent_entries = entries_for_category(entries, categories, "patent", review_years)
    other_entries = entries_for_category(entries, categories, "other", review_years)
    software_entries = entries_for_category(entries, categories, "software", review_years)
    presentation_entries = entries_for_category(entries, categories, "presentations", review_years)
    invited_entries = entries_for_category(entries, categories, "invited", review_years)

    scholarship_summary: list[str] = []
    scholarship_summary.extend(citation_summary(entry, "Journal") for entry in journal_entries)
    scholarship_summary.extend(citation_summary(entry, "Conference") for entry in conference_entries)
    scholarship_summary.extend(citation_summary(entry, "Report") for entry in technical_entries)
    scholarship_summary.extend(citation_summary(entry, "Software") for entry in software_entries)
    scholarship_summary.extend(citation_summary(entry, "Presentation") for entry in presentation_entries)
    scholarship_summary.extend(citation_summary(entry, "Invited talk") for entry in invited_entries)

    research_grants_section = extract_section(main_tex, r"\textbf{RESEARCH GRANTS AND CONTRACTS:}", r"\end{document}")
    grants_lines = [strip_latex(line) for line in research_grants_section.splitlines() if "&" in line]
    grants_for_years = []
    for line in grants_lines:
        if overlaps_review_years(line, review_years):
            grants_for_years.append(line.replace("&", " | "))
    scholarship_summary.extend(f"[Grant] {line}" for line in grants_for_years[:20])

    committee_year_matches = []
    for item in committee_lines:
        year_match = re.match(r"(\d{4})\s+---\s+(.+)", item)
        if not year_match:
            continue
        if int(year_match.group(1)) in review_years:
            committee_year_matches.append(item)
    total_committee = 0
    for item in committee_year_matches:
        counts = [int(num) for num in re.findall(r"(\d+)\s+(?:MSc|PhD)", item, flags=re.IGNORECASE)]
        total_committee += sum(counts)
    if total_committee:
        committee_counts["total"] = str(total_committee)

    return {
        "review_years": review_years,
        "faculty_name": faculty_name,
        "rank": rank,
        "appointment_type": "",
        "appointment_category": "",
        "leave_dates": "",
        "reduced_workload_percentage": "100%",
        "year1_teaching_weight": "",
        "year1_research_weight": "",
        "year1_service_weight": "",
        "year2_teaching_weight": "",
        "year2_research_weight": "",
        "year2_service_weight": "",
        "teaching_courses": [],
        "scp_entries": [],
        "curriculum_work": [],
        "teaching_professional_development": [],
        "sotl_entries": [],
        "undergrad_supervision_counts": {"total": "", "completed": "", "in_progress": ""},
        "undergrad_supervision": [],
        "graduate_supervision_counts": {
            "total": str(len(graduate_rows)) if graduate_rows else "",
            "completed": str(sum(1 for row in graduate_rows if row["completion_status"] and row["completion_status"] != "In progress")) if graduate_rows else "",
            "in_progress": str(sum(1 for row in graduate_rows if row["completion_status"] == "In progress")) if graduate_rows else "",
        },
        "graduate_supervision": graduate_rows,
        "committee_member_counts": committee_counts,
        "committee_memberships": [],
        "scholarly_summary_year": str(review_years[-1]) if review_years else "",
        "scholarly_summary_counts": {
            "Full refereed published articles": str(len(journal_entries)),
            "Full refereed in-press articles": "",
            "Other scholarly work": str(len(other_entries) + len(software_entries)),
            "Books": "",
            "Book chapters": "",
            "Refereed published conference proceedings": str(len(conference_entries)),
            "Refereed in-press conference proceedings": "",
        },
        "teaching_summary": [f"Areas of teaching expertise: {teaching_expertise}"] if teaching_expertise else [],
        "scholarship_summary": scholarship_summary[:60],
        "technical_reports": [citation_summary(entry, "Technical report") for entry in technical_entries] or [""],
        "research_translation": ([f"Current research interests: {research_interests}"] if research_interests else []) + [citation_summary(entry, "Presentation") for entry in presentation_entries[:10]],
        "patents": [citation_summary(entry, "Patent") for entry in patent_entries] or [""],
        "service_university": filter_items_by_year(service_items, review_years),
        "service_profession_membership": ["ACM Professional Member 2008 -- Present"],
        "service_profession_committees": filter_items_by_year(org_committee + prog_committee + conf_referee, review_years),
        "service_academia_grants": filter_items_by_year(grant_referee, review_years),
        "service_academia_journals": filter_items_by_year(journal_referee, review_years),
        "service_academia_other": committee_year_matches or [""],
        "service_public": [citation_summary(entry, "Invited talk") for entry in invited_entries] or [""],
        "service_other": [""],
        "awards": filter_items_by_year(award_items, review_years),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync a CV repo and build APR JSON from it.")
    parser.add_argument("repo_source", help="Git URL or local path to the CV repository")
    parser.add_argument("output_json_path")
    parser.add_argument("--years", nargs="+", type=int, required=True)
    parser.add_argument("--checkout-dir", default="generated/cv_repo_cache")
    args = parser.parse_args()

    output_path = pathlib.Path(args.output_json_path).expanduser().resolve()
    checkout_dir = pathlib.Path(args.checkout_dir)
    if not checkout_dir.is_absolute():
        checkout_dir = (pathlib.Path.cwd() / checkout_dir).resolve()

    repo_dir = sync_repo(args.repo_source, checkout_dir)
    report = build_report_from_repo(repo_dir, args.years)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
