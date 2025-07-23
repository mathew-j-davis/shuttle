# Shuttle Security Model

## Three-Layer Permission Control

1. **Directory Permissions (2770)** - Basic Linux access control
2. **Default ACLs** - Ensures Samba uploads get consistent 660 permissions
3. **Shuttle umask (0007)** - Process-level file creation guarantees

**Purpose of Default ACLs:** Windows clients uploading via Samba can create files with unpredictable permissions (644, 664, 600, etc.) depending on client settings. Default ACLs override this to ensure all uploaded files get 660 permissions.

**Result:** All files created with `660` permissions and proper group ownership.

## Path Permissions

| Path                       | Owner                       | Mode | ACLs                          | Default ACLs         | Purpose |
|----------------------------|-----------------------------|------|-------------------------------|----------------------|---------|
| source_path                | root:shuttle_owners         | 2770 | g:shuttle_samba_in_users:rwX  | u::rw-,g::rw-,o::--- | Samba uploads: F:660 D:770 |
| destination_path           | root:shuttle_owners         | 2770 | g:shuttle_out_users:rwX       | u::rw-,g::rw-,o::--- | Samba downloads: F:660 D:770 |
| quarantine_path            | root:shuttle_owners         | 2770 | None                          | None                 | Shuttle only (umask handles) |
| hazard_archive_path        | root:shuttle_owners         | 2770 | None                          | None                 | Shuttle only (umask handles) |
| log_path                   | root:shuttle_log_owners     | 2770 | None                          | None                 | Shuttle only (umask handles) |
| hazard_encryption_key_path | root:shuttle_config_readers | 0640 | None                          | None                 | Static file |
| ledger_file_path           | root:shuttle_config_readers | 0640 | g:shuttle_log_owners:rw-      | None                 | Static file |
| test_work_dir              | root:shuttle_testers        | 0775 | None                          | None                 | Test isolation |
| test_config_path           | root:shuttle_testers        | 0664 | None                          | None                 | Static file |

## Group Access Matrix

| Group                        | Data Dirs | Logs | Config | Ledger | Tests |
|------------------------------|-----------|------|--------|--------|-------|
| shuttle_owners               | rwx       |      |        |        |       |
| shuttle_log_owners           |           | rwx  |        | rw-    |       |
| shuttle_config_readers       |           |      | r--    | r--    |       |
| shuttle_testers              |           |      |        |        | rwx   |
| shuttle_samba_in_users       | source:rwX|      |        |        |       |
| shuttle_out_users            | dest:rwX  |      |        |        |       |

## Security Features

- **setgid (2xxx):** Files inherit directory group ownership
- **Capital X ACLs:** Execute on directories only, never on files  
- **No "others" access:** All paths restrict access to authorized groups
- **Root ownership:** Defense in depth - service compromise doesn't own files
- **Encrypted hazard files:** Safe to handle with standard data permissions

## Default ACL Commands

Apply ONLY to directories accessed by Samba users (source_path and destination_path):
```bash
# For source_path (Samba uploads)
setfacl -d -m u::rw-,g::rw-,o::--- /path/to/source         # Files get 660
setfacl -d -m u::rwx,g::rwx,o::--- /path/to/source         # Directories get 770

# For destination_path (Samba downloads)
setfacl -d -m u::rw-,g::rw-,o::--- /path/to/destination    # Files get 660
setfacl -d -m u::rwx,g::rwx,o::--- /path/to/destination    # Directories get 770
```

**NOT needed for:** quarantine_path, hazard_archive_path, log_path (only shuttle process writes there, umask(0007) handles permissions)

**Purpose:** Ensures files uploaded via Samba get consistent 660 permissions regardless of Windows client settings or Samba configuration.

**Result:** Samba-uploaded files get proper permissions without manual intervention.

## User Accounts and Group Memberships

### Service Users
```yaml
shuttle_runner:
  description: "Main shuttle application service account"
  groups:
    - shuttle_config_readers
    - shuttle_log_owners
    - shuttle_owners
  shell: /bin/bash
  home: /var/lib/shuttle

shuttle_defender_test_runner:
  description: "Defender testing with production config"
  groups:
    - shuttle_config_readers
    - shuttle_log_owners
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

shuttle_out_user:
  description: "Outbound file retrieval via Samba"
  groups:
    - shuttle_out_users
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