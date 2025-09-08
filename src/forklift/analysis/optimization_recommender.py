"""
Optimization Recommender for Project Completeness Review

This module generates prioritized optimization recommendations based on comprehensive
project analysis including functionality, code quality, test coverage, documentation,
and cleanup opportunities.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Priority levels for recommendations"""
    CRITICAL = "critical"  # Blocks core functionality
    HIGH = "high"         # Significantly impacts users
    MEDIUM = "medium"     # Moderate impact
    LOW = "low"          # Nice to have


class EffortLevel(Enum):
    """Effort estimation levels"""
    SMALL = "small"      # < 1 day
    MEDIUM = "medium"    # 1-3 days
    LARGE = "large"      # > 3 days


class ImpactLevel(Enum):
    """Impact assessment levels"""
    LOW = "low"          # Minor improvement
    MEDIUM = "medium"    # Noticeable improvement
    HIGH = "high"        # Significant improvement


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"          # Safe to implement
    MEDIUM = "medium"    # Some risk, needs testing
    HIGH = "high"        # High risk, needs careful planning


@dataclass
class Recommendation:
    """Individual optimization recommendation"""
    title: str
    description: str
    priority: Priority
    effort_estimate: EffortLevel
    impact_estimate: ImpactLevel
    risk_level: RiskLevel
    category: str
    implementation_steps: List[str]
    success_criteria: List[str]
    dependencies: List[str] = field(default_factory=list)
    files_affected: List[str] = field(default_factory=list)
    estimated_hours: Optional[int] = None
    
    @property
    def priority_score(self) -> int:
        """Calculate priority score for sorting"""
        priority_weights = {
            Priority.CRITICAL: 1000,
            Priority.HIGH: 100,
            Priority.MEDIUM: 10,
            Priority.LOW: 1
        }
        
        impact_weights = {
            ImpactLevel.HIGH: 100,
            ImpactLevel.MEDIUM: 10,
            ImpactLevel.LOW: 1
        }
        
        effort_weights = {
            EffortLevel.SMALL: 10,
            EffortLevel.MEDIUM: 5,
            EffortLevel.LARGE: 1
        }
        
        risk_weights = {
            RiskLevel.LOW: 10,
            RiskLevel.MEDIUM: 5,
            RiskLevel.HIGH: 1
        }
        
        return (
            priority_weights[self.priority] +
            impact_weights[self.impact_estimate] +
            effort_weights[self.effort_estimate] +
            risk_weights[self.risk_level]
        )


@dataclass
class QuickWin:
    """Quick win opportunity"""
    title: str
    description: str
    effort_hours: int
    impact_description: str
    implementation_steps: List[str]
    files_to_modify: List[str] = field(default_factory=list)
    files_to_remove: List[str] = field(default_factory=list)


@dataclass
class OptimizationReport:
    """Complete optimization recommendations report"""
    generated_at: datetime
    project_health_score: float
    critical_issues: List[Recommendation]
    high_priority_recommendations: List[Recommendation]
    medium_priority_recommendations: List[Recommendation]
    low_priority_recommendations: List[Recommendation]
    quick_wins: List[QuickWin]
    cleanup_opportunities: List[str]
    implementation_roadmap: Dict[str, List[Recommendation]]
    resource_estimates: Dict[str, int]  # category -> hours
    
    @property
    def total_recommendations(self) -> int:
        """Total number of recommendations"""
        return (
            len(self.critical_issues) +
            len(self.high_priority_recommendations) +
            len(self.medium_priority_recommendations) +
            len(self.low_priority_recommendations)
        )


