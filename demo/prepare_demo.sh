#!/bin/bash

# Demo Preparation Script for Forklift Hackathon Video
# This script sets up the environment and validates demo scenarios

set -e

echo "🎬 Preparing Forklift Demo Environment..."

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install uv first."
    exit 1
fi

# Check if GitHub token is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN environment variable is not set."
    echo "Please set your GitHub token: export GITHUB_TOKEN=your_token_here"
    exit 1
fi

# Check if forklift is installed
if ! uv run forklift --help &> /dev/null; then
    echo "❌ Forklift is not properly installed."
    echo "Please run: uv sync && uv pip install -e ."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Set up demo directory
echo "📁 Setting up demo directory..."
mkdir -p demo/outputs
mkdir -p demo/cache

# Configure terminal for optimal recording
echo "🖥️  Configuring terminal settings..."
export TERM=xterm-256color
export COLUMNS=120
export LINES=30

# Test GitHub API connectivity
echo "🔗 Testing GitHub API connectivity..."
if ! curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit > /dev/null; then
    echo "❌ GitHub API connectivity test failed."
    echo "Please check your GitHub token and network connection."
    exit 1
fi

# Check rate limit
RATE_LIMIT=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit | grep -o '"remaining":[0-9]*' | cut -d':' -f2)
echo "📊 GitHub API rate limit remaining: $RATE_LIMIT"

if [ "$RATE_LIMIT" -lt 500 ]; then
    echo "⚠️  Warning: Low rate limit remaining ($RATE_LIMIT). Consider waiting or using a different token."
fi

# Validate demo repositories
echo "🔍 Validating demo repositories..."

# Test VSCode repository access
echo "  Testing microsoft/vscode..."
if ! uv run forklift show-repo https://github.com/microsoft/vscode --config demo/vscode-demo-config.yaml > demo/outputs/vscode-test.txt 2>&1; then
    echo "❌ VSCode repository test failed. Check demo/outputs/vscode-test.txt for details."
    exit 1
fi

# Test FastAPI repository access (backup)
echo "  Testing tiangolo/fastapi..."
if ! uv run forklift show-repo https://github.com/tiangolo/fastapi --config demo/fastapi-demo-config.yaml > demo/outputs/fastapi-test.txt 2>&1; then
    echo "❌ FastAPI repository test failed. Check demo/outputs/fastapi-test.txt for details."
    exit 1
fi

echo "✅ Repository validation passed"

# Pre-warm cache for smooth demo execution
echo "🔥 Pre-warming cache for demo repositories..."

echo "  Pre-warming VSCode data..."
uv run forklift show-forks https://github.com/microsoft/vscode --max-forks 5 --config demo/vscode-demo-config.yaml > demo/outputs/vscode-forks-cache.txt 2>&1

echo "  Pre-warming FastAPI data..."
uv run forklift show-forks https://github.com/tiangolo/fastapi --max-forks 5 --config demo/fastapi-demo-config.yaml > demo/outputs/fastapi-forks-cache.txt 2>&1

echo "✅ Cache pre-warming completed"

# Generate sample outputs for reference
echo "📄 Generating sample outputs for reference..."

# VSCode sample analysis
echo "  Generating VSCode sample analysis..."
uv run forklift show-forks https://github.com/microsoft/vscode --detail --max-forks 10 --config demo/vscode-demo-config.yaml > demo/outputs/vscode-sample-analysis.txt 2>&1

# FastAPI sample analysis
echo "  Generating FastAPI sample analysis..."
uv run forklift show-forks https://github.com/tiangolo/fastapi --detail --max-forks 8 --config demo/fastapi-demo-config.yaml > demo/outputs/fastapi-sample-analysis.txt 2>&1

echo "✅ Sample outputs generated"

# Validate demo commands
echo "🧪 Validating demo commands..."

# Test all demo commands with short timeouts
DEMO_COMMANDS=(
    "forklift show-repo https://github.com/microsoft/vscode --config demo/vscode-demo-config.yaml"
    "forklift show-forks https://github.com/microsoft/vscode --detail --max-forks 5 --config demo/vscode-demo-config.yaml"
    "forklift show-repo https://github.com/tiangolo/fastapi --config demo/fastapi-demo-config.yaml"
    "forklift show-forks https://github.com/tiangolo/fastapi --ahead-only --max-forks 5 --config demo/fastapi-demo-config.yaml"
)

for i, cmd in "${!DEMO_COMMANDS[@]}"; do
    echo "  Testing command $((i+1))/4..."
    if ! timeout 30 uv run $cmd > demo/outputs/command-test-$((i+1)).txt 2>&1; then
        echo "❌ Command $((i+1)) failed or timed out. Check demo/outputs/command-test-$((i+1)).txt"
        exit 1
    fi
done

echo "✅ All demo commands validated"

# Create demo execution checklist
cat > demo/execution_checklist.md << 'EOF'
# Demo Execution Checklist

## Pre-Recording Setup
- [ ] Terminal configured (120x30, dark theme, 14pt font)
- [ ] GitHub token verified and rate limit checked (>500 remaining)
- [ ] Screen recording software ready (1080p minimum)
- [ ] Audio input tested and optimized
- [ ] Lighting setup for clear screen visibility
- [ ] Network connectivity stable

## Demo Environment
- [ ] Clean terminal with no previous output
- [ ] Demo configurations validated
- [ ] Cache pre-warmed for smooth execution
- [ ] Backup scenarios ready

## Recording Segments
- [ ] Segment 1: Repository overview (15 seconds)
- [ ] Segment 2: Fork discovery (20 seconds)  
- [ ] Segment 3: Commit analysis (25 seconds)
- [ ] Segment 4: Report generation (10 seconds)

## Post-Recording
- [ ] Video quality verified (clear text, smooth playback)
- [ ] Audio quality checked (clear narration, no background noise)
- [ ] Timing verified against script
- [ ] Backup recordings saved

## Emergency Procedures
- [ ] Pre-recorded outputs ready if live demo fails
- [ ] Alternative repository scenarios prepared
- [ ] Static screenshots available as fallback
- [ ] Troubleshooting guide accessible
EOF

# Display final status
echo ""
echo "🎉 Demo preparation completed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Review demo/execution_checklist.md"
echo "   2. Check sample outputs in demo/outputs/"
echo "   3. Practice demo commands with timing"
echo "   4. Set up recording environment"
echo ""
echo "📊 Demo readiness status:"
echo "   ✅ Environment configured"
echo "   ✅ API connectivity verified"
echo "   ✅ Cache pre-warmed"
echo "   ✅ Commands validated"
echo "   ✅ Sample outputs generated"
echo ""
echo "🎬 Ready to record! Good luck with your demo!"