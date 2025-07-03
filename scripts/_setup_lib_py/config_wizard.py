#!/usr/bin/env python3
"""
Configuration Wizard Entry Point
Refactored modular configuration wizard

This is the main entry point that orchestrates the refactored modules:
- config_wizard_core: Core state and configuration management
- config_wizard_ui: User interface and menu system
- config_wizard_validation: Configuration validation
- config_wizard_groups: Group management
- config_wizard_users: User management (to be created)
- config_wizard_paths: Path management (to be created)
- config_wizard_templates: Template handling (to be created)  
- config_wizard_modes: Mode-specific logic (to be created)
"""

import sys
import argparse
from config_wizard_core import ConfigWizardCore
from config_wizard_ui import ConfigWizardUI
from config_wizard_validation import ConfigWizardValidation
from config_wizard_groups import ConfigWizardGroups

class ConfigWizard(ConfigWizardCore, ConfigWizardUI, ConfigWizardValidation, ConfigWizardGroups):
    """
    Main configuration wizard class that inherits from all modules
    
    This class uses multiple inheritance to combine functionality from:
    - ConfigWizardCore: Core state management and YAML generation
    - ConfigWizardUI: User interface and menu systems
    - ConfigWizardValidation: Configuration validation
    - ConfigWizardGroups: Group management functionality
    
    Additional modules will be added as they are created:
    - ConfigWizardUsers: User management
    - ConfigWizardPaths: Path permission management
    - ConfigWizardTemplates: Template handling
    - ConfigWizardModes: Mode-specific workflows
    """
    
    def __init__(self, shuttle_config_path=None, test_work_dir=None, test_config_path=None):
        """Initialize the wizard with all module functionality"""
        # Initialize core functionality (this calls parent __init__)
        ConfigWizardCore.__init__(self, shuttle_config_path, test_work_dir, test_config_path)
        
        # Other modules don't need explicit initialization as they only provide methods
        
    def run(self):
        """Main wizard execution - orchestrates the entire configuration process"""
        print(self._wrap_title("Shuttle Configuration Wizard"))
        print("Creating YAML configuration for post-installation setup")
        print()
        
        # Show current state
        summary = self.get_state_summary()
        print(f"Loaded shuttle config: {summary['shuttle_config_path']}")
        print(f"Found {summary['shuttle_paths_count']} shuttle paths")
        
        # For now, demonstrate group management (as that module is complete)
        # Full wizard would include mode selection, users, paths, etc.
        print("\n🚀 Starting with Group Configuration (Demo)")
        self._configure_groups()
        
        # Save configuration
        print(f"\n{self._wrap_title('Save Configuration')}")
        if self._confirm("Save the current configuration?"):
            config_file = self._save_configuration()
            print(f"✅ Configuration saved successfully!")
            print(f"Use this file with: ./scripts/2_post_install_config.sh --instructions {config_file}")
            return 0
        else:
            print("Configuration not saved.")
            return 2

def main():
    """Main entry point for the configuration wizard"""
    parser = argparse.ArgumentParser(description='Shuttle Configuration Wizard')
    parser.add_argument('--shuttle-config-path', 
                       help='Path to shuttle configuration file')
    parser.add_argument('--test-work-dir', 
                       help='Test working directory path')
    parser.add_argument('--test-config-path', 
                       help='Test configuration file path')
    
    args = parser.parse_args()
    
    try:
        wizard = ConfigWizard(
            shuttle_config_path=args.shuttle_config_path,
            test_work_dir=args.test_work_dir,
            test_config_path=args.test_config_path
        )
        
        return wizard.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Configuration wizard interrupted by user")
        return 3
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())