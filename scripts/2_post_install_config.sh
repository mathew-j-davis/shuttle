#!/bin/bash
# 2_post_install_config.sh - Production environment configuration orchestrator
# Reads YAML configuration and calls existing scripts with appropriate parameters
#
# This script follows the pattern of 1_install.sh but focuses on production
# environment setup including users, groups, permissions, Samba, and firewall.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PRODUCTION_DIR="$SCRIPT_DIR/2_post_install_config_steps"
SETUP_LIB_DIR="$SCRIPT_DIR/__setup_lib_py"
LIB_DIR="$PRODUCTION_DIR/lib"

# Add setup lib to Python path
export PYTHONPATH="${SETUP_LIB_DIR}:${PYTHONPATH}"

# Import Python constants if possible
if python3 -c "import post_install_config_constants" 2>/dev/null; then
    COMMAND_HISTORY_PREFIX=$(python3 -c "from post_install_config_constants import COMMAND_HISTORY_PREFIX; print(COMMAND_HISTORY_PREFIX)")
else
    # Fallback if module not available
    COMMAND_HISTORY_PREFIX="shuttle_post_install_configuration_command_history"
fi

# Set command history file for this configuration session
export COMMAND_HISTORY_FILE="/tmp/${COMMAND_HISTORY_PREFIX}_$(date +%Y%m%d_%H%M%S).log"

# Export DRY_RUN for use by all scripts and modules
export DRY_RUN

# Source shared setup libraries using clean import pattern
SETUP_LIB_SH_DIR="$SCRIPT_DIR/__setup_lib_sh"
if [[ -f "$SETUP_LIB_SH_DIR/_setup_lib_loader.source.sh" ]]; then
    source "$SETUP_LIB_SH_DIR/_setup_lib_loader.source.sh"
    load_common_libs || {
        echo "ERROR: Failed to load required setup libraries" >&2
        exit 1
    }
else
    echo "ERROR: Setup library loader not found at $SETUP_LIB_SH_DIR/_setup_lib_loader.source.sh" >&2
    exit 1
fi

# Output functions for main script
print_info() {
    echo -e "${GREEN}$*${NC}" >&2
}

print_error() {
    echo -e "${RED}$*${NC}" >&2
}

print_warn() {
    echo -e "${YELLOW}$*${NC}" >&2
}

print_header() {
    echo -e "${BLUE}$*${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✅ $*${NC}" >&2
}

print_fail() {
    echo -e "${RED}❌ $*${NC}" >&2
}

# Import config filename constants
if python3 -c "import post_install_config_constants" 2>/dev/null; then
    CONFIG_DEFAULT_FILENAME=$(python3 -c "from post_install_config_constants import CONFIG_DEFAULT_FILENAME; print(CONFIG_DEFAULT_FILENAME)")
    CONFIG_GLOB_PATTERN=$(python3 -c "from post_install_config_constants import get_config_glob_pattern; print(get_config_glob_pattern())")
else
    # Fallback if module not available
    CONFIG_DEFAULT_FILENAME="shuttle_post_install_configuration.yaml"
    CONFIG_GLOB_PATTERN="shuttle_post_install_config_*.yaml"
fi

# Default configuration file location
DEFAULT_CONFIG="$PROJECT_ROOT/config/$CONFIG_DEFAULT_FILENAME"
CONFIG_FILE=""
INTERACTIVE_MODE=true
DRY_RUN=false
RUN_WIZARD=false

echo "=========================================" >&2
echo "  Shuttle Post-Install Environment Configuration  " >&2
echo "=========================================" >&2
echo "" >&2
echo "This script configures the production environment for Shuttle:" >&2
echo "• System tools installation" >&2
echo "• User and group management" >&2
echo "• File permissions and ownership" >&2
echo "• Samba configuration" >&2
echo "• Firewall configuration" >&2
echo "" >&2

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [options]

Options:
  --instructions <file> Path to YAML instructions file (default: wizard mode)
  --non-interactive     Run in non-interactive mode
  --dry-run             Show what would be done without making changes
  --wizard              Run configuration wizard to create YAML file first
  --help               Show this help message

