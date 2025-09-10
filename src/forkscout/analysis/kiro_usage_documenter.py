"""
Kiro Usage Documentation System

This module provides automated analysis and documentation of Kiro's contributions
to the codebase, including spec evolution analysis, steering rules impact assessment,
and contribution quantification.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

import yaml


@dataclass
class SpecEvolution:
    """Represents the evolution of a single spec"""
    spec_name: str
    creation_date: Optional[datetime]
    last_modified: Optional[datetime]
    requirements_count: int
    design_sections: List[str]
    tasks_count: int
    completed_tasks: int
    in_progress_tasks: int
    not_started_tasks: int
    completion_percentage: float
    key_features: List[str]
    complexity_score: int


@dataclass
class SteeringRuleImpact:
    """Represents the impact of steering rules on development"""
    rule_name: str
    file_path: str
    creation_date: Optional[datetime]
    last_modified: Optional[datetime]
    content_length: int
    key_guidelines: List[str]
    affected_components: List[str]
    usage_examples: List[str]
    impact_score: int


@dataclass
class KiroContribution:
    """Represents Kiro's contribution to a specific component"""
    component_name: str
    file_path: str
    total_lines: int
    kiro_generated_lines: int
    kiro_assisted_lines: int
    human_written_lines: int
    contribution_percentage: float
    development_method: str  # "spec-driven", "direct-generation", "collaborative"
    quality_indicators: Dict[str, Any]


@dataclass
class SpecEvolutionReport:
    """Complete report on spec evolution"""
    total_specs: int
    active_specs: int
    completed_specs: int
    spec_timeline: List[SpecEvolution]
    feature_to_spec_mapping: Dict[str, str]
    iterative_development_examples: List[str]
    development_velocity_metrics: Dict[str, float]


@dataclass
class SteeringRulesReport:
    """Complete report on steering rules impact"""
    total_rules: int
    active_rules: int
    rule_impacts: List[SteeringRuleImpact]
    code_quality_improvements: List[str]
    testing_strategy_influence: List[str]
    architecture_decisions: List[str]
    development_consistency_metrics: Dict[str, float]


@dataclass
class KiroContributionReport:
    """Complete report on Kiro's contributions"""
    total_lines_of_code: int
    kiro_generated_lines: int
    kiro_assisted_lines: int
    manually_written_lines: int
    overall_contribution_percentage: float
    feature_breakdown: Dict[str, KiroContribution]
    spec_driven_components: List[str]
    development_velocity_impact: Dict[str, float]
    quality_improvements: List[str]


