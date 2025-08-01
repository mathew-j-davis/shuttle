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
SETUP_LIB_DIR="$SCRIPT_DIR/_setup_lib_py"
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

# Export DRY_RUN and VERBOSE for use by all scripts and modules
export DRY_RUN
export VERBOSE

# Source required libraries - simple and direct
source "$SCRIPT_DIR/_sources.sh"

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
    INSTRUCTIONS_DEFAULT_FILENAME=$(python3 -c "from post_install_config_constants import INSTRUCTIONS_DEFAULT_FILENAME; print(INSTRUCTIONS_DEFAULT_FILENAME)")
    CONFIG_GLOB_PATTERN=$(python3 -c "from post_install_config_constants import get_config_glob_pattern; print(get_config_glob_pattern())")
else
    # Fallback if module not available
    INSTRUCTIONS_DEFAULT_FILENAME="post_install_config_steps.yaml"
    CONFIG_GLOB_PATTERN="post_install_config_steps*.yaml"
fi

# Default instructions file location
DEFAULT_INSTRUCTIONS_PATH="$PROJECT_ROOT/config/$INSTRUCTIONS_DEFAULT_FILENAME"
INSTRUCTIONS_FILE=""
INTERACTIVE_MODE=true
DRY_RUN=false
RUN_WIZARD=false
VERBOSE=false

# Command-line override variables
CLI_ENVIRONMENT=""
CLI_MODE=""
CLI_CREATE_HOME=""
CLI_BACKUP_USERS=""
CLI_VALIDATE=""
CLI_INSTALL_ACL=""
CLI_INSTALL_SAMBA=""
CLI_CONFIGURE_USERS_GROUPS=""
CLI_CONFIGURE_SAMBA=""
CLI_CONFIGURE_FIREWALL=""

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
  --instructions <file>   Path to YAML instructions file (default: wizard mode)
  --interactive           Force interactive mode (override config file setting)
  --non-interactive       Force non-interactive mode (override config file setting)
  --dry-run               Show what would be done without making changes
  --verbose               Show detailed command execution information
  --wizard                Run configuration wizard to create YAML file first
  --help                  Show this help message

Base Configuration Overrides:
  --environment <env>         Set environment (production|development|testing)
  --mode <mode>              Set configuration mode (simple|standard|custom)
  --create-home              Enable home directory creation
  --no-create-home           Disable home directory creation
  --backup-users             Enable user backup before changes
  --no-backup-users          Disable user backup before changes
  --validate                 Enable validation before apply
  --no-validate              Disable validation before apply

Component Control:
  --install-acl              Enable ACL tools installation
  --no-install-acl           Disable ACL tools installation
  --install-samba            Enable Samba installation
  --no-install-samba         Disable Samba installation
  --configure-users-groups   Enable users and groups configuration
  --no-configure-users-groups Disable users and groups configuration
  --configure-samba          Enable Samba configuration
  --no-configure-samba       Disable Samba configuration
  --configure-firewall       Enable firewall configuration
  --no-configure-firewall    Disable firewall configuration

Examples:
  $0                                    # Interactive mode with default config
  $0 --wizard                          # Run wizard to create config, then apply
  $0 --instructions /path/to/post_install_config_steps.yaml     # Use mode from config file
  $0 --instructions minimal.yaml --non-interactive --environment production  # Minimal config with CLI overrides
  $0 --instructions users-only.yaml --no-install-samba --no-configure-firewall  # Skip components
  $0 --dry-run --no-validate            # Show what would be done without validation

Configuration File:
  The YAML configuration file defines users, groups, and permissions.
  All base configuration settings can be overridden via command-line parameters.
  This allows minimal YAML files containing only groups, users, and/or paths.
  See yaml_user_setup_design.md for complete documentation and examples.
EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --instructions)
                INSTRUCTIONS_FILE="$2"
                shift 2
                ;;
            --non-interactive)
                INTERACTIVE_MODE=false
                COMMAND_LINE_INTERACTIVE_SET=true
                shift
                ;;
            --interactive)
                INTERACTIVE_MODE=true
                COMMAND_LINE_INTERACTIVE_SET=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                COMMAND_LINE_DRY_RUN_SET=true
                export DRY_RUN  # Export for child processes
                shift
                ;;
            --verbose)
                VERBOSE=true
                export VERBOSE  # Export for child processes
                shift
                ;;
            --wizard)
                RUN_WIZARD=true
                shift
                ;;
            # Base configuration overrides
            --environment)
                CLI_ENVIRONMENT="$2"
                shift 2
                ;;
            --mode)
                CLI_MODE="$2"
                shift 2
                ;;
            --create-home)
                CLI_CREATE_HOME="true"
                shift
                ;;
            --no-create-home)
                CLI_CREATE_HOME="false"
                shift
                ;;
            --backup-users)
                CLI_BACKUP_USERS="true"
                shift
                ;;
            --no-backup-users)
                CLI_BACKUP_USERS="false"
                shift
                ;;
            --validate)
                CLI_VALIDATE="true"
                shift
                ;;
            --no-validate)
                CLI_VALIDATE="false"
                shift
                ;;
            # Component control
            --install-acl)
                CLI_INSTALL_ACL="true"
                shift
                ;;
            --no-install-acl)
                CLI_INSTALL_ACL="false"
                shift
                ;;
            --install-samba)
                CLI_INSTALL_SAMBA="true"
                shift
                ;;
            --no-install-samba)
                CLI_INSTALL_SAMBA="false"
                shift
                ;;
            --configure-users-groups)
                CLI_CONFIGURE_USERS_GROUPS="true"
                shift
                ;;
            --no-configure-users-groups)
                CLI_CONFIGURE_USERS_GROUPS="false"
                shift
                ;;
            --configure-samba)
                CLI_CONFIGURE_SAMBA="true"
                shift
                ;;
            --no-configure-samba)
                CLI_CONFIGURE_SAMBA="false"
                shift
                ;;
            --configure-firewall)
                CLI_CONFIGURE_FIREWALL="true"
                shift
                ;;
            --no-configure-firewall)
                CLI_CONFIGURE_FIREWALL="false"
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
    if [[ -z "$INSTRUCTIONS_FILE" && "$RUN_WIZARD" == "false" ]]; then
        RUN_WIZARD=true
    fi
}

# Validate configuration file
validate_config() {
    echo "=== Configuration Validation ===" >&2
    echo "" >&2
    
    if [[ ! -f "$INSTRUCTIONS_FILE" ]]; then
        print_fail "Configuration file not found: $INSTRUCTIONS_FILE"
        echo "" >&2
        echo "Create a YAML configuration file defining users and groups." >&2
        echo "See yaml_user_setup_design.md for examples and documentation." >&2
        exit 1
    fi
    
    # Basic YAML validation using Python
    echo "Validating YAML syntax..."
    if ! python3 -c "import yaml; list(yaml.safe_load_all(open('$INSTRUCTIONS_FILE')))" 2>/dev/null; then
        print_fail "Invalid YAML configuration file"
        echo "" >&2
        echo "Please check your YAML syntax and try again." >&2
        exit 1
    fi
    
    # Enhanced validation with CLI override support
    echo "Validating configuration structure..."
    if ! python3 -m validate_config "$INSTRUCTIONS_FILE"; then
        print_fail "Configuration validation failed"
        echo "" >&2
        echo "Please review your configuration file and try again." >&2
        exit 1
    fi
    
    print_success "Configuration file validated: $INSTRUCTIONS_FILE"
    echo ""
}