Examples:
  $0                                    # Interactive mode with default config
  $0 --wizard                          # Run wizard to create config, then apply
  $0 --instructions /path/to/post_install_instructions.yaml     # Interactive mode with custom instructions
  $0 --instructions post_install_instructions.yaml --non-interactive  # Automated mode
  $0 --dry-run                          # Show what would be done
  $0 --wizard --dry-run                 # Create config with wizard, then dry run

Configuration File:
  The YAML configuration file defines users, groups, and permissions.
  See yaml_user_setup_design.md for complete documentation and examples.
EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --instructions)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --non-interactive)
                INTERACTIVE_MODE=false
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                export DRY_RUN  # Export for child processes
                shift
                ;;
            --wizard)
                RUN_WIZARD=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                print_fail "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # If no --instructions specified and no --wizard, default to wizard
    if [[ -z "$CONFIG_FILE" && "$RUN_WIZARD" == "false" ]]; then
        RUN_WIZARD=true
    fi
}

# Validate configuration file
validate_config() {
    echo "=== Configuration Validation ===" >&2
    echo "" >&2
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        print_fail "Configuration file not found: $CONFIG_FILE"
        echo "" >&2
        echo "Create a YAML configuration file defining users and groups." >&2
        echo "See yaml_user_setup_design.md for examples and documentation." >&2
        exit 1
    fi
    
    # Basic YAML validation using Python
    echo "Validating YAML syntax..."
    if ! python3 -c "import yaml; list(yaml.safe_load_all(open('$CONFIG_FILE')))" 2>/dev/null; then
        print_fail "Invalid YAML configuration file"
        echo "" >&2
        echo "Please check your YAML syntax and try again." >&2
        exit 1
    fi
    
    print_success "Configuration file validated: $CONFIG_FILE"
    echo ""
}

# Check prerequisites
check_prerequisites() {
    echo "=== Prerequisites Check ===" >&2
    echo "" >&2
    
    # Check if Python 3 is available
    if ! execute "command -v python3 >/dev/null 2>&1" \
                "Python 3 found" \
                "Python 3 not found" \
                "Check if Python 3 interpreter is installed and available in PATH"; then
        print_fail "Python 3 is required but not found"
        echo "Please install Python 3 and try again." >&2
        exit 1
    fi
    
    # Check if PyYAML is available
    if ! execute "python3 -c \"import yaml\" 2>/dev/null" \
                "PyYAML library found" \
                "PyYAML library not found" \
                "Check if PyYAML Python library is installed for YAML configuration parsing"; then
        print_fail "PyYAML is required but not found"
        echo "Please install PyYAML: pip install PyYAML" >&2
        exit 1
    fi
    
    # Check if production scripts directory exists
    if [[ ! -d "$PRODUCTION_DIR" ]]; then
        print_fail "Production scripts directory not found: $PRODUCTION_DIR"
        exit 1
    fi
    
    # Check if required scripts exist
    local required_scripts=(
        "11_install_tools.sh"
        "12_users_and_groups.sh"
        "13_configure_samba.sh"
        "14_configure_firewall.sh"
    )
    
    for script in "${required_scripts[@]}"; do
        if [[ ! -f "$PRODUCTION_DIR/$script" ]]; then
            print_fail "Required script not found: $PRODUCTION_DIR/$script"
            exit 1
        fi
        if [[ ! -x "$PRODUCTION_DIR/$script" ]]; then
            print_warn "⚠️  Making script executable: $script"
            execute_or_dryrun "chmod +x \"$PRODUCTION_DIR/$script\"" \
                             "Made script executable: $script" \
                             "Failed to make script executable: $script" \
                             "Set execute permissions on required script for system configuration"
        fi
    done
    
    # Check sudo access for system modifications
    echo "Checking system privileges..." >&2
    if check_active_user_is_root; then
        print_success "Running as root - full system access available"
    elif check_active_user_has_sudo_access; then
        print_success "Sudo access available - system modifications possible"
    else
        print_fail "No root or sudo access - system modifications will fail"
        echo "Please run as root or ensure your user has sudo privileges." >&2
        exit 1
    fi
    
    print_success "All prerequisites satisfied"
    echo ""
}

