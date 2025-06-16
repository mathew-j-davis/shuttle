# Production Environment Configuration Script Planning

## Overview
This script will provide an interactive, guided setup for Shuttle production environments, similar to how `install.sh` works for initial installation. It will orchestrate the individual configuration scripts in `scripts/2_production_environment_steps/`.

## Script: `configure_production_environment.sh`

### Purpose
- Interactive wizard for production environment setup
- Guide users through security, networking, and automation configuration
- Call individual configuration scripts with appropriate parameters
- Support both fresh setup and incremental changes
- Provide clear next steps and validation

### Core Design Principles
1. **Interactive First**: Guide users through choices with sensible defaults
2. **Modular**: Users can choose which components to configure
3. **Safe**: Always offer dry-run and backup options
4. **Flexible**: Support different lab requirements and environments
5. **Documented**: Generate configuration summaries and next steps

### Command Line Interface

```bash
./scripts/configure_production_environment.sh [OPTIONS]

Options:
  --areas AREAS             Comma-separated list of areas to configure:
                            1|user    = Users and Groups
                            2|smb     = Samba File Shares  
                            3|fw      = Firewall Rules
                            4|cron    = Scheduled Jobs
                            5|mon     = Monitoring Setup
  --non-interactive         Use defaults or fail (for automation)
  --config-file FILE        Load configuration from file
  --dry-run                 Show what would be done without making changes
  --skip-prerequisites      Skip prerequisite checks
  --help                    Show help message

Examples:
  # Interactive full setup
  ./configure_production_environment.sh

  # Configure only users and Samba (numeric)
  ./configure_production_environment.sh --areas 1,2

  # Configure only users and Samba (named)
  ./configure_production_environment.sh --areas user,smb

  # Mixed notation supported
  ./configure_production_environment.sh --areas user,2,fw

  # Flexible comma usage (trailing commas ignored)
  ./configure_production_environment.sh --areas user,smb,,,,,

  # Non-interactive with config file
  ./configure_production_environment.sh --non-interactive --config-file prod.yaml
```

### Configuration Areas

#### 1. Users and Groups
- Service account creation (local vs domain)
- Permission groups setup
- **Writer permissions configuration** (NEW):
  - Write-only (secure default, no read)
  - Read-write (for software that needs verification)
  - Lab-specific configurations
- Password management
- Verification steps

#### 2. Samba File Shares
- Share creation with security modes
- Permission configuration based on user choices
- Audit logging setup
- Multiple share types:
  - Processing share (full access)
  - Submission share (configurable read permissions)
  - Admin share (optional)

#### 3. Firewall Configuration
- Auto-detect firewall type (ufw/firewalld)
- Open required Samba ports
- Optional SSH restrictions
- Network interface binding

#### 4. Scheduled Jobs (Cron)
- Shuttle processing schedule
- Defender testing schedule
- Cleanup and maintenance tasks
- Environment variable setup
- Lock file management

#### 5. Monitoring and Alerts
- Log rotation configuration
- Disk space monitoring
- Email alert setup
- Processing metrics
- Audit log configuration

### Interactive Flow

#### Welcome and Overview
```
=========================================
  Shuttle Production Environment Setup   
=========================================

This wizard will help you configure:
• Service accounts and permissions
• Network file shares (Samba)
• Security and firewall rules
• Automated processing schedules
• Monitoring and alerting

=== Permission Check ===
Checking system permissions and tool availability...

✓ Sudo access: Available
✓ User management: Available (useradd, groupadd)
✓ Samba: Installed, admin access available
✓ Firewall: ufw detected, sudo access available
✓ Domain integration: Not configured
⚠ ACL support: Unknown (will test on target filesystem)

Press ENTER for defaults shown in [brackets]
Type 'x' to exit at any prompt
```

#### Area Selection
```
=== Configuration Areas ===

Select what to configure:
1) Users and Groups - Service accounts and permissions  [user]
2) Samba Shares - Network file access                   [smb]
3) Firewall - Security rules                            [fw]
4) Scheduled Jobs - Automation                          [cron]
5) Monitoring - Alerts and logging                      [mon]
6) All areas (recommended for new setup)

Your choice [6]: 
```

