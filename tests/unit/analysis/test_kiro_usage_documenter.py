"""
Unit tests for KiroUsageDocumenter
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.forklift.analysis.kiro_usage_documenter import (
    KiroUsageDocumenter,
    SpecEvolution,
    SteeringRuleImpact,
    KiroContribution,
    SpecEvolutionReport,
    SteeringRulesReport,
    KiroContributionReport
)


class TestKiroUsageDocumenter:
    """Test cases for KiroUsageDocumenter class."""
    
    @pytest.fixture
    def documenter(self, tmp_path):
        """Create a KiroUsageDocumenter instance with temporary directory."""
        return KiroUsageDocumenter(project_root=tmp_path)
    
    @pytest.fixture
    def mock_spec_structure(self, tmp_path):
        """Create mock spec directory structure."""
        specs_dir = tmp_path / ".kiro" / "specs"
        specs_dir.mkdir(parents=True)
        
        # Create test spec
        test_spec = specs_dir / "test-feature"
        test_spec.mkdir()
        
        # Create requirements.md
        requirements_content = """# Requirements Document

## Requirements

### Requirement 1
**User Story:** As a user, I want to test features, so that I can verify functionality.

### Requirement 2
**User Story:** As a developer, I want to implement tests, so that I can ensure quality.
"""
        (test_spec / "requirements.md").write_text(requirements_content)
        
        # Create design.md
        design_content = """# Design Document

## Overview
Test design overview

## Architecture
System architecture

## Components
Component details
"""
        (test_spec / "design.md").write_text(design_content)
        
        # Create tasks.md
        tasks_content = """# Tasks

- [x] 1. Completed task
- [-] 2. In progress task
- [ ] 3. Not started task
- [x] 4. Another completed task
"""
        (test_spec / "tasks.md").write_text(tasks_content)
        
        return test_spec
    
    @pytest.fixture
    def mock_steering_structure(self, tmp_path):
        """Create mock steering directory structure."""
        steering_dir = tmp_path / ".kiro" / "steering"
        steering_dir.mkdir(parents=True)
        
        # Create test steering rule
        rule_content = """# Test Driven Development Guidelines

## Core Principles

- Write tests first before implementation
- Use pytest as the primary testing framework
- Maintain high test coverage

## Implementation

```python
def test_example():
    assert True
```

This affects the following components:
- `test_module.py`
- `TestClass`
"""
        (steering_dir / "tdd.md").write_text(rule_content)
        
        return steering_dir
    
    @pytest.fixture
    def mock_src_structure(self, tmp_path):
        """Create mock source directory structure."""
        src_dir = tmp_path / "src" / "forklift"
        src_dir.mkdir(parents=True)
        
        # Create test Python file
        py_content = '''"""
Test module with comprehensive documentation.

