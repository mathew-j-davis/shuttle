# Setting Up a Python Script as a Cron Job

This guide explains how to set up a Python script to run as a cron job on a machine where you have sudo access but cannot configure cron to run under your user. This is particularly useful if the default for cron jobs on the machine is to run as root.

## Steps

### 1. Prepare Your Python Script
- Ensure your Python script is executable by adding a shebang line at the top:
  ```bash
  #!/usr/bin/env python3
  ```
- Make the script executable:
  ```bash
  chmod +x your_script.py
  ```

### 2. Create a Shell Script Wrapper (Optional)
- If your Python script requires a specific environment, create a shell script to activate the environment and run the script:
  ```bash
  #!/bin/bash
  source /path/to/your/venv/bin/activate
  /path/to/your/script.py
  ```
- Make this shell script executable:
  ```bash
  chmod +x your_script.sh
  ```

### 3. Edit the Root Crontab
- Edit the root user's crontab:
  ```bash
  sudo crontab -e
  ```
- Add a line to schedule your script (e.g., to run every day at midnight):
  ```bash
  0 0 * * * /path/to/your/script.py
  ```
- If using a shell script wrapper, replace `/path/to/your/script.py` with `/path/to/your/script.sh`.

### 4. Ensure Permissions and Environment
- Ensure all files and directories your script interacts with are accessible by the root user.
- Set any required environment variables in the script or shell script wrapper.

### 5. Test the Cron Job
- Manually test the cron job by running the script as root to ensure it behaves as expected.

### 6. Check Cron Logs
- If the cron job doesn't run, check the cron logs for errors, typically found in `/var/log/syslog` or `/var/log/cron`.

By following these steps, you can successfully set up your Python script to run as a cron job on a machine where you have sudo access.
