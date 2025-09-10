"""Repository analyzer for extracting features from fork commits."""

import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from forkscout.github.client import GitHubClient
from forkscout.models.analysis import (
    AnalysisContext,
    CommitExplanation,
    Feature,
    FeatureCategory,
    ForkAnalysis,
    ForkMetrics,
)
from forkscout.models.github import Commit, Fork, Repository

if TYPE_CHECKING:
    from .commit_explanation_engine import CommitExplanationEngine

logger = logging.getLogger(__name__)


class RepositoryAnalysisError(Exception):
    """Base exception for repository analysis errors."""
    pass


class RepositoryAnalyzer:
    """Analyzer for extracting features from repository forks."""

    def __init__(
        self,
        github_client: GitHubClient,
        min_feature_commits: int = 1,
        max_commits_per_feature: int = 10,
        explanation_engine: Optional["CommitExplanationEngine"] = None,
    ):
        """Initialize repository analyzer.
        
        Args:
            github_client: GitHub API client
            min_feature_commits: Minimum commits required to consider a feature
            max_commits_per_feature: Maximum commits to group into a single feature
            explanation_engine: Optional commit explanation engine for generating explanations
        """
        self.github_client = github_client
        self.min_feature_commits = min_feature_commits
        self.max_commits_per_feature = max_commits_per_feature
        self.explanation_engine = explanation_engine

    async def analyze_fork(
        self,
        fork: Fork,
        base_repo: Repository,
        explain: bool = False
    ) -> ForkAnalysis:
        """Analyze a fork to extract features and metrics.
        
        Args:
            fork: Fork to analyze
            base_repo: Base repository to compare against
            explain: Whether to generate commit explanations
            
        Returns:
            ForkAnalysis with discovered features and metrics
            
        Raises:
            RepositoryAnalysisError: If analysis fails
        """
        try:
            logger.info(f"Starting analysis of fork {fork.repository.full_name}")

            # Get unique commits from the fork
            unique_commits = await self._get_unique_commits(fork, base_repo)

            if not unique_commits:
                logger.info(f"No unique commits found in fork {fork.repository.full_name}")
                return ForkAnalysis(
                    fork=fork,
                    features=[],
                    metrics=await self._get_fork_metrics(fork),
                    analysis_date=datetime.utcnow(),
                    commit_explanations=None,
                    explanation_summary=None,
                )

            # Generate commit explanations if requested and engine is available
            commit_explanations = None
            explanation_summary = None

            if explain and self.explanation_engine:
                logger.info(f"Generating explanations for {len(unique_commits)} commits")
                commit_explanations, explanation_summary = await self._analyze_commits_with_explanations(
                    unique_commits, fork, base_repo
                )

            # Extract features from commits
            features = await self.extract_features(unique_commits, fork)

            # Get fork metrics
            metrics = await self._get_fork_metrics(fork)

            logger.info(f"Analysis complete for {fork.repository.full_name}: {len(features)} features found")

            return ForkAnalysis(
                fork=fork,
                features=features,
                metrics=metrics,
                analysis_date=datetime.utcnow(),
                commit_explanations=commit_explanations,
                explanation_summary=explanation_summary,
            )

        except Exception as e:
            raise RepositoryAnalysisError(f"Failed to analyze fork {fork.repository.full_name}: {e}") from e

    async def extract_features(self, commits: list[Commit], fork: Fork) -> list[Feature]:
        """Extract meaningful features from a list of commits.
        
        Args:
            commits: List of commits to analyze
            fork: Source fork for the commits
            
        Returns:
            List of Feature objects
        """
        logger.info(f"Extracting features from {len(commits)} commits")

        # Group commits by potential features
        feature_groups = self._group_commits_by_feature(commits)

        features = []
        for group_id, (group_key, (group_commits, category)) in enumerate(feature_groups.items()):
            if len(group_commits) < self.min_feature_commits:
                logger.debug(f"Skipping feature group with {len(group_commits)} commits (below minimum)")
                continue

            # Create feature from commit group
            feature = self._create_feature_from_commits(
                group_commits, category, fork, group_id
            )
            features.append(feature)

        logger.info(f"Extracted {len(features)} features")
        return features

    async def categorize_changes(self, commits: list[Commit]) -> dict[str, list[Commit]]:
        """Categorize commits by change type.
        
        Args:
            commits: List of commits to categorize
            
        Returns:
            Dictionary mapping category names to lists of commits
        """
        categories = defaultdict(list)

        for commit in commits:
            category = self._categorize_commit(commit)
            categories[category.value].append(commit)

        return dict(categories)

    def _group_commits_by_feature(self, commits: list[Commit]) -> dict[str, tuple[list[Commit], FeatureCategory]]:
        """Group commits that likely belong to the same feature.
        
        Args:
            commits: List of commits to group
            
        Returns:
            Dictionary mapping feature keys to (commits, category) tuples
        """
        if not commits:
            return {}

        # Sort commits by date to process chronologically
        sorted_commits = sorted(commits, key=lambda c: c.date)

        feature_groups = {}
        current_group_key = None
        current_commits = []
        current_category = None
        group_counter = 0

        for commit in sorted_commits:
            commit_category = self._categorize_commit(commit)

            # Determine if this commit should start a new feature group
            should_start_new_group = (
                current_group_key is None or
                len(current_commits) >= self.max_commits_per_feature or
                self._should_separate_commits(current_commits[-1] if current_commits else None, commit) or
                (current_category != commit_category and current_category not in [FeatureCategory.OTHER, FeatureCategory.REFACTOR])
            )

            if should_start_new_group and current_commits:
                # Save current group with unique key
                unique_key = f"{current_group_key}_{group_counter}"
                feature_groups[unique_key] = (current_commits.copy(), current_category)
                current_commits = []
                current_group_key = None
                current_category = None
                group_counter += 1

            # Start new group or add to current
            if not current_commits:
                current_group_key = self._generate_feature_key(commit)
                current_category = commit_category

            current_commits.append(commit)

        # Save final group
        if current_commits and current_group_key:
            unique_key = f"{current_group_key}_{group_counter}"
            feature_groups[unique_key] = (current_commits, current_category)

        return feature_groups

    def _should_separate_commits(self, prev_commit: Commit | None, current_commit: Commit) -> bool:
        """Determine if two commits should be in separate feature groups.
        
        Args:
            prev_commit: Previous commit (can be None)
            current_commit: Current commit
            
        Returns:
            True if commits should be separated
        """
        if not prev_commit:
            return False

        # Separate if commits are far apart in time (more than 7 days)
        time_diff = abs((current_commit.date - prev_commit.date).days)
        if time_diff > 7:
            return True

        # Separate if commits affect completely different file sets
        prev_files = set(prev_commit.files_changed)
        current_files = set(current_commit.files_changed)

        if prev_files and current_files:
            # Calculate file overlap
            overlap = len(prev_files.intersection(current_files))
            total_files = len(prev_files.union(current_files))
            overlap_ratio = overlap / total_files if total_files > 0 else 0

            # Separate if very low file overlap (less than 20%)
            if overlap_ratio < 0.2:
                return True

        return False

    def _generate_feature_key(self, commit: Commit) -> str:
        """Generate a key for grouping commits into features.
        
        Args:
            commit: Commit to generate key for
            
        Returns:
            Feature key string
        """
        # Use commit message and primary file to create a feature key
        message_words = re.findall(r"\w+", commit.message.lower())
        primary_words = [w for w in message_words[:5] if len(w) > 2]  # First 5 meaningful words

        # Add primary file if available
        primary_file = ""
        if commit.files_changed:
            # Use the file with the most changes or the first one
            primary_file = commit.files_changed[0].split("/")[-1]  # Just filename
            primary_file = re.sub(r"\.[^.]+$", "", primary_file)  # Remove extension

        key_parts = primary_words[:3]  # Limit to 3 words
        if primary_file:
            key_parts.append(primary_file)

        return "_".join(key_parts) if key_parts else f"feature_{commit.sha[:8]}"

    def _categorize_commit(self, commit: Commit) -> FeatureCategory:
        """Categorize a commit based on its content.
        
        Args:
            commit: Commit to categorize
            
        Returns:
            FeatureCategory for the commit
        """
        message_lower = commit.message.lower()
        files_changed = [f.lower() for f in commit.files_changed]

        # Check for bug fixes
        if any(keyword in message_lower for keyword in [
            "fix", "bug", "patch", "hotfix", "repair", "resolve", "issue"
        ]):
            return FeatureCategory.BUG_FIX

        # Check for performance improvements
        if any(keyword in message_lower for keyword in [
            "perf", "performance", "optimize", "speed", "faster", "efficient", "cache"
        ]):
            return FeatureCategory.PERFORMANCE

        # Check for documentation
        if any(keyword in message_lower for keyword in [
            "doc", "readme", "comment", "documentation", "guide"
        ]) or any("readme" in f or "doc" in f for f in files_changed):
            return FeatureCategory.DOCUMENTATION

        # Check for tests
        if any(keyword in message_lower for keyword in [
            "test", "spec", "coverage"
        ]) or any("test" in f or "spec" in f for f in files_changed):
            return FeatureCategory.TEST

        # Check for refactoring
        if any(keyword in message_lower for keyword in [
            "refactor", "clean", "restructure", "reorganize", "simplify"
        ]):
            return FeatureCategory.REFACTOR

        # Check for new features
        if any(keyword in message_lower for keyword in [
            "feat", "feature", "add", "implement", "new", "create", "introduce"
        ]):
            return FeatureCategory.NEW_FEATURE

        # Default to other
        return FeatureCategory.OTHER

    def _create_feature_from_commits(
        self,
        commits: list[Commit],
        category: FeatureCategory,
        fork: Fork,
        group_id: int,
    ) -> Feature:
        """Create a Feature object from a group of commits.
        
        Args:
            commits: List of commits for the feature
            category: Feature category
            fork: Source fork
            group_id: Unique group identifier
            
        Returns:
            Feature object
        """
        # Sort commits chronologically
        sorted_commits = sorted(commits, key=lambda c: c.date)

        # Generate feature title from commits
        title = self._generate_feature_title(sorted_commits, category)

        # Generate feature description
        description = self._generate_feature_description(sorted_commits, category)

        # Collect all affected files
        all_files = set()
        for commit in commits:
            all_files.update(commit.files_changed)

        # Generate unique feature ID
        feature_id = f"{fork.repository.full_name}_{category.value}_{group_id}_{sorted_commits[0].sha[:8]}"

        return Feature(
            id=feature_id,
            title=title,
            description=description,
            category=category,
            commits=sorted_commits,
            files_affected=sorted(list(all_files)),
            source_fork=fork,
        )

    def _generate_feature_title(self, commits: list[Commit], category: FeatureCategory) -> str:
        """Generate a title for a feature based on its commits.
        
        Args:
            commits: List of commits
            category: Feature category
            
        Returns:
            Feature title string
        """
        if not commits:
            return f"Unknown {category.value.replace('_', ' ').title()}"

        # Use the first commit's message as base, but clean it up
        first_message = commits[0].message.split("\n")[0]  # First line only

        # Remove common prefixes
        prefixes_to_remove = [
            r"^(feat|fix|docs|style|refactor|test|chore)(\([^)]+\))?\s*:\s*",
            r"^(add|fix|update|remove|implement|create)\s+",
        ]

        cleaned_message = first_message
        for prefix_pattern in prefixes_to_remove:
            cleaned_message = re.sub(prefix_pattern, "", cleaned_message, flags=re.IGNORECASE)

        # Capitalize first letter
        cleaned_message = cleaned_message.strip()
        if cleaned_message:
            cleaned_message = cleaned_message[0].upper() + cleaned_message[1:]

        # If multiple commits, indicate it's a feature set
        if len(commits) > 1:
            return f"{cleaned_message} (+ {len(commits) - 1} related commits)"

        return cleaned_message or f"{category.value.replace('_', ' ').title()} Feature"

    def _generate_feature_description(self, commits: list[Commit], category: FeatureCategory) -> str:
        """Generate a description for a feature based on its commits.
        
        Args:
            commits: List of commits
            category: Feature category
            
        Returns:
            Feature description string
        """
        if not commits:
            return f"A {category.value.replace('_', ' ')} with no detailed information available."

        # Collect commit messages and stats
        messages = []
        total_additions = 0
        total_deletions = 0
        unique_files = set()

        for commit in commits:
            # Get first line of commit message
            first_line = commit.message.split("\n")[0].strip()
            if first_line and first_line not in messages:
                messages.append(first_line)

            total_additions += commit.additions
            total_deletions += commit.deletions
            unique_files.update(commit.files_changed)

        # Build description
        description_parts = []

        # Add category context
        category_descriptions = {
            FeatureCategory.BUG_FIX: "This bug fix addresses",
            FeatureCategory.NEW_FEATURE: "This new feature implements",
            FeatureCategory.PERFORMANCE: "This performance improvement",
            FeatureCategory.DOCUMENTATION: "This documentation update",
            FeatureCategory.REFACTOR: "This refactoring",
            FeatureCategory.TEST: "This test enhancement",
            FeatureCategory.OTHER: "This change",
        }

        intro = category_descriptions.get(category, "This change")

        # Add main description from first commit
        if messages:
            main_description = messages[0].lower()
            # Remove redundant category prefixes
            for prefix in ["fix", "add", "implement", "update", "create"]:
                if main_description.startswith(prefix):
                    main_description = main_description[len(prefix):].strip()
                    break
            description_parts.append(f"{intro} {main_description}.")

        # Add additional commits if any
        if len(messages) > 1:
            additional = messages[1:3]  # Show up to 2 additional messages
            description_parts.append(f"Additional changes include: {'; '.join(additional)}.")

            if len(messages) > 3:
                description_parts.append(f"Plus {len(messages) - 3} more related commits.")

        # Add impact summary
        impact_parts = []
        if total_additions > 0:
            impact_parts.append(f"{total_additions} lines added")
        if total_deletions > 0:
            impact_parts.append(f"{total_deletions} lines removed")
        if unique_files:
            impact_parts.append(f"{len(unique_files)} files modified")

        if impact_parts:
            description_parts.append(f"Impact: {', '.join(impact_parts)}.")

        return " ".join(description_parts)

    async def _analyze_commits_with_explanations(
        self,
        commits: list[Commit],
        fork: Fork,
        base_repo: Repository
    ) -> tuple[list[CommitExplanation], str]:
        """Analyze commits with explanations using the explanation engine.
        
        Args:
            commits: List of commits to analyze
            fork: Fork being analyzed
            base_repo: Base repository for context
            
        Returns:
            Tuple of (commit_explanations, explanation_summary)
        """
        if not self.explanation_engine:
            return [], "No explanation engine available"

        # Create analysis context
        context = AnalysisContext(
            repository=base_repo,
            fork=fork,
            project_type=self._infer_project_type(base_repo),
            main_language=base_repo.language,
            critical_files=self._identify_critical_files(commits)
        )

        # Generate explanations for all commits
        commit_with_explanations = self.explanation_engine.explain_commits_batch(
            commits, context
        )

        # Extract successful explanations
        successful_explanations = [
            cwe.explanation for cwe in commit_with_explanations
            if cwe.explanation is not None
        ]

        # Generate summary
        summary = self.explanation_engine.get_explanation_summary(successful_explanations)

        logger.info(f"Generated {len(successful_explanations)}/{len(commits)} commit explanations")

        return successful_explanations, summary

    def _infer_project_type(self, repository: Repository) -> str | None:
        """Infer the project type from repository information.
        
        Args:
            repository: Repository to analyze
            
        Returns:
            Inferred project type or None
        """
        if not repository.description:
            return None

        description_lower = repository.description.lower()

        # Check for common project types
        if any(keyword in description_lower for keyword in ["web", "website", "webapp", "frontend"]):
            return "web"
        elif any(keyword in description_lower for keyword in ["api", "backend", "server"]):
            return "api"
        elif any(keyword in description_lower for keyword in ["cli", "command", "tool"]):
            return "cli"
        elif any(keyword in description_lower for keyword in ["library", "package", "framework"]):
            return "library"
        elif any(keyword in description_lower for keyword in ["bot", "automation"]):
            return "bot"

        return None

    def _identify_critical_files(self, commits: list[Commit]) -> list[str]:
        """Identify critical files from commit history.
        
        Args:
            commits: List of commits to analyze
            
        Returns:
            List of critical file names
        """
        # Count file modification frequency
        file_counts = {}
        for commit in commits:
            for filename in commit.files_changed:
                file_counts[filename] = file_counts.get(filename, 0) + 1

        # Identify commonly modified files (likely critical)
        if not file_counts:
            return []

        # Get files modified in more than 20% of commits
        threshold = max(1, len(commits) * 0.2)
        critical_files = [
            filename for filename, count in file_counts.items()
            if count >= threshold
        ]

        # Also include files that match critical patterns
        critical_patterns = [
            r"^(main|index|app|server|client)\.py$",
            r"^(main|index|app)\.js$",
            r"^(main|index|app)\.ts$",
            r"^__init__\.py$",
            r"^setup\.py$",
            r"^pyproject\.toml$",
            r"^package\.json$",
            r"config.*\.(py|js|ts|json|yaml|yml|toml)$",
        ]

        for commit in commits:
            for filename in commit.files_changed:
                for pattern in critical_patterns:
                    if re.match(pattern, filename, re.IGNORECASE):
                        if filename not in critical_files:
                            critical_files.append(filename)

        return critical_files[:10]  # Limit to top 10 critical files

    async def _get_unique_commits(self, fork: Fork, base_repo: Repository) -> list[Commit]:
        """Get unique commits from a fork compared to base repository.
        
        Args:
            fork: Fork to analyze
            base_repo: Base repository to compare against
            
        Returns:
            List of unique Commit objects
            
        Raises:
            GitHubAPIError: If API call fails
        """
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

                # If commit has no stats (from comparison API), fetch detailed commit info
                if commit.total_changes == 0 and not commit_data.get("stats"):
                    logger.debug(f"Fetching detailed stats for commit {commit.sha}")
                    try:
                        detailed_commit = await self.github_client.get_commit(
                            fork.repository.owner,
                            fork.repository.name,
                            commit.sha
                        )
                        commit = detailed_commit
                    except Exception as e:
                        logger.warning(f"Failed to fetch detailed commit {commit.sha}: {e}")
                        # Continue with original commit data

                # Skip very small commits (likely not significant features)
                if not commit.is_significant():
                    logger.debug(f"Skipping insignificant commit {commit.sha} (changes: {commit.total_changes})")
                    continue

                unique_commits.append(commit)

            except Exception as e:
                logger.warning(f"Failed to parse commit data: {e}")
                continue

        return unique_commits

    async def _get_fork_metrics(self, fork: Fork) -> ForkMetrics:
        """Get metrics for a fork.
        
        Args:
            fork: Fork to get metrics for
            
        Returns:
            ForkMetrics object
        """
        try:
            # Get contributors count (limit to avoid expensive API calls)
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
