#!/usr/bin/env python3
"""
Kiro Agent Hook Manager

This script manages and executes Kiro agent hooks for automated development workflows.
It can be used to manually trigger hooks or as part of automated processes.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class HookStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class HookResult:
    name: str
    status: HookStatus
    duration: float
    output: str
    error: Optional[str] = None
    auto_fixes_applied: bool = False


class KiroHookManager:
    """Manages and executes Kiro agent hooks"""
    
    def __init__(self, hooks_dir: str = ".kiro/hooks"):
        self.hooks_dir = Path(hooks_dir)
        self.hooks = self._load_hooks()
    
    def _load_hooks(self) -> Dict[str, Dict]:
        """Load all hook configurations from the hooks directory"""
        hooks = {}
        
        if not self.hooks_dir.exists():
            print(f"Hooks directory {self.hooks_dir} does not exist")
            return hooks
        
        for hook_file in self.hooks_dir.glob("*.json"):
            try:
                with open(hook_file, 'r') as f:
                    hook_config = json.load(f)
                    hooks[hook_file.stem] = hook_config
            except Exception as e:
                print(f"Error loading hook {hook_file}: {e}")
        
        return hooks
    
    def list_hooks(self) -> List[str]:
        """List all available hooks"""
        return list(self.hooks.keys())
    
    def get_hook_info(self, hook_name: str) -> Optional[Dict]:
        """Get information about a specific hook"""
        return self.hooks.get(hook_name)
    
    def should_trigger_hook(self, hook_name: str, changed_files: List[str] = None, 
                           branch: str = None, event_type: str = None) -> bool:
        """Determine if a hook should be triggered based on conditions"""
        hook_config = self.hooks.get(hook_name)
        if not hook_config:
            return False
        
        trigger = hook_config.get("trigger", {})
        conditions = hook_config.get("conditions", {})
        
        # Check file patterns
        if changed_files and "patterns" in trigger:
            patterns = trigger["patterns"]
            exclude_patterns = trigger.get("exclude_patterns", [])
            
            # Check if any changed file matches patterns
            matches = False
            for file_path in changed_files:
                # Simple pattern matching (could be enhanced with glob)
                for pattern in patterns:
                    if self._matches_pattern(file_path, pattern):
                        matches = True
                        break
                
                # Check exclude patterns
                for exclude_pattern in exclude_patterns:
                    if self._matches_pattern(file_path, exclude_pattern):
                        matches = False
                        break
                
                if matches:
                    break
            
            if not matches:
                return False
        
        # Check branch patterns
        if branch and "branch_patterns" in conditions:
            branch_patterns = conditions["branch_patterns"]
            if not any(self._matches_pattern(branch, pattern) for pattern in branch_patterns):
                return False
        
        return True
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcards)"""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)
    
    def execute_hook(self, hook_name: str, dry_run: bool = False) -> HookResult:
        """Execute a specific hook"""
        hook_config = self.hooks.get(hook_name)
        if not hook_config:
            return HookResult(
                name=hook_name,
                status=HookStatus.FAILURE,
                duration=0,
                output="",
                error=f"Hook {hook_name} not found"
            )
        
        print(f"Executing hook: {hook_config.get('name', hook_name)}")
        print(f"Description: {hook_config.get('description', 'No description')}")
        
        if dry_run:
            print("DRY RUN - Would execute the following actions:")
            for action in hook_config.get("actions", []):
                print(f"  - {action.get('name', 'Unnamed action')}: {action.get('command', 'No command')}")
            return HookResult(
                name=hook_name,
                status=HookStatus.SUCCESS,
                duration=0,
                output="Dry run completed",
            )
        
        start_time = time.time()
        results = []
        auto_fixes_applied = False
        
        for action in hook_config.get("actions", []):
            action_result = self._execute_action(action)
            results.append(action_result)
            
            if action_result.auto_fixes_applied:
                auto_fixes_applied = True
            
            # Handle failure behavior
            if action_result.status == HookStatus.FAILURE:
                on_failure = action.get("on_failure", "stop")
                if on_failure == "stop":
                    break
        
        duration = time.time() - start_time
        
        # Determine overall status
        if all(r.status == HookStatus.SUCCESS for r in results):
            overall_status = HookStatus.SUCCESS
        elif any(r.status == HookStatus.FAILURE for r in results):
            overall_status = HookStatus.FAILURE
        else:
            overall_status = HookStatus.WARNING
        
        # Combine output
        combined_output = "\n".join(r.output for r in results)
        combined_error = "\n".join(r.error for r in results if r.error)
        
        result = HookResult(
            name=hook_name,
            status=overall_status,
            duration=duration,
            output=combined_output,
            error=combined_error if combined_error else None,
            auto_fixes_applied=auto_fixes_applied
        )
        
        self._send_notification(hook_config, result)
        return result
    
    def _execute_action(self, action: Dict) -> HookResult:
        """Execute a single action within a hook"""
        action_name = action.get("name", "Unnamed action")
        command = action.get("command", "")
        timeout = action.get("timeout", 300)
        
        print(f"  Running: {action_name}")
        
        if not command:
            return HookResult(
                name=action_name,
                status=HookStatus.FAILURE,
                duration=0,
                output="",
                error="No command specified"
            )
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path.cwd()
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                status = HookStatus.SUCCESS
                print(f"    ✅ {action_name} completed successfully ({duration:.2f}s)")
            else:
                status = HookStatus.FAILURE
                print(f"    ❌ {action_name} failed ({duration:.2f}s)")
                
                # Try auto-fix if available
                auto_fix = action.get("auto_fix", {})
                if auto_fix.get("enabled", False) and auto_fix.get("command"):
                    print(f"    🔧 Attempting auto-fix...")
                    fix_result = subprocess.run(
                        auto_fix["command"],
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    
                    if fix_result.returncode == 0:
                        print(f"    ✅ Auto-fix applied successfully")
                        return HookResult(
                            name=action_name,
                            status=HookStatus.SUCCESS,
                            duration=duration,
                            output=result.stdout + "\n" + fix_result.stdout,
                            auto_fixes_applied=True
                        )
            
            return HookResult(
                name=action_name,
                status=status,
                duration=duration,
                output=result.stdout,
                error=result.stderr if result.stderr else None
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"    ⏰ {action_name} timed out after {timeout}s")
            return HookResult(
                name=action_name,
                status=HookStatus.FAILURE,
                duration=duration,
                output="",
                error=f"Command timed out after {timeout} seconds"
            )
        except Exception as e:
            duration = time.time() - start_time
            print(f"    💥 {action_name} failed with exception: {e}")
            return HookResult(
                name=action_name,
                status=HookStatus.FAILURE,
                duration=duration,
                output="",
                error=str(e)
            )
    
    def _send_notification(self, hook_config: Dict, result: HookResult):
        """Send notification based on hook result"""
        notifications = hook_config.get("notifications", {})
        
        if result.status == HookStatus.SUCCESS:
            notification = notifications.get("on_success", {})
        elif result.status == HookStatus.FAILURE:
            notification = notifications.get("on_failure", {})
        else:
            notification = notifications.get("on_partial_success", {})
        
        if notification and notification.get("message"):
            print(f"\n📢 {notification['message']}")
            
            if notification.get("include_summary"):
                print(f"   Duration: {result.duration:.2f}s")
                print(f"   Status: {result.status.value}")
                if result.auto_fixes_applied:
                    print("   Auto-fixes: Applied")
    
    def execute_all_applicable_hooks(self, changed_files: List[str] = None, 
                                   branch: str = None, event_type: str = None,
                                   dry_run: bool = False) -> List[HookResult]:
        """Execute all hooks that should be triggered based on conditions"""
        results = []
        
        for hook_name in self.hooks:
            if self.should_trigger_hook(hook_name, changed_files, branch, event_type):
                result = self.execute_hook(hook_name, dry_run)
                results.append(result)
        
        return results


def main():
    """Main CLI interface for the hook manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kiro Agent Hook Manager")
    parser.add_argument("--list", action="store_true", help="List all available hooks")
    parser.add_argument("--info", type=str, help="Show information about a specific hook")
    parser.add_argument("--execute", type=str, help="Execute a specific hook")
    parser.add_argument("--execute-all", action="store_true", help="Execute all applicable hooks")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be executed without running")
    parser.add_argument("--changed-files", type=str, nargs="*", help="List of changed files")
    parser.add_argument("--branch", type=str, help="Current branch name")
    parser.add_argument("--event", type=str, help="Event type (e.g., pre_commit, pre_merge)")
    
    args = parser.parse_args()
    
    manager = KiroHookManager()
    
    if args.list:
        hooks = manager.list_hooks()
        print("Available hooks:")
        for hook in hooks:
            hook_info = manager.get_hook_info(hook)
            print(f"  - {hook}: {hook_info.get('description', 'No description')}")
    
    elif args.info:
        hook_info = manager.get_hook_info(args.info)
        if hook_info:
            print(f"Hook: {hook_info.get('name', args.info)}")
            print(f"Description: {hook_info.get('description', 'No description')}")
            print(f"Version: {hook_info.get('version', 'Unknown')}")
            print(f"Actions: {len(hook_info.get('actions', []))}")
        else:
            print(f"Hook '{args.info}' not found")
    
    elif args.execute:
        result = manager.execute_hook(args.execute, args.dry_run)
        print(f"\nHook execution completed with status: {result.status.value}")
        if result.error:
            print(f"Errors: {result.error}")
        sys.exit(0 if result.status == HookStatus.SUCCESS else 1)
    
    elif args.execute_all:
        results = manager.execute_all_applicable_hooks(
            changed_files=args.changed_files,
            branch=args.branch,
            event_type=args.event,
            dry_run=args.dry_run
        )
        
        success_count = sum(1 for r in results if r.status == HookStatus.SUCCESS)
        total_count = len(results)
        
        print(f"\nExecuted {total_count} hooks, {success_count} successful")
        
        if total_count > 0 and success_count < total_count:
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()