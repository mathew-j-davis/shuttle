#!/bin/bash
# 02_env_and_venv.sh - Set up Shuttle environment variables and optionally create venv
#
# Usage: 
#   ./02_env_and_venv.sh                    # Use system production defaults (for services)
#   ./02_env_and_venv.sh -e                 # Use development defaults
#   ./02_env_and_venv.sh -u                 # Use user production defaults
#   ./02_env_and_venv.sh --do-not-create-venv  # Skip venv creation (any mode)
#   ./02_env_and_venv.sh --verbose          # Show detailed output
#   ./02_env_and_venv.sh [config] [venv] [work]  # Use custom paths
#
# Flags can be combined: ./02_env_and_venv.sh -e --do-not-create-venv --verbose

set -euo pipefail

# Script identification
SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source required libraries - simple and direct
source "$SCRIPT_DIR/_sources.sh"

# Get home directory and project root
HOME_DIR=$(eval echo ~$USER)
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Initialize flags
DEV_MODE=false
USER_MODE=false
CREATE_VENV=true
DRY_RUN=false
VERBOSE=false
STAGING_MODE=false
STAGING_DIR=""
FINAL_CONFIG_PATH=""
FINAL_TEST_WORK_DIR=""
FINAL_VENV_PATH=""

# Parse flags
REMAINING_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -e)
            DEV_MODE=true
            shift
            ;;
        -u)
            USER_MODE=true
            shift
            ;;
        --do-not-create-venv)
            CREATE_VENV=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --staging-dir)
            STAGING_MODE=true
            STAGING_DIR="$2"
            shift 2
            ;;
        --final-config-path)
            FINAL_CONFIG_PATH="$2"
            shift 2
            ;;
        --final-test-work-dir)
            FINAL_TEST_WORK_DIR="$2"
            shift 2
            ;;
        --final-venv-path)
            FINAL_VENV_PATH="$2"
            shift 2
            ;;
        *)
            REMAINING_ARGS+=("$1")
            shift
            ;;
    esac
done

# Restore positional parameters
set -- "${REMAINING_ARGS[@]}"

# Set default paths based on mode
if [[ "$DEV_MODE" == true ]]; then
    # Development defaults - use project root
    DEFAULT_CONFIG_PATH="$PROJECT_ROOT/config/config.conf"
    DEFAULT_VENV_PATH="$PROJECT_ROOT/.venv"
    DEFAULT_TEST_WORK_DIR="$PROJECT_ROOT/test_area"
    DEFAULT_TEST_CONFIG_PATH="$PROJECT_ROOT/test_area/test_config.conf"
    echo "Using development mode defaults..."
elif [[ "$USER_MODE" == true ]]; then
    # User production defaults - under user's home directory
    DEFAULT_CONFIG_PATH="$HOME_DIR/.config/shuttle/config.conf"
    DEFAULT_VENV_PATH="$HOME_DIR/.local/share/shuttle/venv"
    DEFAULT_TEST_WORK_DIR="$HOME_DIR/.local/share/shuttle/test_area"
    DEFAULT_TEST_CONFIG_PATH="$HOME_DIR/.local/share/shuttle/test_area/test_config.conf"
    echo "Using user production mode defaults..."
else
    # System production defaults - shared paths for service accounts
    DEFAULT_CONFIG_PATH="/etc/shuttle/config.conf"
    DEFAULT_VENV_PATH="/opt/shuttle/venv"
    DEFAULT_TEST_WORK_DIR="/var/lib/shuttle"
    DEFAULT_TEST_CONFIG_PATH="/var/lib/shuttle/test_config.conf"
    echo "Using system production mode defaults..."
fi

# Parse remaining arguments (allow overriding even in dev mode)
CONFIG_PATH=${1:-$DEFAULT_CONFIG_PATH}
VENV_PATH=${2:-$DEFAULT_VENV_PATH}
TEST_WORK_DIR=${3:-$DEFAULT_TEST_WORK_DIR}
TEST_CONFIG_PATH=${4:-$DEFAULT_TEST_CONFIG_PATH}

