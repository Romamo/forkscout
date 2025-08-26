"""Fork discovery service for finding and analyzing repository forks."""

import logging
from datetime import datetime

from forklift.analysis.fork_data_collection_engine import ForkDataCollectionEngine
from forklift.github.client import GitHubAPIError, GitHubClient, GitHubNotFoundError
from forklift.github.fork_list_processor import ForkListProcessor
from forklift.models.analysis import ForkMetrics
from forklift.models.fork_qualification import CollectedForkData, QualifiedForksResult
from forklift.models.github import Commit, Fork, Repository, User

logger = logging.getLogger(__name__)


class ForkDiscoveryError(Exception):
    """Base exception for fork discovery errors."""

    pass


class ForkDiscoveryService:
    """Service for discovering and analyzing repository forks."""

    def __init__(
        self,
        github_client: GitHubClient,
        data_collection_engine: ForkDataCollectionEngine | None = None,
        min_activity_days: int = 365,
        min_commits_ahead: int = 1,
        max_forks_to_analyze: int = 100,
    ):
        """Initialize fork discovery service.

        Args:
            github_client: GitHub API client
            data_collection_engine: Fork data collection engine for comprehensive fork data
            min_activity_days: Minimum days since last activity to consider fork active
            min_commits_ahead: Minimum commits ahead of parent to consider fork interesting
            max_forks_to_analyze: Maximum number of forks to analyze
        """
        self.github_client = github_client
        self.data_collection_engine = data_collection_engine or ForkDataCollectionEngine()
        self.fork_list_processor = ForkListProcessor(github_client)
        self.min_activity_days = min_activity_days
        self.min_commits_ahead = min_commits_ahead
        self.max_forks_to_analyze = max_forks_to_analyze

    async def discover_forks(
        self, repository_url: str, disable_cache: bool = False
    ) -> list[Fork]:
        """Discover all forks of a repository with optimized pre-filtering.

        Args:
            repository_url: GitHub repository URL (e.g., https://github.com/owner/repo)
            disable_cache: Whether to bypass cache for API calls

        Returns:
            List of Fork objects

        Raises:
            ForkDiscoveryError: If fork discovery fails
        """
        try:
            # Parse repository URL to get owner and name
            owner, repo_name = self._parse_repository_url(repository_url)

            logger.info(f"Starting optimized fork discovery for {owner}/{repo_name}")

            # Get the parent repository information
            parent_repo = await self.github_client.get_repository(
                owner, repo_name, disable_cache=disable_cache
            )

            # Try comprehensive data collection first, fallback to old method if it fails
            try:
                # Use comprehensive data collection for better efficiency
                fork_data_result = await self.discover_and_collect_fork_data(
                    repository_url, disable_cache=disable_cache
                )

                # Filter out forks with no commits ahead automatically
                forks_needing_analysis = self.data_collection_engine.exclude_no_commits_ahead(
                    fork_data_result.collected_forks
                )

                logger.info(
                    f"Automatic filtering: {fork_data_result.stats.forks_with_no_commits} forks skipped, "
                    f"{len(forks_needing_analysis)} forks proceeding to full analysis"
                )
                logger.info(
                    f"API calls saved by automatic filtering: {fork_data_result.stats.api_calls_saved}"
                )

                # Stage 2: Full analysis with expensive API calls for remaining forks
                forks = []
                api_calls_made = 0

                for collected_fork in forks_needing_analysis:
                    try:
                        # Convert collected fork data to Repository object
                        fork_repo = self._create_repository_from_collected_data(
                            collected_fork
                        )

                        fork = await self._create_fork_with_comparison(
                            fork_repo, parent_repo, disable_cache=disable_cache
                        )
                        forks.append(fork)
                        api_calls_made += 3  # Estimate: compare, user, commits_ahead_behind
                    except Exception as e:
                        logger.warning(
                            f"Failed to analyze fork {collected_fork.metrics.full_name}: {e}"
                        )
                        continue

                total_potential_calls = len(fork_data_result.collected_forks) * 3
                actual_calls = api_calls_made + fork_data_result.stats.api_calls_made
                reduction_percentage = (
                    ((total_potential_calls - actual_calls) / total_potential_calls * 100)
                    if total_potential_calls > 0
                    else 0
                )

                logger.info(f"Successfully analyzed {len(forks)} forks")
                logger.info(
                    f"Performance metrics: {actual_calls}/{total_potential_calls} API calls made ({reduction_percentage:.1f}% reduction)"
                )

                return forks

            except Exception as data_collection_error:
                logger.warning(
                    f"Data collection method failed, falling back to legacy method: {data_collection_error}"
                )

                # Fallback to legacy method
                return await self._discover_forks_legacy(
                    owner, repo_name, parent_repo, disable_cache
                )

        except GitHubNotFoundError as e:
            raise ForkDiscoveryError(f"Repository not found: {repository_url}") from e
        except GitHubAPIError as e:
            raise ForkDiscoveryError(f"GitHub API error: {e}") from e
        except Exception as e:
            raise ForkDiscoveryError(
                f"Unexpected error during fork discovery: {e}"
            ) from e

    async def _discover_forks_legacy(
        self, owner: str, repo_name: str, parent_repo: Repository, disable_cache: bool = False
    ) -> list[Fork]:
        """Legacy fork discovery method using get_all_repository_forks.
        
        This method is used as a fallback when the new data collection method fails.
        """
        logger.info(f"Using legacy fork discovery method for {owner}/{repo_name}")

        # Get all forks (lightweight operation - only basic repository data)
        fork_repos = await self.github_client.get_all_repository_forks(
            owner, repo_name, max_forks=self.max_forks_to_analyze
        )

        logger.info(f"Found {len(fork_repos)} forks for {owner}/{repo_name}")

        # Stage 1: Early pre-filtering using lightweight metadata analysis
        pre_filtered_forks, skipped_count, api_calls_saved = (
            await self._pre_filter_forks_by_metadata(fork_repos, parent_repo)
        )

        logger.info(
            f"Pre-filtering: {skipped_count} forks skipped, {len(pre_filtered_forks)} forks proceeding to full analysis"
        )
        logger.info(f"API calls saved by pre-filtering: {api_calls_saved}")

        # Stage 2: Full analysis with expensive API calls for remaining forks
        forks = []
        api_calls_made = 0

        for fork_repo in pre_filtered_forks:
            try:
                fork = await self._create_fork_with_comparison(
                    fork_repo, parent_repo, disable_cache=disable_cache
                )
                forks.append(fork)
                api_calls_made += 3  # Estimate: compare, user, commits_ahead_behind
            except Exception as e:
                logger.warning(f"Failed to analyze fork {fork_repo.full_name}: {e}")
                continue

        total_potential_calls = len(fork_repos) * 3
        actual_calls = api_calls_made
        reduction_percentage = (
            ((total_potential_calls - actual_calls) / total_potential_calls * 100)
            if total_potential_calls > 0
            else 0
        )

        logger.info(f"Successfully analyzed {len(forks)} forks")
        logger.info(
            f"Performance metrics: {actual_calls}/{total_potential_calls} API calls made ({reduction_percentage:.1f}% reduction)"
        )

        return forks

    async def filter_active_forks(self, forks: list[Fork]) -> list[Fork]:
        """Filter forks to identify active ones with unique commits.

        Uses automatic filtering based on commits ahead detection:
        - Forks with no commits ahead (created_at >= pushed_at) are automatically excluded
        - All other forks proceed to detailed commit analysis regardless of age or stars

        Args:
            forks: List of Fork objects to filter

        Returns:
            List of active Fork objects
        """
        logger.info(f"Filtering {len(forks)} forks using automatic commits-ahead detection")

        # Automatic filtering - skip only forks with definitively no commits ahead
        pre_filtered_forks = []
        skipped_count = 0

        for fork in forks:
            if self._has_no_commits_ahead(fork):
                logger.debug(
                    f"Automatic filtering: Fork {fork.repository.full_name} has no commits ahead (created_at >= pushed_at)"
                )
                skipped_count += 1
                continue

            pre_filtered_forks.append(fork)

        logger.info(
            f"Automatic filtering: {skipped_count} forks skipped, {len(pre_filtered_forks)} forks proceeding to analysis"
        )

        # Full analysis - all remaining forks are analyzed regardless of age or stars
        active_forks = []

        for fork in pre_filtered_forks:
            # Check if fork has commits ahead of parent (from API comparison)
            if fork.commits_ahead < self.min_commits_ahead:
                logger.debug(
                    f"Analysis: Fork {fork.repository.full_name} has no unique commits ({fork.commits_ahead} ahead)"
                )
                continue

            # Mark fork as active and add to results
            fork.is_active = True
            fork.divergence_score = self._calculate_divergence_score(fork)
            active_forks.append(fork)

        logger.info(
            f"Analysis completed: Found {len(active_forks)} active forks from {len(pre_filtered_forks)} analyzed"
        )
        return active_forks

    async def get_unique_commits(
        self, fork: Fork, base_repo: Repository, disable_cache: bool = False
    ) -> list[Commit]:
        """Get commits that are unique to the fork (ahead of upstream).

        Args:
            fork: Fork object to analyze
            base_repo: Base repository to compare against

        Returns:
            List of unique Commit objects
        """
        try:
            logger.info(f"Getting unique commits for fork {fork.repository.full_name}")

            # Get comparison data between fork and parent
            comparison = await self.github_client.get_fork_comparison(
                fork.repository.owner,
                fork.repository.name,
                base_repo.owner,
                base_repo.name,
                disable_cache=disable_cache,
            )

            # Extract commits that are ahead
            unique_commits = []
            commits_data = comparison.get("commits", [])

            for commit_data in commits_data:
                try:
                    commit = Commit.from_github_api(commit_data)

                    # Skip merge commits for feature analysis
                    if commit.is_merge:
                        logger.debug(f"Skipping merge commit {commit.sha}")
                        continue

                    # Skip very small commits (likely not significant features)
                    if not commit.is_significant():
                        logger.debug(f"Skipping insignificant commit {commit.sha}")
                        continue

                    unique_commits.append(commit)

                except Exception as e:
                    logger.warning(f"Failed to parse commit data: {e}")
                    continue

            logger.info(
                f"Found {len(unique_commits)} unique commits in fork {fork.repository.full_name}"
            )
            return unique_commits

        except GitHubAPIError as e:
            logger.error(
                f"Failed to get unique commits for fork {fork.repository.full_name}: {e}"
            )
            return []

    def _parse_repository_url(self, repository_url: str) -> tuple[str, str]:
        """Parse GitHub repository URL to extract owner and repository name.

        Args:
            repository_url: GitHub repository URL

        Returns:
            Tuple of (owner, repository_name)

        Raises:
            ForkDiscoveryError: If URL format is invalid
        """
        try:
            # Handle different URL formats
            url = repository_url.strip()

            # Remove trailing .git if present
            if url.endswith(".git"):
                url = url[:-4]

            # Handle SSH format: git@github.com:owner/repo
            if url.startswith("git@github.com:"):
                path = url.replace("git@github.com:", "")
                parts = path.split("/")
                if len(parts) >= 2:
                    return parts[0], parts[1]

            # Extract from various GitHub URL formats
            elif "github.com/" in url:
                # Extract the part after github.com/
                path_part = url.split("github.com/")[-1]

                # Handle API URLs like https://api.github.com/repos/owner/repo
                if path_part.startswith("repos/"):
                    path_part = path_part[6:]  # Remove "repos/" prefix

                parts = path_part.split("/")
                if len(parts) >= 2:
                    return parts[0], parts[1]

            # If it's already in owner/repo format
            elif "/" in url and not url.startswith("http"):
                parts = url.split("/")
                if len(parts) == 2:
                    return parts[0], parts[1]

            raise ValueError("Invalid URL format")

        except Exception as e:
            raise ForkDiscoveryError(
                f"Invalid repository URL format: {repository_url}"
            ) from e

    def _create_repository_from_collected_data(
        self, collected_fork: CollectedForkData
    ) -> Repository:
        """Create a Repository object from collected fork data.

        Args:
            collected_fork: Collected fork data with metrics

        Returns:
            Repository object for the fork
        """
        metrics = collected_fork.metrics

        return Repository(
            id=metrics.id,
            owner=metrics.owner,
            name=metrics.name,
            full_name=metrics.full_name,
            url=f"https://api.github.com/repos/{metrics.full_name}",
            html_url=metrics.html_url,
            clone_url=f"https://github.com/{metrics.full_name}.git",
            default_branch=metrics.default_branch,
            stars=metrics.stargazers_count,
            forks_count=metrics.forks_count,
            is_fork=True,
            created_at=metrics.created_at,
            updated_at=metrics.updated_at,
            pushed_at=metrics.pushed_at,
            size=metrics.size,
            language=metrics.language,
            topics=metrics.topics,
            archived=metrics.archived,
            disabled=metrics.disabled,
        )

    async def _create_fork_with_comparison(
        self, fork_repo: Repository, parent_repo: Repository, disable_cache: bool = False
    ) -> Fork:
        """Create a Fork object with comparison data.

        This method performs expensive API calls to get detailed fork information.
        It should only be called for forks that have passed pre-filtering.

        Args:
            fork_repo: Fork repository
            parent_repo: Parent repository

        Returns:
            Fork object with comparison data
        """
        logger.debug(f"Creating fork with comparison data for {fork_repo.full_name}")

        # Get comparison data (expensive API call)
        comparison_data = await self.github_client.get_commits_ahead_behind(
            fork_repo.owner, fork_repo.name, parent_repo.owner, parent_repo.name,
            disable_cache=disable_cache
        )

        # Get the fork owner user information (expensive API call)
        try:
            owner_user = await self.github_client.get_user(fork_repo.owner, disable_cache=disable_cache)
        except Exception as e:
            logger.warning(
                f"Could not fetch user info for {fork_repo.owner}, creating minimal user: {e}"
            )
            # Create a minimal User object if we can't fetch full details
            owner_user = User(
                id=0,  # Unknown ID
                login=fork_repo.owner,
                name=None,
                email=None,
                avatar_url=None,
                html_url=f"https://github.com/{fork_repo.owner}",
            )

        # Create Fork object
        fork = Fork(
            repository=fork_repo,
            parent=parent_repo,
            owner=owner_user,
            commits_ahead=comparison_data["ahead_by"],
            commits_behind=comparison_data["behind_by"],
            last_activity=fork_repo.pushed_at,
        )

        logger.debug(
            f"Fork {fork_repo.full_name}: {fork.commits_ahead} ahead, {fork.commits_behind} behind"
        )

        return fork

    def _has_no_commits_ahead(self, fork: Fork) -> bool:
        """Check if a fork has no commits ahead using created_at >= pushed_at comparison.

        This is a lightweight check to identify forks that have never been modified
        since creation, indicating no new commits have been made.

        Args:
            fork: Fork to check

        Returns:
            True if fork has no commits ahead (should be skipped), False otherwise
        """
        if not fork.repository.created_at or not fork.repository.pushed_at:
            # If we don't have timestamp data, we can't make this determination
            # so we proceed with full analysis to be safe
            return False

        # Normalize both timestamps to UTC for comparison
        created_at = fork.repository.created_at
        pushed_at = fork.repository.pushed_at

        # Convert timezone-aware datetimes to UTC, then remove timezone info
        if created_at.tzinfo is not None:
            created_at_tuple = created_at.utctimetuple()
            created_at = datetime(*created_at_tuple[:6])

        if pushed_at.tzinfo is not None:
            pushed_at_tuple = pushed_at.utctimetuple()
            pushed_at = datetime(*pushed_at_tuple[:6])

        # If created_at >= pushed_at, the fork has never been pushed to after creation
        # This indicates no new commits have been made
        return created_at >= pushed_at

    def _is_fork_active(self, fork: Fork, cutoff_date: datetime) -> bool:
        """Check if a fork is considered active based on last activity.

        Args:
            fork: Fork to check
            cutoff_date: Cutoff date for activity

        Returns:
            True if fork is active, False otherwise
        """
        if not fork.last_activity:
            return False

        # Convert to UTC if timezone-aware
        last_activity = fork.last_activity
        if last_activity.tzinfo is not None:
            last_activity = last_activity.replace(tzinfo=None)

        return last_activity > cutoff_date

    def _calculate_divergence_score(self, fork: Fork) -> float:
        """Calculate how much a fork has diverged from its parent.

        Args:
            fork: Fork to calculate divergence for

        Returns:
            Divergence score between 0.0 and 1.0
        """
        total_commits = fork.commits_ahead + fork.commits_behind

        if total_commits == 0:
            return 0.0

        # Higher score for more commits ahead relative to total divergence
        divergence = fork.commits_ahead / total_commits

        # Apply activity score multiplier
        activity_score = fork.calculate_activity_score()

        return min(1.0, divergence * activity_score)

    async def _pre_filter_forks_by_metadata(
        self, fork_repos: list[Repository], parent_repo: Repository
    ) -> tuple[list[Repository], int, int]:
        """Pre-filter forks using lightweight metadata analysis to reduce API calls.

        This method performs early filtering using only basic repository data
        to identify forks that definitely have no commits ahead, avoiding
        expensive /compare/, /repos/, and /users/ API calls for those forks.

        Args:
            fork_repos: List of fork repositories to pre-filter
            parent_repo: Parent repository for comparison

        Returns:
            Tuple of (filtered_forks, skipped_count, api_calls_saved)
        """
        filtered_forks = []
        skipped_count = 0

        for fork_repo in fork_repos:
            # Use lightweight timestamp analysis to detect forks with no commits ahead
            if self._has_no_commits_ahead_from_repo(fork_repo):
                logger.debug(
                    f"Pre-filtering: Fork {fork_repo.full_name} has no commits ahead "
                    f"(created_at >= pushed_at), skipping expensive API calls"
                )
                skipped_count += 1
                continue

            # Fork potentially has commits ahead, proceed to full analysis
            filtered_forks.append(fork_repo)

        # Calculate API calls saved (each skipped fork saves ~3 API calls)
        api_calls_saved = skipped_count * 3  # compare, user, commits_ahead_behind

        return filtered_forks, skipped_count, api_calls_saved

    def _has_no_commits_ahead_from_repo(self, fork_repo: Repository) -> bool:
        """Check if a fork repository has no commits ahead using lightweight metadata.

        This method uses only the basic repository data (created_at, pushed_at)
        to determine if a fork has never been modified since creation, indicating
        no new commits have been made.

        Args:
            fork_repo: Fork repository to check

        Returns:
            True if fork has no commits ahead (should be skipped), False otherwise
        """
        if not fork_repo.created_at or not fork_repo.pushed_at:
            # If we don't have timestamp data, we can't make this determination
            # so we proceed with full analysis to be safe
            return False

        # Normalize both timestamps to UTC for comparison
        created_at = fork_repo.created_at
        pushed_at = fork_repo.pushed_at

        # Convert timezone-aware datetimes to UTC, then remove timezone info
        if created_at.tzinfo is not None:
            created_at_tuple = created_at.utctimetuple()
            created_at = datetime(*created_at_tuple[:6])

        if pushed_at.tzinfo is not None:
            pushed_at_tuple = pushed_at.utctimetuple()
            pushed_at = datetime(*pushed_at_tuple[:6])

        # If created_at >= pushed_at, the fork has never been pushed to after creation
        # This indicates no new commits have been made
        return created_at >= pushed_at

    async def get_fork_metrics(self, fork: Fork, disable_cache: bool = False) -> ForkMetrics:
        """Get detailed metrics for a fork.

        Args:
            fork: Fork to get metrics for

        Returns:
            ForkMetrics object
        """
        try:
            # Get contributors count (this might be expensive, so we'll limit it)
            contributors = await self.github_client.get_repository_contributors(
                fork.repository.owner, fork.repository.name, per_page=100, disable_cache=disable_cache
            )

            # Calculate commit frequency (commits per day since creation)
            commit_frequency = 0.0
            if fork.repository.created_at and fork.last_activity:
                days_active = (fork.last_activity - fork.repository.created_at).days
                if days_active > 0:
                    # Estimate based on total commits (this is approximate)
                    total_commits = fork.commits_ahead + fork.commits_behind
                    commit_frequency = total_commits / days_active

            return ForkMetrics(
                stars=fork.repository.stars,
                forks=fork.repository.forks_count,
                contributors=len(contributors),
                last_activity=fork.last_activity,
                commit_frequency=commit_frequency,
            )

        except Exception as e:
            logger.warning(
                f"Failed to get metrics for fork {fork.repository.full_name}: {e}"
            )
            return ForkMetrics(
                stars=fork.repository.stars,
                forks=fork.repository.forks_count,
                contributors=0,
                last_activity=fork.last_activity,
                commit_frequency=0.0,
            )

    async def discover_and_filter_forks(
        self, repository_url: str, disable_cache: bool = False
    ) -> list[Fork]:
        """Discover and filter forks in one operation.

        Args:
            repository_url: GitHub repository URL
            disable_cache: Whether to bypass cache for API calls

        Returns:
            List of active Fork objects with unique commits
        """
        # Discover all forks
        all_forks = await self.discover_forks(repository_url, disable_cache=disable_cache)

        # Filter for active forks
        active_forks = await self.filter_active_forks(all_forks)

        return active_forks

    async def discover_and_collect_fork_data(
        self, repository_url: str, disable_cache: bool = False
    ) -> QualifiedForksResult:
        """Discover and collect comprehensive fork data with automatic filtering.

        This method gathers comprehensive fork information using the paginated forks list
        endpoint and automatically excludes forks with no commits ahead from expensive
        analysis operations.

        Args:
            repository_url: GitHub repository URL
            disable_cache: Whether to bypass cache for API calls

        Returns:
            QualifiedForksResult with comprehensive fork data and statistics

        Raises:
            ForkDiscoveryError: If fork discovery or data collection fails
        """
        try:
            import time

            start_time = time.time()

            # Parse repository URL to get owner and name
            owner, repo_name = self._parse_repository_url(repository_url)

            logger.info(
                f"Starting comprehensive fork data collection for {owner}/{repo_name}"
            )

            # Get all forks list data using paginated endpoint (efficient)
            forks_list_data = await self.fork_list_processor.get_all_forks_list_data(
                owner, repo_name
            )

            logger.info(f"Retrieved {len(forks_list_data)} forks from paginated API")

            # Collect comprehensive fork data from list
            collected_forks = self.data_collection_engine.collect_fork_data_from_list(
                forks_list_data
            )

            # Count forks that can be skipped from expensive analysis
            forks_with_no_commits = sum(
                1 for fork in collected_forks if fork.metrics.can_skip_analysis
            )
            forks_needing_analysis = len(collected_forks) - forks_with_no_commits

            # Calculate API call savings
            # Each fork that can be skipped saves approximately 3 API calls
            # (compare, user info, detailed repository data)
            api_calls_saved = forks_with_no_commits * 3
            api_calls_made = len(forks_list_data)  # Only paginated list calls made

            processing_time = time.time() - start_time

            logger.info(
                f"Fork data collection completed: {len(collected_forks)} forks processed, "
                f"{forks_with_no_commits} can skip analysis, "
                f"{forks_needing_analysis} need detailed analysis"
            )
            logger.info(
                f"API efficiency: {api_calls_saved} calls saved by automatic filtering"
            )

            # Create comprehensive result with statistics
            result = self.data_collection_engine.create_qualification_result(
                repository_owner=owner,
                repository_name=repo_name,
                collected_forks=collected_forks,
                processing_time_seconds=processing_time,
                api_calls_made=api_calls_made,
                api_calls_saved=api_calls_saved,
            )

            return result

        except Exception as e:
            logger.error(f"Fork data collection failed for {repository_url}: {e}")
            raise ForkDiscoveryError(
                f"Failed to collect fork data for {repository_url}: {e}"
            ) from e
