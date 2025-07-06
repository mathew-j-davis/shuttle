# Shuttle Configuration System Test Mapping

This document provides a comprehensive mapping of the shuttle configuration system for testing purposes, covering wizard functionality, YAML configuration, command-line tools, and the resulting Unix commands.

## Overview

The shuttle configuration system operates at multiple orchestration levels:

1. **Wizard Level**: Interactive configuration wizard that generates YAML files
2. **YAML Configuration Level**: Declarative configuration processed by Python managers
3. **Main Script Level**: Shell scripts (11-14) that provide command-line interfaces
4. **Command Implementation Level**: _cmd_*.source.sh files with specific functionality
5. **Unix Command Level**: Actual system commands executed

## Configuration Flow

```
Wizard → YAML → Main Scripts → _cmd_ Files → Unix Commands
```

---

## 1. User and Group Management (12_users_and_groups.sh)

### Available Commands (24 commands)

### Detailed Parameter Flow Examples

#### User Management

##### Example 1: Creating a Local User with Full Parameter Flow

**YAML Instruction Document:**
```yaml
---
type: user
user:
  name: alice
  description: Alice Anderson - Lead Developer
  source: local
  account_type: interactive
  uid: 10001
  groups:
    primary: developers
    secondary: ["sudo", "docker", "shuttle_admins"]
  shell: /bin/bash
  home_directory: /home/alice
  create_home: true
```

**Command Flow:**
```bash
# 1. Wizard generates YAML and calls main configuration script
./scripts/2_post_install_config.sh --instructions config/users.yaml --verbose

# 2. Main script parses YAML and calls user management script
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-user \
  --user alice \
  --uid 10001 \
  --description "Alice Anderson - Lead Developer" \
  --primary-group developers \
  --secondary-groups "sudo,docker,shuttle_admins" \
  --shell /bin/bash \
  --home /home/alice \
  --create-home \
  --verbose

# 3. 12_users_and_groups.sh calls _cmd_add_user.source.sh
cmd_add_user "alice" "10001" "Alice Anderson - Lead Developer" "developers" "sudo,docker,shuttle_admins" "/bin/bash" "/home/alice" "true"

# 4. _cmd_add_user.source.sh executes Unix commands
sudo useradd \
  --uid 10001 \
  --comment "Alice Anderson - Lead Developer" \
  --gid developers \
  --groups sudo,docker,shuttle_admins \
  --shell /bin/bash \
  --home-dir /home/alice \
  --create-home \
  alice

# 5. If password provided (not in YAML for security)
printf '%s:%s\n' 'alice' 'SecurePassword123!' | sudo chpasswd
```

##### Example 2: Importing a Domain User with Configuration

**Domain Configuration File (/etc/shuttle/domain_import.conf):**
```ini
[domain_import]
command=/opt/corporate/bin/import-domain-user
args_template=--username {username} --uid {uid} --home {home} --shell {shell} --primary-group {primary_group} --groups {groups}
default_shell=/bin/bash
default_home_pattern=/home/{username}
uid_range_start=70000
uid_range_end=99999
```

**YAML Instruction Document:**
```yaml
---
type: user
user:
  name: alice.domain
  description: Alice Domain User - Engineering Team
  source: domain
  account_type: interactive
  groups:
    primary: engineering
    secondary: ["developers", "docker", "shuttle_samba_in_users"]
  shell: /bin/bash
  home_directory: /home/alice.domain
  create_home: true
```

**Command Flow:**
```bash
# 1. Main configuration script processes YAML
./scripts/2_post_install_config.sh --instructions config/domain_users.yaml --verbose

# 2. Calls domain user import with all parameters
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \
  --username alice.domain \
  --primary-group engineering \
  --secondary-groups "developers,docker,shuttle_samba_in_users" \
  --shell /bin/bash \
  --home /home/alice.domain \
  --command-config /etc/shuttle/domain_import.conf \
  --verbose

# 3. _cmd_import_domain_user.source.sh processes parameters
# - Generates next available UID: 70001
# - Reads configuration from domain_import.conf
# - Substitutes template variables

# 4. Executes configured domain import command
sudo /opt/corporate/bin/import-domain-user \
  --username alice.domain \
  --uid 70001 \
  --home /home/alice.domain \
  --shell /bin/bash \
  --primary-group engineering \
  --groups developers,docker,shuttle_samba_in_users

# 5. Post-import group membership adjustments
sudo gpasswd -a alice.domain developers
sudo gpasswd -a alice.domain docker
sudo gpasswd -a alice.domain shuttle_samba_in_users
```

#### User Management
| Command            | _cmd_ File                        | Main Unix Commands                            | Wizard/YAML Support |
|--------------------|-----------------------------------|-----------------------------------------------|---------------------|
| `add-user`         | `_cmd_add_user.source.sh`         | `sudo useradd`, `sudo passwd`, `sudo usermod` | ✅ Full YAML support |
| `delete-user`      | `_cmd_delete_user.source.sh`      | `sudo userdel -r`                             | ✅ Via user removal  |
| `modify-user`      | `_cmd_modify_user.source.sh`      | `sudo usermod`, `sudo chsh`                   | ✅ User updates      |
| `list-users`       | `_cmd_list_users.source.sh`       | `getent passwd`, `id`, `groups`               | -                   |
| `show-user`        | `_cmd_show_user.source.sh`        | `id`, `getent passwd`, `groups`               | -                   |
| `list-user-groups` | `_cmd_list_user_groups.source.sh` | `groups`, `id`                                | -                   |

#### Domain User Import (NEW)
| Command                  | _cmd_ File                              | Main Unix Commands                        | Wizard/YAML Support  |
|--------------------------|-----------------------------------------|-------------------------------------------|----------------------|
| `import-domain-user`     | `_cmd_import_domain_user.source.sh`     | `${DOMAIN_IMPORT_COMMAND}` (configurable) | ✅ Domain integration |
| `generate-domain-config` | `_cmd_generate_domain_config.source.sh` | File creation, template generation        | ✅ Wizard guidance    |

**Example YAML Configuration:**
```yaml
# Domain user in YAML
type: user
user:
  name: alice.domain
  source: domain
  account_type: interactive
  groups:
    primary: engineering
    secondary: ["developers", "sudo"]
```

**Example Command Execution:**
```bash
# Command generated from YAML
./12_users_and_groups.sh import-domain-user --username alice.domain --primary-group engineering --command-config /etc/shuttle/domain_import.conf

# Resulting Unix command (configurable)
sudo /opt/corporate/bin/import-domain-user --username alice.domain --home /home/alice.domain --shell /bin/bash --primary-group engineering
```

##### Example 3: Creating Groups with GID Assignment

**YAML Instruction Document:**
```yaml
---
type: group
group:
  name: shuttle_data_owners
  gid: 5002
  description: Users who own shuttle data directories
  system: false
```

