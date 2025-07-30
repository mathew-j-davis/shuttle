
# Show usage instructions for saved configuration files
# Usage: show_saved_config_usage "script_name" "config_file" "config_type" [continue_option]
show_saved_config_usage() {
    local script_name="$1"
    local config_file="$2" 
    local config_type="${3:-instructions}"  # "instructions" or "configuration"
    local continue_option="${4:-false}"     # true if offering to continue
    
    # Convert to absolute paths for display
    local abs_config_file
    if [[ "$config_file" = /* ]]; then
        abs_config_file="$config_file"
    else
        abs_config_file="$(cd "$(dirname "$config_file")" && pwd)/$(basename "$config_file")"
    fi
    
    echo -e "${GREEN}✅ ${config_type^} saved to: $abs_config_file${NC}"
    echo ""
    echo "You can run this ${config_type%s} later with:"
    echo -e "${BLUE}$script_name --instructions $abs_config_file${NC}"
    echo ""
    echo "To perform a dry run (show what would be done without making changes) use --dry-run:"
    echo -e "${BLUE}$script_name --instructions $abs_config_file --dry-run${NC}"
    echo ""
    
    if [[ "$continue_option" == "true" ]]; then
        read -p "Proceed with ${config_type%s}? (Default: Yes) [Y/n/x]: " CONFIRM
        case $CONFIRM in
            [Nn])
                echo "${config_type^} cancelled."
                exit 0
                ;;
            [Xx])
                echo "${config_type^} cancelled by user."
                exit 0
                ;;
            *)
                # Continue (default Yes)
                ;;
        esac
    else
        echo "${config_type^} saved but not executed."
    fi
}

# Color constants for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log command execution with parameters
# Usage: log_command_call "command_name" "$@" or log_command_call "command_name" "$original_params"
log_command_call() {
    local command_name="$1"
    shift
    if [[ $# -eq 0 || -z "$*" ]]; then
        log DEBUG "$command_name command called with no parameters"
    else
        log DEBUG "$command_name command called with parameters: $*"
    fi
}

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

# Function to break down complex commands for better visibility in verbose mode
log_command_breakdown() {
    local cmd="$1"
    
    # Only show breakdown for complex commands (more than 3 parameters)
    local param_count=$(echo "$cmd" | wc -w)
    if [[ $param_count -le 3 ]]; then
        return 0
    fi
    
    # Parse command into base command and parameters
    local base_cmd=$(echo "$cmd" | awk '{print $1}')
    local params=$(echo "$cmd" | cut -d' ' -f2-)
    
    log DEBUG "  Command breakdown:"
    log DEBUG "    Base command: $base_cmd"
    
    # Simple parameter parsing - handles common patterns
    local current_param=""
    local param_value=""
    local in_quotes=false
    local quote_char=""
    
    echo "$params" | while read -r word; do
        if [[ "$word" =~ ^-- ]]; then
            # Long option
            if [[ "$word" == *"="* ]]; then
                # Option with value (--option=value)
                log DEBUG "    Parameter: ${word%%=*} = ${word#*=}"
            else
                # Option without value or separate value
                log DEBUG "    Parameter: $word"
            fi
        elif [[ "$word" =~ ^- ]]; then
            # Short option
            log DEBUG "    Parameter: $word"
        elif [[ "$word" =~ ^[0-9]+$ ]]; then
            # Numeric value
            log DEBUG "    Value: $word"
        elif [[ "$word" =~ ^[\'\"] ]]; then
            # Quoted string
            log DEBUG "    Value: $word"
        else
            # Regular argument
            log DEBUG "    Argument: $word"
        fi
    done 2>/dev/null || true  # Suppress any parsing errors
}

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
        if [[ "${VERBOSE:-false}" == "true" ]]; then
            log_command_breakdown "$cmd"
        fi
        log_command_history "$timestamp" "$cmd" "$explanation" "DRY RUN" "true"
        return 0
    fi
    
    # Log command when verbose
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        log DEBUG "Executing: $cmd"
        log_command_breakdown "$cmd"
    fi
    
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

# Function introspection utilities

# Get function definition as a string
function_to_string() {
    local func_name="$1"
    if declare -f "$func_name" >/dev/null 2>&1; then
        declare -f "$func_name"
    else
        echo "Function not found: $func_name" >&2
        return 1
    fi
}

# Get function body only (without the function name and braces)
function_body_to_string() {
    local func_name="$1"
    if declare -f "$func_name" >/dev/null 2>&1; then
        declare -f "$func_name" | sed '1d;2d;$d' | sed 's/^    //'
    else
        echo "Function not found: $func_name" >&2
        return 1
    fi
}

# Resolve variables in function definition to their current values
function_to_string_resolved() {
    local func_name="$1"
    shift  # Remove function name, leaving any arguments
    
    local func_def=$(function_to_string "$func_name")
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    # Extract all variable references
    local var_refs=$(echo "$func_def" | grep -oE '\$\{?[A-Za-z_][A-Za-z0-9_]*\}?' | sort -u)
    
    # Replace each variable with its value
    local resolved_def="$func_def"
    for var_ref in $var_refs; do
        # Remove $ and any braces
        local var_name=$(echo "$var_ref" | sed 's/\${\?//; s/}$//')
        
        # Skip positional parameters and special variables
        if [[ "$var_name" =~ ^[0-9]+$ ]] || [[ "$var_name" =~ ^[@*#?$!_-]$ ]]; then
            continue
        fi
        
        if [[ -v "$var_name" ]]; then
            local var_value="${!var_name}"
            # Escape special characters for sed
            var_value=$(printf '%s\n' "$var_value" | sed 's/[[\.*^$()+?{|]/\\&/g')
            # Limit length for readability
            if [[ ${#var_value} -gt 100 ]]; then
                var_value="${var_value:0:97}..."
            fi
            # Replace in function definition
            resolved_def=$(echo "$resolved_def" | sed "s/\\$var_ref/\"$var_value\"/g")
        fi
    done
    
    echo "$resolved_def"
}

# Create a command string that would execute the function
function_to_command_string() {
    local func_name="$1"
    shift  # Get function arguments
    
    local func_body=$(function_body_to_string "$func_name")
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    # Extract and resolve key commands
    local commands=""
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Resolve variables in the line
        local resolved_line="$line"
        local var_refs=$(echo "$line" | grep -oE '\$\{?[A-Za-z_][A-Za-z0-9_]*\}?' | sort -u)
        
        for var_ref in $var_refs; do
            local var_name=$(echo "$var_ref" | sed 's/\${\?//; s/}$//')
            if [[ -v "$var_name" ]] && ! [[ "$var_name" =~ ^[0-9]+$ ]] && ! [[ "$var_name" =~ ^[@*#?$!_-]$ ]]; then
                local var_value="${!var_name}"
                # Properly quote the value
                var_value=$(printf '%q' "$var_value")
                resolved_line=$(echo "$resolved_line" | sed "s|$var_ref|$var_value|g")
            fi
        done
        
        commands="${commands}${resolved_line}\n"
    done <<< "$func_body"
    
    printf '%b' "$commands" | sed '/^$/d'  # Remove empty lines
}

# Trace function execution (shows each command as it runs)
trace_function() {
    local func_name="$1"
    shift
    
    if ! declare -f "$func_name" >/dev/null 2>&1; then
        echo "Function not found: $func_name" >&2
        return 1
    fi
    
    # Enable tracing for just this function execution
    local old_opts=$-
    set -x
    "$func_name" "$@"
    local result=$?
    set +$old_opts  # Restore previous options
    return $result
}

# Debug function execution with command preview
debug_function() {
    local func_name="$1"
    shift
    
    if ! declare -f "$func_name" >/dev/null 2>&1; then
        echo "Function not found: $func_name" >&2
        return 1
    fi
    
    # Set up a DEBUG trap to show each command
    local old_trap=$(trap -p DEBUG)
    trap 'echo "[DEBUG] Next command: $BASH_COMMAND" >&2' DEBUG
    
    "$func_name" "$@"
    local result=$?
    
    # Restore old trap
    eval "${old_trap:-trap - DEBUG}"
    return $result
}


# Execute a function with dry-run support and configurable sudo behavior
# Usage: execute_function_or_dryrun <function_name> <success_msg> <error_msg> [explanation] [sudo_mode] [function_args...]
# sudo_mode options:
#   - "no" (default): Execute without sudo
#   - "fallback": Try without sudo first, then with sudo if it fails
#   - "always": Always execute with sudo
execute_function_or_dryrun() {
    local func_name="$1"
    local success_msg="$2"
    local error_msg="$3"
    local explanation="${4:-}"
    local sudo_mode="${5:-no}"  # no, fallback, always
    shift 5  # Remove first 5 args, leaving any function arguments
    
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Show explanation if provided
    if [[ -n "$explanation" ]]; then
        log INFO "Explanation: $explanation"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        # Show sudo mode in dry-run output
        local sudo_indicator=""
        case "$sudo_mode" in
            "always") sudo_indicator=" (with sudo)" ;;
            "fallback") sudo_indicator=" (with sudo fallback)" ;;
            "no") sudo_indicator="" ;;
        esac
        
        log INFO "[DRY RUN] Would execute function: $func_name $*$sudo_indicator"
        if [[ "${VERBOSE:-false}" == "true" ]] && declare -f "$func_name" >/dev/null 2>&1; then
            # Show different levels of detail based on verbosity
            log DEBUG "Function analysis:"
            
            # Level 0: Sudo mode
            log DEBUG "0. Sudo mode: $sudo_mode"
            
            # Level 1: Raw function definition
            log DEBUG "1. Raw function definition:"
            function_to_string "$func_name" | sed 's/^/     /' >&2
            
            # Level 2: Function with resolved variables
            log DEBUG "2. Function with resolved variables:"
            function_to_string_resolved "$func_name" "$@" | sed 's/^/     /' >&2
            
            # Level 3: Extracted command sequence
            log DEBUG "3. Commands that would be executed:"
            function_to_command_string "$func_name" "$@" | sed 's/^/     /' >&2
            
        fi
        log_command_history "$timestamp" "$func_name $*$sudo_indicator" "$explanation" "DRY RUN" "true"
        return 0
    fi
    
    # Verify function exists
    if ! declare -f "$func_name" >/dev/null 2>&1; then
        log ERROR "Function not found: $func_name"
        log_command_history "$timestamp" "$func_name $*" "$explanation" "ERROR: Function not found" "false"
        return 1
    fi
    
    # Log when verbose
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        log DEBUG "Executing function: $func_name $*"
    fi
    
    # Execute the function with any provided arguments, handling sudo modes
    case "$sudo_mode" in
        "no")
            # Execute without sudo
            if "$func_name" "$@"; then
                log INFO "$success_msg"
                log_command_history "$timestamp" "$func_name $*" "$explanation" "SUCCESS" "false"
                return 0
            else
                local exit_code=$?
                log ERROR "$error_msg"
                log_command_history "$timestamp" "$func_name $*" "$explanation" "FAILED (exit code: $exit_code)" "false"
                return $exit_code
            fi
            ;;
        "always")
            # Always use sudo
            if [[ "${VERBOSE:-false}" == "true" ]]; then
                log DEBUG "Executing function with sudo: $func_name $*"
            fi
            if sudo bash -c "$(declare -f log); $(declare -p RED GREEN YELLOW BLUE NC 2>/dev/null || true); $(declare -f "$func_name"); $func_name $(printf '%q ' "$@")"; then
                log INFO "$success_msg (with sudo)"
                log_command_history "$timestamp" "sudo $func_name $*" "$explanation" "SUCCESS (with sudo)" "false"
                return 0
            else
                local exit_code=$?
                log ERROR "$error_msg (sudo failed)"
                log_command_history "$timestamp" "sudo $func_name $*" "$explanation" "FAILED with sudo (exit code: $exit_code)" "false"
                return $exit_code
            fi
            ;;
        "fallback")
            # Try without sudo first, then with sudo if it fails
            if "$func_name" "$@"; then
                log INFO "$success_msg"
                log_command_history "$timestamp" "$func_name $*" "$explanation" "SUCCESS" "false"
                return 0
            else
                local first_exit_code=$?
                log INFO "Command failed without sudo (exit code: $first_exit_code), retrying with sudo..."
                if [[ "${VERBOSE:-false}" == "true" ]]; then
                    log DEBUG "Function failed without sudo (exit code: $first_exit_code), trying with sudo: $func_name $*"
                fi
                if sudo bash -c "$(declare -f log); $(declare -p RED GREEN YELLOW BLUE NC 2>/dev/null || true); $(declare -f "$func_name"); $func_name $(printf '%q ' "$@")"; then
                    log INFO "$success_msg (with sudo fallback)"
                    log_command_history "$timestamp" "sudo $func_name $*" "$explanation" "SUCCESS (with sudo fallback)" "false"
                    return 0
                else
                    local sudo_exit_code=$?
                    log ERROR "$error_msg (failed both with and without sudo)"
                    log_command_history "$timestamp" "$func_name $* -> sudo $func_name $*" "$explanation" "FAILED both ways (exit codes: $first_exit_code, $sudo_exit_code)" "false"
                    return $sudo_exit_code
                fi
            fi
            ;;
        *)
            log ERROR "Invalid sudo_mode: $sudo_mode. Valid values: no, fallback, always"
            return 1
            ;;
    esac
}

# Convenience wrapper functions for execute_function_or_dryrun with different sudo modes

# Execute function without sudo (explicit no-sudo mode)
# Usage: execute_function_or_dryrun_no_sudo <function_name> <success_msg> <error_msg> [explanation] [function_args...]
execute_function_or_dryrun_no_sudo() {
    local func_name="$1"
    local success_msg="$2"
    local error_msg="$3"
    local explanation="${4:-}"
    shift 4
    
    execute_function_or_dryrun "$func_name" "$success_msg" "$error_msg" "$explanation" "no" "$@"
}

# Execute function with automatic sudo fallback (try without sudo first, then with sudo if needed)
# Usage: execute_function_or_dryrun_auto_sudo <function_name> <success_msg> <error_msg> [explanation] [function_args...]
execute_function_or_dryrun_auto_sudo() {
    local func_name="$1"
    local success_msg="$2"
    local error_msg="$3"
    local explanation="${4:-}"
    shift 4
    
    execute_function_or_dryrun "$func_name" "$success_msg" "$error_msg" "$explanation" "fallback" "$@"
}

# Execute function always with sudo (force sudo execution)
# Usage: execute_function_or_dryrun_sudo <function_name> <success_msg> <error_msg> [explanation] [function_args...]
execute_function_or_dryrun_sudo() {
    local func_name="$1"
    local success_msg="$2"
    local error_msg="$3"
    local explanation="${4:-}"
    shift 4
    
    execute_function_or_dryrun "$func_name" "$success_msg" "$error_msg" "$explanation" "always" "$@"
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
    
    # Log command when verbose
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        log DEBUG "Executing (read-only): $cmd"
        log_command_breakdown "$cmd"
    fi
    
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
    
    # Modify command based on dry-run and verbose modes
    local actual_cmd="$cmd"
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        # Append --dry-run to our own scripts
        actual_cmd="$cmd --dry-run"
    fi
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        # Append --verbose to our own scripts
        actual_cmd="$actual_cmd --verbose"
    fi
    
    # Log command when verbose
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        log DEBUG "Executing script: $actual_cmd"
        log_command_breakdown "$actual_cmd"
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