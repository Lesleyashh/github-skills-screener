import os
import pytest
from github_api_app.client import GitHubAPIClient, GitHubAPIError

pytestmark = pytest.mark.integration


@pytest.fixture(scope="class")
def client():
    token = os.getenv("GITHUB_TOKEN")
    return GitHubAPIClient(token=token)


def test_get_user_real_api(client):
    user = client.get_user("octocat")
    assert user.login == "octocat"
    assert isinstance(user.id, int)
    assert user.html_url.startswith("https://")


def test_get_nonexistent_user_real_api(client):
    with pytest.raises(GitHubAPIError) as exc:
        client.get_user("thisusershouldnotexist12345")
    assert exc.value.status_code == 404