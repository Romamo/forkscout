"""Tests for interactive step implementations."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from forklift.analysis.interactive_steps import (
    RepositoryDiscoveryStep,
    ForkDiscoveryStep,
    ForkFilteringStep,
    ForkAnalysisStep,
    FeatureRankingStep
)
from forklift.github.client import GitHubClient
from forklift.models.analysis import Feature, FeatureCategory, ForkAnalysis, ForkMetrics, RankedFeature
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
        
        assert "✅ **Repository Found**" in display
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
        
        assert "❌ Repository discovery failed" in display
        assert "Test error" in display
    
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


class TestForkDiscoveryStep:
    """Test cases for ForkDiscoveryStep."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_github_client, sample_repository, sample_forks):
        """Test successful fork discovery."""
        # Mock fork discovery service
        with patch('forklift.analysis.interactive_steps.ForkDiscoveryService') as mock_service_class:
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
        with patch('forklift.analysis.interactive_steps.ForkDiscoveryService') as mock_service_class:
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
        
        assert "✅ **Fork Discovery Complete**" in display
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
        with patch('forklift.analysis.interactive_steps.RepositoryAnalyzer') as mock_analyzer_class:
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
        with patch('forklift.analysis.interactive_steps.FeatureRankingEngine') as mock_engine_class:
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
        
        assert "📊 **Feature Ranking Complete**" in display
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
        
        assert "📊 **Feature Ranking Complete**" in display
        assert "No features were found to rank" in display