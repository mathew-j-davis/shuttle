#!/bin/bash
# 1_install.sh - Interactive Shuttle installation script
#
# This script guides you through installing Shuttle with appropriate
# configuration for your environment (development, user, or system/service)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_DIR="$SCRIPT_DIR/1_deployment_steps"

# Change to project root
cd "$PROJECT_ROOT"

# Global variables
INSTALL_MODE=""
ENV_FLAG=""
VENV_TYPE=""
CREATE_VENV=true
REGISTER_KERNEL=false
IN_VENV=false
CONFIG_PATH=""
VENV_PATH=""
TEST_WORK_DIR=""
GPG_KEY_PATH=""

# Installation flags
INSTALL_BASIC_DEPS=false
INSTALL_PYTHON=false
INSTALL_CLAMAV=false
CHECK_DEFENDER=false
SKIP_PYTHON_DEPS=false
SKIP_MODULES=false

echo "========================================="
echo "    Shuttle Interactive Setup Script     "
echo "========================================="
echo ""
echo "Throughout this installation:"
echo "• Press ENTER to accept the suggested default"
echo "• Defaults are shown in [brackets]"
echo "• Type 'x' to exit at any prompt (except file paths)"
echo ""

# Helper function to check sudo access
check_sudo_access() {
    # Check if sudo command exists
    if ! command -v sudo >/dev/null 2>&1; then
        echo -e "${RED}❌ sudo command not found${NC}"
        echo "This system doesn't have sudo installed or it's not in PATH"
        return 1
    fi
    
    # Check if user has sudo privileges
    if sudo -n true 2>/dev/null; then
        # Can run sudo without password
        return 0
    elif sudo -v 2>/dev/null; then
        # Has sudo but needs password
        echo ""
        echo -e "${YELLOW}🔐 You may be prompted for your sudo password during installation${NC}"
        echo "   This is needed to install system packages"
        echo ""
        return 0
    else
        echo -e "${RED}❌ No sudo access${NC}"
        echo "You need sudo privileges to install system packages"
        return 1
    fi
}

# 1. Installation Mode Selection
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
            echo -e "${GREEN}Selected: Development mode${NC}"
            ;;
        2) 
            INSTALL_MODE="user"
            ENV_FLAG="-u"
            echo -e "${GREEN}Selected: User production mode${NC}"
            ;;
        3) 
            INSTALL_MODE="service"
            ENV_FLAG=""
            echo -e "${GREEN}Selected: Service account mode${NC}"
            ;;
        *) 
            INSTALL_MODE="dev"
            ENV_FLAG="-e"
            echo -e "${GREEN}Defaulting to: Development mode${NC}"
            ;;
    esac
    echo ""
}

# 2. Check Virtual Environment Status
check_venv_status() {
    echo "=== Python Virtual Environment Check ==="
    echo ""
    
    # Check if we're already in a virtual environment
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo -e "${GREEN}✅ Virtual environment is active: $VIRTUAL_ENV${NC}"
        echo ""
        echo "Python packages will be installed in this environment."
        IN_VENV=true
        CREATE_VENV=false
        VENV_TYPE="existing"
        return 0
    fi
    
    echo "No virtual environment is currently active."
    echo ""
    echo "How would you like to handle Python package installation?"
    echo ""
    echo "1) Install globally (no virtual environment)"
    echo "   - Packages will be installed system-wide"
    echo "   - May require sudo for some operations"
    echo "   - Not recommended for development"
    echo ""
    echo "2) Let this script create a virtual environment"
    echo "   - Recommended for isolated installation"
    echo "   - Script will create and activate .venv"
    echo ""
    echo "X) I'll set up my own virtual environment"
    echo "   - Exit now to create and activate your venv"
    echo "   - Then run this script again"
    echo ""
    
    read -p "Your choice [2]: " VENV_CHOICE
    VENV_CHOICE=${VENV_CHOICE:-2}
    
    case $VENV_CHOICE in
        1)
            echo ""
            echo -e "${YELLOW}⚠️  Warning: Installing globally is not recommended${NC}"
            echo "This may conflict with system packages or other projects."
            read -p "Install globally? (Default: No) [y/N/x]: " CONFIRM_GLOBAL
            case $CONFIRM_GLOBAL in
                [Yy]) 
                    CREATE_VENV=false
                    VENV_TYPE="global"
                    IN_VENV=false
                    echo -e "${GREEN}Selected: Global installation${NC}"
                    ;;
                [Xx]) 
                    echo "Installation cancelled by user."
                    exit 0 
                    ;;
                *) # Default is No
                    echo "Cancelled. Please choose another option."
                    check_venv_status  # Recursive call to ask again
                    return
                    ;;
            esac
            ;;
        2)
            CREATE_VENV=true
            VENV_TYPE="script"
            IN_VENV=false
            echo -e "${GREEN}Selected: Script will create virtual environment${NC}"
            ;;
        3|[Xx])
            echo ""
            echo "Please set up your virtual environment:"
            echo ""
            echo "For standard venv:"
            echo -e "  ${BLUE}python3 -m venv .venv${NC}"
            echo -e "  ${BLUE}source .venv/bin/activate${NC}"
            echo ""
            echo "For conda:"
            echo -e "  ${BLUE}conda create -n shuttle python=3.8${NC}"
            echo -e "  ${BLUE}conda activate shuttle${NC}"
            echo ""
            echo "Then run this installer again."
            exit 0
            ;;
        *)
            CREATE_VENV=true
            VENV_TYPE="script"
            IN_VENV=false
            echo -e "${GREEN}Defaulting to: Script will create virtual environment${NC}"
            ;;
    esac
    echo ""
}

