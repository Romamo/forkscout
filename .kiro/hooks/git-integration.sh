#!/bin/bash
# Git Integration Script for Kiro Agent Hooks
# This script can be used as a git hook or in CI/CD pipelines

set -e

# Configuration
HOOKS_DIR=".kiro/hooks"
HOOK_MANAGER="$HOOKS_DIR/hook-manager.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to get changed files
get_changed_files() {
    local base_ref=${1:-"HEAD~1"}
    git diff --name-only "$base_ref" HEAD 2>/dev/null || echo ""
}

# Function to get current branch
get_current_branch() {
    git branch --show-current 2>/dev/null || echo "unknown"
}

# Function to check if hook manager exists
check_hook_manager() {
    if [[ ! -f "$HOOK_MANAGER" ]]; then
        print_status $YELLOW "Warning: Kiro hook manager not found at $HOOK_MANAGER"
        return 1
    fi
    return 0
}

# Main execution function
execute_hooks() {
    local event_type=$1
    local dry_run=${2:-false}
    
    print_status $BLUE "🔧 Kiro Agent Hooks - $event_type"
    
    if ! check_hook_manager; then
        print_status $YELLOW "Skipping hook execution"
        return 0
    fi
    
    # Get context information
    local changed_files=($(get_changed_files))
    local current_branch=$(get_current_branch)
    
    print_status $BLUE "Context:"
    print_status $BLUE "  Branch: $current_branch"
    print_status $BLUE "  Changed files: ${#changed_files[@]}"
    
    # Build command
    local cmd="python $HOOK_MANAGER --execute-all"
    cmd="$cmd --branch $current_branch"
    cmd="$cmd --event $event_type"
    
    if [[ ${#changed_files[@]} -gt 0 ]]; then
        cmd="$cmd --changed-files ${changed_files[*]}"
    fi
    
    if [[ "$dry_run" == "true" ]]; then
        cmd="$cmd --dry-run"
        print_status $YELLOW "DRY RUN MODE - No changes will be made"
    fi
    
    # Execute hooks
    print_status $BLUE "Executing applicable hooks..."
    
    if eval $cmd; then
        print_status $GREEN "✅ All hooks completed successfully"
        return 0
    else
        print_status $RED "❌ Some hooks failed"
        return 1
    fi
}

# Pre-commit hook
pre_commit() {
    print_status $BLUE "Running pre-commit hooks..."
    execute_hooks "pre_commit" "$1"
}

# Pre-push hook
pre_push() {
    print_status $BLUE "Running pre-push hooks..."
    execute_hooks "pre_push" "$1"
}

# Post-commit hook
post_commit() {
    print_status $BLUE "Running post-commit hooks..."
    execute_hooks "post_commit" "$1"
}

# CI/CD integration
ci_integration() {
    local stage=${1:-"ci"}
    print_status $BLUE "Running CI/CD hooks for stage: $stage"
    execute_hooks "ci_$stage" "$2"
}

# Manual execution
manual_execution() {
    local hook_name=$1
    local dry_run=${2:-false}
    
    if ! check_hook_manager; then
        exit 1
    fi
    
    if [[ -n "$hook_name" ]]; then
        print_status $BLUE "Executing specific hook: $hook_name"
        local cmd="python $HOOK_MANAGER --execute $hook_name"
        if [[ "$dry_run" == "true" ]]; then
            cmd="$cmd --dry-run"
        fi
        eval $cmd
    else
        print_status $BLUE "Executing all applicable hooks..."
        execute_hooks "manual" "$dry_run"
    fi
}

# List available hooks
list_hooks() {
    if ! check_hook_manager; then
        exit 1
    fi
    
    print_status $BLUE "Available Kiro Agent Hooks:"
    python "$HOOK_MANAGER" --list
}

# Show hook information
show_hook_info() {
    local hook_name=$1
    
    if ! check_hook_manager; then
        exit 1
    fi
    
    if [[ -z "$hook_name" ]]; then
        print_status $RED "Error: Hook name required"
        exit 1
    fi
    
    python "$HOOK_MANAGER" --info "$hook_name"
}

# Help function
show_help() {
    cat << EOF
Kiro Agent Hooks Git Integration

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    pre-commit [--dry-run]     Run pre-commit hooks
    pre-push [--dry-run]       Run pre-push hooks  
    post-commit [--dry-run]    Run post-commit hooks
    ci [STAGE] [--dry-run]     Run CI/CD hooks for specific stage
    manual [HOOK] [--dry-run]  Run hooks manually
    list                       List available hooks
    info HOOK                  Show information about a specific hook
    help                       Show this help message

Options:
    --dry-run                  Show what would be executed without running

Examples:
    $0 pre-commit              # Run pre-commit hooks
    $0 manual --dry-run        # Show what manual execution would do
    $0 manual automated-testing # Run specific hook
    $0 list                    # List all available hooks
    $0 info code-quality-checks # Show info about specific hook

Git Hook Integration:
    To use as git hooks, create symlinks in .git/hooks/:
    ln -s ../../.kiro/hooks/git-integration.sh .git/hooks/pre-commit
    ln -s ../../.kiro/hooks/git-integration.sh .git/hooks/pre-push

EOF
}

# Main script logic
main() {
    case "$1" in
        "pre-commit")
            pre_commit "$2"
            ;;
        "pre-push")
            pre_push "$2"
            ;;
        "post-commit")
            post_commit "$2"
            ;;
        "ci")
            ci_integration "$2" "$3"
            ;;
        "manual")
            manual_execution "$2" "$3"
            ;;
        "list")
            list_hooks
            ;;
        "info")
            show_hook_info "$2"
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        "")
            print_status $YELLOW "No command specified. Use 'help' for usage information."
            show_help
            exit 1
            ;;
        *)
            print_status $RED "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"