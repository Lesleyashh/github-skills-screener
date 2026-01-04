from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set
import json

SKILLS_CATALOG_PATH = Path("config/skills_catalog.json")
JOB_ROLES_DIR = Path("config/job_roles")
DEFAULT_JD_FILENAME = "job_skills.json"


@dataclass(frozen=True)
class JobDescription:
    name: str
    version: int
    job_id: str
    skills_required: List[str]
    skills_optional: List[str]
    activity: Dict[str, Any]
    scoring: Dict[str, Any]

    @staticmethod
    def load_json(path_or_job_id: str | Path) -> "JobDescription":
        """
        Accepts either:
        - a file path to a Job description json, OR
        - a job_id like "org-12345" which resolves to:
          config/job_roles/<job_id>/job_skills.json
        """
        p = JobDescription._resolve_job_path(path_or_job_id)

        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)

        version = int(data.get("version", 1))

        job_id = str(data.get("job_id", "")).strip()
        if not job_id:
            # If the file didn't include job_id, infer it from directory name
            job_id = p.parent.name

        jd = JobDescription(
            name=str(data["name"]),
            version=version,
            job_id=job_id,
            skills_required=[
                str(s).strip()
                for s in data.get("skills_required", [])
                if str(s).strip()
            ],
            skills_optional=[
                str(s).strip()
                for s in data.get("skills_optional", [])
                if str(s).strip()
            ],
            activity=dict(data.get("activity", {})),
            scoring=dict(data.get("scoring", {})),
        )

        JobDescription._validate_against_skills_catalog(jd)
        return jd

    @staticmethod
    def _resolve_job_path(path_or_job_id: str | Path) -> Path:
        """
        Resolve a Job Description JSON file path.

        Accepts either:
        - a direct file path to a JD JSON file, or
        - a job_id (e.g. "org-12345"), which is resolved to:
        config/job_roles/<job_id>/job_skills.json

        Raises:
            ValueError: if the input is empty
            FileNotFoundError: if the resolved JD file does not exist
        """
        raw = Path(path_or_job_id)

        # If it's an existing file path, use it.
        if raw.exists() and raw.is_file():
            return raw

        # Otherwise treat it as a job_id and resolve to convention path.
        job_id = str(path_or_job_id).strip()
        if not job_id:
            raise ValueError("job_id/path is empty")

        p = JOB_ROLES_DIR / job_id / DEFAULT_JD_FILENAME
        if not p.exists():
            raise FileNotFoundError(
                f"Could not find JD file for job_id='{job_id}'. Expected: {p}"
            )
        return p

    @staticmethod
    def _load_known_skills(catalog_path: Path = SKILLS_CATALOG_PATH) -> Set[str]:
        """
        Load the set of valid skill names from the skills catalog.

        Returns a set of skill identifiers defined under the `skills` key
        in the catalog JSON.

        Raises:
            ValueError: if the catalog format is invalid
        """
        data = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
        skills = data.get("skills")
        if not isinstance(skills, dict):
            raise ValueError(
                f"Invalid skills catalog format: {catalog_path} (missing 'skills' dict)"
            )
        return set(skills.keys())

    @staticmethod
    def _validate_against_skills_catalog(jd: "JobDescription") -> None:
        """
        Validate that all skills referenced by the Job Description
        exist in the skills catalog.

        Raises:
            ValueError: if the JD references unknown skills
        """
        known = JobDescription._load_known_skills()
        unknown = sorted(set(jd.skills_required + jd.skills_optional) - known)

        if unknown:
            raise ValueError(
                "Invalid Job Description config. Unknown skills referenced: "
                f"{unknown}. Valid skills are: {sorted(known)}"
            )
