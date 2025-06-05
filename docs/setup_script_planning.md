# Interactive Setup Script Planning

## Goal
Create an interactive setup script for development that:
1. Collects parameters or provides sensible defaults
2. Handles different IDE contexts appropriately
3. Sets all environment variables within the script context
4. Leaves clear instructions for post-setup steps

## IDE Virtual Environment Handling

### IDEs that Manage .venv Automatically

1. **VSCode**
   - Detects `.venv` in project root automatically
   - Activates it for terminals and debugging
   - Uses Python extension for management
   - Creates `.venv` via Command Palette

2. **PyCharm**
   - Professional virtual environment management
   - Creates and manages venvs through UI
   - Automatically activates for console/debugging
   - Stores venvs in `~/.virtualenvs/` or project root

3. **Visual Studio (Full)**
   - Python Tools for Visual Studio (PTVS)
   - Manages environments through Solution Explorer
   - Auto-activation for debugging

4. **Jupyter/JupyterLab**
   - Can use ipykernel to register venvs
   - Automatic kernel selection
   - Often manages own environments

5. **Spyder**
   - Anaconda-based, prefers conda environments
   - Can work with venv but less integrated

6. **Sublime Text**
   - With Anaconda plugin
   - Less automatic, requires configuration

### Contexts That DON'T Handle .venv

1. **Terminal/Command Line**
   - Requires manual `source .venv/bin/activate`
   
2. **Vim/Neovim**
   - Requires manual activation or plugin config
   
3. **Emacs**
   - Requires packages like `pyvenv` or `virtualenvwrapper`
   
4. **Atom**
   - Limited support without packages

## Interactive Setup Script Design

### 1. Installation Mode Selection
```bash
# Select installation mode first - this determines environment setup
select_installation_mode() {
    echo "=== Shuttle Installation Mode ==="
    echo ""
    echo "Select installation mode:"
    echo "1) Development (-e flag)"
    echo "   - Local development and testing"
    echo "   - Uses project root paths"
    echo "   - Editable Python package installation"
    echo ""
    echo "2) User Production (-u flag)"
    echo "   - Single user installation"
    echo "   - Uses ~/.config/shuttle/ and ~/.local/share/shuttle/"
    echo "   - Standard Python package installation"
    echo ""
    echo "3) Service Account (system production)"
    echo "   - Multi-user/service deployment"
    echo "   - Uses /etc/shuttle/, /opt/shuttle/, /var/lib/shuttle/"
    echo "   - Requires elevated permissions for some steps"
    echo ""
    
    read -p "Installation mode [1]: " INSTALL_MODE_CHOICE
    INSTALL_MODE_CHOICE=${INSTALL_MODE_CHOICE:-1}
    
    case $INSTALL_MODE_CHOICE in
        1) 
            INSTALL_MODE="dev"
            ENV_FLAG="-e"
            echo "Selected: Development mode"
            ;;
        2) 
            INSTALL_MODE="user"
            ENV_FLAG="-u"
            echo "Selected: User production mode"
            ;;
        3) 
            INSTALL_MODE="service"
            ENV_FLAG=""
            echo "Selected: Service account mode"
            ;;
        *) 
            INSTALL_MODE="dev"
            ENV_FLAG="-e"
            echo "Defaulting to: Development mode"
            ;;
    esac
    echo ""
}
```
~~~
Mat: 

Make this first choice "Create a virtual environment (This script will create .venv, for terminal/other IDEs)"

currently

"3. Script managed (this script creates .venv, for terminal/other IDEs)"

~~~
### 2. Virtual Environment Type Selection
```bash
# Select virtual environment management approach
select_venv_type() {
    if [[ "$INSTALL_MODE" == "dev" ]]; then
        # Detect IDEs for development mode
        DETECTED_IDES=()
        if [[ -n "$VSCODE_PID" ]] || [[ -d ".vscode" ]]; then
            DETECTED_IDES+=("vscode")
        fi
        if [[ -n "$PYCHARM_HOSTED" ]] || [[ -d ".idea" ]]; then
            DETECTED_IDES+=("pycharm")
        fi
        if [[ -n "$JPY_PARENT_PID" ]]; then
            DETECTED_IDES+=("jupyter")
        fi
        
        echo "=== Virtual Environment Management ==="
        if [[ ${#DETECTED_IDES[@]} -gt 0 ]]; then
            echo "Detected environments: ${DETECTED_IDES[*]}"
        fi
        echo ""
        
        echo "How would you like to manage the Python virtual environment?"
        echo "1) Create a virtual environment (This script will create .venv, for terminal/other IDEs)"
        echo "2) VSCode managed (let VSCode create and manage .venv)"
        echo "3) PyCharm managed (let PyCharm create and manage venv)"
        echo "4) Jupyter kernel (script creates .venv and registers kernel)"
        echo "5) Skip venv creation (I'll handle it myself)"
        echo ""
        
        # Suggest default based on detection
        if [[ " ${DETECTED_IDES[*]} " =~ " vscode " ]]; then
            echo "💡 Recommended: Option 2 (VSCode managed)"
            DEFAULT_VENV=2
        elif [[ " ${DETECTED_IDES[*]} " =~ " pycharm " ]]; then
            echo "💡 Recommended: Option 3 (PyCharm managed)"
            DEFAULT_VENV=3
        elif [[ " ${DETECTED_IDES[*]} " =~ " jupyter " ]]; then
            echo "💡 Recommended: Option 4 (Jupyter kernel)"
            DEFAULT_VENV=4
        else
            echo "💡 Recommended: Option 1 (Create a virtual environment)"
            DEFAULT_VENV=1
        fi
        
        read -p "Your choice [$DEFAULT_VENV]: " VENV_CHOICE
        VENV_CHOICE=${VENV_CHOICE:-$DEFAULT_VENV}
        
    else
        # For production modes, always use script-managed
        echo "=== Virtual Environment Management ==="
        echo "Production mode: Using script-managed virtual environment"
        VENV_CHOICE=1
    fi
    
    case $VENV_CHOICE in
        1) 
            VENV_TYPE="script"
            CREATE_VENV=true
            echo "Selected: Script will create and manage .venv"
            ;;
        2) 
            VENV_TYPE="vscode"
            CREATE_VENV=false
            echo "Selected: VSCode will manage virtual environment"
            ;;
        3) 
            VENV_TYPE="pycharm"
            CREATE_VENV=false
            echo "Selected: PyCharm will manage virtual environment"
            ;;
        4) 
            VENV_TYPE="jupyter"
            CREATE_VENV=true
            REGISTER_KERNEL=true
            echo "Selected: Script will create .venv and register Jupyter kernel"
            ;;
        5) 
            VENV_TYPE="skip"
            CREATE_VENV=false
            echo "Selected: Skipping virtual environment creation"
            ;;
        *) 
            VENV_TYPE="script"
            CREATE_VENV=true
            echo "Defaulting to: Create a virtual environment"
            ;;
    esac
    echo ""
}
```
~~~
Mat:

