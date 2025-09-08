"""
Optimization Report Generator

Generates comprehensive reports for optimization recommendations including
markdown reports, JSON exports, and implementation roadmaps.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .optimization_recommender import OptimizationReport, Priority, EffortLevel, ImpactLevel, RiskLevel

logger = logging.getLogger(__name__)


class OptimizationReportGenerator:
    """Generates various formats of optimization reports"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_markdown_report(self, report: OptimizationReport, output_path: str) -> None:
        """Generate comprehensive markdown report"""
        self.logger.info(f"Generating markdown optimization report: {output_path}")
        
        content = self._build_markdown_content(report)
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        self.logger.info(f"Markdown report generated: {output_path}")
    
    def generate_json_report(self, report: OptimizationReport, output_path: str) -> None:
        """Generate JSON report for programmatic access"""
        self.logger.info(f"Generating JSON optimization report: {output_path}")
        
        json_data = self._convert_to_json(report)
        
        with open(output_path, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)
        
        self.logger.info(f"JSON report generated: {output_path}")
    
    def generate_implementation_roadmap(self, report: OptimizationReport, output_path: str) -> None:
        """Generate detailed implementation roadmap"""
        self.logger.info(f"Generating implementation roadmap: {output_path}")
        
        content = self._build_roadmap_content(report)
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        self.logger.info(f"Implementation roadmap generated: {output_path}")
    
    def _build_markdown_content(self, report: OptimizationReport) -> str:
        """Build comprehensive markdown report content"""
        content = []
        
        # Header
        content.extend([
            "# Project Optimization Recommendations",
            "",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Project Health Score:** {report.project_health_score:.1f}/100",
            "",
            self._get_health_status_emoji(report.project_health_score),
            "",
        ])
        
        # Executive Summary
        content.extend([
            "## Executive Summary",
            "",
            f"📊 **Total Recommendations:** {report.total_recommendations}",
            f"🔥 **Critical Issues:** {len(report.critical_issues)}",
            f"⚡ **Quick Wins Available:** {len(report.quick_wins)}",
            f"🧹 **Cleanup Opportunities:** {len(report.cleanup_opportunities)}",
            "",
        ])
        
        # Project Health Overview
        content.extend([
            "## Project Health Overview",
            "",
            self._build_health_overview(report),
            "",
        ])
        
        # Critical Issues
        if report.critical_issues:
            content.extend([
                "## 🚨 Critical Issues",
                "",
                "These issues block core functionality and must be addressed immediately:",
                "",
            ])
            
            for issue in report.critical_issues:
                content.extend(self._format_recommendation(issue))
                content.append("")
        
        # Quick Wins
        if report.quick_wins:
            content.extend([
                "## ⚡ Quick Wins",
                "",
                "High-impact, low-effort improvements that can be implemented immediately:",
                "",
            ])
            
            for i, win in enumerate(report.quick_wins, 1):
                content.extend([
                    f"### {i}. {win.title}",
                    "",
                    win.description,
                    "",
                    f"**Effort:** {win.effort_hours} hours",
                    f"**Impact:** {win.impact_description}",
                    "",
                    "**Implementation Steps:**",
                ])
                
                for step in win.implementation_steps:
                    content.append(f"- {step}")
                
                if win.files_to_remove:
                    content.extend([
                        "",
                        "**Files to Remove:**",
                    ])
                    for file in win.files_to_remove:
                        content.append(f"- `{file}`")
                
                content.append("")
        
        # High Priority Recommendations
        if report.high_priority_recommendations:
            content.extend([
                "## 🔴 High Priority Recommendations",
                "",
            ])
            
            for rec in report.high_priority_recommendations:
                content.extend(self._format_recommendation(rec))
                content.append("")
        
        # Medium Priority Recommendations
        if report.medium_priority_recommendations:
            content.extend([
                "## 🟡 Medium Priority Recommendations",
                "",
            ])
            
            for rec in report.medium_priority_recommendations:
                content.extend(self._format_recommendation(rec))
                content.append("")
        
        # Low Priority Recommendations
        if report.low_priority_recommendations:
            content.extend([
                "## 🟢 Low Priority Recommendations",
                "",
            ])
            
            for rec in report.low_priority_recommendations:
                content.extend(self._format_recommendation(rec))
                content.append("")
        
        # Cleanup Opportunities
        if report.cleanup_opportunities:
            content.extend([
                "## 🧹 Cleanup Opportunities",
                "",
                "Specific files and code that can be safely removed:",
                "",
            ])
            
            for opportunity in report.cleanup_opportunities:
                content.append(f"- {opportunity}")
            
            content.append("")
        
        # Implementation Roadmap
        content.extend([
            "## 🗺️ Implementation Roadmap",
            "",
            self._build_roadmap_summary(report),
            "",
        ])
        
        # Resource Estimates
        content.extend([
            "## 📊 Resource Estimates",
            "",
            self._build_resource_estimates(report),
            "",
        ])
        
        # Recommendations by Category
        content.extend([
            "## 📋 Recommendations by Category",
            "",
            self._build_category_breakdown(report),
            "",
        ])
        
        return "\n".join(content)
    
    def _get_health_status_emoji(self, score: float) -> str:
        """Get health status emoji and description"""
        if score >= 90:
            return "🟢 **Excellent** (90-100)"
        elif score >= 75:
            return "🟡 **Good** (75-89)"
        elif score >= 50:
            return "🟠 **Needs Improvement** (50-74)"
        else:
            return "🔴 **Critical** (0-49)"
    
    def _build_health_overview(self, report: OptimizationReport) -> str:
        """Build project health overview section"""
        score = report.project_health_score
        
        lines = [
            f"Current project health score: **{score:.1f}/100**",
            "",
        ]
        
        if score >= 90:
            lines.extend([
                "✅ **Project Status:** Excellent - Minor optimizations recommended",
                "- Focus on low-priority improvements and maintenance",
                "- Consider advanced features and performance optimizations",
            ])
        elif score >= 75:
            lines.extend([
                "✅ **Project Status:** Good - Some improvements needed",
                "- Address medium-priority issues for better maintainability",
                "- Focus on code quality and documentation improvements",
            ])
        elif score >= 50:
            lines.extend([
                "⚠️ **Project Status:** Needs Improvement - Several issues to address",
                "- Prioritize high-impact improvements",
                "- Focus on completing core functionality",
                "- Address technical debt and testing gaps",
            ])
        else:
            lines.extend([
                "🚨 **Project Status:** Critical - Immediate attention required",
                "- Address critical issues blocking core functionality",
                "- Focus on stability and basic feature completion",
                "- Significant refactoring and cleanup needed",
            ])
        
        return "\n".join(lines)
    
    def _format_recommendation(self, rec) -> List[str]:
        """Format a single recommendation"""
        lines = [
            f"### {rec.title}",
            "",
            rec.description,
            "",
            f"**Priority:** {rec.priority.value.title()}",
            f"**Effort:** {rec.effort_estimate.value.title()}",
            f"**Impact:** {rec.impact_estimate.value.title()}",
            f"**Risk:** {rec.risk_level.value.title()}",
            f"**Category:** {rec.category.title()}",
        ]
        
        if rec.estimated_hours:
            lines.append(f"**Estimated Hours:** {rec.estimated_hours}")
        
        lines.extend([
            "",
            "**Implementation Steps:**",
        ])
        
        for step in rec.implementation_steps:
            lines.append(f"- {step}")
        
        lines.extend([
            "",
            "**Success Criteria:**",
        ])
        
        for criteria in rec.success_criteria:
            lines.append(f"- {criteria}")
        
        if rec.dependencies:
            lines.extend([
                "",
                "**Dependencies:**",
            ])
            for dep in rec.dependencies:
                lines.append(f"- {dep}")
        
        if rec.files_affected:
            lines.extend([
                "",
                "**Files Affected:**",
            ])
            for file in rec.files_affected[:5]:  # Limit to first 5
                lines.append(f"- `{file}`")
            if len(rec.files_affected) > 5:
                lines.append(f"- ... and {len(rec.files_affected) - 5} more files")
        
        return lines
    
    def _build_roadmap_summary(self, report: OptimizationReport) -> str:
        """Build implementation roadmap summary"""
        lines = []
        
        for phase, recommendations in report.implementation_roadmap.items():
            if not recommendations:
                continue
            
            lines.extend([
                f"### {phase}",
                "",
                f"**Recommendations:** {len(recommendations)}",
            ])
            
            total_hours = sum(
                rec.estimated_hours or self._estimate_hours_from_effort(rec.effort_estimate)
                for rec in recommendations
            )
            lines.append(f"**Estimated Effort:** {total_hours} hours")
            
            lines.extend([
                "",
                "**Key Items:**",
            ])
            
            for rec in recommendations[:3]:  # Show first 3
                lines.append(f"- {rec.title}")
            
            if len(recommendations) > 3:
                lines.append(f"- ... and {len(recommendations) - 3} more items")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _build_resource_estimates(self, report: OptimizationReport) -> str:
        """Build resource estimates section"""
        lines = [
            "| Category | Hours | Percentage |",
            "|----------|-------|------------|",
        ]
        
        total_hours = report.resource_estimates.get('total', 0)
        
        for category, hours in report.resource_estimates.items():
            if category == 'total':
                continue
            
            percentage = (hours / total_hours * 100) if total_hours > 0 else 0
            lines.append(f"| {category.title()} | {hours} | {percentage:.1f}% |")
        
        lines.extend([
            f"| **Total** | **{total_hours}** | **100.0%** |",
            "",
            f"**Estimated Timeline:** {total_hours // 40} weeks (assuming 40 hours/week)",
        ])
        
        return "\n".join(lines)
    
    def _build_category_breakdown(self, report: OptimizationReport) -> str:
        """Build recommendations breakdown by category"""
        categories = {}
        
        all_recs = (
            report.critical_issues +
            report.high_priority_recommendations +
            report.medium_priority_recommendations +
            report.low_priority_recommendations
        )
        
        for rec in all_recs:
            if rec.category not in categories:
                categories[rec.category] = []
            categories[rec.category].append(rec)
        
        lines = []
        
        for category, recs in categories.items():
            lines.extend([
                f"### {category.title()}",
                "",
                f"**Total Recommendations:** {len(recs)}",
                "",
            ])
            
            priority_counts = {}
            for rec in recs:
                priority = rec.priority.value
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            for priority, count in priority_counts.items():
                lines.append(f"- {priority.title()}: {count}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _build_roadmap_content(self, report: OptimizationReport) -> str:
        """Build detailed implementation roadmap content"""
        content = []
        
        content.extend([
            "# Implementation Roadmap",
            "",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Estimated Effort:** {report.resource_estimates.get('total', 0)} hours",
            "",
            "## Overview",
            "",
            "This roadmap provides a phased approach to implementing the optimization recommendations.",
            "Each phase should be completed before moving to the next to ensure stability and progress.",
            "",
        ])
        
        for phase, recommendations in report.implementation_roadmap.items():
            if not recommendations:
                continue
            
            content.extend([
                f"## {phase}",
                "",
            ])
            
            total_hours = sum(
                rec.estimated_hours or self._estimate_hours_from_effort(rec.effort_estimate)
                for rec in recommendations
            )
            
            content.extend([
                f"**Total Effort:** {total_hours} hours",
                f"**Estimated Duration:** {total_hours // 8} days",
                "",
                "### Recommendations",
                "",
            ])
            
            for i, rec in enumerate(recommendations, 1):
                content.extend([
                    f"#### {i}. {rec.title}",
                    "",
                    f"**Priority:** {rec.priority.value.title()}",
                    f"**Effort:** {rec.effort_estimate.value.title()}",
                    f"**Risk:** {rec.risk_level.value.title()}",
                    "",
                    rec.description,
                    "",
                    "**Implementation Steps:**",
                ])
                
                for step in rec.implementation_steps:
                    content.append(f"- {step}")
                
                content.extend([
                    "",
                    "**Success Criteria:**",
                ])
                
                for criteria in rec.success_criteria:
                    content.append(f"- {criteria}")
                
                content.append("")
        
        return "\n".join(content)
    
    def _convert_to_json(self, report: OptimizationReport) -> Dict:
        """Convert report to JSON-serializable format"""
        return {
            "generated_at": report.generated_at.isoformat(),
            "project_health_score": report.project_health_score,
            "summary": {
                "total_recommendations": report.total_recommendations,
                "critical_issues": len(report.critical_issues),
                "high_priority": len(report.high_priority_recommendations),
                "medium_priority": len(report.medium_priority_recommendations),
                "low_priority": len(report.low_priority_recommendations),
                "quick_wins": len(report.quick_wins),
                "cleanup_opportunities": len(report.cleanup_opportunities)
            },
            "critical_issues": [self._recommendation_to_dict(rec) for rec in report.critical_issues],
            "high_priority_recommendations": [self._recommendation_to_dict(rec) for rec in report.high_priority_recommendations],
            "medium_priority_recommendations": [self._recommendation_to_dict(rec) for rec in report.medium_priority_recommendations],
            "low_priority_recommendations": [self._recommendation_to_dict(rec) for rec in report.low_priority_recommendations],
            "quick_wins": [self._quick_win_to_dict(win) for win in report.quick_wins],
            "cleanup_opportunities": report.cleanup_opportunities,
            "resource_estimates": report.resource_estimates,
            "implementation_roadmap": {
                phase: [self._recommendation_to_dict(rec) for rec in recs]
                for phase, recs in report.implementation_roadmap.items()
            }
        }
    
    def _recommendation_to_dict(self, rec) -> Dict:
        """Convert recommendation to dictionary"""
        return {
            "title": rec.title,
            "description": rec.description,
            "priority": rec.priority.value,
            "effort_estimate": rec.effort_estimate.value,
            "impact_estimate": rec.impact_estimate.value,
            "risk_level": rec.risk_level.value,
            "category": rec.category,
            "implementation_steps": rec.implementation_steps,
            "success_criteria": rec.success_criteria,
            "dependencies": rec.dependencies,
            "files_affected": rec.files_affected,
            "estimated_hours": rec.estimated_hours,
            "priority_score": rec.priority_score
        }
    
    def _quick_win_to_dict(self, win) -> Dict:
        """Convert quick win to dictionary"""
        return {
            "title": win.title,
            "description": win.description,
            "effort_hours": win.effort_hours,
            "impact_description": win.impact_description,
            "implementation_steps": win.implementation_steps,
            "files_to_modify": win.files_to_modify,
            "files_to_remove": win.files_to_remove
        }
    
    def _estimate_hours_from_effort(self, effort: EffortLevel) -> int:
        """Convert effort level to hour estimate"""
        effort_hours = {
            EffortLevel.SMALL: 8,
            EffortLevel.MEDIUM: 16,
            EffortLevel.LARGE: 40
        }
        return effort_hours.get(effort, 16)