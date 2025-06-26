# Shuttle Production User/Group Security Model

## Core Design Principles

1. **Separation of Duties**: Different roles have different access levels
2. **Least Privilege**: Users only get access they need for their function
3. **Directory Ownership**: Each critical directory has a dedicated owning group
4. **Role-based Groups**: Users inherit permissions through group membership
5. **Samba Integration**: Network access controlled separately from local access

## Complete User/Group Model

### Service Users (System Accounts)
```yaml
service_users:
  shuttle_runner:
    description: "Main shuttle application service account"
    groups:
      primary: shuttle_runners
      secondary: []
    
  shuttle_defender_test_runner:
    description: "Defender testing service account - tests defender with production config"
    groups:
      primary: shuttle_defender_test_runners
      secondary: []
    special_access:
      - "Write access to ledger file for tracking defender versions"
    
  shuttle_tester:
    description: "General shuttle testing and validation account"
    groups:
      primary: shuttle_testers
      secondary: []
```

### Human Users (Interactive Accounts)
```yaml
human_users:
  shuttle_admin:
    description: "System administrator for shuttle"
    groups:
      primary: shuttle_admin
      secondary: [shuttle_config_writers, shuttle_runners]
    
  shuttle_operator:
    description: "Day-to-day shuttle operations"
    groups:
      primary: shuttle_operators  
      secondary: [shuttle_config_readers, shuttle_runners]
    
  shuttle_samba_in_user:
    description: "Inbound file submission user via Samba"
    groups:
      primary: shuttle_samba_in_users
      secondary: []
    
  shuttle_out_user:
    description: "Outbound file retrieval user (domain account)"
    groups:
      primary: shuttle_out_users
      secondary: []
    
  cyber_analyst:
    description: "Security analyst for malware review"
    groups:
      primary: shuttle_cyber_ops
      secondary: [shuttle_config_readers]
```

### Directory Ownership Groups
```yaml
directory_owners:
  shuttle_in_owners:
    description: "Owns source/incoming directory"
    gid: 5001
    members: [shuttle_runner, shuttle_admin]
    
  shuttle_quarantine_owners:  
    description: "Owns quarantine directory"
    gid: 5002
    members: [shuttle_runner, shuttle_admin]
    
  shuttle_destination_owners:
    description: "Owns destination/clean files directory" 
    gid: 5003
    members: [shuttle_runner, shuttle_admin]
    
  shuttle_hazard_owners:
    description: "Owns hazard/malware archive directory"
    gid: 5004
    members: [shuttle_runner, shuttle_admin, cyber_analyst]
    
  shuttle_log_owners:
    description: "Owns log directory"
    gid: 5005  
    members: [shuttle_runner, shuttle_admin, shuttle_operator]
    
  shuttle_ledger_owners:
    description: "Owns defender version ledger file"
    gid: 5006
    members: [shuttle_defender_test_runner, shuttle_admin]
```

### Functional Role Groups
```yaml
functional_groups:
  shuttle_runners:
    description: "Can execute shuttle applications"
    gid: 5010
    capabilities: [run-shuttle]
    
  shuttle_defender_test_runners:
    description: "Can run defender testing tools with production config"
    gid: 5011
    capabilities: [run-shuttle-defender-test]
    special_permissions:
      - "Write access to ledger.yaml for version tracking"
    
  shuttle_testers:
    description: "Can run shuttle test suites and validation"
    gid: 5012
    capabilities: [run-tests, run-configurable-test]
    
  shuttle_admin:
    description: "Full administrative access"
    gid: 5020
    capabilities: [all-shuttle-commands, system-config]
    
  shuttle_operators:
    description: "Operational monitoring and basic management"
    gid: 5021
    capabilities: [view-logs, basic-config, restart-services]
```

### Configuration Access Groups  
```yaml
config_groups:
  shuttle_config_writers:
    description: "Can modify shuttle configuration"
    gid: 5030
    access: [write-config, read-config]
    
  shuttle_config_readers:
    description: "Can read shuttle configuration" 
    gid: 5031
    access: [read-config]
    
  shuttle_test_config_readers:
    description: "Can read test configurations"
    gid: 5032
    access: [read-test-config]
```

