# Installation Scripts Security Refactoring Plan

## Overview
Apply the security validation patterns and cleanup patterns developed for `2_post_install_config.sh` and its associated scripts to `1_install.sh` and the `1_installation_steps/` directory.

## Current State Analysis

### 1_install.sh (Main Installation Script)
- **Size**: 1325 lines
- **Purpose**: Interactive installation wizard for Shuttle
- **Current Issues**:
  - No input validation for user-provided paths
  - No protection against command injection in paths or email settings
  - Direct variable interpolation in commands without validation
  - No use of shared validation libraries

### 1_installation_steps/ Directory Scripts

#### System Installation Scripts (Require sudo)
1. **01_sudo_install_python.sh**
   - Installs Python and development tools
   - Needs: Package manager detection, command validation

2. **03_sudo_install_dependencies.sh**
   - Installs system dependencies (lsof, gnupg)
   - Needs: Package list validation, command injection protection

3. **05_sudo_install_clamav.sh**
   - Installs ClamAV antivirus
   - Needs: Service management validation

#### Environment Setup Scripts
4. **02_env_and_venv.sh**
   - Sets up environment variables and virtual environment
   - Needs: Path validation, secure file creation

5. **04_check_defender_is_installed.sh**
   - Checks Microsoft Defender installation
   - Needs: Command output parsing validation

6. **06_install_python_dev_dependencies.sh**
   - Installs Python packages from requirements.txt
   - Needs: Package name validation

7. **07_setup_config.py**
   - Python script for configuration generation
   - Needs: Review for path validation in Python

#### Module Installation Scripts
8. **08_install_shared.sh**
   - Installs shared library module
   - Needs: Flag validation (-e flag)

9. **09_install_defender_test.sh**
   - Installs defender test module
   - Needs: Flag validation

10. **10_install_shuttle.sh**
    - Installs main shuttle application
    - Needs: Flag validation

## Security Patterns to Apply

### 1. Input Validation Functions
From `_setup_lib_sh/_input_validation.source.sh`:
- `validate_no_control_chars()` - Block command injection
- `validate_alphanumeric_underscore()` - For identifiers
- `validate_path_characters()` - For file paths
- `validate_comment_text()` - For user descriptions

### 2. Specialized Validation Functions
From `_setup_lib_sh/_common_.source.sh`:
- `validate_parameter_user()` - Username validation
- `validate_parameter_group()` - Group name validation
- `validate_parameter_path()` - Path validation with existence checks
- `validate_parameter_email()` - Email address validation
- `validate_parameter_port()` - Network port validation
- `validate_parameter_hostname()` - Hostname/IP validation

### 3. Clean Import Pattern
From `_setup_lib_sh/_setup_lib_loader.source.sh`:
- Centralized library loading
- Consistent error handling
- No relative path confusion

## Implementation Plan

### Phase 1: Infrastructure Setup
1. **Move validation libraries to shared location**
   - Ensure `_setup_lib_sh/` is accessible to installation scripts
   - Already done in previous work

2. **Update library loader**
   - Ensure loader works from both installation and post-install contexts
   - Test path resolution from different script locations

### Phase 2: Main Installation Script (1_install.sh)

#### Areas Requiring Validation:
1. **Installation Mode Selection** (lines 105-129)
   - Validate numeric input (1-3)
   - Add 'x' exit handling consistently

2. **Virtual Environment Choices** (lines 167-221)
   - Validate numeric/character input
   - Consistent exit handling

3. **Path Inputs** (Multiple locations)
   - Config path (line 547): `validate_parameter_path`
   - Source path (line 651): `validate_parameter_path`
   - Destination path (line 658): `validate_parameter_path`
   - Quarantine path (line 665): `validate_parameter_path`
   - Log path (line 672): `validate_parameter_path`
   - Hazard path (line 679): `validate_parameter_path`
   - Venv path (line 582): `validate_parameter_path`
   - Test work dir (line 589): `validate_parameter_path`
   - GPG key path (line 282): `validate_parameter_path`
   - Ledger path (line 854): `validate_parameter_path`

