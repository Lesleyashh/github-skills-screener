from unittest.mock import patch, Mock
import pytest
import requests

from github_api_app.client import GitHubAPIClient, GitHubAPIError, GitHubUser, GitHubRepository


class TestMakeRequest:
    @patch("requests.Session.get")
    def test_successful_request(self, mock_get, api_client):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_get.return_value = mock_response

        res = api_client._make_request("/test")

        assert res == {"ok": True}
        mock_get.assert_called_once_with(
            "https://api.github.com/test",
            params=None,
            timeout=20,
        )

    @patch("requests.Session.get")
    def test_network_error(self, mock_get, api_client):
        mock_get.side_effect = requests.RequestException("boom")
        with pytest.raises(GitHubAPIError) as exc:
            api_client._make_request("/test")
        assert "network error" in exc.value.message.lower()


class TestGetUser:
    @patch.object(GitHubAPIClient, "_make_request")
    def test_get_user_success(self, mock_request, api_client, sample_user_data):
        mock_request.return_value = sample_user_data
        user = api_client.get_user("octocat")
        assert isinstance(user, GitHubUser)
        assert user.login == "octocat"
        assert user.id == 583231

    @patch.object(GitHubAPIClient, "_make_request")
    def test_get_user_missing_fields(self, mock_request, api_client):
        mock_request.return_value = {"login": "x"}  # missing id, etc
        with pytest.raises(GitHubAPIError):
            api_client.get_user("x")


class TestGetRepos:
    @patch.object(GitHubAPIClient, "_make_request")
    def test_get_user_repositories_success(self, mock_request, api_client, sample_repos_data):
        mock_request.return_value = sample_repos_data
        repos = api_client.get_user_repositories("octocat")
        assert len(repos) == 1
        assert isinstance(repos[0], GitHubRepository)

    @patch.object(GitHubAPIClient, "_make_request")
    def test_per_page_capped_at_100(self, mock_request, api_client):
        mock_request.return_value = []
        api_client.get_user_repositories("octocat", per_page=1000)
        mock_request.assert_called_once_with(
            "/users/octocat/repos",
            params={"per_page": 100, "sort": "updated"},
        )