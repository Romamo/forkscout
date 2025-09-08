"""
Integration tests for test coverage analysis functionality.
"""

import pytest
from pathlib import Path
import tempfile
import json

from forklift.analysis.test_coverage_analyzer import TestCoverageAnalyzer, TestCoverageAnalysis
from forklift.analysis.test_coverage_report_generator import TestCoverageReportGenerator


class TestCoverageAnalysisIntegration:
    """Integration tests for test coverage analysis."""
    
    @pytest.mark.integration
    def test_test_coverage_analyzer_initialization(self):
        """Test that test coverage analyzer initializes correctly."""
        analyzer = TestCoverageAnalyzer()
        
        assert analyzer.project_root == Path.cwd()
        assert analyzer.src_path == Path.cwd() / "src"
        assert analyzer.tests_path == Path.cwd() / "tests"
    
    @pytest.mark.integration
    def test_test_coverage_analyzer_with_custom_root(self):
        """Test analyzer with custom project root."""
        custom_root = Path("/tmp/test_project")
        analyzer = TestCoverageAnalyzer(custom_root)
        
        assert analyzer.project_root == custom_root
        assert analyzer.src_path == custom_root / "src"
        assert analyzer.tests_path == custom_root / "tests"
    
    @pytest.mark.integration
    def test_coverage_data_loading(self):
        """Test loading coverage data from existing coverage.json."""
        analyzer = TestCoverageAnalyzer()
        
        # Should load existing coverage data
        coverage_data = analyzer._load_coverage_data()
        
        assert isinstance(coverage_data, dict)
        assert "files" in coverage_data or coverage_data == {"files": {}}
    
    @pytest.mark.integration
    def test_test_failure_parsing(self):
        """Test parsing test failures from pytest output."""
        analyzer = TestCoverageAnalyzer()
        
        sample_output = """
        FAILED tests/unit/test_example.py::TestExample::test_method - AssertionError: assert False
        ERROR tests/integration/test_other.py::TestOther::test_error - TypeError: 'NoneType' object has no attribute 'method'
        """
        
        failures = analyzer._parse_test_failures(sample_output, "FAILED")
        errors = analyzer._parse_test_failures(sample_output, "ERROR")
        
        assert len(failures) == 1
        assert len(errors) == 1
        
        assert failures[0].test_name == "TestExample::test_method"
        assert failures[0].error_type == "Assertion Error"
        
        assert errors[0].test_name == "TestOther::test_error"
        assert errors[0].error_type == "Type Error"
    
    @pytest.mark.integration
    def test_error_type_classification(self):
        """Test error type classification."""
        analyzer = TestCoverageAnalyzer()
        
        test_cases = [
            ("AssertionError: assert False", "Assertion Error"),
            ("AttributeError: 'NoneType' object has no attribute 'method'", "Attribute Error"),
            ("TypeError: unsupported operand type", "Type Error"),
            ("KeyError: 'missing_key'", "Key Error"),
            ("ValueError: invalid literal", "Value Error"),
            ("TimeoutError: operation timed out", "Timeout Error"),
            ("ConnectionError: failed to connect", "Network Error"),
            ("Mock object has no attribute", "Mock Error"),
            ("Some other error", "Other Error")
        ]
        
        for error_msg, expected_type in test_cases:
            result = analyzer._classify_error_type(error_msg)
            assert result == expected_type
    
    @pytest.mark.integration
    def test_flaky_test_detection(self):
        """Test detection of potentially flaky tests."""
        analyzer = TestCoverageAnalyzer()
        
        flaky_indicators = [
            "timeout occurred during test",
            "connection refused",
            "network error",
            "race condition detected",
            "timing issue",
            "async operation failed",
            "coroutine was never awaited",
            "random seed changed"
        ]
        
        non_flaky_indicators = [
            "assertion failed",
            "type error occurred",
            "key not found",
            "value error"
        ]
        
        for indicator in flaky_indicators:
            assert analyzer._is_potentially_flaky(indicator) == True
        
        for indicator in non_flaky_indicators:
            assert analyzer._is_potentially_flaky(indicator) == False
    
    @pytest.mark.integration
    def test_coverage_metrics_calculation(self):
        """Test calculation of coverage metrics."""
        analyzer = TestCoverageAnalyzer()
        
        # Mock coverage data
        mock_coverage_data = {
            "files": {
                "src/module1.py": {
                    "summary": {
                        "covered_lines": 80,
                        "num_statements": 100,
                        "missing_branches": 5,
                        "num_branches": 20
                    },
                    "missing_lines": [10, 20, 30]
                },
                "src/module2.py": {
                    "summary": {
                        "covered_lines": 90,
                        "num_statements": 100,
                        "missing_branches": 2,
                        "num_branches": 15
                    },
                    "missing_lines": [5, 15]
                }
            }
        }
        
        metrics = analyzer._calculate_overall_coverage(mock_coverage_data)
        
        assert metrics.covered_lines == 170
        assert metrics.total_lines == 200
        assert metrics.coverage_percentage == 85.0
        assert metrics.missing_branches == 7
        assert metrics.branch_coverage == pytest.approx(80.0, rel=1e-2)  # (35-7)/35 * 100
    
    @pytest.mark.integration
    def test_module_coverage_calculation(self):
        """Test calculation of module-specific coverage."""
        analyzer = TestCoverageAnalyzer()
        
        mock_coverage_data = {
            "files": {
                "src/forklift/analysis/module1.py": {
                    "summary": {
                        "covered_lines": 80,
                        "num_statements": 100,
                        "missing_branches": 5,
                        "num_branches": 20
                    },
                    "missing_lines": [10, 20]
                },
                "src/forklift/github/module2.py": {
                    "summary": {
                        "covered_lines": 90,
                        "num_statements": 100,
                        "missing_branches": 2,
                        "num_branches": 15
                    },
                    "missing_lines": [5]
                }
            }
        }
        
        module_coverage = analyzer._calculate_module_coverage(mock_coverage_data)
        
        assert "analysis" in module_coverage
        assert "github" in module_coverage
        
        analysis_metrics = module_coverage["analysis"]
        assert analysis_metrics.coverage_percentage == 80.0
        assert analysis_metrics.covered_lines == 80
        
        github_metrics = module_coverage["github"]
        assert github_metrics.coverage_percentage == 90.0
        assert github_metrics.covered_lines == 90
    
    @pytest.mark.integration
    def test_test_organization_scoring(self):
        """Test test organization scoring."""
        analyzer = TestCoverageAnalyzer()
        
        # Test with current project structure
        score = analyzer._calculate_organization_score()
        
        # Should be a valid score between 0 and 100
        assert 0 <= score <= 100
        assert isinstance(score, float)
    
    @pytest.mark.integration
    def test_reliability_scoring(self):
        """Test reliability scoring calculation."""
        analyzer = TestCoverageAnalyzer()
        
        # Test with no failures
        score = analyzer._calculate_reliability_score([], [])
        assert score == 100.0
        
        # Test with some failures
        from forklift.analysis.test_coverage_analyzer import TestFailure
        
        failures = [
            TestFailure("test1", "file1.py", "Assertion Error", "msg1", False),
            TestFailure("test2", "file2.py", "Type Error", "msg2", True)
        ]
        
        score = analyzer._calculate_reliability_score(failures, [])
        assert 0 <= score < 100
    
    @pytest.mark.integration
    def test_quality_issues_identification(self):
        """Test identification of test quality issues."""
        analyzer = TestCoverageAnalyzer()
        
        issues = analyzer._identify_quality_issues()
        
        assert isinstance(issues, list)
        for issue in issues:
            assert hasattr(issue, 'issue_type')
            assert hasattr(issue, 'description')
            assert hasattr(issue, 'severity')
            assert hasattr(issue, 'recommendation')
            assert issue.severity in ['critical', 'high', 'medium', 'low']
    
    @pytest.mark.integration
    def test_full_analysis_workflow(self):
        """Test complete analysis workflow."""
        analyzer = TestCoverageAnalyzer()
        
        # Run full analysis
        analysis = analyzer.analyze_test_coverage_and_quality()
        
        # Verify analysis structure
        assert isinstance(analysis, TestCoverageAnalysis)
        assert hasattr(analysis, 'overall_coverage')
        assert hasattr(analysis, 'module_coverage')
        assert hasattr(analysis, 'test_failures')
        assert hasattr(analysis, 'test_errors')
        assert hasattr(analysis, 'quality_issues')
        assert hasattr(analysis, 'test_organization_score')
        assert hasattr(analysis, 'test_reliability_score')
        assert hasattr(analysis, 'recommendations')
        
        # Verify metrics are reasonable
        assert 0 <= analysis.overall_coverage.coverage_percentage <= 100
        assert 0 <= analysis.overall_coverage.branch_coverage <= 100
        assert 0 <= analysis.test_organization_score <= 100
        assert 0 <= analysis.test_reliability_score <= 100
        
        # Verify collections are lists
        assert isinstance(analysis.test_failures, list)
        assert isinstance(analysis.test_errors, list)
        assert isinstance(analysis.quality_issues, list)
        assert isinstance(analysis.recommendations, list)