break this down to a lower level

        echo "  01_sudo_install_dependencies.sh"


# Install system packages
echo "Updating package lists..."
sudo apt-get update -y

# Install lsof for checking if files are open
echo "Installing lsof..."
sudo apt-get install -y lsof

# Install GPG if not present
echo "Installing/updating GPG..."
sudo apt-get install -y gnupg





~~~
### 3. System Dependencies Check and Installation
```bash
check_and_install_system_deps() {
    echo "=== System Dependencies Check ==="
    
    MISSING_BASIC_DEPS=()
    MISSING_PYTHON=false
    MISSING_CLAMAV=false
    MISSING_DEFENDER=false
    
    # Check for basic system tools
    command -v lsof >/dev/null 2>&1 || MISSING_BASIC_DEPS+=("lsof")
    command -v gpg >/dev/null 2>&1 || MISSING_BASIC_DEPS+=("gnupg")
    command -v git >/dev/null 2>&1 || MISSING_BASIC_DEPS+=("git")
    command -v curl >/dev/null 2>&1 || MISSING_BASIC_DEPS+=("curl")
    command -v wget >/dev/null 2>&1 || MISSING_BASIC_DEPS+=("wget")
    
    # Check for Python
    if ! command -v python3 >/dev/null 2>&1 || ! command -v pip3 >/dev/null 2>&1; then
        MISSING_PYTHON=true
    fi
    
    # Check for virus scanners
    if ! command -v clamscan >/dev/null 2>&1; then
        MISSING_CLAMAV=true
    fi
    
    # Check for Microsoft Defender (mdatp)
    if ! command -v mdatp >/dev/null 2>&1; then
        MISSING_DEFENDER=true
    fi
    
    # Report basic dependencies
    if [[ ${#MISSING_BASIC_DEPS[@]} -gt 0 ]]; then
        echo ""
        echo "📦 Shuttle requires the following system tools:"
        echo ""
        for dep in "${MISSING_BASIC_DEPS[@]}"; do
            case $dep in
                "lsof") echo "   • lsof - used to check if applications have files open" ;;
                "gnupg") echo "   • gnupg - used to encrypt suspected malware files" ;;
                "git") echo "   • git - version control system for development" ;;
                "curl") echo "   • curl - used for downloading files and updates" ;;
                "wget") echo "   • wget - alternative file download utility" ;;
            esac
        done
        echo ""
        echo "Do you want to install these system tools?"
        echo ""
        echo "Options:"
        echo "  Yes - Install missing system tools (runs 01_00_sudo_install_dependencies.sh)"
        echo "  No  - Skip installation (may cause issues later)"
        echo "  Exit - Quit setup"
        echo ""
        
        while true; do
            read -p "Install system tools? [Yes/No/Exit]: " choice
            case $choice in
                [Yy]* | [Yy][Ee][Ss]* | "" ) 
                    INSTALL_BASIC_DEPS=true
                    break ;;
                [Nn]* | [Nn][Oo]* ) 
                    INSTALL_BASIC_DEPS=false
                    echo "⚠️  Skipping system tools - installation may fail later"
                    break ;;
                [Ee]* | [Ee][Xx][Ii][Tt]* ) 
                    echo "Installation cancelled by user."
                    exit 0 ;;
                * ) 
                    echo "Please answer Yes, No, or Exit." ;;
            esac
        done
    else
        echo "✅ All required system tools found"
        INSTALL_BASIC_DEPS=false
    fi
    
    # Report Python status
    if [[ "$MISSING_PYTHON" == "true" ]]; then
        echo ""
        echo "🐍 Python 3 and development tools are required:"
        echo ""
        echo "   • python3 - Python interpreter"
        echo "   • python3-pip - Python package manager"
        echo "   • python3-venv - Virtual environment support"
        echo "   • python3-dev - Development headers"
        echo ""
        echo "Do you want to install Python 3 and development tools?"
        echo ""
        echo "Options:"
        echo "  Yes - Install Python (runs 02_sudo_install_python.sh)"
        echo "  No  - Skip installation (cannot continue without Python)"
        echo "  Exit - Quit setup"
        echo ""
        
        while true; do
            read -p "Install Python? [Yes/No/Exit]: " choice
            case $choice in
                [Yy]* | [Yy][Ee][Ss]* | "" ) 
                    INSTALL_PYTHON=true
                    break ;;
                [Nn]* | [Nn][Oo]* ) 
                    echo "❌ Cannot continue without Python"
                    echo "Please install Python manually and run this script again"
                    exit 1 ;;
                [Ee]* | [Ee][Xx][Ii][Tt]* ) 
                    echo "Installation cancelled by user."
                    exit 0 ;;
                * ) 
                    echo "Please answer Yes, No, or Exit." ;;
            esac
        done
    else
        echo "✅ Python 3 found"
        INSTALL_PYTHON=false
    fi
    
    # Report ClamAV status
    if [[ "$MISSING_CLAMAV" == "true" ]]; then
        echo ""
        echo "🛡️  ClamAV antivirus scanner (recommended for malware detection):"
        echo ""
        echo "   • clamscan - Command-line virus scanner"
        echo "   • freshclam - Virus definition updater"
        echo "   • clamav-daemon - Background scanning service"
        echo ""
        echo "Do you want to install ClamAV?"
        echo ""
        echo "Options:"
        echo "  Yes - Install ClamAV (runs 03_sudo_install_clamav.sh)"
        echo "  No  - Skip ClamAV (virus scanning will be limited)"
        echo "  Exit - Quit setup"
        echo ""
        
        while true; do
            read -p "Install ClamAV? [Yes/No/Exit]: " choice
            case $choice in
                [Yy]* | [Yy][Ee][Ss]* | "" ) 
                    INSTALL_CLAMAV=true
                    break ;;
                [Nn]* | [Nn][Oo]* ) 
                    INSTALL_CLAMAV=false
                    echo "⚠️  Skipping ClamAV - virus scanning will be limited to Microsoft Defender"
                    break ;;
                [Ee]* | [Ee][Xx][Ii][Tt]* ) 
                    echo "Installation cancelled by user."
                    exit 0 ;;
                * ) 
                    echo "Please answer Yes, No, or Exit." ;;
            esac
        done
    else
        echo "✅ ClamAV found"
        INSTALL_CLAMAV=false
    fi
    
    # Report Microsoft Defender status
    if [[ "$MISSING_DEFENDER" == "true" ]]; then
        echo ""
        echo "🔒 Microsoft Defender for Endpoint (optional):"
        echo ""
        echo "   • Microsoft's enterprise antivirus solution"
        echo "   • Requires separate installation and licensing"
        echo "   • Can be installed later if needed"
        echo ""
        echo "Do you want to check if Microsoft Defender is properly configured?"
        echo ""
        echo "Options:"
        echo "  Yes - Check Defender status (runs 01_01_check_defender_is_installed.sh)"
        echo "  No  - Skip Defender check"
        echo "  Exit - Quit setup"
        echo ""
        
        while true; do
            read -p "Check Microsoft Defender? [Yes/No/Exit]: " choice
            case $choice in
                [Yy]* | [Yy][Ee][Ss]* | "" ) 
                    CHECK_DEFENDER=true
                    break ;;
                [Nn]* | [Nn][Oo]* ) 
                    CHECK_DEFENDER=false
                    echo "⚠️  Skipping Defender check"
                    break ;;
                [Ee]* | [Ee][Xx][Ii][Tt]* ) 
                    echo "Installation cancelled by user."
                    exit 0 ;;
                * ) 
                    echo "Please answer Yes, No, or Exit." ;;
            esac
        done
    else
        echo "✅ Microsoft Defender found"
        CHECK_DEFENDER=false
    fi
    
    echo ""
}
```

