# APR LaTeX Template Project

This project rebuilds the Faculty Performance Review directly in LaTeX. The goal is to reproduce the Word form natively with LaTeX tables, headings, spacing, and fillable data structures, not by overlaying text onto the original document.

## Project layout

- `reference/apr_template_source.docx`
  - The original APR form copied into the project for reference.
- `reference/apr_template_reference.pdf`
  - PDF export of the same source file for visual comparison while refining the LaTeX layout.
- `tex/apr_template.tex`
  - Main LaTeX template for Attachment A.
- `scripts/extract_cv_text.py`
  - Extracts plain text from a CV.
- `scripts/cv_to_apr_json.py`
  - Produces a draft APR JSON file from CV text.
- `scripts/render_apr.py`
  - Renders APR JSON into LaTeX macros and table bodies.
- `data/report_data.json`
  - Working APR data file.
- `Makefile`
  - Build helpers.

## Workflow

1. Extract CV text:

```bash
python3 scripts/extract_cv_text.py /path/to/your_cv.docx generated/cv.txt
```

2. Build draft APR data:

```bash
python3 scripts/cv_to_apr_json.py generated/cv.txt data/report_data.json --years 2025 2026
```

3. Compile the report:

```bash
make apr
```

4. Open the PDF:

```bash
open generated/apr_filled.pdf
```

## Current status

The LaTeX template now follows the APR’s native table structure more closely:

- front matter and workload weightings
- courses taught table
- SCP table
- curriculum work table
- professional development table
- scholarship of teaching and learning table
- undergraduate, graduate, and committee supervision tables
- scholarly activity summary table
- direct-entry sections for research translation, service, and awards

## What still needs tuning

- line-by-line spacing against the reference PDF
- exact column widths and page breaks
- CV parsing tuned against your actual CV sections and naming conventions
- optional support for Attachments B and C if you want the full package recreated
