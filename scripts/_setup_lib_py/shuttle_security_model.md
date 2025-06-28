# Shuttle Security Model

## Three-Layer Permission Control

1. **Directory Permissions (2770)** - Basic Linux access control
2. **Default ACLs** - Consistent file permissions regardless of creator's umask
3. **Shuttle umask (0007)** - Process-level file creation guarantees

**Result:** All files created with `660` permissions and proper group ownership.

## Path Permissions

| Path                       | Owner                       | Mode | ACLs                          | Default ACLs         | Result |
|----------------------------|-----------------------------|------|-------------------------------|----------------------|--------|
| source_path                | root:shuttle_data_owners    | 2770 | g:shuttle_samba_in_users:rwX  | u::rw-,g::rw-,o::--- | F:660 D:770 |
| destination_path           | root:shuttle_data_owners    | 2770 | g:shuttle_samba_out_users:r-X | u::rw-,g::rw-,o::--- | F:660 D:770 |
| quarantine_path            | root:shuttle_data_owners    | 2770 | None                          | u::rw-,g::rw-,o::--- | F:660 D:770 |
| hazard_archive_path        | root:shuttle_data_owners    | 2770 | None                          | u::rw-,g::rw-,o::--- | F:660 D:770 |
| log_path                   | root:shuttle_log_owners     | 2770 | None                          | None                 | N/A    |
| hazard_encryption_key_path | root:shuttle_config_readers | 0640 | None                          | None                 | N/A    |
| ledger_file_path           | root:shuttle_config_readers | 0640 | g:shuttle_ledger_owners:rw-   | None                 | N/A    |
| test_work_dir              | root:shuttle_testers        | 0775 | None                          | None                 | N/A    |
| test_config_path           | root:shuttle_testers        | 0664 | None                          | None                 | N/A    |

## Group Access Matrix

| Group                        | Data Dirs | Logs | Config | Ledger | Tests |
|------------------------------|-----------|------|--------|--------|-------|
| shuttle_data_owners          | rwx       |      |        |        |       |
| shuttle_log_owners           |           | rwx  |        |        |       |
| shuttle_config_readers       |           |      | r--    | r--    |       |
| shuttle_ledger_owners        |           |      |        | rw-    |       |
| shuttle_testers              |           |      |        |        | rwx   |
| shuttle_samba_in_users       | source:rwX|      |        |        |       |
| shuttle_samba_out_users      | dest:r-X  |      |        |        |       |

## Security Features

- **setgid (2xxx):** Files inherit directory group ownership
- **Capital X ACLs:** Execute on directories only, never on files  
- **No "others" access:** All paths restrict access to authorized groups
- **Root ownership:** Defense in depth - service compromise doesn't own files
- **Encrypted hazard files:** Safe to handle with standard data permissions

## Default ACL Commands

Apply to all data directories to ensure consistent permissions:
```bash
# Set default ACLs on directory (files: 660, dirs: 770)
setfacl -d -m u::rw-,g::rw-,o::--- /path/to/directory    # Files
setfacl -d -m d:u::rwx,d:g::rwx,d:o::--- /path/to/directory  # Directories
```
**Result:** Files created by any process (Samba, manual, etc.) get 660 permissions without execute bit.

## User Accounts and Group Memberships

### Service Users
```yaml
shuttle_runner:
  description: "Main shuttle application service account"
  groups:
    - shuttle_config_readers
    - shuttle_log_owners
    - shuttle_data_owners
    - shuttle_runners
  shell: /bin/bash
  home: /var/lib/shuttle

shuttle_defender_test_runner:
  description: "Defender testing with production config"
  groups:
    - shuttle_config_readers
    - shuttle_log_owners
    - shuttle_ledger_owners
    - shuttle_defender_test_runners
  shell: /bin/bash
  home: /var/lib/shuttle_defender_test

shuttle_tester:
  description: "Shuttle application testing (isolated)"
  groups:
    - shuttle_testers
  shell: /bin/bash
  home: /var/lib/shuttle_test
```

### Network Users (Samba-only, ACL-based access)
```yaml
shuttle_samba_in_user:
  description: "Inbound file submission via Samba"
  groups:
    - shuttle_samba_in_users
  shell: /usr/sbin/nologin
  home: /dev/null
  restrictions:
    - No login capability
    - No other group memberships
    - Access only via Samba ACLs

shuttle_samba_out_user:
  description: "Outbound file retrieval via Samba"
  groups:
    - shuttle_samba_out_users
  shell: /usr/sbin/nologin
  home: /dev/null
  restrictions:
    - No login capability
    - No other group memberships
    - Access only via Samba ACLs
```

## Implementation

- **Shuttle process:** Sets `umask(0007)` at startup for consistent file creation
- **Samba users:** Controlled by default ACLs regardless of their umask
- **Group membership:** Service accounts in appropriate groups for access
- **Network user security:** Samba users have no login shell and restricted group membership