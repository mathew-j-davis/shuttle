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

# Add setup lib to Python path
export PYTHONPATH="${SETUP_LIB_DIR}:${PYTHONPATH}"

# Default configuration file location
DEFAULT_CONFIG="$PROJECT_ROOT/config/shuttle_user_setup.yaml"
CONFIG_FILE=""
INTERACTIVE_MODE=true
DRY_RUN=false

echo "========================================="
echo "  Production Environment Configuration  "
echo "========================================="
echo ""
echo "This script configures the production environment for Shuttle:"
echo "" System tools installation"
echo "" User and group management"
echo "" File permissions and ownership"
echo "" Samba configuration"
echo "" Firewall configuration"
echo ""

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [options]

Options:
  --config <file>       Path to YAML configuration file (default: $DEFAULT_CONFIG)
  --non-interactive     Run in non-interactive mode
  --dry-run             Show what would be done without making changes
  --help               Show this help message

Examples:
  $0                                    # Interactive mode with default config
  $0 --config /path/to/config.yaml     # Interactive mode with custom config
  $0 --config config.yaml --non-interactive  # Automated mode
  $0 --dry-run                          # Show what would be done

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
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                echo -e "${RED}L Unknown option: $1${NC}"
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
        echo -e "${RED}L Configuration file not found: $CONFIG_FILE${NC}"
        echo ""
        echo "Create a YAML configuration file defining users and groups."
        echo "See yaml_user_setup_design.md for examples and documentation."
        exit 1
    fi
    
    # Basic YAML validation using Python
    echo "Validating YAML syntax..."
    if ! python3 -c "import yaml; list(yaml.safe_load_all(open('$CONFIG_FILE')))" 2>/dev/null; then
        echo -e "${RED}L Invalid YAML configuration file${NC}"
        echo ""
        echo "Please check your YAML syntax and try again."
        exit 1
    fi
    
    echo -e "${GREEN} Configuration file validated: $CONFIG_FILE${NC}"
    echo ""
}

# Check prerequisites
check_prerequisites() {
    echo "=== Prerequisites Check ==="
    echo ""
    
    # Check if Python 3 is available
    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "${RED}L Python 3 is required but not found${NC}"
        echo "Please install Python 3 and try again."
        exit 1
    fi
    
    # Check if PyYAML is available
    if ! python3 -c "import yaml" 2>/dev/null; then
        echo -e "${RED}L PyYAML is required but not found${NC}"
        echo "Please install PyYAML: pip install PyYAML"
        exit 1
    fi
    
    # Check if production scripts directory exists
    if [[ ! -d "$PRODUCTION_DIR" ]]; then
        echo -e "${RED}L Production scripts directory not found: $PRODUCTION_DIR${NC}"
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
            echo -e "${RED}L Required script not found: $PRODUCTION_DIR/$script${NC}"
            exit 1
        fi
        if [[ ! -x "$PRODUCTION_DIR/$script" ]]; then
            echo -e "${YELLOW}�  Making script executable: $script${NC}"
            chmod +x "$PRODUCTION_DIR/$script"
        fi
    done
    
    echo -e "${GREEN} All prerequisites satisfied${NC}"
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
    
    # Show configuration summary using Python
    echo "Analyzing configuration..."
    python3 << EOF
import yaml
import sys

try:
    with open('$CONFIG_FILE', 'r') as f:
        docs = list(yaml.safe_load_all(f))
except Exception as e:
    print(f"Error reading configuration: {e}")
    sys.exit(1)

users = []
groups = {}
settings = {}

for doc in docs:
    if doc is None:
        continue
    if doc.get('type') == 'user':
        users.append(doc['user'])
    elif 'groups' in doc:
        groups = doc.get('groups', {})
        settings = doc.get('settings', {})

print("Configuration Summary:")
print(f"  Environment: {settings.get('metadata', {}).get('environment', 'Not specified')}")
print(f"  Groups to create: {len(groups)}")
for group_name, group_info in groups.items():
    desc = group_info.get('description', 'No description') if isinstance(group_info, dict) else str(group_info)
    print(f"    - {group_name}: {desc}")

print(f"  Users to configure: {len(users)}")
for user in users:
    caps = user.get('capabilities', {}).get('executables', [])
    caps_str = ', '.join(caps) if caps else 'None'
    samba_enabled = user.get('samba', {}).get('enabled', False)
    samba_str = ' (Samba enabled)' if samba_enabled else ''
    print(f"    - {user['name']} ({user['source']}, {user['account_type']}){samba_str}")
    print(f"      Capabilities: {caps_str}")
    
    # Show permission summary
    permissions = user.get('permissions', {})
    rw_count = len(permissions.get('read_write', []))
    ro_count = len(permissions.get('read_only', []))
    if rw_count > 0 or ro_count > 0:
        print(f"      Permissions: {rw_count} read-write, {ro_count} read-only")

if len(users) == 0:
    print("�  No users defined in configuration")
EOF
    
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}L Failed to analyze configuration${NC}"
        exit 1
    fi
    
    echo ""
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}= DRY RUN MODE: No changes will be made${NC}"
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

