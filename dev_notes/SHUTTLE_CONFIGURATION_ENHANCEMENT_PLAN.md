# Shuttle Configuration Enhancement Plan

## Overview

This document outlines a comprehensive plan to extend the Shuttle post-install configuration wizard and installation process to support advanced Samba and firewall configuration, including host-specific access controls and isolated host scenarios.

## Current State Analysis

### Existing Capabilities

#### ✅ **Comprehensive Foundation (40 Command Libraries)**

**User Management (15 capabilities)**
- Complete user lifecycle: add, modify, delete, list, show
- Domain support: Auto-detection of winbind/sssd domains
- Advanced features: Account locking, expiration, home directory management
- Output formats: Simple, detailed, CSV, JSON with extensive filtering

**Group Management (10 capabilities)**  
- Full group lifecycle with membership management
- User-to-group relationship handling
- Safety features: Member validation, file ownership checks

**Samba Management (12 capabilities)**
- User account management: Add, remove, enable, disable Samba users
- Share management: Create, configure, enable, disable shares
- Service lifecycle: Start, stop, restart, reload, status, config testing
- Security: Secure password handling, configuration validation

**Firewall Management (5 capabilities)**
- Multi-firewall support: UFW, firewalld, iptables auto-detection
- Samba-specific rules: Allow/deny from specific sources
- Network support: CIDR notation, IP ranges, host-based rules
- Status and rule listing capabilities

**Path Management (8 capabilities)**
- Permissions: File/directory mode setting with advanced options
- Ownership: User/group ownership with recursive operations
- ACLs: Add, remove, show Access Control Lists
- Comprehensive path analysis and validation

#### ✅ **Solid Infrastructure**
- **Logging**: Complete dry-run and verbose support across all capabilities
- **Validation**: Comprehensive input validation and security protection
- **Error Handling**: Standardized error messages and recovery mechanisms
- **Cross-platform**: Support for major Linux distributions and macOS

### Current Gaps and Limitations

#### ❌ **Wizard Integration Gaps**
- **No Samba Configuration Section**: Wizard doesn't configure shares, access controls, or host restrictions
- **Limited Firewall Integration**: Basic firewall checking only, no rule configuration
- **No Network Topology Support**: Can't define isolated hosts vs. normal network access
- **Missing Service Integration**: Samba and firewall rules aren't coordinated

#### ❌ **Configuration Schema Limitations**
- **YAML Schema**: No structure for Samba shares, firewall rules, or host-based access
- **Network Definitions**: No way to define network segments or host categories
- **Service Coordination**: No linkage between Samba shares and firewall access

#### ❌ **Advanced Feature Gaps**
- **Host Isolation**: No capability to allow specific services while denying others per host
- **Rule Management**: Missing bulk rule operations, rule priorities, and conflict resolution
- **Service Discovery**: No automatic network scanning or service detection

## Enhancement Plan

### Phase 1: Core Infrastructure Enhancements

#### 1.1 Configuration Schema Extensions

**YAML Structure Additions:**
```yaml
# Network topology definitions
network:
  topology: "mixed"  # isolated, mixed, open
  segments:
    - name: "isolated_hosts"
      description: "Hosts that need Samba access only"
      hosts: ["192.168.1.100", "192.168.1.101"]
      default_policy: "deny_all"
    - name: "normal_hosts" 
      description: "Regular network hosts"
      hosts: ["192.168.1.0/24"]
      default_policy: "allow_normal"
      exclusions: ["192.168.1.100", "192.168.1.101"]

# Samba configuration
samba:
  global_settings:
    workgroup: "WORKGROUP"
    security: "user"
    map_to_guest: "Bad User"
    log_level: 2
  
  shares:
    - name: "shuttle_data"
      path: "/home/shuttle/shared"
      comment: "Shuttle file transfer data"
      read_only: false
      browseable: true
      guest_ok: false
      valid_users: ["shuttle_user", "@shuttle_group"]
      admin_users: ["shuttle_admin"]
      create_mask: "0664"
      directory_mask: "0775"
      access_control:
        allowed_hosts: ["isolated_hosts"]  # Reference to network segment
        denied_hosts: []
        allowed_users: ["shuttle_user"]
        denied_users: ["guest"]

# Firewall configuration  
firewall:
  engine: "auto"  # auto, ufw, firewalld, iptables
  default_policy: "deny"
  
  service_definitions:
    samba:
      ports: [139, 445]
      protocol: "tcp"
      description: "Samba file sharing"
    ssh:
      ports: [22]
      protocol: "tcp" 
      description: "SSH remote access"
    http:
      ports: [80, 443]
      protocol: "tcp"
      description: "Web services"
  
  host_rules:
    - hosts: ["isolated_hosts"]  # Reference to network segment
      allow_services: ["samba"]
      deny_services: ["*"]
      priority: 100
      comment: "Isolated hosts - Samba only"
    
    - hosts: ["normal_hosts"]
      deny_services: ["samba"]
      allow_services: ["ssh", "http"]
      priority: 200  
      comment: "Normal hosts - No Samba access"
  
  custom_rules:
    - action: "allow"
      source: "192.168.1.50"
      destination: "any"
      service: "ssh"
      comment: "Admin workstation SSH access"
```

