# Samba Configuration for Shuttle

This guide explains how to set up Samba on a Linux server to share the `/mnt/in` directory with Windows users, with special focus on configuring permissions for the shuttle service user.

## Overview

yThis configuration supports two service accounts with different permission levels:

### Service Account: `sa-shuttle-run`
- **Purpose**: Runs the shuttle application for scanning and processing
- **File Access**: Read/write files, no execute
- **Directory Access**: Read/write/execute (for traversal and listing)
- **Security**: Full access needed to scan, move, and delete files

### Service Account: `sa-shuttle-lab` 
- **Purpose**: Receives files from lab systems for scanning
- **File Access**: Write-only (no read, no execute)
- **Directory Access**: Read/write/list directories
- **Security**: Cannot read unscanned files, preventing exposure to malware

**Note**: For additional write-only configurations, see [samba-writeonly-config.md](./samba-writeonly-config.md)

## 1. Install Samba

```bash
# Ubuntu/Debian
# Update package list and install Samba server and utilities
sudo apt update && sudo apt install samba samba-common-bin

# RHEL/CentOS/Rocky
# Install Samba server, client tools, and common utilities
sudo dnf install samba samba-client samba-common
```

## 2. Configure Samba for /mnt/in

Edit the Samba configuration file:

```bash
# Open Samba's main configuration file with a text editor
sudo nano /etc/samba/smb.conf
```

Add this configuration with detailed comments:

```ini
[global]
   # Windows workgroup name (WORKGROUP is the default)
   workgroup = WORKGROUP
   
   # Description that appears when browsing the server
   server string = File Server
   
   # Use user-level security (each user has their own password)
   security = user
   
   # How to handle users without valid authentication
   # 'bad user' = reject connections from unknown users
   map to guest = bad user
   
   # Don't act as a DNS proxy
   dns proxy = no
   
   # Performance optimizations for file transfers
   # TCP_NODELAY = disable Nagle algorithm for better responsiveness
   # IPTOS_LOWDELAY = request low delay IP service
   # SO_RCVBUF/SO_SNDBUF = set receive/send buffer sizes to 128KB
   socket options = TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=131072 SO_SNDBUF=131072
   
   # Use kernel sendfile() for better performance
   use sendfile = yes

# Share for shuttle processing service (full access)
[shuttle-processor]
   comment = Shuttle Processing Access
   path = /mnt/in
   browseable = yes
   guest ok = no
   read only = no
   
   # Standard permissions for processing
   create mask = 0664
   directory mask = 0775
   force create mode = 0664
   force directory mode = 0775
   
   # Only allow processor service account
   valid users = sa-shuttle-run

# Share for lab submission (write-only access)
[shuttle-lab-inbox]
   comment = Shuttle Lab File Submission
   path = /mnt/in
   browseable = yes
   guest ok = no
   read only = no
   
   # Write-only permissions
   write list = sa-shuttle-lab
   read list = 
   
   # Restrictive file permissions (write-only)
   create mask = 0220
   directory mask = 0330
   force create mode = 0220
   force directory mode = 0330
   
   # Force ownership to prevent conflicts
   force user = sa-shuttle-run
   force group = shuttle-processors
   
   # Only allow lab service account
   valid users = sa-shuttle-lab

# General share for human users (standard access)
[shuttle-in]
   comment = Shuttle Input Directory
   path = /mnt/in
   browseable = yes
   guest ok = no
   read only = no
   
   create mask = 0664
   directory mask = 0775
   force create mode = 0664
   force directory mode = 0775
   
   valid users = @shuttle-users
```

## 3. Create Users and Set Permissions

### Create the Shuttle Service Users