**Command Flow:**
```bash
# 1. YAML processing
./scripts/2_post_install_config.sh --instructions config/groups.yaml

# 2. Group creation command
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-group \
  --group shuttle_data_owners \
  --gid 5002 \
  --description "Users who own shuttle data directories"

# 3. _cmd_add_group.source.sh execution
sudo groupadd --gid 5002 shuttle_data_owners
```

#### Group Management
| Command             | _cmd_ File                         | Main Unix Commands        | Wizard/YAML Support |
|---------------------|------------------------------------|---------------------------|---------------------|
| `add-group`         | `_cmd_add_group.source.sh`         | `sudo groupadd`           | ✅ Full YAML support |
| `delete-group`      | `_cmd_delete_group.source.sh`      | `sudo groupdel`           | ✅ Group removal     |
| `modify-group`      | `_cmd_modify_group.source.sh`      | `sudo groupmod`           | ✅ Group updates     |
| `list-groups`       | `_cmd_list_groups.source.sh`       | `getent group`, `cut`     | -                   |
| `show-group`        | `_cmd_show_group.source.sh`        | `getent group`, `members` | -                   |
| `list-group-users`  | `_cmd_list_group_users.source.sh`  | `getent group`, `members` | -                   |
| `count-group-users` | `_cmd_count_group_users.source.sh` | `getent group`, `wc`      | -                   |

**Example YAML Configuration:**
```yaml
type: group
group:
  name: shuttle_admins
  gid: 5000
  description: Administrative users with full shuttle access
```

**Example Command Execution:**
```bash
# Command generated from YAML
./12_users_and_groups.sh add-group --name shuttle_admins --gid 5000 --description "Administrative users"

# Resulting Unix command
sudo groupadd --gid 5000 shuttle_admins
```

#### User-Group Membership
| Command                  | _cmd_ File                              | Main Unix Commands   | Wizard/YAML Support |
|--------------------------|-----------------------------------------|----------------------|---------------------|
| `add-user-to-group`      | `_cmd_add_user_to_group.source.sh`      | `sudo usermod -a -G` | ✅ Via user creation |
| `delete-user-from-group` | `_cmd_delete_user_from_group.source.sh` | `sudo gpasswd -d`    | ✅ User updates      |

##### Example 4: Setting Complex ACLs on Paths

**YAML Instruction Document:**
```yaml
---
type: path
path:
  location: /var/shuttle/quarantine
  owner: shuttle_runner
  group: shuttle_data_owners
  mode: "2770"
  acls:
    - "u:alice:rwx"
    - "u:bob:r-x"
    - "g:shuttle_admins:rwx"
    - "g:shuttle_monitors:r-x"
  default_acls:
    directories:
      - "d:u:alice:rwx"
      - "d:g:shuttle_admins:rwx"
      - "d:g:shuttle_data_owners:rwx"
    files:
      - "d:u:alice:rw-"
      - "d:g:shuttle_admins:rw-"
  recursive: true
```

**Command Flow:**
```bash
# 1. Path creation and ownership
sudo mkdir -p /var/shuttle/quarantine
sudo chown shuttle_runner:shuttle_data_owners /var/shuttle/quarantine
sudo chmod 2770 /var/shuttle/quarantine

# 2. ACL application commands generated
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-acl-to-path \
  --path /var/shuttle/quarantine \
  --acl "u:alice:rwx" \
  --recursive

./scripts/2_post_install_config_steps/12_users_and_groups.sh add-acl-to-path \
  --path /var/shuttle/quarantine \
  --acl "g:shuttle_admins:rwx" \
  --recursive

# 3. Default ACL commands
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-acl-to-path \
  --path /var/shuttle/quarantine \
  --acl "d:u:alice:rwx" \
  --default \
  --recursive

# 4. _cmd_add_acl_to_path.source.sh executes
sudo setfacl -R -m u:alice:rwx /var/shuttle/quarantine
sudo setfacl -R -m g:shuttle_admins:rwx /var/shuttle/quarantine
sudo setfacl -R -d -m u:alice:rwx /var/shuttle/quarantine
sudo setfacl -R -d -m g:shuttle_admins:rwx /var/shuttle/quarantine
```

#### ACL Management
| Command                | _cmd_ File                            | Main Unix Commands | Wizard/YAML Support |
|------------------------|---------------------------------------|--------------------|---------------------|
| `show-acl-on-path`     | `_cmd_show_acl_on_path.source.sh`     | `getfacl`          | -                   |
| `add-acl-to-path`      | `_cmd_add_acl_to_path.source.sh`      | `setfacl -m`       | ✅ Full YAML support |
| `delete-acl-from-path` | `_cmd_delete_acl_from_path.source.sh` | `setfacl -x`       | ✅ ACL removal       |

**Example YAML Configuration:**
```yaml
type: path
path:
  location: /var/shuttle/source
  owner: shuttle_runner
  group: shuttle_data_owners
  mode: "0755"
  acls:
    - "u:alice:rw-"
    - "g:shuttle_admins:rwx"
  default_acls:
    directories:
      - "d:u:alice:rw-"
      - "d:g:shuttle_admins:rwx"
```

**Example Command Execution:**
```bash
# Commands generated from YAML
./12_users_and_groups.sh set-path-owner --path /var/shuttle/source --owner shuttle_runner --group shuttle_data_owners
./12_users_and_groups.sh set-path-permissions --path /var/shuttle/source --mode 0755
./12_users_and_groups.sh add-acl-to-path --path /var/shuttle/source --acl "u:alice:rw-"
./12_users_and_groups.sh add-acl-to-path --path /var/shuttle/source --acl "g:shuttle_admins:rwx" --default

# Resulting Unix commands
sudo chown shuttle_runner:shuttle_data_owners /var/shuttle/source
sudo chmod 0755 /var/shuttle/source
sudo setfacl -m u:alice:rw- /var/shuttle/source
sudo setfacl -m g:shuttle_admins:rwx /var/shuttle/source
sudo setfacl -d -m u:alice:rw- /var/shuttle/source
sudo setfacl -d -m g:shuttle_admins:rwx /var/shuttle/source
```

---

## 2. Samba Configuration (13_configure_samba.sh)

### Available Commands (18 commands)

### Detailed Parameter Flow Examples

#### Share Management

##### Example 5: Creating Samba Share with Advanced Configuration

**YAML Instruction Document:**
```yaml
---
type: samba_share
samba:
  enabled: true
  shares:
    shuttle_inbound:
      path: /var/shuttle/source
      comment: Shuttle inbound file submission area
      browseable: true
      read_only: false
      guest_ok: false
      valid_users: "@shuttle_samba_in_users"
      write_list: "@shuttle_samba_in_users"
      create_mask: "0644"
      directory_mask: "0755"
      force_user: shuttle_runner
      force_group: shuttle_data_owners
      vfs_objects: "recycle audit"
      recycle_repository: ".recycle"
      recycle_keeptree: true
      audit_facility: local5
      audit_priority: info
  global_settings:
    workgroup: WORKGROUP
    server_string: "Shuttle File Transfer Server"
    security: user
    encrypt_passwords: true
    passdb_backend: tdbsam
    log_level: 1
    max_log_size: 1000
```