# Interactive mode configuration
interactive_setup() {
    if [[ "$INTERACTIVE_MODE" != "true" ]]; then
        return 0
    fi
    
    echo "=== Configuration Overview ==="
    echo ""
    echo "Configuration file: $CONFIG_FILE"
    echo ""
    
    # Show configuration summary using Python module
    echo "Analyzing configuration..."
    python3 -m config_analyzer "$CONFIG_FILE"
    
    if [[ $? -ne 0 ]]; then
        print_fail "Failed to analyze configuration"
        exit 1
    fi
    
    echo ""
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warn "🔍 DRY RUN MODE: No changes will be made"
        echo ""
    fi
    
    read -p "Proceed with configuration? [Y/n]: " CONFIRM
    case $CONFIRM in
        [Nn])
            echo "Configuration cancelled." >&2
            exit 0
            ;;
        *)
            print_info "Proceeding with configuration..."
            ;;
    esac
    echo ""
}

# Check if component is enabled in config
is_component_enabled() {
    local component_name="$1"
    python3 -c "
import yaml
import sys
try:
    with open('$CONFIG_FILE', 'r') as f:
        docs = list(yaml.safe_load_all(f))
    
    for doc in docs:
        if doc.get('components', {}).get('$component_name', True):
            sys.exit(0)
    sys.exit(1)
except:
    sys.exit(0)  # Default to enabled if not specified
"
}

# Phase 1: Install system tools
phase_install_tools() {
    echo ""
    print_header "📦 Phase 1: Installing system tools"
    echo ""
    
    local cmd="$PRODUCTION_DIR/11_install_tools.sh"
    
    # Check if ACL and Samba installation is enabled
    local install_flags=""
    if ! is_component_enabled "install_acl"; then
        install_flags="$install_flags --no-acl"
    fi
    if ! is_component_enabled "install_samba"; then
        install_flags="$install_flags --no-samba"
    fi
    
    if ! execute_or_execute_dryrun "$cmd $install_flags" \
                                  "System tools installation complete" \
                                  "Failed to install system tools" \
                                  "Install required system packages (ACL tools, Samba) for Shuttle functionality"; then
        exit 1
    fi
}

# Phase 2: Configure users and groups
phase_configure_users() {
    if ! is_component_enabled "configure_users_groups"; then
        echo ""
        print_warn "⏭️  Phase 2: Skipping users and groups configuration"
        return 0
    fi
    
    echo ""
    print_header "👥 Phase 2: Configuring users and groups"
    echo ""
    
    # Use Python module to process users and groups
    local dry_run_flag=""
    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_flag="--dry-run"
    fi
    
    # Pass shuttle config path if available for path resolution
    local config_args=""
    if [[ -n "$SHUTTLE_CONFIG_PATH" ]]; then
        config_args="--shuttle-config-path=$SHUTTLE_CONFIG_PATH"
    fi
    
    python3 -m user_group_manager "$CONFIG_FILE" "$PRODUCTION_DIR" $dry_run_flag $config_args

    if [[ $? -ne 0 ]]; then
        print_fail "Failed to configure users and groups"
        exit 1
    fi
    print_success "Users and groups configuration complete"
}

# Phase 3: Set permissions
phase_set_permissions() {
    echo ""
    print_header "🔐 Phase 3: Setting file permissions"
    echo ""
    
    # Use Python module to process permissions
    local dry_run_flag=""
    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_flag="--dry-run"
    fi
    
    python3 -m permission_manager "$CONFIG_FILE" "$PRODUCTION_DIR" $dry_run_flag

    if [[ $? -ne 0 ]]; then
        print_warn "⚠️  Some permission settings may have failed"
    else
        print_success "File permissions configuration complete"
    fi
}

# Phase 4: Configure Samba
phase_configure_samba() {
    if ! is_component_enabled "configure_samba"; then
        echo ""
        print_warn "⏭️  Phase 4: Skipping Samba configuration"
        return 0
    fi
    
    echo ""
    print_header "🌐 Phase 4: Configuring Samba"
    echo ""
    
    # Use Python module to configure Samba
    local dry_run_flag=""
    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_flag="--dry-run"
    fi
    
    python3 -m samba_manager "$CONFIG_FILE" "$PRODUCTION_DIR" $dry_run_flag

    if [[ $? -ne 0 ]]; then
        print_warn "⚠️  Some Samba configuration may have failed"
    else
        print_success "Samba configuration complete"
    fi
}