```bash
# Create the shuttle processing service user
# This user runs the shuttle application and needs full access
sudo useradd -r -s /usr/sbin/nologin sa-shuttle-run

# Create the lab input service user  
# This user receives files from lab systems but cannot read them
sudo useradd -r -s /usr/sbin/nologin sa-shuttle-lab

# Create groups for different access levels
sudo groupadd shuttle-processors  # Full read/write access
sudo groupadd shuttle-submitters   # Write-only access
sudo groupadd shuttle-users        # General Samba access group

# Add shuttle processing user to processor group
sudo usermod -a -G shuttle-processors,shuttle-users sa-shuttle-run

# Add lab user to submitter group
sudo usermod -a -G shuttle-submitters,shuttle-users sa-shuttle-lab

# Add human users who need access (replace 'human' with actual username)
sudo usermod -a -G shuttle-users human
```

### Managing Domain Users and Non-Local Accounts

When dealing with domain users (Active Directory, LDAP, etc.), service accounts, and shared accounts, the process differs:

#### 1. Domain Users (Active Directory/LDAP)

```bash
# For Active Directory domain users, the format depends on your Winbind/SSSD configuration
#
# Option A: Using Winbind (domain\user format)
# Domain users appear as DOMAIN\username or DOMAIN+username
sudo usermod -a -G shuttle-users "DOMAIN\username"
# or
sudo usermod -a -G shuttle-users "DOMAIN+username"

# Option B: Using SSSD (user@domain format)
# SSSD often maps domain users as user@domain.com
sudo usermod -a -G shuttle-users "user@domain.com"

# Option C: If domain users are mapped to local format
# Some configurations map domain users without domain prefix
sudo usermod -a -G shuttle-users domain_username

# Verify domain user's groups
id "DOMAIN\username"
groups "DOMAIN\username"
```

#### 2. Nested Domain Groups

```bash
# Best practice: Add entire domain groups instead of individual users
# This requires proper group mapping in smb.conf or sssd.conf

# Add a domain group to local group (requires group mapping)
# First, ensure group mapping is enabled in /etc/samba/smb.conf:
# [global]
#   winbind nested groups = yes
#   winbind expand groups = 5

# Then add the domain group
sudo usermod -a -G shuttle-users "DOMAIN\Domain Users"
# or use net command for group mapping
sudo net groupmap add ntgroup="DOMAIN\FileShareUsers" unixgroup=shuttle-users type=domain
```

#### 3. Service Accounts and Shared Accounts

```bash
# For service accounts that already exist in the domain
# These often have specific naming conventions like svc_appname
sudo usermod -a -G shuttle-users "DOMAIN\svc_shuttle"

# For shared/generic accounts (not recommended but sometimes necessary)
sudo usermod -a -G shuttle-users "DOMAIN\shared_account"

# Verify the account can be resolved
getent passwd "DOMAIN\svc_shuttle"
```

#### 4. Verifying Domain Integration

```bash
# Check if domain users are visible to the system
# This depends on your NSS (Name Service Switch) configuration

# List all users including domain users
getent passwd

# Check specific domain user
getent passwd "DOMAIN\username"

# Verify group membership for domain users
getent group shuttle-users

# Test domain user authentication
# This verifies the user exists and can authenticate
wbinfo -a "DOMAIN\username"
# or
id "DOMAIN\username"
```

#### 5. Samba Configuration for Domain Users

In your smb.conf, add these settings for domain authentication:

```ini
[global]
   # ... existing settings ...
   
   # Domain membership settings
   security = ADS
   realm = YOUR.DOMAIN.COM
   workgroup = DOMAIN
   
   # Winbind settings for domain users
   winbind use default domain = no
   winbind nested groups = yes
   winbind expand groups = 5
   winbind refresh tickets = yes
   
   # ID mapping for domain users
   idmap config * : backend = tdb
   idmap config * : range = 10000-99999
   idmap config DOMAIN : backend = rid
   idmap config DOMAIN : range = 100000-999999
   
   # Template settings for domain users
   template shell = /bin/bash
   template homedir = /home/%D/%U
```

#### 6. Important Considerations for Domain Users