# 2a. IDE-specific Virtual Environment Management (only if in dev mode and creating venv)
select_venv_ide_options() {
    if [[ "$INSTALL_MODE" != "dev" ]] || [[ "$CREATE_VENV" != "true" ]]; then
        return 0
    fi
    
    # Detect IDEs
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
    
    if [[ ${#DETECTED_IDES[@]} -gt 0 ]]; then
        echo "=== IDE Integration ==="
        echo -e "${BLUE}Detected IDEs: ${DETECTED_IDES[*]}${NC}"
        echo ""
        echo "Would you like to register the virtual environment with Jupyter?"
        read -p "Register as Jupyter kernel? (Default: No) [y/N/x]: " REGISTER_JUPYTER
        case $REGISTER_JUPYTER in
            [Yy])
                REGISTER_KERNEL=true
                echo -e "${GREEN}Will register Jupyter kernel after installation${NC}"
                ;;
            [Xx])
                echo "Installation cancelled by user."
                exit 0
                ;;
            *) # Default is No
                REGISTER_KERNEL=false
                ;;
        esac
        echo ""
    fi
}

# 3. Check Prerequisites (GPG Keys)
check_prerequisites() {
    echo "=== Prerequisites Check ==="
    echo ""
    echo "Shuttle requires GPG keys for encrypting malware files that are detected."
    echo "This is done to protect the system."
    echo "The public key must be accessible to Shuttle for encrypting suspicious files."
    echo ""
    
    # Set default key path based on config location
    CONFIG_DIR=$(dirname "$CONFIG_PATH")
    DEFAULT_KEY_PATH="$CONFIG_DIR/shuttle_public.gpg"
    
    echo "GPG public key location:"
    echo "Path where the GPG public key file will be stored for encrypting malware to protect the system."
    echo ""
    read -p "[$DEFAULT_KEY_PATH]: " GPG_KEY_PATH
    GPG_KEY_PATH=${GPG_KEY_PATH:-$DEFAULT_KEY_PATH}
    
    # Check if key exists
    if [[ -f "$GPG_KEY_PATH" ]]; then
        echo -e "${GREEN}✅ GPG public key found at: $GPG_KEY_PATH${NC}"
    else
        echo -e "${YELLOW}⚠️  GPG public key not found at: $GPG_KEY_PATH${NC}"
        echo ""
        echo "This path will be saved in the configuration. You can:"
        echo "1. Generate keys after installation and place the public key at this path"
        echo "2. Generate keys now manually"
        echo ""
        echo "To generate GPG keys:"
        echo -e "  ${BLUE}./scripts/0_key_generation/00_generate_shuttle_keys.sh${NC}"
        echo -e "  ${BLUE}cp shuttle_public.gpg $GPG_KEY_PATH${NC}"
        echo ""
        read -p "Continue without key file? (Default: Yes) [Y/n/x]: " CONTINUE_WITHOUT_KEY
        case $CONTINUE_WITHOUT_KEY in
            [Nn])
                echo "Installation cancelled. Generate keys and run installer again."
                exit 0
                ;;
            [Xx])
                echo "Installation cancelled by user."
                exit 0
                ;;
            *) # Default is Yes - continue
                ;;
        esac
    fi
    echo ""
}

