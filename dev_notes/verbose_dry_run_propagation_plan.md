# Verbose and Dry-Run Flag Propagation Refactoring Plan

## Problem Statement

Currently, when running installation/configuration scripts with `--verbose` or `--dry-run` flags, we only see the Python module calls but not the actual shell commands that would be executed. This creates a visibility gap where users cannot see what system changes would actually be made.

### Current Behavior
```bash
# What we see now with --dry-run:
$ ./scripts/2_post_install_config.sh --dry-run
[DRY RUN] python3 -m user_group_manager config.yaml /path/to/scripts --dry-run

# What we want to see:
$ ./scripts/2_post_install_config.sh --dry-run
[DRY RUN] python3 -m user_group_manager config.yaml /path/to/scripts --dry-run
  [DRY RUN] /path/to/scripts/12_users_and_groups.sh create-user shuttle_service ...
    [DRY RUN] useradd -m -s /bin/bash -g shuttle_users shuttle_service
    [DRY RUN] usermod -aG shuttle_admins shuttle_service
```

## Architecture Analysis - Current State Audit

### Current Call Chain Patterns

1. **Shell → Python → Shell** (❌ **BROKEN: Missing --verbose propagation**)
   ```
   2_post_install_config.sh
   └── python3 -m user_group_manager [args]  # Missing --verbose flag
       └── command_executor.run_command()     # Has dry_run but no verbose
           └── subprocess.run("12_users_and_groups.sh create-user")
               └── execute_or_dryrun("useradd ...")  # ✅ This level works
   ```

2. **Shell → Shell → Shell** (✅ **WORKING: Good flag propagation**)
   ```
   1_install.sh
   └── 01_sudo_install_python.sh --dry-run --verbose  # ✅ Flags propagated
       └── execute_or_dryrun("apt-get install python3")  # ✅ Respects flags
   ```

3. **Python → Python → Shell** (❌ **BROKEN: No flag support**)
   ```
   post_install_config_wizard.py          # No --verbose argument support
   └── user_group_manager.py             # Has --dry-run, no --verbose
       └── command_executor.run_command() # No verbose parameter
   ```

4. **Shell → Python (terminal)** (❌ **BROKEN: No flag support**)
   ```
   2_post_install_config.sh
   └── python3 -m config_analyzer config.yaml  # Missing --verbose --dry-run
       (displays analysis, no further commands)
   ```

### ✅ What's Working Well
- `execute_or_dryrun()` and `execute_or_execute_dryrun()` in shell scripts
- Environment variable export in main scripts (DRY_RUN, VERBOSE)
- Shell-to-shell flag propagation via `add_dry_run_flag()` helper
- All `_cmd_*.source.sh` files properly use execution wrappers

### ❌ What's Broken
- **Shell → Python calls missing --verbose flag** (5 locations in 2_post_install_config.sh)
- **Python modules don't accept --verbose argument** (4 modules need updates)
- **command_executor.py missing verbose parameter** (core utility needs enhancement)
- **Direct command execution** in some installation scripts (pip install, mkdir, python3 -m venv)
- **No flag propagation** from Python modules to shell scripts

### Key Execution Points - Current vs Needed

1. **Shell Script Functions** (✅ **Working**):
   - `execute()` - read-only commands with verbose logging
   - `execute_or_dryrun()` - respects DRY_RUN and VERBOSE environment variables
   - `execute_or_execute_dryrun()` - passes --dry-run to child scripts

2. **Python Execution Functions** (❌ **Needs work**):
   - `command_executor.run_command()` - has dry_run but **no verbose parameter**
   - Various `subprocess.run()` calls - **don't consider environment variables**
   - **No standard execution framework** like shell scripts have

3. **Flag Sources** (⚠️ **Partial**):
   - Environment variables: `$DRY_RUN`, `$VERBOSE` (✅ exported from main scripts)
   - Command-line arguments: `--dry-run`, `--verbose` (❌ not all Python modules support)
   - Python module arguments: **inconsistent support across modules**

### Specific Issues Found

