# Shuttle User Setup Orchestration Plan

## Overview

This document outlines the approach for creating and configuring users and permissions for the Shuttle secure file transfer system. The orchestration script needs to handle multiple user types with different access patterns and support both interactive and automated deployment scenarios.

## User Requirements Analysis

### 1. Samba User (`source_samba_user`)
**Purpose**: Remote users who upload files via Samba shares
- **Access Level**: Limited, write-only to source directory
- **Permissions**: 
  - Read/write access to `source_path` only
  - No shell access (service account)
  - Samba authentication required

### 2. Shuttle Service User (`shuttle_user`)
**Purpose**: Runs the main shuttle application
- **Access Level**: Application service account
- **Executable Access**: 
  - Execute `run-shuttle` command
- **Read/Write Permissions**:
  - `source_path` (read files, delete after processing)
  - `quarantine_path` (read/write for file quarantine)
  - `destination_path` (write processed files)
  - `log_path` (write application logs)
  - `hazard_archive_path` (write quarantined malware)
- **Read-Only Permissions**:
  - `ledger_file_path` (read processing ledger)
  - `hazard_encryption_key_path` (read encryption key)
  - Main config file (`SHUTTLE_CONFIG_PATH`)

### 3. Defender Test User (`defender_test_user`)
**Purpose**: Runs Microsoft Defender testing utility
- **Access Level**: Testing service account (no shell access)
- **Executable Access**:
  - Execute `run-defender-test` command
- **Read/Write Permissions**:
  - `SHUTTLE_TEST_WORK_DIR` (full access to test area)
  - `ledger_file_path` (read/write for test ledger updates)
- **Read-Only Permissions**:
  - `hazard_encryption_key_path` (read encryption key)
  - Main config file (`SHUTTLE_CONFIG_PATH`)
  - Test config file (`SHUTTLE_TEST_CONFIG_PATH`)

## Configuration Sources

### Environment Variables
- `SHUTTLE_CONFIG_PATH`: Main configuration file location
- `SHUTTLE_TEST_WORK_DIR`: Test area directory
- `SHUTTLE_TEST_CONFIG_PATH`: Test configuration file

### Config File Paths (from shuttle config)
```ini
[paths]
source_path = /home/mathew/shuttle/work/incoming
destination_path = /home/mathew/shuttle/work/processed
quarantine_path = /home/mathew/shuttle/work/quarantine
log_path = /home/mathew/shuttle/work/logs
hazard_archive_path = /home/mathew/shuttle/work/hazard
hazard_encryption_key_path = /home/mathew/shuttle/config/shuttle_public.gpg
ledger_file_path = /home/mathew/shuttle/config/ledger/ledger.yaml
```

## User Type Options

### Service Accounts (Used for All Functional Users)
- **Characteristics**: No shell access, dedicated to application function
- **Benefits**: Enhanced security, clear separation of duties
- **Shell**: `/usr/sbin/nologin` or `/bin/false`
- **Home Directory**: Application-specific (e.g., `/var/lib/shuttle`)
- **Usage**: All three user types (samba, shuttle, defender-test) are service accounts

### Local vs Domain Users
- **Local Users**: Created on local system, managed locally
- **Domain Users**: 
  - Existing domain accounts used for shuttle functions
  - Require domain join and local user mapping
  - Initial deployment will use domain users
  - Need additional group membership setup

### Administrative Access
- **Separate human accounts with sudo access to service accounts**
- **Group-based permissions for shared access**
- **Domain administrators can manage shuttle service accounts**

## Security Considerations

### File Permissions Strategy
1. **Directory Ownership**: Service accounts own their respective directories
2. **Group Access**: Use groups for shared access between users
3. **ACLs**: Fine-grained permissions for specific requirements
4. **Minimal Permissions**: Principle of least privilege

### Access Control Groups
- `shuttle-app-users`: Group for shuttle application service accounts
- `shuttle-test-users`: Group for defender test service accounts  
- `shuttle-samba-users`: Group for Samba-only users
- `shuttle-config-readers`: Group for accounts that need config file access
- `shuttle-ledger-writers`: Group for accounts that can write to ledger
- `shuttle-admin`: Administrative access for human operators

