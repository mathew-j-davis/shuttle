#!/bin/bash
# 00_set_env.sh - Set up Shuttle environment variables

# Default paths

DEFAULT_CONFIG_PATH="$HOME_DIR/.config/shuttle/config.conf"
DEFAULT_VENV_PATH="$HOME_DIR/.local/share/shuttle/venv"
DEFAULT_WORK_DIR="$HOME_DIR/.local/share/shuttle/work"


# for development use
# HOME_DIR=$(eval echo ~$USER)
# DEFAULT_CONFIG_PATH="$HOME_DIR/shuttle/config.conf"
# DEFAULT_VENV_PATH="$HOME_DIR/shuttle/.venv"
# DEFAULT_WORK_DIR="$HOME_DIR/shuttle/work"


# Parse arguments
CONFIG_PATH=${1:-$DEFAULT_CONFIG_PATH}
VENV_PATH=${2:-$DEFAULT_VENV_PATH}
WORK_DIR=${3:-$DEFAULT_WORK_DIR}

# Create directories
mkdir -p $(dirname "$CONFIG_PATH")
mkdir -p "$VENV_PATH"
mkdir -p "$WORK_DIR"

# Set environment variables for this session
export SHUTTLE_CONFIG_PATH="$CONFIG_PATH"
export SHUTTLE_VENV_PATH="$VENV_PATH"
export SHUTTLE_WORK_DIR="$WORK_DIR"

# Create a sourceable file
cat > shuttle_env.sh << EOF
#!/bin/bash
export SHUTTLE_CONFIG_PATH="$CONFIG_PATH"
export SHUTTLE_VENV_PATH="$VENV_PATH"
export SHUTTLE_WORK_DIR="$WORK_DIR"

echo "SHUTTLE_CONFIG_PATH="\$SHUTTLE_CONFIG_PATH
echo "SHUTTLE_VENV_PATH="\$SHUTTLE_VENV_PATH
echo "SHUTTLE_WORK_DIR="\$SHUTTLE_WORK_DIR
EOF

echo "Environment variables set:"
echo "SHUTTLE_CONFIG_PATH=$SHUTTLE_CONFIG_PATH"
echo "SHUTTLE_VENV_PATH=$SHUTTLE_VENV_PATH"
echo "SHUTTLE_WORK_DIR=$SHUTTLE_WORK_DIR"
echo ""
echo "These variables are set for the current session."
echo "For future sessions, source the environment with:"
echo "source $(pwd)/shuttle_env.sh"