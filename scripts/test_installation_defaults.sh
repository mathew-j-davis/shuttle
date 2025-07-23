#!/bin/bash
# Test script for installation defaults functionality

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source the defaults
source "$SCRIPT_DIR/_sources.sh"

echo "Testing Installation Defaults Configuration"
echo "=========================================="
echo ""

# Test Python module directly
echo "Python module test:"
python3 "$SCRIPT_DIR/_setup_lib_py/installation_defaults.py"
echo ""

# Test bash functions
echo "Bash functions test:"
echo "Default install mode: $(get_default_install_mode)"
echo ""

for mode in dev user service; do
    echo "$mode mode defaults:"
    echo "  Config: $(get_default_path "$mode" "config" "$PROJECT_ROOT")"
    echo "  Source: $(get_default_path "$mode" "source" "$PROJECT_ROOT")" 
    echo "  Destination: $(get_default_path "$mode" "destination" "$PROJECT_ROOT")" 
    echo "  Quarantine: $(get_default_path "$mode" "quarantine" "$PROJECT_ROOT")" 
    echo "  Logs: $(get_default_path "$mode" "logs" "$PROJECT_ROOT")" 
    echo "  Hazard: $(get_default_path "$mode" "hazard" "$PROJECT_ROOT")" 
    echo "  VEnv: $(get_default_path "$mode" "venv" "$PROJECT_ROOT")" 
    echo "  Test config: $(get_default_path "$mode" "test_config" "$PROJECT_ROOT")" 
    echo "  Test work: $(get_default_path "$mode" "test_work" "$PROJECT_ROOT")" 
    echo "  Log level: $(get_default_log_level "$mode")"
    echo ""
done

echo "Processing defaults:"
echo "  Threads: $(get_default_threads)"
echo "  Min free space: $(get_default_min_free_space) MB"
echo ""

echo "Scanner defaults:"
echo "  Use ClamAV: $(get_default_use_clamav)"
echo "  Use Defender: $(get_default_use_defender)"
echo ""

echo "Email defaults:"
echo "  SMTP port: $(get_default_smtp_port)"
echo "  Use TLS: $(get_default_use_tls)"
echo ""

echo "File processing defaults:"
echo "  Delete source: $(get_default_delete_source)"
echo ""

echo "System dependency defaults:"
echo "  Install basic deps: $(get_default_install_basic_deps)"
echo "  Install Python: $(get_default_install_python)"
echo "  Install ClamAV: $(get_default_install_clamav)"
echo "  Check Defender: $(get_default_check_defender)"
echo ""

echo "Directory creation defaults:"
for dir_type in source dest quarantine log hazard; do
    echo "  Create $dir_type dir: $(get_default_create_directory "$dir_type")"
done
echo ""

echo "VEnv defaults:"
echo "  Default choice when no venv: $(get_default_venv_choice_no_venv)"
echo ""

echo "Test completed!"