class OptimizationRecommender:
    """Generates prioritized optimization recommendations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_recommendations(
        self,
        cleanup_analysis_path: str,
        code_quality_analysis_path: str,
        test_coverage_path: str,
        documentation_analysis_path: str
    ) -> OptimizationReport:
        """
        Generate comprehensive optimization recommendations
        
        Args:
            cleanup_analysis_path: Path to project cleanup analysis JSON
            code_quality_analysis_path: Path to code quality analysis JSON
            test_coverage_path: Path to test coverage JSON
            documentation_analysis_path: Path to documentation analysis
            
        Returns:
            Complete optimization report with prioritized recommendations
        """
        self.logger.info("Generating optimization recommendations")
        
        # Load analysis data
        cleanup_data = self._load_json(cleanup_analysis_path)
        quality_data = self._load_json(code_quality_analysis_path)
        coverage_data = self._load_json(test_coverage_path)
        docs_data = self._load_documentation_analysis(documentation_analysis_path)
        
        # Generate recommendations by category
        critical_issues = self._identify_critical_issues(cleanup_data, quality_data, coverage_data)
        functionality_recs = self._generate_functionality_recommendations(cleanup_data)
        quality_recs = self._generate_code_quality_recommendations(quality_data)
        testing_recs = self._generate_testing_recommendations(coverage_data)
        docs_recs = self._generate_documentation_recommendations(docs_data)
        cleanup_recs = self._generate_cleanup_recommendations(cleanup_data)
        
        # Combine and prioritize all recommendations
        all_recommendations = (
            functionality_recs + quality_recs + testing_recs + 
            docs_recs + cleanup_recs
        )
        
        # Sort by priority score
        all_recommendations.sort(key=lambda r: r.priority_score, reverse=True)
        
        # Categorize by priority
        high_priority = [r for r in all_recommendations if r.priority == Priority.HIGH]
        medium_priority = [r for r in all_recommendations if r.priority == Priority.MEDIUM]
        low_priority = [r for r in all_recommendations if r.priority == Priority.LOW]
        
        # Generate quick wins
        quick_wins = self._identify_quick_wins(cleanup_data, quality_data)
        
        # Generate cleanup opportunities
        cleanup_opportunities = self._generate_cleanup_list(cleanup_data)
        
        # Create implementation roadmap
        roadmap = self._create_implementation_roadmap(all_recommendations)
        
        # Calculate resource estimates
        resource_estimates = self._calculate_resource_estimates(all_recommendations)
        
        # Calculate project health score
        health_score = self._calculate_project_health_score(
            cleanup_data, quality_data, coverage_data, docs_data
        )
        
        return OptimizationReport(
            generated_at=datetime.now(),
            project_health_score=health_score,
            critical_issues=critical_issues,
            high_priority_recommendations=high_priority,
            medium_priority_recommendations=medium_priority,
            low_priority_recommendations=low_priority,
            quick_wins=quick_wins,
            cleanup_opportunities=cleanup_opportunities,
            implementation_roadmap=roadmap,
            resource_estimates=resource_estimates
        )
    
    def _load_json(self, path: str) -> Dict:
        """Load JSON data from file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load {path}: {e}")
            return {}
    
    def _load_documentation_analysis(self, path: str) -> Dict:
        """Load documentation analysis (could be JSON or markdown)"""
        try:
            if path.endswith('.json'):
                return self._load_json(path)
            else:
                # Parse markdown report for key metrics
                with open(path, 'r') as f:
                    content = f.read()
                return self._parse_documentation_markdown(content)
        except Exception as e:
            self.logger.error(f"Failed to load documentation analysis {path}: {e}")
            return {}
    
    def _parse_documentation_markdown(self, content: str) -> Dict:
        """Parse documentation markdown report for key metrics"""
        # Extract key metrics from markdown
        data = {
            'overall_score': 0.0,
            'api_coverage': 0.0,
            'readme_score': 0.0,
            'user_guides_score': 0.0,
            'contributor_docs_score': 0.0,
            'gaps': []
        }
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if 'Overall Score:' in line:
                try:
                    # Extract score from patterns like "**Overall Score:** 73.7/100"
                    parts = line.split('Overall Score:')
                    if len(parts) > 1:
                        score_part = parts[1].strip().replace('*', '').strip()
                        score = float(score_part.split('/')[0])
                        data['overall_score'] = score
                except:
                    pass
            elif 'API Documentation Coverage:' in line:
                try:
                    # Extract coverage from patterns like "- **API Documentation Coverage:** 95.6% across 79 files"
                    parts = line.split('API Documentation Coverage:')
                    if len(parts) > 1:
                        coverage_part = parts[1].strip().replace('*', '').strip()
                        coverage = float(coverage_part.split('%')[0])
                        data['api_coverage'] = coverage
                except:
                    pass
        
        return data
    
    def _identify_critical_issues(
        self, 
        cleanup_data: Dict, 
        quality_data: Dict, 
        coverage_data: Dict
    ) -> List[Recommendation]:
        """Identify critical issues that block core functionality"""
        critical_issues = []
        
        # Check for incomplete specifications that block core features
        spec_analysis = cleanup_data.get('specification_analysis', {})
        incomplete_tasks = spec_analysis.get('incomplete_tasks', 0)
        total_tasks = spec_analysis.get('total_tasks', 0)
        completion_rate = (total_tasks - incomplete_tasks) / total_tasks if total_tasks > 0 else 1.0
        
        if completion_rate < 0.7:  # Less than 70% complete
            critical_issues.append(Recommendation(
                title="Complete Critical Missing Features",
                description=f"Project has {incomplete_tasks} incomplete tasks out of {total_tasks} total tasks. "
                           f"Completion rate is {completion_rate:.1%}, which blocks core functionality.",
                priority=Priority.CRITICAL,
                effort_estimate=EffortLevel.LARGE,
                impact_estimate=ImpactLevel.HIGH,
                risk_level=RiskLevel.MEDIUM,
                category="functionality",
                implementation_steps=[
                    "Review incomplete specifications and prioritize by user impact",
                    "Complete missing core features (report generation, PR automation)",
                    "Implement missing CLI commands and user interfaces",
                    "Add comprehensive error handling and validation",
                    "Test all completed features end-to-end"
                ],
                success_criteria=[
                    "All critical user workflows are functional",
                    "Core features can be used without workarounds",
                    "Task completion rate above 80%",
                    "No blocking issues for primary use cases"
                ],
                estimated_hours=120
            ))
        
        # Check for high-severity code quality issues
        quality_metrics = quality_data.get('metrics', {})
        technical_debt_score = quality_metrics.get('technical_debt_score', 0)
        
        if technical_debt_score > 2.0:  # High technical debt
            critical_issues.append(Recommendation(
                title="Address Critical Technical Debt",
                description=f"Technical debt score of {technical_debt_score:.2f} indicates critical "
                           "code quality issues that impact maintainability and reliability.",
                priority=Priority.CRITICAL,
                effort_estimate=EffortLevel.LARGE,
                impact_estimate=ImpactLevel.HIGH,
                risk_level=RiskLevel.HIGH,
                category="code_quality",
                implementation_steps=[
                    "Fix deprecated code patterns and security issues",
                    "Reduce cyclomatic complexity in critical functions",
                    "Refactor large classes and long functions",
                    "Add missing error handling and input validation",
                    "Update deprecated dependencies and APIs"
                ],
                success_criteria=[
                    "Technical debt score below 1.5",
                    "No deprecated code patterns in critical paths",
                    "All functions have complexity below 15",
                    "Comprehensive error handling implemented"
                ],
                estimated_hours=80
            ))
        
        return critical_issues
    
    def _generate_functionality_recommendations(self, cleanup_data: Dict) -> List[Recommendation]:
        """Generate functionality-related recommendations"""
        recommendations = []
        
        spec_analysis = cleanup_data.get('specification_analysis', {})
        incomplete_specs = spec_analysis.get('incomplete_specifications', 0)
        
        if incomplete_specs > 0:
            recommendations.append(Recommendation(
                title="Complete Incomplete Specifications",
                description=f"Found {incomplete_specs} incomplete specifications that need design or task documents.",
                priority=Priority.HIGH,
                effort_estimate=EffortLevel.MEDIUM,
                impact_estimate=ImpactLevel.MEDIUM,
                risk_level=RiskLevel.LOW,
                category="functionality",
                implementation_steps=[
                    "Review incomplete specifications for missing components",
                    "Complete missing design documents",
                    "Create detailed task breakdowns",
                    "Validate requirements against user needs"
                ],
                success_criteria=[
                    "All specifications have complete design documents",
                    "All specifications have actionable task lists",
                    "Requirements are validated and approved"
                ],
                estimated_hours=24
            ))
        
        return recommendations
    
    def _generate_code_quality_recommendations(self, quality_data: Dict) -> List[Recommendation]:
        """Generate code quality recommendations"""
        recommendations = []
        
        metrics = quality_data.get('metrics', {})
        issue_counts = metrics.get('issue_count_by_priority', {})
        
        # High priority issues
        high_issues = issue_counts.get('high', 0)
        if high_issues > 0:
            recommendations.append(Recommendation(
                title="Fix High-Priority Code Quality Issues",
                description=f"Found {high_issues} high-priority code quality issues including "
                           "complex functions, deprecated code, and missing documentation.",
                priority=Priority.HIGH,
                effort_estimate=EffortLevel.MEDIUM,
                impact_estimate=ImpactLevel.MEDIUM,
                risk_level=RiskLevel.MEDIUM,
                category="code_quality",
                implementation_steps=[
                    "Refactor complex functions to reduce cyclomatic complexity",
                    "Update deprecated code patterns to current standards",
                    "Add missing docstrings to public APIs",
                    "Break down large classes into smaller components",
                    "Add comprehensive error handling"
                ],
                success_criteria=[
                    "All functions have complexity below 15",
                    "No deprecated code patterns remain",
                    "All public APIs have docstrings",
                    "Error handling covers all edge cases"
                ],
                estimated_hours=40
            ))
        
        # Magic numbers and maintainability
        magic_numbers = issue_counts.get('magic_number', 0)
        if magic_numbers > 100:
            recommendations.append(Recommendation(
                title="Replace Magic Numbers with Named Constants",
                description=f"Found {magic_numbers} magic numbers that should be replaced with named constants.",
                priority=Priority.MEDIUM,
                effort_estimate=EffortLevel.MEDIUM,
                impact_estimate=ImpactLevel.LOW,
                risk_level=RiskLevel.LOW,
                category="code_quality",
                implementation_steps=[
                    "Identify all magic numbers in codebase",
                    "Create named constants for configuration values",
                    "Replace magic numbers with descriptive constants",
                    "Group related constants in configuration modules"
                ],
                success_criteria=[
                    "No magic numbers in critical business logic",
                    "All configuration values use named constants",
                    "Constants are well-documented and grouped logically"
                ],
                estimated_hours=16
            ))
        
        return recommendations
    
    def _generate_testing_recommendations(self, coverage_data: Dict) -> List[Recommendation]:
        """Generate testing-related recommendations"""
        recommendations = []
        
        # Calculate overall coverage
        total_statements = 0
        covered_statements = 0
        
        files = coverage_data.get('files', {})
        for file_data in files.values():
            summary = file_data.get('summary', {})
            total_statements += summary.get('num_statements', 0)
            covered_statements += summary.get('covered_lines', 0)
        
        if total_statements > 0:
            coverage_percentage = (covered_statements / total_statements) * 100
            
            if coverage_percentage < 90:
                recommendations.append(Recommendation(
                    title="Improve Test Coverage",
                    description=f"Current test coverage is {coverage_percentage:.1f}%. "
                               "Target is 90% for production readiness.",
                    priority=Priority.HIGH,
                    effort_estimate=EffortLevel.LARGE,
                    impact_estimate=ImpactLevel.HIGH,
                    risk_level=RiskLevel.LOW,
                    category="testing",
                    implementation_steps=[
                        "Identify files with low test coverage",
                        "Write unit tests for uncovered functions",
                        "Add integration tests for critical workflows",
                        "Implement edge case and error condition tests",
                        "Add performance and load tests for critical paths"
                    ],
                    success_criteria=[
                        "Overall test coverage above 90%",
                        "All critical functions have unit tests",
                        "Integration tests cover main user workflows",
                        "Error conditions are thoroughly tested"
                    ],
                    estimated_hours=60
                ))
        
        return recommendations
    
    def _generate_documentation_recommendations(self, docs_data: Dict) -> List[Recommendation]:
        """Generate documentation recommendations"""
        recommendations = []
        
        overall_score = docs_data.get('overall_score', 0)
        api_coverage = docs_data.get('api_coverage', 0)
        
        if overall_score < 80:
            recommendations.append(Recommendation(
                title="Improve Documentation Coverage",
                description=f"Documentation score is {overall_score:.1f}/100. "
                           f"API coverage is {api_coverage:.1f}%.",
                priority=Priority.MEDIUM,
                effort_estimate=EffortLevel.MEDIUM,
                impact_estimate=ImpactLevel.MEDIUM,
                risk_level=RiskLevel.LOW,
                category="documentation",
                implementation_steps=[
                    "Add docstrings to functions with missing documentation",
                    "Create comprehensive user guides",
                    "Update README with current functionality",
                    "Add troubleshooting and FAQ sections",
                    "Create contributor guidelines"
                ],
                success_criteria=[
                    "API documentation coverage above 95%",
                    "All user workflows documented",
                    "Troubleshooting guides available",
                    "Contributor documentation complete"
                ],
                estimated_hours=32
            ))
        
        return recommendations
    
    def _generate_cleanup_recommendations(self, cleanup_data: Dict) -> List[Recommendation]:
        """Generate cleanup recommendations"""
        recommendations = []
        
        file_analysis = cleanup_data.get('file_analysis', {})
        unused_files = file_analysis.get('unused_files', 0)
        temporary_files = file_analysis.get('temporary_files', 0)
        
        if unused_files > 50 or temporary_files > 5:
            recommendations.append(Recommendation(
                title="Clean Up Project Files",
                description=f"Found {unused_files} unused files and {temporary_files} temporary files "
                           "that should be removed to improve project organization.",
                priority=Priority.MEDIUM,
                effort_estimate=EffortLevel.SMALL,
                impact_estimate=ImpactLevel.LOW,
                risk_level=RiskLevel.LOW,
                category="cleanup",
                implementation_steps=[
                    "Review list of unused and temporary files",
                    "Verify files are truly unused (no hidden dependencies)",
                    "Remove temporary and debug files",
                    "Archive or remove unused development artifacts",
                    "Update .gitignore to prevent future accumulation"
                ],
                success_criteria=[
                    "All temporary files removed",
                    "Unused files reduced by 80%",
                    "Project structure is clean and organized",
                    "No build artifacts in version control"
                ],
                estimated_hours=8
            ))
        
        return recommendations
    
    def _identify_quick_wins(self, cleanup_data: Dict, quality_data: Dict) -> List[QuickWin]:
        """Identify quick win opportunities"""
        quick_wins = []
        
        # Temporary file cleanup
        file_analysis = cleanup_data.get('file_analysis', {})
        temporary_files = file_analysis.get('temporary_files', 0)
        
        if temporary_files > 0:
            quick_wins.append(QuickWin(
                title="Remove Temporary Files",
                description=f"Remove {temporary_files} temporary and debug files",
                effort_hours=2,
                impact_description="Cleaner project structure, reduced repository size",
                implementation_steps=[
                    "Identify all temporary files (*.log, debug output, etc.)",
                    "Verify files are safe to remove",
                    "Remove temporary files",
                    "Update .gitignore to prevent re-addition"
                ],
                files_to_remove=["forklift.log", "dev-artifacts/*.txt", "*.tmp"]
            ))
        
        # Fix deprecated code patterns
        tech_debt_items = quality_data.get('technical_debt_items', [])
        deprecated_items = [item for item in tech_debt_items if 'deprecated' in item.get('title', '').lower()]
        
        if deprecated_items:
            quick_wins.append(QuickWin(
                title="Update Deprecated Code",
                description="Replace deprecated code patterns with current alternatives",
                effort_hours=4,
                impact_description="Improved code reliability and future compatibility",
                implementation_steps=[
                    "Identify all deprecated code patterns",
                    "Research current alternatives",
                    "Update deprecated patterns",
                    "Test updated code"
                ]
            ))
        
        # Add missing docstrings to critical functions
        missing_docstrings = quality_data.get('metrics', {}).get('issue_count_by_type', {}).get('missing_docstring', 0)
        if missing_docstrings > 0 and missing_docstrings < 20:
            quick_wins.append(QuickWin(
                title="Add Missing Docstrings",
                description=f"Add docstrings to {missing_docstrings} functions missing documentation",
                effort_hours=6,
                impact_description="Better code documentation and developer experience",
                implementation_steps=[
                    "Identify functions missing docstrings",
                    "Write clear, descriptive docstrings",
                    "Follow project documentation standards",
                    "Validate docstring format and content"
                ]
            ))
        
        return quick_wins
    
    def _generate_cleanup_list(self, cleanup_data: Dict) -> List[str]:
        """Generate list of specific cleanup opportunities"""
        cleanup_list = []
        
        # Extract safe-to-remove files
        detailed_analyses = cleanup_data.get('detailed_analyses', {})
        files = detailed_analyses.get('files', [])
        
        safe_files = [
            f["path"] for f in files 
            if f.get('safety_level') == 'safe' and f.get('removal_reason')
        ]
        
        if safe_files:
            cleanup_list.extend([
                f"Remove temporary file: {file}" for file in safe_files[:10]  # Limit to first 10
            ])
        
        # Add general cleanup opportunities
        file_analysis = cleanup_data.get('file_analysis', {})
        if file_analysis.get('temporary_files', 0) > 0:
            cleanup_list.append("Clean up temporary and debug files")
        
        if file_analysis.get('unused_files', 0) > 50:
            cleanup_list.append("Archive or remove unused development artifacts")
        
        return cleanup_list
    
    def _create_implementation_roadmap(self, recommendations: List[Recommendation]) -> Dict[str, List[Recommendation]]:
        """Create implementation roadmap organized by phases"""
        roadmap = {
            "Phase 1: Critical Issues": [],
            "Phase 2: High Priority": [],
            "Phase 3: Medium Priority": [],
            "Phase 4: Low Priority": []
        }
        
        for rec in recommendations:
            if rec.priority == Priority.CRITICAL:
                roadmap["Phase 1: Critical Issues"].append(rec)
            elif rec.priority == Priority.HIGH:
                roadmap["Phase 2: High Priority"].append(rec)
            elif rec.priority == Priority.MEDIUM:
                roadmap["Phase 3: Medium Priority"].append(rec)
            else:
                roadmap["Phase 4: Low Priority"].append(rec)
        
        return roadmap
    
    def _calculate_resource_estimates(self, recommendations: List[Recommendation]) -> Dict[str, int]:
        """Calculate resource estimates by category"""
        estimates = {}
        
        for rec in recommendations:
            category = rec.category
            hours = rec.estimated_hours or self._estimate_hours_from_effort(rec.effort_estimate)
            
            if category not in estimates:
                estimates[category] = 0
            estimates[category] += hours
        
        # Add total
        estimates["total"] = sum(estimates.values())
        
        return estimates
    
    def _estimate_hours_from_effort(self, effort: EffortLevel) -> int:
        """Convert effort level to hour estimate"""
        effort_hours = {
            EffortLevel.SMALL: 8,
            EffortLevel.MEDIUM: 16,
            EffortLevel.LARGE: 40
        }
        return effort_hours.get(effort, 16)
    
    def _calculate_project_health_score(
        self, 
        cleanup_data: Dict, 
        quality_data: Dict, 
        coverage_data: Dict, 
        docs_data: Dict
    ) -> float:
        """Calculate overall project health score (0-100)"""
        scores = []
        
        # Functionality completeness (30% weight)
        spec_analysis = cleanup_data.get('specification_analysis', {})
        completion_rate = spec_analysis.get('completion_percentage', 0) / 100
        functionality_score = completion_rate * 100
        scores.append((functionality_score, 0.3))
        
        # Code quality (25% weight)
        quality_metrics = quality_data.get('metrics', {})
        debt_score = quality_metrics.get('technical_debt_score', 0)
        # Convert debt score to health score (lower debt = higher health)
        quality_score = max(0, 100 - (debt_score * 20))
        scores.append((quality_score, 0.25))
        
        # Test coverage (25% weight)
        # Calculate coverage from coverage data
        total_statements = sum(
            file_data.get('summary', {}).get('num_statements', 0)
            for file_data in coverage_data.get('files', {}).values()
        )
        covered_statements = sum(
            file_data.get('summary', {}).get('covered_lines', 0)
            for file_data in coverage_data.get('files', {}).values()
        )
        
        if total_statements > 0:
            coverage_score = (covered_statements / total_statements) * 100
        else:
            coverage_score = 0
        scores.append((coverage_score, 0.25))
        
        # Documentation (20% weight)
        docs_score = docs_data.get('overall_score', 0)
        scores.append((docs_score, 0.2))
        
        # Calculate weighted average
        weighted_sum = sum(score * weight for score, weight in scores)
        total_weight = sum(weight for _, weight in scores)
        
        return weighted_sum / total_weight if total_weight > 0 else 0