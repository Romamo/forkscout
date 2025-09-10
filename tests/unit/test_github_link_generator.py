"""Tests for GitHub link generation utilities."""

import pytest

from forkscout.analysis.github_link_generator import GitHubLinkGenerator


class TestGitHubLinkGenerator:
    """Test cases for GitHubLinkGenerator class."""

    def test_generate_commit_url_valid_inputs(self):
        """Test generating commit URLs with valid inputs."""
        # Test with full SHA
        url = GitHubLinkGenerator.generate_commit_url(
            "octocat", "Hello-World", "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
        )
        expected = "https://github.com/octocat/Hello-World/commit/7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
        assert url == expected

        # Test with abbreviated SHA
        url = GitHubLinkGenerator.generate_commit_url(
            "user", "repo", "abc123"
        )
        expected = "https://github.com/user/repo/commit/abc123"
        assert url == expected

        # Test with mixed case SHA
        url = GitHubLinkGenerator.generate_commit_url(
            "owner", "project", "AbC123DeF"
        )
        expected = "https://github.com/owner/project/commit/AbC123DeF"
        assert url == expected

    def test_generate_commit_url_with_special_characters(self):
        """Test generating URLs with valid special characters in names."""
        # Test with dots and hyphens
        url = GitHubLinkGenerator.generate_commit_url(
            "user.name", "repo-name", "abc123"
        )
        expected = "https://github.com/user.name/repo-name/commit/abc123"
        assert url == expected

        # Test with underscores
        url = GitHubLinkGenerator.generate_commit_url(
            "user_name", "repo_name", "def456"
        )
        expected = "https://github.com/user_name/repo_name/commit/def456"
        assert url == expected

    def test_generate_commit_url_empty_parameters(self):
        """Test error handling for empty parameters."""
        with pytest.raises(ValueError, match="Owner cannot be empty"):
            GitHubLinkGenerator.generate_commit_url("", "repo", "abc123")

        with pytest.raises(ValueError, match="Owner cannot be empty"):
            GitHubLinkGenerator.generate_commit_url("   ", "repo", "abc123")

        with pytest.raises(ValueError, match="Repository name cannot be empty"):
            GitHubLinkGenerator.generate_commit_url("owner", "", "abc123")

        with pytest.raises(ValueError, match="Repository name cannot be empty"):
            GitHubLinkGenerator.generate_commit_url("owner", "   ", "abc123")

        with pytest.raises(ValueError, match="Commit SHA cannot be empty"):
            GitHubLinkGenerator.generate_commit_url("owner", "repo", "")

        with pytest.raises(ValueError, match="Commit SHA cannot be empty"):
            GitHubLinkGenerator.generate_commit_url("owner", "repo", "   ")

    def test_generate_commit_url_invalid_sha(self):
        """Test error handling for invalid SHA formats."""
        with pytest.raises(ValueError, match="Invalid commit SHA format"):
            GitHubLinkGenerator.generate_commit_url("owner", "repo", "invalid-sha!")

        with pytest.raises(ValueError, match="Invalid commit SHA format"):
            GitHubLinkGenerator.generate_commit_url("owner", "repo", "sha with spaces")

        with pytest.raises(ValueError, match="Invalid commit SHA format"):
            GitHubLinkGenerator.generate_commit_url("owner", "repo", "sha@special")

    def test_generate_commit_url_invalid_names(self):
        """Test error handling for invalid owner/repo names."""
        with pytest.raises(ValueError, match="Invalid owner name"):
            GitHubLinkGenerator.generate_commit_url("owner@invalid", "repo", "abc123")

        with pytest.raises(ValueError, match="Invalid owner name"):
            GitHubLinkGenerator.generate_commit_url("owner with spaces", "repo", "abc123")

        with pytest.raises(ValueError, match="Invalid repository name"):
            GitHubLinkGenerator.generate_commit_url("owner", "repo@invalid", "abc123")

        with pytest.raises(ValueError, match="Invalid repository name"):
            GitHubLinkGenerator.generate_commit_url("owner", "repo with spaces", "abc123")

    def test_validate_github_url_valid_urls(self):
        """Test validation of valid GitHub URLs."""
        valid_urls = [
            "https://github.com/octocat/Hello-World",
            "http://github.com/user/repo",
            "https://github.com/user/repo/issues",
            "https://github.com/user/repo/commit/abc123",
            "https://github.com/user.name/repo-name",
            "https://github.com/user_name/repo_name/pull/123",
        ]

        for url in valid_urls:
            assert GitHubLinkGenerator.validate_github_url(url), f"Should be valid: {url}"

    def test_validate_github_url_invalid_urls(self):
        """Test validation of invalid GitHub URLs."""
        invalid_urls = [
            "",
            "   ",
            "not-a-url",
            "https://gitlab.com/user/repo",
            "https://github.com",
            "https://github.com/",
            "https://github.com/user",
            "ftp://github.com/user/repo",
            "https://api.github.com/user/repo",
        ]

        for url in invalid_urls:
            assert not GitHubLinkGenerator.validate_github_url(url), f"Should be invalid: {url}"

    def test_validate_commit_url_valid_urls(self):
        """Test validation of valid GitHub commit URLs."""
        valid_commit_urls = [
            "https://github.com/octocat/Hello-World/commit/7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
            "http://github.com/user/repo/commit/abc123",
            "https://github.com/user.name/repo-name/commit/DeF456",
            "https://github.com/user_name/repo_name/commit/123ABC",
        ]

        for url in valid_commit_urls:
            assert GitHubLinkGenerator.validate_commit_url(url), f"Should be valid commit URL: {url}"

    def test_validate_commit_url_invalid_urls(self):
        """Test validation of invalid GitHub commit URLs."""
        invalid_commit_urls = [
            "",
            "https://github.com/user/repo",
            "https://github.com/user/repo/issues/123",
            "https://github.com/user/repo/commit",
            "https://github.com/user/repo/commit/",
            "https://github.com/user/repo/commit/invalid-sha!",
            "https://gitlab.com/user/repo/commit/abc123",
            "https://github.com/user/repo/commits/abc123",  # Wrong path
        ]

        for url in invalid_commit_urls:
            assert not GitHubLinkGenerator.validate_commit_url(url), f"Should be invalid commit URL: {url}"

    def test_format_clickable_link_with_url_only(self):
        """Test formatting clickable links with URL only."""
        url = "https://github.com/user/repo/commit/abc123"
        result = GitHubLinkGenerator.format_clickable_link(url)
        expected = f"\033]8;;{url}\033\\{url}\033]8;;\033\\"
        assert result == expected

    def test_format_clickable_link_with_custom_text(self):
        """Test formatting clickable links with custom display text."""
        url = "https://github.com/user/repo/commit/abc123"
        text = "View Commit"
        result = GitHubLinkGenerator.format_clickable_link(url, text)
        expected = f"\033]8;;{url}\033\\{text}\033]8;;\033\\"
        assert result == expected

    def test_format_clickable_link_empty_url(self):
        """Test formatting clickable links with empty URL."""
        assert GitHubLinkGenerator.format_clickable_link("") == ""
        assert GitHubLinkGenerator.format_clickable_link("   ") == ""

    def test_extract_repo_info_from_url_valid_urls(self):
        """Test extracting repository information from valid URLs."""
        test_cases = [
            ("https://github.com/octocat/Hello-World", ("octocat", "Hello-World")),
            ("http://github.com/user/repo", ("user", "repo")),
            ("https://github.com/user/repo/issues", ("user", "repo")),
            ("https://github.com/user/repo/commit/abc123", ("user", "repo")),
            ("https://github.com/user.name/repo-name", ("user.name", "repo-name")),
            ("https://github.com/user_name/repo_name/pull/123", ("user_name", "repo_name")),
        ]

        for url, expected in test_cases:
            result = GitHubLinkGenerator.extract_repo_info_from_url(url)
            assert result == expected, f"Failed for URL: {url}"

    def test_extract_repo_info_from_url_invalid_urls(self):
        """Test extracting repository information from invalid URLs."""
        invalid_urls = [
            "",
            "not-a-url",
            "https://gitlab.com/user/repo",
            "https://github.com",
            "https://github.com/",
            "https://github.com/user",
        ]

        for url in invalid_urls:
            result = GitHubLinkGenerator.extract_repo_info_from_url(url)
            assert result is None, f"Should return None for invalid URL: {url}"

    def test_parameter_trimming(self):
        """Test that parameters are properly trimmed of whitespace."""
        url = GitHubLinkGenerator.generate_commit_url(
            "  owner  ", "  repo  ", "  abc123  "
        )
        expected = "https://github.com/owner/repo/commit/abc123"
        assert url == expected
