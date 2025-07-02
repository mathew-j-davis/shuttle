# Shuttle Security Audit Tool

The security audit tool validates production Shuttle deployments against expected security configurations.

## Quick Start

```bash
# Basic audit using production defaults
python3 scripts/security_audit.py \
  --audit-config example/security_audit_config/production_audit.yaml \
  --shuttle-config /path/to/your/shuttle_config.yaml

# Verbose output
python3 scripts/security_audit.py \
  --audit-config example/security_audit_config/production_audit.yaml \
  --shuttle-config /path/to/your/shuttle_config.yaml \
  --verbose
```

## What It Checks

### User Account Security
- ✅ Service accounts have `nologin` shells
- ✅ User group memberships match expected configuration
- ✅ Home directories are correctly configured
- ✅ Account types match security model

### Group Configuration
- ✅ Required groups exist with correct members
- ✅ No unauthorized group memberships
- ✅ Group isolation policies enforced

### Samba Security Model
- 🚨 **CRITICAL**: Samba users cannot login interactively
- 🚨 **CRITICAL**: Samba users isolated from other groups
- ✅ Shell restrictions enforced
- ✅ Group membership restrictions

### Path Permissions
- ✅ Correct ownership (from shuttle config paths)
- 🚨 **CRITICAL**: No world-readable files
- ⚠️ **WARNING**: No executable files in data directories
- ✅ Default ACLs present on directories
- ✅ Proper permission levels

### File System Security
- ✅ Scans files in shuttle directories
- 🚨 **CRITICAL**: Detects world-readable files
- ⚠️ **WARNING**: Detects world-writable files
- ⚠️ **WARNING**: Detects executable files in data paths

## Exit Codes

- `0`: All checks passed or warnings only
- `1`: Errors found (configuration issues)
- `2`: Critical security issues found

## Configuration

The audit tool uses two configuration files:

1. **Audit Config** (`production_audit.yaml`): Defines expected security state
2. **Shuttle Config**: Your actual shuttle configuration file

### Customizing Audit Configuration

Edit `production_audit.yaml` to match your deployment:

```yaml
# Add or modify expected users
users:
  - name: my_custom_user
    account_type: service
    groups:
      primary: my_group
      secondary: [other_group]

# Add or modify expected groups  
groups:
  - name: my_group
    members: [my_custom_user]
    allow_extra_members: false
```

## Security Model Validation

The tool enforces Shuttle's security model:

### Service Account Isolation
- Service accounts use `nologin` shells
- No interactive access capability
- Group-based permission model

### Samba User Restrictions
- Samba users completely isolated
- Cannot be members of other shuttle groups
- Prevents privilege escalation

### File Permission Security
- No world-readable files (prevents data exposure)
- No executable files in data directories (prevents malware)
- Proper ownership and group access

## Integration

### CI/CD Pipeline
```bash
#!/bin/bash
# Add to deployment verification script
python3 scripts/security_audit.py \
  --audit-config security_audit_config/production_audit.yaml \
  --shuttle-config /etc/shuttle/shuttle_config.yaml

if [ $? -eq 2 ]; then
    echo "CRITICAL security issues found - deployment blocked"
    exit 1
fi
```

### Monitoring
Run periodically to detect configuration drift:

```bash
# Daily security audit via cron
0 2 * * * /path/to/shuttle/scripts/security_audit.py \
  --audit-config /etc/shuttle/security_audit.yaml \
  --shuttle-config /etc/shuttle/shuttle_config.yaml \
  >> /var/log/shuttle/security_audit.log 2>&1
```

## Troubleshooting

### Common Issues

**User not found errors**:
- Verify users were created during installation
- Check spelling in audit configuration

**Group membership mismatches**:
- Run `groups username` to see actual memberships
- Update audit config to match intended design

**Path permission errors**:
- Ensure paths exist and are accessible
- Check ownership matches shuttle configuration

**Samba security violations**:
- Critical security issue - fix immediately
- Verify Samba users are properly isolated

### Debug Mode

Use `--verbose` flag for detailed output and debugging information.