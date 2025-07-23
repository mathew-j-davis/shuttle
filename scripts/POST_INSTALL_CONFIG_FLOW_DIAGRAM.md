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
│       ├── Phase 5: Configure Firewall
│       └── Phase 6: Security Audit (Optional Validation)
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
- **Template-driven configuration**: Production, development, and custom templates for users, groups, and paths
- **Interactive template editing**: Field-by-field customization with validation and preview
- **Standardized menu system**: Universal menu navigation with back options and consistent numbering
- **Environment profiles**: Multiple environment support (development, testing, production)
- **Path integration**: Reads existing shuttle configuration to extract actual paths
- **Secure password handling**: No password storage in YAML - provides manual setup guidance
- **Configuration validation**: Built-in YAML validation and structure checking
- **Symbolic path resolution**: Automatic resolution of shuttle directory paths

### Detailed Wizard Flow Diagram:
```
Configuration Wizard (post_install_config_wizard.py)
│
├── 1. Initialization
│   ├── Load shuttle config → Extract actual paths
│   ├── Initialize wizard state → Track users, groups, paths
│   └── Display welcome → Show wizard purpose and process
│
├── 2. Environment Selection
│   ├── Choose Configuration Type:
│   │   ├── 1) Production → Use production templates
│   │   ├── 2) Development → Use development templates  
│   │   └── 3) Custom → Start with minimal configuration
│   └── Load base templates for selected environment
│
├── 3. Main Configuration Menu
│   ├── Option 1: Configure Groups
│   │   ├── Show Current Groups → Display configured groups with counts
│   │   ├── Group Management Menu:
│   │   │   ├── 0) Add All Standard Groups → Bulk add environment templates
│   │   │   ├── 1) Add Group from Template → Template selection
│   │   │   ├── 2) Add Custom Group → Manual group creation
│   │   │   ├── 3) Edit Group → Select and modify existing group
│   │   │   ├── 4) Remove Group → Delete group configuration
│   │   │   └── b) Back to Main Menu
│   │   └── Group Template Flow:
│   │       ├── Template Selection → Show available templates with descriptions
│   │       ├── Template Preview → Display complete group information
│   │       ├── Customization Choice:
│   │       │   ├── Use as-is → Accept template defaults
│   │       │   ├── Edit → Field-by-field customization
│   │       │   └── Skip → Don't add this group
│   │       └── Apply Changes → Add to configuration
│   │
│   ├── Option 2: Configure Users  
│   │   ├── Show Current Users → Display configured users with types and counts
│   │   ├── User Management Menu:
│   │   │   ├── 0) Add All Standard Users → Bulk add environment templates
│   │   │   ├── 1) Add User from Template → Template selection
│   │   │   ├── 2) Add Custom User → Manual user creation
│   │   │   ├── 3) Edit User → Select and modify existing user
│   │   │   ├── 4) Remove User → Delete user configuration
│   │   │   └── b) Back to Main Menu
│   │   └── User Template Flow:
│   │       ├── Template Category Selection → admin, core_services, network_services
│   │       ├── Template Selection → Show templates with recommendations
│   │       ├── Template Preview → Display complete user information:
│   │       │   ├── Account type, source, groups
│   │       │   ├── Shell, home directory settings
│   │       │   ├── Samba configuration
│   │       │   └── Password setup guidance
│   │       ├── Customization Choice:
│   │       │   ├── Use as-is → Accept template defaults
│   │       │   ├── Edit → Interactive field editing:
│   │       │   │   ├── Basic Info → Name, description, account type
│   │       │   │   ├── Source Settings → Local, existing, domain
│   │       │   │   ├── Group Configuration → Primary and secondary groups
│   │       │   │   ├── Local Account Settings → Shell, home directory
│   │       │   │   ├── Samba Settings → Enable/disable, auth method
│   │       │   │   └── Final Review → Show all changes before applying
│   │       │   └── Skip → Don't add this user
│   │       └── Apply Changes → Add to configuration with password guidance
│   │
│   ├── Option 3: Configure Path Permissions
│   │   ├── Show Current Paths → Display shuttle paths and permission status
│   │   ├── Path Permission Menu:
│   │   │   ├── 0) Apply Standard Path Permissions to All Paths → Bulk template application
│   │   │   ├── 1) Configure Permissions for Shuttle Path → Path-specific configuration
│   │   │   ├── 2) Configure Permissions for Custom Path → Manual path addition
│   │   │   ├── 3) Edit Path Permission Configuration → Modify existing
│   │   │   ├── 4) Remove Path Permission Configuration → Delete path config
│   │   │   └── b) Back to Main Menu
│   │   └── Path Template Flow:
│   │       ├── Template Selection → Production, development, custom templates
│   │       ├── Template Preview → Display ownership, permissions, ACLs
│   │       ├── Path Selection → Choose from shuttle config paths
│   │       ├── Template Customization:
│   │       │   ├── Owner/Group → Select from configured users/groups
│   │       │   ├── File Mode → Numeric permissions (e.g., 0644)
│   │       │   ├── Directory Mode → Numeric permissions (e.g., 0755)
│   │       │   ├── ACL Configuration → User and group ACLs
│   │       │   └── Default ACLs → Directory inheritance rules
│   │       └── Apply to Paths → Apply template to selected paths
│   │
│   ├── Option 4: Review Configuration
│   │   ├── Show Configuration Summary:
│   │   │   ├── Groups Count → N groups configured
│   │   │   ├── Users Count → N users configured (X service, Y interactive)
│   │   │   ├── Paths Count → N paths configured
│   │   │   └── Interactive Users Warning → Password setup required
│   │   ├── Detailed Review → Show complete configuration
│   │   └── Validation → Check for configuration issues
│   │
│   ├── Option 5: Save Configuration
│   │   ├── Final Validation → YAML syntax and structure check
│   │   ├── Generate Multi-Document YAML:
│   │   │   ├── Document 1 → Global settings and metadata
│   │   │   ├── Document 2 → Group definitions
│   │   │   ├── Document N → User definitions (one per user)
│   │   │   └── Document N+1 → Path permission configurations
│   │   ├── Save Options:
│   │   │   ├── 1) Save configuration only (exit without applying)
│   │   │   ├── 2) Save configuration and continue to installation
│   │   │   └── x) Exit without saving
│   │   └── File Output → post_install_config_steps_YYYYMMDD_HHMMSS.yaml
│   │
│   └── Option x: Exit Wizard
│       ├── Unsaved Changes Check → Warn if configuration not saved
│       └── Exit Codes:
│           ├── 0 → Success, configuration saved and ready to apply
│           ├── 1 → Configuration saved, user chose to exit
│           ├── 2 → User cancelled, no configuration saved
│           └── 3 → Error occurred during wizard execution
│
├── 4. Universal Menu System Features
│   ├── Consistent Navigation:
│   │   ├── Numbered options starting at 1 (0 reserved for special actions)
│   │   ├── 'b' for back navigation (available in most menus)
│   │   ├── 'x' for exit/cancel actions
│   │   └── Default values shown in brackets [default]
│   ├── User Experience:
│   │   ├── Clear prompts with help text
│   │   ├── Input validation with error messages
│   │   ├── Configuration previews before applying
│   │   └── Running totals and status indicators
│   └── Security Integration:
│   │   ├── Password setup guidance for interactive accounts
│   │   ├── Service account security model enforcement
│   │   ├── Samba user isolation warnings
│   │   └── Permission template security implications
│
└── 5. Template System Integration
    ├── Standard Templates (standard_configs.py):
    │   ├── Production Templates → Secure, restrictive defaults
    │   ├── Development Templates → Broader access for testing
    │   └── Base Templates → Foundation for customization
    ├── Template Features:
    │   ├── Category organization → admin, core_services, network_services
    │   ├── Recommendation flags → Highlight recommended templates
    │   ├── Security implications → Clear warnings and guidance
    │   └── Inheritance support → Build on base configurations
    └── Interactive Editing:
        ├── Field-by-field customization → Guided input for each setting
        ├── Validation feedback → Real-time error checking
        ├── Preview generation → Show final configuration before applying
        └── Rollback support → Undo changes if needed
```

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
  # Note: Passwords are NOT stored in YAML files for security
  # Manual setup required: sudo passwd username, sudo smbpasswd -a username
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

