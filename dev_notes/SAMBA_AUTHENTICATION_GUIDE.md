# Samba Authentication Methods Guide

## Overview

This guide explains the components and configurations needed for different Samba authentication methods, with focus on domain integration for production use and local accounts for testing/troubleshooting.

**Note**: Machines already have `/etc/krb5.conf` configured, which simplifies domain integration setup.

## 🔐 Domain Authentication Components

### What Samba Needs to Authenticate with Domain

#### 1. Kerberos Infrastructure
```
/etc/krb5.conf - Kerberos configuration (already configured)
```
- **Purpose**: Defines realm (domain), key distribution centers (domain controllers)
- **How it works**: Kerberos provides the cryptographic framework for secure authentication
- **What it contains**: Domain realm names, domain controller locations, encryption methods
- **Status**: ✅ Already configured on your machines

#### 2. Winbind Service
```
winbindd daemon + libnss_winbind + libpam_winbind
```
- **Purpose**: Translates between Windows domain concepts and Linux user/group concepts
- **How it works**: 
  - Maps domain SIDs to Linux UIDs/GIDs
  - Resolves domain users/groups to Linux system
  - Handles password authentication requests
- **Integration points**: 
  - NSS (Name Service Switch) - so `getent passwd` can see domain users
  - PAM (Pluggable Authentication Modules) - so domain users can authenticate

#### 3. Samba Configuration
```
/etc/samba/smb.conf with domain-specific settings
```
- **Key settings**:
  - `security = ads` - Use Active Directory authentication
  - `realm = DOMAIN.COM` - Kerberos realm
  - `winbind use default domain = yes` - Allow user@domain format
  - `idmap` configuration - How to map domain SIDs to Linux IDs

#### 4. Domain Join Process
```
Machine account in Active Directory + local secrets
```
- **What happens**: 
  - Machine gets a computer account in AD (like SAMBASERVER$)
  - Shared secret established between machine and domain
  - Machine can now ask domain "is this password valid for this user?"
- **Files created**: 
  - `/var/lib/samba/private/secrets.tdb` - Machine account credentials
  - Machine trust relationship in AD

#### 5. Authentication Flow
```
Client → Samba → Winbind → Domain Controller → Response
```
1. Client presents credentials to Samba
2. Samba asks winbind "authenticate this user"
3. Winbind contacts domain controller via Kerberos/LDAP
4. Domain controller validates and responds
5. Winbind maps domain user to local UID
6. Samba grants/denies access based on response

### Required Configuration Files

#### `/etc/samba/smb.conf` - Domain Member Configuration
```ini
[global]
    security = ads
    realm = COMPANY.COM
    workgroup = COMPANY
    winbind use default domain = yes
    winbind offline logon = false
    winbind enum users = yes
    winbind enum groups = yes
    
    # ID mapping - critical for domain integration
    idmap config * : backend = tdb
    idmap config * : range = 3000-7999
    idmap config COMPANY : backend = rid
    idmap config COMPANY : range = 10000-999999
```

#### `/etc/nsswitch.conf` - Name Service Switch
```
passwd:     files winbind
group:      files winbind
shadow:     files
```
- **Purpose**: Tells system to check local files first, then winbind for users/groups
- **Effect**: `getent passwd` will show both local and domain users

#### Required Services
```bash
systemctl enable winbind
systemctl start winbind
systemctl enable smbd
systemctl start smbd
```

---

## 🏠 Local User Password Authentication Components

### What Samba Needs for Local Authentication

#### 1. Password Database Backend

##### Option A: smbpasswd Backend
```
/etc/samba/smbpasswd file
```
- **Purpose**: Simple flat file with username:encrypted_password pairs
- **How it works**: 
  - Each line = one user's SMB password hash
  - Completely separate from Linux system passwords
  - Uses LM/NTLM password hashing
- **Management**: `smbpasswd` command adds/changes/deletes entries

