"""
Installation Instructions Reader

Reads YAML installation instructions files and validates their contents.
Only reads user choices and explicit paths - all derived paths should be
calculated by the installation logic, not stored in instructions.
"""

import yaml
import sys
from pathlib import Path
from installation_constants import InstallationConstants, is_valid_venv_choice, is_valid_install_mode

class InstructionsValidationError(Exception):
    """Raised when installation instructions are invalid"""
    pass

class InstallationInstructionsReader:
    """Reads and validates installation instructions from YAML files"""
    
    def __init__(self, instructions_file_path):
        """
        Initialize reader with path to instructions file
        
        Args:
            instructions_file_path: Path to YAML instructions file
        """
        self.instructions_file_path = Path(instructions_file_path)
        self.instructions = None
    
    def read_instructions(self):
        """
        Read and parse the instructions file
        
        Returns:
            dict: Parsed instructions
            
        Raises:
            InstructionsValidationError: If file cannot be read or parsed
        """
        try:
            if not self.instructions_file_path.exists():
                raise InstructionsValidationError(f"Instructions file not found: {self.instructions_file_path}")
            
            with open(self.instructions_file_path, 'r') as f:
                self.instructions = yaml.safe_load(f)
            
            if not self.instructions:
                raise InstructionsValidationError("Instructions file is empty or invalid YAML")
            
            self._validate_structure()
            return self.instructions
            
        except yaml.YAMLError as e:
            raise InstructionsValidationError(f"Invalid YAML in instructions file: {e}")
        except Exception as e:
            raise InstructionsValidationError(f"Error reading instructions file: {e}")
    
    def _validate_structure(self):
        """Validate the structure and content of instructions"""
        if not isinstance(self.instructions, dict):
            raise InstructionsValidationError("Instructions must be a YAML dictionary")
        
        # Check required top-level sections
        required_sections = ['installation', 'paths']
        for section in required_sections:
            if section not in self.instructions:
                raise InstructionsValidationError(f"Missing required section: {section}")
        
        # Check optional sections
        optional_sections = ['directory_creation']
        # directory_creation section is optional for backward compatibility
        
        self._validate_installation_section()
        self._validate_paths_section()
        
        # Validate optional sections if present
        if 'directory_creation' in self.instructions:
            self._validate_directory_creation_section()
    
    def _validate_installation_section(self):
        """Validate the installation choices section"""
        installation = self.instructions['installation']
        
        if not isinstance(installation, dict):
            raise InstructionsValidationError("Installation section must be a dictionary")
        
        # Validate venv_choice
        venv_choice = installation.get('venv_choice')
        if not venv_choice or not is_valid_venv_choice(venv_choice):
            valid_choices = list(InstallationConstants.Venv.CHOICE_TO_TYPE.keys())
            raise InstructionsValidationError(f"Invalid venv_choice: {venv_choice}. Must be one of: {valid_choices}")
        
        # Validate install_mode
        install_mode = installation.get('install_mode')
        if not install_mode or not is_valid_install_mode(install_mode):
            valid_modes = [InstallationConstants.InstallMode.DEV, 
                          InstallationConstants.InstallMode.USER, 
                          InstallationConstants.InstallMode.SERVICE]
            raise InstructionsValidationError(f"Invalid install_mode: {install_mode}. Must be one of: {valid_modes}")
        
        # Validate boolean fields
        boolean_fields = ['register_jupyter_kernel', 'install_basic_deps', 'install_python', 
                         'install_clamav', 'check_defender']
        for field in boolean_fields:
            value = installation.get(field)
            if value is not None and not isinstance(value, bool):
                raise InstructionsValidationError(f"Field '{field}' must be true or false, got: {value}")
    
    def _validate_paths_section(self):
        """Validate the paths section"""
        paths = self.instructions['paths']
        
        if not isinstance(paths, dict):
            raise InstructionsValidationError("Paths section must be a dictionary")
        
        # Validate required paths
        required_paths = ['config_path', 'test_work_dir']
        for path_key in required_paths:
            path_value = paths.get(path_key)
            if not path_value:
                raise InstructionsValidationError(f"Missing required path: {path_key}")
            
            if not isinstance(path_value, str):
                raise InstructionsValidationError(f"Path '{path_key}' must be a string, got: {type(path_value)}")
            
            if not path_value.strip():
                raise InstructionsValidationError(f"Path '{path_key}' cannot be empty")
    
    def _validate_directory_creation_section(self):
        """Validate the directory creation section"""
        directory_creation = self.instructions['directory_creation']
        
        if not isinstance(directory_creation, dict):
            raise InstructionsValidationError("Directory creation section must be a dictionary")
        
        # Validate boolean fields for directory creation
        directory_fields = ['create_source_dir', 'create_dest_dir', 'create_quarantine_dir', 
                           'create_log_dir', 'create_hazard_dir']
        for field in directory_fields:
            value = directory_creation.get(field)
            if value is not None and not isinstance(value, bool):
                raise InstructionsValidationError(f"Directory creation field '{field}' must be true or false, got: {value}")
    
    def get_installation_choices(self):
        """
        Get installation choices as a dictionary
        
        Returns:
            dict: Installation choices with defaults for missing values
        """
        if not self.instructions:
            raise InstructionsValidationError("Instructions not loaded. Call read_instructions() first.")
        
        installation = self.instructions['installation']
        
        # Return with defaults for any missing boolean values
        return {
            'venv_choice': installation['venv_choice'],
            'install_mode': installation['install_mode'],
            'register_jupyter_kernel': installation.get('register_jupyter_kernel', False),
            'install_basic_deps': installation.get('install_basic_deps', False),
            'install_python': installation.get('install_python', False),
            'install_clamav': installation.get('install_clamav', False),
            'check_defender': installation.get('check_defender', True),
        }
    
    def get_user_paths(self):
        """
        Get user-specified paths
        
        Returns:
            dict: User-specified paths
        """
        if not self.instructions:
            raise InstructionsValidationError("Instructions not loaded. Call read_instructions() first.")
        
        return {
            'config_path': self.instructions['paths']['config_path'],
            'test_work_dir': self.instructions['paths']['test_work_dir'],
        }
    
    def get_directory_creation_choices(self):
        """
        Get directory creation choices
        
        Returns:
            dict: Directory creation choices with defaults for missing values
        """
        if not self.instructions:
            raise InstructionsValidationError("Instructions not loaded. Call read_instructions() first.")
        
        # Get directory creation section, with defaults if section doesn't exist (backward compatibility)
        directory_creation = self.instructions.get('directory_creation', {})
        
        return {
            'create_source_dir': directory_creation.get('create_source_dir', True),
            'create_dest_dir': directory_creation.get('create_dest_dir', True),
            'create_quarantine_dir': directory_creation.get('create_quarantine_dir', True),
            'create_log_dir': directory_creation.get('create_log_dir', True),
            'create_hazard_dir': directory_creation.get('create_hazard_dir', True),
        }


