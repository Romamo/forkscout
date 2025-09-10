#!/usr/bin/env python3
"""
Demo Repository Timing Measurement Script

This script measures the execution time of Forklift commands on various repositories
to ensure they complete within acceptable timeframes for video recording.
"""

import asyncio
import time
import subprocess
import sys
from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class TimingResult:
    """Result of a command timing measurement."""
    command: str
    repository: str
    duration_seconds: float
    success: bool
    output_lines: int
    error_message: str = ""

class DemoTimingMeasurer:
    """Measures timing for demo repository commands."""
    
    def __init__(self):
        self.results: List[TimingResult] = []
        
    def measure_command(self, command: str, timeout_seconds: int = 60) -> TimingResult:
        """Measure execution time of a forklift command."""
        print(f"⏱️  Measuring: {command}")
        
        start_time = time.time()
        
        try:
            # Run command with timeout
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            
            duration = time.time() - start_time
            output_lines = len(result.stdout.splitlines()) if result.stdout else 0
            
            timing_result = TimingResult(
                command=command,
                repository=self._extract_repo_from_command(command),
                duration_seconds=duration,
                success=result.returncode == 0,
                output_lines=output_lines,
                error_message=result.stderr if result.returncode != 0 else ""
            )
            
            status = "✅" if timing_result.success else "❌"
            print(f"   {status} {duration:.2f}s ({output_lines} lines)")
            
            if not timing_result.success:
                print(f"   Error: {timing_result.error_message[:100]}...")
                
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            timing_result = TimingResult(
                command=command,
                repository=self._extract_repo_from_command(command),
                duration_seconds=duration,
                success=False,
                output_lines=0,
                error_message=f"Command timed out after {timeout_seconds}s"
            )
            print(f"   ⏰ TIMEOUT after {duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            timing_result = TimingResult(
                command=command,
                repository=self._extract_repo_from_command(command),
                duration_seconds=duration,
                success=False,
                output_lines=0,
                error_message=str(e)
            )
            print(f"   💥 ERROR: {str(e)}")
        
        self.results.append(timing_result)
        return timing_result
    
    def _extract_repo_from_command(self, command: str) -> str:
        """Extract repository name from command."""
        parts = command.split()
        for part in parts:
            if "github.com/" in part:
                return part.split("github.com/")[1]
        return "unknown"
    
    def measure_demo_repositories(self) -> Dict[str, List[TimingResult]]:
        """Measure timing for all demo repositories and commands."""
        
        # Demo repositories to test
        demo_repos = [
            "https://github.com/pallets/click",      # Primary demo repo
            "https://github.com/psf/requests",       # Backup demo repo
            "https://github.com/Textualize/rich",    # Alternative small repo
            "https://github.com/pytest-dev/pytest", # Another good option
        ]
        
        # Commands to test for each repository
        commands_template = [
            "uv run forklift show-repo {repo}",
            "uv run forklift show-forks {repo} --max-forks 8",
            "uv run forklift analyze {repo} --max-forks 10 --explain",
        ]
        
        results_by_repo = {}
        
        for repo in demo_repos:
            repo_name = repo.split("github.com/")[1]
            print(f"\n🔍 Testing repository: {repo_name}")
            print("=" * 60)
            
            repo_results = []
            
            for cmd_template in commands_template:
                command = cmd_template.format(repo=repo)
                result = self.measure_command(command, timeout_seconds=45)
                repo_results.append(result)
                
                # Add small delay between commands
                time.sleep(1)
            
            results_by_repo[repo_name] = repo_results
        
        return results_by_repo
    
    def generate_timing_report(self, results_by_repo: Dict[str, List[TimingResult]]) -> str:
        """Generate a comprehensive timing report."""
        
        report_lines = [
            "# Demo Repository Timing Report",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Executive Summary",
            ""
        ]
        
        # Calculate summary statistics
        all_results = [result for results in results_by_repo.values() for result in results]
        successful_results = [r for r in all_results if r.success]
        
        if successful_results:
            avg_time = sum(r.duration_seconds for r in successful_results) / len(successful_results)
            max_time = max(r.duration_seconds for r in successful_results)
            min_time = min(r.duration_seconds for r in successful_results)
            
            report_lines.extend([
                f"- **Total Commands Tested**: {len(all_results)}",
                f"- **Successful Commands**: {len(successful_results)} ({len(successful_results)/len(all_results)*100:.1f}%)",
                f"- **Average Execution Time**: {avg_time:.2f} seconds",
                f"- **Fastest Command**: {min_time:.2f} seconds",
                f"- **Slowest Command**: {max_time:.2f} seconds",
                ""
            ])
        
        # Detailed results by repository
        report_lines.extend([
            "## Detailed Results by Repository",
            ""
        ])
        
        for repo_name, results in results_by_repo.items():
            report_lines.extend([
                f"### {repo_name}",
                ""
            ])
            
            # Repository summary
            successful = [r for r in results if r.success]
            if successful:
                repo_avg = sum(r.duration_seconds for r in successful) / len(successful)
                repo_total = sum(r.duration_seconds for r in successful)
                
                report_lines.extend([
                    f"**Summary**: {len(successful)}/{len(results)} commands successful",
                    f"**Average Time**: {repo_avg:.2f}s | **Total Time**: {repo_total:.2f}s",
                    ""
                ])
            
            # Individual command results
            report_lines.append("| Command | Duration | Status | Output Lines |")
            report_lines.append("|---------|----------|--------|--------------|")
            
            for result in results:
                status_icon = "✅" if result.success else "❌"
                cmd_short = result.command.split()[-1] if result.command else "unknown"
                
                report_lines.append(
                    f"| `{cmd_short}` | {result.duration_seconds:.2f}s | {status_icon} | {result.output_lines} |"
                )
            
            report_lines.append("")
            
            # Show errors if any
            failed_results = [r for r in results if not r.success]
            if failed_results:
                report_lines.extend([
                    "**Errors:**",
                    ""
                ])
                for result in failed_results:
                    report_lines.append(f"- `{result.command}`: {result.error_message[:100]}...")
                report_lines.append("")
        
        # Recommendations
        report_lines.extend([
            "## Recommendations for Demo Recording",
            ""
        ])
        
        # Find best repository for demo
        repo_scores = {}
        for repo_name, results in results_by_repo.items():
            successful = [r for r in results if r.success]
            if successful:
                avg_time = sum(r.duration_seconds for r in successful) / len(successful)
                success_rate = len(successful) / len(results)
                # Score: lower time is better, higher success rate is better
                score = avg_time * (2 - success_rate)  # Penalty for failures
                repo_scores[repo_name] = (score, avg_time, success_rate)
        
        if repo_scores:
            best_repo = min(repo_scores.keys(), key=lambda k: repo_scores[k][0])
            best_score, best_avg, best_success = repo_scores[best_repo]
            
            report_lines.extend([
                f"### Recommended Primary Demo Repository: `{best_repo}`",
                f"- Average execution time: {best_avg:.2f} seconds",
                f"- Success rate: {best_success*100:.1f}%",
                f"- Total demo time estimate: {best_avg * 3:.1f} seconds",
                ""
            ])
        
        # Timing guidelines
        report_lines.extend([
            "### Demo Timing Guidelines",
            "",
            "**Acceptable Timing for Video Recording:**",
            "- `show-repo`: < 5 seconds (quick overview)",
            "- `show-forks`: < 10 seconds (table display)",
            "- `analyze`: < 20 seconds (comprehensive analysis)",
            "",
            "**Total demo segment should complete in < 35 seconds**",
            ""
        ])
        
        # Performance recommendations
        fast_repos = []
        slow_repos = []
        
        for repo_name, results in results_by_repo.items():
            successful = [r for r in results if r.success]
            if successful:
                avg_time = sum(r.duration_seconds for r in successful) / len(successful)
                if avg_time < 10:
                    fast_repos.append((repo_name, avg_time))
                else:
                    slow_repos.append((repo_name, avg_time))
        
        if fast_repos:
            report_lines.extend([
                "### ✅ Fast Repositories (Good for Demo):",
                ""
            ])
            for repo, avg_time in sorted(fast_repos, key=lambda x: x[1]):
                report_lines.append(f"- `{repo}`: {avg_time:.2f}s average")
            report_lines.append("")
        
        if slow_repos:
            report_lines.extend([
                "### ⚠️ Slow Repositories (Avoid for Demo):",
                ""
            ])
            for repo, avg_time in sorted(slow_repos, key=lambda x: x[1]):
                report_lines.append(f"- `{repo}`: {avg_time:.2f}s average")
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def save_report(self, report_content: str, filename: str = "demo_timing_report.md"):
        """Save timing report to file."""
        report_path = Path("demo") / filename
        report_path.write_text(report_content)
        print(f"\n📊 Timing report saved to: {report_path}")

