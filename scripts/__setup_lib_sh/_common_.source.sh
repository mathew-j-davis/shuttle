
# Color constants for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Capability flags
#IS_ROOT_USER=false
# HAS_SUDO_ACCESS=false
# SUDO_REQUIRES_PASSWORD=false

# Function to log messages with color coding
log() {
    local level="$1"
    shift
    local message="$*"
    
    case "$level" in
        ERROR)   echo -e "${RED}[ERROR]${NC} $message" >&2 ;;
        WARN)    echo -e "${YELLOW}[WARN]${NC} $message" >&2 ;;
        INFO)    echo -e "${GREEN}[INFO]${NC} $message" >&2 ;;
        DEBUG)   echo -e "${BLUE}[DEBUG]${NC} $message" >&2 ;;
        *)       echo "[$level] $message" >&2 ;;
    esac
    
    # Also log to syslog if available
    if check_command "logger"; then
        logger -t "user-group-manager" "[$level] $message"
    fi
}

# Error handling with colored output
error_exit() {
    local message="$1"
    local exit_code="${2:-1}"
    
    log ERROR "$message"
    log ERROR "Use '$SCRIPT_NAME --help' for usage information"
    exit "$exit_code"
}


# Parameter validation with help integration
validate_parameter_value() {
    local param_name="$1"
    local param_value="$2"
    local error_message="$3"
    local help_function="${4:-}"  # Optional help function name
    
    if [[ -z "$param_value" ]] || [[ "$param_value" =~ ^-- ]]; then
        if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
            "$help_function"
        fi
        error_exit "$error_message"
    fi
    
    echo "$param_value"
}

# ============================================================================
# SPECIALIZED PARAMETER VALIDATION FUNCTIONS
# ============================================================================

# Source input validation library for format validation
# This will be loaded by the setup lib loader, so we don't need to source it here
# The validation functions depend on validate_input() from _input_validation.source.sh

# Validate and cleanse group name parameter
validate_parameter_group() {
    local param_name="$1"
    local param_value="$2"
    local help_function="${3:-}"  # Optional help function name
    
    # First validate parameter exists and is not empty/flag
    param_value=$(validate_parameter_value "$param_name" "$param_value" "Group name required after $param_name (must be 1-32 chars, start with letter, contain only letters/numbers/dots/hyphens/underscores)" "$help_function")
    
    # Then validate group name format
    if ! validate_input "group" "$param_value" "group name"; then
        if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
            "$help_function"
        fi
        error_exit "Invalid group name '$param_value' after $param_name: must start with letter and contain only letters, numbers, dots, hyphens, and underscores (max 32 chars)"
    fi
    
    # Return the validated and cleansed value
    echo "$param_value"
}

# Validate and cleanse username parameter
validate_parameter_user() {
    local param_name="$1"
    local param_value="$2"
    local help_function="${3:-}"  # Optional help function name
    
    # First validate parameter exists and is not empty/flag
    param_value=$(validate_parameter_value "$param_name" "$param_value" "Username required after $param_name (must be 1-32 chars, start with letter, contain only letters/numbers/dots/hyphens/underscores)" "$help_function")
    
    # Then validate username format
    if ! validate_input "username" "$param_value" "username"; then
        if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
            "$help_function"
        fi
        error_exit "Invalid username '$param_value' after $param_name: must start with letter and contain only letters, numbers, dots, hyphens, and underscores (max 32 chars)"
    fi
    
    # Return the validated and cleansed value
    echo "$param_value"
}

# Validate and cleanse path parameter
validate_parameter_path() {
    local param_name="$1"
    local param_value="$2"
    local help_function="${3:-}"  # Optional help function name
    local allow_relative="${4:-false}"  # Allow relative paths
    
    # First validate parameter exists and is not empty/flag
    param_value=$(validate_parameter_value "$param_name" "$param_value" "Path required after $param_name (must be valid filesystem path without shell metacharacters or path traversal)" "$help_function")
    
    # Then validate path format
    if ! validate_input "path" "$param_value" "path" "$allow_relative"; then
        if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
            "$help_function"
        fi
        if [[ "$allow_relative" == "true" ]]; then
            error_exit "Invalid path '$param_value' after $param_name: must be valid path without shell metacharacters or path traversal (..)"
        else
            error_exit "Invalid path '$param_value' after $param_name: must be absolute path without shell metacharacters or path traversal (..)"
        fi
    fi
    
    # Return the validated and cleansed value
    echo "$param_value"
}

