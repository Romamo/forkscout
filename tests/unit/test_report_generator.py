"""Tests for the ReportGenerator class."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from src.forklift.models.analysis import (
    Feature,
    FeatureCategory,
    ForkAnalysis,
    ForkMetrics,
    RankedFeature,
)
from src.forklift.models.github import Commit, Fork, Repository, User
from src.forklift.reporting.generator import ReportGenerator


@pytest.fixture
def sample_repository():
    """Create a sample repository for testing."""
    return Repository(
        id=12345,
        owner="testowner",
        name="testrepo",
        full_name="testowner/testrepo",
        url="https://api.github.com/repos/testowner/testrepo",
        html_url="https://github.com/testowner/testrepo",
        clone_url="https://github.com/testowner/testrepo.git",
        default_branch="main",
        stars=100,
        forks_count=50,
        language="Python",
        description="A test repository",
    )


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id=67890,
        login="testuser",
        name="Test User",
        html_url="https://github.com/testuser",
    )


@pytest.fixture
def sample_fork(sample_repository, sample_user):
    """Create a sample fork for testing."""
    fork_repo = Repository(
        id=54321,
        owner="testuser",
        name="testrepo",
        full_name="testuser/testrepo",
        url="https://api.github.com/repos/testuser/testrepo",
        html_url="https://github.com/testuser/testrepo",
        clone_url="https://github.com/testuser/testrepo.git",
        default_branch="main",
        stars=5,
        forks_count=0,
        language="Python",
        is_fork=True,
    )
    
    return Fork(
        repository=fork_repo,
        parent=sample_repository,
        owner=sample_user,
        last_activity=datetime(2024, 1, 15, tzinfo=timezone.utc),
        commits_ahead=3,
        commits_behind=1,
    )


@pytest.fixture
def sample_commit(sample_user):
    """Create a sample commit for testing."""
    return Commit(
        sha="a1b2c3d4e5f6789012345678901234567890abcd",
        message="Add new feature for user authentication",
        author=sample_user,
        date=datetime(2024, 1, 15, tzinfo=timezone.utc),
        files_changed=["auth.py", "tests/test_auth.py"],
        additions=50,
        deletions=5,
    )


@pytest.fixture
def sample_feature(sample_fork, sample_commit):
    """Create a sample feature for testing."""
    return Feature(
        id="feature-1",
        title="User Authentication System",
        description="Implements JWT-based user authentication with session management",
        category=FeatureCategory.NEW_FEATURE,
        commits=[sample_commit],
        files_affected=["auth.py", "models/user.py", "tests/test_auth.py"],
        source_fork=sample_fork,
    )


@pytest.fixture
def sample_ranked_feature(sample_feature):
    """Create a sample ranked feature for testing."""
    return RankedFeature(
        feature=sample_feature,
        score=85.5,
        ranking_factors={
            "code_quality": 90.0,
            "test_coverage": 85.0,
            "documentation": 80.0,
            "community_engagement": 87.0,
        },
        similar_implementations=[],
    )


@pytest.fixture
def sample_fork_analysis(sample_fork, sample_feature):
    """Create a sample fork analysis for testing."""
    return ForkAnalysis(
        fork=sample_fork,
        features=[sample_feature],
        metrics=ForkMetrics(
            stars=5,
            forks=0,
            contributors=1,
            last_activity=datetime(2024, 1, 15, tzinfo=timezone.utc),
            commit_frequency=0.5,
        ),
        analysis_date=datetime(2024, 1, 20, tzinfo=timezone.utc),
    )


class TestReportGenerator:
    """Test cases for ReportGenerator class."""

    def test_init_default_parameters(self):
        """Test ReportGenerator initialization with default parameters."""
        generator = ReportGenerator()
        
        assert generator.include_code_snippets is True
        assert generator.max_features == 20

    def test_init_custom_parameters(self):
        """Test ReportGenerator initialization with custom parameters."""
        generator = ReportGenerator(include_code_snippets=False, max_features=10)
        
        assert generator.include_code_snippets is False
        assert generator.max_features == 10

    def test_generate_analysis_report_empty_data(self, sample_repository):
        """Test generating report with empty data."""
        generator = ReportGenerator()
        
        report = generator.generate_analysis_report(
            repository=sample_repository,
            fork_analyses=[],
            ranked_features=[],
        )
        
        assert isinstance(report, str)
        assert len(report) > 0
        assert "testowner/testrepo" in report
        assert "No significant features were identified" in report

    def test_generate_analysis_report_with_features(
        self, sample_repository, sample_fork_analysis, sample_ranked_feature
    ):
        """Test generating report with actual features."""
        generator = ReportGenerator()
        
        report = generator.generate_analysis_report(
            repository=sample_repository,
            fork_analyses=[sample_fork_analysis],
            ranked_features=[sample_ranked_feature],
        )
        
        assert isinstance(report, str)
        assert len(report) > 0
        
        # Check header content
        assert "# Fork Analysis Report: testowner/testrepo" in report
        assert "testowner/testrepo" in report
        assert "Python" in report
        assert "100" in report  # stars
        
        # Check overview content
        assert "## Overview" in report
        assert "**1** unique features discovered" in report
        assert "**1** forks contain potentially valuable contributions" in report
        
        # Check executive summary
        assert "## Executive Summary" in report
        assert "User Authentication System" in report
        assert "Score: 85.5" in report
        
        # Check detailed features
        assert "## Top 1 Features (Detailed Analysis)" in report
        assert "JWT-based user authentication" in report
        assert "**Score:** 85.5/100" in report

    def test_generate_header(self, sample_repository):
        """Test header generation."""
        generator = ReportGenerator()
        
        header = generator._generate_header(sample_repository)
        
        assert "# Fork Analysis Report: testowner/testrepo" in header
        assert "[testowner/testrepo](https://github.com/testowner/testrepo)" in header
        assert "**Primary Language:** Python" in header
        assert "**Stars:** 100" in header
        assert "**Forks:** 50" in header

    def test_generate_overview(self, sample_repository, sample_fork_analysis, sample_ranked_feature):
        """Test overview generation."""
        generator = ReportGenerator()
        
        overview = generator._generate_overview(
            sample_repository, [sample_fork_analysis], [sample_ranked_feature]
        )
        
        assert "## Overview" in overview
        assert "**1** unique features discovered" in overview
        assert "**1** forks contain potentially valuable contributions" in overview
        assert "**1** features scored 80+ points" in overview

    def test_generate_executive_summary_empty(self):
        """Test executive summary with no features."""
        generator = ReportGenerator()
        
        summary = generator._generate_executive_summary([])
        
        assert "## Executive Summary" in summary
        assert "No significant features were identified" in summary

    def test_generate_executive_summary_with_features(self, sample_ranked_feature):
        """Test executive summary with features."""
        generator = ReportGenerator()
        
        summary = generator._generate_executive_summary([sample_ranked_feature])
        
        assert "## Executive Summary" in summary
        assert "User Authentication System" in summary
        assert "Score: 85.5" in summary
        assert "testuser/testrepo" in summary

    def test_generate_features_by_category(self, sample_ranked_feature):
        """Test features by category generation."""
        generator = ReportGenerator()
        
        # Create multiple features with different categories
        bug_fix_feature = RankedFeature(
            feature=Feature(
                id="feature-2",
                title="Fix Memory Leak",
                description="Fixes memory leak in data processing",
                category=FeatureCategory.BUG_FIX,
                commits=[],
                files_affected=[],
                source_fork=sample_ranked_feature.feature.source_fork,
            ),
            score=75.0,
            ranking_factors={},
            similar_implementations=[],
        )
        
        features = [sample_ranked_feature, bug_fix_feature]
        
        section = generator._generate_features_by_category(features)
        
        assert "## Features by Category" in section
        assert "✨ New Feature" in section
        assert "🐛 Bug Fix" in section
        assert "User Authentication System" in section
        assert "Fix Memory Leak" in section

    def test_generate_detailed_features(self, sample_ranked_feature):
        """Test detailed features generation."""
        generator = ReportGenerator()
        
        section = generator._generate_detailed_features([sample_ranked_feature])
        
        assert "## Top 1 Features (Detailed Analysis)" in section
        assert "### 1. User Authentication System" in section
        assert "**Category:** ✨ New Feature" in section
        assert "**Score:** 85.5/100" in section
        assert "**Source Fork:** [testuser/testrepo]" in section
        assert "**Scoring Breakdown:**" in section
        assert "Code Quality: 90.0" in section
        assert "**Related Commits (1):**" in section
        assert "**Files Affected (3):**" in section

    def test_generate_fork_statistics(self, sample_fork_analysis):
        """Test fork statistics generation."""
        generator = ReportGenerator()
        
        section = generator._generate_fork_statistics([sample_fork_analysis])
        
        assert "## Fork Analysis Statistics" in section
        assert "**Total Forks Analyzed:** 1" in section
        assert "**Active Forks:** 1 (100.0%)" in section
        assert "**Forks with Features:** 1 (100.0%)" in section
        assert "### Top Contributing Forks" in section
        assert "| Fork | Author | Stars | Features | Last Activity |" in section
        assert "testuser/testrepo" in section

    def test_generate_analysis_metadata(self):
        """Test analysis metadata generation."""
        generator = ReportGenerator()
        
        metadata = {
            "analysis_duration": "45.2s",
            "github_api_calls": 150,
            "cache_hit_rate": "78%",
        }
        
        section = generator._generate_analysis_metadata(metadata)
        
        assert "## Analysis Configuration" in section
        assert "**Analysis Duration:** 45.2s" in section
        assert "**Github Api Calls:** 150" in section
        assert "**Cache Hit Rate:** 78%" in section

    def test_generate_footer(self):
        """Test footer generation."""
        generator = ReportGenerator()
        
        footer = generator._generate_footer()
        
        assert "Report generated by Forklift v1.0" in footer
        assert "**Next Steps:**" in footer
        assert "Review the top-ranked features" in footer
        assert "Create pull requests for high-value features" in footer

    def test_generate_code_snippet(self, sample_feature):
        """Test code snippet generation."""
        generator = ReportGenerator()
        
        snippet = generator._generate_code_snippet(sample_feature)
        
        assert "**Code Changes Preview:**" in snippet
        assert "```" in snippet
        assert "Commit: a1b2c3d4" in snippet
        assert "Message: Add new feature for user authentication" in snippet
        assert "Files changed: 2" in snippet
        assert "Lines added: +50" in snippet
        assert "Lines removed: -5" in snippet
        assert "[View full diff on GitHub]" in snippet

    def test_generate_code_snippet_no_commits(self, sample_feature):
        """Test code snippet generation with no commits."""
        generator = ReportGenerator()
        sample_feature.commits = []
        
        snippet = generator._generate_code_snippet(sample_feature)
        
        assert snippet == ""

    def test_get_category_emoji(self):
        """Test category emoji mapping."""
        generator = ReportGenerator()
        
        assert generator._get_category_emoji(FeatureCategory.NEW_FEATURE) == "✨"
        assert generator._get_category_emoji(FeatureCategory.BUG_FIX) == "🐛"
        assert generator._get_category_emoji(FeatureCategory.PERFORMANCE) == "⚡"
        assert generator._get_category_emoji(FeatureCategory.DOCUMENTATION) == "📚"
        assert generator._get_category_emoji(FeatureCategory.REFACTOR) == "♻️"
        assert generator._get_category_emoji(FeatureCategory.TEST) == "🧪"
        assert generator._get_category_emoji(FeatureCategory.OTHER) == "🔧"

    def test_generate_summary_report(self, sample_repository):
        """Test summary report generation."""
        generator = ReportGenerator()
        
        report = generator.generate_summary_report(
            repository=sample_repository,
            total_forks=25,
            features_found=8,
            analysis_duration=45.2,
        )
        
        assert "# Fork Analysis Summary: testowner/testrepo" in report
        assert "completed in 45.2s" in report
        assert "**Forks analyzed:** 25" in report
        assert "**Features discovered:** 8" in report
        assert "8 valuable features" in report

    def test_generate_summary_report_no_features(self, sample_repository):
        """Test summary report generation with no features."""
        generator = ReportGenerator()
        
        report = generator.generate_summary_report(
            repository=sample_repository,
            total_forks=10,
            features_found=0,
        )
        
        assert "# Fork Analysis Summary: testowner/testrepo" in report
        assert "**Forks analyzed:** 10" in report
        assert "**Features discovered:** 0" in report
        assert "No significant features were found" in report

    def test_generate_summary_report_no_duration(self, sample_repository):
        """Test summary report generation without duration."""
        generator = ReportGenerator()
        
        report = generator.generate_summary_report(
            repository=sample_repository,
            total_forks=5,
            features_found=2,
        )
        
        assert "# Fork Analysis Summary: testowner/testrepo" in report
        assert "**Analysis completed**" in report
        assert "completed in" not in report

    def test_max_features_limit(self, sample_repository, sample_fork_analysis):
        """Test that max_features limit is respected."""
        generator = ReportGenerator(max_features=2)
        
        # Create 3 ranked features
        ranked_features = []
        for i in range(3):
            feature = Feature(
                id=f"feature-{i}",
                title=f"Feature {i}",
                description=f"Description {i}",
                category=FeatureCategory.NEW_FEATURE,
                commits=[],
                files_affected=[],
                source_fork=sample_fork_analysis.fork,
            )
            ranked_features.append(RankedFeature(
                feature=feature,
                score=90.0 - i,
                ranking_factors={},
                similar_implementations=[],
            ))
        
        report = generator.generate_analysis_report(
            repository=sample_repository,
            fork_analyses=[sample_fork_analysis],
            ranked_features=ranked_features,
        )
        
        # Should only show top 2 features in detailed section
        assert "## Top 2 Features (Detailed Analysis)" in report
        assert "### 1. Feature 0" in report
        assert "### 2. Feature 1" in report
        assert "### 3. Feature 2" not in report

    def test_include_code_snippets_disabled(self, sample_repository, sample_fork_analysis, sample_ranked_feature):
        """Test report generation with code snippets disabled."""
        generator = ReportGenerator(include_code_snippets=False)
        
        report = generator.generate_analysis_report(
            repository=sample_repository,
            fork_analyses=[sample_fork_analysis],
            ranked_features=[sample_ranked_feature],
        )
        
        # Should not contain code snippet sections
        assert "**Code Changes Preview:**" not in report
        assert "```" not in report

    def test_similar_implementations_display(self, sample_ranked_feature, sample_fork_analysis):
        """Test display of similar implementations."""
        # Add similar implementation
        similar_feature = Feature(
            id="similar-1",
            title="Similar Auth Feature",
            description="Another auth implementation",
            category=FeatureCategory.NEW_FEATURE,
            commits=[],
            files_affected=[],
            source_fork=sample_fork_analysis.fork,
        )
        sample_ranked_feature.similar_implementations = [similar_feature]
        
        generator = ReportGenerator()
        section = generator._generate_detailed_features([sample_ranked_feature])
        
        assert "**Similar Implementations Found:**" in section
        assert "Similar Auth Feature" in section

    def test_long_commit_list_truncation(self, sample_feature, sample_user):
        """Test that long commit lists are truncated properly."""
        # Add many commits
        commits = []
        for i in range(10):
            commit = Commit(
                sha=f"a1b2c3d4e5f6789012345678901234567890abc{i:01d}",
                message=f"Commit {i}",
                author=sample_user,
                date=datetime(2024, 1, 15, tzinfo=timezone.utc),
                files_changed=[f"file{i}.py"],
                additions=10,
                deletions=2,
            )
            commits.append(commit)
        
        sample_feature.commits = commits
        ranked_feature = RankedFeature(
            feature=sample_feature,
            score=85.0,
            ranking_factors={},
            similar_implementations=[],
        )
        
        generator = ReportGenerator()
        section = generator._generate_detailed_features([ranked_feature])
        
        # Should show only first 3 commits plus truncation message
        assert "**Related Commits (10):**" in section
        assert "Commit 0" in section
        assert "Commit 1" in section
        assert "Commit 2" in section
        assert "...and 7 more commits" in section

    def test_long_files_list_truncation(self, sample_feature):
        """Test that long files lists are truncated properly."""
        # Add many files
        files = [f"file{i}.py" for i in range(10)]
        sample_feature.files_affected = files
        
        ranked_feature = RankedFeature(
            feature=sample_feature,
            score=85.0,
            ranking_factors={},
            similar_implementations=[],
        )
        
        generator = ReportGenerator()
        section = generator._generate_detailed_features([ranked_feature])
        
        # Should show only first 5 files plus truncation message
        assert "**Files Affected (10):**" in section
        assert "file0.py" in section
        assert "file4.py" in section
        assert "...and 5 more files" in section