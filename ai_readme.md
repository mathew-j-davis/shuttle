# AI Assistant Guide to the Shuttle Project

This document outlines a structured approach for AI assistants to understand and work with the Shuttle codebase.

## Getting Context

1. **Start with Key Documentation**
   - Read `readme.md` for the system overview and flow diagram
   - Review `docs/readme_architecture.md` to understand component interactions
   - Examine `docs/readme_modules.md` for detailed module descriptions
   - Check `dev_notes/shuttle_test_architecture.md` for detailed test architecture
   - See `dev_notes/updated_shuttle_process_diagram.md` for the latest execution flow

2. **Understand Configuration**
   - Check `docs/readme_configuration.md` for settings and file formats
   - Note the configuration precedence: CLI args > config file > defaults

3. **Development Environment**
   - Review `docs/readme_development.md` for project structure and environment setup
   - Note virtual environment requirements and package installation

## Code Exploration Strategy

1. **Core Workflow First**
   - Start with `src/shuttle_app/shuttle/shuttle.py` (main entry point)
   - Follow the execution flow through `scanning.py` and `post_scan_processing.py`
   - Understand `daily_processing_tracker.py` for file tracking and metrics
   - Review `throttler.py` for disk space management
   - Review `throttle_utils.py` for throttling implementation details

2. **Common Library Components**
   - Examine `shuttle_common/config.py` for configuration handling
   - Check `shuttle_common/files.py` for file operations
   - Review `shuttle_common/scan_utils.py` for scanning interfaces

3. **Testing Components**
   - Understand `tests/test_shuttle_multithreaded.py` for throttling test structure
   - Examine `tests/run_shuttle_with_simulator.py` for the MDATP simulator integration
   - Review `tests/README_multithreaded_tests.md` for test documentation
   - Study `tests/test_daily_processing_tracker.py` for file tracking test implementation
   - Check `tests/run_configurable_throttling_test.py` for configurable test runner

## Common Issues to Watch For

1. **Configuration Path Resolution**
   - The app looks for config files in multiple locations
   - Pay attention to path handling across different operating systems

2. **File Integrity Verification**
   - File hashing and verification are critical security components
   - Changes here require careful testing
   - Hash calculation has been moved to `quarantine_files_for_scanning` from `scan_and_process_file`

3. **Scanner Integration**
   - ClamAV and Microsoft Defender have different interfaces
   - Threading issues exist when using Microsoft Defender

4. **Error Handling**
   - Check for proper error handling around file operations
   - Ensure logging is properly configured

5. **DailyProcessingTracker Usage**
   - Now tracks individual files using file hash identifiers
   - Proper shutdown handling is critical for data persistence
   - Results tracking now categorized by outcome (success/failure/suspect)

## Modification Guidelines

1. **Configuration Changes**
   - Ensure proper type handling (booleans, paths, etc.)
   - Preserve the separation between common and app-specific config

2. **Code Structure**
   - Preserve the separation between common and app-specific code
   - Maintain the quarantine-first security model
   - Follow the OOP approach for the Shuttle class

3. **Scanning Logic**
   - Be careful with changes to scanning logic or result handling
   - Ensure proper cleanup of temporary files
   - Maintain file hash tracking for the entire processing lifecycle

4. **Testing**
   - Run both scanner tests after any significant changes
   - Test with limited disk space to verify throttling
   - Use the configurable test runner for parametrized testing

5. **Development Process**
   - Plan changes in a markdown file and discuss before implementing
   - Create test plans and update test files for new functionality

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

1. **DailyProcessingTracker Refactoring**
   - Enhanced tracker to store individual file details using hash identifiers
   - Added outcome-specific tracking (success/failure/suspect)
   - Implemented transaction-safe persistence for file data
   - Added proper shutdown handling with pending file management
   - Added comprehensive reporting and summary generation
   - Made tracker the source of truth for processing results

2. **Shuttle Class Refactoring**
   - Converted Shuttle from procedural to OOP design
   - Added proper shutdown hooks for component cleanup
   - Improved object lifecycle management
   - Enhanced testability for unit and integration tests

3. **Scanning Pipeline Enhancement**
   - Moved file hash calculation earlier in the process for better tracking
   - Updated task result processing to handle different outcomes
   - Improved error handling and recovery during scanning
   - Enhanced result collection and reporting

4. **Test Infrastructure Improvements**
   - Added dedicated test files for DailyProcessingTracker
   - Created configurable test runners for parametrized testing
   - Implemented multithreaded test scenarios
   - Added simulator integration for repeatable testing

5. **Configuration Refinement**
   - Improved configuration handling and validation
   - Enhanced error messages for configuration issues
   - Better separation between common and app-specific settings

## User Preferences

1. **Documentation Style**
   - Prefers straightforward, technical documentation without buzzwords
   - Values concise explanations over verbose descriptions
   - Likes ASCII diagrams for visualizing workflows

2. **Development Approach**
   - Appreciates incremental, focused improvements
   - Prefers discussing changes before implementation
   - Values attention to error handling and edge cases