# Handle staging mode
if [[ "$STAGING_MODE" == true ]]; then
    # In staging mode, use final paths for environment variable content
    # but save files to staging directory
    FINAL_CONFIG_PATH=${FINAL_CONFIG_PATH:-$CONFIG_PATH}
    FINAL_TEST_WORK_DIR=${FINAL_TEST_WORK_DIR:-$TEST_WORK_DIR}
    FINAL_VENV_PATH=${FINAL_VENV_PATH:-$VENV_PATH}
    FINAL_TEST_CONFIG_PATH="$FINAL_TEST_WORK_DIR/test_config.conf"
    
    # Update actual file creation paths to staging directory
    CONFIG_PATH="$STAGING_DIR/shuttle_config.yaml"
    VENV_PATH="$STAGING_DIR/venv"
    TEST_WORK_DIR="$STAGING_DIR/work"
    TEST_CONFIG_PATH="$STAGING_DIR/work/test_config.conf"
    
    echo "Staging mode: Creating files in $STAGING_DIR but referencing final paths"
else
    # Normal mode: final paths are the same as actual paths
    FINAL_CONFIG_PATH="$CONFIG_PATH"
    FINAL_TEST_WORK_DIR="$TEST_WORK_DIR"
    FINAL_VENV_PATH="$VENV_PATH"
    FINAL_TEST_CONFIG_PATH="$TEST_CONFIG_PATH"
fi

# Determine install mode for permission handling
CURRENT_INSTALL_MODE="service"  # Default
if [[ "$DEV_MODE" == true ]]; then
    CURRENT_INSTALL_MODE="dev"
elif [[ "$USER_MODE" == true ]]; then
    CURRENT_INSTALL_MODE="user"
fi

# Create directories (but not venv yet)
if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would create directories:"
    echo "  mkdir -p $(dirname "$CONFIG_PATH")"
    echo "  mkdir -p $(dirname "$VENV_PATH")"
    echo "  mkdir -p $TEST_WORK_DIR"
else
    # Use the shared sudo helper functions
    create_directory_with_auto_sudo "$(dirname "$CONFIG_PATH")" "config directory" "false" "$CURRENT_INSTALL_MODE"
    create_directory_with_auto_sudo "$(dirname "$VENV_PATH")" "venv parent directory" "false" "$CURRENT_INSTALL_MODE"  
    create_directory_with_auto_sudo "$TEST_WORK_DIR" "test work directory" "false" "$CURRENT_INSTALL_MODE"
fi

# Set environment variables for this session (use final paths for staging mode)
if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would export environment variables:"
    echo "  SHUTTLE_CONFIG_PATH=\"$FINAL_CONFIG_PATH\""
    echo "  SHUTTLE_TEST_WORK_DIR=\"$FINAL_TEST_WORK_DIR\""
    echo "  SHUTTLE_TEST_CONFIG_PATH=\"$FINAL_TEST_CONFIG_PATH\""
else
    export SHUTTLE_CONFIG_PATH="$FINAL_CONFIG_PATH"
    export SHUTTLE_TEST_WORK_DIR="$FINAL_TEST_WORK_DIR"
    export SHUTTLE_TEST_CONFIG_PATH="$FINAL_TEST_CONFIG_PATH"
fi

# Determine where to save shuttle_env.sh
# Save the environment file in the same directory as the config file
# This keeps all shuttle configuration together in one place
CONFIG_DIR="$(dirname "$CONFIG_PATH")"
ENV_FILE_PATH="$CONFIG_DIR/shuttle_env.sh"

# Create a sourceable file
if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would create environment file: $ENV_FILE_PATH"
    echo "[DRY RUN] Contents would be:"
    echo "#!/bin/bash"
    echo "# Shuttle environment variables"
    echo "# Generated by 02_env_and_venv.sh on $(date)"
    echo ""
    echo "export SHUTTLE_CONFIG_PATH=\"$FINAL_CONFIG_PATH\""
    echo "export SHUTTLE_TEST_WORK_DIR=\"$FINAL_TEST_WORK_DIR\""
    echo "export SHUTTLE_TEST_CONFIG_PATH=\"$FINAL_TEST_CONFIG_PATH\""
    echo ""
    echo "# Display current settings"
    echo "echo \"Shuttle environment loaded:\""
    echo "echo \"  SHUTTLE_CONFIG_PATH=\$SHUTTLE_CONFIG_PATH\""
    echo "echo \"  SHUTTLE_TEST_WORK_DIR=\$SHUTTLE_TEST_WORK_DIR\""
    echo "echo \"  SHUTTLE_TEST_CONFIG_PATH=\$SHUTTLE_TEST_CONFIG_PATH\""
    echo ""
