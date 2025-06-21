# Installation Scripts Refactoring Plan - FINAL

## Key Requirement: Default to Wizard Mode

**Both scripts should launch the wizard when called without parameters, and only use config files when `--config` is explicitly provided.**

### Current Issue

Both scripts currently try to use a default config file when no `--config` is provided:

```bash
# 2_post_install_config.sh line 168
CONFIG_FILE=${CONFIG_FILE:-$DEFAULT_CONFIG}

# 1_install.sh - always interactive, no config file support
```

### Target Behavior

```bash
# Default behavior - launch wizard
./scripts/1_install.sh                    # → Run installation wizard  
./scripts/2_post_install_config.sh       # → Run configuration wizard

# Explicit config file usage
./scripts/1_install.sh --config install_config.yaml
./scripts/2_post_install_config.sh --config post_config.yaml

# Combined options
./scripts/1_install.sh --wizard --dry-run  # → wizard + dry run
./scripts/2_post_install_config.sh --wizard --dry-run
```

## Updated Implementation Plan

### Phase 1: Fix Current Scripts (Quick Win)

#### A. Fix `2_post_install_config.sh` argument parsing
**Current problematic code:**
```bash
parse_arguments() {
    # ... parse --config, --wizard, etc ...
    
    # Set default config if not specified  ← PROBLEM
    CONFIG_FILE=${CONFIG_FILE:-$DEFAULT_CONFIG}
}
```

**Fixed logic:**
```bash
parse_arguments() {
    local CONFIG_SPECIFIED=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config)
                CONFIG_FILE="$2"
                CONFIG_SPECIFIED=true
                shift 2
                ;;
            --wizard)
                RUN_WIZARD=true
                shift
                ;;
            # ... other options ...
        esac
    done
    
    # If no --config specified and no --wizard, default to wizard
    if [[ "$CONFIG_SPECIFIED" == "false" && "$RUN_WIZARD" == "false" ]]; then
        RUN_WIZARD=true
    fi
}
```

#### B. Update `1_install.sh` to support config files
**Add to argument parsing:**
```bash
parse_arguments() {
    local CONFIG_SPECIFIED=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config)
                INSTALL_CONFIG_FILE="$2"
                CONFIG_SPECIFIED=true
                shift 2
                ;;
            --wizard)
                RUN_WIZARD=true
                shift
                ;;
            # ... existing options ...
        esac
    done
    
    # If no --config specified and no --wizard, default to wizard (current behavior)
    if [[ "$CONFIG_SPECIFIED" == "false" && "$RUN_WIZARD" == "false" ]]; then
        RUN_WIZARD=true  # This maintains current behavior
    fi
}
```

### Phase 2: Create Installation Config Infrastructure

#### A. Installation Config Constants
**File: `scripts/_setup_lib_py/installation_config_constants.py`**
```python
# Installation configuration file naming
INSTALL_CONFIG_PREFIX = "shuttle_installation_config"
INSTALL_CONFIG_EXTENSION = "yaml"

def get_install_config_filename(environment=None):
    if environment:
        return f"{INSTALL_CONFIG_PREFIX}_{environment}.{INSTALL_CONFIG_EXTENSION}"
    return f"{INSTALL_CONFIG_PREFIX}.{INSTALL_CONFIG_EXTENSION}"
```

#### B. Installation Wizard
**File: `scripts/_setup_lib_py/installation_wizard.py`**
- Interactive collection of installation settings
- Generates installation config YAML
- Generates shuttle application config
- Same exit code pattern as post-install wizard

#### C. Installation Executor  
**File: `scripts/_setup_lib_py/installation_executor.py`**
- Reads installation config YAML
- Executes installation phases
- Calls existing installation step scripts

### Phase 3: Example Installation Config Format

```yaml
version: '1.0'
metadata:
  description: 'Shuttle Installation Configuration'
  environment: 'development'
  created: '2025-01-18 10:30:00'

# Installation behavior
installation:
  mode: 'development'  # development|user|service
  create_venv: true
  install_modules_editable: true  # -e flag
  register_jupyter_kernel: false

# System dependencies
system_dependencies:
  install_basic_deps: true
  install_python: true
  install_clamav: false
  check_defender: true

# Environment setup
environment:
  config_path: '/path/to/config.conf'
  venv_path: '/path/to/.venv'
  test_work_dir: '/path/to/test_area'

# Shuttle configuration (passed to setup_config.py)
shuttle_config:
  source_path: '/path/to/incoming'
  destination_path: '/path/to/processed'
  # ... all the settings from current interactive collection
```

## Security Validation Integration

### Apply to Both Scripts
- **Path validation**: All user-provided paths
- **Email validation**: SMTP settings  
- **Network validation**: Hostnames and ports
- **Input sanitization**: Prevent command injection
- **Shared libraries**: Use `_setup_lib_sh` validation functions

### Validation Points for `1_install.sh`:
1. **Config path** (line 547): `validate_parameter_path()`
2. **All directory paths**: source, dest, quarantine, logs, hazard, venv, test
3. **Email settings**: admin email, SMTP server, port
4. **Numeric inputs**: threads, disk space, log level choices
5. **GPG key path** (line 282): `validate_parameter_path()`

## Usage Examples (Final Behavior)

### Default Wizard Mode
```bash
# Installation wizard (NEW default behavior)
./scripts/1_install.sh

# Post-install configuration wizard (UPDATED default behavior)  
./scripts/2_post_install_config.sh
```

### Explicit Config File Mode
```bash
# Use saved installation config
./scripts/1_install.sh --config installation_config_dev.yaml

# Use saved post-install config
./scripts/2_post_install_config.sh --config post_install_config_dev.yaml
```

### Explicit Wizard Mode
```bash
# Force wizard mode (same as default, but explicit)
./scripts/1_install.sh --wizard
./scripts/2_post_install_config.sh --wizard
```

### Combined Options
```bash
# Wizard + dry run
./scripts/1_install.sh --wizard --dry-run
./scripts/2_post_install_config.sh --wizard --dry-run

# Config file + interactive confirmation
./scripts/2_post_install_config.sh --config config.yaml --interactive
```

## Implementation Priority

### Phase 1: Quick Fix (Immediate)
1. **Update `2_post_install_config.sh` argument parsing** - Default to wizard mode
2. **Add basic config file support to `1_install.sh`** - Accept `--config` parameter
3. **Test both scripts default to wizard mode**

### Phase 2: Installation Config (Next)  
1. **Create installation config infrastructure**
2. **Create installation wizard and executor**
3. **Update `1_install.sh` to use config files**

### Phase 3: Security & Polish
1. **Add security validation throughout**
2. **Comprehensive testing**
3. **Documentation updates**

## Success Criteria

1. ✅ **Default wizard behavior**: Both scripts launch wizard when called without parameters
2. ✅ **Config file support**: Both scripts accept `--config` parameter
3. ✅ **Backward compatibility**: Current usage patterns continue to work
4. ✅ **Reproducible installations**: Save and replay installation configurations
5. ✅ **Security validated**: All user inputs properly validated
6. ✅ **Team friendly**: Multiple developers can share configurations

This plan prioritizes the key requirement (default to wizard mode) while building toward the full vision of config-file driven installations.