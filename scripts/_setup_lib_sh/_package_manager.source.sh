#!/bin/bash
# Package Manager Library
# Centralized package detection, cache updates, and installation

# Package manager cache status
PACKAGE_MANAGER_CACHE_UPDATED=false

# Supported package managers configuration
declare -A PACKAGE_MANAGERS=(
    ["apt"]="apt-get"
    ["dnf"]="dnf" 
    ["yum"]="yum"
    ["pacman"]="pacman"
    ["zypper"]="zypper"
    ["brew"]="brew"
)

# Package manager update commands (without sudo - will be added dynamically)
declare -A UPDATE_COMMANDS=(
    ["apt"]="apt-get update"
    ["dnf"]="dnf makecache"
    ["yum"]="yum makecache"
    ["pacman"]="pacman -Sy"
    ["zypper"]="zypper refresh"
    ["brew"]="brew update"
)

# Package manager install commands (without sudo - will be added dynamically)
declare -A INSTALL_COMMANDS=(
    ["apt"]="apt-get install -y"
    ["dnf"]="dnf install -y" 
    ["yum"]="yum install -y"
    ["pacman"]="pacman -S --noconfirm"
    ["zypper"]="zypper install -y"
    ["brew"]="brew install"
)


# Detect and validate the available package manager
get_package_manager() {
    local context="${1:-package management}"
    
    # Check each package manager in order of preference
    for pm in "apt" "dnf" "yum" "pacman" "zypper" "brew"; do
        local cmd="${PACKAGE_MANAGERS[$pm]}"
        if execute "command -v \"$cmd\" >/dev/null 2>&1" \
                  "Package manager found: $pm ($cmd)" \
                  "Package manager not found: $pm ($cmd)" \
                  "Check if $pm package manager is available on system"; then
            echo "$pm"
            return 0
        fi
    done
    
    log ERROR "No supported package manager found"
    log ERROR "Supported package managers: ${!PACKAGE_MANAGERS[*]}"
    return 1
}


# Update package manager cache
update_package_cache() {
    local context="${1:-package cache update}"
    local force="${2:-false}"
    
    # Skip if already updated unless forced
    if [[ "$PACKAGE_MANAGER_CACHE_UPDATED" == "true" && "$force" != "true" ]]; then
        echo "Package cache already updated (use force=true to update again)"
        return 0
    fi
    
    local pm
    pm=$(get_package_manager "$context") || return 1
    
    local update_cmd="${UPDATE_COMMANDS[$pm]}"
    if [[ -z "$update_cmd" ]]; then
        log ERROR "Update command not configured for package manager: $pm"
        return 1
    fi
    
    # Get command with sudo prefix if required
    local full_cmd
    full_cmd=$(add_sudo_if_required "${PACKAGE_MANAGERS[$pm]}" "$update_cmd") || return 1
    
    if execute_or_dryrun "$full_cmd" \
                        "Package cache updated successfully using $pm" \
                        "Failed to update package cache using $pm" \
                        "Update package manager cache to ensure latest package information"; then
        PACKAGE_MANAGER_CACHE_UPDATED=true
        return 0
    else
        return 1
    fi
}


# Install packages with the detected package manager
# Package managers handle already-installed packages gracefully
install_packages() {
    local context="${1:-package installation}"
    shift
    local packages=("$@")
    
    if [[ ${#packages[@]} -eq 0 ]]; then
        log INFO "No packages to install"
        return 0
    fi
    
    # Validate package names
    for package in "${packages[@]}"; do
        if ! validate_linux_package_name "$package" "package installation"; then
            log ERROR "Invalid package name: $package"
            return 1
        fi
    done
    
    local pm
    pm=$(get_package_manager "$context") || return 1
    
    local install_cmd="${INSTALL_COMMANDS[$pm]}"
    if [[ -z "$install_cmd" ]]; then
        log ERROR "Install command not configured for package manager: $pm"
        return 1
    fi
    
    local package_list="${packages[*]}"
    
    # Get command with sudo prefix if required
    local full_cmd
    full_cmd=$(add_sudo_if_required "${PACKAGE_MANAGERS[$pm]}" "$install_cmd $package_list") || return 1
    
    execute_or_dryrun "$full_cmd" \
                     "Successfully installed packages using $pm: $package_list" \
                     "Failed to install packages using $pm: $package_list" \
                     "Install system packages for application functionality"
}

# Update cache and install packages in one operation (most common use case)
update_and_install_packages() {
    local context="${1:-update and install}"
    shift
    local packages=("$@")
    
    if [[ ${#packages[@]} -eq 0 ]]; then
        log INFO "No packages specified for installation"
        return 0
    fi
    
    # Update cache first
    update_package_cache "$context" || {
        log WARN "Package cache update failed, attempting install anyway"
    }
    
    # Install packages (package manager handles already-installed packages)
    install_packages "$context" "${packages[@]}"
}

# Install packages using an associative array mapping
# Usage: 
#   declare -A pkg_map
#   pkg_map[apt]="package1 package2"
#   pkg_map[dnf]="package1-devel"
#   install_packages_from_map "context" pkg_map
install_packages_from_map() {
    local context="$1"
    local -n package_map=$2  # nameref to the associative array
    
    # Get current package manager
    local pm
    pm=$(get_package_manager "$context") || return 1
    
    log INFO "Using package manager: $pm"
    
    # Show package mapping in verbose mode
    if [[ "${VERBOSE:-false}" == "true" || "${DRY_RUN:-false}" == "true" ]]; then
        show_package_mapping package_map
    fi
    
    # Get packages for this package manager
    local packages="${package_map[$pm]}"
    
    # If no specific mapping, try a default key
    if [[ -z "$packages" && -n "${package_map[default]}" ]]; then
        packages="${package_map[default]}"
        log INFO "Using default package list: $packages"
    elif [[ -z "$packages" ]]; then
        log INFO "No packages defined for package manager: $pm"
        return 0
    else
        log INFO "Package list for $pm: $packages"
    fi
    
    # Convert to array and install
    read -ra package_array <<< "$packages"
    update_and_install_packages "$context" "${package_array[@]}"
}

# Helper function to print package mapping for debugging
show_package_mapping() {
    local -n map=$1
    echo "Package mapping:"
    for pm in "${!map[@]}"; do
        echo "  $pm: ${map[$pm]}"
    done
}

# Display package manager information
show_package_manager_info() {
    local pm
    pm=$(get_package_manager "info display") || {
        log ERROR "No supported package manager detected"
        log INFO "Supported: ${!PACKAGE_MANAGERS[*]}"
        return 1
    }
    
    local update_cmd
    update_cmd=$(add_sudo_if_required "${PACKAGE_MANAGERS[$pm]}" "${UPDATE_COMMANDS[$pm]}" 2>/dev/null) || update_cmd="[ERROR]"
    
    local install_cmd  
    install_cmd=$(add_sudo_if_required "${PACKAGE_MANAGERS[$pm]}" "${INSTALL_COMMANDS[$pm]}" 2>/dev/null) || install_cmd="[ERROR]"
    
    echo "Package Manager Information:"
    echo "  Detected: $pm (${PACKAGE_MANAGERS[$pm]})"
    echo "  Update command: $update_cmd"
    echo "  Install command: $install_cmd <packages>"
    
    local has_privileges="No"
    if [[ "$update_cmd" != "[ERROR]" && "$install_cmd" != "[ERROR]" ]]; then
        has_privileges="Yes"
    fi
    echo "  Has install privileges: $has_privileges"
    echo "  Cache updated: $PACKAGE_MANAGER_CACHE_UPDATED"
}