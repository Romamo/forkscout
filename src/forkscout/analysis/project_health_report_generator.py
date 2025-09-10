"""
Comprehensive Project Health Report Generator

Generates unified health reports that compile all assessment results from
functionality, code quality, test coverage, documentation, and cleanup analyses.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class ProjectHealthMetrics:
    """Overall project health metrics"""
    functionality_score: float
    code_quality_score: float
    test_coverage_score: float
    documentation_score: float
    cleanup_score: float
    overall_health_score: float
    
    @property
    def health_status(self) -> str:
        """Get health status based on overall score"""
        if self.overall_health_score >= 85:
            return "🟢 EXCELLENT"
        elif self.overall_health_score >= 70:
            return "🟡 GOOD"
        elif self.overall_health_score >= 50:
            return "🟠 NEEDS ATTENTION"
        else:
            return "🔴 CRITICAL"


@dataclass
class CriticalIssue:
    """Critical issue that blocks core functionality"""
    title: str
    description: str
    impact: str
    category: str
    priority: str
    files_affected: List[str] = field(default_factory=list)
    estimated_effort: str = "medium"


@dataclass
class QuickWin:
    """Quick win opportunity for immediate improvement"""
    title: str
    description: str
    effort_hours: int
    impact_description: str
    category: str
    implementation_steps: List[str] = field(default_factory=list)


@dataclass
class ActionItem:
    """Prioritized action item with implementation guidance"""
    title: str
    description: str
    priority: str  # critical, high, medium, low
    category: str
    effort_estimate: str
    impact_level: str
    implementation_steps: List[str]
    success_criteria: List[str]
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ProjectHealthReport:
    """Complete project health report"""
    generated_at: datetime
    project_name: str
    metrics: ProjectHealthMetrics
    critical_issues: List[CriticalIssue]
    quick_wins: List[QuickWin]
    prioritized_actions: List[ActionItem]
    cleanup_opportunities: List[str]
    implementation_roadmap: Dict[str, List[ActionItem]]
    resource_estimates: Dict[str, int]
    executive_summary: str
    detailed_findings: Dict[str, Any]


class ProjectHealthReportGenerator:
    """Generates comprehensive project health reports"""
    
    def __init__(self, project_name: str = "Forkscout"):
        self.project_name = project_name
        self.logger = logging.getLogger(__name__)
    
    def generate_comprehensive_report(
        self,
        functionality_data: Optional[Dict] = None,
        code_quality_data: Optional[Dict] = None,
        test_coverage_data: Optional[Dict] = None,
        documentation_data: Optional[Dict] = None,
        cleanup_data: Optional[Dict] = None,
        optimization_data: Optional[Dict] = None
    ) -> ProjectHealthReport:
        """
        Generate comprehensive project health report from all analysis data
        
        Args:
            functionality_data: Functionality assessment results
            code_quality_data: Code quality analysis results
            test_coverage_data: Test coverage analysis results
            documentation_data: Documentation assessment results
            cleanup_data: Project cleanup analysis results
            optimization_data: Optimization recommendations data
            
        Returns:
            Complete project health report
        """
        self.logger.info("Generating comprehensive project health report")
        
        # Calculate health metrics
        metrics = self._calculate_health_metrics(
            functionality_data, code_quality_data, test_coverage_data,
            documentation_data, cleanup_data
        )
        
        # Identify critical issues
        critical_issues = self._identify_critical_issues(
            functionality_data, code_quality_data, test_coverage_data
        )
        
        # Extract quick wins
        quick_wins = self._extract_quick_wins(
            cleanup_data, code_quality_data, optimization_data
        )
        
        # Generate prioritized action items
        prioritized_actions = self._generate_prioritized_actions(
            functionality_data, code_quality_data, test_coverage_data,
            documentation_data, cleanup_data
        )
        
        # Extract cleanup opportunities
        cleanup_opportunities = self._extract_cleanup_opportunities(cleanup_data)
        
        # Create implementation roadmap
        roadmap = self._create_implementation_roadmap(prioritized_actions)
        
        # Calculate resource estimates
        resource_estimates = self._calculate_resource_estimates(prioritized_actions)
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            metrics, critical_issues, quick_wins, prioritized_actions
        )
        
        # Compile detailed findings
        detailed_findings = self._compile_detailed_findings(
            functionality_data, code_quality_data, test_coverage_data,
            documentation_data, cleanup_data
        )
        
        return ProjectHealthReport(
            generated_at=datetime.now(),
            project_name=self.project_name,
            metrics=metrics,
            critical_issues=critical_issues,
            quick_wins=quick_wins,
            prioritized_actions=prioritized_actions,
            cleanup_opportunities=cleanup_opportunities,
            implementation_roadmap=roadmap,
            resource_estimates=resource_estimates,
            executive_summary=executive_summary,
            detailed_findings=detailed_findings
        )
    
    def generate_markdown_report(self, report: ProjectHealthReport) -> str:
        """Generate comprehensive markdown report"""
        sections = [
            self._generate_header(report),
            self._generate_executive_summary_section(report),
            self._generate_health_metrics_section(report),
            self._generate_critical_issues_section(report),
            self._generate_quick_wins_section(report),
            self._generate_prioritized_actions_section(report),
            self._generate_implementation_roadmap_section(report),
            self._generate_resource_estimates_section(report),
            self._generate_detailed_findings_section(report),
            self._generate_appendix_section(report)
        ]
        
        return "\n\n".join(sections)
    
    def generate_json_report(self, report: ProjectHealthReport) -> str:
        """Generate JSON report for programmatic consumption"""
        report_data = {
            "metadata": {
                "generated_at": report.generated_at.isoformat(),
                "project_name": report.project_name,
                "generator_version": "1.0"
            },
            "metrics": {
                "functionality_score": report.metrics.functionality_score,
                "code_quality_score": report.metrics.code_quality_score,
                "test_coverage_score": report.metrics.test_coverage_score,
                "documentation_score": report.metrics.documentation_score,
                "cleanup_score": report.metrics.cleanup_score,
                "overall_health_score": report.metrics.overall_health_score,
                "health_status": report.metrics.health_status
            },
            "critical_issues": [
                {
                    "title": issue.title,
                    "description": issue.description,
                    "impact": issue.impact,
                    "category": issue.category,
                    "priority": issue.priority,
                    "files_affected": issue.files_affected,
                    "estimated_effort": issue.estimated_effort
                }
                for issue in report.critical_issues
            ],
            "quick_wins": [
                {
                    "title": win.title,
                    "description": win.description,
                    "effort_hours": win.effort_hours,
                    "impact_description": win.impact_description,
                    "category": win.category,
                    "implementation_steps": win.implementation_steps
                }
                for win in report.quick_wins
            ],
            "prioritized_actions": [
                {
                    "title": action.title,
                    "description": action.description,
                    "priority": action.priority,
                    "category": action.category,
                    "effort_estimate": action.effort_estimate,
                    "impact_level": action.impact_level,
                    "implementation_steps": action.implementation_steps,
                    "success_criteria": action.success_criteria,
                    "dependencies": action.dependencies
                }
                for action in report.prioritized_actions
            ],
            "cleanup_opportunities": report.cleanup_opportunities,
            "implementation_roadmap": report.implementation_roadmap,
            "resource_estimates": report.resource_estimates,
            "executive_summary": report.executive_summary,
            "detailed_findings": report.detailed_findings
        }
        
        return json.dumps(report_data, indent=2, default=str)
    
    def _calculate_health_metrics(
        self,
        functionality_data: Optional[Dict],
        code_quality_data: Optional[Dict],
        test_coverage_data: Optional[Dict],
        documentation_data: Optional[Dict],
        cleanup_data: Optional[Dict]
    ) -> ProjectHealthMetrics:
        """Calculate overall project health metrics"""
        
        # Functionality score (based on task completion)
        functionality_score = 0.0
        if functionality_data:
            spec_analysis = functionality_data.get('specification_analysis', {})
            completion_rate = spec_analysis.get('completion_percentage', 0) / 100
            functionality_score = completion_rate * 100
        
        # Code quality score (based on maintainability and technical debt)
        code_quality_score = 0.0
        if code_quality_data:
            metrics = code_quality_data.get('metrics', {})
            maintainability = metrics.get('average_maintainability', 0)
            debt_score = metrics.get('technical_debt_score', 4.0)
            # Convert debt score (0-4, lower is better) to quality score (0-100, higher is better)
            debt_penalty = (debt_score / 4.0) * 30  # Max 30 point penalty
            code_quality_score = max(0, maintainability - debt_penalty)
        
        # Test coverage score
        test_coverage_score = 0.0
        if test_coverage_data:
            # Calculate from coverage data
            total_statements = 0
            covered_statements = 0
            files = test_coverage_data.get('files', {})
            
            for file_data in files.values():
                summary = file_data.get('summary', {})
                total_statements += summary.get('num_statements', 0)
                covered_statements += summary.get('covered_lines', 0)
            
            if total_statements > 0:
                test_coverage_score = (covered_statements / total_statements) * 100
        
        # Documentation score
        documentation_score = 0.0
        if documentation_data:
            documentation_score = documentation_data.get('overall_score', 0)
        
        # Cleanup score (based on project organization)
        cleanup_score = 100.0  # Start with perfect score
        if cleanup_data:
            file_analysis = cleanup_data.get('file_analysis', {})
            unused_files = file_analysis.get('unused_files', 0)
            temporary_files = file_analysis.get('temporary_files', 0)
            
            # Penalize for excess files
            cleanup_score -= min(unused_files * 0.5, 30)  # Max 30 point penalty
            cleanup_score -= min(temporary_files * 2, 20)  # Max 20 point penalty
            cleanup_score = max(0, cleanup_score)
        
        # Calculate weighted overall score
        weights = {
            'functionality': 0.35,
            'code_quality': 0.25,
            'test_coverage': 0.20,
            'documentation': 0.15,
            'cleanup': 0.05
        }
        
        overall_score = (
            functionality_score * weights['functionality'] +
            code_quality_score * weights['code_quality'] +
            test_coverage_score * weights['test_coverage'] +
            documentation_score * weights['documentation'] +
            cleanup_score * weights['cleanup']
        )
        
        return ProjectHealthMetrics(
            functionality_score=functionality_score,
            code_quality_score=code_quality_score,
            test_coverage_score=test_coverage_score,
            documentation_score=documentation_score,
            cleanup_score=cleanup_score,
            overall_health_score=overall_score
        )
    
    def _identify_critical_issues(
        self,
        functionality_data: Optional[Dict],
        code_quality_data: Optional[Dict],
        test_coverage_data: Optional[Dict]
    ) -> List[CriticalIssue]:
        """Identify critical issues that block core functionality"""
        critical_issues = []
        
        # Functionality critical issues
        if functionality_data:
            spec_analysis = functionality_data.get('specification_analysis', {})
            incomplete_tasks = spec_analysis.get('incomplete_tasks', 0)
            total_tasks = spec_analysis.get('total_tasks', 0)
            
            if total_tasks > 0:
                completion_rate = (total_tasks - incomplete_tasks) / total_tasks
                if completion_rate < 0.6:  # More strict threshold for critical
                    critical_issues.append(CriticalIssue(
                        title="Incomplete Core Functionality",
                        description=f"{incomplete_tasks} out of {total_tasks} tasks incomplete ({completion_rate:.1%} completion rate)",
                        impact="Blocks primary user workflows and core value proposition",
                        category="functionality",
                        priority="critical",
                        estimated_effort="large"
                    ))
        
        # Code quality critical issues
        if code_quality_data:
            metrics = code_quality_data.get('metrics', {})
            debt_score = metrics.get('technical_debt_score', 0)
            critical_issues_count = metrics.get('issue_count_by_priority', {}).get('critical', 0)
            
            if debt_score > 3.0 or critical_issues_count > 0:
                critical_issues.append(CriticalIssue(
                    title="Critical Technical Debt",
                    description=f"Technical debt score of {debt_score:.2f}/4.0 with {critical_issues_count} critical issues",
                    impact="Affects system reliability, security, and maintainability",
                    category="code_quality",
                    priority="critical",
                    estimated_effort="large"
                ))
        
        # Test coverage critical issues
        if test_coverage_data:
            # Calculate coverage
            total_statements = 0
            covered_statements = 0
            files = test_coverage_data.get('files', {})
            
            for file_data in files.values():
                summary = file_data.get('summary', {})
                total_statements += summary.get('num_statements', 0)
                covered_statements += summary.get('covered_lines', 0)
            
            if total_statements > 0:
                coverage_percentage = (covered_statements / total_statements) * 100
                if coverage_percentage < 70:
                    critical_issues.append(CriticalIssue(
                        title="Insufficient Test Coverage",
                        description=f"Test coverage at {coverage_percentage:.1f}% is below critical threshold of 70%",
                        impact="High risk of undetected bugs and regressions in production",
                        category="testing",
                        priority="high",  # High rather than critical for coverage
                        estimated_effort="large"
                    ))
        
        return critical_issues
    
    def _extract_quick_wins(
        self,
        cleanup_data: Optional[Dict],
        code_quality_data: Optional[Dict],
        optimization_data: Optional[Dict]
    ) -> List[QuickWin]:
        """Extract quick win opportunities"""
        quick_wins = []
        
        # Cleanup quick wins
        if cleanup_data:
            file_analysis = cleanup_data.get('file_analysis', {})
            temporary_files = file_analysis.get('temporary_files', 0)
            
            if temporary_files > 0:
                quick_wins.append(QuickWin(
                    title="Remove Temporary Files",
                    description=f"Remove {temporary_files} temporary and debug files cluttering the project",
                    effort_hours=2,
                    impact_description="Cleaner project structure, reduced repository size",
                    category="cleanup",
                    implementation_steps=[
                        "Identify all temporary files (*.log, debug output, etc.)",
                        "Verify files are safe to remove",
                        "Remove temporary files",
                        "Update .gitignore to prevent re-addition"
                    ]
                ))
        
        # Code quality quick wins
        if code_quality_data:
            tech_debt_items = code_quality_data.get('technical_debt_items', [])
            
            # Look for small effort items
            small_debt_items = [
                item for item in tech_debt_items 
                if item.get('effort_estimate', '').lower() == 'small'
            ]
            
            if small_debt_items:
                quick_wins.append(QuickWin(
                    title="Fix Small Technical Debt Items",
                    description=f"Address {len(small_debt_items)} small technical debt items",
                    effort_hours=8,
                    impact_description="Improved code quality and maintainability",
                    category="code_quality",
                    implementation_steps=[
                        "Review small technical debt items",
                        "Fix deprecated code patterns",
                        "Add missing docstrings",
                        "Replace magic numbers with constants"
                    ]
                ))
        
        # Optimization quick wins
        if optimization_data:
            opt_quick_wins = optimization_data.get('quick_wins', [])
            for opt_win in opt_quick_wins[:3]:  # Limit to top 3
                quick_wins.append(QuickWin(
                    title=opt_win.get('title', 'Optimization Quick Win'),
                    description=opt_win.get('description', ''),
                    effort_hours=opt_win.get('effort_hours', 4),
                    impact_description=opt_win.get('impact_description', ''),
                    category="optimization",
                    implementation_steps=opt_win.get('implementation_steps', [])
                ))
        
        return quick_wins
    
    def _generate_prioritized_actions(
        self,
        functionality_data: Optional[Dict],
        code_quality_data: Optional[Dict],
        test_coverage_data: Optional[Dict],
        documentation_data: Optional[Dict],
        cleanup_data: Optional[Dict]
    ) -> List[ActionItem]:
        """Generate prioritized action items"""
        actions = []
        
        # Functionality actions
        if functionality_data:
            spec_analysis = functionality_data.get('specification_analysis', {})
            incomplete_specs = spec_analysis.get('incomplete_specifications', 0)
            
            if incomplete_specs > 0:
                actions.append(ActionItem(
                    title="Complete Incomplete Specifications",
                    description=f"Complete {incomplete_specs} specifications missing design or task documents",
                    priority="high",
                    category="functionality",
                    effort_estimate="medium",
                    impact_level="high",
                    implementation_steps=[
                        "Review incomplete specifications",
                        "Complete missing design documents",
                        "Create detailed task breakdowns",
                        "Validate requirements"
                    ],
                    success_criteria=[
                        "All specifications have complete design documents",
                        "All specifications have actionable task lists"
                    ]
                ))
        
        # Code quality actions
        if code_quality_data:
            metrics = code_quality_data.get('metrics', {})
            high_issues = metrics.get('issue_count_by_priority', {}).get('high', 0)
            
            if high_issues > 0:
                actions.append(ActionItem(
                    title="Fix High-Priority Code Quality Issues",
                    description=f"Address {high_issues} high-priority code quality issues",
                    priority="high",
                    category="code_quality",
                    effort_estimate="medium",
                    impact_level="medium",
                    implementation_steps=[
                        "Refactor complex functions",
                        "Update deprecated code patterns",
                        "Add missing docstrings",
                        "Improve error handling"
                    ],
                    success_criteria=[
                        "All functions have complexity below 15",
                        "No deprecated code patterns remain",
                        "All public APIs have docstrings"
                    ]
                ))
        
        # Test coverage actions
        if test_coverage_data:
            total_statements = 0
            covered_statements = 0
            files = test_coverage_data.get('files', {})
            
            for file_data in files.values():
                summary = file_data.get('summary', {})
                total_statements += summary.get('num_statements', 0)
                covered_statements += summary.get('covered_lines', 0)
            
            if total_statements > 0:
                coverage_percentage = (covered_statements / total_statements) * 100
                if coverage_percentage < 90:
                    actions.append(ActionItem(
                        title="Improve Test Coverage",
                        description=f"Increase test coverage from {coverage_percentage:.1f}% to 90%+",
                        priority="high",
                        category="testing",
                        effort_estimate="large",
                        impact_level="high",
                        implementation_steps=[
                            "Identify files with low coverage",
                            "Write unit tests for uncovered functions",
                            "Add integration tests for workflows",
                            "Test error conditions and edge cases"
                        ],
                        success_criteria=[
                            "Overall test coverage above 90%",
                            "All critical functions have unit tests",
                            "Integration tests cover main workflows"
                        ]
                    ))
        
        # Documentation actions
        if documentation_data:
            overall_score = documentation_data.get('overall_score', 0)
            
            if overall_score < 80:
                actions.append(ActionItem(
                    title="Improve Documentation Coverage",
                    description=f"Increase documentation score from {overall_score:.1f}/100 to 80+",
                    priority="medium",
                    category="documentation",
                    effort_estimate="medium",
                    impact_level="medium",
                    implementation_steps=[
                        "Add docstrings to undocumented functions",
                        "Create comprehensive user guides",
                        "Update README with current functionality",
                        "Add troubleshooting documentation"
                    ],
                    success_criteria=[
                        "API documentation coverage above 95%",
                        "All user workflows documented",
                        "Troubleshooting guides available"
                    ]
                ))
        
        # Sort actions by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        actions.sort(key=lambda x: priority_order.get(x.priority, 3))
        
        return actions
    
    def _extract_cleanup_opportunities(self, cleanup_data: Optional[Dict]) -> List[str]:
        """Extract specific cleanup opportunities"""
        opportunities = []
        
        if not cleanup_data:
            return opportunities
        
        file_analysis = cleanup_data.get('file_analysis', {})
        
        # Temporary files
        temporary_files = file_analysis.get('temporary_files', 0)
        if temporary_files > 0:
            opportunities.append(f"Remove {temporary_files} temporary and debug files")
        
        # Unused files
        unused_files = file_analysis.get('unused_files', 0)
        if unused_files > 50:
            opportunities.append(f"Archive or remove {unused_files} unused development artifacts")
        
        # Extract specific files from detailed analysis
        detailed_analyses = cleanup_data.get('detailed_analyses', {})
        files = detailed_analyses.get('files', [])
        
        safe_removals = [
            f["path"] for f in files 
            if f.get('safety_level') == 'safe' and f.get('removal_reason')
        ]
        
        if safe_removals:
            opportunities.extend([
                f"Remove safe file: {file}" for file in safe_removals[:5]  # Limit display
            ])
        
        return opportunities
    
    def _create_implementation_roadmap(self, actions: List[ActionItem]) -> Dict[str, List[ActionItem]]:
        """Create phased implementation roadmap"""
        roadmap = {
            "Phase 1: Critical & High Priority": [],
            "Phase 2: Medium Priority": [],
            "Phase 3: Low Priority & Maintenance": []
        }
        
        for action in actions:
            if action.priority in ["critical", "high"]:
                roadmap["Phase 1: Critical & High Priority"].append(action)
            elif action.priority == "medium":
                roadmap["Phase 2: Medium Priority"].append(action)
            else:
                roadmap["Phase 3: Low Priority & Maintenance"].append(action)
        
        return roadmap
    
    def _calculate_resource_estimates(self, actions: List[ActionItem]) -> Dict[str, int]:
        """Calculate resource estimates by category and phase"""
        estimates = {
            "functionality": 0,
            "code_quality": 0,
            "testing": 0,
            "documentation": 0,
            "cleanup": 0,
            "total": 0
        }
        
        effort_hours = {
            "small": 8,
            "medium": 24,
            "large": 60
        }
        
        for action in actions:
            hours = effort_hours.get(action.effort_estimate, 24)
            category = action.category
            
            if category in estimates:
                estimates[category] += hours
            estimates["total"] += hours
        
        return estimates
    
    def _generate_executive_summary(
        self,
        metrics: ProjectHealthMetrics,
        critical_issues: List[CriticalIssue],
        quick_wins: List[QuickWin],
        actions: List[ActionItem]
    ) -> str:
        """Generate executive summary"""
        summary_lines = []
        
        # Overall health assessment
        summary_lines.append(f"**Project Health Status:** {metrics.health_status}")
        summary_lines.append(f"**Overall Score:** {metrics.overall_health_score:.1f}/100")
        summary_lines.append("")
        
        # Key findings
        summary_lines.append("**Key Findings:**")
        
        if metrics.functionality_score < 70:
            summary_lines.append(f"- 🔴 **Functionality:** {metrics.functionality_score:.1f}% - Significant incomplete features blocking core workflows")
        elif metrics.functionality_score < 85:
            summary_lines.append(f"- 🟡 **Functionality:** {metrics.functionality_score:.1f}% - Some features incomplete but core functionality available")
        else:
            summary_lines.append(f"- 🟢 **Functionality:** {metrics.functionality_score:.1f}% - Core functionality complete and operational")
        
        if metrics.code_quality_score < 60:
            summary_lines.append(f"- 🔴 **Code Quality:** {metrics.code_quality_score:.1f}% - High technical debt requiring immediate attention")
        elif metrics.code_quality_score < 80:
            summary_lines.append(f"- 🟡 **Code Quality:** {metrics.code_quality_score:.1f}% - Moderate technical debt, manageable with focused effort")
        else:
            summary_lines.append(f"- 🟢 **Code Quality:** {metrics.code_quality_score:.1f}% - Well-maintained codebase with minimal technical debt")
        
        if metrics.test_coverage_score < 80:
            summary_lines.append(f"- 🔴 **Test Coverage:** {metrics.test_coverage_score:.1f}% - Insufficient testing increases risk of bugs")
        elif metrics.test_coverage_score < 90:
            summary_lines.append(f"- 🟡 **Test Coverage:** {metrics.test_coverage_score:.1f}% - Good coverage but room for improvement")
        else:
            summary_lines.append(f"- 🟢 **Test Coverage:** {metrics.test_coverage_score:.1f}% - Excellent test coverage providing confidence")
        
        summary_lines.append("")
        
        # Critical issues summary
        if critical_issues:
            summary_lines.append(f"**Critical Issues:** {len(critical_issues)} issues require immediate attention")
            for issue in critical_issues[:3]:  # Top 3
                summary_lines.append(f"- {issue.title}: {issue.description}")
        else:
            summary_lines.append("**Critical Issues:** None identified - project is in stable condition")
        
        summary_lines.append("")
        
        # Quick wins summary
        if quick_wins:
            total_hours = sum(win.effort_hours for win in quick_wins)
            summary_lines.append(f"**Quick Wins Available:** {len(quick_wins)} opportunities ({total_hours} hours total effort)")
        
        # Action items summary
        high_priority_actions = len([a for a in actions if a.priority in ["critical", "high"]])
        summary_lines.append(f"**Priority Actions:** {high_priority_actions} high-priority items requiring attention")
        
        return "\n".join(summary_lines)
    
    def _compile_detailed_findings(
        self,
        functionality_data: Optional[Dict],
        code_quality_data: Optional[Dict],
        test_coverage_data: Optional[Dict],
        documentation_data: Optional[Dict],
        cleanup_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """Compile detailed findings from all analyses"""
        findings = {}
        
        # Functionality findings
        if functionality_data:
            findings["functionality"] = {
                "specification_analysis": functionality_data.get('specification_analysis', {}),
                "task_completion": functionality_data.get('task_completion', {}),
                "feature_gaps": functionality_data.get('feature_gaps', [])
            }
        
        # Code quality findings
        if code_quality_data:
            findings["code_quality"] = {
                "metrics": code_quality_data.get('metrics', {}),
                "technical_debt_items": code_quality_data.get('technical_debt_items', []),
                "issue_summary": code_quality_data.get('issue_summary', {})
            }
        
        # Test coverage findings
        if test_coverage_data:
            findings["test_coverage"] = {
                "overall_coverage": self._extract_coverage_summary(test_coverage_data),
                "module_coverage": self._extract_module_coverage(test_coverage_data),
                "test_failures": test_coverage_data.get('test_failures', [])
            }
        
        # Documentation findings
        if documentation_data:
            findings["documentation"] = {
                "overall_score": documentation_data.get('overall_score', 0),
                "api_coverage": documentation_data.get('api_coverage', 0),
                "gaps": documentation_data.get('gaps', [])
            }
        
        # Cleanup findings
        if cleanup_data:
            findings["cleanup"] = {
                "file_analysis": cleanup_data.get('file_analysis', {}),
                "cleanup_opportunities": cleanup_data.get('cleanup_opportunities', [])
            }
        
        return findings
    
    def _extract_coverage_summary(self, test_coverage_data: Dict) -> Dict[str, Any]:
        """Extract test coverage summary"""
        total_statements = 0
        covered_statements = 0
        files = test_coverage_data.get('files', {})
        
        for file_data in files.values():
            summary = file_data.get('summary', {})
            total_statements += summary.get('num_statements', 0)
            covered_statements += summary.get('covered_lines', 0)
        
        coverage_percentage = (covered_statements / total_statements * 100) if total_statements > 0 else 0
        
        return {
            "total_lines": total_statements,
            "covered_lines": covered_statements,
            "coverage_percentage": coverage_percentage
        }
    
    def _extract_module_coverage(self, test_coverage_data: Dict) -> Dict[str, Any]:
        """Extract module-level coverage data"""
        module_coverage = {}
        files = test_coverage_data.get('files', {})
        
        # Group files by module
        modules = {}
        for file_path, file_data in files.items():
            if file_path.startswith("src/"):
                path_obj = Path(file_path)
                path_parts = path_obj.parts
                
                if len(path_parts) >= 4:
                    module = path_parts[2]  # e.g., 'analysis', 'github', etc.
                elif len(path_parts) >= 3:
                    module = "core"
                else:
                    module = "root"
                
                if module not in modules:
                    modules[module] = {"total": 0, "covered": 0}
                
                summary = file_data.get('summary', {})
                modules[module]["total"] += summary.get('num_statements', 0)
                modules[module]["covered"] += summary.get('covered_lines', 0)
        
        # Calculate coverage percentages
        for module, data in modules.items():
            if data["total"] > 0:
                coverage = (data["covered"] / data["total"]) * 100
                module_coverage[module] = {
                    "coverage_percentage": coverage,
                    "total_lines": data["total"],
                    "covered_lines": data["covered"]
                }
        
        return module_coverage
    
    def _generate_header(self, report: ProjectHealthReport) -> str:
        """Generate report header"""
        return f"""# {report.project_name} Project Health Report