# 4. System Dependencies Check and Installation
check_and_install_system_deps() {
    echo "=== System Dependencies Check ==="
    echo ""
    echo "Shuttle requires several system packages to function properly:"
    echo "• System tools (lsof, gnupg)"
    echo "• Python 3 and development tools"
    echo "• Antivirus scanners (ClamAV recommended)"
    echo ""
    echo "This check will scan your system and offer to install missing packages."
    echo "Installing packages requires sudo privileges and may prompt for your password."
    echo ""
    
    read -p "Check and install system dependencies? (Default: Yes) [Y/n/x]: " CHECK_DEPS
    case $CHECK_DEPS in
        [Nn])
            echo ""
            echo -e "${YELLOW}⚠️  Skipping dependency checks${NC}"
            echo ""
            echo "To check and install dependencies manually:"
            echo ""
            echo "Check what's installed:"
            echo -e "  ${BLUE}command -v lsof gnupg python3 pip3 clamscan${NC}"  
            echo ""
            echo "Install missing packages (Ubuntu/Debian):"
            echo -e "  ${BLUE}sudo apt-get update${NC}"
            echo -e "  ${BLUE}sudo apt-get install lsof gnupg ${NC}"  
            echo -e "  ${BLUE}sudo apt-get install python3 python3-pip python3-venv python3-dev${NC}"
            echo -e "  ${BLUE}sudo apt-get install clamav clamav-daemon${NC}"
            echo ""
            echo "For other distributions, use your package manager (yum, dnf, zypper, pacman, etc.)"
            echo ""
            return 0
            ;;
        [Xx])
            echo "Installation cancelled by user."
            exit 0
            ;;
        *) # Default is Yes - continue with dependency checks
            ;;
    esac
    
    MISSING_BASIC_DEPS=()
    MISSING_PYTHON=false
    MISSING_CLAMAV=false
    MISSING_DEFENDER=false
    NEED_SUDO=false
    
    # Check for basic system tools
    command -v lsof >/dev/null 2>&1 || MISSING_BASIC_DEPS+=("lsof")
    command -v gpg >/dev/null 2>&1 || MISSING_BASIC_DEPS+=("gnupg")

    
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
    
    # Determine if we'll need sudo for any installations
    if [[ ${#MISSING_BASIC_DEPS[@]} -gt 0 ]] || [[ "$MISSING_PYTHON" == "true" ]] || [[ "$MISSING_CLAMAV" == "true" ]]; then
        NEED_SUDO=true
    fi
    
    # Check sudo access if we'll need it
    if [[ "$NEED_SUDO" == "true" ]]; then
        echo ""
        echo -e "${YELLOW}🔐 System package installation requires sudo privileges${NC}"
        if ! check_sudo_access; then
            echo ""
            echo -e "${RED}❌ Cannot proceed without sudo access${NC}"
            echo "Please either:"
            echo "  1. Run this script as a user with sudo privileges"
            echo "  2. Ask your system administrator to install the missing packages"
            echo "  3. Install the packages manually and run this script again"
            exit 1
        fi
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

            esac
        done
        echo ""
        read -p "Install system tools? (Default: Yes) [Y/n/x]: " choice
        case $choice in
            [Nn]) 
                INSTALL_BASIC_DEPS=false
                echo -e "${YELLOW}⚠️  Skipping system tools - installation may fail later${NC}"
                ;;
            [Xx]) 
                echo "Installation cancelled by user."
                exit 0 
                ;;
            *) # Default is Yes
                INSTALL_BASIC_DEPS=true
                ;;
        esac
    else
        echo -e "${GREEN}✅ All required system tools found${NC}"
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
        read -p "Install Python? (Default: Yes) [Y/n/x]: " choice
        case $choice in
            [Nn]) 
                echo -e "${RED}❌ Cannot continue without Python${NC}"
                echo "Please install Python manually and run this script again"
                exit 1 
                ;;
            [Xx]) 
                echo "Installation cancelled by user."
                exit 0 
                ;;
            *) # Default is Yes
                INSTALL_PYTHON=true
                ;;
        esac
    else
        echo -e "${GREEN}✅ Python 3 found${NC}"
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
        read -p "Install ClamAV? (Default: Yes) [Y/n/x]: " choice
        case $choice in
            [Nn]) 
                INSTALL_CLAMAV=false
                echo -e "${YELLOW}⚠️  Skipping ClamAV - virus scanning will be limited to Microsoft Defender${NC}"
                ;;
            [Xx]) 
                echo "Installation cancelled by user."
                exit 0 
                ;;
            *) # Default is Yes
                INSTALL_CLAMAV=true
                ;;
        esac
    else
        echo -e "${GREEN}✅ ClamAV found${NC}"
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
        read -p "Check Microsoft Defender? (Default: Yes) [Y/n/x]: " choice
        case $choice in
            [Nn]) 
                CHECK_DEFENDER=false
                echo -e "${YELLOW}⚠️  Skipping Defender check${NC}"
                ;;
            [Xx]) 
                echo "Installation cancelled by user."
                exit 0 
                ;;
            *) # Default is Yes
                CHECK_DEFENDER=true
                ;;
        esac
    else
        echo -e "${GREEN}✅ Microsoft Defender found${NC}"
        CHECK_DEFENDER=false
    fi
    
    echo ""
}

# 3a. Collect Config Path (early, for prerequisites)
collect_config_path() {
    echo "=== Configuration File Location ==="
    echo "Installation mode: $INSTALL_MODE"
    echo ""
    
    # Set up default config path based on installation mode
    case $INSTALL_MODE in
        "dev")
            DEFAULT_CONFIG="$PROJECT_ROOT/config/config.conf"
            ;;
        "user")
            DEFAULT_CONFIG="$HOME/.config/shuttle/config.conf"
            ;;
        "service")
            DEFAULT_CONFIG="/etc/shuttle/config.conf"
            ;;
    esac
    
    echo "Configuration file location:"
    echo "Path where Shuttle's main configuration file will be stored."
    echo ""
    read -p "[$DEFAULT_CONFIG]: " CONFIG_PATH
    CONFIG_PATH=${CONFIG_PATH:-$DEFAULT_CONFIG}
    
    echo ""
    echo "Configuration file will be: $CONFIG_PATH"
    echo ""
}

