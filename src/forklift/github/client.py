"""GitHub API client implementation."""

import asyncio
import contextlib
import logging
import time
from typing import Any

import httpx

from forklift.config import GitHubConfig
from forklift.models.github import Commit, Fork, RecentCommit, Repository, User

from .error_handler import EnhancedErrorHandler
from .exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from .rate_limiter import CircuitBreaker, RateLimitHandler

logger = logging.getLogger(__name__)


class GitHubClient:
    """Async GitHub API client with authentication and error handling."""

    def __init__(
        self,
        config: GitHubConfig,
        rate_limit_handler: RateLimitHandler | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        error_handler: EnhancedErrorHandler | None = None,
    ):
        """Initialize GitHub client with configuration."""
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._headers = self._build_headers()

        # Initialize rate limiting, circuit breaker, and error handling
        self.rate_limit_handler = rate_limit_handler or RateLimitHandler()
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=5,
            timeout=60.0,
            expected_exception=GitHubAPIError,
        )
        self.error_handler = error_handler or EnhancedErrorHandler(
            timeout_seconds=config.timeout_seconds
        )

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Forklift/1.0.0 (GitHub Fork Analysis Tool)",
        }

        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"

        return headers

    async def __aenter__(self) -> "GitHubClient":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            timeout = httpx.Timeout(self.config.timeout_seconds)
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=self._headers,
                timeout=timeout,
                follow_redirects=True,
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to the GitHub API with retry logic."""
        operation_name = f"{method} {endpoint}"

        async def make_request() -> dict[str, Any]:
            """Inner function to make the actual request."""
            await self._ensure_client()

            url = endpoint if endpoint.startswith("http") else f"/{endpoint.lstrip('/')}"

            try:
                logger.debug(f"Making {method} request to {url}")
                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                )

                # Handle rate limiting with improved detection
                if response.status_code == 403:
                    # Log all response headers for debugging rate limit issues
                    logger.debug(f"403 Forbidden response headers: {dict(response.headers)}")
                    
                    rate_limit_remaining = response.headers.get("x-ratelimit-remaining")
                    rate_limit_reset = response.headers.get("x-ratelimit-reset")
                    rate_limit_limit = response.headers.get("x-ratelimit-limit")
                    
                    # Log rate limit header values for debugging
                    logger.debug(f"Rate limit headers - remaining: {rate_limit_remaining}, reset: {rate_limit_reset}, limit: {rate_limit_limit}")
                    
                    # Enhanced rate limit detection
                    is_rate_limited = self._is_rate_limit_error(response, rate_limit_remaining)
                    
                    if is_rate_limited:
                        reset_time = int(rate_limit_reset) if rate_limit_reset and rate_limit_reset != "0" else 0
                        limit = int(rate_limit_limit) if rate_limit_limit else 0
                        remaining = int(rate_limit_remaining) if rate_limit_remaining else 0
                        
                        logger.info(f"GitHub API rate limit detected - reset_time: {reset_time}, remaining: {remaining}, limit: {limit}")
                        
                        raise GitHubRateLimitError(
                            "GitHub API rate limit exceeded",
                            reset_time=reset_time,
                            remaining=remaining,
                            limit=limit,
                            status_code=response.status_code,
                        )
                    else:
                        # This is a 403 but not a rate limit - likely authentication/authorization issue
                        logger.warning(f"403 Forbidden but not rate limited - likely auth/permission issue")
                        # Fall through to handle as authentication error below

                # Handle authentication errors (non-retryable)
                if response.status_code == 401:
                    raise GitHubAuthenticationError(
                        "GitHub API authentication failed. Check your token.",
                        status_code=response.status_code,
                    )

                # Handle not found errors (non-retryable)
                if response.status_code == 404:
                    raise GitHubNotFoundError(
                        "GitHub resource not found",
                        status_code=response.status_code,
                    )

                # Handle other client errors (mostly non-retryable)
                if 400 <= response.status_code < 500:
                    error_data = {}
                    with contextlib.suppress(Exception):
                        error_data = response.json()

                    # Some 4xx errors might be retryable (e.g., 429 Too Many Requests)
                    if response.status_code == 429:
                        # This is a rate limit error that might not have the standard headers
                        retry_after = response.headers.get("retry-after")
                        reset_time = None
                        if retry_after:
                            try:
                                reset_time = int(time.time()) + int(retry_after)
                            except ValueError:
                                pass

                        raise GitHubRateLimitError(
                            "GitHub API rate limit exceeded (429)",
                            reset_time=reset_time,
                            remaining=0,
                            limit=None,
                            status_code=response.status_code,
                        )

                    raise GitHubAPIError(
                        f"GitHub API client error: {response.status_code}",
                        status_code=response.status_code,
                        response_data=error_data,
                    )

                # Handle server errors (retryable)
                if response.status_code >= 500:
                    raise GitHubAPIError(
                        f"GitHub API server error: {response.status_code}",
                        status_code=response.status_code,
                    )

                # Ensure we got a successful response
                response.raise_for_status()

                # Parse JSON response
                try:
                    return response.json()
                except Exception as e:
                    raise GitHubAPIError(f"Failed to parse JSON response: {e}") from e

            except httpx.TimeoutException as e:
                raise GitHubAPIError(f"Request timeout: {e}") from e
            except httpx.NetworkError as e:
                raise GitHubAPIError(f"Network error: {e}") from e
            except httpx.HTTPStatusError as e:
                raise GitHubAPIError(f"HTTP error: {e}") from e

        # Execute request with circuit breaker and retry logic
        return await self.circuit_breaker.call(
            lambda: self.rate_limit_handler.execute_with_retry(
                make_request,
                operation_name=operation_name,
                retryable_exceptions=(
                    GitHubRateLimitError,
                    httpx.TimeoutException,
                    httpx.NetworkError,
                    GitHubAPIError,  # Include GitHubAPIError for server errors
                ),
            ),
            operation_name=operation_name,
        )

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a GET request to the GitHub API."""
        return await self._request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a POST request to the GitHub API."""
        return await self._request("POST", endpoint, params=params, json_data=json_data)

    async def patch(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a PATCH request to the GitHub API."""
        return await self._request("PATCH", endpoint, params=params, json_data=json_data)

    async def delete(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a DELETE request to the GitHub API."""
        return await self._request("DELETE", endpoint, params=params)

    # Repository operations

    async def get_repository(self, owner: str, repo: str, disable_cache: bool = False) -> Repository:
        """Get repository information.

        Args:
            owner: Repository owner
            repo: Repository name
            disable_cache: Whether to bypass cache (not implemented yet)
        """
        logger.info(f"Fetching repository {owner}/{repo}")
        if disable_cache:
            logger.debug(f"Cache bypass requested for repository {owner}/{repo}")
        
        try:
            data = await self.get(f"repos/{owner}/{repo}")
            return Repository.from_github_api(data)
        except GitHubAPIError as e:
            # Convert to more specific error type
            specific_error = self.error_handler.handle_repository_access_error(e, f"{owner}/{repo}")
            raise specific_error from e

    async def get_repository_safe(self, owner: str, repo: str, disable_cache: bool = False) -> Repository | None:
        """Get repository information with safe error handling.

        Args:
            owner: Repository owner
            repo: Repository name
            disable_cache: Whether to bypass cache (not implemented yet)
            
        Returns:
            Repository object or None if repository cannot be accessed
        """
        return await self.error_handler.safe_repository_operation(
            lambda: self.get_repository(owner, repo, disable_cache),
            repository=f"{owner}/{repo}",
            operation_name="get_repository",
            default_value=None,
        )

    async def get_repository_forks(
        self,
        owner: str,
        repo: str,
        sort: str = "newest",
        per_page: int = 100,
        page: int = 1,
    ) -> list[Repository]:
        """Get repository forks."""
        logger.info(f"Fetching forks for {owner}/{repo} (page {page})")
        params = {
            "sort": sort,
            "per_page": min(per_page, 100),  # GitHub max is 100
            "page": page,
        }
        data = await self.get(f"repos/{owner}/{repo}/forks", params=params)
        return [Repository.from_github_api(fork_data) for fork_data in data]

    async def get_all_repository_forks(
        self, owner: str, repo: str, max_forks: int | None = None
    ) -> list[Repository]:
        """Get all repository forks with pagination."""
        logger.info(f"Fetching all forks for {owner}/{repo}")
        all_forks = []
        page = 1
        per_page = 100

        while True:
            forks = await self.get_repository_forks(
                owner, repo, per_page=per_page, page=page
            )

            if not forks:
                break

            all_forks.extend(forks)

            # Check if we've reached the maximum
            if max_forks and len(all_forks) >= max_forks:
                all_forks = all_forks[:max_forks]
                break

            # If we got fewer than per_page, we're done
            if len(forks) < per_page:
                break

            page += 1

        logger.info(f"Found {len(all_forks)} forks for {owner}/{repo}")
        return all_forks

    async def get_repository_commits(
        self,
        owner: str,
        repo: str,
        sha: str | None = None,
        path: str | None = None,
        author: str | None = None,
        since: str | None = None,
        until: str | None = None,
        per_page: int = 100,
        page: int = 1,
    ) -> list[Commit]:
        """Get repository commits."""
        logger.info(f"Fetching commits for {owner}/{repo}")
        params = {
            "per_page": min(per_page, 100),
            "page": page,
        }

        if sha:
            params["sha"] = sha
        if path:
            params["path"] = path
        if author:
            params["author"] = author
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        try:
            data = await self.get(f"repos/{owner}/{repo}/commits", params=params)
            return [Commit.from_github_api(commit_data) for commit_data in data]
        except GitHubAPIError as e:
            # Convert to more specific error type
            specific_error = self.error_handler.handle_commit_access_error(e, f"{owner}/{repo}")
            raise specific_error from e

    async def get_repository_commits_safe(
        self,
        owner: str,
        repo: str,
        sha: str | None = None,
        path: str | None = None,
        author: str | None = None,
        since: str | None = None,
        until: str | None = None,
        per_page: int = 100,
        page: int = 1,
    ) -> list[Commit]:
        """Get repository commits with safe error handling.
        
        Returns empty list if repository has no commits or cannot be accessed.
        """
        return await self.error_handler.safe_repository_operation(
            lambda: self.get_repository_commits(
                owner, repo, sha, path, author, since, until, per_page, page
            ),
            repository=f"{owner}/{repo}",
            operation_name="get_repository_commits",
            default_value=[],
        ) or []

    async def get_commit(self, owner: str, repo: str, sha: str) -> Commit:
        """Get detailed commit information."""
        logger.info(f"Fetching commit {sha} from {owner}/{repo}")
        data = await self.get(f"repos/{owner}/{repo}/commits/{sha}")
        return Commit.from_github_api(data)

    async def get_commit_details(self, owner: str, repo: str, sha: str) -> dict[str, Any]:
        """Get detailed commit information including diff data."""
        logger.info(f"Fetching commit details with diff for {sha} from {owner}/{repo}")
        return await self.get(f"repos/{owner}/{repo}/commits/{sha}")

    async def compare_commits(
        self, owner: str, repo: str, base: str, head: str
    ) -> dict[str, Any]:
        """Compare two commits or branches."""
        logger.info(f"Comparing {base}...{head} in {owner}/{repo}")
        return await self.get(f"repos/{owner}/{repo}/compare/{base}...{head}")

    async def get_commits_ahead(
        self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str, count: int = 10
    ) -> list[RecentCommit]:
        """Get commits that are ahead in a fork compared to its parent.
        
        Args:
            fork_owner: Fork repository owner
            fork_repo: Fork repository name
            parent_owner: Parent repository owner
            parent_repo: Parent repository name
            count: Maximum number of commits to fetch (1-10)
            
        Returns:
            List of RecentCommit objects representing commits ahead
            
        Raises:
            GitHubAPIError: If API request fails
            ValueError: If count is not between 1 and 10
        """
        if not (1 <= count <= 10):
            raise ValueError("Count must be between 1 and 10")
            
        logger.debug(f"Fetching {count} commits ahead from {fork_owner}/{fork_repo} vs {parent_owner}/{parent_repo}")
        
        try:
            # Get repository info to find default branches
            fork_info = await self.get_repository(fork_owner, fork_repo)
            parent_info = await self.get_repository(parent_owner, parent_repo)
            
            # Compare fork's default branch with parent's default branch
            comparison = await self.compare_commits(
                parent_owner,
                parent_repo,
                parent_info.default_branch,
                f"{fork_owner}:{fork_info.default_branch}",
            )
            
            if not comparison or "commits" not in comparison:
                logger.warning(f"No commits found in comparison for {fork_owner}/{fork_repo}")
                return []
            
            # Get the commits that are ahead (limited by count)
            ahead_commits = comparison["commits"][:count]
            
            # Convert to RecentCommit objects
            recent_commits = []
            for commit_data in ahead_commits:
                try:
                    recent_commit = RecentCommit.from_github_api(commit_data)
                    recent_commits.append(recent_commit)
                except Exception as e:
                    logger.warning(f"Failed to parse commit {commit_data.get('sha', 'unknown')}: {e}")
                    continue
            
            logger.debug(f"Successfully fetched {len(recent_commits)} commits ahead from {fork_owner}/{fork_repo}")
            return recent_commits
            
        except GitHubAPIError:
            # Re-raise GitHub API errors
            raise
        except Exception as e:
            logger.error(f"Failed to fetch commits ahead from {fork_owner}/{fork_repo}: {e}")
            raise GitHubAPIError(f"Failed to fetch commits ahead: {e}")

    # User operations

    async def get_user(self, username: str, disable_cache: bool = False) -> User:
        """Get user information.

        Args:
            username: GitHub username
            disable_cache: Whether to bypass cache (not implemented yet)
        """
        logger.info(f"Fetching user {username}")
        if disable_cache:
            logger.debug(f"Cache bypass requested for user {username}")
        data = await self.get(f"users/{username}")
        return User.from_github_api(data)

    async def get_authenticated_user(self) -> User:
        """Get authenticated user information."""
        logger.info("Fetching authenticated user")
        data = await self.get("user")
        return User.from_github_api(data)

    # Rate limit operations

    async def get_rate_limit(self) -> dict[str, Any]:
        """Get current rate limit status."""
        logger.debug("Fetching rate limit status")
        return await self.get("rate_limit")

    async def check_rate_limit(self) -> dict[str, int]:
        """Check rate limit and return simplified status."""
        rate_limit_data = await self.get_rate_limit()
        core_limit = rate_limit_data["rate"]

        return {
            "limit": core_limit["limit"],
            "remaining": core_limit["remaining"],
            "reset": core_limit["reset"],
            "used": core_limit["used"],
        }

    async def wait_for_rate_limit_reset(self) -> None:
        """Wait for rate limit to reset if necessary."""
        try:
            rate_limit_status = await self.check_rate_limit()
            remaining = rate_limit_status["remaining"]
            reset_time = rate_limit_status["reset"]

            if remaining <= 10:  # Conservative threshold
                current_time = time.time()
                wait_time = max(0, reset_time - current_time + 1)  # +1 second buffer

                if wait_time > 0:
                    logger.info(f"Rate limit low ({remaining} remaining), waiting {wait_time:.1f}s for reset")
                    await asyncio.sleep(wait_time)

        except Exception as e:
            logger.warning(f"Could not check rate limit status: {e}")

    def get_circuit_breaker_status(self) -> dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "state": self.circuit_breaker.state,
            "failure_count": self.circuit_breaker.failure_count,
            "last_failure_time": self.circuit_breaker.last_failure_time,
            "failure_threshold": self.circuit_breaker.failure_threshold,
            "timeout": self.circuit_breaker.timeout,
        }

    def reset_circuit_breaker(self) -> None:
        """Manually reset the circuit breaker."""
        self.circuit_breaker.failure_count = 0
        self.circuit_breaker.last_failure_time = None
        self.circuit_breaker.state = "closed"
        logger.info("Circuit breaker manually reset")

    def _is_rate_limit_error(self, response: httpx.Response, rate_limit_remaining: str | None) -> bool:
        """Enhanced rate limit error detection.
        
        Args:
            response: HTTP response object
            rate_limit_remaining: Value of x-ratelimit-remaining header
            
        Returns:
            True if this is a rate limit error, False otherwise
        """
        # Check if remaining requests is 0
        if rate_limit_remaining == "0":
            return True
        
        if rate_limit_remaining is not None:
            try:
                remaining = int(rate_limit_remaining)
                if remaining == 0:
                    return True
            except ValueError:
                pass
        
        # Check response body for rate limit indicators
        try:
            response_text = response.text.lower()
            rate_limit_indicators = [
                "rate limit",
                "api rate limit exceeded",
                "rate_limit_exceeded",
                "too many requests",
                "abuse detection",
                "secondary rate limit"
            ]
            
            for indicator in rate_limit_indicators:
                if indicator in response_text:
                    logger.debug(f"Rate limit detected via response text: '{indicator}'")
                    return True
                    
        except Exception as e:
            logger.debug(f"Could not check response text for rate limit indicators: {e}")
        
        # Check for specific GitHub rate limit response structure
        try:
            response_data = response.json()
            if isinstance(response_data, dict):
                message = response_data.get("message", "").lower()
                if "rate limit" in message or "abuse" in message:
                    logger.debug(f"Rate limit detected via JSON message: '{message}'")
                    return True
                    
                # Check for documentation_url that points to rate limiting docs
                docs_url = response_data.get("documentation_url", "")
                if "rate-limiting" in docs_url or "abuse-rate-limits" in docs_url:
                    logger.debug(f"Rate limit detected via documentation URL: '{docs_url}'")
                    return True
                    
        except Exception as e:
            logger.debug(f"Could not parse JSON response for rate limit detection: {e}")
        
        return False

    def get_user_friendly_error_message(self, error: Exception) -> str:
        """Get user-friendly error message for display.
        
        Args:
            error: Exception to convert to user-friendly message
            
        Returns:
            User-friendly error message
        """
        return self.error_handler.get_user_friendly_error_message(error)

    def should_continue_processing(self, error: Exception) -> bool:
        """Determine if processing should continue after an error.
        
        Args:
            error: Exception that occurred
            
        Returns:
            True if processing should continue, False if it should stop
        """
        return self.error_handler.should_continue_processing(error)

    # Utility methods

    async def test_authentication(self) -> bool:
        """Test if authentication is working."""
        try:
            await self.get_authenticated_user()
            return True
        except GitHubAuthenticationError:
            return False
        except Exception:
            return False

    def is_authenticated(self) -> bool:
        """Check if client has authentication token."""
        return bool(self.config.token)

    async def get_repository_languages(self, owner: str, repo: str) -> dict[str, int]:
        """Get repository programming languages."""
        logger.debug(f"Fetching languages for {owner}/{repo}")
        return await self.get(f"repos/{owner}/{repo}/languages")

    async def get_repository_topics(self, owner: str, repo: str) -> list[str]:
        """Get repository topics."""
        logger.debug(f"Fetching topics for {owner}/{repo}")
        data = await self.get(f"repos/{owner}/{repo}/topics")
        return data.get("names", [])

    async def get_repository_contributors(
        self, owner: str, repo: str, per_page: int = 100, max_count: int | None = None, disable_cache: bool = False
    ) -> list[dict[str, Any]]:
        """Get repository contributors.

        Args:
            owner: Repository owner
            repo: Repository name
            per_page: Number of contributors per page
            max_count: Maximum number of contributors to fetch
            disable_cache: Whether to bypass cache (not implemented yet)
        """
        logger.info(f"Fetching contributors for {owner}/{repo}")
        if disable_cache:
            logger.debug(f"Cache bypass requested for contributors {owner}/{repo}")

        if max_count and max_count <= per_page:
            # Single request is sufficient
            params = {"per_page": min(max_count, 100)}
            data = await self.get(f"repos/{owner}/{repo}/contributors", params=params)
            return data[:max_count] if max_count else data

        # Paginated request
        all_contributors = []
        page = 1

        while True:
            params = {"per_page": min(per_page, 100), "page": page}
            data = await self.get(f"repos/{owner}/{repo}/contributors", params=params)

            if not data:
                break

            all_contributors.extend(data)

            if max_count and len(all_contributors) >= max_count:
                all_contributors = all_contributors[:max_count]
                break

            if len(data) < per_page:
                break

            page += 1

        return all_contributors

    async def get_repository_branches(
        self, owner: str, repo: str, per_page: int = 100, max_count: int | None = None
    ) -> list[dict[str, Any]]:
        """Get repository branches."""
        logger.debug(f"Fetching branches for {owner}/{repo}")

        if max_count and max_count <= per_page:
            # Single request is sufficient
            params = {"per_page": min(max_count, 100)}
            data = await self.get(f"repos/{owner}/{repo}/branches", params=params)
            return data[:max_count] if max_count else data

        # Paginated request
        all_branches = []
        page = 1

        while True:
            params = {"per_page": min(per_page, 100), "page": page}
            data = await self.get(f"repos/{owner}/{repo}/branches", params=params)

            if not data:
                break

            all_branches.extend(data)

            if max_count and len(all_branches) >= max_count:
                all_branches = all_branches[:max_count]
                break

            if len(data) < per_page:
                break

            page += 1

        return all_branches

    async def get_branch_commits(
        self, owner: str, repo: str, branch: str, per_page: int = 100, max_count: int | None = None
    ) -> list[dict[str, Any]]:
        """Get commits for a specific branch."""
        logger.debug(f"Fetching commits for branch {branch} in {owner}/{repo}")

        params = {"sha": branch, "per_page": min(per_page, 100)}

        if max_count and max_count <= per_page:
            # Single request is sufficient
            params["per_page"] = min(max_count, 100)
            data = await self.get(f"repos/{owner}/{repo}/commits", params=params)
            return data[:max_count] if max_count else data

        # Paginated request
        all_commits = []
        page = 1

        while True:
            params = {"sha": branch, "per_page": min(per_page, 100), "page": page}
            data = await self.get(f"repos/{owner}/{repo}/commits", params=params)

            if not data:
                break

            all_commits.extend(data)

            if max_count and len(all_commits) >= max_count:
                all_commits = all_commits[:max_count]
                break

            if len(data) < per_page:
                break

            page += 1

        return all_commits

    async def get_recent_commits(
        self, owner: str, repo: str, branch: str | None = None, count: int = 5
    ) -> list[RecentCommit]:
        """Get recent commits from a repository's default branch or specified branch.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (defaults to repository's default branch)
            count: Number of recent commits to fetch (1-10)
            
        Returns:
            List of RecentCommit objects with short SHA and truncated message
            
        Raises:
            GitHubAPIError: If API request fails
            ValueError: If count is not between 1 and 10
        """
        if not (1 <= count <= 10):
            raise ValueError("Count must be between 1 and 10")
            
        logger.debug(f"Fetching {count} recent commits from {owner}/{repo} branch {branch or 'default'}")
        
        try:
            # If no branch specified, get repository info to find default branch
            if branch is None:
                repo_info = await self.get_repository(owner, repo)
                branch = repo_info.default_branch
            
            # Fetch recent commits
            params = {"sha": branch, "per_page": min(count, 100)}
            data = await self.get(f"repos/{owner}/{repo}/commits", params=params)
            
            if not data:
                logger.warning(f"No commits found for {owner}/{repo} branch {branch}")
                return []
            
            # Convert to RecentCommit objects
            recent_commits = []
            for commit_data in data[:count]:
                try:
                    recent_commit = RecentCommit.from_github_api(commit_data)
                    recent_commits.append(recent_commit)
                except Exception as e:
                    logger.warning(f"Failed to parse commit {commit_data.get('sha', 'unknown')}: {e}")
                    continue
            
            logger.debug(f"Successfully fetched {len(recent_commits)} recent commits from {owner}/{repo}")
            return recent_commits
            
        except GitHubAPIError:
            # Re-raise GitHub API errors
            raise
        except Exception as e:
            logger.error(f"Failed to fetch recent commits from {owner}/{repo}: {e}")
            raise GitHubAPIError(f"Failed to fetch recent commits: {e}")

    async def get_branch_comparison(
        self, owner: str, repo: str, base: str, head: str
    ) -> dict[str, Any]:
        """Compare two branches."""
        logger.debug(f"Comparing {base}...{head} in {owner}/{repo}")
        return await self.get(f"repos/{owner}/{repo}/compare/{base}...{head}")

    # Fork-specific operations

    async def get_fork_comparison(
        self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str, disable_cache: bool = False
    ) -> dict[str, Any]:
        """Compare a fork with its parent repository.

        Args:
            fork_owner: Fork repository owner
            fork_repo: Fork repository name
            parent_owner: Parent repository owner
            parent_repo: Parent repository name
            disable_cache: Whether to bypass cache (not implemented yet)
        """
        logger.info(f"Comparing fork {fork_owner}/{fork_repo} with parent {parent_owner}/{parent_repo}")
        if disable_cache:
            logger.debug("Cache bypass requested for fork comparison")

        try:
            # Compare fork's default branch with parent's default branch
            fork_info = await self.get_repository(fork_owner, fork_repo, disable_cache=disable_cache)
            parent_info = await self.get_repository(parent_owner, parent_repo, disable_cache=disable_cache)

            # Compare the branches
            comparison = await self.compare_commits(
                parent_owner,
                parent_repo,
                parent_info.default_branch,
                f"{fork_owner}:{fork_info.default_branch}",
            )

            return comparison
        except GitHubAPIError as e:
            # Convert to more specific error type for fork access
            specific_error = self.error_handler.handle_fork_access_error(e, f"{fork_owner}/{fork_repo}")
            raise specific_error from e

    async def get_fork_comparison_safe(
        self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str, disable_cache: bool = False
    ) -> dict[str, Any] | None:
        """Compare a fork with its parent repository with safe error handling.

        Returns None if fork cannot be accessed or compared.
        """
        return await self.error_handler.safe_fork_operation(
            lambda: self.get_fork_comparison(fork_owner, fork_repo, parent_owner, parent_repo, disable_cache),
            fork_url=f"{fork_owner}/{fork_repo}",
            operation_name="get_fork_comparison",
            default_value=None,
        )

    async def get_commits_ahead_behind(
        self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str, disable_cache: bool = False
    ) -> dict[str, int]:
        """Get the number of commits a fork is ahead/behind its parent.

        Args:
            fork_owner: Fork repository owner
            fork_repo: Fork repository name
            parent_owner: Parent repository owner
            parent_repo: Parent repository name
            disable_cache: Whether to bypass cache (not implemented yet)
        """
        try:
            if disable_cache:
                logger.debug(f"Cache bypass requested for commits comparison {fork_owner}/{fork_repo} vs {parent_owner}/{parent_repo}")

            comparison = await self.get_fork_comparison(
                fork_owner, fork_repo, parent_owner, parent_repo, disable_cache=disable_cache
            )

            return {
                "ahead_by": comparison.get("ahead_by", 0),
                "behind_by": comparison.get("behind_by", 0),
                "total_commits": comparison.get("total_commits", 0),
            }
        except GitHubAPIError as e:
            logger.warning(f"Could not compare {fork_owner}/{fork_repo} with parent: {e}")
            return {"ahead_by": 0, "behind_by": 0, "total_commits": 0}

    async def get_commits_ahead_behind_safe(
        self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str, disable_cache: bool = False
    ) -> dict[str, int]:
        """Get the number of commits a fork is ahead/behind its parent with safe error handling.
        
        Returns zero counts if fork cannot be accessed or compared.
        """
        result = await self.error_handler.safe_fork_operation(
            lambda: self.get_commits_ahead_behind(fork_owner, fork_repo, parent_owner, parent_repo, disable_cache),
            fork_url=f"{fork_owner}/{fork_repo}",
            operation_name="get_commits_ahead_behind",
            default_value={"ahead_by": 0, "behind_by": 0, "total_commits": 0},
        )
        return result or {"ahead_by": 0, "behind_by": 0, "total_commits": 0}

    async def create_fork_object(
        self, fork_data: dict[str, Any], parent_data: dict[str, Any]
    ) -> Fork:
        """Create a Fork object with comparison data."""
        fork_repo = Repository.from_github_api(fork_data)
        parent_repo = Repository.from_github_api(parent_data)
        owner = User.from_github_api(fork_data["owner"])

        # Get comparison data
        comparison = await self.get_commits_ahead_behind(
            fork_repo.owner, fork_repo.name, parent_repo.owner, parent_repo.name
        )

        return Fork(
            repository=fork_repo,
            parent=parent_repo,
            owner=owner,
            commits_ahead=comparison["ahead_by"],
            commits_behind=comparison["behind_by"],
            last_activity=fork_repo.pushed_at,
        )

    async def compare_repositories(
        self,
        base_owner: str,
        base_repo: str,
        fork_owner: str,
        fork_repo: str
    ) -> dict[str, Any]:
        """Compare two repositories using GitHub's compare API.

        This method compares the default branch of the fork repository
        with the default branch of the base repository to determine
        how many commits the fork is ahead.

        Args:
            base_owner: Base repository owner
            base_repo: Base repository name
            fork_owner: Fork repository owner
            fork_repo: Fork repository name

        Returns:
            Dictionary containing comparison data including ahead_by count

        Raises:
            GitHubAPIError: If the comparison cannot be performed
        """
        logger.debug(f"Comparing repositories: {base_owner}/{base_repo} vs {fork_owner}/{fork_repo}")

        try:
            # Get repository information to determine default branches
            base_info = await self.get_repository(base_owner, base_repo)
            fork_info = await self.get_repository(fork_owner, fork_repo)

            # Use GitHub's compare API to compare default branches
            # Format: base...head where head can be owner:branch for cross-repo comparison
            comparison_ref = f"{base_info.default_branch}...{fork_owner}:{fork_info.default_branch}"

            comparison = await self.get(f"repos/{base_owner}/{base_repo}/compare/{comparison_ref}")

            return {
                "ahead_by": comparison.get("ahead_by", 0),
                "behind_by": comparison.get("behind_by", 0),
                "status": comparison.get("status", "unknown"),
                "total_commits": comparison.get("total_commits", 0),
                "commits": comparison.get("commits", []),
            }

        except GitHubAPIError as e:
            logger.warning(f"Failed to compare {base_owner}/{base_repo} with {fork_owner}/{fork_repo}: {e}")
            raise

    async def get_recent_commits(
        self,
        owner: str,
        repo: str,
        count: int = 5,
        branch: str | None = None
    ) -> list[RecentCommit]:
        """Get recent commits from a repository's default branch.

        Args:
            owner: Repository owner
            repo: Repository name
            count: Number of recent commits to fetch (default: 5)
            branch: Branch to fetch commits from (default: repository's default branch)

        Returns:
            List of RecentCommit objects with short SHA and truncated messages

        Raises:
            ValueError: If count is not between 1 and 10
            GitHubAPIError: If commits cannot be fetched
        """
        # Validate input parameters
        if not (1 <= count <= 10):
            raise ValueError("Count must be between 1 and 10")

        logger.debug(f"Fetching {count} recent commits from {owner}/{repo}")

        try:
            # If no branch specified, get repository info to determine default branch
            if branch is None:
                repo_info = await self.get_repository(owner, repo)
                branch = repo_info.default_branch

            # Fetch commits from the specified branch
            params = {
                "sha": branch,
                "per_page": min(count, 100),  # GitHub max is 100
                "page": 1,
            }

            commits_data = await self.get(f"repos/{owner}/{repo}/commits", params=params)

            # Process commits using the RecentCommit model
            recent_commits = []
            for commit_data in commits_data[:count]:  # Ensure we don't exceed requested count
                recent_commit = RecentCommit.from_github_api(commit_data, max_message_length=50)
                recent_commits.append(recent_commit)

            logger.debug(f"Successfully fetched {len(recent_commits)} recent commits from {owner}/{repo}")
            return recent_commits

        except GitHubNotFoundError:
            logger.warning(f"Repository {owner}/{repo} not found or branch {branch} does not exist")
            raise GitHubAPIError(f"Repository {owner}/{repo} not found or branch {branch} does not exist")
        except GitHubAPIError as e:
            logger.warning(f"Failed to fetch recent commits from {owner}/{repo}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching recent commits from {owner}/{repo}: {e}")
            raise GitHubAPIError(f"Failed to fetch recent commits: {e}") from e
