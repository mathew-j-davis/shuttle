
# Shuttle Run/Cron/Service Configuration

This guide covers the progression from manual execution to automated scheduling to systemd service for the Shuttle application.

## Environment Variables for Shuttle

Shuttle requires these environment variables to be set:
- `SHUTTLE_CONFIG_PATH` - Path to configuration file
- `SHUTTLE_VENV_PATH` - Path to Python virtual environment  
- `SHUTTLE_WORK_DIR` - Working directory for shuttle

### Setting Up Environment Variables

During deployment, create an environment file at `/etc/shuttle/shuttle_env.sh`:

```bash
# Create shuttle environment file
sudo mkdir -p /etc/shuttle
sudo nano /etc/shuttle/shuttle_env.sh

# Add environment variables:
#!/bin/bash
export SHUTTLE_CONFIG_PATH="/etc/shuttle/config.conf"
export SHUTTLE_VENV_PATH="/opt/shuttle/.venv"
export SHUTTLE_WORK_DIR="/var/lib/shuttle/work"

# Make executable
sudo chmod +x /etc/shuttle/shuttle_env.sh
```

**Note**: The exact paths will depend on your deployment configuration. Adjust these paths to match your actual installation locations.

## Shuttle Integration

### Phase 1: Manual Execution (Current)

```bash
# Run shuttle manually as the zzzz user
# This allows testing and verification before automation
sudo -u zzzz /usr/local/bin/run-shuttle

# Or if you need to set environment variables:
sudo -u zzzz -i bash -c 'source /etc/shuttle/shuttle_env.sh && /usr/local/bin/run-shuttle'

# Monitor the process
ps aux | grep shuttle
tail -f /var/log/shuttle.log  # or wherever logs are configured
```

### Phase 2: Cron Job Configuration (After Testing)

Configure shuttle to run via cron as the non-root user (zzzz):

#### Environment Variables in Cron Jobs

**Critical**: Cron jobs run in a minimal environment without access to user profile settings. You must explicitly handle environment variables using one of these methods:

##### Method 1: Source Environment in Cron Command (Recommended)

```bash
# Edit crontab for the zzzz user
sudo -u zzzz crontab -e

# Option A: Every 10 minutes, Monday-Friday, 8am-10pm with environment
*/10 8-21 * * 1-5 /bin/bash -c 'source /etc/shuttle/shuttle_env.sh && /usr/local/bin/run-shuttle' >> /var/log/shuttle-cron.log 2>&1

# Option B: Every 10 minutes, 24/7 with environment
*/10 * * * * /bin/bash -c 'source /etc/shuttle/shuttle_env.sh && /usr/local/bin/run-shuttle' >> /var/log/shuttle-cron.log 2>&1
```

##### Method 2: Set Environment Variables in Crontab

```bash
# Edit crontab for the zzzz user
sudo -u zzzz crontab -e

# Add these lines at the top of the crontab:
SHUTTLE_CONFIG_PATH=/etc/shuttle/config.conf
SHUTTLE_VENV_PATH=/opt/shuttle/.venv
SHUTTLE_WORK_DIR=/var/lib/shuttle/work
PATH=/usr/local/bin:/usr/bin:/bin

# Then your cron jobs without explicit sourcing:
*/10 8-21 * * 1-5 /usr/local/bin/run-shuttle >> /var/log/shuttle-cron.log 2>&1
*/10 * * * * /usr/local/bin/run-shuttle >> /var/log/shuttle-cron.log 2>&1
```

##### Method 3: Create Wrapper Script

```bash
# Create wrapper script that handles environment setup
sudo nano /usr/local/bin/run-shuttle-with-env

# Add this content:
#!/bin/bash
# Shuttle wrapper script that loads environment
source /etc/shuttle/shuttle_env.sh
exec /usr/local/bin/run-shuttle "$@"

# Make executable
sudo chmod +x /usr/local/bin/run-shuttle-with-env

# Use in crontab (simpler entries):
*/10 8-21 * * 1-5 /usr/local/bin/run-shuttle-with-env >> /var/log/shuttle-cron.log 2>&1
*/10 * * * * /usr/local/bin/run-shuttle-with-env >> /var/log/shuttle-cron.log 2>&1
```

#### Testing Environment Setup

```bash
# Test that environment variables are properly set in cron context
sudo -u zzzz /bin/bash -c 'source /etc/shuttle/shuttle_env.sh && env | grep SHUTTLE'

# Test the actual command with environment
sudo -u zzzz /bin/bash -c 'source /etc/shuttle/shuttle_env.sh && /usr/local/bin/run-shuttle --help'

# Test the wrapper script if using Method 3
sudo -u zzzz /usr/local/bin/run-shuttle-with-env --help
```

#### Cron Expression Breakdown

