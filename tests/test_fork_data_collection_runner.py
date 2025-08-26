"""Test runner for comprehensive fork data collection system testing."""

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest


class ForkDataCollectionTestRunner:
    """Comprehensive test runner for fork data collection system."""

    def __init__(self):
        """Initialize test runner."""
        self.test_results = {}
        self.start_time = None
        self.total_time = None

    def run_all_tests(self, include_online=False, include_performance=False):
        """Run all fork data collection tests."""
        print("=" * 80)
        print("COMPREHENSIVE FORK DATA COLLECTION SYSTEM TESTS")
        print("=" * 80)
        
        self.start_time = time.time()
        
        # Test categories to run
        test_categories = [
            ("Unit Tests", self._run_unit_tests),
            ("Integration Tests", self._run_integration_tests),
        ]
        
        if include_online:
            test_categories.append(("Online Tests", self._run_online_tests))
            
        if include_performance:
            test_categories.append(("Performance Tests", self._run_performance_tests))
            test_categories.append(("End-to-End Tests", self._run_e2e_tests))

        # Run each test category
        for category_name, test_func in test_categories:
            print(f"\n{'-' * 60}")
            print(f"Running {category_name}")
            print(f"{'-' * 60}")
            
            try:
                result = test_func()
                self.test_results[category_name] = {
                    "status": "PASSED" if result == 0 else "FAILED",
                    "exit_code": result,
                }
                print(f"{category_name}: {'PASSED' if result == 0 else 'FAILED'}")
                
            except Exception as e:
                self.test_results[category_name] = {
                    "status": "ERROR",
                    "exit_code": -1,
                    "error": str(e),
                }
                print(f"{category_name}: ERROR - {e}")

        self.total_time = time.time() - self.start_time
        self._print_summary()

    def _run_unit_tests(self):
        """Run unit tests for fork data collection."""
        unit_test_files = [
            "tests/unit/test_fork_data_collection_engine.py",
            "tests/unit/test_fork_list_processor.py", 
            "tests/unit/test_fork_qualification_models.py",
            "tests/unit/test_fork_data_collection_comprehensive.py",
        ]
        
        args = ["-v", "--tb=short"] + unit_test_files
        return pytest.main(args)

    def _run_integration_tests(self):
        """Run integration tests for fork data collection."""
        integration_test_files = [
            "tests/integration/test_fork_data_collection_integration.py",
            "tests/integration/test_cli_fork_data_display.py",
        ]
        
        args = ["-v", "--tb=short", "-m", "integration"] + integration_test_files
        return pytest.main(args)

    def _run_online_tests(self):
        """Run online tests with real GitHub API."""
        if not os.getenv("GITHUB_TOKEN"):
            print("Skipping online tests - GITHUB_TOKEN not set")
            return 0
            
        args = [
            "-v", "--tb=short", "-m", "integration",
            "tests/integration/test_fork_data_collection_integration.py"
        ]
        return pytest.main(args)

    def _run_performance_tests(self):
        """Run performance tests."""
        args = [
            "-v", "--tb=short", "-m", "performance",
            "tests/performance/test_fork_data_collection_performance.py"
        ]
        return pytest.main(args)

    def _run_e2e_tests(self):
        """Run end-to-end tests."""
        if not os.getenv("GITHUB_TOKEN"):
            print("Skipping E2E tests - GITHUB_TOKEN not set")
            return 0
            
        args = [
            "-v", "--tb=short", "-m", "e2e",
            "tests/e2e/test_fork_data_collection_e2e.py"
        ]
        return pytest.main(args)

    def _print_summary(self):
        """Print test execution summary."""
        print("\n" + "=" * 80)
        print("TEST EXECUTION SUMMARY")
        print("=" * 80)
        
        total_categories = len(self.test_results)
        passed_categories = sum(1 for r in self.test_results.values() if r["status"] == "PASSED")
        failed_categories = sum(1 for r in self.test_results.values() if r["status"] == "FAILED")
        error_categories = sum(1 for r in self.test_results.values() if r["status"] == "ERROR")
        
        print(f"Total test categories: {total_categories}")
        print(f"Passed: {passed_categories}")
        print(f"Failed: {failed_categories}")
        print(f"Errors: {error_categories}")
        print(f"Total execution time: {self.total_time:.2f} seconds")
        
        print(f"\nDetailed Results:")
        for category, result in self.test_results.items():
            status_symbol = "✓" if result["status"] == "PASSED" else "✗"
            print(f"  {status_symbol} {category}: {result['status']}")
            if "error" in result:
                print(f"    Error: {result['error']}")
        
        # Overall status
        overall_status = "PASSED" if failed_categories == 0 and error_categories == 0 else "FAILED"
        print(f"\nOverall Status: {overall_status}")
        
        return overall_status == "PASSED"

    def run_specific_test_suite(self, suite_name):
        """Run a specific test suite."""
        suite_map = {
            "unit": self._run_unit_tests,
            "integration": self._run_integration_tests,
            "online": self._run_online_tests,
            "performance": self._run_performance_tests,
            "e2e": self._run_e2e_tests,
        }
        
        if suite_name not in suite_map:
            print(f"Unknown test suite: {suite_name}")
            print(f"Available suites: {', '.join(suite_map.keys())}")
            return False
            
        print(f"Running {suite_name} tests...")
        result = suite_map[suite_name]()
        return result == 0

    def validate_test_environment(self):
        """Validate test environment setup."""
        print("Validating test environment...")
        
        issues = []
        
        # Check required test files exist
        required_files = [
            "tests/unit/test_fork_data_collection_engine.py",
            "tests/unit/test_fork_list_processor.py",
            "tests/unit/test_fork_qualification_models.py",
            "tests/unit/test_fork_data_collection_comprehensive.py",
            "tests/integration/test_fork_data_collection_integration.py",
            "tests/performance/test_fork_data_collection_performance.py",
            "tests/e2e/test_fork_data_collection_e2e.py",
        ]
        
        for file_path in required_files:
            if not Path(file_path).exists():
                issues.append(f"Missing test file: {file_path}")
        
        # Check source files exist
        required_source_files = [
            "src/forklift/analysis/fork_data_collection_engine.py",
            "src/forklift/github/fork_list_processor.py",
            "src/forklift/models/fork_qualification.py",
        ]
        
        for file_path in required_source_files:
            if not Path(file_path).exists():
                issues.append(f"Missing source file: {file_path}")
        
        # Check environment variables for online tests
        if not os.getenv("GITHUB_TOKEN"):
            issues.append("GITHUB_TOKEN environment variable not set (online tests will be skipped)")
        
        if issues:
            print("Environment validation issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("Environment validation: PASSED")
            return True

    def generate_test_report(self, output_file="test_report.md"):
        """Generate a markdown test report."""
        if not self.test_results:
            print("No test results to report")
            return
            
        report_content = f"""# Fork Data Collection System Test Report

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
Total Execution Time: {self.total_time:.2f} seconds

## Test Categories

"""
        
        for category, result in self.test_results.items():
            status_emoji = "✅" if result["status"] == "PASSED" else "❌"
            report_content += f"### {status_emoji} {category}\n\n"
            report_content += f"- Status: {result['status']}\n"
            report_content += f"- Exit Code: {result['exit_code']}\n"
            
            if "error" in result:
                report_content += f"- Error: {result['error']}\n"
            
            report_content += "\n"
        
        # Summary
        total_categories = len(self.test_results)
        passed_categories = sum(1 for r in self.test_results.values() if r["status"] == "PASSED")
        
        report_content += f"""## Summary

- Total Categories: {total_categories}
- Passed: {passed_categories}
- Failed: {total_categories - passed_categories}
- Success Rate: {passed_categories / total_categories * 100:.1f}%

## Test Coverage

This test suite provides comprehensive coverage of the fork data collection system:

1. **Unit Tests**: Test individual components with realistic data
2. **Integration Tests**: Test component interactions with real repositories
3. **Performance Tests**: Measure API call reduction and processing efficiency
4. **Contract Tests**: Validate GitHub API response handling
5. **End-to-End Tests**: Complete workflow validation with real data

## Key Features Tested

- Fork data collection from GitHub API
- Commits ahead detection using timestamp comparison
- API call optimization and efficiency measurement
- Data validation and error handling
- Performance benchmarks and scalability
- Real repository integration testing
"""
        
        with open(output_file, 'w') as f:
            f.write(report_content)
        
        print(f"Test report generated: {output_file}")


def main():
    """Main entry point for test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fork Data Collection Test Runner")
    parser.add_argument("--suite", choices=["unit", "integration", "online", "performance", "e2e", "all"],
                       default="all", help="Test suite to run")
    parser.add_argument("--include-online", action="store_true", 
                       help="Include online tests (requires GITHUB_TOKEN)")
    parser.add_argument("--include-performance", action="store_true",
                       help="Include performance and E2E tests")
    parser.add_argument("--validate-env", action="store_true",
                       help="Validate test environment only")
    parser.add_argument("--generate-report", action="store_true",
                       help="Generate test report")
    
    args = parser.parse_args()
    
    runner = ForkDataCollectionTestRunner()
    
    if args.validate_env:
        success = runner.validate_test_environment()
        sys.exit(0 if success else 1)
    
    if args.suite == "all":
        runner.run_all_tests(
            include_online=args.include_online,
            include_performance=args.include_performance
        )
    else:
        success = runner.run_specific_test_suite(args.suite)
        sys.exit(0 if success else 1)
    
    if args.generate_report:
        runner.generate_test_report()
    
    # Exit with appropriate code
    overall_success = all(r["status"] == "PASSED" for r in runner.test_results.values())
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()