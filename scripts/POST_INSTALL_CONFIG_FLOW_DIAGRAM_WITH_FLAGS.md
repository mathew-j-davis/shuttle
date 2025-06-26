# Shuttle Post-Install Configuration Flow Diagram - With Verbose/Dry-Run Flag Propagation

This document shows the post-install configuration flow with **highlighted changes** for verbose and dry-run flag propagation implementation.

## Overall Flow with Flag Propagation

```
scripts/2_post_install_config.sh [--wizard|--instructions <file>|--help]
├── parse_arguments()
│   ├── --wizard → RUN_WIZARD=true
│   ├── --instructions <file> → CONFIG_FILE=<file>
│   ├── --interactive/--non-interactive → Override YAML setting
│   ├── --dry-run → DRY_RUN=true → export DRY_RUN ✅
│   ├── --verbose → VERBOSE=true → export VERBOSE ✅
│   └── --help → show_usage() → exit
│
├── main()
│   ├── Wizard Phase (if --wizard or no --instructions)
│   │   └── run_configuration_wizard()
│   │       ├── cd config/
│   │       ├── 🔧 NEW: execute_or_execute_dryrun_python_module() replaces direct call
│   │       ├── python3 -m post_install_config_wizard [args] --verbose --dry-run
│   │       ├── Handle exit codes: 0=continue, 2=saved+exit, 3=cancelled
│   │       └── Set CONFIG_FILE to generated YAML
│   │
│   ├── Prerequisites Check
│   │   └── (no changes needed - validation only)
│   │
│   ├── Configuration Analysis
│   │   └── interactive_setup() → Show config summary and confirm
│   │       └── 🔧 NEW: execute_or_execute_dryrun_python_module() replaces direct call
│   │           └── python3 -m config_analyzer "$CONFIG_FILE" --verbose --dry-run
│   │
│   └── Configuration Phases (Execute in Sequence)
│       ├── Phase 1: Install Tools ✅ (already uses execute_or_execute_dryrun)
│       ├── Phase 2: Configure Users & Groups 🔧 (needs flag propagation)
│       ├── Phase 3: Set File Permissions 🔧 (needs flag propagation)
│       ├── Phase 4: Configure Samba 🔧 (needs flag propagation)
│       └── Phase 5: Configure Firewall ✅ (already uses execute_or_execute_dryrun)
```

---

## 🔧 NEW: Flag Propagation Infrastructure

### Shell Library Enhancement (_common_.source.sh)
```bash
# NEW FUNCTION - Builds on existing execute_or_execute_dryrun
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
    
    # 🔧 ADD --verbose (--dry-run handled by parent function)
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        cmd="$cmd --verbose"
    fi
    
    # Call existing function which adds --dry-run automatically
    execute_or_execute_dryrun "$cmd" "$success_msg" "$error_msg" "$explanation"
}
```

### Python Execution Enhancement (command_executor.py)
```python
# 🔧 SIMPLE ENHANCEMENT - Add verbose parameter and env var fallback
def run_command(cmd_list: List[str], description: str, dry_run: bool = False, 
                verbose: bool = False, interactive: bool = False) -> bool:
    # Check environment variables as fallback
    if not dry_run:
        dry_run = os.environ.get('DRY_RUN', 'false').lower() == 'true'
    if not verbose:
        verbose = os.environ.get('VERBOSE', 'false').lower() == 'true'
    
    # Show command if verbose OR dry-run
    if verbose or dry_run:
        if dry_run:
            print(f"[DRY RUN] {description}")
        else:
            print(f"Executing: {description}")
        print(f"  Command: {' '.join(cmd_list)}")
    
    # Rest stays the same...

# 🔧 NEW HELPER - For calling scripts with flag propagation
def run_script_with_flags(script_path, base_args, description, 
                         dry_run=False, verbose=False):
    cmd = [script_path] + base_args
    # Add flags if needed
    if verbose or os.environ.get('VERBOSE') == 'true':
        cmd.append('--verbose')
    if dry_run or os.environ.get('DRY_RUN') == 'true':
        cmd.append('--dry-run')
    return run_command(cmd, description, dry_run, verbose)
```

