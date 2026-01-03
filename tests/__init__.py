"""
Test suite for the GitHub API Client

Comprehensive unit and integration tests for the GitHub API interview app.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from github_api_app.client import (
    GitHubAPIClient, GitHubAPIError, GitHubUser, GitHubRepository
)