#### 1.2 Command Library Extensions

**New Firewall Commands:**
```bash
# Network segment management
_cmd_add_network_segment.source.sh
_cmd_remove_network_segment.source.sh  
_cmd_list_network_segments.source.sh
_cmd_show_network_segment.source.sh

# Service-based rule management
_cmd_allow_service_from.source.sh
_cmd_deny_service_from.source.sh
_cmd_list_service_rules.source.sh

# Advanced firewall operations
_cmd_clear_firewall_rules.source.sh
_cmd_save_firewall_rules.source.sh
_cmd_restore_firewall_rules.source.sh
_cmd_test_firewall_connectivity.source.sh

# Host isolation management  
_cmd_isolate_host.source.sh
_cmd_unisolate_host.source.sh
_cmd_list_isolated_hosts.source.sh
```

**Enhanced Samba Commands:**
```bash
# Share-firewall integration
_cmd_add_share_with_firewall.source.sh
_cmd_modify_share_firewall.source.sh
_cmd_show_share_access.source.sh

# Bulk operations
_cmd_bulk_add_samba_users.source.sh
_cmd_bulk_configure_shares.source.sh

# Access testing
_cmd_test_samba_access.source.sh
_cmd_validate_samba_config.source.sh
```

#### 1.3 Integration Layer Development

**Service Coordinator Module:**
```python
# scripts/_setup_lib_py/service_coordinator.py
class ServiceCoordinator:
    def coordinate_samba_firewall(self, share_config, firewall_config):
        """Ensure Samba shares and firewall rules are synchronized"""
        
    def validate_network_topology(self, network_config):
        """Validate network segment definitions and host assignments"""
        
    def apply_host_isolation(self, host, allowed_services):
        """Apply isolation rules for specific hosts"""
        
    def test_service_connectivity(self, source_host, target_service):
        """Test connectivity from source to service after rule application"""
```

### Phase 2: Wizard Enhancement

#### 2.1 New Wizard Sections

**Network Topology Configuration:**
```
🌐 NETWORK TOPOLOGY CONFIGURATION

Define your network structure and access policies:

1. Network Layout:
   [ ] Simple (all hosts equal access)
   [x] Mixed (some hosts have restricted access)  
   [ ] Isolated (all hosts have custom access rules)

2. Host Categories:
   📍 Isolated Hosts (Samba access only):
      - 192.168.1.100 (production-server)
      - 192.168.1.101 (backup-server)
   
   📍 Normal Hosts (regular network access):
      - 192.168.1.0/24 (excluding isolated hosts)

3. Default Policies:
   ✅ Isolated hosts: Allow Samba, Deny all others
   ✅ Normal hosts: Deny Samba, Allow SSH/HTTP
```

**Samba Share Configuration:**
```
📁 SAMBA SHARE CONFIGURATION

Configure file sharing and access control:

1. Share Definitions:
   Share Name: shuttle_data
   Share Path: /home/shuttle/shared
   Description: Shuttle file transfer data
   
   Access Control:
   ✅ Allowed Users: shuttle_user, @shuttle_group
   ✅ Allowed Hosts: isolated_hosts (192.168.1.100-101)
   ❌ Guest Access: Disabled
   
   Permissions:
   📁 Directory: 0775 (rwxrwxr-x)
   📄 Files: 0664 (rw-rw-r--)

2. Share Security:
   [x] Create firewall rules automatically
   [x] Restrict access to defined hosts only
   [ ] Allow guest access (not recommended)
```

