#!/usr/bin/env python3

import argparse
import json
import pathlib
import re
import sys
from collections import defaultdict


HEADING_HINTS = {
    "teaching": ["teaching", "courses taught", "instruction", "supervision"],
    "scholarship": ["publications", "research", "scholarship", "grants", "presentations"],
    "service": ["service", "committee", "editorial", "peer review", "leadership"],
}


def normalize(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip().lower())


def looks_like_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) > 80:
        return False
    return (
        stripped.isupper()
        or stripped.endswith(":")
        or bool(re.fullmatch(r"[A-Z][A-Za-z/&,\- ]{2,}", stripped))
    )


def detect_section(line: str) -> str | None:
    lowered = normalize(line)
    for section, hints in HEADING_HINTS.items():
        if any(hint in lowered for hint in hints):
            return section
    return None


def filter_lines_for_years(lines: list[str], years: list[int]) -> list[str]:
    year_tokens = {str(year) for year in years}
    short_tokens = {str(year)[-2:] for year in years}
    matched = []
    for line in lines:
        lowered = line.lower()
        if any(token in lowered for token in year_tokens):
            matched.append(line)
            continue
        if re.search(r"\b(?:19|20)\d{2}\b", line):
            continue
        if any(re.search(rf"['’]{token}\b", line) for token in short_tokens):
            matched.append(line)
            continue
    return matched


def infer_name(lines: list[str]) -> str:
    for line in lines[:15]:
        stripped = line.strip()
        if stripped and len(stripped.split()) <= 5 and not looks_like_heading(stripped):
            return stripped
    return "Your Name"


def build_report(cv_text: str, years: list[int]) -> dict:
    lines = [line.rstrip() for line in cv_text.splitlines()]
    current_section = None
    buckets: dict[str, list[str]] = defaultdict(list)

    for line in lines:
        if looks_like_heading(line):
            detected = detect_section(line)
            if detected:
                current_section = detected
            continue
        if current_section and line.strip():
            buckets[current_section].append(line.strip())

    scholarship = filter_lines_for_years(buckets["scholarship"], years)
    service = filter_lines_for_years(buckets["service"], years)
    teaching = filter_lines_for_years(buckets["teaching"], years)

    if not teaching:
        teaching = ["Review CV manually to add teaching activities for the report years."]
    if not scholarship:
        scholarship = ["Review CV manually to add scholarship items for the report years."]
    if not service:
        service = ["Review CV manually to add service items for the report years."]

    return {
        "review_years": years,
        "faculty_name": infer_name(lines),
        "rank": "",
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
        "graduate_supervision_counts": {"total": "", "completed": "", "in_progress": ""},
        "graduate_supervision": [],
        "committee_member_counts": {"total": "", "completed": "", "in_progress": ""},
        "committee_memberships": [],
        "scholarly_summary_year": str(years[-1]) if years else "",
        "scholarly_summary_counts": {
            "Full refereed published articles": "",
            "Full refereed in-press articles": "",
            "Other scholarly work": "",
            "Books": "",
            "Book chapters": "",
            "Refereed published conference proceedings": "",
            "Refereed in-press conference proceedings": "",
        },
        "teaching_summary": teaching[:20],
        "scholarship_summary": scholarship[:30],
        "technical_reports": [],
        "research_translation": scholarship[:15],
        "patents": [],
        "service_university": service[:10],
        "service_profession_membership": [],
        "service_profession_committees": [],
        "service_academia_grants": [],
        "service_academia_journals": [],
        "service_academia_other": [],
        "service_public": service[10:20],
        "service_other": service[20:30],
        "awards": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert CV text into APR JSON.")
    parser.add_argument("input_text_path")
    parser.add_argument("output_json_path")
    parser.add_argument("--years", nargs="+", type=int, required=True)
    args = parser.parse_args()

    text_path = pathlib.Path(args.input_text_path).expanduser().resolve()
    output_path = pathlib.Path(args.output_json_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cv_text = text_path.read_text(encoding="utf-8")
    report = build_report(cv_text, args.years)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
