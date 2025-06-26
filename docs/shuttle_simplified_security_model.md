# Shuttle Simplified Security Model

## Design Principles

1. **Clear Group Ownership**: Each directory has ONE owning group for simplicity
2. **ACLs only for:**
  - **Network Users**: Isolated Samba and outbound users use ACLs
  - **shuttle_runners**: Use 
3. **Service Account Multi-Membership**: Service accounts join multiple groups directly
4. **Read-Only System Files**: Config and keys are read-only groups, written via sudo
5. **Complete Test Isolation**: Test users have no production access

## User and Group Structure

### Service Users
```yaml
shuttle_runner:
  description: "Main shuttle application service account"
  groups:
    - shuttle_config_readers
    - shuttle_log_owners
    - shuttle_runners
    - shuttle_in_owners
    - shuttle_quarantine_owners
    - shuttle_hazard_owners
    - shuttle_destination_owners
    - shuttle_key_readers

shuttle_defender_test_runner:
  description: "Defender testing with production config"
  groups:
    - shuttle_config_readers
    - shuttle_log_owners
    - shuttle_key_readers
    - shuttle_ledger_owners
    - shuttle_defender_test_runners

shuttle_tester:
  description: "Shuttle application testing (isolated)"
  groups:
    - shuttle_testers
```

### Network Users (ACL-based access only)
```yaml
shuttle_samba_in_user:
  description: "Inbound file submission via Samba"
  groups:
    - shuttle_samba_in_users
  access_method: "ACL only - no group ownership"

shuttle_out_user:
  description: "Outbound file retrieval (domain accounts)"
  groups:
    - shuttle_out_users
  access_method: "ACL only - no group ownership"
```

## Access Control Matrix

| User/Group                   | config | key | ledger        | logs | source     | quarantine | hazard | destination | tests | test work |
|------------------------------|--------|-----|---------------|------|------------|------------|--------|-------------|-------|-----------|
| shuttle_runner               | r      | r   | r             | rw   | rw         | rw         | rw     | rw          |       |           |
| shuttle_defender_test_runner | r      | r   | r (w via ACL) | rw   |            |            |        |             |       |           |
| shuttle_samba_in_users       |        |     |               |      | rw via ACL |            |        | r via ACL   |       |           |
| shuttle_out_users            |        |     |               |      |            |            |        | rw via ACL  |       |           |
| shuttle_testers              |        |     |               |      |            |            |        |             | rwx   | rw        |

## Directory Ownership Model

| Directory   | Owner User | Owner Group               | Mode | Additional Access via ACL                             | Notes                                  |
|-------------|------------|---------------------------|------|-------------------------------------------------------|----------------------------------------|
| source      | root       | shuttle_in_owners         | 2775 | shuttle_samba_in_users (rwX)                          | Group owns, Samba users via ACL        |
| quarantine  | root       | shuttle_quarantine_owners | 2750 | None                                                  | Service accounts only                  |
| hazard      | root       | shuttle_hazard_owners     | 2750 | None                                                  | Service accounts only                  |
| destination | root       | shuttle_destination_owners| 2750 | shuttle_samba_in_users (r-X), shuttle_out_users (rwX)| Group owns, network users via ACL       |
| logs        | root       | shuttle_log_owners        | 2770 | None                                                  | Service accounts only                  |
| config      | root       | shuttle_config_readers    | 2750 | None                                                  | Read-only, write via sudo              |
| key         | root       | shuttle_config_readers    | 2750 | None                                                  | Read-only, write via sudo              |
| ledger      | root       | shuttle_config_readers    | 2770 | shuttle_defender_test_runner (rwX)                    | Defender test writes                   |
| tests       | root       | shuttle_testers           | 2755 | None                                                  | Test binaries/scripts                  |
| test work   | root       | shuttle_testers           | 2770 | None                                                  | Test execution workspace               |

## Permission Inheritance Setup

### Directory Inheritance Rules
All directories use:
- **setgid bit (2xxx)**: New files inherit group ownership
- **Default ACLs**: Permissions propagate to new content
- **Capital X in ACLs**: Execute only on directories, never on files

### Example ACL Setup
```bash
# Source directory with inheritance
setfacl -m g:shuttle_samba_in_users:rwX /var/shuttle/incoming
setfacl -m d:g:shuttle_samba_in_users:rwX /var/shuttle/incoming

# Destination with different access levels
setfacl -m g:shuttle_samba_in_users:r-X /var/shuttle/clean
setfacl -m d:g:shuttle_samba_in_users:r-X /var/shuttle/clean
setfacl -m g:shuttle_out_users:rwX /var/shuttle/clean
setfacl -m d:g:shuttle_out_users:rwX /var/shuttle/clean

# Ensure no files get execute permissions
find /var/shuttle -type f -exec chmod a-x {} \;
```