```bash
# Domain User Format Variations
# Different systems may represent domain users differently:
# - DOMAIN\user (Windows style with backslash)
# - DOMAIN+user (Winbind with + separator)
# - DOMAIN/user (Some LDAP configurations)
# - user@domain.com (Kerberos principal style)
# - domain.com\user (Fully qualified domain)

# IMPORTANT: Use quotes when domain separator includes special characters
# The backslash needs quotes or escaping:
sudo usermod -a -G shuttle-users "DOMAIN\user"  # Quoted
sudo usermod -a -G shuttle-users DOMAIN\\user   # Escaped

# Common issues and solutions:

# 1. "user not found" errors
# - Verify NSS is configured: /etc/nsswitch.conf should include winbind or sssd
# - Check domain connection: wbinfo -t
# - Ensure services are running: systemctl status winbind sssd

# 2. Group changes not taking effect
# - Domain users may need to log out/in for group changes
# - Clear NSS cache: nscd -i passwd; nscd -i group
# - For SSSD: sss_cache -E

# 3. Permission denied despite group membership
# - Check effective groups: id "DOMAIN\user"
# - Verify Samba uses the correct groups: net groupmap list
# - Check token size limits for users with many groups
```

### Set Up Samba Passwords

```bash
# smbpasswd : Create Samba password for the shuttle service user
# -a = add user
# -n = no password (for service accounts)
# For service account with no interactive login:
sudo smbpasswd -a -n zzzz

# Or if you want the service account to have a password:
sudo smbpasswd -a zzzz

# Create Samba password for human users
sudo smbpasswd -a human
```

#### Samba Passwords for Domain Users

Domain users authenticate differently and typically DON'T need smbpasswd:

```bash
# Domain users authenticate through Active Directory/Kerberos
# They use their domain credentials, NOT local Samba passwords

# IMPORTANT: Do NOT use smbpasswd for domain users
# This will fail:
# sudo smbpasswd -a "DOMAIN\user"  # DON'T DO THIS

# Instead, domain users authenticate with:
# 1. Their domain username (DOMAIN\user or user@domain.com)
# 2. Their domain password (same as Windows login)

# The authentication flow:
# Windows → Samba → Winbind/SSSD → Active Directory → Validate credentials

# To test domain user authentication:
# From Windows:
net use \\server\share /user:DOMAIN\username
# You'll be prompted for their domain password

# From Linux:
smbclient //server/share -U DOMAIN\\username
# Enter domain password when prompted

# Common authentication issues:
# 1. "NT_STATUS_NO_SUCH_USER" - User format is wrong or NSS not configured
# 2. "NT_STATUS_WRONG_PASSWORD" - Domain password is incorrect
# 3. "NT_STATUS_TRUSTED_DOMAIN_FAILURE" - Domain trust issues
```

### Configure Directory Permissions

```bash
# Set base ownership to shuttle processing user
# This ensures the scanner can access all files
sudo chown -R sa-shuttle-run:shuttle-processors /mnt/in

# Set base permissions for existing files and directories
# Files: 660 (owner: rw, group: rw, others: none)
# Directories: 770 (owner: rwx, group: rwx, others: none)
sudo find /mnt/in -type f -exec chmod 660 {} \;
sudo find /mnt/in -type d -exec chmod 770 {} \;

# Alternative: If you need to allow file execution
# sudo chmod -R 775 /mnt/in

# Ensure new files/directories inherit the group ownership
# Set the setgid (Set Group ID) bit on directories
# 
# What is setgid?
# - A special permission bit that changes how new files/directories inherit ownership
# - When set on a directory, all new files created inside will inherit the directory's group
# - Without setgid: new files get the creator's primary group
# - With setgid: new files get the parent directory's group
#
# Why do we need it?
# - Ensures all files in /mnt/in belong to 'shuttle-users' group
# - Prevents permission issues when different users create files
# - Critical for shared directories where multiple users collaborate
#
# Command breakdown:
# find /mnt/in        - Start searching from /mnt/in directory
# -type d             - Only find directories (not files)
# -exec               - For each found directory, execute the following command
# chmod g+s           - Add (+) setgid bit (s) to group permissions (g)
# {}                  - Placeholder for each found directory
# \;                  - End of the -exec command
sudo find /mnt/in -type d -exec chmod g+s {} \;
```

### Permission Inheritance for New Files

**Important**: The commands above only affect existing files. New files created through different methods need additional configuration:

