# PAM common-auth File Format Guide

## Overview

PAM (Pluggable Authentication Modules) configuration files control how authentication works on Linux systems. The `common-auth` file is typically included by other PAM-aware services for shared authentication configuration.

## Basic Structure

Each line in a PAM configuration file follows this format:
```
type  control  module  [module-arguments]
```

## The Four Fields

### 1. **Type** (Required)
Defines which PAM management group the module belongs to:
- `auth` - Authentication (verifying who you are)
- `account` - Account management (is account valid/expired?)
- `session` - Session management (setup/teardown)
- `password` - Password management (changing passwords)

### 2. **Control** (Required)
Determines how PAM processes the result:
- `required` - Must succeed for overall success, but continues checking other modules
- `requisite` - Must succeed; failure immediately returns failure
- `sufficient` - Success immediately returns success (unless prior required failed)
- `optional` - Result only matters if it's the only module

**Advanced syntax:**
```
[value1=action1 value2=action2 ...]
```
Example: `[success=ok new_authtok_reqd=ok ignore=ignore default=bad]`

### 3. **Module** (Required)
The PAM module to invoke:
- `pam_unix.so` - Traditional Unix authentication
- `pam_krb5.so` - Kerberos authentication
- `pam_winbind.so` - Winbind authentication
- `pam_ldap.so` - LDAP authentication
- `pam_sss.so` - SSSD authentication
- `pam_deny.so` - Always deny
- `pam_permit.so` - Always permit
- `pam_env.so` - Set environment variables
- `pam_limits.so` - Resource limits
- `pam_systemd.so` - Register user sessions with systemd

### 4. **Module Arguments** (Optional)
Module-specific options:
- `nullok` - Allow empty passwords
- `try_first_pass` - Try password from previous module
- `use_first_pass` - Must use password from previous module
- `debug` - Enable debugging
- `minimum_uid=N` - Only apply to UIDs >= N
- `audit` - Enable audit logging

## Example common-auth File

```
# Traditional Unix authentication
auth    required        pam_unix.so nullok_secure

# Kerberos authentication
auth    sufficient      pam_krb5.so use_first_pass

# LDAP authentication
auth    sufficient      pam_ldap.so use_first_pass

# Deny if nothing else worked
auth    required        pam_deny.so
```

## How Authentication Flows

1. PAM tries modules in order
2. Each module returns: success, failure, or other states
3. Control flags determine whether to continue or stop
4. Final decision based on all module results

## Common Patterns

### Local + Domain Auth
```
auth    sufficient      pam_unix.so nullok_secure
auth    sufficient      pam_krb5.so use_first_pass
auth    required        pam_deny.so
```
- First tries local password
- Then tries Kerberos
- Denies if both fail

### Domain-First Auth
```
auth    sufficient      pam_krb5.so
auth    sufficient      pam_unix.so nullok_secure try_first_pass
auth    required        pam_deny.so
```
- Tries domain first
- Falls back to local
- Uses same password for both attempts

### Complex Control Example
```
auth    [success=2 default=ignore]      pam_unix.so nullok_secure
auth    [success=1 default=ignore]      pam_krb5.so use_first_pass
auth    requisite                       pam_deny.so
auth    required                        pam_permit.so
```
- If unix succeeds, skip 2 lines (go to pam_permit)
- If krb5 succeeds, skip 1 line (go to pam_permit)
- Otherwise hit pam_deny

## Include Directives

Modern PAM often uses includes:
```
@include common-auth
```
This includes the contents of `/etc/pam.d/common-auth`

## The minimum_uid Parameter

### What is minimum_uid=65535?

The `minimum_uid=N` parameter tells a PAM module to only process users with UID >= N. Setting it to 65535 effectively **disables** the module for all real users because:

1. **Normal user UIDs range**:
   - System users: 0-999
   - Regular users: 1000-65534
   - Nobody user: 65534 (often)
   - 65535 is typically the maximum UID on many systems

2. **Why use minimum_uid=65535?**
   - **Effectively disables the module** without removing the line
   - **Preserves configuration** for reference/documentation
   - **Allows easy re-enabling** by changing the number
   - **Common in transitions** when migrating authentication methods

### Example Uses of minimum_uid

```bash
# Only use Kerberos for regular users (not system accounts)
auth    sufficient    pam_krb5.so minimum_uid=1000

# Disable winbind temporarily without removing configuration
auth    sufficient    pam_winbind.so minimum_uid=65535

# Only apply LDAP auth to users with UID >= 10000 (domain users)
auth    sufficient    pam_ldap.so minimum_uid=10000
```

### Common UID Ranges

- **0**: root user
- **1-99**: System users (distro-specific)
- **100-999**: Dynamic system users
- **1000-65533**: Regular human users
- **65534**: nobody/nogroup
- **65535**: Often used as "disable" threshold

## Your Situation Analysis

Since you can SSH and sudo with domain passwords but have no winbind/sssd, you likely have:

1. `pam_krb5.so` configured in common-auth
2. Kerberos tickets being obtained during authentication
3. NSS not configured for domain users (hence no `getent passwd` for domain users)

This would look something like:
```
auth    [success=2 default=ignore]      pam_unix.so nullok_secure
auth    [success=1 default=ignore]      pam_krb5.so use_first_pass
auth    requisite                       pam_deny.so
auth    required                        pam_permit.so
```

This explains why authentication works but user enumeration doesn't - PAM handles the auth, but NSS doesn't know about domain users.

## Debugging PAM

### Enable Debug Mode
Add `debug` to module arguments:
```
auth    sufficient    pam_krb5.so debug
```

### Check Logs
- `/var/log/auth.log` (Debian/Ubuntu)
- `/var/log/secure` (RHEL/CentOS)
- `journalctl -u sshd` (systemd systems)

### Test Authentication
```bash
# Test PAM stack for a service
pamtester sshd username authenticate

# Check PAM configuration
pam-auth-update --package
```

## Security Considerations

1. **Order matters** - Put most likely auth method first for performance
2. **Use sufficient carefully** - Can bypass later security checks
3. **Always end with pam_deny.so** - Explicit deny for safety
4. **Test changes carefully** - Bad PAM config can lock you out
5. **Keep root session open** - When making PAM changes

## References

- `man pam.conf` - PAM configuration file syntax
- `man pam.d` - PAM directory configuration
- `man 8 pam` - PAM overview
- Individual module man pages (e.g., `man pam_unix`)