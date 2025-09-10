#!/usr/bin/env python3
"""
Script to verify that Forkscout is ready for PyPI publication.

This script performs comprehensive checks to ensure the package
is properly configured and ready for publication to PyPI.
"""

import json
import subprocess
import sys
import zipfile
from pathlib import Path


def check_version_consistency() -> bool:
    """Check that versions are consistent across files."""
    print("🔍 Checking version consistency...")
    
    # Read version from pyproject.toml
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("❌ pyproject.toml not found")
        return False
    
    pyproject_content = pyproject_path.read_text()
    pyproject_version = None
    for line in pyproject_content.split('\n'):
        if line.strip().startswith('version = '):
            pyproject_version = line.split('=')[1].strip().strip('"')
            break
    
    if not pyproject_version:
        print("❌ Version not found in pyproject.toml")
        return False
    
    # Read version from __init__.py
    init_path = Path("src/forkscout/__init__.py")
    if not init_path.exists():
        print("❌ src/forkscout/__init__.py not found")
        return False
    
    init_content = init_path.read_text()
    init_version = None
    for line in init_content.split('\n'):
        if line.strip().startswith('__version__ = '):
            init_version = line.split('=')[1].strip().strip('"')
            break
    
    if not init_version:
        print("❌ __version__ not found in __init__.py")
        return False
    
    if pyproject_version != init_version:
        print(f"❌ Version mismatch: pyproject.toml={pyproject_version}, __init__.py={init_version}")
        return False
    
    print(f"✅ Version consistency check passed: {pyproject_version}")
    return True


def check_build_artifacts() -> bool:
    """Check that build artifacts exist and are valid."""
    print("🔍 Checking build artifacts...")
    
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ dist/ directory not found. Run 'uv build' first.")
        return False
    
    # Check for wheel file
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        print("❌ No wheel files found in dist/")
        return False
    
    # Check for source distribution
    tar_files = list(dist_dir.glob("*.tar.gz"))
    if not tar_files:
        print("❌ No source distribution files found in dist/")
        return False
    
    print(f"✅ Found {len(wheel_files)} wheel file(s) and {len(tar_files)} source distribution(s)")
    
    # Validate wheel contents
    wheel_file = wheel_files[0]
    try:
        with zipfile.ZipFile(wheel_file, 'r') as zf:
            files = zf.namelist()
            
            # Check for main module
            if not any(f.startswith('forkscout/') for f in files):
                print("❌ Wheel does not contain forkscout module")
                return False
            
            # Check for CLI entry point
            if not any('entry_points.txt' in f for f in files):
                print("❌ Wheel does not contain entry points")
                return False
            
            # Check for metadata
            if not any('METADATA' in f for f in files):
                print("❌ Wheel does not contain metadata")
                return False
            
        print("✅ Wheel file structure is valid")
        
    except Exception as e:
        print(f"❌ Error validating wheel file: {e}")
        return False
    
    return True