### 4. Environment Variables Collection
```bash
collect_environment_variables() {
    echo "=== Environment Variables Setup ==="
    echo "Installation mode: $INSTALL_MODE"
    echo ""
    
    # Set up default paths based on installation mode
    case $INSTALL_MODE in
        "dev")
            PROJECT_ROOT=$(pwd)
            DEFAULT_CONFIG="$PROJECT_ROOT/config.conf"
            DEFAULT_VENV="$PROJECT_ROOT/.venv"
            DEFAULT_WORK="$PROJECT_ROOT/work"
            ;;
        "user")
            DEFAULT_CONFIG="$HOME/.config/shuttle/config.conf"
            DEFAULT_VENV="$HOME/.local/share/shuttle/venv"
            DEFAULT_WORK="$HOME/.local/share/shuttle/work"
            ;;
        "service")
            DEFAULT_CONFIG="/etc/shuttle/config.conf"
            DEFAULT_VENV="/opt/shuttle/venv"
            DEFAULT_WORK="/var/lib/shuttle"
            ;;
    esac
    
    echo "Environment paths (press Enter for defaults):"
    echo ""
    
    read -p "Config file path [$DEFAULT_CONFIG]: " CONFIG_PATH
    CONFIG_PATH=${CONFIG_PATH:-$DEFAULT_CONFIG}
    
    read -p "Virtual environment path [$DEFAULT_VENV]: " VENV_PATH
    VENV_PATH=${VENV_PATH:-$DEFAULT_VENV}
    
    read -p "Working directory [$DEFAULT_WORK]: " WORK_DIR
    WORK_DIR=${WORK_DIR:-$DEFAULT_WORK}
    
    # Derived paths
    CONFIG_DIR=$(dirname "$CONFIG_PATH")
    
    echo ""
    echo "Environment variables set:"
    echo "  SHUTTLE_CONFIG_PATH=$CONFIG_PATH"
    echo "  SHUTTLE_VENV_PATH=$VENV_PATH"
    echo "  SHUTTLE_WORK_DIR=$WORK_DIR"
    echo ""
}
```

