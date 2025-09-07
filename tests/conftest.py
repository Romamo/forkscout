"""Pytest configuration and fixtures for the test suite."""

import pytest


@pytest.fixture
def commit_url():
    """Provide a sample GitHub commit URL for testing."""
    return "https://github.com/octocat/Hello-World/commit/7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"