# Domain User Import Configuration Design

## Overview

Design for adding configurable domain user import functionality to shuttle's user management system, allowing workplace-specific commands without exposing them in the public repository.

## Configuration Approach

### 1. Configuration File Extension

Add to `/etc/shuttle/shuttle_config.yaml`:

```yaml
user_management:
  # Existing user/group settings...
  
  domain_user_import:
    enabled: true
    command: "/opt/corporate/bin/import-domain-user"  # Workplace-specific path
    command_args_template: "--username {username} --home {home} --shell {shell} --uid {uid}"
    default_shell: "/bin/bash"
    default_home_pattern: "/home/{username}"
    uid_range_start: 70000
    uid_range_end: 99999
    
    # Optional: Different commands for different operations
    commands:
      import: "/opt/corporate/bin/import-domain-user"
      remove: "/opt/corporate/bin/remove-domain-user"
      sync: "/opt/corporate/bin/sync-domain-users"
      check: "/opt/corporate/bin/check-domain-user"
```

### 2. New Command File

Create `_cmd_import_domain_user.source.sh`:

```bash
cmd_import_domain_user() {
    local username=""
    local home=""
    local shell=""
    local uid=""
    local custom_args=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --username) username="$2"; shift 2 ;;
            --home) home="$2"; shift 2 ;;
            --shell) shell="$2"; shift 2 ;;
            --uid) uid="$2"; shift 2 ;;
            --custom-args) custom_args="$2"; shift 2 ;;
            --help) show_import_domain_user_usage; return 0 ;;
            *) error_exit "Unknown option: $1" ;;
        esac
    done
    
    # Load configuration
    local import_command=$(get_config_value "user_management.domain_user_import.command" "")
    local args_template=$(get_config_value "user_management.domain_user_import.command_args_template" "")
    
    if [[ -z "$import_command" ]]; then
        error_exit "Domain user import not configured. Set user_management.domain_user_import.command in config"
    fi
    
    # Apply defaults from config
    if [[ -z "$shell" ]]; then
        shell=$(get_config_value "user_management.domain_user_import.default_shell" "/bin/bash")
    fi
    
    if [[ -z "$home" ]]; then
        local home_pattern=$(get_config_value "user_management.domain_user_import.default_home_pattern" "/home/{username}")
        home="${home_pattern//\{username\}/$username}"
    fi
    
    # Build command
    local final_args="$args_template"
    final_args="${final_args//\{username\}/$username}"
    final_args="${final_args//\{home\}/$home}"
    final_args="${final_args//\{shell\}/$shell}"
    final_args="${final_args//\{uid\}/$uid}"
    
    # Execute
    execute_or_log "$import_command $final_args $custom_args"
}
```

### 3. Integration with 12_users_and_groups.sh

Add new commands to the dispatcher:

```bash
# In main() function, add:
"import-domain-user")
    cmd_import_domain_user "$@"
    ;;
"sync-domain-users")
    cmd_sync_domain_users "$@"
    ;;
"check-domain-user")
    cmd_check_domain_user "$@"
    ;;
```

### 4. Wizard Integration

Add to `post_install_config_wizard.py`:

```python
class DomainUserImportConfig:
    """Configuration for domain user import"""
    
    def __init__(self):
        self.enabled = False
        self.command = ""
        self.command_args_template = "--username {username} --home {home} --shell {shell}"
        self.default_shell = "/bin/bash"
        self.default_home_pattern = "/home/{username}"
        self.uid_range_start = 70000
        self.uid_range_end = 99999
    
    def configure_interactive(self):
        """Interactive configuration"""
        print("\n=== Domain User Import Configuration ===")
        
        self.enabled = get_yes_no("Enable domain user import functionality?", default="no")
        
        if self.enabled:
            print("\nProvide the path to your domain user import command.")
            print("This command will be called with the configured arguments.")
            self.command = get_input(
                "Domain user import command path",
                default="",
                validator=self._validate_command_path
            )
            
            print("\nConfigure command arguments template.")
            print("Available variables: {username}, {home}, {shell}, {uid}")
            self.command_args_template = get_input(
                "Command arguments template",
                default=self.command_args_template
            )
            
            # ... more configuration options
```

## Usage Examples

### Manual Command Line Usage

```bash
# Import a domain user with defaults
./12_users_and_groups.sh import-domain-user --username alice.domain

# Import with specific settings
./12_users_and_groups.sh import-domain-user \
    --username alice.domain \
    --uid 70001 \
    --home /home/domain/alice \
    --shell /bin/bash

# With custom arguments for workplace-specific options
./12_users_and_groups.sh import-domain-user \
    --username alice.domain \
    --custom-args "--department engineering --manager bob"
```

### In Automated Scripts

```bash
# Loop through a list of domain users
for user in alice.domain bob.domain charlie.domain; do
    ./12_users_and_groups.sh import-domain-user --username "$user"
done
```

### Configuration File Examples

#### Example 1: Simple Command
```yaml
user_management:
  domain_user_import:
    enabled: true
    command: "/usr/local/bin/ad-import"
    command_args_template: "-u {username} -h {home} -s {shell}"
```

#### Example 2: PowerShell Script
```yaml
user_management:
  domain_user_import:
    enabled: true
    command: "powershell.exe"
    command_args_template: "-File /opt/scripts/Import-ADUser.ps1 -Username {username} -HomeDir {home} -Shell {shell}"
```

#### Example 3: Complex Integration
```yaml
user_management:
  domain_user_import:
    enabled: true
    command: "/opt/corporate/idm/bin/user-sync"
    command_args_template: "--action import --domain CORP --user {username} --unix-home {home} --unix-shell {shell} --unix-uid {uid}"
    commands:
      import: "/opt/corporate/idm/bin/user-sync --action import"
      remove: "/opt/corporate/idm/bin/user-sync --action remove"
      check: "/opt/corporate/idm/bin/user-sync --action verify"
```

## Security Considerations

1. **Command Validation**: Validate that configured commands exist and are executable
2. **Path Restrictions**: Option to restrict commands to specific directories
3. **Argument Sanitization**: Escape special characters in usernames
4. **Audit Logging**: Log all domain user import operations
5. **Dry-run Support**: Test imports without executing

## Implementation Benefits

1. **Flexibility**: Supports any workplace-specific import mechanism
2. **Privacy**: Keeps corporate tools/paths out of public repo
3. **Extensibility**: Easy to add new parameters or commands
4. **Integration**: Works with existing user management tools
5. **Testing**: Can be tested with mock commands

## Alternative Approaches Considered

1. **Plugin System**: Too complex for this use case
2. **Environment Variables**: Less flexible than config file
3. **Hardcoded Paths**: Not portable across environments
4. **Shell Aliases**: Wouldn't work in script context

## Next Steps

1. Implement `_cmd_import_domain_user.source.sh`
2. Add command to `12_users_and_groups.sh`
3. Update configuration schema
4. Add wizard support
5. Create documentation
6. Add tests with mock import command