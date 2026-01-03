.PHONY: help venv install install-dev lint test scan report purge clean export require-job-id ensure-report-dir

PY := .venv/bin/python
PIP := .venv/bin/pip
PRECOMMIT := .venv/bin/pre-commit
PYTEST := .venv/bin/pytest

# -------------------------------------------------
# Usage examples:
#
#   make install-dev
#
#   make scan JOB_ID=org-12345
#
#   make report JOB_ID=org-12345
#
#   make export JOB_ID=org-12345
#
#   make export JOB_ID=org-12345 MIN_SCORE=70
#
#   make export JOB_ID=org-12345 OUT= data/reports/$(JOB_ID).csv
#
#   make purge DAYS=90
# -------------------------------------------------

require-job-id:
	@if [ -z "$(JOB_ID)" ]; then \
		echo "ERROR: JOB_ID is required. Example: make scan JOB_ID=org-12345"; \
		exit 1; \
	fi

# Derived paths based on JOB_ID (no defaults)
JD_PATH = config/job_roles/$(JOB_ID)/job_skills.json
USERNAMES_PATH = candidate_input/job_roles/$(JOB_ID)/usernames.txt

help:
	@echo ""
	@echo "Common commands:"
	@echo "  make install-dev                         Set up dev environment"
	@echo "  make lint                                Run pre-commit on all files"
	@echo "  make test                                Run unit tests (no integration)"
	@echo "  make scan JOB_ID=org-12345               Scan usernames for a job_id"
	@echo "  make report JOB_ID=org-12345             View stored results for job_id"
	@echo "  make export JOB_ID=org-12345             Export report CSV (set OUT=...)"
	@echo "  make purge DAYS=90                       Apply data retention"
	@echo ""

venv:
	python3 -m venv .venv

install: venv
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt

install-dev: install
	$(PIP) install -r requirements-dev.txt
	$(PRECOMMIT) install

lint:
	$(PRECOMMIT) run --all-files

test:
	$(PYTEST) -m "not integration" -v

scan: require-job-id
	$(PY) main.py scan \
		--jd $(JD_PATH) \
		--usernames $(USERNAMES_PATH)

report: require-job-id
	$(PY) main.py report \
		--job-id $(JOB_ID)

DAYS ?= 90
purge:
	$(PY) main.py purge --days $(DAYS)

clean:
	rm -rf .venv data/app.db

# Export (caller can override OUT, MIN_SCORE, VERSION)
MIN_SCORE ?= 0
OUT ?= data/reports/$(JOB_ID).csv

ensure-report-dir:
	@mkdir -p "$$(dirname "$(OUT)")"

export: require-job-id ensure-report-dir
	$(PY) main.py export \
		--job-id $(JOB_ID) \
		--out $(OUT) \
		--min-score $(MIN_SCORE) \
		$(if $(VERSION),--version $(VERSION),)