**HIGH PRIORITY FIXES:**
1. **2_post_install_config.sh lines 357, 455, 476, 508, 562** - Replace direct Python calls with `execute_or_execute_dryrun_python_module()`
2. **4 Python modules** need --verbose argument support: config_analyzer, user_group_manager, permission_manager, samba_manager
3. **command_executor.py** needs simple enhancement - add verbose parameter and env var fallback to existing `run_command()`
4. **Installation scripts** have direct commands not using execution wrappers

**WORKING WELL:**
1. **execute_or_execute_dryrun()** - Proven function that handles dry-run, logging, and command history
2. **All _cmd_*.source.sh files** properly use execute_or_dryrun()
3. **Main script flag export** (DRY_RUN, VERBOSE environment variables)
4. **Shell-to-shell propagation** via existing execution functions
5. **Existing command_executor.py** - Just needs minor enhancement, not rewrite

## Refactoring Strategy

### Phase 1: Create Unified Execution Framework

#### 1.1 Shell Execution Library Enhancement
Create new function in `_common_.source.sh` that builds on existing execute_or_execute_dryrun():

```bash
# Function for executing Python modules with automatic flag propagation
# Builds on execute_or_execute_dryrun to maintain consistency
execute_or_execute_dryrun_python_module() {
    local module_name="$1"
    local base_args="$2"
    local success_msg="$3"
    local error_msg="$4"
    local explanation="${5:-}"
    
    # Build the base Python command
    local cmd="python3 -m $module_name"
    
    # Add base arguments if provided
    if [[ -n "$base_args" ]]; then
        cmd="$cmd $base_args"
    fi
    
    # Add --verbose flag if VERBOSE is true
    # (--dry-run is handled by execute_or_execute_dryrun)
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        cmd="$cmd --verbose"
    fi
    
    # Call the existing function which handles --dry-run automatically
    execute_or_execute_dryrun "$cmd" "$success_msg" "$error_msg" "$explanation"
}
```

**Key advantages of this approach:**
- Reuses existing `execute_or_execute_dryrun()` functionality
- Maintains consistent logging and command history
- --dry-run flag automatically appended by parent function
- Same parameter pattern as other execution functions
- No duplicate execution logic

#### 1.2 Python Execution Framework Enhancement
Enhance existing `command_executor.py` with minimal changes:

```python
# Simple enhancement to existing run_command function
def run_command(cmd_list: List[str], description: str, dry_run: bool = False, 
                verbose: bool = False, interactive: bool = False) -> bool:
    """
    Execute command or show what would be executed in dry run
    
    Args:
        cmd_list: Command and arguments as list
        description: Human readable description
        dry_run: If True, show command but don't execute (check env var as fallback)
        verbose: If True, show command even when executing (check env var as fallback)
        interactive: If True, don't capture output
    """
    import os
    
    # Check environment variables as fallback
    if not dry_run:
        dry_run = os.environ.get('DRY_RUN', 'false').lower() == 'true'
    if not verbose:
        verbose = os.environ.get('VERBOSE', 'false').lower() == 'true'
    
    cmd_str = " ".join([f'"{arg}"' if ' ' in arg else arg for arg in cmd_list])
    
    # Show command if verbose OR dry-run
    if verbose or dry_run:
        if dry_run:
            print(f"[DRY RUN] {description}")
        else:
            print(f"Executing: {description}")
        print(f"  Command: {cmd_str}")
    
    if dry_run:
        return True
    
    # Rest of existing implementation stays exactly the same...
    # [existing try/except blocks unchanged]


# Simple helper for shell script execution with flag propagation
def run_script_with_flags(script_path: str, base_args: List[str], description: str,
                         dry_run: bool = False, verbose: bool = False) -> bool:
    """Run shell script with automatic flag propagation"""
    import os
    cmd = [script_path] + base_args
    
    # Add flags if they should be propagated  
    if verbose or os.environ.get('VERBOSE', 'false').lower() == 'true':
        cmd.append('--verbose')
    if dry_run or os.environ.get('DRY_RUN', 'false').lower() == 'true':
        cmd.append('--dry-run')
        
    return run_command(cmd, description, dry_run, verbose)
```

