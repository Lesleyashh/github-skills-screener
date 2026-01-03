from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from github_api_app.client import GitHubAPIClient, GitHubAPIError
from github_api_app.database import (
    fetch_report_for_job,
    init_db,
    insert_job_description,
    insert_match_result,
    purge_old_data,
    upsert_developer_profile,
)
from github_api_app.job_description import JobDescription
from github_api_app.matcher import match_profile_to_jd
from github_api_app.profile_builder import build_developer_profile

logger = logging.getLogger(__name__)


# -------------------------
# Helper Functions 
# -------------------------

def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_usernames(path: str | Path) -> List[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def compute_score(status: str) -> int:
    """
    Low-precision score (used for ordering and filtering only).
    """
    return 100 if status == "PASS" else 0


def _print_skill_table(title: str, rows: List[tuple[str, bool]]) -> None:
    print()
    print(title)
    print("─" * 44)
    for label, present in rows:
        mark = "✅  present" if present else "❌  missing"
        print(f"{label:<22} {mark}")


def _json_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    return []


# -------------------------
# Commands
# -------------------------
def cmd_scan(args: argparse.Namespace) -> None:
    init_db()

    jd = JobDescription.load_json(args.jd)
    if not jd.job_id:
        raise SystemExit(f"JD file is missing job_id: {args.jd}")

    # Store JD snapshot (idempotent by (job_id, version) in your DB implementation)
    jd_db_id = insert_job_description(
        job_id=jd.job_id,
        name=jd.name,
        version=jd.version,
        criteria={
            "job_id": jd.job_id,
            "skills_required": jd.skills_required,
            "skills_optional": jd.skills_optional,
            "activity": jd.activity,
            "scoring": jd.scoring,
        },
    )

    usernames = load_usernames(args.usernames)
    client = GitHubAPIClient(token=args.token)

    logger.info(
        "Scanning %s usernames for job_id=%s (%s v%s)",
        len(usernames),
        jd.job_id,
        jd.name,
        jd.version,
    )

    for username in usernames:
        logger.info("Scanning username=%s", username)

        try:
            profile = build_developer_profile(
                client=client,
                username=username,
                max_repos=args.max_repos,
                max_repos_to_scan=args.max_repos_to_scan,
            )
        except GitHubAPIError as e:
            logger.error("GitHub API error for %s: %s (status=%s)", username, e.message, e.status_code)
            continue

        user = profile.get("user", {}) or {}
        github_user_id = user.get("id")
        github_username = user.get("login") or profile.get("username") or username

        if github_user_id is None:
            logger.error("Missing GitHub user id for %s; cannot store results.", username)
            continue

        # Upsert profile snapshot + derived signals
        profile_id = upsert_developer_profile(
            github_user_id=int(github_user_id),
            github_username=str(github_username),
            raw_user=user,
            signals={
                "activity": profile.get("activity", {}),
                "evidence": profile.get("evidence", {}),
            },
        )

        # FAST FAIL: 0 public repos
        precheck_reason = profile.get("precheck_fail_reason")
        if precheck_reason:
            insert_match_result(
                developer_profile_id=profile_id,
                job_description_id=jd_db_id,
                status="FAIL",
                score=0,
                reasons=[str(precheck_reason)],
                warnings=[],
            )

            continue

        match = match_profile_to_jd(profile, jd)
        score = compute_score(match.status)

        insert_match_result(
            developer_profile_id=profile_id,
            job_description_id=jd_db_id,
            status=match.status,
            score=score,
            reasons=match.reasons,
            warnings=match.warnings,
        )

        # Pretty CLI output: skills, not evidence keys
        evidence = dict(profile.get("evidence", {}) or {})
        required_rows = [(s, bool(evidence.get(s, False))) for s in jd.skills_required]
        optional_rows = [(s, bool(evidence.get(s, False))) for s in jd.skills_optional]

        print(f"\n== {github_username} ==")
        print(f"Status: {match.status} | Score: {score}")
        _print_skill_table("Required skills", required_rows)
        _print_skill_table("Optional skills", optional_rows)

        print()


def cmd_report(args: argparse.Namespace) -> None:
    init_db()

    rows = fetch_report_for_job(
        job_id=args.job_id,
        version=args.version,
        min_score=args.min_score,
    )

    if not rows:
        print("No results found.")
        return

    job_name = rows[0].get("job_name")
    job_version = rows[0].get("job_version")
    print(f"\nReport for job_id={args.job_id} ({job_name} v{job_version})")

    for r in rows:
        reasons = json.loads(r["reasons_json"]) if r.get("reasons_json") else []
        warnings = json.loads(r["warnings_json"]) if r.get("warnings_json") else []

        print(f"- {r['github_username']} (id={r['github_user_id']}): {r['status']} | score={r['score']} | updated={r['profile_updated_at']}")
        for reason in reasons:
            print(f"    • {reason}")
        for warn in warnings:
            print(f"    ⚠ {warn}")
        print()


def cmd_export(args: argparse.Namespace) -> None:
    init_db()

    rows = fetch_report_for_job(
        job_id=args.job_id,
        version=args.version,
        min_score=args.min_score,
    )

    if not rows:
        print("No results found.")
        return

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "job_id",
        "job_name",
        "job_version",
        "github_username",
        "github_user_id",
        "status",
        "score",
        "profile_updated_at",
        "matched_at",
        "reasons_json",
        "warnings_json",
    ]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Exported {len(rows)} rows to {out_path} for {rows[0].get('job_name')} (v{rows[0].get('job_version')}).")


