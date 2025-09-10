#!/usr/bin/env python3
"""
Comprehensive submission validation script for Code with Kiro Hackathon 2024.

This script validates all submission requirements and provides a detailed report
of the project's readiness for hackathon submission.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ValidationResult:
    """Result of a validation check."""
    name: str
    passed: bool
    message: str
    details: List[str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = []


class SubmissionValidator:
    """Validates hackathon submission requirements."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results: List[ValidationResult] = []
        
    def validate_all(self) -> Dict[str, Any]:
        """Run all validation checks."""
        print("🔍 Validating Hackathon Submission Requirements...")
        print("=" * 60)
        
        # Core submission requirements
        self._validate_project_structure()
        self._validate_documentation()
        self._validate_kiro_artifacts()
        self._validate_code_quality()
        self._validate_package_distribution()
        self._validate_demo_materials()
        
        # Generate summary
        return self._generate_summary()
    
    def _validate_project_structure(self):
        """Validate basic project structure."""
        print("\n📁 Validating Project Structure...")
        
        required_files = [
            "README.md",
            "LICENSE",
            "pyproject.toml",
            "src/forkscout/__init__.py",
            "HACKATHON_SUBMISSION.md",
            "KIRO_DEVELOPMENT_SHOWCASE.md",
            "PROJECT_VALUE_AND_IMPACT.md",
            "SUBMISSION_CHECKLIST.md"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            self.results.append(ValidationResult(
                "Project Structure",
                False,
                f"Missing {len(missing_files)} required files",
                missing_files
            ))
        else:
            self.results.append(ValidationResult(
                "Project Structure",
                True,
                "All required files present"
            ))
    
    def _validate_documentation(self):
        """Validate documentation completeness."""
        print("📚 Validating Documentation...")
        
        # Check main submission document
        submission_doc = self.project_root / "HACKATHON_SUBMISSION.md"
        if submission_doc.exists():
            content = submission_doc.read_text()
            word_count = len(content.split())
            
            if word_count >= 5000:
                self.results.append(ValidationResult(
                    "Submission Documentation",
                    True,
                    f"Comprehensive documentation ({word_count:,} words)"
                ))
            else:
                self.results.append(ValidationResult(
                    "Submission Documentation",
                    False,
                    f"Documentation too brief ({word_count:,} words, need 5000+)"
                ))
        else:
            self.results.append(ValidationResult(
                "Submission Documentation",
                False,
                "HACKATHON_SUBMISSION.md not found"
            ))
        
        # Check README
        readme = self.project_root / "README.md"
        if readme.exists():
            content = readme.read_text()
            if len(content) > 10000:  # Substantial README
                self.results.append(ValidationResult(
                    "README Documentation",
                    True,
                    f"Comprehensive README ({len(content):,} characters)"
                ))
            else:
                self.results.append(ValidationResult(
                    "README Documentation",
                    False,
                    "README needs more detail"
                ))
    
    def _validate_kiro_artifacts(self):
        """Validate Kiro development artifacts."""
        print("🤖 Validating Kiro Artifacts...")
        
        # Check .kiro directory
        kiro_dir = self.project_root / ".kiro"
        if not kiro_dir.exists():
            self.results.append(ValidationResult(
                "Kiro Directory",
                False,
                ".kiro directory not found"
            ))
            return
        
        # Count specifications
        specs_dir = kiro_dir / "specs"
        if specs_dir.exists():
            spec_count = len(list(specs_dir.iterdir()))
            if spec_count >= 10:
                self.results.append(ValidationResult(
                    "Kiro Specifications",
                    True,
                    f"{spec_count} specifications found"
                ))
            else:
                self.results.append(ValidationResult(
                    "Kiro Specifications",
                    False,
                    f"Only {spec_count} specifications (need 10+)"
                ))
        
        # Count steering files
        steering_dir = kiro_dir / "steering"
        if steering_dir.exists():
            steering_count = len(list(steering_dir.glob("*.md")))
            if steering_count >= 15:
                self.results.append(ValidationResult(
                    "Steering Rules",
                    True,
                    f"{steering_count} steering files found"
                ))
            else:
                self.results.append(ValidationResult(
                    "Steering Rules",
                    False,
                    f"Only {steering_count} steering files (need 15+)"
                ))
    
    def _validate_code_quality(self):
        """Validate code quality metrics."""
        print("✨ Validating Code Quality...")
        
        # Check if tests exist
        tests_dir = self.project_root / "tests"
        if tests_dir.exists():
            test_files = list(tests_dir.rglob("test_*.py"))
            if len(test_files) >= 50:
                self.results.append(ValidationResult(
                    "Test Suite",
                    True,
                    f"{len(test_files)} test files found"
                ))
            else:
                self.results.append(ValidationResult(
                    "Test Suite",
                    False,
                    f"Only {len(test_files)} test files (need 50+)"
                ))
        
        # Check source code structure
        src_dir = self.project_root / "src" / "forkscout"
        if src_dir.exists():
            py_files = list(src_dir.rglob("*.py"))
            if len(py_files) >= 30:
                self.results.append(ValidationResult(
                    "Source Code",
                    True,
                    f"{len(py_files)} Python files in source"
                ))
            else:
                self.results.append(ValidationResult(
                    "Source Code",
                    False,
                    f"Only {len(py_files)} Python files"
                ))
    
    def _validate_package_distribution(self):
        """Validate package distribution readiness."""
        print("📦 Validating Package Distribution...")
        
        # Check pyproject.toml
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            if "name = \"forkscout\"" in content and "version = \"1.0.0\"" in content:
                self.results.append(ValidationResult(
                    "Package Configuration",
                    True,
                    "pyproject.toml properly configured"
                ))
            else:
                self.results.append(ValidationResult(
                    "Package Configuration",
                    False,
                    "pyproject.toml missing required fields"
                ))
        
        # Check if package can be built
        try:
            result = subprocess.run(
                ["uv", "build"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                self.results.append(ValidationResult(
                    "Package Build",
                    True,
                    "Package builds successfully"
                ))
            else:
                self.results.append(ValidationResult(
                    "Package Build",
                    False,
                    f"Build failed: {result.stderr[:200]}"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                "Package Build",
                False,
                f"Build test failed: {str(e)}"
            ))
    
    def _validate_demo_materials(self):
        """Validate demo and presentation materials."""
        print("🎬 Validating Demo Materials...")
        
        # Check demo directory
        demo_dir = self.project_root / "demo"
        if demo_dir.exists():
            demo_files = list(demo_dir.glob("*.md"))
            if len(demo_files) >= 5:
                self.results.append(ValidationResult(
                    "Demo Materials",
                    True,
                    f"{len(demo_files)} demo files prepared"
                ))
            else:
                self.results.append(ValidationResult(
                    "Demo Materials",
                    False,
                    f"Only {len(demo_files)} demo files"
                ))
        
        # Check video script
        video_script = self.project_root / "demo" / "video_script.md"
        if video_script.exists():
            content = video_script.read_text()
            if len(content) > 5000:
                self.results.append(ValidationResult(
                    "Video Script",
                    True,
                    "Comprehensive video script prepared"
                ))
            else:
                self.results.append(ValidationResult(
                    "Video Script",
                    False,
                    "Video script needs more detail"
                ))
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate validation summary."""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        for result in self.results:
            status = "✅" if result.passed else "❌"
            print(f"{status} {result.name}: {result.message}")
            if result.details:
                for detail in result.details[:3]:  # Show first 3 details
                    print(f"   • {detail}")
                if len(result.details) > 3:
                    print(f"   • ... and {len(result.details) - 3} more")
        
        print("\n" + "=" * 60)
        print(f"📈 OVERALL SCORE: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed >= total * 0.8:  # 80% pass rate
            print("🎉 SUBMISSION READY: Project meets hackathon requirements!")
            status = "READY"
        elif passed >= total * 0.6:  # 60% pass rate
            print("⚠️  NEEDS WORK: Some issues need attention before submission")
            status = "NEEDS_WORK"
        else:
            print("❌ NOT READY: Significant issues must be resolved")
            status = "NOT_READY"
        
        return {
            "status": status,
            "score": f"{passed}/{total}",
            "percentage": round(passed/total*100, 1),
            "passed_checks": passed,
            "total_checks": total,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results
            ],
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Main validation function."""
    validator = SubmissionValidator()
    summary = validator.validate_all()
    
    # Save detailed results
    results_file = Path(__file__).parent.parent / "submission_validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    # Exit with appropriate code
    if summary["status"] == "READY":
        sys.exit(0)
    elif summary["status"] == "NEEDS_WORK":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()