"""
Integration tests for project cleanup analysis.
"""

import json
import tempfile
from pathlib import Path

import pytest

from scripts.analyze_project_cleanup import ProjectCleanupAnalyzer


class TestProjectCleanupIntegration:
    """Integration tests for project cleanup analyzer."""

    @pytest.fixture
    def realistic_project(self):
        """Create a realistic project structure for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create realistic project structure
            (project_root / "src" / "forklift" / "analysis").mkdir(parents=True)
            (project_root / "src" / "forklift" / "github").mkdir(parents=True)
            (project_root / "tests" / "unit" / "analysis").mkdir(parents=True)
            (project_root / "tests" / "integration").mkdir(parents=True)
            (project_root / "scripts").mkdir(parents=True)
            (project_root / ".kiro" / "specs" / "feature-1").mkdir(parents=True)
            (project_root / ".kiro" / "specs" / "feature-2").mkdir(parents=True)
            (project_root / "docs").mkdir(parents=True)

            # Create source files
            (project_root / "src" / "forklift" / "__init__.py").write_text("")
            (project_root / "src" / "forklift" / "main.py").write_text("""
import os
from pathlib import Path
from .analysis import analyzer

class MainApp:
    def __init__(self):
        self.analyzer = analyzer

    def run(self):
        pass
""")

            (project_root / "src" / "forklift" / "analysis" / "__init__.py").write_text("")
            (project_root / "src" / "forklift" / "analysis" / "analyzer.py").write_text("""
from typing import List, Dict

def analyze_data(data: List[Dict]) -> Dict:
    return {"result": "analyzed"}
""")

            # Create test files
            (project_root / "tests" / "__init__.py").write_text("")
            (project_root / "tests" / "unit" / "__init__.py").write_text("")
            (project_root / "tests" / "unit" / "analysis" / "__init__.py").write_text("")
            (project_root / "tests" / "unit" / "analysis" / "test_analyzer.py").write_text("""
import pytest
from src.forklift.analysis.analyzer import analyze_data

def test_analyze_data():
    result = analyze_data([{"key": "value"}])
    assert result["result"] == "analyzed"
""")

            # Create temporary/debug files
            (project_root / "debug_output.txt").write_text("Debug information")
            (project_root / "test_results.tmp").write_text("Temporary test results")
            (project_root / "session_backup.bak").write_text("Backup data")
            (project_root / "demo_script.py").write_text("# Demo script for testing")

            # Create unused files
            (project_root / "unused_utility.py").write_text("""
def unused_function():
    return "This function is never called"
""")

            # Create configuration files
            (project_root / "pyproject.toml").write_text("""
[tool.pytest.ini_options]
testpaths = ["tests"]
""")
            (project_root / ".gitignore").write_text("__pycache__/\n*.pyc\n")
            (project_root / "config.json").write_text('{"setting": "value"}')

            # Create documentation
            (project_root / "README.md").write_text("# Project README")
            (project_root / "CHANGELOG.md").write_text("# Changelog")
            (project_root / "docs" / "api.md").write_text("# API Documentation")

            # Create scripts
            (project_root / "scripts" / "build.py").write_text("# Build script")
            (project_root / "scripts" / "deploy.py").write_text("# Deploy script")

            # Create complete specification
            spec1_dir = project_root / ".kiro" / "specs" / "feature-1"
            (spec1_dir / "requirements.md").write_text("""
# Requirements
## Requirement 1
User story and acceptance criteria
""")
            (spec1_dir / "design.md").write_text("""
# Design
## Architecture
Design details
""")
            (spec1_dir / "tasks.md").write_text("""
# Tasks
- [x] 1. Implement core functionality
- [x] 2. Add tests
- [-] 3. Update documentation
- [ ] 4. Performance optimization
""")

            # Create incomplete specification
            spec2_dir = project_root / ".kiro" / "specs" / "feature-2"
            (spec2_dir / "requirements.md").write_text("""
