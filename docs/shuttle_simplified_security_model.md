# Shuttle Simplified Security Model

## Design Principles

1. **Clear Group Ownership**: Each directory has ONE owning group for simplicity
2. **Minimal Groups**: Only 3 core groups needed for basic operation
3. **Service Account Multi-Membership**: Service accounts join multiple groups directly
4. **Read-Only System Files**: Config and keys are read-only groups, written via sudo
5. **Complete Test Isolation**: Test users have no production access
6. **ACLs for Future Network Access**: Samba/network groups available but optional

## User and Group Structure

### Service Users
```yaml
shuttle_runner:
  description: "Main shuttle application service account"
  groups:
    - shuttle_common_users    # Config (r), logs (rw), ledger (r)
    - shuttle_owners          # All data directories

shuttle_defender_test_runner:
  description: "Defender testing with production config"
  groups:
    - shuttle_common_users    # Config (r), logs (rw), ledger (r)

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

| User/Group                   | config/key | ledger        | logs | source | quarantine | hazard | destination | tests | test work |
|------------------------------|------------|---------------|------|--------|------------|--------|-------------|-------|-----------|
| shuttle_runner               | r          | r             | rw   | rw     | rw         | rw     | rw          |       |           |
| shuttle_defender_test_runner | r          | r             | rw   |        |            |        |             |       |           |
| shuttle_samba_in_users       |            |               |      | rw via ACL |           |        | r via ACL   |       |           |
| shuttle_out_users            |            |               |      |        |            |        | rw via ACL  |       |           |
| shuttle_testers              |            |               |      |        |            |        |             | rwx   | rw        |

## Directory Ownership Model

| Directory   | Owner User | Owner Group            | Mode | Additional Access via ACL                             | Notes                                  |
|-------------|------------|------------------------|------|-------------------------------------------------------|----------------------------------------|
| source      | root       | shuttle_owners         | 2775 | shuttle_samba_in_users (rwX)                          | Group owns, Samba users via ACL (future) |
| quarantine  | root       | shuttle_owners         | 2750 | None                                                  | Service accounts only                  |
| hazard      | root       | shuttle_owners         | 2750 | None                                                  | Service accounts only                  |
| destination | root       | shuttle_owners         | 2750 | shuttle_samba_in_users (r-X), shuttle_out_users (rwX)| Group owns, network users via ACL (future) |
| logs        | root       | shuttle_common_users   | 2770 | None                                                  | Service accounts write logs            |
| config      | root       | shuttle_common_users   | 2750 | None                                                  | Config and keys, write via sudo       |
| ledger      | root       | shuttle_common_users   | 0640 | None                                                  | Read-only ledger file                  |
| tests       | root       | shuttle_testers        | 2755 | None                                                  | Test binaries/scripts                  |
| test work   | root       | shuttle_testers        | 2770 | None                                                  | Test execution workspace               |

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
# Create core groups (only 3 needed for basic operation)
groupadd -r shuttle_common_users    # Config (r), logs (rw), ledger (r)
groupadd -r shuttle_owners          # All data directories
groupadd -r shuttle_testers         # Test isolation

# Optional groups for future network access
groupadd -r shuttle_samba_in_users  # Network inbound (future)
groupadd -r shuttle_out_users       # Network outbound (future)
```

### User Setup
```bash
# Service accounts with simplified group membership
usermod -aG shuttle_common_users,shuttle_owners shuttle_runner

usermod -aG shuttle_common_users shuttle_defender_test_runner

usermod -aG shuttle_testers shuttle_tester

# Optional network users (for future use)
# usermod -aG shuttle_samba_in_users shuttle_samba_in_user
# usermod -aG shuttle_out_users shuttle_out_user
```

### Directory Setup
```bash
# Set ownership and permissions with simplified groups
chown root:shuttle_owners /mnt/in
chown root:shuttle_owners /mnt/quarantine
chown root:shuttle_owners /mnt/hazard
chown root:shuttle_owners /mnt/out
chmod 2775 /mnt/in
chmod 2750 /mnt/quarantine
chmod 2750 /mnt/hazard
chmod 2750 /mnt/out

chown root:shuttle_common_users /etc/shuttle
chmod 2750 /etc/shuttle

chown root:shuttle_common_users /var/log/shuttle
chmod 2770 /var/log/shuttle

# Optional ACLs for future network users
# setfacl -m g:shuttle_samba_in_users:rwX /mnt/in
# setfacl -m d:g:shuttle_samba_in_users:rwX /mnt/in
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