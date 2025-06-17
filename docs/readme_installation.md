# Installation and Setup Guide

This guide provides step-by-step instructions for installing and setting up the Shuttle project in different environments: development, user production, and system production.

## Prerequisites

### 1. GPG Key Generation (Required First)

**IMPORTANT**: Before starting any installation, you must generate GPG keys for encrypting potential malware files.

```bash
# Generate encryption keys (required for all installations)
./scripts/0_key_generation/00_generate_shuttle_keys.sh
```

This creates:
- `shuttle_public.gpg` - Deploy this on the target machine
- `shuttle_private.gpg` - Keep this secure elsewhere (NOT on the target machine)

### 2. System Dependencies

Ensure these are installed on your system:

```bash
# Required system packages
sudo apt-get update
sudo apt-get install lsof gnupg python3 python3-pip python3-venv

# Virus scanning software
sudo apt-get install clamav clamav-daemon
sudo systemctl start clamav-daemon
sudo systemctl enable clamav-daemon
sudo freshclam  # Update virus definitions
```

## Installation Methods

Choose the appropriate installation method for your use case:

### 🔧 Development Installation

For local development with project root as the base directory.

#### Standard Development Setup

1. **Set up environment**:
   ```bash
   ./scripts/1_installation_steps/00_set_env.sh -e
   source shuttle_env.sh
   ```

2. **Create virtual environment**:
   ```bash
   ./scripts/1_installation_steps/04_create_venv.sh
   source .venv/bin/activate
   ```

3. **Install Python dependencies**:
   ```bash
   ./scripts/1_installation_steps/06_install_python_dev_dependencies.sh
   ```

4. **Set up configuration**:
   ```bash
   python ./scripts/1_installation_steps/07_setup_config.py
   ```

5. **Install modules in development mode**:
   ```bash
   ./scripts/1_installation_steps/08_install_shared.sh -e
   ./scripts/1_installation_steps/09_install_defender_test.sh -e
   ./scripts/1_installation_steps/10_install_shuttle.sh -e
   ```

#### VSCode Development Setup

For VSCode users, use the IDE's built-in Python environment management instead of our scripts:

1. **Set up environment**:
   ```bash
   ./scripts/1_installation_steps/00_set_env.sh -e
   source shuttle_env.sh
   ```

2. **Create virtual environment** (using VSCode):
   - Open project in VSCode
   - Press `Ctrl+Shift+P` → "Python: Create Environment"
   - Select "Venv" and choose Python interpreter
   - VSCode will create `.venv/` automatically

3. **Install dependencies** (using VSCode terminal):
   ```bash
   # VSCode automatically activates the environment in its terminals
   pip install -r scripts/1_installation_steps/requirements.txt
   ```

4. **Set up configuration**:
   ```bash
   python ./scripts/1_installation_steps/07_setup_config.py
   ```

5. **Install modules in development mode**:
   ```bash
   ./scripts/1_installation_steps/08_install_shared.sh -e
   ./scripts/1_installation_steps/09_install_defender_test.sh -e
   ./scripts/1_installation_steps/10_install_shuttle.sh -e
   ```

6. **Configure VSCode**:
   - The `.env` file is automatically created for import resolution
   - Launch configurations are available in `.vscode/launch.json`

### 👤 User Production Installation

For single-user installations using user's home directory (`~/.config/shuttle/`, `~/.local/share/shuttle/`).

1. **Set up environment**:
   ```bash
   ./scripts/1_installation_steps/00_set_env.sh -u
   source ~/.config/shuttle/shuttle_env.sh
   ```

2. **Install system dependencies** (if needed):
   ```bash
   ./scripts/1_installation_steps/03_sudo_install_dependencies.sh
   ./scripts/1_installation_steps/01_sudo_install_python.sh
   ./scripts/1_installation_steps/05_sudo_install_clamav.sh
   ```

3. **Create virtual environment**:
   ```bash
   ./scripts/1_installation_steps/04_create_venv.sh
   source ~/.local/share/shuttle/venv/bin/activate
   ```

4. **Install Python dependencies**:
   ```bash
   ./scripts/1_installation_steps/06_install_python_dev_dependencies.sh
   ```

5. **Set up configuration**:
   ```bash
   python ./scripts/1_installation_steps/07_setup_config.py
   ```

6. **Install modules**:
   ```bash
   ./scripts/1_installation_steps/08_install_shared.sh
   ./scripts/1_installation_steps/09_install_defender_test.sh
   ./scripts/1_installation_steps/10_install_shuttle.sh
   ```

### 🏢 System Production Installation

For system-wide installations using service accounts (`/etc/shuttle/`, `/opt/shuttle/`, `/var/lib/shuttle/`).

1. **Set up environment**:
   ```bash
   ./scripts/1_installation_steps/00_set_env.sh
   source /etc/shuttle/shuttle_env.sh
   ```