# Requirements
## Requirement 1
Basic requirements only
""")
            # Missing design.md and tasks.md

            # Create large file
            large_content = "# Large file\n" + "x" * 150000  # > 100KB
            (project_root / "large_data_file.py").write_text(large_content)

            yield project_root

    @pytest.mark.asyncio
    async def test_full_project_analysis(self, realistic_project):
        """Test complete project analysis with realistic structure."""
        analyzer = ProjectCleanupAnalyzer(str(realistic_project))

        # Run full analysis
        summary = analyzer.analyze_project()

        # Verify file analysis results
        file_stats = summary["file_analysis"]
        assert file_stats["total_files"] > 10
        assert file_stats["temporary_files"] >= 3  # debug_output.txt, test_results.tmp, session_backup.bak, demo_script.py
        assert file_stats["unused_files"] >= 1  # unused_utility.py

        # Verify safety categorization
        safety_stats = file_stats["files_by_safety"]
        assert safety_stats["safe"] >= 3  # Temporary files
        assert safety_stats["caution"] >= 1  # Unused files
        assert safety_stats["unsafe"] >= 3  # Core files like main.py, pyproject.toml, README.md

        # Verify specification analysis
        spec_stats = summary["specification_analysis"]
        assert spec_stats["total_specifications"] == 2
        assert spec_stats["complete_specifications"] == 0  # feature-1 has incomplete task
        assert spec_stats["incomplete_specifications"] == 2
        assert spec_stats["total_tasks"] == 4
        assert spec_stats["completed_tasks"] == 2
        assert spec_stats["incomplete_tasks"] == 1  # 1 incomplete (in progress not counted as incomplete)

        # Verify cleanup opportunities
        assert summary["cleanup_opportunities"] >= 4  # temp files, unused files, large files, incomplete specs

    @pytest.mark.asyncio
    async def test_file_categorization_accuracy(self, realistic_project):
        """Test accuracy of file categorization."""
        analyzer = ProjectCleanupAnalyzer(str(realistic_project))
        analyzer._analyze_files()

        # Check temporary files are correctly identified
        temp_files = [f for f in analyzer.file_analyses if f.is_temporary]
        temp_paths = [f.path for f in temp_files]

        assert "debug_output.txt" in temp_paths
        assert "test_results.tmp" in temp_paths
        assert "session_backup.bak" in temp_paths
        assert "demo_script.py" in temp_paths

        # Check configuration files are correctly identified
        config_files = [f for f in analyzer.file_analyses if f.is_config_file]
        config_paths = [f.path for f in config_files]

        assert "pyproject.toml" in config_paths
        assert "config.json" in config_paths

        # Check documentation files are correctly identified
        doc_files = [f for f in analyzer.file_analyses if f.is_documentation]
        doc_paths = [f.path for f in doc_files]

        assert "README.md" in doc_paths
        assert "CHANGELOG.md" in doc_paths

    @pytest.mark.asyncio
    async def test_safety_assessment_accuracy(self, realistic_project):
        """Test accuracy of safety level assessment."""
        analyzer = ProjectCleanupAnalyzer(str(realistic_project))
        analyzer._analyze_files()

        # Check core files are marked as unsafe
        unsafe_files = [f for f in analyzer.file_analyses if f.safety_level == "unsafe"]
        unsafe_paths = [f.path for f in unsafe_files]

        # Should include core application files
        core_files = [f for f in unsafe_paths if f.startswith("src/")]
        assert len(core_files) > 0

        # Should include important config files
        assert "pyproject.toml" in unsafe_paths
        assert "README.md" in unsafe_paths

        # Check temporary files are marked as safe
        safe_files = [f for f in analyzer.file_analyses if f.safety_level == "safe"]
        safe_paths = [f.path for f in safe_files]

        assert "debug_output.txt" in safe_paths
        assert "test_results.tmp" in safe_paths

    @pytest.mark.asyncio
    async def test_specification_analysis_accuracy(self, realistic_project):
        """Test accuracy of specification analysis."""
        analyzer = ProjectCleanupAnalyzer(str(realistic_project))
        analyzer._analyze_specifications()

        assert len(analyzer.spec_analyses) == 2

        # Check feature-1 analysis
        feature1 = next(s for s in analyzer.spec_analyses if s.name == "feature-1")
        assert feature1.has_requirements is True
        assert feature1.has_design is True
        assert feature1.has_tasks is True
        assert feature1.total_tasks == 4
        assert feature1.completed_tasks == 2
        assert feature1.in_progress_tasks == 1
        assert feature1.incomplete_tasks == 1
        assert feature1.is_complete is False  # Has incomplete tasks

        # Check feature-2 analysis
        feature2 = next(s for s in analyzer.spec_analyses if s.name == "feature-2")
        assert feature2.has_requirements is True
        assert feature2.has_design is False
        assert feature2.has_tasks is False
        assert feature2.is_complete is False

    @pytest.mark.asyncio
    async def test_cleanup_opportunities_identification(self, realistic_project):
        """Test identification of cleanup opportunities."""
        analyzer = ProjectCleanupAnalyzer(str(realistic_project))
        analyzer._analyze_files()
        analyzer._analyze_specifications()
        analyzer._identify_cleanup_opportunities()

        # Should identify temporary files cleanup
        temp_cleanup = next(
            (op for op in analyzer.cleanup_opportunities if op.category == "Temporary Files"),
            None
        )
        assert temp_cleanup is not None
        assert temp_cleanup.safety_level == "safe"
        assert len(temp_cleanup.files_affected) >= 3

        # Should identify large files review
        large_cleanup = next(
            (op for op in analyzer.cleanup_opportunities if op.category == "Large Files"),
            None
        )
        assert large_cleanup is not None
        assert "large_data_file.py" in large_cleanup.files_affected

        # Should identify incomplete specifications
        spec_cleanup = next(
            (op for op in analyzer.cleanup_opportunities if op.category == "Incomplete Specifications"),
            None
        )
        assert spec_cleanup is not None
        assert spec_cleanup.safety_level == "caution"

    @pytest.mark.asyncio
    async def test_report_generation_integration(self, realistic_project):
        """Test end-to-end report generation."""
        analyzer = ProjectCleanupAnalyzer(str(realistic_project))

        # Generate reports
        json_file = str(realistic_project / "cleanup_report.json")
        analyzer.generate_report(json_file)

        # Verify JSON report was created
        assert Path(json_file).exists()

        # Verify JSON content
        with open(json_file) as f:
            report_data = json.load(f)

        assert "file_analysis" in report_data
        assert "specification_analysis" in report_data
        assert "cleanup_opportunities" in report_data
        assert "detailed_analyses" in report_data

        # Verify markdown report was created
        markdown_file = json_file.replace(".json", ".md")
        assert Path(markdown_file).exists()

        # Verify markdown content
        with open(markdown_file) as f:
            markdown_content = f.read()

        assert "# Project Cleanup Analysis Report" in markdown_content
        assert "## Executive Summary" in markdown_content
        assert "## File Analysis" in markdown_content
        assert "## Specification Analysis" in markdown_content
        assert "## Cleanup Opportunities" in markdown_content

    @pytest.mark.asyncio
    async def test_python_file_analysis_integration(self, realistic_project):
        """Test Python file analysis integration."""
        analyzer = ProjectCleanupAnalyzer(str(realistic_project))

        # Analyze the main.py file
        main_file = realistic_project / "src" / "forklift" / "main.py"
        analysis = analyzer._analyze_single_file(main_file)

        assert analysis is not None
        assert "os" in analysis.imports
        assert "pathlib" in analysis.imports
        assert "MainApp" in analysis.exports
        assert analysis.safety_level == "unsafe"  # Core application file

    @pytest.mark.asyncio
    async def test_tasks_file_parsing_integration(self, realistic_project):
        """Test tasks file parsing integration."""
        analyzer = ProjectCleanupAnalyzer(str(realistic_project))

        tasks_file = realistic_project / ".kiro" / "specs" / "feature-1" / "tasks.md"
        total, completed, in_progress = analyzer._analyze_tasks_file(tasks_file)

        assert total == 4
        assert completed == 2
        assert in_progress == 1

    @pytest.mark.asyncio
    async def test_edge_cases_handling(self, realistic_project):
        """Test handling of edge cases."""
        analyzer = ProjectCleanupAnalyzer(str(realistic_project))

        # Create files with special characters
        special_file = realistic_project / "file with spaces.py"
        special_file.write_text("# File with spaces")

        # Create empty file
        empty_file = realistic_project / "empty.py"
        empty_file.write_text("")

        # Create binary file
        binary_file = realistic_project / "binary.dat"
        binary_file.write_bytes(b"\x00\x01\x02\x03")

        # Should handle these without crashing
        analyzer._analyze_files()

        # Verify files were analyzed
        analyzed_paths = [f.path for f in analyzer.file_analyses]
        assert "file with spaces.py" in analyzed_paths
        assert "empty.py" in analyzed_paths
        assert "binary.dat" in analyzed_paths

    @pytest.mark.asyncio
    async def test_performance_with_large_project(self, realistic_project):
        """Test performance with larger project structure."""
        # Create many files to test performance
        for i in range(50):
            (realistic_project / f"test_file_{i}.py").write_text(f"# Test file {i}")

        for i in range(20):
            spec_dir = realistic_project / ".kiro" / "specs" / f"spec-{i}"
            spec_dir.mkdir(parents=True)
            (spec_dir / "requirements.md").write_text(f"# Requirements {i}")

        analyzer = ProjectCleanupAnalyzer(str(realistic_project))

        # Should complete analysis in reasonable time
        import time
        start_time = time.time()
        summary = analyzer.analyze_project()
        end_time = time.time()

        # Should complete within 30 seconds for this size
        assert end_time - start_time < 30

        # Should analyze all files
        assert summary["file_analysis"]["total_files"] > 70
        assert summary["specification_analysis"]["total_specifications"] > 20
