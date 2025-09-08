"""
Test Coverage Report Generator

Generates comprehensive reports on test coverage and quality analysis.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List
import logging

from .test_coverage_analyzer import TestCoverageAnalysis, TestCoverageMetrics, TestFailure, TestQualityIssue

logger = logging.getLogger(__name__)


class TestCoverageReportGenerator:
    """Generates comprehensive test coverage and quality reports."""
    
    def __init__(self):
        self.report_timestamp = datetime.now()
    
    def generate_markdown_report(self, analysis: TestCoverageAnalysis) -> str:
        """Generate a comprehensive markdown report of test coverage and quality."""
        
        report_sections = [
            self._generate_header(),
            self._generate_executive_summary(analysis),
            self._generate_coverage_overview(analysis),
            self._generate_module_coverage_details(analysis),
            self._generate_test_failures_analysis(analysis),
            self._generate_quality_issues_analysis(analysis),
            self._generate_test_organization_assessment(analysis),
            self._generate_recommendations(analysis),
            self._generate_detailed_findings(analysis)
        ]
        
        return "\n\n".join(report_sections)
    
    def _generate_header(self) -> str:
        """Generate report header."""
        return f"""# Test Coverage and Quality Analysis Report

**Generated:** {self.report_timestamp.strftime('%Y-%m-%d %H:%M:%S')}  
**Project:** Forklift - GitHub Repository Fork Analysis Tool  
**Analysis Type:** Comprehensive Test Coverage and Quality Assessment"""
    
    def _generate_executive_summary(self, analysis: TestCoverageAnalysis) -> str:
        """Generate executive summary."""
        total_failures = len(analysis.test_failures) + len(analysis.test_errors)
        critical_issues = len([i for i in analysis.quality_issues if i.severity in ["critical", "high"]])
        
        # Determine overall health status
        if analysis.overall_coverage.coverage_percentage >= 90 and total_failures < 50:
            health_status = "🟢 **GOOD**"
        elif analysis.overall_coverage.coverage_percentage >= 80 and total_failures < 100:
            health_status = "🟡 **NEEDS ATTENTION**"
        else:
            health_status = "🔴 **CRITICAL**"
        
        return f"""## Executive Summary

### Overall Test Health: {health_status}

**Key Metrics:**
- **Test Coverage:** {analysis.overall_coverage.coverage_percentage:.1f}% line coverage, {analysis.overall_coverage.branch_coverage:.1f}% branch coverage
- **Test Reliability:** {analysis.test_reliability_score:.1f}/100 (based on failure rates and flakiness)
- **Test Organization:** {analysis.test_organization_score:.1f}/100 (structure and maintainability)
- **Total Test Issues:** {total_failures} failures/errors, {critical_issues} critical quality issues

### Summary Assessment

The Forklift project has **{len(analysis.test_failures + analysis.test_errors)} test failures/errors** out of approximately 3,000+ tests, indicating significant testing challenges that need immediate attention. While the project has extensive test coverage with **{analysis.overall_coverage.coverage_percentage:.1f}% line coverage**, the high failure rate suggests issues with test reliability, mock usage, and potentially flaky tests.

**Immediate Actions Required:**
1. Fix critical test failures blocking CI/CD pipeline
2. Address mock-related errors and async test issues  
3. Improve test data management and reduce hardcoded values
4. Stabilize flaky tests affecting reliability"""
    
    def _generate_coverage_overview(self, analysis: TestCoverageAnalysis) -> str:
        """Generate coverage overview section."""
        coverage = analysis.overall_coverage
        
        # Coverage status indicators
        line_status = "🟢" if coverage.coverage_percentage >= 90 else "🟡" if coverage.coverage_percentage >= 80 else "🔴"
        branch_status = "🟢" if coverage.branch_coverage >= 85 else "🟡" if coverage.branch_coverage >= 75 else "🔴"
        
        return f"""## Test Coverage Overview

### Coverage Metrics

| Metric | Value | Status | Target |
|--------|-------|--------|---------|
| **Line Coverage** | {coverage.coverage_percentage:.1f}% | {line_status} | ≥90% |
| **Branch Coverage** | {coverage.branch_coverage:.1f}% | {branch_status} | ≥85% |
| **Lines Covered** | {coverage.covered_lines:,} / {coverage.total_lines:,} | - | - |
| **Missing Branches** | {coverage.missing_branches:,} | - | <100 |

### Coverage Analysis

The project achieves **{coverage.coverage_percentage:.1f}% line coverage** across {coverage.total_lines:,} lines of code, which {'meets' if coverage.coverage_percentage >= 85 else 'falls short of'} industry standards for critical applications. Branch coverage at **{coverage.branch_coverage:.1f}%** {'is adequate' if coverage.branch_coverage >= 80 else 'needs improvement'} for ensuring all code paths are tested.