**Key simplifications:**
- No ExecutionContext class - just enhance existing function
- Environment variable check as simple fallback
- Minimal code changes to existing function
- One helper function for flag propagation to scripts

### Phase 2: Update Python Modules

#### 2.1 Critical Module Updates (Based on Audit Findings)

**IMMEDIATE FIXES NEEDED:**

**File: `config_analyzer.py`** (Called from line 357 in 2_post_install_config.sh)
- ❌ **Currently**: No argument parsing, only takes config file positionally
- ✅ **Needs**: `--verbose` and `--dry-run` argument support

**File: `user_group_manager.py`** (Called from line 455)
- ✅ **Has**: `--dry-run`, `--shuttle-config-path`
- ❌ **Missing**: `--verbose` argument support
- ❌ **Problem**: Uses subprocess without flag propagation

**File: `permission_manager.py`** (Called from line 476)
- ✅ **Has**: `--dry-run`, `--shuttle-config-path`
- ❌ **Missing**: `--verbose` argument support

**File: `samba_manager.py`** (Called from line 508)
- ✅ **Has**: `--dry-run`, `--non-interactive`, `--shuttle-config-path`
- ❌ **Missing**: `--verbose` argument support

**File: `post_install_config_wizard.py`** (Called from line 562)
- ❌ **Currently**: No `--verbose` or `--dry-run` support
- ❌ **Problem**: Has subprocess call to shell without flag propagation

#### 2.2 Standard Pattern for Module Updates

**Step 1: Add argument parsing (all modules need this pattern)**
```python
def main():
    parser = argparse.ArgumentParser()
    # Existing arguments...
    parser.add_argument('--verbose', action='store_true', 
                       help='Show detailed execution information')
    if 'dry_run' not in [action.dest for action in parser._actions]:
        parser.add_argument('--dry-run', action='store_true',
                           help='Show what would be done without making changes')
    
    args = parser.parse_args()
    # That's it - no ExecutionContext needed
```

**Step 2: Replace direct subprocess calls**
```python
# OLD (current problematic pattern):
subprocess.run(['bash', script_path, 'create-user', username], check=True)

# NEW (with flag propagation):
from command_executor import run_script_with_flags
run_script_with_flags(
    script_path, 
    ['create-user', username],
    f"Creating user {username}",
    dry_run=args.dry_run,
    verbose=args.verbose
)
```

**Step 3: Update existing command_executor usage**
```python
# OLD (current in some modules):
from command_executor import run_command
run_command(['some', 'command'], 'description', dry_run=args.dry_run)

# NEW (just add verbose parameter):
run_command(['some', 'command'], 'description', dry_run=args.dry_run, verbose=args.verbose)
```

### Phase 3: Update Shell Scripts

#### 3.1 High-Priority Script Updates (Based on Audit)

**CRITICAL: `2_post_install_config.sh`** (5 Python calls need fixing)
```bash
# Line 357 - BEFORE:
python3 -m config_analyzer "$CONFIG_FILE"

# Line 357 - AFTER:
execute_python_module_with_flags "config_analyzer" "\"$CONFIG_FILE\"" \
    "Configuration analysis complete" \
    "Configuration analysis failed" \
    "Analyze YAML configuration structure and settings"

# Lines 455, 476, 508 - Similar pattern for other modules
```

**MEDIUM: Installation Scripts** (Direct commands need wrapping)
- `02_env_and_venv.sh` - Lines 97-99, 196: `mkdir` and `python3 -m venv` calls
- `08_install_shared.sh`, `10_install_shuttle.sh` - Lines 31-35: `pip install` calls

**LOW: Other scripts** (Already working well)
- `1_install.sh` - ✅ Already uses `add_dry_run_flag()` helper correctly
- `_cmd_*.source.sh` files - ✅ Already use `execute_or_dryrun()` correctly

#### 3.2 Updated Patterns for Script Updates

