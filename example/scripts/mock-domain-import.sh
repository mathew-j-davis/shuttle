#!/bin/bash

# Mock Domain User Import Script
# This is a testing script that simulates a workplace-specific domain user import command
# Use this for testing the domain user import functionality

set -euo pipefail

# Script defaults
DRY_RUN=false
VERBOSE=false
USERNAME=""
UID=""
HOME=""
SHELL=""
PRIMARY_GROUP=""
GROUPS=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --username)
            USERNAME="$2"
            shift 2
            ;;
        --uid)
            UID="$2"
            shift 2
            ;;
        --home)
            HOME="$2"
            shift 2
            ;;
        --shell)
            SHELL="$2"
            shift 2
            ;;
        --primary-group)
            PRIMARY_GROUP="$2"
            shift 2
            ;;
        --groups)
            GROUPS="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            cat << EOF
Mock Domain User Import Script

Usage: $0 [OPTIONS]

OPTIONS:
  --username USERNAME    Domain username to import
  --uid UID             UID to assign (optional)
  --home HOME           Home directory (optional)
  --shell SHELL         Login shell (optional)
  --primary-group GROUP Primary group (optional)
  --groups GROUPS       Additional secondary groups (optional)
  --dry-run             Don't actually create user
  --verbose             Show detailed output
  --help                Show this help

This script simulates a workplace-specific domain user import command.
For testing purposes, it will create a local user with the specified parameters.
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$USERNAME" ]]; then
    echo "Error: --username is required"
    exit 1
fi

# Set defaults
if [[ -z "$SHELL" ]]; then
    SHELL="/bin/bash"
fi

if [[ -z "$HOME" ]]; then
    HOME="/home/$USERNAME"
fi

if [[ -z "$UID" ]]; then
    # Simulate domain-determined UID (like your actual domain would do)
    UID=$(( 70000 + RANDOM % 10000 ))
    echo "NOTE: Domain determined UID: $UID (simulated)"
fi

# Show what we're doing
echo "Mock Domain User Import"
echo "======================"
echo "Username: $USERNAME"
echo "UID: $UID"
echo "Home: $HOME"
echo "Shell: $SHELL"
if [[ -n "$PRIMARY_GROUP" ]]; then
    echo "Primary Group: $PRIMARY_GROUP"
fi
if [[ -n "$GROUPS" ]]; then
    echo "Secondary Groups: $GROUPS"
fi
echo "Dry Run: $DRY_RUN"
echo ""

# Simulate the import process
if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would create user with the following command:"
    
    local create_cmd="useradd --uid $UID --home-dir $HOME --shell $SHELL --create-home"
    if [[ -n "$PRIMARY_GROUP" ]]; then
        create_cmd="$create_cmd --gid $PRIMARY_GROUP"
    fi
    create_cmd="$create_cmd $USERNAME"
    echo "  $create_cmd"
    
    if [[ -n "$GROUPS" ]]; then
        echo "  usermod --append --groups $GROUPS $USERNAME"
    fi
    
    echo ""
    echo "[DRY RUN] User import simulation completed successfully"
else
    echo "Creating user account..."
    
    # Check if user already exists
    if id "$USERNAME" >/dev/null 2>&1; then
        echo "Warning: User $USERNAME already exists"
        existing_uid=$(id -u "$USERNAME")
        echo "Existing UID: $existing_uid"
        
        if [[ "$existing_uid" != "$UID" ]]; then
            echo "Error: User exists with different UID ($existing_uid vs $UID)"
            exit 1
        fi
        
        echo "User already exists with correct UID, skipping creation"
    else
        # Create the user
        local create_cmd="useradd --uid $UID --home-dir $HOME --shell $SHELL --create-home"
        if [[ -n "$PRIMARY_GROUP" ]]; then
            create_cmd="$create_cmd --gid $PRIMARY_GROUP"
        fi
        create_cmd="$create_cmd $USERNAME"
        
        if [[ "$VERBOSE" == "true" ]]; then
            echo "Executing: $create_cmd"
        fi
        
        eval "$create_cmd"
        
        if [[ $? -eq 0 ]]; then
            echo "User $USERNAME created successfully"
        else
            echo "Error: Failed to create user $USERNAME"
            exit 1
        fi
    fi
    
    # Add to additional groups if specified
    if [[ -n "$GROUPS" ]]; then
        echo "Adding user to groups: $GROUPS"
        if [[ "$VERBOSE" == "true" ]]; then
            echo "Executing: usermod --append --groups $GROUPS $USERNAME"
        fi
        
        usermod --append --groups "$GROUPS" "$USERNAME"
        
        if [[ $? -eq 0 ]]; then
            echo "User added to groups successfully"
        else
            echo "Warning: Failed to add user to some groups"
        fi
    fi
    
    # Verify the user was created
    echo ""
    echo "User verification:"
    id "$USERNAME"
    
    echo ""
    echo "User import completed successfully"
fi

# Exit with success
exit 0