**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}  
**Overall Health:** {report.metrics.health_status}  
**Health Score:** {report.metrics.overall_health_score:.1f}/100

---"""
    
    def _generate_executive_summary_section(self, report: ProjectHealthReport) -> str:
        """Generate executive summary section"""
        return f"""## Executive Summary

{report.executive_summary}

### Health Metrics Overview

| Category | Score | Status |
|----------|-------|--------|
| **Functionality** | {report.metrics.functionality_score:.1f}% | {self._get_status_icon(report.metrics.functionality_score)} |
| **Code Quality** | {report.metrics.code_quality_score:.1f}% | {self._get_status_icon(report.metrics.code_quality_score)} |
| **Test Coverage** | {report.metrics.test_coverage_score:.1f}% | {self._get_status_icon(report.metrics.test_coverage_score)} |
| **Documentation** | {report.metrics.documentation_score:.1f}% | {self._get_status_icon(report.metrics.documentation_score)} |
| **Project Cleanup** | {report.metrics.cleanup_score:.1f}% | {self._get_status_icon(report.metrics.cleanup_score)} |
| **Overall Health** | **{report.metrics.overall_health_score:.1f}%** | **{self._get_status_icon(report.metrics.overall_health_score)}** |"""
    
    def _generate_health_metrics_section(self, report: ProjectHealthReport) -> str:
        """Generate detailed health metrics section"""
        sections = ["## Detailed Health Metrics\n"]
        
        metrics = report.metrics
        
        sections.append("### Functionality Assessment")
        sections.append(f"**Score: {metrics.functionality_score:.1f}/100**\n")
        if metrics.functionality_score >= 85:
            sections.append("✅ **Status:** Core functionality is complete and operational")
        elif metrics.functionality_score >= 70:
            sections.append("🟡 **Status:** Most functionality complete with some gaps")
        else:
            sections.append("🔴 **Status:** Significant functionality gaps blocking core workflows")
        sections.append("")
        
        sections.append("### Code Quality Assessment")
        sections.append(f"**Score: {metrics.code_quality_score:.1f}/100**\n")
        if metrics.code_quality_score >= 80:
            sections.append("✅ **Status:** Well-maintained codebase with minimal technical debt")
        elif metrics.code_quality_score >= 60:
            sections.append("🟡 **Status:** Moderate technical debt, manageable with focused effort")
        else:
            sections.append("🔴 **Status:** High technical debt requiring immediate attention")
        sections.append("")
        
        sections.append("### Test Coverage Assessment")
        sections.append(f"**Score: {metrics.test_coverage_score:.1f}/100**\n")
        if metrics.test_coverage_score >= 90:
            sections.append("✅ **Status:** Excellent test coverage providing high confidence")
        elif metrics.test_coverage_score >= 80:
            sections.append("🟡 **Status:** Good coverage with room for improvement")
        else:
            sections.append("🔴 **Status:** Insufficient testing increases risk of bugs")
        sections.append("")
        
        sections.append("### Documentation Assessment")
        sections.append(f"**Score: {metrics.documentation_score:.1f}/100**\n")
        if metrics.documentation_score >= 80:
            sections.append("✅ **Status:** Comprehensive documentation supporting users and contributors")
        elif metrics.documentation_score >= 60:
            sections.append("🟡 **Status:** Adequate documentation with some gaps")
        else:
            sections.append("🔴 **Status:** Documentation gaps hinder user adoption and contribution")
        
        return "\n".join(sections)
    
    def _generate_critical_issues_section(self, report: ProjectHealthReport) -> str:
        """Generate critical issues section"""
        if not report.critical_issues:
            return """## Critical Issues

