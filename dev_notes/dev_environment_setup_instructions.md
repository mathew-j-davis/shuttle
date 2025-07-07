# Shuttle Dev Environment Setup Instructions

## Overview
Setting up a development environment with domain user authentication for Samba shares.

## Phase 1: Initial Development Environment Setup

### Step 1: Run the Configuration Wizard
```bash
cd /home/mathew/shuttle
python3 scripts/_setup_lib_py/post_install_config_wizard.py --shuttle-config-path /home/mathew/shuttle/config/config.conf
```

### Step 2: Wizard Choices for Dev Environment
1. **Deployment Mode**: Choose `1) Development`
2. **Admin Username**: Enter your domain username (e.g., `yourusername.domain` or `DOMAIN\yourusername`)
3. **Domain Configuration**: Say "yes" if prompted about domain user configuration
4. **Save Configuration**: Accept the default location or specify where to save

## Phase 2: Custom Configuration for Samba

### Step 1: Run Wizard Again in Custom Mode
```bash
python3 scripts/_setup_lib_py/post_install_config_wizard.py --shuttle-config-path /home/mathew/shuttle/config/config.conf
```

### Step 2: Wizard Choices for Samba Setup
1. **Deployment Mode**: Choose `3) Custom`
2. **Navigate to**: Samba Configuration section
3. **Enable Samba**: Yes
4. **WORKGROUP**: Just press Enter to accept default "WORKGROUP" (this is fine for domain users)
5. **Add Share**: 
   - Share name: `shuttle_source` (or your preference)
   - Path: `/var/shuttle/source` (or your incoming directory)
   - Valid users: Your domain users (e.g., `DOMAIN\user1`, `DOMAIN\user2`)
   - Read only: No (if users need to write files)

### Step 3: Add Second Domain User
When in custom mode:
1. Go to User Management
2. Add domain user
3. Enter the second domain username that needs access
4. Add them to the appropriate Samba access group

## Important Notes

### About WORKGROUP
- **What to choose**: Just use default "WORKGROUP"
- **Why it's OK**: WORKGROUP is just a network label, not a security setting
- **Domain users**: Will still authenticate with their domain credentials regardless

### Domain User Formats
Your organization might use one of these formats:
- `username.domain` (with dots)
- `DOMAIN\username` (with backslash)
- `username@domain.com` (email style)

### Authentication
- Domain users will use their **domain passwords** when connecting to Samba
- The server being in "WORKGROUP" doesn't affect domain authentication
- Samba will pass authentication requests to your domain controller

## Quick Command Reference

### After Setup - Apply Configuration
```bash
# The wizard will show you the exact command, but it will be something like:
./scripts/2_post_install_config.sh --instructions /path/to/generated/config.yaml --dry-run
# Remove --dry-run when ready to actually apply
```

### Test Samba Access
```bash
# List Samba shares
./scripts/2_post_install_config_steps/13_configure_samba.sh list-shares

# Check Samba users
./scripts/2_post_install_config_steps/13_configure_samba.sh list-samba-users

# Test configuration
./scripts/2_post_install_config_steps/13_configure_samba.sh test-config
```

## Troubleshooting

### If Domain User Import Fails
1. Check if domain import is configured:
   ```bash
   ./scripts/2_post_install_config_steps/12_users_and_groups.sh generate-domain-config --output-dir /tmp --dry-run
   ```

2. You may need to configure the domain import command for your organization

### If Samba Authentication Fails
1. Ensure domain user exists in the system:
   ```bash
   id DOMAIN\\username
   ```

2. Check Samba user is added:
   ```bash
   sudo pdbedit -L | grep username
   ```

3. Verify share permissions:
   ```bash
   ./scripts/2_post_install_config_steps/13_configure_samba.sh show-share shuttle_source
   ```