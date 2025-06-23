# Shuttle Post-Install Configuration Flow Diagram

This document describes the complete post-install configuration flow for Shuttle, including both wizard and YAML instruction file modes.

## Overall Flow

```
scripts/2_post_install_config.sh [--wizard|--instructions <file>|--help]
├── parse_arguments()
│   ├── --wizard → RUN_WIZARD=true
│   ├── --instructions <file> → CONFIG_FILE=<file>
│   ├── --interactive/--non-interactive → Override YAML setting
│   ├── --dry-run → DRY_RUN=true
│   ├── --verbose → VERBOSE=true
│   └── --help → show_usage() → exit
│
├── main()
│   ├── Wizard Phase (if --wizard or no --instructions)
│   │   └── run_configuration_wizard()
│   │       ├── cd config/
│   │       ├── python3 -m post_install_config_wizard [options]
│   │       ├── Handle exit codes: 0=continue, 2=saved+exit, 3=cancelled
│   │       └── Set CONFIG_FILE to generated YAML
│   │
│   ├── Prerequisites Check
│   │   ├── check_prerequisites()
│   │   │   ├── Check Python 3 availability
│   │   │   ├── Check PyYAML library
│   │   │   ├── Validate production scripts directory
│   │   │   ├── Check required scripts (11-14)
│   │   │   └── Verify root/sudo privileges
│   │   └── validate_config() → Basic YAML syntax validation
│   │
│   ├── Configuration Analysis
│   │   ├── read_interactive_mode_settings() → Parse YAML for mode settings
│   │   └── interactive_setup() → Show config summary and confirm
│   │
│   └── Configuration Phases (Execute in Sequence)
│       ├── Phase 1: Install Tools
│       ├── Phase 2: Configure Users & Groups
│       ├── Phase 3: Set File Permissions
│       ├── Phase 4: Configure Samba
│       └── Phase 5: Configure Firewall
```

---

## Configuration Wizard Flow

### Wizard Mode (Create YAML Configuration):
```
run_configuration_wizard()
├── cd config/
├── Build wizard arguments from environment variables:
│   ├── --shuttle-config-path (if SHUTTLE_CONFIG_PATH set)
│   ├── --test-work-dir (if SHUTTLE_TEST_WORK_DIR set)
│   └── --test-config-path (if SHUTTLE_TEST_CONFIG_PATH set)
├── python3 -m post_install_config_wizard [args]
├── Handle wizard exit codes:
│   ├── 0 → Success, continue with configuration
│   ├── 2 → Config saved, user chose to exit
│   ├── 3 → User cancelled wizard
│   └── Other → Wizard failed
├── Determine CONFIG_FILE from:
│   ├── /tmp/wizard_config_filename (preferred)
│   └── Latest post_install_config_steps*.yaml file
└── Show saved config usage instructions
```

### Wizard Features:
- Reads existing shuttle configuration to extract actual paths
- Supports multiple environment profiles (development, testing, production)
- Interactive user input with validation
- Generates multi-document YAML with global settings and user definitions
- Provides symbolic path resolution for shuttle directories

---

## Configuration File Structure

### Multi-Document YAML Format:
```yaml
# Document 1: Global Settings
version: '1.0'
metadata:
  description: "Shuttle Production Environment Configuration"
  environment: "production"
  created: "2025-01-18 15:30:00"
  generated_by: "Configuration Wizard"

settings:
  create_home_directories: true
  backup_existing_users: true
  validate_before_apply: true
  interactive_mode: "interactive|non-interactive|mixed"
  dry_run_default: false

groups:
  shuttle_users:
    description: "Users who can run shuttle applications"
    gid: 1001
  shuttle_admins:
    description: "Administrators for shuttle system"

components:
  install_samba: true
  install_acl: true
  configure_users_groups: true
  configure_samba: true
  configure_firewall: true

---
# Document N: User Definition
type: user
user:
  name: "shuttle_service"
  source: "local"
  account_type: "service"
  groups:
    primary: "shuttle_users"
    secondary: ["shuttle_admins"]
  capabilities:
    executables: ["run-shuttle", "run-shuttle-defender-test"]
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
    no_access:
      - path: "hazard_archive_path"
  samba:
    enabled: true
    auth_method: "smbpasswd"
```

---

## Configuration Phase Execution

### Phase 1: Install System Tools
```
phase_install_tools()
├── Check component enablement: install_acl, install_samba
├── Build flags: --no-acl, --no-samba (if disabled)
└── execute_or_execute_dryrun("11_install_tools.sh [flags]")
    ├── Install Samba/Winbind packages (if enabled)
    ├── Install ACL utilities (if enabled)
    └── Validate tool installation and versions
```

