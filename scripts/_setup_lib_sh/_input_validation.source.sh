#!/bin/bash
# Input Validation Library
# Provides security validation functions to prevent command injection

# Colors for validation messages
VALIDATION_RED='\033[0;31m'
VALIDATION_GREEN='\033[0;32m'
VALIDATION_YELLOW='\033[1;33m'
VALIDATION_NC='\033[0m'

# Validation result codes
VALIDATION_SUCCESS=0
VALIDATION_ERROR=1

# Log validation events
validation_log() {
    local level="$1"
    local message="$2"
    
    # Use log function if available, otherwise echo to stderr
    if declare -f log >/dev/null 2>&1; then
        log "$level" "SECURITY: $message"
    else
        echo "[$level] SECURITY: $message" >&2
    fi
}

# Validate username according to POSIX standards
# Username must start with letter, contain only alphanumeric, dot, underscore, hyphen
# Max length 32 characters
validate_username() {
    local username="$1"
    local context="${2:-username}"
    
    if [[ -z "$username" ]]; then
        validation_log "ERROR" "Empty $context provided"
        return $VALIDATION_ERROR
    fi
    
    # Check length (max 32 characters)
    if [[ ${#username} -gt 32 ]]; then
        validation_log "ERROR" "Invalid $context '$username': exceeds 32 character limit"
        return $VALIDATION_ERROR
    fi
    
    # Check POSIX username pattern
    if [[ ! "$username" =~ ^[a-zA-Z][a-zA-Z0-9._-]*$ ]]; then
        validation_log "ERROR" "Invalid $context '$username': must start with letter and contain only alphanumeric, dot, underscore, hyphen"
        return $VALIDATION_ERROR
    fi
    
    # Check for reserved names
    case "$username" in
        root|daemon|bin|sys|sync|games|man|lp|mail|news|uucp|proxy|www-data|backup|list|irc|gnats|nobody|systemd*|_*)
            validation_log "WARN" "Username '$username' is a system reserved name"
            ;;
    esac
    
    # validation_log "DEBUG" "Username '$username' validation passed"
    return $VALIDATION_SUCCESS
}

# Validate group name (similar rules to username)
validate_group_name() {
    local groupname="$1"
    local context="${2:-group name}"
    
    # Use same validation as username
    validate_username "$groupname" "$context"
}

# Validate numeric value (UID/GID)
validate_numeric() {
    local value="$1"
    local name="$2"
    local min_value="${3:-0}"
    local max_value="${4:-65535}"
    
    if [[ -z "$value" ]]; then
        validation_log "ERROR" "Empty $name provided"
        return $VALIDATION_ERROR
    fi
    
    # Check if numeric
    if [[ ! "$value" =~ ^[0-9]+$ ]]; then
        validation_log "ERROR" "Invalid $name '$value': must be numeric"
        return $VALIDATION_ERROR
    fi
    
    # Check range
    if [[ "$value" -lt "$min_value" || "$value" -gt "$max_value" ]]; then
        validation_log "ERROR" "Invalid $name '$value': must be between $min_value and $max_value"
        return $VALIDATION_ERROR
    fi
    
    # Warn about reserved ranges
    if [[ "$value" -lt 1000 && "$value" -gt 0 ]]; then
        validation_log "WARN" "$name '$value' is in system reserved range (1-999)"
    fi
    
    # validation_log "DEBUG" "$name '$value' validation passed"
    return $VALIDATION_SUCCESS
}

# Validate file system path
validate_path() {
    local path="$1"
    local context="${2:-path}"
    local allow_relative="${3:-false}"
    
    if [[ -z "$path" ]]; then
        validation_log "ERROR" "Empty $context provided"
        return $VALIDATION_ERROR
    fi
    
    # Use whitelist approach - allow only safe characters for paths
    # Allow: letters, numbers, forward slash, underscore, hyphen, dot
    if [[ ! "$path" =~ ^[a-zA-Z0-9/_.-]+$ ]]; then
        validation_log "ERROR" "Invalid $context '$path': contains forbidden characters (only alphanumeric, /, _, -, . allowed)"
        return $VALIDATION_ERROR
    fi
    
    # Check for path traversal
    if [[ "$path" =~ \.\. ]]; then
        validation_log "ERROR" "Invalid $context '$path': contains path traversal (..)"
        return $VALIDATION_ERROR
    fi
    
    # Check if absolute path (unless relative allowed)
    if [[ "$allow_relative" != "true" && ! "$path" =~ ^/ ]]; then
        validation_log "ERROR" "Invalid $context '$path': must be absolute path"
        return $VALIDATION_ERROR
    fi
    
    # Check for null bytes (only if path is not empty)
    if [[ -n "$path" && "$path" != "${path%$'\0'*}" ]]; then
        validation_log "ERROR" "Invalid $context '$path': contains null bytes"
        return $VALIDATION_ERROR
    fi
    
    # Check length (max 4096 for most filesystems)
    if [[ ${#path} -gt 4096 ]]; then
        validation_log "ERROR" "Invalid $context '$path': exceeds maximum path length"
        return $VALIDATION_ERROR
    fi
    
    # validation_log "DEBUG" "$context '$path' validation passed"
    return $VALIDATION_SUCCESS
}

# Validate shell path
validate_shell() {
    local shell="$1"
    local context="${2:-shell}"
    
    if [[ -z "$shell" ]]; then
        validation_log "ERROR" "Empty $context provided"
        return $VALIDATION_ERROR
    fi
    
    # First validate as a path
    if ! validate_path "$shell" "$context"; then
        return $VALIDATION_ERROR
    fi
    
    # Check if shell exists in /etc/shells (if file exists)
    if [[ -f /etc/shells ]]; then
        if ! grep -Fxq "$shell" /etc/shells; then
            validation_log "WARN" "Shell '$shell' not found in /etc/shells"
        fi
    fi
    
    # Check if shell file exists and is executable
    if [[ -f "$shell" ]]; then
        if [[ ! -x "$shell" ]]; then
            validation_log "WARN" "Shell '$shell' exists but is not executable"
        fi
    else
        validation_log "WARN" "Shell '$shell' does not exist"
    fi
    
    # validation_log "DEBUG" "Shell '$shell' validation passed"
    return $VALIDATION_SUCCESS
}

# Validate password strength (basic checks)
# NOTE: Passwords can contain almost any characters for security
# We block null bytes and newlines due to technical limitations with password input methods
validate_password() {
    local password="$1"
    local context="${2:-password}"
    
    if [[ -z "$password" ]]; then
        validation_log "ERROR" "Empty $context provided"
        return $VALIDATION_ERROR
    fi
    
    # Check for null bytes (technical limitation - can't be passed in shell)
    if [[ "$password" =~ $'\0' ]]; then
        validation_log "ERROR" "Invalid $context: contains null bytes"
        return $VALIDATION_ERROR
    fi
    
    # Check for newlines/carriage returns (limitation with password confirmation)
    # smbpasswd expects: password<newline>password<newline>
    # A password with newlines would break this format
    if [[ "$password" =~ $'\n' ]]; then
        validation_log "ERROR" "Invalid $context: contains newline characters (not supported by password confirmation protocol)"
        return $VALIDATION_ERROR
    fi
    
    if [[ "$password" =~ $'\r' ]]; then
        validation_log "ERROR" "Invalid $context: contains carriage return characters (not supported by password confirmation protocol)"
        return $VALIDATION_ERROR
    fi
    
    # Basic length check (allow very strong passwords)
    if [[ ${#password} -lt 1 ]]; then
        validation_log "ERROR" "Invalid $context: minimum length not met"
        return $VALIDATION_ERROR
    fi
    
    if [[ ${#password} -gt 1024 ]]; then
        validation_log "ERROR" "Invalid $context: exceeds maximum length (1024 chars)"
        return $VALIDATION_ERROR
    fi
    
    # Log character types for debugging (without revealing password)
    local has_special=false
    if [[ "$password" =~ [^a-zA-Z0-9] ]]; then
        has_special=true
    fi
    
    # validation_log "DEBUG" "$context validation passed (length: ${#password}, has_special_chars: $has_special)"
    return $VALIDATION_SUCCESS
}

# Sanitize string for use in regex patterns
sanitize_for_regex() {
    local input="$1"
    # Escape regex metacharacters: . * ^ $ + ? { } [ ] \ | ( )
    printf '%s' "$input" | sed 's/[[\.*^$()+?{|}]/\\&/g'
}

# Validate and sanitize comment/description fields
validate_comment() {
    local comment="$1"
    local context="${2:-comment}"
    local max_length="${3:-256}"
    
    if [[ -z "$comment" ]]; then
        # Empty comments are usually OK
        return $VALIDATION_SUCCESS
    fi
    
    # Check for dangerous shell metacharacters
    # Block: ; | & ` $ ( ) < >
    if [[ "$comment" =~ [';|&`$()<>'] ]]; then
        validation_log "ERROR" "Invalid $context '$comment': contains shell metacharacters"
        return $VALIDATION_ERROR
    fi
    
    # Check for null bytes
    if [[ "$comment" != "${comment%$'\0'*}" ]]; then
        validation_log "ERROR" "Invalid $context: contains null bytes"
        return $VALIDATION_ERROR
    fi
    
    # Check length
    if [[ ${#comment} -gt "$max_length" ]]; then
        validation_log "ERROR" "Invalid $context: exceeds maximum length of $max_length"
        return $VALIDATION_ERROR
    fi
    
    # validation_log "DEBUG" "$context validation passed"
    return $VALIDATION_SUCCESS
}

# Validate permission mode (octal)
validate_permission_mode() {
    local mode="$1"
    local context="${2:-permission mode}"
    
    if [[ -z "$mode" ]]; then
        validation_log "ERROR" "Empty $context provided"
        return $VALIDATION_ERROR
    fi
    
    # Check if valid octal mode (3 or 4 digits)
    if [[ ! "$mode" =~ ^[0-7]{3,4}$ ]]; then
        validation_log "ERROR" "Invalid $context '$mode': must be 3-4 digit octal (e.g., 755, 0644)"
        return $VALIDATION_ERROR
    fi
    
    # validation_log "DEBUG" "$context '$mode' validation passed"
    return $VALIDATION_SUCCESS
}

# Main validation function that can validate multiple types
validate_input() {
    local type="$1"
    local value="$2"
    local context="${3:-$type}"
    
    case "$type" in
        username|user)
            validate_username "$value" "$context"
            ;;
        group|groupname)
            validate_group_name "$value" "$context"
            ;;
        uid|gid|numeric)
            validate_numeric "$value" "$context"
            ;;
        path)
            validate_path "$value" "$context"
            ;;
        shell)
            validate_shell "$value" "$context"
            ;;
        password)
            validate_password "$value" "$context"
            ;;
        comment)
            validate_comment "$value" "$context"
            ;;
        mode|permissions)
            validate_permission_mode "$value" "$context"
            ;;
        *)
            validation_log "ERROR" "Unknown validation type: $type"
            return $VALIDATION_ERROR
            ;;
    esac
}

# Validation summary function for debugging
show_validation_rules() {
    cat << 'EOF'
Input Validation Rules:
======================

Usernames:
- Must start with letter (a-z, A-Z)
- Can contain letters, numbers, dot, underscore, hyphen
- Maximum 32 characters
- No shell metacharacters

Paths:
- Must be absolute (start with /)
- Only allowed characters: letters, numbers, /, _, -, .
- No path traversal (..)
- No null bytes
- Maximum 4096 characters

Numeric Values (UID/GID):
- Must be numeric only
- Range 0-65535
- Values 1-999 are system reserved

Shells:
- Must be valid path
- Should exist in /etc/shells
- Should be executable

Passwords:
- No null bytes
- Warning for single quotes
- Length 1-256 characters

Permission Modes:
- Must be 3-4 digit octal (e.g., 755, 0644)

Comments:
- No shell metacharacters (; | & ` $ ( ) < >)
- No null bytes
- Maximum 256 characters
EOF
}

# Convenience aliases for specific path types
validate_file_path() {
    local path="$1"
    local context="${2:-file path}"
    validate_path "$path" "$context" false
}

validate_directory_path() {
    local path="$1"
    local context="${2:-directory path}"
    validate_path "$path" "$context" false
}

# Validate email address
validate_email_address() {
    local email="$1"
    local context="${2:-email address}"
    
    if [[ -z "$email" ]]; then
        validation_log "ERROR" "Empty $context provided"
        return $VALIDATION_ERROR
    fi
    
    # Basic email validation - must contain @ and basic structure
    if [[ ! "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        validation_log "ERROR" "Invalid $context '$email': must be valid email format"
        return $VALIDATION_ERROR
    fi
    
    # validation_log "INFO" "Successfully validated $context: '$email'"
    return $VALIDATION_SUCCESS
}

# Validate hostname or IP address
validate_hostname_or_ip() {
    local host="$1"
    local context="${2:-hostname/IP}"
    
    if [[ -z "$host" ]]; then
        validation_log "ERROR" "Empty $context provided"
        return $VALIDATION_ERROR
    fi
    
    # Allow alphanumeric, dots, hyphens for hostnames/IPs
    if [[ ! "$host" =~ ^[a-zA-Z0-9.-]+$ ]]; then
        validation_log "ERROR" "Invalid $context '$host': contains forbidden characters"
        return $VALIDATION_ERROR
    fi
    
    # Basic length check
    if [[ ${#host} -gt 253 ]]; then
        validation_log "ERROR" "Invalid $context '$host': exceeds maximum length"
        return $VALIDATION_ERROR
    fi
    
    # validation_log "INFO" "Successfully validated $context: '$host'"
    return $VALIDATION_SUCCESS
}

# Validate port number
validate_port_number() {
    local port="$1"
    local context="${2:-port number}"
    
    if [[ -z "$port" ]]; then
        validation_log "ERROR" "Empty $context provided"
        return $VALIDATION_ERROR
    fi
    
    # Must be numeric
    if [[ ! "$port" =~ ^[0-9]+$ ]]; then
        validation_log "ERROR" "Invalid $context '$port': must be numeric"
        return $VALIDATION_ERROR
    fi
    
    # Must be in valid port range
    if [[ "$port" -lt 1 || "$port" -gt 65535 ]]; then
        validation_log "ERROR" "Invalid $context '$port': must be between 1 and 65535"
        return $VALIDATION_ERROR
    fi
    
    # validation_log "INFO" "Successfully validated $context: '$port'"
    return $VALIDATION_SUCCESS
}

# Validate safe text input (for choices and general text)
validate_safe_text() {
    local text="$1"
    local context="${2:-text input}"
    
    # Use existing validate_comment function which has proper security checks
    validate_comment "$text" "$context"
}