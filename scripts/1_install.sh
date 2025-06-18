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
DEPLOYMENT_DIR="$SCRIPT_DIR/1_installation_steps"

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

# Set command history file for this installation session
export COMMAND_HISTORY_FILE="/tmp/shuttle_install_command_history_$(date +%Y%m%d_%H%M%S).log"

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

# Validate saved installation mode against current state
validate_install_mode_instructions() {
    local saved_mode="$1"
    
    # Validate the saved mode is valid
    if ! is_valid_install_mode "$saved_mode"; then
        echo -e "${RED}❌ Invalid installation mode in instructions: $saved_mode${NC}"
        echo "Run in wizard mode: $0 --wizard"
        exit 1
    fi
    
    # For service mode, check if user has appropriate permissions
    if [[ "$saved_mode" == "$INSTALL_MODE_SERVICE" ]]; then
        # Check if user can potentially write to system directories
        if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
            echo -e "${YELLOW}⚠️  Instructions specify service mode but you may lack system permissions${NC}"
            echo ""
            echo "Service mode typically requires root or sudo access for:"
            echo "- Writing to /etc/shuttle/ and /opt/shuttle/"
            echo "- Creating system users and groups"
            echo ""
            read -p "Continue with service mode? [y/N]: " confirm
            case "$confirm" in
                [Yy])
                    echo "Proceeding with service mode - you may be prompted for sudo later"
                    ;;
                *)
                    echo "Installation cancelled. Run in wizard mode: $0 --wizard"
                    exit 1
                    ;;
            esac
        fi
    fi
    
    # Apply the saved mode
    INSTALL_MODE="$saved_mode"
    ENV_FLAG=$(get_env_flag_for_mode "$saved_mode")
    USER_INSTALL_MODE_CHOICE="$saved_mode"
    
    echo -e "${GREEN}✅ Using installation mode from instructions: $saved_mode${NC}"
}

# Interactive installation mode selection (wizard mode)
interactive_install_mode_choice() {
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
            INSTALL_MODE="$INSTALL_MODE_DEV"
            ENV_FLAG=$(get_env_flag_for_mode "$INSTALL_MODE")
            USER_INSTALL_MODE_CHOICE="$INSTALL_MODE_DEV"
            echo -e "${GREEN}Selected: Development mode${NC}"
            ;;
        2) 
            INSTALL_MODE="$INSTALL_MODE_USER"
            ENV_FLAG=$(get_env_flag_for_mode "$INSTALL_MODE")
            USER_INSTALL_MODE_CHOICE="$INSTALL_MODE_USER"
            echo -e "${GREEN}Selected: User production mode${NC}"
            ;;
        3) 
            INSTALL_MODE="$INSTALL_MODE_SERVICE"
            ENV_FLAG=$(get_env_flag_for_mode "$INSTALL_MODE")
            USER_INSTALL_MODE_CHOICE="$INSTALL_MODE_SERVICE"
            echo -e "${GREEN}Selected: Service account mode${NC}"
            ;;
        *) 
            INSTALL_MODE="$INSTALL_MODE_DEV"
            ENV_FLAG=$(get_env_flag_for_mode "$INSTALL_MODE")
            USER_INSTALL_MODE_CHOICE="$INSTALL_MODE_DEV"
            echo -e "${GREEN}Defaulting to: Development mode${NC}"
            ;;
    esac
    echo ""
}

# 2. Unified Installation Mode Selection
select_installation_mode() {
    # Check if we're running from instructions or wizard mode
    if [[ -n "$INSTALL_INSTRUCTIONS_FILE" ]]; then
        # Instructions mode - validate saved choice
        echo "Reading installation mode from instructions..."
        
        # TODO: Read saved choice from instructions file
        # For now, this is a placeholder - we'll implement file reading later
        echo "Instructions mode not yet implemented - falling back to wizard"
        interactive_install_mode_choice
    else
        # Wizard mode - interactive choice
        interactive_install_mode_choice
    fi
}

