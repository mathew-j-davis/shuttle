#!/bin/bash
# Direct source file for post-install config step scripts
# No path searching - just direct sourcing of required libraries

# Get the directory where this _sources.sh file is located
SOURCES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPTS_DIR="$(dirname "$SOURCES_DIR")"

# Common libraries from _setup_lib_sh
source "$SCRIPTS_DIR/_setup_lib_sh/_common_.source.sh"
source "$SCRIPTS_DIR/_setup_lib_sh/_input_validation.source.sh"
source "$SCRIPTS_DIR/_setup_lib_sh/_check_active_user.source.sh"
source "$SCRIPTS_DIR/_setup_lib_sh/_check_tool.source.sh"
source "$SCRIPTS_DIR/_setup_lib_sh/_users_and_groups_inspect.source.sh"
source "$SCRIPTS_DIR/_setup_lib_sh/sudo_helpers.source.sh"

# Package manager for tools installation
source "$SCRIPTS_DIR/_setup_lib_sh/_package_manager.source.sh"

# Additional libraries if needed by specific scripts
# source "$SCRIPTS_DIR/_setup_lib_sh/installation_constants.source.sh"