**Command Flow:**
```bash
# 1. YAML processing by samba_manager.py
./scripts/2_post_install_config.sh --instructions config/samba.yaml --verbose

# 2. Samba share creation command with all parameters
./scripts/2_post_install_config_steps/13_configure_samba.sh add-share \
  --name shuttle_inbound \
  --path /var/shuttle/source \
  --comment "Shuttle inbound file submission area" \
  --browseable true \
  --read-only false \
  --guest-ok false \
  --valid-users "@shuttle_samba_in_users" \
  --write-list "@shuttle_samba_in_users" \
  --create-mask 0644 \
  --directory-mask 0755 \
  --force-user shuttle_runner \
  --force-group shuttle_data_owners \
  --vfs-objects "recycle audit" \
  --recycle-repository ".recycle" \
  --recycle-keeptree true \
  --audit-facility local5 \
  --audit-priority info \
  --verbose

# 3. _cmd_add_share.source.sh processes parameters
# - Validates path exists and is accessible
# - Backs up existing smb.conf
# - Generates share configuration block

# 4. Share configuration added to smb.conf
sudo tee -a /etc/samba/smb.conf << 'EOF'
[shuttle_inbound]
path = /var/shuttle/source
comment = Shuttle inbound file submission area
browseable = yes
read only = no
guest ok = no
valid users = @shuttle_samba_in_users
write list = @shuttle_samba_in_users
create mask = 0644
directory mask = 0755
force user = shuttle_runner
force group = shuttle_data_owners
vfs objects = recycle audit
recycle:repository = .recycle
recycle:keeptree = yes
audit:facility = local5
audit:priority = info
EOF

# 5. Configuration validation
sudo testparm -s

# 6. Service reload if validation passes
sudo systemctl reload smbd
```

##### Example 6: Adding Samba User with Password Management

**YAML Instruction Document:**
```yaml
---
type: user
user:
  name: alice
  samba:
    enabled: true
    # Password handled via separate secure process
    # password: "SecurePassword123!"  # Optional, not recommended in YAML
```

**Command Flow:**
```bash
# 1. User already exists in system (created by user management)
# 2. Samba user addition command
./scripts/2_post_install_config_steps/13_configure_samba.sh add-samba-user \
  --user alice \
  --verbose

# 3. _cmd_add_samba_user.source.sh execution
# - Prompts for password securely (not from YAML)
# - Or reads from secure environment variable

# 4. Samba user database update
sudo smbpasswd -a alice
# Password entered interactively or via stdin

# 5. Verification
sudo pdbedit -L | grep alice
```

#### Share Management
| Command         | _cmd_ File                     | Main Unix Commands                                 | Wizard/YAML Support |
|-----------------|--------------------------------|----------------------------------------------------|---------------------|
| `add-share`     | `_cmd_add_share.source.sh`     | `sudo tee -a /etc/samba/smb.conf`, `sudo testparm` | ✅ Full YAML support |
| `remove-share`  | `_cmd_remove_share.source.sh`  | `sudo sed -i`, `sudo testparm`                     | ✅ Share removal     |
| `list-shares`   | `_cmd_list_shares.source.sh`   | `sudo testparm -s`, `grep`                         | -                   |
| `show-share`    | `_cmd_show_share.source.sh`    | `sudo testparm -s`, `sed`                          | -                   |
| `enable-share`  | `_cmd_enable_share.source.sh`  | `sudo sed -i` (remove disabled)                    | -                   |
| `disable-share` | `_cmd_disable_share.source.sh` | `sudo sed -i` (add disabled)                       | -                   |

**Example YAML Configuration:**
```yaml
samba:
  enabled: true
  shares:
    shuttle_inbound:
      path: /var/shuttle/source
      comment: Shuttle inbound file submission
      read_only: false
      valid_users: "@shuttle_samba_in_users"
      write_list: "@shuttle_samba_in_users"
      create_mask: "0644"
      directory_mask: "0755"
      force_user: shuttle_runner
      force_group: shuttle_data_owners
  global_settings:
    workgroup: WORKGROUP
    server_string: Shuttle File Transfer Server
    security: user
```

**Example Command Execution:**
```bash
# Command generated from YAML
./13_configure_samba.sh add-share --name shuttle_inbound --path /var/shuttle/source --comment "Shuttle inbound file submission" --read-only false --valid-users "@shuttle_samba_in_users"

# Resulting Unix commands
sudo tee -a /etc/samba/smb.conf << 'EOF'
[shuttle_inbound]
path = /var/shuttle/source
comment = Shuttle inbound file submission
read only = no
valid users = @shuttle_samba_in_users
write list = @shuttle_samba_in_users
create mask = 0644
directory mask = 0755
force user = shuttle_runner
force group = shuttle_data_owners
EOF
sudo testparm -s
```

#### User Management
| Command              | _cmd_ File                          | Main Unix Commands  | Wizard/YAML Support     |
|----------------------|-------------------------------------|---------------------|-------------------------|
| `add-samba-user`     | `_cmd_add_samba_user.source.sh`     | `sudo smbpasswd -a` | ✅ Via user Samba config |
| `remove-samba-user`  | `_cmd_remove_samba_user.source.sh`  | `sudo smbpasswd -x` | ✅ User removal          |
| `set-samba-password` | `_cmd_set_samba_password.source.sh` | `sudo smbpasswd`    | -                       |
| `list-samba-users`   | `_cmd_list_samba_users.source.sh`   | `sudo pdbedit -L`   | -                       |
| `enable-samba-user`  | `_cmd_enable_samba_user.source.sh`  | `sudo smbpasswd -e` | -                       |
| `disable-samba-user` | `_cmd_disable_samba_user.source.sh` | `sudo smbpasswd -d` | -                       |

**Example YAML Configuration:**
```yaml
type: user
user:
  name: alice
  source: local
  account_type: interactive
  samba:
    enabled: true
    password: "secure123"  # Optional in YAML
```

**Example Command Execution:**
```bash
# Command generated from YAML (if password provided)
./13_configure_samba.sh add-samba-user --user alice --password "secure123"

# Resulting Unix command
echo -e "secure123\nsecure123" | sudo smbpasswd -a alice
```

##### Example 7: Managing Samba Services with Status Monitoring

**Command Flow:**
```bash
# 1. Service management commands
./scripts/2_post_install_config_steps/13_configure_samba.sh restart-samba --verbose

# 2. _cmd_restart_samba.source.sh execution
# - Stops services gracefully
# - Validates configuration
# - Starts services with monitoring

# 3. Unix commands executed
sudo systemctl stop smbd nmbd
sudo testparm -s  # Validate config before restart
sudo systemctl start smbd nmbd

# 4. Service status verification
sudo systemctl status smbd nmbd
sudo systemctl is-active smbd nmbd

# 5. Port listening verification
sudo netstat -tlnp | grep -E ":(445|139|137|138) "
```

