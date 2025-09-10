"""Unit tests for commit explanation data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

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


class TestCategoryType:
    """Test CategoryType enum."""

    def test_category_type_values(self):
        """Test that all expected category types are available."""
        expected_values = {
            "feature", "bugfix", "refactor", "docs", "test",
            "chore", "performance", "security", "other"
        }
        actual_values = {category.value for category in CategoryType}
        assert actual_values == expected_values

    def test_category_type_string_conversion(self):
        """Test that category types convert to strings correctly."""
        assert CategoryType.FEATURE.value == "feature"
        assert CategoryType.BUGFIX.value == "bugfix"
        assert CategoryType.DOCS.value == "docs"


class TestImpactLevel:
    """Test ImpactLevel enum."""

    def test_impact_level_values(self):
        """Test that all expected impact levels are available."""
        expected_values = {"low", "medium", "high", "critical"}
        actual_values = {level.value for level in ImpactLevel}
        assert actual_values == expected_values

    def test_impact_level_string_conversion(self):
        """Test that impact levels convert to strings correctly."""
        assert ImpactLevel.LOW.value == "low"
        assert ImpactLevel.HIGH.value == "high"
        assert ImpactLevel.CRITICAL.value == "critical"


class TestMainRepoValue:
    """Test MainRepoValue enum."""

    def test_main_repo_value_values(self):
        """Test that all expected main repo values are available."""
        expected_values = {"yes", "no", "unclear"}
        actual_values = {value.value for value in MainRepoValue}
        assert actual_values == expected_values

    def test_main_repo_value_string_conversion(self):
        """Test that main repo values convert to strings correctly."""
        assert MainRepoValue.YES.value == "yes"
        assert MainRepoValue.NO.value == "no"
        assert MainRepoValue.UNCLEAR.value == "unclear"


class TestFileChange:
    """Test FileChange model."""

    def test_file_change_creation_with_required_fields(self):
        """Test creating FileChange with required fields."""
        file_change = FileChange(
            filename="test.py",
            status="modified"
        )

        assert file_change.filename == "test.py"
        assert file_change.status == "modified"
        assert file_change.additions == 0
        assert file_change.deletions == 0
        assert file_change.patch is None

    def test_file_change_creation_with_all_fields(self):
        """Test creating FileChange with all fields."""
        file_change = FileChange(
            filename="src/main.py",
            status="added",
            additions=50,
            deletions=10,
            patch="@@ -1,3 +1,4 @@\n+new line\n old line"
        )

        assert file_change.filename == "src/main.py"
        assert file_change.status == "added"
        assert file_change.additions == 50
        assert file_change.deletions == 10
        assert file_change.patch == "@@ -1,3 +1,4 @@\n+new line\n old line"

    def test_file_change_negative_additions_validation(self):
        """Test that negative additions are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FileChange(
                filename="test.py",
                status="modified",
                additions=-5
            )

        assert "greater than or equal to 0" in str(exc_info.value)

    def test_file_change_negative_deletions_validation(self):
        """Test that negative deletions are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FileChange(
                filename="test.py",
                status="modified",
                deletions=-3
            )

        assert "greater than or equal to 0" in str(exc_info.value)

    def test_file_change_serialization(self):
        """Test FileChange serialization."""
        file_change = FileChange(
            filename="test.py",
            status="modified",
            additions=10,
            deletions=5
        )

        data = file_change.model_dump()
        expected = {
            "filename": "test.py",
            "status": "modified",
            "additions": 10,
            "deletions": 5,
            "patch": None
        }
        assert data == expected


class TestCommitCategory:
    """Test CommitCategory model."""

    def test_commit_category_creation(self):
        """Test creating CommitCategory with valid data."""
        category = CommitCategory(
            category_type=CategoryType.FEATURE,
            confidence=0.85,
            reasoning="Contains 'add' keyword and modifies core functionality"
        )

        assert category.category_type == CategoryType.FEATURE
        assert category.confidence == 0.85
        assert "add" in category.reasoning

    def test_commit_category_confidence_validation(self):
        """Test confidence score validation."""
        # Valid confidence scores
        CommitCategory(
            category_type=CategoryType.BUGFIX,
            confidence=0.0,
            reasoning="Test"
        )

        CommitCategory(
            category_type=CategoryType.BUGFIX,
            confidence=1.0,
            reasoning="Test"
        )

        # Invalid confidence scores
        with pytest.raises(ValidationError):
            CommitCategory(
                category_type=CategoryType.BUGFIX,
                confidence=-0.1,
                reasoning="Test"
            )

        with pytest.raises(ValidationError):
            CommitCategory(
                category_type=CategoryType.BUGFIX,
                confidence=1.1,
                reasoning="Test"
            )

    def test_commit_category_serialization(self):
        """Test CommitCategory serialization."""
        category = CommitCategory(
            category_type=CategoryType.DOCS,
            confidence=0.9,
            reasoning="Updates README file"
        )

        data = category.model_dump()
        expected = {
            "category_type": "docs",
            "confidence": 0.9,
            "reasoning": "Updates README file"
        }
        assert data == expected


class TestImpactAssessment:
    """Test ImpactAssessment model."""

    def test_impact_assessment_creation(self):
        """Test creating ImpactAssessment with valid data."""
        assessment = ImpactAssessment(
            impact_level=ImpactLevel.HIGH,
            change_magnitude=150.5,
            file_criticality=0.8,
            quality_factors={"test_coverage": 0.9, "documentation": 0.7},
            reasoning="Large change to critical system component"
        )

        assert assessment.impact_level == ImpactLevel.HIGH
        assert assessment.change_magnitude == 150.5
        assert assessment.file_criticality == 0.8
        assert assessment.quality_factors["test_coverage"] == 0.9
        assert "critical" in assessment.reasoning

    def test_impact_assessment_file_criticality_validation(self):
        """Test file criticality validation."""
        # Valid criticality scores
        ImpactAssessment(
            impact_level=ImpactLevel.LOW,
            change_magnitude=10.0,
            file_criticality=0.0,
            reasoning="Test"
        )

        ImpactAssessment(
            impact_level=ImpactLevel.LOW,
            change_magnitude=10.0,
            file_criticality=1.0,
            reasoning="Test"
        )

        # Invalid criticality scores
        with pytest.raises(ValidationError):
            ImpactAssessment(
                impact_level=ImpactLevel.LOW,
                change_magnitude=10.0,
                file_criticality=-0.1,
                reasoning="Test"
            )

        with pytest.raises(ValidationError):
            ImpactAssessment(
                impact_level=ImpactLevel.LOW,
                change_magnitude=10.0,
                file_criticality=1.1,
                reasoning="Test"
            )

    def test_impact_assessment_change_magnitude_validation(self):
        """Test change magnitude validation."""
        # Valid magnitude
        ImpactAssessment(
            impact_level=ImpactLevel.LOW,
            change_magnitude=0.0,
            file_criticality=0.5,
            reasoning="Test"
        )

        # Invalid magnitude
        with pytest.raises(ValidationError):
            ImpactAssessment(
                impact_level=ImpactLevel.LOW,
                change_magnitude=-1.0,
                file_criticality=0.5,
                reasoning="Test"
            )

    def test_impact_assessment_serialization(self):
        """Test ImpactAssessment serialization."""
        assessment = ImpactAssessment(
            impact_level=ImpactLevel.MEDIUM,
            change_magnitude=50.0,
            file_criticality=0.6,
            quality_factors={"tests": 0.8},
            reasoning="Moderate impact"
        )

        data = assessment.model_dump()
        expected = {
            "impact_level": "medium",
            "change_magnitude": 50.0,
            "file_criticality": 0.6,
            "quality_factors": {"tests": 0.8},
            "reasoning": "Moderate impact"
        }
        assert data == expected


class TestAnalysisContext:
    """Test AnalysisContext model."""

    @pytest.fixture
    def sample_repository(self):
        """Create a sample repository for testing."""
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
        """Create a sample fork for testing."""
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

    def test_analysis_context_creation_minimal(self, sample_repository, sample_fork):
        """Test creating AnalysisContext with minimal required fields."""
        context = AnalysisContext(
            repository=sample_repository,
            fork=sample_fork
        )

        assert context.repository == sample_repository
        assert context.fork == sample_fork
        assert context.project_type is None
        assert context.main_language is None
        assert context.critical_files == []

    def test_analysis_context_creation_full(self, sample_repository, sample_fork):
        """Test creating AnalysisContext with all fields."""
        context = AnalysisContext(
            repository=sample_repository,
            fork=sample_fork,
            project_type="web",
            main_language="python",
            critical_files=["main.py", "config.py", "requirements.txt"]
        )

        assert context.repository == sample_repository
        assert context.fork == sample_fork
        assert context.project_type == "web"
        assert context.main_language == "python"
        assert context.critical_files == ["main.py", "config.py", "requirements.txt"]

    def test_analysis_context_serialization(self, sample_repository, sample_fork):
        """Test AnalysisContext serialization."""
        context = AnalysisContext(
            repository=sample_repository,
            fork=sample_fork,
            project_type="library",
            main_language="python"
        )

        data = context.model_dump()
        assert data["project_type"] == "library"
        assert data["main_language"] == "python"
        assert data["critical_files"] == []


class TestCommitExplanation:
    """Test CommitExplanation model."""

    @pytest.fixture
    def sample_category(self):
        """Create a sample commit category."""
        return CommitCategory(
            category_type=CategoryType.FEATURE,
            confidence=0.9,
            reasoning="Adds new functionality"
        )

    @pytest.fixture
    def sample_impact_assessment(self):
        """Create a sample impact assessment."""
        return ImpactAssessment(
            impact_level=ImpactLevel.HIGH,
            change_magnitude=100.0,
            file_criticality=0.8,
            reasoning="Significant change to core module"
        )

    def test_commit_explanation_creation(self, sample_category, sample_impact_assessment):
        """Test creating CommitExplanation with valid data."""
        explanation = CommitExplanation(
            commit_sha="a1b2c3d4e5f6789012345678901234567890abcd",
            category=sample_category,
            impact_assessment=sample_impact_assessment,
            what_changed="Added user authentication system",
            main_repo_value=MainRepoValue.YES,
            explanation="This commit adds a comprehensive user authentication system with JWT tokens.",
            is_complex=False,
            github_url="https://github.com/test/repo/commit/a1b2c3d4e5f6789012345678901234567890abcd"
        )

        assert explanation.commit_sha == "a1b2c3d4e5f6789012345678901234567890abcd"
        assert explanation.category == sample_category
        assert explanation.impact_assessment == sample_impact_assessment
        assert explanation.what_changed == "Added user authentication system"
        assert explanation.main_repo_value == MainRepoValue.YES
        assert "authentication" in explanation.explanation
        assert explanation.is_complex is False
        assert isinstance(explanation.generated_at, datetime)

    def test_commit_explanation_with_complex_commit(self, sample_category, sample_impact_assessment):
        """Test creating CommitExplanation for complex commit."""
        explanation = CommitExplanation(
            commit_sha="b2c3d4e5f6789012345678901234567890abcdef",
            category=sample_category,
            impact_assessment=sample_impact_assessment,
            what_changed="Multiple changes: added auth, fixed bugs, updated docs",
            main_repo_value=MainRepoValue.UNCLEAR,
            explanation="This commit does multiple things at once, making it complex to integrate.",
            is_complex=True,
            github_url="https://github.com/test/repo/commit/b2c3d4e5f6789012345678901234567890abcdef"
        )

        assert explanation.is_complex is True
        assert explanation.main_repo_value == MainRepoValue.UNCLEAR
        assert "multiple things" in explanation.explanation

    def test_commit_explanation_serialization(self, sample_category, sample_impact_assessment):
        """Test CommitExplanation serialization."""
        explanation = CommitExplanation(
            commit_sha="c3d4e5f6789012345678901234567890abcdef12",
            category=sample_category,
            impact_assessment=sample_impact_assessment,
            what_changed="Fixed critical security vulnerability",
            main_repo_value=MainRepoValue.YES,
            explanation="This commit fixes a critical security issue in user input validation.",
            github_url="https://github.com/test/repo/commit/c3d4e5f6789012345678901234567890abcdef12"
        )

        data = explanation.model_dump()
        assert data["commit_sha"] == "c3d4e5f6789012345678901234567890abcdef12"
        assert data["what_changed"] == "Fixed critical security vulnerability"
        assert data["main_repo_value"] == "yes"
        assert data["is_complex"] is False


class TestCommitWithExplanation:
    """Test CommitWithExplanation model."""

    @pytest.fixture
    def sample_commit(self):
        """Create a sample commit."""
        user = User(
            login="testuser",
            html_url="https://github.com/testuser"
        )

        return Commit(
            sha="d4e5f6789012345678901234567890abcdef1234",
            message="Add user authentication",
            author=user,
            date=datetime.utcnow()
        )

    @pytest.fixture
    def sample_explanation(self):
        """Create a sample commit explanation."""
        category = CommitCategory(
            category_type=CategoryType.FEATURE,
            confidence=0.9,
            reasoning="Adds new functionality"
        )

        impact = ImpactAssessment(
            impact_level=ImpactLevel.HIGH,
            change_magnitude=100.0,
            file_criticality=0.8,
            reasoning="Major feature addition"
        )

        return CommitExplanation(
            commit_sha="d4e5f6789012345678901234567890abcdef1234",
            category=category,
            impact_assessment=impact,
            what_changed="Added authentication system",
            main_repo_value=MainRepoValue.YES,
            explanation="This commit adds user authentication with JWT tokens.",
            github_url="https://github.com/test/repo/commit/d4e5f6789012345678901234567890abcdef1234"
        )

    def test_commit_with_explanation_creation_with_explanation(self, sample_commit, sample_explanation):
        """Test creating CommitWithExplanation with explanation."""
        commit_with_explanation = CommitWithExplanation(
            commit=sample_commit,
            explanation=sample_explanation
        )

        assert commit_with_explanation.commit == sample_commit
        assert commit_with_explanation.explanation == sample_explanation
        assert commit_with_explanation.explanation_error is None

    def test_commit_with_explanation_creation_without_explanation(self, sample_commit):
        """Test creating CommitWithExplanation without explanation."""
        commit_with_explanation = CommitWithExplanation(
            commit=sample_commit
        )

        assert commit_with_explanation.commit == sample_commit
        assert commit_with_explanation.explanation is None
        assert commit_with_explanation.explanation_error is None

    def test_commit_with_explanation_creation_with_error(self, sample_commit):
        """Test creating CommitWithExplanation with error."""
        commit_with_explanation = CommitWithExplanation(
            commit=sample_commit,
            explanation_error="Failed to generate explanation: API timeout"
        )

        assert commit_with_explanation.commit == sample_commit
        assert commit_with_explanation.explanation is None
        assert commit_with_explanation.explanation_error == "Failed to generate explanation: API timeout"

    def test_commit_with_explanation_serialization(self, sample_commit, sample_explanation):
        """Test CommitWithExplanation serialization."""
        commit_with_explanation = CommitWithExplanation(
            commit=sample_commit,
            explanation=sample_explanation
        )

        data = commit_with_explanation.model_dump()
        assert "commit" in data
        assert "explanation" in data
        assert data["explanation_error"] is None
        assert data["commit"]["sha"] == sample_commit.sha
        assert data["explanation"]["commit_sha"] == sample_explanation.commit_sha
