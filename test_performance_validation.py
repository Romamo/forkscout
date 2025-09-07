#!/usr/bin/env python3
"""
Test suite performance validation script.
Validates that different test categories complete within acceptable time limits.
"""

import asyncio
import subprocess
import time
import sys
from typing import Dict, List, Tuple


class TestPerformanceValidator:
    """Validates test suite performance across different categories."""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
    
    def run_test_category(self, name: str, command: List[str], timeout: int = 300) -> Dict:
        """Run a test category and measure performance."""
        print(f"\n🧪 Running {name} tests...")
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse pytest output for test counts
            output_lines = result.stdout.split('\n')
            test_summary = ""
            for line in output_lines:
                if "passed" in line and ("failed" in line or "error" in line or "skipped" in line):
                    test_summary = line.strip()
                    break
            
            return {
                'duration': duration,
                'exit_code': result.returncode,
                'test_summary': test_summary,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                'duration': timeout,
                'exit_code': -1,
                'test_summary': 'TIMEOUT',
                'stdout': '',
                'stderr': f'Test timed out after {timeout} seconds',
                'success': False
            }
        except Exception as e:
            return {
                'duration': 0,
                'exit_code': -2,
                'test_summary': 'ERROR',
                'stdout': '',
                'stderr': str(e),
                'success': False
            }
    
    def validate_performance(self):
        """Run performance validation for different test categories."""
        
        # Test categories with their expected time limits
        test_categories = [
            {
                'name': 'Core Unit Tests',
                'command': ['uv', 'run', 'pytest', 'tests/unit/test_cache_manager.py', 
                           'tests/unit/test_analysis_cache.py', 'tests/unit/test_repository_analyzer.py', 
                           '--tb=short', '-q'],
                'max_time': 30,  # 30 seconds
                'description': 'Fast core unit tests'
            },
            {
                'name': 'Examples Tests',
                'command': ['uv', 'run', 'pytest', 'examples/', '--tb=short', '-q'],
                'max_time': 30,  # 30 seconds
                'description': 'Example tests with async decorators'
            },
            {
                'name': 'Unit Tests Sample',
                'command': ['uv', 'run', 'pytest', 'tests/unit/', '--tb=short', '-q', '--maxfail=5'],
                'max_time': 120,  # 2 minutes
                'description': 'Unit tests (limited failures for speed)'
            },
            {
                'name': 'Integration Tests Sample',
                'command': ['uv', 'run', 'pytest', 'tests/integration/', '--tb=short', '-q', '--maxfail=3'],
                'max_time': 180,  # 3 minutes
                'description': 'Integration tests (limited failures for speed)'
            }
        ]
        
        print("🚀 Starting Test Suite Performance Validation")
        print("=" * 60)
        
        overall_start = time.time()
        
        for category in test_categories:
            result = self.run_test_category(
                category['name'],
                category['command'],
                timeout=category['max_time'] + 30  # Add buffer for timeout
            )
            
            self.results[category['name']] = {
                **result,
                'max_time': category['max_time'],
                'description': category['description']
            }
            
            # Print immediate results
            status = "✅ PASS" if result['success'] and result['duration'] <= category['max_time'] else "❌ FAIL"
            print(f"{status} {category['name']}: {result['duration']:.1f}s (limit: {category['max_time']}s)")
            
            if result['test_summary']:
                print(f"   📊 {result['test_summary']}")
            
            if not result['success']:
                print(f"   ⚠️  Exit code: {result['exit_code']}")
                if result['stderr']:
                    print(f"   🔍 Error: {result['stderr'][:200]}...")
        
        overall_duration = time.time() - overall_start
        
        print("\n" + "=" * 60)
        print("📋 PERFORMANCE VALIDATION SUMMARY")
        print("=" * 60)
        
        all_passed = True
        for name, result in self.results.items():
            max_time = result['max_time']
            duration = result['duration']
            success = result['success']
            
            performance_ok = duration <= max_time
            overall_ok = success and performance_ok
            
            status = "✅ PASS" if overall_ok else "❌ FAIL"
            print(f"{status} {name}")
            print(f"   ⏱️  Duration: {duration:.1f}s / {max_time}s")
            print(f"   🎯 Success: {success}")
            print(f"   📈 Performance: {'OK' if performance_ok else 'SLOW'}")
            
            if not overall_ok:
                all_passed = False
                if not success:
                    print(f"   🚨 Test failures detected")
                if not performance_ok:
                    print(f"   🐌 Exceeded time limit by {duration - max_time:.1f}s")
            
            print()
        
        print(f"⏱️  Total validation time: {overall_duration:.1f}s")
        print(f"🎯 Overall result: {'✅ ALL TESTS MEET PERFORMANCE REQUIREMENTS' if all_passed else '❌ PERFORMANCE ISSUES DETECTED'}")
        
        return all_passed
    
    def generate_report(self):
        """Generate a detailed performance report."""
        print("\n" + "=" * 60)
        print("📊 DETAILED PERFORMANCE REPORT")
        print("=" * 60)
        
        for name, result in self.results.items():
            print(f"\n🔍 {name}")
            print(f"   Description: {result['description']}")
            print(f"   Duration: {result['duration']:.2f}s")
            print(f"   Max Time: {result['max_time']}s")
            print(f"   Exit Code: {result['exit_code']}")
            print(f"   Test Summary: {result['test_summary']}")
            
            if result['stderr'] and result['stderr'].strip():
                print(f"   Errors: {result['stderr'][:300]}...")


def main():
    """Main function to run performance validation."""
    validator = TestPerformanceValidator()
    
    try:
        success = validator.validate_performance()
        validator.generate_report()
        
        if success:
            print("\n🎉 All test categories meet performance requirements!")
            sys.exit(0)
        else:
            print("\n⚠️  Some test categories have performance issues.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Performance validation interrupted by user.")
        sys.exit(2)
    except Exception as e:
        print(f"\n💥 Performance validation failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()