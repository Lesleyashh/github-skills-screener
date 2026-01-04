from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from github_api_app.client import GitHubAPIClient, GitHubRepository, GitHubUser
from github_api_app.evidence import extract_evidence

from pathlib import Path
import json

SKILLS_CATALOG_PATH = Path("config/skills_catalog.json")


def build_developer_profile(
    client: GitHubAPIClient,
    username: str,
    max_repos: int = 50,
    max_repos_to_scan: int = 20,
) -> Dict[str, Any]:
    """Build a derived candidate profile from public GitHub data."""
    user: GitHubUser = client.get_user(username)

    user_block = {
        "login": user.login,
        "id": user.id,
        "name": user.name,
        "public_repos": user.public_repos,
        "created_at": user.created_at,
        "html_url": user.html_url,
    }

    # FAST FAIL: if user has no public repos, stop here (no extra calls)
    if user.public_repos == 0:
        return {
            "username": user.login,
            "user": user_block,
            "activity": {
                "days_since_last_update": None,
                "most_recent_updated_at": None,
            },
            "evidence": {},
            "precheck_fail_reason": "User has 0 public repositories; no evidence can be evaluated.",
        }

    repos: List[GitHubRepository] = client.get_user_repositories(
        user.login,
        per_page=min(max_repos, 100),
    )

    # Evidence: include forks (so we don't miss LICENSE/README, etc.), but still exclude archived
    repos = [r for r in repos if not r.archived and not r.is_fork]

    activity = _extract_activity(repos)
    raw_evidence = extract_evidence(client, repos, max_repos_to_scan=max_repos_to_scan)
    skills = map_evidence_to_skills(raw_evidence)

    return {
        "username": user.login,
        "user": user_block,
        "activity": activity,
        "evidence": skills,
    }


def _extract_activity(repos: List[GitHubRepository]) -> Dict[str, Any]:
    """Compute recent activity metrics from repository's update timestamps."""
    most_recent: datetime | None = None
    for r in repos:
        dt = _parse_github_iso(r.updated_at)
        if dt and (most_recent is None or dt > most_recent):
            most_recent = dt

    if most_recent is None:
        return {"days_since_last_update": None, "most_recent_updated_at": None}

    now = datetime.now(timezone.utc)
    days = (now - most_recent).days
    return {
        "days_since_last_update": days,
        "most_recent_updated_at": most_recent.isoformat(),
    }


def _parse_github_iso(s: str) -> datetime | None:
    """Parse GitHub ISO timestamp strings into datetime objects."""
    try:
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def map_evidence_to_skills(
    evidence: Dict[str, bool], catalog_path: Path = SKILLS_CATALOG_PATH
) -> Dict[str, bool]:
    """Aggregate low-level evidence signals into high-level skill flags."""
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    skills = catalog.get("skills", {})
    if not isinstance(skills, dict):
        raise ValueError(f"Invalid skills catalog: {catalog_path}")

    skill_flags: Dict[str, bool] = {}
    for skill_name, evidence_keys in skills.items():
        if not isinstance(evidence_keys, list):
            raise ValueError(
                f"Invalid evidence list for skill '{skill_name}' in {catalog_path}"
            )
        skill_flags[skill_name] = any(
            bool(evidence.get(k, False)) for k in evidence_keys
        )

    return skill_flags