#### Service Management
| Command         | _cmd_ File                     | Main Unix Commands                 | Wizard/YAML Support |
|-----------------|--------------------------------|------------------------------------|---------------------|
| `start-samba`   | `_cmd_start_samba.source.sh`   | `sudo systemctl start smbd nmbd`   | ✅ Service component |
| `stop-samba`    | `_cmd_stop_samba.source.sh`    | `sudo systemctl stop smbd nmbd`    | ✅ Service component |
| `restart-samba` | `_cmd_restart_samba.source.sh` | `sudo systemctl restart smbd nmbd` | ✅ Service component |
| `reload-samba`  | `_cmd_reload_samba.source.sh`  | `sudo systemctl reload smbd`       | ✅ Config reload     |
| `status-samba`  | `_cmd_status_samba.source.sh`  | `sudo systemctl status smbd nmbd`  | -                   |
| `test-config`   | `_cmd_test_config.source.sh`   | `sudo testparm`                    | ✅ Config validation |

---

## 3. Firewall Configuration (14_configure_firewall.sh)

### Available Commands (14 commands)

### Detailed Parameter Flow Examples

#### Firewall Management

##### Example 8: Complete Firewall Setup with Network Topology

**YAML Instruction Document:**
```yaml
---
type: firewall_config
firewall:
  enabled: true
  default_policy:
    incoming: deny
    outgoing: allow
    forward: deny
  logging: low
  rules:
    ssh_management:
      service: ssh
      action: allow
      sources: ["10.10.5.0/24", "172.16.100.0/24"]
      comment: SSH access from management networks
      ports: [22]
      protocol: tcp
    samba_clients:
      service: samba
      action: allow
      sources: ["192.168.1.0/24", "192.168.2.0/24"]
      comment: Samba access from client networks
      ports: [445, 139, 137, 138]
      protocol: both
    web_monitoring:
      service: http
      action: allow
      sources: ["10.10.5.100", "10.10.5.101"]
      comment: Web monitoring from specific servers
      ports: [80, 443]
      protocol: tcp
  network_topology:
    management_networks:
      - "10.10.5.0/24"
      - "172.16.100.0/24"
    client_networks:
      - "192.168.1.0/24"
      - "192.168.2.0/24"
    monitoring_hosts:
      - "10.10.5.100"
      - "10.10.5.101"
    isolated_hosts:
      - host: "192.168.1.50"
        allowed_services: ["samba"]
        comment: "Isolated file server - only Samba access"
```

**Command Flow:**
```bash
# 1. Firewall initialization
./scripts/2_post_install_config.sh --instructions config/firewall.yaml --verbose

# 2. Enable firewall with default policies
./scripts/2_post_install_config_steps/14_configure_firewall.sh enable-firewall \
  --default-incoming deny \
  --default-outgoing allow \
  --default-forward deny \
  --logging low \
  --verbose

# 3. _cmd_enable_firewall.source.sh execution
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw default deny forward
sudo ufw logging low
sudo ufw --force enable

# 4. SSH management rule
./scripts/2_post_install_config_steps/14_configure_firewall.sh allow-service-from \
  --service ssh \
  --sources "10.10.5.0/24,172.16.100.0/24" \
  --comment "SSH access from management networks" \
  --ports 22 \
  --protocol tcp

# 5. _cmd_allow_service_from.source.sh execution
sudo ufw allow from 10.10.5.0/24 to any port 22 proto tcp comment 'SSH access from management networks'
sudo ufw allow from 172.16.100.0/24 to any port 22 proto tcp comment 'SSH access from management networks'

# 6. Samba client access
./scripts/2_post_install_config_steps/14_configure_firewall.sh allow-samba-from \
  --source "192.168.1.0/24,192.168.2.0/24" \
  --comment "Samba access from client networks" \
  --protocol both

# 7. _cmd_allow_samba_from.source.sh execution (all Samba ports)
sudo ufw allow from 192.168.1.0/24 to any port 445 proto tcp comment 'Samba access from client networks'
sudo ufw allow from 192.168.1.0/24 to any port 139 proto tcp comment 'Samba access from client networks'
sudo ufw allow from 192.168.1.0/24 to any port 137 proto udp comment 'Samba access from client networks'
sudo ufw allow from 192.168.1.0/24 to any port 138 proto udp comment 'Samba access from client networks'
# (repeated for 192.168.2.0/24)

# 8. Host isolation
./scripts/2_post_install_config_steps/14_configure_firewall.sh isolate-host \
  --host 192.168.1.50 \
  --allowed-services samba \
  --comment "Isolated file server - only Samba access"

# 9. _cmd_isolate_host.source.sh execution
# First, allow Samba from this host
sudo ufw allow from 192.168.1.50 to any port 445 proto tcp comment 'Isolated file server - only Samba access'
sudo ufw allow from 192.168.1.50 to any port 139 proto tcp comment 'Isolated file server - only Samba access'
sudo ufw allow from 192.168.1.50 to any port 137 proto udp comment 'Isolated file server - only Samba access'
sudo ufw allow from 192.168.1.50 to any port 138 proto udp comment 'Isolated file server - only Samba access'
# Then, deny all other services from this host
sudo ufw deny from 192.168.1.50 to any port 22 comment 'Isolated host - SSH denied'
sudo ufw deny from 192.168.1.50 to any port 80 comment 'Isolated host - HTTP denied'
sudo ufw deny from 192.168.1.50 to any port 443 comment 'Isolated host - HTTPS denied'
```

##### Example 9: Complex Service-Based Firewall Rules

**YAML Instruction Document:**
```yaml
---
type: firewall_service_rules
firewall:
  service_rules:
    database_access:
      service: postgresql
      action: allow
      sources: ["10.10.10.0/24"]
      ports: [5432]
      protocol: tcp
      comment: Database access from application servers
      rate_limit: "5/minute"
    monitoring_snmp:
      service: snmp
      action: allow
      sources: ["10.10.5.200"]
      ports: [161]
      protocol: udp
      comment: SNMP monitoring from monitoring server
    backup_rsync:
      service: rsync
      action: allow
      sources: ["10.10.20.100"]
      ports: [873]
      protocol: tcp
      comment: Backup server rsync access
      time_restrictions:
        start: "02:00"
        end: "06:00"
```

**Command Flow:**
```bash
# 1. Service-specific rules with advanced options
./scripts/2_post_install_config_steps/14_configure_firewall.sh allow-service-from \
  --service postgresql \
  --sources "10.10.10.0/24" \
  --ports 5432 \
  --protocol tcp \
  --comment "Database access from application servers" \
  --rate-limit "5/minute"

# 2. _cmd_allow_service_from.source.sh with rate limiting
sudo ufw allow from 10.10.10.0/24 to any port 5432 proto tcp comment 'Database access from application servers'
# Rate limiting applied via ufw rate limiting syntax
sudo ufw limit from 10.10.10.0/24 to any port 5432 proto tcp

# 3. SNMP monitoring rule
./scripts/2_post_install_config_steps/14_configure_firewall.sh allow-service-from \
  --service snmp \
  --sources "10.10.5.200" \
  --ports 161 \
  --protocol udp \
  --comment "SNMP monitoring from monitoring server"

# 4. _cmd_allow_service_from.source.sh execution
sudo ufw allow from 10.10.5.200 to any port 161 proto udp comment 'SNMP monitoring from monitoring server'
```