# Load installation constants for consistent choice handling
load_installation_constants_for_install() {
    # Load the constants library
    SETUP_LIB_SH_DIR="$SCRIPT_DIR/__setup_lib_sh"
    local loader_path="$SETUP_LIB_SH_DIR/_setup_lib_loader.source.sh"
    
    if [[ -f "$loader_path" ]]; then
        source "$loader_path"
        # Pass explicit directory to ensure correct path resolution
        load_installation_constants_lib "$SCRIPT_DIR" || {
            echo "ERROR: Failed to load installation constants from $SCRIPT_DIR" >&2
            return 1
        }
    else
        echo "ERROR: Setup library loader not found at: $loader_path" >&2
        return 1
    fi
}

# Detect current virtual environment state (always runs)
detect_venv_state() {
    local current_venv_active=false
    local current_venv_path=""
    
    if [[ -n "$VIRTUAL_ENV" ]]; then
        current_venv_active=true
        current_venv_path="$VIRTUAL_ENV"
    fi
    
    # Export state for use by other functions
    CURRENT_VENV_ACTIVE="$current_venv_active"
    CURRENT_VENV_PATH="$current_venv_path"
}

# Validate saved instructions against current venv state
validate_venv_instructions() {
    local current_venv_active="$1"
    local saved_user_choice="$2"
    
    case "$saved_user_choice" in
        "$VENV_CHOICE_EXISTING")
            # Instructions expect to use existing venv
            if [[ "$current_venv_active" == "true" ]]; then
                IN_VENV=true
                CREATE_VENV=false
                VENV_TYPE="$VENV_TYPE_EXISTING"
                echo -e "${GREEN}✅ Using active virtual environment as instructed: $CURRENT_VENV_PATH${NC}"
            else
                echo -e "${RED}❌ Instructions expect active virtual environment${NC}"
                echo ""
                echo "When instructions were saved, a virtual environment was active,"
                echo "but no virtual environment is currently active."
                echo ""
                echo "Please either:"
                echo "1. Activate your virtual environment and run again"
                echo "2. Run in wizard mode: $0 --wizard"
                exit 1
            fi
            ;;
            
        "$VENV_CHOICE_SCRIPT_CREATES")
            # Instructions want script to create venv
            if [[ "$current_venv_active" == "true" ]]; then
                echo -e "${RED}❌ Instructions want script to create virtual environment${NC}"
                echo ""
                echo "When instructions were saved, no virtual environment was active,"
                echo "but you currently have a virtual environment active: $CURRENT_VENV_PATH"
                echo ""
                echo "Please either:"
                echo "1. Deactivate your virtual environment: deactivate"
                echo "2. Run in wizard mode: $0 --wizard"
                exit 1
            else
                CREATE_VENV=true
                VENV_TYPE="$VENV_TYPE_SCRIPT"
                IN_VENV=false
                echo -e "${GREEN}✅ Will create virtual environment as instructed${NC}"
            fi
            ;;
            
        "$VENV_CHOICE_GLOBAL")
            # Instructions want global install
            if [[ "$current_venv_active" == "true" ]]; then
                echo -e "${YELLOW}⚠️  Instructions specify global install but venv is active${NC}"
                echo ""
                echo "When instructions were saved, global installation was chosen,"
                echo "but you currently have a virtual environment active: $CURRENT_VENV_PATH"
                echo ""
                echo "Global installation will ignore the virtual environment."
                read -p "Continue with global install? [y/N]: " confirm
                case "$confirm" in
                    [Yy])
                        CREATE_VENV=false
                        VENV_TYPE="$VENV_TYPE_GLOBAL"
                        IN_VENV=false
                        echo -e "${GREEN}✅ Using global Python installation as instructed${NC}"
                        ;;
                    *)
                        echo "Installation cancelled. Run in wizard mode: $0 --wizard"
                        exit 1
                        ;;
                esac
            else
                CREATE_VENV=false
                VENV_TYPE="$VENV_TYPE_GLOBAL"
                IN_VENV=false
                echo -e "${GREEN}✅ Using global Python installation as instructed${NC}"
            fi
            ;;
        *)
            echo -e "${RED}❌ Unknown venv choice in instructions: $saved_user_choice${NC}"
            echo "Run in wizard mode: $0 --wizard"
            exit 1
            ;;
    esac
}

