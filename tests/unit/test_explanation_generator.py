"""Unit tests for ExplanationGenerator."""

import pytest
from datetime import datetime

from forklift.analysis.explanation_generator import ExplanationGenerator, ExplanationTemplates
from forklift.models import (
    CategoryType,
    ImpactLevel,
    MainRepoValue,
    FileChange,
    Commit,
    User,
    Repository,
)


class TestExplanationTemplates:
    """Test ExplanationTemplates class."""

    def test_explanation_templates_initialization(self):
        """Test that ExplanationTemplates initializes with all expected templates."""
        templates = ExplanationTemplates()
        
        # Check that all category types have templates
        expected_categories = {
            CategoryType.FEATURE, CategoryType.BUGFIX, CategoryType.REFACTOR,
            CategoryType.DOCS, CategoryType.TEST, CategoryType.CHORE,
            CategoryType.PERFORMANCE, CategoryType.SECURITY, CategoryType.OTHER
        }
        
        assert set(templates.category_templates.keys()) == expected_categories
        
        # Check that each category has at least one template
        for category, template_list in templates.category_templates.items():
            assert len(template_list) > 0, f"No templates for {category}"
            # Check that templates have placeholder
            for template in template_list:
                assert "{description}" in template, f"Template missing placeholder: {template}"

    def test_value_templates_initialization(self):
        """Test that value templates are properly initialized."""
        templates = ExplanationTemplates()
        
        # Check that all main repo values have templates
        expected_values = {MainRepoValue.YES, MainRepoValue.NO, MainRepoValue.UNCLEAR}
        assert set(templates.value_templates.keys()) == expected_values
        
        # Check that each value has at least one template
        for value, template_list in templates.value_templates.items():
            assert len(template_list) > 0, f"No templates for {value}"

    def test_complexity_indicators_initialization(self):
        """Test that complexity indicators are properly initialized."""
        templates = ExplanationTemplates()
        
        assert len(templates.complexity_indicators) > 0
        for indicator in templates.complexity_indicators:
            assert isinstance(indicator, str)
            assert len(indicator) > 10  # Should be descriptive


