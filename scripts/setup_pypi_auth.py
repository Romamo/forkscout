#!/usr/bin/env python3
"""
Script to help set up PyPI authentication.

This script guides you through setting up PyPI credentials for publishing.
"""

import os
import sys
from pathlib import Path


def main():
    """Guide user through PyPI setup."""
    print("🔐 PyPI Authentication Setup")
    print("=" * 40)
    
    print("\n📋 Before proceeding, you need:")
    print("1. Test PyPI account: https://test.pypi.org/account/register/")
    print("2. PyPI account: https://pypi.org/account/register/")
    print("3. API tokens from both accounts")
    print("   - Test PyPI: https://test.pypi.org/manage/account/token/")
    print("   - PyPI: https://pypi.org/manage/account/token/")
    
    response = input("\n✅ Have you completed the above steps? (y/N): ")
    if response.lower() != 'y':
        print("\n🛑 Please complete the setup steps first, then run this script again.")
        sys.exit(0)
    
    print("\n🔧 Choose authentication method:")
    print("1. Environment variables (recommended for CI/CD)")
    print("2. Configuration file (~/.pypirc)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        setup_environment_variables()
    elif choice == "2":
        setup_config_file()
    else:
        print("❌ Invalid choice. Please run the script again.")
        sys.exit(1)


def setup_environment_variables():
    """Set up environment variables for PyPI authentication."""
    print("\n🌍 Setting up environment variables...")
    
    print("\n📝 Add these to your shell profile (.bashrc, .zshrc, etc.):")
    print("export TWINE_PASSWORD_TESTPYPI='your-test-pypi-token-here'")
    print("export TWINE_PASSWORD='your-pypi-token-here'")
    
    print("\n💡 For this session, you can also run:")
    print("export TWINE_PASSWORD_TESTPYPI='your-test-pypi-token-here'")
    print("export TWINE_PASSWORD='your-pypi-token-here'")
    
    print("\n✅ After setting these variables, you can run:")
    print("uv run scripts/publish_to_pypi.py --test-pypi --production")


def setup_config_file():
    """Set up ~/.pypirc configuration file."""
    print("\n📁 Setting up ~/.pypirc configuration file...")
    
    pypirc_path = Path.home() / ".pypirc"
    
    if pypirc_path.exists():
        response = input(f"\n⚠️  {pypirc_path} already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("🛑 Setup cancelled.")
            return
    
    test_token = input("\n🔑 Enter your Test PyPI API token: ").strip()
    if not test_token.startswith('pypi-'):
        print("⚠️  Warning: Test PyPI tokens usually start with 'pypi-'")
    
    pypi_token = input("🔑 Enter your PyPI API token: ").strip()
    if not pypi_token.startswith('pypi-'):
        print("⚠️  Warning: PyPI tokens usually start with 'pypi-'")
    
    config_content = f"""[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = {pypi_token}

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = {test_token}
"""
    
    try:
        with open(pypirc_path, 'w') as f:
            f.write(config_content)
        
        # Set secure permissions
        os.chmod(pypirc_path, 0o600)
        
        print(f"\n✅ Configuration saved to {pypirc_path}")
        print("🔒 File permissions set to 600 (owner read/write only)")
        
        print("\n✅ You can now run:")
        print("uv run scripts/publish_to_pypi.py --test-pypi --production")
        
    except Exception as e:
        print(f"\n❌ Failed to create configuration file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()