### Network Access Groups
```yaml
network_groups:
  shuttle_samba_in_users:
    description: "Inbound file submission via Samba from isolated systems"
    gid: 5040
    samba_enabled: true
    network_shares: [shuttle_incoming]
    access_pattern: "Upload files and verify submissions"
    
  shuttle_out_users:
    description: "Outbound file retrieval via network file system"
    gid: 5041
    network_access: "NFS/CIFS from domain systems"
    access_pattern: "Retrieve and delete processed files"
    note: "Domain accounts, not local users"
    
  shuttle_cyber_ops:
    description: "Security operations team"
    gid: 5050
    special_access: [hazard_archive]
```

## Directory Permission Matrix

### Core Shuttle Directories
```yaml
directory_permissions:
  source_path: "/var/shuttle/incoming"
    owner: "root"
    group: "shuttle_in_owners" 
    mode: "2775"  # setgid bit ensures group inheritance
    umask: "0027"  # New files: 640 (rw-r-----), dirs: 750 (rwxr-x---)
    acl:
      - "g:shuttle_samba_in_users:rwx"  # Inbound users can upload/verify
      - "g:shuttle_runners:rwx"          # Service can process
    acl_default:  # Inherited by new files/dirs
      - "d:g:shuttle_in_owners:rwX"      # X = execute only on dirs
      - "d:g:shuttle_samba_in_users:rwX"
      - "d:g:shuttle_runners:rwX"
    security_notes:
      - "setgid ensures new files inherit group ownership"
      - "Default ACLs ensure permissions propagate to new content"
      - "Capital X grants execute only on directories, not files"
    
  quarantine_path: "/var/shuttle/quarantine"
    owner: "root"
    group: "shuttle_quarantine_owners"
    mode: "2750"  # setgid + restricted access
    umask: "0027"
    acl: []
    acl_default:
      - "d:g:shuttle_quarantine_owners:rwX"
    security_notes:
      - "No ACL access - only group members can access"
      - "Files created without execute permissions"
    
  destination_path: "/var/shuttle/clean"
    owner: "root" 
    group: "shuttle_destination_owners"
    mode: "2750"  # setgid + group access only
    umask: "0027"
    acl:
      - "g:shuttle_samba_in_users:r-x"   # Inbound users can check results
      - "g:shuttle_out_users:rwx"        # Outbound users can retrieve/delete
    acl_default:
      - "d:g:shuttle_destination_owners:rwX"
      - "d:g:shuttle_samba_in_users:r-X"
      - "d:g:shuttle_out_users:rwX"
    security_notes:
      - "Read-only users cannot modify files"
      - "Files never have execute permissions"
    
  hazard_archive_path: "/var/shuttle/hazard"
    owner: "root"
    group: "shuttle_hazard_owners" 
    mode: "2750"  # setgid + highly restricted
    umask: "0077"  # Maximum restriction for malware
    acl:
      - "g:shuttle_cyber_ops:rwx"    # Security team access
    acl_default:
      - "d:g:shuttle_hazard_owners:rwX"
      - "d:g:shuttle_cyber_ops:rwX"
    security_notes:
      - "Contains encrypted malware samples"
      - "Strict umask prevents any 'other' access"
      - "Files must never be executable"
    
  log_path: "/var/log/shuttle"
    owner: "root"
    group: "shuttle_log_owners"
    mode: "2770"  # Group writable for services
    acl:
      - "g:shuttle_cyber_ops:r-x"    # Security team can read logs
      
  ledger_file_path: "/var/shuttle/ledger/ledger.yaml"
    owner: "root"
    group: "shuttle_ledger_owners"
    mode: "2664"  # Group writable for defender test runner
    acl: []
```

### Permission Inheritance Rules

```yaml
inheritance_rules:
  file_permissions:
    description: "All files in data directories must be non-executable"
    applies_to: [source, quarantine, hazard, destination]
    rules:
      - "New files inherit group from parent directory (setgid)"
      - "Files created with 640 permissions (rw-r-----)"
      - "No execute bit on files, even if umask allows it"
      - "ACL permissions use 'X' (capital) for conditional execute"
  
  directory_permissions:
    description: "Directories must be traversable by authorized groups"
    rules:
      - "New directories inherit group from parent (setgid)"
      - "Directories created with 750 permissions (rwxr-x---)"
      - "Execute bit required for directory traversal"
      - "Default ACLs propagate to subdirectories"
  
  acl_inheritance:
    description: "ACLs must propagate to new content"
    rules:
      - "Use default ACLs (d:) for automatic inheritance"
      - "Capital X in ACLs = execute on dirs only, not files"
      - "Default ACLs apply to all new files and subdirectories"
      - "Explicit ACLs don't inherit without defaults"
```

