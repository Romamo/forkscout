"""Fork qualification data lookup service for retrieving and managing cached fork data."""

import logging
from datetime import datetime, timedelta

from forklift.analysis.fork_data_collection_engine import ForkDataCollectionEngine
from forklift.analysis.fork_discovery import ForkDiscoveryService
from forklift.github.client import GitHubClient
from forklift.models.fork_qualification import CollectedForkData, QualifiedForksResult
from forklift.storage.analysis_cache import AnalysisCacheManager

logger = logging.getLogger(__name__)


class ForkQualificationLookupError(Exception):
    """Raised when fork qualification data lookup fails."""
    pass


class ForkQualificationLookup:
    """Service for looking up and managing fork qualification data."""

    def __init__(
        self,
        github_client: GitHubClient,
        cache_manager: AnalysisCacheManager | None = None,
        data_freshness_hours: int = 24,
    ):
        """
        Initialize fork qualification lookup service.

        Args:
            github_client: GitHub API client for fallback operations
            cache_manager: Cache manager for storing/retrieving qualification data
            data_freshness_hours: Hours after which qualification data is considered stale
        """
        self.github_client = github_client
        self.cache_manager = cache_manager
        self.data_freshness_hours = data_freshness_hours
        self._fork_discovery_service = None

    async def get_fork_qualification_data(
        self, repository_url: str, disable_cache: bool = False
    ) -> QualifiedForksResult | None:
        """
        Get fork qualification data for a repository, using cache when available.

        Args:
            repository_url: Repository URL to get qualification data for
            disable_cache: Whether to bypass cache and fetch fresh data

        Returns:
            QualifiedForksResult if available, None if not found or stale

        Raises:
            ForkQualificationLookupError: If lookup fails
        """
        try:
            owner, repo_name = self._parse_repository_url(repository_url)
            cache_key = f"fork_qualification:{owner}/{repo_name}"

            # Try to get from cache first (unless cache is disabled)
            if not disable_cache and self.cache_manager:
                try:
                    cached_data = await self.cache_manager.cache.get_json(cache_key)
                    if cached_data:
                        # Check if data is fresh
                        qualification_result = QualifiedForksResult(**cached_data)
                        if self._is_data_fresh(qualification_result):
                            logger.debug(f"Using fresh cached qualification data for {owner}/{repo_name}")
                            return qualification_result
                        else:
                            logger.debug(f"Cached qualification data for {owner}/{repo_name} is stale")
                except Exception as e:
                    logger.warning(f"Failed to retrieve cached qualification data: {e}")

            # If no fresh cached data, try to generate new data
            logger.info(f"Generating fresh qualification data for {owner}/{repo_name}")
            qualification_result = await self._generate_qualification_data(
                repository_url, disable_cache
            )

            # Cache the new data (unless cache is disabled)
            if not disable_cache and self.cache_manager and qualification_result:
                try:
                    await self.cache_manager.cache.set_json(
                        key=cache_key,
                        value=qualification_result.model_dump(),
                        entry_type="fork_qualification",
                        ttl_hours=self.data_freshness_hours,
                        repository_url=qualification_result.repository_url,
                        metadata={"owner": owner, "repo": repo_name}
                    )
                    logger.debug(f"Cached fresh qualification data for {owner}/{repo_name}")
                except Exception as e:
                    logger.warning(f"Failed to cache qualification data: {e}")

            return qualification_result

        except Exception as e:
            logger.error(f"Failed to get qualification data for {repository_url}: {e}")
            raise ForkQualificationLookupError(
                f"Failed to get qualification data for {repository_url}: {e}"
            ) from e

    async def lookup_fork_data(
        self, fork_url: str, repository_url: str, disable_cache: bool = False
    ) -> CollectedForkData | None:
        """
        Look up specific fork data from qualification results.

        Args:
            fork_url: URL of the specific fork to look up
            repository_url: URL of the parent repository
            disable_cache: Whether to bypass cache

        Returns:
            CollectedForkData if found, None otherwise

        Raises:
            ForkQualificationLookupError: If lookup fails
        """
        try:
            # Get qualification data for the repository
            qualification_result = await self.get_fork_qualification_data(
                repository_url, disable_cache
            )

            if not qualification_result:
                logger.debug(f"No qualification data available for {repository_url}")
                return None

            # Parse fork URL to get owner/repo
            fork_owner, fork_repo = self._parse_repository_url(fork_url)
            fork_full_name = f"{fork_owner}/{fork_repo}"

            # Find the specific fork in the qualification data
            for fork_data in qualification_result.collected_forks:
                if fork_data.metrics.full_name == fork_full_name:
                    logger.debug(f"Found fork data for {fork_full_name} in qualification results")
                    return fork_data

            logger.debug(f"Fork {fork_full_name} not found in qualification data")
            return None

        except Exception as e:
            logger.error(f"Failed to lookup fork data for {fork_url}: {e}")
            raise ForkQualificationLookupError(
                f"Failed to lookup fork data for {fork_url}: {e}"
            ) from e

    async def is_fork_data_available(
        self, repository_url: str, disable_cache: bool = False
    ) -> bool:
        """
        Check if fresh fork qualification data is available for a repository.

        Args:
            repository_url: Repository URL to check
            disable_cache: Whether to bypass cache

        Returns:
            True if fresh data is available, False otherwise
        """
        try:
            qualification_result = await self.get_fork_qualification_data(
                repository_url, disable_cache
            )
            return qualification_result is not None
        except Exception as e:
            logger.warning(f"Error checking fork data availability: {e}")
            return False

    def _is_data_fresh(self, qualification_result: QualifiedForksResult) -> bool:
        """
        Check if qualification data is still fresh based on timestamp.

        Args:
            qualification_result: Qualification result to check

        Returns:
            True if data is fresh, False if stale
        """
        if not qualification_result.qualification_timestamp:
            return False

        now = datetime.utcnow()
        data_age = now - qualification_result.qualification_timestamp.replace(tzinfo=None)
        max_age = timedelta(hours=self.data_freshness_hours)

        is_fresh = data_age <= max_age

        if not is_fresh:
            logger.debug(
                f"Qualification data is stale: age={data_age.total_seconds()/3600:.1f}h, "
                f"max_age={self.data_freshness_hours}h"
            )

        return is_fresh

    async def _generate_qualification_data(
        self, repository_url: str, disable_cache: bool = False
    ) -> QualifiedForksResult | None:
        """
        Generate fresh qualification data using fork discovery service.

        Args:
            repository_url: Repository URL to generate data for
            disable_cache: Whether to bypass cache

        Returns:
            QualifiedForksResult if successful, None if failed
        """
        try:
            # Initialize fork discovery service if not already done
            if not self._fork_discovery_service:
                data_collection_engine = ForkDataCollectionEngine()
                self._fork_discovery_service = ForkDiscoveryService(
                    self.github_client, data_collection_engine
                )

            # Generate qualification data
            qualification_result = await self._fork_discovery_service.discover_and_collect_fork_data(
                repository_url, disable_cache
            )

            logger.info(
                f"Generated qualification data for {repository_url}: "
                f"{qualification_result.stats.total_forks_discovered} forks, "
                f"{qualification_result.stats.forks_with_no_commits} can skip analysis"
            )

            return qualification_result

        except Exception as e:
            logger.error(f"Failed to generate qualification data for {repository_url}: {e}")
            return None

    def _parse_repository_url(self, repository_url: str) -> tuple[str, str]:
        """
        Parse repository URL to extract owner and repository name.

        Args:
            repository_url: GitHub repository URL

        Returns:
            Tuple of (owner, repo)

        Raises:
            ForkQualificationLookupError: If URL format is invalid
        """
        from urllib.parse import urlparse

        if not repository_url or not repository_url.strip():
            raise ForkQualificationLookupError(f"Invalid repository URL: {repository_url}")

        try:
            # Handle both full URLs and owner/repo format
            if repository_url.startswith("http"):
                parsed = urlparse(repository_url)

                # Check if it's a GitHub URL
                if parsed.netloc != "github.com":
                    raise ValueError("Not a GitHub URL")

                path_parts = [
                    part for part in parsed.path.strip("/").split("/") if part
                ]
                if len(path_parts) >= 2:
                    return path_parts[0], path_parts[1]
                else:
                    raise ValueError("Invalid GitHub URL path")
            else:
                # Handle owner/repo format
                if "/" in repository_url:
                    parts = repository_url.split("/")
                    if len(parts) == 2 and all(part.strip() for part in parts):
                        return parts[0], parts[1]
                    else:
                        raise ValueError("Invalid owner/repo format")
                else:
                    raise ValueError("Invalid repository URL format")

        except Exception as e:
            raise ForkQualificationLookupError(
                f"Invalid repository URL format: {repository_url}"
            ) from e

    async def get_data_freshness_info(
        self, repository_url: str
    ) -> dict[str, any]:
        """
        Get information about the freshness of qualification data.

        Args:
            repository_url: Repository URL to check

        Returns:
            Dictionary with freshness information
        """
        try:
            owner, repo_name = self._parse_repository_url(repository_url)
            cache_key = f"fork_qualification:{owner}/{repo_name}"

            info = {
                "repository": f"{owner}/{repo_name}",
                "has_cached_data": False,
                "is_fresh": False,
                "age_hours": None,
                "max_age_hours": self.data_freshness_hours,
                "last_updated": None,
            }

            if self.cache_manager:
                try:
                    cached_data = await self.cache_manager.cache.get_json(cache_key)
                    if cached_data:
                        info["has_cached_data"] = True
                        qualification_result = QualifiedForksResult(**cached_data)

                        if qualification_result.qualification_timestamp:
                            now = datetime.utcnow()
                            data_age = now - qualification_result.qualification_timestamp.replace(tzinfo=None)
                            info["age_hours"] = data_age.total_seconds() / 3600
                            info["is_fresh"] = self._is_data_fresh(qualification_result)
                            info["last_updated"] = qualification_result.qualification_timestamp.isoformat()

                except Exception as e:
                    logger.warning(f"Error getting freshness info: {e}")

            return info

        except Exception as e:
            logger.error(f"Failed to get freshness info for {repository_url}: {e}")
            return {"error": str(e)}
