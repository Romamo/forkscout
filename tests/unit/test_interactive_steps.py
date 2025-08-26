"""Tests for interactive step implementations."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from forklift.analysis.interactive_steps import (
    FeatureRankingStep,
    ForkAnalysisStep,
    ForkDiscoveryStep,
    ForkFilteringStep,
    RepositoryDiscoveryStep,
)
from forklift.github.client import GitHubClient
from forklift.models.analysis import (
    Feature,
    FeatureCategory,
    ForkAnalysis,
    ForkMetrics,
    RankedFeature,
)
from forklift.models.github import Fork, Repository, User


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    return Mock(spec=GitHubClient)


@pytest.fixture
def sample_repository():
    """Create a sample repository."""
    return Repository(
        id=123,
        owner="test-owner",
        name="test-repo",
        full_name="test-owner/test-repo",
        url="https://api.github.com/repos/test-owner/test-repo",
        html_url="https://github.com/test-owner/test-repo",
        clone_url="https://github.com/test-owner/test-repo.git",
        description="Test repository",
        language="Python",
        stars=100,
        forks_count=50,
        is_private=False,
        is_fork=False,
        is_archived=False,
        is_disabled=False,
        created_at=datetime(2023, 1, 1),
        updated_at=datetime(2024, 1, 1),
        pushed_at=datetime(2024, 1, 15)
    )


@pytest.fixture
def sample_forks():
    """Create sample forks."""
    return [
        Fork(
            repository=Repository(
                id=124,
                owner="fork-owner-1",
                name="test-repo",
                full_name="fork-owner-1/test-repo",
                url="https://api.github.com/repos/fork-owner-1/test-repo",
                html_url="https://github.com/fork-owner-1/test-repo",
                clone_url="https://github.com/fork-owner-1/test-repo.git",
                description="Fork 1",
                language="Python",
                stars=10,
                forks_count=2,
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
            owner=User(id=1, login="fork-owner-1", html_url="https://github.com/fork-owner-1"),
            last_activity=datetime(2024, 1, 10),
            commits_ahead=5,
            commits_behind=2,
            is_active=True,
            divergence_score=0.8
        ),
        Fork(
            repository=Repository(
                id=125,
                owner="fork-owner-2",
                name="test-repo",
                full_name="fork-owner-2/test-repo",
                url="https://api.github.com/repos/fork-owner-2/test-repo",
                html_url="https://github.com/fork-owner-2/test-repo",
                clone_url="https://github.com/fork-owner-2/test-repo.git",
                description="Fork 2",
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
            owner=User(id=2, login="fork-owner-2", html_url="https://github.com/fork-owner-2"),
            last_activity=datetime(2024, 1, 12),
            commits_ahead=10,
            commits_behind=1,
            is_active=True,
            divergence_score=0.9
        )
    ]


class TestRepositoryDiscoveryStep:
    """Test cases for RepositoryDiscoveryStep."""

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_github_client, sample_repository):
        """Test successful repository discovery."""
        mock_github_client.get_repository.return_value = sample_repository

        step = RepositoryDiscoveryStep(mock_github_client)
        context = {"repo_url": "https://github.com/test-owner/test-repo"}

        result = await step.execute(context)

        assert result.success
        assert result.step_name == "Repository Discovery"
        assert result.data == sample_repository
        assert "Successfully discovered repository" in result.summary
        assert context["repository"] == sample_repository
        assert context["owner"] == "test-owner"
        assert context["repo_name"] == "test-repo"

        # Verify the GitHub client was called with correct arguments
        mock_github_client.get_repository.assert_called_once_with("test-owner", "test-repo")

        # Check metrics
        assert result.metrics["repository_name"] == "test-owner/test-repo"
        assert result.metrics["stars"] == 100
        assert result.metrics["forks_count"] == 50

    @pytest.mark.asyncio
    async def test_execute_with_short_url(self, mock_github_client, sample_repository):
        """Test repository discovery with short URL format."""
        mock_github_client.get_repository.return_value = sample_repository

        step = RepositoryDiscoveryStep(mock_github_client)
        context = {"repo_url": "test-owner/test-repo"}

        result = await step.execute(context)

        assert result.success
        assert context["owner"] == "test-owner"
        assert context["repo_name"] == "test-repo"

    @pytest.mark.asyncio
    async def test_execute_invalid_url(self, mock_github_client):
        """Test repository discovery with invalid URL."""
        step = RepositoryDiscoveryStep(mock_github_client)
        context = {"repo_url": "invalid-url"}

        result = await step.execute(context)

        assert not result.success
        assert "Invalid repository URL format" in result.summary
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_incomplete_url(self, mock_github_client):
        """Test repository discovery with incomplete URL (missing repo name)."""
        step = RepositoryDiscoveryStep(mock_github_client)
        context = {"repo_url": "https://github.com/owner"}

        result = await step.execute(context)

        assert not result.success
        assert "Invalid repository URL format" in result.summary
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_single_part_url(self, mock_github_client):
        """Test repository discovery with single part URL."""
        step = RepositoryDiscoveryStep(mock_github_client)
        context = {"repo_url": "owner"}

        result = await step.execute(context)

        assert not result.success
        assert "Invalid repository URL format" in result.summary
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_missing_url(self, mock_github_client):
        """Test repository discovery with missing URL."""
        step = RepositoryDiscoveryStep(mock_github_client)
        context = {}

        result = await step.execute(context)

        assert not result.success
        assert "Repository URL not provided" in result.summary

    @pytest.mark.asyncio
    async def test_execute_api_error(self, mock_github_client):
        """Test repository discovery with API error."""
        mock_github_client.get_repository.side_effect = Exception("API Error")

        step = RepositoryDiscoveryStep(mock_github_client)
        context = {"repo_url": "test-owner/test-repo"}

        result = await step.execute(context)

        assert not result.success
        assert "API Error" in result.summary

    def test_display_results_success(self, sample_repository):
        """Test displaying successful results."""
        step = RepositoryDiscoveryStep(Mock())
        result = Mock()
        result.success = True
        result.data = sample_repository

        display = step.display_results(result)

        assert "SUCCESS - **Repository Found**" in display
        assert "test-owner/test-repo" in display
        assert "Python" in display
        assert "100" in display  # stars

    def test_display_results_failure(self):
        """Test displaying failed results."""
        step = RepositoryDiscoveryStep(Mock())
        result = Mock()
        result.success = False
        result.summary = "Test error"

        display = step.display_results(result)

        assert "ERROR - Repository discovery failed" in display
        assert "Test error" in display

    def test_display_results_no_data(self):
        """Test displaying results when repository data is None."""
        step = RepositoryDiscoveryStep(Mock())
        result = Mock()
        result.success = True
        result.data = None

        display = step.display_results(result)

        assert "ERROR - No repository data available" in display

    def test_get_confirmation_prompt_success(self, sample_repository):
        """Test confirmation prompt for successful discovery."""
        step = RepositoryDiscoveryStep(Mock())
        result = Mock()
        result.success = True
        result.data = sample_repository

        prompt = step.get_confirmation_prompt(result)

        assert "test-owner/test-repo" in prompt
        assert "Proceed with fork discovery" in prompt

    def test_get_confirmation_prompt_failure(self):
        """Test confirmation prompt for failed discovery."""
        step = RepositoryDiscoveryStep(Mock())
        result = Mock()
        result.success = False

        prompt = step.get_confirmation_prompt(result)

        assert "Repository discovery failed" in prompt
        assert "Skip to next step" in prompt


class TestForkFilteringStep:
    """Test cases for ForkFilteringStep."""

    @pytest.mark.asyncio
    async def test_execute_success(self, sample_forks):
        """Test successful fork filtering."""
        step = ForkFilteringStep(min_commits_ahead=1, min_stars=0)
        context = {"all_forks": sample_forks}

        result = await step.execute(context)

        assert result.success
        assert result.step_name == "Fork Filtering"
        assert len(result.data) == 2  # Both sample forks should pass filter
        assert context["filtered_forks"] == result.data

        # Check metrics
        assert result.metrics["total_forks"] == 2
        assert result.metrics["filtered_forks"] == 2
        assert result.metrics["filter_ratio"] == 1.0

    @pytest.mark.asyncio
    async def test_execute_with_strict_filters(self, sample_forks):
        """Test fork filtering with strict criteria."""
        step = ForkFilteringStep(min_commits_ahead=10, min_stars=50)
        context = {"all_forks": sample_forks}

        result = await step.execute(context)

        assert result.success
        # Only the second fork has 10 commits ahead
        assert len(result.data) == 1
        assert result.data[0].commits_ahead == 10

    @pytest.mark.asyncio
    async def test_execute_no_forks(self):
        """Test fork filtering with no forks."""
        step = ForkFilteringStep()
        context = {"all_forks": []}

        result = await step.execute(context)

        assert result.success
        assert len(result.data) == 0
        assert "No forks to filter" in result.summary
        assert result.metrics["filtered_forks"] == 0
        assert result.metrics["total_forks"] == 0

    @pytest.mark.asyncio
    async def test_execute_missing_forks_context(self):
        """Test fork filtering with missing forks in context."""
        step = ForkFilteringStep()
        context = {}

        result = await step.execute(context)

        assert result.success
        assert len(result.data) == 0
        assert "No forks to filter" in result.summary

    @pytest.mark.asyncio
    async def test_execute_inactive_forks(self, sample_forks):
        """Test fork filtering with inactive forks."""
        # Make forks inactive
        for fork in sample_forks:
            fork.is_active = False

        step = ForkFilteringStep()
        context = {"all_forks": sample_forks}

        result = await step.execute(context)

        assert result.success
        assert len(result.data) == 0  # No active forks should pass

    @pytest.mark.asyncio
    async def test_execute_exception(self):
        """Test fork filtering with exception."""
        step = ForkFilteringStep()
        # Create a mock fork that will cause an exception
        mock_fork = Mock()
        mock_fork.commits_ahead = None  # This should cause an exception
        context = {"all_forks": [mock_fork]}

        result = await step.execute(context)

        assert not result.success
        assert "Failed to filter forks" in result.summary
        assert result.error is not None

    def test_display_results_success(self, sample_forks):
        """Test displaying successful filtering results."""
        step = ForkFilteringStep()
        result = Mock()
        result.success = True
        result.data = sample_forks
        result.metrics = {
            "total_forks": 5,
            "filtered_forks": 2,
            "filter_ratio": 0.4,
            "avg_stars_filtered": 25.0,
            "avg_commits_ahead_filtered": 7.5
        }

        display = step.display_results(result)

        assert "🔍 **Fork Filtering Complete**" in display
        assert "5" in display
        assert "2" in display

    def test_display_results_no_forks(self):
        """Test displaying results when no forks pass filter."""
        step = ForkFilteringStep()
        result = Mock()
        result.success = True
        result.data = []
        result.metrics = {"total_forks": 5, "filtered_forks": 0}

        display = step.display_results(result)

        assert "No Forks Passed Filtering" in display

    def test_display_results_failure(self):
        """Test displaying failed filtering results."""
        step = ForkFilteringStep()
        result = Mock()
        result.success = False
        result.summary = "Filter error"

        display = step.display_results(result)

        assert "❌ Fork filtering failed" in display
        assert "Filter error" in display

    def test_get_confirmation_prompt_many_forks(self, sample_forks):
        """Test confirmation prompt with many filtered forks."""
        step = ForkFilteringStep()
        result = Mock()
        result.success = True
        result.data = sample_forks * 10  # 20 forks

        prompt = step.get_confirmation_prompt(result)

        assert "20 forks" in prompt
        assert "Continue" in prompt or "Proceed" in prompt

    def test_get_confirmation_prompt_few_forks(self, sample_forks):
        """Test confirmation prompt with few filtered forks."""
        step = ForkFilteringStep()
        result = Mock()
        result.success = True
        result.data = sample_forks[:1]  # 1 fork

        prompt = step.get_confirmation_prompt(result)

        assert "1 forks" in prompt or "1 fork" in prompt

    def test_get_confirmation_prompt_no_forks(self):
        """Test confirmation prompt with no filtered forks."""
        step = ForkFilteringStep()
        result = Mock()
        result.success = True
        result.data = []

        prompt = step.get_confirmation_prompt(result)

        assert "No forks passed" in prompt
        assert "summary report" in prompt

    def test_get_confirmation_prompt_failure(self):
        """Test confirmation prompt for failed filtering."""
        step = ForkFilteringStep()
        result = Mock()
        result.success = False

        prompt = step.get_confirmation_prompt(result)

        assert "filtering encountered issues" in prompt
        assert "partial results" in prompt


class TestForkDiscoveryStep:
    """Test cases for ForkDiscoveryStep."""

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_github_client, sample_repository, sample_forks):
        """Test successful fork discovery."""
        # Mock fork discovery service
        with patch("forklift.analysis.interactive_steps.ForkDiscoveryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.discover_forks.return_value = sample_forks
            mock_service_class.return_value = mock_service

            step = ForkDiscoveryStep(mock_github_client)
            context = {"repository": sample_repository}

            result = await step.execute(context)

            assert result.success
            assert result.step_name == "Fork Discovery"
            assert result.data == sample_forks
            assert context["all_forks"] == sample_forks
            assert context["total_forks"] == 2

            # Verify the service was called with the HTML URL, not the API URL
            mock_service.discover_forks.assert_called_once_with(sample_repository.html_url)

            # Check metrics
            assert result.metrics["total_forks"] == 2
            assert result.metrics["active_forks"] == 2
            assert result.metrics["forks_with_commits_ahead"] == 2
            assert result.metrics["max_commits_ahead"] == 10

    @pytest.mark.asyncio
    async def test_execute_no_repository(self, mock_github_client):
        """Test fork discovery without repository in context."""
        step = ForkDiscoveryStep(mock_github_client)
        context = {}

        result = await step.execute(context)

        assert not result.success
        assert "Repository not found in context" in result.summary

    @pytest.mark.asyncio
    async def test_execute_discovery_error(self, mock_github_client, sample_repository):
        """Test fork discovery with service error."""
        with patch("forklift.analysis.interactive_steps.ForkDiscoveryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.discover_forks.side_effect = Exception("Discovery failed")
            mock_service_class.return_value = mock_service

            step = ForkDiscoveryStep(mock_github_client)
            context = {"repository": sample_repository}

            result = await step.execute(context)

            assert not result.success
            assert "Discovery failed" in result.summary

    def test_display_results_with_forks(self, sample_forks):
        """Test displaying results with forks found."""
        step = ForkDiscoveryStep(Mock())
        result = Mock()
        result.success = True
        result.data = sample_forks
        result.metrics = {
            "total_forks": 2,
            "active_forks": 2,
            "forks_with_commits_ahead": 2,
            "max_commits_ahead": 10,
            "avg_commits_ahead": 7.5
        }

        display = step.display_results(result)

        assert "SUCCESS - **Fork Discovery Complete**" in display
        assert "Total Forks Found: 2" in display
        assert "Active Forks: 2" in display
        assert "Top 5 Most Active Forks:" in display
        assert "fork-owner-2/test-repo" in display  # Should be first (10 commits ahead)

    def test_display_results_no_forks(self):
        """Test displaying results with no forks found."""
        step = ForkDiscoveryStep(Mock())
        result = Mock()
        result.success = True
        result.data = []
        result.metrics = {}

        display = step.display_results(result)

        assert "📭 **No Forks Found**" in display
        assert "no public forks to analyze" in display


class TestForkFilteringStep:
    """Test cases for ForkFilteringStep."""

    @pytest.mark.asyncio
    async def test_execute_success(self, sample_forks):
        """Test successful fork filtering."""
        step = ForkFilteringStep(min_commits_ahead=1, min_stars=5)
        context = {"all_forks": sample_forks}

        result = await step.execute(context)

        assert result.success
        assert result.step_name == "Fork Filtering"
        # Both forks should pass (commits_ahead >= 1, stars >= 5 for fork 2, stars = 10 for fork 1)
        assert len(result.data) == 2
        assert context["filtered_forks"] == result.data

        # Check metrics
        assert result.metrics["total_forks"] == 2
        assert result.metrics["filtered_forks"] == 2

    @pytest.mark.asyncio
    async def test_execute_strict_filtering(self, sample_forks):
        """Test fork filtering with strict criteria."""
        step = ForkFilteringStep(min_commits_ahead=8, min_stars=20)
        context = {"all_forks": sample_forks}

        result = await step.execute(context)

        assert result.success
        # Only fork 2 should pass (10 commits ahead, 25 stars)
        assert len(result.data) == 1
        assert result.data[0].repository.full_name == "fork-owner-2/test-repo"

    @pytest.mark.asyncio
    async def test_execute_no_forks(self):
        """Test fork filtering with no forks."""
        step = ForkFilteringStep()
        context = {"all_forks": []}

        result = await step.execute(context)

        assert result.success
        assert len(result.data) == 0
        assert result.metrics["filtered_forks"] == 0

    def test_display_results_with_filtered_forks(self, sample_forks):
        """Test displaying results with filtered forks."""
        step = ForkFilteringStep(min_commits_ahead=1, min_stars=5)
        result = Mock()
        result.success = True
        result.data = sample_forks
        result.metrics = {
            "total_forks": 2,
            "filtered_forks": 2,
            "filter_ratio": 1.0,
            "avg_stars_filtered": 17.5,
            "avg_commits_ahead_filtered": 7.5
        }

        display = step.display_results(result)

        assert "🔍 **Fork Filtering Complete**" in display
        assert "Minimum commits ahead: 1" in display
        assert "Minimum stars: 5" in display
        assert "Original forks discovered: 2" in display
        assert "Forks passing filters: 2" in display
        assert "Selected Forks for Detailed Analysis:" in display


class TestForkAnalysisStep:
    """Test cases for ForkAnalysisStep."""

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_github_client, sample_repository, sample_forks):
        """Test successful fork analysis."""
        # Mock repository analyzer
        with patch("forklift.analysis.interactive_steps.RepositoryAnalyzer") as mock_analyzer_class:
            mock_analyzer = AsyncMock()

            # Create mock analysis results
            mock_analyses = []
            for fork in sample_forks:
                analysis = ForkAnalysis(
                    fork=fork,
                    features=[
                        Feature(
                            id=f"feature-{fork.repository.owner}",
                            title=f"Feature from {fork.repository.owner}",
                            description="Test feature",
                            category=FeatureCategory.NEW_FEATURE,
                            source_fork=fork
                        )
                    ],
                    metrics=ForkMetrics(stars=fork.repository.stars),
                    analysis_date=datetime.now()
                )
                mock_analyses.append(analysis)

            mock_analyzer.analyze_fork.side_effect = mock_analyses
            mock_analyzer_class.return_value = mock_analyzer

            step = ForkAnalysisStep(mock_github_client)
            context = {
                "filtered_forks": sample_forks,
                "repository": sample_repository
            }

            result = await step.execute(context)

            assert result.success
            assert result.step_name == "Fork Analysis"
            assert len(result.data) == 2
            assert context["fork_analyses"] == result.data
            assert context["total_features"] == 2

            # Check metrics
            assert result.metrics["total_forks_to_analyze"] == 2
            assert result.metrics["successfully_analyzed"] == 2
            assert result.metrics["failed_analyses"] == 0
            assert result.metrics["total_features"] == 2

    @pytest.mark.asyncio
    async def test_execute_no_repository(self, mock_github_client):
        """Test fork analysis without repository in context."""
        step = ForkAnalysisStep(mock_github_client)
        context = {"filtered_forks": []}

        result = await step.execute(context)

        assert not result.success
        assert "Repository not found in context" in result.summary

    @pytest.mark.asyncio
    async def test_execute_no_forks(self, mock_github_client, sample_repository):
        """Test fork analysis with no forks to analyze."""
        step = ForkAnalysisStep(mock_github_client)
        context = {
            "filtered_forks": [],
            "repository": sample_repository
        }

        result = await step.execute(context)

        assert result.success
        assert len(result.data) == 0
        assert result.metrics["analyzed_forks"] == 0

    def test_display_results_success(self):
        """Test displaying successful analysis results."""
        step = ForkAnalysisStep(Mock())

        # Create mock analyses with proper features attribute
        mock_analysis1 = Mock()
        mock_analysis1.features = [Mock(), Mock()]  # 2 features
        mock_analysis1.fork.repository.full_name = "owner1/repo"

        mock_analysis2 = Mock()
        mock_analysis2.features = [Mock(), Mock(), Mock()]  # 3 features
        mock_analysis2.fork.repository.full_name = "owner2/repo"

        result = Mock()
        result.success = True
        result.data = [mock_analysis1, mock_analysis2]
        result.metrics = {
            "total_forks_to_analyze": 2,
            "successfully_analyzed": 2,
            "failed_analyses": 0,
            "analysis_success_rate": 1.0,
            "total_features": 5,
            "avg_features_per_fork": 2.5
        }

        display = step.display_results(result)

        assert "🔬 **Fork Analysis Complete**" in display
        assert "Forks targeted for analysis: 2" in display
        assert "Successfully analyzed: 2" in display
        assert "Success rate: 100.0%" in display
        assert "Total features discovered: 5" in display


class TestForkAnalysisStep:
    """Test cases for ForkAnalysisStep."""

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_github_client, sample_repository, sample_forks):
        """Test successful fork analysis."""
        with patch("forklift.analysis.interactive_steps.RepositoryAnalyzer") as mock_analyzer_class:
            mock_analyzer = AsyncMock()

            # Create mock analyses
            mock_analyses = []
            for i, fork in enumerate(sample_forks):
                features = [
                    Feature(
                        id=f"feature-{i}-{j}",
                        title=f"Feature {j} from {fork.repository.owner}",
                        description="Test feature",
                        category=FeatureCategory.NEW_FEATURE,
                        source_fork=fork
                    )
                    for j in range(2)  # 2 features per fork
                ]

                analysis = ForkAnalysis(
                    fork=fork,
                    features=features,
                    metrics=ForkMetrics(stars=fork.repository.stars),
                    analysis_date=datetime.now()
                )
                mock_analyses.append(analysis)

            mock_analyzer.analyze_fork.side_effect = mock_analyses
            mock_analyzer_class.return_value = mock_analyzer

            step = ForkAnalysisStep(mock_github_client)
            context = {
                "repository": sample_repository,
                "filtered_forks": sample_forks
            }

            result = await step.execute(context)

            assert result.success
            assert result.step_name == "Fork Analysis"
            assert len(result.data) == 2
            assert context["fork_analyses"] == result.data
            assert context["total_features"] == 4  # 2 features per fork

            # Check metrics
            assert result.metrics["total_forks_to_analyze"] == 2
            assert result.metrics["successfully_analyzed"] == 2
            assert result.metrics["failed_analyses"] == 0
            assert result.metrics["total_features"] == 4
            assert result.metrics["avg_features_per_fork"] == 2.0
            assert result.metrics["analysis_success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_execute_no_repository(self, mock_github_client):
        """Test fork analysis without repository in context."""
        step = ForkAnalysisStep(mock_github_client)
        context = {"filtered_forks": []}

        result = await step.execute(context)

        assert not result.success
        assert "Repository not found in context" in result.summary

    @pytest.mark.asyncio
    async def test_execute_no_forks(self, mock_github_client, sample_repository):
        """Test fork analysis with no filtered forks."""
        step = ForkAnalysisStep(mock_github_client)
        context = {
            "repository": sample_repository,
            "filtered_forks": []
        }

        result = await step.execute(context)

        assert result.success
        assert len(result.data) == 0
        assert "No forks to analyze" in result.summary
        assert result.metrics["analyzed_forks"] == 0
        assert result.metrics["total_features"] == 0

    @pytest.mark.asyncio
    async def test_execute_missing_forks_context(self, mock_github_client, sample_repository):
        """Test fork analysis with missing filtered_forks in context."""
        step = ForkAnalysisStep(mock_github_client)
        context = {"repository": sample_repository}

        result = await step.execute(context)

        assert result.success
        assert len(result.data) == 0
        assert "No forks to analyze" in result.summary

    @pytest.mark.asyncio
    async def test_execute_with_explanation_engine(self, mock_github_client, sample_repository, sample_forks):
        """Test fork analysis with explanation engine."""
        mock_explanation_engine = Mock()

        with patch("forklift.analysis.interactive_steps.RepositoryAnalyzer") as mock_analyzer_class:
            mock_analyzer = AsyncMock()
            mock_analysis = Mock(spec=ForkAnalysis)
            mock_analysis.features = []
            mock_analyzer.analyze_fork.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            step = ForkAnalysisStep(mock_github_client, explanation_engine=mock_explanation_engine)
            context = {
                "repository": sample_repository,
                "filtered_forks": sample_forks[:1]
            }

            result = await step.execute(context)

            assert result.success
            # Verify analyzer was called with explain=True
            mock_analyzer.analyze_fork.assert_called_once_with(
                sample_forks[0], sample_repository, explain=True
            )

    @pytest.mark.asyncio
    async def test_execute_partial_failures(self, mock_github_client, sample_repository, sample_forks):
        """Test fork analysis with some failures."""
        with patch("forklift.analysis.interactive_steps.RepositoryAnalyzer") as mock_analyzer_class:
            mock_analyzer = AsyncMock()

            # First fork succeeds, second fails
            mock_analysis = Mock(spec=ForkAnalysis)
            mock_analysis.features = [Mock()]
            mock_analyzer.analyze_fork.side_effect = [
                mock_analysis,
                Exception("Analysis failed")
            ]
            mock_analyzer_class.return_value = mock_analyzer

            step = ForkAnalysisStep(mock_github_client)
            context = {
                "repository": sample_repository,
                "filtered_forks": sample_forks
            }

            result = await step.execute(context)

            assert result.success
            assert len(result.data) == 1  # Only one successful analysis
            assert result.metrics["successfully_analyzed"] == 1
            assert result.metrics["failed_analyses"] == 1
            assert result.metrics["analysis_success_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_execute_exception(self, mock_github_client):
        """Test fork analysis with exception."""
        step = ForkAnalysisStep(mock_github_client)
        context = {"repository": None}  # This should cause an exception

        result = await step.execute(context)

        assert not result.success
        assert "Failed to analyze forks" in result.summary
        assert result.error is not None

    def test_display_results_success(self, sample_forks):
        """Test displaying successful analysis results."""
        step = ForkAnalysisStep(Mock())

        # Create mock analyses
        mock_analyses = []
        for fork in sample_forks:
            analysis = Mock()
            analysis.fork = fork
            analysis.features = [Mock(), Mock()]  # 2 features each
            mock_analyses.append(analysis)

        result = Mock()
        result.success = True
        result.data = mock_analyses
        result.metrics = {
            "total_forks_to_analyze": 2,
            "successfully_analyzed": 2,
            "failed_analyses": 0,
            "analysis_success_rate": 1.0,
            "total_features": 4,
            "avg_features_per_fork": 2.0
        }

        display = step.display_results(result)

        assert "🔬 **Fork Analysis Complete**" in display
        assert "2" in display  # forks analyzed
        assert "4" in display  # total features

    def test_display_results_no_analyses(self):
        """Test displaying results when no analyses are available."""
        step = ForkAnalysisStep(Mock())
        result = Mock()
        result.success = True
        result.data = []
        result.metrics = {
            "total_forks_to_analyze": 0,
            "successfully_analyzed": 0,
            "total_features": 0
        }

        display = step.display_results(result)

        assert "🔬 **Fork Analysis Complete**" in display
        assert "0" in display

    def test_display_results_failure(self):
        """Test displaying failed analysis results."""
        step = ForkAnalysisStep(Mock())
        result = Mock()
        result.success = False
        result.summary = "Analysis error"

        display = step.display_results(result)

        assert "ERROR - Fork analysis failed" in display
        assert "Analysis error" in display

    def test_get_confirmation_prompt_many_features(self):
        """Test confirmation prompt with many features found."""
        step = ForkAnalysisStep(Mock())
        result = Mock()
        result.success = True
        result.metrics = {"total_features": 50}

        prompt = step.get_confirmation_prompt(result)

        assert "50 features" in prompt
        assert "rank" in prompt

    def test_get_confirmation_prompt_few_features(self):
        """Test confirmation prompt with few features found."""
        step = ForkAnalysisStep(Mock())
        result = Mock()
        result.success = True
        result.metrics = {"total_features": 3}

        prompt = step.get_confirmation_prompt(result)

        assert "3 features" in prompt

    def test_get_confirmation_prompt_no_features(self):
        """Test confirmation prompt with no features found."""
        step = ForkAnalysisStep(Mock())
        result = Mock()
        result.success = True
        result.metrics = {"total_features": 0}

        prompt = step.get_confirmation_prompt(result)

        assert "No forks were successfully analyzed" in prompt
        assert "diagnostic report" in prompt

    def test_get_confirmation_prompt_failure(self):
        """Test confirmation prompt for failed analysis."""
        step = ForkAnalysisStep(Mock())
        result = Mock()
        result.success = False

        prompt = step.get_confirmation_prompt(result)

        assert "encountered significant errors" in prompt


class TestFeatureRankingStep:
    """Test cases for FeatureRankingStep."""

    @pytest.mark.asyncio
    async def test_execute_success(self, sample_forks):
        """Test successful feature ranking."""
        # Create mock fork analyses with features
        mock_analyses = []
        for i, fork in enumerate(sample_forks):
            features = [
                Feature(
                    id=f"feature-{i}-{j}",
                    title=f"Feature {j} from {fork.repository.owner}",
                    description="Test feature",
                    category=FeatureCategory.NEW_FEATURE,
                    source_fork=fork
                )
                for j in range(2)  # 2 features per fork
            ]

            analysis = ForkAnalysis(
                fork=fork,
                features=features,
                metrics=ForkMetrics(stars=fork.repository.stars),
                analysis_date=datetime.now()
            )
            mock_analyses.append(analysis)

        # Mock ranking engine
        with patch("forklift.analysis.interactive_steps.FeatureRankingEngine") as mock_engine_class:
            mock_engine = Mock()

            # Create mock ranked features
            all_features = []
            for analysis in mock_analyses:
                all_features.extend(analysis.features)

            ranked_features = [
                RankedFeature(
                    feature=feature,
                    score=90.0 - i * 10,  # Decreasing scores
                    ranking_factors={"test": 1.0}
                )
                for i, feature in enumerate(all_features)
            ]

            mock_engine.rank_features.return_value = ranked_features
            mock_engine_class.return_value = mock_engine

            step = FeatureRankingStep()
            context = {"fork_analyses": mock_analyses}

            result = await step.execute(context)

            assert result.success
            assert result.step_name == "Feature Ranking"
            assert len(result.data) == 4  # 2 forks * 2 features each
            assert context["ranked_features"] == result.data
            assert "final_result" in context

            # Check metrics
            assert result.metrics["total_features"] == 4
            assert result.metrics["ranked_features"] == 4
            assert result.metrics["high_value_features"] == 2  # Scores 90 and 80

    @pytest.mark.asyncio
    async def test_execute_no_analyses(self):
        """Test feature ranking with no analyses."""
        step = FeatureRankingStep()
        context = {"fork_analyses": []}

        result = await step.execute(context)

        assert result.success
        assert len(result.data) == 0
        assert result.metrics["ranked_features"] == 0

    @pytest.mark.asyncio
    async def test_execute_no_features(self, sample_forks):
        """Test feature ranking with analyses but no features."""
        # Create analyses with no features
        mock_analyses = [
            ForkAnalysis(
                fork=fork,
                features=[],  # No features
                metrics=ForkMetrics(stars=fork.repository.stars),
                analysis_date=datetime.now()
            )
            for fork in sample_forks
        ]

        step = FeatureRankingStep()
        context = {"fork_analyses": mock_analyses}

        result = await step.execute(context)

        assert result.success
        assert len(result.data) == 0
        assert "No features found to rank" in result.summary

    @pytest.mark.asyncio
    async def test_execute_missing_analyses_context(self):
        """Test feature ranking with missing fork_analyses in context."""
        step = FeatureRankingStep()
        context = {}

        result = await step.execute(context)

        assert result.success
        assert len(result.data) == 0
        assert "No features to rank" in result.summary
        assert result.metrics["ranked_features"] == 0

    @pytest.mark.asyncio
    async def test_execute_exception(self, sample_forks):
        """Test feature ranking with exception."""
        # Create mock analyses with real features
        mock_analyses = []
        for fork in sample_forks:
            features = [
                Feature(
                    id="test-feature",
                    title="Test Feature",
                    description="Test feature",
                    category=FeatureCategory.NEW_FEATURE,
                    source_fork=fork
                )
            ]
            analysis = ForkAnalysis(
                fork=fork,
                features=features,
                metrics=ForkMetrics(stars=fork.repository.stars),
                analysis_date=datetime.now()
            )
            mock_analyses.append(analysis)

        with patch("forklift.analysis.interactive_steps.FeatureRankingEngine") as mock_engine_class:
            mock_engine_class.side_effect = Exception("Ranking engine failed")

            step = FeatureRankingStep()
            context = {"fork_analyses": mock_analyses}

            result = await step.execute(context)

            assert not result.success
            assert "Failed to rank features" in result.summary
            assert result.error is not None

    def test_display_results_with_features(self):
        """Test displaying results with ranked features."""
        step = FeatureRankingStep()

        # Create mock ranked features
        mock_feature1 = Mock()
        mock_feature1.score = 95.0
        mock_feature1.feature = Mock()
        mock_feature1.feature.title = "Feature 1"
        mock_feature1.feature.source_fork = Mock()
        mock_feature1.feature.source_fork.repository = Mock()
        mock_feature1.feature.source_fork.repository.full_name = "owner1/repo"
        mock_feature1.feature.category = Mock()
        mock_feature1.feature.category.value = "feature"
        mock_feature1.ranking_factors = {"code_quality": 0.9, "community": 0.8}

        mock_feature2 = Mock()
        mock_feature2.score = 85.0
        mock_feature2.feature = Mock()
        mock_feature2.feature.title = "Feature 2"
        mock_feature2.feature.source_fork = Mock()
        mock_feature2.feature.source_fork.repository = Mock()
        mock_feature2.feature.source_fork.repository.full_name = "owner2/repo"
        mock_feature2.feature.category = Mock()
        mock_feature2.feature.category.value = "bugfix"
        mock_feature2.ranking_factors = {"test_coverage": 0.85, "documentation": 0.7}

        mock_features = [mock_feature1, mock_feature2]

        result = Mock()
        result.success = True
        result.data = mock_features
        result.metrics = {
            "total_features": 2,
            "high_value_features": 2,
            "medium_value_features": 0,
            "avg_score": 90.0,
            "top_score": 95.0
        }

        display = step.display_results(result)

        assert "**Feature Ranking Complete**" in display
        assert "Total features ranked: 2" in display
        assert "High-value features (80-89): 1" in display
        assert "Top-Tier Features (Score ≥80):" in display
        assert "Feature 1" in display
        assert "Score: 95.0" in display

    def test_display_results_no_features(self):
        """Test displaying results with no features."""
        step = FeatureRankingStep()
        result = Mock()
        result.success = True
        result.data = []
        result.metrics = {}

        display = step.display_results(result)

        assert "**Feature Ranking Complete**" in display
        assert "No features were found to rank" in display

    def test_display_results_failure(self):
        """Test displaying failed ranking results."""
        step = FeatureRankingStep()
        result = Mock()
        result.success = False
        result.summary = "Ranking error"

        display = step.display_results(result)

        assert "ERROR - Feature ranking failed" in display
        assert "Ranking error" in display

    def test_get_confirmation_prompt_excellent_features(self):
        """Test confirmation prompt with excellent features."""
        step = FeatureRankingStep()
        result = Mock()
        result.success = True
        result.data = [Mock(score=95), Mock(score=85)]  # Mock ranked features
        result.metrics = {"high_value_features": 5, "total_features": 10}

        prompt = step.get_confirmation_prompt(result)

        assert "features" in prompt
        assert "report" in prompt

    def test_get_confirmation_prompt_few_features(self):
        """Test confirmation prompt with few features."""
        step = FeatureRankingStep()
        result = Mock()
        result.success = True
        result.data = [Mock(score=70), Mock(score=65), Mock(score=60)]  # Mock ranked features
        result.metrics = {"high_value_features": 0, "total_features": 3}

        prompt = step.get_confirmation_prompt(result)

        assert "features" in prompt
        assert "report" in prompt

    def test_get_confirmation_prompt_no_features(self):
        """Test confirmation prompt with no features."""
        step = FeatureRankingStep()
        result = Mock()
        result.success = True
        result.data = []  # No ranked features
        result.metrics = {"total_features": 0}

        prompt = step.get_confirmation_prompt(result)

        assert "no features were identified" in prompt
        assert "diagnostic report" in prompt

    def test_get_confirmation_prompt_failure(self):
        """Test confirmation prompt for failed ranking."""
        step = FeatureRankingStep()
        result = Mock()
        result.success = False

        prompt = step.get_confirmation_prompt(result)

        assert "encountered errors" in prompt