# Validate and cleanse numeric parameter (UID/GID)
validate_parameter_numeric() {
    local param_name="$1"
    local param_value="$2"
    local help_function="${3:-}"  # Optional help function name
    local min_value="${4:-0}"
    local max_value="${5:-65535}"
    
    # First validate parameter exists and is not empty/flag
    param_value=$(validate_parameter_value "$param_name" "$param_value" "Numeric value required after $param_name (must be integer between $min_value and $max_value)" "$help_function")
    
    # Then validate numeric format
    if ! validate_input "numeric" "$param_value" "numeric value" "$min_value" "$max_value"; then
        if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
            "$help_function"
        fi
        error_exit "Invalid numeric value '$param_value' after $param_name: must be integer between $min_value and $max_value"
    fi
    
    # Return the validated and cleansed value
    echo "$param_value"
}

# Validate password parameter (allows all characters except null bytes)
validate_parameter_password() {
    local param_name="$1"
    local param_value="$2"
    local help_function="${3:-}"  # Optional help function name
    
    # First validate parameter exists and is not empty/flag
    param_value=$(validate_parameter_value "$param_name" "$param_value" "Password required after $param_name (1-1024 chars, no null bytes or newlines)" "$help_function")
    
    # Then validate password format (very permissive for security)
    if ! validate_input "password" "$param_value" "password"; then
        if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
            "$help_function"
        fi
        error_exit "Invalid password after $param_name: must be 1-1024 characters without null bytes or newlines (all other characters allowed for strong passwords)"
    fi
    
    # Return the validated password (no cleansing - preserve all characters)
    echo "$param_value"
}

# Validate and cleanse permission mode parameter
validate_parameter_mode() {
    local param_name="$1"
    local param_value="$2"
    local help_function="${3:-}"  # Optional help function name
    
    # First validate parameter exists and is not empty/flag
    param_value=$(validate_parameter_value "$param_name" "$param_value" "Permission mode required after $param_name (octal like 755, 644 or symbolic like u+x,g-w)" "$help_function")
    
    # Then validate mode format
    if ! validate_input "mode" "$param_value" "permission mode"; then
        if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
            "$help_function"
        fi
        error_exit "Invalid permission mode '$param_value' after $param_name: use octal format (755, 644) or symbolic format (u+x, g-w, a=r)"
    fi
    
    # Return the validated and cleansed value
    echo "$param_value"
}

# Validate and cleanse shell parameter
validate_parameter_shell() {
    local param_name="$1"
    local param_value="$2"
    local help_function="${3:-}"  # Optional help function name
    
    # First validate parameter exists and is not empty/flag
    param_value=$(validate_parameter_value "$param_name" "$param_value" "Shell path required after $param_name (must be valid executable path like /bin/bash)" "$help_function")
    
    # Then validate shell format
    if ! validate_input "shell" "$param_value" "shell"; then
        if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
            "$help_function"
        fi
        error_exit "Invalid shell '$param_value' after $param_name: must be valid executable path (check /etc/shells for valid shells)"
    fi
    
    # Return the validated and cleansed value
    echo "$param_value"
}

# Validate and cleanse comment parameter
validate_parameter_comment() {
    local param_name="$1"
    local param_value="$2"
    local help_function="${3:-}"  # Optional help function name
    local max_length="${4:-256}"
    
    # First validate parameter exists and is not empty/flag
    param_value=$(validate_parameter_value "$param_name" "$param_value" "Comment required after $param_name (max $max_length chars, avoid shell metacharacters)" "$help_function")
    
    # Then validate comment format
    if ! validate_input "comment" "$param_value" "comment" "$max_length"; then
        if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
            "$help_function"
        fi
        error_exit "Invalid comment '$param_value' after $param_name: max $max_length chars, avoid shell metacharacters (; | & \` \$ ( ))"
    fi
    
    # Return the validated and cleansed value
    echo "$param_value"
}