**Coverage Gaps:**
- {len(coverage.missing_lines):,} lines lack test coverage
- {coverage.missing_branches:,} branches remain untested
- Focus needed on error handling and edge case scenarios"""
    
    def _generate_module_coverage_details(self, analysis: TestCoverageAnalysis) -> str:
        """Generate detailed module coverage breakdown."""
        sections = ["## Module Coverage Breakdown\n"]
        
        # Sort modules by coverage percentage
        sorted_modules = sorted(
            analysis.module_coverage.items(),
            key=lambda x: x[1].coverage_percentage,
            reverse=True
        )
        
        sections.append("| Module | Line Coverage | Branch Coverage | Lines | Status |")
        sections.append("|--------|---------------|-----------------|-------|--------|")
        
        for module_name, metrics in sorted_modules:
            status = "🟢" if metrics.coverage_percentage >= 90 else "🟡" if metrics.coverage_percentage >= 80 else "🔴"
            sections.append(
                f"| **{module_name}** | {metrics.coverage_percentage:.1f}% | "
                f"{metrics.branch_coverage:.1f}% | {metrics.covered_lines}/{metrics.total_lines} | {status} |"
            )
        
        # Identify modules needing attention
        low_coverage_modules = [
            name for name, metrics in analysis.module_coverage.items()
            if metrics.coverage_percentage < 80
        ]
        
        if low_coverage_modules:
            sections.append(f"\n### Modules Requiring Attention\n")
            sections.append(f"The following modules have coverage below 80% and should be prioritized:\n")
            for module in low_coverage_modules[:5]:  # Top 5 worst
                metrics = analysis.module_coverage[module]
                sections.append(f"- **{module}**: {metrics.coverage_percentage:.1f}% coverage ({metrics.total_lines - metrics.covered_lines} uncovered lines)")
        
        return "\n".join(sections)
    
    def _generate_test_failures_analysis(self, analysis: TestCoverageAnalysis) -> str:
        """Generate test failures analysis section."""
        failures = analysis.test_failures
        errors = analysis.test_errors
        total_issues = len(failures) + len(errors)
        
        if total_issues == 0:
            return """## Test Failures Analysis

### ✅ No Test Failures

All tests are currently passing. Excellent test reliability!"""
        
        # Categorize failures by type
        failure_types = {}
        for failure in failures + errors:
            failure_types[failure.error_type] = failure_types.get(failure.error_type, 0) + 1
        
        # Identify flaky tests
        flaky_tests = [f for f in failures + errors if f.is_flaky]
        
        sections = [f"## Test Failures Analysis\n"]
        sections.append(f"### Overview\n")
        sections.append(f"- **Total Issues:** {total_issues} ({len(failures)} failures, {len(errors)} errors)")
        sections.append(f"- **Potentially Flaky Tests:** {len(flaky_tests)}")
        sections.append(f"- **Success Rate:** {((3000 - total_issues) / 3000 * 100):.1f}% (estimated)\n")
        
        sections.append("### Failure Types Breakdown\n")
        sections.append("| Error Type | Count | Percentage |")
        sections.append("|------------|-------|------------|")
        
        for error_type, count in sorted(failure_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_issues) * 100
            sections.append(f"| {error_type} | {count} | {percentage:.1f}% |")
        
        # Most common failures
        if failure_types:
            most_common = max(failure_types.items(), key=lambda x: x[1])
            sections.append(f"\n### Most Common Issue: {most_common[0]}\n")
            sections.append(f"**{most_common[1]} occurrences** - This represents {(most_common[1]/total_issues*100):.1f}% of all test issues.")
            
            # Provide specific recommendations based on most common error
            if "Mock Error" in most_common[0]:
                sections.append("\n**Recommendation:** Review mock usage patterns, ensure proper async mock handling, and validate mock configurations.")
            elif "Assertion Error" in most_common[0]:
                sections.append("\n**Recommendation:** Review test expectations and ensure they align with actual implementation behavior.")
            elif "Type Error" in most_common[0]:
                sections.append("\n**Recommendation:** Add type checking and validation, review function signatures and parameter passing.")
        
        # Flaky tests section
        if flaky_tests:
            sections.append(f"\n### Potentially Flaky Tests ({len(flaky_tests)} identified)\n")
            sections.append("These tests may fail intermittently due to timing, async operations, or external dependencies:\n")
            
            for flaky in flaky_tests[:10]:  # Show first 10
                sections.append(f"- `{flaky.test_file}::{flaky.test_name}` - {flaky.error_type}")
        
        return "\n".join(sections)
    
    def _generate_quality_issues_analysis(self, analysis: TestCoverageAnalysis) -> str:
        """Generate test quality issues analysis."""
        issues = analysis.quality_issues
        
        if not issues:
            return """## Test Quality Analysis