### Security Implementation Commands

```bash
# Example: Setting up source directory with proper inheritance
setfacl -R -m g:shuttle_samba_in_users:rwX /var/shuttle/incoming
setfacl -R -m d:g:shuttle_samba_in_users:rwX /var/shuttle/incoming

# Ensure no files have execute permissions
find /var/shuttle/incoming -type f -exec chmod a-x {} \;

# Set proper umask for shuttle service
echo "umask 0027" >> /etc/profile.d/shuttle.sh
```

## Multi-Group Access Strategy

### Directory Ownership and Access Model

| Directory   | Owner User | Owner Group                | Mode | Additional Access via ACL                             | Notes                                  |
|-------------|------------|----------------------------|------|-------------------------------------------------------|----------------------------------------|
| source      | root       | shuttle_in_owners          | 2775 | shuttle_samba_in_users (rwX), shuttle_runners (rwX)   | Primary group owns, ACLs extend access |
| quarantine  | root       | shuttle_quarantine_owners  | 2750 | None                                                  | Single group control                   |
| hazard      | root       | shuttle_hazard_owners      | 2750 | shuttle_cyber_ops (rwX)                               | Primary group + security team          |
| destination | root       | shuttle_destination_owners | 2750 | shuttle_samba_in_users (r-X), shuttle_out_users (rwX) | Primary group + network users          |
| logs        | root       | shuttle_log_owners         | 2770 | shuttle_cyber_ops (r-X)                               | Writers via group, readers via ACL     |
| config      | root       | shuttle_config_writers     | 2750 | shuttle_config_readers (r-X)                          | Write via group, read via ACL          |

### Access Achievement Methods

```yaml
access_methods:
  primary_group_ownership:
    description: "Directory owned by a dedicated group"
    example: "chown root:shuttle_in_owners /var/shuttle/incoming"
    use_when: "One group needs full control"
    
  acl_extensions:
    description: "Additional groups get access via ACLs"
    example: "setfacl -m g:shuttle_samba_in_users:rwX /var/shuttle/incoming"
    use_when: "Multiple groups need different access levels"
    
  user_membership:
    description: "Users join the owning group"
    example: "usermod -aG shuttle_in_owners shuttle_runner"
    use_when: "User needs same access as group"
```

### Group Membership Patterns

**Linux groups CANNOT belong to other groups**, but we achieve similar effects through:

1. **User Multi-Membership**:
   ```bash
   # User belongs to multiple groups
   shuttle_admin belongs to: shuttle_admin, shuttle_config_writers, shuttle_runners
   ```

2. **Synchronized Membership**:
   ```yaml
   # When adding a cyber analyst, add to both groups:
   usermod -aG shuttle_cyber_ops cyber_analyst
   usermod -aG shuttle_hazard_owners cyber_analyst
   ```

3. **ACL Layering**:
   ```bash
   # Base access via group ownership
   chown root:shuttle_destination_owners /var/shuttle/clean
   # Extended access via ACLs
   setfacl -m g:shuttle_out_users:rwX /var/shuttle/clean
   ```

### Practical Examples

| Scenario | Implementation |
|----------|----------------|
| **shuttle_runner needs access to all data dirs** | Add user to: shuttle_in_owners, shuttle_quarantine_owners, shuttle_hazard_owners, shuttle_destination_owners |
| **Samba users need source access** | Use ACL: `setfacl -m g:shuttle_samba_in_users:rwX` |
| **Config read/write separation** | Group owns (writers), ACL for readers |
| **Cyber analyst needs hazard access** | Use ACL rather than changing ownership |

### Why This Design?

1. **Single Owner Group**: Each directory has ONE owning group (Linux limitation)
2. **ACLs for Extension**: Additional groups get access via ACLs
3. **No Execute on Files**: Using 'X' in ACLs ensures only directories are executable
4. **Inheritance**: Both setgid and default ACLs ensure permissions propagate