class TestExplanationGenerator:
    """Test ExplanationGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create an ExplanationGenerator instance."""
        return ExplanationGenerator()

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            login="testuser",
            html_url="https://github.com/testuser"
        )

    @pytest.fixture
    def sample_repository(self):
        """Create a sample repository."""
        return Repository(
            owner="testowner",
            name="testrepo",
            full_name="testowner/testrepo",
            url="https://api.github.com/repos/testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            clone_url="https://github.com/testowner/testrepo.git"
        )

    def create_commit(
        self,
        message: str,
        files: list[str] = None,
        user=None
    ) -> Commit:
        """Helper to create a commit for testing."""
        if user is None:
            user = User(login="testuser", html_url="https://github.com/testuser")
        
        return Commit(
            sha="a1b2c3d4e5f6789012345678901234567890abcd",
            message=message,
            author=user,
            date=datetime.utcnow(),
            files_changed=files or ["test.py"]
        )

    def create_file_changes(self, files_data: list[tuple[str, int, int]]) -> list[FileChange]:
        """Helper to create file changes for testing.
        
        Args:
            files_data: List of tuples (filename, additions, deletions)
        """
        return [
            FileChange(
                filename=filename,
                status="modified",
                additions=additions,
                deletions=deletions
            )
            for filename, additions, deletions in files_data
        ]

    def test_generator_initialization_default_templates(self):
        """Test generator initialization with default templates."""
        generator = ExplanationGenerator()
        assert generator.templates is not None
        assert isinstance(generator.templates, ExplanationTemplates)

    def test_generator_initialization_custom_templates(self):
        """Test generator initialization with custom templates."""
        custom_templates = ExplanationTemplates()
        generator = ExplanationGenerator(custom_templates)
        assert generator.templates is custom_templates

    def test_generate_explanation_feature_commit(self, generator, sample_user, sample_repository):
        """Test generating explanation for a feature commit."""
        commit = self.create_commit(
            "feat: add user authentication system",
            files=["auth.py", "user_service.py"],
            user=sample_user
        )
        file_changes = self.create_file_changes([
            ("auth.py", 100, 10),
            ("user_service.py", 50, 5)
        ])
        
        what_changed, explanation, main_repo_value, is_complex, github_url = generator.generate_explanation(
            commit, CategoryType.FEATURE, ImpactLevel.HIGH, file_changes, sample_repository
        )
        
        assert "user authentication system" in what_changed.lower()
        assert len(explanation) > 0
        assert main_repo_value in [MainRepoValue.YES, MainRepoValue.UNCLEAR]
        assert isinstance(is_complex, bool)
        assert github_url.startswith("https://github.com/testowner/testrepo/commit/")
        assert commit.sha in github_url

    def test_generate_explanation_bugfix_commit(self, generator, sample_user, sample_repository):
        """Test generating explanation for a bugfix commit."""
        commit = self.create_commit(
            "fix: resolve login issue with special characters",
            files=["auth.py"],
            user=sample_user
        )
        file_changes = self.create_file_changes([("auth.py", 20, 10)])
        
        what_changed, explanation, main_repo_value, is_complex, github_url = generator.generate_explanation(
            commit, CategoryType.BUGFIX, ImpactLevel.MEDIUM, file_changes, sample_repository
        )
        
        assert "login issue" in what_changed.lower() or "special characters" in what_changed.lower()
        assert main_repo_value == MainRepoValue.YES  # Bugfixes are usually valuable
        assert not is_complex  # Simple bugfix shouldn't be complex
        assert github_url.startswith("https://github.com/testowner/testrepo/commit/")

    def test_generate_explanation_test_commit(self, generator, sample_user, sample_repository):
        """Test generating explanation for a test commit."""
        commit = self.create_commit(
            "test: add comprehensive user tests",
            files=["test_user.py", "test_auth.py"],
            user=sample_user
        )
        file_changes = self.create_file_changes([
            ("test_user.py", 50, 5),
            ("test_auth.py", 30, 2)
        ])
        
        what_changed, explanation, main_repo_value, is_complex, github_url = generator.generate_explanation(
            commit, CategoryType.TEST, ImpactLevel.LOW, file_changes, sample_repository
        )
        
        assert "test" in explanation.lower()
        assert main_repo_value == MainRepoValue.YES  # Tests are usually valuable
        assert github_url.startswith("https://github.com/testowner/testrepo/commit/")

    def test_generate_explanation_docs_commit(self, generator, sample_user, sample_repository):
        """Test generating explanation for a documentation commit."""
        commit = self.create_commit(
            "docs: update README with installation instructions",
            files=["README.md"],
            user=sample_user
        )
        file_changes = self.create_file_changes([("README.md", 30, 5)])
        
        what_changed, explanation, main_repo_value, is_complex, github_url = generator.generate_explanation(
            commit, CategoryType.DOCS, ImpactLevel.LOW, file_changes, sample_repository
        )
        
        assert "readme" in what_changed.lower() or "installation" in what_changed.lower()
        assert main_repo_value == MainRepoValue.YES  # Docs are usually valuable
        assert github_url.startswith("https://github.com/testowner/testrepo/commit/")

    def test_describe_what_changed_conventional_commit(self, generator, sample_user):
        """Test describing changes from conventional commit message."""
        commit = self.create_commit(
            "feat: implement JWT token authentication",
            user=sample_user
        )
        file_changes = self.create_file_changes([("auth.py", 50, 10)])
        
        what_changed = generator._describe_what_changed(commit, file_changes)
        
        assert "implement JWT token authentication" in what_changed
        assert "feat:" not in what_changed  # Prefix should be removed

    def test_describe_what_changed_generic_message(self, generator, sample_user):
        """Test describing changes when commit message is generic."""
        commit = self.create_commit(
            "update stuff",
            user=sample_user
        )
        file_changes = self.create_file_changes([
            ("test_user.py", 20, 5),
            ("test_auth.py", 15, 3)
        ])
        
        what_changed = generator._describe_what_changed(commit, file_changes)
        
        # Should infer from files since message is generic
        assert "test" in what_changed.lower()

    def test_infer_changes_from_files_test_files(self, generator):
        """Test inferring changes from test files."""
        file_changes = self.create_file_changes([
            ("test_user.py", 30, 5),
            ("test_auth.py", 20, 3)
        ])
        
        description = generator._infer_changes_from_files(file_changes)
        
        assert "test" in description.lower()

    def test_infer_changes_from_files_doc_files(self, generator):
        """Test inferring changes from documentation files."""
        file_changes = self.create_file_changes([
            ("README.md", 20, 5),
            ("docs/guide.md", 15, 2)
        ])
        
        description = generator._infer_changes_from_files(file_changes)
        
        assert "documentation" in description.lower()

    def test_infer_changes_from_files_config_files(self, generator):
        """Test inferring changes from configuration files."""
        file_changes = self.create_file_changes([
            ("config.py", 10, 5),
            ("settings.json", 5, 2)
        ])
        
        description = generator._infer_changes_from_files(file_changes)
        
        assert "config" in description.lower()

    def test_infer_changes_from_files_core_files(self, generator):
        """Test inferring changes from core files."""
        file_changes = self.create_file_changes([
            ("main.py", 50, 10),
            ("app.py", 30, 5)
        ])
        
        description = generator._infer_changes_from_files(file_changes)
        
        assert "core" in description.lower() or "application" in description.lower()

    def test_infer_changes_from_files_single_file(self, generator):
        """Test inferring changes from single file."""
        file_changes = self.create_file_changes([("utils.py", 20, 5)])
        
        description = generator._infer_changes_from_files(file_changes)
        
        assert "utils.py" in description

    def test_infer_changes_from_files_multiple_mixed(self, generator):
        """Test inferring changes from multiple mixed files."""
        file_changes = self.create_file_changes([
            ("user.py", 20, 5),
            ("auth.py", 15, 3),
            ("utils.py", 10, 2)
        ])
        
        description = generator._infer_changes_from_files(file_changes)
        
        assert "3 files" in description

    def test_is_generic_message_generic_cases(self, generator):
        """Test identifying generic commit messages."""
        generic_messages = [
            "update",
            "fix",
            "changes",
            "wip",
            "stuff",
            "misc"
        ]
        
        for message in generic_messages:
            assert generator._is_generic_message(message)

    def test_is_generic_message_specific_cases(self, generator):
        """Test identifying specific commit messages."""
        specific_messages = [
            "fix user authentication bug",
            "update README with new instructions",
            "add comprehensive test coverage",
            "refactor database connection logic"
        ]
        
        for message in specific_messages:
            assert not generator._is_generic_message(message)

    def test_assess_main_repo_value_bugfix(self, generator, sample_user):
        """Test main repo value assessment for bugfix."""
        commit = self.create_commit("fix: resolve critical issue", user=sample_user)
        file_changes = self.create_file_changes([("main.py", 10, 5)])
        
        value = generator._assess_main_repo_value(commit, CategoryType.BUGFIX, file_changes)
        
        assert value == MainRepoValue.YES

    def test_assess_main_repo_value_security(self, generator, sample_user):
        """Test main repo value assessment for security."""
        commit = self.create_commit("security: fix vulnerability", user=sample_user)
        file_changes = self.create_file_changes([("auth.py", 20, 10)])
        
        value = generator._assess_main_repo_value(commit, CategoryType.SECURITY, file_changes)
        
        assert value == MainRepoValue.YES

    def test_assess_main_repo_value_performance(self, generator, sample_user):
        """Test main repo value assessment for performance."""
        commit = self.create_commit("perf: optimize database queries", user=sample_user)
        file_changes = self.create_file_changes([("db.py", 30, 15)])
        
        value = generator._assess_main_repo_value(commit, CategoryType.PERFORMANCE, file_changes)
        
        assert value == MainRepoValue.YES

    def test_assess_main_repo_value_feature_large(self, generator, sample_user):
        """Test main repo value assessment for large feature."""
        commit = self.create_commit("feat: add user management", user=sample_user)
        file_changes = self.create_file_changes([("user.py", 100, 20)])  # Large change
        
        value = generator._assess_main_repo_value(commit, CategoryType.FEATURE, file_changes)
        
        assert value == MainRepoValue.YES

    def test_assess_main_repo_value_feature_small(self, generator, sample_user):
        """Test main repo value assessment for small feature."""
        commit = self.create_commit("feat: add helper function", user=sample_user)
        file_changes = self.create_file_changes([("utils.py", 10, 2)])  # Small change
        
        value = generator._assess_main_repo_value(commit, CategoryType.FEATURE, file_changes)
        
        assert value == MainRepoValue.UNCLEAR

    def test_assess_main_repo_value_chore_security(self, generator, sample_user):
        """Test main repo value assessment for security-related chore."""
        commit = self.create_commit("chore: update dependencies for security", user=sample_user)
        file_changes = self.create_file_changes([("requirements.txt", 5, 5)])
        
        value = generator._assess_main_repo_value(commit, CategoryType.CHORE, file_changes)
        
        assert value == MainRepoValue.YES

    def test_assess_main_repo_value_chore_general(self, generator, sample_user):
        """Test main repo value assessment for general chore."""
        commit = self.create_commit("chore: cleanup old files", user=sample_user)
        file_changes = self.create_file_changes([("old_file.py", 0, 50)])
        
        value = generator._assess_main_repo_value(commit, CategoryType.CHORE, file_changes)
        
        assert value == MainRepoValue.NO

    def test_is_complex_commit_multiple_categories(self, generator, sample_user):
        """Test complexity detection for commits touching multiple categories."""
        commit = self.create_commit("add feature with tests and docs", user=sample_user)
        file_changes = self.create_file_changes([
            ("feature.py", 50, 10),      # code
            ("test_feature.py", 30, 5),  # test
            ("README.md", 20, 3),        # doc
            ("config.py", 10, 2)         # config
        ])
        
        is_complex = generator._is_complex_commit(commit, file_changes)
        
        assert is_complex

    def test_is_complex_commit_many_files(self, generator, sample_user):
        """Test complexity detection for commits with many files."""
        commit = self.create_commit("large refactoring", user=sample_user)
        file_changes = self.create_file_changes([
            (f"file{i}.py", 10, 5) for i in range(15)  # Many files
        ])
        
        is_complex = generator._is_complex_commit(commit, file_changes)
        
        assert is_complex

    def test_is_complex_commit_multiple_actions(self, generator, sample_user):
        """Test complexity detection for commits with multiple actions."""
        commit = self.create_commit("add feature, fix bug, and update docs", user=sample_user)
        file_changes = self.create_file_changes([("main.py", 30, 10)])
        
        is_complex = generator._is_complex_commit(commit, file_changes)
        
        assert is_complex

    def test_is_complex_commit_simple_case(self, generator, sample_user):
        """Test complexity detection for simple commits."""
        commit = self.create_commit("fix authentication bug", user=sample_user)
        file_changes = self.create_file_changes([("auth.py", 20, 5)])
        
        is_complex = generator._is_complex_commit(commit, file_changes)
        
        assert not is_complex

    def test_generate_full_explanation_simple_commit(self, generator, sample_user):
        """Test generating full explanation for simple commit."""
        commit = self.create_commit("fix: resolve login issue", user=sample_user)
        
        explanation = generator._generate_full_explanation(
            commit,
            CategoryType.BUGFIX,
            "login issue",
            MainRepoValue.YES,
            is_complex=False
        )
        
        assert "fixes" in explanation.lower() or "resolves" in explanation.lower()
        assert "login issue" in explanation.lower()
        assert "useful" in explanation.lower() or "benefit" in explanation.lower()

    def test_generate_full_explanation_complex_commit(self, generator, sample_user):
        """Test generating full explanation for complex commit."""
        commit = self.create_commit("add feature and fix bugs", user=sample_user)
        
        explanation = generator._generate_full_explanation(
            commit,
            CategoryType.FEATURE,
            "multiple changes",
            MainRepoValue.UNCLEAR,
            is_complex=True
        )
        
        assert "multiple things" in explanation.lower() or "complex" in explanation.lower()
        assert "unclear" in explanation.lower() or "uncertain" in explanation.lower()

    def test_ensure_brevity_long_explanation(self, generator):
        """Test ensuring brevity for long explanations."""
        long_explanation = "This is the first sentence. This is the second sentence. This is the third sentence. This is the fourth sentence."
        
        brief_explanation = generator._ensure_brevity(long_explanation, max_sentences=2)
        
        sentences = brief_explanation.split('. ')
        assert len(sentences) <= 2
        assert brief_explanation.endswith('.')

    def test_ensure_brevity_short_explanation(self, generator):
        """Test ensuring brevity for already short explanations."""
        short_explanation = "This is a short explanation."
        
        brief_explanation = generator._ensure_brevity(short_explanation, max_sentences=2)
        
        assert brief_explanation == short_explanation

    def test_ensure_brevity_no_punctuation(self, generator):
        """Test ensuring brevity adds punctuation if missing."""
        explanation = "This is an explanation without punctuation"
        
        brief_explanation = generator._ensure_brevity(explanation)
        
        assert brief_explanation.endswith('.')

    def test_generate_explanation_comprehensive_workflow(self, generator, sample_user, sample_repository):
        """Test the complete explanation generation workflow."""
        commit = self.create_commit(
            "feat: implement user authentication with JWT tokens and add comprehensive tests",
            files=["auth.py", "user_service.py", "test_auth.py"],
            user=sample_user
        )
        file_changes = self.create_file_changes([
            ("auth.py", 80, 10),
            ("user_service.py", 60, 15),
            ("test_auth.py", 40, 5)
        ])
        
        what_changed, explanation, main_repo_value, is_complex, github_url = generator.generate_explanation(
            commit, CategoryType.FEATURE, ImpactLevel.HIGH, file_changes, sample_repository
        )
        
        # Verify all components
        assert len(what_changed) > 0
        assert len(explanation) > 0
        assert main_repo_value in [MainRepoValue.YES, MainRepoValue.NO, MainRepoValue.UNCLEAR]
        assert isinstance(is_complex, bool)
        assert github_url.startswith("https://github.com/testowner/testrepo/commit/")
        assert commit.sha in github_url
        
        # Verify explanation is properly formatted
        assert explanation.endswith('.')
        sentences = explanation.split('. ')
        assert len(sentences) <= 2  # Should be brief

    def test_generate_github_commit_url(self, generator, sample_user, sample_repository):
        """Test GitHub commit URL generation."""
        commit = self.create_commit("test commit", user=sample_user)
        
        github_url = generator._generate_github_commit_url(commit, sample_repository)
        
        expected_url = f"https://github.com/{sample_repository.owner}/{sample_repository.name}/commit/{commit.sha}"
        assert github_url == expected_url

    def test_generate_github_commit_url_fallback(self, generator, sample_user, sample_repository):
        """Test GitHub commit URL generation with fallback for GitHubLinkGenerator errors."""
        from unittest.mock import patch
        
        commit = self.create_commit("test commit", user=sample_user)
        
        # Mock GitHubLinkGenerator to raise an exception
        with patch('forklift.analysis.explanation_generator.GitHubLinkGenerator.generate_commit_url') as mock_generate:
            mock_generate.side_effect = ValueError("Test error")
            
            github_url = generator._generate_github_commit_url(commit, sample_repository)
            
            # Should return fallback URL
            expected_fallback = f"https://github.com/{sample_repository.owner}/{sample_repository.name}/commit/{commit.sha}"
            assert github_url == expected_fallback