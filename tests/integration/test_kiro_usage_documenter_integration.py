"""
Integration tests for KiroUsageDocumenter

These tests verify the KiroUsageDocumenter works with real project structure
and can analyze actual spec files, steering rules, and source code.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

from src.forklift.analysis.kiro_usage_documenter import (
    KiroUsageDocumenter,
    SpecEvolutionReport,
    SteeringRulesReport,
    KiroContributionReport
)


class TestKiroUsageDocumenterIntegration:
    """Integration tests for KiroUsageDocumenter with real project data."""
    
    @pytest.fixture
    def real_documenter(self):
        """Create documenter with real project root."""
        project_root = Path(__file__).parent.parent.parent
        return KiroUsageDocumenter(project_root=project_root)
    
    def test_analyze_real_spec_evolution(self, real_documenter):
        """Test spec evolution analysis with real project specs."""
        report = real_documenter.analyze_spec_evolution()
        
        assert isinstance(report, SpecEvolutionReport)
        
        # Should find actual specs in the project
        if report.total_specs > 0:
            assert len(report.spec_timeline) == report.total_specs
            assert report.total_specs >= report.completed_specs
            assert report.total_specs >= report.active_specs
            
            # Check that we have meaningful data
            for spec in report.spec_timeline:
                assert spec.spec_name is not None
                assert spec.tasks_count >= 0
                assert spec.requirements_count >= 0
                assert 0 <= spec.completion_percentage <= 100
                
            # Verify feature mapping
            assert isinstance(report.feature_to_spec_mapping, dict)
            
            # Check development velocity metrics
            assert isinstance(report.development_velocity_metrics, dict)
            if report.development_velocity_metrics:
                assert "average_completion_rate" in report.development_velocity_metrics
    
    def test_analyze_real_steering_rules(self, real_documenter):
        """Test steering rules analysis with real project rules."""
        report = real_documenter.document_steering_rules_impact()
        
        assert isinstance(report, SteeringRulesReport)
        
        # Should find actual steering rules
        if report.total_rules > 0:
            assert len(report.rule_impacts) == report.total_rules
            assert report.total_rules >= report.active_rules
            
            # Check rule impacts
            for rule in report.rule_impacts:
                assert rule.rule_name is not None
                assert rule.file_path is not None
                assert rule.content_length > 0
                assert rule.impact_score >= 0
                
            # Check categorized impacts
            assert isinstance(report.code_quality_improvements, list)
            assert isinstance(report.testing_strategy_influence, list)
            assert isinstance(report.architecture_decisions, list)
            
            # Check consistency metrics
            assert isinstance(report.development_consistency_metrics, dict)
    
    def test_analyze_real_kiro_contributions(self, real_documenter):
        """Test Kiro contributions analysis with real source code."""
        report = real_documenter.extract_kiro_contributions()
        
        assert isinstance(report, KiroContributionReport)
        
        # Should analyze actual source files
        if report.total_lines_of_code > 0:
            assert report.kiro_generated_lines >= 0
            assert report.kiro_assisted_lines >= 0
            assert report.manually_written_lines >= 0
            assert (report.kiro_generated_lines + report.kiro_assisted_lines + 
                   report.manually_written_lines) <= report.total_lines_of_code * 1.1  # Allow some overlap
            
            assert 0 <= report.overall_contribution_percentage <= 100
            
            # Check feature breakdown
            assert isinstance(report.feature_breakdown, dict)
            for component_name, contribution in report.feature_breakdown.items():
                assert contribution.component_name == component_name
                assert contribution.total_lines > 0
                assert 0 <= contribution.contribution_percentage <= 100
                assert contribution.development_method in ["spec-driven", "direct-generation", "collaborative"]
                assert isinstance(contribution.quality_indicators, dict)
            
            # Check spec-driven components
            assert isinstance(report.spec_driven_components, list)
            
            # Check velocity impact
            assert isinstance(report.development_velocity_impact, dict)
            
            # Check quality improvements
            assert isinstance(report.quality_improvements, list)
    
    def test_generate_comprehensive_real_report(self, real_documenter):
        """Test comprehensive report generation with real project data."""
        report = real_documenter.generate_comprehensive_report()
        
        assert isinstance(report, dict)
        
        # Check required sections
        required_sections = [
            "analysis_timestamp",
            "project_root", 
            "spec_evolution",
            "steering_rules_impact",
            "kiro_contributions",
            "summary"
        ]
        
        for section in required_sections:
            assert section in report
        
        # Verify timestamp format
        timestamp = report["analysis_timestamp"]
        datetime.fromisoformat(timestamp)  # Should not raise exception
        
        # Check project root
        assert Path(report["project_root"]).exists()
        
        # Verify nested report structures
        assert isinstance(report["spec_evolution"], dict)
        assert isinstance(report["steering_rules_impact"], dict)
        assert isinstance(report["kiro_contributions"], dict)
        
        # Check summary
        summary = report["summary"]
        assert "total_specs" in summary
        assert "total_steering_rules" in summary
        assert "overall_kiro_contribution" in summary
        assert "development_method" in summary
        assert "key_achievements" in summary
        
        assert isinstance(summary["key_achievements"], list)
        assert len(summary["key_achievements"]) > 0
    
    def test_save_real_report_to_file(self, real_documenter, tmp_path):
        """Test saving real report to file."""
        output_path = tmp_path / "real_kiro_analysis.json"
        
        saved_path = real_documenter.save_report_to_file(output_path)
        
        assert saved_path == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        
        # Verify JSON structure
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert isinstance(data, dict)
        assert "analysis_timestamp" in data
        assert "summary" in data
    
    def test_real_spec_file_parsing(self, real_documenter):
        """Test parsing of actual spec files in the project."""
        specs_dir = real_documenter.specs_dir
        
        if not specs_dir.exists():
            pytest.skip("No specs directory found")
        
        spec_dirs = [d for d in specs_dir.iterdir() if d.is_dir()]
        
        if not spec_dirs:
            pytest.skip("No spec directories found")
        
        # Test parsing of first available spec
        test_spec = spec_dirs[0]
        spec_evolution = real_documenter._analyze_single_spec(test_spec)
        
        if spec_evolution:
            assert spec_evolution.spec_name == test_spec.name
            assert spec_evolution.requirements_count >= 0
            assert spec_evolution.tasks_count >= 0
            assert 0 <= spec_evolution.completion_percentage <= 100
            
            # If tasks exist, verify counts add up
            if spec_evolution.tasks_count > 0:
                total_tasks = (spec_evolution.completed_tasks + 
                             spec_evolution.in_progress_tasks + 
                             spec_evolution.not_started_tasks)
                assert total_tasks == spec_evolution.tasks_count
    
    def test_real_steering_rule_parsing(self, real_documenter):
        """Test parsing of actual steering rule files."""
        steering_dir = real_documenter.steering_dir
        
        if not steering_dir.exists():
            pytest.skip("No steering directory found")
        
        rule_files = list(steering_dir.glob("*.md"))
        
        if not rule_files:
            pytest.skip("No steering rule files found")
        
        # Test parsing of first available rule
        test_rule = rule_files[0]
        rule_impact = real_documenter._analyze_steering_rule(test_rule)
        
        if rule_impact:
            assert rule_impact.rule_name == test_rule.stem
            assert rule_impact.content_length > 0
            assert rule_impact.impact_score >= 0
            assert isinstance(rule_impact.key_guidelines, list)
            assert isinstance(rule_impact.affected_components, list)
            assert isinstance(rule_impact.usage_examples, list)
    
    def test_real_source_file_analysis(self, real_documenter):
        """Test analysis of actual source files."""
        src_dir = real_documenter.src_dir
        
        if not src_dir.exists():
            pytest.skip("No source directory found")
        
        py_files = list(src_dir.rglob("*.py"))
        
        if not py_files:
            pytest.skip("No Python files found")
        
        # Test analysis of first available Python file
        test_file = py_files[0]
        contribution = real_documenter._analyze_file_contribution(test_file)
        
        if contribution:
            assert contribution.component_name is not None
            assert contribution.total_lines > 0
            assert contribution.kiro_generated_lines >= 0
            assert contribution.kiro_assisted_lines >= 0
            assert contribution.human_written_lines >= 0
            assert 0 <= contribution.contribution_percentage <= 100
            assert contribution.development_method in ["spec-driven", "direct-generation", "collaborative"]
            assert isinstance(contribution.quality_indicators, dict)
    
    def test_pattern_detection_accuracy(self, real_documenter):
        """Test accuracy of Kiro pattern detection in real code."""
        # Create test content with known patterns
        test_content = '''"""