#### Area Parsing Logic
```bash
# Parse --areas parameter with flexible syntax
parse_areas() {
    local areas_input="$1"
    
    # Reset configuration flags
    CONFIGURE_USERS=false
    CONFIGURE_SAMBA=false
    CONFIGURE_FIREWALL=false
    CONFIGURE_CRON=false
    CONFIGURE_MONITORING=false
    
    # Handle empty or "all" case
    if [[ -z "$areas_input" ]] || [[ "$areas_input" == "all" ]] || [[ "$areas_input" == "6" ]]; then
        CONFIGURE_USERS=true
        CONFIGURE_SAMBA=true
        CONFIGURE_FIREWALL=true
        CONFIGURE_CRON=true
        CONFIGURE_MONITORING=true
        return 0
    fi
    
    # Split by comma and process each area
    IFS=',' read -ra AREAS <<< "$areas_input"
    for area in "${AREAS[@]}"; do
        # Trim whitespace and skip empty entries
        area=$(echo "$area" | xargs)
        [[ -z "$area" ]] && continue
        
        case "$area" in
            1|user|users)
                CONFIGURE_USERS=true
                echo "Selected: Users and Groups"
                ;;
            2|smb|samba)
                CONFIGURE_SAMBA=true
                echo "Selected: Samba File Shares"
                ;;
            3|fw|firewall)
                CONFIGURE_FIREWALL=true
                echo "Selected: Firewall Rules"
                ;;
            4|cron|schedule|jobs)
                CONFIGURE_CRON=true
                echo "Selected: Scheduled Jobs"
                ;;
            5|mon|monitor|monitoring)
                CONFIGURE_MONITORING=true
                echo "Selected: Monitoring Setup"
                ;;
            *)
                echo "Warning: Unknown area '$area' (valid: 1|user, 2|smb, 3|fw, 4|cron, 5|mon)"
                ;;
        esac
    done
}

# Example usage:
# parse_areas "user,smb"      # Configure users and Samba
# parse_areas "1,2,,,,"       # Same as above, with trailing commas
# parse_areas "user,2,fw"     # Mixed notation
# parse_areas ""              # All areas (default)
```

#### User Configuration Flow
```
=== User Configuration ===

User account type:
1) Local Linux accounts (standalone)
2) Domain accounts (AD/LDAP)
Choice [1]: 

Service accounts:
Processing account [sa-shuttle-run]: 
Writer account [sa-shuttle-lab]: 

=== Writer Permissions ===
Some file transfer software needs to read files
after writing to verify successful transfer.

Writer account permissions:
1) Write-only (more secure, cannot read)
2) Read-write (can verify transfers)
Choice [1]: 

Lab-specific configuration:
Do you have different labs with different requirements? [y/N]:
```

#### Samba Configuration Flow
```
=== Samba Share Configuration ===

Share location [/srv/data/shuttle/inbox]: 
Share name [shuttle-inbox]: 

Based on your writer permissions (write-only):
→ Creating secure write-only submission share
→ Creating full-access processing share

Additional options:
Enable audit logging? [Y/n]: 
Backup existing config? [Y/n]: 
```

#### Validation and Summary
```
=== Configuration Summary ===

✓ Users and Groups
  - Type: Local
  - Processing: sa-shuttle-run
  - Writer: sa-shuttle-lab (write-only)
  
✓ Samba Shares
  - Path: /srv/data/shuttle/inbox
  - Audit: Enabled
  
✓ Firewall
  - Type: ufw
  - Samba ports will be opened
  
Ready to configure? [Y/n]: 
```

### Lab-Specific Configuration Support

#### Configuration File Format
```yaml
# lab-config.yaml
labs:
  - name: "Lab A - Sequencing"
    writer_user: "sa-lab-a"
    permissions: "write-only"
    share_name: "lab-a-inbox"
    
  - name: "Lab B - Analysis" 
    writer_user: "sa-lab-b"
    permissions: "read-write"  # Their software needs read
    share_name: "lab-b-inbox"
    
  - name: "Lab C - External"
    writer_user: "CORP\svc_lab_c"
    permissions: "write-only"
    share_name: "lab-c-inbox"
    domain_user: true
```

