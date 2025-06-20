# Shuttle Installation Flow Diagram

## Current Implementation Status

✅ = Fully implemented with our new pattern  
🔧 = Partially implemented (needs instructions file integration)  
📋 = Planned but not yet implemented  

---

## Overall Flow

```
scripts/1_install.sh [--wizard|--instructions <file>|--help]
├── parse_arguments()
│   ├── --wizard (or no args) → RUN_WIZARD=true
│   ├── --instructions <file> → INSTALL_INSTRUCTIONS_FILE=<file>
│   └── --help → show_usage() → exit
│
├── main()
│   ├── load_installation_constants_for_install() ✅
│   │   ├── source __setup_lib_sh/_setup_lib_loader.source.sh
│   │   ├── load_installation_constants_lib()
│   │   └── Export all constants: VENV_CHOICE_*, INSTALL_MODE_*, LOG_LEVEL_*, etc.
│   │
│   ├── STEP 1: check_venv_status() ✅
│   ├── STEP 2: select_installation_mode() ✅  
│   ├── STEP 3: select_venv_ide_options() ✅
│   ├── STEP 4: collect_config_path() ✅
│   ├── STEP 5: check_prerequisites() ✅
│   ├── STEP 6: check_and_install_system_deps() ✅
│   ├── STEP 7: collect_environment_variables() ✅
│   ├── STEP 8: collect_config_parameters() 🔧
│   ├── STEP 9: execute_installation()
│   └── STEP 10: show_next_steps()
```

---

## Step-by-Step Breakdown

### STEP 1: Virtual Environment Status ✅

```
check_venv_status()
├── detect_venv_state() → Sets CURRENT_VENV_ACTIVE, CURRENT_VENV_PATH
├── IF INSTALL_INSTRUCTIONS_FILE set:
│   └── validate_venv_instructions(saved_choice) 📋
│       ├── Check saved choice vs current state
│       ├── Handle conflicts (error with clear message)
│       └── Set: VENV_TYPE, CREATE_VENV, IN_VENV, USER_VENV_CHOICE
└── ELSE (wizard mode):
    └── interactive_venv_choice()
        ├── IF venv active → use existing
        ├── ELSE → prompt for choice (global/script_creates/exit)
        ├── Handle recursive prompting with while loop
        └── Set: VENV_TYPE, CREATE_VENV, IN_VENV, USER_VENV_CHOICE, EXPECTED_VENV_ACTIVE
```

### STEP 2: Installation Mode Selection ✅

```
select_installation_mode()
├── IF INSTALL_INSTRUCTIONS_FILE set:
│   └── validate_install_mode_instructions(saved_mode) 📋
│       ├── Validate mode is valid
│       ├── Check permissions for service mode
│       └── Set: INSTALL_MODE, ENV_FLAG, USER_INSTALL_MODE_CHOICE
└── ELSE (wizard mode):
    └── interactive_install_mode_choice()
        ├── Prompt: 1=dev, 2=user, 3=service
        ├── Use constants: INSTALL_MODE_DEV, INSTALL_MODE_USER, INSTALL_MODE_SERVICE  
        ├── Call get_env_flag_for_mode() helper
        └── Set: INSTALL_MODE, ENV_FLAG, USER_INSTALL_MODE_CHOICE
```

### STEP 3: IDE Integration Options ✅

```
select_venv_ide_options()
├── detect_ide_state() → Sets DETECTED_IDES array
├── IF INSTALL_INSTRUCTIONS_FILE set:
│   └── validate_ide_instructions(saved_register_kernel) 📋
│       ├── Check prerequisites (dev mode + creating venv)
│       ├── Apply or warn about conflicts
│       └── Set: REGISTER_KERNEL, USER_REGISTER_KERNEL_CHOICE
└── ELSE (wizard mode):
    └── interactive_ide_choice()
        ├── Skip if not (dev mode + creating venv)
        ├── Show detected IDEs
        ├── Prompt for Jupyter kernel registration
        └── Set: REGISTER_KERNEL, USER_REGISTER_KERNEL_CHOICE
```

### STEP 4: Configuration File Path ✅

```
collect_config_path()
├── IF INSTALL_INSTRUCTIONS_FILE set:
│   └── validate_config_path_instructions(saved_path) 📋
│       ├── Validate path not empty
│       ├── Check parent directory existence/permissions
│       └── Set: CONFIG_PATH, USER_CONFIG_PATH_CHOICE
└── ELSE (wizard mode):
    └── interactive_config_path_choice()
        ├── Set default based on INSTALL_MODE (using constants)
        ├── Prompt for config file location
        └── Set: CONFIG_PATH, USER_CONFIG_PATH_CHOICE
```

