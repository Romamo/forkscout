"""Unit tests for ImpactAssessor."""

from datetime import datetime

import pytest

from forklift.analysis.impact_assessor import FileCriticalityRules, ImpactAssessor
from forklift.models import (
    AnalysisContext,
    Commit,
    FileChange,
    Fork,
    ImpactAssessment,
    ImpactLevel,
    Repository,
    User,
)


class TestFileCriticalityRules:
    """Test FileCriticalityRules class."""

    def test_file_criticality_rules_initialization(self):
        """Test that FileCriticalityRules initializes with all expected patterns."""
        rules = FileCriticalityRules()

        # Check that all pattern categories exist
        assert hasattr(rules, "core_patterns")
        assert hasattr(rules, "config_patterns")
        assert hasattr(rules, "security_patterns")
        assert hasattr(rules, "data_patterns")
        assert hasattr(rules, "api_patterns")
        assert hasattr(rules, "test_patterns")
        assert hasattr(rules, "doc_patterns")

        # Check that each category has patterns
        assert len(rules.core_patterns) > 0
        assert len(rules.config_patterns) > 0
        assert len(rules.security_patterns) > 0
        assert len(rules.test_patterns) > 0
        assert len(rules.doc_patterns) > 0


class TestImpactAssessor:
    """Test ImpactAssessor class."""

    @pytest.fixture
    def assessor(self):
        """Create an ImpactAssessor instance."""
        return ImpactAssessor()

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

    def create_commit(
        self,
        message: str,
        additions: int = 10,
        deletions: int = 5,
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
            additions=additions,
            deletions=deletions,
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

    def test_assessor_initialization_default_rules(self):
        """Test assessor initialization with default rules."""
        assessor = ImpactAssessor()
        assert assessor.criticality_rules is not None
        assert isinstance(assessor.criticality_rules, FileCriticalityRules)

    def test_assessor_initialization_custom_rules(self):
        """Test assessor initialization with custom rules."""
        custom_rules = FileCriticalityRules()
        assessor = ImpactAssessor(custom_rules)
        assert assessor.criticality_rules is custom_rules

    def test_assess_impact_small_change(self, assessor, sample_context, sample_user):
        """Test assessing impact of a small change."""
        commit = self.create_commit(
            "fix: minor bug fix",
            additions=5,
            deletions=2,
            user=sample_user
        )
        file_changes = self.create_file_changes([("utils.py", 5, 2)])

        assessment = assessor.assess_impact(commit, file_changes, sample_context)

        assert isinstance(assessment, ImpactAssessment)
        assert assessment.impact_level in [ImpactLevel.LOW, ImpactLevel.MEDIUM]
        assert assessment.change_magnitude < 1.0
        assert 0.0 <= assessment.file_criticality <= 1.0
        assert isinstance(assessment.quality_factors, dict)
        assert len(assessment.reasoning) > 0

    def test_assess_impact_large_change(self, assessor, sample_context, sample_user):
        """Test assessing impact of a large change."""
        commit = self.create_commit(
            "feat: major feature implementation",
            additions=500,
            deletions=100,
            user=sample_user
        )
        file_changes = self.create_file_changes([
            ("main.py", 200, 50),
            ("config.py", 150, 30),
            ("utils.py", 150, 20)
        ])

        assessment = assessor.assess_impact(commit, file_changes, sample_context)

        assert assessment.impact_level in [ImpactLevel.HIGH, ImpactLevel.CRITICAL]
        assert assessment.change_magnitude > 2.0
        assert assessment.file_criticality > 0.5  # Should be high due to critical files

    def test_assess_impact_critical_files(self, assessor, sample_context, sample_user):
        """Test assessing impact when critical files are changed."""
        commit = self.create_commit(
            "fix: update main application logic",
            additions=50,
            deletions=20,
            user=sample_user
        )
        file_changes = self.create_file_changes([("main.py", 50, 20)])

        assessment = assessor.assess_impact(commit, file_changes, sample_context)

        # main.py is in critical_files, so should have high criticality
        assert assessment.file_criticality >= 0.8
        assert assessment.impact_level in [ImpactLevel.MEDIUM, ImpactLevel.HIGH, ImpactLevel.CRITICAL]

    def test_assess_impact_test_files(self, assessor, sample_context, sample_user):
        """Test assessing impact when only test files are changed."""
        commit = self.create_commit(
            "test: add comprehensive tests",
            additions=100,
            deletions=10,
            user=sample_user
        )
        file_changes = self.create_file_changes([
            ("test_main.py", 50, 5),
            ("test_utils.py", 50, 5)
        ])

        assessment = assessor.assess_impact(commit, file_changes, sample_context)

        # Test files should have low criticality but high test coverage
        assert assessment.file_criticality <= 0.3
        assert assessment.quality_factors["test_coverage"] > 0.5
        assert assessment.impact_level in [ImpactLevel.LOW, ImpactLevel.MEDIUM]

    def test_assess_impact_documentation_files(self, assessor, sample_context, sample_user):
        """Test assessing impact when documentation files are changed."""
        commit = self.create_commit(
            "docs: update README and documentation",
            additions=50,
            deletions=10,
            user=sample_user
        )
        file_changes = self.create_file_changes([
            ("README.md", 30, 5),
            ("docs/guide.md", 20, 5)
        ])

        assessment = assessor.assess_impact(commit, file_changes, sample_context)

        # Doc files should have low criticality but high documentation score
        assert assessment.file_criticality <= 0.2
        assert assessment.quality_factors["documentation"] > 0.5
        assert assessment.impact_level == ImpactLevel.LOW

    def test_calculate_change_magnitude_small(self, assessor):
        """Test calculating change magnitude for small changes."""
        commit = self.create_commit("small change", additions=10, deletions=5)
        file_changes = self.create_file_changes([("test.py", 10, 5)])

        magnitude = assessor._calculate_change_magnitude(commit, file_changes)

        assert magnitude < 1.0
        assert magnitude > 0.0

    def test_calculate_change_magnitude_large(self, assessor):
        """Test calculating change magnitude for large changes."""
        commit = self.create_commit("large change", additions=600, deletions=200)
        file_changes = self.create_file_changes([
            ("file1.py", 200, 100),
            ("file2.py", 200, 50),
            ("file3.py", 200, 50)
        ])

        magnitude = assessor._calculate_change_magnitude(commit, file_changes)

        assert magnitude > 3.0  # Should be high due to large changes and bonus

    def test_assess_file_criticality_core_files(self, assessor, sample_context):
        """Test file criticality assessment for core files."""
        file_changes = self.create_file_changes([
            ("main.py", 10, 5),
            ("__init__.py", 5, 2)
        ])

        criticality = assessor._assess_file_criticality(file_changes, sample_context)

        assert criticality >= 0.8  # Should be high for core files

    def test_assess_file_criticality_test_files(self, assessor, sample_context):
        """Test file criticality assessment for test files."""
        file_changes = self.create_file_changes([
            ("test_main.py", 20, 5),
            ("test_utils.py", 15, 3)
        ])

        criticality = assessor._assess_file_criticality(file_changes, sample_context)

        assert criticality <= 0.3  # Should be low for test files

    def test_assess_file_criticality_mixed_files(self, assessor, sample_context):
        """Test file criticality assessment for mixed file types."""
        file_changes = self.create_file_changes([
            ("main.py", 50, 10),      # Critical
            ("test_main.py", 20, 5),  # Low criticality
            ("utils.py", 10, 2)       # Medium criticality
        ])

        criticality = assessor._assess_file_criticality(file_changes, sample_context)

        # Should be weighted average, but main.py has most changes so should be high
        assert 0.4 < criticality < 1.0

    def test_get_file_criticality_score_known_critical(self, assessor, sample_context):
        """Test file criticality score for known critical files."""
        # main.py is in sample_context.critical_files
        score = assessor._get_file_criticality_score("main.py", sample_context)
        assert score == 1.0

    def test_get_file_criticality_score_core_patterns(self, assessor, sample_context):
        """Test file criticality score for core pattern files."""
        score = assessor._get_file_criticality_score("app.py", sample_context)
        assert score == 1.0

        score = assessor._get_file_criticality_score("__init__.py", sample_context)
        assert score == 1.0

    def test_get_file_criticality_score_security_patterns(self, assessor, sample_context):
        """Test file criticality score for security pattern files."""
        score = assessor._get_file_criticality_score("auth_service.py", sample_context)
        assert score == 0.9

        score = assessor._get_file_criticality_score("security_utils.py", sample_context)
        assert score == 0.9

    def test_get_file_criticality_score_test_patterns(self, assessor, sample_context):
        """Test file criticality score for test pattern files."""
        score = assessor._get_file_criticality_score("test_main.py", sample_context)
        assert score == 0.2

        score = assessor._get_file_criticality_score("main_test.py", sample_context)
        assert score == 0.2

    def test_get_file_criticality_score_doc_patterns(self, assessor, sample_context):
        """Test file criticality score for documentation pattern files."""
        score = assessor._get_file_criticality_score("README.md", sample_context)
        assert score == 0.1

        score = assessor._get_file_criticality_score("docs/guide.md", sample_context)
        assert score == 0.1

    def test_get_file_criticality_score_unknown_file(self, assessor, sample_context):
        """Test file criticality score for unknown files."""
        score = assessor._get_file_criticality_score("random_file.py", sample_context)
        assert score == 0.4  # Default score

    def test_evaluate_quality_factors(self, assessor, sample_context, sample_user):
        """Test evaluation of quality factors."""
        commit = self.create_commit("feat: add feature with tests", user=sample_user)
        file_changes = self.create_file_changes([
            ("feature.py", 50, 10),
            ("test_feature.py", 30, 5),
            ("README.md", 10, 2)
        ])

        factors = assessor._evaluate_quality_factors(commit, file_changes, sample_context)

        assert "test_coverage" in factors
        assert "documentation" in factors
        assert "code_organization" in factors
        assert "commit_quality" in factors

        # Should have good test coverage and documentation
        assert factors["test_coverage"] > 0.5
        assert factors["documentation"] > 0.5

    def test_assess_test_coverage_with_tests(self, assessor):
        """Test test coverage assessment when tests are present."""
        file_changes = self.create_file_changes([
            ("feature.py", 30, 5),
            ("test_feature.py", 20, 3)
        ])

        coverage = assessor._assess_test_coverage(file_changes)

        assert coverage > 0.5  # Should be good due to test files

    def test_assess_test_coverage_without_tests(self, assessor):
        """Test test coverage assessment when no tests are present."""
        file_changes = self.create_file_changes([
            ("feature.py", 30, 5),
            ("utils.py", 20, 3)
        ])

        coverage = assessor._assess_test_coverage(file_changes)

        assert coverage == 0.0  # Should be zero without tests

    def test_assess_documentation_impact_with_docs(self, assessor):
        """Test documentation impact assessment when docs are present."""
        file_changes = self.create_file_changes([
            ("feature.py", 30, 5),
            ("README.md", 20, 3)
        ])

        doc_impact = assessor._assess_documentation_impact(file_changes)

        assert doc_impact > 0.5  # Should be good due to doc files

    def test_assess_documentation_impact_without_docs(self, assessor):
        """Test documentation impact assessment when no docs are present."""
        file_changes = self.create_file_changes([
            ("feature.py", 30, 5),
            ("utils.py", 20, 3)
        ])

        doc_impact = assessor._assess_documentation_impact(file_changes)

        assert doc_impact == 0.0  # Should be zero without docs

    def test_assess_code_organization_focused_changes(self, assessor, sample_user):
        """Test code organization assessment for focused changes."""
        commit = self.create_commit("focused change", user=sample_user)
        file_changes = self.create_file_changes([("feature.py", 30, 10)])

        organization = assessor._assess_code_organization(commit, file_changes)

        assert organization > 0.5  # Should be good for focused changes

    def test_assess_code_organization_scattered_changes(self, assessor, sample_user):
        """Test code organization assessment for scattered changes."""
        commit = self.create_commit("scattered changes", user=sample_user)
        file_changes = self.create_file_changes([
            (f"file{i}.py", 20, 5) for i in range(15)  # Many files
        ])

        organization = assessor._assess_code_organization(commit, file_changes)

        assert organization < 0.5  # Should be lower for scattered changes

    def test_assess_commit_quality_good_message(self, assessor, sample_user):
        """Test commit quality assessment for good commit message."""
        commit = self.create_commit(
            "feat: implement user authentication with JWT tokens",
            user=sample_user
        )

        quality = assessor._assess_commit_quality(commit)

        assert quality > 0.7  # Should be high for conventional commit with good message

    def test_assess_commit_quality_poor_message(self, assessor, sample_user):
        """Test commit quality assessment for poor commit message."""
        commit = self.create_commit("fix", user=sample_user)

        quality = assessor._assess_commit_quality(commit)

        assert quality < 0.5  # Should be low for short, non-descriptive message

    def test_assess_commit_quality_merge_commit(self, assessor, sample_user):
        """Test commit quality assessment for merge commit."""
        commit = self.create_commit("Merge branch 'feature'", user=sample_user)
        commit.is_merge = True

        quality = assessor._assess_commit_quality(commit)

        assert quality < 0.5  # Should be lower for merge commits

    def test_determine_impact_level_critical(self, assessor):
        """Test determining critical impact level."""
        level = assessor._determine_impact_level(
            change_magnitude=5.0,
            file_criticality=1.0,
            quality_factors={"test_coverage": 0.8, "documentation": 0.7}
        )

        assert level == ImpactLevel.CRITICAL

    def test_determine_impact_level_high(self, assessor):
        """Test determining high impact level."""
        level = assessor._determine_impact_level(
            change_magnitude=3.0,
            file_criticality=0.7,
            quality_factors={"test_coverage": 0.6, "documentation": 0.5}
        )

        assert level == ImpactLevel.HIGH

    def test_determine_impact_level_medium(self, assessor):
        """Test determining medium impact level."""
        level = assessor._determine_impact_level(
            change_magnitude=1.5,
            file_criticality=0.5,
            quality_factors={"test_coverage": 0.4, "documentation": 0.3}
        )

        assert level == ImpactLevel.MEDIUM

    def test_determine_impact_level_low(self, assessor):
        """Test determining low impact level."""
        level = assessor._determine_impact_level(
            change_magnitude=0.5,
            file_criticality=0.2,
            quality_factors={"test_coverage": 0.1, "documentation": 0.1}
        )

        assert level == ImpactLevel.LOW

    def test_generate_reasoning_comprehensive(self, assessor):
        """Test generating comprehensive reasoning."""
        reasoning = assessor._generate_reasoning(
            impact_level=ImpactLevel.HIGH,
            change_magnitude=3.5,
            file_criticality=0.8,
            quality_factors={"test_coverage": 0.7, "documentation": 0.6}
        )

        assert "high" in reasoning.lower()
        assert "large" in reasoning.lower() or "moderate" in reasoning.lower()
        assert "critical" in reasoning.lower() or "important" in reasoning.lower()
        assert "test" in reasoning.lower()
        assert "documentation" in reasoning.lower()

    def test_generate_reasoning_minimal(self, assessor):
        """Test generating reasoning for minimal impact."""
        reasoning = assessor._generate_reasoning(
            impact_level=ImpactLevel.LOW,
            change_magnitude=0.3,
            file_criticality=0.1,
            quality_factors={"test_coverage": 0.0, "documentation": 0.0}
        )

        assert "low" in reasoning.lower()
        assert "small" in reasoning.lower()
        assert "low-impact" in reasoning.lower()

    def test_assess_impact_empty_file_changes(self, assessor, sample_context, sample_user):
        """Test assessing impact with empty file changes."""
        commit = self.create_commit("empty change", user=sample_user)

        assessment = assessor.assess_impact(commit, [], sample_context)

        assert assessment.file_criticality == 0.0
        assert assessment.impact_level == ImpactLevel.LOW

    def test_assess_impact_no_file_changes_uses_commit_files(self, assessor, sample_context, sample_user):
        """Test that assessment uses commit.files_changed when file_changes is None."""
        commit = self.create_commit(
            "change with commit files",
            files=["main.py", "utils.py"],
            user=sample_user
        )

        # Pass None for file_changes to test fallback
        assessment = assessor.assess_impact(commit, None, sample_context)

        # Should still work and have reasonable criticality
        assert assessment.file_criticality > 0.0
        assert isinstance(assessment.impact_level, ImpactLevel)
