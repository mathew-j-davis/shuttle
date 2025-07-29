#!/bin/bash
# sudo_helpers.source.sh
# Common sudo helper functions for installation scripts

# Check if a path is a system path that typically requires sudo
is_system_path() {
    local path="$1"
    [[ "$path" == /etc/* ]] || [[ "$path" == /opt/* ]] || [[ "$path" == /var/* ]] || [[ "$path" == /usr/local/* ]]
}

# Set appropriate permissions for service mode installations
set_service_permissions() {
    local path="$1"
    local install_mode="${2:-$INSTALL_MODE}"
    
    if [[ "$install_mode" == "service" ]]; then
        if getent group shuttle >/dev/null 2>&1; then
            sudo chown :shuttle "$path" 2>/dev/null || true
            sudo chmod 775 "$path" 2>/dev/null || true
        fi
    fi
}

# Change file permissions with automatic sudo detection and dry-run support
# Usage: chmod_with_sudo_fallback <path> <mode> [description] [allow_sudo]
chmod_with_sudo_fallback() {
    local path="$1"
    local mode="$2"
    local description="${3:-file}"
    local allow_sudo="${4:-true}"
    
    # Validate inputs
    if [[ -z "$path" || -z "$mode" ]]; then
        echo "Error: Path and mode are required for chmod_with_sudo_fallback" >&2
        return 1
    fi
    
    # Handle dry run mode first (before checking if path exists)
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        echo -e "${BLUE:-}[DRY RUN] Would change permissions: chmod $mode $path${NC:-}"
        return 0
    fi
    
    # Check if path exists (only in non-dry-run mode)
    if [[ ! -e "$path" ]]; then
        echo "Error: Path does not exist: $path" >&2
        return 1
    fi
    
    # Try chmod without sudo first
    if chmod "$mode" "$path" 2>/dev/null; then
        [[ "${VERBOSE:-false}" == "true" ]] && echo -e "${GREEN:-}✅ Changed permissions: $path -> $mode${NC:-}"
        return 0
    fi
    
    # If sudo is allowed, try with sudo
    if [[ "$allow_sudo" == "true" ]]; then
        if sudo chmod "$mode" "$path" 2>/dev/null; then
            [[ "${VERBOSE:-false}" == "true" ]] && echo -e "${GREEN:-}✅ Changed permissions with sudo: $path -> $mode${NC:-}"
            return 0
        fi
    fi
    
    echo "Error: Cannot change permissions of $description: $path" >&2
    return 1
}

# Make file executable with automatic sudo detection and dry-run support  
# Usage: make_executable_with_sudo_fallback <path> [description] [allow_sudo]
make_executable_with_sudo_fallback() {
    local path="$1"
    local description="${2:-file}"
    local allow_sudo="${3:-true}"
    
    chmod_with_sudo_fallback "$path" "+x" "$description" "$allow_sudo"
}

# Create directory with automatic sudo detection
create_directory_with_auto_sudo() {
    local dir_path="$1"
    local description="${2:-directory}"
    local quiet="${3:-false}"
    local install_mode="${4:-$INSTALL_MODE}"
    
    # Skip if directory already exists
    if [[ -d "$dir_path" ]]; then
        [[ "$quiet" != "true" ]] && echo -e "    ${GREEN:-}✅ Directory exists: $dir_path${NC:-}"
        return 0
    fi
    
    # Handle dry run mode
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        echo -e "    ${BLUE:-}[DRY RUN] Would create $description: $dir_path${NC:-}"
        return 0
    fi
    
    [[ "$quiet" != "true" ]] && echo -e "    ${YELLOW:-}Creating $description: $dir_path${NC:-}"
    
    # Try creating without sudo first
    if mkdir -p "$dir_path" 2>/dev/null; then
        [[ "$quiet" != "true" ]] && echo -e "    ${GREEN:-}✅ Directory created: $dir_path${NC:-}"
        return 0
    fi
    
    # Check if this is a system path that needs sudo
    if is_system_path "$dir_path"; then
        [[ "$quiet" != "true" ]] && echo -e "    ${YELLOW:-}Attempting with sudo for system directory...${NC:-}"
        if sudo mkdir -p "$dir_path" 2>/dev/null; then
            set_service_permissions "$dir_path" "$install_mode"
            [[ "$quiet" != "true" ]] && echo -e "    ${GREEN:-}✅ Directory created with sudo: $dir_path${NC:-}"
            return 0
        else
            echo -e "    ${RED:-}❌ Failed to create directory even with sudo: $dir_path${NC:-}" >&2
            echo "    Please check permissions and parent directory existence." >&2
            return 1
        fi
    else
        echo -e "    ${RED:-}❌ Failed to create directory: $dir_path${NC:-}" >&2
        echo "    You may need elevated permissions or the parent directory may not exist." >&2
        return 1
    fi
}

# Check if a path is readable, with optional sudo fallback
check_path_readable() {
    local path="$1"
    local allow_sudo="${2:-true}"
    
    # Try reading without sudo first
    if [[ -r "$path" ]]; then
        return 0
    fi
    
    # If sudo is allowed and this is a system path, try with sudo
    if [[ "$allow_sudo" == "true" ]] && is_system_path "$path"; then
        if sudo test -r "$path" 2>/dev/null; then
            return 0
        fi
    fi
    
    return 1
}

# Read file content with sudo fallback if needed
read_file_with_sudo_fallback() {
    local file_path="$1"
    local allow_sudo="${2:-true}"
    
    # Try reading without sudo first
    if [[ -r "$file_path" ]]; then
        cat "$file_path"
        return 0
    fi
    
    # If sudo is allowed and this is a system path, try with sudo
    if [[ "$allow_sudo" == "true" ]] && is_system_path "$file_path"; then
        if sudo test -r "$file_path" 2>/dev/null; then
            sudo cat "$file_path"
            return 0
        fi
    fi
    
    echo "Error: Cannot read file $file_path" >&2
    return 1
}

# Write file with sudo fallback if needed
write_file_with_sudo_fallback() {
    local file_path="$1"
    local content="$2"
    local allow_sudo="${3:-true}"
    
    # Try writing without sudo first
    if echo "$content" > "$file_path" 2>/dev/null; then
        return 0
    fi
    
    # If sudo is allowed, try with sudo (no path restriction per user request)
    if [[ "$allow_sudo" == "true" ]]; then
        if echo "$content" | sudo tee "$file_path" >/dev/null 2>&1; then
            return 0
        fi
    fi
    
    echo "Error: Cannot write to file $file_path" >&2
    return 1
}

# Write file from temp file with sudo fallback - for Python scripts
# This copies a temporary file to the final location with sudo if needed
write_temp_file_with_sudo_fallback() {
    local temp_file_path="$1"
    local final_file_path="$2"
    local allow_sudo="${3:-true}"
    
    # Validate temp file exists
    if [[ ! -f "$temp_file_path" ]]; then
        echo "Error: Temporary file does not exist: $temp_file_path" >&2
        return 1
    fi
    
    # Try copying without sudo first
    if cp "$temp_file_path" "$final_file_path" 2>/dev/null; then
        return 0
    fi
    
    # If sudo is allowed, try with sudo (no path restriction per user request)
    if [[ "$allow_sudo" == "true" ]]; then
        if sudo cp "$temp_file_path" "$final_file_path" 2>/dev/null; then
            return 0
        fi
    fi
    
    echo "Error: Cannot copy temp file to final location: $final_file_path" >&2
    return 1
}

# Check if a configuration file exists and is readable
check_config_file_access() {
    local config_path="$1"
    local allow_sudo="${2:-true}"
    local show_warnings="${3:-true}"
    
    # Check if file exists first
    if [[ ! -f "$config_path" ]] && [[ ! -L "$config_path" ]]; then
        # For system paths, also check with sudo
        if [[ "$allow_sudo" == "true" ]] && is_system_path "$config_path"; then
            if ! sudo test -f "$config_path" 2>/dev/null; then
                [[ "$show_warnings" == "true" ]] && echo "Warning: Configuration file does not exist: $config_path" >&2
                return 1
            fi
        else
            [[ "$show_warnings" == "true" ]] && echo "Warning: Configuration file does not exist: $config_path" >&2
            return 1
        fi
    fi
    
    # Check if file is readable
    if check_path_readable "$config_path" "$allow_sudo"; then
        return 0
    else
        [[ "$show_warnings" == "true" ]] && echo "Warning: Configuration file exists but is not readable: $config_path" >&2
        [[ "$show_warnings" == "true" ]] && echo "You may need elevated permissions to read this file." >&2
        return 1
    fi
}

# Parse a configuration file with sudo fallback if needed
# This is a simple key=value parser that works with config files
parse_config_file_with_sudo() {
    local config_path="$1"
    local allow_sudo="${2:-true}"
    local var_prefix="${3:-CONFIG_}"
    
    if ! check_config_file_access "$config_path" "$allow_sudo" "false"; then
        return 1
    fi
    
    # Read the file content
    local file_content
    if ! file_content=$(read_file_with_sudo_fallback "$config_path" "$allow_sudo"); then
        echo "Error: Failed to read configuration file: $config_path" >&2
        return 1
    fi
    
    # Parse simple key=value pairs (skip comments and empty lines)
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" ]] && continue
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Parse key=value format
        if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local value="${BASH_REMATCH[2]}"
            
            # Clean up key and value (remove surrounding whitespace)
            key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            
            # Remove quotes from value if present
            if [[ "$value" =~ ^[\"\'](.*)[\"\']$ ]]; then
                value="${BASH_REMATCH[1]}"
            fi
            
            # Export the variable with prefix
            export "${var_prefix}${key}"="$value"
        fi
    done <<< "$file_content"
    
    return 0
}