**For Python module calls (use new helper):**
```bash
# OLD (problematic):
python3 -m user_group_manager "$CONFIG_FILE" "$PRODUCTION_DIR" $dry_run_flag

# NEW (with proper flag propagation):
execute_or_execute_dryrun_python_module "user_group_manager" \
    "\"$CONFIG_FILE\" \"$PRODUCTION_DIR\"" \
    "User and group configuration complete" \
    "User and group configuration failed" \
    "Configure system users and groups according to YAML specification"
```

**For direct commands (use existing wrappers):**
```bash
# OLD (direct execution):
mkdir -p "$VENV_PATH"
python3 -m venv "$VENV_PATH"
pip install -e .

# NEW (with proper execution wrapping):
execute_or_dryrun "mkdir -p \"$VENV_PATH\"" \
    "Virtual environment directory created" \
    "Failed to create virtual environment directory" \
    "Create directory for Python virtual environment"

execute_or_dryrun "python3 -m venv \"$VENV_PATH\"" \
    "Virtual environment created" \
    "Failed to create virtual environment" \
    "Create isolated Python virtual environment for shuttle"
```

**Note:** The `execute_or_execute_dryrun_python_module()` function handles all flag propagation automatically, so there's no need for manual flag addition patterns. The function:
- Adds `--verbose` when VERBOSE=true
- Adds `--dry-run` when DRY_RUN=true (via execute_or_execute_dryrun)
- Maintains command history and logging
- Shows commands when verbose or dry-run is enabled

### Phase 4: Handle Special Cases

#### 4.1 Scripts That Need Flag Awareness
Some shell scripts (like `12_users_and_groups.sh`) need to accept and handle flags:

```bash
# Add to script header
VERBOSE=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        # ... other arguments ...
    esac
done

# Export for child processes
export VERBOSE
export DRY_RUN
```

