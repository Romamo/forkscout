"""
Unit tests for KiroContributionStatistics
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from src.forklift.analysis.kiro_contribution_statistics import (
    KiroContributionStatistics,
    FeatureContribution,
    VelocityMetrics,
    QualityAssessment,
    ContributionStatistics
)


class TestKiroContributionStatistics:
    """Test cases for KiroContributionStatistics class."""
    
    @pytest.fixture
    def statistics_generator(self, tmp_path):
        """Create a KiroContributionStatistics instance with temporary directory."""
        return KiroContributionStatistics(project_root=tmp_path)
    
    @pytest.fixture
    def mock_src_structure(self, tmp_path):
        """Create mock source directory structure."""
        src_dir = tmp_path / "src" / "forklift"
        src_dir.mkdir(parents=True)
        
        # Create test files for different features
        github_client = src_dir / "github_client.py"
        github_client.write_text('''"""
GitHub API client with comprehensive functionality.

This module provides async GitHub API access with rate limiting.
"""

from typing import Optional, List, Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class GitHubClient:
    """GitHub API client with rate limiting."""
    token: str
    base_url: str = "https://api.github.com"
    
    async def get_repository(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get repository information."""
        try:
            # TODO: Implement actual API call
            logger.info(f"Fetching repository {owner}/{repo}")
            return {"owner": owner, "name": repo}
        except Exception as e:
            logger.error(f"Failed to fetch repository: {e}")
            raise GitHubAPIError("Repository fetch failed") from e


def test_github_client():
    """Test GitHub client functionality."""
    client = GitHubClient("test-token")
    assert client.token == "test-token"
''')
        
        fork_discovery = src_dir / "fork_discovery.py"
        fork_discovery.write_text('''"""
Fork discovery service for repository analysis.
"""

from typing import List
import asyncio

class ForkDiscoveryService:
    """Discovers and analyzes repository forks."""
    
    def __init__(self, github_client):
        self.github_client = github_client
    
    async def discover_forks(self, repo_url: str) -> List[dict]:
        """Discover all forks of a repository."""
        # Simple implementation
        return []

def test_fork_discovery():
    """Test fork discovery."""
    service = ForkDiscoveryService(None)
    assert service is not None
''')
        
        return src_dir
    
    @pytest.fixture
    def mock_tests_structure(self, tmp_path):
        """Create mock tests directory structure."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir(parents=True)
        
        # Create test files
        test_github = tests_dir / "test_github_client.py"
        test_github.write_text('''"""
Tests for GitHub client.
"""

import pytest
from unittest.mock import Mock

def test_github_client_init():
    """Test GitHub client initialization."""
    assert True

def test_github_client_get_repository():
    """Test repository fetching."""
    assert True

class TestGitHubClient:
    """Test class for GitHub client."""
    
    def test_method(self):
        """Test method."""
        assert True
