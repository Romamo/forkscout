"""Unit tests for CommitCategorizer."""

import pytest
from datetime import datetime

from forklift.analysis.commit_categorizer import CommitCategorizer, CategoryPatterns
from forklift.models import (
    CategoryType,
    CommitCategory,
    FileChange,
    Commit,
    User,
)


class TestCategoryPatterns:
    """Test CategoryPatterns class."""

    def test_category_patterns_initialization(self):
        """Test that CategoryPatterns initializes with all expected patterns."""
        patterns = CategoryPatterns()
        
        # Check that all category types have message patterns
        expected_categories = {
            CategoryType.FEATURE, CategoryType.BUGFIX, CategoryType.REFACTOR,
            CategoryType.DOCS, CategoryType.TEST, CategoryType.CHORE,
            CategoryType.PERFORMANCE, CategoryType.SECURITY
        }
        
        assert set(patterns.message_patterns.keys()) == expected_categories
        
        # Check that each category has at least one pattern
        for category, pattern_list in patterns.message_patterns.items():
            assert len(pattern_list) > 0, f"No patterns for {category}"

    def test_file_patterns_initialization(self):
        """Test that file patterns are properly initialized."""
        patterns = CategoryPatterns()
        
        # Check that key categories have file patterns
        expected_file_categories = {
            CategoryType.TEST, CategoryType.DOCS, CategoryType.CHORE, CategoryType.SECURITY
        }
        
        for category in expected_file_categories:
            assert category in patterns.file_patterns
            assert len(patterns.file_patterns[category]) > 0


