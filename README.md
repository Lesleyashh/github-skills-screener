# GitHub Evidence Screener

A lightweight, opt-in screening tool that validates **public GitHub evidence**
against **explicit, transparent job criteria**.

This tool evaluates **only**:
- what a candidate explicitly provides (a GitHub username)
- what is publicly accessible on GitHub

It does **not** infer seniority or proficiency.
It checks for observable evidence signals (e.g. Dockerfile, tests, CI workflows)
and produces an explainable PASS / FAIL result.

---

## What this tool is for

- Reducing **manual CV screening noise**
- Making early-stage screening **consistent and explainable**
- Supporting (not replacing) human review and interviews

---

## What this tool is *not*

- It does **not** judge code quality or architectural skill
- It does **not** rank candidates by “strength”
- It does **not** penalise private or proprietary work
- It does **not** scrape, clone, or inspect commit history

---

## How it works

1. A **job role** defines required and optional **skills**
2. Skills are mapped to **evidence signals**
3. Evidence signals are mapped to **file globs**
4. Public repositories are scanned (forks excluded)
5. Results are stored locally and reported in a readable format

---

## Matching rules

A candidate **PASSES** if **either**:

- **All required skills are matched**
- **At least half of required skills are matched AND at least 2 optional skills are matched**

Otherwise, the candidate **FAILS**.

This rule is intentionally simple and easy to explain in an interview.

---

## Assumptions & constraints

- Candidates explicitly opt-in by providing a GitHub username
- Only **public** GitHub data is evaluated
- Forked repositories are excluded
- File presence is a heuristic, not proof of authorship or depth
- Activity recency is contextual only

---

## Privacy & retention

- GitHub usernames are treated as personal data
- The local database (`data/app.db`) is **not committed**
- Candidate username files are **not committed**
- A purge command exists to enforce data retention
- Data can be deleted on request

---

## Authentication & rate limits

A GitHub token is optional but recommended.

- Without token: low rate limits (testing only)
- With token: higher rate limits (recommended)

For CI usage:

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GH_API_TOKEN }}


