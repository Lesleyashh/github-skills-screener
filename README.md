# GitHub Skills Screener

A lightweight, opt-in screening tool that validates file presence from **public GitHub user repos** as evidence of **explicit job skills criteria**.

---

## What this tool is for

- Reducing **manual CV screening noise**
- Helping make early-stage screening **consistent and explainable**
- Supporting (not replacing) human review and interviews
- Enabling **clear, actionable feedback** at early hiring stages

---

## What this tool is *not*

- It does **not** judge code quality or architectural skill
- It does **not** rank candidates
- It does **not** penalise private or proprietary work
- It does **not** scrape, clone, or inspect commit history
- It does **not** infer seniority or proficiency from file presence

---

## How it works

### Assumption(s)
- Users explicitly opts-in to screening by providing a GitHub username in job application
- Recruiters provide a plain .txt file with **one username per line**.
- The tool assumes use within an organisation that maintains consistent internal practices, including standardised job_id naming conventions and a minimum set of required and optional skills across roles

1. A **job role** defines required and optional **skills**
2. Skills map to business-defined **evidence signals**
3. Evidence signals map to **file glob patterns**
4. Only public, non-forked, and non-archived repositories are scanned for matching file patterns, and candidates are assigned PASS/FAIL based upon the number of matches found.
5. Results are stored locally in a lightweight SQLite database (`data/app.db`) to support reporting and exporting.

---

### Screening logic

A candidate **PASS**es if **either**:

- **All required skills are matched**, **or**
- **At least 50% of required skills are matched AND at least 2 optional skills are matched**
- Allows strong optional signals to compensate for partial required coverage

Otherwise, the candidate **FAILS**.

Logic in github_api_app/matcher.py

---

## Privacy & retention

- GitHub usernames are treated as personal data
- The local database (`data/app.db`) is **not committed**
- Candidate username files are **not committed**
- Data can be deleted on request
- A purge command enforces data retention like:

   ```bash
   make purge DAYS=90
   ```

---

## Authentication & Rate limits

A GitHub PAT token is optional but recommended.

### GitHub API endpoints used

- `GET /users/{username}`
- `GET /users/{username}/repos`
- `GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1`

### Without token
- ~60 requests/hour (suitable for local testing only)

### With token
- ~5000 requests/hour
- Recommended for real usage and CI

### Getting a GitHub Token
1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Generate new classic token
3. No specific scopes needed as only public data used
4. Copy token and export as `GITHUB_TOKEN` environment variable

---

## Features

- GitHub API integration for public data
- Rule-based, explainable matching
- Command-line interface with readable output
- Local persistence for reporting and export
- CSV export for downstream review
- Unit tests (mocked)
- Integration tests (real API, opt-in)
- Token-based authentication support

---

## Requirements

- **Python 3.10+**
- `requests`
- Optional: GitHub Personal Access Token

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <path/to/cloned/repo>
   ```
2. **Create and activate virtual env:**
   ```bash
   make venv
   ```

3. **Install dependencies:**
Minimum dependencies needed for run time:
   ```bash
   make install
   ```

4. **For development (optional):**
Minimum dependencies needed for development:
   ```bash
   make install-dev
   ```

---

## Usage

Optional: set a default job_id
```bash
export JOB_ID=org-12345
```

Scan usernames:
```bash
make scan JOB_ID=org-12345
# or (if you exported JOB_ID already):
make scan
```

View stored results:
```bash
make report JOB_ID=org-12345
# or:
make report
```

Export results to CSV:
```bash
make export JOB_ID=org-12345
# or:
make export
# or optional filters:
make export JOB_ID=org-12345 VERSION=1 MIN_SCORE=100
#defaults: VERSION=1 (version of job config), MIN_SCORE=0 (returns all users passed and failed).
# when MIN_SCORE=100 report returns only passes
```
---

## Testing

### Run Unit Tests
```bash
make test-unit
```

### Run All Tests (excluding integration)
```bash
make test-all
```

### Run Integration Tests (requires internet)
```bash
make test-integration
```

### Run All Tests
```bash
pytest -v
```

### Run Pre-commit
```bash
make lint
```

---

## License

This project is for personal and educational use.
Reuse and modification are permitted.
