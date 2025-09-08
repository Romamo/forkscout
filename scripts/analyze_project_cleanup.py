#!/usr/bin/env python3
"""
Project Cleanup Analysis Script

Analyzes the project for excess functionality, unused files, and cleanup opportunities.
Generates a comprehensive report with safety assessments for potential removals.
"""

import ast
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any


@dataclass
class FileAnalysis:
    """Analysis result for a single file."""
    path: str
    size_bytes: int
    last_modified: str
    is_test_file: bool
    is_config_file: bool
    is_documentation: bool
    is_temporary: bool
    imports: list[str]
    exports: list[str]
    references_count: int
    safety_level: str  # "safe", "caution", "unsafe"
    removal_reason: str | None = None


@dataclass
class SpecAnalysis:
    """Analysis result for a specification."""
    name: str
    path: str
    has_requirements: bool
    has_design: bool
    has_tasks: bool
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    incomplete_tasks: int
    completion_percentage: float
    is_complete: bool


@dataclass
class CleanupOpportunity:
    """Represents a cleanup opportunity with safety assessment."""
    category: str
    description: str
    files_affected: list[str]
    safety_level: str
    estimated_impact: str
    recommendation: str
    prerequisites: list[str]


class ProjectCleanupAnalyzer:
    """Analyzes project for cleanup opportunities."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.file_analyses: list[FileAnalysis] = []
        self.spec_analyses: list[SpecAnalysis] = []
        self.cleanup_opportunities: list[CleanupOpportunity] = []

        # Patterns for identifying different file types
        self.temp_patterns = [
            r".*\.tmp$", r".*\.temp$", r".*\.bak$", r".*\.backup$",
            r".*_test\.txt$", r".*_output\.txt$", r".*_debug\.txt$",
            r".*\.log$", r".*\.cache$", r"test_.*\.txt$",
            r"debug_.*\.py$", r".*_demo\.py$", r".*demo.*\.py$"
        ]

        self.config_patterns = [
            r".*\.json$", r".*\.yaml$", r".*\.yml$", r".*\.toml$",
            r".*\.ini$", r".*\.cfg$", r".*\.conf$", r"\.env.*"
        ]

        self.doc_patterns = [
            r".*\.md$", r".*\.rst$", r".*\.txt$", r"README.*",
            r"CHANGELOG.*", r"LICENSE.*", r"CONTRIBUTING.*"
        ]

    def analyze_project(self) -> Dict[str, Any]:
        """Run complete project analysis."""
        print("🔍 Starting project cleanup analysis...")

        # Analyze all files
        self._analyze_files()

        # Analyze specifications
        self._analyze_specifications()

        # Identify cleanup opportunities
        self._identify_cleanup_opportunities()

        # Generate summary
        summary = self._generate_summary()

        print("✅ Project cleanup analysis completed!")
        return summary

    def _analyze_files(self) -> None:
        """Analyze all files in the project."""
        print("📁 Analyzing project files...")

        # Get all files, excluding common ignore patterns
        ignore_dirs = {".git", "__pycache__", ".pytest_cache", ".mypy_cache",
                      ".ruff_cache", "node_modules", ".venv", "venv", "htmlcov"}

        for file_path in self._get_all_files():
            if any(ignore_dir in str(file_path) for ignore_dir in ignore_dirs):
                continue

            analysis = self._analyze_single_file(file_path)
            if analysis:
                self.file_analyses.append(analysis)

    def _get_all_files(self) -> list[Path]:
        """Get all files in the project."""
        files: List[Path] = []
        for root, dirs, filenames in os.walk(self.project_root):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                      {"__pycache__", "node_modules", "venv", "htmlcov"}]

            files.extend(Path(root) / filename for filename in filenames
                        if not filename.startswith("."))
        return files

    def _analyze_single_file(self, file_path: Path) -> FileAnalysis | None:
        """Analyze a single file."""
        try:
            stat = file_path.stat()
            relative_path = str(file_path.relative_to(self.project_root))

            # Determine file characteristics
            is_test = "test" in relative_path.lower() or relative_path.startswith("tests/")
            is_config = any(re.match(pattern, relative_path) for pattern in self.config_patterns)
            is_doc = any(re.match(pattern, relative_path) for pattern in self.doc_patterns)
            is_temp = any(re.match(pattern, relative_path) for pattern in self.temp_patterns)

            # Analyze Python files for imports/exports
            imports: List[str] = []
            exports: List[str] = []
            if file_path.suffix == ".py":
                imports, exports = self._analyze_python_file(file_path)

            # Count references to this file
            references = self._count_file_references(relative_path)

            # Determine safety level
            safety_level = self._assess_file_safety(relative_path, is_test, is_config,
                                                  is_doc, is_temp, references)

            # Determine removal reason if applicable
            removal_reason = None
            if is_temp:
                removal_reason = "Temporary or debug file"
            elif references == 0 and not is_config and not is_doc:
                removal_reason = "No references found"

            return FileAnalysis(
                path=relative_path,
                size_bytes=stat.st_size,
                last_modified=str(stat.st_mtime),
                is_test_file=is_test,
                is_config_file=is_config,
                is_documentation=is_doc,
                is_temporary=is_temp,
                imports=imports,
                exports=exports,
                references_count=references,
                safety_level=safety_level,
                removal_reason=removal_reason
            )

        except Exception as e:
            print(f"⚠️  Error analyzing {file_path}: {e}")
            return None

    def _analyze_python_file(self, file_path: Path) -> tuple[list[str], list[str]]:
        """Analyze Python file for imports and exports."""
        imports: List[str] = []
        exports: List[str] = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                elif isinstance(node, ast.FunctionDef | ast.ClassDef) and not node.name.startswith("_"):
                    exports.append(node.name)

        except Exception as e:
            print(f"⚠️  Error parsing Python file {file_path}: {e}")

        return imports, exports

    def _count_file_references(self, file_path: str) -> int:
        """Count references to a file across the project."""
        references = 0
        file_name = Path(file_path).name
        module_name = Path(file_path).stem

        # Search for imports and references
        try:
            # Use grep to search for references
            patterns = [
                f"import.*{module_name}",
                f"from.*{module_name}",
                f'"{file_path}"',
                f"'{file_path}'",
                file_name
            ]

            for pattern in patterns:
                try:
                    result = subprocess.run(
                        ["grep", "-r", "--include=*.py", pattern, str(self.project_root)],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        references += len(result.stdout.strip().split("\n"))
                except subprocess.TimeoutExpired:
                    pass
                except Exception:
                    pass

        except Exception:
            pass

        return max(0, references - 1)  # Subtract self-reference

    def _assess_file_safety(self, file_path: str, is_test: bool, is_config: bool,
                          is_doc: bool, is_temp: bool, references: int) -> str:
        """Assess safety level for file removal."""
        # Core application files
        if file_path.startswith("src/") and not is_test:
            return "unsafe"

        # Configuration files
        if is_config and file_path in ["pyproject.toml", "uv.lock", ".gitignore"]:
            return "unsafe"

        # Important documentation
        if file_path in ["README.md", "LICENSE", "CHANGELOG.md"]:
            return "unsafe"

        # Temporary files
        if is_temp:
            return "safe"

        # Files with no references
        if references == 0 and not is_config and not is_doc:
            return "caution"

        # Test files
        if is_test:
            return "caution"

        return "caution"

    def _analyze_specifications(self) -> None:
        """Analyze all specifications for completeness."""
        print("📋 Analyzing specifications...")

        specs_dir = self.project_root / ".kiro" / "specs"
        if not specs_dir.exists():
            return

        for spec_dir in specs_dir.iterdir():
            if spec_dir.is_dir():
                analysis = self._analyze_single_spec(spec_dir)
                if analysis:
                    self.spec_analyses.append(analysis)

    def _analyze_single_spec(self, spec_dir: Path) -> SpecAnalysis | None:
        """Analyze a single specification."""
        try:
            spec_name = spec_dir.name

            # Check for required files
            requirements_file = spec_dir / "requirements.md"
            design_file = spec_dir / "design.md"
            tasks_file = spec_dir / "tasks.md"

            has_requirements = requirements_file.exists()
            has_design = design_file.exists()
            has_tasks = tasks_file.exists()

            # Analyze tasks if present
            total_tasks = 0
            completed_tasks = 0
            in_progress_tasks = 0

            if has_tasks:
                total_tasks, completed_tasks, in_progress_tasks = self._analyze_tasks_file(tasks_file)

            incomplete_tasks = total_tasks - completed_tasks - in_progress_tasks
            completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            is_complete = has_requirements and has_design and has_tasks and incomplete_tasks == 0

            return SpecAnalysis(
                name=spec_name,
                path=str(spec_dir.relative_to(self.project_root)),
                has_requirements=has_requirements,
                has_design=has_design,
                has_tasks=has_tasks,
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                in_progress_tasks=in_progress_tasks,
                incomplete_tasks=incomplete_tasks,
                completion_percentage=completion_percentage,
                is_complete=is_complete
            )

        except Exception as e:
            print(f"⚠️  Error analyzing spec {spec_dir}: {e}")
            return None

    def _analyze_tasks_file(self, tasks_file: Path) -> tuple[int, int, int]:
        """Analyze tasks file for completion status."""
        total = completed = in_progress = 0

        try:
            with open(tasks_file, encoding="utf-8") as f:
                content = f.read()

            # Find task lines with checkboxes
            task_pattern = r"^\s*-\s*\[([ x-])\]\s+\d+\.?\d*\.?\s+"

            for line in content.split("\n"):
                match = re.match(task_pattern, line)
                if match:
                    total += 1
                    status = match.group(1)
                    if status == "x":
                        completed += 1
                    elif status == "-":
                        in_progress += 1

        except Exception as e:
            print(f"⚠️  Error analyzing tasks file {tasks_file}: {e}")

        return total, completed, in_progress

    def _identify_cleanup_opportunities(self) -> None:
        """Identify cleanup opportunities based on analysis."""
        print("🧹 Identifying cleanup opportunities...")

        # Temporary files cleanup
        temp_files = [f.path for f in self.file_analyses if f.is_temporary]
        if temp_files:
            self.cleanup_opportunities.append(CleanupOpportunity(
                category="Temporary Files",
                description=f"Remove {len(temp_files)} temporary/debug files",
                files_affected=temp_files,
                safety_level="safe",
                estimated_impact="low",
                recommendation="Remove immediately - these are development artifacts",
                prerequisites=["Verify no active debugging sessions"]
            ))

        # Unused files cleanup
        unused_files = [f.path for f in self.file_analyses
                       if f.references_count == 0 and not f.is_config_file and not f.is_documentation
                       and not f.is_temporary and f.safety_level == "caution"]
        if unused_files:
            self.cleanup_opportunities.append(CleanupOpportunity(
                category="Unused Files",
                description=f"Remove {len(unused_files)} files with no references",
                files_affected=unused_files,
                safety_level="caution",
                estimated_impact="medium",
                recommendation="Review each file before removal - may be entry points or utilities",
                prerequisites=["Code review", "Test suite verification"]
            ))

        # Large files review
        large_files = [f.path for f in self.file_analyses if f.size_bytes > 100000]  # > 100KB
        if large_files:
            self.cleanup_opportunities.append(CleanupOpportunity(
                category="Large Files",
                description=f"Review {len(large_files)} large files for optimization",
                files_affected=large_files,
                safety_level="caution",
                estimated_impact="medium",
                recommendation="Review for potential splitting or optimization",
                prerequisites=["Performance analysis", "Code review"]
            ))

        # Incomplete specifications
        incomplete_specs = [s.name for s in self.spec_analyses if not s.is_complete]
        if incomplete_specs:
            self.cleanup_opportunities.append(CleanupOpportunity(
                category="Incomplete Specifications",
                description=f"Complete or remove {len(incomplete_specs)} incomplete specifications",
                files_affected=[f".kiro/specs/{spec}" for spec in incomplete_specs],
                safety_level="caution",
                estimated_impact="high",
                recommendation="Complete missing documents or archive unused specs",
                prerequisites=["Product owner review", "Development priority assessment"]
            ))

        # Root directory cleanup
        root_files = [f.path for f in self.file_analyses
                     if "/" not in f.path and not f.is_documentation and not f.is_config_file]
        if root_files:
            self.cleanup_opportunities.append(CleanupOpportunity(
                category="Root Directory Cleanup",
                description=f"Organize {len(root_files)} files in project root",
                files_affected=root_files,
                safety_level="caution",
                estimated_impact="low",
                recommendation="Move to appropriate subdirectories or remove if unused",
                prerequisites=["File purpose verification"]
            ))

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate analysis summary."""
        total_files = len(self.file_analyses)
        temp_files = len([f for f in self.file_analyses if f.is_temporary])
        unused_files = len([f for f in self.file_analyses if f.references_count == 0])

        total_specs = len(self.spec_analyses)
        complete_specs = len([s for s in self.spec_analyses if s.is_complete])
        total_tasks = sum(s.total_tasks for s in self.spec_analyses)
        completed_tasks = sum(s.completed_tasks for s in self.spec_analyses)
        incomplete_tasks = sum(s.incomplete_tasks for s in self.spec_analyses)

        return {
            "file_analysis": {
                "total_files": total_files,
                "temporary_files": temp_files,
                "unused_files": unused_files,
                "files_by_safety": {
                    "safe": len([f for f in self.file_analyses if f.safety_level == "safe"]),
                    "caution": len([f for f in self.file_analyses if f.safety_level == "caution"]),
                    "unsafe": len([f for f in self.file_analyses if f.safety_level == "unsafe"])
                }
            },
            "specification_analysis": {
                "total_specifications": total_specs,
                "complete_specifications": complete_specs,
                "incomplete_specifications": total_specs - complete_specs,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "incomplete_tasks": incomplete_tasks,
                "completion_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            },
            "cleanup_opportunities": len(self.cleanup_opportunities),
            "detailed_analyses": {
                "files": [asdict(f) for f in self.file_analyses],
                "specifications": [asdict(s) for s in self.spec_analyses],
                "cleanup_opportunities": [asdict(c) for c in self.cleanup_opportunities]
            }
        }

    def generate_report(self, output_file: str = "project_cleanup_analysis.json") -> Dict[str, Any]:
        """Generate and save analysis report."""
        summary = self.analyze_project()

        # Save detailed JSON report
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)

        # Generate markdown report
        markdown_file = output_file.replace(".json", ".md")
        self._generate_markdown_report(summary, markdown_file)

        print("📊 Reports generated:")
        print(f"   - JSON: {output_file}")
        print(f"   - Markdown: {markdown_file}")

        return summary

    def _generate_markdown_report(self, summary: Dict[str, Any], output_file: str) -> None:
        """Generate markdown report."""
        with open(output_file, "w") as f:
            f.write("# Project Cleanup Analysis Report\n\n")
            f.write(f"Generated on: {os.popen('date').read().strip()}\n\n")

            # Executive Summary
            f.write("## Executive Summary\n\n")
            file_stats = summary["file_analysis"]
            spec_stats = summary["specification_analysis"]

            f.write(f"- **Total Files Analyzed**: {file_stats['total_files']}\n")
            f.write(f"- **Temporary Files**: {file_stats['temporary_files']}\n")
            f.write(f"- **Unused Files**: {file_stats['unused_files']}\n")
            f.write(f"- **Total Specifications**: {spec_stats['total_specifications']}\n")
            f.write(f"- **Incomplete Specifications**: {spec_stats['incomplete_specifications']}\n")
            f.write(f"- **Incomplete Tasks**: {spec_stats['incomplete_tasks']}\n")
            f.write(f"- **Cleanup Opportunities**: {summary['cleanup_opportunities']}\n\n")

            # File Analysis
            f.write("## File Analysis\n\n")
            f.write("### Files by Safety Level\n\n")
            safety_stats = file_stats["files_by_safety"]
            f.write(f"- **Safe to Remove**: {safety_stats['safe']} files\n")
            f.write(f"- **Caution Required**: {safety_stats['caution']} files\n")
            f.write(f"- **Unsafe to Remove**: {safety_stats['unsafe']} files\n\n")

            # Specification Analysis
            f.write("## Specification Analysis\n\n")
            f.write(f"**Overall Completion**: {spec_stats['completion_percentage']:.1f}%\n\n")

            f.write("### Specification Status\n\n")
            for spec in summary["detailed_analyses"]["specifications"]:
                status = "✅ Complete" if spec["is_complete"] else "❌ Incomplete"
                f.write(f"- **{spec['name']}**: {status}\n")
                f.write(f"  - Requirements: {'✅' if spec['has_requirements'] else '❌'}\n")
                f.write(f"  - Design: {'✅' if spec['has_design'] else '❌'}\n")
                f.write(f"  - Tasks: {'✅' if spec['has_tasks'] else '❌'}\n")
                if spec["total_tasks"] > 0:
                    f.write(f"  - Task Progress: {spec['completed_tasks']}/{spec['total_tasks']} "
                           f"({spec['completion_percentage']:.1f}%)\n")
                f.write("\n")

            # Cleanup Opportunities
            f.write("## Cleanup Opportunities\n\n")
            for opportunity in summary["detailed_analyses"]["cleanup_opportunities"]:
                f.write(f"### {opportunity['category']}\n\n")
                f.write(f"**Description**: {opportunity['description']}\n\n")
                f.write(f"**Safety Level**: {opportunity['safety_level'].upper()}\n\n")
                f.write(f"**Estimated Impact**: {opportunity['estimated_impact'].upper()}\n\n")
                f.write(f"**Recommendation**: {opportunity['recommendation']}\n\n")

                if opportunity["prerequisites"]:
                    f.write("**Prerequisites**:\n")
                    for prereq in opportunity["prerequisites"]:
                        f.write(f"- {prereq}\n")
                    f.write("\n")

                if opportunity["files_affected"]:
                    f.write("**Files Affected**:\n")
                    for file_path in opportunity["files_affected"][:10]:  # Limit to first 10
                        f.write(f"- `{file_path}`\n")
                    if len(opportunity["files_affected"]) > 10:
                        f.write(f"- ... and {len(opportunity['files_affected']) - 10} more files\n")
                    f.write("\n")


def main() -> None:
    """Main function."""
    analyzer = ProjectCleanupAnalyzer()
    summary = analyzer.generate_report()

    print("\n🎯 Key Findings:")
    print(f"   - {summary['file_analysis']['temporary_files']} temporary files can be removed")
    print(f"   - {summary['file_analysis']['unused_files']} unused files need review")
    print(f"   - {summary['specification_analysis']['incomplete_specifications']} specifications are incomplete")
    print(f"   - {summary['specification_analysis']['incomplete_tasks']} tasks remain incomplete")
    print(f"   - {summary['cleanup_opportunities']} cleanup opportunities identified")


if __name__ == "__main__":
    main()