# Phase 1: Install system tools
phase_install_tools() {
    echo ""
    echo -e "${BLUE}=� Phase 1: Installing system tools${NC}"
    echo ""
    
    local cmd="$PRODUCTION_DIR/11_install_tools.sh"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would execute: $cmd"
        echo -e "${GREEN} System tools installation (dry run)${NC}"
    else
        echo "Installing required system tools..."
        if "$cmd"; then
            echo -e "${GREEN} System tools installation complete${NC}"
        else
            echo -e "${RED}L Failed to install system tools${NC}"
            exit 1
        fi
    fi
}

# Phase 2: Configure users and groups
phase_configure_users() {
    echo ""
    echo -e "${BLUE}=e Phase 2: Configuring users and groups${NC}"
    echo ""
    
    # Use Python to parse YAML and generate commands
    python3 << EOF
import yaml
import subprocess
import sys
import os

dry_run = "$DRY_RUN" == "true"
production_dir = "$PRODUCTION_DIR"

def run_command(cmd_list, description):
    """Execute command or show what would be executed in dry run"""
    cmd_str = " ".join([f'"{arg}"' if ' ' in arg else arg for arg in cmd_list])
    
    if dry_run:
        print(f"[DRY RUN] {description}")
        print(f"  Command: {cmd_str}")
        return True
    else:
        print(f"Executing: {description}")
        try:
            result = subprocess.run(cmd_list, check=True, capture_output=True, text=True)
            if result.stdout.strip():
                print(f"  Output: {result.stdout.strip()}")
            print(f" {description} completed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"L {description} failed")
            if e.stdout:
                print(f"  stdout: {e.stdout.strip()}")
            if e.stderr:
                print(f"  stderr: {e.stderr.strip()}")
            return False

# Read YAML configuration
try:
    with open('$CONFIG_FILE', 'r') as f:
        docs = list(yaml.safe_load_all(f))
except Exception as e:
    print(f"Error reading configuration: {e}")
    sys.exit(1)

# Parse documents
groups = {}
users = []
settings = {}

for doc in docs:
    if doc is None:
        continue
    if doc.get('type') == 'user':
        users.append(doc['user'])
    elif 'groups' in doc:
        groups = doc.get('groups', {})
        settings = doc.get('settings', {})

# Create groups first
if groups:
    print("Creating groups...")
    for group_name, group_info in groups.items():
        cmd = [f"{production_dir}/12_users_and_groups.sh", "add-group", "--group", group_name]
        if not run_command(cmd, f"Create group '{group_name}'"):
            print(f"Warning: Failed to create group {group_name}")
    print()

# Process users
if users:
    print("Processing users...")
    for user in users:
        user_name = user['name']
        print(f"Configuring user: {user_name}")
        
        # Create user if source is 'local'
        if user['source'] == 'local':
            cmd = [f"{production_dir}/12_users_and_groups.sh", "add-user", "--user", user_name]
            
            if 'shell' in user:
                cmd.extend(["--shell", user['shell']])
            if 'home_directory' in user:
                cmd.extend(["--home", user['home_directory']])
            if user.get('create_home', False):
                cmd.append("--create-home")
            
            if not run_command(cmd, f"Create local user '{user_name}'"):
                print(f"Error: Failed to create user {user_name}")
                sys.exit(1)
        
        # Add user to groups
        groups_config = user.get('groups', {})
        
        # Set primary group if specified
        if 'primary' in groups_config:
            cmd = [f"{production_dir}/12_users_and_groups.sh", "add-user-to-group", 
                   "--user", user_name, "--group", groups_config['primary']]
            if user['source'] == 'domain':
                cmd.append("--domain")
            
            if not run_command(cmd, f"Add '{user_name}' to primary group '{groups_config['primary']}'"):
                print(f"Warning: Failed to add {user_name} to primary group")
        
        # Add to secondary groups
        for group in groups_config.get('secondary', []):
            cmd = [f"{production_dir}/12_users_and_groups.sh", "add-user-to-group", 
                   "--user", user_name, "--group", group]
            if user['source'] == 'domain':
                cmd.append("--domain")
            
            if not run_command(cmd, f"Add '{user_name}' to secondary group '{group}'"):
                print(f"Warning: Failed to add {user_name} to group {group}")
        
        print()

print("Users and groups configuration complete")
EOF

    if [[ $? -ne 0 ]]; then
        echo -e "${RED}L Failed to configure users and groups${NC}"
        exit 1
    fi
    echo -e "${GREEN} Users and groups configuration complete${NC}"
}

# Phase 3: Set permissions
phase_set_permissions() {
    echo ""
    echo -e "${BLUE}= Phase 3: Setting file permissions${NC}"
    echo ""
    
    python3 << EOF
import yaml
import subprocess
import sys
import os
import configparser
from pathlib import Path

dry_run = "$DRY_RUN" == "true"
production_dir = "$PRODUCTION_DIR"

# Path resolver (embedded version)
def resolve_path(symbolic_name):
    """Resolve symbolic path name to actual path"""
    shuttle_config_path = os.environ.get('SHUTTLE_CONFIG_PATH')
    config = None
    
    # Load shuttle config if available
    if shuttle_config_path and Path(shuttle_config_path).exists():
        try:
            config = configparser.ConfigParser()
            config.read(shuttle_config_path)
        except:
            pass  # Ignore config read errors
    
    path_map = {
        'source_path': {
            'env': 'SHUTTLE_CONFIG_SOURCE_PATH',
            'config': ('paths', 'source_path'),
            'default': '/srv/shuttle/incoming'
        },
        'destination_path': {
            'env': 'SHUTTLE_CONFIG_DEST_PATH',
            'config': ('paths', 'destination_path'),
            'default': '/srv/shuttle/processed'
        },
        'quarantine_path': {
            'env': 'SHUTTLE_CONFIG_QUARANTINE_PATH',
            'config': ('paths', 'quarantine_path'),
            'default': '/tmp/shuttle/quarantine'
        },
        'log_path': {
            'env': 'SHUTTLE_CONFIG_LOG_PATH',
            'config': ('paths', 'log_path'),
            'default': '/var/log/shuttle'
        },
        'hazard_archive_path': {
            'env': 'SHUTTLE_CONFIG_HAZARD_PATH',
            'config': ('paths', 'hazard_archive_path'),
            'default': '/srv/shuttle/hazard'
        },
        'ledger_file_path': {
            'env': 'SHUTTLE_CONFIG_LEDGER_PATH',
            'config': ('paths', 'ledger_file_path'),
            'default': '/etc/shuttle/ledger.yaml'
        },
        'hazard_encryption_key_path': {
            'env': 'SHUTTLE_CONFIG_KEY_PATH',
            'config': ('paths', 'hazard_encryption_key_path'),
            'default': '/etc/shuttle/shuttle_public.gpg'
        },
        'shuttle_config_path': {
            'env': 'SHUTTLE_CONFIG_PATH',
            'config': None,
            'default': '/etc/shuttle/config.conf'
        },
        'test_work_dir': {
            'env': 'SHUTTLE_TEST_WORK_DIR',
            'config': None,
            'default': '/var/lib/shuttle/test'
        },
        'test_config_path': {
            'env': 'SHUTTLE_TEST_CONFIG_PATH',
            'config': None,
            'default': '/etc/shuttle/test_config.conf'
        }
    }
    
    if symbolic_name not in path_map:
        return symbolic_name  # Return as-is if not symbolic
    
    path_info = path_map[symbolic_name]
    
    # Check environment variable
    if path_info['env'] and os.environ.get(path_info['env']):
        return os.environ[path_info['env']]
    
    # Check config file
    if (path_info['config'] and config and 
        config.has_section(path_info['config'][0]) and
        config.has_option(path_info['config'][0], path_info['config'][1])):
        return config.get(path_info['config'][0], path_info['config'][1])
    
    # Use default
    return path_info['default']

def run_command(cmd_list, description):
    """Execute command or show what would be executed in dry run"""
    cmd_str = " ".join([f'"{arg}"' if ' ' in arg else arg for arg in cmd_list])
    
    if dry_run:
        print(f"[DRY RUN] {description}")
        print(f"  Command: {cmd_str}")
        return True
    else:
        print(f"Executing: {description}")
        try:
            result = subprocess.run(cmd_list, check=True, capture_output=True, text=True)
            if result.stdout.strip():
                print(f"  Output: {result.stdout.strip()}")
            print(f" {description} completed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"L {description} failed")
            if e.stderr:
                print(f"  Error: {e.stderr.strip()}")
            return False

# Read YAML configuration
try:
    with open('$CONFIG_FILE', 'r') as f:
        docs = list(yaml.safe_load_all(f))
except Exception as e:
    print(f"Error reading configuration: {e}")
    sys.exit(1)

# Find users
users = []
for doc in docs:
    if doc is None:
        continue
    if doc.get('type') == 'user':
        users.append(doc['user'])

# Set permissions for each user
permission_count = 0
for user in users:
    user_name = user['name']
    permissions = user.get('permissions', {})
    
    if not permissions:
        continue
        
    print(f"Setting permissions for user: {user_name}")
    
    # Handle read-write permissions
    for perm in permissions.get('read_write', []):
        actual_path = resolve_path(perm['path'])
        mode = perm.get('mode', '755')
        
        cmd = [f"{production_dir}/12_users_and_groups.sh", "set-path-permissions", 
               "--path", actual_path, "--mode", mode]
        
        if perm.get('recursive', False):
            cmd.append("--recursive")
        
        desc = f"Set {mode} permissions on {actual_path}"
        if perm.get('recursive', False):
            desc += " (recursive)"
        
        if run_command(cmd, desc):
            permission_count += 1
        else:
            print(f"Warning: Failed to set permissions on {actual_path}")
    
    # Handle read-only permissions
    for perm in permissions.get('read_only', []):
        actual_path = resolve_path(perm['path'])
        mode = perm.get('mode', '644')
        
        cmd = [f"{production_dir}/12_users_and_groups.sh", "set-path-permissions", 
               "--path", actual_path, "--mode", mode]
        
        desc = f"Set {mode} permissions on {actual_path}"
        
        if run_command(cmd, desc):
            permission_count += 1
        else:
            print(f"Warning: Failed to set permissions on {actual_path}")

if permission_count > 0:
    print(f"Processed {permission_count} permission settings")
else:
    print("No permissions to set")

print("File permissions configuration complete")
EOF

    if [[ $? -ne 0 ]]; then
        echo -e "${YELLOW}�  Some permission settings may have failed${NC}"
    else
        echo -e "${GREEN} File permissions configuration complete${NC}"
    fi
}

# Phase 4: Configure Samba
phase_configure_samba() {
    echo ""
    echo -e "${BLUE}< Phase 4: Configuring Samba${NC}"
    echo ""
    
    # Extract Samba users from configuration
    python3 << EOF
import yaml
import subprocess
import sys

dry_run = "$DRY_RUN" == "true"
production_dir = "$PRODUCTION_DIR"

def run_command(cmd_list, description):
    """Execute command or show what would be executed in dry run"""
    cmd_str = " ".join([f'"{arg}"' if ' ' in arg else arg for arg in cmd_list])
    
    if dry_run:
        print(f"[DRY RUN] {description}")
        print(f"  Command: {cmd_str}")
        return True
    else:
        print(f"Executing: {description}")
        try:
            result = subprocess.run(cmd_list, check=True, capture_output=True, text=True)
            if result.stdout.strip():
                print(f"  Output: {result.stdout.strip()}")
            print(f" {description} completed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"L {description} failed")
            if e.stderr:
                print(f"  Error: {e.stderr.strip()}")
            return False

# Read YAML configuration
try:
    with open('$CONFIG_FILE', 'r') as f:
        docs = list(yaml.safe_load_all(f))
except Exception as e:
    print(f"Error reading configuration: {e}")
    sys.exit(1)

# Find users with Samba enabled
samba_users = []
for doc in docs:
    if doc is None:
        continue
    if doc.get('type') == 'user':
        user = doc['user']
        if user.get('samba', {}).get('enabled', False):
            samba_users.append(user)

if not samba_users:
    print("No Samba users configured")
else:
    print(f"Configuring {len(samba_users)} Samba users...")
    
    for user in samba_users:
        user_name = user['name']
        print(f"Configuring Samba for user: {user_name}")
        
        # Add Samba user
        cmd = [f"{production_dir}/13_configure_samba.sh", "add-samba-user", "--user", user_name]
        if user['source'] == 'domain':
            cmd.append("--domain")
        
        if not run_command(cmd, f"Add Samba user '{user_name}'"):
            print(f"Warning: Failed to add Samba user {user_name}")
            continue
        
        # Set Samba password if provided
        samba_config = user.get('samba', {})
        if 'password' in samba_config:
            cmd = [f"{production_dir}/13_configure_samba.sh", "set-samba-password", 
                   "--user", user_name, "--password", samba_config['password']]
            if not run_command(cmd, f"Set Samba password for '{user_name}'"):
                print(f"Warning: Failed to set Samba password for {user_name}")

print("Samba configuration complete")
EOF

    if [[ $? -ne 0 ]]; then
        echo -e "${YELLOW}�  Some Samba configuration may have failed${NC}"
    else
        echo -e "${GREEN} Samba configuration complete${NC}"
    fi
}

# Phase 5: Configure firewall
phase_configure_firewall() {
    echo ""
    echo -e "${BLUE}=% Phase 5: Configuring firewall${NC}"
    echo ""
    
    local cmd="$PRODUCTION_DIR/14_configure_firewall.sh show-status"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would execute: $cmd"
        echo -e "${GREEN} Firewall configuration (dry run)${NC}"
    else
        echo "Checking firewall status..."
        if "$PRODUCTION_DIR/14_configure_firewall.sh" show-status; then
            echo -e "${GREEN} Firewall configuration complete${NC}"
        else
            echo -e "${YELLOW}�  Firewall configuration check completed with warnings${NC}"
        fi
    fi
}

# Show completion summary
show_completion_summary() {
    echo ""
    echo -e "${GREEN}<� Production environment configuration complete!${NC}"
    echo ""
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}This was a dry run. No changes were made.${NC}"
        echo "Run without --dry-run to apply the configuration."
        echo ""
    else
        echo "Configuration applied successfully:"
        echo " System tools installed"
        echo " Users and groups configured"
        echo " File permissions set"
        echo " Samba configured"
        echo " Firewall checked"
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