✅ **No critical issues identified.** The project is in stable condition with no blocking problems."""
        
        sections = [f"## Critical Issues\n"]
        sections.append(f"🔴 **{len(report.critical_issues)} critical issues** require immediate attention:\n")
        
        for i, issue in enumerate(report.critical_issues, 1):
            sections.append(f"### {i}. {issue.title}")
            sections.append(f"**Category:** {issue.category.title()}")
            sections.append(f"**Priority:** {issue.priority.upper()}")
            sections.append(f"**Estimated Effort:** {issue.estimated_effort.title()}")
            sections.append("")
            sections.append(f"**Description:** {issue.description}")
            sections.append("")
            sections.append(f"**Impact:** {issue.impact}")
            sections.append("")
            if issue.files_affected:
                sections.append(f"**Files Affected:** {len(issue.files_affected)} files")
                sections.append("")
        
        return "\n".join(sections)
    
    def _generate_quick_wins_section(self, report: ProjectHealthReport) -> str:
        """Generate quick wins section"""
        if not report.quick_wins:
            return """## Quick Wins

No immediate quick wins identified. Focus on addressing critical issues first."""
        
        total_hours = sum(win.effort_hours for win in report.quick_wins)
        
        sections = [f"## Quick Wins\n"]
        sections.append(f"🚀 **{len(report.quick_wins)} quick wins** available for immediate impact ({total_hours} hours total effort):\n")
        
        for i, win in enumerate(report.quick_wins, 1):
            sections.append(f"### {i}. {win.title}")
            sections.append(f"**Effort:** {win.effort_hours} hours")
            sections.append(f"**Category:** {win.category.title()}")
            sections.append("")
            sections.append(f"**Description:** {win.description}")
            sections.append("")
            sections.append(f"**Impact:** {win.impact_description}")
            sections.append("")
            if win.implementation_steps:
                sections.append("**Implementation Steps:**")
                for step in win.implementation_steps:
                    sections.append(f"- {step}")
                sections.append("")
        
        return "\n".join(sections)
    
    def _generate_prioritized_actions_section(self, report: ProjectHealthReport) -> str:
        """Generate prioritized actions section"""
        if not report.prioritized_actions:
            return """## Prioritized Action Items

