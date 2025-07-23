#!/bin/bash
# installation_defaults.source.sh
# 
# Bash functions to read installation defaults from installation_defaults.conf
# This provides easy access to user-configurable defaults while keeping 
# enums and constants in Python code.

# Helper function to get Python path setup
run_python_with_defaults() {
    local python_code="$1"
    
    # Add setup path for imports
    PYTHONPATH="${SCRIPT_DIR}/_setup_lib_py:${PYTHONPATH:-}" python3 -c "$python_code"
}

# Get default installation mode
get_default_install_mode() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print(defaults.get_default_install_mode())
"
}

# Get default path for installation mode and path type
get_default_path() {
    local install_mode="$1"
    local path_type="$2"
    local project_root="${3:-}"
    
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
path = defaults.get_default_path('$install_mode', '$path_type', '$project_root')
print(path)
"
}

# Get default log level for installation mode
get_default_log_level() {
    local install_mode="$1"
    
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print(defaults.get_default_log_level('$install_mode'))
"
}

# Get default number of scan threads
get_default_threads() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print(defaults.get_default_threads())
"
}

# Get default minimum free space
get_default_min_free_space() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print(defaults.get_default_min_free_space())
"
}

# Get default scanner settings
get_default_use_clamav() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print('y' if defaults.get_default_use_clamav() else 'n')
"
}

get_default_use_defender() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print('Y' if defaults.get_default_use_defender() else 'n')
"
}

# Get default email settings
get_default_smtp_port() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print(defaults.get_default_smtp_port())
"
}

get_default_use_tls() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print('Y' if defaults.get_default_use_tls() else 'n')
"
}

# Get default file processing settings
get_default_delete_source() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print('Y' if defaults.get_default_delete_source() else 'n')
"
}

# Get default system dependency settings
get_default_install_basic_deps() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print('true' if defaults.get_default_install_basic_deps() else 'false')
"
}

get_default_install_python() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print('true' if defaults.get_default_install_python() else 'false')
"
}

get_default_install_clamav() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print('true' if defaults.get_default_install_clamav() else 'false')
"
}

get_default_check_defender() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print('true' if defaults.get_default_check_defender() else 'false')
"
}

# Get default directory creation settings
get_default_create_directory() {
    local dir_type="$1"
    
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print('true' if defaults.get_default_create_directory('$dir_type') else 'false')
"
}

# Get default venv choice when no venv is active
get_default_venv_choice_no_venv() {
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
print(defaults.get_default_venv_choice_no_venv())
"
}

# Get all defaults for a specific installation mode
get_all_defaults_for_mode() {
    local install_mode="$1"
    local project_root="${2:-}"
    
    run_python_with_defaults "
from installation_defaults import get_installation_defaults
defaults = get_installation_defaults()
mode_defaults = defaults.get_all_defaults_for_mode('$install_mode', '$project_root')
for key, value in sorted(mode_defaults.items()):
    print(f'{key.upper()}=\"{value}\"')
"
}

# Test function to validate defaults are loading correctly
test_installation_defaults() {
    echo "Testing installation defaults..."
    echo ""
    
    echo "Default install mode: $(get_default_install_mode)"
    echo ""
    
    for mode in dev user service; do
        echo "$mode mode defaults:"
        echo "  Config: $(get_default_path "$mode" "config" "/test/project")"
        echo "  Source: $(get_default_path "$mode" "source" "/test/project")" 
        echo "  Log level: $(get_default_log_level "$mode")"
        echo ""
    done
    
    echo "Processing defaults:"
    echo "  Threads: $(get_default_threads)"
    echo "  Min free space: $(get_default_min_free_space)"
    echo ""
    
    echo "Scanner defaults:"
    echo "  Use ClamAV: $(get_default_use_clamav)"
    echo "  Use Defender: $(get_default_use_defender)"
}