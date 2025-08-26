"""Commit categorization for explanation system."""

import re
from re import Pattern

from forklift.models import CategoryType, Commit, CommitCategory, FileChange


class CategoryPatterns:
    """Patterns for categorizing commits based on messages and file changes."""

    def __init__(self):
        """Initialize category patterns."""
        # Message patterns for each category (ordered by priority/specificity)
        self.message_patterns: dict[CategoryType, list[Pattern[str]]] = {
            CategoryType.FEATURE: [
                re.compile(r"^feat(\([^)]+\))?:", re.IGNORECASE),  # Conventional commits
                re.compile(r"\b(feature|implement|new)\b", re.IGNORECASE),
                re.compile(r"\b(add|introduce|create|build)\b", re.IGNORECASE),
                re.compile(r"\b(support for|enable)\b", re.IGNORECASE),
            ],
            CategoryType.BUGFIX: [
                re.compile(r"^fix(\([^)]+\))?:", re.IGNORECASE),  # Conventional commits
                re.compile(r"\b(bug|patch|hotfix|repair)\b", re.IGNORECASE),
                re.compile(r"\b(resolve|correct|address)\b", re.IGNORECASE),
                re.compile(r"\b(issue|problem|error)\b", re.IGNORECASE),
            ],
            CategoryType.REFACTOR: [
                re.compile(r"^refactor(\([^)]+\))?:", re.IGNORECASE),  # Conventional commits
                re.compile(r"\b(refactor|clean|improve)\b", re.IGNORECASE),
                re.compile(r"\b(restructure|reorganize|simplify)\b", re.IGNORECASE),
                re.compile(r"\b(extract|rename|move)\b", re.IGNORECASE),
            ],
            CategoryType.DOCS: [
                re.compile(r"^docs?(\([^)]+\))?:", re.IGNORECASE),  # Conventional commits
                re.compile(r"\b(documentation|readme)\b", re.IGNORECASE),
                re.compile(r"\b(comment|comments|docstring)\b", re.IGNORECASE),
                re.compile(r"\b(guide|tutorial|example)\b", re.IGNORECASE),
            ],
            CategoryType.TEST: [
                re.compile(r"^test(\([^)]+\))?:", re.IGNORECASE),  # Conventional commits
                re.compile(r"\b(tests|testing|spec)\b", re.IGNORECASE),
                re.compile(r"\b(unittest|pytest|coverage)\b", re.IGNORECASE),
                re.compile(r"\b(mock|fixture|assert)\b", re.IGNORECASE),
            ],
            CategoryType.CHORE: [
                re.compile(r"^chore(\([^)]+\))?:", re.IGNORECASE),  # Conventional commits
                re.compile(r"\b(maintenance|upgrade)\b", re.IGNORECASE),
                re.compile(r"\b(dependency|dependencies|version)\b", re.IGNORECASE),
                re.compile(r"\b(config|configuration|setup)\b", re.IGNORECASE),
                re.compile(r"\bupdate\s+(dependencies|deps|packages|requirements)\b", re.IGNORECASE),
            ],
            CategoryType.PERFORMANCE: [
                re.compile(r"^perf(\([^)]+\))?:", re.IGNORECASE),  # Conventional commits
                re.compile(r"\b(performance|speed|fast)\b", re.IGNORECASE),
                re.compile(r"\b(optimize|optimization|efficient)\b", re.IGNORECASE),
                re.compile(r"\b(cache|caching|memory)\b", re.IGNORECASE),
            ],
            CategoryType.SECURITY: [
                re.compile(r"^security(\([^)]+\))?:", re.IGNORECASE),  # Conventional commits
                re.compile(r"\b(secure|vulnerability)\b", re.IGNORECASE),
                re.compile(r"\b(auth|authentication|authorization)\b", re.IGNORECASE),
                re.compile(r"\b(encrypt|decrypt|hash)\b", re.IGNORECASE),
            ],
        }

        # File patterns for each category
        self.file_patterns: dict[CategoryType, list[Pattern[str]]] = {
            CategoryType.TEST: [
                re.compile(r"test_.*\.py$", re.IGNORECASE),
                re.compile(r".*_test\.py$", re.IGNORECASE),
                re.compile(r"tests?/.*\.py$", re.IGNORECASE),
                re.compile(r".*\.test\.js$", re.IGNORECASE),
                re.compile(r".*\.spec\.js$", re.IGNORECASE),
            ],
            CategoryType.DOCS: [
                re.compile(r"README.*", re.IGNORECASE),
                re.compile(r".*\.md$", re.IGNORECASE),
                re.compile(r".*\.rst$", re.IGNORECASE),
                re.compile(r"docs?/.*", re.IGNORECASE),
                re.compile(r".*\.txt$", re.IGNORECASE),
            ],
            CategoryType.CHORE: [
                re.compile(r"requirements.*\.txt$", re.IGNORECASE),
                re.compile(r"package\.json$", re.IGNORECASE),
                re.compile(r"pyproject\.toml$", re.IGNORECASE),
                re.compile(r"setup\.py$", re.IGNORECASE),
                re.compile(r"Dockerfile$", re.IGNORECASE),
                re.compile(r"\.github/.*", re.IGNORECASE),
                re.compile(r"\.gitignore$", re.IGNORECASE),
            ],
            CategoryType.SECURITY: [
                re.compile(r".*auth.*\.py$", re.IGNORECASE),
                re.compile(r".*security.*\.py$", re.IGNORECASE),
                re.compile(r".*crypto.*\.py$", re.IGNORECASE),
            ],
        }


