#!/usr/bin/env python3
"""
Test timing for originally specified repositories from Forklift specs.
"""

import subprocess
import time

def test_repo_timing(repo_url: str, repo_name: str) -> dict:
    """Test timing for a specific repository."""
    print(f"\n🔍 Testing: {repo_name}")
    print(f"📍 URL: {repo_url}")
    print("-" * 50)
    
    results = {}
    
    # Test 1: Repository overview
    print("⏱️  Testing: show-repo")
    start_time = time.time()
    try:
        result = subprocess.run(
            ["uv", "run", "forklift", "show-repo", repo_url],
            capture_output=True,
            text=True,
            timeout=30
        )
        duration = time.time() - start_time
        success = result.returncode == 0
        
        if success:
            # Extract fork count from output
            lines = result.stdout.splitlines()
            fork_count = "unknown"
            for line in lines:
                if "FORKS:" in line:
                    fork_count = line.split("FORKS:")[1].strip().split()[0]
                    break
            
            print(f"   ✅ {duration:.2f}s - Found {fork_count} forks")
            results['show_repo'] = {'duration': duration, 'success': True, 'forks': fork_count}
        else:
            print(f"   ❌ {duration:.2f}s - Error: {result.stderr[:100]}")
            results['show_repo'] = {'duration': duration, 'success': False, 'error': result.stderr}
            
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"   ⏰ TIMEOUT after {duration:.2f}s")
        results['show_repo'] = {'duration': duration, 'success': False, 'error': 'timeout'}
    
    # Only continue if show-repo was successful and fast
    if results['show_repo']['success'] and results['show_repo']['duration'] < 10:
        # Test 2: Fork discovery (limited)
        print("⏱️  Testing: show-forks (limited to 5)")
        start_time = time.time()
        try:
            result = subprocess.run(
                ["uv", "run", "forklift", "show-forks", repo_url, "--max-forks", "5"],
                capture_output=True,
                text=True,
                timeout=45
            )
            duration = time.time() - start_time
            success = result.returncode == 0
            
            if success:
                lines = len(result.stdout.splitlines())
                print(f"   ✅ {duration:.2f}s - {lines} output lines")
                results['show_forks'] = {'duration': duration, 'success': True, 'lines': lines}
            else:
                print(f"   ❌ {duration:.2f}s - Error: {result.stderr[:100]}")
                results['show_forks'] = {'duration': duration, 'success': False, 'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"   ⏰ TIMEOUT after {duration:.2f}s")
            results['show_forks'] = {'duration': duration, 'success': False, 'error': 'timeout'}
    else:
        print("   ⚠️  Skipping show-forks (show-repo too slow or failed)")
        results['show_forks'] = {'duration': 999, 'success': False, 'error': 'skipped'}
    
    return results

def main():
    """Test the originally specified repositories."""
    print("🚀 Testing Originally Specified Repositories")
    print("=" * 60)
    print("These repositories were mentioned in the original Forklift specs")
    print()
    
    # Originally specified repositories
    test_repos = [
        # Small test repositories
        ("sanila2007/youtube-bot-telegram", "https://github.com/sanila2007/youtube-bot-telegram"),
        ("maliayas/github-network-ninja", "https://github.com/maliayas/github-network-ninja"),
        
        # Production examples with manageable fork counts
        ("newmarcel/KeepingYouAwake", "https://github.com/newmarcel/KeepingYouAwake"),  # 232 forks
        ("xgboosted/pandas-ta-classic", "https://github.com/xgboosted/pandas-ta-classic"),  # 18 forks
        ("aarigs/pandas-ta", "https://github.com/aarigs/pandas-ta"),
        ("NoMore201/googleplay-api", "https://github.com/NoMore201/googleplay-api"),
        ("virattt/ai-hedge-fund", "https://github.com/virattt/ai-hedge-fund"),
    ]
    
    all_results = {}
    
    for repo_name, repo_url in test_repos:
        try:
            results = test_repo_timing(repo_url, repo_name)
            all_results[repo_name] = results
            time.sleep(2)  # Brief pause between repositories
        except KeyboardInterrupt:
            print(f"\n⏹️  Testing interrupted at {repo_name}")
            break
        except Exception as e:
            print(f"\n💥 Error testing {repo_name}: {e}")
            all_results[repo_name] = {'error': str(e)}
    
    # Summary report
    print("\n" + "=" * 60)
    print("TIMING SUMMARY FOR ORIGINAL REPOSITORIES")
    print("=" * 60)
    
    suitable_for_demo = []
    
    for repo_name, results in all_results.items():
        print(f"\n📊 {repo_name}:")
        
        if 'show_repo' in results and results['show_repo']['success']:
            show_repo_time = results['show_repo']['duration']
            forks = results['show_repo'].get('forks', 'unknown')
            print(f"   show-repo: ✅ {show_repo_time:.2f}s ({forks} forks)")
            
            if 'show_forks' in results and results['show_forks']['success']:
                show_forks_time = results['show_forks']['duration']
                total_time = show_repo_time + show_forks_time
                print(f"   show-forks: ✅ {show_forks_time:.2f}s")
                print(f"   📈 Total demo time: {total_time:.2f}s")
                
                if total_time < 20:
                    print(f"   🏆 EXCELLENT for demo")
                    suitable_for_demo.append((repo_name, total_time, forks))
                elif total_time < 40:
                    print(f"   ✅ GOOD for demo")
                    suitable_for_demo.append((repo_name, total_time, forks))
                else:
                    print(f"   ⚠️  SLOW for demo")
            else:
                print(f"   show-forks: ❌ Failed or skipped")
        else:
            print(f"   show-repo: ❌ Failed")
    
    # Final recommendation
    print(f"\n🎯 DEMO RECOMMENDATIONS:")
    
    if suitable_for_demo:
        # Sort by total time
        suitable_for_demo.sort(key=lambda x: x[1])
        
        print(f"\n✅ Suitable repositories (fast execution):")
        for i, (repo_name, total_time, forks) in enumerate(suitable_for_demo[:3]):
            rank = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            print(f"   {rank} {repo_name}: {total_time:.2f}s total ({forks} forks)")
        
        best_repo = suitable_for_demo[0]
        print(f"\n🎬 RECOMMENDED FOR VIDEO:")
        print(f"   Primary: {best_repo[0]} ({best_repo[1]:.2f}s, {best_repo[2]} forks)")
        
        if len(suitable_for_demo) > 1:
            backup_repo = suitable_for_demo[1]
            print(f"   Backup: {backup_repo[0]} ({backup_repo[1]:.2f}s, {backup_repo[2]} forks)")
    else:
        print(f"   ⚠️  No repositories completed fast enough for smooth demo")
        print(f"   Consider using pre-cached results or smaller repositories")
    
    print(f"\n💡 These are the repositories originally specified in Forklift specs")
    print(f"   Using them shows consistency with the original project vision")

if __name__ == "__main__":
    main()