No specific action items identified at this time."""
        
        sections = [f"## Prioritized Action Items\n"]
        sections.append(f"📋 **{len(report.prioritized_actions)} action items** prioritized by impact and urgency:\n")
        
        # Group by priority
        priority_groups = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        for action in report.prioritized_actions:
            priority_groups[action.priority].append(action)
        
        priority_labels = {
            "critical": "🔴 Critical Priority",
            "high": "🟠 High Priority", 
            "medium": "🟡 Medium Priority",
            "low": "🟢 Low Priority"
        }
        
        for priority, actions in priority_groups.items():
            if not actions:
                continue
                
            sections.append(f"### {priority_labels[priority]}\n")
            
            for i, action in enumerate(actions, 1):
                sections.append(f"#### {i}. {action.title}")
                sections.append(f"**Category:** {action.category.title()}")
                sections.append(f"**Effort:** {action.effort_estimate.title()}")
                sections.append(f"**Impact:** {action.impact_level.title()}")
                sections.append("")
                sections.append(f"**Description:** {action.description}")
                sections.append("")
                
                if action.implementation_steps:
                    sections.append("**Implementation Steps:**")
                    for step in action.implementation_steps:
                        sections.append(f"- {step}")
                    sections.append("")
                
                if action.success_criteria:
                    sections.append("**Success Criteria:**")
                    for criterion in action.success_criteria:
                        sections.append(f"- {criterion}")
                    sections.append("")
                
                if action.dependencies:
                    sections.append("**Dependencies:**")
                    for dependency in action.dependencies:
                        sections.append(f"- {dependency}")
                    sections.append("")
        
        return "\n".join(sections)
    
    def _generate_implementation_roadmap_section(self, report: ProjectHealthReport) -> str:
        """Generate implementation roadmap section"""
        sections = ["## Implementation Roadmap\n"]
        sections.append("📅 **Phased approach** for systematic project improvement:\n")
        
        for phase, actions in report.implementation_roadmap.items():
            if not actions:
                continue
                
            sections.append(f"### {phase}")
            sections.append(f"**Actions:** {len(actions)} items")
            
            # Calculate phase effort
            effort_hours = {
                "small": 8,
                "medium": 24,
                "large": 60
            }
            
            total_hours = sum(effort_hours.get(action.effort_estimate, 24) for action in actions)
            sections.append(f"**Estimated Effort:** {total_hours} hours")
            sections.append("")
            
            for action in actions:
                sections.append(f"- **{action.title}** ({action.effort_estimate} effort)")
            sections.append("")
        
        return "\n".join(sections)
    
    def _generate_resource_estimates_section(self, report: ProjectHealthReport) -> str:
        """Generate resource estimates section"""
        sections = ["## Resource Estimates\n"]
        sections.append("💰 **Development effort estimates** by category:\n")
        
        sections.append("| Category | Hours | Percentage |")
        sections.append("|----------|-------|------------|")
        
        total_hours = report.resource_estimates.get("total", 0)
        
        for category, hours in report.resource_estimates.items():
            if category == "total":
                continue
            percentage = (hours / total_hours * 100) if total_hours > 0 else 0
            sections.append(f"| {category.title()} | {hours} | {percentage:.1f}% |")
        
        sections.append(f"| **Total** | **{total_hours}** | **100%** |")
        sections.append("")
        
        # Convert to weeks/months
        hours_per_week = 40
        weeks = total_hours / hours_per_week
        months = weeks / 4
        
        sections.append(f"**Timeline Estimates:**")
        sections.append(f"- **Full-time equivalent:** {weeks:.1f} weeks ({months:.1f} months)")
        sections.append(f"- **Part-time (20h/week):** {weeks*2:.1f} weeks ({months*2:.1f} months)")
        sections.append(f"- **Spare time (10h/week):** {weeks*4:.1f} weeks ({months*4:.1f} months)")
        
        return "\n".join(sections)
    
    def _generate_detailed_findings_section(self, report: ProjectHealthReport) -> str:
        """Generate detailed findings section"""
        sections = ["## Detailed Findings\n"]
        
        for category, findings in report.detailed_findings.items():
            sections.append(f"### {category.title()} Details\n")
            
            if category == "functionality":
                spec_analysis = findings.get("specification_analysis", {})
                sections.append(f"- **Total Tasks:** {spec_analysis.get('total_tasks', 0)}")
                sections.append(f"- **Incomplete Tasks:** {spec_analysis.get('incomplete_tasks', 0)}")
                sections.append(f"- **Completion Rate:** {spec_analysis.get('completion_percentage', 0):.1f}%")
                
            elif category == "code_quality":
                metrics = findings.get("metrics", {})
                sections.append(f"- **Total Files:** {metrics.get('total_files', 0)}")
                sections.append(f"- **Lines of Code:** {metrics.get('total_lines', 0):,}")
                sections.append(f"- **Average Complexity:** {metrics.get('average_complexity', 0):.2f}")
                sections.append(f"- **Technical Debt Score:** {metrics.get('technical_debt_score', 0):.2f}/4.0")
                
            elif category == "test_coverage":
                coverage = findings.get("overall_coverage", {})
                sections.append(f"- **Total Lines:** {coverage.get('total_lines', 0):,}")
                sections.append(f"- **Covered Lines:** {coverage.get('covered_lines', 0):,}")
                sections.append(f"- **Coverage Percentage:** {coverage.get('coverage_percentage', 0):.1f}%")
                
            elif category == "documentation":
                sections.append(f"- **Overall Score:** {findings.get('overall_score', 0):.1f}/100")
                sections.append(f"- **API Coverage:** {findings.get('api_coverage', 0):.1f}%")
                
            elif category == "cleanup":
                file_analysis = findings.get("file_analysis", {})
                sections.append(f"- **Unused Files:** {file_analysis.get('unused_files', 0)}")
                sections.append(f"- **Temporary Files:** {file_analysis.get('temporary_files', 0)}")
            
            sections.append("")
        
        return "\n".join(sections)
    
    def _generate_appendix_section(self, report: ProjectHealthReport) -> str:
        """Generate appendix section"""
        return f"""## Appendix