### ✅ No Major Quality Issues Detected

Test organization and structure appear to be well-maintained."""
        
        # Group issues by severity
        critical_issues = [i for i in issues if i.severity == "critical"]
        high_issues = [i for i in issues if i.severity == "high"]
        medium_issues = [i for i in issues if i.severity == "medium"]
        low_issues = [i for i in issues if i.severity == "low"]
        
        sections = ["## Test Quality Analysis\n"]
        sections.append(f"### Quality Issues Summary\n")
        sections.append(f"- **Critical:** {len(critical_issues)} issues")
        sections.append(f"- **High:** {len(high_issues)} issues")
        sections.append(f"- **Medium:** {len(medium_issues)} issues")
        sections.append(f"- **Low:** {len(low_issues)} issues\n")
        
        # Detail each severity level
        for severity, issue_list in [
            ("Critical", critical_issues),
            ("High Priority", high_issues),
            ("Medium Priority", medium_issues),
            ("Low Priority", low_issues)
        ]:
            if issue_list:
                sections.append(f"### {severity} Issues\n")
                for issue in issue_list:
                    sections.append(f"**{issue.issue_type}**")
                    sections.append(f"- *Description:* {issue.description}")
                    sections.append(f"- *Affected Files:* {len(issue.affected_files)} files")
                    sections.append(f"- *Recommendation:* {issue.recommendation}\n")
        
        return "\n".join(sections)
    
    def _generate_test_organization_assessment(self, analysis: TestCoverageAnalysis) -> str:
        """Generate test organization assessment."""
        score = analysis.test_organization_score
        
        # Determine organization status
        if score >= 90:
            status = "🟢 Excellent"
        elif score >= 75:
            status = "🟡 Good"
        elif score >= 60:
            status = "🟠 Needs Improvement"
        else:
            status = "🔴 Poor"
        
        return f"""## Test Organization Assessment

### Organization Score: {score:.1f}/100 ({status})

### Test Structure Analysis

The project demonstrates {'strong' if score >= 80 else 'adequate' if score >= 60 else 'weak'} test organization with the following structure:

```
tests/
├── unit/           # ✅ Unit tests (isolated component testing)
├── integration/    # ✅ Integration tests (component interaction)
├── e2e/           # ✅ End-to-end tests (full workflow testing)
├── contract/      # ✅ Contract tests (API schema validation)
├── performance/   # ✅ Performance tests (load and timing)
├── utils/         # ✅ Test utilities and helpers
└── fixtures/      # {'✅' if score >= 80 else '❌'} Test data and fixtures
```

### Organization Strengths
- Comprehensive test categorization (unit, integration, e2e, contract, performance)
- Clear separation of test types
- Dedicated utilities and helper functions
- {len([f for f in Path('tests').rglob('test_*.py')])} total test files organized across categories

