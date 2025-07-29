#!/bin/bash

# Domain Config Generator Command
# Creates domain import configuration files and setup instructions

# Show usage for generate-domain-config command
show_generate_domain_config_usage() {
    cat << EOF
Usage: $SCRIPT_NAME generate-domain-config [OPTIONS]

Generate domain user import configuration files and setup instructions.

OPTIONS:
  --output-dir DIR        Directory to create config files (default: current directory)
  --config-name NAME      Name for config file (default: domain_import.conf)
  --format FORMAT         Config format: conf, yaml (default: conf)
  --command CMD           Domain import command to use in template
  --interactive           Interactive configuration setup
  --dry-run               Show what would be created without creating files
  --verbose               Show detailed output
  --help                  Show this help message

EXAMPLES:
  # Generate template config file
  $SCRIPT_NAME generate-domain-config --output-dir /etc/shuttle
  
  # Generate with specific command
  $SCRIPT_NAME generate-domain-config --command "sudo /opt/corporate/bin/import-user" --output-dir /etc/shuttle
  
  # Interactive setup
  $SCRIPT_NAME generate-domain-config --interactive --output-dir /etc/shuttle
  
  # Generate YAML format
  $SCRIPT_NAME generate-domain-config --format yaml --output-dir /etc/shuttle

GENERATED FILES:
  • domain_import.conf (or .yaml) - Configuration file
  • domain_setup_instructions.md - Setup and usage instructions
  • test_domain_import.sh - Test script

NOTES:
  • Config files are templates that need customization for your environment
  • Instructions include examples specific to your generated config
  • Test script helps verify domain import functionality
  • Use --interactive for guided setup
EOF
}

# Generate domain configuration template
generate_domain_config_template() {
    local output_dir="$1"
    local config_name="$2"
    local format="$3"
    local command="$4"
    local interactive="$5"
    
    # Set defaults
    local default_command="sudo /path/to/your/domain-import-script"
    local default_args_template="--username {username} --home {home} --shell {shell} --primary-group {primary_group}"
    local default_shell="/bin/bash"
    local default_home_pattern="/home/{username}"
    
    # Interactive configuration
    if [[ "$interactive" == "true" ]]; then
        echo "=== Domain User Import Configuration Setup ==="
        echo ""
        
        echo "Enter your domain user import command path:"
        echo "Example: /opt/corporate/bin/import-domain-user"
        read -p "Command path: " -r command
        [[ -z "$command" ]] && command="$default_command"
        
        echo ""
        echo "Enter command arguments template:"
        echo "Available variables: {username}, {uid}, {home}, {shell}, {primary_group}, {groups}"
        echo "Default: $default_args_template"
        read -p "Args template: " -r args_template
        [[ -z "$args_template" ]] && args_template="$default_args_template"
        
        echo ""
        echo "Enter default shell for imported users:"
        read -p "Default shell [$default_shell]: " -r shell
        [[ -z "$shell" ]] && shell="$default_shell"
        
        echo ""
        echo "Enter home directory pattern:"
        echo "Use {username} as placeholder for the username"
        read -p "Home pattern [$default_home_pattern]: " -r home_pattern
        [[ -z "$home_pattern" ]] && home_pattern="$default_home_pattern"
    else
        # Use provided or default values
        [[ -z "$command" ]] && command="$default_command"
        args_template="$default_args_template"
        shell="$default_shell"
        home_pattern="$default_home_pattern"
    fi
    
    # Ensure output directory exists
    if [[ ! -d "$output_dir" ]]; then
        if [[ "$DRY_RUN" == "false" ]]; then
            mkdir -p "$output_dir"
            log INFO "Created directory: $output_dir"
        else
            log INFO "[DRY RUN] Would create directory: $output_dir"
        fi
    fi
    
    # Generate config file
    local config_file="$output_dir/$config_name"
    
    if [[ "$format" == "yaml" ]]; then
        generate_yaml_config "$config_file" "$command" "$args_template" "$shell" "$home_pattern"
    else
        generate_conf_config "$config_file" "$command" "$args_template" "$shell" "$home_pattern"
    fi
    
    # Generate instructions
    generate_setup_instructions "$output_dir" "$config_file" "$command" "$args_template"
    
    # Generate test script
    generate_test_script "$output_dir" "$config_file"
    
    echo ""
    echo "✅ Domain configuration generated successfully!"
    echo ""
    echo "Generated files:"
    echo "  📄 Config: $config_file"
    echo "  📋 Instructions: $output_dir/domain_setup_instructions.md"
    echo "  🧪 Test script: $output_dir/test_domain_import.sh"
    echo ""
    echo "Next steps:"
    echo "  1. Edit $config_file with your actual domain import command"
    echo "  2. Review domain_setup_instructions.md"
    echo "  3. Test with: ./test_domain_import.sh"
}

