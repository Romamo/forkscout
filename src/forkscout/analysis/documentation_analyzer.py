"""
Documentation completeness and accuracy analyzer for the Forkscout project.

This module provides comprehensive analysis of documentation coverage,
accuracy, and quality across the entire project.
"""

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class DocstringInfo:
    """Information about a function or class docstring."""
    name: str
    type: str  # 'function', 'class', 'method'
    has_docstring: bool
    docstring_length: int
    has_parameters: bool
    has_return_type: bool
    has_examples: bool
    file_path: str
    line_number: int


@dataclass
class FileDocumentation:
    """Documentation analysis for a single file."""
    file_path: str
    total_functions: int = 0
    documented_functions: int = 0
    total_classes: int = 0
    documented_classes: int = 0
    total_methods: int = 0
    documented_methods: int = 0
    docstrings: List[DocstringInfo] = field(default_factory=list)
    
    @property
    def function_coverage(self) -> float:
        """Calculate function documentation coverage percentage."""
        if self.total_functions == 0:
            return 100.0
        return (self.documented_functions / self.total_functions) * 100
    
    @property
    def class_coverage(self) -> float:
        """Calculate class documentation coverage percentage."""
        if self.total_classes == 0:
            return 100.0
        return (self.documented_classes / self.total_classes) * 100
    
    @property
    def method_coverage(self) -> float:
        """Calculate method documentation coverage percentage."""
        if self.total_methods == 0:
            return 100.0
        return (self.documented_methods / self.total_methods) * 100
    
    @property
    def overall_coverage(self) -> float:
        """Calculate overall documentation coverage percentage."""
        total_items = self.total_functions + self.total_classes + self.total_methods
        if total_items == 0:
            return 100.0
        documented_items = self.documented_functions + self.documented_classes + self.documented_methods
        return (documented_items / total_items) * 100


@dataclass
class DocumentationGap:
    """Represents a gap in documentation."""
    type: str  # 'missing_docstring', 'outdated_example', 'broken_link', 'missing_section'
    severity: str  # 'critical', 'high', 'medium', 'low'
    file_path: str
    line_number: Optional[int]
    description: str
    suggestion: str


@dataclass
class DocumentationAssessment:
    """Complete documentation assessment results."""
    readme_assessment: Dict[str, any]
    api_documentation: Dict[str, FileDocumentation]
    user_guide_assessment: Dict[str, any]
    contributor_docs_assessment: Dict[str, any]
    example_validation: Dict[str, any]
    documentation_gaps: List[DocumentationGap]
    overall_score: float
    recommendations: List[str]