class TestCoverageReportGeneratorIntegration:
    """Integration tests for test coverage report generator."""
    
    @pytest.mark.integration
    def test_report_generator_initialization(self):
        """Test report generator initialization."""
        generator = TestCoverageReportGenerator()
        
        assert hasattr(generator, 'report_timestamp')
        assert generator.report_timestamp is not None
    
    @pytest.mark.integration
    def test_markdown_report_generation(self):
        """Test generation of markdown report."""
        # Create a mock analysis
        from forklift.analysis.test_coverage_analyzer import (
            TestCoverageAnalysis, TestCoverageMetrics, TestFailure, TestQualityIssue
        )
        
        mock_analysis = TestCoverageAnalysis(
            overall_coverage=TestCoverageMetrics(
                covered_lines=850,
                total_lines=1000,
                coverage_percentage=85.0,
                missing_lines=[10, 20, 30],
                branch_coverage=80.0,
                missing_branches=50
            ),
            module_coverage={
                "analysis": TestCoverageMetrics(
                    covered_lines=400,
                    total_lines=500,
                    coverage_percentage=80.0,
                    missing_lines=[5, 10],
                    branch_coverage=75.0,
                    missing_branches=25
                )
            },
            test_failures=[
                TestFailure("test1", "file1.py", "Assertion Error", "Test failed", False)
            ],
            test_errors=[
                TestFailure("test2", "file2.py", "Type Error", "Type mismatch", True)
            ],
            quality_issues=[
                TestQualityIssue(
                    issue_type="Test Organization",
                    description="Poor organization",
                    severity="medium",
                    affected_files=["tests/"],
                    recommendation="Improve structure"
                )
            ],
            test_organization_score=75.0,
            test_reliability_score=90.0,
            recommendations=["Improve coverage", "Fix failures"]
        )
        
        generator = TestCoverageReportGenerator()
        report = generator.generate_markdown_report(mock_analysis)
        
        # Verify report structure
        assert isinstance(report, str)
        assert "# Test Coverage and Quality Analysis Report" in report
        assert "## Executive Summary" in report
        assert "## Test Coverage Overview" in report
        assert "## Module Coverage Breakdown" in report
        assert "## Test Failures Analysis" in report
        assert "## Recommendations" in report
        
        # Verify metrics are included
        assert "85.0%" in report  # Coverage percentage
        assert "80.0%" in report  # Branch coverage
        assert "75.0/100" in report  # Organization score
        assert "90.0/100" in report  # Reliability score
    
    @pytest.mark.integration
    def test_report_sections_generation(self):
        """Test individual report section generation."""
        generator = TestCoverageReportGenerator()
        
        # Test header generation
        header = generator._generate_header()
        assert "# Test Coverage and Quality Analysis Report" in header
        assert "Generated:" in header
        assert "Forklift" in header
        
        # Test with minimal analysis data
        from forklift.analysis.test_coverage_analyzer import (
            TestCoverageAnalysis, TestCoverageMetrics
        )
        
        minimal_analysis = TestCoverageAnalysis(
            overall_coverage=TestCoverageMetrics(
                covered_lines=100,
                total_lines=100,
                coverage_percentage=100.0,
                missing_lines=[],
                branch_coverage=100.0,
                missing_branches=0
            ),
            module_coverage={},
            test_failures=[],
            test_errors=[],
            quality_issues=[],
            test_organization_score=100.0,
            test_reliability_score=100.0,
            recommendations=[]
        )
        
        # Test executive summary with perfect scores
        summary = generator._generate_executive_summary(minimal_analysis)
        assert "🟢 **GOOD**" in summary
        assert "100.0%" in summary
        
        # Test coverage overview
        coverage_overview = generator._generate_coverage_overview(minimal_analysis)
        assert "100.0%" in coverage_overview
        assert "🟢" in coverage_overview
    
    @pytest.mark.integration
    def test_report_with_real_analysis_data(self):
        """Test report generation with real analysis data."""
        # Run actual analysis
        analyzer = TestCoverageAnalyzer()
        analysis = analyzer.analyze_test_coverage_and_quality()
        
        # Generate report
        generator = TestCoverageReportGenerator()
        report = generator.generate_markdown_report(analysis)
        
        # Verify report is comprehensive
        assert len(report) > 1000  # Should be a substantial report
        assert "Test Coverage and Quality Analysis Report" in report
        
        # Verify all major sections are present
        required_sections = [
            "Executive Summary",
            "Test Coverage Overview", 
            "Module Coverage Breakdown",
            "Test Failures Analysis",
            "Test Quality Analysis",
            "Test Organization Assessment",
            "Recommendations",
            "Detailed Findings"
        ]
        
        for section in required_sections:
            assert section in report, f"Missing section: {section}"
        
        # Verify metrics are realistic
        assert "%" in report  # Coverage percentages
        assert "/100" in report  # Scores out of 100
        
        # Should contain actual project data
        assert "forklift" in report.lower()
        assert any(module in report for module in ["analysis", "github", "cli"])
    
    @pytest.mark.integration
    def test_report_file_generation(self):
        """Test saving report to file."""
        analyzer = TestCoverageAnalyzer()
        analysis = analyzer.analyze_test_coverage_and_quality()
        
        generator = TestCoverageReportGenerator()
        report = generator.generate_markdown_report(analysis)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(report)
            temp_file = f.name
        
        try:
            # Verify file was created and contains expected content
            temp_path = Path(temp_file)
            assert temp_path.exists()
            
            content = temp_path.read_text()
            assert len(content) > 1000
            assert "Test Coverage and Quality Analysis Report" in content
            
        finally:
            # Clean up
            Path(temp_file).unlink(missing_ok=True)