#### Via Samba (Windows Users)
New files created through Samba will use the permissions defined in smb.conf:
- `create mask = 0664` - Maximum permissions for new files (rw-rw-r--)
- `force create mode = 0664` - Minimum permissions for new files
- `directory mask = 0775` - Maximum permissions for new directories (rwxrwxr-x)
- `force directory mode = 0775` - Minimum permissions for new directories

#### Via Local Copy (SSH/Shell)
Files created locally depend on:

1. **umask** - The user's default permission mask
   - umask is a "mask" that removes permissions from newly created files
   - Default file permissions start at 666 (rw-rw-rw-)
   - Default directory permissions start at 777 (rwxrwxrwx)
   - umask subtracts from these defaults
   - Example: umask 0113 removes write for others (1), execute for group (1), execute+write for others (3)
   - Result: 666 - 113 = 664 for files, 777 - 113 = 775 for directories

2. **setgid bit** - Ensures group inheritance (already set above)
   - Makes new files inherit the parent directory's group
   - Does NOT affect permission bits, only ownership

3. **ACL (Access Control Lists) defaults** - Most reliable method for consistent permissions
   - ACLs provide fine-grained permission control beyond traditional Unix permissions
   - Default ACLs are templates that apply to all new files/directories
   - More flexible than umask - can set different defaults for different users/groups

#### Complete Inheritance Solution

```bash
# 1. Set default ACLs for all new files and directories
#
# What are ACLs?
# - Access Control Lists provide more granular permissions than traditional Unix permissions
# - Can set different permissions for multiple users/groups on the same file
# - Default ACLs (set with -d) are templates for new files/directories
#
# Command breakdown for setfacl:
# setfacl           - Set file access control lists
# -R                - Recursive (apply to all subdirectories)
# -d                - Set default ACL (for new files created in directory)
# -m                - Modify ACL (add or change entries)
# u::rw             - User (owner) gets read+write
# g::rw             - Group gets read+write  
# o::r              - Others get read only
# /mnt/in           - Target directory
#
# This sets defaults for ALL new files to be rw-rw-r-- (664)
sudo setfacl -Rdm u::rw,g::rw,o::r /mnt/in

# For directories, we need different permissions (need execute to enter)
# This finds all directories and sets their default ACL to rwxrwxr-x (775)
# Why separate command? Directories need execute permission to be traversable
sudo find /mnt/in -type d -exec setfacl -dm u::rwx,g::rwx,o::rx {} \;

# 2. Set specific ACLs for service accounts

# sa-shuttle-run: Full access (read/write files, read/write/execute directories)
sudo setfacl -Rdm u:sa-shuttle-run:rw /mnt/in
sudo find /mnt/in -type d -exec setfacl -dm u:sa-shuttle-run:rwx {} \;
sudo setfacl -Rm u:sa-shuttle-run:rw /mnt/in
sudo find /mnt/in -type d -exec setfacl -m u:sa-shuttle-run:rwx {} \;

# sa-shuttle-lab: Write-only for files, read/write/execute for directories
sudo setfacl -Rdm u:sa-shuttle-lab:-w- /mnt/in
sudo find /mnt/in -type d -exec setfacl -dm u:sa-shuttle-lab:rwx {} \;
sudo setfacl -Rm u:sa-shuttle-lab:-w- /mnt/in
sudo find /mnt/in -type d -exec setfacl -m u:sa-shuttle-lab:rwx {} \;

# 3. Configure umask for the shuttle service user
#
# What does this do?
# - Creates a shell script that sets umask when zzzz logs in
# - /etc/profile.d/ scripts run for all users at login
# - umask 0113 calculation:
#   - Start with 0777 (all permissions)
#   - Subtract 0113: 0 (owner unchanged), 1 (remove execute from group), 
#     1 (remove execute from others), 3 (remove write+execute from others)
#   - Result: 664 for files, 775 for directories
#
# Command breakdown:
# echo "umask 0113"         - Output the umask command
# |                         - Pipe output to next command
# sudo tee                  - Write to file with sudo privileges
# /etc/profile.d/shuttle-umask.sh - Location for login scripts
echo "umask 0113" | sudo tee /etc/profile.d/shuttle-umask.sh
# Make the script executable so it runs at login
sudo chmod +x /etc/profile.d/shuttle-umask.sh

# 4. For systemd services, set umask in the service file
# Add "UMask=0113" to the [Service] section

# 5. Verify ACL settings
getfacl /mnt/in

# Example output:
# # file: /mnt/in
# # owner: root
# # group: shuttle-users
# # flags: -s-
# user::rwx
# group::rwx
# other::r-x
# default:user::rw-
# default:user:zzzz:rw-
# default:group::rw-
# default:other::r--
```

