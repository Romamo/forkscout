"""
Tests for OptimizationRecommender

Tests the generation of prioritized optimization recommendations based on
project analysis data.
"""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, mock_open

from forkscout.analysis.optimization_recommender import (
    OptimizationRecommender,
    Priority,
    EffortLevel,
    ImpactLevel,
    RiskLevel,
    Recommendation,
    QuickWin,
    OptimizationReport
)


class TestOptimizationRecommender:
    """Test OptimizationRecommender functionality"""
    
    @pytest.fixture
    def recommender(self):
        """Create OptimizationRecommender instance"""
        return OptimizationRecommender()
    
    @pytest.fixture
    def sample_cleanup_data(self):
        """Sample cleanup analysis data"""
        return {
            "file_analysis": {
                "total_files": 377,
                "temporary_files": 13,
                "unused_files": 258,
                "files_by_safety": {
                    "safe": 13,
                    "caution": 284,
                    "unsafe": 80
                }
            },
            "specification_analysis": {
                "total_specifications": 19,
                "complete_specifications": 4,
                "incomplete_specifications": 15,
                "total_tasks": 442,
                "completed_tasks": 221,
                "incomplete_tasks": 216,
                "completion_percentage": 50.0
            },
            "cleanup_opportunities": 5,
            "detailed_analyses": {
                "files": [
                    {
                        "path": "temp_file.log",
                        "safety_level": "safe",
                        "removal_reason": "Temporary or debug file"
                    },
                    {
                        "path": "important_file.py",
                        "safety_level": "unsafe",
                        "removal_reason": None
                    }
                ]
            }
        }
    
    @pytest.fixture
    def sample_quality_data(self):
        """Sample code quality analysis data"""
        return {
            "metrics": {
                "total_files": 75,
                "technical_debt_score": 1.26,
                "issue_count_by_priority": {
                    "high": 42,
                    "medium": 120,
                    "low": 621
                },
                "issue_count_by_type": {
                    "complex_function": 37,
                    "missing_docstring": 7,
                    "magic_number": 614,
                    "deprecated_code": 5
                }
            },
            "technical_debt_items": [
                {
                    "title": "Multiple Deprecated Code Issues",
                    "description": "Found deprecated code patterns",
                    "priority": "high"
                }
            ]
        }
    
    @pytest.fixture
    def sample_coverage_data(self):
        """Sample test coverage data"""
        return {
            "files": {
                "src/module1.py": {
                    "summary": {
                        "num_statements": 100,
                        "covered_lines": 85
                    }
                },
                "src/module2.py": {
                    "summary": {
                        "num_statements": 50,
                        "covered_lines": 40
                    }
                }
            }
        }
    
    @pytest.fixture
    def sample_docs_data(self):
        """Sample documentation analysis data"""
        return {
            "overall_score": 73.7,
            "api_coverage": 95.6,
            "readme_score": 100.0,
            "user_guides_score": 0.0,
            "contributor_docs_score": 50.0
        }
    
    def test_recommendation_priority_score(self):
        """Test recommendation priority score calculation"""
        rec = Recommendation(
            title="Test Recommendation",
            description="Test description",
            priority=Priority.HIGH,
            effort_estimate=EffortLevel.SMALL,
            impact_estimate=ImpactLevel.HIGH,
            risk_level=RiskLevel.LOW,
            category="test",
            implementation_steps=["Step 1"],
            success_criteria=["Criteria 1"]
        )
        
        # High priority (100) + High impact (100) + Small effort (10) + Low risk (10) = 220
        assert rec.priority_score == 220
    
    def test_critical_priority_score(self):
        """Test critical priority gets highest score"""
        critical_rec = Recommendation(
            title="Critical Issue",
            description="Critical description",
            priority=Priority.CRITICAL,
            effort_estimate=EffortLevel.LARGE,
            impact_estimate=ImpactLevel.LOW,
            risk_level=RiskLevel.HIGH,
            category="critical",
            implementation_steps=["Step 1"],
            success_criteria=["Criteria 1"]
        )
        
        high_rec = Recommendation(
            title="High Priority Issue",
            description="High description",
            priority=Priority.HIGH,
            effort_estimate=EffortLevel.SMALL,
            impact_estimate=ImpactLevel.HIGH,
            risk_level=RiskLevel.LOW,
            category="high",
            implementation_steps=["Step 1"],
            success_criteria=["Criteria 1"]
        )
        
        assert critical_rec.priority_score > high_rec.priority_score
    
    @patch('builtins.open', new_callable=mock_open)
    def test_load_json_success(self, mock_file, recommender):
        """Test successful JSON loading"""
        test_data = {"key": "value"}
        mock_file.return_value.read.return_value = json.dumps(test_data)
        
        with patch('json.load', return_value=test_data):
            result = recommender._load_json("test.json")
        
        assert result == test_data
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_json_file_not_found(self, mock_file, recommender):
        """Test JSON loading with missing file"""
        result = recommender._load_json("missing.json")
        assert result == {}
    
    def test_parse_documentation_markdown(self, recommender):
        """Test parsing documentation markdown report"""
        markdown_content = """
        # Documentation Report
        **Overall Score:** 73.7/100
        **API Documentation Coverage:** 95.6% across 79 files
        """
        
        result = recommender._parse_documentation_markdown(markdown_content)
        
        assert result['overall_score'] == 73.7
        assert result['api_coverage'] == 95.6
    
    def test_identify_critical_issues_low_completion(self, recommender, sample_cleanup_data, sample_quality_data, sample_coverage_data):
        """Test identification of critical issues with low completion rate"""
        # Set completion rate to 50% (below 70% threshold)
        critical_issues = recommender._identify_critical_issues(
            sample_cleanup_data, sample_quality_data, sample_coverage_data
        )
        
        assert len(critical_issues) >= 1
        assert any("Complete Critical Missing Features" in issue.title for issue in critical_issues)
        assert all(issue.priority == Priority.CRITICAL for issue in critical_issues)
    
    def test_identify_critical_issues_high_tech_debt(self, recommender, sample_cleanup_data, sample_quality_data, sample_coverage_data):
        """Test identification of critical issues with high technical debt"""
        # Set high technical debt score
        sample_quality_data['metrics']['technical_debt_score'] = 2.5
        
        critical_issues = recommender._identify_critical_issues(
            sample_cleanup_data, sample_quality_data, sample_coverage_data
        )
        
        assert len(critical_issues) >= 1
        assert any("Address Critical Technical Debt" in issue.title for issue in critical_issues)
    
    def test_generate_functionality_recommendations(self, recommender, sample_cleanup_data):
        """Test generation of functionality recommendations"""
        recommendations = recommender._generate_functionality_recommendations(sample_cleanup_data)
        
        assert len(recommendations) >= 1
        assert any("Complete Incomplete Specifications" in rec.title for rec in recommendations)
        assert all(rec.category == "functionality" for rec in recommendations)
    
    def test_generate_code_quality_recommendations(self, recommender, sample_quality_data):
        """Test generation of code quality recommendations"""
        recommendations = recommender._generate_code_quality_recommendations(sample_quality_data)
        
        assert len(recommendations) >= 1
        assert any("Fix High-Priority Code Quality Issues" in rec.title for rec in recommendations)
        assert all(rec.category == "code_quality" for rec in recommendations)
    
    def test_generate_testing_recommendations(self, recommender, sample_coverage_data):
        """Test generation of testing recommendations"""
        recommendations = recommender._generate_testing_recommendations(sample_coverage_data)
        
        # Coverage is 125/150 = 83.3%, below 90% threshold
        assert len(recommendations) >= 1
        assert any("Improve Test Coverage" in rec.title for rec in recommendations)
        assert all(rec.category == "testing" for rec in recommendations)
    
    def test_generate_documentation_recommendations(self, recommender, sample_docs_data):
        """Test generation of documentation recommendations"""
        recommendations = recommender._generate_documentation_recommendations(sample_docs_data)
        
        # Score is 73.7, below 80 threshold
        assert len(recommendations) >= 1
        assert any("Improve Documentation Coverage" in rec.title for rec in recommendations)
        assert all(rec.category == "documentation" for rec in recommendations)
    
    def test_generate_cleanup_recommendations(self, recommender, sample_cleanup_data):
        """Test generation of cleanup recommendations"""
        recommendations = recommender._generate_cleanup_recommendations(sample_cleanup_data)
        
        # Has 258 unused files and 13 temporary files
        assert len(recommendations) >= 1
        assert any("Clean Up Project Files" in rec.title for rec in recommendations)
        assert all(rec.category == "cleanup" for rec in recommendations)
    
    def test_identify_quick_wins(self, recommender, sample_cleanup_data, sample_quality_data):
        """Test identification of quick wins"""
        quick_wins = recommender._identify_quick_wins(sample_cleanup_data, sample_quality_data)
        
        assert len(quick_wins) >= 1
        assert any("Remove Temporary Files" in win.title for win in quick_wins)
        assert all(isinstance(win.effort_hours, int) for win in quick_wins)
        assert all(win.effort_hours <= 8 for win in quick_wins)  # Quick wins should be small effort
    
    def test_generate_cleanup_list(self, recommender, sample_cleanup_data):
        """Test generation of cleanup list"""
        cleanup_list = recommender._generate_cleanup_list(sample_cleanup_data)
        
        assert len(cleanup_list) >= 1
        assert any("Remove temporary file" in item for item in cleanup_list)
    
    def test_create_implementation_roadmap(self, recommender):
        """Test creation of implementation roadmap"""
        recommendations = [
            Recommendation(
                title="Critical Issue",
                description="Critical",
                priority=Priority.CRITICAL,
                effort_estimate=EffortLevel.SMALL,
                impact_estimate=ImpactLevel.HIGH,
                risk_level=RiskLevel.LOW,
                category="critical",
                implementation_steps=["Step 1"],
                success_criteria=["Criteria 1"]
            ),
            Recommendation(
                title="High Priority Issue",
                description="High",
                priority=Priority.HIGH,
                effort_estimate=EffortLevel.MEDIUM,
                impact_estimate=ImpactLevel.MEDIUM,
                risk_level=RiskLevel.MEDIUM,
                category="high",
                implementation_steps=["Step 1"],
                success_criteria=["Criteria 1"]
            )
        ]
        
        roadmap = recommender._create_implementation_roadmap(recommendations)
        
        assert "Phase 1: Critical Issues" in roadmap
        assert "Phase 2: High Priority" in roadmap
        assert len(roadmap["Phase 1: Critical Issues"]) == 1
        assert len(roadmap["Phase 2: High Priority"]) == 1
    
    def test_calculate_resource_estimates(self, recommender):
        """Test calculation of resource estimates"""
        recommendations = [
            Recommendation(
                title="Test 1",
                description="Test",
                priority=Priority.HIGH,
                effort_estimate=EffortLevel.SMALL,
                impact_estimate=ImpactLevel.HIGH,
                risk_level=RiskLevel.LOW,
                category="testing",
                implementation_steps=["Step 1"],
                success_criteria=["Criteria 1"],
                estimated_hours=10
            ),
            Recommendation(
                title="Test 2",
                description="Test",
                priority=Priority.MEDIUM,
                effort_estimate=EffortLevel.MEDIUM,
                impact_estimate=ImpactLevel.MEDIUM,
                risk_level=RiskLevel.MEDIUM,
                category="quality",
                implementation_steps=["Step 1"],
                success_criteria=["Criteria 1"],
                estimated_hours=20
            )
        ]
        
        estimates = recommender._calculate_resource_estimates(recommendations)
        
        assert estimates["testing"] == 10
        assert estimates["quality"] == 20
        assert estimates["total"] == 30
    
    def test_calculate_project_health_score(self, recommender, sample_cleanup_data, sample_quality_data, sample_coverage_data, sample_docs_data):
        """Test calculation of project health score"""
        health_score = recommender._calculate_project_health_score(
            sample_cleanup_data, sample_quality_data, sample_coverage_data, sample_docs_data
        )
        
        assert 0 <= health_score <= 100
        assert isinstance(health_score, float)
    
    @patch.object(OptimizationRecommender, '_load_json')
    @patch.object(OptimizationRecommender, '_load_documentation_analysis')
    def test_generate_recommendations_integration(
        self, 
        mock_load_docs, 
        mock_load_json, 
        recommender,
        sample_cleanup_data,
        sample_quality_data,
        sample_coverage_data,
        sample_docs_data
    ):
        """Test full recommendations generation integration"""
        # Setup mocks
        mock_load_json.side_effect = [
            sample_cleanup_data,
            sample_quality_data,
            sample_coverage_data
        ]
        mock_load_docs.return_value = sample_docs_data
        
        # Generate recommendations
        report = recommender.generate_recommendations(
            cleanup_analysis_path="cleanup.json",
            code_quality_analysis_path="quality.json",
            test_coverage_path="coverage.json",
            documentation_analysis_path="docs.md"
        )
        
        # Verify report structure
        assert isinstance(report, OptimizationReport)
        assert isinstance(report.generated_at, datetime)
        assert 0 <= report.project_health_score <= 100
        assert report.total_recommendations >= 0
        assert isinstance(report.critical_issues, list)
        assert isinstance(report.high_priority_recommendations, list)
        assert isinstance(report.medium_priority_recommendations, list)
        assert isinstance(report.low_priority_recommendations, list)
        assert isinstance(report.quick_wins, list)
        assert isinstance(report.cleanup_opportunities, list)
        assert isinstance(report.implementation_roadmap, dict)
        assert isinstance(report.resource_estimates, dict)
        
        # Verify roadmap phases
        expected_phases = [
            "Phase 1: Critical Issues",
            "Phase 2: High Priority", 
            "Phase 3: Medium Priority",
            "Phase 4: Low Priority"
        ]
        for phase in expected_phases:
            assert phase in report.implementation_roadmap
        
        # Verify resource estimates include total
        assert "total" in report.resource_estimates
    
    def test_optimization_report_total_recommendations(self):
        """Test OptimizationReport total_recommendations property"""
        report = OptimizationReport(
            generated_at=datetime.now(),
            project_health_score=75.0,
            critical_issues=[Mock()],
            high_priority_recommendations=[Mock(), Mock()],
            medium_priority_recommendations=[Mock()],
            low_priority_recommendations=[],
            quick_wins=[],
            cleanup_opportunities=[],
            implementation_roadmap={},
            resource_estimates={}
        )
        
        assert report.total_recommendations == 4  # 1 + 2 + 1 + 0
    
    def test_estimate_hours_from_effort(self, recommender):
        """Test effort level to hours conversion"""
        assert recommender._estimate_hours_from_effort(EffortLevel.SMALL) == 8
        assert recommender._estimate_hours_from_effort(EffortLevel.MEDIUM) == 16
        assert recommender._estimate_hours_from_effort(EffortLevel.LARGE) == 40
    
    def test_quick_win_dataclass(self):
        """Test QuickWin dataclass functionality"""
        win = QuickWin(
            title="Test Win",
            description="Test description",
            effort_hours=4,
            impact_description="High impact",
            implementation_steps=["Step 1", "Step 2"]
        )
        
        assert win.title == "Test Win"
        assert win.effort_hours == 4
        assert len(win.implementation_steps) == 2
        assert win.files_to_modify == []  # Default empty list
        assert win.files_to_remove == []  # Default empty list