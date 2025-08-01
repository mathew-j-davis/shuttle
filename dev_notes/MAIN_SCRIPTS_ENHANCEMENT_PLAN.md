# Main Scripts Enhancement Plan

## Overview

This document outlines the specific enhancements needed for the four main orchestration scripts to integrate our new service-based firewall commands and host isolation capabilities.

## Current State Analysis

### ✅ **11_install_tools.sh** - System Tool Installation
**Current Focus**: Installs Samba/winbind and ACL tools  
**Current Commands**: Package installation and verification only  
**Status**: Well-implemented, minimal changes needed

### ✅ **12_users_and_groups.sh** - User/Group Management
**Current Focus**: User and group lifecycle management  
**Current Commands**: 22 user/group commands with excellent safety features  
**Status**: Complete for user/group management, no firewall integration needed

### ✅ **13_configure_samba.sh** - Samba Management
**Current Focus**: Samba shares, users, and service management  
**Current Commands**: 17 Samba-specific commands  
**Status**: Missing firewall integration for shares

### ❌ **14_configure_firewall.sh** - Firewall Management
**Current Focus**: Basic Samba allow/deny rules  
**Current Commands**: Only 5 basic commands, many missing implementations  
**Status**: Needs major enhancement with our new commands

## Enhancement Plan by Script

### 1. **11_install_tools.sh** - Minor Enhancements

#### **Add Firewall Tool Detection and Installation**

**New Options:**
```bash
--install-firewall-tools    # Install firewall management tools
--no-firewall-tools        # Skip firewall tools installation
```

**New Package Mappings:**
```bash
# Define package mapping for firewall tools
declare -A firewall_packages
firewall_packages[apt]="ufw iptables-persistent"
firewall_packages[dnf]="firewalld iptables-services"
firewall_packages[yum]="firewalld iptables-services"
firewall_packages[pacman]="ufw iptables"
firewall_packages[zypper]="ufw iptables"
firewall_packages[brew]=""  # Not applicable
firewall_packages[default]="iptables"
```

**New Verification Commands:**
```bash
# Verify firewall tools
if [[ "$INSTALL_FIREWALL_TOOLS" == "true" ]]; then
    log INFO "Verifying firewall tools installation..."
    if ! check_tool_with_version "iptables" "iptables --version" "iptables firewall tool"; then
        all_tools_ok=false
    fi
    # Check for UFW or firewalld
    if command -v ufw >/dev/null 2>&1; then
        log INFO "UFW detected and available"
    elif command -v firewall-cmd >/dev/null 2>&1; then
        log INFO "firewalld detected and available"
    else
        log WARN "No high-level firewall manager detected (ufw/firewalld)"
    fi
fi
```

---

### 2. **12_users_and_groups.sh** - No Changes Needed

This script is focused on user and group management and doesn't need firewall integration. The existing 22 commands provide comprehensive user/group functionality.

---

### 3. **13_configure_samba.sh** - Major Enhancements

#### **Add New Share-Firewall Integration Commands**

**New Commands to Add:**
```bash
# Add to sourced libraries
source "$SCRIPT_DIR/lib/_cmd_add_share_with_firewall.source.sh"
source "$SCRIPT_DIR/lib/_cmd_modify_share_firewall.source.sh"
source "$SCRIPT_DIR/lib/_cmd_show_share_access.source.sh"
source "$SCRIPT_DIR/lib/_cmd_test_samba_access.source.sh"
```

**Enhanced Command Dispatcher:**
```bash
case "$COMMAND" in
    # Existing commands...
    
    # New integrated commands
    "add-share-with-firewall")
        cmd_add_share_with_firewall "$@"
        ;;
    "modify-share-firewall")
        cmd_modify_share_firewall "$@"
        ;;
    "show-share-access")
        cmd_show_share_access "$@"
        ;;
    "test-samba-access")
        cmd_test_samba_access "$@"
        ;;
    # ... existing commands
esac
```