#### Firewall Management
| Command                | _cmd_ File                            | Main Unix Commands                            | Wizard/YAML Support |
|------------------------|---------------------------------------|-----------------------------------------------|---------------------|
| `enable-firewall`      | `_cmd_enable_firewall.source.sh`      | `sudo ufw --force enable`, `sudo ufw default` | ✅ Full YAML support |
| `disable-firewall`     | `_cmd_disable_firewall.source.sh`     | `sudo ufw disable`                            | ✅ Component control |
| `detect-firewall`      | `_cmd_detect_firewall.source.sh`      | `command -v ufw/firewall-cmd/iptables`        | -                   |
| `show-status`          | `_cmd_show_status.source.sh`          | `sudo ufw status verbose`                     | -                   |
| `list-firewall-rules`  | `_cmd_list_firewall_rules.source.sh`  | `sudo ufw status numbered`                    | -                   |
| `delete-firewall-rule` | `_cmd_delete_firewall_rule.source.sh` | `sudo ufw delete`                             | -                   |

**Example YAML Configuration:**
```yaml
firewall:
  enabled: true
  default_policy:
    incoming: deny
    outgoing: allow
  logging: low
  rules:
    ssh_access:
      service: ssh
      action: allow
      sources: ["10.10.5.0/24"]
      comment: SSH administrative access
    samba_access:
      service: samba
      action: allow
      sources: ["192.168.1.0/24"]
      comment: Samba file sharing access
  network_topology:
    management_networks: ["10.10.5.0/24"]
    client_networks: ["192.168.1.0/24"]
    isolated_hosts: []
```

**Example Command Execution:**
```bash
# Commands generated from YAML
./14_configure_firewall.sh enable-firewall --default-policy deny --logging low
./14_configure_firewall.sh allow-service-from --service ssh --source "10.10.5.0/24" --comment "SSH administrative access"
./14_configure_firewall.sh allow-samba-from --source "192.168.1.0/24" --comment "Samba file sharing access"

# Resulting Unix commands
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw logging low
sudo ufw --force enable
sudo ufw allow from 10.10.5.0/24 to any port 22
sudo ufw allow from 192.168.1.0/24 to any port 445
sudo ufw allow from 192.168.1.0/24 to any port 139
sudo ufw allow from 192.168.1.0/24 to any port 137
sudo ufw allow from 192.168.1.0/24 to any port 138
```

#### Samba Access Control
| Command            | _cmd_ File                        | Main Unix Commands                                  | Wizard/YAML Support |
|--------------------|-----------------------------------|-----------------------------------------------------|---------------------|
| `allow-samba-from` | `_cmd_allow_samba_from.source.sh` | `sudo ufw allow from X to any port 445/139/137/138` | ✅ Full YAML support |
| `deny-samba-from`  | `_cmd_deny_samba_from.source.sh`  | `sudo ufw deny from X to any port 445/139/137/138`  | ✅ Rule generation   |
| `list-samba-rules` | `_cmd_list_samba_rules.source.sh` | `sudo ufw status \| grep -E "445\|139\|137\|138"`   | -                   |

#### Service Access Control
| Command              | _cmd_ File                          | Main Unix Commands                    | Wizard/YAML Support     |
|----------------------|-------------------------------------|---------------------------------------|-------------------------|
| `allow-service-from` | `_cmd_allow_service_from.source.sh` | `sudo ufw allow from X to any port Y` | ✅ Generic service rules |
| `deny-service-from`  | `_cmd_deny_service_from.source.sh`  | `sudo ufw deny from X to any port Y`  | ✅ Service blocking      |
| `list-service-rules` | `_cmd_list_service_rules.source.sh` | `sudo ufw status \| grep SERVICE`     | -                       |

##### Example 10: Advanced Host Isolation with Multiple Service Access

**YAML Instruction Document:**
```yaml
---
type: host_isolation
firewall:
  isolated_hosts:
    - host: "192.168.1.100"
      allowed_services: ["samba", "ssh"]
      comment: "File server with admin access"
      management_access: true
    - host: "192.168.1.101"
      allowed_services: ["samba"]
      comment: "Restricted file server"
      management_access: false
    - host: "192.168.1.200"
      allowed_services: ["http", "https"]
      comment: "Web server with limited access"
      management_access: false
```

**Command Flow:**
```bash
# 1. File server with admin access
./scripts/2_post_install_config_steps/14_configure_firewall.sh isolate-host \
  --host 192.168.1.100 \
  --allowed-services "samba,ssh" \
  --comment "File server with admin access" \
  --management-access

# 2. _cmd_isolate_host.source.sh execution
# Allow specified services
sudo ufw allow from 192.168.1.100 to any port 445 proto tcp comment 'File server with admin access'
sudo ufw allow from 192.168.1.100 to any port 139 proto tcp comment 'File server with admin access'
sudo ufw allow from 192.168.1.100 to any port 137 proto udp comment 'File server with admin access'
sudo ufw allow from 192.168.1.100 to any port 138 proto udp comment 'File server with admin access'
sudo ufw allow from 192.168.1.100 to any port 22 proto tcp comment 'File server with admin access'

# Deny all other common services
sudo ufw deny from 192.168.1.100 to any port 80 comment 'Isolated host - HTTP denied'
sudo ufw deny from 192.168.1.100 to any port 443 comment 'Isolated host - HTTPS denied'
sudo ufw deny from 192.168.1.100 to any port 25 comment 'Isolated host - SMTP denied'
sudo ufw deny from 192.168.1.100 to any port 110 comment 'Isolated host - POP3 denied'
sudo ufw deny from 192.168.1.100 to any port 143 comment 'Isolated host - IMAP denied'

# 3. Restricted file server (Samba only)
./scripts/2_post_install_config_steps/14_configure_firewall.sh isolate-host \
  --host 192.168.1.101 \
  --allowed-services "samba" \
  --comment "Restricted file server"

# 4. _cmd_isolate_host.source.sh execution
# Allow only Samba ports
sudo ufw allow from 192.168.1.101 to any port 445 proto tcp comment 'Restricted file server'
sudo ufw allow from 192.168.1.101 to any port 139 proto tcp comment 'Restricted file server'
sudo ufw allow from 192.168.1.101 to any port 137 proto udp comment 'Restricted file server'
sudo ufw allow from 192.168.1.101 to any port 138 proto udp comment 'Restricted file server'

# Deny all other services including SSH
sudo ufw deny from 192.168.1.101 to any port 22 comment 'Isolated host - SSH denied'
sudo ufw deny from 192.168.1.101 to any port 80 comment 'Isolated host - HTTP denied'
sudo ufw deny from 192.168.1.101 to any port 443 comment 'Isolated host - HTTPS denied'
# ... (all other common services denied)

# 5. Verification commands
./scripts/2_post_install_config_steps/14_configure_firewall.sh list-isolated-hosts
./scripts/2_post_install_config_steps/14_configure_firewall.sh list-firewall-rules --format detailed
```

