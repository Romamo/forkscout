"""
Code Quality and Technical Debt Analysis Engine

This module provides comprehensive analysis of code quality, technical debt,
and maintainability issues across the Forkscout codebase.
"""

import ast
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class IssueType(Enum):
    """Types of code quality issues"""
    TODO_COMMENT = "todo_comment"
    DEPRECATED_CODE = "deprecated_code"
    LONG_FUNCTION = "long_function"
    COMPLEX_FUNCTION = "complex_function"
    LARGE_CLASS = "large_class"
    DUPLICATE_CODE = "duplicate_code"
    MISSING_DOCSTRING = "missing_docstring"
    POOR_ERROR_HANDLING = "poor_error_handling"
    MAGIC_NUMBER = "magic_number"
    LONG_PARAMETER_LIST = "long_parameter_list"
    DEEP_NESTING = "deep_nesting"
    UNUSED_IMPORT = "unused_import"
    INCONSISTENT_NAMING = "inconsistent_naming"
    PERFORMANCE_ISSUE = "performance_issue"


class Priority(Enum):
    """Priority levels for technical debt items"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CodeIssue:
    """Represents a code quality issue"""
    issue_type: IssueType
    priority: Priority
    file_path: str
    line_number: int
    description: str
    suggestion: str
    context: str | None = None
    effort_estimate: str = "small"  # small, medium, large


@dataclass
class FileAnalysis:
    """Analysis results for a single file"""
    file_path: str
    lines_of_code: int
    complexity_score: float
    maintainability_index: float
    issues: list[CodeIssue] = field(default_factory=list)
    functions: list[dict[str, Any]] = field(default_factory=list)
    classes: list[dict[str, Any]] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


@dataclass
class QualityMetrics:
    """Overall code quality metrics"""
    total_files: int
    total_lines: int
    average_complexity: float
    average_maintainability: float
    issue_count_by_type: dict[IssueType, int] = field(default_factory=dict)
    issue_count_by_priority: dict[Priority, int] = field(default_factory=dict)
    technical_debt_score: float = 0.0


@dataclass
class TechnicalDebtItem:
    """Represents a technical debt item with prioritization"""
    title: str
    description: str
    priority: Priority
    effort_estimate: str
    impact_assessment: str
    files_affected: list[str]
    related_issues: list[CodeIssue]
    recommendation: str


class CodeQualityAnalyzer:
    """Analyzes code quality and identifies technical debt"""

    def __init__(self, source_path: str = "src"):
        self.source_path = Path(source_path)
        self.file_analyses: list[FileAnalysis] = []
        self.quality_metrics = QualityMetrics(0, 0, 0.0, 0.0)
        self.technical_debt_items: list[TechnicalDebtItem] = []

        # Configuration thresholds
        self.max_function_length = 50
        self.max_class_length = 300
        self.max_complexity = 10
        self.max_parameters = 6
        self.max_nesting_depth = 4

        # Patterns for analysis
        self.todo_patterns = [
            r"#\s*TODO[:\s]*(.*)",
            r"#\s*FIXME[:\s]*(.*)",
            r"#\s*HACK[:\s]*(.*)",
            r"#\s*XXX[:\s]*(.*)",
            r"#\s*BUG[:\s]*(.*)",
        ]

        self.deprecated_patterns = [
            r"@deprecated",
            r"# deprecated",
            r"# DEPRECATED",
            r"warnings\.warn.*deprecated",
        ]

        self.magic_number_pattern = r"\b\d+\b"

    def analyze_codebase(self) -> QualityMetrics:
        """Perform comprehensive code quality analysis"""
        logger.info("Starting code quality analysis")

        python_files = list(self.source_path.rglob("*.py"))
        logger.info(f"Found {len(python_files)} Python files to analyze")

        for file_path in python_files:
            try:
                analysis = self._analyze_file(file_path)
                self.file_analyses.append(analysis)
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")

        self._calculate_metrics()
        self._identify_technical_debt()

        logger.info("Code quality analysis completed")
        return self.quality_metrics

    def _analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a single Python file"""
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return FileAnalysis(
                file_path=str(file_path),
                lines_of_code=len(content.splitlines()),
                complexity_score=0.0,
                maintainability_index=0.0,
                issues=[CodeIssue(
                    IssueType.DEPRECATED_CODE,
                    Priority.HIGH,
                    str(file_path),
                    e.lineno or 0,
                    f"Syntax error: {e.msg}",
                    "Fix syntax error"
                )]
            )

        analysis = FileAnalysis(
            file_path=str(file_path),
            lines_of_code=len([line for line in content.splitlines() if line.strip()]),
            complexity_score=0.0,
            maintainability_index=0.0
        )

        # Analyze AST
        visitor = CodeAnalysisVisitor(file_path, content)
        visitor.visit(tree)

        analysis.functions = visitor.functions
        analysis.classes = visitor.classes
        analysis.imports = visitor.imports
        analysis.complexity_score = visitor.total_complexity
        analysis.issues.extend(visitor.issues)

        # Text-based analysis
        self._analyze_text_patterns(file_path, content, analysis)

        # Calculate maintainability index
        analysis.maintainability_index = self._calculate_maintainability_index(analysis)

        return analysis

    def _analyze_text_patterns(self, file_path: Path, content: str, analysis: FileAnalysis):
        """Analyze text patterns for issues"""
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            # Check for TODO comments
            for pattern in self.todo_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    todo_text = match.group(1) if match.groups() else "No description"
                    analysis.issues.append(CodeIssue(
                        IssueType.TODO_COMMENT,
                        Priority.MEDIUM,
                        str(file_path),
                        line_num,
                        f"TODO comment: {todo_text}",
                        "Address TODO item or remove comment",
                        context=line.strip()
                    ))

            # Check for deprecated code
            for pattern in self.deprecated_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    analysis.issues.append(CodeIssue(
                        IssueType.DEPRECATED_CODE,
                        Priority.HIGH,
                        str(file_path),
                        line_num,
                        "Deprecated code found",
                        "Update to use current API or remove deprecated code",
                        context=line.strip()
                    ))

            # Check for magic numbers (excluding common ones)
            magic_numbers = re.findall(self.magic_number_pattern, line)
            for number in magic_numbers:
                if number not in ["0", "1", "2", "10", "100", "1000"] and len(number) > 1:
                    analysis.issues.append(CodeIssue(
                        IssueType.MAGIC_NUMBER,
                        Priority.LOW,
                        str(file_path),
                        line_num,
                        f"Magic number: {number}",
                        "Replace with named constant",
                        context=line.strip()
                    ))

    def _calculate_maintainability_index(self, analysis: FileAnalysis) -> float:
        """Calculate maintainability index for a file"""
        # Simplified maintainability index calculation
        # Based on lines of code, complexity, and issue count

        loc_factor = max(0, 100 - (analysis.lines_of_code / 10))
        complexity_factor = max(0, 100 - (analysis.complexity_score * 5))
        issue_factor = max(0, 100 - (len(analysis.issues) * 2))

        return (loc_factor + complexity_factor + issue_factor) / 3

    def _calculate_metrics(self):
        """Calculate overall quality metrics"""
        if not self.file_analyses:
            return

        self.quality_metrics.total_files = len(self.file_analyses)
        self.quality_metrics.total_lines = sum(f.lines_of_code for f in self.file_analyses)
        self.quality_metrics.average_complexity = sum(f.complexity_score for f in self.file_analyses) / len(self.file_analyses)
        self.quality_metrics.average_maintainability = sum(f.maintainability_index for f in self.file_analyses) / len(self.file_analyses)

        # Count issues by type and priority
        issue_type_counts = defaultdict(int)
        priority_counts = defaultdict(int)

        for analysis in self.file_analyses:
            for issue in analysis.issues:
                issue_type_counts[issue.issue_type] += 1
                priority_counts[issue.priority] += 1

        self.quality_metrics.issue_count_by_type = dict(issue_type_counts)
        self.quality_metrics.issue_count_by_priority = dict(priority_counts)

        # Calculate technical debt score
        total_issues = sum(priority_counts.values())
        critical_weight = priority_counts.get(Priority.CRITICAL, 0) * 4
        high_weight = priority_counts.get(Priority.HIGH, 0) * 3
        medium_weight = priority_counts.get(Priority.MEDIUM, 0) * 2
        low_weight = priority_counts.get(Priority.LOW, 0) * 1

        if total_issues > 0:
            self.quality_metrics.technical_debt_score = (
                (critical_weight + high_weight + medium_weight + low_weight) / total_issues
            )

    def _identify_technical_debt(self):
        """Identify and prioritize technical debt items"""
        # Group issues by type and location to identify patterns
        issue_groups = defaultdict(list)

        for analysis in self.file_analyses:
            for issue in analysis.issues:
                key = f"{issue.issue_type.value}_{Path(issue.file_path).parent}"
                issue_groups[key].append(issue)

        # Create technical debt items for significant issue clusters
        for issues in issue_groups.values():
            if len(issues) >= 3:  # Only create debt items for recurring issues
                issue_type = issues[0].issue_type
                files_affected = list({issue.file_path for issue in issues})

                debt_item = TechnicalDebtItem(
                    title=f"Multiple {issue_type.value.replace('_', ' ').title()} Issues",
                    description=f"Found {len(issues)} instances of {issue_type.value} across {len(files_affected)} files",
                    priority=self._determine_debt_priority(issues),
                    effort_estimate=self._estimate_effort(issues),
                    impact_assessment=self._assess_impact(issues),
                    files_affected=files_affected,
                    related_issues=issues,
                    recommendation=self._generate_recommendation(issue_type, issues)
                )

                self.technical_debt_items.append(debt_item)

        # Sort by priority and impact
        self.technical_debt_items.sort(
            key=lambda x: (x.priority.value, -len(x.related_issues))
        )

    def _determine_debt_priority(self, issues: list[CodeIssue]) -> Priority:
        """Determine priority for a technical debt item"""
        priorities = [issue.priority for issue in issues]
        priority_counts = Counter(priorities)

        if priority_counts[Priority.CRITICAL] > 0:
            return Priority.CRITICAL
        elif priority_counts[Priority.HIGH] >= len(issues) * 0.5:
            return Priority.HIGH
        elif priority_counts[Priority.MEDIUM] >= len(issues) * 0.3:
            return Priority.MEDIUM
        else:
            return Priority.LOW

    def _estimate_effort(self, issues: list[CodeIssue]) -> str:
        """Estimate effort required to address issues"""
        if len(issues) > 20:
            return "large"
        elif len(issues) > 10:
            return "medium"
        else:
            return "small"

    def _assess_impact(self, issues: list[CodeIssue]) -> str:
        """Assess impact of addressing the technical debt"""
        issue_type = issues[0].issue_type

        high_impact_types = {
            IssueType.DEPRECATED_CODE,
            IssueType.POOR_ERROR_HANDLING,
            IssueType.PERFORMANCE_ISSUE
        }

        medium_impact_types = {
            IssueType.COMPLEX_FUNCTION,
            IssueType.LONG_FUNCTION,
            IssueType.MISSING_DOCSTRING
        }

        if issue_type in high_impact_types:
            return "High - Affects reliability and maintainability"
        elif issue_type in medium_impact_types:
            return "Medium - Affects code readability and maintainability"
        else:
            return "Low - Minor improvement to code quality"

    def _generate_recommendation(self, issue_type: IssueType, issues: list[CodeIssue]) -> str:
        """Generate recommendation for addressing technical debt"""
        recommendations = {
            IssueType.TODO_COMMENT: "Review and address all TODO comments. Create tickets for legitimate work items and remove outdated comments.",
            IssueType.DEPRECATED_CODE: "Update deprecated code to use current APIs. This is critical for future compatibility.",
            IssueType.LONG_FUNCTION: "Break down long functions into smaller, focused functions with single responsibilities.",
            IssueType.COMPLEX_FUNCTION: "Reduce cyclomatic complexity by extracting helper functions and simplifying logic.",
            IssueType.MISSING_DOCSTRING: "Add comprehensive docstrings to improve code documentation and maintainability.",
            IssueType.MAGIC_NUMBER: "Replace magic numbers with named constants to improve code readability.",
            IssueType.POOR_ERROR_HANDLING: "Implement proper error handling with specific exception types and meaningful error messages."
        }

        base_recommendation = recommendations.get(
            issue_type,
            f"Address {issue_type.value.replace('_', ' ')} issues to improve code quality"
        )

        return f"{base_recommendation} Affects {len({issue.file_path for issue in issues})} files."