---

## Configuration Phase Execution with Flag Propagation

### Phase 1: Install System Tools ✅ (Already Working)
```
phase_install_tools()
├── Check component enablement
├── Build flags: --no-acl, --no-samba
└── execute_or_execute_dryrun("11_install_tools.sh [flags]")
    └── ✅ Already respects DRY_RUN and VERBOSE environment variables
```

### Phase 2: Configure Users and Groups 🔧 (Needs Update)
```
phase_configure_users()
├── Check component enablement
├── Build Python module arguments
│   ├── --dry-run (if DRY_RUN=true) ✅ (existing)
│   └── --shuttle-config-path (if set) ✅ (existing)
│
└── 🔧 CHANGE: Use execute_or_execute_dryrun_python_module()
    └── python3 -m user_group_manager CONFIG_FILE DIR --verbose --dry-run
        ├── 🔧 UPDATE: Add --verbose argument parsing
        ├── 🔧 UPDATE: Pass verbose=args.verbose to functions
        └── Process users with flag awareness:
            └── run_script_with_flags("12_users_and_groups.sh", ["create-user"], verbose=True)
                └── 12_users_and_groups.sh create-user --verbose --dry-run
                    └── execute_or_dryrun("useradd ...") ✅ Shows command
```

### Phase 3: Set File Permissions 🔧 (Needs Update)
```
phase_set_permissions()
├── Build arguments (--dry-run if DRY_RUN=true)
│
└── 🔧 CHANGE: Use execute_or_execute_dryrun_python_module()
    └── python3 -m permission_manager CONFIG_FILE DIR --verbose --dry-run
        ├── 🔧 UPDATE: Add --verbose argument parsing
        ├── 🔧 UPDATE: Pass verbose parameter to functions
        └── Apply permissions with visibility:
            └── run_command(["chmod", "755", path], verbose=True) 
                └── 🔧 Shows: "Executing: Set permissions on /path"
                └── 🔧 Shows: "  Command: chmod 755 /path"
```

### Phase 4: Configure Samba 🔧 (Needs Update)
```
phase_configure_samba()
├── Build arguments (--dry-run, --non-interactive)
│
└── 🔧 CHANGE: Use execute_or_execute_dryrun_python_module()
    └── python3 -m samba_manager CONFIG_FILE DIR --verbose --dry-run
        ├── 🔧 UPDATE: Add --verbose argument parsing
        └── Configure with visibility:
            └── ctx.run_command(["smbpasswd", "-a", username])
                └── 🔧 Shows commands in verbose/dry-run mode
```

### Phase 5: Configure Firewall ✅ (Already Working)
```
phase_configure_firewall()
└── execute_or_execute_dryrun("14_configure_firewall.sh show-status")
    └── ✅ Already respects DRY_RUN and VERBOSE environment variables
```

---

## Flag Propagation Flow Example

### User Command:
```bash
./scripts/2_post_install_config.sh --instructions config.yaml --verbose --dry-run
```

### Execution Flow with Flags:
```
1. Shell Script Sets Environment:
   export DRY_RUN=true
   export VERBOSE=true

2. Shell → Python (NEW PATTERN):
   execute_or_execute_dryrun_python_module "user_group_manager" "config.yaml /scripts"
   ↓ Automatically adds --verbose, parent function adds --dry-run ↓
   python3 -m user_group_manager config.yaml /scripts --verbose --dry-run

3. Python Module (ENHANCED):
   args = parser.parse_args()  # Gets --verbose and --dry-run
   # No ExecutionContext needed - just use args.verbose and args.dry_run
   
4. Python → Shell (WITH FLAGS):
   run_script_with_flags("12_users_and_groups.sh", ["create-user", "bob"], 
                        "Creating user", dry_run=args.dry_run, verbose=args.verbose)
   ↓ Automatically adds flags ↓
   12_users_and_groups.sh create-user bob --verbose --dry-run

5. Shell Script (ACCEPTS FLAGS):
   while [[ $# -gt 0 ]]; do
       case $1 in
           --verbose) VERBOSE=true ;;
           --dry-run) DRY_RUN=true ;;
   
6. Shell → System Command (VISIBLE):
   execute_or_dryrun "useradd -m bob"
   ↓ With verbose=true ↓
   [VERBOSE] Executing: useradd -m bob
   [DRY RUN] Command would execute: useradd -m bob
```