else
    # Create the environment file content
    ENV_FILE_CONTENT="#!/bin/bash
# Shuttle environment variables
# Generated by 02_env_and_venv.sh on $(date)

export SHUTTLE_CONFIG_PATH=\"$FINAL_CONFIG_PATH\"
export SHUTTLE_TEST_WORK_DIR=\"$FINAL_TEST_WORK_DIR\"
export SHUTTLE_TEST_CONFIG_PATH=\"$FINAL_TEST_CONFIG_PATH\"

# Display current settings
echo \"Shuttle environment loaded:\"
echo \"  SHUTTLE_CONFIG_PATH=\$SHUTTLE_CONFIG_PATH\"
echo \"  SHUTTLE_TEST_WORK_DIR=\$SHUTTLE_TEST_WORK_DIR\"
echo \"  SHUTTLE_TEST_CONFIG_PATH=\$SHUTTLE_TEST_CONFIG_PATH\""
    
    # Use the standard helper to write with sudo fallback
    if ! write_file_with_sudo_fallback "$ENV_FILE_PATH" "$ENV_FILE_CONTENT" "true"; then
        echo "ERROR: Failed to create environment file: $ENV_FILE_PATH"
        exit 1
    fi
fi

# Make the env file executable
make_executable_with_sudo_fallback "$ENV_FILE_PATH" "environment file" "true" || {
    echo "Warning: Could not make environment file executable"
}

# In development mode, also create a .env file in project root for IDEs/tools
if [[ "$DEV_MODE" == true ]]; then
    DOT_ENV_PATH="$PROJECT_ROOT/.env"
    DOT_ENV_CONTENT="# Python paths for IDE import resolution (append to existing PYTHONPATH)
PYTHONPATH=./src/shared_library:./src/shuttle_app:./src/shuttle_defender_test_app:./tests:$PYTHONPATH

# Shuttle environment variables
SHUTTLE_CONFIG_PATH=$CONFIG_PATH
SHUTTLE_TEST_WORK_DIR=$TEST_WORK_DIR
SHUTTLE_TEST_CONFIG_PATH=$TEST_CONFIG_PATH

# Development logging
SHUTTLE_LOG_LEVEL=DEBUG"
    
    # Define function to create the development .env file
    create_dev_env_file() {
        write_file_with_sudo_fallback "$DOT_ENV_PATH" "$DOT_ENV_CONTENT" "true"
    }
    
    # Use execute_function_or_dryrun to handle dry-run mode automatically
    execute_function_or_dryrun create_dev_env_file \
        "Development .env file created at: $DOT_ENV_PATH" \
        "Warning: Could not create .env file at: $DOT_ENV_PATH" \
        "Create development .env file for IDE integration"
fi

# Create virtual environment if requested
if [[ "$CREATE_VENV" == true ]]; then
    # Check if Python3 is available
    if ! command -v python3 &>/dev/null; then
        echo "ERROR: Python3 is not installed. Cannot create virtual environment."
        echo "Please run 00_sudo_install_python.sh first."
        exit 1
    fi
    
    # Check if venv already exists
    if [[ -d "$VENV_PATH" ]] && [[ -f "$VENV_PATH/bin/activate" ]]; then
        echo "Virtual environment already exists at: $VENV_PATH"
    else
        # Create virtual environment - may need sudo for directory creation
        echo "Creating virtual environment at: $VENV_PATH"
        
        # Ensure parent directory exists with sudo fallback
        VENV_PARENT_DIR=$(dirname "$VENV_PATH")
        if ! create_directory_with_auto_sudo "$VENV_PARENT_DIR" "virtual environment parent directory" "true" "$CURRENT_INSTALL_MODE"; then
            echo "❌ Failed to create parent directory for virtual environment: $VENV_PARENT_DIR"
            exit 1
        fi
        
        # Try to create venv directly first, then with sudo if needed
        local venv_created_with_sudo=false
        if ! execute_or_dryrun "python3 -m venv \"$VENV_PATH\"" "Virtual environment created successfully" "Failed to create virtual environment" "Create Python virtual environment"; then
            # If direct creation fails, try with sudo
            if ! execute_or_dryrun "sudo python3 -m venv \"$VENV_PATH\"" "Virtual environment created with sudo" "Failed to create virtual environment even with sudo" "Create Python virtual environment with elevated permissions"; then
                echo "❌ Failed to create virtual environment: $VENV_PATH"
                exit 1
            fi
            venv_created_with_sudo=true
        fi
        
        # Set exec permissions on activate
        make_executable_with_sudo_fallback "$VENV_PATH/bin/activate" "venv activate script" "true" || {
            echo "Warning: Could not make venv activate script executable"
        }
        
        echo "✅ Virtual environment created successfully"
        
        # Upgrade pip in the new venv (use sudo if venv was created with sudo)
        if [[ "$venv_created_with_sudo" == "true" ]]; then
            execute_or_dryrun "sudo \"$VENV_PATH/bin/python\" -m pip install --upgrade pip" "Upgraded pip in virtual environment with sudo" "Failed to upgrade pip even with sudo" "Upgrade pip to latest version in virtual environment (with elevated permissions)"
        else
            execute_or_dryrun "\"$VENV_PATH/bin/python\" -m pip install --upgrade pip" "Upgraded pip in virtual environment" "Failed to upgrade pip" "Upgrade pip to latest version in virtual environment"
        fi
        
        # Create activation helper script
        ACTIVATE_SCRIPT="$CONFIG_DIR/shuttle_activate_virtual_environment.sh"
        
        # Create the activation script content
        ACTIVATE_SCRIPT_CONTENT="#!/bin/bash
