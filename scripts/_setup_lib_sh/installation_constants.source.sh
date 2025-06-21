#!/bin/bash
# installation_constants.source.sh
# Shell wrapper for Python installation constants
#
# Provides shell access to constants defined in installation_constants.py
# Usage: 
#   source_setup_lib "installation_constants"
#   load_installation_constants

# Helper function to run Python with correct path
run_python_with_setup_path() {
    local script_dir="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
    local scripts_dir="$(dirname "$script_dir")"
    local setup_lib_py_dir="$scripts_dir/_setup_lib_py"
    
    PYTHONPATH="$setup_lib_py_dir:${PYTHONPATH:-}" python3 "$@"
}

# Function to get all constants from Python and export them as shell variables
get_installation_constants() {
    run_python_with_setup_path -c "
from installation_constants import InstallationConstants as IC

# Virtual environment constants
print(f'VENV_CHOICE_EXISTING={IC.Venv.CHOICE_EXISTING}')
print(f'VENV_CHOICE_SCRIPT_CREATES={IC.Venv.CHOICE_SCRIPT_CREATES}')
print(f'VENV_CHOICE_GLOBAL={IC.Venv.CHOICE_GLOBAL}')
print(f'VENV_TYPE_EXISTING={IC.Venv.TYPE_EXISTING}')
print(f'VENV_TYPE_SCRIPT={IC.Venv.TYPE_SCRIPT}')
print(f'VENV_TYPE_GLOBAL={IC.Venv.TYPE_GLOBAL}')

# Installation mode constants
print(f'INSTALL_MODE_DEV={IC.InstallMode.DEV}')
print(f'INSTALL_MODE_USER={IC.InstallMode.USER}')
print(f'INSTALL_MODE_SERVICE={IC.InstallMode.SERVICE}')

# Log level constants
print(f'LOG_LEVEL_DEBUG={IC.LogLevel.DEBUG}')
print(f'LOG_LEVEL_INFO={IC.LogLevel.INFO}')
print(f'LOG_LEVEL_WARNING={IC.LogLevel.WARNING}')
print(f'LOG_LEVEL_ERROR={IC.LogLevel.ERROR}')
print(f'LOG_LEVEL_CRITICAL={IC.LogLevel.CRITICAL}')

# System dependency constants
print(f'SYSDEP_INSTALL_BASIC_DEPS={IC.SystemDeps.INSTALL_BASIC_DEPS}')
print(f'SYSDEP_INSTALL_PYTHON={IC.SystemDeps.INSTALL_PYTHON}')
print(f'SYSDEP_INSTALL_CLAMAV={IC.SystemDeps.INSTALL_CLAMAV}')
print(f'SYSDEP_CHECK_DEFENDER={IC.SystemDeps.CHECK_DEFENDER}')
print(f'SYSDEP_USE_CLAMAV={IC.SystemDeps.USE_CLAMAV}')
print(f'SYSDEP_USE_DEFENDER={IC.SystemDeps.USE_DEFENDER}')

# File processing constants
print(f'FILEPROC_DELETE_SOURCE={IC.FileProcessing.DELETE_SOURCE}')
"
}

# Load constants into shell environment
load_installation_constants() {
    local constants_output
    constants_output=$(get_installation_constants)
    if [[ $? -eq 0 ]]; then
        eval "$constants_output"
        return 0
    else
        echo "ERROR: Failed to load installation constants from Python module" >&2
        return 1
    fi
}

# Helper functions that call Python for conversions

# Convert venv type to choice
get_venv_choice_from_type() {
    local venv_type="$1"
    run_python_with_setup_path -c "
from installation_constants import get_venv_choice_from_type
print(get_venv_choice_from_type('$venv_type'))
"
}

# Convert venv choice to type
get_venv_type_from_choice() {
    local choice="$1"
    run_python_with_setup_path -c "
from installation_constants import get_venv_type_from_choice
print(get_venv_type_from_choice('$choice'))
"
}

# Get environment flag for installation mode
get_env_flag_for_mode() {
    local install_mode="$1"
    run_python_with_setup_path -c "
from installation_constants import get_env_flag_for_mode
print(get_env_flag_for_mode('$install_mode'))
"
}

# Convert log level number to name
get_log_level_from_number() {
    local number="$1"
    run_python_with_setup_path -c "
from installation_constants import get_log_level_from_number
print(get_log_level_from_number('$number'))
"
}

# Convert log level name to number
get_log_level_number() {
    local level="$1"
    run_python_with_setup_path -c "
from installation_constants import get_log_level_number
print(get_log_level_number('$level'))
"
}

# Validation functions

# Check if venv choice is valid
is_valid_venv_choice() {
    local choice="$1"
    run_python_with_setup_path -c "
from installation_constants import is_valid_venv_choice
import sys
sys.exit(0 if is_valid_venv_choice('$choice') else 1)
"
}

# Check if installation mode is valid
is_valid_install_mode() {
    local mode="$1"
    run_python_with_setup_path -c "
from installation_constants import is_valid_install_mode
import sys
sys.exit(0 if is_valid_install_mode('$mode') else 1)
"
}

# Check if log level is valid
is_valid_log_level() {
    local level="$1"
    run_python_with_setup_path -c "
from installation_constants import is_valid_log_level
import sys
sys.exit(0 if is_valid_log_level('$level') else 1)
"
}

# Utility function to show all loaded constants (for debugging)
show_installation_constants() {
    echo "Installation Constants Loaded:"
    echo ""
    echo "Virtual Environment:"
    echo "  VENV_CHOICE_EXISTING=$VENV_CHOICE_EXISTING"
    echo "  VENV_CHOICE_SCRIPT_CREATES=$VENV_CHOICE_SCRIPT_CREATES"
    echo "  VENV_CHOICE_GLOBAL=$VENV_CHOICE_GLOBAL"
    echo "  VENV_TYPE_EXISTING=$VENV_TYPE_EXISTING"
    echo "  VENV_TYPE_SCRIPT=$VENV_TYPE_SCRIPT"
    echo "  VENV_TYPE_GLOBAL=$VENV_TYPE_GLOBAL"
    echo ""
    echo "Installation Modes:"
    echo "  INSTALL_MODE_DEV=$INSTALL_MODE_DEV"
    echo "  INSTALL_MODE_USER=$INSTALL_MODE_USER"
    echo "  INSTALL_MODE_SERVICE=$INSTALL_MODE_SERVICE"
    echo ""
    echo "Log Levels:"
    echo "  LOG_LEVEL_DEBUG=$LOG_LEVEL_DEBUG"
    echo "  LOG_LEVEL_INFO=$LOG_LEVEL_INFO"
    echo "  LOG_LEVEL_WARNING=$LOG_LEVEL_WARNING"
    echo "  LOG_LEVEL_ERROR=$LOG_LEVEL_ERROR"
    echo "  LOG_LEVEL_CRITICAL=$LOG_LEVEL_CRITICAL"
}