### Configuration Directories
```yaml
config_permissions:
  config_path: "/etc/shuttle"
    owner: "root"
    group: "shuttle_config_writers"
    mode: "2750"
    acl:
      - "g:shuttle_config_readers:r-x"
      
  test_config_path: "/var/lib/shuttle/test"
    owner: "root"
    group: "shuttle_testers"
    mode: "2755"
    acl:
      - "g:shuttle_test_config_readers:r-x"
      
  test_work_dir: "/var/lib/shuttle/test/work"
    owner: "root"
    group: "shuttle_testers"
    mode: "2770"  # Group writable for test execution
    acl: []
    note: "Isolated directory for all test operations"
```

## Access Scenarios by Role

### 1. Service Account (shuttle_runner)
```yaml
shuttle_runner_access:
  can_read:
    - "/etc/shuttle/config.conf" (via shuttle_config_readers)
    - "/var/shuttle/incoming/*" (via shuttle_in_owners)
  can_write:
    - "/var/shuttle/quarantine/*" (via shuttle_quarantine_owners)
    - "/var/shuttle/clean/*" (via shuttle_destination_owners)  
    - "/var/shuttle/hazard/*" (via shuttle_hazard_owners)
    - "/var/log/shuttle/*" (via shuttle_log_owners)
  cannot_access:
    - Test configurations (not in shuttle_test_config_readers)
    - Ledger file (not in shuttle_ledger_owners)
```

### 2. Defender Test Runner (shuttle_defender_test_runner)
```yaml
shuttle_defender_test_runner_access:
  can_read:
    - "/etc/shuttle/config.conf" (needs production config for testing)
    - "/var/shuttle/ledger/ledger.yaml" (via shuttle_ledger_owners)
  can_write:
    - "/var/shuttle/ledger/ledger.yaml" (via shuttle_ledger_owners)
    - Test output directories
  special_purpose:
    - Tests Microsoft Defender with production configuration
    - Updates ledger with tested defender versions
    - Completely separate from shuttle testing functionality
```

### 3. Administrator (shuttle_admin)
```yaml
shuttle_admin_access:
  can_read:
    - All shuttle directories (member of all owner groups)
    - All configuration files (shuttle_config_writers)
  can_write:
    - All shuttle directories
    - All configuration files
    - Can manage users/groups
  special_privileges:
    - Can restart services
    - Can modify system configuration
```

### 4. Inbound Samba User (shuttle_samba_in_user)
```yaml
shuttle_samba_in_user_access:
  can_read:
    - "/var/shuttle/incoming/*" (via ACL - verify uploads)
    - "/var/shuttle/clean/*" (via ACL - check processing results)
  can_write:
    - "/var/shuttle/incoming/*" (via ACL - submit files)
  cannot_access:
    - Quarantine, hazard, logs, config (security boundary)
  network_access:
    - Samba share for incoming directory
    - Connect from isolated submission systems
```

### 5. Outbound User (shuttle_out_user)
```yaml
shuttle_out_user_access:
  can_read:
    - "/var/shuttle/clean/*" (via ACL - retrieve files)
  can_write:
    - "/var/shuttle/clean/*" (via ACL - delete after retrieval)
  cannot_access:
    - Source, quarantine, hazard, logs, config (complete isolation)
  network_access:
    - Network file system (NFS/CIFS)
    - Domain accounts from remote systems
    - No local system access
```

### 6. Security Analyst (cyber_analyst) 
```yaml
cyber_analyst_access:
  can_read:
    - "/etc/shuttle/config.conf" (via shuttle_config_readers)
    - "/var/log/shuttle/*" (read-only access)
  can_write:
    - "/var/shuttle/hazard/*" (via shuttle_cyber_ops)
  cannot_access:
    - Source, quarantine, destination directories
    - Ledger file
    - Test directories
  special_access:
    - Can decrypt and analyze malware samples
    - Can generate security reports
```

### 7. Shuttle Tester (shuttle_tester)
```yaml
shuttle_tester_access:
  can_read:
    - "/var/lib/shuttle/test/*" (via shuttle_testers group)
    - Test configurations only
  can_write:
    - "/var/lib/shuttle/test/work/*" (test work directory only)
    - Test output directories within work directory
  cannot_access:
    - Production source directory (/var/shuttle/incoming)
    - Production quarantine directory (/var/shuttle/quarantine)
    - Production destination directory (/var/shuttle/clean)
    - Production hazard directory (/var/shuttle/hazard)
    - Production configuration (/etc/shuttle/config.conf)
    - Ledger file
  purpose:
    - Tests shuttle application functionality in isolation
    - Runs integration tests with test data only
    - Works entirely within test work directory
    - Completely separate from production operations
```