**File Format**: `/etc/samba/smbpasswd`
```
# Format: username:uid:LM_hash:NT_hash:flags:last_change
testuser:1001:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX:YYYYYYYYYYYYYYYYYYYYYYYYYYYYYY:[U          ]:LCT-507C4C42:
```

##### Option B: tdbsam Backend (Recommended for testing)
```
/var/lib/samba/private/passdb.tdb
```
- **Purpose**: More advanced database with user attributes
- **How it works**:
  - Binary database (Trivial Database)
  - Stores passwords + additional user metadata
  - Supports more features than smbpasswd
- **Management**: `pdbedit` command manages users

#### 2. Samba Configuration

##### For smbpasswd Backend
```ini
[global]
    security = user
    passdb backend = smbpasswd
    workgroup = WORKGROUP
    map to guest = Bad User
```

##### For tdbsam Backend
```ini
[global]
    security = user
    passdb backend = tdbsam
    workgroup = WORKGROUP
    map to guest = Bad User
```

#### 3. Authentication Flow
```
Client → Samba → Local Password Database → Response
```
1. Client presents credentials to Samba
2. Samba looks up user in local password database
3. Samba compares provided password hash with stored hash
4. Samba grants/denies access based on match

---

## 🔄 Can Domain and Local Methods Operate Simultaneously?

### Short Answer: Not Really (for the same user)

### Technical Explanation

#### Samba's Authentication Method is Global
The `security =` setting in `[global]` section determines authentication method for the **entire Samba server**:
- `security = user` = All users authenticate locally
- `security = ads` = All users authenticate via domain

#### You Cannot Mix Methods Per User because:
1. **Authentication happens before user identification**
2. **Samba needs to know HOW to authenticate before knowing WHO is authenticating**
3. **The authentication protocol (SMB/CIFS) doesn't support per-user authentication methods**

#### What You CAN Do:

##### Option 1: Domain Integration with Local Fallback
```ini
[global]
    security = ads
    passdb backend = tdbsam
    winbind nested groups = yes
```
- **Domain users** authenticate via AD
- **Local users** can be added to tdbsam as backup
- **Limitation**: Local users still need domain-style names

##### Option 2: Local Authentication with Domain User Names
```ini
[global]
    security = user
    passdb backend = tdbsam
```
- Add domain users as local Samba users: `pdbedit -a "alice@domain.com"`
- **All authentication is local**, but usernames can look like domain users
- **Limitation**: Passwords are separate from domain passwords

##### Option 3: Multiple Samba Instances
- Run two separate Samba servers on different ports/IPs
- One configured for domain auth, one for local auth
- **Complex setup**, rarely used

---

## 🔄 Hybrid Setup for Testing

### Problem: Can't Run Both Simultaneously
The `security =` setting is global - you can't have some users authenticate via domain and others via local database in the same Samba instance.

### Solution: Testing Configuration

#### Option 1: Switchable Configuration
Create multiple smb.conf files and switch between them:

**`/etc/samba/smb.conf.domain`** - Domain config
```ini
[global]
    security = ads
    realm = COMPANY.COM
    workgroup = COMPANY
    winbind use default domain = yes
    # ... other domain settings
```

**`/etc/samba/smb.conf.local`** - Local config  
```ini
[global]
    security = user
    passdb backend = tdbsam
    workgroup = TESTGROUP
    # ... local settings
```

**Switch between them:**
```bash
# Switch to local for testing
cp /etc/samba/smb.conf.local /etc/samba/smb.conf
systemctl restart smbd winbind

# Switch back to domain
cp /etc/samba/smb.conf.domain /etc/samba/smb.conf  
systemctl restart smbd winbind
```

#### Option 2: Testing Share with Guest Access
```ini
[global]
    security = ads
    # ... domain settings

[test-share]
    path = /srv/test
    guest ok = yes
    guest only = yes
    writable = yes
    comment = Testing share - no authentication required
```

#### Option 3: Separate Samba Instance
Run a second Samba instance on different ports for testing:

