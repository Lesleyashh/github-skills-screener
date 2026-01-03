import json

import pytest

import github_api_app.job_description as jd_mod
from github_api_app.job_description import JobDescription


def test_job_description_load_json_validates_known_skills(tmp_path, monkeypatch):
    # Arrange: temporary skills catalog
    catalog_path = tmp_path / "skills_catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "version": 1,
                "skills": {
                    "python": ["python_project"],
                    "documentation": ["documentation_readme", "license"],
                    "ci": ["github_actions"],
                },
            }
        ),
        encoding="utf-8",
    )

    # Make JobDescription read the temp catalog instead of repo config/
    monkeypatch.setattr(jd_mod, "SKILLS_CATALOG_PATH", catalog_path)

    # Arrange: a valid JD that uses only known skills
    jd_path = tmp_path / "job_skills.json"
    jd_path.write_text(
        json.dumps(
            {
                "job_id": "org-12345",
                "name": "senior engineer",
                "version": 1,
                "skills_required": ["python", "ci"],
                "skills_optional": ["documentation"],
                "activity": {"updated_within_days": 365},
                "scoring": {"pass_threshold": 70},
            }
        ),
        encoding="utf-8",
    )

    # Act
    jd = JobDescription.load_json(jd_path)

    # Assert
    assert jd.job_id == "org-12345"
    assert jd.skills_required == ["python", "ci"]
    assert jd.skills_optional == ["documentation"]


def test_job_description_load_json_raises_on_unknown_skill(tmp_path, monkeypatch):
    catalog_path = tmp_path / "skills_catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "version": 1,
                "skills": {
                    "python": ["python_project"],
                    "documentation": ["documentation_readme", "license"],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(jd_mod, "SKILLS_CATALOG_PATH", catalog_path)

    jd_path = tmp_path / "job_skills.json"
    jd_path.write_text(
        json.dumps(
            {
                "job_id": "org-12345",
                "name": "senior engineer",
                "version": 1,
                "skills_required": ["python"],
                "skills_optional": ["code_qualityyyyyy", "documentation"],
                "activity": {},
                "scoring": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc:
        JobDescription.load_json(jd_path)

    msg = str(exc.value)
    assert "Unknown skills referenced" in msg
    assert "code_qualityyyyyy" in msg