# Interactive venv choice (wizard mode)
interactive_venv_choice() {
    local current_venv_active="$1"
    
    if [[ "$current_venv_active" == "true" ]]; then
        echo -e "${GREEN}✅ Virtual environment is active: $CURRENT_VENV_PATH${NC}"
        echo ""
        echo "Python packages will be installed in this environment."
        IN_VENV=true
        CREATE_VENV=false
        VENV_TYPE="$VENV_TYPE_EXISTING"
        
        # Save the choice that was made for instructions file
        USER_VENV_CHOICE="$VENV_CHOICE_EXISTING"
        EXPECTED_VENV_ACTIVE=true
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
    
    # Loop until we get a valid choice (avoids recursive calls)
    while true; do
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
                        VENV_TYPE="$VENV_TYPE_GLOBAL"
                        IN_VENV=false
                        USER_VENV_CHOICE="$VENV_CHOICE_GLOBAL"
                        echo -e "${GREEN}Selected: Global installation${NC}"
                        break
                        ;;
                    [Xx]) 
                        echo "Installation cancelled by user."
                        exit 0 
                        ;;
                    *) # Default is No - ask again
                        echo "Cancelled. Please choose another option."
                        echo ""
                        continue
                        ;;
                esac
                ;;
            2)
                CREATE_VENV=true
                VENV_TYPE="$VENV_TYPE_SCRIPT"
                IN_VENV=false
                USER_VENV_CHOICE="$VENV_CHOICE_SCRIPT_CREATES"
                echo -e "${GREEN}Selected: Script will create virtual environment${NC}"
                break
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
                VENV_TYPE="$VENV_TYPE_SCRIPT"
                IN_VENV=false
                USER_VENV_CHOICE="$VENV_CHOICE_SCRIPT_CREATES"
                echo -e "${GREEN}Defaulting to: Script will create virtual environment${NC}"
                break
                ;;
        esac
    done
    
    # Save that no venv was active when choice was made
    EXPECTED_VENV_ACTIVE=false
    echo ""
}

# 2. Unified Virtual Environment Status Check
check_venv_status() {
    echo "=== Python Virtual Environment Check ==="
    echo ""
    
    # Always detect current state first
    detect_venv_state
    
    # Check if we're running from instructions or wizard mode
    if [[ -n "$INSTALL_INSTRUCTIONS_FILE" ]]; then
        # Instructions mode - validate saved choice against current state
        echo "Reading virtual environment choice from instructions..."
        
        # TODO: Read saved choice from instructions file
        # For now, this is a placeholder - we'll implement file reading later
        echo "Instructions mode not yet implemented - falling back to wizard"
        interactive_venv_choice "$CURRENT_VENV_ACTIVE"
    else
        # Wizard mode - interactive choice
        interactive_venv_choice "$CURRENT_VENV_ACTIVE"
    fi
}

# Detect current IDE state (always runs when applicable)
detect_ide_state() {
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
}

# Validate saved IDE preferences against current state
validate_ide_instructions() {
    local saved_register_kernel="$1"
    
    # Always detect current IDE state
    detect_ide_state
    
    # Check if the saved preference can be applied
    if [[ "$saved_register_kernel" == "true" ]]; then
        # Check prerequisites for kernel registration
        if [[ "$INSTALL_MODE" != "$INSTALL_MODE_DEV" ]]; then
            echo -e "${YELLOW}⚠️  Instructions specify Jupyter kernel registration but not in dev mode${NC}"
            echo "Jupyter kernel registration is only available in development mode."
            REGISTER_KERNEL=false
        elif [[ "$CREATE_VENV" != "true" ]]; then
            echo -e "${YELLOW}⚠️  Instructions specify Jupyter kernel registration but not creating venv${NC}"
            echo "Jupyter kernel registration requires creating a virtual environment."
            REGISTER_KERNEL=false
        else
            REGISTER_KERNEL=true
            echo -e "${GREEN}✅ Will register Jupyter kernel as instructed${NC}"
        fi
    else
        REGISTER_KERNEL=false
        echo -e "${GREEN}✅ Will not register Jupyter kernel as instructed${NC}"
    fi
    
    USER_REGISTER_KERNEL_CHOICE="$saved_register_kernel"
}

