#!/usr/bin/env python3
"""
Quick Demo Repository Timing Test

Tests just the essential commands for demo repositories to get fast feedback.
"""

import subprocess
import time
import sys

def measure_command(command: str, timeout: int = 30) -> tuple:
    """Measure a single command execution time."""
    print(f"⏱️  Testing: {command}")
    
    start_time = time.time()
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        duration = time.time() - start_time
        success = result.returncode == 0
        lines = len(result.stdout.splitlines()) if result.stdout else 0
        
        status = "✅" if success else "❌"
        print(f"   {status} {duration:.2f}s ({lines} lines)")
        
        if not success:
            print(f"   Error: {result.stderr[:100]}...")
            
        return duration, success, lines
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"   ⏰ TIMEOUT after {duration:.2f}s")
        return duration, False, 0
    except Exception as e:
        duration = time.time() - start_time
        print(f"   💥 ERROR: {e}")
        return duration, False, 0

def main():
    """Test key repositories with essential commands only."""
    
    print("🚀 Quick Demo Repository Timing Test")
    print("=" * 50)
    
    # Test repositories (smaller list)
    repos = [
        ("pallets/click", "https://github.com/pallets/click"),
        ("psf/requests", "https://github.com/psf/requests"),
        ("Textualize/rich", "https://github.com/Textualize/rich"),
    ]
    
    results = {}
    
    for repo_name, repo_url in repos:
        print(f"\n🔍 Testing: {repo_name}")
        print("-" * 40)
        
        repo_results = []
        
        # Test 1: Repository overview (should be very fast)
        duration, success, lines = measure_command(
            f"uv run forklift show-repo {repo_url}"
        )
        repo_results.append(("show-repo", duration, success))
        
        if success and duration < 5:  # Only continue if first command is fast
            # Test 2: Fork discovery (limited to 5 forks for speed)
            duration, success, lines = measure_command(
                f"uv run forklift show-forks {repo_url} --max-forks 5"
            )
            repo_results.append(("show-forks", duration, success))
        else:
            print("   ⚠️  Skipping fork analysis (repo overview too slow)")
            repo_results.append(("show-forks", 999, False))
        
        results[repo_name] = repo_results
        
        # Small delay between repositories
        time.sleep(1)
    
    # Summary report
    print("\n" + "=" * 50)
    print("QUICK TIMING SUMMARY")
    print("=" * 50)
    
    for repo_name, repo_results in results.items():
        print(f"\n📊 {repo_name}:")
        
        total_time = 0
        all_success = True
        
        for cmd_name, duration, success in repo_results:
            status = "✅" if success else "❌"
            print(f"   {cmd_name}: {status} {duration:.2f}s")
            
            if success:
                total_time += duration
            else:
                all_success = False
        
        if all_success:
            print(f"   📈 Total demo time: {total_time:.2f}s")
            
            if total_time < 15:
                print(f"   🏆 EXCELLENT for demo (< 15s)")
            elif total_time < 30:
                print(f"   ✅ GOOD for demo (< 30s)")
            else:
                print(f"   ⚠️  SLOW for demo (> 30s)")
        else:
            print(f"   ❌ NOT SUITABLE for demo (has failures)")
    
    # Recommendation
    print(f"\n🎯 RECOMMENDATION:")
    
    suitable_repos = []
    for repo_name, repo_results in results.items():
        total_time = sum(duration for _, duration, success in repo_results if success)
        all_success = all(success for _, _, success in repo_results)
        
        if all_success and total_time < 20:
            suitable_repos.append((repo_name, total_time))
    
    if suitable_repos:
        best_repo = min(suitable_repos, key=lambda x: x[1])
        print(f"   🥇 Best for demo: {best_repo[0]} ({best_repo[1]:.2f}s total)")
        
        print(f"\n📝 Demo script should use:")
        print(f"   Primary: {best_repo[0]}")
        if len(suitable_repos) > 1:
            backup = sorted(suitable_repos, key=lambda x: x[1])[1]
            print(f"   Backup: {backup[0]}")
    else:
        print("   ⚠️  No repositories completed fast enough for smooth demo")
        print("   Consider using smaller repos or pre-cached results")

if __name__ == "__main__":
    main()