# Shuttle Configuration System Command Mapping Analysis

## Overview

This document provides a comprehensive mapping of the shuttle configuration system, detailing:
1. Main script commands and their functionality
2. _cmd_*.source.sh file implementations
3. Wizard and YAML configuration orchestration
4. Actual Unix commands executed

## Main Scripts and Their Commands

### 1. 11_install_tools.sh - Package Installation

**Purpose**: Installs required system packages (Samba, ACL tools)

**Commands**: None (direct script execution)

**Functionality**:
- Detects package manager (apt, dnf, yum, pacman, zypper, brew)
- Installs Samba/Winbind packages
- Installs ACL tools (getfacl, setfacl)
- Verifies tool installation

**Unix Commands Generated**:
```bash
# Package manager detection
which apt dnf yum pacman zypper brew

# Package installation (varies by system)
sudo apt update && sudo apt install -y samba winbind libnss-winbind libpam-winbind acl attr
sudo dnf install -y samba samba-winbind samba-winbind-clients acl attr
sudo yum install -y samba samba-winbind samba-winbind-clients acl attr

# Tool verification
smbpasswd --version
smbd -V
net --version
winbindd -V
getfacl --version
setfacl --version
```

### 2. 12_users_and_groups.sh - User and Group Management

**Purpose**: Comprehensive user, group, and permission management

**Commands**:
```
User Management:
- add-user                    # Create local or domain user
- delete-user                 # Remove user account
- modify-user                 # Modify existing user
- list-users                  # List users with filtering
- show-user                   # Display user details
- list-user-groups            # List user's groups
- import-domain-user          # Import domain user
- generate-domain-config      # Generate domain config

Group Management:
- add-group                   # Create new group
- delete-group                # Remove group
- modify-group                # Modify group
- list-groups                 # List groups
- show-group                  # Display group details
- list-group-users            # List group members
- count-group-users           # Count group members

Membership:
- add-user-to-group           # Add user to group
- delete-user-from-group      # Remove user from group

Path Management:
- set-path-owner              # Set file/directory ownership
- set-path-permissions        # Set permissions
- show-path-owner-permissions-and-acl  # Display all permissions

ACL Management:
- show-acl-on-path            # Display ACLs
- add-acl-to-path             # Add ACL entries
- delete-acl-from-path        # Remove ACL entries
```

### 3. 13_configure_samba.sh - Samba Configuration

**Purpose**: Manage Samba shares, users, and services

**Commands**:
```
Share Management:
- add-share                   # Create Samba share
- remove-share                # Remove share
- list-shares                 # List all shares
- show-share                  # Display share details
- enable-share                # Enable disabled share
- disable-share               # Disable share

User Management:
- add-samba-user              # Add user to Samba
- remove-samba-user           # Remove from Samba
- set-samba-password          # Set/change password
- list-samba-users            # List Samba users
- enable-samba-user           # Enable user
- disable-samba-user          # Disable user

Service Management:
- start-samba                 # Start services
- stop-samba                  # Stop services
- restart-samba               # Restart services
- reload-samba                # Reload config
- status-samba                # Show status
- test-config                 # Test configuration
```

### 4. 14_configure_firewall.sh - Firewall Configuration

**Purpose**: Manage host-based firewall rules for Samba and services

**Commands**:
```
Firewall Management:
- enable-firewall             # Enable UFW firewall
- disable-firewall            # Disable firewall
- detect-firewall             # Detect firewall type
- show-status                 # Show firewall status
- list-firewall-rules         # List all rules
- delete-firewall-rule        # Delete specific rules

Samba Access:
- allow-samba-from            # Allow Samba access
- deny-samba-from             # Deny Samba access
- list-samba-rules            # List Samba rules

Service Access:
- allow-service-from          # Allow service access
- deny-service-from           # Deny service access
- list-service-rules          # List service rules

Host Isolation:
- isolate-host                # Isolate host
- unisolate-host              # Remove isolation
- list-isolated-hosts         # List isolated hosts
```

## Key _cmd_ File Implementations

### User Management Commands

#### _cmd_add_user.source.sh
**Function**: `cmd_add_user`
**Unix Commands**:
```bash
# Local user creation
sudo useradd --create-home --shell /bin/bash --gid groupname --groups group1,group2 username
printf '%s:%s\n' 'username' 'password' | sudo chpasswd

# Domain user setup (local resources only)
id "DOMAIN\\username"  # Verify domain user exists
sudo mkdir -p /home/username
sudo chown "DOMAIN\\username:domain users" /home/username
sudo gpasswd -a "DOMAIN\\username" groupname
```

