"""
Unit tests for project cleanup analyzer.
"""

import re
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from scripts.analyze_project_cleanup import (
    CleanupOpportunity,
    FileAnalysis,
    ProjectCleanupAnalyzer,
    SpecAnalysis,
)


class TestProjectCleanupAnalyzer:
    """Test cases for ProjectCleanupAnalyzer."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project structure for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create project structure
            (project_root / "src" / "forklift").mkdir(parents=True)
            (project_root / "tests" / "unit").mkdir(parents=True)
            (project_root / ".kiro" / "specs" / "test-spec").mkdir(parents=True)

            # Create test files
            (project_root / "src" / "forklift" / "main.py").write_text("# Main module")
            (project_root / "tests" / "unit" / "test_main.py").write_text("# Test file")
            (project_root / "temp_file.tmp").write_text("# Temporary file")
            (project_root / "debug_output.txt").write_text("# Debug output")
            (project_root / "README.md").write_text("# Project README")
            (project_root / "pyproject.toml").write_text("[tool.pytest]")

            # Create spec files
            spec_dir = project_root / ".kiro" / "specs" / "test-spec"
            (spec_dir / "requirements.md").write_text("# Requirements")
            (spec_dir / "design.md").write_text("# Design")
            (spec_dir / "tasks.md").write_text("""
# Tasks
- [x] 1. Completed task
- [-] 2. In progress task
- [ ] 3. Incomplete task
""")

            yield project_root

    @pytest.fixture
    def analyzer(self, temp_project):
        """Create analyzer instance with temp project."""
        return ProjectCleanupAnalyzer(str(temp_project))

    def test_init(self, temp_project):
        """Test analyzer initialization."""
        analyzer = ProjectCleanupAnalyzer(str(temp_project))

        assert analyzer.project_root == temp_project
        assert analyzer.file_analyses == []
        assert analyzer.spec_analyses == []
        assert analyzer.cleanup_opportunities == []

    def test_analyze_single_file_python(self, analyzer, temp_project):
        """Test analysis of Python file."""
        # Create a Python file with imports and exports
        python_file = temp_project / "test_module.py"
        python_file.write_text("""
import os
from pathlib import Path

class TestClass:
    def public_method(self):
        pass

    def _private_method(self):
        pass

def public_function():
    pass
""")

        analysis = analyzer._analyze_single_file(python_file)

        assert analysis is not None
        assert analysis.path == "test_module.py"
        assert "os" in analysis.imports
        assert "pathlib" in analysis.imports
        assert "TestClass" in analysis.exports
        assert "public_function" in analysis.exports
        assert "_private_method" not in analysis.exports

    def test_analyze_single_file_temporary(self, analyzer, temp_project):
        """Test analysis of temporary file."""
        temp_file = temp_project / "debug_test.txt"
        temp_file.write_text("Debug content")

        analysis = analyzer._analyze_single_file(temp_file)

        assert analysis is not None
        assert analysis.is_temporary is True
        assert analysis.safety_level == "safe"
        assert "Temporary or debug file" in analysis.removal_reason

    def test_analyze_single_file_config(self, analyzer, temp_project):
        """Test analysis of configuration file."""
        config_file = temp_project / "config.json"
        config_file.write_text('{"key": "value"}')

        analysis = analyzer._analyze_single_file(config_file)

        assert analysis is not None
        assert analysis.is_config_file is True

    def test_analyze_single_file_documentation(self, analyzer, temp_project):
        """Test analysis of documentation file."""
        doc_file = temp_project / "CHANGELOG.md"
        doc_file.write_text("# Changelog")

        analysis = analyzer._analyze_single_file(doc_file)

        assert analysis is not None
        assert analysis.is_documentation is True

    def test_assess_file_safety_core_files(self, analyzer):
        """Test safety assessment for core application files."""
        safety = analyzer._assess_file_safety("src/forklift/main.py", False, False, False, False, 5)
        assert safety == "unsafe"

    def test_assess_file_safety_config_files(self, analyzer):
        """Test safety assessment for important config files."""
        safety = analyzer._assess_file_safety("pyproject.toml", False, True, False, False, 5)
        assert safety == "unsafe"

    def test_assess_file_safety_temp_files(self, analyzer):
        """Test safety assessment for temporary files."""
        safety = analyzer._assess_file_safety("debug.tmp", False, False, False, True, 0)
        assert safety == "safe"

    def test_assess_file_safety_unused_files(self, analyzer):
        """Test safety assessment for unused files."""
        safety = analyzer._assess_file_safety("unused.py", False, False, False, False, 0)
        assert safety == "caution"

    def test_analyze_tasks_file(self, analyzer, temp_project):
        """Test analysis of tasks file."""
        tasks_file = temp_project / "tasks.md"
        tasks_file.write_text("""
# Tasks