# Read interactive mode settings from configuration
read_interactive_mode_settings() {
    # Only read from config if not explicitly set via command line
    if [[ "$INTERACTIVE_MODE" == "true" ]] && [[ -z "$COMMAND_LINE_INTERACTIVE_SET" ]]; then
        local mode=$(python3 -m read_config_settings "$INSTRUCTIONS_FILE" "interactive_mode")
        
        if [[ -n "$mode" ]]; then
            case "$mode" in
                "non-interactive")
                    print_info "Using non-interactive mode from configuration"
                    INTERACTIVE_MODE=false
                    ;;
                "interactive")
                    print_info "Using interactive mode from configuration"
                    INTERACTIVE_MODE=true
                    ;;
                "mixed")
                    print_info "Using mixed mode from configuration (critical prompts only)"
                    INTERACTIVE_MODE=true
                    # Set a flag for mixed mode that scripts can check
                    export MIXED_MODE=true
                    ;;
            esac
        fi
    fi
    
    # Check for dry-run default in config
    if [[ "$DRY_RUN" == "false" ]] && [[ -z "$COMMAND_LINE_DRY_RUN_SET" ]]; then
        local dry_run_default=$(python3 -m read_config_settings "$INSTRUCTIONS_FILE" "dry_run_default")
        
        if [[ "$dry_run_default" == "true" ]]; then
            print_info "Dry-run mode enabled by default from configuration"
            DRY_RUN=true
            export DRY_RUN
        fi
    fi
}

# Export CLI overrides as environment variables for Python modules
export_cli_overrides() {
    # Export CLI overrides as environment variables
    if [[ -n "$CLI_ENVIRONMENT" ]]; then
        export CLI_OVERRIDE_ENVIRONMENT="$CLI_ENVIRONMENT"
    fi
    
    if [[ -n "$CLI_MODE" ]]; then
        export CLI_OVERRIDE_MODE="$CLI_MODE"
    fi
    
    if [[ -n "$CLI_CREATE_HOME" ]]; then
        export CLI_OVERRIDE_CREATE_HOME="$CLI_CREATE_HOME"
    fi
    
    if [[ -n "$CLI_BACKUP_USERS" ]]; then
        export CLI_OVERRIDE_BACKUP_USERS="$CLI_BACKUP_USERS"
    fi
    
    if [[ -n "$CLI_VALIDATE" ]]; then
        export CLI_OVERRIDE_VALIDATE="$CLI_VALIDATE"
    fi
    
    if [[ -n "$CLI_INSTALL_ACL" ]]; then
        export CLI_OVERRIDE_INSTALL_ACL="$CLI_INSTALL_ACL"
    fi
    
    if [[ -n "$CLI_INSTALL_SAMBA" ]]; then
        export CLI_OVERRIDE_INSTALL_SAMBA="$CLI_INSTALL_SAMBA"
    fi
    
    if [[ -n "$CLI_CONFIGURE_USERS_GROUPS" ]]; then
        export CLI_OVERRIDE_CONFIGURE_USERS_GROUPS="$CLI_CONFIGURE_USERS_GROUPS"
    fi
    
    if [[ -n "$CLI_CONFIGURE_SAMBA" ]]; then
        export CLI_OVERRIDE_CONFIGURE_SAMBA="$CLI_CONFIGURE_SAMBA"
    fi
    
    if [[ -n "$CLI_CONFIGURE_FIREWALL" ]]; then
        export CLI_OVERRIDE_CONFIGURE_FIREWALL="$CLI_CONFIGURE_FIREWALL"
    fi
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
    echo "Configuration file: $INSTRUCTIONS_FILE"
    echo ""
    
    # Show configuration summary using Python module
    echo "Analyzing configuration..."
    python3 -m config_analyzer "$INSTRUCTIONS_FILE"
    
    if [[ $? -ne 0 ]]; then
        print_fail "Failed to analyze configuration"
        exit 1
    fi
    
    echo ""
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warn "🔍 DRY RUN MODE: No changes will be made"
        echo ""
    fi
    
    read -p "Proceed with configuration? (Default: Yes) [Y/n/x]: " CONFIRM
    case $CONFIRM in
        [Nn])
            echo "Configuration cancelled." >&2
            exit 0
            ;;
        [Xx])
            echo "Configuration cancelled by user." >&2
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
    
    # Check CLI overrides first
    case "$component_name" in
        "install_acl")
            if [[ -n "$CLI_INSTALL_ACL" ]]; then
                [[ "$CLI_INSTALL_ACL" == "true" ]]
                return $?
            fi
            ;;
        "install_samba")
            if [[ -n "$CLI_INSTALL_SAMBA" ]]; then
                [[ "$CLI_INSTALL_SAMBA" == "true" ]]
                return $?
            fi
            ;;
        "configure_users_groups")
            if [[ -n "$CLI_CONFIGURE_USERS_GROUPS" ]]; then
                [[ "$CLI_CONFIGURE_USERS_GROUPS" == "true" ]]
                return $?
            fi
            ;;
        "configure_samba")
            if [[ -n "$CLI_CONFIGURE_SAMBA" ]]; then
                [[ "$CLI_CONFIGURE_SAMBA" == "true" ]]
                return $?
            fi
            ;;
        "configure_firewall")
            if [[ -n "$CLI_CONFIGURE_FIREWALL" ]]; then
                [[ "$CLI_CONFIGURE_FIREWALL" == "true" ]]
                return $?
            fi
            ;;
    esac
    
    # Fall back to config file
    python3 -m check_component_enabled "$INSTRUCTIONS_FILE" "$component_name"
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
    
    python3 -m user_group_manager "$INSTRUCTIONS_FILE" "$PRODUCTION_DIR" $dry_run_flag $config_args

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
    
    python3 -m permission_manager "$INSTRUCTIONS_FILE" "$PRODUCTION_DIR" $dry_run_flag

    if [[ $? -ne 0 ]]; then
        print_warn "⚠️  Some permission settings may have failed"
    else
        print_success "File permissions configuration complete"
    fi
}

