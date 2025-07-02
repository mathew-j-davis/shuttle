# AI Assistant Guide to the Shuttle Project

This document provides a structured approach for AI assistants to understand and work with the Shuttle codebase effectively.
While it is similar in content to readme.md, this file is different in that the content below is entirely AI generated with the intent of providing an AI with an efficient introduction to the project.

## Project Context and Purpose

**Shuttle** is a secure file transfer utility designed to be deployed as part of a hardened, secure system that functions as an intermediary between untrusted systems and protected networks. It uses a quarantine-first approach where files are hashed, quarantined, scanned for malware, and then moved to their destination or hazard archive based on scan results.

**Important Security Note**: Shuttle is a utility tool that must be deployed within an already-secured system. It does not, by itself, secure the system. Instead, it provides:
- A secure file processing pipeline with malware scanning
- Configuration tools to help integrate with the host system's security posture
- User, group, and permission management tools to align with security policies
- Integration points for existing security infrastructure (firewalls, access controls)

**Primary Use Case**: Safely transferring data files from equipment running old, unpatched operating systems (industrial control systems, legacy medical devices, aging infrastructure) to secure networks without compromising network integrity. The host system must be properly hardened and secured according to organizational security requirements.

## Getting Context

1. **Essential Documentation (Read First)**
   - `CLAUDE.md` - Project overview, commands, and architecture for Claude Code
   - `readme.md` - System overview, use case, and installation guide
   - `scripts/INSTALLATION_FLOW_DIAGRAM.md` - Complete installation process flow
   - `scripts/POST_INSTALL_CONFIG_FLOW_DIAGRAM.md` - Post-installation configuration flow

2. **Architecture and Design**
   - `docs/readme_architecture.md` - Component interactions and system design
   - `docs/readme_modules.md` - Detailed module descriptions
   - `dev_notes/updated_shuttle_process_diagram.md` - Latest execution flow
   - `dev_notes/shuttle_test_architecture.md` - Test architecture and patterns

3. **Configuration and Setup**
   - `docs/readme_configuration.md` - Settings, file formats, and options
   - `docs/readme_development.md` - Development environment setup
   - `docs/run-cron-service-config.md` - Environment variables for production deployment
   - Configuration precedence: CLI args > config file > defaults

4. **Security and Audit**
   - `scripts/security_audit.py` - Production security validation tool
   - `example/security_audit_config/production_audit.yaml` - Expected security configuration
   - `example/security_audit_config/README.md` - Security audit tool documentation
   - `docs/shuttle_production_user_group_model.md` - Complete security model

## Code Exploration Strategy

1. **Installation and Configuration System**
   - `scripts/1_install.sh` - Main installation orchestrator with wizard mode
   - `scripts/2_post_install_config.sh` - Production environment configuration
   - `scripts/1_installation_steps/` - Individual installation scripts (01-10)
   - `scripts/2_post_install_config_steps/` - Production configuration scripts (11-14)
   - `scripts/_setup_lib_py/` - Python wizard and configuration modules
   - `scripts/_setup_lib_sh/` - Shell function libraries

2. **Core Application Workflow**
   - `src/shuttle_app/shuttle/shuttle.py` - Main entry point and ShuttleApp class
   - `src/shuttle_app/shuttle/scanning.py` - Malware scanning orchestration
   - `src/shuttle_app/shuttle/post_scan_processing.py` - Post-scan file handling
   - `src/shuttle_app/shuttle/daily_processing_tracker.py` - File tracking and metrics
   - `src/shuttle_app/shuttle/throttler.py` - Disk space monitoring
   - `src/shuttle_app/shuttle/throttle_utils.py` - Throttling implementation

3. **Shared Library Components**
   - `src/shared_library/shuttle_common/config.py` - Configuration hierarchy management
   - `src/shared_library/shuttle_common/files.py` - File operations and utilities
   - `src/shared_library/shuttle_common/scan_utils.py` - Scanner interfaces (ClamAV/Defender)
   - `src/shared_library/shuttle_common/notifier.py` - Email notification system
   - `src/shared_library/shuttle_common/logging.py` - Hierarchy logging with function-level context

4. **Testing Infrastructure**
   - `tests/README.md` - Test environment setup and GPG key generation
   - `tests/run.md` - Detailed test execution guide
   - `tests/test_shuttle.py` - Main application tests
   - `tests/test_daily_processing_tracker.py` - File tracking tests
   - `tests/run_shuttle_with_simulator.py` - MDATP simulator integration
   - `tests/run_configurable_shuttle_test.py` - Parametrized testing

5. **Defender Testing Utility**
   - `src/shuttle_defender_test_app/` - Standalone Microsoft Defender testing
   - Required before running shuttle with Defender configuration

## Common Issues to Watch For

1. **Installation and Configuration**
   - Installation scripts must run in correct sequence (01-10)
   - Virtual environment activation required before development
   - Configuration hierarchy: CLI args > config file > defaults
   - Path resolution varies by installation mode (dev/user/service)
   - Post-install configuration requires YAML validation and component enablement

2. **Package Management Consistency**
   - All scripts use standardized package management functions from `_setup_lib_sh/`
   - Avoid hardcoded apt/dnf/yum commands - use shared library functions
   - Cross-platform compatibility maintained through package manager abstraction

3. **File Integrity and Security**
   - File hashing moved to `quarantine_files_for_scanning` for better tracking
   - Quarantine-first security model must be preserved
   - Hash calculation critical for DailyProcessingTracker file identification
   - GPG encryption for suspect files in hazard archive