def cmd_purge(args: argparse.Namespace) -> None:
    init_db()
    summary = purge_old_data(args.days)
    print(f"Purged data older than {args.days} days.")
    print(f"- Deleted match results: {summary['deleted_match_results']}")
    print(f"- Deleted developer profiles: {summary['deleted_developer_profiles']}")


# -------------------------
# CLI
# -------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GitHub Evidence Screener (opt-in, public evidence only)")
    parser.add_argument("--log-level", default="INFO", help="DEBUG, INFO, WARNING, ERROR")

    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan usernames against a Job Description config")
    scan.add_argument("--usernames", required=True, help="Path to usernames.txt (one GitHub username per line)")
    scan.add_argument("--jd", required=True, help="Path to job_skills.json for the role")
    scan.add_argument("--token", default=None, help="Optional GitHub token (or set GITHUB_TOKEN env var)")
    scan.add_argument("--max-repos", type=int, default=50, help="Max repos to fetch per user (<=100)")
    scan.add_argument("--max-repos-to-scan", type=int, default=20, help="Max repos to scan for evidence")
    scan.set_defaults(func=cmd_scan)

    report = sub.add_parser("report", help="Show stored results for a job_id")
    report.add_argument("--job-id", required=True, help="Job ID (e.g. org-12345)")
    report.add_argument("--version", type=int, default=None, help="JD version (defaults to latest)")
    report.add_argument("--min-score", type=int, default=0, help="Minimum score filter")
    report.set_defaults(func=cmd_report)

    export = sub.add_parser("export", help="Export stored results for a job_id to CSV")
    export.add_argument("--job-id", required=True, help="Job id (e.g. org-12345)")
    export.add_argument("--out", required=True, help="Output CSV path")
    export.add_argument("--min-score", type=int, default=0, help="Minimum score filter")
    export.add_argument("--version", type=int, default=None, help="Job version (default: latest)")
    export.set_defaults(func=cmd_export)

    purge = sub.add_parser("purge", help="Purge stored personal data older than N days (retention)")
    purge.add_argument("--days", type=int, default=90, help="Keep data for the last N days")
    purge.set_defaults(func=cmd_purge)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)
    args.func(args)


if __name__ == "__main__":
    main()