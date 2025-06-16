
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
        WARN)    echo -e "${YELLOW}[WARN]${NC} $message" ;;
        INFO)    echo -e "${GREEN}[INFO]${NC} $message" ;;
        DEBUG)   echo -e "${BLUE}[DEBUG]${NC} $message" ;;
        *)       echo "[$level] $message" ;;
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
# DRY RUN HELPER FUNCTIONS
# ============================================================================

# Function to execute command or show what would be done in dry-run mode
# Note: Command should already include sudo prefix if needed
execute_or_dryrun() {
    local cmd="$1"
    local success_msg="$2"
    local error_msg="$3"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would execute: $cmd"
        return 0
    fi
    
    log DEBUG "Executing: $cmd"
    
    if eval "$cmd"; then
        log INFO "$success_msg"
        return 0
    else
        log ERROR "$error_msg"
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