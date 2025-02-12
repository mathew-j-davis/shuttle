#!/bin/bash

set -e  # Exit on error

# Constants
# This the public key of the owasp dependency check developer
# This key is not secret. 
# It is openly published on the net to be used to verify downloads
OWASP_KEY="259A55407DD6C00299E6607EFFDE55BE73A2D1ED"
INSTALL_DIR="$HOME/.owasp"
VERSION_PATTERN="^[0-9]+\.[0-9]+\.[0-9]+$"

# Functions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    log "ERROR: $1" >&2
    exit 1
}

validate_version() {
    if [[ ! $1 =~ $VERSION_PATTERN ]]; then
        error "Invalid version format. Expected x.y.z"
    fi
}

# Compare semantic versions
# Returns 0 if version1 >= version2
# Returns 1 if version1 < version2
compare_versions() {
    local version1=$1
    local version2=$2
    
    # Split versions into arrays
    IFS='.' read -ra VER1 <<< "$version1"
    IFS='.' read -ra VER2 <<< "$version2"
    
    # Compare major version
    if [[ ${VER1[0]} -gt ${VER2[0]} ]]; then
        return 0
    elif [[ ${VER1[0]} -lt ${VER2[0]} ]]; then
        return 1
    fi
    
    # Compare minor version
    if [[ ${VER1[1]} -gt ${VER2[1]} ]]; then
        return 0
    elif [[ ${VER1[1]} -lt ${VER2[1]} ]]; then
        return 1
    fi
    
    # Compare patch version
    if [[ ${VER1[2]} -ge ${VER2[2]} ]]; then
        return 0
    else
        return 1
    fi
}

get_installed_version() {
    if command -v dependency-check.sh >/dev/null; then
        dependency-check.sh --version | grep -oP '\d+\.\d+\.\d+'
    fi
}

download_and_verify() {
    local version=$1
    local base_url="https://github.com/jeremylong/DependencyCheck/releases/download/v${version}"
    local zip_file="dependency-check-${version}-release.zip"
    local sig_file="${zip_file}.asc"
    
    log "Downloading OWASP Dependency-Check ${version}..."
    
    # Download files
    wget -q --show-progress "${base_url}/${zip_file}" || error "Download failed"
    wget -q "${base_url}/${sig_file}" || error "Signature download failed"
    
    # Import key and verify signature
    log "Verifying GPG signature..."
    gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys "$OWASP_KEY" 2>/dev/null || \
        error "Failed to import GPG key"
    
    gpg --verify "$sig_file" "$zip_file" 2>/dev/null || error "GPG verification failed"
    
    # Install
    log "Installing..."
    mkdir -p "$INSTALL_DIR"
    unzip -q -o "$zip_file" -d "$INSTALL_DIR"
    
    # Cleanup
    rm -f "$zip_file" "$sig_file"
    
    # Add to PATH if not already there
    INSTALL_BIN="$INSTALL_DIR/dependency-check/bin"
    if [[ ":$PATH:" != *":$INSTALL_BIN:"* ]]; then
        echo "export PATH=\"$INSTALL_BIN:\$PATH\"" >> "$HOME/.bashrc"
        export PATH="$INSTALL_BIN:$PATH"
    fi
}

run_scan() {
    local project_path=$1
    log "Running dependency check on $project_path"
    
    dependency-check.sh \
        --scan "$project_path" \
        --format HTML \
        --out "dependency-check-report.html" || error "Scan failed"
        
    log "Scan complete. Report generated: dependency-check-report.html"
}

# Main script
main() {
    local version=$1
    local project_path=${2:-.}
    
    # Check if project path exists
    [[ -d "$project_path" ]] || error "Project path does not exist: $project_path"
    
    # Get current version
    current_version=$(get_installed_version)
    
    # Handle version logic
    if [[ -z "$version" && -z "$current_version" ]]; then
        error "No version specified and OWASP Dependency-Check not installed"
    fi
    
    if [[ -n "$version" ]]; then
        validate_version "$version"
        if [[ -z "$current_version" ]]; then
            download_and_verify "$version"
        else
            if ! compare_versions "$current_version" "$version"; then
                log "Updating from version $current_version to $version"
                download_and_verify "$version"
            else
                log "Current version $current_version meets or exceeds required version $version"
            fi
        fi
    fi
    
    run_scan "$project_path"
}

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --version) version="$2"; shift ;;
        --project-path) project_path="$2"; shift ;;
        *) error "Unknown parameter: $1" ;;
    esac
    shift
done

main "$version" "$project_path" 