#### _cmd_import_domain_user.source.sh
**Function**: `cmd_import_domain_user`
**Unix Commands**:
```bash
# Executes configured domain import command
# Example (configured in domain_import.conf):
sudo /opt/corporate/bin/import-domain-user --username alice.domain --uid 70001 --home /home/alice.domain --shell /bin/bash --primary-group users --groups developers,sudo

# UID generation
getent passwd | awk -F: '$3 >= 70000 && $3 <= 99999 {print $3}' | sort -n

# User verification
id username
```

### Group Management Commands

#### _cmd_add_group.source.sh
**Unix Commands**:
```bash
sudo groupadd --gid 5001 groupname
sudo groupadd --system systemgroup
```

#### _cmd_add_user_to_group.source.sh
**Unix Commands**:
```bash
sudo gpasswd -a username groupname
sudo usermod -a -G groupname username  # Alternative
```

### Samba Management Commands

#### _cmd_add_share.source.sh
**Unix Commands**:
```bash
# Backup configuration
sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.backup.20240105_143022

# Add share configuration
echo -e '[sharename]\n   path = /var/data\n   browseable = yes\n   read only = no\n   guest ok = no\n   create mask = 0644\n   directory mask = 0755\n   valid users = alice,bob' | sudo tee -a /etc/samba/smb.conf

# Test configuration
sudo testparm -s
```

#### _cmd_add_samba_user.source.sh
**Unix Commands**:
```bash
# Add user to Samba (sets password)
sudo smbpasswd -a username
sudo smbpasswd -s username  # With stdin password

# Enable/disable user
sudo smbpasswd -e username  # Enable
sudo smbpasswd -d username  # Disable
```

### Firewall Management Commands

#### _cmd_allow_samba_from.source.sh
**Unix Commands**:
```bash
# UFW commands
sudo ufw allow from 192.168.1.0/24 to any port 445 proto tcp comment 'Internal LAN'
sudo ufw allow from 192.168.1.0/24 to any port 139 proto tcp
sudo ufw allow from 192.168.1.0/24 to any port 137 proto udp
sudo ufw allow from 192.168.1.0/24 to any port 138 proto udp

# Firewalld commands
sudo firewall-cmd --add-rich-rule='rule family="ipv4" source address="192.168.1.0/24" port protocol="tcp" port="445" accept' --permanent
sudo firewall-cmd --reload

# Iptables commands
sudo iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 445 -m comment --comment "Internal LAN" -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

### ACL Management Commands

#### _cmd_add_acl_to_path.source.sh
**Unix Commands**:
```bash
# Set ACL permissions
sudo setfacl -m u:username:rwx /path/to/directory
sudo setfacl -m g:groupname:r-x /path/to/directory
sudo setfacl -m d:u:username:rwx /path/to/directory  # Default ACL

# Recursive ACL
sudo setfacl -R -m u:username:rwx /path/to/directory
```

## Wizard and YAML Configuration Orchestration

### Wizard Components

1. **post_install_config_wizard.py** - Main wizard interface
   - Collects user input through interactive prompts
   - Offers three deployment modes: Development, Standard, Custom
   - Generates YAML configuration files

2. **wizard_domain_integration.py** - Domain user integration
   - Validates domain user requirements
   - Generates domain import configuration
   - Creates test scripts for domain setup

3. **wizard_domain_validation.py** - Domain validation logic
   - Detects domain users (patterns: dots, @, backslash)
   - Validates domain configuration files
   - Provides helper functions for domain setup

### YAML Configuration Structure

The wizard generates multiple YAML files:

1. **Main instruction file** (e.g., `shuttle_config_production.yaml`):
```yaml
description: "Shuttle Production Configuration"
created_by: "Post-Install Configuration Wizard"
deployment_mode: "standard"
installation_order:
  - groups
  - users
  - paths
  - samba
  - firewall
```

2. **Groups configuration** (`groups.yaml`):
```yaml
shuttle-service:
  description: "Service account for shuttle operations"
  gid: 5001
  
shuttle-users:
  description: "Network users who can submit files"
  gid: 5002
```

3. **Users configuration** (`users.yaml`):
```yaml
- name: shuttle-service
  type: service
  shell: /sbin/nologin
  groups:
    primary: shuttle-service
    secondary: []
  home: /var/shuttle/service
  
- name: alice.domain
  type: domain
  groups:
    secondary: [shuttle-users, developers]
```

4. **Paths configuration** (`paths.yaml`):
```yaml
/var/shuttle/incoming:
  owner: shuttle-service
  group: shuttle-service
  permissions: "2770"
  acl:
    - "g:shuttle-users:rwx"
    - "d:g:shuttle-users:rwx"
```

5. **Samba configuration** (`samba.yaml`):
```yaml
shares:
  shuttle-incoming:
    path: /var/shuttle/incoming
    comment: "Shuttle file intake"
    browseable: yes
    read_only: no
    valid_users: "@shuttle-users"
    create_mask: "0660"
    directory_mask: "2770"