### Phase 2: Configure Users and Groups
```
phase_configure_users()
├── Check component enablement: configure_users_groups
├── Skip if disabled → print warning and return
├── Build Python module arguments:
│   ├── --dry-run (if DRY_RUN=true)
│   └── --shuttle-config-path (if SHUTTLE_CONFIG_PATH set)
└── python3 -m user_group_manager CONFIG_FILE PRODUCTION_DIR [args]
    ├── Parse multi-document YAML configuration
    ├── Extract global settings and user definitions
    ├── Process groups:
    │   ├── Create system groups with optional GIDs
    │   └── Validate group creation success
    ├── Process users by source type:
    │   ├── local → Call 12_users_and_groups.sh create-user
    │   ├── domain → Validate domain user exists
    │   └── existing → Validate existing user
    ├── Configure group memberships:
    │   ├── Set primary group membership
    │   └── Add to secondary groups
    ├── Set user capabilities:
    │   └── Grant executable access (run-shuttle, etc.)
    └── Apply user-specific permissions via permission_manager
```

### Phase 3: Set File Permissions
```
phase_set_permissions()
├── Build Python module arguments:
│   └── --dry-run (if DRY_RUN=true)
└── python3 -m permission_manager CONFIG_FILE PRODUCTION_DIR [args]
    ├── Parse YAML user definitions
    ├── Resolve symbolic paths to actual filesystem paths:
    │   ├── source_path → /path/to/source
    │   ├── destination_path → /path/to/destination
    │   ├── quarantine_path → /path/to/quarantine
    │   ├── log_path → /path/to/logs
    │   ├── hazard_archive_path → /path/to/hazard
    │   ├── ledger_file_path → /path/to/ledger.yaml
    │   ├── hazard_encryption_key_path → /path/to/key.gpg
    │   ├── shuttle_config_path → /path/to/config.conf
    │   ├── test_work_dir → /path/to/test_area
    │   └── test_config_path → /path/to/test_config.conf
    ├── Apply permission sets per user:
    │   ├── read_write → Full access with specified mode
    │   ├── read_only → Read access only
    │   └── no_access → Remove all access
    └── Use shell scripts for actual permission changes
```

### Phase 4: Configure Samba
```
phase_configure_samba()
├── Check component enablement: configure_samba
├── Skip if disabled → print warning and return
├── Build Python module arguments:
│   ├── --dry-run (if DRY_RUN=true)
│   └── --non-interactive (if INTERACTIVE_MODE=false)
└── python3 -m samba_manager CONFIG_FILE PRODUCTION_DIR [args]
    ├── Parse users with samba.enabled=true
    ├── For each Samba user:
    │   ├── Validate user exists in system
    │   ├── Configure authentication method:
    │   │   └── smbpasswd → Set/update Samba password
    │   └── Configure shares and access permissions
    └── Test Samba configuration validity
```

### Phase 5: Configure Firewall
```
phase_configure_firewall()
├── Check component enablement: configure_firewall  
├── Skip if disabled → print warning and return
└── execute_or_execute_dryrun("14_configure_firewall.sh show-status")
    ├── Display current firewall status
    ├── Check for required port access
    ├── Show configuration recommendations
    └── Provide manual configuration guidance
```

---

## Python Module Architecture

### Core Configuration Modules

#### post_install_config_wizard.py
- **Purpose**: Interactive YAML configuration generation
- **Features**: 
  - Reads shuttle config to extract actual paths
  - Multi-environment support (dev/test/prod)
  - User input validation and guidance
  - Generates complete multi-document YAML

#### config_analyzer.py  
- **Purpose**: YAML configuration parsing and validation
- **Features**:
  - Multi-document YAML parsing
  - Configuration summary generation
  - Settings and user extraction
  - Validation and error reporting

#### user_group_manager.py
- **Purpose**: User and group management orchestration
- **Features**:
  - YAML parsing for user definitions
  - Group creation with optional GIDs
  - User processing by source type (local/domain/existing)
  - Group membership management
  - Capability assignment (executable access)

#### permission_manager.py
- **Purpose**: File and directory permission management
- **Features**:
  - Symbolic path resolution to actual paths
  - Permission set application (read-write/read-only/no-access)
  - Recursive permission handling
  - Integration with shell permission scripts

#### samba_manager.py
- **Purpose**: Samba user and share configuration
- **Features**:
  - Samba user account management
  - Authentication method configuration
  - Interactive vs non-interactive modes
  - Share configuration and testing

#### path_resolver.py
- **Purpose**: Symbolic path to filesystem path resolution
- **Features**:
  - Priority resolution: Environment → Config → Defaults
  - Support for all shuttle symbolic paths
  - Path validation and existence checking

---

## Component Control System

