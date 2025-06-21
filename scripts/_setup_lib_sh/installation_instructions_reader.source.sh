#!/bin/bash
# Installation Instructions Reader
# Shell wrapper for Python installation instructions reader

# Function to read installation instructions from YAML file
read_installation_instructions() {
    local instructions_file="$1"
    
    if [[ -z "$instructions_file" ]]; then
        echo "ERROR: Instructions file path required" >&2
        return 1
    fi
    
    if [[ ! -f "$instructions_file" ]]; then
        echo "ERROR: Instructions file not found: $instructions_file" >&2
        return 1
    fi
    
    # Call Python reader to extract values
    local reader_script="$SCRIPT_DIR/_setup_lib_py/installation_instructions_reader.py"
    if [[ ! -f "$reader_script" ]]; then
        echo "ERROR: Python reader script not found: $reader_script" >&2
        return 1
    fi
    
    # Use Python to read and export all values
    local temp_vars
    temp_vars=$(python3 "$reader_script" "$instructions_file" --export-shell-vars)
    local python_exit_code=$?
    
    if [[ $python_exit_code -ne 0 ]]; then
        echo "ERROR: Failed to read instructions file" >&2
        return 1
    fi
    
    # Source the exported variables
    eval "$temp_vars"
    
    return 0
}

# Function to validate required instruction variables are set
validate_instruction_variables() {
    local required_vars=(
        "SAVED_VENV_CHOICE"
        "SAVED_INSTALL_MODE"
        "SAVED_CONFIG_PATH"
        "SAVED_TEST_WORK_DIR"
        "SAVED_INSTALL_BASIC_DEPS"
        "SAVED_INSTALL_PYTHON"
        "SAVED_INSTALL_CLAMAV"
        "SAVED_CHECK_DEFENDER"
        "SAVED_CREATE_SOURCE_DIR"
        "SAVED_CREATE_DEST_DIR"
        "SAVED_CREATE_QUARANTINE_DIR"
        "SAVED_CREATE_LOG_DIR"
        "SAVED_CREATE_HAZARD_DIR"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo "ERROR: Missing required instruction variables:" >&2
        printf "  %s\n" "${missing_vars[@]}" >&2
        return 1
    fi
    
    return 0
}