#### Testing Permission Inheritance

```bash
# Test as shuttle processor (should have full access)
sudo -u sa-shuttle-run touch /mnt/in/test-processor-file.txt
sudo -u sa-shuttle-run cat /mnt/in/test-processor-file.txt  # Should succeed
ls -la /mnt/in/test-processor-file.txt  # Should show -rw-rw----

# Test as lab user (write-only)
sudo -u sa-shuttle-lab touch /mnt/in/test-lab-file.txt
sudo -u sa-shuttle-lab cat /mnt/in/test-lab-file.txt  # Should fail (Permission denied)
sudo -u sa-shuttle-lab ls /mnt/in/  # Should succeed (can list directories)

# Test directory creation
sudo -u sa-shuttle-run mkdir /mnt/in/test-dir
sudo -u sa-shuttle-lab mkdir /mnt/in/test-lab-dir  # Should succeed
ls -la /mnt/in/ | grep test-dir  # Should show drwxrwx---

# Test via Samba (from Windows)
# Create a file through Windows Explorer
# Check permissions: should match the Samba create mask settings
```

## 4. Advanced Permission Configuration

### Option A: No Execute Permissions (More Secure)

To prevent execution while allowing read/write:

```bash
# Mount the filesystem with noexec option
#
# What is noexec?
# - A mount option that prevents ANY file execution on the filesystem
# - Even if a file has execute permissions, it cannot be run
# - Provides strong security but limits functionality
#
# To make permanent, edit /etc/fstab:
# /etc/fstab format: device mount-point filesystem options dump pass
# /dev/sdX1         - The device to mount (replace with actual device)
# /mnt/in           - Where to mount it
# ext4              - Filesystem type
# defaults,noexec,nosuid - Mount options:
#   - defaults: rw, suid, dev, exec, auto, nouser, async
#   - noexec: prevent execution of any files
#   - nosuid: ignore setuid/setgid bits (security measure)
# 0                 - dump frequency (0 = don't backup)
# 2                 - fsck order (2 = check after root filesystem)
#
# Example /etc/fstab entry:
# /dev/sdX1 /mnt/in ext4 defaults,noexec,nosuid 0 2

# Or remount temporarily (until next reboot):
# -o remount        - Remount an already mounted filesystem
# noexec            - Add the noexec option
sudo mount -o remount,noexec /mnt/in
```

**Note**: The `noexec` option prevents ALL execution, including `ls`. Users can still list files through Samba, but not via SSH.

### Option B: ACL-based Permissions (More Flexible)

```bash
# Enable ACLs on the filesystem (if not already enabled)
sudo mount -o remount,acl /mnt/in

# Set default ACLs for the shuttle user
# This gives zzzz read/write but no execute on files
sudo setfacl -Rdm u:zzzz:rw- /mnt/in
sudo setfacl -Rm u:zzzz:rw- /mnt/in

# For directories, we need execute to traverse
sudo find /mnt/in -type d -exec setfacl -m u:zzzz:rwx {} \;
sudo find /mnt/in -type d -exec setfacl -dm u:zzzz:rwx {} \;
```

## 5. Configure Firewall

### Ubuntu (ufw - Uncomplicated Firewall)