# Interactive IDE options (wizard mode)
interactive_ide_choice() {
    # Only run if in dev mode and creating venv
    if [[ "$INSTALL_MODE" != "$INSTALL_MODE_DEV" ]] || [[ "$CREATE_VENV" != "true" ]]; then
        REGISTER_KERNEL=false
        USER_REGISTER_KERNEL_CHOICE="false"
        return 0
    fi
    
    # Detect current IDE state
    detect_ide_state
    
    if [[ ${#DETECTED_IDES[@]} -gt 0 ]]; then
        echo "=== IDE Integration ==="
        echo -e "${BLUE}Detected IDEs: ${DETECTED_IDES[*]}${NC}"
        echo ""
        echo "Would you like to register the virtual environment with Jupyter?"
        read -p "Register as Jupyter kernel? (Default: No) [y/N/x]: " REGISTER_JUPYTER
        case $REGISTER_JUPYTER in
            [Yy])
                REGISTER_KERNEL=true
                USER_REGISTER_KERNEL_CHOICE="true"
                echo -e "${GREEN}Will register Jupyter kernel after installation${NC}"
                ;;
            [Xx])
                echo "Installation cancelled by user."
                exit 0
                ;;
            *) # Default is No
                REGISTER_KERNEL=false
                USER_REGISTER_KERNEL_CHOICE="false"
                ;;
        esac
        echo ""
    else
        # No IDEs detected - set defaults
        REGISTER_KERNEL=false
        USER_REGISTER_KERNEL_CHOICE="false"
    fi
}

# 3. Unified IDE-specific Virtual Environment Management
select_venv_ide_options() {
    # Check if we're running from instructions or wizard mode
    if [[ -n "$INSTALL_INSTRUCTIONS_FILE" ]]; then
        # Instructions mode - validate saved preference
        echo "Reading IDE preferences from instructions..."
        
        # TODO: Read saved preference from instructions file
        # For now, this is a placeholder - we'll implement file reading later
        echo "Instructions mode not yet implemented - falling back to wizard"
        interactive_ide_choice
    else
        # Wizard mode - interactive choice
        interactive_ide_choice
    fi
}

# Validate saved GPG key path against current state
validate_gpg_instructions() {
    local saved_gpg_path="$1"
    
    # Basic path validation
    if [[ -z "$saved_gpg_path" ]]; then
        echo -e "${RED}❌ Empty GPG key path in instructions${NC}"
        echo "Run in wizard mode: $0 --wizard"
        exit 1
    fi
    
    # Check if key exists at saved path
    if [[ -f "$saved_gpg_path" ]]; then
        echo -e "${GREEN}✅ GPG public key found at saved path: $saved_gpg_path${NC}"
    else
        echo -e "${YELLOW}⚠️  GPG public key not found at saved path: $saved_gpg_path${NC}"
        echo ""
        echo "The key file from instructions doesn't exist. You can:"
        echo "1. Generate keys and place the public key at this path"
        echo "2. Continue installation and generate keys later"
        echo ""
        echo "To generate GPG keys:"
        echo -e "  ${BLUE}./scripts/0_key_generation/00_generate_shuttle_keys.sh${NC}"
        echo -e "  ${BLUE}cp shuttle_public.gpg $saved_gpg_path${NC}"
        echo ""
        read -p "Continue with this key path? [Y/n]: " confirm
        case "$confirm" in
            [Nn])
                echo "Installation cancelled. Run in wizard mode: $0 --wizard"
                exit 1
                ;;
        esac
    fi
    
    # Apply saved path
    GPG_KEY_PATH="$saved_gpg_path"
    USER_GPG_KEY_PATH_CHOICE="$saved_gpg_path"
    
    echo -e "${GREEN}✅ Using GPG key path from instructions: $saved_gpg_path${NC}"
}

