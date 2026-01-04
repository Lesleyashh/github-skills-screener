from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Dict, List

from github_api_app.client import GitHubAPIClient, GitHubRepository

EVIDENCE_CATALOG_PATH = Path("config/skill_evidence.json")


def extract_evidence(
    client: GitHubAPIClient,
    repos: List[GitHubRepository],
    max_repos_to_scan: int = 20,
    catalog_path: Path = EVIDENCE_CATALOG_PATH,
) -> Dict[str, bool]:
    """
    Derive boolean evidence signals from public repository file trees.

    A signal is marked true if any configured file pattern matches
    any file in any scanned repository
    """
    evidence_catalog = _load_evidence_catalog(catalog_path)
    evidence_signals = evidence_catalog["evidence_signals"]

    evidence: Dict[str, bool] = {key: False for key in evidence_signals.keys()}

    scanned = 0
    for repo in repos:
        if scanned >= max_repos_to_scan:
            break

        # keep these exclusions here (consistent behavior)
        if repo.archived:
            continue

        scanned += 1

        try:
            paths = client.get_repo_tree(repo.full_name, repo.default_branch)
        except Exception:
            # don't kill the whole run because one repo tree call fails
            continue

        # normalize once
        paths_set = {p.replace("\\", "/") for p in paths}

        # apply catalog rules
        for evidence_key, spec in evidence_signals.items():
            if evidence[evidence_key]:
                continue  # already satisfied somewhere

            globs = list(spec.get("file_globs", []))
            if _matches_any(paths_set, globs):
                evidence[evidence_key] = True

    return evidence


def _load_evidence_catalog(path: Path) -> Dict[str, object]:
    """
    Load and validate the evidence catalog JSON.

    Ensures the file contains an `evidence_signals` mapping.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "evidence_signals" not in data or not isinstance(data["evidence_signals"], dict):
        raise ValueError(f"Invalid evidence catalog format: {path}")
    return data


def _matches_any(paths: set[str], globs: List[str]) -> bool:
    """
    Return True if any file path matches any of the provided glob patterns.
    """
    for g in globs:
        g = g.replace("\\", "/")
        for p in paths:
            if fnmatch.fnmatch(p, g):
                return True
    return False