class DocumentationAnalyzer:
    """Analyzes documentation completeness and accuracy across the project."""
    
    def __init__(self, project_root: str = "."):
        """Initialize the documentation analyzer.
        
        Args:
            project_root: Root directory of the project to analyze
        """
        self.project_root = Path(project_root)
        self.source_dirs = ["src", "forkscout"]  # Common source directories
        self.doc_files = ["README.md", "DEVELOPMENT.md", "CONTRIBUTING.md"]
        self.config_files = [".env.example", "pyproject.toml", "requirements.txt"]
        
    def analyze_documentation(self) -> DocumentationAssessment:
        """Perform comprehensive documentation analysis.
        
        Returns:
            Complete documentation assessment results
        """
        logger.info("Starting comprehensive documentation analysis")
        
        # Analyze different documentation aspects
        readme_assessment = self._analyze_readme()
        api_documentation = self._analyze_api_documentation()
        user_guide_assessment = self._analyze_user_guides()
        contributor_docs_assessment = self._analyze_contributor_documentation()
        example_validation = self._validate_examples()
        
        # Identify documentation gaps
        documentation_gaps = self._identify_documentation_gaps(
            readme_assessment, api_documentation, user_guide_assessment,
            contributor_docs_assessment, example_validation
        )
        
        # Calculate overall score and generate recommendations
        overall_score = self._calculate_overall_score(
            readme_assessment, api_documentation, user_guide_assessment,
            contributor_docs_assessment, example_validation
        )
        
        recommendations = self._generate_recommendations(documentation_gaps, overall_score)
        
        return DocumentationAssessment(
            readme_assessment=readme_assessment,
            api_documentation=api_documentation,
            user_guide_assessment=user_guide_assessment,
            contributor_docs_assessment=contributor_docs_assessment,
            example_validation=example_validation,
            documentation_gaps=documentation_gaps,
            overall_score=overall_score,
            recommendations=recommendations
        )
    
    def _analyze_readme(self) -> Dict[str, any]:
        """Analyze README completeness and accuracy."""
        readme_path = self.project_root / "README.md"
        
        assessment = {
            "exists": readme_path.exists(),
            "sections": {},
            "accuracy_issues": [],
            "completeness_score": 0.0,
            "accuracy_score": 0.0
        }
        
        if not readme_path.exists():
            assessment["completeness_score"] = 0.0
            assessment["accuracy_score"] = 0.0
            return assessment
        
        try:
            content = readme_path.read_text(encoding='utf-8')
            
            # Check for essential sections
            essential_sections = {
                "title": r"^#\s+",
                "description": r"description|overview|about",
                "installation": r"install|setup",
                "usage": r"usage|quick start|getting started",
                "examples": r"example|demo",
                "configuration": r"config|settings",
                "troubleshooting": r"troubleshoot|common issues|faq",
                "contributing": r"contribut|development",
                "license": r"license"
            }
            
            for section, pattern in essential_sections.items():
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    assessment["sections"][section] = True
                else:
                    assessment["sections"][section] = False
            
            # Check for accuracy issues
            accuracy_issues = []
            
            # Check for outdated installation instructions
            if "pip install" in content and "uv" not in content:
                accuracy_issues.append("Installation instructions may be outdated - project uses uv")
            
            # Check for broken internal links
            internal_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
            for link_text, link_url in internal_links:
                if not link_url.startswith(('http', 'mailto')):
                    # Internal link - check if file exists
                    link_path = self.project_root / link_url.lstrip('./')
                    if not link_path.exists():
                        accuracy_issues.append(f"Broken internal link: {link_url}")
            
            # Check for outdated command examples
            if "python" in content and "uv run" not in content:
                accuracy_issues.append("Command examples may be outdated - should use 'uv run'")
            
            assessment["accuracy_issues"] = accuracy_issues
            
            # Calculate scores
            total_sections = len(essential_sections)
            present_sections = sum(assessment["sections"].values())
            assessment["completeness_score"] = (present_sections / total_sections) * 100
            
            # Accuracy score based on issues found
            max_accuracy_issues = 10  # Arbitrary max for scoring
            accuracy_penalty = min(len(accuracy_issues), max_accuracy_issues) * 10
            assessment["accuracy_score"] = max(0, 100 - accuracy_penalty)
            
        except Exception as e:
            logger.error(f"Error analyzing README: {e}")
            assessment["completeness_score"] = 0.0
            assessment["accuracy_score"] = 0.0
        
        return assessment
    
    def _analyze_api_documentation(self) -> Dict[str, FileDocumentation]:
        """Analyze API documentation coverage for functions and classes."""
        api_docs = {}
        
        # Find all Python files in source directories
        python_files = []
        for source_dir in self.source_dirs:
            source_path = self.project_root / source_dir
            if source_path.exists():
                python_files.extend(source_path.rglob("*.py"))
        
        for py_file in python_files:
            try:
                file_doc = self._analyze_python_file(py_file)
                relative_path = str(py_file.relative_to(self.project_root))
                api_docs[relative_path] = file_doc
            except Exception as e:
                logger.warning(f"Error analyzing {py_file}: {e}")
        
        return api_docs
    
    def _analyze_python_file(self, file_path: Path) -> FileDocumentation:
        """Analyze documentation in a single Python file."""
        file_doc = FileDocumentation(file_path=str(file_path))
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith('_') and not node.name.startswith('__'):
                        # Skip private functions for now
                        continue
                    
                    file_doc.total_functions += 1
                    docstring_info = self._extract_docstring_info(node, 'function', str(file_path))
                    file_doc.docstrings.append(docstring_info)
                    
                    if docstring_info.has_docstring:
                        file_doc.documented_functions += 1
                
                elif isinstance(node, ast.ClassDef):
                    file_doc.total_classes += 1
                    docstring_info = self._extract_docstring_info(node, 'class', str(file_path))
                    file_doc.docstrings.append(docstring_info)
                    
                    if docstring_info.has_docstring:
                        file_doc.documented_classes += 1
                    
                    # Analyze methods in the class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if item.name.startswith('_') and not item.name.startswith('__'):
                                # Skip private methods for now
                                continue
                            
                            file_doc.total_methods += 1
                            method_docstring_info = self._extract_docstring_info(
                                item, 'method', str(file_path)
                            )
                            file_doc.docstrings.append(method_docstring_info)
                            
                            if method_docstring_info.has_docstring:
                                file_doc.documented_methods += 1
        
        except Exception as e:
            logger.warning(f"Error parsing {file_path}: {e}")
        
        return file_doc
    
    def _extract_docstring_info(self, node: ast.AST, node_type: str, file_path: str) -> DocstringInfo:
        """Extract docstring information from an AST node."""
        docstring = ast.get_docstring(node)
        has_docstring = docstring is not None
        docstring_length = len(docstring) if docstring else 0
        
        # Check for parameter documentation
        has_parameters = False
        has_return_type = False
        has_examples = False
        
        if docstring:
            docstring_lower = docstring.lower()
            has_parameters = any(keyword in docstring_lower for keyword in ['args:', 'arguments:', 'parameters:', 'param'])
            has_return_type = any(keyword in docstring_lower for keyword in ['returns:', 'return:', 'yields:'])
            has_examples = any(keyword in docstring_lower for keyword in ['example:', 'examples:', '>>>', 'usage:'])
        
        return DocstringInfo(
            name=getattr(node, 'name', 'unknown'),
            type=node_type,
            has_docstring=has_docstring,
            docstring_length=docstring_length,
            has_parameters=has_parameters,
            has_return_type=has_return_type,
            has_examples=has_examples,
            file_path=file_path,
            line_number=getattr(node, 'lineno', 0)
        )
    
    def _analyze_user_guides(self) -> Dict[str, any]:
        """Analyze user guide documentation accuracy and completeness."""
        assessment = {
            "guides_found": [],
            "accuracy_issues": [],
            "completeness_issues": [],
            "score": 0.0
        }
        
        # Check docs directory
        docs_dir = self.project_root / "docs"
        if docs_dir.exists():
            guide_files = list(docs_dir.glob("*.md"))
            assessment["guides_found"] = [str(f.relative_to(self.project_root)) for f in guide_files]
        
        # Check for specific user guides
        expected_guides = [
            "docs/USAGE.md",
            "docs/TROUBLESHOOTING.md", 
            "docs/CONFIGURATION.md",
            "docs/EXAMPLES.md"
        ]
        
        missing_guides = []
        for guide in expected_guides:
            if not (self.project_root / guide).exists():
                missing_guides.append(guide)
        
        assessment["completeness_issues"] = missing_guides
        
        # Calculate score based on available guides and issues
        total_expected = len(expected_guides)
        available_guides = total_expected - len(missing_guides)
        assessment["score"] = (available_guides / total_expected) * 100 if total_expected > 0 else 0
        
        return assessment
    
    def _analyze_contributor_documentation(self) -> Dict[str, any]:
        """Analyze contributor documentation and development setup instructions."""
        assessment = {
            "contributing_file": False,
            "development_file": False,
            "setup_instructions": False,
            "testing_instructions": False,
            "code_style_guidelines": False,
            "pr_guidelines": False,
            "score": 0.0,
            "issues": []
        }
        
        # Check for CONTRIBUTING.md
        contributing_path = self.project_root / "CONTRIBUTING.md"
        if contributing_path.exists():
            assessment["contributing_file"] = True
            try:
                content = contributing_path.read_text(encoding='utf-8')
                if re.search(r'pull request|pr', content, re.IGNORECASE):
                    assessment["pr_guidelines"] = True
                if re.search(r'test|testing', content, re.IGNORECASE):
                    assessment["testing_instructions"] = True
                if re.search(r'style|format|lint', content, re.IGNORECASE):
                    assessment["code_style_guidelines"] = True
            except Exception as e:
                logger.warning(f"Error reading CONTRIBUTING.md: {e}")
        else:
            assessment["issues"].append("Missing CONTRIBUTING.md file")
        
        # Check for DEVELOPMENT.md
        development_path = self.project_root / "DEVELOPMENT.md"
        if development_path.exists():
            assessment["development_file"] = True
            try:
                content = development_path.read_text(encoding='utf-8')
                if re.search(r'setup|install|environment', content, re.IGNORECASE):
                    assessment["setup_instructions"] = True
            except Exception as e:
                logger.warning(f"Error reading DEVELOPMENT.md: {e}")
        else:
            assessment["issues"].append("Missing DEVELOPMENT.md file")
        
        # Check README for development instructions
        readme_path = self.project_root / "README.md"
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding='utf-8')
                if re.search(r'development|contributing|setup.*dev', content, re.IGNORECASE):
                    assessment["setup_instructions"] = True
                if re.search(r'test|testing|pytest', content, re.IGNORECASE):
                    assessment["testing_instructions"] = True
            except Exception as e:
                logger.warning(f"Error reading README.md: {e}")
        
        # Calculate score
        criteria = [
            assessment["contributing_file"],
            assessment["development_file"], 
            assessment["setup_instructions"],
            assessment["testing_instructions"],
            assessment["code_style_guidelines"],
            assessment["pr_guidelines"]
        ]
        assessment["score"] = (sum(criteria) / len(criteria)) * 100
        
        return assessment
    
    def _validate_examples(self) -> Dict[str, any]:
        """Validate example code and configuration templates."""
        assessment = {
            "config_examples": {},
            "code_examples": {},
            "validation_issues": [],
            "score": 0.0
        }
        
        # Check .env.example
        env_example_path = self.project_root / ".env.example"
        if env_example_path.exists():
            assessment["config_examples"][".env.example"] = {
                "exists": True,
                "issues": []
            }
            
            try:
                content = env_example_path.read_text(encoding='utf-8')
                
                # Check for required environment variables
                required_vars = ["GITHUB_TOKEN"]
                for var in required_vars:
                    if var not in content:
                        assessment["config_examples"][".env.example"]["issues"].append(
                            f"Missing required variable: {var}"
                        )
                
                # Check for placeholder values
                if "your_" not in content.lower():
                    assessment["config_examples"][".env.example"]["issues"].append(
                        "No placeholder values found - may contain real secrets"
                    )
                    
            except Exception as e:
                assessment["config_examples"][".env.example"]["issues"].append(f"Read error: {e}")
        else:
            assessment["config_examples"][".env.example"] = {
                "exists": False,
                "issues": ["File does not exist"]
            }
        
        # Check for example configuration files
        config_files = ["forkscout.yaml", "forkscout.example.yaml", "config.example.yaml"]
        for config_file in config_files:
            config_path = self.project_root / config_file
            if config_path.exists():
                assessment["config_examples"][config_file] = {
                    "exists": True,
                    "issues": []
                }
                # Could add YAML validation here
        
        # Check README for code examples
        readme_path = self.project_root / "README.md"
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding='utf-8')
                
                # Find code blocks
                code_blocks = re.findall(r'```(?:bash|python|yaml|json)?\n(.*?)\n```', content, re.DOTALL)
                assessment["code_examples"]["readme_blocks"] = len(code_blocks)
                
                # Check for outdated command patterns
                for block in code_blocks:
                    if "python " in block and "uv run" not in block:
                        assessment["validation_issues"].append(
                            "README contains outdated Python command examples"
                        )
                        break
                
            except Exception as e:
                assessment["validation_issues"].append(f"Error validating README examples: {e}")
        
        # Calculate score
        total_checks = len(assessment["config_examples"]) + 1  # +1 for code examples
        passed_checks = sum(
            1 for config in assessment["config_examples"].values() 
            if config["exists"] and not config["issues"]
        )
        
        if assessment["code_examples"].get("readme_blocks", 0) > 0:
            passed_checks += 1
        
        assessment["score"] = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        return assessment
    
    def _identify_documentation_gaps(self, readme_assessment: Dict, api_docs: Dict, 
                                   user_guides: Dict, contributor_docs: Dict, 
                                   examples: Dict) -> List[DocumentationGap]:
        """Identify specific documentation gaps and issues."""
        gaps = []
        
        # README gaps
        if not readme_assessment["exists"]:
            gaps.append(DocumentationGap(
                type="missing_file",
                severity="critical",
                file_path="README.md",
                line_number=None,
                description="README.md file is missing",
                suggestion="Create a comprehensive README.md with project overview, installation, and usage instructions"
            ))
        else:
            for section, present in readme_assessment["sections"].items():
                if not present:
                    gaps.append(DocumentationGap(
                        type="missing_section",
                        severity="high" if section in ["installation", "usage"] else "medium",
                        file_path="README.md",
                        line_number=None,
                        description=f"Missing {section} section in README",
                        suggestion=f"Add a {section} section to README.md"
                    ))
        
        # API documentation gaps
        for file_path, file_doc in api_docs.items():
            if file_doc.overall_coverage < 50:
                gaps.append(DocumentationGap(
                    type="low_api_coverage",
                    severity="high",
                    file_path=file_path,
                    line_number=None,
                    description=f"Low API documentation coverage ({file_doc.overall_coverage:.1f}%)",
                    suggestion="Add docstrings to public functions and classes"
                ))
            
            # Identify specific undocumented items
            for docstring_info in file_doc.docstrings:
                if not docstring_info.has_docstring and not docstring_info.name.startswith('_'):
                    gaps.append(DocumentationGap(
                        type="missing_docstring",
                        severity="medium",
                        file_path=file_path,
                        line_number=docstring_info.line_number,
                        description=f"Missing docstring for {docstring_info.type} '{docstring_info.name}'",
                        suggestion=f"Add docstring to {docstring_info.type} '{docstring_info.name}'"
                    ))
        
        # User guide gaps
        for missing_guide in user_guides.get("completeness_issues", []):
            gaps.append(DocumentationGap(
                type="missing_file",
                severity="medium",
                file_path=missing_guide,
                line_number=None,
                description=f"Missing user guide: {missing_guide}",
                suggestion=f"Create {missing_guide} with relevant user documentation"
            ))
        
        # Contributor documentation gaps
        for issue in contributor_docs.get("issues", []):
            gaps.append(DocumentationGap(
                type="missing_file",
                severity="medium",
                file_path="",
                line_number=None,
                description=issue,
                suggestion="Create missing contributor documentation file"
            ))
        
        # Example validation gaps
        for issue in examples.get("validation_issues", []):
            gaps.append(DocumentationGap(
                type="outdated_example",
                severity="medium",
                file_path="README.md",
                line_number=None,
                description=issue,
                suggestion="Update examples to use current best practices"
            ))
        
        return gaps
    
    def _calculate_overall_score(self, readme_assessment: Dict, api_docs: Dict,
                               user_guides: Dict, contributor_docs: Dict,
                               examples: Dict) -> float:
        """Calculate overall documentation score."""
        weights = {
            "readme": 0.3,
            "api": 0.3,
            "user_guides": 0.2,
            "contributor": 0.1,
            "examples": 0.1
        }
        
        # README score (average of completeness and accuracy)
        readme_score = (readme_assessment["completeness_score"] + readme_assessment["accuracy_score"]) / 2
        
        # API documentation score (average coverage across all files)
        if api_docs:
            api_scores = [doc.overall_coverage for doc in api_docs.values()]
            api_score = sum(api_scores) / len(api_scores)
        else:
            api_score = 0.0
        
        # User guides score
        user_guides_score = user_guides["score"]
        
        # Contributor documentation score
        contributor_score = contributor_docs["score"]
        
        # Examples score
        examples_score = examples["score"]
        
        # Calculate weighted average
        overall_score = (
            readme_score * weights["readme"] +
            api_score * weights["api"] +
            user_guides_score * weights["user_guides"] +
            contributor_score * weights["contributor"] +
            examples_score * weights["examples"]
        )
        
        return round(overall_score, 1)
    
    def _generate_recommendations(self, gaps: List[DocumentationGap], overall_score: float) -> List[str]:
        """Generate prioritized recommendations for documentation improvement."""
        recommendations = []
        
        # Critical issues first
        critical_gaps = [gap for gap in gaps if gap.severity == "critical"]
        if critical_gaps:
            recommendations.append("🔴 CRITICAL: Address missing essential documentation files")
            for gap in critical_gaps:
                recommendations.append(f"  - {gap.suggestion}")
        
        # High priority issues
        high_gaps = [gap for gap in gaps if gap.severity == "high"]
        if high_gaps:
            recommendations.append("🟠 HIGH PRIORITY: Improve core documentation coverage")
            # Group by type for better organization
            gap_types = {}
            for gap in high_gaps:
                if gap.type not in gap_types:
                    gap_types[gap.type] = []
                gap_types[gap.type].append(gap)
            
            for gap_type, type_gaps in gap_types.items():
                if gap_type == "low_api_coverage":
                    recommendations.append(f"  - Add docstrings to {len(type_gaps)} files with low API coverage")
                elif gap_type == "missing_section":
                    sections = [gap.description.split("Missing ")[1].split(" section")[0] for gap in type_gaps]
                    recommendations.append(f"  - Add missing README sections: {', '.join(sections)}")
        
        # Medium priority issues
        medium_gaps = [gap for gap in gaps if gap.severity == "medium"]
        if medium_gaps and len(medium_gaps) > 5:
            recommendations.append(f"🟡 MEDIUM PRIORITY: Address {len(medium_gaps)} documentation gaps")
            recommendations.append("  - Focus on missing docstrings for public APIs")
            recommendations.append("  - Update outdated examples and configurations")
            recommendations.append("  - Create missing user guide documents")
        
        # Overall recommendations based on score
        if overall_score < 50:
            recommendations.append("📈 IMPROVEMENT PLAN: Documentation needs significant improvement")
            recommendations.append("  - Start with README completeness and accuracy")
            recommendations.append("  - Add docstrings to all public APIs")
            recommendations.append("  - Create essential user guides")
        elif overall_score < 75:
            recommendations.append("📈 IMPROVEMENT PLAN: Good foundation, focus on coverage gaps")
            recommendations.append("  - Improve API documentation coverage")
            recommendations.append("  - Update examples to current best practices")
            recommendations.append("  - Add missing contributor guidelines")
        else:
            recommendations.append("✅ MAINTENANCE: Documentation is in good shape")
            recommendations.append("  - Address remaining minor gaps")
            recommendations.append("  - Keep examples and configurations up to date")
            recommendations.append("  - Consider adding advanced user guides")
        
        return recommendations