# Interactive GPG prerequisites (wizard mode)
interactive_gpg_choice() {
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
    USER_GPG_KEY_PATH_CHOICE="$GPG_KEY_PATH"
    
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

# 5. Unified Prerequisites Check
check_prerequisites() {
    # Check if we're running from instructions or wizard mode
    if [[ -n "$INSTALL_INSTRUCTIONS_FILE" ]]; then
        # Instructions mode - validate saved path
        echo "Reading GPG key path from instructions..."
        
        # TODO: Read saved path from instructions file
        # For now, this is a placeholder - we'll implement file reading later
        echo "Instructions mode not yet implemented - falling back to wizard"
        interactive_gpg_choice
    else
        # Wizard mode - interactive choice
        interactive_gpg_choice
    fi
}

# Detect current system dependency state (always runs)
detect_system_deps_state() {
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
}

# Validate saved system dependency choices against current state
validate_system_deps_instructions() {
    local saved_install_basic_deps="$1"
    local saved_install_python="$2"
    local saved_install_clamav="$3"
    local saved_check_defender="$4"
    
    # Always detect current system state
    detect_system_deps_state
    
    # Check for conflicts between saved choices and current state
    
    # Python is required - cannot skip if missing
    if [[ "$saved_install_python" == "false" && "$MISSING_PYTHON" == "true" ]]; then
        echo -e "${RED}❌ Instructions say don't install Python, but Python is missing${NC}"
        echo "Python is required for Shuttle to function."
        echo "Run in wizard mode: $0 --wizard"
        exit 1
    fi
    
    # Check sudo access if we'll need it
    if [[ "$NEED_SUDO" == "true" ]]; then
        if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
            echo -e "${YELLOW}⚠️  Instructions require system package installation but sudo access is limited${NC}"
            echo "You may be prompted for your password during installation."
        fi
    fi
    
    # Apply saved choices
    INSTALL_BASIC_DEPS="$saved_install_basic_deps"
    INSTALL_PYTHON="$saved_install_python"
    INSTALL_CLAMAV="$saved_install_clamav"
    CHECK_DEFENDER="$saved_check_defender"
    
    USER_INSTALL_BASIC_DEPS_CHOICE="$saved_install_basic_deps"
    USER_INSTALL_PYTHON_CHOICE="$saved_install_python"
    USER_INSTALL_CLAMAV_CHOICE="$saved_install_clamav"
    USER_CHECK_DEFENDER_CHOICE="$saved_check_defender"
    
    echo -e "${GREEN}✅ Using system dependency choices from instructions${NC}"
}

# Interactive system dependency selection (wizard mode)  
interactive_system_deps_choice() {
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
        read -p "Install ClamAV? (Default: No) [Y/n/x]: " choice
        case $choice in
            [Yy]) 
                INSTALL_CLAMAV=true
                ;;
            [Xx]) 
                echo "Installation cancelled by user."
                exit 0 
                ;;
            *) # Default is No
                INSTALL_CLAMAV=false
                echo -e "${YELLOW}⚠️  Skipping ClamAV - virus scanning will be limited to Microsoft Defender${NC}"
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
    
    # Track user choices for instructions file generation
    USER_INSTALL_BASIC_DEPS_CHOICE="$INSTALL_BASIC_DEPS"
    USER_INSTALL_PYTHON_CHOICE="$INSTALL_PYTHON"
    USER_INSTALL_CLAMAV_CHOICE="$INSTALL_CLAMAV" 
    USER_CHECK_DEFENDER_CHOICE="$CHECK_DEFENDER"
}

# 6. Unified System Dependencies Check and Installation
check_and_install_system_deps() {
    # Always detect current system state first
    detect_system_deps_state
    
    # Check if we're running from instructions or wizard mode
    if [[ -n "$INSTALL_INSTRUCTIONS_FILE" ]]; then
        # Instructions mode - validate saved choices against current state
        echo "Reading system dependency choices from instructions..."
        
        # TODO: Read saved choices from instructions file
        # For now, this is a placeholder - we'll implement file reading later
        echo "Instructions mode not yet implemented - falling back to wizard"
        interactive_system_deps_choice
    else
        # Wizard mode - interactive choice
        interactive_system_deps_choice
    fi
}

# Validate saved config path against current state
validate_config_path_instructions() {
    local saved_config_path="$1"
    
    # Basic path validation
    if [[ -z "$saved_config_path" ]]; then
        echo -e "${RED}❌ Empty config path in instructions${NC}"
        echo "Run in wizard mode: $0 --wizard"
        exit 1
    fi
    
    # Check if parent directory exists or can be created
    local parent_dir=$(dirname "$saved_config_path")
    if [[ ! -d "$parent_dir" ]]; then
        echo -e "${YELLOW}⚠️  Config directory doesn't exist: $parent_dir${NC}"
        echo ""
        echo "The configuration file directory from instructions doesn't exist."
        echo "This directory will be created during installation if needed."
        echo ""
    fi
    
    # Check write permissions for the directory
    if [[ -d "$parent_dir" ]] && [[ ! -w "$parent_dir" ]]; then
        echo -e "${YELLOW}⚠️  No write permission for config directory: $parent_dir${NC}"
        echo ""
        echo "You may need sudo access to write to this location during installation."
        echo ""
    fi
    
    # Apply the saved path
    CONFIG_PATH="$saved_config_path"
    USER_CONFIG_PATH_CHOICE="$saved_config_path"
    
    echo -e "${GREEN}✅ Using config path from instructions: $saved_config_path${NC}"
}