class TestCommitCategorizer:
    """Test CommitCategorizer class."""

    @pytest.fixture
    def categorizer(self):
        """Create a CommitCategorizer instance."""
        return CommitCategorizer()

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for commits."""
        return User(
            login="testuser",
            html_url="https://github.com/testuser"
        )

    def create_commit(self, message: str, files: list[str] = None, user=None) -> Commit:
        """Helper to create a commit for testing."""
        if user is None:
            user = User(login="testuser", html_url="https://github.com/testuser")
        
        return Commit(
            sha="a1b2c3d4e5f6789012345678901234567890abcd",
            message=message,
            author=user,
            date=datetime.utcnow(),
            files_changed=files or []
        )

    def create_file_changes(self, filenames: list[str]) -> list[FileChange]:
        """Helper to create file changes for testing."""
        return [
            FileChange(filename=filename, status="modified")
            for filename in filenames
        ]

    def test_categorizer_initialization_default_patterns(self):
        """Test categorizer initialization with default patterns."""
        categorizer = CommitCategorizer()
        assert categorizer.patterns is not None
        assert isinstance(categorizer.patterns, CategoryPatterns)

    def test_categorizer_initialization_custom_patterns(self):
        """Test categorizer initialization with custom patterns."""
        custom_patterns = CategoryPatterns()
        categorizer = CommitCategorizer(custom_patterns)
        assert categorizer.patterns is custom_patterns

    def test_categorize_feature_commit_by_message(self, categorizer, sample_user):
        """Test categorizing a feature commit based on message."""
        commit = self.create_commit("feat: add user authentication system", user=sample_user)
        
        category = categorizer.categorize_commit(commit)
        
        assert category.category_type == CategoryType.FEATURE
        assert category.confidence > 0.5
        assert "feat" in category.reasoning.lower() or "feature" in category.reasoning.lower()

    def test_categorize_bugfix_commit_by_message(self, categorizer, sample_user):
        """Test categorizing a bugfix commit based on message."""
        commit = self.create_commit("fix: resolve login issue with special characters", user=sample_user)
        
        category = categorizer.categorize_commit(commit)
        
        assert category.category_type == CategoryType.BUGFIX
        assert category.confidence > 0.5
        assert "fix" in category.reasoning.lower() or "bug" in category.reasoning.lower()

    def test_categorize_refactor_commit_by_message(self, categorizer, sample_user):
        """Test categorizing a refactor commit based on message."""
        commit = self.create_commit("refactor: clean up database connection logic", user=sample_user)
        
        category = categorizer.categorize_commit(commit)
        
        assert category.category_type == CategoryType.REFACTOR
        assert category.confidence > 0.5
        assert "refactor" in category.reasoning.lower()

    def test_categorize_docs_commit_by_message(self, categorizer, sample_user):
        """Test categorizing a docs commit based on message."""
        commit = self.create_commit("docs: update README with installation instructions", user=sample_user)
        
        category = categorizer.categorize_commit(commit)
        
        assert category.category_type == CategoryType.DOCS
        assert category.confidence > 0.5
        assert "docs" in category.reasoning.lower() or "documentation" in category.reasoning.lower()

    def test_categorize_test_commit_by_message(self, categorizer, sample_user):
        """Test categorizing a test commit based on message."""
        commit = self.create_commit("test: add unit tests for user service", user=sample_user)
        
        category = categorizer.categorize_commit(commit)
        
        assert category.category_type == CategoryType.TEST
        assert category.confidence > 0.5
        assert "test" in category.reasoning.lower()

    def test_categorize_chore_commit_by_message(self, categorizer, sample_user):
        """Test categorizing a chore commit based on message."""
        commit = self.create_commit("chore: update dependencies to latest versions", user=sample_user)
        
        category = categorizer.categorize_commit(commit)
        
        assert category.category_type == CategoryType.CHORE
        assert category.confidence > 0.5
        assert "chore" in category.reasoning.lower()

    def test_categorize_performance_commit_by_message(self, categorizer, sample_user):
        """Test categorizing a performance commit based on message."""
        commit = self.create_commit("perf: optimize database queries for user lookup", user=sample_user)
        
        category = categorizer.categorize_commit(commit)
        
        assert category.category_type == CategoryType.PERFORMANCE
        assert category.confidence > 0.5
        assert "perf" in category.reasoning.lower() or "performance" in category.reasoning.lower()

    def test_categorize_security_commit_by_message(self, categorizer, sample_user):
        """Test categorizing a security commit based on message."""
        commit = self.create_commit("security: fix SQL injection vulnerability in search", user=sample_user)
        
        category = categorizer.categorize_commit(commit)
        
        assert category.category_type == CategoryType.SECURITY
        assert category.confidence > 0.5
        assert "security" in category.reasoning.lower()

    def test_categorize_test_commit_by_files(self, categorizer, sample_user):
        """Test categorizing a commit as test based on file patterns."""
        commit = self.create_commit("Update user validation", user=sample_user)
        file_changes = self.create_file_changes(["test_user_service.py", "test_validation.py"])
        
        category = categorizer.categorize_commit(commit, file_changes)
        
        assert category.category_type == CategoryType.TEST
        assert category.confidence > 0.5
        assert "file" in category.reasoning.lower()

    def test_categorize_docs_commit_by_files(self, categorizer, sample_user):
        """Test categorizing a commit as docs based on file patterns."""
        commit = self.create_commit("Update project information", user=sample_user)
        file_changes = self.create_file_changes(["README.md", "docs/installation.md"])
        
        category = categorizer.categorize_commit(commit, file_changes)
        
        assert category.category_type == CategoryType.DOCS
        assert category.confidence > 0.5
        assert "file" in category.reasoning.lower()

    def test_categorize_chore_commit_by_files(self, categorizer, sample_user):
        """Test categorizing a commit as chore based on file patterns."""
        commit = self.create_commit("Update project configuration", user=sample_user)
        file_changes = self.create_file_changes(["requirements.txt", "pyproject.toml"])
        
        category = categorizer.categorize_commit(commit, file_changes)
        
        assert category.category_type == CategoryType.CHORE
        assert category.confidence > 0.5

    def test_categorize_security_commit_by_files(self, categorizer, sample_user):
        """Test categorizing a commit as security based on file patterns."""
        commit = self.create_commit("Update authentication logic", user=sample_user)
        file_changes = self.create_file_changes(["auth_service.py", "security_utils.py"])
        
        category = categorizer.categorize_commit(commit, file_changes)
        
        assert category.category_type == CategoryType.SECURITY
        assert category.confidence > 0.5

    def test_categorize_commit_message_and_files_agree(self, categorizer, sample_user):
        """Test categorizing when message and files agree on category."""
        commit = self.create_commit("test: add comprehensive user tests", user=sample_user)
        file_changes = self.create_file_changes(["test_user.py", "test_user_service.py"])
        
        category = categorizer.categorize_commit(commit, file_changes)
        
        assert category.category_type == CategoryType.TEST
        assert category.confidence > 0.7  # Should be higher when both agree
        assert "both indicate" in category.reasoning.lower()

    def test_categorize_commit_strong_file_pattern_overrides_message(self, categorizer, sample_user):
        """Test that strong file patterns can override message category."""
        # Message suggests feature, but all files are tests
        commit = self.create_commit("add new functionality", user=sample_user)
        file_changes = self.create_file_changes([
            "test_feature1.py", "test_feature2.py", "test_feature3.py", "test_feature4.py"
        ])
        
        category = categorizer.categorize_commit(commit, file_changes)
        
        # Should be categorized as test due to strong file pattern
        assert category.category_type == CategoryType.TEST
        assert "strong file pattern" in category.reasoning.lower()

    def test_categorize_commit_with_no_clear_patterns(self, categorizer, sample_user):
        """Test categorizing a commit with no clear patterns."""
        commit = self.create_commit("misc changes", user=sample_user)
        file_changes = self.create_file_changes(["random_file.py"])
        
        category = categorizer.categorize_commit(commit, file_changes)
        
        assert category.category_type == CategoryType.OTHER
        assert category.confidence <= 0.2

    def test_categorize_commit_without_file_changes(self, categorizer, sample_user):
        """Test categorizing a commit without explicit file changes."""
        commit = self.create_commit(
            "feat: add user authentication",
            files=["auth.py", "user_service.py"],
            user=sample_user
        )
        
        # Don't pass file_changes, should use commit.files_changed
        category = categorizer.categorize_commit(commit)
        
        assert category.category_type == CategoryType.FEATURE
        assert category.confidence > 0.5

    def test_categorize_commit_empty_file_changes(self, categorizer, sample_user):
        """Test categorizing a commit with empty file changes."""
        commit = self.create_commit("fix: resolve issue", user=sample_user)
        
        category = categorizer.categorize_commit(commit, [])
        
        assert category.category_type == CategoryType.BUGFIX
        assert category.confidence > 0.5

    def test_analyze_commit_message_multiple_patterns(self, categorizer):
        """Test message analysis with multiple matching patterns."""
        message = "feat: add new feature with tests and documentation"
        
        category, confidence = categorizer._analyze_commit_message(message)
        
        # Should match feature patterns most strongly
        assert category == CategoryType.FEATURE
        assert confidence > 0.5

    def test_analyze_commit_message_no_patterns(self, categorizer):
        """Test message analysis with no matching patterns."""
        message = "random commit message with no keywords"
        
        category, confidence = categorizer._analyze_commit_message(message)
        
        assert category == CategoryType.OTHER
        assert confidence == 0.1

    def test_analyze_file_changes_no_files(self, categorizer):
        """Test file analysis with no files."""
        category, confidence = categorizer._analyze_file_changes([])
        
        assert category == CategoryType.OTHER
        assert confidence == 0.0

    def test_analyze_file_changes_mixed_files(self, categorizer):
        """Test file analysis with mixed file types."""
        file_changes = self.create_file_changes([
            "test_user.py",  # test
            "README.md",     # docs
            "main.py"        # no pattern
        ])
        
        category, confidence = categorizer._analyze_file_changes(file_changes)
        
        # Should pick the category with most matches (or first if tied)
        assert category in [CategoryType.TEST, CategoryType.DOCS]
        assert 0.0 < confidence <= 1.0

    def test_confidence_scoring_accuracy(self, categorizer, sample_user):
        """Test that confidence scores are reasonable."""
        # Very clear feature commit
        clear_commit = self.create_commit("feat: implement user authentication system", user=sample_user)
        clear_category = categorizer.categorize_commit(clear_commit)
        
        # Ambiguous commit
        ambiguous_commit = self.create_commit("update stuff", user=sample_user)
        ambiguous_category = categorizer.categorize_commit(ambiguous_commit)
        
        # Clear commit should have higher confidence
        assert clear_category.confidence > ambiguous_category.confidence

    def test_reasoning_provides_context(self, categorizer, sample_user):
        """Test that reasoning provides meaningful context."""
        commit = self.create_commit("docs: update README", user=sample_user)
        file_changes = self.create_file_changes(["README.md"])
        
        category = categorizer.categorize_commit(commit, file_changes)
        
        assert category.reasoning is not None
        assert len(category.reasoning) > 10  # Should be descriptive
        assert category.category_type.value in category.reasoning.lower()

    def test_case_insensitive_pattern_matching(self, categorizer, sample_user):
        """Test that pattern matching is case insensitive."""
        # Test different cases
        commits = [
            self.create_commit("FIX: resolve issue", user=sample_user),
            self.create_commit("fix: resolve issue", user=sample_user),
            self.create_commit("Fix: resolve issue", user=sample_user),
        ]
        
        for commit in commits:
            category = categorizer.categorize_commit(commit)
            assert category.category_type == CategoryType.BUGFIX

    def test_pattern_matching_with_word_boundaries(self, categorizer, sample_user):
        """Test that patterns respect word boundaries."""
        # "fix" should match, but "prefix" should not strongly match fix patterns
        fix_commit = self.create_commit("fix the bug", user=sample_user)
        prefix_commit = self.create_commit("add prefix to function names", user=sample_user)
        
        fix_category = categorizer.categorize_commit(fix_commit)
        prefix_category = categorizer.categorize_commit(prefix_commit)
        
        assert fix_category.category_type == CategoryType.BUGFIX
        # prefix_commit might be OTHER or FEATURE, but shouldn't be BUGFIX with high confidence
        if prefix_category.category_type == CategoryType.BUGFIX:
            assert prefix_category.confidence < fix_category.confidence