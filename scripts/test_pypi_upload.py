#!/usr/bin/env python3
"""
Simple script to test PyPI upload with better error reporting.
"""

import os
import subprocess
import sys


def main():
    """Test PyPI upload with detailed error reporting."""
    
    # Check if tokens are set
    test_token = os.getenv('TWINE_PASSWORD_TESTPYPI')
    prod_token = os.getenv('TWINE_PASSWORD')
    
    print("🔍 Checking authentication...")
    print(f"Test PyPI token set: {'YES' if test_token else 'NO'}")
    print(f"Production PyPI token set: {'YES' if prod_token else 'NO'}")
    
    if not test_token:
        print("\n❌ TWINE_PASSWORD_TESTPYPI not set!")
        print("Please run: export TWINE_PASSWORD_TESTPYPI='your-test-token'")
        return False
    
    # Check if dist files exist
    import glob
    wheel_files = glob.glob("dist/*.whl")
    tar_files = glob.glob("dist/*.tar.gz")
    
    print(f"\n📦 Package files:")
    print(f"Wheel files: {wheel_files}")
    print(f"Source files: {tar_files}")
    
    if not wheel_files or not tar_files:
        print("❌ Missing package files. Run 'uv build' first.")
        return False
    
    # Try upload with verbose output
    print("\n🚀 Attempting Test PyPI upload...")
    
    cmd = [
        "uv", "run", "python", "-m", "twine", "upload",
        "--repository-url", "https://test.pypi.org/legacy/",
        "--username", "__token__",
        "--password", test_token,
        "--verbose",
        "dist/*"
    ]
    
    print(f"Command: {' '.join(cmd[:8])} [TOKEN_HIDDEN] {' '.join(cmd[9:])}")
    
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print("✅ Upload successful!")
        print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Upload failed with return code {e.returncode}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)