#!/bin/bash
# Example script demonstrating the clean import pattern
# This replaces the old relative path sourcing

set -euo pipefail

# Script identification
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
SCRIPT_NAME="$(basename "$0")"

# === NEW CLEAN IMPORT PATTERN ===
# Instead of:
#   if [[ -f "$SCRIPT_DIR/lib/_common_.source.sh" ]]; then
#       source "$SCRIPT_DIR/lib/_common_.source.sh"
#   fi
#   if [[ -f "$SCRIPT_DIR/../lib/_common_.source.sh" ]]; then
#       source "$SCRIPT_DIR/../lib/_common_.source.sh"
#   fi

# Use this clean pattern:
SETUP_LIB_DIR="$(dirname "$SCRIPT_DIR")/_setup_lib_sh"
if [[ -f "$SETUP_LIB_DIR/_setup_lib_loader.source.sh" ]]; then
    source "$SETUP_LIB_DIR/_setup_lib_loader.source.sh"
    
    # Option 1: Load just the common libraries
    load_common_libs || {
        echo "ERROR: Failed to load required setup libraries" >&2
        exit 1
    }
    
    # Option 2: Load all setup libraries (if you need _users_and_groups_inspect.source.sh)
    # load_all_setup_libs || {
    #     echo "ERROR: Failed to load required setup libraries" >&2
    #     exit 1
    # }
    
    # Option 3: Load individual libraries as needed
    # source_setup_lib "_input_validation" || exit 1
    # source_setup_lib "_common_" || exit 1
    
else
    echo "ERROR: Setup library loader not found at $SETUP_LIB_DIR/_setup_lib_loader.source.sh" >&2
    exit 1
fi

# === BENEFITS OF THIS APPROACH ===
# 1. No complex relative paths (../../../lib/)
# 2. Intelligent path resolution handles different script locations
# 3. Clear error messages if libraries are missing
# 4. Dependency order is handled automatically
# 5. Single source of truth for library loading
# 6. Easy to maintain and debug

# Now you have access to all the functions:
log INFO "Clean import pattern loaded successfully!"
log INFO "Available functions include:"
log INFO "  - log(), error_exit()"
log INFO "  - validate_parameter_user(), validate_parameter_group(), etc."
log INFO "  - check_active_user_is_root(), check_active_user_has_sudo_access()"
log INFO "  - execute_or_dryrun(), check_command()"

# Example usage
if check_active_user_is_root; then
    log INFO "Running as root"
else
    log INFO "Running as regular user"
fi

# Example of secured parameter validation
if [[ $# -gt 0 ]]; then
    # This uses the specialized validation functions from the shared library
    test_user=$(validate_parameter_user "--user" "$1")
    log INFO "Validated user parameter: $test_user"
fi

log INFO "Script completed successfully"