**Updated Usage Documentation:**
```
Share Management:
  add-share                   Create a new Samba share
  add-share-with-firewall     Create share and configure firewall rules
  modify-share-firewall       Modify firewall rules for existing share
  remove-share                Remove an existing Samba share
  show-share                  Display details of a specific share
  show-share-access           Show share details including firewall rules
  test-samba-access           Test Samba connectivity from specific hosts

Examples:
  # Create share with automatic firewall configuration
  $SCRIPT_NAME add-share-with-firewall --name "data" --path "/srv/data" \
    --allow-hosts "192.168.1.100,192.168.1.101" \
    --comment "Isolated file server access"
  
  # Test access from isolated host
  $SCRIPT_NAME test-samba-access --share "data" --from-host "192.168.1.100"
```

---

### 4. **14_configure_firewall.sh** - Complete Overhaul

#### **Add All New Service-Based Commands**

**New Source Libraries:**
```bash
# Add to existing sources
source "$SCRIPT_DIR/lib/_cmd_allow_service_from.source.sh"
source "$SCRIPT_DIR/lib/_cmd_deny_service_from.source.sh"
source "$SCRIPT_DIR/lib/_cmd_list_service_rules.source.sh"
source "$SCRIPT_DIR/lib/_cmd_isolate_host.source.sh"
source "$SCRIPT_DIR/lib/_cmd_unisolate_host.source.sh"
source "$SCRIPT_DIR/lib/_cmd_list_isolated_hosts.source.sh"
```

**Complete Command Dispatcher Overhaul:**
```bash
case "$COMMAND" in
    # Legacy Samba commands (keep for backward compatibility)
    "allow-samba-from")
        cmd_allow_samba_from "$@"
        ;;
    "deny-samba-from")
        cmd_deny_samba_from "$@"
        ;;
    "list-samba-rules")
        cmd_list_samba_rules "$@"
        ;;
    
    # New service-based commands
    "allow-service-from")
        cmd_allow_service_from "$@"
        ;;
    "deny-service-from")
        cmd_deny_service_from "$@"
        ;;
    "list-service-rules")
        cmd_list_service_rules "$@"
        ;;
    
    # Host isolation commands
    "isolate-host")
        cmd_isolate_host "$@"
        ;;
    "unisolate-host")
        cmd_unisolate_host "$@"
        ;;
    "list-isolated-hosts")
        cmd_list_isolated_hosts "$@"
        ;;
    
    # Basic firewall commands
    "detect-firewall")
        cmd_detect_firewall "$@"
        ;;
    "show-status")
        cmd_show_status "$@"
        ;;
    
    # TODO: Implement these missing commands
    "enable-firewall")
        cmd_enable_firewall "$@"
        ;;
    "disable-firewall")
        cmd_disable_firewall "$@"
        ;;
    "allow-port")
        cmd_allow_port "$@"
        ;;
    "deny-port")
        cmd_deny_port "$@"
        ;;
    "list-rules")
        cmd_list_rules "$@"
        ;;
    "save-rules")
        cmd_save_rules "$@"
        ;;
    "clear-samba-rules")
        cmd_clear_samba_rules "$@"
        ;;
esac
```

**Updated Usage Documentation:**
```
Service Access Control:
  allow-service-from         Allow specific service from specific hosts
  deny-service-from          Deny specific service from specific hosts
  list-service-rules         List firewall rules for specific services

Host Isolation:
  isolate-host               Isolate host to allow only specific services
  unisolate-host             Remove isolation rules for a host
  list-isolated-hosts        List currently isolated hosts

Legacy Samba Commands (deprecated - use service commands):
  allow-samba-from           Allow Samba access from specific IP/network
  deny-samba-from            Deny Samba access from specific IP/network
  list-samba-rules           List current Samba firewall rules

Examples:
  # Your exact use case - isolate host to Samba only
  $SCRIPT_NAME isolate-host --host 192.168.1.100 --allow-services samba
  
  # Deny Samba from normal network, allow other services
  $SCRIPT_NAME deny-service-from --service samba --source 192.168.1.0/24
  $SCRIPT_NAME allow-service-from --service ssh --source 192.168.1.0/24
  $SCRIPT_NAME allow-service-from --service http --source 192.168.1.0/24
  
  # List all isolated hosts
  $SCRIPT_NAME list-isolated-hosts --format detailed
```

