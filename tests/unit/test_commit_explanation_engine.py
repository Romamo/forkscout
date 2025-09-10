"""Unit tests for CommitExplanationEngine."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from forkscout.analysis.commit_categorizer import CommitCategorizer
from forkscout.analysis.commit_explanation_engine import CommitExplanationEngine
from forkscout.analysis.explanation_generator import ExplanationGenerator
from forkscout.analysis.impact_assessor import ImpactAssessor
from forkscout.models import (
    AnalysisContext,
    CategoryType,
    Commit,
    CommitCategory,
    CommitExplanation,
    CommitWithExplanation,
    FileChange,
    Fork,
    ImpactAssessment,
    ImpactLevel,
    MainRepoValue,
    Repository,
    User,
)


class TestCommitExplanationEngine:
    """Test CommitExplanationEngine class."""

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

    @pytest.fixture
    def sample_fork(self, sample_repository):
        """Create a sample fork."""
        fork_repo = Repository(
            owner="forkowner",
            name="testrepo",
            full_name="forkowner/testrepo",
            url="https://api.github.com/repos/forkowner/testrepo",
            html_url="https://github.com/forkowner/testrepo",
            clone_url="https://github.com/forkowner/testrepo.git",
            is_fork=True
        )

        user = User(
            login="forkowner",
            html_url="https://github.com/forkowner"
        )

        return Fork(
            repository=fork_repo,
            parent=sample_repository,
            owner=user
        )

    @pytest.fixture
    def sample_context(self, sample_repository, sample_fork):
        """Create a sample analysis context."""
        return AnalysisContext(
            repository=sample_repository,
            fork=sample_fork,
            project_type="web",
            main_language="python",
            critical_files=["main.py", "config.py"]
        )

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            login="testuser",
            html_url="https://github.com/testuser"
        )

    @pytest.fixture
    def sample_commit(self, sample_user):
        """Create a sample commit."""
        return Commit(
            sha="a1b2c3d4e5f6789012345678901234567890abcd",
            message="feat: add user authentication system",
            author=sample_user,
            date=datetime.utcnow(),
            additions=100,
            deletions=20,
            files_changed=["auth.py", "user_service.py"]
        )

    @pytest.fixture
    def sample_file_changes(self):
        """Create sample file changes."""
        return [
            FileChange(filename="auth.py", status="modified", additions=80, deletions=15),
            FileChange(filename="user_service.py", status="modified", additions=20, deletions=5)
        ]

    @pytest.fixture
    def engine(self):
        """Create a CommitExplanationEngine instance."""
        return CommitExplanationEngine()

    @pytest.fixture
    def mock_engine(self):
        """Create a CommitExplanationEngine with mocked components."""
        mock_categorizer = Mock(spec=CommitCategorizer)
        mock_assessor = Mock(spec=ImpactAssessor)
        mock_generator = Mock(spec=ExplanationGenerator)

        return CommitExplanationEngine(
            categorizer=mock_categorizer,
            assessor=mock_assessor,
            generator=mock_generator
        )

    def test_engine_initialization_default_components(self):
        """Test engine initialization with default components."""
        engine = CommitExplanationEngine()

        assert engine.categorizer is not None
        assert engine.assessor is not None
        assert engine.generator is not None
        assert isinstance(engine.categorizer, CommitCategorizer)
        assert isinstance(engine.assessor, ImpactAssessor)
        assert isinstance(engine.generator, ExplanationGenerator)

    def test_engine_initialization_custom_components(self):
        """Test engine initialization with custom components."""
        categorizer = CommitCategorizer()
        assessor = ImpactAssessor()
        generator = ExplanationGenerator()

        engine = CommitExplanationEngine(
            categorizer=categorizer,
            assessor=assessor,
            generator=generator
        )

        assert engine.categorizer is categorizer
        assert engine.assessor is assessor
        assert engine.generator is generator

    def test_explain_commit_success(
        self, engine, sample_commit, sample_context, sample_file_changes
    ):
        """Test successful commit explanation."""
        explanation = engine.explain_commit(
            sample_commit, sample_context, sample_file_changes
        )

        assert isinstance(explanation, CommitExplanation)
        assert explanation.commit_sha == sample_commit.sha
        assert explanation.category is not None
        assert explanation.impact_assessment is not None
        assert explanation.what_changed is not None
        assert explanation.explanation is not None
        assert explanation.main_repo_value in [MainRepoValue.YES, MainRepoValue.NO, MainRepoValue.UNCLEAR]
        assert isinstance(explanation.is_complex, bool)
        assert isinstance(explanation.generated_at, datetime)
        assert explanation.github_url is not None
        assert explanation.github_url.startswith("https://github.com/")

    def test_explain_commit_without_file_changes(
        self, engine, sample_commit, sample_context
    ):
        """Test commit explanation without explicit file changes."""
        explanation = engine.explain_commit(sample_commit, sample_context)

        assert isinstance(explanation, CommitExplanation)
        assert explanation.commit_sha == sample_commit.sha
        # Should work by inferring file changes from commit.files_changed

    def test_explain_commit_with_mocked_components(
        self, mock_engine, sample_commit, sample_context, sample_file_changes
    ):
        """Test commit explanation with mocked components."""
        # Setup mocks
        mock_category = CommitCategory(
            category_type=CategoryType.FEATURE,
            confidence=0.9,
            reasoning="Test category"
        )
        mock_engine.categorizer.categorize_commit.return_value = mock_category

        mock_impact = ImpactAssessment(
            impact_level=ImpactLevel.HIGH,
            change_magnitude=5.0,
            file_criticality=0.8,
            reasoning="Test impact"
        )
        mock_engine.assessor.assess_impact.return_value = mock_impact

        mock_engine.generator.generate_explanation.return_value = (
            "user authentication system",
            "This commit adds user authentication system. This could be useful for the main repository.",
            MainRepoValue.YES,
            False,
            "https://github.com/testowner/testrepo/commit/a1b2c3d4e5f6789012345678901234567890abcd"
        )

        # Test explanation
        explanation = mock_engine.explain_commit(
            sample_commit, sample_context, sample_file_changes
        )

        # Verify mocks were called
        mock_engine.categorizer.categorize_commit.assert_called_once_with(
            sample_commit, sample_file_changes
        )
        mock_engine.assessor.assess_impact.assert_called_once_with(
            sample_commit, sample_file_changes, sample_context
        )
        mock_engine.generator.generate_explanation.assert_called_once_with(
            sample_commit, CategoryType.FEATURE, ImpactLevel.HIGH, sample_file_changes, sample_context.repository
        )

        # Verify result
        assert explanation.commit_sha == sample_commit.sha
        assert explanation.category == mock_category
        assert explanation.impact_assessment == mock_impact
        assert explanation.what_changed == "user authentication system"
        assert explanation.main_repo_value == MainRepoValue.YES
        assert not explanation.is_complex
        assert explanation.github_url == "https://github.com/testowner/testrepo/commit/a1b2c3d4e5f6789012345678901234567890abcd"

    def test_explain_commit_error_handling(
        self, mock_engine, sample_commit, sample_context
    ):
        """Test error handling in commit explanation."""
        # Make categorizer raise an exception
        mock_engine.categorizer.categorize_commit.side_effect = Exception("Categorization failed")

        with pytest.raises(Exception, match="Categorization failed"):
            mock_engine.explain_commit(sample_commit, sample_context)

    def test_explain_commits_batch_success(
        self, engine, sample_context, sample_user
    ):
        """Test successful batch commit explanation."""
        commits = [
            Commit(
                sha=f"a{i}b2c3d4e5f6789012345678901234567890abc{i}",
                message=f"feat: add feature {i}",
                author=sample_user,
                date=datetime.utcnow(),
                files_changed=[f"feature{i}.py"]
            )
            for i in range(3)
        ]

        results = engine.explain_commits_batch(commits, sample_context)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, CommitWithExplanation)
            assert result.commit is not None
            assert result.explanation is not None or result.explanation_error is not None

    def test_explain_commits_batch_with_file_changes_map(
        self, engine, sample_context, sample_user
    ):
        """Test batch explanation with file changes map."""
        commits = [
            Commit(
                sha="a1b2c3d4e5f6789012345678901234567890abc1",
                message="feat: add feature 1",
                author=sample_user,
                date=datetime.utcnow(),
                files_changed=["feature1.py"]
            )
        ]

        file_changes_map = {
            "a1b2c3d4e5f6789012345678901234567890abc1": [
                FileChange(filename="feature1.py", status="added", additions=50, deletions=0)
            ]
        }

        results = engine.explain_commits_batch(commits, sample_context, file_changes_map)

        assert len(results) == 1
        assert results[0].explanation is not None

    def test_explain_commits_batch_with_errors(
        self, mock_engine, sample_context, sample_user
    ):
        """Test batch explanation with some failures."""
        commits = [
            Commit(
                sha="a1b2c3d4e5f6789012345678901234567890abcd",
                message="feat: good commit",
                author=sample_user,
                date=datetime.utcnow(),
                files_changed=["good.py"]
            ),
            Commit(
                sha="b1c2d3e4f5a6789012345678901234567890abcd",
                message="bad commit",
                author=sample_user,
                date=datetime.utcnow(),
                files_changed=["bad.py"]
            )
        ]

        # Mock to succeed for first commit, fail for second
        def mock_explain_commit(commit, context, file_changes=None):
            if commit.sha == "a1b2c3d4e5f6789012345678901234567890abcd":
                return CommitExplanation(
                    commit_sha=commit.sha,
                    category=CommitCategory(
                        category_type=CategoryType.FEATURE,
                        confidence=0.9,
                        reasoning="Test"
                    ),
                    impact_assessment=ImpactAssessment(
                        impact_level=ImpactLevel.MEDIUM,
                        change_magnitude=2.0,
                        file_criticality=0.5,
                        reasoning="Test"
                    ),
                    what_changed="good changes",
                    main_repo_value=MainRepoValue.YES,
                    explanation="Good commit explanation.",
                    github_url="https://github.com/testowner/testrepo/commit/a1b2c3d4e5f6789012345678901234567890abcd"
                )
            else:
                raise Exception("Bad commit error")

        mock_engine.explain_commit = mock_explain_commit

        results = mock_engine.explain_commits_batch(commits, sample_context)

        assert len(results) == 2
        assert results[0].explanation is not None
        assert results[0].explanation_error is None
        assert results[1].explanation is None
        assert results[1].explanation_error == "Bad commit error"

    def test_is_explanation_enabled(self, engine):
        """Test explanation enabled check."""
        assert engine.is_explanation_enabled() is True

    def test_get_explanation_summary_empty(self, engine):
        """Test explanation summary with no explanations."""
        summary = engine.get_explanation_summary([])
        assert "No commit explanations generated" in summary

    def test_get_explanation_summary_with_explanations(self, engine):
        """Test explanation summary with explanations."""
        explanations = [
            CommitExplanation(
                commit_sha="commit1" + "0" * 33,
                category=CommitCategory(
                    category_type=CategoryType.FEATURE,
                    confidence=0.9,
                    reasoning="Test"
                ),
                impact_assessment=ImpactAssessment(
                    impact_level=ImpactLevel.HIGH,
                    change_magnitude=3.0,
                    file_criticality=0.8,
                    reasoning="Test"
                ),
                what_changed="feature implementation",
                main_repo_value=MainRepoValue.YES,
                explanation="Feature explanation.",
                is_complex=False,
                github_url="https://github.com/testowner/testrepo/commit/commit1000000000000000000000000000000000"
            ),
            CommitExplanation(
                commit_sha="commit2" + "0" * 33,
                category=CommitCategory(
                    category_type=CategoryType.BUGFIX,
                    confidence=0.8,
                    reasoning="Test"
                ),
                impact_assessment=ImpactAssessment(
                    impact_level=ImpactLevel.MEDIUM,
                    change_magnitude=1.5,
                    file_criticality=0.6,
                    reasoning="Test"
                ),
                what_changed="bug fix",
                main_repo_value=MainRepoValue.YES,
                explanation="Bug fix explanation.",
                is_complex=True,
                github_url="https://github.com/testowner/testrepo/commit/commit2000000000000000000000000000000000"
            )
        ]

        summary = engine.get_explanation_summary(explanations)

        assert "Analyzed 2 commits" in summary
        assert "feature" in summary.lower()
        assert "bugfix" in summary.lower()
        assert "high" in summary.lower()
        assert "medium" in summary.lower()
        assert "2 commits could benefit" in summary
        assert "1 commits are complex" in summary

    def test_validate_explanation_valid(self, engine):
        """Test validation of valid explanation."""
        explanation = CommitExplanation(
            commit_sha="a1b2c3d4e5f6789012345678901234567890abcd",
            category=CommitCategory(
                category_type=CategoryType.FEATURE,
                confidence=0.9,
                reasoning="Test category"
            ),
            impact_assessment=ImpactAssessment(
                impact_level=ImpactLevel.HIGH,
                change_magnitude=3.0,
                file_criticality=0.8,
                reasoning="Test impact"
            ),
            what_changed="user authentication system",
            main_repo_value=MainRepoValue.YES,
            explanation="This commit adds user authentication system. This could be useful for the main repository.",
            github_url="https://github.com/testowner/testrepo/commit/a1b2c3d4e5f6789012345678901234567890abcd"
        )

        errors = engine.validate_explanation(explanation)
        assert len(errors) == 0

    def test_validate_explanation_missing_fields(self, engine):
        """Test validation of explanation with missing fields."""
        explanation = CommitExplanation(
            commit_sha="",  # Missing
            category=CommitCategory(
                category_type=CategoryType.FEATURE,
                confidence=0.9,
                reasoning="Test"
            ),
            impact_assessment=ImpactAssessment(
                impact_level=ImpactLevel.HIGH,
                change_magnitude=3.0,
                file_criticality=0.8,
                reasoning="Test"
            ),
            what_changed="",  # Missing
            main_repo_value=MainRepoValue.YES,
            explanation="",  # Missing
            github_url=""  # Missing
        )

        errors = engine.validate_explanation(explanation)

        assert "Missing commit SHA" in errors
        assert "Missing 'what changed' description" in errors
        assert "Missing explanation text" in errors
        assert "Missing GitHub URL" in errors

    def test_validate_explanation_quality_issues(self, engine):
        """Test validation of explanation with quality issues."""
        # Create a valid impact assessment first, then test validation logic
        explanation = CommitExplanation(
            commit_sha="a1b2c3d4e5f6789012345678901234567890abcd",
            category=CommitCategory(
                category_type=CategoryType.FEATURE,
                confidence=0.05,  # Too low
                reasoning="Test"
            ),
            impact_assessment=ImpactAssessment(
                impact_level=ImpactLevel.HIGH,
                change_magnitude=1.0,  # Valid for creation
                file_criticality=0.8,  # Valid for creation
                reasoning="Test"
            ),
            what_changed="fix",  # Too short
            main_repo_value=MainRepoValue.YES,
            explanation="Short.",  # Too short
            github_url="https://github.com/testowner/testrepo/commit/a1b2c3d4e5f6789012345678901234567890abcd"
        )

        # Manually set invalid values after creation to test validation
        explanation.impact_assessment.change_magnitude = -1.0
        explanation.impact_assessment.file_criticality = 1.5

        errors = engine.validate_explanation(explanation)

        assert "Category confidence is too low" in errors
        assert "Invalid change magnitude" in errors
        assert "File criticality must be between 0 and 1" in errors
        assert "'What changed' description is too short" in errors
        assert "Explanation is too short" in errors

    def test_get_engine_stats(self, engine):
        """Test getting engine statistics."""
        stats = engine.get_engine_stats()

        assert "categorizer_patterns" in stats
        assert "assessor_rules" in stats
        assert "generator_templates" in stats
        assert "explanation_enabled" in stats

        assert isinstance(stats["categorizer_patterns"], int)
        assert isinstance(stats["assessor_rules"], int)
        assert isinstance(stats["generator_templates"], int)
        assert stats["explanation_enabled"] is True

    @patch("forklift.analysis.commit_explanation_engine.logger")
    def test_logging_during_explanation(
        self, mock_logger, engine, sample_commit, sample_context
    ):
        """Test that appropriate logging occurs during explanation."""
        engine.explain_commit(sample_commit, sample_context)

        # Verify debug logging was called
        assert mock_logger.debug.called

        # Check for specific log messages
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("Explaining commit" in msg for msg in debug_calls)
        assert any("Successfully explained commit" in msg for msg in debug_calls)

    @patch("forklift.analysis.commit_explanation_engine.logger")
    def test_logging_during_batch_explanation(
        self, mock_logger, engine, sample_context, sample_user
    ):
        """Test that appropriate logging occurs during batch explanation."""
        commits = [
            Commit(
                sha="a1b2c3d4e5f6789012345678901234567890abc1",
                message="feat: test commit",
                author=sample_user,
                date=datetime.utcnow(),
                files_changed=["test.py"]
            )
        ]

        engine.explain_commits_batch(commits, sample_context)

        # Verify info logging was called
        assert mock_logger.info.called

        # Check for specific log messages
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Explaining 1 commits in batch" in msg for msg in info_calls)
        assert any("Successfully explained" in msg for msg in info_calls)
