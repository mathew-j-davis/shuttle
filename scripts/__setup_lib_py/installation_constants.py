"""
Installation Constants

Central definition of all choice values, types, and mappings used throughout
the installation process. This serves as the single source of truth for:
- Virtual environment choices and types
- Installation modes
- Log levels
- System dependency choices
- Other installation configuration constants

Used by both Python modules (YAML generation, validation) and shell scripts
(interactive prompts, argument parsing).
"""

class InstallationConstants:
    """Container for all installation-related constants"""
    
    class Venv:
        """Virtual environment choices and types"""
        # User choices (saved in instructions)
        CHOICE_EXISTING = "existing"
        CHOICE_SCRIPT_CREATES = "script_creates"
        CHOICE_GLOBAL = "global"
        
        # Internal types (used by shell variables)
        TYPE_EXISTING = "existing"
        TYPE_SCRIPT = "script"
        TYPE_GLOBAL = "global"
        
        # Mapping between choices and types
        CHOICE_TO_TYPE = {
            CHOICE_EXISTING: TYPE_EXISTING,
            CHOICE_SCRIPT_CREATES: TYPE_SCRIPT,
            CHOICE_GLOBAL: TYPE_GLOBAL,
        }
        
        TYPE_TO_CHOICE = {v: k for k, v in CHOICE_TO_TYPE.items()}
    
    class InstallMode:
        """Installation mode choices"""
        DEV = "dev"
        USER = "user"
        SERVICE = "service"
        
        # Environment flags
        ENV_FLAGS = {
            DEV: "-e",
            USER: "-u",
            SERVICE: "",
        }
    
    class LogLevel:
        """Log level choices"""
        DEBUG = "DEBUG"
        INFO = "INFO"
        WARNING = "WARNING"
        ERROR = "ERROR"
        CRITICAL = "CRITICAL"
        
        # Mapping for interactive prompts
        CHOICES = [DEBUG, INFO, WARNING, ERROR, CRITICAL]
        CHOICE_TO_NUMBER = {level: i+1 for i, level in enumerate(CHOICES)}
        NUMBER_TO_CHOICE = {v: k for k, v in CHOICE_TO_NUMBER.items()}
    
    class SystemDeps:
        """System dependency installation choices"""
        # Boolean choices for system dependencies
        INSTALL_BASIC_DEPS = "install_basic_deps"
        INSTALL_PYTHON = "install_python"
        INSTALL_CLAMAV = "install_clamav"
        CHECK_DEFENDER = "check_defender"
        
        # Scanner choices
        USE_CLAMAV = "use_clamav"
        USE_DEFENDER = "use_defender"
    
    class FileProcessing:
        """File processing option choices"""
        DELETE_SOURCE = "delete_source"
        
        # Boolean choice mappings
        BOOLEAN_CHOICES = {
            "Y": True,
            "y": True,
            "N": False,
            "n": False,
        }
    
    class UserChoiceTracking:
        """Variable names for tracking user choices (for instructions file generation)"""
        # These are the variable names we set to track user choices
        VENV_CHOICE = "USER_VENV_CHOICE"
        VENV_EXPECTED_ACTIVE = "EXPECTED_VENV_ACTIVE"
        INSTALL_MODE_CHOICE = "USER_INSTALL_MODE_CHOICE"
        CONFIG_PATH_CHOICE = "USER_CONFIG_PATH_CHOICE"
        VENV_PATH_CHOICE = "USER_VENV_PATH_CHOICE"
        TEST_WORK_DIR_CHOICE = "USER_TEST_WORK_DIR_CHOICE"
        REGISTER_KERNEL_CHOICE = "USER_REGISTER_KERNEL_CHOICE"
        GPG_KEY_PATH_CHOICE = "USER_GPG_KEY_PATH_CHOICE"
        INSTALL_BASIC_DEPS_CHOICE = "USER_INSTALL_BASIC_DEPS_CHOICE"
        INSTALL_PYTHON_CHOICE = "USER_INSTALL_PYTHON_CHOICE"
        INSTALL_CLAMAV_CHOICE = "USER_INSTALL_CLAMAV_CHOICE"
        CHECK_DEFENDER_CHOICE = "USER_CHECK_DEFENDER_CHOICE"
        # Config parameters choices
        SOURCE_PATH_CHOICE = "USER_SOURCE_PATH_CHOICE"
        DEST_PATH_CHOICE = "USER_DEST_PATH_CHOICE"
        QUARANTINE_PATH_CHOICE = "USER_QUARANTINE_PATH_CHOICE"
        LOG_PATH_CHOICE = "USER_LOG_PATH_CHOICE"
        HAZARD_PATH_CHOICE = "USER_HAZARD_PATH_CHOICE"
        USE_CLAMAV_CHOICE = "USER_USE_CLAMAV_CHOICE"
        USE_DEFENDER_CHOICE = "USER_USE_DEFENDER_CHOICE"
        SCAN_THREADS_CHOICE = "USER_SCAN_THREADS_CHOICE"
        MIN_FREE_SPACE_CHOICE = "USER_MIN_FREE_SPACE_CHOICE"
        LOG_LEVEL_CHOICE = "USER_LOG_LEVEL_CHOICE"
        ADMIN_EMAIL_CHOICE = "USER_ADMIN_EMAIL_CHOICE"
        SMTP_SERVER_CHOICE = "USER_SMTP_SERVER_CHOICE"
        SMTP_PORT_CHOICE = "USER_SMTP_PORT_CHOICE"
        SMTP_USERNAME_CHOICE = "USER_SMTP_USERNAME_CHOICE"
        SMTP_PASSWORD_CHOICE = "USER_SMTP_PASSWORD_CHOICE"
        USE_TLS_CHOICE = "USER_USE_TLS_CHOICE"
        DELETE_SOURCE_CHOICE = "USER_DELETE_SOURCE_CHOICE"
        LEDGER_PATH_CHOICE = "USER_LEDGER_PATH_CHOICE"