## Orchestration Script Design

### Script Structure
```
15_setup_shuttle_users.sh
├── Configuration parsing functions
├── User creation functions  
├── Permission setup functions
├── Validation functions
└── Interactive/CLI mode handlers
```

### Command-Line Interface
```bash
# Interactive mode
./15_setup_shuttle_users.sh

# Automated mode with domain users (initial deployment)
./15_setup_shuttle_users.sh \
    --user-source domain \
    --samba-user "DOMAIN\\samba-service" \
    --shuttle-user "DOMAIN\\shuttle-service" \
    --test-user "DOMAIN\\defender-test" \
    --auto-confirm

# Automated mode with local users
./15_setup_shuttle_users.sh \
    --user-source local \
    --samba-user shuttle-samba \
    --shuttle-user shuttle-app \
    --test-user shuttle-test \
    --auto-confirm

# Single user setup
./15_setup_shuttle_users.sh --setup-user samba --name shuttle-samba --source local
./15_setup_shuttle_users.sh --setup-user shuttle --name "DOMAIN\\shuttle-service" --source domain
```

### Interactive Flow
1. **Environment Detection**: Check for required environment variables
2. **Configuration Parsing**: Extract paths from shuttle config
3. **User Source Selection**: Local vs. domain users
4. **Username Configuration**: Allow custom usernames or use defaults
5. **Group Strategy**: Define groups and membership
6. **Permission Preview**: Show what will be created/modified
7. **Confirmation**: Require explicit confirmation before changes
8. **Execution**: Create/configure users and set permissions
9. **Validation**: Verify setup was successful

### Automated Flow
- Accept all configuration via command-line arguments
- Skip interactive prompts when `--auto-confirm` provided
- Support environment variable overrides
- Enable integration with configuration management tools

## Implementation Phases

### Phase 1: Core Infrastructure
- Config file parsing functions
- Path validation and directory creation
- Basic user creation using existing commands

### Phase 2: Permission Management
- Directory ownership setup
- File permission configuration
- ACL setup for fine-grained access

### Phase 3: Integration
- Samba user configuration
- Service account hardening
- Validation and testing functions

### Phase 4: Orchestration
- Interactive mode implementation
- CLI argument processing
- Error handling and rollback

## Validation Strategy

### Pre-Setup Validation
- Environment variables present and valid
- Config files readable and parseable
- Required directories exist or can be created
- No conflicting users/groups exist

### Post-Setup Validation
- Users created successfully
- Permissions set correctly
- Applications can execute with appropriate users
- File access works as expected
- Samba integration functional

### Test Suite
- Unit tests for individual functions
- Integration tests for complete workflows
- Smoke tests for production deployment
- Rollback tests for failure scenarios

## Error Handling

### Rollback Strategy
- Track all changes made during setup
- Provide rollback function to undo changes
- Support partial rollback for specific components
- Log all actions for audit trail

### Common Error Scenarios
- Insufficient privileges for user creation
- Directory creation failures
- Permission setting failures
- Configuration file parsing errors
- Environment variable conflicts

## Future Considerations

### Configuration Management Integration
- Ansible playbook compatibility
- Salt state integration
- Puppet manifest support
- Docker container user setup

### Monitoring and Maintenance
- User access auditing
- Permission drift detection
- Automated permission remediation
- Security compliance reporting

## Dependencies

### Required Commands
- User management: `useradd`, `usermod`, `groupadd`, `gpasswd`
- Permission management: `chmod`, `chown`, `setfacl`
- Samba integration: `smbpasswd`, `pdbedit`
- System utilities: `id`, `getent`, `stat`

### Required Files
- Shuttle configuration file
- Test configuration file (for test user setup)
- Encryption key file (for permission validation)

### Environment Requirements
- Root or sudo access for user creation
- Samba service available (for samba user setup)
- ACL support on filesystem (if using ACLs)