# Phase 4: Install launch scripts
phase_install_launch_scripts() {
    echo ""
    print_header "🚀 Phase 4: Installing launch scripts"
    echo ""
    
    # Determine installation mode from config
    local install_mode="production"
    if [[ -f "$INSTRUCTIONS_FILE" ]]; then
        install_mode=$(python3 -c "
import yaml
with open('$INSTRUCTIONS_FILE', 'r') as f:
    config = yaml.safe_load(f)
    print(config.get('install_mode', 'production'))
" 2>/dev/null || echo "production")
    fi
    
    # Set target directory based on mode
    local target_dir="/usr/local/bin"
    case "$install_mode" in
        development)
            target_dir="$PROJECT_ROOT/scripts"
            ;;
        user)
            target_dir="${HOME}/.local/bin"
            mkdir -p "$target_dir" 2>/dev/null || true
            ;;
        production|service)
            target_dir="/usr/local/bin"
            ;;
    esac
    
    # Copy launch scripts
    local scripts_copied=0
    
    # Copy shuttle launch script
    if [[ -f "$PROJECT_ROOT/scripts/launch-shuttle.sh" ]]; then
        if execute_or_execute_dryrun "sudo cp '$PROJECT_ROOT/scripts/launch-shuttle.sh' '$target_dir/launch-shuttle'" \
                                      "Copied shuttle launch script to $target_dir/launch-shuttle" \
                                      "Failed to copy shuttle launch script" \
                                      "Copy shuttle launch script with environment setup"; then
            execute_or_execute_dryrun "sudo chmod 755 '$target_dir/launch-shuttle'" \
                                      "Set executable permissions on launch-shuttle" \
                                      "Failed to set permissions on launch-shuttle" \
                                      "Make launch-shuttle executable"
            execute_or_execute_dryrun "sudo chown root:root '$target_dir/launch-shuttle'" \
                                      "Set ownership of launch-shuttle to root:root" \
                                      "Failed to set ownership on launch-shuttle" \
                                      "Set secure ownership on launch-shuttle"
            ((scripts_copied++))
        fi
    else
        print_warn "⚠️  Shuttle launch script not found at $PROJECT_ROOT/scripts/launch-shuttle.sh"
    fi
    
    # Copy defender test launch script
    if [[ -f "$PROJECT_ROOT/scripts/launch-shuttle-defender-test.sh" ]]; then
        if execute_or_execute_dryrun "sudo cp '$PROJECT_ROOT/scripts/launch-shuttle-defender-test.sh' '$target_dir/launch-shuttle-defender-test'" \
                                      "Copied defender test launch script to $target_dir/launch-shuttle-defender-test" \
                                      "Failed to copy defender test launch script" \
                                      "Copy defender test launch script with environment setup"; then
            execute_or_execute_dryrun "sudo chmod 755 '$target_dir/launch-shuttle-defender-test'" \
                                      "Set executable permissions on launch-shuttle-defender-test" \
                                      "Failed to set permissions on launch-shuttle-defender-test" \
                                      "Make launch-shuttle-defender-test executable"
            execute_or_execute_dryrun "sudo chown root:root '$target_dir/launch-shuttle-defender-test'" \
                                      "Set ownership of launch-shuttle-defender-test to root:root" \
                                      "Failed to set ownership on launch-shuttle-defender-test" \
                                      "Set secure ownership on launch-shuttle-defender-test"
            ((scripts_copied++))
        fi
    else
        print_warn "⚠️  Defender test launch script not found at $PROJECT_ROOT/scripts/launch-shuttle-defender-test.sh"
    fi
    
    if [[ $scripts_copied -gt 0 ]]; then
        print_success "Launch scripts installation complete ($scripts_copied scripts installed)"
        echo ""
        echo "Launch scripts installed to: $target_dir"
        echo "Usage:"
        echo "  sudo -u shuttle_runner $target_dir/launch-shuttle"
        echo "  sudo -u shuttle_defender_test_runner $target_dir/launch-shuttle-defender-test"
    else
        print_warn "⚠️  No launch scripts were installed"
    fi
}

