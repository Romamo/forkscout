#!/bin/bash
# Quick script to set PyPI tokens for publication

echo "🔐 Setting PyPI Authentication Tokens"
echo "======================================"

echo ""
echo "Please enter your API tokens:"
echo ""

read -p "Test PyPI token (starts with pypi-): " TEST_TOKEN
read -p "Production PyPI token (starts with pypi-): " PROD_TOKEN

echo ""
echo "Setting environment variables..."

export TWINE_PASSWORD_TESTPYPI="$TEST_TOKEN"
export TWINE_PASSWORD="$PROD_TOKEN"

echo "✅ Tokens set for this session"
echo ""
echo "Now run: uv run scripts/publish_to_pypi.py --test-pypi --production"
echo ""
echo "Or run the commands separately:"
echo "  uv run scripts/publish_to_pypi.py --test-pypi"
echo "  uv run scripts/publish_to_pypi.py --production"