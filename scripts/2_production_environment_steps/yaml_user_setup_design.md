# YAML-Based User Setup Configuration System

## Table of Contents
1. [Overview](#overview)
2. [YAML Configuration Schema](#yaml-configuration-schema)
3. [Example Configurations](#example-configurations)
4. [Path Resolution System](#path-resolution-system)
5. [Orchestration Script Design](#orchestration-script-design)
6. [Command Translation](#command-translation)
7. [Implementation Details](#implementation-details)
8. [Usage Examples](#usage-examples)
9. [Advanced Scenarios](#advanced-scenarios)

## Overview

### Purpose
The YAML-based user setup system provides maximum flexibility for configuring Shuttle users and permissions without hardcoded assumptions. It supports any combination of user types, permissions, and deployment scenarios while integrating seamlessly with the existing command infrastructure.

### Key Benefits
- **No Constraints**: Same user can perform multiple roles or users can be strictly separated
- **Environment Agnostic**: Works for development, testing, and production environments
- **Configuration Management Ready**: Version controlled, templatable configurations
- **Existing Command Integration**: Uses all existing script parameters without modifications

### Architecture
- **YAML Configuration**: Multi-document YAML defines users, groups, and permissions
- **Orchestration Script**: `2_configure_production.sh` reads config and calls existing scripts
- **Path Resolution**: Symbolic path names resolve to actual shuttle configuration paths
- **Command Translation**: YAML specifications translate to existing command parameters

## YAML Configuration Schema

### File Structure
**Location**: `/home/mathew/shuttle/config/shuttle_user_setup.yaml`
**Format**: Multi-document YAML with `---` separators

### Schema Definition

#### Document 1: Global Configuration
```yaml
---
version: "1.0"
metadata:
  description: "Shuttle user setup configuration"
  environment: "production"  # production|development|testing
  created: "2025-01-01"
  updated: "2025-01-01"

settings:
  create_home_directories: true
  backup_existing_users: true
  validate_before_apply: true
  dry_run: false

groups:
  <group_name>:
    description: "Group description"
    gid: <number>  # Optional - auto-assign if null
```

#### Document N: User Configuration
```yaml
---
type: "user"
user:
  name: "<username>"
  source: "local|domain|existing"
  account_type: "service|interactive"
  shell: "<shell_path>"
  home_directory: "<path>"
  create_home: true|false
  
  groups:
    primary: "<primary_group>"
    secondary: ["<group1>", "<group2>"]
  
  capabilities:
    executables: ["<executable1>", "<executable2>"]
  
  permissions:
    read_write:
      - path: "<symbolic_path_name>"
        mode: "<permissions>"
        recursive: true|false
    read_only:
      - path: "<symbolic_path_name>"
        mode: "<permissions>"
    no_access: ["<path1>", "<path2>"]
  
  samba:
    enabled: true|false
    password: "<password>"  # Optional - will prompt if not provided
```

### Field Definitions

#### User Fields
- **name**: Username (required)
- **source**: `local` (create new), `domain` (existing domain user), `existing` (existing local user)
- **account_type**: `service` (no shell) or `interactive` (shell access)
- **shell**: Shell path (e.g., `/usr/sbin/nologin`, `/bin/bash`)
- **home_directory**: Home directory path
- **create_home**: Whether to create home directory

#### Permission Fields
- **path**: Symbolic path name that resolves to actual shuttle paths
- **mode**: File permissions (octal or symbolic)
- **recursive**: Apply permissions recursively

#### Symbolic Path Names
- `source_path`: Shuttle source directory
- `destination_path`: Shuttle destination directory
- `quarantine_path`: Shuttle quarantine directory
- `log_path`: Shuttle log directory
- `hazard_archive_path`: Shuttle hazard archive directory
- `ledger_file_path`: Shuttle ledger file
- `hazard_encryption_key_path`: GPG public key file
- `shuttle_config_path`: Main shuttle configuration file
- `test_work_dir`: Test working directory
- `test_config_path`: Test configuration file

## Example Configurations

### Example 1: Single User Does Everything
**Scenario**: One domain service account handles all shuttle functions
**Use Case**: Simple deployment, minimal user management overhead

```yaml
# Single User Configuration
---
version: "1.0"
metadata:
  description: "Single user handles all shuttle functions"
  environment: "production"

settings:
  create_home_directories: true
  backup_existing_users: true

groups:
  shuttle_users:
    description: "All shuttle-related functionality"
  shuttle_config_readers:
    description: "Can read configuration files"

---
type: "user"
user:
  name: "shuttle_service"
  source: "domain"
  account_type: "service"
  shell: "/usr/sbin/nologin"
  home_directory: "/var/lib/shuttle"
  create_home: true
  
  groups:
    primary: "shuttle_users"
    secondary: ["shuttle_config_readers"]
  
  capabilities:
    executables: ["run-shuttle", "run-defender-test"]
  
  permissions:
    read_write:
      - path: "source_path"
        mode: "755"
        recursive: true
      - path: "destination_path"
        mode: "755"
        recursive: true
      - path: "quarantine_path"
        mode: "755"
        recursive: true
      - path: "log_path"
        mode: "755"
        recursive: true
      - path: "hazard_archive_path"
        mode: "755"
        recursive: true
      - path: "ledger_file_path"
        mode: "644"
      - path: "test_work_dir"
        mode: "755"
        recursive: true
    read_only:
      - path: "hazard_encryption_key_path"
        mode: "644"
      - path: "shuttle_config_path"
        mode: "644"
      - path: "test_config_path"
        mode: "644"
  
  samba:
    enabled: true
```

### Example 2: Strict User Separation
**Scenario**: Separate users for each function with minimal permissions
**Use Case**: High security environment, principle of least privilege

```yaml
# Strict Separation Configuration
---
version: "1.0"
metadata:
  description: "Strict separation of duties"
  environment: "production"

groups:
  shuttle_app_users:
    description: "Users who run shuttle application"
  shuttle_test_users:
    description: "Users who run defender tests"
  shuttle_samba_users:
    description: "Users who access via Samba"
  shuttle_config_readers:
    description: "Users who can read config files"
  shuttle_ledger_writers:
    description: "Users who can write to ledger"

---
type: "user"
user:
  name: "samba_service"
  source: "domain"
  account_type: "service"
  shell: "/usr/sbin/nologin"
  home_directory: "/var/lib/shuttle/samba"
  
  groups:
    primary: "shuttle_samba_users"
    secondary: ["shuttle_config_readers"]
  
  capabilities:
    executables: []
  
  permissions:
    read_write:
      - path: "source_path"
        mode: "755"
    read_only:
      - path: "shuttle_config_path"
        mode: "644"
  
  samba:
    enabled: true

---
type: "user"
user:
  name: "shuttle_app_service"
  source: "domain"
  account_type: "service"
  shell: "/usr/sbin/nologin"
  home_directory: "/var/lib/shuttle/app"
  
  groups:
    primary: "shuttle_app_users"
    secondary: ["shuttle_config_readers", "shuttle_ledger_writers"]
  
  capabilities:
    executables: ["run-shuttle"]
  
  permissions:
    read_write:
      - path: "source_path"
        mode: "755"
      - path: "destination_path"
        mode: "755"
      - path: "quarantine_path"
        mode: "755"
      - path: "log_path"
        mode: "755"
      - path: "hazard_archive_path"
        mode: "755"
      - path: "ledger_file_path"
        mode: "644"
    read_only:
      - path: "hazard_encryption_key_path"
        mode: "644"
      - path: "shuttle_config_path"
        mode: "644"

---
type: "user"
user:
  name: "defender_test_service"
  source: "local"
  account_type: "service"
  shell: "/usr/sbin/nologin"
  home_directory: "/var/lib/shuttle/test"
  
  groups:
    primary: "shuttle_test_users"
    secondary: ["shuttle_config_readers", "shuttle_ledger_writers"]
  
  capabilities:
    executables: ["run-defender-test"]
  
  permissions:
    read_write:
      - path: "test_work_dir"
        mode: "755"
        recursive: true
      - path: "ledger_file_path"
        mode: "644"
    read_only:
      - path: "hazard_encryption_key_path"
        mode: "644"
      - path: "shuttle_config_path"
        mode: "644"
      - path: "test_config_path"
        mode: "644"
```

### Example 3: Development Environment
**Scenario**: Interactive users for development and debugging
**Use Case**: Development environment with human users

```yaml
# Development Environment Configuration
---
version: "1.0"
metadata:
  description: "Development environment with interactive users"
  environment: "development"

groups:
  shuttle_developers:
    description: "Shuttle developers with full access"
  shuttle_testers:
    description: "Testers with limited access"

---
type: "user"
user:
  name: "dev_user"
  source: "local"
  account_type: "interactive"
  shell: "/bin/bash"
  home_directory: "/home/dev_user"
  create_home: true
  
  groups:
    primary: "shuttle_developers"
    secondary: []
  
  capabilities:
    executables: ["run-shuttle", "run-defender-test"]
  
  permissions:
    read_write:
      - path: "source_path"
        mode: "755"
        recursive: true
      - path: "destination_path"
        mode: "755"
        recursive: true
      - path: "quarantine_path"
        mode: "755"
        recursive: true
      - path: "log_path"
        mode: "755"
        recursive: true
      - path: "hazard_archive_path"
        mode: "755"
        recursive: true
      - path: "ledger_file_path"
        mode: "644"
      - path: "test_work_dir"
        mode: "755"
        recursive: true
      - path: "shuttle_config_path"
        mode: "644"
      - path: "test_config_path"
        mode: "644"
      - path: "hazard_encryption_key_path"
        mode: "644"
  
  samba:
    enabled: false

---
type: "user"
user:
  name: "test_user"
  source: "local"
  account_type: "interactive"
  shell: "/bin/bash"
  home_directory: "/home/test_user"
  
  groups:
    primary: "shuttle_testers"
    secondary: []
  
  capabilities:
    executables: ["run-defender-test"]
  
  permissions:
    read_write:
      - path: "test_work_dir"
        mode: "755"
        recursive: true
    read_only:
      - path: "shuttle_config_path"
        mode: "644"
      - path: "test_config_path"
        mode: "644"
      - path: "source_path"
        mode: "644"
      - path: "destination_path"
        mode: "644"
```

### Example 4: Mixed Local and Domain Users
**Scenario**: Combination of local and domain accounts
**Use Case**: Transition period or mixed environment

```yaml
# Mixed Environment Configuration
---
version: "1.0"
metadata:
  description: "Mixed local and domain users"
  environment: "production"

groups:
  shuttle_app_users:
    description: "Application users"
  shuttle_samba_users:
    description: "Samba users"
  shuttle_admin:
    description: "Administrative users"

---
type: "user"
user:
  name: "DOMAIN\\shuttle-app"
  source: "domain"
  account_type: "service"
  shell: "/usr/sbin/nologin"
  home_directory: "/var/lib/shuttle/app"
  
  groups:
    primary: "shuttle_app_users"
    secondary: []
  
  capabilities:
    executables: ["run-shuttle"]
  
  permissions:
    read_write:
      - path: "source_path"
        mode: "755"
      - path: "destination_path"
        mode: "755"
      - path: "quarantine_path"
        mode: "755"
      - path: "log_path"
        mode: "755"
      - path: "hazard_archive_path"
        mode: "755"
      - path: "ledger_file_path"
        mode: "644"
    read_only:
      - path: "shuttle_config_path"
        mode: "644"
      - path: "hazard_encryption_key_path"
        mode: "644"

---
type: "user"
user:
  name: "local_samba"
  source: "local"
  account_type: "service"
  shell: "/usr/sbin/nologin"
  home_directory: "/var/lib/shuttle/samba"
  
  groups:
    primary: "shuttle_samba_users"
    secondary: []
  
  capabilities:
    executables: []
  
  permissions:
    read_write:
      - path: "source_path"
        mode: "755"
    read_only:
      - path: "shuttle_config_path"
        mode: "644"
  
  samba:
    enabled: true

---
type: "user"
user:
  name: "admin_user"
  source: "existing"
  account_type: "interactive"
  # Shell and home not specified for existing users
  
  groups:
    primary: "shuttle_admin"
    secondary: ["shuttle_app_users"]
  
  capabilities:
    executables: ["run-shuttle", "run-defender-test"]
  
  permissions:
    read_write:
      - path: "shuttle_config_path"
        mode: "644"
      - path: "test_config_path"
        mode: "644"
```

## Path Resolution System

### Purpose
The path resolution system maps symbolic path names in the YAML configuration to actual file system paths defined in the shuttle configuration and environment variables.

### Path Mapping Table

| Symbolic Name | Environment Variable | Shuttle Config Section | Default Fallback |
|---------------|---------------------|----------------------|------------------|
| `source_path` | `SHUTTLE_CONFIG_SOURCE_PATH` | `[paths].source_path` | `/srv/shuttle/incoming` |
| `destination_path` | `SHUTTLE_CONFIG_DEST_PATH` | `[paths].destination_path` | `/srv/shuttle/processed` |
| `quarantine_path` | `SHUTTLE_CONFIG_QUARANTINE_PATH` | `[paths].quarantine_path` | `/tmp/shuttle/quarantine` |
| `log_path` | `SHUTTLE_CONFIG_LOG_PATH` | `[paths].log_path` | `/var/log/shuttle` |
| `hazard_archive_path` | `SHUTTLE_CONFIG_HAZARD_PATH` | `[paths].hazard_archive_path` | `/srv/shuttle/hazard` |
| `ledger_file_path` | `SHUTTLE_CONFIG_LEDGER_PATH` | `[paths].ledger_file_path` | `/etc/shuttle/ledger.yaml` |
| `hazard_encryption_key_path` | `SHUTTLE_CONFIG_KEY_PATH` | `[paths].hazard_encryption_key_path` | `/etc/shuttle/shuttle_public.gpg` |
| `shuttle_config_path` | `SHUTTLE_CONFIG_PATH` | N/A | `/etc/shuttle/config.conf` |
| `test_work_dir` | `SHUTTLE_TEST_WORK_DIR` | N/A | `/var/lib/shuttle/test` |
| `test_config_path` | `SHUTTLE_TEST_CONFIG_PATH` | N/A | `/etc/shuttle/test_config.conf` |

### Resolution Priority
1. **Environment Variable**: If set, use the environment variable value
2. **Shuttle Config File**: Parse the main shuttle config file for the path
3. **Default Fallback**: Use the default value if neither above are available

### Python Implementation
```python
import os
import configparser
from pathlib import Path

class PathResolver:
    """Resolves symbolic path names to actual file system paths"""
    
    def __init__(self, shuttle_config_path=None):
        self.shuttle_config_path = shuttle_config_path or os.environ.get('SHUTTLE_CONFIG_PATH')
        self.config = None
        self._load_shuttle_config()
    
    def _load_shuttle_config(self):
        """Load shuttle configuration file if available"""
        if self.shuttle_config_path and Path(self.shuttle_config_path).exists():
            self.config = configparser.ConfigParser()
            self.config.read(self.shuttle_config_path)
    
    def resolve_path(self, symbolic_name):
        """Resolve symbolic path name to actual path"""
        
        # Path mapping with environment variables, config keys, and defaults
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
            raise ValueError(f"Unknown symbolic path: {symbolic_name}")
        
        path_info = path_map[symbolic_name]
        
        # 1. Check environment variable
        if path_info['env'] and os.environ.get(path_info['env']):
            return os.environ[path_info['env']]
        
        # 2. Check shuttle config file
        if (path_info['config'] and self.config and 
            self.config.has_section(path_info['config'][0]) and
            self.config.has_option(path_info['config'][0], path_info['config'][1])):
            return self.config.get(path_info['config'][0], path_info['config'][1])
        
        # 3. Use default
        return path_info['default']
    
    def resolve_all_paths(self, path_list):
        """Resolve a list of symbolic paths"""
        return {path: self.resolve_path(path) for path in path_list}
```

## Orchestration Script Design

### Script Location and Purpose
**File**: `/home/mathew/shuttle/scripts/2_configure_production.sh`
**Purpose**: Main orchestrator that reads YAML config and calls existing scripts with appropriate parameters

### Complete Script Implementation

```bash
#!/bin/bash
# 2_configure_production.sh - Production environment configuration orchestrator
# Reads YAML configuration and calls existing scripts with appropriate parameters

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

# Default configuration file location
DEFAULT_CONFIG="$PROJECT_ROOT/config/shuttle_user_setup.yaml"
CONFIG_FILE=""
INTERACTIVE_MODE=true
DRY_RUN=false

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
                echo -e "${RED}Unknown option: $1${NC}"
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
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo -e "${RED}❌ Configuration file not found: $CONFIG_FILE${NC}"
        exit 1
    fi
    
    # Basic YAML validation using Python
    if ! python3 -c "import yaml; yaml.safe_load_all(open('$CONFIG_FILE'))" 2>/dev/null; then
        echo -e "${RED}❌ Invalid YAML configuration file${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Configuration file validated: $CONFIG_FILE${NC}"
}

# Interactive mode configuration
interactive_setup() {
    if [[ "$INTERACTIVE_MODE" != "true" ]]; then
        return 0
    fi
    
    echo "========================================="
    echo "    Production Environment Setup        "
    echo "========================================="
    echo ""
    echo "Configuration file: $CONFIG_FILE"
    echo ""
    
    # Show configuration summary
    echo "Configuration Summary:"
    python3 << EOF
import yaml
with open('$CONFIG_FILE', 'r') as f:
    docs = list(yaml.safe_load_all(f))

users = []
groups = {}
for doc in docs:
    if doc.get('type') == 'user':
        users.append(doc['user'])
    elif 'groups' in doc:
        groups = doc['groups']

print(f"  Groups to create: {len(groups)}")
print(f"  Users to configure: {len(users)}")
for user in users:
    print(f"    - {user['name']} ({user['source']}, {user['account_type']})")
EOF
    
    echo ""
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
    echo -e "${BLUE}📦 Phase 1: Installing system tools${NC}"
    
    local cmd="$PRODUCTION_DIR/11_install_tools.sh"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would execute: $cmd"
    else
        if ! "$cmd"; then
            echo -e "${RED}❌ Failed to install system tools${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ System tools installation complete${NC}"
    fi
}

# Phase 2: Configure users and groups
phase_configure_users() {
    echo ""
    echo -e "${BLUE}👥 Phase 2: Configuring users and groups${NC}"
    
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
    cmd_str = " ".join(cmd_list)
    if dry_run:
        print(f"[DRY RUN] {description}: {cmd_str}")
        return True
    else:
        print(f"Executing: {description}")
        try:
            result = subprocess.run(cmd_list, check=True, capture_output=True, text=True)
            print(f"✅ {description} completed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} failed: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
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
    if doc.get('type') == 'user':
        users.append(doc['user'])
    elif 'groups' in doc:
        groups = doc.get('groups', {})
        settings = doc.get('settings', {})

# Create groups first
print("Creating groups...")
for group_name, group_info in groups.items():
    cmd = [f"{production_dir}/12_users_and_groups.sh", "add-group", "--group", group_name]
    if not run_command(cmd, f"Create group {group_name}"):
        sys.exit(1)

# Process users
print("Processing users...")
for user in users:
    user_name = user['name']
    
    # Create user if source is 'local'
    if user['source'] == 'local':
        cmd = [f"{production_dir}/12_users_and_groups.sh", "add-user", "--user", user_name]
        
        if 'shell' in user:
            cmd.extend(["--shell", user['shell']])
        if 'home_directory' in user:
            cmd.extend(["--home", user['home_directory']])
        if user.get('create_home', False):
            cmd.append("--create-home")
        
        if not run_command(cmd, f"Create user {user_name}"):
            sys.exit(1)
    
    # Add user to groups
    groups_config = user.get('groups', {})
    
    # Set primary group if specified
    if 'primary' in groups_config:
        cmd = [f"{production_dir}/12_users_and_groups.sh", "add-user-to-group", 
               "--user", user_name, "--group", groups_config['primary']]
        if user['source'] == 'domain':
            cmd.append("--domain")
        if not run_command(cmd, f"Add {user_name} to primary group {groups_config['primary']}"):
            sys.exit(1)
    
    # Add to secondary groups
    for group in groups_config.get('secondary', []):
        cmd = [f"{production_dir}/12_users_and_groups.sh", "add-user-to-group", 
               "--user", user_name, "--group", group]
        if user['source'] == 'domain':
            cmd.append("--domain")
        if not run_command(cmd, f"Add {user_name} to secondary group {group}"):
            sys.exit(1)

print("Users and groups configuration complete")
EOF

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
        config = configparser.ConfigParser()
        config.read(shuttle_config_path)
    
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
    cmd_str = " ".join(cmd_list)
    if dry_run:
        print(f"[DRY RUN] {description}: {cmd_str}")
        return True
    else:
        print(f"Executing: {description}")
        try:
            result = subprocess.run(cmd_list, check=True, capture_output=True, text=True)
            print(f"✅ {description} completed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} failed: {e}")
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
    if doc.get('type') == 'user':
        users.append(doc['user'])

# Set permissions for each user
print("Setting file permissions...")
for user in users:
    user_name = user['name']
    permissions = user.get('permissions', {})
    
    # Handle read-write permissions
    for perm in permissions.get('read_write', []):
        actual_path = resolve_path(perm['path'])
        mode = perm.get('mode', '755')
        
        cmd = [f"{production_dir}/12_users_and_groups.sh", "set-path-permissions", 
               "--path", actual_path, "--mode", mode]
        
        if perm.get('recursive', False):
            cmd.append("--recursive")
        
        if not run_command(cmd, f"Set {mode} permissions on {actual_path}"):
            print(f"Warning: Failed to set permissions on {actual_path}")
    
    # Handle read-only permissions
    for perm in permissions.get('read_only', []):
        actual_path = resolve_path(perm['path'])
        mode = perm.get('mode', '644')
        
        cmd = [f"{production_dir}/12_users_and_groups.sh", "set-path-permissions", 
               "--path", actual_path, "--mode", mode]
        
        if not run_command(cmd, f"Set {mode} permissions on {actual_path}"):
            print(f"Warning: Failed to set permissions on {actual_path}")

print("File permissions configuration complete")
EOF

    if [[ $? -ne 0 ]]; then
        echo -e "${YELLOW}⚠️  Some permission settings may have failed${NC}"
    else
        echo -e "${GREEN}✅ File permissions configuration complete${NC}"
    fi
}

# Phase 4: Configure Samba
phase_configure_samba() {
    echo ""
    echo -e "${BLUE}🌐 Phase 4: Configuring Samba${NC}"
    
    # Extract Samba users from configuration
    python3 << EOF
import yaml
import subprocess
import sys

dry_run = "$DRY_RUN" == "true"
production_dir = "$PRODUCTION_DIR"

def run_command(cmd_list, description):
    """Execute command or show what would be executed in dry run"""
    cmd_str = " ".join(cmd_list)
    if dry_run:
        print(f"[DRY RUN] {description}: {cmd_str}")
        return True
    else:
        print(f"Executing: {description}")
        try:
            result = subprocess.run(cmd_list, check=True, capture_output=True, text=True)
            print(f"✅ {description} completed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} failed: {e}")
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
    if doc.get('type') == 'user':
        user = doc['user']
        if user.get('samba', {}).get('enabled', False):
            samba_users.append(user)

if not samba_users:
    print("No Samba users configured")
    sys.exit(0)

print(f"Configuring {len(samba_users)} Samba users...")
for user in samba_users:
    user_name = user['name']
    
    # Add Samba user
    cmd = [f"{production_dir}/13_configure_samba.sh", "add-samba-user", "--user", user_name]
    if user['source'] == 'domain':
        cmd.append("--domain")
    
    if not run_command(cmd, f"Add Samba user {user_name}"):
        print(f"Warning: Failed to add Samba user {user_name}")
        continue
    
    # Set Samba password if provided
    samba_config = user.get('samba', {})
    if 'password' in samba_config:
        cmd = [f"{production_dir}/13_configure_samba.sh", "set-samba-password", 
               "--user", user_name, "--password", samba_config['password']]
        if not run_command(cmd, f"Set Samba password for {user_name}"):
            print(f"Warning: Failed to set Samba password for {user_name}")

print("Samba configuration complete")
EOF

    if [[ $? -ne 0 ]]; then
        echo -e "${YELLOW}⚠️  Some Samba configuration may have failed${NC}"
    else
        echo -e "${GREEN}✅ Samba configuration complete${NC}"
    fi
}

# Phase 5: Configure firewall
phase_configure_firewall() {
    echo ""
    echo -e "${BLUE}🔥 Phase 5: Configuring firewall${NC}"
    
    local cmd="$PRODUCTION_DIR/14_configure_firewall.sh show-status"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would execute: $cmd"
    else
        if ! "$PRODUCTION_DIR/14_configure_firewall.sh" show-status; then
            echo -e "${YELLOW}⚠️  Firewall configuration check failed${NC}"
        else
            echo -e "${GREEN}✅ Firewall configuration complete${NC}"
        fi
    fi
}

# Main execution function
main() {
    echo -e "${GREEN}Starting production environment configuration...${NC}"
    
    # Parse command line arguments
    parse_arguments "$@"
    
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
    
    echo ""
    echo -e "${GREEN}🎉 Production environment configuration complete!${NC}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo ""
        echo -e "${YELLOW}This was a dry run. No changes were made.${NC}"
        echo "Run without --dry-run to apply the configuration."
    fi
}

# Run main function with all arguments
main "$@"
```

## Command Translation

### How YAML Translates to Commands

The orchestration script reads the YAML configuration and translates it into specific command calls to existing scripts. Here are the translation patterns:

#### Group Creation
**YAML:**
```yaml
groups:
  shuttle_app_users:
    description: "Users who run shuttle application"
```

**Command:**
```bash
./12_users_and_groups.sh add-group --group shuttle_app_users
```

#### User Creation (Local)
**YAML:**
```yaml
user:
  name: "shuttle_service"
  source: "local"
  shell: "/usr/sbin/nologin"
  home_directory: "/var/lib/shuttle"
  create_home: true
```

**Commands:**
```bash
./12_users_and_groups.sh add-user --user shuttle_service --shell /usr/sbin/nologin --home /var/lib/shuttle --create-home
```

#### User Creation (Domain)
**YAML:**
```yaml
user:
  name: "DOMAIN\\shuttle-service"
  source: "domain"
```

**Commands:**
```bash
# Domain users are not created, only added to groups
./12_users_and_groups.sh add-user-to-group --user "DOMAIN\\shuttle-service" --group shuttle_app_users --domain
```

#### Group Membership
**YAML:**
```yaml
groups:
  primary: "shuttle_app_users"
  secondary: ["shuttle_config_readers", "shuttle_ledger_writers"]
```

**Commands:**
```bash
./12_users_and_groups.sh add-user-to-group --user shuttle_service --group shuttle_app_users
./12_users_and_groups.sh add-user-to-group --user shuttle_service --group shuttle_config_readers
./12_users_and_groups.sh add-user-to-group --user shuttle_service --group shuttle_ledger_writers
```

#### File Permissions
**YAML:**
```yaml
permissions:
  read_write:
    - path: "source_path"
      mode: "755"
      recursive: true
  read_only:
    - path: "shuttle_config_path"
      mode: "644"
```

**Commands:**
```bash
# source_path resolves to actual path from shuttle config
./12_users_and_groups.sh set-path-permissions --path /srv/shuttle/incoming --mode 755 --recursive
./12_users_and_groups.sh set-path-permissions --path /etc/shuttle/config.conf --mode 644
```

#### Samba Configuration
**YAML:**
```yaml
samba:
  enabled: true
  password: "secure_password"
```

**Commands:**
```bash
./13_configure_samba.sh add-samba-user --user shuttle_service
./13_configure_samba.sh set-samba-password --user shuttle_service --password secure_password
```

### Complete Translation Example

Given this YAML configuration:
```yaml
---
type: "user"
user:
  name: "shuttle_service"
  source: "local"
  account_type: "service"
  shell: "/usr/sbin/nologin"
  home_directory: "/var/lib/shuttle"
  create_home: true
  
  groups:
    primary: "shuttle_app_users"
    secondary: ["shuttle_config_readers"]
  
  permissions:
    read_write:
      - path: "source_path"
        mode: "755"
    read_only:
      - path: "shuttle_config_path"
        mode: "644"
  
  samba:
    enabled: true
```

The orchestrator generates these commands:
```bash
# Create user
./12_users_and_groups.sh add-user --user shuttle_service --shell /usr/sbin/nologin --home /var/lib/shuttle --create-home

# Add to groups
./12_users_and_groups.sh add-user-to-group --user shuttle_service --group shuttle_app_users
./12_users_and_groups.sh add-user-to-group --user shuttle_service --group shuttle_config_readers

# Set permissions (paths resolved from shuttle config)
./12_users_and_groups.sh set-path-permissions --path /srv/shuttle/incoming --mode 755
./12_users_and_groups.sh set-path-permissions --path /etc/shuttle/config.conf --mode 644

# Configure Samba
./13_configure_samba.sh add-samba-user --user shuttle_service
```

## Implementation Details

### Complete Python YAML Parser

```python
#!/usr/bin/env python3
"""
YAML User Setup Configuration Parser
Parses multi-document YAML configuration and orchestrates user setup
"""

import yaml
import subprocess
import sys
import os
import configparser
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

class PathResolver:
    """Resolves symbolic path names to actual file system paths"""
    
    def __init__(self, shuttle_config_path: Optional[str] = None):
        self.shuttle_config_path = shuttle_config_path or os.environ.get('SHUTTLE_CONFIG_PATH')
        self.config = None
        self._load_shuttle_config()
    
    def _load_shuttle_config(self):
        """Load shuttle configuration file if available"""
        if self.shuttle_config_path and Path(self.shuttle_config_path).exists():
            self.config = configparser.ConfigParser()
            self.config.read(self.shuttle_config_path)
    
    def resolve_path(self, symbolic_name: str) -> str:
        """Resolve symbolic path name to actual path"""
        
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
        
        # Return as-is if not a symbolic path
        if symbolic_name not in path_map:
            return symbolic_name
        
        path_info = path_map[symbolic_name]
        
        # 1. Check environment variable
        if path_info['env'] and os.environ.get(path_info['env']):
            return os.environ[path_info['env']]
        
        # 2. Check shuttle config file
        if (path_info['config'] and self.config and 
            self.config.has_section(path_info['config'][0]) and
            self.config.has_option(path_info['config'][0], path_info['config'][1])):
            return self.config.get(path_info['config'][0], path_info['config'][1])
        
        # 3. Use default
        return path_info['default']

class UserSetupOrchestrator:
    """Orchestrates user setup based on YAML configuration"""
    
    def __init__(self, config_file: str, production_dir: str, dry_run: bool = False):
        self.config_file = config_file
        self.production_dir = production_dir
        self.dry_run = dry_run
        self.path_resolver = PathResolver()
        
        # Load and parse configuration
        self.groups = {}
        self.users = []
        self.settings = {}
        self._load_configuration()
    
    def _load_configuration(self):
        """Load and parse YAML configuration"""
        try:
            with open(self.config_file, 'r') as f:
                docs = list(yaml.safe_load_all(f))
        except Exception as e:
            raise RuntimeError(f"Error reading configuration: {e}")
        
        for doc in docs:
            if doc is None:
                continue
                
            if doc.get('type') == 'user':
                self.users.append(doc['user'])
            elif 'groups' in doc:
                self.groups = doc.get('groups', {})
                self.settings = doc.get('settings', {})
    
    def _run_command(self, cmd_list: List[str], description: str) -> bool:
        """Execute command or show what would be executed in dry run"""
        cmd_str = " ".join(cmd_list)
        
        if self.dry_run:
            print(f"[DRY RUN] {description}: {cmd_str}")
            return True
        else:
            print(f"Executing: {description}")
            try:
                result = subprocess.run(cmd_list, check=True, capture_output=True, text=True)
                print(f"✅ {description} completed")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ {description} failed: {e}")
                if e.stdout:
                    print(f"stdout: {e.stdout}")
                if e.stderr:
                    print(f"stderr: {e.stderr}")
                return False
    
    def create_groups(self) -> bool:
        """Create all groups defined in configuration"""
        print("Creating groups...")
        
        for group_name, group_info in self.groups.items():
            cmd = [f"{self.production_dir}/12_users_and_groups.sh", "add-group", "--group", group_name]
            
            if not self._run_command(cmd, f"Create group {group_name}"):
                return False
        
        return True
    
    def create_users(self) -> bool:
        """Create users and configure group memberships"""
        print("Processing users...")
        
        for user in self.users:
            user_name = user['name']
            
            # Create user if source is 'local'
            if user['source'] == 'local':
                if not self._create_local_user(user):
                    return False
            
            # Configure group memberships
            if not self._configure_user_groups(user):
                return False
        
        return True
    
    def _create_local_user(self, user: Dict[str, Any]) -> bool:
        """Create a local user"""
        user_name = user['name']
        cmd = [f"{self.production_dir}/12_users_and_groups.sh", "add-user", "--user", user_name]
        
        if 'shell' in user:
            cmd.extend(["--shell", user['shell']])
        if 'home_directory' in user:
            cmd.extend(["--home", user['home_directory']])
        if user.get('create_home', False):
            cmd.append("--create-home")
        
        return self._run_command(cmd, f"Create user {user_name}")
    
    def _configure_user_groups(self, user: Dict[str, Any]) -> bool:
        """Configure user group memberships"""
        user_name = user['name']
        groups_config = user.get('groups', {})
        
        # Set primary group if specified
        if 'primary' in groups_config:
            cmd = [f"{self.production_dir}/12_users_and_groups.sh", "add-user-to-group", 
                   "--user", user_name, "--group", groups_config['primary']]
            if user['source'] == 'domain':
                cmd.append("--domain")
            
            if not self._run_command(cmd, f"Add {user_name} to primary group {groups_config['primary']}"):
                return False
        
        # Add to secondary groups
        for group in groups_config.get('secondary', []):
            cmd = [f"{self.production_dir}/12_users_and_groups.sh", "add-user-to-group", 
                   "--user", user_name, "--group", group]
            if user['source'] == 'domain':
                cmd.append("--domain")
            
            if not self._run_command(cmd, f"Add {user_name} to secondary group {group}"):
                print(f"Warning: Failed to add {user_name} to group {group}")
        
        return True
    
    def set_permissions(self) -> bool:
        """Set file permissions for all users"""
        print("Setting file permissions...")
        
        for user in self.users:
            user_name = user['name']
            permissions = user.get('permissions', {})
            
            # Handle read-write permissions
            for perm in permissions.get('read_write', []):
                if not self._set_permission(perm, 'read-write'):
                    print(f"Warning: Failed to set read-write permission for {user_name}")
            
            # Handle read-only permissions
            for perm in permissions.get('read_only', []):
                if not self._set_permission(perm, 'read-only'):
                    print(f"Warning: Failed to set read-only permission for {user_name}")
        
        return True
    
    def _set_permission(self, perm: Dict[str, Any], perm_type: str) -> bool:
        """Set a specific permission"""
        actual_path = self.path_resolver.resolve_path(perm['path'])
        mode = perm.get('mode', '755' if perm_type == 'read-write' else '644')
        
        cmd = [f"{self.production_dir}/12_users_and_groups.sh", "set-path-permissions", 
               "--path", actual_path, "--mode", mode]
        
        if perm.get('recursive', False):
            cmd.append("--recursive")
        
        return self._run_command(cmd, f"Set {mode} permissions on {actual_path}")
    
    def configure_samba(self) -> bool:
        """Configure Samba for users that have it enabled"""
        print("Configuring Samba...")
        
        samba_users = [user for user in self.users if user.get('samba', {}).get('enabled', False)]
        
        if not samba_users:
            print("No Samba users configured")
            return True
        
        print(f"Configuring {len(samba_users)} Samba users...")
        for user in samba_users:
            user_name = user['name']
            
            # Add Samba user
            cmd = [f"{self.production_dir}/13_configure_samba.sh", "add-samba-user", "--user", user_name]
            if user['source'] == 'domain':
                cmd.append("--domain")
            
            if not self._run_command(cmd, f"Add Samba user {user_name}"):
                print(f"Warning: Failed to add Samba user {user_name}")
                continue
            
            # Set Samba password if provided
            samba_config = user.get('samba', {})
            if 'password' in samba_config:
                cmd = [f"{self.production_dir}/13_configure_samba.sh", "set-samba-password", 
                       "--user", user_name, "--password", samba_config['password']]
                if not self._run_command(cmd, f"Set Samba password for {user_name}"):
                    print(f"Warning: Failed to set Samba password for {user_name}")
        
        return True
    
    def run_orchestration(self) -> bool:
        """Run the complete orchestration process"""
        print(f"Starting user setup orchestration from {self.config_file}")
        print(f"Groups to create: {len(self.groups)}")
        print(f"Users to configure: {len(self.users)}")
        
        if self.dry_run:
            print("DRY RUN MODE - No changes will be made")
        
        print()
        
        # Execute phases
        if not self.create_groups():
            print("❌ Failed to create groups")
            return False
        
        if not self.create_users():
            print("❌ Failed to create users")
            return False
        
        if not self.set_permissions():
            print("❌ Failed to set permissions")
            return False
        
        if not self.configure_samba():
            print("❌ Failed to configure Samba")
            return False
        
        print("✅ User setup orchestration completed successfully")
        return True

def main():
    """Main entry point for standalone execution"""
    parser = argparse.ArgumentParser(description='YAML User Setup Orchestrator')
    parser.add_argument('config_file', help='Path to YAML configuration file')
    parser.add_argument('--production-dir', required=True, help='Path to production scripts directory')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    try:
        orchestrator = UserSetupOrchestrator(args.config_file, args.production_dir, args.dry_run)
        success = orchestrator.run_orchestration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

## Usage Examples

### Interactive Mode (Default)
```bash
# Use default configuration file
./2_configure_production.sh

# Use custom configuration file
./2_configure_production.sh --config /path/to/my_config.yaml
```

### Automated Mode
```bash
# Non-interactive mode for automation
./2_configure_production.sh --config config.yaml --non-interactive

# Dry run to see what would be done
./2_configure_production.sh --dry-run

# Combined: automated dry run
./2_configure_production.sh --config config.yaml --non-interactive --dry-run
```

### Validation Only
```bash
# Just validate the configuration file
python3 -c "
import yaml
try:
    with open('config.yaml', 'r') as f:
        docs = list(yaml.safe_load_all(f))
    print('✅ Configuration is valid')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"
```

### Configuration Summary
```bash
# Show what would be configured
python3 << 'EOF'
import yaml
with open('shuttle_user_setup.yaml', 'r') as f:
    docs = list(yaml.safe_load_all(f))

users = []
groups = {}
for doc in docs:
    if doc.get('type') == 'user':
        users.append(doc['user'])
    elif 'groups' in doc:
        groups = doc['groups']

print(f"Groups to create: {len(groups)}")
for group_name, group_info in groups.items():
    print(f"  - {group_name}: {group_info.get('description', 'No description')}")

print(f"\nUsers to configure: {len(users)}")
for user in users:
    caps = user.get('capabilities', {}).get('executables', [])
    caps_str = ', '.join(caps) if caps else 'None'
    print(f"  - {user['name']} ({user['source']}, {user['account_type']}) - Capabilities: {caps_str}")
EOF
```

## Advanced Scenarios

### Scenario 1: Multi-Environment Deployment

Create environment-specific configuration files:

**production.yaml:**
```yaml
---
version: "1.0"
metadata:
  environment: "production"

groups:
  shuttle_app_users:
    description: "Production shuttle users"

---
type: "user"
user:
  name: "DOMAIN\\shuttle-prod"
  source: "domain"
  account_type: "service"
  shell: "/usr/sbin/nologin"
  
  groups:
    primary: "shuttle_app_users"
  
  capabilities:
    executables: ["run-shuttle"]
  
  permissions:
    read_write:
      - path: "source_path"
      - path: "destination_path"
```

**development.yaml:**
```yaml
---
version: "1.0"
metadata:
  environment: "development"

groups:
  shuttle_developers:
    description: "Development users"

---
type: "user"
user:
  name: "dev_user"
  source: "local"
  account_type: "interactive"
  shell: "/bin/bash"
  
  groups:
    primary: "shuttle_developers"
  
  capabilities:
    executables: ["run-shuttle", "run-defender-test"]
  
  permissions:
    read_write:
      - path: "source_path"
      - path: "test_work_dir"
```

**Usage:**
```bash
# Deploy to production
./2_configure_production.sh --config production.yaml --non-interactive

# Deploy to development
./2_configure_production.sh --config development.yaml
```

### Scenario 2: Configuration Templating

Use environment variables in YAML configurations:

**template.yaml:**
```yaml
---
version: "1.0"
metadata:
  environment: "${DEPLOY_ENV}"

groups:
  shuttle_users:
    description: "Shuttle users for ${DEPLOY_ENV}"

---
type: "user"
user:
  name: "${SHUTTLE_USER_NAME}"
  source: "${SHUTTLE_USER_SOURCE}"
  account_type: "service"
  
  groups:
    primary: "shuttle_users"
  
  capabilities:
    executables: ["run-shuttle"]
```

**Usage:**
```bash
# Set environment variables
export DEPLOY_ENV="production"
export SHUTTLE_USER_NAME="DOMAIN\\shuttle-prod"
export SHUTTLE_USER_SOURCE="domain"

# Expand template and deploy
envsubst < template.yaml > expanded_config.yaml
./2_configure_production.sh --config expanded_config.yaml --non-interactive
```

### Scenario 3: Custom Permission Structures

Complex permission configurations with ACLs:

```yaml
---
type: "user"
user:
  name: "shuttle_service"
  source: "local"
  
  permissions:
    read_write:
      - path: "source_path"
        mode: "755"
        recursive: true
      - path: "destination_path"
        mode: "755"
        recursive: true
    read_only:
      - path: "shuttle_config_path"
        mode: "644"
    custom:
      - command: "set-acl"
        path: "log_path"
        acl: "user:shuttle_service:rw-"
      - command: "set-path-owner"
        path: "quarantine_path"
        owner: "shuttle_service"
        group: "shuttle_users"
```

### Scenario 4: Rollback Configuration

Create rollback configurations:

**rollback.yaml:**
```yaml
---
version: "1.0"
metadata:
  description: "Rollback user configuration"
  action: "remove"

users_to_remove:
  - "shuttle_service"
  - "samba_service"

groups_to_remove:
  - "shuttle_app_users"
  - "shuttle_samba_users"

paths_to_reset:
  - path: "source_path"
    mode: "755"
    owner: "root"
    group: "root"
```

This comprehensive system provides maximum flexibility for user setup while maintaining integration with existing command infrastructure and following established patterns from the installation script.