#### Host Isolation
| Command               | _cmd_ File                           | Main Unix Commands                         | Wizard/YAML Support |
|-----------------------|--------------------------------------|--------------------------------------------|---------------------|
| `isolate-host`        | `_cmd_isolate_host.source.sh`        | Multiple `sudo ufw deny from X` rules      | ✅ Network topology  |
| `unisolate-host`      | `_cmd_unisolate_host.source.sh`      | `sudo ufw delete` rules for host           | ✅ Topology changes  |
| `list-isolated-hosts` | `_cmd_list_isolated_hosts.source.sh` | `sudo ufw status \| parse isolation rules` | -                   |

---

## 4. Package Installation (11_install_tools.sh)

| Component          | Main Unix Commands                            | Wizard/YAML Support       |
|--------------------|-----------------------------------------------|---------------------------|
| Samba Installation | `sudo apt-get install samba samba-common-bin` | ✅ install_samba component |
| ACL Tools          | `sudo apt-get install acl`                    | ✅ install_acl component   |

**Example YAML Configuration:**
```yaml
components:
  install_samba: true
  install_acl: true
  configure_users_groups: true
  configure_samba: true
  configure_firewall: true
```

---

## 5. Wizard and YAML Integration

### Wizard Modes

#### Development Mode
- Creates single admin user with full access
- Disables firewall by default
- Minimal security boundaries
- **Generated YAML**: Single user, all groups, no firewall rules

#### Standard/Production Mode
- Creates service accounts and proper isolation
- Enables firewall with network topology
- Production security model
- **Generated YAML**: Multiple users, all groups, firewall rules, Samba shares

#### Custom Mode
- Full interactive configuration builder
- All functionality available
- **Generated YAML**: User-customized configuration

### Domain User Integration Flow

1. **Wizard Detection**: Detects domain users by pattern (dots, @, backslashes)
2. **Configuration Check**: Validates domain import configuration exists
3. **Template Generation**: Creates domain_import.conf if needed
4. **Integration**: Adds domain users to YAML with import commands

### Example Complete YAML Configuration

```yaml
---
version: '1.0'
metadata:
  description: Shuttle post-install user configuration
  environment: production
  generated_by: Configuration Wizard
  created: '2024-01-15T10:30:00Z'
  mode: standard
settings:
  create_home_directories: true
  backup_existing_users: true
  validate_before_apply: true
components:
  install_samba: true
  install_acl: true
  configure_users_groups: true
  configure_samba: true
  configure_firewall: true
samba:
  enabled: true
  shares:
    shuttle_inbound:
      path: /var/shuttle/source
      comment: Shuttle inbound file submission
      read_only: false
      valid_users: "@shuttle_samba_in_users"
firewall:
  enabled: true
  default_policy:
    incoming: deny
    outgoing: allow
  rules:
    ssh_access:
      service: ssh
      action: allow
      sources: ["10.10.5.0/24"]
    samba_access:
      service: samba
      action: allow
      sources: ["192.168.1.0/24"]
  network_topology:
    management_networks: ["10.10.5.0/24"]
    client_networks: ["192.168.1.0/24"]

---
type: group
group:
  name: shuttle_admins
  description: Administrative users with full shuttle access
  gid: 5000

---
type: user
user:
  name: shuttle_runner
  description: Main application service account
  source: local
  account_type: service
  groups:
    primary: shuttle_runners
    secondary: ["shuttle_config_readers", "shuttle_data_owners"]
  shell: /usr/sbin/nologin
  home_directory: /var/lib/shuttle/shuttle_runner
  create_home: true

---
type: user
user:
  name: alice.domain
  description: Domain user account
  source: domain
  account_type: interactive
  groups:
    primary: engineering
    secondary: ["developers", "sudo"]
  shell: /bin/bash
  home_directory: /home/alice.domain
  create_home: true

---
type: path
path:
  location: /var/shuttle/source
  owner: shuttle_runner
  group: shuttle_data_owners
  mode: "0755"
  acls:
    - "g:shuttle_samba_in_users:rwx"
```

---

## 6. Test Scenarios

---

## Complete Orchestration Examples

### Example 11: End-to-End Production Deployment

**Master YAML Configuration (shuttle_production_config.yaml):**
```yaml
---
version: '2.0'
metadata:
  description: Complete Shuttle Production Deployment
  environment: production
  generated_by: Configuration Wizard
  created: '2024-01-15T10:30:00Z'
  deployment_mode: standard
  
settings:
  create_home_directories: true
  backup_existing_configs: true
  validate_before_apply: true
  
components:
  install_samba: true
  install_acl: true
  configure_users_groups: true
  configure_samba: true
  configure_firewall: true
  
installation_order:
  - groups
  - users
  - paths
  - samba
  - firewall
  
# Include separate configuration files
includes:
  - groups.yaml
  - users.yaml
  - paths.yaml
  - samba.yaml
  - firewall.yaml
  - domain_users.yaml
```

