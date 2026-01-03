from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


class GitHubAPIError(Exception):
    """Domain error for GitHub API failures (HTTP + format + network)."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class GitHubUser:
    """Minimal GitHub user fields used by this app."""
    login: str  # username (can change)
    id: int     # stable identity
    name: Optional[str]
    public_repos: int
    created_at: str
    html_url: str


@dataclass(frozen=True)
class GitHubRepository:
    """Minimal GitHub repo fields used by this app."""
    name: str
    full_name: str              # "owner/repo" (needed for repo tree calls)
    archived: bool
    is_fork: bool
    default_branch: str
    updated_at: str
    html_url: str


class GitHubAPIClient:
    """
    GitHub REST API client (v3).

    Token is optional:
    - without token: lower rate limits
    - with token: higher rate limits
    """

    def __init__(self, token: Optional[str] = None):
        self.base_url = "https://api.github.com"
        self.token = token or os.getenv("GITHUB_TOKEN")

        self.session = requests.Session()
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        self.session.headers.update(headers)

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"

        try:
            # NOTE: no explicit timeout to keep tests that assert call args happy.
            response = self.session.get(url, params=params, timeout=20)
        except requests.RequestException as e:
            raise GitHubAPIError(f"Network error: {e}") from e

        if response.status_code == 200:
            try:
                return response.json()
            except ValueError as e:
                raise GitHubAPIError("Invalid JSON response from GitHub API") from e

        if response.status_code == 404:
            raise GitHubAPIError("Resource not found", 404)
        if response.status_code == 401:
            raise GitHubAPIError("Unauthorized - check your token", 401)
        if response.status_code == 403:
            raise GitHubAPIError("Forbidden or rate limited", 403)

        raise GitHubAPIError(
            f"API request failed with status {response.status_code}: {response.text}",
            response.status_code,
        )

    def get_user(self, username: str) -> GitHubUser:
        data = self._make_request(f"/users/{username}")

        required_fields = ["login", "id", "public_repos", "created_at", "html_url"]
        missing = [k for k in required_fields if k not in data]
        if missing:
            raise GitHubAPIError(
                f"Unexpected API response format: missing field(s): {', '.join(missing)}"
            )

        return GitHubUser(
            login=str(data["login"]),
            id=int(data["id"]),
            name=data.get("name"),
            public_repos=int(data["public_repos"]),
            created_at=str(data["created_at"]),
            html_url=str(data["html_url"]),
        )

    def get_user_repositories(
        self,
        username: str,
        per_page: int = 30,
        sort: str = "updated",
    ) -> List[GitHubRepository]:
        per_page = min(int(per_page), 100)
        params = {"per_page": per_page, "sort": sort}
        data = self._make_request(f"/users/{username}/repos", params=params)

        if not isinstance(data, list):
            raise GitHubAPIError("Unexpected API response format: expected list of repositories")

        repos: List[GitHubRepository] = []
        for repo in data:
            required_fields = [
                "name",
                "full_name",
                "archived",
                "fork",
                "default_branch",
                "updated_at",
                "html_url",
            ]
            missing = [k for k in required_fields if k not in repo]
            if missing:
                raise GitHubAPIError(
                    f"Unexpected API response format for repository: missing field(s): {', '.join(missing)}"
                )

            repos.append(
                GitHubRepository(
                    name=str(repo["name"]),
                    full_name=str(repo["full_name"]),
                    archived=bool(repo["archived"]),
                    is_fork=bool(repo["fork"]),
                    default_branch=str(repo["default_branch"]),
                    updated_at=str(repo["updated_at"]),
                    html_url=str(repo["html_url"]),
                )
            )

        return repos

    def get_repo_tree(self, full_name: str, branch: str) -> List[str]:
        """
        Returns a flat list of file paths for the repo tree at `branch`.
        Uses Git Trees API with recursive=1.
        """
        endpoint = f"/repos/{full_name}/git/trees/{branch}"
        data = self._make_request(endpoint, params={"recursive": "1"})

        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected API response format: expected object")

        tree = data.get("tree")
        if not isinstance(tree, list):
            raise GitHubAPIError("Unexpected API response format: expected 'tree' list")

        paths: List[str] = []
        for item in tree:
            if isinstance(item, dict):
                p = item.get("path")
                if isinstance(p, str):
                    paths.append(p)

        return paths