# Generate shell-style config file
generate_conf_config() {
    local config_file="$1"
    local command="$2"
    local args_template="$3"
    local shell="$4"
    local home_pattern="$5"
    
    local content
    content=$(cat << EOF
# Domain User Import Configuration
# Generated by shuttle domain config generator
# 
# INSTRUCTIONS:
# 1. Replace '/path/to/your/domain-import-script' with your actual command
# 2. Adjust arguments template for your environment
# 3. Test with: ./test_domain_import.sh

# Required: Command to import domain users
command=$command

# Optional: Command arguments template
# Available variables: {username}, {uid}, {home}, {shell}, {primary_group}, {groups}
args_template=$args_template

# Optional: Default settings
default_shell=$shell
default_home_pattern=$home_pattern

# Optional: UID range (only needed if script generates UIDs)
# uid_range_start=70000
# uid_range_end=99999

# Example usage:
# ./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \\
#   --username alice.domain --command-config $config_file
EOF
)
    
    if [[ "$DRY_RUN" == "false" ]]; then
        echo "$content" > "$config_file"
        log INFO "Generated config file: $config_file"
    else
        log INFO "[DRY RUN] Would generate config file: $config_file"
        if [[ "$VERBOSE" == "true" ]]; then
            echo "--- Config file content ---"
            echo "$content"
            echo "--- End config file ---"
        fi
    fi
}

# Generate YAML config file
generate_yaml_config() {
    local config_file="$1"
    local command="$2"
    local args_template="$3"
    local shell="$4"
    local home_pattern="$5"
    
    local content
    content=$(cat << EOF
# Domain User Import Configuration (YAML format)
# Generated by shuttle domain config generator
# 
# INSTRUCTIONS:
# 1. Replace '/path/to/your/domain-import-script' with your actual command
# 2. Adjust arguments template for your environment  
# 3. Test with: ./test_domain_import.sh

# Required: Command to import domain users
command: "$command"

# Optional: Command arguments template
# Available variables: {username}, {uid}, {home}, {shell}, {primary_group}, {groups}
command_args_template: "$args_template"

# Optional: Default settings
default_shell: "$shell"
default_home_pattern: "$home_pattern"

# Optional: UID range (only needed if script generates UIDs)
# uid_range_start: 70000
# uid_range_end: 99999

# Example usage:
# ./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \\
#   --username alice.domain --command-config $config_file
EOF
)
    
    if [[ "$DRY_RUN" == "false" ]]; then
        echo "$content" > "$config_file"
        log INFO "Generated YAML config file: $config_file"
    else
        log INFO "[DRY RUN] Would generate YAML config file: $config_file"
        if [[ "$VERBOSE" == "true" ]]; then
            echo "--- YAML config file content ---"
            echo "$content"
            echo "--- End YAML config file ---"
        fi
    fi
}