4. **Email Configuration** (lines 774-823)
   - Admin email (line 781): `validate_parameter_email`
   - SMTP server (line 791): `validate_parameter_hostname`
   - SMTP port (line 797): `validate_parameter_port`
   - SMTP username (line 804): `validate_parameter_value` with alphanumeric
   - SMTP password: Special handling (no validation, secure storage)

5. **Numeric Inputs**
   - Scan threads (line 724): Validate positive integer
   - Min free space (line 731): Validate positive integer
   - Log level choice (line 759): Validate 1-5 or level names

6. **Boolean Choices**
   - Various Y/N/X prompts: Standardize validation

### Phase 3: Installation Step Scripts

#### Priority 1: Scripts with User Input
1. **02_env_and_venv.sh**
   - Validate environment flags (-e, -u, -s)
   - Validate paths for directory creation
   - Secure environment file generation

#### Priority 2: System Installation Scripts
2. **01_sudo_install_python.sh**
   - Validate package manager detection
   - No direct user input, but validate system commands

3. **03_sudo_install_dependencies.sh**
   - Similar to Python installation
   - Validate package lists

4. **05_sudo_install_clamav.sh**
   - Validate service management commands
   - Check systemctl/service availability

#### Priority 3: Module Installation Scripts
5. **08_install_shared.sh**, **09_install_defender_test.sh**, **10_install_shuttle.sh**
   - Validate -e flag if provided
   - Validate pip commands

### Phase 4: Additional Improvements

1. **Consistent Exit Codes**
   - 0: Success
   - 1: General error
   - 2: User cancelled (like wizard pattern)

2. **Dry Run Support**
   - Add --dry-run flag to 1_install.sh
   - Pass through to all sub-scripts

3. **Logging Enhancement**
   - Use COMMAND_HISTORY_FILE pattern
   - Log all validated inputs

4. **Error Handling**
   - Consistent error messages
   - Clear remediation steps

## Security Validation Patterns to Add

### For 1_install.sh:
```bash
# Source validation libraries
source_setup_lib "common"

# Validate path input
read -p "Source directory [$DEFAULT_SOURCE]: " SOURCE_PATH
SOURCE_PATH=${SOURCE_PATH:-$DEFAULT_SOURCE}
SOURCE_PATH=$(validate_parameter_path "$SOURCE_PATH" "create") || exit 1

# Validate email
read -p "Admin email: " ADMIN_EMAIL
if [[ -n "$ADMIN_EMAIL" ]]; then
    ADMIN_EMAIL=$(validate_parameter_email "$ADMIN_EMAIL") || exit 1
fi

# Validate port
read -p "SMTP port [587]: " SMTP_PORT
SMTP_PORT=${SMTP_PORT:-587}
SMTP_PORT=$(validate_parameter_port "$SMTP_PORT") || exit 1

# Validate hostname
read -p "SMTP server: " SMTP_SERVER
SMTP_SERVER=$(validate_parameter_hostname "$SMTP_SERVER") || exit 1
```

### For installation step scripts:
```bash
# At script start
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SETUP_LIB_DIR="$(dirname "$SCRIPT_DIR")/_setup_lib_sh"
source "$SETUP_LIB_DIR/_setup_lib_loader.source.sh"
load_common_libs || exit 1

# Validate any user input or parameters
```

## Testing Plan

1. **Unit Tests**
   - Test each validation function with valid/invalid inputs
   - Test path traversal attempts
   - Test command injection attempts

2. **Integration Tests**
   - Run full installation with various inputs
   - Test cancellation at each prompt
   - Test invalid input handling

3. **Security Tests**
   - Attempt path traversal: `../../../etc/passwd`
   - Attempt command injection: `; rm -rf /`
   - Attempt variable expansion: `$HOME/../../../`

## Success Criteria

1. All user inputs are validated before use
2. No unvalidated variables in command execution
3. Consistent error handling and user feedback
4. Clean, maintainable code using shared libraries
5. No regression in functionality
6. Improved security posture

## Next Steps

1. Review and approve this plan
2. Implement Phase 1 (Infrastructure)
3. Implement Phase 2 (Main script) incrementally
4. Implement Phase 3 (Sub-scripts) by priority
5. Comprehensive testing
6. Documentation updates