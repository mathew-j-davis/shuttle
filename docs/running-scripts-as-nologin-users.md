# Running Scripts as Users with /usr/sbin/nologin Shell

This document explains how to execute scripts and commands as service accounts that have `/usr/sbin/nologin` as their shell for security purposes.

## Background

Service accounts in production deployments are often configured with `/usr/sbin/nologin` shell to prevent interactive login while still allowing programmatic execution. This is a security best practice that prevents unauthorized shell access while maintaining functional capability.

## Methods to Execute Commands

### 1. Using `sudo -u` (Recommended)

The `sudo -u` command allows you to run commands as another user without requiring an interactive shell:

```bash
# Basic syntax
sudo -u username command

# Examples
sudo -u shuttle_runner /path/to/script.sh
sudo -u shuttle_runner python3 /opt/shuttle/process_files.py
sudo -u shuttle_runner /bin/bash /path/to/complex_script.sh
```

**Advantages:**
- Works regardless of the target user's shell
- Preserves environment and logging context
- Can execute any command or script
- Respects sudo security policies

### 2. Using `sudo su -` with Shell Override

You can override the nologin shell by explicitly specifying a shell:

```bash
# Switch to user with explicit shell
sudo su - shuttle_runner -s /bin/bash

# Execute single command
sudo su - shuttle_runner -s /bin/bash -c "command here"

# Examples
sudo su - shuttle_runner -s /bin/bash -c "/path/to/script.sh"
sudo su - shuttle_runner -s /bin/bash -c "cd /opt/shuttle && python3 process.py"
```

**Note:** This bypasses the nologin restriction, so use carefully.

### 3. Direct Script Execution Patterns

For scripts that need to run as service accounts:

```bash
# Make script executable by the service user
sudo chown shuttle_runner:shuttle_group /path/to/script.sh
sudo chmod 755 /path/to/script.sh

# Execute via sudo -u
sudo -u shuttle_runner /path/to/script.sh
```

## Script Content Considerations

When the script itself contains calls to other commands or scripts, the nologin shell doesn't affect execution:

```bash
#!/bin/bash
# This script runs fine with sudo -u even if user has nologin shell

# All of these work normally:
echo "Starting processing..."
python3 /opt/shuttle/main.py
/usr/bin/some-command --option value
cd /opt/shuttle && ./another-script.sh

# Environment variables work
export CONFIG_PATH="/etc/shuttle/config.conf"
./process-with-config.py
```

## Cron Jobs with Service Accounts

Service accounts with nologin shells can still run cron jobs:

```bash
# Edit crontab for service user
sudo crontab -u shuttle_runner -e

# Example crontab entry
0 */6 * * * /opt/shuttle/bin/run-shuttle.sh >> /var/log/shuttle/cron.log 2>&1
```

The cron daemon executes commands directly without requiring an interactive shell.

## Environment Considerations

### Environment Variables

When using `sudo -u`, environment variables may not be fully inherited:

```bash
# Preserve environment
sudo -E -u shuttle_runner command

# Set specific variables
sudo -u shuttle_runner env VAR=value command

# Use a wrapper script for complex environments
sudo -u shuttle_runner /opt/shuttle/bin/env-wrapper.sh
```

### Working Directory

Specify working directory explicitly:

```bash
# Change directory first
sudo -u shuttle_runner bash -c "cd /opt/shuttle && ./script.sh"

# Or use absolute paths
sudo -u shuttle_runner /opt/shuttle/script.sh
```

## Security Benefits of nologin

Using `/usr/sbin/nologin` provides these security advantages:

1. **Prevents Interactive Login**: Users cannot ssh or login directly
2. **Reduces Attack Surface**: No shell access if credentials are compromised  
3. **Audit Trail**: All execution must go through sudo, providing clear audit logs
4. **Controlled Access**: Administrators control exactly what the service account can execute

## Verification

To verify a user's shell and test execution:

```bash
# Check user's shell
getent passwd shuttle_runner

# Test command execution  
sudo -u shuttle_runner whoami
sudo -u shuttle_runner pwd
sudo -u shuttle_runner /bin/bash -c "echo 'Test successful'"
```

## Common Issues and Solutions

### Issue: "This account is currently not available"
**Cause:** Attempting to use `su` without shell override  
**Solution:** Use `sudo -u` or specify shell with `su -s`

### Issue: Environment variables not available
**Cause:** sudo doesn't preserve environment by default  
**Solution:** Use `sudo -E` or set variables explicitly

### Issue: Permission denied on script execution
**Cause:** Script not executable or wrong ownership  
**Solution:** Fix permissions and ownership:
```bash
sudo chown shuttle_runner:shuttle_group script.sh
sudo chmod 755 script.sh
```

## Best Practices

1. **Use `sudo -u` for most cases** - it's the most reliable method
2. **Set proper ownership** on scripts and directories
3. **Use absolute paths** in scripts and commands
4. **Test thoroughly** in your environment before production
5. **Monitor logs** to ensure commands execute successfully
6. **Document service account usage** for operational clarity

This approach maintains security while providing necessary operational flexibility for service accounts.