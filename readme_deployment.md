# Deployment and Script Management on Ubuntu Server

This guide provides instructions for deploying and managing your project scripts on an Ubuntu server, which you will interact with via SSH and Visual Studio Code Remote. It covers the setup of virtual environments, directory structures, and cron job configurations.

## Visual Studio Code Remote and Virtual Environment

When using Visual Studio Code Remote, a virtual environment (venv) is created in the root of the folder you open as your workspace. This venv is essential for managing dependencies specific to your project.

## Virtual Environment Troubleshooting

If you encounter issues with the virtual environment (venv) on Ubuntu, consider the following troubleshooting steps:

### Activation Issues
- Ensure the virtual environment is activated using:
  ```bash
  source /path/to/venv/bin/activate
  ```
- Verify activation by checking the paths of `pip` and `python`:
  ```bash
  which pip
  which python
  ```
  Both should point to the virtual environment's binaries.

### Using Full Paths
- If activation does not work as expected, use the full path to `pip` and `python`:
  ```bash
  /path/to/venv/bin/pip install -r requirements.txt
  ```

### Environment Variables
- Check for any environment variables or server configurations that might interfere with the activation process.

### Activation Script
- Ensure the `activate` script in the virtual environment is not altered and functions correctly to set the `PATH` environment variable.

These steps should help resolve common issues related to virtual environment activation and usage on Ubuntu.

## Directory Structure for Deployment

### 1. Deployment Scripts
- **Location:** `/opt/your_project_name/1_deployment`
- **Purpose:** This directory will contain scripts that need to be deployed and persist on the server.
- **Setup:**
  - Copy your deployment scripts from `c:\Users\mathew\OneDrive\Documents\development\forge\1_deployment` to `/opt/your_project_name/1_deployment` on the server.
  - Ensure the venv is activated in this directory when running scripts.

### 2. Temporary Setup Scripts
- **Location:** `/tmp/your_project_name/2_set_up_scripts`
- **Purpose:** This directory is for scripts that only need to be run once on the server and do not need to persist.
- **Setup:**
  - Copy your setup scripts from `c:\Users\mathew\OneDrive\Documents\development\forge\2_set_up_scripts_to_run_on_host` to `/tmp/your_project_name/2_set_up_scripts` on the server.
  - Run these scripts as needed and delete them afterward.

## Running Scripts as Cron Jobs

- **Cron Job Setup:**
  - Use the root crontab to schedule scripts that need to run periodically.
  - Ensure the scripts in `/opt/your_project_name/1_deployment` are executable and configured to run within the venv.
  - Example cron job entry:
    ```bash
    0 0 * * * /opt/your_project_name/1_deployment/your_script.py
    ```

## Best Practices

- **Permissions:** Set appropriate permissions for directories and scripts to prevent unauthorized access.
- **Environment Management:** Always activate the venv before running scripts to ensure dependencies are correctly handled.
- **Documentation:** Keep documentation updated for each script's purpose and usage.

By following these guidelines, you can efficiently manage your deployment and script execution on the Ubuntu server.
