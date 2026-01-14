#!/bin/bash
# Install shuttle from main repo at specified version
#
# Usage: ./install.sh [--venv /path/to/venv]
#
# This script reads the VERSION file and installs all shuttle packages
# from the main repository at that version tag.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="https://github.com/mathew-j-davis/shuttle.git"
VERSION=$(cat "$SCRIPT_DIR/VERSION")

# Default venv path (can be overridden with --venv)
VENV_PATH="/opt/shuttle/venv"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --venv)
            VENV_PATH="$2"
            shift 2
            ;;
        --repo)
            REPO="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--venv /path/to/venv] [--repo git-url]"
            echo ""
            echo "Options:"
            echo "  --venv PATH    Path to virtual environment (default: /opt/shuttle/venv)"
            echo "  --repo URL     Git repository URL (default: $REPO)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

PIP="$VENV_PATH/bin/pip"

echo "======================================"
echo "Installing Shuttle v${VERSION}"
echo "======================================"
echo "Repository: $REPO"
echo "Venv path:  $VENV_PATH"
echo ""

# Check venv exists
if [[ ! -f "$PIP" ]]; then
    echo "ERROR: Virtual environment not found at $VENV_PATH"
    echo "Create it first: python3 -m venv $VENV_PATH"
    exit 1
fi

# Install packages in dependency order
echo "1/3 Installing shuttle_common (shared library)..."
$PIP install "git+${REPO}@v${VERSION}#subdirectory=src/shared_library"

echo ""
echo "2/3 Installing shuttle (main application)..."
$PIP install "git+${REPO}@v${VERSION}#subdirectory=src/shuttle_app"

echo ""
echo "3/3 Installing shuttle_defender_test..."
$PIP install "git+${REPO}@v${VERSION}#subdirectory=src/shuttle_defender_test_app"

echo ""
echo "======================================"
echo "Installation complete: Shuttle v${VERSION}"
echo "======================================"