### 5. Configuration Parameters Collection
```bash
collect_config_parameters() {
    echo "=== Configuration Parameters ==="
    echo ""
    
    # Set defaults based on installation mode
    case $INSTALL_MODE in
        "dev")
            DEFAULT_SOURCE="$WORK_DIR/test_data/source"
            DEFAULT_DEST="$WORK_DIR/test_data/destination"
            DEFAULT_QUARANTINE="$WORK_DIR/test_data/quarantine"
            DEFAULT_LOG="$WORK_DIR/logs"
            DEFAULT_HAZARD="$WORK_DIR/hazard"
            DEFAULT_THREADS=2
            DEFAULT_LOG_LEVEL="DEBUG"
            DEFAULT_CLAMAV="y"
            DEFAULT_DEFENDER="Y"
            ;;
        "user")
            DEFAULT_SOURCE="$HOME/shuttle/incoming"
            DEFAULT_DEST="$HOME/shuttle/processed"
            DEFAULT_QUARANTINE="/tmp/shuttle/quarantine"
            DEFAULT_LOG="$WORK_DIR/logs"
            DEFAULT_HAZARD="$WORK_DIR/hazard"
            DEFAULT_THREADS=4
            DEFAULT_LOG_LEVEL="INFO"
            DEFAULT_CLAMAV="y"
            DEFAULT_DEFENDER="Y"
            ;;
        "service")
            DEFAULT_SOURCE="/srv/data/incoming"
            DEFAULT_DEST="/srv/data/processed"
            DEFAULT_QUARANTINE="/tmp/shuttle/quarantine"
            DEFAULT_LOG="/var/log/shuttle"
            DEFAULT_HAZARD="$WORK_DIR/hazard"
            DEFAULT_THREADS=8
            DEFAULT_LOG_LEVEL="INFO"
            DEFAULT_CLAMAV="y"
            DEFAULT_DEFENDER="Y"
            ;;
    esac
    
    # File paths
    echo "File Processing Paths:"
    read -p "Source directory [$DEFAULT_SOURCE]: " SOURCE_PATH
    SOURCE_PATH=${SOURCE_PATH:-$DEFAULT_SOURCE}
    
    read -p "Destination directory [$DEFAULT_DEST]: " DEST_PATH
    DEST_PATH=${DEST_PATH:-$DEFAULT_DEST}
    
    read -p "Quarantine directory [$DEFAULT_QUARANTINE]: " QUARANTINE_PATH
    QUARANTINE_PATH=${QUARANTINE_PATH:-$DEFAULT_QUARANTINE}
    
    read -p "Log directory [$DEFAULT_LOG]: " LOG_PATH
    LOG_PATH=${LOG_PATH:-$DEFAULT_LOG}
    
    read -p "Hazard archive directory [$DEFAULT_HAZARD]: " HAZARD_PATH
    HAZARD_PATH=${HAZARD_PATH:-$DEFAULT_HAZARD}
    
    # Scanning configuration
    echo ""
    echo "Virus Scanning Configuration:"
    read -p "Enable ClamAV scanning? [$DEFAULT_CLAMAV/N]: " USE_CLAMAV
    USE_CLAMAV=${USE_CLAMAV:-$DEFAULT_CLAMAV}
    
    read -p "Enable Microsoft Defender? [$DEFAULT_DEFENDER/n]: " USE_DEFENDER
    USE_DEFENDER=${USE_DEFENDER:-$DEFAULT_DEFENDER}
    
    # Performance settings
    echo ""
    echo "Performance Settings:"
    read -p "Number of scan threads [$DEFAULT_THREADS]: " SCAN_THREADS
    SCAN_THREADS=${SCAN_THREADS:-$DEFAULT_THREADS}
    
    read -p "Minimum free space (MB) [1000]: " MIN_FREE_SPACE
    MIN_FREE_SPACE=${MIN_FREE_SPACE:-1000}
    
    # Logging
    echo ""
    echo "Logging Configuration:"
    echo "1) DEBUG"
    echo "2) INFO"
    echo "3) WARNING"
    echo "4) ERROR"
    read -p "Log level [$DEFAULT_LOG_LEVEL]: " LOG_LEVEL_INPUT
    LOG_LEVEL=${LOG_LEVEL_INPUT:-$DEFAULT_LOG_LEVEL}
    
    # Email notifications
    echo ""
    echo "Email Notifications (optional - leave blank to skip):"
    read -p "Admin email address: " ADMIN_EMAIL
    if [[ -n "$ADMIN_EMAIL" ]]; then
        read -p "SMTP server: " SMTP_SERVER
        read -p "SMTP port [587]: " SMTP_PORT
        SMTP_PORT=${SMTP_PORT:-587}
        read -p "SMTP username: " SMTP_USERNAME
        read -p "SMTP password: " SMTP_PASSWORD
        read -p "Use TLS? [Y/n]: " USE_TLS
        USE_TLS=${USE_TLS:-Y}
    fi
    
    # File processing options
    echo ""
    echo "File Processing Options:"
    read -p "Delete source files after copying? [Y/n]: " DELETE_SOURCE
    DELETE_SOURCE=${DELETE_SOURCE:-Y}
    
    echo ""
    echo "Configuration summary:"
    echo "  Source: $SOURCE_PATH"
    echo "  Destination: $DEST_PATH"
    echo "  Quarantine: $QUARANTINE_PATH"
    echo "  Logs: $LOG_PATH"
    echo "  Scan threads: $SCAN_THREADS"
    echo "  Log level: $LOG_LEVEL"
    if [[ -n "$ADMIN_EMAIL" ]]; then
        echo "  Notifications: Enabled ($ADMIN_EMAIL)"
    else
        echo "  Notifications: Disabled"
    fi
    echo ""
}
```

### 6. Prerequisites Check
```bash
check_prerequisites() {
    echo "=== Prerequisites Check ==="
    
    # GPG Keys check
    if [[ ! -f "shuttle_public.gpg" ]]; then
        echo "⚠️  GPG encryption keys not found"
        echo ""
        echo "Shuttle requires GPG keys for encrypting malware files."
        echo "This should be done BEFORE installation."
        echo ""
        read -p "Generate GPG keys now? [Y/n]: " GENERATE_KEYS
        if [[ "$GENERATE_KEYS" != "n" ]]; then
            echo "Generating GPG keys..."
            ./scripts/0_key_generation/00_generate_shuttle_keys.sh
            if [[ $? -eq 0 ]]; then
                echo "✅ GPG keys generated successfully"
            else
                echo "❌ GPG key generation failed"
                exit 1
            fi
        else
            echo "⚠️  Continuing without GPG keys - you must generate them later"
            echo "Run: ./scripts/0_key_generation/00_generate_shuttle_keys.sh"
        fi
    else
        echo "✅ GPG keys found"
    fi
    echo ""
}

### 7. Installation Execution Phase

```bash
# Helper function for script confirmation
confirm_script_execution() {
    local script_name="$1"
    local description="$2"
    
    echo ""
    echo "📋 About to run: $script_name"
    echo "   Description: $description"
    echo ""
    echo "Options:"
    echo "  y/Y - Yes, run this script"
    echo "  n/N - No, skip this script"
    echo "  q/Q - Quit installation"
    echo ""
    
    while true; do
        read -p "Run $script_name? [Y/n/q]: " choice
        case $choice in
            [Yy]* | "" ) return 0 ;;  # Yes (default)
            [Nn]* ) return 1 ;;       # No
            [Qq]* ) echo "Installation cancelled by user."; exit 0 ;;  # Quit
            * ) echo "Please answer y, n, or q." ;;
        esac
    done
}