This module demonstrates Kiro-generated patterns.
"""

from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class TestClass:
    """Test class with type hints."""
    name: str
    value: Optional[int] = None
    
    async def process(self) -> List[str]:
        """Process data asynchronously."""
        try:
            # TODO: Implement processing logic
            result = []
            logger.info("Processing started")
            return result
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise ProcessingError("Failed to process") from e


def test_example():
    """Test function."""
    assert True
'''
        (src_dir / "test_module.py").write_text(py_content)
        
        return src_dir
    
    def test_init(self, tmp_path):
        """Test KiroUsageDocumenter initialization."""
        documenter = KiroUsageDocumenter(project_root=tmp_path)
        
        assert documenter.project_root == tmp_path
        assert documenter.specs_dir == tmp_path / ".kiro" / "specs"
        assert documenter.steering_dir == tmp_path / ".kiro" / "steering"
        assert documenter.src_dir == tmp_path / "src"
    
    def test_init_default_path(self):
        """Test KiroUsageDocumenter initialization with default path."""
        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/test/path")
            documenter = KiroUsageDocumenter()
            
            assert documenter.project_root == Path("/test/path")
    
    def test_analyze_spec_evolution_no_specs(self, documenter):
        """Test spec evolution analysis with no specs directory."""
        report = documenter.analyze_spec_evolution()
        
        assert isinstance(report, SpecEvolutionReport)
        assert report.total_specs == 0
        assert report.active_specs == 0
        assert report.completed_specs == 0
        assert report.spec_timeline == []
        assert report.feature_to_spec_mapping == {}
    
    def test_analyze_spec_evolution_with_specs(self, documenter, mock_spec_structure):
        """Test spec evolution analysis with mock specs."""
        report = documenter.analyze_spec_evolution()
        
        assert isinstance(report, SpecEvolutionReport)
        assert report.total_specs == 1
        assert len(report.spec_timeline) == 1
        
        spec = report.spec_timeline[0]
        assert spec.spec_name == "test-feature"
        assert spec.requirements_count == 2
        assert spec.tasks_count == 4
        assert spec.completed_tasks == 2
        assert spec.in_progress_tasks == 1
        assert spec.not_started_tasks == 1
        assert spec.completion_percentage == 50.0
    
    def test_analyze_single_spec(self, documenter, mock_spec_structure):
        """Test analysis of a single spec."""
        spec = documenter._analyze_single_spec(mock_spec_structure)
        
        assert isinstance(spec, SpecEvolution)
        assert spec.spec_name == "test-feature"
        assert spec.requirements_count == 2
        assert spec.tasks_count == 4
        assert spec.completed_tasks == 2
        assert spec.completion_percentage == 50.0
        assert len(spec.design_sections) == 3  # Overview, Architecture, Components
    
    def test_analyze_single_spec_error_handling(self, documenter, tmp_path):
        """Test error handling in single spec analysis."""
        # Create invalid spec directory
        invalid_spec = tmp_path / ".kiro" / "specs" / "invalid"
        invalid_spec.mkdir(parents=True)
        
        spec = documenter._analyze_single_spec(invalid_spec)
        
        # Should handle missing files gracefully
        assert spec is not None
        assert spec.spec_name == "invalid"
        assert spec.requirements_count == 0
        assert spec.tasks_count == 0
    
    def test_document_steering_rules_impact_no_rules(self, documenter):
        """Test steering rules analysis with no rules directory."""
        report = documenter.document_steering_rules_impact()
        
        assert isinstance(report, SteeringRulesReport)
        assert report.total_rules == 0
        assert report.active_rules == 0
        assert report.rule_impacts == []
    
    def test_document_steering_rules_impact_with_rules(self, documenter, mock_steering_structure):
        """Test steering rules analysis with mock rules."""
        report = documenter.document_steering_rules_impact()
        
        assert isinstance(report, SteeringRulesReport)
        assert report.total_rules == 1
        assert len(report.rule_impacts) == 1
        
        rule = report.rule_impacts[0]
        assert rule.rule_name == "tdd"
        assert len(rule.key_guidelines) > 0
        assert len(rule.affected_components) > 0
        assert rule.impact_score > 0
    
    def test_analyze_steering_rule(self, documenter, mock_steering_structure):
        """Test analysis of a single steering rule."""
        rule_file = mock_steering_structure / "tdd.md"
        impact = documenter._analyze_steering_rule(rule_file)
        
        assert isinstance(impact, SteeringRuleImpact)
        assert impact.rule_name == "tdd"
        assert impact.content_length > 0
        assert len(impact.key_guidelines) > 0
        assert "test_module.py" in impact.affected_components
        assert "TestClass" in impact.affected_components
        assert len(impact.usage_examples) > 0
    
    def test_extract_kiro_contributions_no_src(self, documenter):
        """Test Kiro contributions analysis with no source directory."""
        report = documenter.extract_kiro_contributions()
        
        assert isinstance(report, KiroContributionReport)
        assert report.total_lines_of_code == 0
        assert report.overall_contribution_percentage == 0
        assert report.feature_breakdown == {}
    
    def test_extract_kiro_contributions_with_src(self, documenter, mock_src_structure):
        """Test Kiro contributions analysis with mock source files."""
        report = documenter.extract_kiro_contributions()
        
        assert isinstance(report, KiroContributionReport)
        assert report.total_lines_of_code > 0
        assert report.overall_contribution_percentage > 0
        assert len(report.feature_breakdown) > 0
        
        # Check that we have a contribution for the test module
        assert "Test Module" in report.feature_breakdown
        contribution = report.feature_breakdown["Test Module"]
        assert contribution.total_lines > 0
        assert contribution.contribution_percentage > 0
    
    def test_analyze_file_contribution(self, documenter, mock_src_structure):
        """Test analysis of a single file contribution."""
        test_file = mock_src_structure / "test_module.py"
        contribution = documenter._analyze_file_contribution(test_file)
        
        assert isinstance(contribution, KiroContribution)
        assert contribution.component_name == "Test Module"
        assert contribution.total_lines > 0
        assert contribution.kiro_generated_lines > 0
        assert contribution.development_method in ["spec-driven", "direct-generation", "collaborative"]
        assert "has_docstrings" in contribution.quality_indicators
        assert "has_type_hints" in contribution.quality_indicators
    
    def test_count_kiro_generated_lines(self, documenter):
        """Test counting of Kiro-generated lines."""
        content = '''"""
