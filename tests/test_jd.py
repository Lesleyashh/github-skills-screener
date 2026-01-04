"""
Tests for JobDescription JSON loading and skill validation.
"""

import json
import pytest

import github_api_app.job_description as jd_mod
from github_api_app.job_description import JobDescription


def test_load_json_accepts_known_skills(tmp_path, monkeypatch):
    """JobDescription loads successfully when all skills exist in the catalog."""
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
    monkeypatch.setattr(jd_mod, "SKILLS_CATALOG_PATH", catalog_path)

    jd_path = tmp_path / "job_skills.json"
    jd_path.write_text(
        json.dumps(
            {
                "job_id": "org-12345",
                "name": "senior engineer",
                "version": 1,
                "skills_required": ["python", "ci"],
                "skills_optional": ["documentation", "iac"],
                "activity": {"updated_within_days": 365},
                "scoring": {"pass_threshold": 70},
            }
        ),
        encoding="utf-8",
    )

    jd = JobDescription.load_json(jd_path)

    assert jd.job_id == "org-12345"
    assert jd.skills_required == ["python", "ci"]
    assert jd.skills_optional == ["documentation", "iac"]


def test_load_json_rejects_unknown_skill(tmp_path, monkeypatch):
    """Unknown skills in the JD config should raise a clear validation error."""
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
                "skills_required": ["python", "iac"],
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