## Access Control Matrix

### Permission Key
- `r` = read access
- `w` = write access  
- `x` = execute access
- `rw` = read/write access
- `rx` = read/execute access
- `rwx` = read/write/execute access
- (blank) = no access

### Complete Access Matrix




| User                         | config | key | ledger | logs | source     | quarantine | hazard | destination | tests | test work |
|------------------------------|--------|----------------|--------|------|------------|------------|--------|-------------|-------|-----------|
| shuttle_defender_test_runner | r      | r              | rw     | rw   |            |            |        |             |       |           |
| shuttle_runner               | r      | r              | r      | rw   | rw         | rw         | rw     | rw          |       |           |
| shuttle_samba_in_users       |        |                |        |      | rw via ACL |            |        | r via ACL   |       |           |
| shuttle_out_users            |        |                |        |      |            |            |        | rw via ACL  |       |           |
| shuttle_testers              |        |                |        |      |            |            |        |             | rwx   | rw        |



| User                         | config | key | ledger | logs | source     | quarantine | hazard | destination | tests | test work |
|------------------------------|--------|-----|--------|------|------------|------------|--------|-------------|-------|-----------|
| shuttle_defender_test_runner | r      | r   | rw     | rw   |            |            |        |             |       |           |
| shuttle_runner               | r      | r   | r      | rw   | rw         | rw         | rw     | rw          |       |           |
| shuttle_samba_in_users       |        |     |        |      | rw via ACL |            |        | r via ACL   |       |           |
| shuttle_out_users            |        |     |        |      |            |            |        | rw via ACL  |       |           |
| shuttle_testers              |        |     |        |      |            |            |        |             | rwx   | rw        |

| Directory   | Owner User                   | Owner Group                | group Mode | Additional Access via ACL                             | Notes                                  |
|-------------|------------------------------|----------------------------|------------|-------------------------------------------------------|----------------------------------------|
| source      | root                         | shuttle_in_owners          | rwX        | shuttle_samba_in_users (rwX),                         | Primary group owns, ACLs extend access |
| quarantine  | root                         | shuttle_quarantine_owners  | rwX        |                                                       |                                        |
| hazard      | root                         | shuttle_hazard_owners      | rwX        |                                                       |                                        |
| destination | root                         | shuttle_destination_owners | rwX        | shuttle_samba_in_users (r-X), shuttle_out_users (rwX) | Primary group + network users          |
|             |                              |                            |            |                                                       |                                        |
| logs        | root                         | shuttle_log_owners         | rwX        |                                                       |                                        |
| config      | root                         | shuttle_config_readers     | rX         |                                                       | Write via root / sudo                  |
| key         | root                         | shuttle_key_readers        | rX         |                                                       | Write via root / sudo                  |
| ledger      | root                         | shuttle_ledger_owners      | rwX        | shuttle_runners (r-X)                                 |                                        |
|             |                              |                            |            |                                                       |                                        |
| test work   | root                         | shuttle_testers            | rwX        |                                                       |                                        |
|             |                              |                            |            |                                                       |                                        |




shuttle_runners -- needs to be able to write remove lock file
shuttle_defender_test_runner - not sure what they need yet!

user: 
belongs to groups

shuttle_runner:
shuttle_config_readers  
shuttle_log_owners  
shuttle_runners
shuttle_in_owners         
shuttle_quarantine_owners 
shuttle_hazard_owners     
shuttle_destination_owners                         
      
  
shuttle_defender_test_runner:
shuttle_config_readers 
shuttle_log_owners  
shuttle_key_readers
shuttle_ledger_owners
shuttle_defender_test_runners

shuttle_samba_in_user:
shuttle_samba_in_users 

shuttle_tester:
shuttle_testers

shuttle_out_user:
shuttle_out_users






### Key Observations

1. **Complete Isolation**:
   - `shuttle_testers` have NO access to production directories (source, quarantine, hazard, destination)
   - `shuttle_samba_in_users` and `shuttle_out_users` have NO access to sensitive areas (config, logs, hazard)
   - `shuttle_defender_test_runners` have NO access to shuttle file processing directories
   - `shuttle_out_users` have NO access to source directory (one-way data flow)