```

6. **Firewall configuration** (`firewall.yaml`):
```yaml
samba:
  allow_from:
    - source: "192.168.1.0/24"
      comment: "Internal LAN"
    - source: "10.10.5.0/24"
      comment: "Management VLAN"
```

### Configuration to Command Translation

The wizard-generated YAML is processed to create shell commands:

1. **Group Creation**:
   - YAML: `shuttle-service: {gid: 5001}`
   - Command: `./12_users_and_groups.sh add-group --group shuttle-service --gid 5001`

2. **User Creation**:
   - YAML: `{name: alice.domain, type: domain}`
   - Commands:
     ```bash
     ./12_users_and_groups.sh generate-domain-config --output-dir /etc/shuttle
     ./12_users_and_groups.sh import-domain-user --username alice.domain --command-config /etc/shuttle/domain_import.conf
     ```

3. **Path Permissions**:
   - YAML: `{owner: shuttle-service, permissions: "2770"}`
   - Commands:
     ```bash
     ./12_users_and_groups.sh set-path-owner --path /var/shuttle/incoming --user shuttle-service --group shuttle-service
     ./12_users_and_groups.sh set-path-permissions --path /var/shuttle/incoming --mode 2770
     ./12_users_and_groups.sh add-acl-to-path --path /var/shuttle/incoming --acl "g:shuttle-users:rwx"
     ```

4. **Samba Share**:
   - YAML: `{name: shuttle-incoming, path: /var/shuttle/incoming}`
   - Command: `./13_configure_samba.sh add-share --name shuttle-incoming --path /var/shuttle/incoming --valid-users "@shuttle-users"`

5. **Firewall Rules**:
   - YAML: `{source: "192.168.1.0/24", comment: "Internal LAN"}`
   - Command: `./14_configure_firewall.sh allow-samba-from --source "192.168.1.0/24" --comment "Internal LAN"`

## Domain User Import Process

### Configuration Flow
1. Wizard detects domain users (usernames with dots, @, or backslash)
2. Prompts for domain configuration method
3. Generates `domain_import.conf` with template
4. User edits template to specify actual import command
5. Test script validates configuration
6. Import command executed for each domain user

### Example Domain Configuration (`/etc/shuttle/domain_import.conf`):
```ini
# Domain user import configuration
command=/opt/corporate/bin/import-domain-user
args_template=--username {username} --home {home} --shell {shell} --primary-group {primary_group}
default_shell=/bin/bash
default_home_pattern=/home/{username}
uid_range_start=70000
uid_range_end=99999
```

### Generated Test Script (`test_domain_import.sh`):
```bash
#!/bin/bash
# Test domain import configuration
echo "Testing with sample values:"
echo "Command: /opt/corporate/bin/import-domain-user"
echo "Arguments: --username testuser --home /home/testuser --shell /bin/bash --primary-group users"
```

## Security Features

### Path Validation
- Safe prefixes whitelist (shuttle directories)
- Dangerous paths blacklist (system directories)
- Warning for paths outside shuttle directories
- --reckless flag to bypass (with warnings)

### User Type Handling
- Local users: Full useradd creation
- Domain users: Local resource setup only (home, groups)
- Service accounts: nologin shell, no password
- Interactive users: Password setup instructions

### Firewall Integration
- Auto-detects firewall type (ufw, firewalld, iptables)
- Persistent rule configuration
- Network source validation
- Comment support for rule documentation

## Command Execution Patterns

### Dry Run Support
All commands support `--dry-run` flag:
```bash
# Shows what would be done without executing
./12_users_and_groups.sh add-user --user alice --group users --dry-run
[DRY RUN] Would execute: sudo useradd --create-home --shell /bin/bash --gid users alice
```

### Verbose Mode
All commands support `--verbose` flag for detailed output:
```bash
./13_configure_samba.sh add-share --name data --path /var/data --verbose
[INFO] Adding Samba share 'data' at path '/var/data'
[INFO] Backed up smb.conf to /etc/samba/smb.conf.backup.20240105_143022
[INFO] Added share configuration to smb.conf
[INFO] Samba configuration test passed
```

### Error Handling
- Input validation before execution
- Rollback support (e.g., Samba config restore)
- Detailed error messages with suggestions
- Exit codes for automation

## Integration with Shuttle

The configuration system integrates with shuttle through:

1. **Path Discovery**: Reads shuttle_config.yaml for actual paths
2. **User/Group Setup**: Creates accounts for shuttle operations
3. **Permission Model**: Implements shuttle security model
4. **Samba Shares**: Provides network access to shuttle directories
5. **Firewall Rules**: Restricts access to authorized networks

This comprehensive system provides a complete solution for deploying and configuring shuttle in production environments with proper security boundaries and access controls.