# Helper functions for easy access
def get_venv_type_from_choice(choice):
    """Convert user choice to internal venv type"""
    return InstallationConstants.Venv.CHOICE_TO_TYPE.get(choice, "unknown")

def get_venv_choice_from_type(venv_type):
    """Convert internal venv type to user choice"""
    return InstallationConstants.Venv.TYPE_TO_CHOICE.get(venv_type, "unknown")

def get_log_level_from_number(number):
    """Convert numeric choice to log level name"""
    try:
        num = int(number)
        return InstallationConstants.LogLevel.NUMBER_TO_CHOICE.get(num, "INFO")
    except (ValueError, TypeError):
        return "INFO"

def get_log_level_number(level):
    """Convert log level name to numeric choice"""
    return InstallationConstants.LogLevel.CHOICE_TO_NUMBER.get(level, 2)

def get_env_flag_for_mode(install_mode):
    """Get environment flag for installation mode"""
    return InstallationConstants.InstallMode.ENV_FLAGS.get(install_mode, "")

# Validation functions
def is_valid_venv_choice(choice):
    """Check if venv choice is valid"""
    return choice in InstallationConstants.Venv.CHOICE_TO_TYPE

def is_valid_install_mode(mode):
    """Check if installation mode is valid"""
    return mode in [InstallationConstants.InstallMode.DEV, 
                   InstallationConstants.InstallMode.USER, 
                   InstallationConstants.InstallMode.SERVICE]

def is_valid_log_level(level):
    """Check if log level is valid"""
    return level in InstallationConstants.LogLevel.CHOICES

if __name__ == "__main__":
    # Test/demo the constants
    print("Virtual Environment Constants:")
    print(f"  Choices: {list(InstallationConstants.Venv.CHOICE_TO_TYPE.keys())}")
    print(f"  Types: {list(InstallationConstants.Venv.TYPE_TO_CHOICE.keys())}")
    print()
    
    print("Installation Mode Constants:")
    modes = [InstallationConstants.InstallMode.DEV, 
            InstallationConstants.InstallMode.USER, 
            InstallationConstants.InstallMode.SERVICE]
    for mode in modes:
        flag = get_env_flag_for_mode(mode)
        print(f"  {mode}: {flag if flag else '(no flag)'}")
    print()
    
    print("Log Level Constants:")
    for i, level in enumerate(InstallationConstants.LogLevel.CHOICES, 1):
        print(f"  {i}) {level}")