class KiroUsageDocumenter:
    """
    Automated analysis and documentation of Kiro usage throughout development.
    
    This class analyzes spec files, steering rules, and codebase to quantify
    and document Kiro's contributions to the project.
    """
    
    def __init__(self, project_root: Path = None):
        """Initialize the documenter with project root path."""
        self.project_root = project_root or Path.cwd()
        self.specs_dir = self.project_root / ".kiro" / "specs"
        self.steering_dir = self.project_root / ".kiro" / "steering"
        self.src_dir = self.project_root / "src"
        
    def analyze_spec_evolution(self) -> SpecEvolutionReport:
        """
        Analyze how specs evolved during development.
        
        Returns:
            SpecEvolutionReport: Complete analysis of spec evolution
        """
        if not self.specs_dir.exists():
            return SpecEvolutionReport(
                total_specs=0,
                active_specs=0,
                completed_specs=0,
                spec_timeline=[],
                feature_to_spec_mapping={},
                iterative_development_examples=[],
                development_velocity_metrics={}
            )
        
        spec_evolutions = []
        feature_mapping = {}
        
        for spec_dir in self.specs_dir.iterdir():
            if spec_dir.is_dir():
                evolution = self._analyze_single_spec(spec_dir)
                if evolution:
                    spec_evolutions.append(evolution)
                    
                    # Map features to specs
                    for feature in evolution.key_features:
                        feature_mapping[feature] = evolution.spec_name
        
        # Sort by creation date
        spec_evolutions.sort(key=lambda x: x.creation_date or datetime.min)
        
        # Calculate metrics
        total_specs = len(spec_evolutions)
        completed_specs = sum(1 for s in spec_evolutions if s.completion_percentage >= 100)
        active_specs = sum(1 for s in spec_evolutions if 0 < s.completion_percentage < 100)
        
        # Generate development examples
        examples = self._generate_iterative_examples(spec_evolutions)
        
        # Calculate velocity metrics
        velocity_metrics = self._calculate_development_velocity(spec_evolutions)
        
        return SpecEvolutionReport(
            total_specs=total_specs,
            active_specs=active_specs,
            completed_specs=completed_specs,
            spec_timeline=spec_evolutions,
            feature_to_spec_mapping=feature_mapping,
            iterative_development_examples=examples,
            development_velocity_metrics=velocity_metrics
        )
    
    def document_steering_rules_impact(self) -> SteeringRulesReport:
        """
        Document how steering rules guided development practices.
        
        Returns:
            SteeringRulesReport: Complete analysis of steering rules impact
        """
        if not self.steering_dir.exists():
            return SteeringRulesReport(
                total_rules=0,
                active_rules=0,
                rule_impacts=[],
                code_quality_improvements=[],
                testing_strategy_influence=[],
                architecture_decisions=[],
                development_consistency_metrics={}
            )
        
        rule_impacts = []
        
        for rule_file in self.steering_dir.glob("*.md"):
            impact = self._analyze_steering_rule(rule_file)
            if impact:
                rule_impacts.append(impact)
        
        # Categorize impacts
        quality_improvements = self._extract_quality_improvements(rule_impacts)
        testing_influence = self._extract_testing_influence(rule_impacts)
        architecture_decisions = self._extract_architecture_decisions(rule_impacts)
        
        # Calculate consistency metrics
        consistency_metrics = self._calculate_consistency_metrics(rule_impacts)
        
        return SteeringRulesReport(
            total_rules=len(rule_impacts),
            active_rules=len([r for r in rule_impacts if r.impact_score > 0]),
            rule_impacts=rule_impacts,
            code_quality_improvements=quality_improvements,
            testing_strategy_influence=testing_influence,
            architecture_decisions=architecture_decisions,
            development_consistency_metrics=consistency_metrics
        )
    
    def extract_kiro_contributions(self) -> KiroContributionReport:
        """
        Extract and quantify Kiro's contributions to the codebase.
        
        Returns:
            KiroContributionReport: Complete analysis of Kiro contributions
        """
        contributions = {}
        total_lines = 0
        kiro_generated = 0
        kiro_assisted = 0
        manually_written = 0
        
        # Analyze Python source files
        for py_file in self.src_dir.rglob("*.py"):
            if py_file.is_file():
                contribution = self._analyze_file_contribution(py_file)
                if contribution:
                    contributions[contribution.component_name] = contribution
                    total_lines += contribution.total_lines
                    kiro_generated += contribution.kiro_generated_lines
                    kiro_assisted += contribution.kiro_assisted_lines
                    manually_written += contribution.human_written_lines
        
        # Calculate overall percentage
        overall_percentage = (
            (kiro_generated + kiro_assisted) / total_lines * 100
            if total_lines > 0 else 0
        )
        
        # Identify spec-driven components
        spec_driven = self._identify_spec_driven_components(contributions)
        
        # Calculate velocity impact
        velocity_impact = self._calculate_velocity_impact(contributions)
        
        # Extract quality improvements
        quality_improvements = self._extract_quality_improvements_from_code(contributions)
        
        return KiroContributionReport(
            total_lines_of_code=total_lines,
            kiro_generated_lines=kiro_generated,
            kiro_assisted_lines=kiro_assisted,
            manually_written_lines=manually_written,
            overall_contribution_percentage=overall_percentage,
            feature_breakdown=contributions,
            spec_driven_components=spec_driven,
            development_velocity_impact=velocity_impact,
            quality_improvements=quality_improvements
        )
    
    def _analyze_single_spec(self, spec_dir: Path) -> Optional[SpecEvolution]:
        """Analyze a single spec directory."""
        try:
            spec_name = spec_dir.name
            
            # Get file timestamps
            creation_date = None
            last_modified = None
            
            requirements_file = spec_dir / "requirements.md"
            design_file = spec_dir / "design.md"
            tasks_file = spec_dir / "tasks.md"
            
            if requirements_file.exists():
                stat = requirements_file.stat()
                creation_date = datetime.fromtimestamp(stat.st_ctime)
                last_modified = datetime.fromtimestamp(stat.st_mtime)
            
            # Analyze requirements
            requirements_count = 0
            if requirements_file.exists():
                content = requirements_file.read_text(encoding='utf-8')
                requirements_count = len(re.findall(r'### Requirement \d+', content))
            
            # Analyze design sections
            design_sections = []
            if design_file.exists():
                content = design_file.read_text(encoding='utf-8')
                design_sections = re.findall(r'## ([^#\n]+)', content)
            
            # Analyze tasks
            tasks_count = 0
            completed_tasks = 0
            in_progress_tasks = 0
            not_started_tasks = 0
            
            if tasks_file.exists():
                content = tasks_file.read_text(encoding='utf-8')
                
                # Count different task statuses
                completed_tasks = len(re.findall(r'- \[x\]', content))
                in_progress_tasks = len(re.findall(r'- \[-\]', content))
                not_started_tasks = len(re.findall(r'- \[ \]', content))
                
                tasks_count = completed_tasks + in_progress_tasks + not_started_tasks
            
            # Calculate completion percentage
            completion_percentage = (
                (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0
            )
            
            # Extract key features
            key_features = self._extract_key_features(spec_dir)
            
            # Calculate complexity score
            complexity_score = self._calculate_spec_complexity(
                requirements_count, len(design_sections), tasks_count
            )
            
            return SpecEvolution(
                spec_name=spec_name,
                creation_date=creation_date,
                last_modified=last_modified,
                requirements_count=requirements_count,
                design_sections=design_sections,
                tasks_count=tasks_count,
                completed_tasks=completed_tasks,
                in_progress_tasks=in_progress_tasks,
                not_started_tasks=not_started_tasks,
                completion_percentage=completion_percentage,
                key_features=key_features,
                complexity_score=complexity_score
            )
            
        except Exception as e:
            print(f"Error analyzing spec {spec_dir.name}: {e}")
            return None
    
    def _analyze_steering_rule(self, rule_file: Path) -> Optional[SteeringRuleImpact]:
        """Analyze a single steering rule file."""
        try:
            rule_name = rule_file.stem
            
            # Get file info
            stat = rule_file.stat()
            creation_date = datetime.fromtimestamp(stat.st_ctime)
            last_modified = datetime.fromtimestamp(stat.st_mtime)
            
            content = rule_file.read_text(encoding='utf-8')
            content_length = len(content)
            
            # Extract key guidelines
            key_guidelines = self._extract_guidelines(content)
            
            # Identify affected components
            affected_components = self._identify_affected_components(content)
            
            # Extract usage examples
            usage_examples = self._extract_usage_examples(content)
            
            # Calculate impact score
            impact_score = self._calculate_impact_score(
                content_length, len(key_guidelines), len(affected_components)
            )
            
            return SteeringRuleImpact(
                rule_name=rule_name,
                file_path=str(rule_file.relative_to(self.project_root)),
                creation_date=creation_date,
                last_modified=last_modified,
                content_length=content_length,
                key_guidelines=key_guidelines,
                affected_components=affected_components,
                usage_examples=usage_examples,
                impact_score=impact_score
            )
            
        except Exception as e:
            print(f"Error analyzing steering rule {rule_file.name}: {e}")
            return None
    
    def _analyze_file_contribution(self, file_path: Path) -> Optional[KiroContribution]:
        """Analyze Kiro's contribution to a specific file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            total_lines = len([line for line in lines if line.strip()])
            
            # Analyze contribution patterns
            kiro_generated = self._count_kiro_generated_lines(content)
            kiro_assisted = self._count_kiro_assisted_lines(content)
            human_written = total_lines - kiro_generated - kiro_assisted
            
            # Calculate contribution percentage
            contribution_percentage = (
                (kiro_generated + kiro_assisted) / total_lines * 100
                if total_lines > 0 else 0
            )
            
            # Determine development method
            development_method = self._determine_development_method(file_path, content)
            
            # Calculate quality indicators
            quality_indicators = self._calculate_quality_indicators(content)
            
            component_name = self._get_component_name(file_path)
            
            return KiroContribution(
                component_name=component_name,
                file_path=str(file_path.relative_to(self.project_root)),
                total_lines=total_lines,
                kiro_generated_lines=kiro_generated,
                kiro_assisted_lines=kiro_assisted,
                human_written_lines=human_written,
                contribution_percentage=contribution_percentage,
                development_method=development_method,
                quality_indicators=quality_indicators
            )
            
        except Exception as e:
            print(f"Error analyzing file {file_path}: {e}")
            return None
    
    def _extract_key_features(self, spec_dir: Path) -> List[str]:
        """Extract key features from spec files."""
        features = []
        
        # Check requirements file for user stories
        requirements_file = spec_dir / "requirements.md"
        if requirements_file.exists():
            content = requirements_file.read_text(encoding='utf-8')
            # Extract user stories
            user_stories = re.findall(r'\*\*User Story:\*\* (.+?)(?=\n|$)', content)
            features.extend([story.split(',')[0] for story in user_stories[:3]])  # Top 3
        
        # Check design file for main components
        design_file = spec_dir / "design.md"
        if design_file.exists():
            content = design_file.read_text(encoding='utf-8')
            # Extract component names
            components = re.findall(r'### (\d+\.\d+\s+[^#\n]+)', content)
            features.extend([comp.split()[-1] for comp in components[:2]])  # Top 2
        
        return features[:5]  # Limit to 5 key features
    
    def _calculate_spec_complexity(self, requirements: int, design_sections: int, tasks: int) -> int:
        """Calculate complexity score for a spec."""
        return min(100, (requirements * 2) + (design_sections * 3) + (tasks * 1))
    
    def _extract_guidelines(self, content: str) -> List[str]:
        """Extract key guidelines from steering rule content."""
        guidelines = []
        
        # Look for bullet points and numbered lists
        bullet_points = re.findall(r'^[-*]\s+(.+)$', content, re.MULTILINE)
        numbered_points = re.findall(r'^\d+\.\s+(.+)$', content, re.MULTILINE)
        
        guidelines.extend(bullet_points[:3])  # Top 3 bullet points
        guidelines.extend(numbered_points[:2])  # Top 2 numbered points
        
        return [g.strip() for g in guidelines if len(g.strip()) > 10][:5]
    
    def _identify_affected_components(self, content: str) -> List[str]:
        """Identify components affected by steering rules."""
        components = []
        
        # Look for code patterns, file references, and class names
        file_refs = re.findall(r'`([^`]+\.py)`', content)
        class_refs = re.findall(r'`([A-Z][a-zA-Z]+)`', content)
        
        components.extend(file_refs[:3])
        components.extend(class_refs[:3])
        
        return list(set(components))[:5]
    
    def _extract_usage_examples(self, content: str) -> List[str]:
        """Extract usage examples from steering rules."""
        examples = []
        
        # Look for code blocks
        code_blocks = re.findall(r'```(?:python)?\n(.*?)\n```', content, re.DOTALL)
        examples.extend([block.strip()[:100] + "..." if len(block) > 100 else block.strip() 
                        for block in code_blocks[:3]])
        
        return examples
    
    def _calculate_impact_score(self, content_length: int, guidelines: int, components: int) -> int:
        """Calculate impact score for steering rules."""
        base_score = min(50, content_length // 100)  # Length factor
        guideline_score = guidelines * 5  # Guidelines factor
        component_score = components * 3  # Components factor
        
        return min(100, base_score + guideline_score + component_score)
    
    def _count_kiro_generated_lines(self, content: str) -> int:
        """Count lines that appear to be Kiro-generated."""
        lines = content.split('\n')
        kiro_patterns = [
            r'""".*?"""',  # Comprehensive docstrings
            r'@dataclass',  # Dataclass usage
            r'from typing import',  # Type hints
            r'async def',  # Async patterns
            r'raise \w+Error',  # Proper exception handling
        ]
        
        kiro_lines = 0
        for line in lines:
            if any(re.search(pattern, line) for pattern in kiro_patterns):
                kiro_lines += 1
        
        return min(kiro_lines, len(lines) // 2)  # Cap at 50% of file
    
    def _count_kiro_assisted_lines(self, content: str) -> int:
        """Count lines that appear to be Kiro-assisted."""
        lines = content.split('\n')
        assisted_patterns = [
            r'# TODO:',  # TODO comments
            r'# FIXME:',  # FIXME comments
            r'logger\.',  # Logging usage
            r'pytest\.',  # Test patterns
            r'assert ',  # Assertions
        ]
        
        assisted_lines = 0
        for line in lines:
            if any(re.search(pattern, line) for pattern in assisted_patterns):
                assisted_lines += 1
        
        return min(assisted_lines, len(lines) // 4)  # Cap at 25% of file
    
    def _determine_development_method(self, file_path: Path, content: str) -> str:
        """Determine how the file was developed."""
        # Check if file is related to specs
        if any(spec in str(file_path) for spec in ["analysis", "models", "services"]):
            return "spec-driven"
        
        # Check for comprehensive patterns
        if len(re.findall(r'""".*?"""', content, re.DOTALL)) > 2:
            return "direct-generation"
        
        return "collaborative"
    
    def _calculate_quality_indicators(self, content: str) -> Dict[str, Any]:
        """Calculate quality indicators for code."""
        return {
            "has_docstrings": len(re.findall(r'""".*?"""', content, re.DOTALL)) > 0,
            "has_type_hints": "from typing import" in content,
            "has_error_handling": "except " in content,
            "has_tests": "test_" in content or "Test" in content,
            "complexity_score": min(100, len(content.split('\n')) // 10)
        }
    
    def _get_component_name(self, file_path: Path) -> str:
        """Get component name from file path."""
        return file_path.stem.replace('_', ' ').title()
    
    def _generate_iterative_examples(self, spec_evolutions: List[SpecEvolution]) -> List[str]:
        """Generate examples of iterative development."""
        examples = []
        
        for spec in spec_evolutions[:3]:  # Top 3 specs
            if spec.completion_percentage > 50:
                example = f"The {spec.spec_name} spec evolved through {spec.requirements_count} requirements and {spec.tasks_count} tasks, achieving {spec.completion_percentage:.1f}% completion"
                examples.append(example)
        
        return examples
    
    def _calculate_development_velocity(self, spec_evolutions: List[SpecEvolution]) -> Dict[str, float]:
        """Calculate development velocity metrics."""
        if not spec_evolutions:
            return {}
        
        total_tasks = sum(s.tasks_count for s in spec_evolutions)
        completed_tasks = sum(s.completed_tasks for s in spec_evolutions)
        
        return {
            "average_completion_rate": sum(s.completion_percentage for s in spec_evolutions) / len(spec_evolutions),
            "total_task_completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "average_spec_complexity": sum(s.complexity_score for s in spec_evolutions) / len(spec_evolutions)
        }
    
    def _extract_quality_improvements(self, rule_impacts: List[SteeringRuleImpact]) -> List[str]:
        """Extract code quality improvements from steering rules."""
        improvements = []
        
        quality_rules = [r for r in rule_impacts if "quality" in r.rule_name.lower() or "code" in r.rule_name.lower()]
        for rule in quality_rules[:3]:
            improvements.extend(rule.key_guidelines[:2])
        
        return improvements[:5]
    
    def _extract_testing_influence(self, rule_impacts: List[SteeringRuleImpact]) -> List[str]:
        """Extract testing strategy influence from steering rules."""
        testing_influence = []
        
        testing_rules = [r for r in rule_impacts if "test" in r.rule_name.lower() or "tdd" in r.rule_name.lower()]
        for rule in testing_rules[:3]:
            testing_influence.extend(rule.key_guidelines[:2])
        
        return testing_influence[:5]
    
    def _extract_architecture_decisions(self, rule_impacts: List[SteeringRuleImpact]) -> List[str]:
        """Extract architecture decisions from steering rules."""
        decisions = []
        
        arch_rules = [r for r in rule_impacts if any(term in r.rule_name.lower() 
                     for term in ["structure", "api", "performance", "security"])]
        for rule in arch_rules[:3]:
            decisions.extend(rule.key_guidelines[:2])
        
        return decisions[:5]
    
    def _calculate_consistency_metrics(self, rule_impacts: List[SteeringRuleImpact]) -> Dict[str, float]:
        """Calculate development consistency metrics."""
        if not rule_impacts:
            return {}
        
        total_impact = sum(r.impact_score for r in rule_impacts)
        active_rules = len([r for r in rule_impacts if r.impact_score > 0])
        
        return {
            "average_rule_impact": total_impact / len(rule_impacts),
            "active_rules_percentage": (active_rules / len(rule_impacts) * 100),
            "consistency_score": min(100, total_impact / len(rule_impacts))
        }
    
    def _identify_spec_driven_components(self, contributions: Dict[str, KiroContribution]) -> List[str]:
        """Identify components developed using spec-driven approach."""
        return [name for name, contrib in contributions.items() 
                if contrib.development_method == "spec-driven"]
    
    def _calculate_velocity_impact(self, contributions: Dict[str, KiroContribution]) -> Dict[str, float]:
        """Calculate development velocity impact."""
        if not contributions:
            return {}
        
        total_contribution = sum(c.contribution_percentage for c in contributions.values())
        avg_contribution = total_contribution / len(contributions)
        
        return {
            "average_kiro_contribution": avg_contribution,
            "velocity_multiplier": 1 + (avg_contribution / 100),
            "development_acceleration": avg_contribution * 1.5  # Estimated acceleration
        }
    
    def _extract_quality_improvements_from_code(self, contributions: Dict[str, KiroContribution]) -> List[str]:
        """Extract quality improvements from code analysis."""
        improvements = []
        
        for contrib in contributions.values():
            if contrib.quality_indicators.get("has_docstrings"):
                improvements.append(f"Comprehensive documentation in {contrib.component_name}")
            if contrib.quality_indicators.get("has_type_hints"):
                improvements.append(f"Type safety in {contrib.component_name}")
            if contrib.quality_indicators.get("has_error_handling"):
                improvements.append(f"Robust error handling in {contrib.component_name}")
        
        return improvements[:10]
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate a comprehensive report of all Kiro usage analysis."""
        spec_report = self.analyze_spec_evolution()
        steering_report = self.document_steering_rules_impact()
        contribution_report = self.extract_kiro_contributions()
        
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "spec_evolution": self._serialize_for_json(asdict(spec_report)),
            "steering_rules_impact": self._serialize_for_json(asdict(steering_report)),
            "kiro_contributions": self._serialize_for_json(asdict(contribution_report)),
            "summary": {
                "total_specs": spec_report.total_specs,
                "total_steering_rules": steering_report.total_rules,
                "overall_kiro_contribution": contribution_report.overall_contribution_percentage,
                "development_method": "Spec-driven development with AI assistance",
                "key_achievements": [
                    f"{spec_report.completed_specs} completed specs out of {spec_report.total_specs}",
                    f"{steering_report.active_rules} active steering rules",
                    f"{contribution_report.overall_contribution_percentage:.1f}% Kiro contribution to codebase"
                ]
            }
        }
    
    def _serialize_for_json(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable format."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._serialize_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return self._serialize_for_json(obj.__dict__)
        else:
            return obj
    
    def save_report_to_file(self, output_path: Path = None) -> Path:
        """Save the comprehensive report to a JSON file."""
        if output_path is None:
            output_path = self.project_root / "kiro_usage_analysis.json"
        
        report = self.generate_comprehensive_report()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return output_path