```bash
# Cron format: minute hour day-of-month month day-of-week command
# */10        - Every 10 minutes (0,10,20,30,40,50)
# 8-21        - Hours from 8am to 9:50pm (last run at 21:50)
# *           - Every day of month
# *           - Every month
# 1-5         - Monday(1) through Friday(5)
# 
# Note: 8-21 gives you 8:00am to 9:50pm (last run)
# If you need exactly until 10pm, use 8-22 (last run at 10:00pm)
```

#### Advanced Cron Configuration

```bash
# For more complex scheduling needs:

# Option C: With lock file to prevent overlapping runs (environment-aware)
*/10 * * * * /usr/bin/flock -n /var/lock/shuttle.lock /bin/bash -c 'source /etc/shuttle/shuttle_env.sh && /usr/local/bin/run-shuttle' >> /var/log/shuttle-cron.log 2>&1

# Option D: With timeout to kill hung processes (30 minutes)
*/10 * * * * /usr/bin/timeout 30m /bin/bash -c 'source /etc/shuttle/shuttle_env.sh && /usr/local/bin/run-shuttle' >> /var/log/shuttle-cron.log 2>&1

# Option E: Combined lock file, timeout, and environment
*/10 * * * * /usr/bin/flock -n /var/lock/shuttle.lock /usr/bin/timeout 30m /bin/bash -c 'source /etc/shuttle/shuttle_env.sh && /usr/local/bin/run-shuttle' >> /var/log/shuttle-cron.log 2>&1

# Option F: With email notifications on failure
# First set MAILTO in crontab:
MAILTO=admin@example.com
*/10 * * * * /bin/bash -c 'source /etc/shuttle/shuttle_env.sh && /usr/local/bin/run-shuttle' || echo "Shuttle failed at $(date)" >> /var/log/shuttle-cron.log 2>&1

# Option G: Using wrapper script with advanced features
*/10 * * * * /usr/bin/flock -n /var/lock/shuttle.lock /usr/bin/timeout 30m /usr/local/bin/run-shuttle-with-env >> /var/log/shuttle-cron.log 2>&1
```

#### Monitoring Cron Execution

```bash
# View current crontab for zzzz user
sudo -u zzzz crontab -l

# Check cron logs for execution
# Ubuntu/Debian
grep CRON /var/log/syslog | grep zzzz

# RHEL/CentOS
grep CRON /var/log/cron | grep zzzz

# Monitor shuttle-specific cron log
tail -f /var/log/shuttle-cron.log

# Check if cron job is running
ps aux | grep -E "(cron|shuttle)"
```

#### Cron Best Practices

```bash
# 1. Always use full paths in cron
# Good: /usr/local/bin/run-shuttle
# Bad: run-shuttle

# 2. Redirect output to prevent email spam
# >> /var/log/shuttle-cron.log 2>&1

# 3. Set PATH if needed
PATH=/usr/local/bin:/usr/bin:/bin

# 4. Consider using anacron for laptops/systems that aren't always on
# Install: sudo apt install anacron
# Then use @daily, @weekly instead of specific times

# 5. Test your cron expression
# Use: https://crontab.guru/ to verify your schedule
```

### Phase 3: Systemd Service (Future - After Proven Reliability)

Once shuttle has proven reliable as a cron job, convert to a systemd service for better control:

```bash
# Create systemd service file
sudo nano /etc/systemd/system/shuttle.service

# Add this content:
[Unit]
Description=Shuttle File Transfer Service
After=network.target

[Service]
Type=simple
User=zzzz
Group=shuttle-users
UMask=0113
ExecStart=/usr/local/bin/run-shuttle

# Restart configuration
Restart=on-failure
RestartSec=300  # Wait 5 minutes before restart

# Resource limits (optional)
MemoryLimit=2G
CPUQuota=50%

# Environment variables
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="SHUTTLE_CONFIG_PATH=/etc/shuttle/config.conf"
Environment="SHUTTLE_VENV_PATH=/opt/shuttle/.venv"
Environment="SHUTTLE_WORK_DIR=/var/lib/shuttle/work"

# Alternative: Use environment file (create without .sh extension for systemd)
# EnvironmentFile=-/etc/shuttle/shuttle.env

[Install]
WantedBy=multi-user.target

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable shuttle.service
sudo systemctl start shuttle.service

# For timer-based execution (like cron)
# Create a timer unit instead: /etc/systemd/system/shuttle.timer
[Unit]
Description=Run Shuttle every 10 minutes
Requires=shuttle.service

[Timer]
OnCalendar=*:0/10
Persistent=true

[Install]
WantedBy=timers.target

# Enable timer instead of service
sudo systemctl enable shuttle.timer
sudo systemctl start shuttle.timer
```

### Transition Planning

```bash
# Phase transitions checklist:

# Manual → Cron:
# □ Verify manual runs complete successfully
# □ Check log output and error handling  
# □ Confirm file permissions work as expected
# □ Test with small batches first
# □ Monitor for 3-5 days minimum

# Cron → Service:
# □ Cron runs reliably for 2+ weeks
# □ No manual interventions needed
# □ Resource usage is predictable
# □ Error handling is robust
# □ Monitoring/alerting is in place
```