### STEP 5: Prerequisites (GPG Keys) ✅

```
check_prerequisites()
├── IF INSTALL_INSTRUCTIONS_FILE set:
│   └── validate_gpg_instructions(saved_gpg_path) 📋
│       ├── Validate path not empty
│       ├── Check if key file exists
│       ├── Show generation instructions if missing
│       └── Set: GPG_KEY_PATH, USER_GPG_KEY_PATH_CHOICE
└── ELSE (wizard mode):
    └── interactive_gpg_choice()
        ├── Set default: CONFIG_DIR/shuttle_public.gpg
        ├── Prompt for GPG key location
        ├── Check if key exists, show instructions if not
        ├── Prompt to continue without key
        └── Set: GPG_KEY_PATH, USER_GPG_KEY_PATH_CHOICE
```

### STEP 6: System Dependencies ✅

```
check_and_install_system_deps()
├── detect_system_deps_state() → Always runs
│   ├── Check: lsof, gnupg, python3, pip3, clamscan, mdatp
│   └── Set: MISSING_BASIC_DEPS[], MISSING_PYTHON, MISSING_CLAMAV, MISSING_DEFENDER, NEED_SUDO
├── IF INSTALL_INSTRUCTIONS_FILE set:
│   └── validate_system_deps_instructions(saved_choices) 📋
│       ├── Check conflicts (e.g., Python required but instructions say don't install)
│       ├── Validate sudo access if needed
│       └── Set: INSTALL_BASIC_DEPS, INSTALL_PYTHON, INSTALL_CLAMAV, CHECK_DEFENDER
└── ELSE (wizard mode):
    └── interactive_system_deps_choice()
        ├── Prompt for overall dependency check
        ├── IF skipped → show manual instructions, return
        ├── Check sudo access if needed
        ├── Report each missing component with descriptions
        ├── Prompt for each: basic deps, Python, ClamAV, Defender
        └── Set: INSTALL_BASIC_DEPS, INSTALL_PYTHON, INSTALL_CLAMAV, CHECK_DEFENDER + USER_*_CHOICE
```

### STEP 7: Environment Variables ✅

```
collect_environment_variables()
├── IF INSTALL_INSTRUCTIONS_FILE set:
│   └── validate_environment_paths_instructions(saved_venv_path, saved_test_dir) 📋
│       ├── Validate paths not empty
│       ├── Check parent directories
│       └── Set: VENV_PATH, TEST_WORK_DIR, CONFIG_DIR, USER_*_CHOICE
└── ELSE (wizard mode):
    └── interactive_environment_paths_choice()
        ├── Set defaults based on INSTALL_MODE (using constants)
        ├── Prompt for venv path and test work directory
        ├── Set CONFIG_DIR from CONFIG_PATH
        └── Set: VENV_PATH, TEST_WORK_DIR, CONFIG_DIR, USER_*_CHOICE
```

### STEP 8: Configuration Parameters 🔧

```
collect_config_parameters()
├── IF INSTALL_INSTRUCTIONS_FILE set: 📋
│   └── Skip entirely - config already exists
└── ELSE (wizard mode): 🔧
    └── Current implementation (needs modularization):
        ├── Set defaults based on INSTALL_MODE (using constants)
        ├── Collect all shuttle config parameters:
        │   ├── File paths: source, dest, quarantine, logs, hazard
        │   ├── Scanning: ClamAV, Defender settings
        │   ├── Performance: threads, free space
        │   ├── Logging: log level
        │   ├── Email: SMTP settings (if admin email provided)
        │   └── Processing: delete source files, ledger path
        ├── Set all USER_*_CHOICE variables for 18+ parameters
        └── PLANNED: Call 07_setup_config.py to create files immediately
```

---

## STEP 8 Planned Refactoring 📋

### Wizard Mode (Create Real Files):
```
collect_config_parameters() [wizard mode]
├── interactive_config_choice() → Collect all parameters
├── Call 07_setup_config.py --create-config → Create config.conf
├── Call 07_setup_config.py --create-test-config → Create test_config.conf + test keys
├── Call 07_setup_config.py --create-ledger → Create ledger.yaml
└── wizard_completion_options() → Save/Continue/Exit choices
```