# Phase 5: Configure firewall
phase_configure_firewall() {
    if ! is_component_enabled "configure_firewall"; then
        echo ""
        print_warn "⏭️  Phase 5: Skipping firewall configuration"
        return 0
    fi
    
    echo ""
    print_header "🔥 Phase 5: Configuring firewall"
    echo ""
    
    execute_or_execute_dryrun "$PRODUCTION_DIR/14_configure_firewall.sh show-status" \
                              "Firewall configuration complete" \
                              "Firewall configuration check completed with warnings" \
                              "Check and configure firewall settings for Shuttle security requirements"
}

# Run configuration wizard
run_configuration_wizard() {
    echo ""
    print_header "🧙 Running Configuration Wizard"
    echo ""
    
    # Change to config directory
    cd "$PROJECT_ROOT/config"
    
    # Build wizard arguments
    local wizard_args=""
    
    # Pass shuttle config path if available
    if [[ -n "$SHUTTLE_CONFIG_PATH" ]]; then
        wizard_args="$wizard_args --shuttle-config-path $SHUTTLE_CONFIG_PATH"
    fi
    
    # Pass test directories if available
    if [[ -n "$SHUTTLE_TEST_WORK_DIR" ]]; then
        wizard_args="$wizard_args --test-work-dir $SHUTTLE_TEST_WORK_DIR"
    fi
    
    if [[ -n "$SHUTTLE_TEST_CONFIG_PATH" ]]; then
        wizard_args="$wizard_args --test-config-path $SHUTTLE_TEST_CONFIG_PATH"
    fi
    
    # Run the wizard with arguments
    python3 -m post_install_config_wizard $wizard_args
    local wizard_exit_code=$?
    
    if [[ $wizard_exit_code -eq 2 ]]; then
        print_success "Configuration saved successfully"
        echo "Exiting as requested - configuration saved but not applied."
        exit 0
    elif [[ $wizard_exit_code -ne 0 ]]; then
        print_fail "Configuration wizard failed"
        exit 1
    fi
    
    # Check if wizard saved a filename for us to use
    if [[ -f /tmp/wizard_config_filename ]]; then
        local wizard_filename=$(cat /tmp/wizard_config_filename)
        rm -f /tmp/wizard_config_filename
        CONFIG_FILE="$PROJECT_ROOT/config/$wizard_filename"
        echo ""
        print_success "Using wizard-generated configuration: $CONFIG_FILE"
        echo ""
    else
        # Try to find the most recently generated config file
        local latest_config=$(ls -t $CONFIG_GLOB_PATTERN 2>/dev/null | head -1)
        
        if [[ -n "$latest_config" ]]; then
            CONFIG_FILE="$PROJECT_ROOT/config/$latest_config"
            echo ""
            print_success "Using generated configuration: $CONFIG_FILE"
            echo ""
        else
            print_fail "Could not find generated configuration file"
            exit 1
        fi
    fi
    
    # Return to script directory
    cd "$SCRIPT_DIR"
}

# Show completion summary
show_completion_summary() {
    echo ""
    print_success "🎉 Production environment configuration complete!"
    echo ""
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warn "This was a dry run. No changes were made."
        echo "Run without --dry-run to apply the configuration."
        echo ""
    else
        echo "Configuration applied successfully:"
        echo "✅ System tools installed"
        echo "✅ Users and groups configured"
        echo "✅ File permissions set"
        echo "✅ Samba configured"
        echo "✅ Firewall checked"
        echo ""
        
        echo "Next steps:"
        echo "1. Verify user access and permissions"
        echo "2. Test Samba connectivity if configured"
        echo "3. Configure firewall rules as needed"
        echo "4. Test shuttle application functionality"
        echo ""
    fi
    
    echo "Configuration file used: $CONFIG_FILE"
    echo "For detailed configuration options, see: yaml_user_setup_design.md"
}

# Main execution function
main() {
    echo "Starting production environment configuration..." >&2
    echo "" >&2
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Run wizard if requested
    if [[ "$RUN_WIZARD" == "true" ]]; then
        run_configuration_wizard
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Validate configuration
    validate_config
    
    # Interactive setup if needed
    interactive_setup
    
    # Execute phases
    phase_install_tools
    phase_configure_users
    phase_set_permissions
    phase_configure_samba
    phase_configure_firewall
    
    # Show completion summary
    show_completion_summary
}

# Run main function with all arguments
main "$@"