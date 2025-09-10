#!/usr/bin/env python3
"""
Interactive PyPI upload script with step-by-step guidance.
"""

import getpass
import subprocess
import sys


def main():
    """Interactive PyPI upload."""
    print("🚀 Interactive PyPI Upload")
    print("=" * 30)
    
    print("\n📋 This script will help you upload to Test PyPI first")
    print("You'll need your Test PyPI API token (starts with 'pypi-')")
    
    # Get token securely
    token = getpass.getpass("\n🔑 Enter your Test PyPI API token: ")
    
    if not token.startswith('pypi-'):
        print("⚠️  Warning: Token doesn't start with 'pypi-'")
        proceed = input("Continue anyway? (y/N): ")
        if proceed.lower() != 'y':
            print("🛑 Upload cancelled")
            return
    
    print("\n🔍 Validating package...")
    
    # Validate first
    try:
        result = subprocess.run([
            "uv", "run", "python", "-m", "twine", "check", "dist/*"
        ], check=True, capture_output=True, text=True)
        print("✅ Package validation passed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Package validation failed: {e.stderr}")
        return
    
    print("\n🚀 Uploading to Test PyPI...")
    
    # Upload to Test PyPI
    cmd = [
        "uv", "run", "python", "-m", "twine", "upload",
        "--repository-url", "https://test.pypi.org/legacy/",
        "--username", "__token__",
        "--password", token,
        "--verbose",
        "dist/*"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, text=True)
        print("\n🎉 Upload to Test PyPI successful!")
        print("\n📋 Next steps:")
        print("1. Check your package: https://test.pypi.org/project/forkscout/")
        print("2. Test installation: pip install --index-url https://test.pypi.org/simple/ forkscout")
        
        # Ask about production upload
        prod_upload = input("\n🤔 Upload to production PyPI now? (y/N): ")
        if prod_upload.lower() == 'y':
            upload_to_production()
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Upload failed!")
        print(f"Error details:")
        if hasattr(e, 'stdout') and e.stdout:
            print(f"Stdout: {e.stdout}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Stderr: {e.stderr}")
        print(f"Return code: {e.returncode}")


def upload_to_production():
    """Upload to production PyPI."""
    print("\n🚀 Production PyPI Upload")
    print("=" * 25)
    
    token = getpass.getpass("\n🔑 Enter your production PyPI API token: ")
    
    print("\n🚀 Uploading to production PyPI...")
    
    cmd = [
        "uv", "run", "python", "-m", "twine", "upload",
        "--username", "__token__",
        "--password", token,
        "--verbose",
        "dist/*"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, text=True)
        print("\n🎉 Upload to production PyPI successful!")
        print("\n📋 Your package is now live:")
        print("1. Package page: https://pypi.org/project/forkscout/")
        print("2. Install with: pip install forkscout")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Production upload failed!")
        print(f"Error details:")
        if hasattr(e, 'stdout') and e.stdout:
            print(f"Stdout: {e.stdout}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Stderr: {e.stderr}")


if __name__ == "__main__":
    main()