# Validate user parameter (allows both username and numeric UID)
validate_parameter_user_or_uid() {
    local param_name="$1"
    local param_value="$2"
    local help_function="${3:-}"  # Optional help function name
    
    # First validate parameter exists and is not empty/flag
    param_value=$(validate_parameter_value "$param_name" "$param_value" "User required after $param_name (username or numeric UID)" "$help_function")
    
    # Check if it's numeric (UID)
    if [[ "$param_value" =~ ^[0-9]+$ ]]; then
        # Validate as numeric UID
        if ! validate_input "numeric" "$param_value" "user ID"; then
            if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
                "$help_function"
            fi
            error_exit "Invalid user ID '$param_value' after $param_name: must be integer between 0 and 65535"
        fi
    else
        # Validate as username
        if ! validate_input "username" "$param_value" "username"; then
            if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
                "$help_function"
            fi
            error_exit "Invalid username '$param_value' after $param_name: must start with letter and contain only letters, numbers, dots, hyphens, and underscores (max 32 chars)"
        fi
    fi
    
    # Return the validated value
    echo "$param_value"
}

# Validate group parameter (allows both group name and numeric GID)
validate_parameter_group_or_gid() {
    local param_name="$1"
    local param_value="$2"
    local help_function="${3:-}"  # Optional help function name
    
    # First validate parameter exists and is not empty/flag
    param_value=$(validate_parameter_value "$param_name" "$param_value" "Group required after $param_name (group name or numeric GID)" "$help_function")
    
    # Check if it's numeric (GID)
    if [[ "$param_value" =~ ^[0-9]+$ ]]; then
        # Validate as numeric GID
        if ! validate_input "numeric" "$param_value" "group ID"; then
            if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
                "$help_function"
            fi
            error_exit "Invalid group ID '$param_value' after $param_name: must be integer between 0 and 65535"
        fi
    else
        # Validate as group name
        if ! validate_input "group" "$param_value" "group name"; then
            if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
                "$help_function"
            fi
            error_exit "Invalid group name '$param_value' after $param_name: must start with letter and contain only letters, numbers, dots, hyphens, and underscores (max 32 chars)"
        fi
    fi
    
    # Return the validated value
    echo "$param_value"
}

