"""
Integration tests for GitHubAPIClient using the real GitHub API.

These tests require network access and optionally a GITHUB_TOKEN.
"""

import os
import pytest
from github_api_app.client import GitHubAPIClient, GitHubAPIError

pytestmark = pytest.mark.integration


@pytest.fixture(scope="class")
def client():
    """Create a GitHub API client using an optional env token."""
    token = os.getenv("GITHUB_TOKEN")
    return GitHubAPIClient(token=token)


def test_get_user_real_api(client):
    """Fetch a known public user and validate core fields."""
    user = client.get_user("octocat")
    assert user.login == "octocat"
    assert isinstance(user.id, int)
    assert user.html_url.startswith("https://")


def test_get_nonexistent_user_real_api(client):
    """Non-existent users should return a 404 GitHubAPIError."""
    with pytest.raises(GitHubAPIError) as exc:
        client.get_user("thisusershouldnotexist12345")
    assert exc.value.status_code == 404