**Firewall Rules Configuration:**
```
🔥 FIREWALL RULES CONFIGURATION

Configure host-based access controls:

1. Service Access Rules:
   
   🏠 Isolated Hosts (192.168.1.100-101):
   ✅ Samba (139, 445/tcp) - File sharing access
   ❌ SSH (22/tcp) - Blocked for security
   ❌ HTTP (80, 443/tcp) - Blocked for security
   ❌ All Other Services - Default deny
   
   🌐 Normal Hosts (192.168.1.0/24):
   ❌ Samba (139, 445/tcp) - Prevent data access  
   ✅ SSH (22/tcp) - Administrative access
   ✅ HTTP (80, 443/tcp) - Web services
   ✅ Other Services - Default allow

2. Custom Rules:
   [ ] Add custom rule for admin workstation
   [ ] Add temporary access rules
   [ ] Add port forwarding rules
```

#### 2.2 Wizard Flow Integration

**Enhanced Configuration Flow:**
```
1. Basic Configuration (existing)
   - Environment selection
   - Users and groups
   - Path permissions

2. 🆕 Network Topology (new)
   - Define host categories
   - Set default access policies
   - Validate network structure

3. 🆕 Samba Configuration (new)
   - Configure shares and paths
   - Define user access controls  
   - Set host-based restrictions

4. 🆕 Firewall Integration (new)
   - Review service access rules
   - Configure host isolation
   - Validate rule consistency

5. 🆕 Security Validation (enhanced)
   - Test network connectivity
   - Validate access controls
   - Generate security report
```

#### 2.3 Interactive Features

**Network Discovery:**
```python
def discover_network_hosts(self):
    """Scan local network and suggest host categorization"""
    # Use nmap, ping sweeps, ARP tables
    # Suggest isolated vs normal host assignments
    # Detect existing Samba servers and potential conflicts
```

**Access Testing:**
```python
def test_access_scenarios(self):
    """Test access control scenarios before applying"""
    # Simulate connections from different host categories
    # Validate rule effectiveness
    # Provide connectivity reports
```

**Conflict Detection:**
```python
def detect_rule_conflicts(self):
    """Identify conflicting firewall and Samba rules"""
    # Check for overlapping rules
    # Identify potential security gaps
    # Suggest rule optimization
```

### Phase 3: Advanced Features

#### 3.1 Host Isolation Templates

**Predefined Isolation Scenarios:**
```yaml
isolation_templates:
  strict_data_server:
    description: "Server with Samba access only"
    allowed_services: ["samba"]
    denied_services: ["*"]
    monitoring: true
    
  secure_workstation:
    description: "Workstation with limited service access"
    allowed_services: ["samba", "ssh"]
    denied_services: ["http", "ftp"]
    time_restrictions:
      - "09:00-17:00 Monday-Friday"
      
  backup_server:
    description: "Backup server with scheduled access"
    allowed_services: ["samba", "rsync"]
    denied_services: ["*"]
    schedule_based: true
    backup_windows:
      - "02:00-04:00 daily"
```

#### 3.2 Dynamic Rule Management

**Adaptive Firewall Rules:**
```python
class DynamicRuleManager:
    def add_temporary_access(self, host, service, duration):
        """Grant temporary access with automatic expiration"""
        
    def emergency_access_mode(self, enabled=True):
        """Enable/disable emergency access mode"""
        
    def schedule_rule_changes(self, rules, schedule):
        """Schedule firewall rule changes"""
        
    def monitor_access_patterns(self):
        """Monitor and analyze access patterns for rule optimization"""
```

#### 3.3 Monitoring and Alerting

**Access Monitoring:**
```python
class AccessMonitor:
    def log_connection_attempts(self, source, destination, service):
        """Log all connection attempts for analysis"""
        
    def detect_anomalous_access(self):
        """Detect unusual access patterns"""
        
    def generate_access_reports(self, period="daily"):
        """Generate access reports and security summaries"""
        
    def alert_on_violations(self, violation_type):
        """Send alerts for security violations"""
```

#### 3.4 Configuration Management

**Version Control and Rollback:**
```python
class ConfigurationManager:
    def save_configuration_snapshot(self, description):
        """Save current configuration state"""
        
    def restore_configuration(self, snapshot_id):
        """Restore previous configuration"""
        
    def compare_configurations(self, snapshot1, snapshot2):
        """Compare configuration differences"""
        
    def validate_configuration_consistency(self):
        """Ensure all configurations are consistent"""
```