class CodeAnalysisVisitor(ast.NodeVisitor):
    """AST visitor for analyzing Python code structure"""

    def __init__(self, file_path: Path, content: str):
        self.file_path = file_path
        self.content = content
        self.lines = content.splitlines()
        self.functions = []
        self.classes = []
        self.imports = []
        self.issues = []
        self.total_complexity = 0
        self.current_class = None
        self.nesting_depth = 0

    def visit_FunctionDef(self, node):
        """Analyze function definitions"""
        func_info = {
            "name": node.name,
            "line_number": node.lineno,
            "parameters": len(node.args.args),
            "lines": self._count_function_lines(node),
            "complexity": self._calculate_complexity(node),
            "has_docstring": ast.get_docstring(node) is not None
        }

        self.functions.append(func_info)
        self.total_complexity += func_info["complexity"]

        # Check for issues
        if func_info["lines"] > 50:
            self.issues.append(CodeIssue(
                IssueType.LONG_FUNCTION,
                Priority.MEDIUM,
                str(self.file_path),
                node.lineno,
                f"Function '{node.name}' is {func_info['lines']} lines long",
                "Break down into smaller functions"
            ))

        if func_info["complexity"] > 10:
            self.issues.append(CodeIssue(
                IssueType.COMPLEX_FUNCTION,
                Priority.HIGH,
                str(self.file_path),
                node.lineno,
                f"Function '{node.name}' has complexity {func_info['complexity']}",
                "Reduce cyclomatic complexity"
            ))

        if func_info["parameters"] > 6:
            self.issues.append(CodeIssue(
                IssueType.LONG_PARAMETER_LIST,
                Priority.MEDIUM,
                str(self.file_path),
                node.lineno,
                f"Function '{node.name}' has {func_info['parameters']} parameters",
                "Consider using parameter objects or reducing parameters"
            ))

        if not func_info["has_docstring"] and not node.name.startswith("_"):
            self.issues.append(CodeIssue(
                IssueType.MISSING_DOCSTRING,
                Priority.LOW,
                str(self.file_path),
                node.lineno,
                f"Function '{node.name}' missing docstring",
                "Add docstring to document function purpose and parameters"
            ))

        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Analyze class definitions"""
        class_lines = self._count_class_lines(node)

        class_info = {
            "name": node.name,
            "line_number": node.lineno,
            "lines": class_lines,
            "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)]),
            "has_docstring": ast.get_docstring(node) is not None
        }

        self.classes.append(class_info)

        # Check for issues
        if class_lines > 300:
            self.issues.append(CodeIssue(
                IssueType.LARGE_CLASS,
                Priority.MEDIUM,
                str(self.file_path),
                node.lineno,
                f"Class '{node.name}' is {class_lines} lines long",
                "Consider breaking into smaller classes"
            ))

        if not class_info["has_docstring"]:
            self.issues.append(CodeIssue(
                IssueType.MISSING_DOCSTRING,
                Priority.LOW,
                str(self.file_path),
                node.lineno,
                f"Class '{node.name}' missing docstring",
                "Add docstring to document class purpose"
            ))

        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

    def visit_Import(self, node):
        """Track imports"""
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Track from imports"""
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")
        self.generic_visit(node)

    def _count_function_lines(self, node):
        """Count lines in a function"""
        if hasattr(node, "end_lineno") and node.end_lineno:
            return node.end_lineno - node.lineno + 1
        return 1

    def _count_class_lines(self, node):
        """Count lines in a class"""
        if hasattr(node, "end_lineno") and node.end_lineno:
            return node.end_lineno - node.lineno + 1
        return 1

    def _calculate_complexity(self, node):
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, ast.If | ast.While | ast.For | ast.AsyncFor | ast.ExceptHandler | ast.And | ast.Or):
                complexity += 1

        return complexity