2. **Shared Resources**:
   - Both `shuttle_testers` and `shuttle_defender_test_runners` can execute `run-shuttle-defender-test`
   - Only `shuttle_runners` and `shuttle_admin` have access to production file directories
   - Log access is granted to those who need it for their function

3. **Special Access Patterns**:
   - `shuttle_samba_in_users` use ACL for source (read/write) and destination (read) access
   - `shuttle_out_users` use ACL for destination only (read/write for retrieval/cleanup)
   - `shuttle_cyber_analyst` has full access to hazard directory for malware analysis
   - `shuttle_defender_test_runners` can update the ledger file

4. **Data Flow Security**:
   - Inbound: `shuttle_samba_in_users` → source → processing → destination
   - Outbound: destination → `shuttle_out_users` (no reverse flow to source)
   - Complete separation between inbound and outbound user accounts

## Group Membership Summary

### Primary Groups Only
- `shuttle_samba_in_user` → `shuttle_samba_in_users`
- `shuttle_out_user` → `shuttle_out_users`
- `shuttle_defender_test_runner` → `shuttle_defender_test_runners`
- `shuttle_tester` → `shuttle_testers`

### With Secondary Groups
- `shuttle_admin` → `shuttle_admin` + `[shuttle_config_writers, shuttle_runners]`
- `shuttle_operator` → `shuttle_operators` + `[shuttle_config_readers, shuttle_runners]`
- `cyber_analyst` → `shuttle_cyber_ops` + `[shuttle_config_readers]`

### Directory Owner Groups Membership
- `shuttle_in_owners`: shuttle_runner, shuttle_admin
- `shuttle_quarantine_owners`: shuttle_runner, shuttle_admin
- `shuttle_destination_owners`: shuttle_runner, shuttle_admin
- `shuttle_hazard_owners`: shuttle_runner, shuttle_admin, cyber_analyst
- `shuttle_log_owners`: shuttle_runner, shuttle_admin, shuttle_operator
- `shuttle_ledger_owners`: shuttle_defender_test_runner, shuttle_admin

## Wizard Complexity Requirements

Based on this model, the wizard needs to handle:

### 1. **Role-Based Templates**
```yaml
role_templates:
  service_account:
    suggested_groups: [shuttle_runners, directory_owners]
    access_patterns: [read_config, write_logs, process_files]
    
  defender_tester:
    suggested_groups: [shuttle_defender_test_runners, shuttle_ledger_owners]
    access_patterns: [read_production_config, write_ledger]
    
  shuttle_tester:
    suggested_groups: [shuttle_testers]
    access_patterns: [read_test_config, write_test_work_dir]
    isolation: "Complete separation from production directories"
    
  administrator:
    suggested_groups: [shuttle_admin, shuttle_config_writers]  
    access_patterns: [full_access]
    
  operator:
    suggested_groups: [shuttle_operators, shuttle_config_readers]  
    access_patterns: [monitor_logs, basic_management]
    
  inbound_user:
    suggested_groups: [shuttle_samba_in_users]
    access_patterns: [upload_files, check_processing_results]
    
  outbound_user:
    suggested_groups: [shuttle_out_users]
    access_patterns: [retrieve_processed_files, cleanup_after_retrieval]
    
  security_analyst:
    suggested_groups: [shuttle_cyber_ops]
    access_patterns: [analyze_malware, read_logs]
```

### 2. **Multi-Level Group Membership**
- Primary group (main role)
- Secondary groups (additional permissions)
- Automatic group relationships (cyber_ops → hazard_owners)

### 3. **Directory Strategy Selection**
- Group ownership (most directories)
- ACL supplements (network users, cross-role access)
- Service account integration

### 4. **Conflict Prevention**
- Ensure service accounts can function
- Prevent security violations (e.g., samba user accessing hazard)
- Validate group membership chains

### 5. **Special Access Patterns**
- Defender test runner needs ledger write access
- Shuttle testers need test config access only
- Cyber ops need hazard archive access

This model provides clear separation between:
- Shuttle testing (application functionality)
- Defender testing (malware detection with production config)
- Production operations (file processing)
- Security analysis (malware investigation)