### Methodology

This comprehensive health report was generated by analyzing multiple aspects of the {report.project_name} project:

1. **Functionality Assessment** - Analysis of specification completeness and task completion rates
2. **Code Quality Analysis** - Static code analysis for complexity, maintainability, and technical debt
3. **Test Coverage Evaluation** - Analysis of test coverage metrics and quality
4. **Documentation Review** - Assessment of documentation completeness and accuracy
5. **Project Cleanup Analysis** - Identification of unused files and cleanup opportunities

### Scoring Methodology

- **Overall Health Score** is calculated as a weighted average:
  - Functionality: 35%
  - Code Quality: 25% 
  - Test Coverage: 20%
  - Documentation: 15%
  - Project Cleanup: 5%

### Health Status Definitions

- **🟢 EXCELLENT (85-100):** Project is in excellent condition with minimal issues
- **🟡 GOOD (70-84):** Project is in good condition with minor improvements needed
- **🟠 NEEDS ATTENTION (50-69):** Project has significant issues requiring focused attention
- **🔴 CRITICAL (0-49):** Project has critical issues that must be addressed immediately

### Report Generation

- **Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
- **Generator Version:** 1.0
- **Analysis Scope:** Complete project codebase and documentation"""
    
    def _get_status_icon(self, score: float) -> str:
        """Get status icon for score"""
        if score >= 85:
            return "🟢 Excellent"
        elif score >= 70:
            return "🟡 Good"
        elif score >= 50:
            return "🟠 Needs Attention"
        else:
            return "🔴 Critical"
    
    def save_report(self, report: ProjectHealthReport, output_path: str, format: str = "markdown") -> None:
        """Save project health report to file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == "json":
            content = self.generate_json_report(report)
        else:
            content = self.generate_markdown_report(report)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.logger.info(f"Project health report saved to {output_path}")