**`/etc/samba/smb-test.conf`**
```ini
[global]
    security = user
    passdb backend = tdbsam
    workgroup = TESTGROUP
    
    # Different ports to avoid conflict
    smb ports = 1445
    nmb port = 1137
    
    # Different directories
    private dir = /var/lib/samba-test/private
    lock directory = /var/lib/samba-test/locks
```

**Start second instance:**
```bash
smbd -D --configfile=/etc/samba/smb-test.conf
```

---

## 🔧 Practical Implementation

### Primary Configuration: Domain Integration

Since `/etc/krb5.conf` is already configured, domain setup is simplified:

```bash
# 1. Install required components (winbind may already be installed)
apt-get install samba winbind libnss-winbind libpam-winbind

# 2. Configure Samba for domain membership
# Edit /etc/samba/smb.conf with domain settings (see above)

# 3. Configure NSS to use winbind
# Edit /etc/nsswitch.conf (see above)

# 4. Join domain
net ads join -U Administrator@company.com

# 5. Start services
systemctl enable --now winbind smbd nmbd

# 6. Test domain integration
wbinfo -t  # Test trust relationship
wbinfo -u  # List domain users
getent passwd | grep COMPANY  # See if domain users visible
```

### Testing Configuration: Local Accounts

```bash
# 1. Create backup of domain config
cp /etc/samba/smb.conf /etc/samba/smb.conf.domain

# 2. Create local testing config
cat > /etc/samba/smb.conf.local << EOF
[global]
    security = user
    passdb backend = tdbsam
    workgroup = TESTGROUP
    
[test-data]
    path = /srv/test-data
    valid users = testuser
    writable = yes
EOF

# 3. Switch to local config
cp /etc/samba/smb.conf.local /etc/samba/smb.conf

# 4. Create test user
useradd testuser  # Create system user first
pdbedit -a testuser  # Add to Samba database

# 5. Test local authentication
smbclient //localhost/test-data -U testuser

# 6. Switch back to domain when done
cp /etc/samba/smb.conf.domain /etc/samba/smb.conf
systemctl restart smbd winbind
```

---

## 🛠 Troubleshooting Tools

### Domain Integration Tests
```bash
wbinfo -t                    # Test domain trust
wbinfo -u                    # List domain users  
wbinfo -a "user@domain.com"  # Test authentication
kinit user@DOMAIN.COM        # Test Kerberos
net ads testjoin             # Test domain join status
net ads info                 # Show domain information
```

### Local Authentication Tests
```bash
pdbedit -L                   # List local Samba users
pdbedit -v username          # Show detailed user info
smbpasswd -x testuser        # Delete local user
testparm                     # Test configuration syntax
smbclient //localhost/share -U username  # Test local connection
```

### General Samba Tests
```bash
testparm                     # Validate smb.conf syntax
smbstatus                    # Show current connections
systemctl status smbd        # Check Samba daemon status
systemctl status winbind     # Check winbind status
tail -f /var/log/samba/*     # Monitor Samba logs
```

---

## 🎯 For Your Specific Architecture

### Your Authentication Flow
```
[Isolated Machine] 
    ↓ "I'm sambauser@domain.com with password XYZ"
[Samba Server] 
    ↓ "Domain controller, is this password valid for sambauser?"
[Domain Controller]
    ↓ "Yes, password is valid"
[Samba Server]
    ↓ "Access granted"
[Isolated Machine]
```

### Why Domain Integration is Required
- Your domain accounts don't exist in any local password database
- You'd have to manually recreate every domain user locally  
- Passwords would be separate and get out of sync
- **Samba server acts as authentication proxy** between isolated machines and domain

### Benefits of Having Local Testing Capability
- **Quick troubleshooting**: Test Samba functionality without domain dependencies
- **Network isolation testing**: Verify Samba works when domain is unreachable
- **Configuration validation**: Test share permissions and access controls
- **Performance testing**: Isolate Samba performance from domain authentication overhead

This approach gives you a robust domain-integrated setup for production with the ability to quickly switch to local authentication for testing and troubleshooting when needed.