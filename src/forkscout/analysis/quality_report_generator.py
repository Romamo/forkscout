"""
Code Quality Report Generator

Generates comprehensive reports for code quality analysis and technical debt assessment.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .code_quality_analyzer import (
    CodeQualityAnalyzer,
    IssueType,
    Priority,
)

logger = logging.getLogger(__name__)


class QualityReportGenerator:
    """Generates various formats of code quality reports"""

    def __init__(self, analyzer: CodeQualityAnalyzer):
        self.analyzer = analyzer
        self.timestamp = datetime.now()

    def generate_comprehensive_report(self, output_path: str = "code_quality_report.md") -> str:
        """Generate a comprehensive markdown report"""
        report_lines = []

        # Header
        report_lines.extend([
            "# Code Quality and Technical Debt Analysis Report",
            "",
            f"**Generated:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "**Analyzer Version:** Forkscout Code Quality Analyzer v1.0",
            "",
            "## Executive Summary",
            ""
        ])

        # Executive summary
        metrics = self.analyzer.quality_metrics
        total_issues = sum(metrics.issue_count_by_priority.values())
        critical_issues = metrics.issue_count_by_priority.get(Priority.CRITICAL, 0)
        high_issues = metrics.issue_count_by_priority.get(Priority.HIGH, 0)

        report_lines.extend([
            f"- **Total Files Analyzed:** {metrics.total_files}",
            f"- **Total Lines of Code:** {metrics.total_lines:,}",
            f"- **Average Complexity Score:** {metrics.average_complexity:.2f}",
            f"- **Average Maintainability Index:** {metrics.average_maintainability:.2f}/100",
            f"- **Technical Debt Score:** {metrics.technical_debt_score:.2f}/4.0",
            f"- **Total Issues Found:** {total_issues}",
            f"  - Critical: {critical_issues}",
            f"  - High: {high_issues}",
            f"  - Medium: {metrics.issue_count_by_priority.get(Priority.MEDIUM, 0)}",
            f"  - Low: {metrics.issue_count_by_priority.get(Priority.LOW, 0)}",
            "",
            self._get_health_assessment(),
            "",
            "## Detailed Analysis",
            ""
        ])

        # Quality metrics section
        report_lines.extend(self._generate_metrics_section())

        # Technical debt section
        report_lines.extend(self._generate_technical_debt_section())

        # Issues by type section
        report_lines.extend(self._generate_issues_by_type_section())

        # File-level analysis section
        report_lines.extend(self._generate_file_analysis_section())

        # Recommendations section
        report_lines.extend(self._generate_recommendations_section())

        # Appendix
        report_lines.extend(self._generate_appendix())

        report_content = "\n".join(report_lines)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        logger.info(f"Comprehensive report generated: {output_path}")
        return report_content

    def generate_json_report(self, output_path: str = "code_quality_report.json") -> dict[str, Any]:
        """Generate a JSON report for programmatic consumption"""
        report_data = {
            "metadata": {
                "generated_at": self.timestamp.isoformat(),
                "analyzer_version": "1.0",
                "source_path": str(self.analyzer.source_path)
            },
            "metrics": asdict(self.analyzer.quality_metrics),
            "technical_debt_items": [asdict(item) for item in self.analyzer.technical_debt_items],
            "file_analyses": [
                {
                    "file_path": analysis.file_path,
                    "lines_of_code": analysis.lines_of_code,
                    "complexity_score": analysis.complexity_score,
                    "maintainability_index": analysis.maintainability_index,
                    "issue_count": len(analysis.issues),
                    "function_count": len(analysis.functions),
                    "class_count": len(analysis.classes),
                    "issues": [asdict(issue) for issue in analysis.issues]
                }
                for analysis in self.analyzer.file_analyses
            ]
        }

        # Convert enums to strings for JSON serialization
        report_data = self._convert_enums_to_strings(report_data)

        # Convert enum keys in dictionaries to strings
        if "metrics" in report_data and "issue_count_by_type" in report_data["metrics"]:
            report_data["metrics"]["issue_count_by_type"] = {
                k.value if hasattr(k, "value") else str(k): v
                for k, v in report_data["metrics"]["issue_count_by_type"].items()
            }

        if "metrics" in report_data and "issue_count_by_priority" in report_data["metrics"]:
            report_data["metrics"]["issue_count_by_priority"] = {
                k.value if hasattr(k, "value") else str(k): v
                for k, v in report_data["metrics"]["issue_count_by_priority"].items()
            }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"JSON report generated: {output_path}")
        return report_data

    def generate_summary_report(self) -> str:
        """Generate a brief summary report"""
        metrics = self.analyzer.quality_metrics
        total_issues = sum(metrics.issue_count_by_priority.values())

        summary_lines = [
            "# Code Quality Summary",
            "",
            f"**Files:** {metrics.total_files} | **LOC:** {metrics.total_lines:,} | **Issues:** {total_issues}",
            f"**Maintainability:** {metrics.average_maintainability:.1f}/100 | **Debt Score:** {metrics.technical_debt_score:.1f}/4.0",
            "",
            "## Top Issues:",
        ]

        # Show top 5 technical debt items
        for i, debt_item in enumerate(self.analyzer.technical_debt_items[:5], 1):
            summary_lines.append(
                f"{i}. **{debt_item.title}** ({debt_item.priority.value}) - {len(debt_item.related_issues)} issues"
            )

        return "\n".join(summary_lines)

    def _get_health_assessment(self) -> str:
        """Generate overall health assessment"""
        metrics = self.analyzer.quality_metrics

        if metrics.average_maintainability >= 80 and metrics.technical_debt_score <= 1.5:
            return "**Overall Health:** 🟢 **GOOD** - Code quality is well-maintained with minimal technical debt."
        elif metrics.average_maintainability >= 60 and metrics.technical_debt_score <= 2.5:
            return "**Overall Health:** 🟡 **FAIR** - Code quality is acceptable but has areas for improvement."
        else:
            return "**Overall Health:** 🔴 **NEEDS ATTENTION** - Significant technical debt and quality issues require immediate attention."

    def _generate_metrics_section(self) -> list[str]:
        """Generate the metrics section"""
        metrics = self.analyzer.quality_metrics

        lines = [
            "### Quality Metrics",
            "",
            "| Metric | Value | Assessment |",
            "|--------|-------|------------|",
            f"| Files Analyzed | {metrics.total_files} | - |",
            f"| Total Lines of Code | {metrics.total_lines:,} | {self._assess_codebase_size(metrics.total_lines)} |",
            f"| Average Complexity | {metrics.average_complexity:.2f} | {self._assess_complexity(metrics.average_complexity)} |",
            f"| Average Maintainability | {metrics.average_maintainability:.1f}/100 | {self._assess_maintainability(metrics.average_maintainability)} |",
            f"| Technical Debt Score | {metrics.technical_debt_score:.2f}/4.0 | {self._assess_debt_score(metrics.technical_debt_score)} |",
            "",
        ]

        return lines

    def _generate_technical_debt_section(self) -> list[str]:
        """Generate the technical debt section"""
        lines = [
            "### Technical Debt Items",
            "",
            f"Found {len(self.analyzer.technical_debt_items)} significant technical debt items:",
            "",
        ]

        if not self.analyzer.technical_debt_items:
            lines.append("No significant technical debt items identified.")
            lines.append("")
            return lines

        for i, debt_item in enumerate(self.analyzer.technical_debt_items, 1):
            priority_emoji = {
                Priority.CRITICAL: "🔴",
                Priority.HIGH: "🟠",
                Priority.MEDIUM: "🟡",
                Priority.LOW: "🟢"
            }

            lines.extend([
                f"#### {i}. {debt_item.title} {priority_emoji.get(debt_item.priority, '')}",
                "",
                f"**Priority:** {debt_item.priority.value.title()}",
                f"**Effort Estimate:** {debt_item.effort_estimate.title()}",
                f"**Files Affected:** {len(debt_item.files_affected)}",
                f"**Related Issues:** {len(debt_item.related_issues)}",
                "",
                f"**Description:** {debt_item.description}",
                "",
                f"**Impact:** {debt_item.impact_assessment}",
                "",
                f"**Recommendation:** {debt_item.recommendation}",
                "",
                "**Affected Files:**",
            ])

            lines.extend(f"- `{file_path}`" for file_path in debt_item.files_affected[:10])  # Limit to first 10 files

            if len(debt_item.files_affected) > 10:
                lines.append(f"- ... and {len(debt_item.files_affected) - 10} more files")

            lines.append("")

        return lines

    def _generate_issues_by_type_section(self) -> list[str]:
        """Generate issues by type section"""
        lines = [
            "### Issues by Type",
            "",
            "| Issue Type | Count | Priority Distribution |",
            "|------------|-------|---------------------|",
        ]

        # Group issues by type and priority
        issue_type_priority = {}
        for analysis in self.analyzer.file_analyses:
            for issue in analysis.issues:
                if issue.issue_type not in issue_type_priority:
                    issue_type_priority[issue.issue_type] = dict.fromkeys(Priority, 0)
                issue_type_priority[issue.issue_type][issue.priority] += 1

        for issue_type, priority_counts in sorted(issue_type_priority.items(),
                                                key=lambda x: sum(x[1].values()), reverse=True):
            total_count = sum(priority_counts.values())
            priority_dist = " | ".join([
                f"{p.value[0].upper()}: {count}"
                for p, count in priority_counts.items() if count > 0
            ])

            lines.append(f"| {issue_type.value.replace('_', ' ').title()} | {total_count} | {priority_dist} |")

        lines.append("")
        return lines

    def _generate_file_analysis_section(self) -> list[str]:
        """Generate file-level analysis section"""
        lines = [
            "### File-Level Analysis",
            "",
            "#### Most Complex Files",
            "",
        ]

        # Sort files by complexity
        complex_files = sorted(
            self.analyzer.file_analyses,
            key=lambda x: x.complexity_score,
            reverse=True
        )[:10]

        lines.extend([
            "| File | LOC | Complexity | Maintainability | Issues |",
            "|------|-----|------------|-----------------|--------|",
        ])

        for analysis in complex_files:
            file_name = Path(analysis.file_path).name
            lines.append(
                f"| `{file_name}` | {analysis.lines_of_code} | "
                f"{analysis.complexity_score:.1f} | {analysis.maintainability_index:.1f} | "
                f"{len(analysis.issues)} |"
            )

        lines.extend([
            "",
            "#### Files with Most Issues",
            "",
        ])

        # Sort files by issue count
        problematic_files = sorted(
            self.analyzer.file_analyses,
            key=lambda x: len(x.issues),
            reverse=True
        )[:10]

        lines.extend([
            "| File | Issues | Critical | High | Medium | Low |",
            "|------|--------|----------|------|--------|-----|",
        ])

        for analysis in problematic_files:
            if len(analysis.issues) == 0:
                continue

            file_name = Path(analysis.file_path).name
            priority_counts = dict.fromkeys(Priority, 0)
            for issue in analysis.issues:
                priority_counts[issue.priority] += 1

            lines.append(
                f"| `{file_name}` | {len(analysis.issues)} | "
                f"{priority_counts[Priority.CRITICAL]} | {priority_counts[Priority.HIGH]} | "
                f"{priority_counts[Priority.MEDIUM]} | {priority_counts[Priority.LOW]} |"
            )

        lines.append("")
        return lines

    def _generate_recommendations_section(self) -> list[str]:
        """Generate recommendations section"""
        lines = [
            "### Recommendations",
            "",
            "#### Immediate Actions (High Priority)",
            "",
        ]

        high_priority_items = [
            item for item in self.analyzer.technical_debt_items
            if item.priority in [Priority.CRITICAL, Priority.HIGH]
        ]

        if high_priority_items:
            for i, item in enumerate(high_priority_items[:5], 1):
                lines.extend([
                    f"{i}. **{item.title}**",
                    f"   - {item.recommendation}",
                    f"   - Effort: {item.effort_estimate}, Files: {len(item.files_affected)}",
                    ""
                ])
        else:
            lines.append("No high-priority items identified.")

        lines.extend([
            "",
            "#### Medium-Term Improvements",
            "",
        ])

        medium_priority_items = [
            item for item in self.analyzer.technical_debt_items
            if item.priority == Priority.MEDIUM
        ]

        if medium_priority_items:
            for i, item in enumerate(medium_priority_items[:5], 1):
                lines.extend([
                    f"{i}. **{item.title}**",
                    f"   - {item.recommendation}",
                    ""
                ])
        else:
            lines.append("No medium-priority items identified.")

        lines.extend([
            "",
            "#### General Best Practices",
            "",
            "- Establish code review guidelines focusing on complexity and maintainability",
            "- Implement automated code quality checks in CI/CD pipeline",
            "- Regular refactoring sessions to address technical debt",
            "- Documentation standards for all public APIs",
            "- Performance monitoring and optimization",
            "",
        ])

        return lines

    def _generate_appendix(self) -> list[str]:
        """Generate appendix with methodology and definitions"""
        lines = [
            "## Appendix",
            "",
            "### Methodology",
            "",
            "This analysis was performed using static code analysis techniques including:",
            "",
            "- **AST Analysis:** Python Abstract Syntax Tree parsing for structural analysis",
            "- **Pattern Matching:** Regular expression matching for code patterns and comments",
            "- **Complexity Calculation:** Cyclomatic complexity measurement",
            "- **Maintainability Index:** Composite score based on LOC, complexity, and issues",
            "",
            "### Definitions",
            "",
            "- **Cyclomatic Complexity:** Measure of code complexity based on decision points",
            "- **Maintainability Index:** Score from 0-100 indicating how maintainable code is",
            "- **Technical Debt Score:** Weighted average of issue priorities (0-4 scale)",
            "- **LOC:** Lines of Code (excluding blank lines and comments)",
            "",
            "### Issue Types",
            "",
        ]

        issue_descriptions = {
            IssueType.TODO_COMMENT: "TODO, FIXME, HACK, or similar comments indicating incomplete work",
            IssueType.DEPRECATED_CODE: "Code marked as deprecated or using deprecated APIs",
            IssueType.LONG_FUNCTION: "Functions exceeding recommended length (>50 lines)",
            IssueType.COMPLEX_FUNCTION: "Functions with high cyclomatic complexity (>10)",
            IssueType.LARGE_CLASS: "Classes exceeding recommended size (>300 lines)",
            IssueType.MISSING_DOCSTRING: "Public functions/classes without documentation",
            IssueType.MAGIC_NUMBER: "Hardcoded numbers that should be named constants",
            IssueType.LONG_PARAMETER_LIST: "Functions with too many parameters (>6)",
            IssueType.POOR_ERROR_HANDLING: "Inadequate or missing error handling"
        }

        for issue_type, description in issue_descriptions.items():
            lines.append(f"- **{issue_type.value.replace('_', ' ').title()}:** {description}")

        lines.append("")
        return lines

    def _assess_codebase_size(self, lines: int) -> str:
        """Assess codebase size"""
        if lines < 10000:
            return "Small codebase"
        elif lines < 50000:
            return "Medium codebase"
        else:
            return "Large codebase"

    def _assess_complexity(self, complexity: float) -> str:
        """Assess complexity score"""
        if complexity <= 5:
            return "Low complexity"
        elif complexity <= 10:
            return "Moderate complexity"
        else:
            return "High complexity"

    def _assess_maintainability(self, maintainability: float) -> str:
        """Assess maintainability score"""
        if maintainability >= 80:
            return "Excellent"
        elif maintainability >= 60:
            return "Good"
        elif maintainability >= 40:
            return "Fair"
        else:
            return "Poor"

    def _assess_debt_score(self, debt_score: float) -> str:
        """Assess technical debt score"""
        if debt_score <= 1.5:
            return "Low debt"
        elif debt_score <= 2.5:
            return "Moderate debt"
        else:
            return "High debt"

    def _convert_enums_to_strings(self, obj):
        """Convert enum values to strings for JSON serialization"""
        if isinstance(obj, dict):
            return {key: self._convert_enums_to_strings(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_enums_to_strings(item) for item in obj]
        elif hasattr(obj, "value"):  # Enum
            return obj.value
        else:
            return obj
