from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
from github_api_app.job_description import JobDescription


@dataclass(frozen=True)
class MatchResult:
    """
    Result of matching a candidate profile against a Job Description.
    """

    status: str
    reasons: List[str]
    warnings: List[str]
    required_matched: List[str]
    required_missing: List[str]
    optional_matched: List[str]
    optional_missing: List[str]


def match_profile_to_jd(profile: Dict[str, Any], jd: JobDescription) -> MatchResult:
    """
    Evaluate a candidate profile against a Job Description.

    Uses derived evidence signals to determine whether required and
    optional skills are satisfied, applies simple decision rules,
    and returns an explainable match result.
    """
    evidence: Dict[str, bool] = dict(profile.get("evidence", {}) or {})
    activity: Dict[str, Any] = dict(profile.get("activity", {}) or {})

    required = list(jd.skills_required or [])
    optional = list(jd.skills_optional or [])

    required_matched, required_missing = _partition(required, evidence)
    optional_matched, optional_missing = _partition(optional, evidence)

    r_total = len(required)
    r_hit = len(required_matched)
    o_hit = len(optional_matched)

    reasons: List[str] = []
    warnings: List[str] = []

    # ---- Reasons (always explainable) ----
    if required_matched:
        reasons.append(f"Required skills matched: {', '.join(required_matched)}.")
    if required_missing:
        reasons.append(f"Required skills missing: {', '.join(required_missing)}.")

    if optional_matched:
        reasons.append(f"Optional skills matched: {', '.join(optional_matched)}.")
    if optional_missing and optional:
        reasons.append(f"Optional skills missing: {', '.join(optional_missing)}.")

    _apply_activity_warning(activity, jd, warnings)

    # ---- Decision logic (simple + defensible) ----

    # All required matched → PASS
    if r_total > 0 and r_hit == r_total:
        reasons.insert(0, "All required skills are matched.")
        return MatchResult(
            "PASS",
            reasons,
            warnings,
            required_matched,
            required_missing,
            optional_matched,
            optional_missing,
        )

    # ≥50% required AND ≥2 optional → PASS
    if r_total > 0 and (r_hit / r_total) >= 0.5 and o_hit >= 2:
        reasons.insert(
            0,
            f"At least half of required skills matched ({r_hit}/{r_total}) "
            f"with strong optional support ({o_hit} optional skills).",
        )
        return MatchResult(
            "PASS",
            reasons,
            warnings,
            required_matched,
            required_missing,
            optional_matched,
            optional_missing,
        )

    # Otherwise → FAIL
    reasons.insert(
        0,
        "Required skill threshold not met for automatic pass.",
    )
    return MatchResult(
        "FAIL",
        reasons,
        warnings,
        required_matched,
        required_missing,
        optional_matched,
        optional_missing,
    )


def _partition(
    skills: List[str], evidence: Dict[str, bool]
) -> tuple[List[str], List[str]]:
    """
    Split a list of skills into matched skills and missing skills based on evidence flags.
    """
    matched: List[str] = []
    missing: List[str] = []

    for skill in skills:
        if evidence.get(skill, False):
            matched.append(skill)
        else:
            missing.append(skill)

    return matched, missing


def _apply_activity_warning(
    activity: Dict[str, Any], jd: JobDescription, warnings: List[str]
) -> None:
    """
    Append an activity-related warning if the profile falls outside
    the preferred recency window defined in the Job Description.
    """
    window = jd.activity.get("updated_within_days")
    if not window:
        return

    days = activity.get("days_since_last_update")
    if days is None:
        return

    try:
        if int(days) > int(window):
            warnings.append(
                f"Last public repo update was {days} days ago "
                f"(outside preferred window of {window} days)."
            )
    except (TypeError, ValueError):
        return
