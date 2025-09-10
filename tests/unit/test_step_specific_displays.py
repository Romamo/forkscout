"""Tests for step-specific displays and confirmations."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from forkscout.analysis.interactive_steps import (
    FeatureRankingStep,
    ForkAnalysisStep,
    ForkDiscoveryStep,
    ForkFilteringStep,
)
from forkscout.models.github import Fork, Repository, User


@pytest.fixture
def sample_forks():
    """Create sample forks with different activity levels."""
    return [
        # High activity fork
        Fork(
            repository=Repository(
                id=124,
                owner="high-activity",
                name="test-repo",
                full_name="high-activity/test-repo",
                url="https://api.github.com/repos/high-activity/test-repo",
                html_url="https://github.com/high-activity/test-repo",
                clone_url="https://github.com/high-activity/test-repo.git",
                description="High activity fork",
                language="Python",
                stars=25,
                forks_count=5,
                is_private=False,
                is_fork=True,
                is_archived=False,
                is_disabled=False
            ),
            parent=Repository(
                id=123,
                owner="test-owner",
                name="test-repo",
                full_name="test-owner/test-repo",
                url="https://api.github.com/repos/test-owner/test-repo",
                html_url="https://github.com/test-owner/test-repo",
                clone_url="https://github.com/test-owner/test-repo.git",
                description="Parent repo",
                language="Python",
                stars=100,
                forks_count=50,
                is_private=False,
                is_fork=False,
                is_archived=False,
                is_disabled=False
            ),
            owner=User(id=1, login="high-activity", html_url="https://github.com/high-activity"),
            last_activity=datetime(2024, 1, 15),
            commits_ahead=15,
            commits_behind=2,
            is_active=True,
            divergence_score=0.9
        ),
        # Medium activity fork
        Fork(
            repository=Repository(
                id=125,
                owner="medium-activity",
                name="test-repo",
                full_name="medium-activity/test-repo",
                url="https://api.github.com/repos/medium-activity/test-repo",
                html_url="https://github.com/medium-activity/test-repo",
                clone_url="https://github.com/medium-activity/test-repo.git",
                description="Medium activity fork",
                language="Python",
                stars=8,
                forks_count=1,
                is_private=False,
                is_fork=True,
                is_archived=False,
                is_disabled=False
            ),
            parent=Repository(
                id=123,
                owner="test-owner",
                name="test-repo",
                full_name="test-owner/test-repo",
                url="https://api.github.com/repos/test-owner/test-repo",
                html_url="https://github.com/test-owner/test-repo",
                clone_url="https://github.com/test-owner/test-repo.git",
                description="Parent repo",
                language="Python",
                stars=100,
                forks_count=50,
                is_private=False,
                is_fork=False,
                is_archived=False,
                is_disabled=False
            ),
            owner=User(id=2, login="medium-activity", html_url="https://github.com/medium-activity"),
            last_activity=datetime(2024, 1, 10),
            commits_ahead=5,
            commits_behind=1,
            is_active=True,
            divergence_score=0.7
        ),
        # Low activity fork
        Fork(
            repository=Repository(
                id=126,
                owner="low-activity",
                name="test-repo",
                full_name="low-activity/test-repo",
                url="https://api.github.com/repos/low-activity/test-repo",
                html_url="https://github.com/low-activity/test-repo",
                clone_url="https://github.com/low-activity/test-repo.git",
                description="Low activity fork",
                language="Python",
                stars=2,
                forks_count=0,
                is_private=False,
                is_fork=True,
                is_archived=False,
                is_disabled=False
            ),
            parent=Repository(
                id=123,
                owner="test-owner",
                name="test-repo",
                full_name="test-owner/test-repo",
                url="https://api.github.com/repos/test-owner/test-repo",
                html_url="https://github.com/test-owner/test-repo",
                clone_url="https://github.com/test-owner/test-repo.git",
                description="Parent repo",
                language="Python",
                stars=100,
                forks_count=50,
                is_private=False,
                is_fork=False,
                is_archived=False,
                is_disabled=False
            ),
            owner=User(id=3, login="low-activity", html_url="https://github.com/low-activity"),
            last_activity=datetime(2024, 1, 5),
            commits_ahead=2,
            commits_behind=0,
            is_active=True,
            divergence_score=0.3
        )
    ]


class TestForkDiscoveryStepDisplays:
    """Test enhanced displays for fork discovery step."""

    def test_display_results_with_activity_breakdown(self, sample_forks):
        """Test fork discovery display with activity level breakdown."""
        step = ForkDiscoveryStep(Mock())
        result = Mock()
        result.success = True
        result.data = sample_forks
        result.metrics = {
            "total_forks": 3,
            "active_forks": 3,
            "forks_with_commits_ahead": 3,
            "max_commits_ahead": 15,
            "avg_commits_ahead": 7.3
        }

        display = step.display_results(result)

        # Check for enhanced formatting
        assert "SUCCESS - **Fork Discovery Complete**" in display
        assert "Fork Activity Breakdown:" in display
        assert "High Activity (≥10 commits): 1 forks" in display
        assert "Medium Activity (3-9 commits): 1 forks" in display
        assert "Low Activity (1-2 commits): 1 forks" in display
        assert "[HIGH] high-activity/test-repo" in display
        assert "[MED] medium-activity/test-repo" in display
        assert "[LOW] low-activity/test-repo" in display
        assert "15 commits ahead" in display
        assert "25 stars" in display

    def test_get_confirmation_prompt_with_metrics(self, sample_forks):
        """Test enhanced confirmation prompt with detailed metrics."""
        step = ForkDiscoveryStep(Mock())
        result = Mock()
        result.success = True
        result.data = sample_forks
        result.metrics = {
            "active_forks": 3,
            "forks_with_commits_ahead": 3
        }

        prompt = step.get_confirmation_prompt(result)

        assert "Found 3 forks (3 active, 3 with new commits)" in prompt
        assert "Continue to filtering stage?" in prompt

    def test_get_confirmation_prompt_no_forks(self):
        """Test confirmation prompt when no forks are found."""
        step = ForkDiscoveryStep(Mock())
        result = Mock()
        result.success = True
        result.data = []
        result.metrics = {}

        prompt = step.get_confirmation_prompt(result)

        assert "No forks found for this repository" in prompt
        assert "Skip to final report generation?" in prompt

    def test_get_confirmation_prompt_error(self):
        """Test confirmation prompt when discovery fails."""
        step = ForkDiscoveryStep(Mock())
        result = Mock()
        result.success = False

        prompt = step.get_confirmation_prompt(result)

        assert "Fork discovery encountered errors" in prompt
        assert "Continue with available data or abort analysis?" in prompt


class TestForkFilteringStepDisplays:
    """Test enhanced displays for fork filtering step."""

    def test_display_results_with_value_categorization(self, sample_forks):
        """Test filtering display with high/medium/other value categorization."""
        step = ForkFilteringStep(min_commits_ahead=1, min_stars=0)
        result = Mock()
        result.success = True
        result.data = sample_forks
        result.metrics = {
            "total_forks": 5,
            "filtered_forks": 3,
            "filter_ratio": 0.6,
            "avg_stars_filtered": 11.7,
            "avg_commits_ahead_filtered": 7.3
        }

        display = step.display_results(result)

        # Check for enhanced categorization
        assert "FILTERING - **Fork Filtering Complete**" in display
        assert "Minimum commits ahead: 1" in display
        assert "Minimum stars: 0" in display
        assert "Original forks discovered: 5" in display
        assert "Forks passing filters: 3" in display
        assert "Selection ratio: 60.0%" in display
        assert "**High-Value Forks" in display
        assert "high-activity/test-repo" in display
        assert "15 commits ahead, 25 stars" in display

    def test_display_results_no_forks_passed(self):
        """Test filtering display when no forks pass criteria."""
        step = ForkFilteringStep(min_commits_ahead=20, min_stars=50)
        result = Mock()
        result.success = True
        result.data = []
        result.metrics = {
            "total_forks": 3,
            "filtered_forks": 0,
            "filter_ratio": 0.0
        }

        display = step.display_results(result)

        assert "WARNING: **No Forks Passed Filtering**" in display
        assert "**Suggestions:**" in display
        assert "Consider lowering the minimum commits ahead (currently 20)" in display
        assert "Consider lowering the minimum stars requirement (currently 50)" in display

    def test_get_confirmation_prompt_with_high_value_forks(self, sample_forks):
        """Test confirmation prompt when high-value forks are selected."""
        step = ForkFilteringStep()
        result = Mock()
        result.success = True
        result.data = sample_forks
        result.metrics = {}

        prompt = step.get_confirmation_prompt(result)

        assert "Selected 3 forks for analysis (1 high-value)" in prompt
        assert "This may take several minutes. Continue?" in prompt

    def test_get_confirmation_prompt_no_high_value(self, sample_forks):
        """Test confirmation prompt when no high-value forks are selected."""
        low_value_forks = [sample_forks[2]]  # Only the low-activity fork
        step = ForkFilteringStep()
        result = Mock()
        result.success = True
        result.data = low_value_forks
        result.metrics = {}

        prompt = step.get_confirmation_prompt(result)

        assert "Selected 1 forks for analysis" in prompt
        assert "Proceed with detailed feature extraction?" in prompt


class TestForkAnalysisStepDisplays:
    """Test enhanced displays for fork analysis step."""

    def test_display_results_with_feature_distribution(self, sample_forks):
        """Test analysis display with feature distribution breakdown."""
        step = ForkAnalysisStep(Mock())

        # Create mock analyses with different feature counts
        rich_analysis = Mock()
        rich_analysis.fork = sample_forks[0]
        rich_analysis.features = [Mock() for _ in range(7)]  # 7 features
        for i, feature in enumerate(rich_analysis.features):
            feature.category = Mock()
            feature.category.value = ["new_feature", "bug_fix", "performance"][i % 3]

        moderate_analysis = Mock()
        moderate_analysis.fork = sample_forks[1]
        moderate_analysis.features = [Mock() for _ in range(3)]  # 3 features
        for feature in moderate_analysis.features:
            feature.category = Mock()
            feature.category.value = "new_feature"

        sparse_analysis = Mock()
        sparse_analysis.fork = sample_forks[2]
        sparse_analysis.features = [Mock()]  # 1 feature
        sparse_analysis.features[0].category = Mock()
        sparse_analysis.features[0].category.value = "bug_fix"

        result = Mock()
        result.success = True
        result.data = [rich_analysis, moderate_analysis, sparse_analysis]
        result.metrics = {
            "total_forks_to_analyze": 3,
            "successfully_analyzed": 3,
            "failed_analyses": 0,
            "analysis_success_rate": 1.0,
            "total_features": 11,
            "avg_features_per_fork": 3.7
        }

        display = step.display_results(result)

        # Check for enhanced categorization
        assert "ANALYSIS - **Fork Analysis Complete**" in display
        assert "Forks targeted for analysis: 3" in display
        assert "Successfully analyzed: 3" in display
        assert "Success rate: 100.0%" in display
        assert "Total features discovered: 11" in display
        assert "**Feature Distribution:**" in display
        assert "Feature-rich forks (≥5 features): 1" in display
        assert "Moderate forks (2-4 features): 1" in display
        assert "Sparse forks (1 feature): 1" in display
        assert "**Top Feature-Rich Forks:**" in display
        assert "high-activity/test-repo" in display
        assert "7 features discovered" in display
        assert "CATEGORIES:" in display

    def test_get_confirmation_prompt_excellent_results(self):
        """Test confirmation prompt for excellent analysis results."""
        step = ForkAnalysisStep(Mock())
        result = Mock()
        result.success = True
        result.metrics = {
            "total_features": 25,
            "successfully_analyzed": 5
        }

        prompt = step.get_confirmation_prompt(result)

        assert "Excellent! Discovered 25 features from 5 forks" in prompt
        assert "Ready to rank and prioritize these features?" in prompt

    def test_get_confirmation_prompt_good_results(self):
        """Test confirmation prompt for good analysis results."""
        step = ForkAnalysisStep(Mock())
        result = Mock()
        result.success = True
        result.metrics = {
            "total_features": 15,
            "successfully_analyzed": 3
        }

        prompt = step.get_confirmation_prompt(result)

        assert "Good results! Found 15 features from 3 forks" in prompt
        assert "Continue to feature ranking and scoring?" in prompt

    def test_get_confirmation_prompt_no_features(self):
        """Test confirmation prompt when no features are found."""
        step = ForkAnalysisStep(Mock())
        result = Mock()
        result.success = True
        result.metrics = {
            "total_features": 0,
            "successfully_analyzed": 2
        }

        prompt = step.get_confirmation_prompt(result)

        assert "Analysis completed for 2 forks but no distinct features were identified" in prompt
        assert "Generate summary report anyway?" in prompt


class TestFeatureRankingStepDisplays:
    """Test enhanced displays for feature ranking step."""

    def test_display_results_with_quality_distribution(self):
        """Test ranking display with quality distribution breakdown."""
        step = FeatureRankingStep()

        # Create mock ranked features with different scores
        excellent_feature = Mock()
        excellent_feature.score = 95.0
        excellent_feature.feature = Mock()
        excellent_feature.feature.title = "Excellent Feature"
        excellent_feature.feature.source_fork = Mock()
        excellent_feature.feature.source_fork.repository = Mock()
        excellent_feature.feature.source_fork.repository.full_name = "excellent/repo"
        excellent_feature.feature.category = Mock()
        excellent_feature.feature.category.value = "new_feature"
        excellent_feature.ranking_factors = {"code_quality": 0.9, "community_engagement": 0.8}

        high_value_feature = Mock()
        high_value_feature.score = 85.0
        high_value_feature.feature = Mock()
        high_value_feature.feature.title = "High Value Feature"
        high_value_feature.feature.source_fork = Mock()
        high_value_feature.feature.source_fork.repository = Mock()
        high_value_feature.feature.source_fork.repository.full_name = "high-value/repo"
        high_value_feature.feature.category = Mock()
        high_value_feature.feature.category.value = "bug_fix"
        high_value_feature.ranking_factors = {"test_coverage": 0.85, "documentation": 0.7}

        good_feature = Mock()
        good_feature.score = 75.0
        good_feature.feature = Mock()
        good_feature.feature.title = "Good Feature"
        good_feature.feature.source_fork = Mock()
        good_feature.feature.source_fork.repository = Mock()
        good_feature.feature.source_fork.repository.full_name = "good/repo"
        good_feature.feature.category = Mock()
        good_feature.feature.category.value = "performance"
        good_feature.ranking_factors = {}

        result = Mock()
        result.success = True
        result.data = [excellent_feature, high_value_feature, good_feature]
        result.metrics = {
            "total_features": 3,
            "high_value_features": 2,
            "medium_value_features": 1,
            "avg_score": 85.0,
            "top_score": 95.0
        }

        display = step.display_results(result)

        # Check for enhanced quality distribution
        assert "**Feature Ranking Complete**" in display
        assert "**Quality Distribution:**" in display
        assert "Excellent features (≥90): 1" in display
        assert "High-value features (80-89): 1" in display
        assert "Good features (70-79): 1" in display
        assert "Average score: 85.0/100" in display
        assert "Highest score achieved: 95.0/100" in display
        assert "**Top-Tier Features (Score ≥80):**" in display
        assert "[EXCELLENT] **Excellent Feature**" in display
        assert "Score: 95.0/100" in display
        assert "SOURCE: excellent/repo" in display
        assert "CATEGORY: New Feature" in display
        assert "Key factors: code_quality: 0.9, community_engagement: 0.8" in display

    def test_display_results_only_medium_features(self):
        """Test ranking display when only medium-quality features are found."""
        step = FeatureRankingStep()

        medium_feature = Mock()
        medium_feature.score = 65.0
        medium_feature.feature = Mock()
        medium_feature.feature.title = "Medium Feature"
        medium_feature.feature.source_fork = Mock()
        medium_feature.feature.source_fork.repository = Mock()
        medium_feature.feature.source_fork.repository.full_name = "medium/repo"

        result = Mock()
        result.success = True
        result.data = [medium_feature]
        result.metrics = {
            "total_features": 1,
            "high_value_features": 0,
            "medium_value_features": 1,
            "avg_score": 65.0,
            "top_score": 65.0
        }

        display = step.display_results(result)

        assert "INFO: **Available Features (Score 60-69):**" in display
        assert "Medium Feature (Score: 65.0)" in display
        assert "**Recommendation:** Consider reviewing the analysis criteria" in display

    def test_get_confirmation_prompt_outstanding_results(self):
        """Test confirmation prompt for outstanding ranking results."""
        step = FeatureRankingStep()
        result = Mock()
        result.success = True
        result.data = [Mock(score=95), Mock(score=88), Mock(score=82)]

        prompt = step.get_confirmation_prompt(result)

        assert "EXCELLENT - Outstanding results! Found 1 excellent features (≥90 score) and 2 high-value features" in prompt
        assert "Ready to generate your comprehensive analysis report?" in prompt

    def test_get_confirmation_prompt_good_results(self):
        """Test confirmation prompt for good ranking results."""
        step = FeatureRankingStep()
        result = Mock()
        result.success = True
        result.data = [Mock(score=85), Mock(score=82)]

        prompt = step.get_confirmation_prompt(result)

        assert "Great results! Identified 2 high-value features (≥80 score)" in prompt
        assert "Generate detailed report with recommendations?" in prompt

    def test_get_confirmation_prompt_moderate_results(self):
        """Test confirmation prompt for moderate ranking results."""
        step = FeatureRankingStep()
        result = Mock()
        result.success = True
        result.data = [Mock(score=75), Mock(score=72)]

        prompt = step.get_confirmation_prompt(result)

        assert "Found 2 good features (≥70 score) from the analysis" in prompt
        assert "Create summary report with findings?" in prompt

    def test_get_confirmation_prompt_no_features(self):
        """Test confirmation prompt when no features are found."""
        step = FeatureRankingStep()
        result = Mock()
        result.success = True
        result.data = []

        prompt = step.get_confirmation_prompt(result)

        assert "Feature ranking completed but no features were identified" in prompt
        assert "Would you like a diagnostic report explaining the analysis results?" in prompt
