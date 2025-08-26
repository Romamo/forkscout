"""Feature ranking and scoring engine."""

import re
from datetime import UTC, datetime
from difflib import SequenceMatcher

from ..config.settings import ScoringConfig
from ..models.analysis import Feature, ForkMetrics, RankedFeature


class FeatureRankingEngine:
    """Engine for ranking and scoring features discovered in forks."""

    def __init__(self, scoring_config: ScoringConfig):
        """Initialize the ranking engine with scoring configuration.
        
        Args:
            scoring_config: Configuration for scoring weights and parameters
        """
        self.scoring_config = scoring_config

    def calculate_feature_score(self, feature: Feature, fork_metrics: ForkMetrics) -> float:
        """Calculate a numerical score (0-100) for a feature.
        
        Args:
            feature: The feature to score
            fork_metrics: Metrics about the fork containing the feature
            
        Returns:
            Score between 0 and 100
        """
        # Calculate individual scoring components
        code_quality_score = self._calculate_code_quality_score(feature)
        community_engagement_score = self._calculate_community_engagement_score(fork_metrics)
        test_coverage_score = self._calculate_test_coverage_score(feature)
        documentation_score = self._calculate_documentation_score(feature)
        recency_score = self._calculate_recency_score(feature)

        # Apply weights and calculate final score
        weighted_score = (
            code_quality_score * self.scoring_config.code_quality_weight +
            community_engagement_score * self.scoring_config.community_engagement_weight +
            test_coverage_score * self.scoring_config.test_coverage_weight +
            documentation_score * self.scoring_config.documentation_weight +
            recency_score * self.scoring_config.recency_weight
        )

        # Ensure score is within bounds
        return max(0.0, min(100.0, weighted_score))

    def rank_features(self, features: list[Feature], fork_metrics_map: dict[str, ForkMetrics]) -> list[RankedFeature]:
        """Rank a list of features by their calculated scores.
        
        Args:
            features: List of features to rank
            fork_metrics_map: Map of fork URLs to their metrics
            
        Returns:
            List of ranked features sorted by score (highest first)
        """
        ranked_features = []

        for feature in features:
            fork_url = feature.source_fork.repository.url
            fork_metrics = fork_metrics_map.get(fork_url, ForkMetrics())

            score = self.calculate_feature_score(feature, fork_metrics)

            # Calculate ranking factors breakdown
            ranking_factors = {
                "code_quality": self._calculate_code_quality_score(feature),
                "community_engagement": self._calculate_community_engagement_score(fork_metrics),
                "test_coverage": self._calculate_test_coverage_score(feature),
                "documentation": self._calculate_documentation_score(feature),
                "recency": self._calculate_recency_score(feature)
            }

            ranked_feature = RankedFeature(
                feature=feature,
                score=score,
                ranking_factors=ranking_factors,
                similar_implementations=[]  # Will be populated by grouping algorithm
            )
            ranked_features.append(ranked_feature)

        # Sort by score (highest first)
        ranked_features.sort(key=lambda rf: rf.score, reverse=True)

        # Group similar features
        self._group_similar_features(ranked_features)

        return ranked_features

    def _calculate_code_quality_score(self, feature: Feature) -> float:
        """Calculate code quality score based on commits and changes.
        
        Args:
            feature: Feature to analyze
            
        Returns:
            Score between 0 and 100
        """
        if not feature.commits:
            return 0.0

        total_score = 0.0

        for commit in feature.commits:
            commit_score = 50.0  # Base score

            # Analyze commit message quality
            message_score = self._analyze_commit_message_quality(commit.message)
            commit_score += message_score * 0.3

            # Analyze change size (moderate changes are better)
            change_size_score = self._analyze_change_size(commit.additions, commit.deletions)
            commit_score += change_size_score * 0.2

            # Check for code patterns that indicate quality
            quality_indicators_score = self._analyze_quality_indicators(feature.files_affected)
            commit_score += quality_indicators_score * 0.5

            total_score += commit_score

        # Average across all commits
        average_score = total_score / len(feature.commits)
        return max(0.0, min(100.0, average_score))

    def _calculate_community_engagement_score(self, fork_metrics: ForkMetrics) -> float:
        """Calculate community engagement score based on fork metrics.
        
        Args:
            fork_metrics: Metrics about the fork
            
        Returns:
            Score between 0 and 100
        """
        score = 0.0

        # Stars indicate community interest
        if fork_metrics.stars > 0:
            # Logarithmic scaling for stars (diminishing returns)
            star_score = min(40.0, 10.0 * (fork_metrics.stars ** 0.5))
            score += star_score

        # Forks indicate reusability
        if fork_metrics.forks > 0:
            fork_score = min(20.0, 5.0 * (fork_metrics.forks ** 0.5))
            score += fork_score

        # Contributors indicate collaboration
        if fork_metrics.contributors > 1:
            contributor_score = min(20.0, 5.0 * fork_metrics.contributors)
            score += contributor_score

        # Recent activity indicates maintenance
        if fork_metrics.last_activity:
            activity_score = self._calculate_activity_score(fork_metrics.last_activity)
            score += activity_score * 0.2

        # Commit frequency indicates active development
        if fork_metrics.commit_frequency > 0:
            frequency_score = min(20.0, fork_metrics.commit_frequency * 10)
            score += frequency_score

        return max(0.0, min(100.0, score))

    def _calculate_test_coverage_score(self, feature: Feature) -> float:
        """Calculate test coverage score based on test-related files.
        
        Args:
            feature: Feature to analyze
            
        Returns:
            Score between 0 and 100
        """
        if not feature.files_affected:
            return 0.0

        test_files = []
        source_files = []

        for file_path in feature.files_affected:
            if self._is_test_file(file_path):
                test_files.append(file_path)
            elif self._is_source_file(file_path):
                source_files.append(file_path)

        if not source_files:
            return 50.0  # Neutral score if no source files

        # Calculate test ratio
        test_ratio = len(test_files) / len(source_files)

        # Score based on test coverage
        if test_ratio >= 1.0:
            return 100.0  # Excellent coverage
        elif test_ratio >= 0.5:
            return 80.0   # Good coverage
        elif test_ratio >= 0.25:
            return 60.0   # Moderate coverage
        elif test_ratio > 0:
            return 40.0   # Some coverage
        else:
            return 20.0   # No test coverage

    def _calculate_documentation_score(self, feature: Feature) -> float:
        """Calculate documentation score based on documentation files and commit messages.
        
        Args:
            feature: Feature to analyze
            
        Returns:
            Score between 0 and 100
        """
        score = 0.0

        # Check for documentation files
        doc_files = [f for f in feature.files_affected if self._is_documentation_file(f)]
        if doc_files:
            score += 40.0

        # Check for README updates
        readme_files = [f for f in feature.files_affected if "readme" in f.lower()]
        if readme_files:
            score += 20.0

        # Analyze commit messages for documentation quality
        if feature.commits:
            message_quality = sum(
                self._analyze_commit_message_documentation(commit.message)
                for commit in feature.commits
            ) / len(feature.commits)
            score += message_quality * 0.4

        return max(0.0, min(100.0, score))

    def _calculate_recency_score(self, feature: Feature) -> float:
        """Calculate recency score based on when commits were made.
        
        Args:
            feature: Feature to analyze
            
        Returns:
            Score between 0 and 100
        """
        if not feature.commits:
            return 0.0

        now = datetime.now(UTC)
        most_recent_commit = max(feature.commits, key=lambda c: c.date)

        # Ensure both datetimes are timezone-aware for comparison
        commit_date = most_recent_commit.date
        if commit_date.tzinfo is None:
            # If commit date is naive, assume it's UTC
            commit_date = commit_date.replace(tzinfo=UTC)

        days_old = (now - commit_date).days

        # Score decreases with age
        if days_old <= 7:
            return 100.0  # Very recent
        elif days_old <= 30:
            return 90.0   # Recent
        elif days_old <= 90:
            return 70.0   # Moderately recent
        elif days_old <= 180:
            return 50.0   # Somewhat old
        elif days_old <= 365:
            return 30.0   # Old
        else:
            return 10.0   # Very old

    def _analyze_commit_message_quality(self, message: str) -> float:
        """Analyze the quality of a commit message.
        
        Args:
            message: Commit message to analyze
            
        Returns:
            Quality score between -25 and 20
        """
        if not message:
            return -25.0

        score = 0.0

        # Length check (good messages are descriptive but not too long)
        if 20 <= len(message) <= 100:
            score += 10.0
        elif len(message) < 10:
            score -= 10.0

        # Check for conventional commit format
        if re.match(r"^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .+", message):
            score += 15.0

        # Check for issue references
        if re.search(r"#\d+|fixes|closes|resolves", message, re.IGNORECASE):
            score += 5.0

        # Penalize vague messages
        vague_patterns = [
            r"^(fix|update|change|modify)$",
            r"^wip$",
            r"^temp$",
            r"^test$"
        ]
        if any(re.match(pattern, message.lower()) for pattern in vague_patterns):
            score -= 10.0

        return score

    def _analyze_change_size(self, additions: int, deletions: int) -> float:
        """Analyze the size of changes in a commit.
        
        Args:
            additions: Number of lines added
            deletions: Number of lines deleted
            
        Returns:
            Score between -10 and 10
        """
        total_changes = additions + deletions

        # Moderate changes are preferred
        if 10 <= total_changes <= 100:
            return 10.0
        elif 5 <= total_changes <= 200:
            return 5.0
        elif total_changes < 5:
            return -5.0  # Too small might be trivial
        else:
            return -10.0  # Too large might be risky

    def _analyze_quality_indicators(self, files_affected: list[str]) -> float:
        """Analyze files for quality indicators.
        
        Args:
            files_affected: List of affected file paths
            
        Returns:
            Score between 0 and 20
        """
        score = 0.0

        for file_path in files_affected:
            # Configuration files indicate good practices
            if any(config in file_path.lower() for config in [
                "pyproject.toml", "setup.py", "requirements.txt",
                "dockerfile", "makefile", ".github"
            ]):
                score += 5.0

            # Type hints files
            if file_path.endswith(".pyi"):
                score += 3.0

        return min(20.0, score)

    def _calculate_activity_score(self, last_activity: datetime) -> float:
        """Calculate activity score based on last activity date.
        
        Args:
            last_activity: Date of last activity
            
        Returns:
            Score between 0 and 100
        """
        now = datetime.now(UTC)

        # Ensure both datetimes are timezone-aware for comparison
        activity_date = last_activity
        if activity_date.tzinfo is None:
            # If activity date is naive, assume it's UTC
            activity_date = activity_date.replace(tzinfo=UTC)

        days_since_activity = (now - activity_date).days

        if days_since_activity <= 7:
            return 100.0
        elif days_since_activity <= 30:
            return 80.0
        elif days_since_activity <= 90:
            return 60.0
        elif days_since_activity <= 180:
            return 40.0
        elif days_since_activity <= 365:
            return 20.0
        else:
            return 0.0

    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file is a test file.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if it's a test file
        """
        test_patterns = [
            r"test_.*\.py$",
            r".*_test\.py$",
            r"tests?/.*\.py$",
            r"spec/.*\.py$",
            r".*\.test\.py$"
        ]
        return any(re.search(pattern, file_path, re.IGNORECASE) for pattern in test_patterns)

    def _is_source_file(self, file_path: str) -> bool:
        """Check if a file is a source code file.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if it's a source file
        """
        source_extensions = [".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs", ".rb"]
        return any(file_path.endswith(ext) for ext in source_extensions) and not self._is_test_file(file_path)

    def _is_documentation_file(self, file_path: str) -> bool:
        """Check if a file is a documentation file.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if it's a documentation file
        """
        doc_patterns = [
            r".*\.md$",
            r".*\.rst$",
            r".*\.txt$",
            r"docs?/.*",
            r".*\.adoc$"
        ]
        return any(re.search(pattern, file_path, re.IGNORECASE) for pattern in doc_patterns)

    def _analyze_commit_message_documentation(self, message: str) -> float:
        """Analyze commit message for documentation quality indicators.
        
        Args:
            message: Commit message to analyze
            
        Returns:
            Score between 0 and 100
        """
        if not message:
            return 0.0

        score = 50.0  # Base score

        # Look for documentation-related keywords
        doc_keywords = ["docs", "documentation", "readme", "guide", "tutorial", "example"]
        if any(keyword in message.lower() for keyword in doc_keywords):
            score += 30.0

        # Look for explanatory content
        if len(message) > 50:  # Longer messages tend to be more explanatory
            score += 20.0

        return min(100.0, score)

    def group_similar_features(self, features: list[Feature]) -> list[list[Feature]]:
        """Group similar features together.
        
        Args:
            features: List of features to group
            
        Returns:
            List of feature groups, where each group contains similar features
        """
        if not features:
            return []

        groups = []
        ungrouped_features = features.copy()

        while ungrouped_features:
            current_feature = ungrouped_features.pop(0)
            current_group = [current_feature]

            # Find similar features
            remaining_features = []
            for feature in ungrouped_features:
                if self._are_features_similar(current_feature, feature):
                    current_group.append(feature)
                else:
                    remaining_features.append(feature)

            ungrouped_features = remaining_features
            groups.append(current_group)

        return groups

    def _group_similar_features(self, ranked_features: list[RankedFeature]) -> None:
        """Group similar features and populate similar_implementations field.
        
        Args:
            ranked_features: List of ranked features to process in-place
        """
        # Create a map for quick lookup
        feature_to_ranked = {rf.feature.id: rf for rf in ranked_features}

        # Group features by similarity
        features = [rf.feature for rf in ranked_features]
        groups = self.group_similar_features(features)

        # Populate similar_implementations for each feature
        for group in groups:
            if len(group) > 1:  # Only process groups with multiple features
                for feature in group:
                    ranked_feature = feature_to_ranked[feature.id]
                    # Add all other features in the group as similar implementations
                    similar_features = [f for f in group if f.id != feature.id]
                    ranked_feature.similar_implementations = similar_features

    def _are_features_similar(self, feature1: Feature, feature2: Feature) -> bool:
        """Determine if two features are similar.
        
        Args:
            feature1: First feature to compare
            feature2: Second feature to compare
            
        Returns:
            True if features are considered similar
        """
        # Don't group features from the same fork
        if feature1.source_fork.repository.url == feature2.source_fork.repository.url:
            return False

        # Calculate similarity score based on multiple factors
        similarity_score = 0.0

        # Title similarity (40% weight)
        title_similarity = self._calculate_text_similarity(feature1.title, feature2.title)
        similarity_score += title_similarity * 0.4

        # Description similarity (30% weight)
        desc_similarity = self._calculate_text_similarity(feature1.description, feature2.description)
        similarity_score += desc_similarity * 0.3

        # File overlap similarity (20% weight)
        file_similarity = self._calculate_file_similarity(feature1.files_affected, feature2.files_affected)
        similarity_score += file_similarity * 0.2

        # Category similarity (10% weight)
        category_similarity = 1.0 if feature1.category == feature2.category else 0.0
        similarity_score += category_similarity * 0.1

        # Consider features similar if similarity score is above threshold
        return similarity_score >= 0.4

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0.0

        # Normalize text for comparison
        normalized_text1 = self._normalize_text(text1)
        normalized_text2 = self._normalize_text(text2)

        # Use sequence matcher for similarity
        similarity = SequenceMatcher(None, normalized_text1, normalized_text2).ratio()

        # Also check for common keywords
        keywords1 = self._extract_keywords(normalized_text1)
        keywords2 = self._extract_keywords(normalized_text2)

        if keywords1 and keywords2:
            keyword_overlap = len(keywords1.intersection(keywords2)) / len(keywords1.union(keywords2))
            # Combine sequence similarity with keyword overlap
            similarity = max(similarity, keyword_overlap * 0.8)

        return similarity

    def _calculate_file_similarity(self, files1: list[str], files2: list[str]) -> float:
        """Calculate similarity between two lists of files.
        
        Args:
            files1: First list of file paths
            files2: Second list of file paths
            
        Returns:
            Similarity score between 0 and 1
        """
        if not files1 or not files2:
            return 0.0

        # Normalize file paths for comparison
        normalized_files1 = {self._normalize_file_path(f) for f in files1}
        normalized_files2 = {self._normalize_file_path(f) for f in files2}

        # Calculate Jaccard similarity
        intersection = len(normalized_files1.intersection(normalized_files2))
        union = len(normalized_files1.union(normalized_files2))

        if union == 0:
            return 0.0

        return intersection / union

    def _normalize_text(self, text: str) -> str:
        """Normalize text for similarity comparison.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Convert to lowercase and remove special characters
        normalized = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        return normalized

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract meaningful keywords from text.
        
        Args:
            text: Text to extract keywords from
            
        Returns:
            Set of keywords
        """
        # Common stop words to exclude
        stop_words = {
            "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
            "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
            "to", "was", "will", "with", "this", "these", "those"
        }

        words = text.split()
        keywords = {word.lower() for word in words if len(word) > 2 and word.lower() not in stop_words}

        return keywords

    def _normalize_file_path(self, file_path: str) -> str:
        """Normalize file path for comparison.
        
        Args:
            file_path: File path to normalize
            
        Returns:
            Normalized file path
        """
        # Extract just the filename and directory structure
        # Remove leading directories that might be project-specific
        parts = file_path.split("/")

        # Keep the last 2-3 parts of the path for comparison
        if len(parts) > 3:
            normalized = "/".join(parts[-3:])
        else:
            normalized = file_path

        return normalized.lower()
