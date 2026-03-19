#!/usr/bin/env python3

import argparse
import json
import pathlib
import sys


def latex_escape(text: str) -> str:
    replacements = {
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
    return "".join(replacements.get(char, char) for char in text)


def macro(name: str, value: str) -> str:
    return f"\\newcommand\\{name}{{{latex_escape(value)}}}\n"


def list_macro(name: str, values: list[str]) -> str:
    items = []
    for value in values:
        if value.strip():
            items.append(f"\\item {latex_escape(value)}")
    if not items:
        items.append("\\item ")
    body = "\n".join(items)
    return f"\\newcommand\\{name}{{\\begin{{itemize}}\\itemsep0.2em {body} \\end{{itemize}}}}\n"


def table_body_macro(name: str, rows: list[dict], keys: list[str]) -> str:
    body_lines = []
    for row in rows:
        values = [row.get(key, "") for key in keys]
        escaped = [latex_escape(str(value)) for value in values]
        body_lines.append(" & ".join(escaped) + r" \\ \hline")

    if not body_lines:
        body_lines.append(" & ".join("" for _ in keys) + r" \\ \hline")

    body = "\n".join(body_lines)
    return f"\\newcommand\\{name}{{\n{body}\n}}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render APR macros for LaTeX.")
    parser.add_argument("input_json_path")
    parser.add_argument("output_tex_path")
    args = parser.parse_args()

    input_path = pathlib.Path(args.input_json_path).expanduser().resolve()
    output_path = pathlib.Path(args.output_tex_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = json.loads(input_path.read_text(encoding="utf-8"))
    years = report.get("review_years", [])
    review_years = "-".join(str(year) for year in years) if years else ""

    content = []
    content.append(macro("APRReviewYears", review_years))
    content.append(macro("APRFacultyName", report.get("faculty_name", "")))
    content.append(macro("APRRank", report.get("rank", "")))
    content.append(macro("APRAppointmentType", report.get("appointment_type", "")))
    content.append(macro("APRAppointmentCategory", report.get("appointment_category", "")))
    content.append(macro("APRLeaveDates", report.get("leave_dates", "")))
    content.append(macro("APRReducedWorkload", report.get("reduced_workload_percentage", "")))
    content.append(macro("APRYearOneTeaching", report.get("year1_teaching_weight", "")))
    content.append(macro("APRYearOneResearch", report.get("year1_research_weight", "")))
    content.append(macro("APRYearOneService", report.get("year1_service_weight", "")))
    content.append(macro("APRYearTwoTeaching", report.get("year2_teaching_weight", "")))
    content.append(macro("APRYearTwoResearch", report.get("year2_research_weight", "")))
    content.append(macro("APRYearTwoService", report.get("year2_service_weight", "")))
    content.append(table_body_macro("TeachingCoursesTableBody", report.get("teaching_courses", []), [
        "year_label", "course_term", "enrolled", "first_time", "level", "delivery", "developed", "required_or_elective", "team_taught"
    ]))
    content.append(table_body_macro("SCPTableBody", report.get("scp_entries", []), [
        "course", "implementation", "design", "response_rate", "enrolled", "comments"
    ]))
    content.append(table_body_macro("CurriculumWorkTableBody", report.get("curriculum_work", []), [
        "date", "activity"
    ]))
    content.append(table_body_macro("TeachingPDTableBody", report.get("teaching_professional_development", []), [
        "date", "activity"
    ]))
    content.append(table_body_macro("SOTLTableBody", report.get("sotl_entries", []), [
        "date", "activity"
    ]))
    content.append(table_body_macro("UndergradSupervisionTableBody", report.get("undergrad_supervision", []), [
        "student_name", "project", "start_date", "completion_status", "co_supervisor"
    ]))
    content.append(table_body_macro("GraduateSupervisionTableBody", report.get("graduate_supervision", []), [
        "student_name", "level", "start_date", "completion_status", "co_supervisor"
    ]))
    content.append(table_body_macro("CommitteeMembershipTableBody", report.get("committee_memberships", []), [
        "student_name", "level", "department", "start_date", "completion_status"
    ]))
    content.append(macro("APRUndergradTotal", report.get("undergrad_supervision_counts", {}).get("total", "")))
    content.append(macro("APRUndergradCompleted", report.get("undergrad_supervision_counts", {}).get("completed", "")))
    content.append(macro("APRUndergradInProgress", report.get("undergrad_supervision_counts", {}).get("in_progress", "")))
    content.append(macro("APRGraduateTotal", report.get("graduate_supervision_counts", {}).get("total", "")))
    content.append(macro("APRGraduateCompleted", report.get("graduate_supervision_counts", {}).get("completed", "")))
    content.append(macro("APRGraduateInProgress", report.get("graduate_supervision_counts", {}).get("in_progress", "")))
    content.append(macro("APRCommitteeTotal", report.get("committee_member_counts", {}).get("total", "")))
    content.append(macro("APRCommitteeCompleted", report.get("committee_member_counts", {}).get("completed", "")))
    content.append(macro("APRCommitteeInProgress", report.get("committee_member_counts", {}).get("in_progress", "")))
    content.append(macro("APRScholarlySummaryYear", report.get("scholarly_summary_year", "")))
    content.append(macro("APRPublishedArticles", report.get("scholarly_summary_counts", {}).get("Full refereed published articles", "")))
    content.append(macro("APRInPressArticles", report.get("scholarly_summary_counts", {}).get("Full refereed in-press articles", "")))
    content.append(macro("APROtherScholarlyWork", report.get("scholarly_summary_counts", {}).get("Other scholarly work", "")))
    content.append(macro("APRBooks", report.get("scholarly_summary_counts", {}).get("Books", "")))
    content.append(macro("APRBookChapters", report.get("scholarly_summary_counts", {}).get("Book chapters", "")))
    content.append(macro("APRPublishedProceedings", report.get("scholarly_summary_counts", {}).get("Refereed published conference proceedings", "")))
    content.append(macro("APRInPressProceedings", report.get("scholarly_summary_counts", {}).get("Refereed in-press conference proceedings", "")))
    content.append(list_macro("APRTeachingSummary", report.get("teaching_summary", [])))
    content.append(list_macro("APRScholarshipSummary", report.get("scholarship_summary", [])))
    content.append(list_macro("APRTechnicalReports", report.get("technical_reports", [])))
    content.append(list_macro("APRResearchTranslation", report.get("research_translation", [])))
    content.append(list_macro("APRPatents", report.get("patents", [])))
    content.append(list_macro("APRServiceUniversity", report.get("service_university", [])))
    content.append(list_macro("APRServiceProfessionMembership", report.get("service_profession_membership", [])))
    content.append(list_macro("APRServiceProfessionCommittees", report.get("service_profession_committees", [])))
    content.append(list_macro("APRServiceAcademiaGrants", report.get("service_academia_grants", [])))
    content.append(list_macro("APRServiceAcademiaJournals", report.get("service_academia_journals", [])))
    content.append(list_macro("APRServiceAcademiaOther", report.get("service_academia_other", [])))
    content.append(list_macro("APRServicePublic", report.get("service_public", [])))
    content.append(list_macro("APRServiceOther", report.get("service_other", [])))
    content.append(list_macro("APRAwards", report.get("awards", [])))

    output_path.write_text("".join(content), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