Comprehensive module documentation.

This module demonstrates various Kiro-generated patterns.
"""

from typing import Optional, List, Dict
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ExampleClass:
    """Example class with comprehensive documentation."""
    name: str
    value: Optional[int] = None
    
    async def process_data(self) -> List[Dict[str, Any]]:
        """Process data asynchronously with proper error handling."""
        try:
            # TODO: Implement actual processing logic
            logger.info("Starting data processing")
            result = []
            
            # Process items
            for item in self.get_items():
                processed = await self.process_item(item)
                result.append(processed)
            
            logger.info(f"Processed {len(result)} items")
            return result
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise ProcessingError("Failed to process data") from e
    
    def test_method(self):
        """Test method for validation."""
        assert self.name is not None
        pytest.fixture
        return True
'''
        
        # Test pattern detection
        kiro_generated = real_documenter._count_kiro_generated_lines(test_content)
        kiro_assisted = real_documenter._count_kiro_assisted_lines(test_content)
        
        # Should detect comprehensive docstrings, type hints, async patterns, etc.
        assert kiro_generated > 0
        assert kiro_assisted > 0
        
        # Test quality indicators
        quality = real_documenter._calculate_quality_indicators(test_content)
        
        assert quality["has_docstrings"] is True
        assert quality["has_type_hints"] is True
        assert quality["has_error_handling"] is True
        assert quality["has_tests"] is True
        assert quality["complexity_score"] > 0
    
    def test_development_method_detection(self, real_documenter):
        """Test detection of development methods for real files."""
        src_dir = real_documenter.src_dir
        
        if not src_dir.exists():
            pytest.skip("No source directory found")
        
        # Find analysis files (should be spec-driven)
        analysis_files = list(src_dir.rglob("analysis/*.py"))
        
        if analysis_files:
            test_file = analysis_files[0]
            content = test_file.read_text(encoding='utf-8')
            method = real_documenter._determine_development_method(test_file, content)
            
            # Analysis files should be detected as spec-driven
            assert method == "spec-driven"
        
        # Test with comprehensive content (should be direct-generation)
        comprehensive_content = '"""Doc1"""\n"""Doc2"""\n"""Doc3"""'
        other_file = Path("src/other/test.py")
        method = real_documenter._determine_development_method(other_file, comprehensive_content)
        assert method == "direct-generation"
    
    def test_feature_extraction_accuracy(self, real_documenter):
        """Test accuracy of feature extraction from real specs."""
        specs_dir = real_documenter.specs_dir
        
        if not specs_dir.exists():
            pytest.skip("No specs directory found")
        
        spec_dirs = [d for d in specs_dir.iterdir() if d.is_dir()]
        
        if not spec_dirs:
            pytest.skip("No spec directories found")
        
        # Test feature extraction from first available spec
        test_spec = spec_dirs[0]
        features = real_documenter._extract_key_features(test_spec)
        
        assert isinstance(features, list)
        assert len(features) <= 5  # Should limit to 5 features
        
        # Features should be meaningful strings
        for feature in features:
            assert isinstance(feature, str)
            assert len(feature) > 0
    
    def test_report_data_consistency(self, real_documenter):
        """Test consistency of data across different report sections."""
        report = real_documenter.generate_comprehensive_report()
        
        # Extract data from different sections
        spec_data = report["spec_evolution"]
        steering_data = report["steering_rules_impact"]
        contribution_data = report["kiro_contributions"]
        summary = report["summary"]
        
        # Verify consistency
        assert summary["total_specs"] == spec_data["total_specs"]
        assert summary["total_steering_rules"] == steering_data["total_rules"]
        assert summary["overall_kiro_contribution"] == contribution_data["overall_contribution_percentage"]
        
        # Check that achievements list contains meaningful data
        achievements = summary["key_achievements"]
        assert len(achievements) >= 3
        
        for achievement in achievements:
            assert isinstance(achievement, str)
            assert len(achievement) > 0
    
    def test_error_handling_with_real_data(self, real_documenter):
        """Test error handling when processing real project data."""
        # This test ensures the documenter handles real-world edge cases gracefully
        
        # Test with potentially missing directories
        original_specs_dir = real_documenter.specs_dir
        original_steering_dir = real_documenter.steering_dir
        original_src_dir = real_documenter.src_dir
        
        try:
            # Test with non-existent specs directory
            real_documenter.specs_dir = Path("/non/existent/specs")
            spec_report = real_documenter.analyze_spec_evolution()
            assert spec_report.total_specs == 0
            
            # Test with non-existent steering directory
            real_documenter.steering_dir = Path("/non/existent/steering")
            steering_report = real_documenter.document_steering_rules_impact()
            assert steering_report.total_rules == 0
            
            # Test with non-existent source directory
            real_documenter.src_dir = Path("/non/existent/src")
            contribution_report = real_documenter.extract_kiro_contributions()
            assert contribution_report.total_lines_of_code == 0
            
        finally:
            # Restore original paths
            real_documenter.specs_dir = original_specs_dir
            real_documenter.steering_dir = original_steering_dir
            real_documenter.src_dir = original_src_dir
    
    def test_performance_with_real_data(self, real_documenter):
        """Test performance of analysis with real project data."""
        import time
        
        start_time = time.time()
        
        # Run comprehensive analysis
        report = real_documenter.generate_comprehensive_report()
        
        end_time = time.time()
        analysis_time = end_time - start_time
        
        # Analysis should complete in reasonable time (less than 30 seconds)
        assert analysis_time < 30.0
        
        # Report should contain meaningful data
        assert isinstance(report, dict)
        assert len(report) > 0
        
        print(f"Analysis completed in {analysis_time:.2f} seconds")
    
    @pytest.mark.slow
    def test_full_project_analysis(self, real_documenter, tmp_path):
        """Comprehensive test of full project analysis."""
        # Generate complete report
        report = real_documenter.generate_comprehensive_report()
        
        # Save to file
        output_path = tmp_path / "full_analysis.json"
        saved_path = real_documenter.save_report_to_file(output_path)
        
        # Verify file was created and contains valid JSON
        assert saved_path.exists()
        
        with open(saved_path, 'r', encoding='utf-8') as f:
            loaded_report = json.load(f)
        
        # Verify loaded report matches generated report
        assert loaded_report == report
        
        # Print summary for manual verification
        summary = report["summary"]
        print(f"\nProject Analysis Summary:")
        print(f"Total Specs: {summary['total_specs']}")
        print(f"Total Steering Rules: {summary['total_steering_rules']}")
        print(f"Overall Kiro Contribution: {summary['overall_kiro_contribution']:.1f}%")
        print(f"Development Method: {summary['development_method']}")
        print(f"Key Achievements:")
        for achievement in summary['key_achievements']:
            print(f"  - {achievement}")