Comprehensive docstring.
"""

from typing import Optional
import asyncio

@dataclass
class TestClass:
    pass

async def test_function():
    raise ValueError("Test error")
'''
        
        count = documenter._count_kiro_generated_lines(content)
        assert count > 0  # Should detect patterns
    
    def test_count_kiro_assisted_lines(self, documenter):
        """Test counting of Kiro-assisted lines."""
        content = '''
# TODO: Implement this
# FIXME: Fix this issue
logger.info("Test message")
pytest.fixture
assert result == expected
'''
        
        count = documenter._count_kiro_assisted_lines(content)
        assert count > 0  # Should detect patterns
    
    def test_determine_development_method(self, documenter):
        """Test determination of development method."""
        # Test spec-driven
        analysis_file = Path("src/forklift/analysis/test.py")
        method = documenter._determine_development_method(analysis_file, "content")
        assert method == "spec-driven"
        
        # Test direct-generation
        other_file = Path("src/other/test.py")
        comprehensive_content = '"""Doc1"""\n"""Doc2"""\n"""Doc3"""'
        method = documenter._determine_development_method(other_file, comprehensive_content)
        assert method == "direct-generation"
        
        # Test collaborative
        method = documenter._determine_development_method(other_file, "simple content")
        assert method == "collaborative"
    
    def test_calculate_quality_indicators(self, documenter):
        """Test calculation of quality indicators."""
        content = '''"""
Test docstring
"""

from typing import Optional

try:
    result = process()
except Exception:
    pass

def test_function():
    pass
'''
        
        indicators = documenter._calculate_quality_indicators(content)
        
        assert indicators["has_docstrings"] is True
        assert indicators["has_type_hints"] is True
        assert indicators["has_error_handling"] is True
        assert indicators["has_tests"] is True
        assert "complexity_score" in indicators
    
    def test_extract_key_features(self, documenter, mock_spec_structure):
        """Test extraction of key features from spec."""
        features = documenter._extract_key_features(mock_spec_structure)
        
        assert isinstance(features, list)
        assert len(features) > 0
        # Should extract from user stories and design sections
    
    def test_calculate_spec_complexity(self, documenter):
        """Test spec complexity calculation."""
        complexity = documenter._calculate_spec_complexity(5, 3, 10)
        expected = min(100, (5 * 2) + (3 * 3) + (10 * 1))  # 29
        assert complexity == expected
    
    def test_extract_guidelines(self, documenter):
        """Test extraction of guidelines from content."""
        content = """
# Guidelines

- First guideline point
- Second guideline point
* Third bullet point

