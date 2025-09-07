"""Contract tests for GitHub API commit counting responses."""

import pytest
import respx
import httpx
from datetime import datetime

from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient
from forklift.github.exceptions import GitHubAPIError


class TestCommitCountingContracts:
    """Contract tests to verify GitHub API response format for commit counting."""

    @pytest.fixture
    def client(self):
        """Create a GitHub client for testing."""
        config = GitHubConfig(
            token="ghp_1234567890abcdef1234567890abcdef12345678",
            base_url="https://api.github.com",
            timeout_seconds=30,
        )
        return GitHubClient(config)

    @pytest.fixture
    def expected_repository_fields(self):
        """Expected fields in GitHub repository API response."""
        return {
            # Required fields for our Repository model
            "id", "name", "full_name", "owner", "url", "html_url", "clone_url",
            "default_branch", "stargazers_count", "forks_count", "watchers_count",
            "open_issues_count", "size", "language", "description", "topics",
            "license", "private", "fork", "archived", "disabled",
            "created_at", "updated_at", "pushed_at"
        }

    @pytest.fixture
    def expected_comparison_fields(self):
        """Expected fields in GitHub comparison API response."""
        return {
            # Critical fields for commit counting
            "ahead_by", "behind_by", "total_commits", "status", "commits"
        }

    @pytest.fixture
    def expected_commit_fields(self):
        """Expected fields in GitHub commit object."""
        return {
            # Required fields for RecentCommit model
            "sha", "commit"
        }

    @pytest.fixture
    def expected_commit_detail_fields(self):
        """Expected fields in GitHub commit detail object."""
        return {
            # Required fields in commit.commit object
            "message", "author"
        }

    @pytest.mark.contract
    @pytest.mark.asyncio
    @respx.mock
    async def test_repository_api_response_contract(self, client, expected_repository_fields):
        """Test that GitHub repository API response contains expected fields."""
        # Mock a realistic GitHub repository response
        repo_response = {
            "id": 1296269,
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "owner": {
                "login": "octocat",
                "id": 1,
                "type": "User"
            },
            "url": "https://api.github.com/repos/octocat/Hello-World",
            "html_url": "https://github.com/octocat/Hello-World",
            "clone_url": "https://github.com/octocat/Hello-World.git",
            "ssh_url": "git@github.com:octocat/Hello-World.git",
            "default_branch": "master",
            "stargazers_count": 80,
            "forks_count": 9,
            "watchers_count": 80,
            "open_issues_count": 0,
            "size": 108,
            "language": "C",
            "description": "My first repository on GitHub!",
            "topics": [],
            "license": {
                "key": "mit",
                "name": "MIT License",
                "spdx_id": "MIT"
            },
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2011-01-26T19:01:12Z",
            "updated_at": "2011-01-26T19:14:43Z",
            "pushed_at": "2011-01-26T19:06:43Z"
        }

        # Mock the API call
        respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
            return_value=httpx.Response(200, json=repo_response)
        )

        async with client:
            # Make the API call through our client
            repo = await client.get_repository("octocat", "Hello-World")

            # Verify all expected fields are present in the response
            response_fields = set(repo_response.keys())
            missing_fields = expected_repository_fields - response_fields
            
            assert not missing_fields, f"GitHub repository API response missing expected fields: {missing_fields}"
            
            # Verify our model can be constructed from the response
            assert repo is not None
            assert repo.name == "Hello-World"
            assert repo.owner == "octocat"
            assert repo.full_name == "octocat/Hello-World"

    @pytest.mark.contract
    @pytest.mark.asyncio
    @respx.mock
    async def test_comparison_api_response_contract(self, client, expected_comparison_fields):
        """Test that GitHub comparison API response contains expected fields."""
        # Mock repository responses
        repo_response = {
            "id": 1296269,
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "owner": {"login": "octocat"},
            "url": "https://api.github.com/repos/octocat/Hello-World",
            "html_url": "https://github.com/octocat/Hello-World",
            "clone_url": "https://github.com/octocat/Hello-World.git",
            "default_branch": "master",
            "stargazers_count": 80,
            "forks_count": 9,
            "watchers_count": 80,
            "open_issues_count": 0,
            "size": 108,
            "language": "C",
            "description": "My first repository on GitHub!",
            "topics": [],
            "license": {"key": "mit", "name": "MIT License"},
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2011-01-26T19:01:12Z",
            "updated_at": "2011-01-26T19:14:43Z",
            "pushed_at": "2011-01-26T19:06:43Z"
        }

        # Mock a realistic GitHub comparison response
        comparison_response = {
            "ahead_by": 5,
            "behind_by": 0,
            "total_commits": 5,
            "status": "ahead",
            "commits": [
                {
                    "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
                    "commit": {
                        "message": "Fix all the bugs",
                        "author": {
                            "name": "Monalisa Octocat",
                            "email": "support@github.com",
                            "date": "2011-04-14T16:00:49Z"
                        },
                        "committer": {
                            "name": "Monalisa Octocat",
                            "email": "support@github.com",
                            "date": "2011-04-14T16:00:49Z"
                        }
                    },
                    "url": "https://api.github.com/repos/octocat/Hello-World/commits/6dcb09b5b57875f334f61aebed695e2e4193db5e",
                    "html_url": "https://github.com/octocat/Hello-World/commit/6dcb09b5b57875f334f61aebed695e2e4193db5e"
                }
            ],
            "base_commit": {
                "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
                "commit": {
                    "message": "Initial commit",
                    "author": {
                        "name": "Monalisa Octocat",
                        "email": "support@github.com",
                        "date": "2011-04-14T16:00:49Z"
                    }
                }
            },
            "merge_base_commit": {
                "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
                "commit": {
                    "message": "Initial commit",
                    "author": {
                        "name": "Monalisa Octocat",
                        "email": "support@github.com",
                        "date": "2011-04-14T16:00:49Z"
                    }
                }
            }
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/Hello-World").mock(
            return_value=httpx.Response(200, json=repo_response)
        )
        respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
            return_value=httpx.Response(200, json=repo_response)
        )
        respx.get("https://api.github.com/repos/octocat/Hello-World/compare/master...fork-owner:master").mock(
            return_value=httpx.Response(200, json=comparison_response)
        )

        async with client:
            # Test get_commits_ahead_count which uses comparison API
            count = await client.get_commits_ahead_count("fork-owner", "Hello-World", "octocat", "Hello-World")

            # Verify all expected fields are present in the comparison response
            response_fields = set(comparison_response.keys())
            missing_fields = expected_comparison_fields - response_fields
            
            assert not missing_fields, f"GitHub comparison API response missing expected fields: {missing_fields}"
            
            # Verify critical fields have expected types and values
            assert isinstance(comparison_response["ahead_by"], int)
            assert isinstance(comparison_response["behind_by"], int)
            assert isinstance(comparison_response["total_commits"], int)
            assert isinstance(comparison_response["status"], str)
            assert isinstance(comparison_response["commits"], list)
            
            # Verify our method correctly uses the ahead_by field
            assert count == comparison_response["ahead_by"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    @respx.mock
    async def test_commit_object_contract(self, client, expected_commit_fields, expected_commit_detail_fields):
        """Test that GitHub commit objects contain expected fields."""
        # Mock repository responses
        repo_response = {
            "id": 1296269,
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "owner": {"login": "octocat"},
            "url": "https://api.github.com/repos/octocat/Hello-World",
            "html_url": "https://github.com/octocat/Hello-World",
            "clone_url": "https://github.com/octocat/Hello-World.git",
            "default_branch": "master",
            "stargazers_count": 80,
            "forks_count": 9,
            "watchers_count": 80,
            "open_issues_count": 0,
            "size": 108,
            "language": "C",
            "description": "My first repository on GitHub!",
            "topics": [],
            "license": {"key": "mit", "name": "MIT License"},
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2011-01-26T19:01:12Z",
            "updated_at": "2011-01-26T19:14:43Z",
            "pushed_at": "2011-01-26T19:06:43Z"
        }

        # Mock comparison response with detailed commit objects
        comparison_response = {
            "ahead_by": 2,
            "behind_by": 0,
            "total_commits": 2,
            "status": "ahead",
            "commits": [
                {
                    "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
                    "commit": {
                        "message": "Fix all the bugs",
                        "author": {
                            "name": "Monalisa Octocat",
                            "email": "support@github.com",
                            "date": "2011-04-14T16:00:49Z"
                        },
                        "committer": {
                            "name": "Monalisa Octocat",
                            "email": "support@github.com",
                            "date": "2011-04-14T16:00:49Z"
                        },
                        "tree": {
                            "sha": "827efc6d56897b048c772eb4087f854f46256132"
                        }
                    },
                    "url": "https://api.github.com/repos/octocat/Hello-World/commits/6dcb09b5b57875f334f61aebed695e2e4193db5e",
                    "html_url": "https://github.com/octocat/Hello-World/commit/6dcb09b5b57875f334f61aebed695e2e4193db5e",
                    "author": {
                        "login": "octocat",
                        "id": 1
                    },
                    "committer": {
                        "login": "octocat",
                        "id": 1
                    }
                },
                {
                    "sha": "827efc6d56897b048c772eb4087f854f46256132",
                    "commit": {
                        "message": "Add new feature",
                        "author": {
                            "name": "Monalisa Octocat",
                            "email": "support@github.com",
                            "date": "2011-04-15T16:00:49Z"
                        },
                        "committer": {
                            "name": "Monalisa Octocat",
                            "email": "support@github.com",
                            "date": "2011-04-15T16:00:49Z"
                        }
                    }
                }
            ]
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/Hello-World").mock(
            return_value=httpx.Response(200, json=repo_response)
        )
        respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
            return_value=httpx.Response(200, json=repo_response)
        )
        respx.get("https://api.github.com/repos/octocat/Hello-World/compare/master...fork-owner:master").mock(
            return_value=httpx.Response(200, json=comparison_response)
        )

        async with client:
            # Test get_commits_ahead which returns commit details
            commits = await client.get_commits_ahead("fork-owner", "Hello-World", "octocat", "Hello-World", count=2)

            # Verify commit objects have expected structure
            assert len(commits) == 2
            
            for i, commit_data in enumerate(comparison_response["commits"]):
                # Verify top-level commit fields
                commit_fields = set(commit_data.keys())
                missing_commit_fields = expected_commit_fields - commit_fields
                assert not missing_commit_fields, f"Commit object missing expected fields: {missing_commit_fields}"
                
                # Verify commit detail fields
                commit_detail_fields = set(commit_data["commit"].keys())
                missing_detail_fields = expected_commit_detail_fields - commit_detail_fields
                assert not missing_detail_fields, f"Commit detail object missing expected fields: {missing_detail_fields}"
                
                # Verify field types
                assert isinstance(commit_data["sha"], str)
                assert isinstance(commit_data["commit"]["message"], str)
                assert isinstance(commit_data["commit"]["author"], dict)
                assert "date" in commit_data["commit"]["author"]
                
                # Verify our RecentCommit model can be constructed
                recent_commit = commits[i]
                assert recent_commit.short_sha == commit_data["sha"][:7]
                assert recent_commit.message == commit_data["commit"]["message"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    @respx.mock
    async def test_ahead_by_field_presence_and_type(self, client):
        """Test that ahead_by field is always present and has correct type."""
        repo_response = {
            "id": 1296269,
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "owner": {"login": "octocat"},
            "url": "https://api.github.com/repos/octocat/Hello-World",
            "html_url": "https://github.com/octocat/Hello-World",
            "clone_url": "https://github.com/octocat/Hello-World.git",
            "default_branch": "master",
            "stargazers_count": 80,
            "forks_count": 9,
            "watchers_count": 80,
            "open_issues_count": 0,
            "size": 108,
            "language": "C",
            "description": "My first repository on GitHub!",
            "topics": [],
            "license": {"key": "mit", "name": "MIT License"},
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2011-01-26T19:01:12Z",
            "updated_at": "2011-01-26T19:14:43Z",
            "pushed_at": "2011-01-26T19:06:43Z"
        }

        # Test various ahead_by scenarios
        test_scenarios = [
            {"ahead_by": 0, "status": "identical"},
            {"ahead_by": 1, "status": "ahead"},
            {"ahead_by": 50, "status": "ahead"},
            {"ahead_by": 250, "status": "ahead"},  # GitHub API limit
            {"ahead_by": 1000, "status": "ahead"},  # Large count
        ]

        async with client:
            for scenario in test_scenarios:
                comparison_response = {
                    "ahead_by": scenario["ahead_by"],
                    "behind_by": 0,
                    "total_commits": scenario["ahead_by"],
                    "status": scenario["status"],
                    "commits": []
                }

                # Mock API calls
                respx.get("https://api.github.com/repos/fork-owner/Hello-World").mock(
                    return_value=httpx.Response(200, json=repo_response)
                )
                respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
                    return_value=httpx.Response(200, json=repo_response)
                )
                respx.get("https://api.github.com/repos/octocat/Hello-World/compare/master...fork-owner:master").mock(
                    return_value=httpx.Response(200, json=comparison_response)
                )

                count = await client.get_commits_ahead_count("fork-owner", "Hello-World", "octocat", "Hello-World")

                # Verify ahead_by field contract
                assert "ahead_by" in comparison_response, "ahead_by field must be present in comparison response"
                assert isinstance(comparison_response["ahead_by"], int), "ahead_by must be an integer"
                assert comparison_response["ahead_by"] >= 0, "ahead_by must be non-negative"
                assert count == scenario["ahead_by"], f"Expected count {scenario['ahead_by']}, got {count}"

    @pytest.mark.contract
    @pytest.mark.asyncio
    @respx.mock
    async def test_comparison_status_field_contract(self, client):
        """Test that comparison status field has expected values."""
        repo_response = {
            "id": 1296269,
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "owner": {"login": "octocat"},
            "url": "https://api.github.com/repos/octocat/Hello-World",
            "html_url": "https://github.com/octocat/Hello-World",
            "clone_url": "https://github.com/octocat/Hello-World.git",
            "default_branch": "master",
            "stargazers_count": 80,
            "forks_count": 9,
            "watchers_count": 80,
            "open_issues_count": 0,
            "size": 108,
            "language": "C",
            "description": "My first repository on GitHub!",
            "topics": [],
            "license": {"key": "mit", "name": "MIT License"},
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2011-01-26T19:01:12Z",
            "updated_at": "2011-01-26T19:14:43Z",
            "pushed_at": "2011-01-26T19:06:43Z"
        }

        # Test expected status values
        valid_statuses = ["identical", "ahead", "behind", "diverged"]
        
        async with client:
            for status in valid_statuses:
                comparison_response = {
                    "ahead_by": 5 if status == "ahead" else 0,
                    "behind_by": 5 if status == "behind" else 0,
                    "total_commits": 5,
                    "status": status,
                    "commits": []
                }

                # Mock API calls
                respx.get("https://api.github.com/repos/fork-owner/Hello-World").mock(
                    return_value=httpx.Response(200, json=repo_response)
                )
                respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
                    return_value=httpx.Response(200, json=repo_response)
                )
                respx.get("https://api.github.com/repos/octocat/Hello-World/compare/master...fork-owner:master").mock(
                    return_value=httpx.Response(200, json=comparison_response)
                )

                count = await client.get_commits_ahead_count("fork-owner", "Hello-World", "octocat", "Hello-World")

                # Verify status field contract
                assert comparison_response["status"] in valid_statuses, f"Invalid status: {comparison_response['status']}"
                assert isinstance(comparison_response["status"], str), "Status must be a string"

    @pytest.mark.contract
    @pytest.mark.asyncio
    @respx.mock
    async def test_commits_array_structure_contract(self, client):
        """Test that commits array has expected structure."""
        repo_response = {
            "id": 1296269,
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "owner": {"login": "octocat"},
            "url": "https://api.github.com/repos/octocat/Hello-World",
            "html_url": "https://github.com/octocat/Hello-World",
            "clone_url": "https://github.com/octocat/Hello-World.git",
            "default_branch": "master",
            "stargazers_count": 80,
            "forks_count": 9,
            "watchers_count": 80,
            "open_issues_count": 0,
            "size": 108,
            "language": "C",
            "description": "My first repository on GitHub!",
            "topics": [],
            "license": {"key": "mit", "name": "MIT License"},
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2011-01-26T19:01:12Z",
            "updated_at": "2011-01-26T19:14:43Z",
            "pushed_at": "2011-01-26T19:06:43Z"
        }

        # Test with different commit array sizes
        test_cases = [
            {"ahead_by": 0, "commits_count": 0},  # No commits
            {"ahead_by": 1, "commits_count": 1},  # Single commit
            {"ahead_by": 10, "commits_count": 10},  # Multiple commits
            {"ahead_by": 250, "commits_count": 250},  # GitHub API limit
        ]

        async with client:
            for case in test_cases:
                commits_array = [
                    {
                        "sha": f"6dcb09b5b57875f334f61aebed695e2e4193db{i:02d}",
                        "commit": {
                            "message": f"Commit {i}",
                            "author": {
                                "name": "Test Author",
                                "email": "test@example.com",
                                "date": "2011-04-14T16:00:49Z"
                            }
                        }
                    }
                    for i in range(case["commits_count"])
                ]

                comparison_response = {
                    "ahead_by": case["ahead_by"],
                    "behind_by": 0,
                    "total_commits": case["ahead_by"],
                    "status": "ahead" if case["ahead_by"] > 0 else "identical",
                    "commits": commits_array
                }

                # Mock API calls
                respx.get("https://api.github.com/repos/fork-owner/Hello-World").mock(
                    return_value=httpx.Response(200, json=repo_response)
                )
                respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
                    return_value=httpx.Response(200, json=repo_response)
                )
                respx.get("https://api.github.com/repos/octocat/Hello-World/compare/master...fork-owner:master").mock(
                    return_value=httpx.Response(200, json=comparison_response)
                )

                count = await client.get_commits_ahead_count("fork-owner", "Hello-World", "octocat", "Hello-World")

                # Verify commits array contract
                assert isinstance(comparison_response["commits"], list), "Commits must be an array"
                assert len(comparison_response["commits"]) == case["commits_count"], f"Expected {case['commits_count']} commits in array"
                
                # Verify each commit has required structure
                for commit in comparison_response["commits"]:
                    assert "sha" in commit, "Each commit must have sha field"
                    assert "commit" in commit, "Each commit must have commit field"
                    assert isinstance(commit["sha"], str), "SHA must be a string"
                    assert len(commit["sha"]) >= 7, "SHA must be at least 7 characters"
                    assert isinstance(commit["commit"], dict), "Commit detail must be an object"
                    assert "message" in commit["commit"], "Commit must have message"
                    assert "author" in commit["commit"], "Commit must have author"

                # Verify our count method uses ahead_by, not len(commits)
                assert count == case["ahead_by"], f"Count should use ahead_by ({case['ahead_by']}), not len(commits) ({len(commits_array)})"

    @pytest.mark.contract
    @pytest.mark.asyncio
    @respx.mock
    async def test_error_response_contract(self, client):
        """Test that GitHub API error responses have expected structure."""
        from tests.utils.test_helpers import mock_rate_limiter
        
        async with mock_rate_limiter(client):
            # Test 404 Not Found
            error_404 = {
                "message": "Not Found",
                "documentation_url": "https://docs.github.com/rest/reference/repos#get-a-repository"
            }

            respx.get("https://api.github.com/repos/nonexistent/repo").mock(
                return_value=httpx.Response(404, json=error_404)
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get_repository("nonexistent", "repo")
            
            # Verify error handling works with GitHub's error format
            assert "not found" in str(exc_info.value).lower() or "private" in str(exc_info.value).lower()

            # Test 403 Rate Limited
            error_403 = {
                "message": "API rate limit exceeded",
                "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting"
            }

            respx.get("https://api.github.com/repos/rate-limited/repo").mock(
                return_value=httpx.Response(403, json=error_403)
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get_repository("rate-limited", "repo")
            
            # Verify rate limit error handling
            assert "rate limit" in str(exc_info.value).lower()

    @pytest.mark.contract
    @pytest.mark.asyncio
    @respx.mock
    async def test_api_version_header_contract(self, client):
        """Test that our client sends the expected API version header."""
        repo_response = {
            "id": 1296269,
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "owner": {"login": "octocat"},
            "url": "https://api.github.com/repos/octocat/Hello-World",
            "html_url": "https://github.com/octocat/Hello-World",
            "clone_url": "https://github.com/octocat/Hello-World.git",
            "default_branch": "master",
            "stargazers_count": 80,
            "forks_count": 9,
            "watchers_count": 80,
            "open_issues_count": 0,
            "size": 108,
            "language": "C",
            "description": "My first repository on GitHub!",
            "topics": [],
            "license": {"key": "mit", "name": "MIT License"},
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2011-01-26T19:01:12Z",
            "updated_at": "2011-01-26T19:14:43Z",
            "pushed_at": "2011-01-26T19:06:43Z"
        }

        # Capture request headers
        captured_headers = {}
        
        def capture_request(request):
            captured_headers.update(request.headers)
            return httpx.Response(200, json=repo_response)

        respx.get("https://api.github.com/repos/octocat/Hello-World").mock(side_effect=capture_request)

        async with client:
            await client.get_repository("octocat", "Hello-World")

            # Verify required headers are sent (case-insensitive check)
            header_keys = [k.lower() for k in captured_headers.keys()]
            assert "accept" in header_keys, "Accept header must be sent"
            assert "user-agent" in header_keys, "User-Agent header must be sent"
            
            # Check Accept header value
            accept_header = next((v for k, v in captured_headers.items() if k.lower() == "accept"), "")
            assert "application/vnd.github+json" in accept_header, "Accept header must specify GitHub JSON format"
            
            # Check User-Agent header value
            user_agent_header = next((v for k, v in captured_headers.items() if k.lower() == "user-agent"), "")
            assert "Forklift" in user_agent_header, "User-Agent must identify our application"

    @pytest.mark.contract
    @pytest.mark.asyncio
    @respx.mock
    async def test_pagination_contract(self, client):
        """Test GitHub API pagination contract for large commit lists."""
        repo_response = {
            "id": 1296269,
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "owner": {"login": "octocat"},
            "url": "https://api.github.com/repos/octocat/Hello-World",
            "html_url": "https://github.com/octocat/Hello-World",
            "clone_url": "https://github.com/octocat/Hello-World.git",
            "default_branch": "master",
            "stargazers_count": 80,
            "forks_count": 9,
            "watchers_count": 80,
            "open_issues_count": 0,
            "size": 108,
            "language": "C",
            "description": "My first repository on GitHub!",
            "topics": [],
            "license": {"key": "mit", "name": "MIT License"},
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2011-01-26T19:01:12Z",
            "updated_at": "2011-01-26T19:14:43Z",
            "pushed_at": "2011-01-26T19:06:43Z"
        }

        # Test with large ahead_by count that exceeds GitHub's commit limit
        comparison_response = {
            "ahead_by": 500,  # Large count
            "behind_by": 0,
            "total_commits": 500,
            "status": "ahead",
            "commits": [  # GitHub API only returns up to 250 commits
                {
                    "sha": f"6dcb09b5b57875f334f61aebed695e2e4193db{i:02d}",
                    "commit": {
                        "message": f"Commit {i}",
                        "author": {
                            "name": "Test Author",
                            "email": "test@example.com",
                            "date": "2011-04-14T16:00:49Z"
                        }
                    }
                }
                for i in range(250)  # GitHub's limit
            ]
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/Hello-World").mock(
            return_value=httpx.Response(200, json=repo_response)
        )
        respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
            return_value=httpx.Response(200, json=repo_response)
        )
        respx.get("https://api.github.com/repos/octocat/Hello-World/compare/master...fork-owner:master").mock(
            return_value=httpx.Response(200, json=comparison_response)
        )

        async with client:
            count = await client.get_commits_ahead_count("fork-owner", "Hello-World", "octocat", "Hello-World")

            # Verify pagination contract
            assert count == 500, "Count should use ahead_by field, not limited commits array"
            assert len(comparison_response["commits"]) == 250, "GitHub API should limit commits array to 250"
            
            # Verify our implementation handles this correctly
            # The count should be from ahead_by (500), not len(commits) (250)
            assert count != len(comparison_response["commits"]), "Count should not be limited by commits array size"