# Interactive config path collection (wizard mode)
interactive_config_path_choice() {
    echo "=== Configuration File Location ==="
    echo "Installation mode: $INSTALL_MODE"
    echo ""
    
    # Set up default config path based on installation mode
    case $INSTALL_MODE in
        "$INSTALL_MODE_DEV")
            DEFAULT_CONFIG="$PROJECT_ROOT/config/config.conf"
            ;;
        "$INSTALL_MODE_USER")
            DEFAULT_CONFIG="$HOME/.config/shuttle/config.conf"
            ;;
        "$INSTALL_MODE_SERVICE")
            DEFAULT_CONFIG="/etc/shuttle/config.conf"
            ;;
    esac
    
    echo "Configuration file location:"
    echo "Path where Shuttle's main configuration file will be stored."
    echo ""
    read -p "[$DEFAULT_CONFIG]: " CONFIG_PATH
    CONFIG_PATH=${CONFIG_PATH:-$DEFAULT_CONFIG}
    USER_CONFIG_PATH_CHOICE="$CONFIG_PATH"
    
    echo ""
    echo "Configuration file will be: $CONFIG_PATH"
    echo ""
}

# 4. Unified Configuration Path Collection
collect_config_path() {
    # Check if we're running from instructions or wizard mode
    if [[ -n "$INSTALL_INSTRUCTIONS_FILE" ]]; then
        # Instructions mode - validate saved path
        echo "Reading configuration path from instructions..."
        
        # TODO: Read saved path from instructions file
        # For now, this is a placeholder - we'll implement file reading later
        echo "Instructions mode not yet implemented - falling back to wizard"
        interactive_config_path_choice
    else
        # Wizard mode - interactive choice
        interactive_config_path_choice
    fi
}

# Validate saved environment paths against current state
validate_environment_paths_instructions() {
    local saved_venv_path="$1"
    local saved_test_work_dir="$2"
    
    # Validate venv path
    if [[ -z "$saved_venv_path" ]]; then
        echo -e "${RED}❌ Empty venv path in instructions${NC}"
        echo "Run in wizard mode: $0 --wizard"
        exit 1
    fi
    
    # Validate test work dir
    if [[ -z "$saved_test_work_dir" ]]; then
        echo -e "${RED}❌ Empty test work directory in instructions${NC}"
        echo "Run in wizard mode: $0 --wizard"
        exit 1
    fi
    
    # Check venv path parent directory
    local venv_parent=$(dirname "$saved_venv_path")
    if [[ ! -d "$venv_parent" ]]; then
        echo -e "${YELLOW}⚠️  Venv parent directory doesn't exist: $venv_parent${NC}"
        echo "This directory will be created during installation if needed."
    fi
    
    # Check test work dir parent directory
    local test_parent=$(dirname "$saved_test_work_dir")
    if [[ ! -d "$test_parent" ]]; then
        echo -e "${YELLOW}⚠️  Test work parent directory doesn't exist: $test_parent${NC}"
        echo "This directory will be created during installation if needed."
    fi
    
    # Apply saved paths
    VENV_PATH="$saved_venv_path"
    TEST_WORK_DIR="$saved_test_work_dir"
    USER_VENV_PATH_CHOICE="$saved_venv_path"
    USER_TEST_WORK_DIR_CHOICE="$saved_test_work_dir"
    
    # Derived paths
    CONFIG_DIR=$(dirname "$CONFIG_PATH")
    
    echo -e "${GREEN}✅ Using environment paths from instructions${NC}"
    echo "  Venv path: $VENV_PATH"
    echo "  Test work dir: $TEST_WORK_DIR"
}

