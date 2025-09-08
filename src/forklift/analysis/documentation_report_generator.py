"""
Documentation assessment report generator for the Forklift project.

This module generates comprehensive reports about documentation completeness,
accuracy, and quality across the entire project.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .documentation_analyzer import DocumentationAssessment, DocumentationGap, FileDocumentation


class DocumentationReportGenerator:
    """Generates comprehensive documentation assessment reports."""
    
    def __init__(self):
        """Initialize the documentation report generator."""
        pass
    
    def generate_markdown_report(self, assessment: DocumentationAssessment) -> str:
        """Generate a comprehensive markdown report of documentation assessment.
        
        Args:
            assessment: Complete documentation assessment results
            
        Returns:
            Formatted markdown report string
        """
        report_lines = []
        
        # Header
        report_lines.extend([
            "# Documentation Completeness Assessment Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Overall Score:** {assessment.overall_score}/100",
            "",
            self._get_score_badge(assessment.overall_score),
            ""
        ])
        
        # Executive Summary
        report_lines.extend([
            "## Executive Summary",
            "",
            self._generate_executive_summary(assessment),
            ""
        ])
        
        # README Assessment
        report_lines.extend([
            "## README Assessment",
            "",
            self._generate_readme_section(assessment.readme_assessment),
            ""
        ])
        
        # API Documentation Coverage
        report_lines.extend([
            "## API Documentation Coverage",
            "",
            self._generate_api_documentation_section(assessment.api_documentation),
            ""
        ])
        
        # User Guide Assessment
        report_lines.extend([
            "## User Guide Assessment",
            "",
            self._generate_user_guide_section(assessment.user_guide_assessment),
            ""
        ])
        
        # Contributor Documentation
        report_lines.extend([
            "## Contributor Documentation Assessment",
            "",
            self._generate_contributor_docs_section(assessment.contributor_docs_assessment),
            ""
        ])
        
        # Example Validation
        report_lines.extend([
            "## Example and Configuration Validation",
            "",
            self._generate_example_validation_section(assessment.example_validation),
            ""
        ])
        
        # Documentation Gaps
        report_lines.extend([
            "## Documentation Gaps and Issues",
            "",
            self._generate_gaps_section(assessment.documentation_gaps),
            ""
        ])
        
        # Recommendations
        report_lines.extend([
            "## Recommendations",
            "",
            self._generate_recommendations_section(assessment.recommendations),
            ""
        ])
        
        # Detailed Findings
        report_lines.extend([
            "## Detailed Findings",
            "",
            self._generate_detailed_findings(assessment),
            ""
        ])
        
        return "\n".join(report_lines)
    
    def generate_json_report(self, assessment: DocumentationAssessment) -> str:
        """Generate a JSON report of documentation assessment.
        
        Args:
            assessment: Complete documentation assessment results
            
        Returns:
            JSON formatted report string
        """
        # Convert assessment to JSON-serializable format
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "overall_score": assessment.overall_score,
            "readme_assessment": assessment.readme_assessment,
            "api_documentation": {
                path: {
                    "file_path": doc.file_path,
                    "total_functions": doc.total_functions,
                    "documented_functions": doc.documented_functions,
                    "total_classes": doc.total_classes,
                    "documented_classes": doc.documented_classes,
                    "total_methods": doc.total_methods,
                    "documented_methods": doc.documented_methods,
                    "function_coverage": doc.function_coverage,
                    "class_coverage": doc.class_coverage,
                    "method_coverage": doc.method_coverage,
                    "overall_coverage": doc.overall_coverage,
                    "docstrings": [
                        {
                            "name": ds.name,
                            "type": ds.type,
                            "has_docstring": ds.has_docstring,
                            "docstring_length": ds.docstring_length,
                            "has_parameters": ds.has_parameters,
                            "has_return_type": ds.has_return_type,
                            "has_examples": ds.has_examples,
                            "line_number": ds.line_number
                        }
                        for ds in doc.docstrings
                    ]
                }
                for path, doc in assessment.api_documentation.items()
            },
            "user_guide_assessment": assessment.user_guide_assessment,
            "contributor_docs_assessment": assessment.contributor_docs_assessment,
            "example_validation": assessment.example_validation,
            "documentation_gaps": [
                {
                    "type": gap.type,
                    "severity": gap.severity,
                    "file_path": gap.file_path,
                    "line_number": gap.line_number,
                    "description": gap.description,
                    "suggestion": gap.suggestion
                }
                for gap in assessment.documentation_gaps
            ],
            "recommendations": assessment.recommendations
        }
        
        return json.dumps(report_data, indent=2, default=str)
    
    def _get_score_badge(self, score: float) -> str:
        """Get a visual badge for the overall score."""
        if score >= 90:
            return "🟢 **Excellent** (90-100)"
        elif score >= 75:
            return "🟡 **Good** (75-89)"
        elif score >= 50:
            return "🟠 **Needs Improvement** (50-74)"
        else:
            return "🔴 **Poor** (0-49)"
    
    def _generate_executive_summary(self, assessment: DocumentationAssessment) -> str:
        """Generate executive summary section."""
        lines = []
        
        # Overall assessment
        if assessment.overall_score >= 75:
            lines.append("✅ **Overall Status:** Documentation is in good condition with minor gaps to address.")
        elif assessment.overall_score >= 50:
            lines.append("⚠️ **Overall Status:** Documentation needs improvement in several key areas.")
        else:
            lines.append("❌ **Overall Status:** Documentation requires significant improvement across multiple areas.")
        
        lines.append("")
        
        # Key metrics
        api_files = len(assessment.api_documentation)
        if api_files > 0:
            avg_api_coverage = sum(doc.overall_coverage for doc in assessment.api_documentation.values()) / api_files
            lines.append(f"- **API Documentation Coverage:** {avg_api_coverage:.1f}% across {api_files} files")
        
        lines.append(f"- **README Completeness:** {assessment.readme_assessment['completeness_score']:.1f}%")
        lines.append(f"- **README Accuracy:** {assessment.readme_assessment['accuracy_score']:.1f}%")
        lines.append(f"- **User Guides Score:** {assessment.user_guide_assessment['score']:.1f}%")
        lines.append(f"- **Contributor Docs Score:** {assessment.contributor_docs_assessment['score']:.1f}%")
        lines.append(f"- **Examples Validation Score:** {assessment.example_validation['score']:.1f}%")
        
        lines.append("")
        
        # Gap summary
        critical_gaps = len([gap for gap in assessment.documentation_gaps if gap.severity == "critical"])
        high_gaps = len([gap for gap in assessment.documentation_gaps if gap.severity == "high"])
        medium_gaps = len([gap for gap in assessment.documentation_gaps if gap.severity == "medium"])
        
        lines.append(f"- **Documentation Gaps:** {critical_gaps} critical, {high_gaps} high priority, {medium_gaps} medium priority")
        
        return "\n".join(lines)
    
    def _generate_readme_section(self, readme_assessment: Dict) -> str:
        """Generate README assessment section."""
        lines = []
        
        if not readme_assessment["exists"]:
            lines.extend([
                "❌ **Status:** README.md file is missing",
                "",
                "**Critical Issue:** The project lacks a README.md file, which is essential for user onboarding and project understanding."
            ])
            return "\n".join(lines)
        
        # Scores
        lines.extend([
            f"**Completeness Score:** {readme_assessment['completeness_score']:.1f}/100",
            f"**Accuracy Score:** {readme_assessment['accuracy_score']:.1f}/100",
            ""
        ])
        
        # Section analysis
        lines.append("### Section Analysis")
        lines.append("")
        lines.append("| Section | Present | Status |")
        lines.append("|---------|---------|--------|")
        
        for section, present in readme_assessment["sections"].items():
            status = "✅" if present else "❌"
            lines.append(f"| {section.title()} | {status} | {'Complete' if present else 'Missing'} |")
        
        lines.append("")
        
        # Accuracy issues
        if readme_assessment["accuracy_issues"]:
            lines.append("### Accuracy Issues")
            lines.append("")
            for issue in readme_assessment["accuracy_issues"]:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_api_documentation_section(self, api_docs: Dict[str, FileDocumentation]) -> str:
        """Generate API documentation coverage section."""
        lines = []
        
        if not api_docs:
            lines.append("❌ **No Python files found for API documentation analysis.**")
            return "\n".join(lines)
        
        # Overall statistics
        total_functions = sum(doc.total_functions for doc in api_docs.values())
        total_classes = sum(doc.total_classes for doc in api_docs.values())
        total_methods = sum(doc.total_methods for doc in api_docs.values())
        
        documented_functions = sum(doc.documented_functions for doc in api_docs.values())
        documented_classes = sum(doc.documented_classes for doc in api_docs.values())
        documented_methods = sum(doc.documented_methods for doc in api_docs.values())
        
        function_coverage = (documented_functions / total_functions * 100) if total_functions > 0 else 100
        class_coverage = (documented_classes / total_classes * 100) if total_classes > 0 else 100
        method_coverage = (documented_methods / total_methods * 100) if total_methods > 0 else 100
        
        lines.extend([
            "### Overall API Documentation Statistics",
            "",
            f"- **Functions:** {documented_functions}/{total_functions} documented ({function_coverage:.1f}%)",
            f"- **Classes:** {documented_classes}/{total_classes} documented ({class_coverage:.1f}%)",
            f"- **Methods:** {documented_methods}/{total_methods} documented ({method_coverage:.1f}%)",
            "",
            "### File-by-File Coverage",
            ""
        ])
        
        # Sort files by coverage (lowest first to highlight issues)
        sorted_files = sorted(api_docs.items(), key=lambda x: x[1].overall_coverage)
        
        lines.append("| File | Functions | Classes | Methods | Overall |")
        lines.append("|------|-----------|---------|---------|---------|")
        
        for file_path, doc in sorted_files:
            # Shorten file path for display
            display_path = file_path.replace("src/forklift/", "").replace("src/", "")
            
            func_status = f"{doc.documented_functions}/{doc.total_functions}" if doc.total_functions > 0 else "N/A"
            class_status = f"{doc.documented_classes}/{doc.total_classes}" if doc.total_classes > 0 else "N/A"
            method_status = f"{doc.documented_methods}/{doc.total_methods}" if doc.total_methods > 0 else "N/A"
            
            coverage_icon = "🔴" if doc.overall_coverage < 50 else "🟡" if doc.overall_coverage < 75 else "🟢"
            
            lines.append(f"| {display_path} | {func_status} | {class_status} | {method_status} | {coverage_icon} {doc.overall_coverage:.1f}% |")
        
        lines.append("")
        
        # Highlight files needing attention
        low_coverage_files = [path for path, doc in api_docs.items() if doc.overall_coverage < 50]
        if low_coverage_files:
            lines.extend([
                "### Files Needing Attention (< 50% coverage)",
                ""
            ])
            for file_path in low_coverage_files[:10]:  # Limit to top 10
                doc = api_docs[file_path]
                display_path = file_path.replace("src/forklift/", "").replace("src/", "")
                lines.append(f"- **{display_path}** ({doc.overall_coverage:.1f}% coverage)")
            
            if len(low_coverage_files) > 10:
                lines.append(f"- ... and {len(low_coverage_files) - 10} more files")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_user_guide_section(self, user_guide_assessment: Dict) -> str:
        """Generate user guide assessment section."""
        lines = []
        
        lines.extend([
            f"**Score:** {user_guide_assessment['score']:.1f}/100",
            ""
        ])
        
        # Found guides
        if user_guide_assessment["guides_found"]:
            lines.append("### Available User Guides")
            lines.append("")
            for guide in user_guide_assessment["guides_found"]:
                lines.append(f"- ✅ {guide}")
            lines.append("")
        
        # Missing guides
        if user_guide_assessment["completeness_issues"]:
            lines.append("### Missing User Guides")
            lines.append("")
            for missing_guide in user_guide_assessment["completeness_issues"]:
                lines.append(f"- ❌ {missing_guide}")
            lines.append("")
        
        # Accuracy issues
        if user_guide_assessment.get("accuracy_issues"):
            lines.append("### Accuracy Issues")
            lines.append("")
            for issue in user_guide_assessment["accuracy_issues"]:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_contributor_docs_section(self, contributor_assessment: Dict) -> str:
        """Generate contributor documentation assessment section."""
        lines = []
        
        lines.extend([
            f"**Score:** {contributor_assessment['score']:.1f}/100",
            "",
            "### Contributor Documentation Checklist",
            ""
        ])
        
        checklist_items = [
            ("Contributing file", contributor_assessment["contributing_file"]),
            ("Development file", contributor_assessment["development_file"]),
            ("Setup instructions", contributor_assessment["setup_instructions"]),
            ("Testing instructions", contributor_assessment["testing_instructions"]),
            ("Code style guidelines", contributor_assessment["code_style_guidelines"]),
            ("PR guidelines", contributor_assessment["pr_guidelines"])
        ]
        
        for item_name, present in checklist_items:
            status = "✅" if present else "❌"
            lines.append(f"- {status} {item_name}")
        
        lines.append("")
        
        # Issues
        if contributor_assessment.get("issues"):
            lines.append("### Issues Found")
            lines.append("")
            for issue in contributor_assessment["issues"]:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_example_validation_section(self, example_validation: Dict) -> str:
        """Generate example validation section."""
        lines = []
        
        lines.extend([
            f"**Score:** {example_validation['score']:.1f}/100",
            ""
        ])
        
        # Configuration examples
        if example_validation["config_examples"]:
            lines.append("### Configuration Examples")
            lines.append("")
            for config_name, config_info in example_validation["config_examples"].items():
                status = "✅" if config_info["exists"] and not config_info["issues"] else "❌"
                lines.append(f"- {status} **{config_name}**")
                
                if config_info["issues"]:
                    for issue in config_info["issues"]:
                        lines.append(f"  - ⚠️ {issue}")
            lines.append("")
        
        # Code examples
        if example_validation["code_examples"]:
            lines.append("### Code Examples")
            lines.append("")
            readme_blocks = example_validation["code_examples"].get("readme_blocks", 0)
            lines.append(f"- **README code blocks:** {readme_blocks}")
            lines.append("")
        
        # Validation issues
        if example_validation["validation_issues"]:
            lines.append("### Validation Issues")
            lines.append("")
            for issue in example_validation["validation_issues"]:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_gaps_section(self, gaps: List[DocumentationGap]) -> str:
        """Generate documentation gaps section."""
        lines = []
        
        if not gaps:
            lines.append("✅ **No significant documentation gaps identified.**")
            return "\n".join(lines)
        
        # Group gaps by severity
        critical_gaps = [gap for gap in gaps if gap.severity == "critical"]
        high_gaps = [gap for gap in gaps if gap.severity == "high"]
        medium_gaps = [gap for gap in gaps if gap.severity == "medium"]
        low_gaps = [gap for gap in gaps if gap.severity == "low"]
        
        # Critical gaps
        if critical_gaps:
            lines.extend([
                "### 🔴 Critical Issues",
                ""
            ])
            for gap in critical_gaps:
                lines.append(f"- **{gap.file_path}**: {gap.description}")
                lines.append(f"  - *Suggestion:* {gap.suggestion}")
            lines.append("")
        
        # High priority gaps
        if high_gaps:
            lines.extend([
                "### 🟠 High Priority Issues",
                ""
            ])
            for gap in high_gaps[:10]:  # Limit display
                file_display = gap.file_path if gap.file_path else "General"
                lines.append(f"- **{file_display}**: {gap.description}")
                if gap.line_number:
                    lines.append(f"  - *Line:* {gap.line_number}")
                lines.append(f"  - *Suggestion:* {gap.suggestion}")
            
            if len(high_gaps) > 10:
                lines.append(f"- ... and {len(high_gaps) - 10} more high priority issues")
            lines.append("")
        
        # Medium priority gaps (summary only)
        if medium_gaps:
            lines.extend([
                f"### 🟡 Medium Priority Issues ({len(medium_gaps)} total)",
                ""
            ])
            
            # Group by type for summary
            gap_types = {}
            for gap in medium_gaps:
                if gap.type not in gap_types:
                    gap_types[gap.type] = 0
                gap_types[gap.type] += 1
            
            for gap_type, count in gap_types.items():
                lines.append(f"- **{gap_type.replace('_', ' ').title()}**: {count} issues")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_recommendations_section(self, recommendations: List[str]) -> str:
        """Generate recommendations section."""
        lines = []
        
        if not recommendations:
            lines.append("✅ **No specific recommendations at this time.**")
            return "\n".join(lines)
        
        for recommendation in recommendations:
            lines.append(recommendation)
        
        return "\n".join(lines)
    
    def _generate_detailed_findings(self, assessment: DocumentationAssessment) -> str:
        """Generate detailed findings section."""
        lines = []
        
        # API Documentation Details
        if assessment.api_documentation:
            lines.extend([
                "### API Documentation Details",
                "",
                "#### Files with Missing Docstrings",
                ""
            ])
            
            missing_docstrings = []
            for file_path, doc in assessment.api_documentation.items():
                for docstring_info in doc.docstrings:
                    if not docstring_info.has_docstring and not docstring_info.name.startswith('_'):
                        missing_docstrings.append((file_path, docstring_info))
            
            if missing_docstrings:
                # Group by file
                by_file = {}
                for file_path, docstring_info in missing_docstrings:
                    if file_path not in by_file:
                        by_file[file_path] = []
                    by_file[file_path].append(docstring_info)
                
                for file_path, docstrings in list(by_file.items())[:10]:  # Limit display
                    display_path = file_path.replace("src/forklift/", "").replace("src/", "")
                    lines.append(f"**{display_path}:**")
                    for ds in docstrings[:5]:  # Limit per file
                        lines.append(f"- {ds.type} `{ds.name}` (line {ds.line_number})")
                    if len(docstrings) > 5:
                        lines.append(f"- ... and {len(docstrings) - 5} more")
                    lines.append("")
                
                if len(by_file) > 10:
                    lines.append(f"*... and {len(by_file) - 10} more files with missing docstrings*")
                    lines.append("")
            else:
                lines.append("✅ All public APIs have docstrings.")
                lines.append("")
        
        return "\n".join(lines)
    
    def save_report(self, assessment: DocumentationAssessment, output_path: str, format: str = "markdown") -> None:
        """Save documentation assessment report to file.
        
        Args:
            assessment: Complete documentation assessment results
            output_path: Path where to save the report
            format: Report format ('markdown' or 'json')
        """
        if format.lower() == "json":
            content = self.generate_json_report(assessment)
        else:
            content = self.generate_markdown_report(assessment)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)