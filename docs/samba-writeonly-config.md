# Samba Write-Only Configuration for Shuttle Inbox

## Overview

This configuration allows a domain service user to:
- ✅ Write files to /mnt/in
- ✅ List directories and see file metadata
- ❌ Read file contents
- ❌ Execute files

This is ideal for a malware scanning inbox where unscanned files should not be readable.

## Samba Configuration

Add this to `/etc/samba/smb.conf`:

```ini
[shuttle-writeonly-in]
   comment = Shuttle Write-Only Input Directory
   path = /mnt/in
   browseable = yes
   guest ok = no
   
   # Core write-only settings
   read only = no
   write list = @shuttle-writers, "DOMAIN\svc_shuttle"
   
   # Force permissions that prevent reading
   create mask = 0220
   directory mask = 0330
   force create mode = 0220
   force directory mode = 0330
   
   # Force ownership
   force user = shuttle-writer
   force group = shuttle-scanners
   
   # Prevent file execution
   veto files = /*.exe/*.com/*.bat/*.cmd/*.scr/*.vbs/*.js/
   delete veto files = yes
```

## Linux Permissions Setup

```bash
# Create users and groups
sudo groupadd shuttle-writers
sudo groupadd shuttle-scanners
sudo useradd -r -s /usr/sbin/nologin shuttle-writer

# Add domain service account to writers group
sudo usermod -a -G shuttle-writers "DOMAIN\svc_shuttle"

# Set base permissions
sudo chown -R shuttle-writer:shuttle-scanners /mnt/in
sudo chmod -R 330 /mnt/in

# Set special permissions for directories (need execute to traverse)
sudo find /mnt/in -type d -exec chmod 330 {} \;

# Set special permissions for files (write-only)
sudo find /mnt/in -type f -exec chmod 220 {} \;
```

## Permission Breakdown

### File Permissions: 220 (-w--w----)
- Owner (shuttle-writer): Write only
- Group (shuttle-scanners): Write only  
- Others: No access

### Directory Permissions: 330 (-wx-wx---)
- Owner: Write and execute (can create files, traverse)
- Group: Write and execute (can create files, traverse)
- Others: No access

**Note**: Execute on directories allows traversal/listing but NOT reading file contents.

## Important Considerations for Virtual Storage

Since you're using corporate virtual storage:

1. **Check Underlying Permissions First**
   ```bash
   # Check current mount permissions
   mount | grep /mnt/in
   
   # Check if storage has its own ACLs
   getfacl /mnt/in
   ```

2. **Test Impact on Storage**
   - These permissions only affect the Linux/Samba layer
   - Won't loosen underlying storage permissions
   - Storage ACLs take precedence if more restrictive

3. **Alternative: Storage-Level Solution**
   Consider if the storage system supports:
   - Write-only folders natively
   - API-based file submission
   - Separate ingestion endpoint

## Testing Write-Only Access

```bash
# Test as domain user (should fail to read)
sudo -u "DOMAIN\svc_shuttle" cat /mnt/in/testfile.txt
# Expected: Permission denied

# Test write (should succeed)
sudo -u "DOMAIN\svc_shuttle" cp /tmp/test.txt /mnt/in/
# Expected: Success

# Test directory listing (should succeed)
sudo -u "DOMAIN\svc_shuttle" ls -la /mnt/in/
# Expected: Shows files but can't read contents
```

## Security Notes

1. **No Read = No Verification**: Users can't verify what they uploaded
2. **Consider Audit Logging**: Track all write operations
3. **Implement Notifications**: Alert on new file arrivals
4. **Set Quotas**: Prevent filling disk with unreadable files

## Audit Configuration

Add to the share configuration:

```ini
   # Audit all write operations
   vfs objects = full_audit
   full_audit:prefix = %u|%I|%S
   full_audit:success = write pwrite create_file mkdir
   full_audit:failure = none
   full_audit:facility = local5
   full_audit:priority = NOTICE
```

This logs all successful writes to syslog for tracking.