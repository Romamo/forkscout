#!/usr/bin/env python3
"""
Basic functionality test for Forklift demo environment.
This script tests the core commands that will be used in the demo video.
"""

import subprocess
import sys
import os
import time

def run_command(cmd, timeout=30):
    """Run a command with timeout and return result."""
    print(f"🔍 Testing: {cmd}")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout} seconds"

def test_basic_commands():
    """Test basic Forklift commands for demo readiness."""
    
    print("🎬 Testing Forklift Demo Environment")
    print("=" * 50)
    
    # Test 1: Check if forklift is available
    success, stdout, stderr = run_command("uv run forklift --version")
    if not success:
        print("❌ Forklift is not available")
        return False
    print("✅ Forklift is available")
    
    # Test 2: Check GitHub token
    if not os.getenv('GITHUB_TOKEN'):
        print("❌ GITHUB_TOKEN not set")
        return False
    print("✅ GitHub token is configured")
    
    # Test 3: Test simple repository info (small repo)
    print("\n📋 Testing repository info command...")
    success, stdout, stderr = run_command(
        "uv run forklift show-repo https://github.com/octocat/Hello-World", 
        timeout=15
    )
    if success and "Hello-World" in stdout:
        print("✅ Repository info command works")
    else:
        print(f"❌ Repository info failed: {stderr}")
        return False
    
    # Test 4: Test fork listing with very small limit
    print("\n🍴 Testing fork listing command...")
    success, stdout, stderr = run_command(
        "uv run forklift list-forks https://github.com/octocat/Hello-World", 
        timeout=20
    )
    if success:
        print("✅ Fork listing command works")
    else:
        print(f"❌ Fork listing failed: {stderr}")
        return False
    
    print("\n🎉 Basic functionality test completed successfully!")
    print("\n📝 Demo Environment Status:")
    print("✅ Forklift CLI is working")
    print("✅ GitHub API access is functional") 
    print("✅ Basic commands execute without errors")
    print("✅ Ready for demo recording")
    
    return True

def main():
    """Main test function."""
    if test_basic_commands():
        print("\n🚀 Demo environment is ready!")
        sys.exit(0)
    else:
        print("\n❌ Demo environment needs fixes before recording")
        sys.exit(1)

if __name__ == "__main__":
    main()