execute_installation() {
    echo "=== Installation Execution ==="
    echo ""
    
    # Set environment variables for script duration
    export SHUTTLE_CONFIG_PATH="$CONFIG_PATH"
    export SHUTTLE_VENV_PATH="$VENV_PATH"
    export SHUTTLE_WORK_DIR="$WORK_DIR"
    
    echo "Setting up environment variables..."
    
    # Phase 1: System Dependencies (requires sudo)
    echo ""
    echo "📦 Phase 1: Installing system dependencies (requires sudo)"
    
    # Install basic system tools if needed
    if [[ "$INSTALL_BASIC_DEPS" == "true" ]]; then
        echo "Installing basic system tools..."
        ./scripts/1_deployment/01_00_sudo_install_dependencies.sh
        if [[ $? -ne 0 ]]; then
            echo "❌ Failed to install system dependencies"
            exit 1
        fi
        echo "✅ Basic system tools installed"
    fi
    
    # Install Python if needed
    if [[ "$INSTALL_PYTHON" == "true" ]]; then
        echo "Installing Python 3 and development tools..."
        ./scripts/1_deployment/02_sudo_install_python.sh
        if [[ $? -ne 0 ]]; then
            echo "❌ Failed to install Python"
            exit 1
        fi
        echo "✅ Python installed"
    fi
    
    # Install ClamAV if requested
    if [[ "$INSTALL_CLAMAV" == "true" ]]; then
        echo "Installing ClamAV antivirus scanner..."
        ./scripts/1_deployment/03_sudo_install_clamav.sh
        if [[ $? -ne 0 ]]; then
            echo "❌ Failed to install ClamAV"
            exit 1
        fi
        echo "✅ ClamAV installed"
    fi
    
    # Check Microsoft Defender if requested
    if [[ "$CHECK_DEFENDER" == "true" ]]; then
        echo "Checking Microsoft Defender configuration..."
        ./scripts/1_deployment/01_01_check_defender_is_installed.sh
        if [[ $? -ne 0 ]]; then
            echo "⚠️  Microsoft Defender check completed with warnings"
        else
            echo "✅ Microsoft Defender check completed"
        fi
    fi
    
    echo "✅ System dependencies phase complete"
    
    # Phase 2: Environment Setup
    echo ""
    echo "🔧 Phase 2: Setting up environment"
    
    if confirm_script_execution "00_set_env.sh $ENV_FLAG" "Configure environment variables and paths"; then
        ./scripts/1_deployment/00_set_env.sh $ENV_FLAG
        if [[ $? -ne 0 ]]; then
            echo "❌ Failed to set up environment"
            exit 1
        fi
        
        # Re-export the environment variables in this script's context
        export SHUTTLE_CONFIG_PATH="$CONFIG_PATH"
        export SHUTTLE_VENV_PATH="$VENV_PATH"
        export SHUTTLE_WORK_DIR="$WORK_DIR"
        
        echo "✅ Environment setup complete"
    else
        echo "❌ Environment setup is required - cannot continue"
        exit 1
    fi
    
    # Phase 3: Virtual Environment (conditional)
    echo ""
    echo "🐍 Phase 3: Python virtual environment"
    
    if [[ "$CREATE_VENV" == "true" ]]; then
        if confirm_script_execution "04_create_venv.sh" "Create Python virtual environment at $VENV_PATH"; then
            ./scripts/1_deployment/04_create_venv.sh
            if [[ $? -ne 0 ]]; then
                echo "❌ Failed to create virtual environment"
                exit 1
            fi
            echo "✅ Virtual environment created"
            
            # Note: We can't activate it in this script for the user's shell
            # but we can activate it for our own use
            if [[ -f "$VENV_PATH/bin/activate" ]]; then
                source "$VENV_PATH/bin/activate"
                echo "✅ Virtual environment activated for installation"
            fi
        else
            echo "⚠️  Skipped virtual environment creation - you'll need to create it manually"
            CREATE_VENV=false  # Update flag to skip later steps
        fi
    else
        echo "⏭️  Skipping virtual environment creation (will be handled by IDE)"
    fi
    
    # Phase 4: Python Dependencies
    echo ""
    echo "📚 Phase 4: Installing Python dependencies"
    
    # Check if we need to pause for manual venv activation
    if [[ "$VENV_TYPE" == "vscode" || "$VENV_TYPE" == "pycharm" ]]; then
        echo ""
        echo "⚠️  MANUAL STEP REQUIRED:"
        echo ""
        case $VENV_TYPE in
            "vscode")
                echo "Please set up the virtual environment in VSCode:"
                echo "1. Open Command Palette (Ctrl+Shift+P)"
                echo "2. Run 'Python: Create Environment'"
                echo "3. Select 'Venv'"
                echo "4. Wait for VSCode to create the environment"
                ;;
            "pycharm")
                echo "Please set up the virtual environment in PyCharm:"
                echo "1. Go to Settings → Project → Python Interpreter"
                echo "2. Click gear icon → Add"
                echo "3. Select 'New Environment'"
                echo "4. Wait for PyCharm to create the environment"
                ;;
        esac
        echo ""
        read -p "Press Enter when you have completed the virtual environment setup..."
        echo ""
        
        # For IDE-managed venvs, we can't activate them here
        echo "⚠️  Cannot auto-install Python dependencies with IDE-managed virtual environments"
        echo "You will need to install them manually after setup is complete"
        SKIP_PYTHON_DEPS=true
    else
        # Install Python dependencies in our activated environment
        if confirm_script_execution "06_install_python_dev_dependencies.sh" "Install Python development dependencies (requirements.txt)"; then
            ./scripts/1_deployment/06_install_python_dev_dependencies.sh
            if [[ $? -ne 0 ]]; then
                echo "❌ Failed to install Python dependencies"
                exit 1
            fi
            echo "✅ Python dependencies installed"
            SKIP_PYTHON_DEPS=false
        else
            echo "⚠️  Skipped Python dependencies - you'll need to install them manually"
            SKIP_PYTHON_DEPS=true
        fi
    fi
    
    # Phase 5: Configuration
    echo ""
    echo "⚙️  Phase 5: Generating configuration"
    
    # Build config arguments
    CONFIG_ARGS=(
        "--source-path" "$SOURCE_PATH"
        "--destination-path" "$DEST_PATH"
        "--quarantine-path" "$QUARANTINE_PATH"
        "--log-path" "$LOG_PATH"
        "--hazard-archive-path" "$HAZARD_PATH"
        "--log-level" "$LOG_LEVEL"
        "--max-scan-threads" "$SCAN_THREADS"
        "--throttle-free-space-mb" "$MIN_FREE_SPACE"
    )
    
    # Add scanning options
    if [[ "$USE_CLAMAV" == "y" ]]; then
        CONFIG_ARGS+=("--on-demand-clam-av")
    fi
    
    if [[ "$USE_DEFENDER" != "n" ]]; then
        CONFIG_ARGS+=("--on-demand-defender")
    else
        CONFIG_ARGS+=("--no-on-demand-defender")
    fi
    
    # Add file processing options
    if [[ "$DELETE_SOURCE" == "Y" ]]; then
        CONFIG_ARGS+=("--delete-source-files-after-copying")
    else
        CONFIG_ARGS+=("--no-delete-source-files-after-copying")
    fi
    
    # Add notification options
    if [[ -n "$ADMIN_EMAIL" ]]; then
        CONFIG_ARGS+=(
            "--notify"
            "--notify-recipient-email" "$ADMIN_EMAIL"
            "--notify-smtp-server" "$SMTP_SERVER"
            "--notify-smtp-port" "$SMTP_PORT"
            "--notify-username" "$SMTP_USERNAME"
            "--notify-password" "$SMTP_PASSWORD"
        )
        if [[ "$USE_TLS" == "Y" ]]; then
            CONFIG_ARGS+=("--notify-use-tls")
        fi
    fi
    
    # Run configuration script
    if confirm_script_execution "07_setup_config.py" "Generate Shuttle configuration file at $CONFIG_PATH"; then
        echo "Generating configuration file..."
        python3 ./scripts/1_deployment/07_setup_config.py "${CONFIG_ARGS[@]}"
        if [[ $? -ne 0 ]]; then
            echo "❌ Failed to generate configuration"
            exit 1
        fi
        echo "✅ Configuration generated"
    else
        echo "⚠️  Skipped configuration generation - you'll need to create config.conf manually"
    fi
    
    # Phase 6: Module Installation
    echo ""
    echo "📦 Phase 6: Installing Shuttle modules"
    
    if [[ "$SKIP_PYTHON_DEPS" == "true" ]]; then
        echo "⚠️  Skipping module installation (will be done manually later)"
        SKIP_MODULES=true
    else
        # Determine if we need -e flag
        MODULE_FLAG=""
        if [[ "$INSTALL_MODE" == "dev" ]]; then
            MODULE_FLAG="-e"
            echo "Installing modules in development mode (editable)..."
        else
            echo "Installing modules in production mode..."
        fi
        
        if confirm_script_execution "08_install_shared.sh $MODULE_FLAG" "Install shared library (shuttle_common)"; then
            ./scripts/1_deployment/08_install_shared.sh $MODULE_FLAG
            if [[ $? -ne 0 ]]; then
                echo "❌ Failed to install shared library"
                exit 1
            fi
        else
            echo "⚠️  Skipped shared library installation"
        fi
        
        if confirm_script_execution "09_install_defender_test.sh $MODULE_FLAG" "Install defender test module"; then
            ./scripts/1_deployment/09_install_defender_test.sh $MODULE_FLAG
            if [[ $? -ne 0 ]]; then
                echo "❌ Failed to install defender test module"
                exit 1
            fi
        else
            echo "⚠️  Skipped defender test module installation"
        fi
        
        if confirm_script_execution "10_install_shuttle.sh $MODULE_FLAG" "Install main shuttle application"; then
            ./scripts/1_deployment/10_install_shuttle.sh $MODULE_FLAG
            if [[ $? -ne 0 ]]; then
                echo "❌ Failed to install shuttle application"
                exit 1
            fi
        else
            echo "⚠️  Skipped shuttle application installation"
        fi
        
        echo "✅ Module installation phase complete"
        SKIP_MODULES=false
    fi
    
    # Phase 7: Final Setup
    echo ""
    echo "🎯 Phase 7: Final setup"
    
    # Create any additional files for IDEs
    if [[ "$VENV_TYPE" == "vscode" || "$VENV_TYPE" == "pycharm" ]]; then
        echo "Creating .env file for IDE..."
        cat > .env << EOF
