# Shared Setup Libraries

This directory contains common shell libraries that can be shared between installation and configuration scripts.

## Files Moved Here

- **`_common_.source.sh`** - Core functions (logging, validation, command execution)
- **`_input_validation.source.sh`** - Security validation and input sanitization  
- **`_check_active_user.source.sh`** - User permission checking
- **`_check_tool.source.sh`** - Tool availability and permission checking
- **`_users_and_groups_inspect.source.sh`** - User/group inspection utilities

## New Clean Import Pattern

### Before (Messy Relative Paths)
```bash
# Old way - brittle and hard to maintain
if [[ -f "$SCRIPT_DIR/lib/_common_.source.sh" ]]; then
    source "$SCRIPT_DIR/lib/_common_.source.sh"
fi
if [[ -f "$SCRIPT_DIR/../lib/_common_.source.sh" ]]; then
    source "$SCRIPT_DIR/../lib/_common_.source.sh"
fi
if [[ -f "$SCRIPT_DIR/../../lib/_common_.source.sh" ]]; then
    source "$SCRIPT_DIR/../../lib/_common_.source.sh"
fi
```

### After (Clean Intelligent Loading)
```bash
# New way - clean and robust
SETUP_LIB_DIR="$(dirname "$SCRIPT_DIR")/_setup_lib_sh"
if [[ -f "$SETUP_LIB_DIR/_setup_lib_loader.source.sh" ]]; then
    source "$SETUP_LIB_DIR/_setup_lib_loader.source.sh"
    load_common_libs || {
        echo "ERROR: Failed to load required setup libraries" >&2
        exit 1
    }
else
    echo "ERROR: Setup library loader not found" >&2
    exit 1
fi
```

## Loading Options

### 1. Load Common Libraries (Recommended)
```bash
load_common_libs
```
Loads: `_input_validation`, `_check_active_user`, `_check_tool`, `_common_`

### 2. Load All Setup Libraries
```bash
load_all_setup_libs  
```
Loads all libraries including `_users_and_groups_inspect`

### 3. Load Individual Libraries
```bash
source_setup_lib "_input_validation"
source_setup_lib "_common_"
```

## Benefits

1. **No Complex Relative Paths** - No more `../../../lib/` nonsense
2. **Intelligent Path Resolution** - Works from any script location
3. **Clear Error Messages** - Shows exactly what's missing
4. **Dependency Order** - Libraries loaded in correct order automatically
5. **Easy Maintenance** - Single source of truth for library loading
6. **Robust** - Handles missing files gracefully

## Available Functions After Loading

### Logging and Error Handling
- `log INFO|WARN|ERROR|DEBUG "message"`
- `error_exit "message" [exit_code]`

### Secure Parameter Validation
- `validate_parameter_user()` - Username validation
- `validate_parameter_group()` - Group name validation
- `validate_parameter_path()` - File path validation
- `validate_parameter_password()` - Password validation
- `validate_parameter_numeric()` - UID/GID validation
- `validate_parameter_comment()` - Comment validation
- `validate_parameter_shell()` - Shell path validation
- `validate_parameter_group_list()` - Comma-separated groups

### Command Execution
- `execute_or_dryrun()` - Execute with dry-run support
- `execute()` - Execute read-only commands
- `check_command()` - Check if command exists

### User/System Checks
- `check_active_user_is_root()`
- `check_active_user_has_sudo_access()`
- `check_tool_permission_or_error_exit()`

## Security Features

All validation functions provide:
- **Command injection prevention** through input sanitization
- **Format validation** using POSIX standards
- **Path traversal protection** for file paths
- **Shell metacharacter filtering**
- **Automatic help integration** on validation failure

## Usage Example

See `../example_clean_import.sh` for a complete working example.