# Validate and cleanse group list parameter (comma-separated)
validate_parameter_group_list() {
    local param_name="$1"
    local param_value="$2"
    local help_function="${3:-}"  # Optional help function name
    
    # First validate parameter exists and is not empty/flag
    param_value=$(validate_parameter_value "$param_name" "$param_value" "Group list required after $param_name (comma-separated group names)" "$help_function")
    
    # Split on comma and validate each group name
    local IFS=','
    local group_array
    read -ra group_array <<< "$param_value"
    
    local validated_groups=()
    for group in "${group_array[@]}"; do
        # Trim whitespace from group name
        group=$(echo "$group" | xargs)
        
        # Skip empty groups (from double commas or trailing commas)
        if [[ -z "$group" ]]; then
            if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
                "$help_function"
            fi
            error_exit "Empty group name found in group list after $param_name (check for double commas or trailing commas)"
        fi
        
        # Validate individual group name format
        if ! validate_input "group" "$group" "group name in list"; then
            if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
                "$help_function"
            fi
            error_exit "Invalid group name '$group' in group list after $param_name: must start with letter and contain only letters, numbers, dots, hyphens, and underscores (max 32 chars)"
        fi
        
        # Add validated group to array
        validated_groups+=("$group")
    done
    
    # Check if we have at least one valid group
    if [[ ${#validated_groups[@]} -eq 0 ]]; then
        if [[ -n "$help_function" ]] && declare -f "$help_function" >/dev/null; then
            "$help_function"
        fi
        error_exit "No valid group names found in group list after $param_name"
    fi
    
    # Return cleaned, validated group list (rejoined with commas, no spaces)
    local IFS=','
    echo "${validated_groups[*]}"
}

# ============================================================================
# SECURE PASSWORD HANDLING FUNCTIONS
# ============================================================================

# Securely pass password to smbpasswd using here-document
# This avoids password exposure in command line or process list
#
# WHY PASSWORD IS PASSED TWICE:
# smbpasswd follows standard Unix password protocols requiring confirmation:
# 1. First line: New password
# 2. Second line: Confirm password (must match)
# This prevents typos when setting passwords interactively
#
# LIMITATION: Passwords cannot contain newlines (\n) or carriage returns (\r)
# because they would break the two-line input format that smbpasswd expects
execute_smbpasswd_with_password() {
    local username="$1"
    local password="$2"
    local smbpasswd_flags="${3:--a -s}"  # Default: add user, stdin mode
    local description="${4:-Set Samba password}"
    
    # Validate inputs
    if [[ -z "$username" ]]; then
        log ERROR "Username required for smbpasswd operation"
        return 1
    fi
    
    if [[ -z "$password" ]]; then
        log ERROR "Password required for smbpasswd operation"
        return 1
    fi
    
    log INFO "Setting Samba password for user '$username' using secure method"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would execute: sudo smbpasswd $smbpasswd_flags '$username'"
        log INFO "[DRY RUN] Would provide password via secure stdin (password length: ${#password} chars)"
        return 0
    fi
    
    # Use here-document to securely pass password
    # This method:
    # 1. Doesn't expose password in command line
    # 2. Doesn't expose password in process list  
    # 3. Handles all special characters safely
    # 4. Provides password via stdin as smbpasswd expects
    local smbpasswd_result
    smbpasswd_result=$(sudo smbpasswd $smbpasswd_flags "$username" 2>&1 <<EOF
$password
$password
EOF
)
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log INFO "Successfully set Samba password for user '$username'"
        return 0
    else
        log ERROR "Failed to set Samba password for user '$username'"
        log ERROR "smbpasswd output: $smbpasswd_result"
        return $exit_code
    fi
}

# Alternative secure method using file descriptor
# More complex but avoids any temporary data
execute_smbpasswd_with_fd() {
    local username="$1"
    local password="$2"
    local smbpasswd_flags="${3:--a -s}"
    local description="${4:-Set Samba password}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would execute: sudo smbpasswd $smbpasswd_flags '$username'"
        log INFO "[DRY RUN] Would provide password via file descriptor (length: ${#password} chars)"
        return 0
    fi
    
    # Create file descriptor with password
    exec 3<<<$''"$password"$'\n'"$password"
    
    # Execute smbpasswd with password from file descriptor
    local smbpasswd_result exit_code
    smbpasswd_result=$(sudo smbpasswd $smbpasswd_flags "$username" <&3 2>&1)
    exit_code=$?
    
    # Close file descriptor
    exec 3<&-
    
    if [[ $exit_code -eq 0 ]]; then
        log INFO "Successfully set Samba password for user '$username'"
        return 0
    else
        log ERROR "Failed to set Samba password for user '$username'"
        log ERROR "smbpasswd output: $smbpasswd_result"
        return $exit_code
    fi
}

# ============================================================================
# DRY RUN HELPER FUNCTIONS
# ============================================================================

# Function to execute command or show what would be done in dry-run mode
# Note: Command should already include sudo prefix if needed
# History file for command logging
# Main process should set this, otherwise use generic name
COMMAND_HISTORY_FILE="${COMMAND_HISTORY_FILE:-/tmp/shuttle_generic_command_history_$(date +%Y%m%d_%H%M%S).log}"

# Initialize history file
init_command_history() {
    if [[ ! -f "$COMMAND_HISTORY_FILE" ]]; then
        {
            echo "# Shuttle Command History"
            echo "# Started: $(date)"
            echo "# Script: ${SCRIPT_NAME:-unknown}"
            echo "# User: $(whoami)"
            echo "# Working Directory: $(pwd)"
            echo ""
        } > "$COMMAND_HISTORY_FILE"
        log INFO "Command history logging to: $COMMAND_HISTORY_FILE"
    fi
}

# Log command to history
log_command_history() {
    local timestamp="$1"
    local command="$2"
    local explanation="$3"
    local status="$4"
    local dry_run="$5"
    
    init_command_history
    
    {
        echo "[$timestamp] $status"
        if [[ -n "$explanation" ]]; then
            echo "  Explanation: $explanation"
        fi
        echo "  Command: $command"
        if [[ "$dry_run" == "true" ]]; then
            echo "  Mode: DRY RUN"
        fi
        echo ""
    } >> "$COMMAND_HISTORY_FILE"
}

execute_or_dryrun() {
    local cmd="$1"
    local success_msg="$2"
    local error_msg="$3"
    local explanation="${4:-}"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Show explanation if provided
    if [[ -n "$explanation" ]]; then
        log INFO "Explanation: $explanation"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would execute: $cmd"
        log_command_history "$timestamp" "$cmd" "$explanation" "DRY RUN" "true"
        return 0
    fi
    
    log DEBUG "Executing: $cmd"
    
    if eval "$cmd"; then
        log INFO "$success_msg"
        log_command_history "$timestamp" "$cmd" "$explanation" "SUCCESS" "false"
        return 0
    else
        log ERROR "$error_msg"
        log_command_history "$timestamp" "$cmd" "$explanation" "FAILED" "false"
        return 1
    fi
}

execute() {
    local cmd="$1"
    local success_msg="$2"
    local error_msg="$3"
    local explanation="${4:-}"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Show explanation if provided
    if [[ -n "$explanation" ]]; then
        log INFO "Explanation: $explanation"
    fi
    
    log DEBUG "Executing (read-only): $cmd"
    
    if eval "$cmd"; then
        log INFO "$success_msg"
        log_command_history "$timestamp" "$cmd" "$explanation" "SUCCESS (READ)" "false"
        return 0
    else
        log ERROR "$error_msg"
        log_command_history "$timestamp" "$cmd" "$explanation" "FAILED (READ)" "false"
        return 1
    fi
}

# Function for executing our own scripts with dry-run support
# When in dry-run mode, this actually executes the script but passes --dry-run
# When not in dry-run mode, executes the script normally
execute_or_execute_dryrun() {
    local cmd="$1"
    local success_msg="$2"
    local error_msg="$3"
    local explanation="${4:-}"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Show explanation if provided
    if [[ -n "$explanation" ]]; then
        log INFO "Explanation: $explanation"
    fi
    
    # Modify command based on dry-run mode
    local actual_cmd="$cmd"
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        # Append --dry-run to our own scripts
        actual_cmd="$cmd --dry-run"
        log DEBUG "Executing (dry-run): $actual_cmd"
    else
        log DEBUG "Executing: $actual_cmd"
    fi
    
    if eval "$actual_cmd"; then
        log INFO "$success_msg"
        log_command_history "$timestamp" "$actual_cmd" "$explanation" "SUCCESS" "${DRY_RUN:-false}"
        return 0
    else
        log ERROR "$error_msg"
        log_command_history "$timestamp" "$actual_cmd" "$explanation" "FAILED" "${DRY_RUN:-false}"
        return 1
    fi
}

check_command() {
    local cmd="$1"

    # Parameter validation: ensure a command name was provided
    # Empty string test using [[ -z ]] is more robust than [ -z ] for bash
    if [[ -z "$cmd" ]]; then
        return 1
    fi
    
    # Core command existence check using POSIX-compliant 'command -v'
    # The return code of 'command -v' directly indicates success/failure:
    # - 0 (success): command exists and is accessible
    # - non-zero (failure): command not found or not accessible
    if command -v "$cmd" >/dev/null 2>&1; then
        return 0
    fi
    
    # Explicit return for clarity, though this would be the default behavior
    return 1
}

# Command building utility functions
prefix_if() {
    local condition_func="$1"
    local base_cmd="$2"
    local prefix="$3"
    
    # Execute the condition function and use its return code
    # Use eval to properly handle negation and complex conditions
    if eval "$condition_func"; then
        echo "$prefix$base_cmd"
    else
        echo "$base_cmd"
    fi
}

append_if_true() {
    local flag_var="$1"
    local base_cmd="$2"
    local append_text="$3"
    
    if [[ "$flag_var" == "true" ]]; then
        echo "$base_cmd$append_text"
    else
        echo "$base_cmd"
    fi
}

append_if_false() {
    local flag_var="$1"
    local base_cmd="$2"
    local append_text="$3"
    
    if [[ "$flag_var" == "false" ]]; then
        echo "$base_cmd$append_text"
    else
        echo "$base_cmd"
    fi
}

append_if_set() {
    local var_value="$1"
    local base_cmd="$2"
    local append_text="$3"
    
    if [[ -n "$var_value" ]]; then
        echo "$base_cmd$append_text"
    else
        echo "$base_cmd"
    fi
}