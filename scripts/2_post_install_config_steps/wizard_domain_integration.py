#!/usr/bin/env python3

"""
Domain User Integration for Shuttle Configuration Wizard
Extends the existing wizard with domain user validation and configuration flows
"""

import os
import sys
from pathlib import Path

# Import the domain validation logic
from wizard_domain_validation import (
    WizardDomainUserValidator, 
    DomainConfigurationHelper,
    ValidationResult,
    get_input, 
    get_yes_no, 
    get_choice
)


class WizardDomainIntegration:
    """Integrates domain user functionality into the wizard"""
    
    def __init__(self, config):
        self.config = config
        self.validator = WizardDomainUserValidator(config)
        self.helper = DomainConfigurationHelper(config)
    
    def validate_and_configure_domain_users(self):
        """Main entry point for domain user validation and configuration"""
        
        print("\n🔍 Checking for domain user requirements...")
        
        validation_result = self.validator.validate_domain_user_requirements()
        
        if not validation_result.valid:
            return self._handle_validation_failure(validation_result)
        elif self.validator.has_domain_users:
            print("✅ Domain users detected and configuration is valid")
            return True
        else:
            print("ℹ️  No domain users detected")
            return True
    
    def _handle_validation_failure(self, validation_result: ValidationResult):
        """Handle validation failures with user guidance"""
        
        print(f"\n⚠️  {validation_result.message}")
        
        if validation_result.error_type == "DOMAIN_CONFIG_MISSING":
            return self._handle_missing_domain_config()
        elif validation_result.error_type == "DOMAIN_CONFIG_INVALID":
            return self._handle_invalid_domain_config()
        
        return False
    
    def _handle_missing_domain_config(self):
        """Handle missing domain configuration"""
        
        domain_users = self.validator.get_domain_users()
        
        print("\nYou have configured domain users but no domain import configuration exists:")
        for user in domain_users:
            print(f"   • {user}")
        
        print("\nDomain users will not be importable without proper configuration.")
        
        choice = get_choice(
            "How would you like to handle domain user import?",
            [
                ("existing", "Use existing domain configuration file"),
                ("create", "Create new domain configuration template"),
                ("skip", "Skip domain configuration (users won't be importable)"),
                ("remove", "Remove domain users from configuration")
            ],
            default="create"
        )
        
        if choice == "existing":
            return self._configure_existing_domain_config()
        elif choice == "create":
            return self._create_domain_config_template()
        elif choice == "skip":
            return self._warn_about_skipped_domain_config()
        elif choice == "remove":
            return self._remove_domain_users_from_config()
        
        return False
    
    def _handle_invalid_domain_config(self):
        """Handle invalid domain configuration"""
        
        print(f"\nDomain configuration file exists but is invalid: {self.validator.domain_config_path}")
        print("The file exists but doesn't contain a valid 'command' configuration,")
        print("or it still contains the 'cat' placeholder.")
        
        choice = get_choice(
            "How would you like to fix the domain configuration?",
            [
                ("edit", "I'll edit the existing file manually"),
                ("recreate", "Create a new template to replace it"),
                ("skip", "Skip domain configuration for now")
            ],
            default="edit"
        )
        
        if choice == "edit":
            print(f"\n📝 Please edit the domain configuration file:")
            print(f"   {self.validator.domain_config_path}")
            print("\n   Replace 'cat' with your actual domain import command")
            print("   Example: command=sudo /opt/corporate/bin/import-domain-user")
            
            if get_yes_no("\nHave you finished editing the configuration file?"):
                # Re-validate
                if self.validator._validate_domain_config_file(self.validator.domain_config_path):
                    print("✅ Domain configuration is now valid")
                    return True
                else:
                    print("❌ Configuration is still invalid")
                    return False
            else:
                print("⚠️  Domain configuration remains invalid")
                return False
        
        elif choice == "recreate":
            return self._create_domain_config_template()
        
        elif choice == "skip":
            return self._warn_about_skipped_domain_config()
        
        return False
    
    def _configure_existing_domain_config(self):
        """Configure existing domain configuration"""
        
        config_path = get_input(
            "Enter path to existing domain configuration file",
            default="/etc/shuttle/domain_import.conf",
            validator=lambda p: None if os.path.exists(p) else "File does not exist"
        )
        
        # Validate the config file
        if self.validator._validate_domain_config_file(config_path):
            # Update config to reference this file
            if hasattr(self.config, 'domain_import_config_path'):
                self.config.domain_import_config_path = config_path
            else:
                setattr(self.config, 'domain_import_config_path', config_path)
            
            print(f"✅ Using domain configuration: {config_path}")
            
            # Test the configuration
            if get_yes_no("Would you like to test the domain configuration?"):
                success = self.helper.test_domain_configuration(config_path)
                return success
            
            return True
        else:
            print(f"❌ Invalid domain configuration file: {config_path}")
            print("The file exists but doesn't contain a valid 'command' configuration.")
            
            if get_yes_no("Would you like to create a new template instead?"):
                return self._create_domain_config_template()
            
            return False
    
    def _create_domain_config_template(self):
        """Create domain configuration template"""
        
        print("\n📝 Creating domain import configuration template...")
        
        config_dir = getattr(self.config, 'config_base_path', '/etc/shuttle')
        
        # Ask user if they want interactive setup or just a template
        use_interactive = get_yes_no(
            "Would you like interactive configuration setup?",
            default=True
        )
        
        try:
            if use_interactive:
                config_path = self.helper.generate_domain_config_interactive(config_dir)
            else:
                config_path = self.helper.create_domain_config_template(config_dir)
            
            # Update config to reference this file
            if hasattr(self.config, 'domain_import_config_path'):
                self.config.domain_import_config_path = config_path
            else:
                setattr(self.config, 'domain_import_config_path', config_path)
            
            print(f"✅ Created domain configuration template: {config_path}")
            print(f"⚠️  IMPORTANT: You must edit this file before domain users can be imported!")
            
            if not use_interactive:
                print(f"   The template uses 'cat' as a placeholder - replace with your actual command.")
            
            # Offer to test the configuration
            if get_yes_no("Would you like to test the domain configuration template?"):
                success = self.helper.test_domain_configuration(config_path)
                if success:
                    print("✅ Template test passed - argument construction is working")
                else:
                    print("❌ Template test failed - check the configuration")
                
                return success
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to create domain configuration: {e}")
            return False
    
    def _warn_about_skipped_domain_config(self):
        """Warn user about consequences of skipping domain config"""
        
        print("\n⚠️  Skipping domain configuration:")
        print("   • Domain users will be listed in installation instructions")
        print("   • Domain user import commands will be included")
        print("   • But imports will fail until domain configuration is set up")
        print("   • You can configure domain import later using:")
        print("     ./scripts/2_post_install_config_steps/12_users_and_groups.sh generate-domain-config")
        
        return True  # Allow wizard to continue
    
    def _remove_domain_users_from_config(self):
        """Remove domain users from configuration"""
        
        if not hasattr(self.config, 'users') or not hasattr(self.config.users, 'users_to_create'):
            print("❌ No users configuration found")
            return False
        
        original_count = len(self.config.users.users_to_create)
        
        # Filter out domain users
        self.config.users.users_to_create = [
            user for user in self.config.users.users_to_create
            if not self.validator._is_domain_user(
                user.username if hasattr(user, 'username') else str(user)
            )
        ]
        
        removed_count = original_count - len(self.config.users.users_to_create)
        print(f"✅ Removed {removed_count} domain users from configuration")
        
        if removed_count > 0:
            print("   Domain users can be added later using domain import commands")
        
        return True
    
    def generate_domain_user_instructions(self) -> str:
        """Generate domain user specific installation instructions"""
        
        if not self.validator.has_domain_users:
            return ""
        
        domain_users = self.validator.get_domain_users()
        config_path = getattr(self.config, 'domain_import_config_path', None)
        
        if config_path and os.path.exists(config_path):
            # Configuration exists - provide import commands
            instructions = f"""
## Domain User Import

The following domain users are configured and ready to import:
{chr(10).join(f"• {user}" for user in domain_users)}

Domain configuration: {config_path}

### Import Commands
```bash
# Test domain configuration first
cd /path/to/shuttle
{config_path.replace(os.path.dirname(config_path), '.')}/test_domain_import.sh --verbose

# Import all configured domain users
{chr(10).join(f'./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user --username {user} --command-config {config_path}' for user in domain_users)}
```

### Verify Domain Users
```bash
# Check if domain users were imported successfully
{chr(10).join(f'id {user}' for user in domain_users)}
```

### Force Re-import (if needed)
```bash
# Re-import existing users (updates groups, etc.)
{chr(10).join(f'./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user --username {user} --command-config {config_path} --force' for user in domain_users)}
```
"""
        else:
            # No configuration - provide setup instructions
            config_dir = getattr(self.config, 'config_base_path', '/etc/shuttle')
            instructions = f"""
## ⚠️ Domain User Configuration Required

The following domain users are configured but cannot be imported without domain configuration:
{chr(10).join(f"• {user}" for user in domain_users)}

### Required Setup Steps

1. **Configure domain import** (choose one option):

   **Option A: Use generated template**
   ```bash
   # Edit the generated template (if it exists)
   vim {config_dir}/domain_import.conf
   
   # Replace 'cat' with your actual domain import command
   # Example: command=sudo /opt/corporate/bin/import-domain-user
   ```

   **Option B: Create new configuration**
   ```bash
   # Generate new configuration interactively
   cd /path/to/shuttle
   ./scripts/2_post_install_config_steps/12_users_and_groups.sh generate-domain-config \\
     --output-dir {config_dir} --interactive
   ```

2. **Test domain configuration**:
   ```bash
   cd /path/to/shuttle
   ./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \\
     --username {domain_users[0]} --command-config {config_dir}/domain_import.conf \\
     --dry-run --verbose
   ```

3. **Import domain users**:
   ```bash
   # Import all configured domain users
   {chr(10).join(f'./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user --username {user} --command-config {config_dir}/domain_import.conf' for user in domain_users)}
   ```

### ⚠️ Important Notes
- Domain user import will fail until configuration is completed
- The template uses 'cat' as a placeholder - replace with your actual command
- Test with --dry-run before importing users
- Ensure domain import command has proper sudo privileges

### Alternative: Command-line Override
You can also specify the command directly without a config file:
```bash
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \\
  --username {domain_users[0]} \\
  --command 'sudo /path/to/your/domain-import-script' \\
  --args-template '--username {{username}} --home {{home}} --shell {{shell}} --primary-group {{primary_group}}'
```
"""
        
        return instructions
    
    def add_domain_menu_options(self, menu_options: list) -> list:
        """Add domain user options to custom flow menu"""
        
        domain_menu = ("domain_users", "🌐 Domain User Configuration", [
            ("detect_domain_users", "Detect domain users in current configuration"),
            ("configure_domain_import", "Configure domain user import"),
            ("create_domain_template", "Create domain configuration template"),
            ("test_domain_config", "Test domain configuration"),
            ("import_domain_user", "Import specific domain user"),
            ("validate_domain_setup", "Validate current domain setup"),
        ])
        
        # Insert domain menu after user management (if it exists)
        for i, (key, title, _) in enumerate(menu_options):
            if 'user' in key.lower() or 'User' in title:
                menu_options.insert(i + 1, domain_menu)
                return menu_options
        
        # If no user menu found, add at the end
        menu_options.append(domain_menu)
        return menu_options
    
    def handle_domain_menu_action(self, action: str):
        """Handle domain user menu actions"""
        
        if action == "detect_domain_users":
            self._detect_and_report_domain_users()
        
        elif action == "configure_domain_import":
            self._configure_domain_import_interactive()
        
        elif action == "create_domain_template":
            self._create_domain_template_interactive()
        
        elif action == "test_domain_config":
            self._test_domain_configuration_interactive()
        
        elif action == "import_domain_user":
            self._import_domain_user_interactive()
        
        elif action == "validate_domain_setup":
            self._validate_domain_setup_interactive()
    
    def _detect_and_report_domain_users(self):
        """Detect and report on domain users in configuration"""
        
        print("\n🔍 Scanning configuration for domain users...")
        
        has_domain_users, domain_users = self.validator._detect_domain_users()
        
        if has_domain_users:
            print(f"✅ Found {len(domain_users)} domain users:")
            for username in domain_users:
                print(f"   • {username}")
            
            # Check configuration status
            config_exists, config_path = self.validator._check_domain_config()
            if config_exists:
                print(f"✅ Domain configuration found: {config_path}")
                
                # Validate the configuration
                if self.validator._validate_domain_config_file(config_path):
                    print("✅ Domain configuration is valid")
                else:
                    print("⚠️  Domain configuration needs setup (contains 'cat' placeholder)")
            else:
                print("⚠️  No domain configuration found")
                if get_yes_no("Would you like to create domain configuration now?"):
                    self._create_domain_template_interactive()
        else:
            print("ℹ️  No domain users detected in current configuration")
            print("   Domain user patterns checked:")
            print("   • usernames containing dots (alice.domain)")
            print("   • usernames containing @ (alice@domain.com)")
            print("   • usernames containing \\ (DOMAIN\\alice)")
    
    def _configure_domain_import_interactive(self):
        """Interactive domain import configuration"""
        
        print("\n=== Configure Domain User Import ===")
        
        # Check current state
        validation_result = self.validator.validate_domain_user_requirements()
        
        if validation_result.valid and self.validator.has_domain_users:
            print("✅ Domain configuration is already valid")
            
            if get_yes_no("Would you like to reconfigure anyway?"):
                self._create_domain_config_template()
        else:
            self.validate_and_configure_domain_users()
    
    def _create_domain_template_interactive(self):
        """Interactive domain template creation"""
        
        print("\n=== Create Domain Configuration Template ===")
        
        config_base = getattr(self.config, 'config_base_path', '/etc/shuttle')
        
        output_dir = get_input(
            "Output directory for domain configuration",
            default=config_base,
            validator=lambda p: None if os.path.isdir(os.path.dirname(p)) or os.path.isdir(p) else "Parent directory must exist"
        )
        
        self._create_domain_config_template()
    
    def _test_domain_configuration_interactive(self):
        """Interactive domain configuration testing"""
        
        print("\n=== Test Domain Configuration ===")
        
        # Check for existing configuration
        config_exists, config_path = self.validator._check_domain_config()
        
        if not config_exists:
            config_path = get_input(
                "Enter path to domain configuration file to test",
                validator=lambda p: None if os.path.exists(p) else "File does not exist"
            )
        
        print(f"Testing configuration: {config_path}")
        success = self.helper.test_domain_configuration(config_path)
        
        if success:
            print("✅ Domain configuration test passed")
        else:
            print("❌ Domain configuration test failed")
    
    def _import_domain_user_interactive(self):
        """Interactive domain user import"""
        
        print("\n=== Import Domain User ===")
        
        username = get_input("Enter domain username to import")
        
        # Check for existing configuration
        config_exists, config_path = self.validator._check_domain_config()
        
        if config_exists:
            print(f"Using domain configuration: {config_path}")
        else:
            print("No domain configuration found")
            if get_yes_no("Would you like to create domain configuration first?"):
                config_path = self._create_domain_config_template()
                if not config_path:
                    return
            else:
                return
        
        # Build import command
        script_dir = os.path.dirname(os.path.abspath(__file__))
        user_script = os.path.join(script_dir, "12_users_and_groups.sh")
        
        if not os.path.exists(user_script):
            user_script = "./scripts/2_post_install_config_steps/12_users_and_groups.sh"
        
        cmd = [
            user_script,
            "import-domain-user",
            "--username", username,
            "--command-config", config_path,
            "--verbose"
        ]
        
        if get_yes_no("Use dry-run mode (recommended for testing)?", default=True):
            cmd.append("--dry-run")
        
        print(f"🔧 Executing: {' '.join(cmd)}")
        
        try:
            import subprocess
            result = subprocess.run(cmd, check=True, text=True)
            print("✅ Domain user import completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Domain user import failed: {e}")
        except FileNotFoundError:
            print(f"❌ Could not find user management script: {user_script}")
    
    def _validate_domain_setup_interactive(self):
        """Interactive domain setup validation"""
        
        print("\n=== Validate Domain Setup ===")
        
        # Run full validation
        validation_result = self.validator.validate_domain_user_requirements()
        
        print(f"Domain users detected: {'Yes' if self.validator.has_domain_users else 'No'}")
        
        if self.validator.has_domain_users:
            domain_users = self.validator.get_domain_users()
            print(f"Domain users: {', '.join(domain_users)}")
            
            print(f"Domain configuration exists: {'Yes' if self.validator.domain_config_exists else 'No'}")
            
            if self.validator.domain_config_exists:
                print(f"Configuration path: {self.validator.domain_config_path}")
                valid = self.validator._validate_domain_config_file(self.validator.domain_config_path)
                print(f"Configuration valid: {'Yes' if valid else 'No (contains placeholder)'}")
        
        print(f"Overall validation: {'✅ PASS' if validation_result.valid else '❌ FAIL'}")
        
        if not validation_result.valid:
            print(f"Issue: {validation_result.message}")
            
            if get_yes_no("Would you like to fix the configuration now?"):
                self.validate_and_configure_domain_users()


# Example integration function for existing wizard
def integrate_domain_validation_into_wizard(wizard_instance):
    """
    Example function showing how to integrate domain validation into existing wizard
    This would be called from the main wizard after user configuration
    """
    
    # Create domain integration instance
    domain_integration = WizardDomainIntegration(wizard_instance.config)
    
    # Validate and configure domain users
    success = domain_integration.validate_and_configure_domain_users()
    
    if not success:
        print("⚠️  Domain user configuration failed or was skipped")
        print("   Domain users may not be importable until configuration is completed")
    
    # Add domain integration to wizard instance for later use
    wizard_instance.domain_integration = domain_integration
    
    return success


if __name__ == "__main__":
    # Test the domain integration
    print("Domain Integration Test")
    
    # This would normally be called from the main wizard
    # integrate_domain_validation_into_wizard(wizard_instance)