#### Interactive Lab Setup
```
=== Lab-Specific Configuration ===

Number of labs to configure [1]: 3

Lab 1:
  Name: Sequencing Lab
  Writer account [sa-shuttle-lab-1]: sa-seq-lab
  Permissions (write-only/read-write) [write-only]: 
  Share name [seq-lab-inbox]: 

Lab 2:
  Name: Analysis Lab
  Writer account [sa-shuttle-lab-2]: sa-analysis-lab
  Permissions (write-only/read-write) [write-only]: read-write
  Share name [analysis-lab-inbox]: 
```

### Script Orchestration

#### Script Dependencies
```
scripts/2_production_environment_steps/
├── 11_configure_firewall.sh        # (to be created)
├── 12_configure_users.sh           # Main user/group setup
├── 13_configure_smb.sh             # Samba configuration
├── 14_configure_cron.sh            # (to be created)
├── 15_configure_monitoring.sh      # (to be created)
└── 16_validate_configuration.sh    # (to be created)
```

#### Parameter Passing Examples
```bash
# User configuration with write-only
./12_configure_users.sh \
  --local \
  --processor-user sa-shuttle-run \
  --writer-user sa-shuttle-lab \
  --writer-permissions write-only

# Samba with write-only security
./13_configure_smb.sh \
  --share-path /srv/data/shuttle/inbox \
  --no-read \
  --audit \
  --service-user sa-shuttle-run \
  --write-user sa-shuttle-lab
```

### Error Handling

#### Prerequisites Check
- Verify sudo access levels
- Check tool permissions and availability
- Check if scripts exist and are executable
- Verify no conflicting configuration
- Test domain connectivity (if domain mode)

#### Permission Levels and Tool Access
Different tools require different permission levels:

**1. Can run without sudo:**
- `id`, `groups` - Check user information
- `getent` - Query user/group databases
- `smbclient -L` - List shares (with credentials)

**2. Requires sudo for full functionality:**
- `useradd`, `groupadd` - User/group creation
- `usermod` - Modify users
- `setfacl` - Set ACLs (may work without sudo on owned files)
- `systemctl restart smbd` - Service management
- `ufw`, `firewall-cmd` - Firewall configuration

**3. May not work even with sudo:**
- Domain operations if not domain-joined
- Samba operations if Samba not installed
- Firewall commands if firewall not installed/enabled
- ACL commands if filesystem doesn't support ACLs

**4. Requires specific group membership:**
- `smbpasswd` - May require 'sambashare' group
- `crontab` - May be restricted by /etc/cron.allow
- Docker commands - Requires 'docker' group
- Systemd user services - May require 'systemd-journal' group

#### Permission Checking Strategy

**1. Check Tool Availability:**
```bash
# Basic tools (required)
check_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "❌ $1 not found"
    return 1
  fi
  echo "✓ $1 available"
}

# Check basic tools
check_tool sudo || MISSING_TOOLS+=("sudo")
check_tool useradd || MISSING_TOOLS+=("useradd") 
check_tool smbpasswd || MISSING_TOOLS+=("samba")
```

**2. Check Permission Levels:**
```bash
# Test sudo access
test_sudo() {
  if sudo -n true 2>/dev/null; then
    echo "✓ Sudo: Passwordless access"
    return 0
  elif sudo -v 2>/dev/null; then
    echo "✓ Sudo: Available with password"
    return 0
  else
    echo "❌ Sudo: No access"
    return 1
  fi
}

# Test specific operations
test_user_management() {
  if sudo -n useradd --dry-run test-user 2>/dev/null; then
    echo "✓ User management: Full access"
    return 0
  else
    echo "⚠ User management: May require password"
    return 1
  fi
}
```

**3. Check Service Permissions:**
```bash
# Test Samba management
test_samba_admin() {
  if sudo -n systemctl status smbd >/dev/null 2>&1; then
    echo "✓ Samba: Admin access available"
    return 0
  elif systemctl --user status >/dev/null 2>&1; then
    echo "⚠ Samba: User-level access only"
    return 1
  else
    echo "❌ Samba: No service access"
    return 2
  fi
}

# Test firewall access
test_firewall_access() {
  if command -v ufw >/dev/null 2>&1; then
    if sudo -n ufw status >/dev/null 2>&1; then
      echo "✓ Firewall (ufw): Admin access"
      return 0
    else
      echo "⚠ Firewall (ufw): Requires sudo password"
      return 1
    fi
  elif command -v firewall-cmd >/dev/null 2>&1; then
    if sudo -n firewall-cmd --state >/dev/null 2>&1; then
      echo "✓ Firewall (firewalld): Admin access"
      return 0
    else
      echo "⚠ Firewall (firewalld): Requires sudo password"
      return 1
    fi
  else
    echo "❌ Firewall: No supported firewall found"
    return 2
  fi
}
```