''')
        
        return tests_dir
    
    @pytest.fixture
    def mock_specs_structure(self, tmp_path):
        """Create mock specs directory structure."""
        specs_dir = tmp_path / ".kiro" / "specs"
        specs_dir.mkdir(parents=True)
        
        # Create spec directories
        (specs_dir / "forklift-tool").mkdir()
        (specs_dir / "commit-explanation-feature").mkdir()
        
        return specs_dir
    
    def test_init(self, tmp_path):
        """Test KiroContributionStatistics initialization."""
        stats = KiroContributionStatistics(project_root=tmp_path)
        
        assert stats.project_root == tmp_path
        assert stats.src_dir == tmp_path / "src"
        assert stats.tests_dir == tmp_path / "tests"
        assert stats.specs_dir == tmp_path / ".kiro" / "specs"
    
    def test_init_default_path(self):
        """Test initialization with default path."""
        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/test/path")
            stats = KiroContributionStatistics()
            
            assert stats.project_root == Path("/test/path")
    
    def test_analyze_project_overview(self, statistics_generator, mock_src_structure, mock_tests_structure, mock_specs_structure):
        """Test project overview analysis."""
        overview = statistics_generator._analyze_project_overview()
        
        assert isinstance(overview, dict)
        assert "project_name" in overview
        assert "development_approach" in overview
        assert "total_python_files" in overview
        assert "total_test_files" in overview
        assert "total_specs" in overview
        assert "total_lines_of_code" in overview
        
        assert overview["total_python_files"] > 0
        assert overview["total_test_files"] > 0
        assert overview["total_specs"] > 0
        assert overview["total_lines_of_code"] > 0
    
    def test_analyze_project_overview_no_directories(self, statistics_generator):
        """Test project overview with no directories."""
        overview = statistics_generator._analyze_project_overview()
        
        assert overview["total_python_files"] == 0
        assert overview["total_test_files"] == 0
        assert overview["total_specs"] == 0
        assert overview["total_lines_of_code"] == 0
    
    def test_analyze_feature_contributions(self, statistics_generator, mock_src_structure):
        """Test feature contributions analysis."""
        contributions = statistics_generator._analyze_feature_contributions()
        
        assert isinstance(contributions, list)
        # Should find GitHub API Client and Fork Discovery features
        feature_names = [c.feature_name for c in contributions]
        assert "GitHub API Client" in feature_names
        assert "Fork Discovery" in feature_names
    
    def test_analyze_feature_area(self, statistics_generator, mock_src_structure):
        """Test analysis of a specific feature area."""
        contribution = statistics_generator._analyze_feature_area("GitHub API Client", "github")
        
        assert contribution is not None
        assert isinstance(contribution, FeatureContribution)
        assert contribution.feature_name == "GitHub API Client"
        assert contribution.total_lines > 0
        assert contribution.kiro_generated_lines >= 0
        assert contribution.kiro_assisted_lines >= 0
        assert contribution.human_written_lines >= 0
        assert contribution.ai_assistance_level in ["high", "medium", "low"]
        assert contribution.development_method in ["spec-driven", "iterative", "collaborative"]
        assert len(contribution.files_involved) > 0
        assert 0 <= contribution.test_coverage <= 100
        assert contribution.documentation_quality in ["excellent", "good", "fair", "minimal"]
    
    def test_analyze_feature_area_no_files(self, statistics_generator):
        """Test feature area analysis with no matching files."""
        contribution = statistics_generator._analyze_feature_area("Nonexistent Feature", "nonexistent")
        
        assert contribution is None
    
    def test_count_kiro_generated_patterns(self, statistics_generator):
        """Test counting of Kiro-generated patterns."""
        content = '''"""
Comprehensive docstring with detailed information.
"""

from typing import Optional, List, Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

@dataclass
class TestClass:
    """Test class with comprehensive documentation."""
    name: str
    
    async def process(self) -> List[str]:
        """Process data asynchronously."""
        try:
            logger.info("Processing started")
            return []
        except Exception as e:
            raise ProcessingError("Processing failed") from e

@pytest.fixture
def test_fixture():
    """Test fixture."""
    return TestClass("test")

def test_function():
    """Test function."""
    assert True, "Test should pass"
'''
        
        count = statistics_generator._count_kiro_generated_patterns(content)
        assert count > 0  # Should detect multiple patterns
    
    def test_count_kiro_assisted_patterns(self, statistics_generator):
        """Test counting of Kiro-assisted patterns."""
        content = '''
# TODO: Implement this feature
# FIXME: Fix this issue
# NOTE: Important note

try:
    result = process_data()
except Exception as e:
    logger.error(f"Error: {e}")

if value is None:
    return default

if isinstance(obj, str):
    return obj.upper()

data = config.get("key", "default")
message = f"Processing {count} items"
'''
        
        count = statistics_generator._count_kiro_assisted_patterns(content)
        assert count > 0  # Should detect multiple patterns
    
    def test_analyze_file_quality(self, statistics_generator):
        """Test file quality analysis."""
        content = '''"""
Module docstring.
"""

from typing import Optional

def function(param: str) -> Optional[str]:
    """Function docstring."""
    try:
        logger.info("Processing")
        if param is None:
            return None
        assert param is not None
        return param.upper()
    except Exception:
        return None

def test_function():
    """Test function."""
    assert True

class TestClass:
    """Test class."""
    pass