---

## Summary of Changes by File

### 🔧 Shell Scripts (2 changes)
1. **_common_.source.sh**: Add `execute_or_execute_dryrun_python_module()` function
2. **2_post_install_config.sh**: Replace 5 Python calls (lines 357, 455, 476, 508, 562)

### 🔧 Python Modules (6 changes)
3. **command_executor.py**: Simple enhancement - add verbose parameter and env var fallback
4. **config_analyzer.py**: Add --verbose argument parsing
5. **user_group_manager.py**: Add --verbose argument support, pass to functions
6. **permission_manager.py**: Add --verbose argument support, pass to functions
7. **samba_manager.py**: Add --verbose argument support, pass to functions
8. **post_install_config_wizard.py**: Add --verbose and --dry-run support

### 🔧 Installation Scripts (4 changes - lower priority)
9. **02_env_and_venv.sh**: Wrap direct mkdir and python3 -m venv calls
10. **08_install_shared.sh**: Wrap pip install calls
11. **09_install_defender_test.sh**: Wrap pip install calls
12. **10_install_shuttle.sh**: Wrap pip install calls

---

## Before and After Comparison

### BEFORE (Current Behavior):
```bash
$ ./scripts/2_post_install_config.sh --dry-run --verbose
[DRY RUN] python3 -m user_group_manager config.yaml /scripts --dry-run
# No visibility into what user_group_manager would do internally
```

### AFTER (With Flag Propagation):
```bash
$ ./scripts/2_post_install_config.sh --dry-run --verbose
[DEBUG] Executing script: python3 -m user_group_manager config.yaml /scripts --dry-run --verbose
[INFO] Explanation: Configure system users and groups according to YAML specification
[DRY RUN] Configure system users and groups according to YAML specification
  Processing user: shuttle_service
  [DRY RUN] Creating user shuttle_service
    Command: /scripts/12_users_and_groups.sh create-user shuttle_service --verbose --dry-run
      [DRY RUN] Create new system user account for Shuttle file operations
        Command: useradd -m -s /bin/bash -g shuttle_users shuttle_service
      [DRY RUN] Add user to secondary groups
        Command: usermod -aG shuttle_admins shuttle_service
[INFO] User and group configuration complete
```

---

## Testing the Implementation

### Test Scenarios:
1. **Verbose Only**: Shows commands as they execute
   ```bash
   ./scripts/2_post_install_config.sh --verbose
   # Shows all commands being executed in real-time
   ```

2. **Dry-Run Only**: Shows what would happen without executing
   ```bash
   ./scripts/2_post_install_config.sh --dry-run
   # Shows all commands that would be executed
   ```

3. **Both Flags**: Maximum visibility
   ```bash
   ./scripts/2_post_install_config.sh --verbose --dry-run
   # Shows detailed command hierarchy without executing
   ```

4. **Environment Variables**: Alternative to command-line flags
   ```bash
   export VERBOSE=true
   export DRY_RUN=true
   ./scripts/2_post_install_config.sh
   # Same as using --verbose --dry-run
   ```

---

## Implementation Benefits

1. **🔍 Complete Visibility**: See every command at every level
2. **🔄 Automatic Propagation**: Flags flow through all execution layers
3. **🛡️ Safe Testing**: Dry-run prevents all changes at every level
4. **🐛 Better Debugging**: Verbose mode shows exact command execution
5. **♻️ Backward Compatible**: Existing scripts continue to work unchanged
6. **📝 Command History**: All Python module executions logged with timestamps
7. **🔧 Reuses Infrastructure**: Builds on proven execute_or_execute_dryrun() function