class CommitCategorizer:
    """Categorizes commits based on message patterns and file changes."""

    def __init__(self, patterns: CategoryPatterns = None):
        """Initialize the categorizer with patterns.
        
        Args:
            patterns: Category patterns to use. If None, uses default patterns.
        """
        self.patterns = patterns or CategoryPatterns()

    def categorize_commit(self, commit: Commit, file_changes: list[FileChange] = None) -> CommitCategory:
        """Categorize a commit based on its message and file changes.
        
        Args:
            commit: The commit to categorize
            file_changes: Optional list of file changes for additional context
            
        Returns:
            CommitCategory with the determined category and confidence
        """
        if file_changes is None:
            file_changes = [
                FileChange(filename=filename, status="modified")
                for filename in commit.files_changed
            ]

        # Analyze commit message
        message_category, message_confidence = self._analyze_commit_message(commit.message)

        # Analyze file changes
        files_category, files_confidence = self._analyze_file_changes(file_changes)

        # Determine final category
        final_category, final_confidence, reasoning = self._determine_category(
            message_category, message_confidence,
            files_category, files_confidence,
            commit, file_changes
        )

        return CommitCategory(
            category_type=final_category,
            confidence=final_confidence,
            reasoning=reasoning
        )

    def _analyze_commit_message(self, message: str) -> tuple[CategoryType, float]:
        """Analyze commit message to determine category.
        
        Args:
            message: Commit message to analyze
            
        Returns:
            Tuple of (category, confidence_score)
        """
        category_scores: dict[CategoryType, float] = {}

        for category, patterns in self.patterns.message_patterns.items():
            score = 0.0

            for i, pattern in enumerate(patterns):
                if pattern.search(message):
                    if i == 0:  # First pattern (conventional commit prefix)
                        score += 2.0  # High weight for conventional commits
                    else:
                        # Decreasing weight for subsequent patterns
                        score += 1.0 - (i * 0.2)

            if score > 0:
                # Calculate confidence with higher base for conventional commits
                if score >= 2.0:  # Conventional commit match
                    confidence = 0.9
                elif score >= 1.0:  # Strong keyword match
                    confidence = 0.7
                else:  # Weak match
                    confidence = min(score, 0.5)

                category_scores[category] = confidence

        if not category_scores:
            return CategoryType.OTHER, 0.1

        # Return category with highest score
        best_category = max(category_scores.items(), key=lambda x: x[1])
        return best_category[0], best_category[1]

    def _analyze_file_changes(self, file_changes: list[FileChange]) -> tuple[CategoryType, float]:
        """Analyze file changes to determine category.
        
        Args:
            file_changes: List of file changes to analyze
            
        Returns:
            Tuple of (category, confidence_score)
        """
        if not file_changes:
            return CategoryType.OTHER, 0.0

        category_scores: dict[CategoryType, int] = {}

        for file_change in file_changes:
            for category, patterns in self.patterns.file_patterns.items():
                for pattern in patterns:
                    if pattern.search(file_change.filename):
                        category_scores[category] = category_scores.get(category, 0) + 1
                        break  # Only count once per file per category

        if not category_scores:
            return CategoryType.OTHER, 0.0

        # Calculate confidence based on proportion of matching files
        total_files = len(file_changes)
        best_category = max(category_scores.items(), key=lambda x: x[1])
        confidence = best_category[1] / total_files

        return best_category[0], min(confidence, 1.0)

    def _determine_category(
        self,
        message_category: CategoryType,
        message_confidence: float,
        files_category: CategoryType,
        files_confidence: float,
        commit: Commit,
        file_changes: list[FileChange]
    ) -> tuple[CategoryType, float, str]:
        """Determine final category by combining message and file analysis.
        
        Args:
            message_category: Category from message analysis
            message_confidence: Confidence from message analysis
            files_category: Category from file analysis
            files_confidence: Confidence from file analysis
            commit: Original commit for additional context
            file_changes: File changes for additional context
            
        Returns:
            Tuple of (final_category, final_confidence, reasoning)
        """
        # If message and files agree, boost confidence (check this first)
        if message_category == files_category and message_confidence > 0.3:
            combined_confidence = min((message_confidence + files_confidence) / 2 + 0.2, 1.0)
            reasoning = f"Message and file patterns both indicate {message_category.value}"
            return message_category, combined_confidence, reasoning

        # Special case: if files strongly indicate a category, prefer that
        if files_confidence > 0.8:
            reasoning = f"Strong file pattern match for {files_category.value} (confidence: {files_confidence:.2f})"
            return files_category, files_confidence, reasoning



        # If message has higher confidence, use it
        if message_confidence > files_confidence:
            reasoning = f"Commit message indicates {message_category.value} (confidence: {message_confidence:.2f})"
            return message_category, message_confidence, reasoning

        # If files have higher confidence, use that
        if files_confidence > message_confidence:
            reasoning = f"File changes indicate {files_category.value} (confidence: {files_confidence:.2f})"
            return files_category, files_confidence, reasoning

        # Default to message category if confidences are equal
        if message_confidence > 0.1:
            reasoning = f"Default to message-based category: {message_category.value}"
            return message_category, message_confidence, reasoning

        # Last resort: classify as OTHER
        reasoning = "Unable to determine specific category from message or files"
        return CategoryType.OTHER, 0.1, reasoning