# Phase 5: Configure Samba
phase_configure_samba() {
    if ! is_component_enabled "configure_samba"; then
        echo ""
        print_warn "⏭️  Phase 5: Skipping Samba configuration"
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
    
    local interactive_flag=""
    if [[ "$INTERACTIVE_MODE" == "false" ]]; then
        interactive_flag="--non-interactive"
    fi
    
    python3 -m samba_manager "$INSTRUCTIONS_FILE" "$PRODUCTION_DIR" $dry_run_flag $interactive_flag

    if [[ $? -ne 0 ]]; then
        print_warn "⚠️  Some Samba configuration may have failed"
    else
        print_success "Samba configuration complete"
    fi
}

# Phase 6: Configure firewall
phase_configure_firewall() {
    if ! is_component_enabled "configure_firewall"; then
        echo ""
        print_warn "⏭️  Phase 6: Skipping firewall configuration"
        return 0
    fi
    
    echo ""
    print_header "🔥 Phase 6: Configuring firewall"
    echo ""
    
    # Use Python module to configure firewall from YAML
    local dry_run_flag=""
    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_flag="--dry-run"
    fi
    
    local interactive_flag=""
    if [[ "$INTERACTIVE_MODE" == "false" ]]; then
        interactive_flag="--non-interactive"
    fi
    
    python3 -m firewall_manager "$INSTRUCTIONS_FILE" "$PRODUCTION_DIR" $dry_run_flag $interactive_flag

    if [[ $? -ne 0 ]]; then
        print_warn "⚠️  Some firewall configuration may have failed"
    else
        print_success "Firewall configuration complete"
    fi
}