## Security Boundaries

### Complete Isolation
- **shuttle_testers**: No access to any production directories
- **shuttle_samba_in_users**: No access to config, logs, hazard, quarantine
- **shuttle_out_users**: No access to source, config, logs, hazard, quarantine
- **shuttle_defender_test_runner**: No access to file processing directories

### Data Flow Security
```
Inbound:  shuttle_samba_in_users → source → processing → destination
Outbound: destination → shuttle_out_users
Testing:  test work (completely isolated)
```

### Key Design Decisions
1. **No execute permissions on data files**: All data files are non-executable
2. **Directory traversal only**: ACLs use 'X' for directory access without file execution
3. **One-way data flow**: Inbound and outbound users cannot access each other's domains
4. **Service account consolidation**: shuttle_runner has broad access via group membership
5. **Test isolation**: Complete separation from production data

## Implementation Strategy

### Group Creation
```bash
# Create all owner groups
groupadd -r shuttle_config_readers
groupadd -r shuttle_key_readers
groupadd -r shuttle_log_owners
groupadd -r shuttle_runners
groupadd -r shuttle_in_owners
groupadd -r shuttle_quarantine_owners
groupadd -r shuttle_hazard_owners
groupadd -r shuttle_destination_owners
groupadd -r shuttle_ledger_owners
groupadd -r shuttle_testers
groupadd -r shuttle_defender_test_runners
groupadd -r shuttle_samba_in_users
groupadd -r shuttle_out_users
```

### User Setup
```bash
# Service accounts with multiple group membership
usermod -aG shuttle_config_readers,shuttle_log_owners,shuttle_runners,\
shuttle_in_owners,shuttle_quarantine_owners,shuttle_hazard_owners,\
shuttle_destination_owners,shuttle_key_readers shuttle_runner

usermod -aG shuttle_config_readers,shuttle_log_owners,shuttle_key_readers,\
shuttle_ledger_owners,shuttle_defender_test_runners shuttle_defender_test_runner

usermod -aG shuttle_testers shuttle_tester

# Network users (single group membership)
usermod -aG shuttle_samba_in_users shuttle_samba_in_user
usermod -aG shuttle_out_users shuttle_out_user
```

### Directory Setup
```bash
# Set ownership and permissions
chown root:shuttle_in_owners /var/shuttle/incoming
chmod 2775 /var/shuttle/incoming

chown root:shuttle_config_readers /etc/shuttle
chmod 2750 /etc/shuttle

# Add ACLs for network users (with inheritance)
setfacl -m g:shuttle_samba_in_users:rwX /var/shuttle/incoming
setfacl -m d:g:shuttle_samba_in_users:rwX /var/shuttle/incoming
```

## Wizard Implementation Requirements

### Role Templates
```yaml
role_templates:
  service_account:
    suggested_groups: [multiple group membership based on role]
    access_strategy: "group_membership"
    
  network_inbound:
    suggested_groups: [shuttle_samba_in_users]
    access_strategy: "acl_only"
    
  network_outbound:
    suggested_groups: [shuttle_out_users]
    access_strategy: "acl_only"
    
  tester:
    suggested_groups: [shuttle_testers]
    access_strategy: "group_membership"
    isolation: "complete"
```

### Access Strategy Types
```python
class AccessStrategy(Enum):
    GROUP_MEMBERSHIP = "group_membership"  # Add user to owning groups
    ACL_ONLY = "acl_only"                 # Use ACLs, no group ownership
    READ_ONLY = "read_only"               # Config/key access pattern
```

### Conflict Prevention
- Service accounts: Allow multiple group membership
- Network users: Only ACL access, no ownership conflicts
- Test users: Complete isolation prevents conflicts
- Config/keys: Read-only groups prevent write conflicts

## Validation Rules

### Multi-User Validation
1. **Single ownership**: Each directory has one owning group
2. **ACL consistency**: Network users only get ACL access
3. **Isolation verification**: Test users have no production access
4. **Read-only enforcement**: Config/key directories are not writable via groups

### Permission Validation
1. **No file execution**: Data files never have execute permissions
2. **Directory traversal**: Ensure 'X' permission on directories for authorized groups
3. **Inheritance check**: Verify setgid and default ACLs are set
4. **Network isolation**: Verify Samba users cannot access sensitive areas

This simplified model maintains security while being much easier to understand, implement, and maintain than the original complex design.