# 5. Environment Variables Collection
collect_environment_variables() {
    echo "=== Environment Variables Setup ==="
    echo ""
    
    # Set up default paths based on installation mode (config path already set)
    case $INSTALL_MODE in
        "dev")
            DEFAULT_VENV="$PROJECT_ROOT/.venv"
            DEFAULT_TEST_WORK="$PROJECT_ROOT/test_area"
            ;;
        "user")
            DEFAULT_VENV="$HOME/.local/share/shuttle/venv"
            DEFAULT_TEST_WORK="$HOME/.local/share/shuttle/test_area"
            ;;
        "service")
            DEFAULT_VENV="/opt/shuttle/venv"
            DEFAULT_TEST_WORK="/var/lib/shuttle/test_area"
            ;;
    esac
    
    echo "Additional environment paths:"
    echo ""
    
    echo "Virtual environment path:"
    echo "Location of Python virtual environment."
    echo ""
    read -p "[$DEFAULT_VENV]: " VENV_PATH
    VENV_PATH=${VENV_PATH:-$DEFAULT_VENV}
    echo ""
    
    echo "Test working directory:"
    echo "Directory used by automated tests for temporary file operations."
    echo ""
    read -p "[$DEFAULT_TEST_WORK]: " TEST_WORK_DIR
    TEST_WORK_DIR=${TEST_WORK_DIR:-$DEFAULT_TEST_WORK}
    
    # Derived paths
    CONFIG_DIR=$(dirname "$CONFIG_PATH")
    
    echo ""
    echo "Environment variables set:"
    echo "  SHUTTLE_CONFIG_PATH=$CONFIG_PATH"
    echo "  SHUTTLE_TEST_WORK_DIR=$TEST_WORK_DIR"
    echo ""
}