1. First numbered point
2. Second numbered point
"""
        
        guidelines = documenter._extract_guidelines(content)
        
        assert isinstance(guidelines, list)
        assert len(guidelines) > 0
        assert "First guideline point" in guidelines
    
    def test_identify_affected_components(self, documenter):
        """Test identification of affected components."""
        content = """
This affects `test_file.py` and `AnotherClass`.
Also impacts `third_file.py`.
"""
        
        components = documenter._identify_affected_components(content)
        
        assert isinstance(components, list)
        assert "test_file.py" in components
        assert "AnotherClass" in components
    
    def test_extract_usage_examples(self, documenter):
        """Test extraction of usage examples."""
        content = """
Example usage:

```python
def example():
    return True
```

Another example:
```
simple code
```
"""
        
        examples = documenter._extract_usage_examples(content)
        
        assert isinstance(examples, list)
        assert len(examples) > 0
        assert any("def example" in ex for ex in examples)
    
    def test_calculate_impact_score(self, documenter):
        """Test impact score calculation."""
        score = documenter._calculate_impact_score(1000, 5, 3)
        
        # Should be: min(100, 10 + 25 + 9) = 44
        expected = min(100, 10 + 25 + 9)
        assert score == expected
    
    def test_generate_comprehensive_report(self, documenter, mock_spec_structure, mock_steering_structure, mock_src_structure):
        """Test generation of comprehensive report."""
        report = documenter.generate_comprehensive_report()
        
        assert isinstance(report, dict)
        assert "analysis_timestamp" in report
        assert "project_root" in report
        assert "spec_evolution" in report
        assert "steering_rules_impact" in report
        assert "kiro_contributions" in report
        assert "summary" in report
        
        # Check summary content
        summary = report["summary"]
        assert "total_specs" in summary
        assert "total_steering_rules" in summary
        assert "overall_kiro_contribution" in summary
        assert "key_achievements" in summary
    
    def test_save_report_to_file(self, documenter, tmp_path):
        """Test saving report to file."""
        with patch.object(documenter, 'generate_comprehensive_report') as mock_report:
            mock_report.return_value = {"test": "data"}
            
            output_path = documenter.save_report_to_file()
            
            assert output_path.exists()
            assert output_path.name == "kiro_usage_analysis.json"
            
            # Verify content
            with open(output_path, 'r') as f:
                data = json.load(f)
            assert data == {"test": "data"}
    
    def test_save_report_to_custom_path(self, documenter, tmp_path):
        """Test saving report to custom path."""
        custom_path = tmp_path / "custom_report.json"
        
        with patch.object(documenter, 'generate_comprehensive_report') as mock_report:
            mock_report.return_value = {"test": "data"}
            
            output_path = documenter.save_report_to_file(custom_path)
            
            assert output_path == custom_path
            assert output_path.exists()
    
    def test_get_component_name(self, documenter):
        """Test component name extraction."""
        file_path = Path("src/forklift/analysis/test_component.py")
        name = documenter._get_component_name(file_path)
        
        assert name == "Test Component"
    
    def test_generate_iterative_examples(self, documenter):
        """Test generation of iterative development examples."""
        specs = [
            SpecEvolution(
                spec_name="test-spec",
                creation_date=None,
                last_modified=None,
                requirements_count=5,
                design_sections=[],
                tasks_count=10,
                completed_tasks=8,
                in_progress_tasks=1,
                not_started_tasks=1,
                completion_percentage=80.0,
                key_features=[],
                complexity_score=50
            )
        ]
        
        examples = documenter._generate_iterative_examples(specs)
        
        assert isinstance(examples, list)
        assert len(examples) > 0
        assert "test-spec" in examples[0]
        assert "80.0%" in examples[0]
    
    def test_calculate_development_velocity(self, documenter):
        """Test development velocity calculation."""
        specs = [
            SpecEvolution(
                spec_name="spec1",
                creation_date=None,
                last_modified=None,
                requirements_count=5,
                design_sections=[],
                tasks_count=10,
                completed_tasks=8,
                in_progress_tasks=1,
                not_started_tasks=1,
                completion_percentage=80.0,
                key_features=[],
                complexity_score=50
            ),
            SpecEvolution(
                spec_name="spec2",
                creation_date=None,
                last_modified=None,
                requirements_count=3,
                design_sections=[],
                tasks_count=5,
                completed_tasks=5,
                in_progress_tasks=0,
                not_started_tasks=0,
                completion_percentage=100.0,
                key_features=[],
                complexity_score=30
            )
        ]
        
        metrics = documenter._calculate_development_velocity(specs)
        
        assert isinstance(metrics, dict)
        assert "average_completion_rate" in metrics
        assert "total_task_completion_rate" in metrics
        assert "average_spec_complexity" in metrics
        
        assert metrics["average_completion_rate"] == 90.0  # (80 + 100) / 2
        assert metrics["total_task_completion_rate"] == (13/15) * 100  # 13 completed out of 15 total
        assert metrics["average_spec_complexity"] == 40.0  # (50 + 30) / 2


class TestDataClasses:
    """Test the data classes used by KiroUsageDocumenter."""
    
    def test_spec_evolution_creation(self):
        """Test SpecEvolution dataclass creation."""
        spec = SpecEvolution(
            spec_name="test",
            creation_date=datetime.now(),
            last_modified=datetime.now(),
            requirements_count=5,
            design_sections=["Overview", "Architecture"],
            tasks_count=10,
            completed_tasks=7,
            in_progress_tasks=2,
            not_started_tasks=1,
            completion_percentage=70.0,
            key_features=["feature1", "feature2"],
            complexity_score=85
        )
        
        assert spec.spec_name == "test"
        assert spec.requirements_count == 5
        assert spec.completion_percentage == 70.0
    
    def test_steering_rule_impact_creation(self):
        """Test SteeringRuleImpact dataclass creation."""
        impact = SteeringRuleImpact(
            rule_name="tdd",
            file_path=".kiro/steering/tdd.md",
            creation_date=datetime.now(),
            last_modified=datetime.now(),
            content_length=1000,
            key_guidelines=["Write tests first"],
            affected_components=["test_module.py"],
            usage_examples=["def test_example(): pass"],
            impact_score=75
        )
        
        assert impact.rule_name == "tdd"
        assert impact.impact_score == 75
        assert len(impact.key_guidelines) == 1
    
    def test_kiro_contribution_creation(self):
        """Test KiroContribution dataclass creation."""
        contribution = KiroContribution(
            component_name="Test Component",
            file_path="src/test.py",
            total_lines=100,
            kiro_generated_lines=60,
            kiro_assisted_lines=20,
            human_written_lines=20,
            contribution_percentage=80.0,
            development_method="spec-driven",
            quality_indicators={"has_docstrings": True}
        )
        
        assert contribution.component_name == "Test Component"
        assert contribution.contribution_percentage == 80.0
        assert contribution.development_method == "spec-driven"
    
    def test_reports_creation(self):
        """Test report dataclasses creation."""
        spec_report = SpecEvolutionReport(
            total_specs=5,
            active_specs=3,
            completed_specs=2,
            spec_timeline=[],
            feature_to_spec_mapping={},
            iterative_development_examples=[],
            development_velocity_metrics={}
        )
        
        steering_report = SteeringRulesReport(
            total_rules=10,
            active_rules=8,
            rule_impacts=[],
            code_quality_improvements=[],
            testing_strategy_influence=[],
            architecture_decisions=[],
            development_consistency_metrics={}
        )
        
        contribution_report = KiroContributionReport(
            total_lines_of_code=1000,
            kiro_generated_lines=600,
            kiro_assisted_lines=200,
            manually_written_lines=200,
            overall_contribution_percentage=80.0,
            feature_breakdown={},
            spec_driven_components=[],
            development_velocity_impact={},
            quality_improvements=[]
        )
        
        assert spec_report.total_specs == 5
        assert steering_report.total_rules == 10
        assert contribution_report.overall_contribution_percentage == 80.0