**Complete Command Orchestration:**
```bash
# 1. Master deployment command
./scripts/2_post_install_config.sh \
  --instructions config/shuttle_production_config.yaml \
  --verbose \
  --validate-only  # First validation pass

# 2. Actual deployment (after validation)
./scripts/2_post_install_config.sh \
  --instructions config/shuttle_production_config.yaml \
  --verbose

# 3. Groups creation phase (from groups.yaml)
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-group \
  --group shuttle_runners --gid 5000 --description "Shuttle service runners"
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-group \
  --group shuttle_data_owners --gid 5001 --description "Shuttle data owners"
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-group \
  --group shuttle_samba_in_users --gid 5002 --description "Samba inbound users"
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-group \
  --group shuttle_admins --gid 5003 --description "Shuttle administrators"

# 4. Service user creation phase (from users.yaml)
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-user \
  --user shuttle_runner \
  --uid 5000 \
  --description "Main shuttle service account" \
  --primary-group shuttle_runners \
  --secondary-groups "shuttle_data_owners" \
  --shell /usr/sbin/nologin \
  --home /var/lib/shuttle/shuttle_runner \
  --create-home \
  --account-type service

# 5. Interactive user creation
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-user \
  --user admin \
  --uid 10000 \
  --description "Shuttle administrator" \
  --primary-group shuttle_admins \
  --secondary-groups "sudo,shuttle_data_owners" \
  --shell /bin/bash \
  --home /home/admin \
  --create-home \
  --account-type interactive

# 6. Domain user import phase (from domain_users.yaml)
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \
  --username alice.corp \
  --primary-group shuttle_samba_in_users \
  --secondary-groups "shuttle_data_owners" \
  --command-config /etc/shuttle/domain_import.conf

# 7. Path creation and ACL setup phase (from paths.yaml)
./scripts/2_post_install_config_steps/12_users_and_groups.sh set-path-owner \
  --path /var/shuttle/source \
  --owner shuttle_runner \
  --group shuttle_data_owners
./scripts/2_post_install_config_steps/12_users_and_groups.sh set-path-permissions \
  --path /var/shuttle/source \
  --mode 2775
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-acl-to-path \
  --path /var/shuttle/source \
  --acl "g:shuttle_samba_in_users:rwx" \
  --recursive

# 8. Samba configuration phase (from samba.yaml)
./scripts/2_post_install_config_steps/13_configure_samba.sh add-share \
  --name shuttle_inbound \
  --path /var/shuttle/source \
  --comment "Shuttle file intake" \
  --valid-users "@shuttle_samba_in_users" \
  --write-list "@shuttle_samba_in_users" \
  --create-mask 0664 \
  --directory-mask 2775 \
  --force-user shuttle_runner \
  --force-group shuttle_data_owners

# 9. Samba user setup
./scripts/2_post_install_config_steps/13_configure_samba.sh add-samba-user \
  --user alice.corp  # Password setup handled separately

# 10. Firewall configuration phase (from firewall.yaml)
./scripts/2_post_install_config_steps/14_configure_firewall.sh enable-firewall \
  --default-incoming deny \
  --default-outgoing allow \
  --logging low

./scripts/2_post_install_config_steps/14_configure_firewall.sh allow-service-from \
  --service ssh \
  --sources "10.10.5.0/24" \
  --comment "SSH admin access"

./scripts/2_post_install_config_steps/14_configure_firewall.sh allow-samba-from \
  --source "192.168.1.0/24" \
  --comment "Samba client access"

# 11. Service startup and validation
./scripts/2_post_install_config_steps/13_configure_samba.sh restart-samba
./scripts/2_post_install_config_steps/13_configure_samba.sh test-config
./scripts/2_post_install_config_steps/14_configure_firewall.sh show-status
```

**Unix Commands Generated (Complete Flow):**
```bash
# Groups
sudo groupadd --gid 5000 shuttle_runners
sudo groupadd --gid 5001 shuttle_data_owners
sudo groupadd --gid 5002 shuttle_samba_in_users
sudo groupadd --gid 5003 shuttle_admins

# Service Account
sudo useradd --uid 5000 --gid shuttle_runners --groups shuttle_data_owners \
  --shell /usr/sbin/nologin --home-dir /var/lib/shuttle/shuttle_runner \
  --create-home --comment "Main shuttle service account" shuttle_runner

# Interactive Admin
sudo useradd --uid 10000 --gid shuttle_admins --groups sudo,shuttle_data_owners \
  --shell /bin/bash --home-dir /home/admin --create-home \
  --comment "Shuttle administrator" admin

# Domain User Import
sudo /opt/corporate/bin/import-domain-user --username alice.corp \
  --uid 70001 --home /home/alice.corp --shell /bin/bash \
  --primary-group shuttle_samba_in_users --groups shuttle_data_owners

# Path Setup
sudo mkdir -p /var/shuttle/source /var/shuttle/destination /var/shuttle/quarantine
sudo chown shuttle_runner:shuttle_data_owners /var/shuttle/source
sudo chmod 2775 /var/shuttle/source
sudo setfacl -R -m g:shuttle_samba_in_users:rwx /var/shuttle/source
sudo setfacl -R -d -m g:shuttle_samba_in_users:rwx /var/shuttle/source

# Samba Configuration
sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.backup.$(date +%Y%m%d_%H%M%S)
sudo tee -a /etc/samba/smb.conf << 'EOF'
[shuttle_inbound]
path = /var/shuttle/source
comment = Shuttle file intake
valid users = @shuttle_samba_in_users
write list = @shuttle_samba_in_users
create mask = 0664
directory mask = 2775
force user = shuttle_runner
force group = shuttle_data_owners
EOF
sudo testparm -s
sudo smbpasswd -a alice.corp

# Firewall Rules
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw logging low
sudo ufw allow from 10.10.5.0/24 to any port 22 proto tcp comment 'SSH admin access'
sudo ufw allow from 192.168.1.0/24 to any port 445 proto tcp comment 'Samba client access'
sudo ufw allow from 192.168.1.0/24 to any port 139 proto tcp comment 'Samba client access'
sudo ufw allow from 192.168.1.0/24 to any port 137 proto udp comment 'Samba client access'
sudo ufw allow from 192.168.1.0/24 to any port 138 proto udp comment 'Samba client access'
sudo ufw --force enable

# Service Management
sudo systemctl restart smbd nmbd
sudo systemctl enable smbd nmbd
```

### Test Scenario 1: Complete Standard Deployment
```bash
# 1. Run wizard to generate YAML
cd /path/to/shuttle/config
python3 -m post_install_config_wizard --shuttle-config-path shuttle_config.yaml

# 2. Apply configuration with dry-run
cd /path/to/shuttle
./scripts/2_post_install_config.sh --instructions config/shuttle_post_install_config_20240115_103000.yaml --dry-run --verbose

# Expected: Complete dry-run output showing all commands that would be executed
```

### Test Scenario 2: Domain User Import
```bash
# 1. Create domain configuration
./scripts/2_post_install_config_steps/12_users_and_groups.sh generate-domain-config --output-dir /etc/shuttle --interactive

# 2. Import domain user
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user --username alice.domain --primary-group engineering --dry-run --verbose

# Expected: Shows domain import command execution (dry-run)
```

### Test Scenario 3: Samba Configuration
```bash
# 1. Configure Samba share
./scripts/2_post_install_config_steps/13_configure_samba.sh add-share --name test-share --path /tmp/test --comment "Test share" --dry-run --verbose

# 2. Add Samba user
./scripts/2_post_install_config_steps/13_configure_samba.sh add-samba-user --user testuser --dry-run --verbose

# Expected: Shows smb.conf modification and smbpasswd commands (dry-run)
```

### Example 12: Parameter Validation and Error Handling

**Invalid Configuration Testing:**
```bash
# 1. Test invalid user parameters
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-user \
  --user "invalid user" \
  --uid -1 \
  --shell /nonexistent/shell \
  --dry-run --verbose

# Expected validation errors:
# - Username contains spaces (invalid)
# - UID is negative (invalid)
# - Shell doesn't exist (warning)

# 2. Test invalid firewall parameters
./scripts/2_post_install_config_steps/14_configure_firewall.sh allow-samba-from \
  --source "999.999.999.999" \
  --ports "invalid" \
  --protocol "invalid" \
  --dry-run --verbose

# Expected validation errors:
# - Invalid IP address format
# - Invalid port specification
# - Invalid protocol (must be tcp, udp, or both)

# 3. Test invalid path parameters
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-acl-to-path \
  --path "/nonexistent/path" \
  --acl "invalid:format" \
  --dry-run --verbose

# Expected validation errors:
# - Path doesn't exist
# - Invalid ACL format

# 4. Test domain user import without configuration
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \
  --username domain.user \
  --dry-run --verbose

# Expected validation errors:
# - Domain configuration not found
# - Import command not configured
```