4. **Scanner Integration**
   - ClamAV and Microsoft Defender have different interfaces and behaviors
   - Threading issues exist with Microsoft Defender - may require single-threaded mode
   - Defender test must pass before shuttle will run with Defender configuration
   - EICAR test file used for validation

5. **Logging Architecture**
   - Uses direct `get_logger(logging_options=logging_options)` calls (no decorators)
   - Function-level logger context for better debugging
   - `logging_options` parameter passed through call chains
   - Hierarchy logging shows call chains in DEBUG mode

6. **DailyProcessingTracker**
   - Tracks individual files using hash identifiers
   - Thread-safe file tracking with outcome categorization
   - Proper shutdown handling critical for data persistence
   - Source of truth for processing results and metrics

7. **Environment Variables and Deployment**
   - Production deployment requires proper environment variable setup
   - Three deployment phases: manual → cron → systemd service
   - `shuttle_env.sh` file contains required environment variables
   - Path resolution depends on correct environment configuration

## Modification Guidelines

1. **Installation and Configuration System**
   - Maintain script execution order and dependencies
   - Use shared library functions instead of hardcoded commands
   - Preserve YAML configuration structure and validation
   - Test both wizard mode and instruction file mode
   - Ensure cross-platform package management compatibility

2. **Configuration Management**
   - Preserve separation between common and app-specific config
   - Maintain configuration hierarchy precedence
   - Ensure proper type handling (booleans, paths, etc.)
   - Test configuration resolution in different installation modes
   - Validate email notification enhancements (error/summary/hazard recipients)

3. **Code Architecture**
   - Maintain separation between shared library and app-specific code
   - Preserve quarantine-first security model
   - Follow OOP approach for ShuttleApp class
   - Use direct logging calls with `logging_options` parameter
   - Maintain module structure: shuttle_common, shuttle, shuttle_defender_test

4. **Security and Scanning**
   - Preserve file hash tracking throughout processing lifecycle
   - Maintain scanner abstraction for ClamAV/Defender compatibility
   - Ensure proper cleanup of temporary files
   - Test suspect file encryption and hazard archive handling
   - Validate defender test requirements before shuttle execution

5. **Testing and Validation**
   - Run defender test before any Defender-related changes
   - Test with limited disk space to verify throttling
   - Use configurable test runners for parametrized scenarios
   - Test installation scripts in clean environments
   - Validate post-install configuration with different YAML structures

6. **Development Workflow**
   - Always activate virtual environment before development
   - Use `-e` flag for editable installs during development
   - Plan changes in markdown files and discuss before implementing
   - Update both installation flow diagrams when changing processes
   - Test verbose logging and dry-run modes

7. **Deployment Considerations**
   - Test environment variable setup for production deployment
   - Validate cron job configuration and service deployment
   - Ensure proper file permissions and ownership
   - Test Samba configuration if network shares required
   - Validate firewall configuration and security requirements

## Project Conventions

1. **Documentation**
   - Keep documentation straightforward and buzzword-free
   - Focus on technical accuracy over verbose explanations
   - Update process diagrams when workflow changes

2. **Error Messages**
   - Error messages should be clear and actionable
   - Include file paths and specific error details when logging

3. **Code Comments**
   - Comments should explain "why" not just "what"
   - Note any non-obvious security or performance considerations

4. **Deployment**
   - Use the numbered installation scripts in sequence
   - Note which scripts require sudo and which need to be sourced

## Recent Development History

1. **Installation System Standardization (January 2025)**
   - Refactored all installation scripts to use shared library functions
   - Standardized package management across platforms (apt, dnf, yum, pacman, zypper, brew)
   - Added comprehensive `--verbose` parameter support to all scripts
   - Unified configuration file usage display between Python and shell scripts
   - Created installation flow diagrams documenting complete process

2. **Post-Install Configuration System (January 2025)**
   - Built comprehensive YAML-based configuration system
   - Created interactive wizard for production environment setup
   - Implemented five-phase configuration: tools, users/groups, permissions, Samba, firewall
   - Added symbolic path resolution for flexible deployment scenarios
   - Integrated component enablement system for selective configuration

3. **Email Notification Enhancement (December 2024)**
   - Added support for different recipient emails per notification type
   - Implemented `notify_error()`, `notify_summary()`, `notify_hazard()` methods
   - Maintained full backwards compatibility with existing configurations
   - Enhanced configuration options with fallback logic

4. **Logging Architecture Refactoring (January 2025)**
   - Removed problematic `@with_logger` decorator pattern
   - Implemented direct `get_logger(logging_options=logging_options)` calls
   - Added function-level logger context for better debugging
   - Consistent `logging_options` parameter passing through call chains

5. **DailyProcessingTracker Refactoring**
   - Enhanced tracker to store individual file details using hash identifiers
   - Added outcome-specific tracking (success/failure/suspect)
   - Implemented transaction-safe persistence with proper shutdown handling
   - Made tracker the source of truth for processing results and metrics

6. **Shuttle Class Refactoring**
   - Converted from procedural to OOP design (ShuttleApp class)
   - Added proper shutdown hooks for component cleanup
   - Improved object lifecycle management and testability
   - Enhanced integration with DailyProcessingTracker

7. **Environment Variables Documentation**
   - Created comprehensive documentation for production deployment
   - Documented three deployment phases: manual → cron → systemd service
   - Standardized environment file location and structure
   - Added cron job configuration examples and best practices

## User Preferences

1. **Documentation Style**
   - Prefers straightforward, technical documentation without buzzwords
   - Values concise explanations over verbose descriptions
   - Likes ASCII diagrams for visualizing workflows

2. **Development Approach**
   - Appreciates incremental, focused improvements
   - Prefers discussing changes before implementation
   - Values attention to error handling and edge cases