### Phase 6: Security Audit (Optional Validation)
```
phase_security_audit() [Optional - can be run separately]
├── Check if security audit is requested
├── Validate audit configuration exists
├── python3 scripts/security_audit.py --audit-config production_audit.yaml --shuttle-config SHUTTLE_CONFIG
└── Security validation checks:
    ├── User account security (shells, group memberships)
    ├── Group configuration (proper members, no unauthorized access)
    ├── Samba security model (user isolation, shell restrictions)
    ├── Path permissions (ownership, world-readable detection)
    ├── File system security (ACLs, executable files in data directories)
    └── Exit codes: 0=passed, 1=errors, 2=critical issues
```

---

## Python Module Architecture

### Core Configuration Modules

#### post_install_config_wizard.py
- **Purpose**: Interactive YAML configuration generation with template-driven approach
- **Features**: 
  - **Template system**: Production, development, and custom templates for users, groups, and paths
  - **Interactive editing**: Field-by-field template customization with validation
  - **Universal menu system**: Standardized navigation with back options and consistent numbering
  - **Security-focused**: No password storage, provides manual setup guidance
  - **Multi-environment support**: Development, testing, and production profiles
  - **Path integration**: Reads shuttle config to extract actual paths
  - **Configuration validation**: Built-in YAML syntax and structure validation
  - **User-friendly UX**: Clear prompts, help text, and configuration previews

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