# Interactive environment paths collection (wizard mode)
interactive_environment_paths_choice() {
    echo "=== Environment Variables Setup ==="
    echo ""
    
    # Set up default paths based on installation mode (config path already set)
    case $INSTALL_MODE in
        "$INSTALL_MODE_DEV")
            DEFAULT_VENV="$PROJECT_ROOT/.venv"
            DEFAULT_TEST_WORK="$PROJECT_ROOT/test_area"
            ;;
        "$INSTALL_MODE_USER")
            DEFAULT_VENV="$HOME/.local/share/shuttle/venv"
            DEFAULT_TEST_WORK="$HOME/.local/share/shuttle/test_area"
            ;;
        "$INSTALL_MODE_SERVICE")
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
    USER_VENV_PATH_CHOICE="$VENV_PATH"
    echo ""
    
    echo "Test working directory:"
    echo "Directory used by automated tests for temporary file operations."
    echo ""
    read -p "[$DEFAULT_TEST_WORK]: " TEST_WORK_DIR
    TEST_WORK_DIR=${TEST_WORK_DIR:-$DEFAULT_TEST_WORK}
    USER_TEST_WORK_DIR_CHOICE="$TEST_WORK_DIR"
    
    # Derived paths
    CONFIG_DIR=$(dirname "$CONFIG_PATH")
    
    echo ""
    echo "Environment variables set:"
    echo "  SHUTTLE_CONFIG_PATH=$CONFIG_PATH"
    echo "  SHUTTLE_TEST_WORK_DIR=$TEST_WORK_DIR"
    echo ""
}

# 7. Unified Environment Variables Collection
collect_environment_variables() {
    # Check if we're running from instructions or wizard mode
    if [[ -n "$INSTALL_INSTRUCTIONS_FILE" ]]; then
        # Instructions mode - validate saved paths
        echo "Reading environment paths from instructions..."
        
        # TODO: Read saved paths from instructions file
        # For now, this is a placeholder - we'll implement file reading later
        echo "Instructions mode not yet implemented - falling back to wizard"
        interactive_environment_paths_choice
    else
        # Wizard mode - interactive choice
        interactive_environment_paths_choice
    fi
}

# 6. Configuration Parameters Collection
collect_config_parameters() {
    echo "=== Configuration Parameters ==="
    echo ""
    
    # Set defaults based on installation mode (using constants)
    case $INSTALL_MODE in
        "$INSTALL_MODE_DEV")
            DEFAULT_SOURCE="$PROJECT_ROOT/work/incoming"
            DEFAULT_DEST="$PROJECT_ROOT/work/processed"
            DEFAULT_QUARANTINE="$PROJECT_ROOT/work/quarantine"
            DEFAULT_LOG="$PROJECT_ROOT/work/logs"
            DEFAULT_HAZARD="$PROJECT_ROOT/work/hazard"
            DEFAULT_THREADS=1
            DEFAULT_LOG_LEVEL="$LOG_LEVEL_DEBUG"
            DEFAULT_CLAMAV="n"
            DEFAULT_DEFENDER="Y"
            ;;
        "$INSTALL_MODE_USER")
            DEFAULT_SOURCE="$HOME/shuttle/incoming"
            DEFAULT_DEST="$HOME/shuttle/processed"
            DEFAULT_QUARANTINE="/tmp/shuttle/quarantine"
            DEFAULT_LOG="$HOME/shuttle/logs"
            DEFAULT_HAZARD="$HOME/shuttle/hazard"
            DEFAULT_THREADS=1
            DEFAULT_LOG_LEVEL="$LOG_LEVEL_INFO"
            DEFAULT_CLAMAV="n"
            DEFAULT_DEFENDER="Y"
            ;;
        "$INSTALL_MODE_SERVICE")
            DEFAULT_SOURCE="/srv/data/incoming"
            DEFAULT_DEST="/srv/data/processed"
            DEFAULT_QUARANTINE="/tmp/shuttle/quarantine"
            DEFAULT_LOG="/var/log/shuttle"
            DEFAULT_HAZARD="/srv/data/hazard"
            DEFAULT_THREADS=1
            DEFAULT_LOG_LEVEL="$LOG_LEVEL_INFO"
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
    
    # Track user choices for instructions file generation
    USER_SOURCE_PATH_CHOICE="$SOURCE_PATH"
    USER_DEST_PATH_CHOICE="$DEST_PATH"
    USER_QUARANTINE_PATH_CHOICE="$QUARANTINE_PATH"
    USER_LOG_PATH_CHOICE="$LOG_PATH"
    USER_HAZARD_PATH_CHOICE="$HAZARD_PATH"
    USER_USE_CLAMAV_CHOICE="$USE_CLAMAV"
    USER_USE_DEFENDER_CHOICE="$USE_DEFENDER"
    USER_SCAN_THREADS_CHOICE="$SCAN_THREADS"
    USER_MIN_FREE_SPACE_CHOICE="$MIN_FREE_SPACE"
    USER_LOG_LEVEL_CHOICE="$LOG_LEVEL"
    USER_ADMIN_EMAIL_CHOICE="$ADMIN_EMAIL"
    USER_SMTP_SERVER_CHOICE="$SMTP_SERVER"
    USER_SMTP_PORT_CHOICE="$SMTP_PORT"
    USER_SMTP_USERNAME_CHOICE="$SMTP_USERNAME"
    USER_SMTP_PASSWORD_CHOICE="$SMTP_PASSWORD"
    USER_USE_TLS_CHOICE="$USE_TLS"
    USER_DELETE_SOURCE_CHOICE="$DELETE_SOURCE"
    USER_LEDGER_PATH_CHOICE="$LEDGER_PATH"
}

