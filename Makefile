PYTHON := python3
PDLATEX := pdflatex

.PHONY: apr clean cv-json

apr:
	mkdir -p generated
	$(PYTHON) scripts/render_apr.py data/report_data.json generated/macros.tex
	$(PDLATEX) -interaction=nonstopmode -halt-on-error -output-directory=generated tex/apr_template.tex
	$(PDLATEX) -interaction=nonstopmode -halt-on-error -output-directory=generated tex/apr_template.tex
	mv -f generated/apr_template.pdf generated/apr_filled.pdf

cv-json:
	@test -n "$(CV)" || (echo "Usage: make cv-json CV=/path/to/cv.docx YEARS='2025 2026'" && exit 1)
	$(PYTHON) scripts/extract_cv_text.py "$(CV)" generated/cv.txt
	$(PYTHON) scripts/cv_to_apr_json.py generated/cv.txt data/report_data.json --years $(YEARS)

cv-repo-json:
	@test -n "$(CV_REPO)" || (echo "Usage: make cv-repo-json CV_REPO=https://github.com/user/repo YEARS='2025 2026'" && exit 1)
	$(PYTHON) scripts/cv_repo_to_apr_json.py "$(CV_REPO)" data/report_data.json --years $(YEARS)

clean:
	rm -f generated/*.aux generated/*.log generated/*.out generated/*.tex generated/*.txt generated/*.pdf