# 6. Configuration Parameters Collection
collect_config_parameters() {
    echo "=== Configuration Parameters ==="
    echo ""
    
    # Set defaults based on installation mode
    case $INSTALL_MODE in
        "dev")
            DEFAULT_SOURCE="$PROJECT_ROOT/work/incoming"
            DEFAULT_DEST="$PROJECT_ROOT/work/processed"
            DEFAULT_QUARANTINE="$PROJECT_ROOT/work/quarantine"
            DEFAULT_LOG="$PROJECT_ROOT/work/logs"
            DEFAULT_HAZARD="$PROJECT_ROOT/work/hazard"
            DEFAULT_THREADS=1
            DEFAULT_LOG_LEVEL="DEBUG"
            DEFAULT_CLAMAV="n"
            DEFAULT_DEFENDER="Y"
            ;;
        "user")
            DEFAULT_SOURCE="$HOME/shuttle/incoming"
            DEFAULT_DEST="$HOME/shuttle/processed"
            DEFAULT_QUARANTINE="/tmp/shuttle/quarantine"
            DEFAULT_LOG="$HOME/shuttle/logs"
            DEFAULT_HAZARD="$HOME/shuttle/hazard"
            DEFAULT_THREADS=1
            DEFAULT_LOG_LEVEL="INFO"
            DEFAULT_CLAMAV="n"
            DEFAULT_DEFENDER="Y"
            ;;
        "service")
            DEFAULT_SOURCE="/srv/data/incoming"
            DEFAULT_DEST="/srv/data/processed"
            DEFAULT_QUARANTINE="/tmp/shuttle/quarantine"
            DEFAULT_LOG="/var/log/shuttle"
            DEFAULT_HAZARD="/srv/data/hazard"
            DEFAULT_THREADS=1
            DEFAULT_LOG_LEVEL="INFO"
            DEFAULT_CLAMAV="n"
            DEFAULT_DEFENDER="Y"
            ;;
    esac
    
    # File paths
    echo "File Processing Paths:"
    echo ""
    
    echo "Source directory:"
    echo "Location where new files are monitored and picked up for processing."
    echo ""
    read -p "[$DEFAULT_SOURCE]: " SOURCE_PATH
    SOURCE_PATH=${SOURCE_PATH:-$DEFAULT_SOURCE}
    echo ""
    
    echo "Destination directory:"
    echo "Location where clean files are moved after successful scanning."
    echo ""
    read -p "[$DEFAULT_DEST]: " DEST_PATH
    DEST_PATH=${DEST_PATH:-$DEFAULT_DEST}
    echo ""
    
    echo "Quarantine directory:"
    echo "Temporary storage for files during scanning (hashed and isolated)."
    echo ""
    read -p "[$DEFAULT_QUARANTINE]: " QUARANTINE_PATH
    QUARANTINE_PATH=${QUARANTINE_PATH:-$DEFAULT_QUARANTINE}
    echo ""
    
    echo "Log directory:"
    echo "Location where Shuttle writes log files and tracking information."
    echo ""
    read -p "[$DEFAULT_LOG]: " LOG_PATH
    LOG_PATH=${LOG_PATH:-$DEFAULT_LOG}
    echo ""
    
    echo "Hazard archive directory:"
    echo "Location where malware and suspicious files are stored (encrypted)."
    echo ""
    read -p "[$DEFAULT_HAZARD]: " HAZARD_PATH
    HAZARD_PATH=${HAZARD_PATH:-$DEFAULT_HAZARD}
    
    # Scanning configuration
    echo ""
    echo "Virus Scanning Configuration:"
    echo ""
    
    # ClamAV default text
    CLAMAV_DEFAULT_TEXT="No"
    [[ "$DEFAULT_CLAMAV" == "y" ]] && CLAMAV_DEFAULT_TEXT="Yes"
    
    echo "ClamAV scanning:"
    echo "Enable ClamAV antivirus scanner for file scanning."
    echo ""
    read -p "Use ClamAV? (Default: $CLAMAV_DEFAULT_TEXT) [y/N/x]: " USE_CLAMAV
    case $USE_CLAMAV in
        [Yy]) USE_CLAMAV="y" ;;
        [Xx]) echo "Installation cancelled by user."; exit 0 ;;
        *) USE_CLAMAV="$DEFAULT_CLAMAV" ;;
    esac
    echo ""
    
    # Defender default text  
    DEFENDER_DEFAULT_TEXT="Yes"
    [[ "$DEFAULT_DEFENDER" == "n" ]] && DEFENDER_DEFAULT_TEXT="No"
    
    echo "Microsoft Defender scanning:"
    echo "Enable Microsoft Defender for Endpoint scanner for file scanning."
    echo ""
    read -p "Use Defender? (Default: $DEFENDER_DEFAULT_TEXT) [Y/n/x]: " USE_DEFENDER
    case $USE_DEFENDER in
        [Nn]) USE_DEFENDER="n" ;;
        [Xx]) echo "Installation cancelled by user."; exit 0 ;;
        *) USE_DEFENDER="$DEFAULT_DEFENDER" ;;
    esac
    
    # Performance settings
    echo ""
    echo "Performance Settings:"
    echo ""
    
    echo "Scan threads:"
    echo "Number of parallel threads used for file scanning."
    echo ""
    read -p "Threads [$DEFAULT_THREADS]: " SCAN_THREADS
    SCAN_THREADS=${SCAN_THREADS:-$DEFAULT_THREADS}
    echo ""
    
    echo "Minimum free space:"
    echo "Minimum disk space (in MB) required before processing stops."
    echo ""
    read -p "Min Space MB [100]: " MIN_FREE_SPACE
    MIN_FREE_SPACE=${MIN_FREE_SPACE:-100}
    
    # Logging
    echo ""
    echo "Logging Configuration:"
    echo ""
    
    echo "Log level:"
    echo "Detail level for log messages written to files and system logs."
    echo ""
    echo "1) DEBUG   - Detailed diagnostic information"
    echo "2) INFO    - General operational information" 
    echo "3) WARNING - Warning messages for potential issues"
    echo "4) ERROR   - Error messages for serious problems"
    echo "5) CRITICAL - Critical system failures only"
    echo ""
    
    # Get numeric default for display
    case $DEFAULT_LOG_LEVEL in
        "DEBUG") DEFAULT_LOG_NUM=1 ;;
        "INFO") DEFAULT_LOG_NUM=2 ;;
        "WARNING") DEFAULT_LOG_NUM=3 ;;
        "ERROR") DEFAULT_LOG_NUM=4 ;;
        "CRITICAL") DEFAULT_LOG_NUM=5 ;;
        *) DEFAULT_LOG_NUM=2 ;;
    esac
    
    read -p "Log level (Default: $DEFAULT_LOG_LEVEL) [$DEFAULT_LOG_NUM]: " LOG_LEVEL_INPUT
    LOG_LEVEL_INPUT=${LOG_LEVEL_INPUT:-$DEFAULT_LOG_NUM}
    
    # Map number to log level name
    case $LOG_LEVEL_INPUT in
        1) LOG_LEVEL="DEBUG" ;;
        2) LOG_LEVEL="INFO" ;;
        3) LOG_LEVEL="WARNING" ;;
        4) LOG_LEVEL="ERROR" ;;
        5) LOG_LEVEL="CRITICAL" ;;
        "DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL") LOG_LEVEL="$LOG_LEVEL_INPUT" ;;
        *) LOG_LEVEL="$DEFAULT_LOG_LEVEL" ;;
    esac
    
    # Email notifications
    echo ""
    echo "Email Notifications:"
    echo ""
    
    echo "Admin email address:"
    echo "Email address for error notifications and daily summaries (optional)."
    echo ""
    read -p "Admin email (leave blank to skip): " ADMIN_EMAIL
    echo ""
    
    if [[ -n "$ADMIN_EMAIL" ]]; then
        echo "SMTP server configuration:"
        echo ""
        
        echo "SMTP server:"
        echo "Hostname or IP address of your email server."
        echo ""
        read -p "SMTP server: " SMTP_SERVER
        echo ""
        
        echo "SMTP port:"
        echo "Port number for SMTP connection (typically 587 for TLS, 25 for standard)."
        echo ""
        read -p "[587]: " SMTP_PORT
        SMTP_PORT=${SMTP_PORT:-587}
        echo ""
        
        echo "SMTP username:"
        echo "Username for authenticating with the email server."
        echo ""
        read -p "username: " SMTP_USERNAME
        echo ""
        
        echo "SMTP password:"
        echo "Password for authenticating with the email server."
        echo ""
        read -s -p "password: " SMTP_PASSWORD
        echo ""
        echo ""
        
        echo "TLS encryption:"
        echo "Use encrypted connection to the email server."
        echo ""
        read -p "Use TLS? (Default: Yes) [Y/n/x]: " USE_TLS
        case $USE_TLS in
            [Nn]) USE_TLS="n" ;;
            [Xx]) echo "Installation cancelled by user."; exit 0 ;;
            *) USE_TLS="Y" ;;
        esac
    fi
    
    # File processing options
    echo ""
    echo "File Processing Options:"
    echo ""
    
    echo "Delete source files:"
    echo "Remove original files from source directory after successful processing."
    echo ""
    read -p "Delete source files after copying? (Default: Yes) [Y/n/x]: " DELETE_SOURCE
    case $DELETE_SOURCE in
        [Nn]) DELETE_SOURCE="n" ;;
        [Xx]) echo "Installation cancelled by user."; exit 0 ;;
        *) DELETE_SOURCE="Y" ;;
    esac
    echo ""
    
    # Ledger file configuration
    echo "Ledger File Configuration:"
    echo ""
    
    echo "Ledger file path:"
    echo "The ledger file records tested versions of Microsoft Defender."
    echo "This helps track which Defender versions have been validated with Shuttle."
    echo ""
    
    # Set default ledger path based on config location
    CONFIG_DIR=$(dirname "$CONFIG_PATH")
    DEFAULT_LEDGER_PATH="$CONFIG_DIR/ledger/ledger.yaml"
    
    read -p "[$DEFAULT_LEDGER_PATH]: " LEDGER_PATH
    LEDGER_PATH=${LEDGER_PATH:-$DEFAULT_LEDGER_PATH}
    
    echo ""
    echo "Configuration summary:"
    echo "  Source: $SOURCE_PATH"
    echo "  Destination: $DEST_PATH"
    echo "  Quarantine: $QUARANTINE_PATH"
    echo "  Logs: $LOG_PATH"
    echo "  Hazard Archive: $HAZARD_PATH"
    echo "  Ledger file: $LEDGER_PATH"
    echo "  Scan threads: $SCAN_THREADS"
    echo "  Log level: $LOG_LEVEL"
    if [[ -n "$ADMIN_EMAIL" ]]; then
        echo "  Notifications: Enabled ($ADMIN_EMAIL)"
    else
        echo "  Notifications: Disabled"
    fi
    echo ""
}

