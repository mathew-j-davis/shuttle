#!/bin/bash
# 2_configure_production.sh - Production environment configuration orchestrator
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
PRODUCTION_DIR="$SCRIPT_DIR/2_production_environment_steps"
SETUP_LIB_DIR="$SCRIPT_DIR/__setup_lib"
LIB_DIR="$PRODUCTION_DIR/lib"

# Add setup lib to Python path
export PYTHONPATH="${SETUP_LIB_DIR}:${PYTHONPATH}"

# Source helper functions for sudo detection and logging
source "$LIB_DIR/_common_.source.sh"
source "$LIB_DIR/_check_active_user.source.sh"

# Default configuration file location
DEFAULT_CONFIG="$PROJECT_ROOT/config/shuttle_user_setup.yaml"
CONFIG_FILE=""
INTERACTIVE_MODE=true
DRY_RUN=false
RUN_WIZARD=false

echo "========================================="
echo "  Production Environment Configuration  "
echo "========================================="
echo ""
echo "This script configures the production environment for Shuttle:"
echo "• System tools installation"
echo "• User and group management"
echo "• File permissions and ownership"
echo "• Samba configuration"
echo "• Firewall configuration"
echo ""

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [options]

Options:
  --config <file>       Path to YAML configuration file (default: $DEFAULT_CONFIG)
  --non-interactive     Run in non-interactive mode
  --dry-run             Show what would be done without making changes
  --wizard              Run configuration wizard to create YAML file first
  --help               Show this help message

Examples:
  $0                                    # Interactive mode with default config
  $0 --wizard                          # Run wizard to create config, then apply
  $0 --config /path/to/config.yaml     # Interactive mode with custom config
  $0 --config config.yaml --non-interactive  # Automated mode
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
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --non-interactive)
                INTERACTIVE_MODE=false
                shift
                ;;
            --dry-run)
                DRY_RUN=true
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
                echo -e "${RED}❌ Unknown option: $1${NC}"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Set default config if not specified
    CONFIG_FILE=${CONFIG_FILE:-$DEFAULT_CONFIG}
}

# Validate configuration file
validate_config() {
    echo "=== Configuration Validation ==="
    echo ""
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo -e "${RED}❌ Configuration file not found: $CONFIG_FILE${NC}"
        echo ""
        echo "Create a YAML configuration file defining users and groups."
        echo "See yaml_user_setup_design.md for examples and documentation."
        exit 1
    fi
    
    # Basic YAML validation using Python
    echo "Validating YAML syntax..."
    if ! python3 -c "import yaml; list(yaml.safe_load_all(open('$CONFIG_FILE')))" 2>/dev/null; then
        echo -e "${RED}❌ Invalid YAML configuration file${NC}"
        echo ""
        echo "Please check your YAML syntax and try again."
        exit 1
    fi
    
    echo -e "${GREEN}✅ Configuration file validated: $CONFIG_FILE${NC}"
    echo ""
}

# Check prerequisites
check_prerequisites() {
    echo "=== Prerequisites Check ==="
    echo ""
    
    # Check if Python 3 is available
    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "${RED}❌ Python 3 is required but not found${NC}"
        echo "Please install Python 3 and try again."
        exit 1
    fi
    
    # Check if PyYAML is available
    if ! python3 -c "import yaml" 2>/dev/null; then
        echo -e "${RED}❌ PyYAML is required but not found${NC}"
        echo "Please install PyYAML: pip install PyYAML"
        exit 1
    fi
    
    # Check if production scripts directory exists
    if [[ ! -d "$PRODUCTION_DIR" ]]; then
        echo -e "${RED}❌ Production scripts directory not found: $PRODUCTION_DIR${NC}"
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
            echo -e "${RED}❌ Required script not found: $PRODUCTION_DIR/$script${NC}"
            exit 1
        fi
        if [[ ! -x "$PRODUCTION_DIR/$script" ]]; then
            echo -e "${YELLOW}⚠️  Making script executable: $script${NC}"
            chmod +x "$PRODUCTION_DIR/$script"
        fi
    done
    
    # Check sudo access for system modifications
    echo "Checking system privileges..."
    if check_active_user_is_root; then
        echo -e "${GREEN}✅ Running as root - full system access available${NC}"
    elif check_active_user_has_sudo_access; then
        echo -e "${GREEN}✅ Sudo access available - system modifications possible${NC}"
    else
        echo -e "${RED}❌ No root or sudo access - system modifications will fail${NC}"
        echo "Please run as root or ensure your user has sudo privileges."
        exit 1
    fi
    
    echo -e "${GREEN}✅ All prerequisites satisfied${NC}"
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
        echo -e "${RED}❌ Failed to analyze configuration${NC}"
        exit 1
    fi
    
    echo ""
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}🔍 DRY RUN MODE: No changes will be made${NC}"
        echo ""
    fi
    
    read -p "Proceed with configuration? [Y/n]: " CONFIRM
    case $CONFIRM in
        [Nn])
            echo "Configuration cancelled."
            exit 0
            ;;
        *)
            echo -e "${GREEN}Proceeding with configuration...${NC}"
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
    echo -e "${BLUE}📦 Phase 1: Installing system tools${NC}"
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
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would execute: $cmd $install_flags"
        echo -e "${GREEN}✅ System tools installation (dry run)${NC}"
    else
        echo "Installing required system tools..."
        if "$cmd" $install_flags; then
            echo -e "${GREEN}✅ System tools installation complete${NC}"
        else
            echo -e "${RED}❌ Failed to install system tools${NC}"
            exit 1
        fi
    fi
}