# Python paths for IDE import resolution
PYTHONPATH=./src/shared_library:./src/shuttle_app:./src/shuttle_defender_test_app:./tests

# Shuttle environment variables
SHUTTLE_CONFIG_PATH=$CONFIG_PATH
SHUTTLE_VENV_PATH=$VENV_PATH
SHUTTLE_WORK_DIR=$WORK_DIR

# Development logging
SHUTTLE_LOG_LEVEL=$LOG_LEVEL
EOF
        echo "✅ .env file created"
    fi
    
    # Handle Jupyter kernel registration
    if [[ "$VENV_TYPE" == "jupyter" && "$SKIP_MODULES" == "false" ]]; then
        echo "Installing Jupyter kernel support..."
        pip install ipykernel
        python -m ipykernel install --user --name shuttle --display-name "Shuttle Dev"
        echo "✅ Jupyter kernel registered"
    fi
    
    echo ""
    echo "🎉 Installation completed successfully!"
}
```

### 4. IDE-Specific Setup

```bash
setup_for_ide() {
    case $SELECTED_IDE in
        "vscode")
            echo "📝 VSCode - Special handling:"
            echo "  - Will NOT create .venv (let VSCode handle it)"
            echo "  - Will create .env file for environment variables"
            echo "  - Will ensure .vscode/settings.json exists"
            CREATE_VENV=false
            CREATE_DOT_ENV=true
            ;;
            
        "pycharm")
            echo "🧠 PyCharm - Special handling:"
            echo "  - Will NOT create .venv (let PyCharm handle it)"
            echo "  - Will create .env file for run configurations"
            CREATE_VENV=false
            CREATE_DOT_ENV=true
            ;;
            
        "jupyter")
            echo "📓 Jupyter - Special handling:"
            echo "  - Will create .venv"
            echo "  - Will provide kernel registration instructions"
            CREATE_VENV=true
            REGISTER_KERNEL=true
            ;;
            
        "terminal"|"other")
            echo "🖥️  Terminal/Other - Standard setup:"
            echo "  - Will create .venv"
            echo "  - Manual activation required"
            CREATE_VENV=true
            ;;
    esac
}
```

### 5. System Dependencies Check

```bash
check_system_deps() {
    echo "Checking system dependencies..."
    
    MISSING_DEPS=()
    
    # Check for required commands
    command -v python3 >/dev/null 2>&1 || MISSING_DEPS+=("python3")
    command -v pip3 >/dev/null 2>&1 || MISSING_DEPS+=("python3-pip")
    command -v gpg >/dev/null 2>&1 || MISSING_DEPS+=("gnupg")
    command -v lsof >/dev/null 2>&1 || MISSING_DEPS+=("lsof")
    
    if [[ ${#MISSING_DEPS[@]} -gt 0 ]]; then
        echo "❌ Missing system dependencies: ${MISSING_DEPS[*]}"
        echo ""
        echo "Install with:"
        echo "  sudo apt-get update"
        echo "  sudo apt-get install ${MISSING_DEPS[*]}"
        echo ""
        read -p "Run installation now? (requires sudo) [Y/n]: " INSTALL_NOW
        if [[ "$INSTALL_NOW" != "n" ]]; then
            sudo apt-get update
            sudo apt-get install -y ${MISSING_DEPS[*]}
        else
            echo "Please install dependencies and run this script again."
            exit 1
        fi
    fi
}
```

### 6. Configuration Generation

```bash
generate_config() {
    # Build config arguments
    CONFIG_ARGS=(
        "--source-path" "$SOURCE_PATH"
        "--destination-path" "$DEST_PATH"
        "--quarantine-path" "$QUARANTINE_PATH"
        "--log-path" "$LOG_PATH"
        "--log-level" "$LOG_LEVEL"
        "--max-scan-threads" "$SCAN_THREADS"
    )
    
    # Add conditional arguments
    if [[ "$USE_CLAMAV" == "y" ]]; then
        CONFIG_ARGS+=("--on-demand-clam-av")
    fi
    
    if [[ "$USE_DEFENDER" != "n" ]]; then
        CONFIG_ARGS+=("--on-demand-defender")
    else
        CONFIG_ARGS+=("--no-on-demand-defender")
    fi
    
    if [[ -n "$ADMIN_EMAIL" ]]; then
        CONFIG_ARGS+=(
            "--notify"
            "--notify-recipient-email" "$ADMIN_EMAIL"
            "--notify-smtp-server" "$SMTP_SERVER"
            "--notify-smtp-port" "$SMTP_PORT"
        )
    fi
    
    # Run configuration script
    python3 ./scripts/1_deployment/07_setup_config.py "${CONFIG_ARGS[@]}"
}
```

### 8. Post-Setup Instructions

```bash
show_next_steps() {
    echo ""
    echo "✅ Setup Complete!"
    echo ""
    echo "=== Next Steps ==="
    echo ""
    
    # Environment file location depends on mode
    case $INSTALL_MODE in
        "dev")
            ENV_FILE_PATH="$PROJECT_ROOT/shuttle_env.sh"
            ;;
        "user")
            ENV_FILE_PATH="$HOME/.config/shuttle/shuttle_env.sh"
            ;;
        "service")
            ENV_FILE_PATH="/etc/shuttle/shuttle_env.sh"
            ;;
    esac
    
    # Step 1: Environment activation
    echo "1. Activate the Shuttle environment:"
    echo "   source $ENV_FILE_PATH"
    echo ""
    
    # Step 2: Virtual environment (conditional)
    if [[ "$SKIP_MODULES" == "true" ]]; then
        # IDE-managed venv
        case $VENV_TYPE in
            "vscode")
                echo "2. Complete VSCode virtual environment setup:"
                echo "   - Ensure VSCode has created the .venv"
                echo "   - Select the interpreter: Ctrl+Shift+P → 'Python: Select Interpreter'"
                echo "   - Choose .venv/bin/python"
                echo ""
                echo "3. Install Python dependencies in VSCode terminal:"
                echo "   pip install -r scripts/1_deployment/requirements.txt"
                echo ""
                echo "4. Install Shuttle modules:"
                if [[ "$INSTALL_MODE" == "dev" ]]; then
                    echo "   ./scripts/1_deployment/08_install_shared.sh -e"
                    echo "   ./scripts/1_deployment/09_install_defender_test.sh -e"
                    echo "   ./scripts/1_deployment/10_install_shuttle.sh -e"
                else
                    echo "   ./scripts/1_deployment/08_install_shared.sh"
                    echo "   ./scripts/1_deployment/09_install_defender_test.sh"
                    echo "   ./scripts/1_deployment/10_install_shuttle.sh"
                fi
                ;;
            "pycharm")
                echo "2. Complete PyCharm virtual environment setup:"
                echo "   - Ensure PyCharm has created the venv"
                echo "   - Verify interpreter is selected in Settings"
                echo ""
                echo "3. Install Python dependencies in PyCharm terminal:"
                echo "   pip install -r scripts/1_deployment/requirements.txt"
                echo ""
                echo "4. Install Shuttle modules:"
                if [[ "$INSTALL_MODE" == "dev" ]]; then
                    echo "   ./scripts/1_deployment/08_install_shared.sh -e"
                    echo "   ./scripts/1_deployment/09_install_defender_test.sh -e"
                    echo "   ./scripts/1_deployment/10_install_shuttle.sh -e"
                else
                    echo "   ./scripts/1_deployment/08_install_shared.sh"
                    echo "   ./scripts/1_deployment/09_install_defender_test.sh"
                    echo "   ./scripts/1_deployment/10_install_shuttle.sh"
                fi
                ;;
            *)
                echo "2. Unexpected state - please run module installation manually"
                ;;
        esac
    else
        # Script-managed venv or no venv
        if [[ "$CREATE_VENV" == "true" ]]; then
            echo "2. Activate Python virtual environment:"
            echo "   source $VENV_PATH/bin/activate"
            echo ""
        fi
        
        if [[ "$VENV_TYPE" == "jupyter" ]]; then
            echo "3. Register Jupyter kernel:"
            echo "   python -m ipykernel install --user --name shuttle --display-name 'Shuttle Dev'"
            echo ""
        fi
    fi
    
    # GPG keys reminder
    if [[ ! -f "shuttle_public.gpg" ]]; then
        echo ""
        echo "⚠️  IMPORTANT: Generate GPG keys before using Shuttle:"
        echo "   ./scripts/0_key_generation/00_generate_shuttle_keys.sh"
        echo "   cp shuttle_public.gpg $CONFIG_DIR/"
    fi
    
    # Testing
    echo ""
    echo "To verify installation:"
    echo "   python tests/run_tests.py"
    echo ""
    echo "To run Shuttle:"
    echo "   run-shuttle"
    echo ""
    
    # Save detailed instructions
    cat > setup_complete.txt <<EOF