#### 4.2 Terminal Python Modules
Some Python modules (like `config_analyzer.py`) only display information and don't execute commands. These need minimal changes:
- Accept `--verbose` for detailed output
- Accept `--dry-run` for consistency (even if it doesn't change behavior)

## Implementation Order (Revised Based on Audit)

### Priority 1: Fix Immediate Blockers (High Impact, Quick Wins)
1. **Enhance `command_executor.py`** - Add verbose parameter and environment variable checking to existing `run_command()`
2. **Add Python module execution function to `_common_.source.sh`** - `execute_or_execute_dryrun_python_module()`
3. **Fix `2_post_install_config.sh`** - Update 5 Python module calls (lines 357, 455, 476, 508, 562)

### Priority 2: Add Missing Flag Support (Medium Impact)
1. **Update 4 Python modules** - Add --verbose argument support:
   - `config_analyzer.py` (currently has no argument parsing)
   - `user_group_manager.py` (add --verbose to existing args)
   - `permission_manager.py` (add --verbose to existing args)
   - `samba_manager.py` (add --verbose to existing args)
2. **Update `post_install_config_wizard.py`** - Add full flag support

### Priority 3: Wrap Direct Commands (Low Impact, Good Practice)
1. **Fix installation script direct commands**:
   - `02_env_and_venv.sh` - Wrap mkdir and python3 -m venv calls
   - `08_install_shared.sh` - Wrap pip install calls
   - `10_install_shuttle.sh` - Wrap pip install calls

### Priority 4: Polish and Consistency (Future Improvements)
1. **Create comprehensive integration tests** for flag propagation
2. **Add verbose output examples** to help text
3. **Document the unified execution patterns** for future development
4. **Consider environment variable fallbacks** for Python modules

### Already Working Well (No Changes Needed)
- ✅ `1_install.sh` - Flag propagation working with `add_dry_run_flag()`
- ✅ All `_cmd_*.source.sh` files - Properly use `execute_or_dryrun()`
- ✅ Environment variable export from main scripts
- ✅ Shell-to-shell flag propagation

## Testing Strategy

### Unit Tests
1. Test `ExecutionContext` with mock subprocess
2. Test flag propagation logic
3. Test indentation and output formatting

### Integration Tests
1. Create test YAML configurations
2. Run with `--dry-run --verbose` and verify output
3. Compare actual commands that would be executed
4. Test multi-level propagation (shell → python → shell → shell)

### Manual Testing Checklist
- [ ] Run `1_install.sh --dry-run --verbose`
- [ ] Run `2_post_install_config.sh --dry-run --verbose`
- [ ] Verify all commands shown with proper indentation
- [ ] Verify no actual system changes in dry-run mode
- [ ] Test with only `--verbose` (commands execute, output shown)
- [ ] Test with only `--dry-run` (commands not executed)

## Backwards Compatibility

### Maintaining Compatibility
1. All changes should be additive (new functions, not replacing)
2. Existing scripts without flags should work unchanged
3. Environment variables continue to work as fallback

### Migration Path
1. Add new functions alongside existing ones
2. Gradually update scripts to use new functions
3. Mark old patterns as deprecated after full migration
4. Remove deprecated code in future release

## Success Criteria (Updated)

### Immediate Success (Priority 1-2 complete)
1. **Python Module Visibility**: `--verbose` flag shows all subprocess commands from Python modules
2. **Consistent Flag Support**: All Python modules accept `--verbose` and `--dry-run` arguments
3. **Automatic Propagation**: `execute_or_execute_dryrun_python_module()` automatically adds flags
4. **Environment Variable Integration**: Python modules respect DRY_RUN/VERBOSE environment variables
5. **Unified Execution Pattern**: Python modules called same way as shell scripts

### Full Success (All priorities complete)
6. **Complete Command Visibility**: All system commands shown in verbose mode, regardless of call depth
7. **Consistent Infrastructure**: Both shell and Python scripts use same execution patterns
8. **Command History**: All Python module executions logged in command history
9. **Safe Dry-Run**: No system changes at any level when dry-run enabled

### Specific Test Cases
- ✅ `./scripts/2_post_install_config.sh --dry-run --verbose` shows all commands that would be executed
- ✅ Python modules called with `--verbose` show their subprocess commands
- ✅ Environment variables properly propagated through multi-level calls
- ✅ Installation scripts with `--verbose` show pip install, mkdir, etc. commands
- ✅ Flag propagation works: shell → python → shell → system command
- ✅ Command history includes Python module executions with timestamps

## Risks and Mitigation

### Risk 1: Circular Dependencies
**Mitigation**: Careful module design to avoid Python modules importing each other

### Risk 2: Flag Explosion
**Mitigation**: Limit to --verbose and --dry-run; other flags don't propagate

### Risk 3: Output Overload
**Mitigation**: 
- Use existing command_executor.py patterns for clean output
- Implement indentation levels for nested calls
- Only show commands in verbose mode, not all debug info

### Risk 4: Performance Impact
**Mitigation**: 
- Environment variable checking is very fast (os.environ.get())
- Argument parsing overhead is minimal
- Most overhead is in I/O (command execution) not flag checking

### Risk 5: Regression in Working Code
**Mitigation**:
- Phase 1 focuses only on adding missing --verbose support
- Don't change existing dry-run mechanisms that work
- Test both with and without flags to ensure backward compatibility

## Future Enhancements

### Phase 2 Improvements (After Core Issues Fixed)
1. **Consistent Execution Patterns**: Standardize command execution between shell and Python
2. **Enhanced command_executor.py**: Add indentation support for nested calls
3. **Improved Error Handling**: Better error propagation through multi-level calls

### Long-term Enhancements
4. **Structured Output**: JSON/YAML output mode for automation
5. **Execution Plans**: Save dry-run output as executable plan
6. **Selective Verbosity**: Control verbosity by component (--verbose=install,users,samba)
7. **Progress Indicators**: Show progress in non-verbose mode
8. **Rollback Support**: Track changes for potential rollback

### Integration with Existing Infrastructure
- **Leverage command_executor.py**: Build on existing dry-run infrastructure rather than replace
- **Maintain backward compatibility**: Existing scripts should continue to work
- **Use existing environment variables**: Build on DRY_RUN/VERBOSE pattern already established
- **Preserve existing execution wrappers**: execute_or_dryrun() and execute_or_execute_dryrun() are working well