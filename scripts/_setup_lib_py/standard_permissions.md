# Shuttle Standard Permissions Plan

## Overview
This document defines the standard permission configuration for all shuttle paths. These permissions will be applied when users select "Apply standard permissions to all paths" in the configuration wizard.

## Permission Structure

### Data Directories
These directories contain files being processed by shuttle and need write access for the shuttle process.

**Paths:**
- `source_path` - Incoming files to be processed
- `destination_path` - Successfully processed files  
- `quarantine_path` - Files awaiting scanning
- `hazard_archive_path` - **Encrypted** hazardous files (safe once encrypted)

**Permissions:**
- **Owner:** `root:shuttle_data_owners`
- **Mode:** `2770` (drwxrwx---)
  - `2` = setgid bit (new files inherit group ownership)
  - `7` = rwx for owner (root)
  - `7` = rwx for group (shuttle_data_owners)
  - `0` = no access for others
- **ACLs:**
  - `source_path` only: `g:shuttle_samba_in_users:rwX` (allow Samba users to submit files)
  - `destination_path` only: `g:shuttle_samba_out_users:r-X` (allow Samba users to retrieve files)
  - Note: Capital `X` means execute only on directories, not files
- **Default ACLs (ensure consistent file permissions):**
  - All data directories:
    ```
    # For files: 660 (rw-rw----)
    setfacl -d -m u::rw- <directory>  # Default: user gets rw-
    setfacl -d -m g::rw- <directory>  # Default: group gets rw-
    setfacl -d -m o::--- <directory>  # Default: others get nothing
    
    # For directories: 770 (rwxrwx---)
    setfacl -d -m d:u::rwx <directory>  # Default: user gets rwx on new dirs
    setfacl -d -m d:g::rwx <directory>  # Default: group gets rwx on new dirs
    setfacl -d -m d:o::--- <directory>  # Default: others get nothing on new dirs
    ```
  - This ensures:
    - New files are created with 660 permissions (no execute)
    - New directories are created with 770 permissions (traversable)
    - Both regardless of the creating process's umask

### Log Directory
For shuttle application logs.

**Path:**
- `log_path` - Shuttle application logs

**Permissions:**
- **Owner:** `root:shuttle_log_owners`
- **Mode:** `2770` (drwxrwx---)
- **ACLs:** None

### Configuration Files
Sensitive configuration and key files with restricted access.

**Paths:**
- `hazard_encryption_key_path` - GPG public key for encrypting hazardous files
- `ledger_file_path` - Transaction ledger

**Permissions:**
- **Owner:** `root:shuttle_config_readers`
- **Mode:** `0640` (-rw-r-----)
  - `6` = rw- for owner (root)
  - `4` = r-- for group (shuttle_config_readers)
  - `0` = no access for others
- **ACLs:**
  - `ledger_file_path` only: `g:shuttle_ledger_owners:rw-` (allow ledger updates)

### Test Directories and Files
For testing shuttle functionality.

**Paths:**
- `test_work_dir` - Test working directory (directory)
- `test_config_path` - Test configuration file (file)

**Permissions for test_work_dir:**
- **Owner:** `root:shuttle_testers`
- **Mode:** `0775` (drwxrwxr-x)
- **ACLs:** None

**Permissions for test_config_path:**
- **Owner:** `root:shuttle_testers`
- **Mode:** `0664` (-rw-rw-r--)
- **ACLs:** None

## Key Security Principles

1. **Setgid on Data Directories:** Ensures all files created maintain `shuttle_data_owners` group ownership regardless of which user/process creates them.

2. **No Execute on Data Files:** While directories need execute permission for traversal, the capital `X` in ACLs ensures files cannot be executed.

3. **Restricted "Others" Access:** Most paths have `0` for others permission, following principle of least privilege.

4. **Separate Log Access:** Logs have their own group (`shuttle_log_owners`) to allow debugging without granting data access.

5. **Read-Only Config Files:** Configuration files are read-only for most groups, with write access carefully controlled via ACLs.

## File Creation Permissions

### Shuttle Process File Creation
The shuttle application sets `umask(0007)` at startup, ensuring all files created by shuttle have consistent permissions:
- **Files created by shuttle:** `660` (rw-rw----) 
- **Directories created by shuttle:** `770` (rwxrwx---)
- **Applies regardless** of how shuttle is invoked (systemd, cron, manual)

### Samba User File Creation  
Files created by Samba users are controlled by **default ACLs** on directories:
- **Files created by Samba:** `660` (rw-rw----) - no execute permission
- **Directories created by Samba:** `770` (rwxrwx---) - traversable by shuttle
- **Consistent permissions** regardless of Samba user's umask

### Group Ownership via Setgid
The setgid bit (`2` in `2770`) ensures **all files inherit the directory's group**:
- **Without setgid:** Files get creator's primary group (e.g., `shuttle:shuttle`)
- **With setgid:** Files get directory's group (e.g., `shuttle:shuttle_data_owners`)
- **Result:** All group members can access files created by any process

## Resolved Design Decisions

1. **Root vs shuttle service account ownership:** Using `root:shuttle_data_owners` provides defense in depth while group permissions give shuttle process needed access.

2. **Umask enforcement:** Implemented via `os.umask(0007)` in shuttle Python code for universal coverage across all execution methods.

3. **Subdirectory permissions:** Not needed - setgid and default ACLs automatically handle inheritance.

4. **Hazard archive restrictions:** Same permissions as other data directories since files are encrypted and no longer dangerous.

## Implementation Notes

- These permissions assume standard groups have been created via the setup process
- The `shuttle_data_owners` group should include the shuttle service account
- Samba groups are only needed if network file sharing is enabled
- Test permissions are more permissive to allow easier debugging

## Security Summary

This permission model provides **three layers of protection**:

1. **Directory Permissions (2770):** Basic Linux permissions control directory access
2. **Default ACLs:** Ensure consistent file permissions regardless of creator's umask  
3. **Shuttle umask (0007):** Guarantees shuttle process creates secure files

**Result:** All files end up with `660` permissions and proper group ownership, whether created by:
- Shuttle process (via umask)
- Samba users (via default ACLs)  
- Manual operations (inherit from setgid + default ACLs)

This eliminates umask-related permission inconsistencies while maintaining the principle of least privilege.