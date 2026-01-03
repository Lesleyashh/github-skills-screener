import pytest
from github_api_app.client import GitHubAPIClient


@pytest.fixture
def api_client():
    return GitHubAPIClient(token="test_token")


@pytest.fixture
def sample_user_data():
    return {
        "login": "octocat",
        "id": 583231,
        "name": "The Octocat",
        "public_repos": 8,
        "created_at": "2011-01-25T18:44:36Z",
        "avatar_url": "https://github.com/images/error/octocat_happy.gif",
        "html_url": "https://github.com/octocat",
    }


@pytest.fixture
def sample_repos_data():
    return [
        {
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "archived": False,
            "fork": False,
            "default_branch": "main",
            "updated_at": "2023-01-01T12:00:00Z",
            "html_url": "https://github.com/octocat/Hello-World",
        }
    ]