# Specialized Parameter Validation Approach

## Overview

We've implemented a defense-in-depth approach that validates and cleanses input **at the point of parameter parsing** rather than later in the function. This provides immediate feedback with better error messages and eliminates the need for redundant validation.

## New Specialized Validation Functions

Located in `_common_.source.sh`, these functions combine parameter validation with format validation:

### Available Functions

| Function | Purpose | Example Usage |
|----------|---------|---------------|
| `validate_parameter_group()` | Group names | `groupname=$(validate_parameter_group "$1" "${2:-}" "show_help_add_group")` |
| `validate_parameter_user()` | Usernames | `username=$(validate_parameter_user "$1" "${2:-}" "show_help_add_user")` |
| `validate_parameter_path()` | File paths | `home_dir=$(validate_parameter_path "$1" "${2:-}" "show_help_add_user")` |
| `validate_parameter_numeric()` | UID/GID values | `uid=$(validate_parameter_numeric "$1" "${2:-}" "show_help_add_user")` |
| `validate_parameter_password()` | Passwords | `password=$(validate_parameter_password "$1" "${2:-}" "show_help_add_user")` |
| `validate_parameter_shell()` | Shell paths | `shell=$(validate_parameter_shell "$1" "${2:-}" "show_help_add_user")` |
| `validate_parameter_mode()` | Permission modes | `mode=$(validate_parameter_mode "$1" "${2:-}" "show_help_set_permissions")` |
| `validate_parameter_comment()` | Comments/descriptions | `comment=$(validate_parameter_comment "$1" "${2:-}" "show_help_add_user")` |

## Implementation Example

### Before (Old Approach)
```bash
# Parameter parsing with basic validation
--group)
    groupname=$(validate_parameter_value "$1" "${2:-}" "Group name required after --group" "show_help_add_group")
    shift 2
    ;;

# Later in function - redundant validation
if ! validate_input "group" "$groupname" "group name"; then
    error_exit "Invalid group name provided to add group function"
fi
```

### After (New Approach)
```bash
# Parameter parsing with comprehensive validation
--group)
    groupname=$(validate_parameter_group "$1" "${2:-}" "show_help_add_group")
    shift 2
    ;;

# Later in function - no redundant validation needed
# Note: Input validation is already performed during parameter parsing
# using validate_parameter_group()
```

## Benefits of This Approach

### 1. **Immediate Validation**
- Input is validated and cleansed as soon as it's received
- Prevents invalid data from propagating through the function
- Early exit with clear error messages

### 2. **Better Error Messages**
Instead of generic errors, users get specific format requirements:

```bash
# Old error message
"Group name required after --group"

# New error message  
"Invalid group name 'test;evil' after --group: must start with letter and contain only letters, numbers, dots, hyphens, and underscores (max 32 chars)"
```

### 3. **Automatic Help Integration**
When validation fails, the help function is automatically called:
```bash
validate_parameter_group() {
    # ... validation logic ...
    if ! validate_input "group" "$param_value" "group name"; then
        if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
            "$help_function"  # Automatically shows help
        fi
        error_exit "Invalid group name..."
    fi
}
```

### 4. **Defense in Depth**
Each function performs multiple layers of validation:
1. **Parameter existence check** (via `validate_parameter_value`)
2. **Format validation** (via `validate_input`)
3. **Security sanitization** (blocks shell metacharacters)
4. **Length and range checks**

### 5. **Consistent Patterns**
All command files can use the same validation patterns:
```bash
username=$(validate_parameter_user "$1" "${2:-}" "show_help_function")
groupname=$(validate_parameter_group "$1" "${2:-}" "show_help_function")
path=$(validate_parameter_path "$1" "${2:-}" "show_help_function")
uid=$(validate_parameter_numeric "$1" "${2:-}" "show_help_function")
```

## Security Improvements

### Command Injection Prevention
```bash
# Malicious input blocked at parameter parsing
./script add-group --group "evil;rm -rf /"
# Error: Invalid group name 'evil;rm -rf /' after --group: must start with letter and contain only letters, numbers, dots, hyphens, and underscores (max 32 chars)
```

### Format Validation Examples
```bash
# Username validation
validate_parameter_user() validates:
✅ Must start with letter
✅ Only letters, numbers, dots, hyphens, underscores
✅ Maximum 32 characters
❌ Blocks shell metacharacters: ; | & ` $ ( )
❌ Blocks numbers at start
❌ Blocks empty values

# Path validation  
validate_parameter_path() validates:
✅ Must be absolute path (starts with /)
✅ Valid filesystem characters
❌ Blocks path traversal: ../
❌ Blocks shell metacharacters: ; | & ` $ ( )
❌ Blocks null bytes

# Numeric validation
validate_parameter_numeric() validates:
✅ Must be positive integer
✅ Range 0-65535 (configurable)
❌ Blocks non-numeric characters
❌ Blocks negative numbers
❌ Blocks numbers outside valid range
```

## Updated Files Using New Approach

### ✅ Already Updated
- `_cmd_add_group.source.sh` - Uses `validate_parameter_group()` and `validate_parameter_numeric()`
- `_cmd_add_user.source.sh` - Uses `validate_parameter_user()`, `validate_parameter_group()`, `validate_parameter_path()`, `validate_parameter_shell()`, `validate_parameter_comment()`, `validate_parameter_numeric()`, `validate_parameter_password()`

### 🔄 Need Updates (35 files)
All remaining command files should be updated to use the specialized validation functions:

```bash
# Replace patterns like this:
username=$(validate_parameter_value "$1" "${2:-}" "Username required" "help_func")

# With this:
username=$(validate_parameter_user "$1" "${2:-}" "help_func")
```

## Implementation Roadmap

### Phase 1: Core Functions (Completed)
- Created specialized validation functions in `_common_.source.sh`
- Updated `_cmd_add_group.source.sh` and `_cmd_add_user.source.sh`

### Phase 2: High-Risk Commands (Remaining)
Update all user/group/system management commands to use specialized validation:
- `_cmd_delete_user.source.sh`
- `_cmd_modify_user.source.sh`
- `_cmd_add_user_to_group.source.sh`
- All Samba management commands
- All file system commands

### Phase 3: Information Commands (Remaining)
Update "read-only" commands that still process user input:
- `_cmd_show_user.source.sh`
- `_cmd_list_*` commands
- `_cmd_show_*` commands

## Testing

Create test scripts to verify:
1. Valid inputs are accepted and properly formatted
2. Invalid inputs are rejected with clear error messages
3. Malicious inputs (command injection attempts) are blocked
4. Help functions are automatically called on validation failure

## Conclusion

This specialized validation approach provides:
- **Immediate security** - Input validated at entry point
- **Better user experience** - Clear error messages with format requirements
- **Maintainable code** - Consistent validation patterns across all commands
- **Defense in depth** - Multiple validation layers with automatic help integration

All remaining command files should be updated to follow this pattern for comprehensive security coverage.