'''
        
        quality = statistics_generator._analyze_file_quality(content)
        
        assert isinstance(quality, dict)
        assert "docstring_count" in quality
        assert "type_hint_count" in quality
        assert "error_handling_count" in quality
        assert "test_count" in quality
        assert "logging_count" in quality
        assert "assertion_count" in quality
        assert "complexity_indicators" in quality
        
        assert quality["docstring_count"] > 0
        assert quality["type_hint_count"] > 0
        assert quality["error_handling_count"] > 0
        assert quality["test_count"] > 0
    
    def test_determine_assistance_level(self, statistics_generator):
        """Test AI assistance level determination."""
        assert statistics_generator._determine_assistance_level(80.0) == "high"
        assert statistics_generator._determine_assistance_level(50.0) == "medium"
        assert statistics_generator._determine_assistance_level(30.0) == "low"
    
    def test_determine_development_method_for_feature(self, statistics_generator):
        """Test development method determination."""
        assert statistics_generator._determine_development_method_for_feature("GitHub API Client") == "spec-driven"
        assert statistics_generator._determine_development_method_for_feature("CLI Interface") == "iterative"
        assert statistics_generator._determine_development_method_for_feature("Unknown Feature") == "collaborative"
    
    def test_calculate_feature_complexity(self, statistics_generator):
        """Test feature complexity calculation."""
        complexity = statistics_generator._calculate_feature_complexity(1000, 5)
        expected = min(100, 50 + 25)  # min(100, 1000//20 + 5*5)
        assert complexity == expected
    
    def test_estimate_test_coverage(self, statistics_generator, mock_tests_structure):
        """Test test coverage estimation."""
        coverage = statistics_generator._estimate_test_coverage("GitHub API Client", "github")
        assert 0 <= coverage <= 100
    
    def test_estimate_test_coverage_no_tests(self, statistics_generator):
        """Test test coverage estimation with no test directory."""
        coverage = statistics_generator._estimate_test_coverage("GitHub API Client", "github")
        assert coverage == 0.0
    
    def test_assess_documentation_quality(self, statistics_generator):
        """Test documentation quality assessment."""
        # Test excellent quality
        quality_indicators = {"docstring_count": 15}
        assert statistics_generator._assess_documentation_quality(quality_indicators) == "excellent"
        
        # Test good quality
        quality_indicators = {"docstring_count": 7}
        assert statistics_generator._assess_documentation_quality(quality_indicators) == "good"
        
        # Test fair quality
        quality_indicators = {"docstring_count": 3}
        assert statistics_generator._assess_documentation_quality(quality_indicators) == "fair"
        
        # Test minimal quality
        quality_indicators = {"docstring_count": 1}
        assert statistics_generator._assess_documentation_quality(quality_indicators) == "minimal"
    
    def test_find_associated_spec(self, statistics_generator, mock_specs_structure):
        """Test finding associated specs."""
        spec = statistics_generator._find_associated_spec("GitHub API Client")
        assert spec == "forklift-tool"
        
        spec = statistics_generator._find_associated_spec("Commit Analysis")
        assert spec == "commit-explanation-feature"
        
        spec = statistics_generator._find_associated_spec("Unknown Feature")
        assert spec is None
    
    def test_find_associated_spec_no_specs(self, statistics_generator):
        """Test finding specs with no specs directory."""
        spec = statistics_generator._find_associated_spec("GitHub API Client")
        assert spec is None
    
    def test_calculate_overall_contribution_percentage(self, statistics_generator):
        """Test overall contribution percentage calculation."""
        contributions = [
            FeatureContribution(
                feature_name="Feature 1",
                spec_name=None,
                total_lines=100,
                kiro_generated_lines=60,
                kiro_assisted_lines=20,
                human_written_lines=20,
                ai_assistance_level="high",
                development_method="spec-driven",
                complexity_score=50,
                quality_indicators={},
                files_involved=[],
                test_coverage=80.0,
                documentation_quality="good"
            ),
            FeatureContribution(
                feature_name="Feature 2",
                spec_name=None,
                total_lines=200,
                kiro_generated_lines=80,
                kiro_assisted_lines=40,
                human_written_lines=80,
                ai_assistance_level="medium",
                development_method="iterative",
                complexity_score=60,
                quality_indicators={},
                files_involved=[],
                test_coverage=70.0,
                documentation_quality="fair"
            )
        ]
        
        percentage = statistics_generator._calculate_overall_contribution_percentage(contributions)
        expected = ((60 + 20 + 80 + 40) / (100 + 200)) * 100  # 66.67%
        assert abs(percentage - expected) < 0.01
    
    def test_calculate_overall_contribution_percentage_empty(self, statistics_generator):
        """Test overall contribution percentage with empty contributions."""
        percentage = statistics_generator._calculate_overall_contribution_percentage([])
        assert percentage == 0.0
    
    def test_calculate_velocity_metrics(self, statistics_generator):
        """Test velocity metrics calculation."""
        contributions = [
            FeatureContribution(
                feature_name="Feature 1",
                spec_name=None,
                total_lines=100,
                kiro_generated_lines=60,
                kiro_assisted_lines=20,
                human_written_lines=20,
                ai_assistance_level="high",
                development_method="spec-driven",
                complexity_score=50,
                quality_indicators={},
                files_involved=[],
                test_coverage=80.0,
                documentation_quality="good"
            )
        ]
        
        metrics = statistics_generator._calculate_velocity_metrics(contributions)
        
        assert isinstance(metrics, VelocityMetrics)
        assert metrics.baseline_velocity == 50.0
        assert metrics.ai_assisted_velocity == 150.0
        assert metrics.velocity_multiplier == 3.0
        assert metrics.time_saved_hours > 0
        assert metrics.features_completed == 1
        assert metrics.average_feature_completion_time > 0
        assert metrics.quality_maintenance_factor == 1.2
    
    def test_assess_code_quality(self, statistics_generator):
        """Test code quality assessment."""
        contributions = [
            FeatureContribution(
                feature_name="Feature 1",
                spec_name=None,
                total_lines=100,
                kiro_generated_lines=60,
                kiro_assisted_lines=20,
                human_written_lines=20,
                ai_assistance_level="high",
                development_method="spec-driven",
                complexity_score=50,
                quality_indicators={
                    "docstring_count": 10,
                    "type_hint_count": 20,
                    "error_handling_count": 5,
                    "test_count": 8
                },
                files_involved=[],
                test_coverage=85.0,
                documentation_quality="excellent"
            )
        ]
        
        assessment = statistics_generator._assess_code_quality(contributions)
        
        assert isinstance(assessment, QualityAssessment)
        assert 0 <= assessment.overall_quality_score <= 100
        assert 0 <= assessment.consistency_score <= 100
        assert 0 <= assessment.maintainability_score <= 100
        assert 0 <= assessment.documentation_score <= 100
        assert 0 <= assessment.test_coverage_score <= 100
        assert 0 <= assessment.error_handling_score <= 100
        assert 0 <= assessment.performance_score <= 100
        assert 0 <= assessment.security_score <= 100
        assert len(assessment.quality_improvements) > 0
        assert len(assessment.areas_for_improvement) > 0
    
    def test_assess_code_quality_empty(self, statistics_generator):
        """Test code quality assessment with empty contributions."""
        assessment = statistics_generator._assess_code_quality([])
        
        assert assessment.overall_quality_score == 0
        assert assessment.consistency_score == 0
        assert len(assessment.quality_improvements) == 0
    
    def test_analyze_development_patterns(self, statistics_generator):
        """Test development patterns analysis."""
        contributions = [
            FeatureContribution(
                feature_name="Feature 1",
                spec_name=None,
                total_lines=100,
                kiro_generated_lines=60,
                kiro_assisted_lines=20,
                human_written_lines=20,
                ai_assistance_level="high",
                development_method="spec-driven",
                complexity_score=50,
                quality_indicators={},
                files_involved=[],
                test_coverage=85.0,
                documentation_quality="excellent"
            ),
            FeatureContribution(
                feature_name="Feature 2",
                spec_name=None,
                total_lines=200,
                kiro_generated_lines=80,
                kiro_assisted_lines=40,
                human_written_lines=80,
                ai_assistance_level="medium",
                development_method="iterative",
                complexity_score=60,
                quality_indicators={},
                files_involved=[],
                test_coverage=70.0,
                documentation_quality="good"
            )
        ]
        
        patterns = statistics_generator._analyze_development_patterns(contributions)
        
        assert isinstance(patterns, dict)
        assert "development_method_distribution" in patterns
        assert "ai_assistance_level_distribution" in patterns
        assert "spec_driven_percentage" in patterns
        assert "high_ai_assistance_percentage" in patterns
        assert "average_complexity_score" in patterns
        assert "most_complex_feature" in patterns
        assert "highest_ai_contribution" in patterns
        
        assert patterns["spec_driven_percentage"] == 50.0  # 1 out of 2
        assert patterns["high_ai_assistance_percentage"] == 50.0  # 1 out of 2
        assert patterns["average_complexity_score"] == 55.0  # (50 + 60) / 2
    
    def test_create_ai_assistance_breakdown(self, statistics_generator):
        """Test AI assistance breakdown creation."""
        contributions = [
            FeatureContribution(
                feature_name="Feature 1",
                spec_name=None,
                total_lines=100,
                kiro_generated_lines=60,
                kiro_assisted_lines=20,
                human_written_lines=20,
                ai_assistance_level="high",
                development_method="spec-driven",
                complexity_score=50,
                quality_indicators={},
                files_involved=[],
                test_coverage=80.0,
                documentation_quality="good"
            )
        ]
        
        breakdown = statistics_generator._create_ai_assistance_breakdown(contributions)
        
        assert isinstance(breakdown, dict)
        assert "kiro_generated_percentage" in breakdown
        assert "kiro_assisted_percentage" in breakdown
        assert "human_written_percentage" in breakdown
        assert "total_ai_contribution" in breakdown
        assert "lines_breakdown" in breakdown
        
        assert breakdown["kiro_generated_percentage"] == 60.0
        assert breakdown["kiro_assisted_percentage"] == 20.0
        assert breakdown["human_written_percentage"] == 20.0
        assert breakdown["total_ai_contribution"] == 80.0
    
    def test_create_comparative_analysis(self, statistics_generator):
        """Test comparative analysis creation."""
        contributions = []
        velocity_metrics = VelocityMetrics(
            baseline_velocity=50.0,
            ai_assisted_velocity=150.0,
            velocity_multiplier=3.0,
            time_saved_hours=100.0,
            features_completed=5,
            average_feature_completion_time=2.0,
            quality_maintenance_factor=1.2
        )
        
        analysis = statistics_generator._create_comparative_analysis(contributions, velocity_metrics)
        
        assert isinstance(analysis, dict)
        assert "development_speed_comparison" in analysis
        assert "quality_comparison" in analysis
        assert "feature_complexity_handling" in analysis
        assert "development_methodology_impact" in analysis
        
        speed_comp = analysis["development_speed_comparison"]
        assert "3.0x faster" in speed_comp["speed_improvement"]
        assert "100.0 hours" in speed_comp["time_saved"]
    
    def test_generate_comprehensive_statistics(self, statistics_generator, mock_src_structure, mock_tests_structure, mock_specs_structure):
        """Test comprehensive statistics generation."""
        stats = statistics_generator.generate_comprehensive_statistics()
        
        assert isinstance(stats, ContributionStatistics)
        assert stats.analysis_timestamp is not None
        assert isinstance(stats.project_overview, dict)
        assert isinstance(stats.overall_contribution_percentage, float)
        assert isinstance(stats.feature_contributions, list)
        assert isinstance(stats.velocity_metrics, VelocityMetrics)
        assert isinstance(stats.quality_assessment, QualityAssessment)
        assert isinstance(stats.development_patterns, dict)
        assert isinstance(stats.ai_assistance_breakdown, dict)
        assert isinstance(stats.comparative_analysis, dict)
    
    def test_save_statistics_to_file(self, statistics_generator, tmp_path):
        """Test saving statistics to file."""
        output_path = tmp_path / "test_stats.json"
        
        with patch.object(statistics_generator, 'generate_comprehensive_statistics') as mock_gen:
            mock_stats = ContributionStatistics(
                analysis_timestamp="2024-01-01T00:00:00",
                project_overview={},
                overall_contribution_percentage=75.0,
                feature_contributions=[],
                velocity_metrics=VelocityMetrics(50.0, 150.0, 3.0, 100.0, 5, 2.0, 1.2),
                quality_assessment=QualityAssessment(85, 90, 80, 85, 90, 85, 80, 85, [], []),
                development_patterns={},
                ai_assistance_breakdown={},
                comparative_analysis={}
            )
            mock_gen.return_value = mock_stats
            
            saved_path = statistics_generator.save_statistics_to_file(output_path)
            
            assert saved_path == output_path
            assert output_path.exists()
            
            # Verify JSON structure
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert isinstance(data, dict)
            assert data["overall_contribution_percentage"] == 75.0
    
    def test_save_statistics_default_path(self, statistics_generator):
        """Test saving statistics with default path."""
        with patch.object(statistics_generator, 'generate_comprehensive_statistics') as mock_gen:
            mock_stats = ContributionStatistics(
                analysis_timestamp="2024-01-01T00:00:00",
                project_overview={},
                overall_contribution_percentage=75.0,
                feature_contributions=[],
                velocity_metrics=VelocityMetrics(50.0, 150.0, 3.0, 100.0, 5, 2.0, 1.2),
                quality_assessment=QualityAssessment(85, 90, 80, 85, 90, 85, 80, 85, [], []),
                development_patterns={},
                ai_assistance_breakdown={},
                comparative_analysis={}
            )
            mock_gen.return_value = mock_stats
            
            output_path = statistics_generator.save_statistics_to_file()
            
            assert output_path.name == "kiro_contribution_statistics.json"
            assert output_path.exists()


class TestDataClasses:
    """Test the data classes used by KiroContributionStatistics."""
    
    def test_feature_contribution_creation(self):
        """Test FeatureContribution dataclass creation."""
        contribution = FeatureContribution(
            feature_name="Test Feature",
            spec_name="test-spec",
            total_lines=100,
            kiro_generated_lines=60,
            kiro_assisted_lines=20,
            human_written_lines=20,
            ai_assistance_level="high",
            development_method="spec-driven",
            complexity_score=75,
            quality_indicators={"docstring_count": 5},
            files_involved=["test.py"],
            test_coverage=85.0,
            documentation_quality="good"
        )
        
        assert contribution.feature_name == "Test Feature"
        assert contribution.total_lines == 100
        assert contribution.ai_assistance_level == "high"
        assert contribution.test_coverage == 85.0
    
    def test_velocity_metrics_creation(self):
        """Test VelocityMetrics dataclass creation."""
        metrics = VelocityMetrics(
            baseline_velocity=50.0,
            ai_assisted_velocity=150.0,
            velocity_multiplier=3.0,
            time_saved_hours=100.0,
            features_completed=5,
            average_feature_completion_time=2.0,
            quality_maintenance_factor=1.2
        )
        
        assert metrics.baseline_velocity == 50.0
        assert metrics.velocity_multiplier == 3.0
        assert metrics.features_completed == 5
    
    def test_quality_assessment_creation(self):
        """Test QualityAssessment dataclass creation."""
        assessment = QualityAssessment(
            overall_quality_score=85,
            consistency_score=90,
            maintainability_score=80,
            documentation_score=85,
            test_coverage_score=90,
            error_handling_score=85,
            performance_score=80,
            security_score=85,
            quality_improvements=["Improvement 1"],
            areas_for_improvement=["Area 1"]
        )
        
        assert assessment.overall_quality_score == 85
        assert assessment.consistency_score == 90
        assert len(assessment.quality_improvements) == 1
        assert len(assessment.areas_for_improvement) == 1
    
    def test_contribution_statistics_creation(self):
        """Test ContributionStatistics dataclass creation."""
        stats = ContributionStatistics(
            analysis_timestamp="2024-01-01T00:00:00",
            project_overview={},
            overall_contribution_percentage=75.0,
            feature_contributions=[],
            velocity_metrics=VelocityMetrics(50.0, 150.0, 3.0, 100.0, 5, 2.0, 1.2),
            quality_assessment=QualityAssessment(85, 90, 80, 85, 90, 85, 80, 85, [], []),
            development_patterns={},
            ai_assistance_breakdown={},
            comparative_analysis={}
        )
        
        assert stats.analysis_timestamp == "2024-01-01T00:00:00"
        assert stats.overall_contribution_percentage == 75.0
        assert isinstance(stats.velocity_metrics, VelocityMetrics)
        assert isinstance(stats.quality_assessment, QualityAssessment)