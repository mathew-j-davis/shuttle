#!/bin/bash

# to activate this outside of the script you need to call like this:
# source ./05_activate_venv_CALL_BY_SOURCE.sh

# Check if SHUTTLE_VENV_PATH is set
if [ -z "$SHUTTLE_VENV_PATH" ]; then
    echo "SHUTTLE_VENV_PATH environment variable is not set."
    echo "Please run 00_set_env.sh first."
    exit 1
fi

# Check virtual environment status
if [[ "$VIRTUAL_ENV" == "" ]]; then
    # No virtual environment is active, activate ours
    echo "Activating the virtual environment at $SHUTTLE_VENV_PATH..."
    . "$SHUTTLE_VENV_PATH/bin/activate"
    echo "Virtual environment activated: $VIRTUAL_ENV"
else
    # A virtual environment is already active
    if [[ "$VIRTUAL_ENV" == "$SHUTTLE_VENV_PATH" ]]; then
        echo "Shuttle virtual environment is already active."
    else
        echo "WARNING: Another virtual environment is already active:"
        echo "  Current: $VIRTUAL_ENV"
        echo "  Shuttle: $SHUTTLE_VENV_PATH"
        echo ""
        echo "To switch to the Shuttle environment, first run 'deactivate' and then source this script again."
        echo "Alternatively, you can force activation by setting FORCE_VENV=1:"
        echo "  FORCE_VENV=1 source $0"
        
        # Check if force flag is set
        if [[ "$FORCE_VENV" == "1" ]]; then
            echo "Force flag set, switching virtual environments..."
            deactivate 2>/dev/null || true
            . "$SHUTTLE_VENV_PATH/bin/activate"
            echo "Virtual environment activated: $VIRTUAL_ENV"
        fi
    fi
fi


# linux
# . venv/bin/activate

# windows gitbash
#source venv/Scripts/activate
