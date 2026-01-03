import json
from github_api_app import database


def test_db_roundtrip_profile_jd_match(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()

    jd_row_id = database.insert_job_description(
        job_id="ORG-12345",
        name="Senior Engineer",
        version=1,
        criteria={"job_id": "ORG-12345", "skills_required": ["python"]},
    )

    profile_row_id = database.upsert_developer_profile(
        github_user_id=583231,
        github_username="octocat",
        raw_user={"login": "octocat", "id": 583231},
        signals={"evidence": {"python": True}},
    )

    database.insert_match_result(
        developer_profile_id=profile_row_id,
        job_description_id=jd_row_id,
        status="PASS",
        score=85,
        reasons=["All required skills are matched."],
        warnings=[],
    )

    rows = database.fetch_report_for_job(job_id="ORG-12345", version=1, min_score=0)
    assert len(rows) == 1
    assert rows[0]["github_username"] == "octocat"
    assert rows[0]["github_user_id"] == 583231

    reasons = json.loads(rows[0]["reasons_json"])
    assert "All required skills are matched." in reasons