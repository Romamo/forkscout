"""
Integration tests for optimization recommendations generation

Tests the complete workflow of generating optimization recommendations
using real analysis data files.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from forkscout.analysis.optimization_recommender import OptimizationRecommender
from forkscout.analysis.optimization_report_generator import OptimizationReportGenerator


class TestOptimizationRecommendationsIntegration:
    """Integration tests for optimization recommendations"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_cleanup_analysis(self, temp_dir):
        """Create sample cleanup analysis file"""
        data = {
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
                        "path": "forklift.log",
                        "size_bytes": 21393257,
                        "safety_level": "safe",
                        "removal_reason": "Temporary or debug file"
                    },
                    {
                        "path": "dev-artifacts/debug_output.txt",
                        "size_bytes": 62230,
                        "safety_level": "safe",
                        "removal_reason": "Temporary or debug file"
                    },
                    {
                        "path": "src/forkscout/cli.py",
                        "size_bytes": 150000,
                        "safety_level": "unsafe",
                        "removal_reason": None
                    }
                ]
            }
        }
        
        file_path = temp_dir / "cleanup_analysis.json"
        with open(file_path, 'w') as f:
            json.dump(data, f)
        
        return str(file_path)
    
    @pytest.fixture
    def sample_quality_analysis(self, temp_dir):
        """Create sample code quality analysis file"""
        data = {
            "metadata": {
                "generated_at": "2025-09-08T15:10:32.632518",
                "analyzer_version": "1.0",
                "source_path": "/test/src"
            },
            "metrics": {
                "total_files": 75,
                "total_lines": 28320,
                "average_complexity": 35.09,
                "average_maintainability": 61.06,
                "issue_count_by_type": {
                    "long_function": 73,
                    "complex_function": 37,
                    "long_parameter_list": 15,
                    "missing_docstring": 7,
                    "magic_number": 614,
                    "large_class": 31,
                    "deprecated_code": 5,
                    "todo_comment": 1
                },
                "issue_count_by_priority": {
                    "medium": 120,
                    "high": 42,
                    "low": 621
                },
                "technical_debt_score": 1.26
            },
            "technical_debt_items": [
                {
                    "title": "Multiple Complex Function Issues",
                    "description": "Found 11 instances of complex_function across 7 files",
                    "priority": "high",
                    "effort_estimate": "medium",
                    "impact_assessment": "Medium - Affects code readability and maintainability"
                },
                {
                    "title": "Multiple Deprecated Code Issues",
                    "description": "Found 5 instances of deprecated_code across 1 files",
                    "priority": "high",
                    "effort_estimate": "small",
                    "impact_assessment": "High - Affects reliability and maintainability"
                }
            ]
        }
        
        file_path = temp_dir / "quality_analysis.json"
        with open(file_path, 'w') as f:
            json.dump(data, f)
        
        return str(file_path)
    
    @pytest.fixture
    def sample_coverage_data(self, temp_dir):
        """Create sample test coverage file"""
        data = {
            "meta": {
                "format": 3,
                "version": "7.10.3",
                "timestamp": "2025-09-08T15:19:47.815057"
            },
            "files": {
                "src/forkscout/__init__.py": {
                    "summary": {
                        "covered_lines": 6,
                        "num_statements": 6,
                        "percent_covered": 100.0
                    }
                },
                "src/forkscout/cli.py": {
                    "summary": {
                        "covered_lines": 150,
                        "num_statements": 200,
                        "percent_covered": 75.0
                    }
                },
                "src/forkscout/analysis/analyzer.py": {
                    "summary": {
                        "covered_lines": 80,
                        "num_statements": 120,
                        "percent_covered": 66.7
                    }
                }
            }
        }
        
        file_path = temp_dir / "coverage.json"
        with open(file_path, 'w') as f:
            json.dump(data, f)
        
        return str(file_path)
    
    @pytest.fixture
    def sample_documentation_analysis(self, temp_dir):
        """Create sample documentation analysis file"""
        content = """# Documentation Completeness Assessment Report

**Generated:** 2025-09-08 15:59:58
**Overall Score:** 73.7/100

🟠 **Needs Improvement** (50-74)

## Executive Summary

⚠️ **Overall Status:** Documentation needs improvement in several key areas.

- **API Documentation Coverage:** 95.6% across 79 files
- **README Completeness:** 100.0%
- **README Accuracy:** 100.0%
- **User Guides Score:** 0.0%
- **Contributor Docs Score:** 50.0%
- **Examples Validation Score:** 100.0%

- **Documentation Gaps:** 0 critical, 2 high priority, 15 medium priority

## Recommendations

🟠 HIGH PRIORITY: Improve core documentation coverage
  - Add docstrings to 2 files with low API coverage
🟡 MEDIUM PRIORITY: Address 15 documentation gaps
  - Focus on missing docstrings for public APIs
"""
        
        file_path = temp_dir / "documentation_analysis.md"
        with open(file_path, 'w') as f:
            f.write(content)
        
        return str(file_path)
    
    def test_generate_recommendations_with_real_data(
        self,
        sample_cleanup_analysis,
        sample_quality_analysis,
        sample_coverage_data,
        sample_documentation_analysis
    ):
        """Test generating recommendations with realistic data"""
        recommender = OptimizationRecommender()
        
        report = recommender.generate_recommendations(
            cleanup_analysis_path=sample_cleanup_analysis,
            code_quality_analysis_path=sample_quality_analysis,
            test_coverage_path=sample_coverage_data,
            documentation_analysis_path=sample_documentation_analysis
        )
        
        # Verify report structure
        assert report is not None
        assert 0 <= report.project_health_score <= 100
        assert report.total_recommendations > 0
        
        # Should have recommendations due to low completion rate (50%)
        assert len(report.critical_issues) > 0 or len(report.high_priority_recommendations) > 0
        
        # Should have quick wins due to temporary files
        assert len(report.quick_wins) > 0
        
        # Should have cleanup opportunities
        assert len(report.cleanup_opportunities) > 0
        
        # Verify roadmap structure
        expected_phases = [
            "Phase 1: Critical Issues",
            "Phase 2: High Priority",
            "Phase 3: Medium Priority", 
            "Phase 4: Low Priority"
        ]
        for phase in expected_phases:
            assert phase in report.implementation_roadmap
        
        # Verify resource estimates
        assert "total" in report.resource_estimates
        assert report.resource_estimates["total"] > 0
    
    def test_generate_all_report_formats(
        self,
        temp_dir,
        sample_cleanup_analysis,
        sample_quality_analysis,
        sample_coverage_data,
        sample_documentation_analysis
    ):
        """Test generating all report formats"""
        # Generate recommendations
        recommender = OptimizationRecommender()
        report = recommender.generate_recommendations(
            cleanup_analysis_path=sample_cleanup_analysis,
            code_quality_analysis_path=sample_quality_analysis,
            test_coverage_path=sample_coverage_data,
            documentation_analysis_path=sample_documentation_analysis
        )
        
        # Generate reports
        report_generator = OptimizationReportGenerator()
        
        # Test markdown report
        markdown_path = temp_dir / "optimization_report.md"
        report_generator.generate_markdown_report(report, str(markdown_path))
        
        assert markdown_path.exists()
        content = markdown_path.read_text()
        assert "# Project Optimization Recommendations" in content
        assert "Project Health Score" in content
        assert "Critical Issues" in content or "Quick Wins" in content
        
        # Test JSON report
        json_path = temp_dir / "optimization_report.json"
        report_generator.generate_json_report(report, str(json_path))
        
        assert json_path.exists()
        with open(json_path) as f:
            json_data = json.load(f)
        
        assert "generated_at" in json_data
        assert "project_health_score" in json_data
        assert "summary" in json_data
        assert "critical_issues" in json_data
        assert "quick_wins" in json_data
        
        # Test implementation roadmap
        roadmap_path = temp_dir / "implementation_roadmap.md"
        report_generator.generate_implementation_roadmap(report, str(roadmap_path))
        
        assert roadmap_path.exists()
        roadmap_content = roadmap_path.read_text()
        assert "# Implementation Roadmap" in roadmap_content
        assert "Phase" in roadmap_content
    
    def test_recommendations_prioritization(
        self,
        sample_cleanup_analysis,
        sample_quality_analysis,
        sample_coverage_data,
        sample_documentation_analysis
    ):
        """Test that recommendations are properly prioritized"""
        recommender = OptimizationRecommender()
        
        report = recommender.generate_recommendations(
            cleanup_analysis_path=sample_cleanup_analysis,
            code_quality_analysis_path=sample_quality_analysis,
            test_coverage_path=sample_coverage_data,
            documentation_analysis_path=sample_documentation_analysis
        )
        
        # Verify critical issues have highest priority
        for issue in report.critical_issues:
            assert issue.priority.value == "critical"
        
        # Verify high priority recommendations
        for rec in report.high_priority_recommendations:
            assert rec.priority.value == "high"
        
        # Verify medium priority recommendations
        for rec in report.medium_priority_recommendations:
            assert rec.priority.value == "medium"
        
        # Verify low priority recommendations
        for rec in report.low_priority_recommendations:
            assert rec.priority.value == "low"
        
        # Verify quick wins have reasonable effort estimates
        for win in report.quick_wins:
            assert win.effort_hours <= 8  # Should be quick
    
    def test_resource_estimation_accuracy(
        self,
        sample_cleanup_analysis,
        sample_quality_analysis,
        sample_coverage_data,
        sample_documentation_analysis
    ):
        """Test accuracy of resource estimates"""
        recommender = OptimizationRecommender()
        
        report = recommender.generate_recommendations(
            cleanup_analysis_path=sample_cleanup_analysis,
            code_quality_analysis_path=sample_quality_analysis,
            test_coverage_path=sample_coverage_data,
            documentation_analysis_path=sample_documentation_analysis
        )
        
        # Verify resource estimates are reasonable
        total_hours = report.resource_estimates.get("total", 0)
        assert total_hours > 0
        assert total_hours < 1000  # Should be reasonable for a project
        
        # Verify category breakdown sums to total
        category_sum = sum(
            hours for category, hours in report.resource_estimates.items()
            if category != "total"
        )
        assert category_sum == total_hours
    
    def test_health_score_calculation(
        self,
        sample_cleanup_analysis,
        sample_quality_analysis,
        sample_coverage_data,
        sample_documentation_analysis
    ):
        """Test project health score calculation"""
        recommender = OptimizationRecommender()
        
        report = recommender.generate_recommendations(
            cleanup_analysis_path=sample_cleanup_analysis,
            code_quality_analysis_path=sample_quality_analysis,
            test_coverage_path=sample_coverage_data,
            documentation_analysis_path=sample_documentation_analysis
        )
        
        # Health score should be reasonable given the test data
        # - 50% completion rate (low)
        # - 1.26 technical debt score (moderate)
        # - ~72% test coverage (moderate)
        # - 73.7 documentation score (moderate)
        
        assert 40 <= report.project_health_score <= 80  # Should be in moderate range
    
    def test_missing_input_files_handling(self, temp_dir):
        """Test handling of missing input files"""
        recommender = OptimizationRecommender()
        
        # Test with non-existent files
        report = recommender.generate_recommendations(
            cleanup_analysis_path=str(temp_dir / "missing1.json"),
            code_quality_analysis_path=str(temp_dir / "missing2.json"),
            test_coverage_path=str(temp_dir / "missing3.json"),
            documentation_analysis_path=str(temp_dir / "missing4.md")
        )
        
        # Should still generate a report with empty data
        assert report is not None
        assert report.project_health_score >= 0
        assert isinstance(report.total_recommendations, int)
    
    def test_edge_case_data_handling(self, temp_dir):
        """Test handling of edge case data"""
        # Create files with minimal/edge case data
        cleanup_data = {
            "file_analysis": {"total_files": 0, "temporary_files": 0, "unused_files": 0},
            "specification_analysis": {"total_tasks": 0, "completed_tasks": 0, "completion_percentage": 0}
        }
        
        quality_data = {
            "metrics": {
                "total_files": 0,
                "technical_debt_score": 0,
                "issue_count_by_priority": {},
                "issue_count_by_type": {}
            },
            "technical_debt_items": []
        }
        
        coverage_data = {"files": {}}
        
        # Create files
        cleanup_path = temp_dir / "cleanup.json"
        quality_path = temp_dir / "quality.json"
        coverage_path = temp_dir / "coverage.json"
        docs_path = temp_dir / "docs.md"
        
        with open(cleanup_path, 'w') as f:
            json.dump(cleanup_data, f)
        with open(quality_path, 'w') as f:
            json.dump(quality_data, f)
        with open(coverage_path, 'w') as f:
            json.dump(coverage_data, f)
        with open(docs_path, 'w') as f:
            f.write("# Empty Documentation Report\n**Overall Score:** 0/100")
        
        # Generate recommendations
        recommender = OptimizationRecommender()
        report = recommender.generate_recommendations(
            cleanup_analysis_path=str(cleanup_path),
            code_quality_analysis_path=str(quality_path),
            test_coverage_path=str(coverage_path),
            documentation_analysis_path=str(docs_path)
        )
        
        # Should handle edge cases gracefully
        assert report is not None
        assert 0 <= report.project_health_score <= 100
        assert report.total_recommendations >= 0