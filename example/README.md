# Shuttle Example Configuration

This directory contains example configuration files and directory structure for the Shuttle file transfer and scanning utility.

## Directory Structure

- `shuttle_config/` - Contains configuration files that would typically be located in `~/.shuttle/` or other standard locations
  - `config.conf` - Main configuration file with all settings
  - `public-key.gpg` - Example encryption key for hazardous files (not a real key)
  - `ledger.yaml` - Sample ledger file showing antivirus version tracking

- `shuttle_work/` - Example working directory structure for Shuttle
  - `in/` - Source directory for files to be processed
  - `out/` - Destination directory for clean files
  - `quarantine/` - Directory for files that need further inspection
  - `hazard/` - Archive for encrypted hazardous files

## Usage

These examples demonstrate how to configure Shuttle. In a real deployment:

1. The configuration files would be placed in standard locations:
   - `~/.config/shuttle/config.conf` (XDG compliant)
   - `~/.shuttle/config.conf` 
   - `/etc/shuttle/config.conf` (system-wide)

2. Shuttle automatically searches these locations in order, or you can specify a custom location with:
   ```
   ./shuttle -SettingsPath /path/to/your/config.conf
   ```

3. You can also set an environment variable:
   ```
   export SHUTTLE_CONFIG_PATH=/path/to/your/config.conf
   ./shuttle
   ```

## Directory Paths

The example configuration uses the following directory structure:
- Source files: `~/shuttle_work/in`
- Destination: `~/shuttle_work/out`
- Quarantine: `~/shuttle_work/quarantine`
- Hazard archive: `~/shuttle_work/hazard`
- Logs: `~/shuttle_work/logs`

## Configuration Options

The example `config.conf` includes configurations for:
- File paths
- Logging settings
- Throttling options
- Scanning preferences
- Notification settings

Adjust these settings according to your specific requirements.