2. **Install system dependencies**:
   ```bash
   sudo ./scripts/1_installation_steps/03_sudo_install_dependencies.sh
   sudo ./scripts/1_installation_steps/01_sudo_install_python.sh
   sudo ./scripts/1_installation_steps/05_sudo_install_clamav.sh
   ```

3. **Create virtual environment**:
   ```bash
   ./scripts/1_installation_steps/04_create_venv.sh
   source /opt/shuttle/venv/bin/activate
   ```

4. **Install Python dependencies**:
   ```bash
   ./scripts/1_installation_steps/06_install_python_dev_dependencies.sh
   ```

5. **Set up configuration**:
   ```bash
   python ./scripts/1_installation_steps/07_setup_config.py
   ```

6. **Install modules**:
   ```bash
   ./scripts/1_installation_steps/08_install_shared.sh
   ./scripts/1_installation_steps/09_install_defender_test.sh
   ./scripts/1_installation_steps/10_install_shuttle.sh
   ```

7. **Create systemd service** (optional):
   ```bash
   # Create service file
   sudo tee /etc/systemd/system/shuttle.service > /dev/null <<EOF
   [Unit]
   Description=Shuttle File Transfer and Scanning Service
   After=network.target

   [Service]
   Type=simple
   User=shuttle
   Group=shuttle
   WorkingDirectory=/opt/shuttle
   ExecStart=/opt/shuttle/venv/bin/python -m shuttle.shuttle
   Restart=on-failure
   KillSignal=SIGTERM
   TimeoutStopSec=30

   [Install]
   WantedBy=multi-user.target
   EOF

   # Enable and start
   sudo systemctl daemon-reload
   sudo systemctl enable shuttle
   sudo systemctl start shuttle
   ```

## Installation Summary

| Mode | Environment Script | Virtual Environment | Config Location | Modules Flag |
|------|-------------------|-------------------|----------------|--------------|
| **Development** | `00_set_env.sh -e` | Project `.venv/` | Project root | `-e` |
| **VSCode Development** | `00_set_env.sh -e` | VSCode managed | Project root | `-e` |
| **User Production** | `00_set_env.sh -u` | `~/.local/share/shuttle/venv` | `~/.config/shuttle/` | none |
| **System Production** | `00_set_env.sh` | `/opt/shuttle/venv` | `/etc/shuttle/` | none |

## Key Differences

### Development vs Production
- **Development** (`-e` flag): Installs modules in editable mode, creates `.env` file for IDE support
- **Production**: Standard installation, no IDE-specific files

### VSCode vs Standard Development
- **VSCode**: Uses IDE's built-in virtual environment management
- **Standard**: Uses project scripts for virtual environment

### User vs System Production
- **User** (`-u` flag): Uses user's home directory structure
- **System**: Uses system-wide directories, suitable for service accounts

## Post-Installation

### Copy Public Key
After installation, copy your public key to the configured location:

```bash
# Development
cp shuttle_public.gpg /path/to/project/public-key.gpg

# User Production
cp shuttle_public.gpg ~/.config/shuttle/public-key.gpg

# System Production
sudo cp shuttle_public.gpg /etc/shuttle/public-key.gpg
```

### Verify Installation
Run tests to verify everything works:

```bash
# Activate the appropriate virtual environment first
python tests/run_tests.py
```

### Running Shuttle
```bash
# After activating virtual environment
run-shuttle
# or
python -m shuttle.shuttle
```

## Environment Variables

All installation modes set these environment variables:

- `SHUTTLE_CONFIG_PATH` - Path to main configuration file
- `SHUTTLE_VENV_PATH` - Path to Python virtual environment  
- `SHUTTLE_TEST_WORK_DIR` - Path to working directory (quarantine, logs, etc.)

Access them via:
- **Development**: `source shuttle_env.sh`
- **User Production**: `source ~/.config/shuttle/shuttle_env.sh`
- **System Production**: `source /etc/shuttle/shuttle_env.sh`

## Troubleshooting

### Virtual Environment Issues
If virtual environment activation fails:

```bash
# Check if environment exists
ls -la .venv/bin/activate  # or appropriate path

# Set permissions
chmod +x .venv/bin/activate

# Use full path
/path/to/venv/bin/python -m pip list
```

### Permission Issues
For system production installs:

```bash
# Ensure proper ownership
sudo chown -R shuttle:shuttle /opt/shuttle /etc/shuttle /var/lib/shuttle

# Set appropriate permissions
sudo chmod -R 755 /opt/shuttle /etc/shuttle
sudo chmod -R 750 /var/lib/shuttle
```

### Import Resolution (Development)
If IDEs can't find modules:

1. **VSCode**: The `.env` file should handle this automatically
2. **Other IDEs**: Add these paths to PYTHONPATH:
   ```
   ./src/shared_library
   ./src/shuttle_app  
   ./src/shuttle_defender_test_app
   ./tests
   ```