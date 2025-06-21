#!/bin/bash
# Direct source file for main scripts (1_install.sh, 2_post_install_config.sh)
# No path searching - just direct sourcing of required libraries

# Get the directory where this _sources.sh file is located
SOURCES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Common libraries from _setup_lib_sh
source "$SOURCES_DIR/_setup_lib_sh/_common_.source.sh"
source "$SOURCES_DIR/_setup_lib_sh/_input_validation.source.sh"
source "$SOURCES_DIR/_setup_lib_sh/_check_active_user.source.sh"

# Installation-specific libraries for 1_install.sh
source "$SOURCES_DIR/_setup_lib_sh/installation_constants.source.sh"
source "$SOURCES_DIR/_setup_lib_sh/installation_instructions_reader.source.sh"

# Post-install config libraries for 2_post_install_config.sh
source "$SOURCES_DIR/_setup_lib_sh/_check_tool.source.sh"
source "$SOURCES_DIR/_setup_lib_sh/_users_and_groups_inspect.source.sh"

# Package manager for any installation needs
source "$SOURCES_DIR/_setup_lib_sh/_package_manager.source.sh"