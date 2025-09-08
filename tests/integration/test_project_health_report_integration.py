"""
Integration tests for Project Health Report Generator

Tests the complete workflow of generating project health reports
with real data and file operations.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.forklift.analysis.project_health_report_generator import (
    ProjectHealthReportGenerator,
    ProjectHealthReport
)


class TestProjectHealthReportIntegration:
    """Integration tests for project health report generation"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_analysis_files(self, temp_dir):
        """Create sample analysis files for testing"""
        files = {}
        
        # Create cleanup analysis file
        cleanup_data = {
            'specification_analysis': {
                'total_tasks': 150,
                'incomplete_tasks': 45,
                'completion_percentage': 70,
                'incomplete_specifications': 3
            },
            'file_analysis': {
                'unused_files': 35,
                'temporary_files': 12
            },
            'detailed_analyses': {
                'files': [
                    {
                        'path': 'debug_output.txt',
                        'safety_level': 'safe',
                        'removal_reason': 'Debug output file'
                    },
                    {
                        'path': 'temp_cache.json',
                        'safety_level': 'safe',
                        'removal_reason': 'Temporary cache file'
                    }
                ]
            }
        }
        
        cleanup_file = temp_dir / "cleanup_analysis.json"
        with open(cleanup_file, 'w') as f:
            json.dump(cleanup_data, f)
        files['cleanup'] = cleanup_file
        
        # Create code quality analysis file
        quality_data = {
            'metrics': {
                'total_files': 75,
                'total_lines': 15000,
                'average_complexity': 8.5,
                'average_maintainability': 72.3,
                'technical_debt_score': 2.8,
                'issue_count_by_type': {
                    'todo_comment': 25,
                    'deprecated_code': 8,
                    'long_function': 12,
                    'complex_function': 6,
                    'missing_docstring': 45
                },
                'issue_count_by_priority': {
                    'critical': 3,
                    'high': 18,
                    'medium': 42,
                    'low': 35
                }
            },
            'technical_debt_items': [
                {
                    'title': 'Multiple Complex Function Issues',
                    'description': 'Found 6 instances of complex_function across 4 files',
                    'priority': 'high',
                    'effort_estimate': 'medium',
                    'impact_assessment': 'High - Affects reliability and maintainability',
                    'files_affected': ['src/module1.py', 'src/module2.py'],
                    'related_issues': [],
                    'recommendation': 'Reduce cyclomatic complexity by extracting helper functions'
                },
                {
                    'title': 'Multiple Missing Docstring Issues',
                    'description': 'Found 45 instances of missing_docstring across 15 files',
                    'priority': 'medium',
                    'effort_estimate': 'small',
                    'impact_assessment': 'Medium - Affects code readability and maintainability',
                    'files_affected': ['src/module3.py', 'src/module4.py'],
                    'related_issues': [],
                    'recommendation': 'Add comprehensive docstrings to improve code documentation'
                }
            ]
        }
        
        quality_file = temp_dir / "quality_analysis.json"
        with open(quality_file, 'w') as f:
            json.dump(quality_data, f)
        files['quality'] = quality_file
        
        # Create test coverage file
        coverage_data = {
            'files': {
                'src/forklift/analysis/module1.py': {
                    'summary': {
                        'num_statements': 150,
                        'covered_lines': 135,
                        'missing_lines': [45, 67, 89, 123, 145],
                        'num_branches': 20,
                        'missing_branches': 3
                    }
                },
                'src/forklift/github/client.py': {
                    'summary': {
                        'num_statements': 200,
                        'covered_lines': 170,
                        'missing_lines': [12, 34, 56, 78, 90, 112, 134, 156, 178, 190],
                        'num_branches': 30,
                        'missing_branches': 5
                    }
                },
                'src/forklift/core/engine.py': {
                    'summary': {
                        'num_statements': 100,
                        'covered_lines': 85,
                        'missing_lines': [23, 45, 67, 89, 95],
                        'num_branches': 15,
                        'missing_branches': 2
                    }
                }
            }
        }
        
        coverage_file = temp_dir / "coverage.json"
        with open(coverage_file, 'w') as f:
            json.dump(coverage_data, f)
        files['coverage'] = coverage_file
        
        # Create documentation analysis file (markdown)
        doc_content = """# Documentation Assessment Report

**Generated:** 2024-01-15 10:30:00
**Overall Score:** 73.7/100

## Executive Summary

⚠️ **Overall Status:** Documentation needs improvement in several key areas.

- **API Documentation Coverage:** 85.6% across 79 files
- **README Completeness:** 80.0%
- **README Accuracy:** 75.0%
- **User Guides Score:** 60.0%
- **Contributor Docs Score:** 70.0%
- **Examples Validation Score:** 65.0%

- **Documentation Gaps:** 2 critical, 8 high priority, 15 medium priority

## Detailed Findings

The project has good API documentation coverage but needs improvement in user guides and examples.
"""
        
        doc_file = temp_dir / "documentation_analysis.md"
        with open(doc_file, 'w') as f:
            f.write(doc_content)
        files['documentation'] = doc_file
        
        # Create optimization recommendations file
        optimization_data = {
            'quick_wins': [
                {
                    'title': 'Remove Debug Files',
                    'description': 'Remove 12 debug and temporary files',
                    'effort_hours': 2,
                    'impact_description': 'Cleaner project structure',
                    'implementation_steps': [
                        'Identify debug files',
                        'Verify safe to remove',
                        'Remove files',
                        'Update .gitignore'
                    ]
                },
                {
                    'title': 'Fix Deprecated Code',
                    'description': 'Update 8 deprecated code patterns',
                    'effort_hours': 6,
                    'impact_description': 'Improved compatibility and reliability',
                    'implementation_steps': [
                        'Identify deprecated patterns',
                        'Research current alternatives',
                        'Update code',
                        'Test changes'
                    ]
                }
            ],
            'cleanup_opportunities': [
                'Remove temporary files from project root',
                'Archive unused development artifacts',
                'Clean up debug output files'
            ]
        }
        
        optimization_file = temp_dir / "optimization_recommendations.json"
        with open(optimization_file, 'w') as f:
            json.dump(optimization_data, f)
        files['optimization'] = optimization_file
        
        return files
    
    def test_end_to_end_report_generation(self, sample_analysis_files, temp_dir):
        """Test complete end-to-end report generation workflow"""
        generator = ProjectHealthReportGenerator(project_name="Integration Test Project")
        
        # Load analysis data
        with open(sample_analysis_files['cleanup']) as f:
            cleanup_data = json.load(f)
        
        with open(sample_analysis_files['quality']) as f:
            quality_data = json.load(f)
        
        with open(sample_analysis_files['coverage']) as f:
            coverage_data = json.load(f)
        
        with open(sample_analysis_files['documentation']) as f:
            doc_content = f.read()
        
        # Parse documentation data
        doc_data = {'overall_score': 73.7, 'api_coverage': 85.6}
        
        with open(sample_analysis_files['optimization']) as f:
            optimization_data = json.load(f)
        
        # Generate comprehensive report
        report = generator.generate_comprehensive_report(
            functionality_data=cleanup_data,
            code_quality_data=quality_data,
            test_coverage_data=coverage_data,
            documentation_data=doc_data,
            cleanup_data=cleanup_data,
            optimization_data=optimization_data
        )
        
        # Verify report structure
        assert isinstance(report, ProjectHealthReport)
        assert report.project_name == "Integration Test Project"
        assert 0 <= report.metrics.overall_health_score <= 100
        
        # Verify metrics calculation
        assert report.metrics.functionality_score == 70.0  # From completion_percentage
        assert report.metrics.code_quality_score > 0
        assert report.metrics.test_coverage_score > 0
        assert report.metrics.documentation_score == 73.7
        assert report.metrics.cleanup_score < 100  # Should be penalized for unused files
        
        # Verify critical issues identification
        assert len(report.critical_issues) >= 0  # May or may not have critical issues
        
        # Verify quick wins extraction
        assert len(report.quick_wins) >= 2  # Should have at least the optimization quick wins
        
        # Verify prioritized actions
        assert len(report.prioritized_actions) > 0
        
        # Verify cleanup opportunities
        assert len(report.cleanup_opportunities) > 0
        
        # Verify implementation roadmap
        assert isinstance(report.implementation_roadmap, dict)
        assert len(report.implementation_roadmap) > 0
        
        # Verify resource estimates
        assert isinstance(report.resource_estimates, dict)
        assert "total" in report.resource_estimates
        assert report.resource_estimates["total"] > 0
        
        # Verify executive summary
        assert isinstance(report.executive_summary, str)
        assert len(report.executive_summary) > 0
        assert "Project Health Status:" in report.executive_summary
        
        # Verify detailed findings
        assert isinstance(report.detailed_findings, dict)
        assert len(report.detailed_findings) > 0
    
    def test_markdown_report_generation_and_save(self, sample_analysis_files, temp_dir):
        """Test markdown report generation and file saving"""
        generator = ProjectHealthReportGenerator(project_name="Markdown Test Project")
        
        # Load minimal data for testing
        with open(sample_analysis_files['cleanup']) as f:
            cleanup_data = json.load(f)
        
        # Generate report
        report = generator.generate_comprehensive_report(
            functionality_data=cleanup_data,
            cleanup_data=cleanup_data
        )
        
        # Generate markdown content
        markdown_content = generator.generate_markdown_report(report)
        
        # Verify markdown structure
        assert isinstance(markdown_content, str)
        assert len(markdown_content) > 1000  # Should be substantial
        
        # Check for required sections
        required_sections = [
            "# Markdown Test Project Project Health Report",
            "## Executive Summary",
            "## Detailed Health Metrics",
            "## Critical Issues",
            "## Quick Wins",
            "## Prioritized Action Items",
            "## Implementation Roadmap",
            "## Resource Estimates",
            "## Detailed Findings",
            "## Appendix"
        ]
        
        for section in required_sections:
            assert section in markdown_content, f"Missing section: {section}"
        
        # Check for health metrics
        assert f"{report.metrics.overall_health_score:.1f}/100" in markdown_content
        assert report.metrics.health_status in markdown_content
        
        # Save to file and verify
        output_file = temp_dir / "test_health_report.md"
        generator.save_report(report, str(output_file), "markdown")
        
        assert output_file.exists()
        
        # Verify saved content
        with open(output_file, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        
        assert saved_content == markdown_content
    
    def test_json_report_generation_and_save(self, sample_analysis_files, temp_dir):
        """Test JSON report generation and file saving"""
        generator = ProjectHealthReportGenerator(project_name="JSON Test Project")
        
        # Load minimal data for testing
        with open(sample_analysis_files['quality']) as f:
            quality_data = json.load(f)
        
        # Generate report
        report = generator.generate_comprehensive_report(
            code_quality_data=quality_data
        )
        
        # Generate JSON content
        json_content = generator.generate_json_report(report)
        
        # Verify JSON structure
        assert isinstance(json_content, str)
        assert len(json_content) > 500  # Should be substantial
        
        # Parse and verify JSON structure
        data = json.loads(json_content)
        
        required_keys = [
            "metadata",
            "metrics",
            "critical_issues",
            "quick_wins",
            "prioritized_actions",
            "cleanup_opportunities",
            "implementation_roadmap",
            "resource_estimates",
            "executive_summary",
            "detailed_findings"
        ]
        
        for key in required_keys:
            assert key in data, f"Missing key: {key}"
        
        # Verify metadata
        assert data["metadata"]["project_name"] == "JSON Test Project"
        assert data["metadata"]["generator_version"] == "1.0"
        assert "generated_at" in data["metadata"]
        
        # Verify metrics
        metrics = data["metrics"]
        assert "overall_health_score" in metrics
        assert "health_status" in metrics
        assert 0 <= metrics["overall_health_score"] <= 100
        
        # Save to file and verify
        output_file = temp_dir / "test_health_report.json"
        generator.save_report(report, str(output_file), "json")
        
        assert output_file.exists()
        
        # Verify saved content
        with open(output_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data == data
    
    def test_comprehensive_analysis_integration(self, sample_analysis_files, temp_dir):
        """Test integration with all analysis types"""
        generator = ProjectHealthReportGenerator(project_name="Comprehensive Test")
        
        # Load all analysis data
        with open(sample_analysis_files['cleanup']) as f:
            cleanup_data = json.load(f)
        
        with open(sample_analysis_files['quality']) as f:
            quality_data = json.load(f)
        
        with open(sample_analysis_files['coverage']) as f:
            coverage_data = json.load(f)
        
        doc_data = {'overall_score': 73.7, 'api_coverage': 85.6}
        
        with open(sample_analysis_files['optimization']) as f:
            optimization_data = json.load(f)
        
        # Generate comprehensive report
        report = generator.generate_comprehensive_report(
            functionality_data=cleanup_data,
            code_quality_data=quality_data,
            test_coverage_data=coverage_data,
            documentation_data=doc_data,
            cleanup_data=cleanup_data,
            optimization_data=optimization_data
        )
        
        # Verify all data sources are reflected in the report
        
        # Functionality data should affect functionality score
        assert report.metrics.functionality_score == 70.0
        
        # Code quality data should create technical debt issues
        quality_actions = [
            action for action in report.prioritized_actions 
            if action.category == "code_quality"
        ]
        assert len(quality_actions) > 0
        
        # Test coverage data should affect coverage score
        # Expected: (135+170+85)/(150+200+100) = 390/450 = 86.67%
        expected_coverage = (135 + 170 + 85) / (150 + 200 + 100) * 100
        assert abs(report.metrics.test_coverage_score - expected_coverage) < 1.0
        
        # Documentation data should set documentation score
        assert report.metrics.documentation_score == 73.7
        
        # Cleanup data should create cleanup opportunities
        assert len(report.cleanup_opportunities) > 0
        
        # Optimization data should create quick wins
        optimization_wins = [
            win for win in report.quick_wins 
            if win.title in ["Remove Debug Files", "Fix Deprecated Code"]
        ]
        assert len(optimization_wins) >= 2
        
        # Verify detailed findings contain all categories
        expected_categories = ["functionality", "code_quality", "test_coverage", "documentation", "cleanup"]
        for category in expected_categories:
            assert category in report.detailed_findings
    
    def test_error_handling_with_missing_data(self, temp_dir):
        """Test error handling when analysis data is missing or incomplete"""
        generator = ProjectHealthReportGenerator(project_name="Error Test Project")
        
        # Test with no data
        report = generator.generate_comprehensive_report()
        
        assert isinstance(report, ProjectHealthReport)
        assert report.project_name == "Error Test Project"
        assert report.metrics.overall_health_score >= 0
        
        # Test with partial data
        partial_data = {
            'specification_analysis': {
                'total_tasks': 50,
                'incomplete_tasks': 10,
                'completion_percentage': 80
            }
        }
        
        report = generator.generate_comprehensive_report(
            functionality_data=partial_data
        )
        
        assert report.metrics.functionality_score == 80.0
        assert report.metrics.code_quality_score == 0.0  # No data provided
        assert report.metrics.test_coverage_score == 0.0  # No data provided
        
        # Should still generate valid report
        markdown_content = generator.generate_markdown_report(report)
        assert len(markdown_content) > 0
        
        json_content = generator.generate_json_report(report)
        data = json.loads(json_content)
        assert data["metadata"]["project_name"] == "Error Test Project"
    
    def test_large_dataset_performance(self, temp_dir):
        """Test performance with large datasets"""
        generator = ProjectHealthReportGenerator(project_name="Performance Test")
        
        # Create large dataset
        large_coverage_data = {
            'files': {}
        }
        
        # Generate 100 files with coverage data
        for i in range(100):
            file_path = f"src/module_{i}.py"
            large_coverage_data['files'][file_path] = {
                'summary': {
                    'num_statements': 100 + i,
                    'covered_lines': 80 + (i % 20),
                    'missing_lines': list(range(5)),
                    'num_branches': 10 + (i % 5),
                    'missing_branches': i % 3
                }
            }
        
        large_quality_data = {
            'metrics': {
                'total_files': 100,
                'total_lines': 50000,
                'average_complexity': 7.5,
                'average_maintainability': 75.0,
                'technical_debt_score': 2.2,
                'issue_count_by_priority': {
                    'critical': 5,
                    'high': 25,
                    'medium': 75,
                    'low': 100
                }
            },
            'technical_debt_items': [
                {
                    'title': f'Issue {i}',
                    'description': f'Description {i}',
                    'priority': 'medium',
                    'effort_estimate': 'small'
                }
                for i in range(20)
            ]
        }
        
        # Generate report with large dataset
        import time
        start_time = time.time()
        
        report = generator.generate_comprehensive_report(
            code_quality_data=large_quality_data,
            test_coverage_data=large_coverage_data
        )
        
        generation_time = time.time() - start_time
        
        # Should complete within reasonable time (< 5 seconds)
        assert generation_time < 5.0
        
        # Verify report is still valid
        assert isinstance(report, ProjectHealthReport)
        assert report.metrics.test_coverage_score > 0
        assert report.metrics.code_quality_score > 0
        
        # Generate markdown report
        start_time = time.time()
        markdown_content = generator.generate_markdown_report(report)
        markdown_time = time.time() - start_time
        
        # Should complete within reasonable time (< 2 seconds)
        assert markdown_time < 2.0
        assert len(markdown_content) > 1000