# 7. Execute Installation
execute_installation() {
    echo "=== Installation Execution ==="
    echo ""
    
    # Set environment variables for script duration
    export SHUTTLE_CONFIG_PATH="$CONFIG_PATH"
    export SHUTTLE_TEST_WORK_DIR="$TEST_WORK_DIR"
    export SHUTTLE_TEST_CONFIG_PATH="$TEST_WORK_DIR/test_config.conf"
    
    echo "Setting up environment variables..."
    
    # Phase 1: System Dependencies (requires sudo)
    echo ""
    echo "📦 Phase 1: Installing system dependencies (requires sudo)"
    
    # Install basic system tools if needed
    if [[ "$INSTALL_BASIC_DEPS" == "true" ]]; then
        echo "Installing basic system tools..."
        "$DEPLOYMENT_DIR/03_sudo_install_dependencies.sh"
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}❌ Failed to install system dependencies${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ Basic system tools installed${NC}"
    fi
    
    # Install Python if needed
    if [[ "$INSTALL_PYTHON" == "true" ]]; then
        echo "Installing Python 3 and development tools..."
        "$DEPLOYMENT_DIR/00_sudo_install_python.sh"
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}❌ Failed to install Python${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ Python installed${NC}"
    fi
    
    # Install ClamAV if requested
    if [[ "$INSTALL_CLAMAV" == "true" ]]; then
        echo "Installing ClamAV antivirus scanner..."
        "$DEPLOYMENT_DIR/05_sudo_install_clamav.sh"
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}❌ Failed to install ClamAV${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ ClamAV installed${NC}"
    fi
    
    # Check Microsoft Defender if requested
    if [[ "$CHECK_DEFENDER" == "true" ]]; then
        echo "Checking Microsoft Defender configuration..."
        "$DEPLOYMENT_DIR/04_check_defender_is_installed.sh"
        if [[ $? -ne 0 ]]; then
            echo -e "${YELLOW}⚠️  Microsoft Defender check completed with warnings${NC}"
        else
            echo -e "${GREEN}✅ Microsoft Defender check completed${NC}"
        fi
    fi
    
    echo -e "${GREEN}✅ System dependencies phase complete${NC}"
    
    # Phase 2: Environment Setup and Virtual Environment
    echo ""
    echo "🔧 Phase 2: Setting up environment and virtual environment"
    
    # Build the command with appropriate flags
    ENV_VENV_CMD="$DEPLOYMENT_DIR/02_env_and_venv.sh $ENV_FLAG"
    
    # Add --do-not-create-venv flag if venv should be handled by IDE
    if [[ "$CREATE_VENV" == "false" ]]; then
        ENV_VENV_CMD="$ENV_VENV_CMD --do-not-create-venv"
    fi
    
    echo "Running: $ENV_VENV_CMD"
    $ENV_VENV_CMD
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ Failed to set up environment and virtual environment${NC}"
        exit 1
    fi
    
    # Re-export the environment variables in this script's context
    export SHUTTLE_CONFIG_PATH="$CONFIG_PATH"
    export SHUTTLE_TEST_WORK_DIR="$TEST_WORK_DIR"
    export SHUTTLE_TEST_CONFIG_PATH="$TEST_WORK_DIR/test_config.conf"
    
    # Activate venv for our use if it was created
    if [[ "$CREATE_VENV" == "true" ]] && [[ -f "$VENV_PATH/bin/activate" ]]; then
        source "$VENV_PATH/bin/activate"
        echo -e "${GREEN}✅ Virtual environment activated for installation${NC}"
    fi
    
    echo -e "${GREEN}✅ Environment and virtual environment setup complete${NC}"
    
    # Phase 3: Python Dependencies
    echo ""
    echo "📚 Phase 3: Installing Python dependencies"
    
    # We can install dependencies if:
    # 1. We're in an active venv (IN_VENV=true)
    # 2. We created a venv and activated it
    # 3. User chose global installation
    
    if [[ "$IN_VENV" == "true" ]] || [[ "$VENV_TYPE" == "global" ]] || [[ -n "$VIRTUAL_ENV" ]]; then
        # Install Python dependencies
        echo "Installing Python development dependencies..."
        "$DEPLOYMENT_DIR/06_install_python_dev_dependencies.sh"
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}❌ Failed to install Python dependencies${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ Python dependencies installed${NC}"
        SKIP_PYTHON_DEPS=false
    else
        echo -e "${YELLOW}⚠️  Cannot install Python dependencies without an active environment${NC}"
        echo "You'll need to install them manually after activating your virtual environment"
        SKIP_PYTHON_DEPS=true
    fi
    
    # Phase 4: Configuration
    echo ""
    echo "⚙️  Phase 4: Generating configuration"
    
    # Build config arguments
    # Use the ledger path specified by user during configuration
    
    CONFIG_ARGS=(
        "--source-path" "$SOURCE_PATH"
        "--destination-path" "$DEST_PATH"
        "--quarantine-path" "$QUARANTINE_PATH"
        "--log-path" "$LOG_PATH"
        "--hazard-archive-path" "$HAZARD_PATH"
        "--ledger-file-path" "$LEDGER_PATH"
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
    
    # Add GPG key path
    CONFIG_ARGS+=("--hazard-encryption-key-path" "$GPG_KEY_PATH")
    
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
    echo "Generating configuration file..."
    python3 "$DEPLOYMENT_DIR/07_setup_config.py" "${CONFIG_ARGS[@]}"
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ Failed to generate configuration${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Configuration generated${NC}"
    
    # Phase 5: Module Installation
    echo ""
    echo "📦 Phase 5: Installing Shuttle modules"
    
    if [[ "$SKIP_PYTHON_DEPS" == "true" ]]; then
        echo -e "${YELLOW}⚠️  Skipping module installation (will be done manually later)${NC}"
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
        
        echo "Installing shared library..."
        "$DEPLOYMENT_DIR/08_install_shared.sh" $MODULE_FLAG
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}❌ Failed to install shared library${NC}"
            exit 1
        fi
        
        echo "Installing defender test module..."
        "$DEPLOYMENT_DIR/09_install_defender_test.sh" $MODULE_FLAG
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}❌ Failed to install defender test module${NC}"
            exit 1
        fi
        
        echo "Installing shuttle application..."
        "$DEPLOYMENT_DIR/10_install_shuttle.sh" $MODULE_FLAG
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}❌ Failed to install shuttle application${NC}"
            exit 1
        fi
        
        echo -e "${GREEN}✅ All modules installed successfully${NC}"
        SKIP_MODULES=false
    fi
    
    # Phase 6: Final Setup
    echo ""
    echo "🎯 Phase 6: Final setup"
    
    # Handle Jupyter kernel registration
    if [[ "$VENV_TYPE" == "jupyter" && "$SKIP_MODULES" == "false" ]]; then
        echo "Installing Jupyter kernel support..."
        pip install ipykernel
        python -m ipykernel install --user --name shuttle --display-name "Shuttle Dev"
        echo -e "${GREEN}✅ Jupyter kernel registered${NC}"
    fi
    
    # Copy GPG key if it exists and config directory is different
    if [[ -f "$PROJECT_ROOT/shuttle_public.gpg" ]] && [[ "$CONFIG_DIR" != "$PROJECT_ROOT" ]]; then
        echo "Copying GPG public key to config directory..."
        cp "$PROJECT_ROOT/shuttle_public.gpg" "$CONFIG_DIR/"
        echo -e "${GREEN}✅ GPG key copied${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}🎉 Installation completed successfully!${NC}"
}