Shuttle Installation Complete
============================

Installation Mode: $INSTALL_MODE
Virtual Environment Type: $VENV_TYPE

Environment Variables:
  SHUTTLE_CONFIG_PATH=$CONFIG_PATH
  SHUTTLE_VENV_PATH=$VENV_PATH
  SHUTTLE_WORK_DIR=$WORK_DIR

Configuration:
  Source: $SOURCE_PATH
  Destination: $DEST_PATH
  Quarantine: $QUARANTINE_PATH
  Logs: $LOG_PATH
  Hazard Archive: $HAZARD_PATH
  Scan threads: $SCAN_THREADS
  Log level: $LOG_LEVEL
  ClamAV: $USE_CLAMAV
  Defender: $USE_DEFENDER

To start working:
1. source $ENV_FILE_PATH
2. source $VENV_PATH/bin/activate (if applicable)
3. run-shuttle (to test)

Configuration file: $CONFIG_PATH
Environment file: $ENV_FILE_PATH
EOF

    if [[ -n "$ADMIN_EMAIL" ]]; then
        cat >> setup_complete.txt <<EOF

Email Notifications:
  Admin email: $ADMIN_EMAIL
  SMTP server: $SMTP_SERVER:$SMTP_PORT
  TLS: $USE_TLS
EOF
    fi

    echo "These instructions have been saved to: setup_complete.txt"
    echo ""
}
```

## Main Script Structure

```bash
#!/bin/bash
# setup_shuttle_interactive.sh - Interactive Shuttle setup script

