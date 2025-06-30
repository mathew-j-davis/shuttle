#!/usr/bin/env python3
"""
Command Executor
Executes or dry-runs shell commands with proper logging
"""

import subprocess
from typing import List, Tuple


def run_command(cmd_list: List[str], description: str, dry_run: bool = False, interactive: bool = False) -> bool:
    """
    Execute command or show what would be executed in dry run
    
    Args:
        cmd_list: List of command arguments
        description: Human-readable description of the command
        dry_run: If True, only print what would be executed
        interactive: If True, allow interactive input (don't capture output)
        
    Returns:
        True if successful, False otherwise
    """
    # Build command string with proper quoting
    cmd_str = " ".join([f'"{arg}"' if arg is not None and ' ' in arg else str(arg) for arg in cmd_list])
    
    if dry_run:
        print(f"[DRY RUN] {description}")
        print(f"  Command: {cmd_str}")
        return True
    else:
        print(f"Executing: {description}")
        try:
            if interactive:
                # For interactive commands, don't capture output - let it go to terminal
                result = subprocess.run(cmd_list, check=True)
                print(f"✅ {description} completed")
            else:
                # For non-interactive commands, capture output as before
                result = subprocess.run(cmd_list, check=True, capture_output=True, text=True)
                if result.stdout.strip():
                    print(f"  Output: {result.stdout.strip()}")
                print(f"✅ {description} completed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} failed")
            if hasattr(e, 'stdout') and e.stdout and e.stdout.strip():
                print(f"  stdout: {e.stdout.strip()}")
            if hasattr(e, 'stderr') and e.stderr and e.stderr.strip():
                print(f"  stderr: {e.stderr.strip()}")
            # For interactive commands, the error was already shown to user
            if interactive:
                print(f"  Error: Command exited with status {e.returncode}")
            return False
        except Exception as e:
            print(f"❌ {description} failed with error: {e}")
            return False


def execute_commands(commands: List[Tuple[List[str], str]], dry_run: bool = False, 
                    stop_on_error: bool = True) -> Tuple[int, int]:
    """
    Execute a batch of commands
    
    Args:
        commands: List of (cmd_list, description) tuples
        dry_run: If True, only print what would be executed
        stop_on_error: If True, stop execution on first error
        
    Returns:
        Tuple of (success_count, error_count)
    """
    success_count = 0
    error_count = 0
    
    for cmd_list, description in commands:
        if run_command(cmd_list, description, dry_run):
            success_count += 1
        else:
            error_count += 1
            if stop_on_error and not dry_run:
                print(f"Stopping execution due to error")
                break
    
    return success_count, error_count