## Implementation Priority

### **Phase 1: Core Functionality (High Priority)**
1. ✅ **Complete**: New _cmd*.sh files created and tested
2. **Enhance 14_configure_firewall.sh**: Add all new commands to dispatcher
3. **Enhance 13_configure_samba.sh**: Add firewall integration commands
4. **Test integration**: Verify all commands work through main scripts

### **Phase 2: Advanced Features (Medium Priority)**
5. **Enhance 11_install_tools.sh**: Add firewall tools installation
6. **Create missing commands**: Implement remaining firewall commands
7. **Add bulk operations**: Create commands for multiple hosts/services

### **Phase 3: Integration (Lower Priority)**
8. **YAML integration**: Connect to configuration files
9. **Wizard integration**: Add to post-install wizard
10. **Documentation**: Update all help and documentation

## Required New Command Files to Create

### **For 13_configure_samba.sh Integration**
```bash
_cmd_add_share_with_firewall.source.sh      # Create share + firewall rules
_cmd_modify_share_firewall.source.sh        # Modify share firewall rules
_cmd_show_share_access.source.sh            # Show share + firewall details
_cmd_test_samba_access.source.sh            # Test Samba connectivity
```

### **For 14_configure_firewall.sh Missing Commands**
```bash
_cmd_enable_firewall.source.sh              # Enable firewall service
_cmd_disable_firewall.source.sh             # Disable firewall service
_cmd_allow_port.source.sh                   # Allow specific port access
_cmd_deny_port.source.sh                    # Deny specific port access
_cmd_list_rules.source.sh                   # List all firewall rules
_cmd_save_rules.source.sh                   # Save/persist rules
_cmd_clear_samba_rules.source.sh            # Clear all Samba rules
```

## Testing Strategy

### **Unit Testing**
```bash
# Test individual commands
./scripts/2_post_install_config_steps/14_configure_firewall.sh isolate-host --help
./scripts/2_post_install_config_steps/14_configure_firewall.sh isolate-host --dry-run --verbose \
  --host 192.168.1.100 --allow-services samba,ping

# Test Samba integration
./scripts/2_post_install_config_steps/13_configure_samba.sh add-share-with-firewall --help
```

### **Integration Testing**
```bash
# Test your exact use case end-to-end
./scripts/2_post_install_config.sh --dry-run --verbose

# Test isolated host scenario
./scripts/2_post_install_config_steps/14_configure_firewall.sh isolate-host \
  --host 192.168.1.100 --allow-services samba --dry-run

# Test normal host restrictions
./scripts/2_post_install_config_steps/14_configure_firewall.sh deny-service-from \
  --service samba --source 192.168.1.0/24 --dry-run
```

## Benefits of This Approach

### **✅ Backward Compatibility**
- All existing commands continue to work
- Legacy Samba commands remain functional
- Existing scripts don't break

### **✅ Incremental Enhancement**
- Can implement and test each script individually
- No need to change multiple scripts simultaneously
- Clear migration path from legacy to new commands

### **✅ User Experience**
- Consistent command interface across all scripts
- Comprehensive help documentation
- Safe testing with --dry-run mode

### **✅ Your Use Case Ready**
Once implemented, your exact scenario becomes:
```bash
# Isolate hosts to Samba only
./scripts/2_post_install_config_steps/14_configure_firewall.sh isolate-host \
  --host 192.168.1.100 --allow-services samba

# Deny Samba from normal network
./scripts/2_post_install_config_steps/14_configure_firewall.sh deny-service-from \
  --service samba --source 192.168.1.0/24

# Allow normal services for regular hosts
./scripts/2_post_install_config_steps/14_configure_firewall.sh allow-service-from \
  --service ssh,http --source 192.168.1.0/24
```

This approach provides a complete solution that integrates seamlessly with your existing infrastructure while adding the advanced host isolation capabilities you need.