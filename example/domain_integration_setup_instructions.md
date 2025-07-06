# Domain User Import Setup Instructions

## Overview

This shuttle installation includes domain user import functionality. To enable it, you need to configure your workplace-specific domain import command.

## Configuration Options

### Option 1: Domain Config File (Recommended)

Create a separate configuration file for domain-specific settings:

**File:** `/etc/shuttle/domain_config.yaml`
```yaml
# Domain User Import Configuration
command: sudo /path/to/your/domain-import-script
command_args_template: --username {username} --home {home} --shell {shell} --primary-group {primary_group}
default_shell: /bin/bash
default_home_pattern: /home/{username}
```

### Option 2: Shell-style Config File

**File:** `/etc/shuttle/domain_import.conf`
```bash
# Domain User Import Configuration
command=sudo /path/to/your/domain-import-script
args_template=--username {username} --home {home} --shell {shell} --primary-group {primary_group}
default_shell=/bin/bash
default_home_pattern=/home/{username}
```

### Option 3: Main Shuttle Config (Legacy)

Add to your main `shuttle_config.yaml`:
```yaml
user_management:
  domain_user_import:
    enabled: true
    command: sudo /path/to/your/domain-import-script
    command_args_template: --username {username} --home {home} --shell {shell} --primary-group {primary_group}
```

## Usage

Once configured, import domain users with:

```bash
# Simple import (minimal parameters)
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user --username alice.domain

# Import with primary group
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user --username alice.domain --primary-group engineering

# Import with groups
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user --username alice.domain --primary-group engineering --groups "developers,sudo"

# Test with dry-run
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user --username alice.domain --dry-run --verbose

# Force re-import existing user
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user --username alice.domain --force
```

## Template Variables

Your domain import command will receive these variables:

- `{username}` - The domain username to import
- `{uid}` - UID (if specified, empty if domain determines)
- `{home}` - Home directory path
- `{shell}` - Login shell
- `{primary_group}` - Primary group (if specified)
- `{groups}` - Secondary groups (if specified)

## Security Notes

- The import command typically requires `sudo` privileges
- Keep domain-specific commands in separate config files
- Test with `--dry-run` before importing users
- Use `--force` to update existing users

## Troubleshooting

### Check Configuration
```bash
# Test if domain config is detected
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user --username test.user --dry-run --verbose
```

### Common Issues

1. **"Domain user import not configured"**
   - Create one of the domain config files above
   - Or enable in main shuttle config

2. **"Import command not found"**
   - Check that your domain import script path is correct
   - Ensure the script is executable

3. **Permission denied**
   - Make sure `sudo` is included in the command
   - Check that your script has proper permissions

## Example Domain Import Scripts

Your workplace domain import script might look like:
```bash
#!/bin/bash
# Example: /opt/corporate/bin/import-domain-user
username="$1"
# ... your domain-specific logic here ...
useradd --home-dir "/home/$username" --shell "/bin/bash" "$username"
```

The shuttle script will call it as:
```bash
sudo /opt/corporate/bin/import-domain-user --username alice.domain --home /home/alice.domain --shell /bin/bash --primary-group engineering
```