#!/bin/bash
# Setup Library Loader
# Provides clean import functionality for shared shell libraries

# Function to source a shared library with intelligent path resolution
source_setup_lib() {
    local lib_name="$1"
    local calling_script_dir="${2:-$(dirname "$(readlink -f "${BASH_SOURCE[1]}")")}"
    
    # Ensure lib_name has proper extension
    if [[ "$lib_name" != *.source.sh ]]; then
        lib_name="${lib_name}.source.sh"
    fi
    
    # Try different possible locations for the shared library
    local possible_paths=(
        # Same directory as calling script (for scripts already in _setup_lib_sh)
        "$calling_script_dir/$lib_name"
        # Shared library from script directory
        "$calling_script_dir/_setup_lib_sh/$lib_name"
        # Shared library from parent directory (for scripts in subdirectories)
        "$calling_script_dir/../_setup_lib_sh/$lib_name"
        # Shared library from project root
        "$(dirname "$calling_script_dir")/_setup_lib_sh/$lib_name"
        # Legacy location (fallback)
        "$calling_script_dir/lib/$lib_name"
    )
    
    # Try to source from each possible location
    for lib_path in "${possible_paths[@]}"; do
        if [[ -f "$lib_path" ]]; then
            source "$lib_path"
            return 0
        fi
    done
    
    # If we get here, the library wasn't found
    echo "ERROR: Could not find shared library: $lib_name" >&2
    echo "Searched in:" >&2
    for lib_path in "${possible_paths[@]}"; do
        echo "  - $lib_path" >&2
    done
    return 1
}

# Convenience function to load common libraries
load_common_libs() {
    local calling_script_dir="${1:-$(dirname "$(readlink -f "${BASH_SOURCE[1]}")")}"
    
    # Load core libraries in dependency order
    source_setup_lib "_input_validation" "$calling_script_dir" || return 1
    source_setup_lib "_check_active_user" "$calling_script_dir" || return 1
    source_setup_lib "_check_tool" "$calling_script_dir" || return 1
    source_setup_lib "_common_" "$calling_script_dir" || return 1
    
    return 0
}

# Load installation constants and helper functions
load_installation_constants_lib() {
    local calling_script_dir="${1:-$(dirname "$(readlink -f "${BASH_SOURCE[1]}")")}"
    
    # Load installation constants library
    source_setup_lib "installation_constants" "$calling_script_dir" || return 1
    
    # Load the constants into shell variables
    load_installation_constants || return 1
    
    return 0
}

# Load package manager library
load_package_manager_lib() {
    local calling_script_dir="${1:-$(dirname "$(readlink -f "${BASH_SOURCE[1]}")")}"
    
    # Load package manager library
    source_setup_lib "_package_manager" "$calling_script_dir" || return 1
    
    return 0
}

# Alternative: Load all essential libraries at once
load_all_setup_libs() {
    local calling_script_dir="${1:-$(dirname "$(readlink -f "${BASH_SOURCE[1]}")")}"
    
    # Load all shared libraries
    source_setup_lib "_input_validation" "$calling_script_dir" || return 1
    source_setup_lib "_check_active_user" "$calling_script_dir" || return 1
    source_setup_lib "_check_tool" "$calling_script_dir" || return 1
    source_setup_lib "_users_and_groups_inspect" "$calling_script_dir" || return 1
    source_setup_lib "_common_" "$calling_script_dir" || return 1
    source_setup_lib "_package_manager" "$calling_script_dir" || return 1
    
    return 0
}

# Load all libraries including installation constants
load_all_libs_with_constants() {
    local calling_script_dir="${1:-$(dirname "$(readlink -f "${BASH_SOURCE[1]}")")}"
    
    # Load common libraries
    load_all_setup_libs "$calling_script_dir" || return 1
    
    # Load installation constants
    load_installation_constants_lib "$calling_script_dir" || return 1
    
    return 0
}