```bash
# Allow all Samba-related ports with one command
sudo ufw allow samba

# Or manually specify each port:
# Port 139 - NetBIOS Session Service (SMB over NetBIOS)
sudo ufw allow 139/tcp

# Port 445 - Direct SMB over TCP (modern Windows)
sudo ufw allow 445/tcp

# Port 137 - NetBIOS Name Service
sudo ufw allow 137/udp

# Port 138 - NetBIOS Datagram Service
sudo ufw allow 138/udp

# Check firewall status
sudo ufw status
```

### RHEL/CentOS (firewalld)

```bash
# Add Samba service to firewall (includes all necessary ports)
# --permanent = persist after reboot
sudo firewall-cmd --permanent --add-service=samba

# Reload firewall to apply changes
sudo firewall-cmd --reload

# Verify the service is added
sudo firewall-cmd --list-services
```

## 6. Start and Enable Services

```bash
# Restart Samba services to apply configuration changes
# smbd = handles file/printer sharing
# nmbd = handles NetBIOS name resolution
sudo systemctl restart smbd nmbd

# Enable services to start automatically at boot
sudo systemctl enable smbd nmbd

# Check if services are running properly
# Look for "active (running)" in the output
sudo systemctl status smbd nmbd

# View recent log entries if there are issues
sudo journalctl -u smbd -u nmbd --since "5 minutes ago"
```

## 7. Test Configuration

```bash
# Test Samba configuration file for syntax errors
# This will also show the effective configuration
sudo testparm

# Test listing shares as the shuttle processing user
smbclient -L localhost -U sa-shuttle-run

# Test listing shares as the lab user
smbclient -L localhost -U sa-shuttle-lab

# Test accessing the shares
# Processor should have full access
smbclient //localhost/shuttle-processor -U sa-shuttle-run

# Lab user should have write-only access
smbclient //localhost/shuttle-lab-inbox -U sa-shuttle-lab

# Test from another Linux machine
smbclient //<server-ip>/shuttle-in -U zzzz
```

## 8. Windows Connection

Windows users can connect using:
- File Explorer: `\\<server-ip>\shuttle-in`
- Map Network Drive: `\\<server-ip>\shuttle-in`
- Command line: `net use Z: \\<server-ip>\shuttle-in`

### Connection Details:

**For Shuttle Processing:**
- Share name: `shuttle-processor`
- Username: `sa-shuttle-run`
- Password: Set with `smbpasswd`
- Access: Full read/write

**For Lab File Submission:**
- Share name: `shuttle-lab-inbox`
- Username: `sa-shuttle-lab`
- Password: Set with `smbpasswd`
- Access: Write-only (cannot read files)

**For General Users:**
- Share name: `shuttle-in`
- Username: Linux username (e.g., `human`)
- Password: Set with `smbpasswd`

## Troubleshooting

1. **Cannot connect**: Check firewall rules and ensure Samba ports (139, 445) are open
2. **Permission denied**: Verify user is in `shuttle-users` group and has Samba password set
3. **Cannot see share**: Ensure `browseable = yes` in config and restart Samba
4. **Behind jump boxes**: Ensure Samba ports are forwarded through network infrastructure

## Security Notes

### Access Control
- Only users in the `shuttle-users` group can access the share
- Guest access is disabled (`guest ok = no`)
- Each user must have both a Linux account and Samba password

### Permission Security
- **sa-shuttle-run**: Full access to scan and process files (660/770 permissions)
- **sa-shuttle-lab**: Write-only access prevents reading unscanned files
- Files created with no execute permissions for security
- Directories need execute permissions for traversal
- Consider using `noexec` mount option for additional security
- All service accounts have no shell access (`/usr/sbin/nologin`)
- ACLs provide granular control over file access

### Additional Hardening
```bash
# Restrict Samba to specific network interfaces
# Add to [global] section in smb.conf:
# interfaces = 192.168.1.0/24 127.0.0.1
# bind interfaces only = yes

# Set up audit logging for the share
# Add to [shuttle-in] section:
# vfs objects = full_audit
# full_audit:prefix = %u|%I|%m|%S
# full_audit:success = mkdir rename unlink rmdir write
# full_audit:failure = none
# full_audit:facility = local7
# full_audit:priority = NOTICE
```