**Parameter Flow Validation:**
```bash
# 1. Comprehensive parameter tracing
./scripts/2_post_install_config_steps/12_users_and_groups.sh add-user \
  --user testuser \
  --uid 15000 \
  --description "Test User Account" \
  --primary-group developers \
  --secondary-groups "sudo,docker" \
  --shell /bin/bash \
  --home /home/testuser \
  --create-home \
  --dry-run --verbose

# Expected parameter tracing output:
# [TRACE] Command: add-user
# [TRACE] Parameters received: --user testuser --uid 15000 ...
# [TRACE] Parsed parameters:
#   - user: testuser
#   - uid: 15000
#   - description: Test User Account
#   - primary_group: developers
#   - secondary_groups: sudo,docker
#   - shell: /bin/bash
#   - home: /home/testuser
#   - create_home: true
# [TRACE] Validation passed
# [TRACE] Generated command: sudo useradd --uid 15000 --gid developers ...
# [DRY RUN] Would execute: sudo useradd --uid 15000 --gid developers --groups sudo,docker --shell /bin/bash --home-dir /home/testuser --create-home --comment "Test User Account" testuser
```

### Test Scenario 4: Firewall Configuration
```bash
# 1. Enable firewall
./scripts/2_post_install_config_steps/14_configure_firewall.sh enable-firewall --dry-run --verbose

# 2. Configure Samba access
./scripts/2_post_install_config_steps/14_configure_firewall.sh allow-samba-from --source "192.168.1.0/24" --comment "Internal LAN" --dry-run --verbose

# Expected: Shows UFW commands for firewall setup and Samba rules (dry-run)
```

---

---

## Complete Testing Framework

### Automated Test Suite Design

**Test Categories:**
1. **Unit Tests**: Individual _cmd_*.source.sh function testing
2. **Integration Tests**: Full wizard → YAML → Unix command flow
3. **Validation Tests**: Parameter validation and error handling
4. **Security Tests**: Permission and access control verification
5. **Performance Tests**: Large-scale deployment scenarios

**Test Implementation Strategy:**
```bash
# 1. Unit test framework
#!/bin/bash
# test_cmd_add_user.sh
source ../scripts/2_post_install_config_steps/lib/_cmd_add_user.source.sh

# Mock functions for testing
sudo() { echo "[MOCK] sudo $*"; }
execute_or_dryrun() { echo "[MOCK] $1"; }

# Test cases
test_add_user_basic() {
    DRY_RUN=true
    cmd_add_user "testuser" "1000" "Test User" "users" "" "/bin/bash" "/home/testuser" "true"
    # Verify expected output
}

test_add_user_with_groups() {
    DRY_RUN=true
    cmd_add_user "testuser" "1000" "Test User" "users" "sudo,docker" "/bin/bash" "/home/testuser" "true"
    # Verify group handling
}

# 2. Integration test framework
#!/bin/bash
# test_integration_user_creation.sh

# Create test YAML
cat > test_user.yaml << 'EOF'
---
type: user
user:
  name: integration_test_user
  source: local
  account_type: interactive
  uid: 19999
  groups:
    primary: test_group
    secondary: ["sudo"]
EOF

# Run integration test
./scripts/2_post_install_config.sh --instructions test_user.yaml --dry-run --verbose

# Verify output contains expected commands
grep -q "sudo useradd.*integration_test_user" output.log
grep -q "--uid 19999" output.log
grep -q "--gid test_group" output.log

# 3. Validation test framework
#!/bin/bash
# test_validation.sh

# Test invalid parameters
test_invalid_uid() {
    result=$(./scripts/2_post_install_config_steps/12_users_and_groups.sh add-user --user test --uid -1 --dry-run 2>&1)
    if [[ $result =~ "Invalid UID" ]]; then
        echo "PASS: Invalid UID validation"
    else
        echo "FAIL: Invalid UID validation"
    fi
}

test_invalid_ip() {
    result=$(./scripts/2_post_install_config_steps/14_configure_firewall.sh allow-samba-from --source "999.999.999.999" --dry-run 2>&1)
    if [[ $result =~ "Invalid IP address" ]]; then
        echo "PASS: Invalid IP validation"
    else
        echo "FAIL: Invalid IP validation"
    fi
}

# 4. Security test framework
#!/bin/bash
# test_security.sh

# Test permission restrictions
test_dangerous_path_protection() {
    result=$(./scripts/2_post_install_config_steps/12_users_and_groups.sh add-acl-to-path --path "/etc/passwd" --acl "u:test:rwx" --dry-run 2>&1)
    if [[ $result =~ "Dangerous path" ]]; then
        echo "PASS: Dangerous path protection"
    else
        echo "FAIL: Dangerous path protection"
    fi
}

test_service_account_shell() {
    result=$(./scripts/2_post_install_config_steps/12_users_and_groups.sh add-user --user service_test --account-type service --dry-run)
    if [[ $result =~ "nologin" ]]; then
        echo "PASS: Service account shell restriction"
    else
        echo "FAIL: Service account shell restriction"
    fi
}
```

### Test Execution Commands

**Complete Test Suite:**
```bash
# Run all tests
./tests/run_all_tests.sh

# Run specific test categories
./tests/run_unit_tests.sh
./tests/run_integration_tests.sh
./tests/run_validation_tests.sh
./tests/run_security_tests.sh

# Run tests with different verbosity levels
./tests/run_all_tests.sh --verbose
./tests/run_all_tests.sh --dry-run
./tests/run_all_tests.sh --trace

# Performance testing
./tests/run_performance_tests.sh --users 100 --groups 50 --threads 4
```

**Test Coverage Goals:**
- **Unit Tests**: 100% coverage of all _cmd_*.source.sh functions
- **Integration Tests**: All wizard modes and YAML configurations
- **Validation Tests**: All parameter validation scenarios
- **Security Tests**: All security boundaries and restrictions
- **Performance Tests**: Large-scale deployment scenarios

---

## 7. Command Implementation Status

### Fully Implemented with YAML Support ✅
- User/Group creation and management
- ACL configuration 
- Domain user import
- Samba share and user configuration
- Firewall rule management
- Service component control

### Command-Line Only (No YAML orchestration) ⚠️
- List/show commands (informational)
- Service status commands
- Configuration testing commands
- Individual rule deletion commands

### Key Integration Points
1. **wizard → YAML**: Interactive configuration generates declarative YAML
2. **YAML → Python managers**: samba_manager.py and firewall_manager.py process YAML
3. **Python → Shell scripts**: Managers call main scripts with appropriate parameters
4. **Shell → _cmd_ files**: Main scripts dispatch to specific command implementations
5. **_cmd_ → Unix**: Command files execute actual system commands

This architecture provides comprehensive testing coverage from high-level wizard functionality down to individual Unix command execution.