# 8. Show Next Steps
show_next_steps() {
    echo ""
    echo -e "${GREEN}✅ Setup Complete!${NC}"
    echo ""
    echo "=== Next Steps ==="
    echo ""
    
    # Step 1: Environment activation
    echo "1. Activate the Shuttle environment:"
    echo -e "   ${BLUE}source $CONFIG_DIR/shuttle_env.sh${NC}"
    echo ""
    
    # Step 2: Virtual environment and dependencies (conditional)
    if [[ "$SKIP_MODULES" == "true" ]]; then
        # Need to install dependencies and modules manually
        echo "2. Install Python dependencies:"
        
        case $VENV_TYPE in
            "existing")
                echo "   - You already have a virtual environment active"
                echo -e "   ${BLUE}pip install -r scripts/1_deployment_steps/requirements.txt${NC}"
                ;;
            "script")
                echo "   - Activate the virtual environment first:"
                echo -e "   ${BLUE}source $VENV_PATH/bin/activate${NC}"
                echo -e "   ${BLUE}pip install -r scripts/1_deployment_steps/requirements.txt${NC}"
                ;;
            "global")
                echo "   - Installing globally:"
                echo -e "   ${BLUE}pip install -r scripts/1_deployment_steps/requirements.txt${NC}"
                ;;
        esac
        
        echo ""
        echo "3. Install Shuttle modules:"
        if [[ "$INSTALL_MODE" == "dev" ]]; then
            echo -e "   ${BLUE}./scripts/1_deployment_steps/08_install_shared.sh -e${NC}"
            echo -e "   ${BLUE}./scripts/1_deployment_steps/09_install_defender_test.sh -e${NC}"
            echo -e "   ${BLUE}./scripts/1_deployment_steps/10_install_shuttle.sh -e${NC}"
        else
            echo -e "   ${BLUE}./scripts/1_deployment_steps/08_install_shared.sh${NC}"
            echo -e "   ${BLUE}./scripts/1_deployment_steps/09_install_defender_test.sh${NC}"
            echo -e "   ${BLUE}./scripts/1_deployment_steps/10_install_shuttle.sh${NC}"
        fi
    else
        # Everything was installed successfully
        if [[ "$VENV_TYPE" == "script" ]] && [[ "$CREATE_VENV" == "true" ]]; then
            echo "2. To use Shuttle, activate the virtual environment:"
            echo -e "   ${BLUE}source $VENV_PATH/bin/activate${NC}"
            echo ""
        elif [[ "$VENV_TYPE" == "existing" ]]; then
            echo "2. Continue using your existing virtual environment"
            echo ""
        elif [[ "$VENV_TYPE" == "global" ]]; then
            echo "2. Shuttle is installed globally and ready to use"
            echo ""
        fi
        
        if [[ "$REGISTER_KERNEL" == "true" ]]; then
            echo "3. Jupyter kernel is registered as 'Shuttle Dev'"
            echo "   You can now use it in Jupyter notebooks"
            echo ""
        fi
    fi
    
    # GPG keys reminder
    if [[ ! -f "$PROJECT_ROOT/shuttle_public.gpg" ]]; then
        echo ""
        echo -e "${YELLOW}⚠️  IMPORTANT: Generate GPG keys before using Shuttle:${NC}"
        echo -e "   ${BLUE}./scripts/0_key_generation/00_generate_shuttle_keys.sh${NC}"
        echo -e "   ${BLUE}cp shuttle_public.gpg $CONFIG_DIR/${NC}"
    fi
    
    # Testing
    echo ""
    echo "To verify installation:"
    echo -e "   ${BLUE}python tests/run_tests.py${NC}"
    echo ""
    echo "To run Shuttle:"
    echo -e "   ${BLUE}run-shuttle${NC}"
    echo ""
    
    # Save detailed instructions
    SETUP_LOG="$PROJECT_ROOT/setup_complete.txt"
    cat > "$SETUP_LOG" <<EOF