# Phase 2: Configure users and groups
phase_configure_users() {
    if ! is_component_enabled "configure_users_groups"; then
        echo ""
        echo -e "${YELLOW}⏭️  Phase 2: Skipping users and groups configuration${NC}"
        return 0
    fi
    
    echo ""
    echo -e "${BLUE}👥 Phase 2: Configuring users and groups${NC}"
    echo ""
    
    # Use Python module to process users and groups
    local dry_run_flag=""
    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_flag="--dry-run"
    fi
    
    python3 -m user_group_manager "$CONFIG_FILE" "$PRODUCTION_DIR" $dry_run_flag

    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ Failed to configure users and groups${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Users and groups configuration complete${NC}"
}

# Phase 3: Set permissions
phase_set_permissions() {
    echo ""
    echo -e "${BLUE}🔐 Phase 3: Setting file permissions${NC}"
    echo ""
    
    # Use Python module to process permissions
    local dry_run_flag=""
    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_flag="--dry-run"
    fi
    
    python3 -m permission_manager "$CONFIG_FILE" "$PRODUCTION_DIR" $dry_run_flag

    if [[ $? -ne 0 ]]; then
        echo -e "${YELLOW}⚠️  Some permission settings may have failed${NC}"
    else
        echo -e "${GREEN}✅ File permissions configuration complete${NC}"
    fi
}

# Phase 4: Configure Samba
phase_configure_samba() {
    if ! is_component_enabled "configure_samba"; then
        echo ""
        echo -e "${YELLOW}⏭️  Phase 4: Skipping Samba configuration${NC}"
        return 0
    fi
    
    echo ""
    echo -e "${BLUE}🌐 Phase 4: Configuring Samba${NC}"
    echo ""
    
    # Use Python module to configure Samba
    local dry_run_flag=""
    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_flag="--dry-run"
    fi
    
    python3 -m samba_manager "$CONFIG_FILE" "$PRODUCTION_DIR" $dry_run_flag

    if [[ $? -ne 0 ]]; then
        echo -e "${YELLOW}⚠️  Some Samba configuration may have failed${NC}"
    else
        echo -e "${GREEN}✅ Samba configuration complete${NC}"
    fi
}

# Phase 5: Configure firewall
phase_configure_firewall() {
    if ! is_component_enabled "configure_firewall"; then
        echo ""
        echo -e "${YELLOW}⏭️  Phase 5: Skipping firewall configuration${NC}"
        return 0
    fi
    
    echo ""
    echo -e "${BLUE}🔥 Phase 5: Configuring firewall${NC}"
    echo ""
    
    local cmd="$PRODUCTION_DIR/14_configure_firewall.sh show-status"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would execute: $cmd"
        echo -e "${GREEN}✅ Firewall configuration (dry run)${NC}"
    else
        echo "Checking firewall status..."
        if "$PRODUCTION_DIR/14_configure_firewall.sh" show-status; then
            echo -e "${GREEN}✅ Firewall configuration complete${NC}"
        else
            echo -e "${YELLOW}⚠️  Firewall configuration check completed with warnings${NC}"
        fi
    fi
}

# Run configuration wizard
run_configuration_wizard() {
    echo ""
    echo -e "${BLUE}🧙 Running Configuration Wizard${NC}"
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
    python3 -m config_wizard $wizard_args
    
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ Configuration wizard failed${NC}"
        exit 1
    fi
    
    # Try to find the generated config file
    local latest_config=$(ls -t shuttle_user_setup_*.yaml 2>/dev/null | head -1)
    
    if [[ -n "$latest_config" ]]; then
        CONFIG_FILE="$PROJECT_ROOT/config/$latest_config"
        echo ""
        echo -e "${GREEN}✅ Using generated configuration: $CONFIG_FILE${NC}"
        echo ""
    else
        echo -e "${RED}❌ Could not find generated configuration file${NC}"
        exit 1
    fi
    
    # Return to script directory
    cd "$SCRIPT_DIR"
}

# Show completion summary
show_completion_summary() {
    echo ""
    echo -e "${GREEN}🎉 Production environment configuration complete!${NC}"
    echo ""
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}This was a dry run. No changes were made.${NC}"
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
    echo "Starting production environment configuration..."
    echo ""
    
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