### Instructions Mode (Use Existing Files):
```
collect_config_parameters() [instructions mode]
├── Read config file path from instructions
├── Validate config file exists
├── Skip config generation entirely
└── Set environment variables pointing to existing config
```

---

## Wizard Completion Flow 📋

```
wizard_completion_options() [After step 8]
├── Show configuration summary
├── Prompt user:
│   ├── 1) Continue with installation → execute_installation()
│   ├── 2) Save instructions and continue → save_instructions() → execute_installation()  
│   ├── 3) Save instructions only (exit) → save_instructions() → exit 0
│   └── 4) Exit without saving → exit 0
└── save_instructions() creates YAML with:
    ├── All USER_*_CHOICE variables
    ├── Paths to created config files
    └── Installation preferences
```

---

## STEP 9: Execute Installation

```
execute_installation()
├── Set environment variables for session
├── PHASE 1: System Dependencies (sudo required)
│   ├── IF INSTALL_BASIC_DEPS → ./1_installation_steps/03_sudo_install_dependencies.sh
│   ├── IF INSTALL_PYTHON → ./1_installation_steps/01_sudo_install_python.sh  
│   └── IF INSTALL_CLAMAV → ./1_installation_steps/05_sudo_install_clamav.sh
├── PHASE 2: Environment Setup
│   └── ./1_installation_steps/02_env_and_venv.sh $ENV_FLAG [--do-not-create-venv]
├── PHASE 3: Python Dependencies  
│   └── ./1_installation_steps/06_install_python_dev_dependencies.sh
├── PHASE 4: Configuration (CHANGED) 🔧
│   └── Skip - config already created in step 8
├── PHASE 5: Module Installation
│   ├── ./1_installation_steps/08_install_shared.sh [$MODULE_FLAG]
│   ├── ./1_installation_steps/09_install_defender_test.sh [$MODULE_FLAG]  
│   └── ./1_installation_steps/10_install_shuttle.sh [$MODULE_FLAG]
└── PHASE 6: Final Setup
    ├── Register Jupyter kernel if requested
    └── Copy GPG key if needed
```

---

## Files Created During Installation

### Wizard Mode Creates:
```
├── Installation instructions: install_instructions.yaml
├── Shuttle config: $CONFIG_PATH (e.g., /path/config/config.conf)
├── Test config: $TEST_CONFIG_PATH (e.g., /path/test_area/test_config.conf)
├── Ledger file: $LEDGER_PATH (e.g., /path/config/ledger/ledger.yaml)
├── GPG keys: $GPG_KEY_PATH (e.g., /path/config/shuttle_public.gpg)
├── Test keys: $TEST_WORK_DIR/shuttle_test_key_public.gpg
├── Environment vars: $CONFIG_DIR/shuttle_env.sh
└── Virtual environment: $VENV_PATH
```

### Instructions Mode Uses:
```
├── Installation instructions: <specified file>
├── Existing config: <path from instructions>
├── Existing test config: <path from instructions>  
├── Existing keys: <paths from config files>
└── Creates environment vars and venv as needed
```

---

## Instructions File Format 📋

```yaml
version: '1.0'
metadata:
  description: 'Shuttle Installation Instructions'
  created: '2025-01-18 10:30:00'

# Installation choices (steps 1-7)
installation:
  venv_choice: "script_creates"
  venv_expected_active: false
  install_mode: "dev"
  register_jupyter_kernel: false
  install_basic_deps: true
  install_python: false
  install_clamav: true
  check_defender: true

# File paths (created during wizard)
files:
  config_file: "/path/to/config/config.conf"
  test_config_file: "/path/to/test_area/test_config.conf"
  ledger_file: "/path/to/config/ledger/ledger.yaml"
  gpg_key_file: "/path/to/config/shuttle_public.gpg"

# Environment paths
paths:
  config_path: "/path/to/config/config.conf"
  venv_path: "/path/to/.venv"
  test_work_dir: "/path/to/test_area"
```

---

## Next Implementation Steps 📋

1. **Refactor 07_setup_config.py** → Make modular for individual file creation
2. **Implement instructions file save/load** → YAML generation and parsing
3. **Add wizard completion options** → Save/Continue/Exit choices
4. **Update step 8** → Call modular config creation in wizard mode
5. **Add environment variable generation** → Create shell scripts
6. **Integration testing** → Full wizard → instructions → install workflow