# Generate setup instructions
generate_setup_instructions() {
    local output_dir="$1"
    local config_file="$2"
    local command="$3"
    local args_template="$4"
    
    local instructions_file="$output_dir/domain_setup_instructions.md"
    local config_basename=$(basename "$config_file")
    
    local content
    content=$(cat << EOF
# Domain User Import Setup Instructions

## Overview

This directory contains configuration for shuttle's domain user import functionality.

## Generated Files

- **$config_basename** - Domain import configuration
- **domain_setup_instructions.md** - This file
- **test_domain_import.sh** - Test script

## Setup Steps

### 1. Configure Domain Import Command

Edit \`$config_basename\` and replace:
\`\`\`
$command
\`\`\`

With your actual domain import command path.

### 2. Test Configuration

Run the test script to verify your configuration:
\`\`\`bash
./test_domain_import.sh
\`\`\`

### 3. Import Domain Users

Once configured, import users with:

\`\`\`bash
# Simple import
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \\
  --username alice.domain --command-config $config_file

# Import with primary group
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \\
  --username alice.domain --primary-group engineering --command-config $config_file

# Import with groups
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \\
  --username alice.domain --primary-group engineering --groups "developers,sudo" \\
  --command-config $config_file

# Test import (dry run)
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \\
  --username alice.domain --command-config $config_file --dry-run --verbose
\`\`\`

## Alternative Usage

### Command-line Override
You can also specify the command directly without a config file:
\`\`\`bash
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \\
  --username alice.domain \\
  --command '$command' \\
  --args-template '$args_template'
\`\`\`

### Global Configuration
To use this config automatically, copy it to one of these locations:
- \`/etc/shuttle/domain_config.yaml\`
- \`/etc/shuttle/domain_import.conf\` 
- \`\$HOME/.config/shuttle/domain_config.yaml\`

## Template Variables

Your domain import command will receive these variables:

- \`{username}\` - The domain username to import
- \`{uid}\` - UID (if specified, empty if domain determines)
- \`{home}\` - Home directory path
- \`{shell}\` - Login shell
- \`{primary_group}\` - Primary group (if specified)
- \`{groups}\` - Secondary groups (if specified)

## Troubleshooting

### Test Configuration
\`\`\`bash
./test_domain_import.sh --verbose
\`\`\`

### Check Import Command
\`\`\`bash
./scripts/2_post_install_config_steps/12_users_and_groups.sh import-domain-user \\
  --username test.user --command-config $config_file --dry-run --verbose
\`\`\`

### Common Issues

1. **"Import command not found"**
   - Check command path in $config_basename
   - Ensure script is executable

2. **Permission denied**
   - Add \`sudo\` to command if needed
   - Check script permissions

3. **Configuration not loaded**
   - Verify config file syntax
   - Check file path and permissions

## Security Notes

- Domain import commands typically require sudo privileges
- Test with \`--dry-run\` before importing users
- Keep domain-specific commands in separate config files
- Use \`--force\` to update existing users

Generated by shuttle domain config generator on $(date)
EOF
)
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would generate instructions: $instructions_file"
        return 0
    fi
    
    # Write the instructions file
    if ! write_file_with_sudo_fallback "$instructions_file" "$content" "true"; then
        log ERROR "Failed to create instructions file: $instructions_file"
        return 1
    fi
    
    log INFO "Generated instructions: $instructions_file"
}

# Generate test script
generate_test_script() {
    local output_dir="$1"
    local config_file="$2"
    
    local test_file="$output_dir/test_domain_import.sh"
    local config_basename=$(basename "$config_file")
    local script_dir=$(dirname "$(realpath "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")")
    local user_script_path="$script_dir/../12_users_and_groups.sh"
    
    # Make paths relative for portability
    local relative_config_file="./${config_basename}"
    local relative_user_script="./scripts/2_post_install_config_steps/12_users_and_groups.sh"
    
    local content
    content=$(cat << 'EOF'
#!/bin/bash

# Test script for domain user import configuration
# Generated by shuttle domain config generator

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="PLACEHOLDER_CONFIG_FILE"
USER_SCRIPT="PLACEHOLDER_USER_SCRIPT"

# Test configuration
echo "=== Testing Domain User Import Configuration ==="
echo ""

echo "📁 Config file: $CONFIG_FILE"
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "❌ Config file not found!"
    echo "   Create and configure: $CONFIG_FILE"
    exit 1
fi

echo "✅ Config file exists"
echo ""

echo "📋 Configuration contents:"
echo "----------------------------------------"
cat "$CONFIG_FILE"
echo "----------------------------------------"
echo ""

echo "🧪 Testing with dry-run..."
if [[ -f "$USER_SCRIPT" ]]; then
    echo "Command: $USER_SCRIPT import-domain-user --username test.domain --command-config $CONFIG_FILE --dry-run --verbose"
    echo ""
    
    "$USER_SCRIPT" import-domain-user \
        --username test.domain \
        --command-config "$CONFIG_FILE" \
        --dry-run --verbose
    
    echo ""
    echo "✅ Test completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Edit $CONFIG_FILE with your actual domain import command"
    echo "  2. Test with a real domain user:"
    echo "     $USER_SCRIPT import-domain-user --username your.domain.user --command-config $CONFIG_FILE --dry-run"
    echo "  3. Remove --dry-run when ready to import"
else
    echo "❌ User management script not found: $USER_SCRIPT"
    echo "   This test script should be run from the shuttle directory"
    exit 1
fi
EOF
)
    
    # Replace placeholders with relative paths for portability
    content="${content//PLACEHOLDER_CONFIG_FILE/$relative_config_file}"
    content="${content//PLACEHOLDER_USER_SCRIPT/$relative_user_script}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would generate test script: $test_file"
        log INFO "[DRY RUN] Would make executable: $test_file"
        return 0
    fi
    
    # Write the test script file
    if ! write_file_with_sudo_fallback "$test_file" "$content" "true"; then
        log ERROR "Failed to create test script: $test_file"
        return 1
    fi
    
    # Make the script executable
    if ! make_executable_with_sudo_fallback "$test_file" "test script" "true"; then
        log WARN "Could not make test script executable: $test_file"
    fi
    
    log INFO "Generated test script: $test_file"
}

# Main function for generate-domain-config command
cmd_generate_domain_config() {
    local output_dir="."
    local config_name="domain_import.conf"
    local format="conf"
    local command=""
    local interactive=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --output-dir)
                output_dir="$2"
                shift 2
                ;;
            --config-name)
                config_name="$2"
                shift 2
                ;;
            --format)
                format="$2"
                if [[ "$format" != "conf" && "$format" != "yaml" ]]; then
                    error_exit "Invalid format: $format. Use 'conf' or 'yaml'"
                fi
                shift 2
                ;;
            --command)
                command="$2"
                shift 2
                ;;
            --interactive)
                interactive=true
                shift
                ;;
            --dry-run)
                # Already handled globally
                shift
                ;;
            --verbose)
                # Already handled globally
                shift
                ;;
            --help)
                show_generate_domain_config_usage
                return 0
                ;;
            *)
                error_exit "Unknown option: $1. Use --help for usage information."
                ;;
        esac
    done
    
    # Adjust config name extension based on format
    if [[ "$format" == "yaml" && "$config_name" == "domain_import.conf" ]]; then
        config_name="domain_config.yaml"
    fi
    
    log INFO "Generating domain user import configuration..."
    if [[ "$VERBOSE" == "true" ]]; then
        log INFO "  Output directory: $output_dir"
        log INFO "  Config name: $config_name"
        log INFO "  Format: $format"
        log INFO "  Interactive: $interactive"
    fi
    
    generate_domain_config_template "$output_dir" "$config_name" "$format" "$command" "$interactive"
}

# Export functions for use by other scripts
export -f cmd_generate_domain_config
export -f show_generate_domain_config_usage
export -f generate_domain_config_template
export -f generate_conf_config
export -f generate_yaml_config
export -f generate_setup_instructions
export -f generate_test_script