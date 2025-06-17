# Environment Files in Shuttle

## Overview

Shuttle uses several types of environment configuration files. Understanding the differences helps you configure your development environment correctly.

## File Types

### 1. `.venv/` (Directory)
- **What it is**: Python virtual environment
- **Location**: Project root (development) or `~/.local/share/shuttle/venv` (production)
- **Purpose**: Contains Python interpreter, pip, and installed packages
- **Created by**: `python -m venv .venv` or `04_create_venv.sh`
- **Used by**: Python when activated

### 2. `shuttle_env.sh` (Shell Script)
- **What it is**: Bash script that exports environment variables
- **Location**: 
  - Development mode (`-e`): Project root
  - Production mode: `scripts/1_installation_steps/`
- **Purpose**: Sets `SHUTTLE_CONFIG_PATH`, `SHUTTLE_VENV_PATH`, `SHUTTLE_TEST_WORK_DIR`
- **Created by**: `00_set_env.sh`
- **Used by**: Shell sessions after sourcing

### 3. `.env` (Optional)
- **What it is**: Key-value pairs for environment variables
- **Location**: Project root
- **Purpose**: Set environment variables for development tools
- **Format**: `KEY=VALUE` pairs, one per line
- **Used by**: VSCode, python-dotenv, and other development tools

## When to Use Each

### Development Setup

1. **Initial setup**:
   ```bash
   cd ~/shuttle
   ./scripts/1_installation_steps/00_set_env.sh -e
   source shuttle_env.sh
   ```

2. **Activate Python environment**:
   ```bash
   source .venv/bin/activate
   ```

3. **Optional `.env` file** (for VSCode/IDEs):
   ```
   PYTHONPATH=./src/shared_library:./src/shuttle_app:./src/shuttle_defender_test_app:./tests
   SHUTTLE_CONFIG_PATH=/home/user/shuttle/config.conf
   SHUTTLE_VENV_PATH=/home/user/shuttle/.venv
   SHUTTLE_TEST_WORK_DIR=/home/user/shuttle/work
   ```

### Production Setup

1. **Initial setup**:
   ```bash
   ./scripts/1_installation_steps/00_set_env.sh
   source scripts/1_installation_steps/shuttle_env.sh
   ```

2. **Activate Python environment**:
   ```bash
   source ~/.local/share/shuttle/venv/bin/activate
   ```

## VSCode Integration

### Automatic `.env` Loading

VSCode automatically loads `.env` files when:
- Opening a terminal in VSCode
- Running/debugging Python files
- Using the Python extension

To enable this:
1. Install the Python extension
2. Create `.env` in project root
3. VSCode will automatically use it

### Manual Configuration

If `.env` isn't loaded automatically, add to `.vscode/settings.json`:
```json
{
    "python.envFile": "${workspaceFolder}/.env"
}
```

## Priority Order

When multiple environment sources exist:

1. **Command line**: Highest priority
   ```bash
   SHUTTLE_CONFIG_PATH=/custom/path python script.py
   ```

2. **Already exported variables**: From `shuttle_env.sh`
   ```bash
   source shuttle_env.sh
   ```

3. **`.env` file**: Loaded by tools that support it
   
4. **System environment**: Lowest priority

## Common Issues

### Issue: VSCode not finding modules
**Solution**: Either use `.vscode/settings.json` with `python.analysis.extraPaths` OR create `.env` with `PYTHONPATH`

### Issue: Wrong paths in production
**Solution**: Don't use development `.env` file in production. Use `shuttle_env.sh` instead.

### Issue: Environment variables not persisting
**Solution**: Add `source /path/to/shuttle_env.sh` to your `~/.bashrc` or `~/.bash_profile`

## Best Practices

1. **Don't commit `.env`**: Add it to `.gitignore` if it contains sensitive data
2. **Use `shuttle_env.sh` for deployment**: It's more explicit and shell-compatible
3. **Document required variables**: List all required environment variables in your README
4. **Use consistent paths**: Stick to either development or production paths, don't mix

## Example Configurations

### Development `.env`
```
# Python paths
PYTHONPATH=./src/shared_library:./src/shuttle_app:./src/shuttle_defender_test_app:./tests

# Shuttle paths
SHUTTLE_CONFIG_PATH=/home/user/shuttle/config.conf
SHUTTLE_VENV_PATH=/home/user/shuttle/.venv
SHUTTLE_TEST_WORK_DIR=/home/user/shuttle/work

# Logging
SHUTTLE_LOG_LEVEL=DEBUG
```

### Production cron job
```bash
#!/bin/bash
source /home/user/.local/share/shuttle/venv/bin/activate
source /opt/shuttle/scripts/1_installation_steps/shuttle_env.sh
/home/user/.local/share/shuttle/venv/bin/python -m shuttle.shuttle
```