### Areas for Improvement
{'- Test structure mirrors source code organization well' if score >= 80 else '- Test directory structure should better mirror source code structure'}
{'- Good use of fixtures and test data management' if score >= 70 else '- Improve test data management with centralized fixtures'}
{'- Test utilities are well organized' if score >= 75 else '- Consider consolidating test utilities and helpers'}"""
    
    def _generate_recommendations(self, analysis: TestCoverageAnalysis) -> str:
        """Generate recommendations section."""
        sections = ["## Recommendations\n"]
        
        # Priority-based recommendations
        sections.append("### Immediate Actions (High Priority)\n")
        
        high_priority_recs = []
        
        # Coverage-based recommendations
        if analysis.overall_coverage.coverage_percentage < 85:
            high_priority_recs.append(
                f"**Increase Test Coverage**: Current {analysis.overall_coverage.coverage_percentage:.1f}% is below recommended 85%. Focus on untested modules and error handling paths."
            )
        
        # Failure-based recommendations
        total_failures = len(analysis.test_failures) + len(analysis.test_errors)
        if total_failures > 100:
            high_priority_recs.append(
                f"**Fix Critical Test Failures**: {total_failures} failing tests indicate serious issues. Prioritize mock errors and assertion failures."
            )
        
        # Quality-based recommendations
        critical_quality_issues = len([i for i in analysis.quality_issues if i.severity in ["critical", "high"]])
        if critical_quality_issues > 0:
            high_priority_recs.append(
                f"**Address Quality Issues**: {critical_quality_issues} high-priority test quality issues need immediate attention."
            )
        
        for i, rec in enumerate(high_priority_recs, 1):
            sections.append(f"{i}. {rec}\n")
        
        # Medium priority recommendations
        sections.append("### Medium Priority Improvements\n")
        
        medium_recs = []
        
        if analysis.overall_coverage.branch_coverage < 85:
            medium_recs.append(
                f"**Improve Branch Coverage**: Current {analysis.overall_coverage.branch_coverage:.1f}% branch coverage should reach 85%+ for comprehensive testing."
            )
        
        flaky_tests = len([f for f in analysis.test_failures + analysis.test_errors if f.is_flaky])
        if flaky_tests > 0:
            medium_recs.append(
                f"**Stabilize Flaky Tests**: {flaky_tests} potentially flaky tests affect reliability. Add proper timeouts and async handling."
            )
        
        if analysis.test_organization_score < 80:
            medium_recs.append(
                "**Improve Test Organization**: Enhance test structure to better mirror source code organization and improve maintainability."
            )
        
        for i, rec in enumerate(medium_recs, 1):
            sections.append(f"{i}. {rec}\n")
        
        # Long-term recommendations
        sections.append("### Long-term Improvements\n")
        
        long_term_recs = [
            "**Implement Continuous Test Quality Monitoring**: Set up automated test quality metrics tracking",
            "**Enhance Test Data Management**: Create comprehensive fixture system for better test data management",
            "**Add Performance Test Benchmarks**: Establish performance baselines and regression testing",
            "**Improve Test Documentation**: Document test strategies and patterns for team consistency"
        ]
        
        for i, rec in enumerate(long_term_recs, 1):
            sections.append(f"{i}. {rec}\n")
        
        return "\n".join(sections)
    
    def _generate_detailed_findings(self, analysis: TestCoverageAnalysis) -> str:
        """Generate detailed findings section."""
        sections = ["## Detailed Findings\n"]
        
        # Test execution summary
        total_issues = len(analysis.test_failures) + len(analysis.test_errors)
        sections.append(f"### Test Execution Summary\n")
        sections.append(f"- **Total Tests Executed**: ~3,000+ tests")
        sections.append(f"- **Passed**: ~{3000 - total_issues:,} tests")
        sections.append(f"- **Failed**: {len(analysis.test_failures)} tests")
        sections.append(f"- **Errors**: {len(analysis.test_errors)} tests")
        sections.append(f"- **Success Rate**: {((3000 - total_issues) / 3000 * 100):.1f}%\n")
        
        # Coverage details
        sections.append("### Coverage Details\n")
        sections.append(f"- **Total Lines of Code**: {analysis.overall_coverage.total_lines:,}")
        sections.append(f"- **Covered Lines**: {analysis.overall_coverage.covered_lines:,}")
        sections.append(f"- **Uncovered Lines**: {analysis.overall_coverage.total_lines - analysis.overall_coverage.covered_lines:,}")
        sections.append(f"- **Missing Branches**: {analysis.overall_coverage.missing_branches:,}\n")
        
        # Test categories breakdown
        test_categories = {
            "Unit Tests": "tests/unit/",
            "Integration Tests": "tests/integration/", 
            "End-to-End Tests": "tests/e2e/",
            "Contract Tests": "tests/contract/",
            "Performance Tests": "tests/performance/"
        }
        
        sections.append("### Test Categories Analysis\n")
        for category, path in test_categories.items():
            test_files = list(Path(path).glob("test_*.py")) if Path(path).exists() else []
            sections.append(f"- **{category}**: {len(test_files)} test files")
        
        # Common failure patterns
        if analysis.test_failures or analysis.test_errors:
            sections.append("\n### Common Failure Patterns\n")
            
            # Mock-related failures
            mock_failures = [f for f in analysis.test_failures + analysis.test_errors if "mock" in f.error_message.lower()]
            if mock_failures:
                sections.append(f"- **Mock Issues**: {len(mock_failures)} tests failing due to mock configuration or async mock handling")
            
            # Assertion failures
            assertion_failures = [f for f in analysis.test_failures + analysis.test_errors if f.error_type == "Assertion Error"]
            if assertion_failures:
                sections.append(f"- **Assertion Failures**: {len(assertion_failures)} tests with expectation mismatches")
            
            # Type errors
            type_errors = [f for f in analysis.test_failures + analysis.test_errors if f.error_type == "Type Error"]
            if type_errors:
                sections.append(f"- **Type Errors**: {len(type_errors)} tests with type-related issues")
        
        return "\n".join(sections)