**4. Check Domain Integration:**
```bash
# Test domain connectivity
test_domain_access() {
  # Check if domain-joined
  if command -v realm >/dev/null 2>&1; then
    if realm list 2>/dev/null | grep -q domain; then
      echo "✓ Domain: System is domain-joined"
      return 0
    fi
  fi
  
  # Check winbind
  if command -v wbinfo >/dev/null 2>&1; then
    if wbinfo -t 2>/dev/null; then
      echo "✓ Domain: Winbind trust available"
      return 0
    fi
  fi
  
  # Check SSSD
  if systemctl is-active sssd >/dev/null 2>&1; then
    echo "✓ Domain: SSSD active"
    return 0
  fi
  
  echo "⚠ Domain: Not configured"
  return 1
}
```

**5. Graceful Degradation:**
```bash
# Handle missing permissions
handle_permission_failure() {
  local tool="$1"
  local operation="$2"
  
  case "$tool" in
    "useradd")
      echo "Cannot create users automatically."
      echo "Manual steps required:"
      echo "  sudo useradd -r -s /usr/sbin/nologin sa-shuttle-run"
      echo "  sudo groupadd shuttle-processors"
      MANUAL_STEPS+=("user_creation")
      ;;
    "samba")
      echo "Cannot configure Samba automatically."
      echo "Manual configuration required:"
      echo "  Edit /etc/samba/smb.conf"
      echo "  sudo systemctl restart smbd"
      MANUAL_STEPS+=("samba_config")
      ;;
    "firewall")
      echo "Cannot configure firewall automatically."
      echo "Manual firewall rules needed:"
      echo "  sudo ufw allow samba"
      MANUAL_STEPS+=("firewall_config")
      ;;
  esac
}
```

#### Rollback Support
- Create backups before changes
- Track all modifications
- Provide rollback instructions
- Test configurations before committing

#### Common Issues
- Existing users/groups
- Samba already configured
- Firewall conflicts
- Domain trust issues

### Output and Documentation

#### Configuration Summary File
```
production_setup_$(date +%Y%m%d_%H%M%S).txt
- All choices made
- Commands executed
- Next steps required
- Troubleshooting tips
```

#### Generated Documentation
```
/etc/shuttle/production/
├── setup_summary.txt
├── user_configuration.txt
├── samba_shares.txt
├── firewall_rules.txt
├── cron_schedules.txt
└── monitoring_config.txt
```

### Advanced Features

#### Multi-Environment Support
- Development mode (relaxed security)
- Staging mode (production-like)
- Production mode (full security)

#### Integration Modes
- Standalone server
- Domain-integrated
- Cloud-ready (future)

#### Automation Support
- Export configuration for Ansible
- Generate Terraform resources
- Create Docker configurations

### Testing Strategy

#### Dry Run Mode
- Show all commands without execution
- Validate prerequisites
- Check for conflicts
- Generate report

#### Validation Steps
- Test user creation
- Verify Samba connectivity
- Check firewall rules
- Validate cron syntax
- Test monitoring alerts

### Security Considerations

#### Secure Defaults
- Write-only permissions by default
- Audit logging enabled
- Service accounts with no shell
- Minimal firewall openings

#### Compliance Features
- Configuration change tracking
- Audit trail generation
- Security report creation
- Regular review reminders

### Future Enhancements

#### Phase 2 Features
- Kubernetes deployment support
- Cloud storage integration
- Multi-site replication
- Advanced monitoring dashboards

#### Integration Points
- SIEM integration
- Backup system hooks
- Ticketing system alerts
- Compliance reporting

This master script will make production deployment consistent, secure, and well-documented while supporting the diverse needs of different labs and their file transfer software requirements.