set -e  # Exit on error

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Main function
main() {
    echo "========================================="
    echo "    Shuttle Interactive Setup Script     "
    echo "========================================="
    echo ""
    
    # Step 1: Installation mode selection
    select_installation_mode
    
    # Step 2: Check prerequisites (GPG keys)
    check_prerequisites
    
    # Step 3: Check system dependencies
    check_and_install_system_deps
    
    # Step 4: Virtual environment type selection
    select_venv_type
    
    # Step 5: Collect environment variables
    collect_environment_variables
    
    # Step 6: Collect configuration parameters
    collect_config_parameters
    
    # Step 7: Confirm settings
    echo ""
    echo "=== Configuration Review ==="
    echo ""
    echo "Installation mode: $INSTALL_MODE"
    echo "Virtual environment: $VENV_TYPE"
    echo "Config path: $CONFIG_PATH"
    echo "Working directory: $WORK_DIR"
    echo ""
    read -p "Proceed with installation? [Y/n]: " CONFIRM
    if [[ "$CONFIRM" == "n" ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    
    # Step 8: Execute installation
    execute_installation
    
    # Step 9: Show next steps
    show_next_steps
}

# Include all function definitions here...
# (All the functions from sections 1-8 above)

# Run main function
main "$@"
```

## Script Flow

1. **Start** → Welcome message and mode selection
2. **Prerequisites** → Check for GPG keys
3. **Dependencies** → Verify/install system dependencies
4. **Environment** → Select virtual environment approach
5. **Variables** → Collect environment paths
6. **Configuration** → Collect all configuration parameters
7. **Confirm** → Review and confirm settings
8. **Execute** → Run installation with 01-10 scripts
9. **Complete** → Show next steps and save instructions

## Key Features

- **IDE Detection**: Automatically detects VSCode, PyCharm, Jupyter
- **Smart Defaults**: Different defaults for dev vs production
- **Flexible**: All parameters can be customized
- **Non-invasive**: Doesn't interfere with IDE virtual environment management
- **Instructive**: Clear post-setup instructions
- **Resumable**: Saves configuration for reference

## Implementation Notes

- Script runs with user privileges (no sudo required during main flow)
- System dependencies check can trigger sudo if needed
- All environment variables are exported for script duration
- Creates shuttle_env.sh for future sessions
- Creates .env file for IDEs that use it
- Respects IDE preferences for virtual environment management