Shuttle Installation Complete
============================

Installation Mode: $INSTALL_MODE
Virtual Environment Type: $VENV_TYPE

Environment Variables:
  SHUTTLE_CONFIG_PATH=$CONFIG_PATH
  SHUTTLE_TEST_WORK_DIR=$TEST_WORK_DIR
  SHUTTLE_TEST_CONFIG_PATH=$TEST_WORK_DIR/test_config.conf

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

File Locations:
  Configuration file: $CONFIG_PATH
  Environment variables: $CONFIG_DIR/shuttle_env.sh
  Ledger file: $LEDGER_PATH
  GPG public key: $GPG_KEY_PATH
  Virtual environment: $VENV_PATH
  VEnv activation script: $CONFIG_DIR/shuttle_activate_virtual_environment.sh
EOF

if [[ "$INSTALL_MODE" == "dev" ]]; then
    cat >> "$SETUP_LOG" <<EOF
  IDE .env file: $PROJECT_ROOT/.env
EOF
fi

cat >> "$SETUP_LOG" <<EOF

To start working:
1. source $CONFIG_DIR/shuttle_env.sh
2. source $CONFIG_DIR/shuttle_activate_virtual_environment.sh (if using venv)
3. run-shuttle (to test)
EOF

    if [[ -n "$ADMIN_EMAIL" ]]; then
        cat >> "$SETUP_LOG" <<EOF

Email Notifications:
  Admin email: $ADMIN_EMAIL
  SMTP server: $SMTP_SERVER:$SMTP_PORT
  TLS: $USE_TLS
EOF
    fi

    echo -e "These instructions have been saved to: ${BLUE}$SETUP_LOG${NC}"
    echo ""
}

# Main function
main() {
    # Step 1: Check virtual environment status FIRST
    check_venv_status
    
    # Step 2: Installation mode selection
    select_installation_mode
    
    # Step 2a: IDE options if applicable
    select_venv_ide_options
    
    # Step 3: Collect config path (needed for prerequisites)
    collect_config_path
    
    # Step 4: Check prerequisites (GPG keys)
    check_prerequisites
    
    # Step 5: Check system dependencies
    check_and_install_system_deps
    
    # Step 6: Collect remaining environment variables
    collect_environment_variables
    
    # Step 7: Collect configuration parameters
    collect_config_parameters
    
    # Step 8: Confirm settings
    echo ""
    echo "=== Configuration Review ==="
    echo ""
    echo "Installation mode: $INSTALL_MODE"
    echo "Virtual environment: $VENV_TYPE"
    echo "Config path: $CONFIG_PATH"
    echo "Working directory: $TEST_WORK_DIR"
    echo ""
    read -p "Proceed with installation? (Default: Yes) [Y/n/x]: " CONFIRM
    case $CONFIRM in
        [Nn]) 
            echo "Installation cancelled."
            exit 0 
            ;;
        [Xx]) 
            echo "Installation cancelled by user."
            exit 0 
            ;;
        *) # Default is Yes - continue
            ;;
    esac
    
    # Step 9: Execute installation
    execute_installation
    
    # Step 10: Show next steps
    show_next_steps
}

# Run main function
main "$@"