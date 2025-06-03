# Samba Configuration for Shuttle

This guide explains how to set up Samba on a Linux server to share the `/mnt/in` directory with Windows users, with special focus on configuring permissions for the shuttle service user.

## Overview

The shuttle application runs as a specific user (we'll call it `zzzz` in this guide) that needs:
- Read access to scan files
- Write access to move/delete files  
- Create/delete directory permissions
- No execute permissions (for security, though this prevents using `ls`)

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

[shuttle-in]
   # Description shown when browsing shares
   comment = Shuttle Input Directory
   
   # Physical path on the server
   path = /mnt/in
   
   # Allow this share to be seen when browsing
   browseable = yes
   
   # Disable guest access (require authentication)
   guest ok = no
   
   # Allow both read and write access
   read only = no
   
   # File creation permissions (octal)
   # 0664 = rw-rw-r-- (owner: rw, group: rw, others: r)
   create mask = 0664
   
   # Directory creation permissions
   # 0775 = rwxrwxr-x (owner: rwx, group: rwx, others: r-x)
   directory mask = 0775
   
   # Force minimum permissions for files
   force create mode = 0664
   
   # Force minimum permissions for directories
   force directory mode = 0775
   
   # Only allow users in the shuttle-users group
   # @ prefix means it's a group, not individual user
   valid users = @shuttle-users
```

## 3. Create Users and Set Permissions

### Create the Shuttle Service User

```bash
# Create the shuttle service user 'zzzz' as a system account
#
# Command breakdown:
# useradd           - Command to add a new user to the system
# -r                - Create a system account (UID < 1000, no home dir by default)
#                     System accounts are for services, not human users
# -s /usr/sbin/nologin - Set the user's shell to nologin
#                     This prevents the user from logging in interactively
#                     Security measure: service accounts shouldn't have shell access
# zzzz              - The username we're creating
#
# Why use a system account?
# - Lower UID (typically < 1000) keeps it separate from human users
# - No home directory needed for a service
# - Shows up differently in user listings
# - Standard practice for service accounts
sudo useradd -r -s /usr/sbin/nologin zzzz

# Create group for all users who need Samba access
sudo groupadd shuttle-users

# Add the shuttle service user to the group
sudo usermod -a -G shuttle-users zzzz

# Add human users who need access (replace 'human' with actual username)
# -a = append to existing groups, -G = supplementary groups
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
# Change group ownership of files and directories
#
# Command breakdown for chgrp:
# sudo              - Run with superuser privileges (needed to change ownership)
# chgrp             - Change group ownership command (stands for "change group")
# -R                - Recursive flag - apply to all files and subdirectories
#                     Without -R, only /mnt/in itself would change, not its contents
# shuttle-users     - The new group name to assign
#                     This group must already exist (created with groupadd)
# /mnt/in           - The target directory whose group ownership will change
#
# This command changes the group owner of /mnt/in and everything inside it
# to the 'shuttle-users' group, ensuring all users in that group can access the files
sudo chgrp -R shuttle-users /mnt/in

# Set permissions for read/write but no execute (for data security)
#
# Command breakdown for find:
# sudo              - Run with superuser privileges (needed to change permissions)
# find              - Search for files/directories in a directory hierarchy
# /mnt/in           - Starting directory path (where to begin the search)
# -type f           - Filter by type: 'f' means regular files only
# -type d           - Filter by type: 'd' means directories only
# -exec             - Execute a command on each found item
# chmod             - Command to change file permissions
# 664               - Octal permission notation for files:
#                     6 (rw-) = 4+2 = read(4) + write(2) for owner
#                     6 (rw-) = 4+2 = read(4) + write(2) for group
#                     4 (r--) = 4   = read(4) only for others
#                     Result: rw-rw-r-- (no execute for security)
# 775               - Octal permission notation for directories:
#                     7 (rwx) = 4+2+1 = read(4) + write(2) + execute(1) for owner
#                     7 (rwx) = 4+2+1 = read(4) + write(2) + execute(1) for group  
#                     5 (r-x) = 4+1   = read(4) + execute(1) for others
#                     Result: rwxrwxr-x (execute needed to enter directories)
# {}                - Placeholder that gets replaced with each found file/directory path
#                     Example: if find locates /mnt/in/file1.txt, {} becomes /mnt/in/file1.txt
# \;                - Marks the end of the -exec command
#                     The backslash (\) escapes the semicolon so shell doesn't interpret it
#                     The semicolon (;) tells find where the -exec command ends
#
# First command: Find all files and set their permissions to 664
sudo find /mnt/in -type f -exec chmod 664 {} \;
# Second command: Find all directories and set their permissions to 775
sudo find /mnt/in -type d -exec chmod 775 {} \;

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

# 2. Set specific defaults for the shuttle user
# u:zzzz:rw means user zzzz gets read+write on new files
# This overrides the general ACL for this specific user
sudo setfacl -Rdm u:zzzz:rw /mnt/in
# Directories need execute permission, so set rwx for zzzz on directories
sudo find /mnt/in -type d -exec setfacl -dm u:zzzz:rwx {} \;

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
# Test as shuttle user
sudo -u zzzz touch /mnt/in/test-file.txt
ls -la /mnt/in/test-file.txt  # Should show -rw-rw-r--

# Test directory creation
sudo -u zzzz mkdir /mnt/in/test-dir
ls -la /mnt/in/ | grep test-dir  # Should show drwxrwxr-x

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

# Test listing shares as the shuttle service user
smbclient -L localhost -U zzzz

# Test listing shares as a human user
# -L = list shares, -U = username
# You'll be prompted for the password
smbclient -L localhost -U human

# Test accessing the share
# Connect to the share and get an interactive prompt
smbclient //localhost/shuttle-in -U zzzz

# Test from another Linux machine
smbclient //<server-ip>/shuttle-in -U zzzz
```

## 8. Windows Connection

Windows users can connect using:
- File Explorer: `\\<server-ip>\shuttle-in`
- Map Network Drive: `\\<server-ip>\shuttle-in`
- Command line: `net use Z: \\<server-ip>\shuttle-in`

### Connection Details:
- Share name: `shuttle-in`
- Username: Linux username (e.g., `human`)
- Password: Password set with `smbpasswd`

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
- Files are created with 664 permissions (no execute) for security
- Directories need 775 (execute required to traverse)
- Consider using `noexec` mount option for additional security
- The shuttle service user (zzzz) has no shell access

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