# Shuttle virtual environment activation script
# Generated by 02_env_and_venv.sh on $(date)

# Activate the virtual environment
source \"$FINAL_VENV_PATH/bin/activate\"

# Show status
echo \"Shuttle virtual environment activated:\"
echo \"  Virtual environment: $FINAL_VENV_PATH\"
echo \"  Python: \$(which python)\"
echo \"  Python version: \$(python --version)\""
        
        # Use the standard helper to write with sudo fallback
        if write_file_with_sudo_fallback "$ACTIVATE_SCRIPT" "$ACTIVATE_SCRIPT_CONTENT" "true"; then
            # Make executable
            make_executable_with_sudo_fallback "$ACTIVATE_SCRIPT" "activation script" "true" || {
                echo "Warning: Could not make activation script executable"
            }
            echo "✅ Virtual environment activation script created: $ACTIVATE_SCRIPT"
        else
            echo "Warning: Could not create activation script: $ACTIVATE_SCRIPT"
        fi
    fi
else
    echo "Skipping virtual environment creation (--do-not-create-venv flag set)"
fi

echo ""
if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Environment variables would be set:"
    echo "  SHUTTLE_CONFIG_PATH=$CONFIG_PATH"
    echo "  SHUTTLE_TEST_WORK_DIR=$TEST_WORK_DIR"
    echo "  SHUTTLE_TEST_CONFIG_PATH=$TEST_CONFIG_PATH"
    echo ""
    echo "[DRY RUN] Environment file would be created at: $ENV_FILE_PATH"
else
    echo "Environment variables set:"
    echo "  SHUTTLE_CONFIG_PATH=$SHUTTLE_CONFIG_PATH"
    echo "  SHUTTLE_TEST_WORK_DIR=$SHUTTLE_TEST_WORK_DIR"
    echo "  SHUTTLE_TEST_CONFIG_PATH=$SHUTTLE_TEST_CONFIG_PATH"
    echo ""
    echo "Environment file created at: $ENV_FILE_PATH"
fi

if [[ "$CREATE_VENV" == true ]] && [[ -f "$VENV_PATH/bin/activate" ]]; then
    echo ""
    if [[ "$STAGING_MODE" == true ]]; then
        echo "To activate the virtual environment (after deploying to production):"
        echo "  source $(dirname "$FINAL_CONFIG_PATH")/shuttle_activate_virtual_environment.sh"
        echo "  (or directly: source $FINAL_VENV_PATH/bin/activate)"
    else
        echo "To activate the virtual environment:"
        echo "  source $CONFIG_DIR/shuttle_activate_virtual_environment.sh"
        echo "  (or directly: source $FINAL_VENV_PATH/bin/activate)"
    fi
fi

echo ""
if [[ "$STAGING_MODE" == true ]]; then
    echo "Staging mode: Files created in $STAGING_DIR"
    echo "After deploying to production, source the environment with:"
    echo "  source $(dirname "$FINAL_CONFIG_PATH")/shuttle_env.sh"
else
    echo "These variables are set for the current session."
    echo "For future sessions, source the environment with:"
    echo "  source $ENV_FILE_PATH"
fi