### Phase 4: Integration and Testing

#### 4.1 End-to-End Testing Framework

**Automated Testing:**
```bash
# Test scripts for validation
test_isolated_host_access.sh     # Verify isolated hosts can only access Samba
test_normal_host_restrictions.sh # Verify normal hosts cannot access Samba  
test_rule_conflict_detection.sh  # Test conflict detection algorithms
test_emergency_access.sh         # Test emergency access procedures
```

**Integration Testing:**
```python
class IntegrationTestSuite:
    def test_wizard_to_deployment(self):
        """Test complete wizard-to-deployment flow"""
        
    def test_configuration_consistency(self):
        """Test consistency across all configuration files"""
        
    def test_rollback_procedures(self):
        """Test configuration rollback capabilities"""
        
    def test_multi_host_scenarios(self):
        """Test complex multi-host access scenarios"""
```

#### 4.2 Performance Optimization

**Rule Optimization:**
```python
class RuleOptimizer:
    def optimize_firewall_rules(self, rules):
        """Optimize firewall rules for performance"""
        
    def minimize_rule_conflicts(self, rules):
        """Minimize rule conflicts and overlaps"""
        
    def suggest_rule_consolidation(self, rules):
        """Suggest rule consolidation opportunities"""
```

#### 4.3 Documentation and Training

**Enhanced Documentation:**
- **Network Topology Guide**: How to design secure network layouts
- **Host Isolation Best Practices**: Security recommendations for isolated hosts
- **Troubleshooting Guide**: Common issues and solutions
- **Security Audit Checklist**: Validation procedures for configurations

**Interactive Tutorials:**
- **Wizard Walkthrough**: Step-by-step configuration guide
- **Security Scenarios**: Common security setup examples
- **Emergency Procedures**: How to handle security incidents

## Implementation Timeline

### Week 1-2: Foundation
- [ ] Extend YAML configuration schema
- [ ] Create network topology validation
- [ ] Implement basic service coordinator

### Week 3-4: Command Extensions  
- [ ] Develop new firewall command libraries
- [ ] Enhance Samba integration commands
- [ ] Implement host isolation functions

### Week 5-6: Wizard Enhancement
- [ ] Add network topology wizard section
- [ ] Implement Samba configuration wizard
- [ ] Integrate firewall rule configuration

### Week 7-8: Advanced Features
- [ ] Develop dynamic rule management
- [ ] Implement access monitoring
- [ ] Create configuration management tools

### Week 9-10: Integration and Testing
- [ ] End-to-end testing framework
- [ ] Performance optimization
- [ ] Documentation and tutorials

## Success Criteria

### Functional Requirements
- ✅ **Host Isolation**: Successfully isolate hosts to specific services
- ✅ **Service Control**: Granular control over service access per host
- ✅ **Configuration Consistency**: All components work together seamlessly
- ✅ **Security Validation**: Comprehensive security testing and validation

### User Experience Requirements  
- ✅ **Intuitive Wizard**: Easy-to-use configuration interface
- ✅ **Clear Feedback**: Comprehensive dry-run and verbose output
- ✅ **Error Recovery**: Graceful error handling and rollback capabilities
- ✅ **Documentation**: Complete documentation and examples

### Technical Requirements
- ✅ **Cross-Platform**: Support for major Linux distributions
- ✅ **Performance**: Efficient rule application and management
- ✅ **Extensibility**: Easy to add new services and rule types
- ✅ **Maintainability**: Clean, well-documented code structure

## Risk Mitigation

### Security Risks
- **Configuration Errors**: Comprehensive validation and testing
- **Rule Conflicts**: Automated conflict detection and resolution
- **Access Bypass**: Multi-layer validation and monitoring

### Operational Risks
- **Service Disruption**: Careful rollout procedures and rollback capabilities
- **Performance Impact**: Rule optimization and performance testing
- **User Confusion**: Clear documentation and intuitive interfaces

### Technical Risks
- **Platform Compatibility**: Extensive cross-platform testing
- **Integration Issues**: Comprehensive integration testing
- **Scalability Concerns**: Performance testing with large rule sets

This enhancement plan provides a comprehensive roadmap for extending Shuttle's configuration capabilities to support advanced Samba and firewall management with host-specific access controls. The phased approach ensures manageable development while building on the strong foundation of existing capabilities.