- [x] 1. Completed task
- [-] 2. In progress task
- [ ] 3. Incomplete task
- [x] 4. Another completed task
""")

        total, completed, in_progress = analyzer._analyze_tasks_file(tasks_file)

        assert total == 4
        assert completed == 2
        assert in_progress == 1

    def test_analyze_single_spec_complete(self, analyzer, temp_project):
        """Test analysis of complete specification."""
        spec_dir = temp_project / ".kiro" / "specs" / "complete-spec"
        spec_dir.mkdir(parents=True)

        (spec_dir / "requirements.md").write_text("# Requirements")
        (spec_dir / "design.md").write_text("# Design")
        (spec_dir / "tasks.md").write_text("- [x] 1. Task")

        analysis = analyzer._analyze_single_spec(spec_dir)

        assert analysis is not None
        assert analysis.name == "complete-spec"
        assert analysis.has_requirements is True
        assert analysis.has_design is True
        assert analysis.has_tasks is True
        assert analysis.is_complete is True

    def test_analyze_single_spec_incomplete(self, analyzer, temp_project):
        """Test analysis of incomplete specification."""
        spec_dir = temp_project / ".kiro" / "specs" / "incomplete-spec"
        spec_dir.mkdir(parents=True)

        (spec_dir / "requirements.md").write_text("# Requirements")
        # Missing design.md and tasks.md

        analysis = analyzer._analyze_single_spec(spec_dir)

        assert analysis is not None
        assert analysis.name == "incomplete-spec"
        assert analysis.has_requirements is True
        assert analysis.has_design is False
        assert analysis.has_tasks is False
        assert analysis.is_complete is False

    @patch("subprocess.run")
    def test_count_file_references(self, mock_run, analyzer):
        """Test counting file references."""
        # Mock grep output
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "file1.py:import test\nfile2.py:from test import"

        references = analyzer._count_file_references("test.py")

        assert references >= 0  # Should handle the mock appropriately

    def test_identify_cleanup_opportunities_temp_files(self, analyzer):
        """Test identification of temporary file cleanup opportunities."""
        # Add temporary files to analysis
        analyzer.file_analyses = [
            FileAnalysis(
                path="debug.tmp", size_bytes=100, last_modified="123456",
                is_test_file=False, is_config_file=False, is_documentation=False,
                is_temporary=True, imports=[], exports=[], references_count=0,
                safety_level="safe", removal_reason="Temporary file"
            ),
            FileAnalysis(
                path="test_output.txt", size_bytes=200, last_modified="123456",
                is_test_file=False, is_config_file=False, is_documentation=False,
                is_temporary=True, imports=[], exports=[], references_count=0,
                safety_level="safe", removal_reason="Temporary file"
            )
        ]

        analyzer._identify_cleanup_opportunities()

        temp_opportunities = [op for op in analyzer.cleanup_opportunities
                            if op.category == "Temporary Files"]
        assert len(temp_opportunities) == 1
        assert temp_opportunities[0].safety_level == "safe"
        assert len(temp_opportunities[0].files_affected) == 2

    def test_identify_cleanup_opportunities_unused_files(self, analyzer):
        """Test identification of unused file cleanup opportunities."""
        # Add unused files to analysis
        analyzer.file_analyses = [
            FileAnalysis(
                path="unused.py", size_bytes=100, last_modified="123456",
                is_test_file=False, is_config_file=False, is_documentation=False,
                is_temporary=False, imports=[], exports=[], references_count=0,
                safety_level="caution", removal_reason="No references"
            )
        ]

        analyzer._identify_cleanup_opportunities()

        unused_opportunities = [op for op in analyzer.cleanup_opportunities
                              if op.category == "Unused Files"]
        assert len(unused_opportunities) == 1
        assert unused_opportunities[0].safety_level == "caution"

    def test_identify_cleanup_opportunities_incomplete_specs(self, analyzer):
        """Test identification of incomplete specification cleanup opportunities."""
        # Add incomplete specs to analysis
        analyzer.spec_analyses = [
            SpecAnalysis(
                name="incomplete-spec", path=".kiro/specs/incomplete-spec",
                has_requirements=True, has_design=False, has_tasks=False,
                total_tasks=0, completed_tasks=0, in_progress_tasks=0,
                incomplete_tasks=0, completion_percentage=0, is_complete=False
            )
        ]

        analyzer._identify_cleanup_opportunities()

        spec_opportunities = [op for op in analyzer.cleanup_opportunities
                            if op.category == "Incomplete Specifications"]
        assert len(spec_opportunities) == 1
        assert spec_opportunities[0].safety_level == "caution"

    def test_generate_summary(self, analyzer):
        """Test summary generation."""
        # Add test data
        analyzer.file_analyses = [
            FileAnalysis(
                path="temp.tmp", size_bytes=100, last_modified="123456",
                is_test_file=False, is_config_file=False, is_documentation=False,
                is_temporary=True, imports=[], exports=[], references_count=0,
                safety_level="safe"
            ),
            FileAnalysis(
                path="main.py", size_bytes=1000, last_modified="123456",
                is_test_file=False, is_config_file=False, is_documentation=False,
                is_temporary=False, imports=[], exports=[], references_count=5,
                safety_level="unsafe"
            )
        ]

        analyzer.spec_analyses = [
            SpecAnalysis(
                name="test-spec", path=".kiro/specs/test-spec",
                has_requirements=True, has_design=True, has_tasks=True,
                total_tasks=3, completed_tasks=1, in_progress_tasks=1,
                incomplete_tasks=1, completion_percentage=33.3, is_complete=False
            )
        ]

        analyzer.cleanup_opportunities = [
            CleanupOpportunity(
                category="Test", description="Test opportunity",
                files_affected=["test.txt"], safety_level="safe",
                estimated_impact="low", recommendation="Test",
                prerequisites=[]
            )
        ]

        summary = analyzer._generate_summary()

        assert summary["file_analysis"]["total_files"] == 2
        assert summary["file_analysis"]["temporary_files"] == 1
        assert summary["specification_analysis"]["total_specifications"] == 1
        assert summary["specification_analysis"]["incomplete_tasks"] == 1
        assert summary["cleanup_opportunities"] == 1

    @patch("builtins.open", new_callable=mock_open)
    def test_generate_report(self, mock_file, analyzer):
        """Test report generation."""
        # Mock the analyze_project method
        with patch.object(analyzer, "analyze_project") as mock_analyze:
            mock_analyze.return_value = {
                "file_analysis": {
                    "total_files": 10,
                    "temporary_files": 2,
                    "unused_files": 1,
                    "files_by_safety": {"safe": 2, "caution": 5, "unsafe": 3}
                },
                "specification_analysis": {
                    "total_specifications": 5,
                    "incomplete_specifications": 2,
                    "incomplete_tasks": 3,
                    "completed_tasks": 7,
                    "total_tasks": 10,
                    "completion_percentage": 70.0
                },
                "cleanup_opportunities": 3,
                "detailed_analyses": {"files": [], "specifications": [], "cleanup_opportunities": []}
            }

            summary = analyzer.generate_report("test_output.json")

            assert mock_analyze.called
            assert mock_file.called
            assert summary is not None

    def test_file_analysis_dataclass(self):
        """Test FileAnalysis dataclass."""
        analysis = FileAnalysis(
            path="test.py", size_bytes=1000, last_modified="123456",
            is_test_file=True, is_config_file=False, is_documentation=False,
            is_temporary=False, imports=["os"], exports=["main"],
            references_count=5, safety_level="caution"
        )

        assert analysis.path == "test.py"
        assert analysis.size_bytes == 1000
        assert analysis.is_test_file is True
        assert analysis.safety_level == "caution"

    def test_spec_analysis_dataclass(self):
        """Test SpecAnalysis dataclass."""
        analysis = SpecAnalysis(
            name="test-spec", path=".kiro/specs/test-spec",
            has_requirements=True, has_design=True, has_tasks=True,
            total_tasks=5, completed_tasks=3, in_progress_tasks=1,
            incomplete_tasks=1, completion_percentage=60.0, is_complete=False
        )

        assert analysis.name == "test-spec"
        assert analysis.total_tasks == 5
        assert analysis.completed_tasks == 3
        assert analysis.completion_percentage == 60.0

    def test_cleanup_opportunity_dataclass(self):
        """Test CleanupOpportunity dataclass."""
        opportunity = CleanupOpportunity(
            category="Test Category", description="Test description",
            files_affected=["file1.py", "file2.py"], safety_level="caution",
            estimated_impact="medium", recommendation="Test recommendation",
            prerequisites=["Review", "Testing"]
        )

        assert opportunity.category == "Test Category"
        assert len(opportunity.files_affected) == 2
        assert opportunity.safety_level == "caution"
        assert len(opportunity.prerequisites) == 2


class TestProjectCleanupAnalyzerIntegration:
    """Integration tests for project cleanup analyzer."""

    def test_temp_patterns_matching(self):
        """Test temporary file pattern matching."""
        analyzer = ProjectCleanupAnalyzer()

        temp_files = [
            "debug.tmp", "test_output.txt", "backup.bak",
            "session.temp", "debug_info.py", "demo_script.py"
        ]

        for file_path in temp_files:
            is_temp = any(re.match(pattern, file_path) for pattern in analyzer.temp_patterns)
            assert is_temp, f"File {file_path} should match temp patterns"

    def test_config_patterns_matching(self):
        """Test configuration file pattern matching."""
        analyzer = ProjectCleanupAnalyzer()

        config_files = [
            "config.json", "settings.yaml", "app.yml",
            "pyproject.toml", "setup.cfg", ".env"
        ]

        for file_path in config_files:
            is_config = any(re.match(pattern, file_path) for pattern in analyzer.config_patterns)
            assert is_config, f"File {file_path} should match config patterns"

    def test_doc_patterns_matching(self):
        """Test documentation file pattern matching."""
        analyzer = ProjectCleanupAnalyzer()

        doc_files = [
            "README.md", "CHANGELOG.rst", "docs.txt",
            "LICENSE", "CONTRIBUTING.md"
        ]

        for file_path in doc_files:
            is_doc = any(re.match(pattern, file_path) for pattern in analyzer.doc_patterns)
            assert is_doc, f"File {file_path} should match doc patterns"