def check_package_metadata() -> bool:
    """Check package metadata completeness."""
    print("🔍 Checking package metadata...")
    
    try:
        result = subprocess.run(
            ["uv", "run", "python", "-m", "twine", "check", "dist/*"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if "PASSED" in result.stdout:
            print("✅ Package metadata validation passed")
            return True
        else:
            print(f"❌ Package metadata validation failed: {result.stdout}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Twine check failed: {e.stderr}")
        return False


def check_dependencies() -> bool:
    """Check that all dependencies are properly specified."""
    print("🔍 Checking dependencies...")
    
    # Extract and check wheel metadata
    dist_dir = Path("dist")
    wheel_files = list(dist_dir.glob("*.whl"))
    
    if not wheel_files:
        print("❌ No wheel files found")
        return False
    
    wheel_file = wheel_files[0]
    
    try:
        with zipfile.ZipFile(wheel_file, 'r') as zf:
            # Find METADATA file
            metadata_files = [f for f in zf.namelist() if f.endswith('METADATA')]
            if not metadata_files:
                print("❌ No METADATA file found in wheel")
                return False
            
            metadata_content = zf.read(metadata_files[0]).decode('utf-8')
            
            # Check for required dependencies
            required_deps = [
                'httpx', 'click', 'pydantic', 'pydantic-settings', 
                'pyyaml', 'rich', 'asyncio-throttle', 'aiosqlite',
                'openai', 'gitpython', 'aiohttp'
            ]
            
            missing_deps = []
            for dep in required_deps:
                if f"Requires-Dist: {dep}" not in metadata_content:
                    missing_deps.append(dep)
            
            if missing_deps:
                print(f"❌ Missing dependencies in metadata: {missing_deps}")
                return False
            
            print("✅ All required dependencies are specified")
            return True
            
    except Exception as e:
        print(f"❌ Error checking dependencies: {e}")
        return False


def check_cli_functionality() -> bool:
    """Check that CLI functionality works after installation."""
    print("🔍 Checking CLI functionality...")
    
    try:
        # Test version command
        result = subprocess.run(
            ["uv", "run", "forkscout", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if "forkscout, version" in result.stdout:
            print("✅ CLI version command works")
        else:
            print(f"❌ Unexpected version output: {result.stdout}")
            return False
        
        # Test help command
        result = subprocess.run(
            ["uv", "run", "forkscout", "--help"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if "Forkscout - GitHub repository fork analysis tool" in result.stdout:
            print("✅ CLI help command works")
            return True
        else:
            print(f"❌ Unexpected help output: {result.stdout}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ CLI functionality check failed: {e.stderr}")
        return False


def check_readme_and_license() -> bool:
    """Check that README and LICENSE files are present and valid."""
    print("🔍 Checking README and LICENSE files...")
    
    readme_path = Path("README.md")
    if not readme_path.exists():
        print("❌ README.md not found")
        return False
    
    readme_content = readme_path.read_text()
    if len(readme_content) < 1000:
        print("❌ README.md seems too short (less than 1000 characters)")
        return False
    
    if "# Forkscout" not in readme_content:
        print("❌ README.md doesn't contain expected title")
        return False
    
    print("✅ README.md is present and looks good")
    
    license_path = Path("LICENSE")
    if not license_path.exists():
        print("❌ LICENSE file not found")
        return False
    
    license_content = license_path.read_text()
    if "MIT License" not in license_content:
        print("❌ LICENSE file doesn't contain MIT License text")
        return False
    
    print("✅ LICENSE file is present and valid")
    return True


def main():
    """Run all PyPI readiness checks."""
    print("🚀 Verifying PyPI publication readiness for Forkscout...\n")
    
    checks = [
        ("Version Consistency", check_version_consistency),
        ("Build Artifacts", check_build_artifacts),
        ("Package Metadata", check_package_metadata),
        ("Dependencies", check_dependencies),
        ("CLI Functionality", check_cli_functionality),
        ("README and LICENSE", check_readme_and_license),
    ]
    
    passed_checks = 0
    total_checks = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n{'='*50}")
        print(f"Running: {check_name}")
        print('='*50)
        
        if check_func():
            passed_checks += 1
        else:
            print(f"❌ {check_name} check failed")
    
    print(f"\n{'='*50}")
    print("SUMMARY")
    print('='*50)
    print(f"Passed: {passed_checks}/{total_checks} checks")
    
    if passed_checks == total_checks:
        print("\n🎉 All checks passed! Forkscout is ready for PyPI publication.")
        print("\nNext steps:")
        print("1. Run: python scripts/publish_to_pypi.py --test-pypi")
        print("2. Test installation from Test PyPI")
        print("3. Run: python scripts/publish_to_pypi.py --production")
        return 0
    else:
        print(f"\n❌ {total_checks - passed_checks} check(s) failed. Please fix the issues before publishing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())