def main():
    """Main execution function."""
    print("🚀 Forklift Demo Repository Timing Measurement")
    print("=" * 60)
    print("This script will test the execution time of Forklift commands")
    print("on various repositories to optimize demo performance.")
    print()
    
    # Check if forklift is available
    try:
        result = subprocess.run(["uv", "run", "forklift", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("❌ Error: Forklift not available or not working")
            print("Please ensure you can run: uv run forklift --version")
            sys.exit(1)
        else:
            print(f"✅ Forklift available: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Error checking Forklift availability: {e}")
        sys.exit(1)
    
    # Create measurer and run tests
    measurer = DemoTimingMeasurer()
    
    print("\n🔍 Starting repository timing measurements...")
    print("This may take several minutes depending on network speed and API limits.")
    print()
    
    try:
        results_by_repo = measurer.measure_demo_repositories()
        
        print("\n📊 Generating timing report...")
        report_content = measurer.generate_timing_report(results_by_repo)
        
        # Save report
        measurer.save_report(report_content)
        
        # Print summary to console
        print("\n" + "=" * 60)
        print("TIMING MEASUREMENT COMPLETE")
        print("=" * 60)
        
        all_results = [result for results in results_by_repo.values() for result in results]
        successful_results = [r for r in all_results if r.success]
        
        if successful_results:
            avg_time = sum(r.duration_seconds for r in successful_results) / len(successful_results)
            print(f"✅ {len(successful_results)}/{len(all_results)} commands successful")
            print(f"⏱️  Average execution time: {avg_time:.2f} seconds")
            
            # Find fastest repository
            repo_times = {}
            for repo_name, results in results_by_repo.items():
                successful = [r for r in results if r.success]
                if successful:
                    repo_times[repo_name] = sum(r.duration_seconds for r in successful) / len(successful)
            
            if repo_times:
                fastest_repo = min(repo_times.keys(), key=lambda k: repo_times[k])
                print(f"🏆 Fastest repository: {fastest_repo} ({repo_times[fastest_repo]:.2f}s avg)")
        
        print(f"\n📋 Full report available in: demo/demo_timing_report.md")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Measurement interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error during measurement: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()