def read_installation_instructions(instructions_file_path):
    """
    Convenience function to read installation instructions
    
    Args:
        instructions_file_path: Path to instructions file
        
    Returns:
        tuple: (installation_choices, user_paths, directory_choices)
        
    Raises:
        InstructionsValidationError: If instructions are invalid
    """
    reader = InstallationInstructionsReader(instructions_file_path)
    reader.read_instructions()
    
    installation_choices = reader.get_installation_choices()
    user_paths = reader.get_user_paths()
    directory_choices = reader.get_directory_creation_choices()
    
    return installation_choices, user_paths, directory_choices


if __name__ == "__main__":
    # Command line usage for testing
    if len(sys.argv) != 2:
        print("Usage: python3 installation_instructions_reader.py <instructions_file>")
        sys.exit(1)
    
    try:
        choices, paths, directory_choices = read_installation_instructions(sys.argv[1])
        print("Installation Choices:")
        for key, value in choices.items():
            print(f"  {key}: {value}")
        print("\nUser Paths:")
        for key, value in paths.items():
            print(f"  {key}: {value}")
        print("\nDirectory Creation Choices:")
        for key, value in directory_choices.items():
            print(f"  {key}: {value}")
    except InstructionsValidationError as e:
        print(f"Error: {e}")
        sys.exit(1)