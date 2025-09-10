#!/usr/bin/env python3
"""
Script to publish Forkscout to PyPI.

This script handles the complete PyPI publication process including:
- Package validation
- Test PyPI upload (optional)
- Production PyPI upload
- Post-publication verification

Usage:
    python scripts/publish_to_pypi.py --test-pypi  # Upload to Test PyPI first
    python scripts/publish_to_pypi.py --production # Upload to production PyPI
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔄 {description}...")
    print(f"Command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False


def check_authentication() -> bool:
    """Check authentication setup and provide guidance."""
    import os
    from pathlib import Path
    
    print("\n🔐 Checking authentication setup...")
    
    # Check environment variables
    test_token = os.getenv('TWINE_PASSWORD_TESTPYPI')
    prod_token = os.getenv('TWINE_PASSWORD')
    
    # Check .pypirc file
    pypirc_path = Path.home() / ".pypirc"
    pypirc_exists = pypirc_path.exists()
    
    print(f"Environment variables:")
    print(f"  TWINE_PASSWORD_TESTPYPI: {'✅ SET' if test_token else '❌ NOT SET'}")
    print(f"  TWINE_PASSWORD: {'✅ SET' if prod_token else '❌ NOT SET'}")
    print(f"Configuration file:")
    print(f"  ~/.pypirc: {'✅ EXISTS' if pypirc_exists else '❌ NOT FOUND'}")
    
    if not test_token and not prod_token and not pypirc_exists:
        print("\n❌ No authentication method configured!")
        print("\n🔧 Setup options:")
        print("1. Environment variables (recommended):")
        print("   export TWINE_PASSWORD_TESTPYPI='pypi-your-test-token'")
        print("   export TWINE_PASSWORD='pypi-your-production-token'")
        print("2. Configuration file:")
        print("   Run: uv run python scripts/setup_pypi_auth.py")
        print("3. Interactive upload:")
        print("   Run: uv run python scripts/interactive_upload.py")
        return False
    
    return True


def validate_package() -> bool:
    """Validate the package before publication."""
    print("🔍 Validating package...")
    
    # Check that dist directory exists and has files
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ dist/ directory not found. Run 'uv build' first.")
        return False
    
    wheel_files = list(dist_dir.glob("*.whl"))
    tar_files = list(dist_dir.glob("*.tar.gz"))
    
    if not wheel_files:
        print("❌ No wheel files found in dist/")
        return False
    
    if not tar_files:
        print("❌ No source distribution files found in dist/")
        return False
    
    print(f"✅ Found {len(wheel_files)} wheel file(s) and {len(tar_files)} source distribution(s)")
    
    # Validate package metadata
    if not run_command(["uv", "run", "python", "-m", "twine", "check", "dist/*"], 
                      "Package metadata validation"):
        return False
    
    return True


def publish_to_test_pypi() -> bool:
    """Publish to Test PyPI for validation."""
    print("\n📦 Publishing to Test PyPI...")
    
    # Check for environment variable first
    import os
    test_token = os.getenv('TWINE_PASSWORD_TESTPYPI')
    
    if test_token:
        print("✅ Using TWINE_PASSWORD_TESTPYPI environment variable")
        cmd = [
            "uv", "run", "python", "-m", "twine", "upload",
            "--repository-url", "https://test.pypi.org/legacy/",
            "--username", "__token__",
            "--password", test_token,
            "--verbose",
            "dist/*"
        ]
    else:
        print("⚠️  TWINE_PASSWORD_TESTPYPI not set, using ~/.pypirc or interactive auth")
        cmd = [
            "uv", "run", "python", "-m", "twine", "upload",
            "--repository", "testpypi",
            "--verbose",
            "dist/*"
        ]
    
    success = run_command(cmd, "Test PyPI upload")
    
    if not success:
        print("\n🔧 Troubleshooting Test PyPI upload failure:")
        print("1. Check your Test PyPI API token:")
        print("   - Go to: https://test.pypi.org/manage/account/token/")
        print("   - Create a new token if needed")
        print("   - Set it: export TWINE_PASSWORD_TESTPYPI='pypi-your-token'")
        print("2. Verify your Test PyPI account exists and is verified")
        print("3. Check if the package name 'forkscout' is already taken on Test PyPI")
        print("4. Try the interactive upload: uv run python scripts/interactive_upload.py")
    
    return success


def publish_to_production_pypi() -> bool:
    """Publish to production PyPI."""
    print("\n🚀 Publishing to production PyPI...")
    
    # Check for environment variable first
    import os
    pypi_token = os.getenv('TWINE_PASSWORD')
    
    if pypi_token:
        print("✅ Using TWINE_PASSWORD environment variable")
        cmd = [
            "uv", "run", "python", "-m", "twine", "upload",
            "--username", "__token__",
            "--password", pypi_token,
            "--verbose",
            "dist/*"
        ]
    else:
        print("⚠️  TWINE_PASSWORD not set, using ~/.pypirc or interactive auth")
        cmd = [
            "uv", "run", "python", "-m", "twine", "upload",
            "--verbose",
            "dist/*"
        ]
    
    success = run_command(cmd, "Production PyPI upload")
    
    if not success:
        print("\n🔧 Troubleshooting Production PyPI upload failure:")
        print("1. Check your PyPI API token:")
        print("   - Go to: https://pypi.org/manage/account/token/")
        print("   - Create a new token if needed")
        print("   - Set it: export TWINE_PASSWORD='pypi-your-token'")
        print("2. Verify your PyPI account exists and is verified")
        print("3. Check if the package name 'forkscout' is already taken on PyPI")
        print("4. Ensure you have the rights to upload this package")
        print("5. Try the interactive upload: uv run python scripts/interactive_upload.py")
    
    return success


def verify_publication(test_pypi: bool = False) -> bool:
    """Verify that the package was published successfully."""
    repository = "Test PyPI" if test_pypi else "PyPI"
    print(f"\n🔍 Verifying publication on {repository}...")
    
    # Try to install the package from PyPI
    if test_pypi:
        cmd = [
            "uv", "pip", "install", 
            "--index-url", "https://test.pypi.org/simple/",
            "--extra-index-url", "https://pypi.org/simple/",
            "forkscout==1.0.5"
        ]
    else:
        cmd = ["uv", "pip", "install", "forkscout==1.0.5"]
    
    return run_command(cmd, f"Package installation from {repository}")


def main():
    """Main publication workflow."""
    parser = argparse.ArgumentParser(description="Publish Forkscout to PyPI")
    parser.add_argument("--test-pypi", action="store_true", 
                       help="Publish to Test PyPI first")
    parser.add_argument("--production", action="store_true",
                       help="Publish to production PyPI")
    parser.add_argument("--skip-validation", action="store_true",
                       help="Skip package validation")
    
    args = parser.parse_args()
    
    if not args.test_pypi and not args.production:
        print("❌ Please specify either --test-pypi or --production")
        sys.exit(1)
    
    print("🚀 Starting PyPI publication process...")
    
    # Check authentication setup
    import os
    test_token = os.getenv('TWINE_PASSWORD_TESTPYPI')
    prod_token = os.getenv('TWINE_PASSWORD')
    
    print(f"\n🔐 Authentication Status:")
    print(f"Test PyPI token: {'✅ SET' if test_token else '❌ NOT SET'}")
    print(f"Production PyPI token: {'✅ SET' if prod_token else '❌ NOT SET'}")
    
    if args.test_pypi and not test_token:
        print("\n⚠️  Warning: Test PyPI token not set as environment variable")
        print("Set it with: export TWINE_PASSWORD_TESTPYPI='pypi-your-token'")
        print("Or the script will try to use ~/.pypirc or prompt interactively")
    
    if args.production and not prod_token:
        print("\n⚠️  Warning: Production PyPI token not set as environment variable")
        print("Set it with: export TWINE_PASSWORD='pypi-your-token'")
        print("Or the script will try to use ~/.pypirc or prompt interactively")
    
    # Step 1: Check authentication
    if not check_authentication():
        print("❌ Authentication setup incomplete. Please configure authentication first.")
        sys.exit(1)
    
    # Step 2: Validate package
    if not args.skip_validation:
        if not validate_package():
            print("❌ Package validation failed. Aborting publication.")
            sys.exit(1)
    
    # Step 3: Install twine if not available
    print("\n📦 Ensuring twine is available...")
    if not run_command(["uv", "add", "--dev", "twine"], "Installing twine"):
        print("❌ Failed to install twine. Aborting publication.")
        sys.exit(1)
    
    # Step 4: Publish to Test PyPI if requested
    if args.test_pypi:
        if not publish_to_test_pypi():
            print("\n❌ Test PyPI publication failed.")
            print("\n🆘 Quick fixes to try:")
            print("1. Run the interactive script: uv run python scripts/interactive_upload.py")
            print("2. Set your token: export TWINE_PASSWORD_TESTPYPI='pypi-your-token'")
            print("3. Check ~/.pypirc file exists and has correct format")
            print("4. Verify Test PyPI account: https://test.pypi.org/account/login/")
            sys.exit(1)
        
        # Verify Test PyPI publication
        if not verify_publication(test_pypi=True):
            print("⚠️  Test PyPI verification failed, but continuing...")
    
    # Step 5: Publish to production PyPI if requested
    if args.production:
        if args.test_pypi:
            response = input("\n✅ Test PyPI publication successful. Continue with production PyPI? (y/N): ")
            if response.lower() != 'y':
                print("🛑 Production publication cancelled by user.")
                sys.exit(0)
        
        if not publish_to_production_pypi():
            print("\n❌ Production PyPI publication failed.")
            print("\n🆘 Quick fixes to try:")
            print("1. Run the interactive script: uv run python scripts/interactive_upload.py")
            print("2. Set your token: export TWINE_PASSWORD='pypi-your-token'")
            print("3. Check ~/.pypirc file exists and has correct format")
            print("4. Verify PyPI account: https://pypi.org/account/login/")
            print("5. Check if package name is available: https://pypi.org/project/forkscout/")
            sys.exit(1)
        
        # Verify production PyPI publication
        if not verify_publication(test_pypi=False):
            print("⚠️  Production PyPI verification failed, but package may still be available.")
    
    print("\n🎉 PyPI publication process completed successfully!")
    print("\n📋 Next steps:")
    if args.test_pypi and not args.production:
        print("1. Check the package page on Test PyPI: https://test.pypi.org/project/forkscout/")
        print("2. Test installation: pip install --index-url https://test.pypi.org/simple/ forkscout")
    elif args.production:
        print("1. Check the package page on PyPI: https://pypi.org/project/forkscout/")
        print("2. Test installation: pip install forkscout")
    print("3. Update documentation with installation instructions")


if __name__ == "__main__":
    main()