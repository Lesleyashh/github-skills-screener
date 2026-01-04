"""
DB round-trip integration test.

Verifies we can persist and fetch a JD + profile + match result.
"""

import json
from github_api_app import database


def test_db_e2e(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()

    jd_id = database.insert_job_description(
        job_id="ORG-12345",
        name="Senior Engineer",
        version=1,
        criteria={"job_id": "ORG-12345", "skills_required": ["python"]},
    )

    profile_id = database.upsert_developer_profile(
        github_user_id=583231,
        github_username="octocat",
        raw_user={"login": "octocat", "id": 583231},
        signals={"evidence": {"python": True}},
    )

    database.insert_match_result(
        developer_profile_id=profile_id,
        job_description_id=jd_id,
        status="PASS",
        score=85,
        reasons=["All required skills are matched."],
        warnings=[],
    )

    row = database.fetch_report_for_job(job_id="ORG-12345", version=1)[0]
    assert (row["github_username"], row["github_user_id"], row["status"]) == (
        "octocat",
        583231,
        "PASS",
    )
    assert "All required skills are matched." in json.loads(row["reasons_json"])
