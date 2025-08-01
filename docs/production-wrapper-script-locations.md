# Production Wrapper Script Locations

## Standard Locations for Shuttle Wrapper Script

### 1. **`/usr/local/bin/` (Recommended)**
This is the standard location for locally-installed executables that aren't part of the OS distribution.

```bash
/usr/local/bin/run-shuttle
```

**Advantages:**
- Already in system PATH
- Standard location for custom executables
- Accessible to all users
- Survives system updates
- Clear separation from OS-provided binaries

**Setup:**
```bash
sudo cp shuttle-wrapper.sh /usr/local/bin/run-shuttle
sudo chmod 755 /usr/local/bin/run-shuttle
sudo chown root:root /usr/local/bin/run-shuttle
```

### 2. **`/opt/shuttle/bin/`**
If shuttle is installed in `/opt/shuttle/`, creating a `bin` subdirectory follows the FHS (Filesystem Hierarchy Standard).

```bash
/opt/shuttle/bin/run-shuttle
```

**Advantages:**
- Keeps all shuttle components together
- Clear application boundary
- Easy to manage permissions
- Good for self-contained applications

**Setup:**
```bash
sudo mkdir -p /opt/shuttle/bin
sudo cp shuttle-wrapper.sh /opt/shuttle/bin/run-shuttle
sudo chmod 755 /opt/shuttle/bin/run-shuttle
sudo chown root:shuttle_group /opt/shuttle/bin/run-shuttle
```

### 3. **`/usr/local/sbin/`**
Use this if the script should only be run by administrators.

```bash
/usr/local/sbin/run-shuttle-admin
```

**Advantages:**
- Indicates administrative tool
- Not in regular user PATH
- Clear security boundary

## Example Wrapper Script

```bash
#!/bin/bash
# /usr/local/bin/run-shuttle
# Shuttle wrapper script for production environment

set -euo pipefail

# Source environment variables
if [[ -f /etc/shuttle/shuttle_env.sh ]]; then
    source /etc/shuttle/shuttle_env.sh
else
    echo "Error: Environment file /etc/shuttle/shuttle_env.sh not found" >&2
    exit 1
fi

# Activate virtual environment
if [[ -f /opt/shuttle/venv/bin/activate ]]; then
    source /opt/shuttle/venv/bin/activate
else
    echo "Error: Virtual environment not found at /opt/shuttle/venv" >&2
    exit 1
fi

# Set any additional environment variables
export SHUTTLE_CONFIG_PATH="${SHUTTLE_CONFIG_PATH:-/etc/shuttle/config.conf}"
export SHUTTLE_LOG_PATH="${SHUTTLE_LOG_PATH:-/var/log/shuttle}"

# Run shuttle with all arguments passed to this script
exec python3 -m shuttle.shuttle "$@"
```

## Configuration File Locations

### Environment Variables File
```bash
/etc/shuttle/shuttle_env.sh
```

**Example content:**
```bash
# /etc/shuttle/shuttle_env.sh
export SHUTTLE_CONFIG_PATH="/etc/shuttle/config.conf"
export SHUTTLE_LOG_PATH="/var/log/shuttle"
export SHUTTLE_WORK_DIR="/var/lib/shuttle"
export PYTHONPATH="/opt/shuttle/lib:${PYTHONPATH:-}"
```

### Alternative Systemd Approach

If using systemd, you might not need a wrapper script:

```ini
# /etc/systemd/system/shuttle.service
[Unit]
Description=Shuttle File Transfer Service
After=network.target

[Service]
Type=oneshot
User=shuttle_runner
Group=shuttle_group
Environment="PATH=/opt/shuttle/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/etc/shuttle/shuttle_env.sh
ExecStart=/opt/shuttle/venv/bin/python -m shuttle.shuttle
WorkingDirectory=/var/lib/shuttle

[Install]
WantedBy=multi-user.target
```

## Cron Integration

For cron jobs, reference the wrapper script:

```bash
# /etc/cron.d/shuttle
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin

0 */6 * * * shuttle_runner /usr/local/bin/run-shuttle >> /var/log/shuttle/cron.log 2>&1
```

## Best Practices

1. **Make it executable**: `chmod 755 /usr/local/bin/run-shuttle`
2. **Set secure ownership**: `chown root:root` (or `root:shuttle_group`)
3. **Use absolute paths**: Always use full paths in production scripts
4. **Error handling**: Check for required files before proceeding
5. **Logging**: Ensure output is captured when run from cron
6. **Documentation**: Add comments explaining the script's purpose

## Directory Structure Summary

```
/usr/local/bin/
└── run-shuttle                 # Main wrapper script

/etc/shuttle/
├── config.conf                 # Application configuration
├── shuttle_env.sh             # Environment variables
└── shuttle_public.gpg         # Encryption key

/opt/shuttle/
├── venv/                      # Python virtual environment
├── lib/                       # Python packages (if needed)
└── bin/                       # Alternative script location

/var/log/shuttle/              # Log files
/var/lib/shuttle/              # Working directory
```

## Testing the Wrapper

```bash
# Test as root
sudo /usr/local/bin/run-shuttle --help

# Test as service user
sudo -u shuttle_runner /usr/local/bin/run-shuttle --help

# Test with systemd
sudo systemctl start shuttle.service
sudo systemctl status shuttle.service
```

This approach provides a clean, maintainable way to run shuttle in production with proper environment setup.