#### standard_configs.py
- **Purpose**: Template definitions for users, groups, and path permissions
- **Features**:
  - Production and development template variants
  - Base templates with recommended configurations
  - Template inheritance and customization support
  - Security-focused default configurations

#### security_audit.py
- **Purpose**: Production deployment security validation
- **Features**:
  - User account security verification (shells, group memberships)
  - Samba security model enforcement (user isolation, restrictions)
  - File system security validation (permissions, ACLs, world-readable detection)
  - Path ownership verification against shuttle configuration
  - Configuration-driven audit policies with YAML definitions
  - CI/CD integration with exit codes (0=pass, 1=errors, 2=critical)

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
  security_audit: false   # Phase 6: Security validation (optional)
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

## Template-Driven Configuration System

### Template Architecture:
```
Standard Templates (standard_configs.py)
├── User Templates
│   ├── Production Templates (STANDARD_PRODUCTION_USER_TEMPLATES)
│   │   ├── Service accounts (shuttle_runner, shuttle_monitor)
│   │   ├── Admin accounts (shuttle_admin)
│   │   └── Samba accounts (shuttle_samba_in, shuttle_samba_out)
│   └── Development Templates (STANDARD_DEVELOPMENT_USER_TEMPLATES)
│       ├── Developer accounts with broader access
│       └── Testing accounts for validation
├── Group Templates  
│   ├── Core permission groups (shuttle_owners, shuttle_log_owners, shuttle_config_readers, shuttle_testers)
│   └── Optional network groups (shuttle_samba_in_users, shuttle_out_users)
└── Path Permission Templates (PATH_PERMISSION_BASE_TEMPLATES)
    ├── Production template (restrictive permissions)
    ├── Development template (broader access for testing)
    └── Custom template (user-defined baseline)
```

### Template Selection and Customization:
1. **Environment Selection**: Choose production, development, or custom baseline
2. **Template Review**: Display template details with security implications
3. **Interactive Editing**: Field-by-field customization with validation
4. **Bulk Operations**: "Add All" options for complete environment setup
5. **Template Application**: Apply templates to all paths with consistent permissions

### Security Model Integration:
- **Service Account Templates**: No-login shells, minimal group memberships
- **Samba User Templates**: Complete isolation from other shuttle groups
- **Permission Templates**: Secure defaults with ACL inheritance
- **Path Templates**: Ownership and permission patterns for shuttle directories

### Wizard User Experience:
- **Universal Menu System**: Consistent navigation with numbered options and back functionality
- **Template Previews**: Clear display of what each template configures
- **Validation Feedback**: Real-time validation with clear error messages
- **Security Guidance**: Password setup instructions and security best practices
- **Configuration Counts**: Running totals of users, groups, and paths configured

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

### Security Validation:
```bash
# Run security audit after configuration
python3 scripts/security_audit.py \
  --audit-config example/security_audit_config/production_audit.yaml \
  --shuttle-config /etc/shuttle/shuttle_config.yaml

# Security audit with verbose output
python3 scripts/security_audit.py \
  --audit-config example/security_audit_config/production_audit.yaml \
  --shuttle-config /etc/shuttle/shuttle_config.yaml \
  --verbose

# Check exit code for CI/CD integration
if ! python3 scripts/security_audit.py --audit-config audit.yaml --shuttle-config config.yaml; then
    echo "Security audit failed - review configuration"
    exit 1
fi
```