# Run configuration wizard
run_configuration_wizard() {
    echo ""
    print_header "🧙 Running Configuration Wizard"
    echo ""
    
    # Change to config directory
    cd "$PROJECT_ROOT/config"
    
    # Ensure PYTHONPATH is set for the wizard
    export PYTHONPATH="${SETUP_LIB_DIR}:${PYTHONPATH}"
    
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
    
    if [[ $wizard_exit_code -eq 3 ]]; then
        # User cancelled the wizard
        print_info "Configuration wizard cancelled by user"
        exit 0
    elif [[ $wizard_exit_code -eq 2 ]]; then
        # Configuration was saved but user chose not to continue
        local config_filename=""
        if [[ -f /tmp/wizard_config_filename ]]; then
            config_filename=$(cat /tmp/wizard_config_filename)
            rm -f /tmp/wizard_config_filename
            # Check if config_filename is already an absolute path
            if [[ "$config_filename" = /* ]]; then
                # Already absolute path, use as-is
                config_filename="$config_filename"
            else
                config_filename="$PROJECT_ROOT/config/$config_filename"
            fi
        else
            # Try to find the most recently generated config file
            local latest_config=$(ls -t $CONFIG_GLOB_PATTERN 2>/dev/null | head -1)
            if [[ -n "$latest_config" ]]; then
                config_filename="$PROJECT_ROOT/config/$latest_config"
            fi
        fi
        
        if [[ -n "$config_filename" ]]; then
            show_saved_config_usage "$0" "$config_filename" "configuration" "false"
        else
            print_success "Configuration saved successfully"
            echo "Exiting as requested - configuration saved but not applied."
        fi
        exit 0
    elif [[ $wizard_exit_code -ne 0 ]]; then
        print_fail "Configuration wizard failed"
        exit 1
    fi
    
    # Check if wizard saved a filename for us to use
    if [[ -f /tmp/wizard_config_filename ]]; then
        local wizard_filename=$(cat /tmp/wizard_config_filename)
        rm -f /tmp/wizard_config_filename
        # Check if wizard_filename is already an absolute path
        if [[ "$wizard_filename" = /* ]]; then
            INSTRUCTIONS_FILE="$wizard_filename"
        else
            INSTRUCTIONS_FILE="$PROJECT_ROOT/config/$wizard_filename"
        fi
        echo ""
        print_success "Using wizard-generated configuration: $INSTRUCTIONS_FILE"
        echo ""
        # Show usage instructions for the saved configuration
        show_saved_config_usage "$0" "$INSTRUCTIONS_FILE" "configuration" "false"
        echo ""
        print_info "Continuing to apply configuration..."
        echo ""
    else
        # Try to find the most recently generated config file
        local latest_config=$(ls -t $CONFIG_GLOB_PATTERN 2>/dev/null | head -1)
        
        if [[ -n "$latest_config" ]]; then
            INSTRUCTIONS_FILE="$PROJECT_ROOT/config/$latest_config"
            echo ""
            print_success "Using generated configuration: $INSTRUCTIONS_FILE"
            echo ""
            # Show usage instructions for the saved configuration
            show_saved_config_usage "$0" "$INSTRUCTIONS_FILE" "configuration" "false"
            echo ""
            print_info "Continuing to apply configuration..."
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
    
    echo "Configuration file used: $INSTRUCTIONS_FILE"
    echo "For detailed configuration options, see: yaml_user_setup_design.md"
}

# Main execution function
main() {
    # Parse command line arguments first (before banner, in case of --help)
    parse_arguments "$@"
    
    echo "Starting production environment configuration..." >&2
    echo "" >&2
    
    # Export CLI overrides for Python modules
    export_cli_overrides
    
    # Run wizard if requested
    if [[ "$RUN_WIZARD" == "true" ]]; then
        run_configuration_wizard
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Validate configuration
    validate_config
    
    # Read interactive mode settings from config
    read_interactive_mode_settings
    
    # Interactive setup if needed
    interactive_setup
    
    # Execute phases
    phase_install_tools
    phase_configure_users
    phase_set_permissions
    phase_install_launch_scripts
    phase_configure_samba
    phase_configure_firewall
    
    # Show completion summary
    show_completion_summary
}

# Run main function with all arguments
main "$@"