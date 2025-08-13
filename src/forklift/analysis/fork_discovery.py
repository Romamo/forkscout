"""Fork discovery service for finding and analyzing repository forks."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from forklift.github.client import GitHubClient, GitHubAPIError, GitHubNotFoundError
from forklift.models.github import Fork, Repository, Commit, User
from forklift.models.analysis import ForkMetrics

logger = logging.getLogger(__name__)


class ForkDiscoveryError(Exception):
    """Base exception for fork discovery errors."""
    pass


class ForkDiscoveryService:
    """Service for discovering and analyzing repository forks."""

    def __init__(
        self,
        github_client: GitHubClient,
        min_activity_days: int = 365,
        min_commits_ahead: int = 1,
        max_forks_to_analyze: int = 100,
    ):
        """Initialize fork discovery service.
        
        Args:
            github_client: GitHub API client
            min_activity_days: Minimum days since last activity to consider fork active
            min_commits_ahead: Minimum commits ahead of parent to consider fork interesting
            max_forks_to_analyze: Maximum number of forks to analyze
        """
        self.github_client = github_client
        self.min_activity_days = min_activity_days
        self.min_commits_ahead = min_commits_ahead
        self.max_forks_to_analyze = max_forks_to_analyze

    async def discover_forks(self, repository_url: str) -> list[Fork]:
        """Discover all forks of a repository.
        
        Args:
            repository_url: GitHub repository URL (e.g., https://github.com/owner/repo)
            
        Returns:
            List of Fork objects
            
        Raises:
            ForkDiscoveryError: If fork discovery fails
        """
        try:
            # Parse repository URL to get owner and name
            owner, repo_name = self._parse_repository_url(repository_url)
            
            logger.info(f"Starting fork discovery for {owner}/{repo_name}")
            
            # Get the parent repository information
            parent_repo = await self.github_client.get_repository(owner, repo_name)
            
            # Get all forks
            fork_repos = await self.github_client.get_all_repository_forks(
                owner, repo_name, max_forks=self.max_forks_to_analyze
            )
            
            logger.info(f"Found {len(fork_repos)} forks for {owner}/{repo_name}")
            
            # Convert repository objects to Fork objects with comparison data
            forks = []
            for fork_repo in fork_repos:
                try:
                    fork = await self._create_fork_with_comparison(fork_repo, parent_repo)
                    forks.append(fork)
                except Exception as e:
                    logger.warning(f"Failed to analyze fork {fork_repo.full_name}: {e}")
                    continue
            
            logger.info(f"Successfully analyzed {len(forks)} forks")
            return forks
            
        except GitHubNotFoundError:
            raise ForkDiscoveryError(f"Repository not found: {repository_url}")
        except GitHubAPIError as e:
            raise ForkDiscoveryError(f"GitHub API error: {e}") from e
        except Exception as e:
            raise ForkDiscoveryError(f"Unexpected error during fork discovery: {e}") from e

    async def filter_active_forks(self, forks: list[Fork]) -> list[Fork]:
        """Filter forks to identify active ones with unique commits.
        
        Args:
            forks: List of Fork objects to filter
            
        Returns:
            List of active Fork objects
        """
        logger.info(f"Filtering {len(forks)} forks for active ones")
        
        active_forks = []
        cutoff_date = datetime.utcnow() - timedelta(days=self.min_activity_days)
        
        for fork in forks:
            # Check if fork has recent activity
            if not self._is_fork_active(fork, cutoff_date):
                logger.debug(f"Fork {fork.repository.full_name} is not active (last activity: {fork.last_activity})")
                continue
            
            # Check if fork has commits ahead of parent
            if fork.commits_ahead < self.min_commits_ahead:
                logger.debug(f"Fork {fork.repository.full_name} has no unique commits ({fork.commits_ahead} ahead)")
                continue
            
            # Mark fork as active and add to results
            fork.is_active = True
            fork.divergence_score = self._calculate_divergence_score(fork)
            active_forks.append(fork)
            
        logger.info(f"Found {len(active_forks)} active forks")
        return active_forks

    async def get_unique_commits(self, fork: Fork, base_repo: Repository) -> list[Commit]:
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
            
            logger.info(f"Found {len(unique_commits)} unique commits in fork {fork.repository.full_name}")
            return unique_commits
            
        except GitHubAPIError as e:
            logger.error(f"Failed to get unique commits for fork {fork.repository.full_name}: {e}")
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
            if url.endswith('.git'):
                url = url[:-4]
            
            # Handle SSH format: git@github.com:owner/repo
            if url.startswith('git@github.com:'):
                path = url.replace('git@github.com:', '')
                parts = path.split('/')
                if len(parts) >= 2:
                    return parts[0], parts[1]
            
            # Extract from various GitHub URL formats
            elif 'github.com/' in url:
                # Extract the part after github.com/
                parts = url.split('github.com/')[-1].split('/')
                if len(parts) >= 2:
                    return parts[0], parts[1]
            
            # If it's already in owner/repo format
            elif '/' in url and not url.startswith('http'):
                parts = url.split('/')
                if len(parts) == 2:
                    return parts[0], parts[1]
            
            raise ValueError("Invalid URL format")
            
        except Exception as e:
            raise ForkDiscoveryError(f"Invalid repository URL format: {repository_url}") from e

    async def _create_fork_with_comparison(self, fork_repo: Repository, parent_repo: Repository) -> Fork:
        """Create a Fork object with comparison data.
        
        Args:
            fork_repo: Fork repository
            parent_repo: Parent repository
            
        Returns:
            Fork object with comparison data
        """
        # Get comparison data
        comparison_data = await self.github_client.get_commits_ahead_behind(
            fork_repo.owner, fork_repo.name, parent_repo.owner, parent_repo.name
        )
        
        # Get the fork owner user information
        try:
            owner_user = await self.github_client.get_user(fork_repo.owner)
        except Exception as e:
            logger.warning(f"Could not fetch user info for {fork_repo.owner}, creating minimal user: {e}")
            # Create a minimal User object if we can't fetch full details
            owner_user = User(
                login=fork_repo.owner,
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
        
        return fork

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

    async def get_fork_metrics(self, fork: Fork) -> ForkMetrics:
        """Get detailed metrics for a fork.
        
        Args:
            fork: Fork to get metrics for
            
        Returns:
            ForkMetrics object
        """
        try:
            # Get contributors count (this might be expensive, so we'll limit it)
            contributors = await self.github_client.get_repository_contributors(
                fork.repository.owner, fork.repository.name, per_page=100
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
            logger.warning(f"Failed to get metrics for fork {fork.repository.full_name}: {e}")
            return ForkMetrics(
                stars=fork.repository.stars,
                forks=fork.repository.forks_count,
                contributors=0,
                last_activity=fork.last_activity,
                commit_frequency=0.0,
            )

    async def discover_and_filter_forks(self, repository_url: str) -> list[Fork]:
        """Discover and filter forks in one operation.
        
        Args:
            repository_url: GitHub repository URL
            
        Returns:
            List of active Fork objects with unique commits
        """
        # Discover all forks
        all_forks = await self.discover_forks(repository_url)
        
        # Filter for active forks
        active_forks = await self.filter_active_forks(all_forks)
        
        return active_forks