# 8. Execute Installation
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
                echo -e "   ${BLUE}pip install -r scripts/1_installation_steps/requirements.txt${NC}"
                ;;
            "script")
                echo "   - Activate the virtual environment first:"
                echo -e "   ${BLUE}source $VENV_PATH/bin/activate${NC}"
                echo -e "   ${BLUE}pip install -r scripts/1_installation_steps/requirements.txt${NC}"
                ;;
            "global")
                echo "   - Installing globally:"
                echo -e "   ${BLUE}pip install -r scripts/1_installation_steps/requirements.txt${NC}"
                ;;
        esac
        
        echo ""
        echo "3. Install Shuttle modules:"
        if [[ "$INSTALL_MODE" == "dev" ]]; then
            echo -e "   ${BLUE}./scripts/1_installation_steps/08_install_shared.sh -e${NC}"
            echo -e "   ${BLUE}./scripts/1_installation_steps/09_install_defender_test.sh -e${NC}"
            echo -e "   ${BLUE}./scripts/1_installation_steps/10_install_shuttle.sh -e${NC}"
        else
            echo -e "   ${BLUE}./scripts/1_installation_steps/08_install_shared.sh${NC}"
            echo -e "   ${BLUE}./scripts/1_installation_steps/09_install_defender_test.sh${NC}"
            echo -e "   ${BLUE}./scripts/1_installation_steps/10_install_shuttle.sh${NC}"
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

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [options]

Options:
  --instructions <file> Path to YAML installation instructions file (default: wizard mode)
  --wizard              Run installation wizard (default when no options provided)
  --help               Show this help message

Examples:
  $0                                    # Interactive wizard mode (default)
  $0 --wizard                          # Explicit wizard mode
  $0 --instructions install_instructions.yaml   # Use saved installation instructions

Installation Instructions File:
  The YAML file defines installation settings including paths, environment,
  and system dependencies for reproducible installations.
EOF
}

# Parse command line arguments
parse_arguments() {
    INSTALL_INSTRUCTIONS_FILE=""
    RUN_WIZARD=false
    local INSTALL_INSTRUCTIONS_SPECIFIED=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --instructions)
                INSTALL_INSTRUCTIONS_FILE="$2"
                INSTALL_INSTRUCTIONS_SPECIFIED=true
                shift 2
                ;;
            --wizard)
                RUN_WIZARD=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Unknown option: $1${NC}" >&2
                show_usage
                exit 1
                ;;
        esac
    done
    
    # If no --instructions specified and no --wizard, default to wizard
    if [[ "$INSTALL_INSTRUCTIONS_SPECIFIED" == "false" && "$RUN_WIZARD" == "false" ]]; then
        RUN_WIZARD=true
    fi
}

# Main function
main() {
    # Load installation constants first
    if ! load_installation_constants_for_install; then
        echo "Failed to initialize installation system" >&2
        exit 1
    fi
    
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

# Parse arguments and run main function
parse_arguments "$@"
main