### Configurable Components:
```yaml
components:
  install_samba: true      # Phase 1: Samba package installation
  install_acl: true        # Phase 1: ACL tools installation  
  configure_users_groups: true  # Phase 2: User/group management
  configure_samba: true    # Phase 4: Samba configuration
  configure_firewall: true # Phase 5: Firewall configuration
```

### Component Behavior:
- **Enabled (true)**: Phase executes normally
- **Disabled (false)**: Phase skipped with warning message
- **Missing**: Defaults to enabled for backwards compatibility

---

## Interactive Mode Options

### Mode Settings in YAML:
```yaml
settings:
  interactive_mode: "interactive|non-interactive|mixed"
  dry_run_default: false
```

### Interactive Mode Behavior:
- **interactive**: Full interactive prompts and confirmations
- **non-interactive**: Automated execution, minimal user interaction
- **mixed**: Critical prompts only, automated for routine operations

### Command Line Overrides:
- `--interactive`: Force interactive mode (override YAML)
- `--non-interactive`: Force non-interactive mode (override YAML)
- `--dry-run`: Enable dry-run mode (preview without changes)

---

## Symbolic Path System

### Path Resolution Priority:
1. **Environment Variables**: `SHUTTLE_SOURCE_PATH`, `SHUTTLE_DESTINATION_PATH`, etc.
2. **Shuttle Config File**: Values from main shuttle configuration
3. **Default Values**: Fallback defaults for each path type

### Supported Symbolic Paths:
- `source_path`: Shuttle source directory for incoming files
- `destination_path`: Shuttle destination directory for clean files
- `quarantine_path`: Shuttle quarantine directory for temporary storage
- `log_path`: Shuttle log directory for application logs
- `hazard_archive_path`: Shuttle hazard archive for encrypted suspect files
- `ledger_file_path`: Daily processing tracker ledger file
- `hazard_encryption_key_path`: GPG public key for hazard encryption
- `shuttle_config_path`: Main shuttle configuration file
- `test_work_dir`: Test working directory for development
- `test_config_path`: Test configuration file for development

---

## Error Handling and Recovery

### Validation Points:
1. **Prerequisites**: Python, PyYAML, scripts, privileges
2. **YAML Syntax**: Basic syntax validation before processing
3. **Configuration Structure**: Multi-document format validation
4. **Path Resolution**: Symbolic path to filesystem path mapping
5. **Component Dependencies**: Required tools and services

### Failure Handling:
- **Critical Failures**: Stop execution, show error, exit non-zero
- **Warning Conditions**: Log warning, continue execution
- **Dry-run Mode**: Show what would be done, no actual changes
- **Interactive Confirmations**: Allow user to review and approve changes

### Recovery Options:
- **Dry-run First**: Preview changes before applying
- **Component Disable**: Skip problematic components
- **Wizard Regeneration**: Create new configuration if YAML invalid
- **Manual Intervention**: Clear guidance for manual fixes

---

## Command History and Auditing

### Command Tracking:
```bash
COMMAND_HISTORY_FILE="/tmp/shuttle_post_install_configuration_command_history_YYYYMMDD_HHMMSS.log"
```

### Logged Information:
- All executed system commands
- Command results and exit codes
- Timestamp and execution context
- User and permission changes
- Configuration file locations

### Audit Trail:
- Complete record of configuration changes
- Ability to reproduce configuration steps
- Troubleshooting and compliance support
- Integration with system logging

---

## Files Created During Configuration

### Configuration Files:
```
├── YAML Configuration: post_install_config_steps_YYYYMMDD_HHMMSS.yaml
├── Command History: /tmp/shuttle_post_install_configuration_command_history_*.log
└── Temporary Files: /tmp/wizard_config_filename (during wizard)
```

### System Changes:
```
├── System Groups: Created as defined in YAML
├── User Accounts: Local users created, domain users validated
├── File Permissions: Applied to shuttle directories and files
├── Samba Users: Configured for network access
└── System Packages: Samba, ACL tools installed
```

---

## Usage Examples

### Wizard Mode (Default):
```bash
# Run wizard to create configuration, then apply
./scripts/2_post_install_config.sh

# Run wizard with dry-run to preview changes
./scripts/2_post_install_config.sh --wizard --dry-run
```

### Instruction File Mode:
```bash
# Use existing configuration file
./scripts/2_post_install_config.sh --instructions /path/to/config.yaml

# Force interactive mode with existing config
./scripts/2_post_install_config.sh --instructions config.yaml --interactive

# Non-interactive execution with existing config
./scripts/2_post_install_config.sh --instructions config.yaml --non-interactive
```

### Development and Testing:
```bash
# Preview changes without applying
./scripts/2_post_install_config.sh --dry-run

# Verbose output for debugging
./scripts/2_post_install_config.sh --verbose

# Create config only (don't apply)
./scripts/2_post_install_config.sh --wizard
# (Choose "Save configuration and exit" option)
```