# AI Assistant Guide to the Shuttle Project

This document outlines a structured approach for AI assistants to understand and work with the Shuttle codebase.

## Getting Context

1. **Start with Key Documentation**
   - Read `readme.md` for the system overview and flow diagram
   - Review `readme_architecture.md` to understand component interactions
   - Examine `readme_modules.md` for detailed module descriptions

2. **Understand Configuration**
   - Check `readme_configuration.md` for settings and file formats
   - Note the configuration precedence: CLI args > config file > defaults

3. **Development Environment**
   - Review `readme_development.md` for project structure and environment setup
   - Note virtual environment requirements and package installation

## Code Exploration Strategy

1. **Core Workflow First**
   - Start with `src/shuttle_app/shuttle/shuttle.py` (main entry point)
   - Follow the execution flow through `scanning.py` and `post_scan_processing.py`
   - Understand `throttler.py` for disk space management

2. **Common Library Components**
   - Examine `shuttle_common/config.py` for configuration handling
   - Check `shuttle_common/files.py` for file operations
   - Review `shuttle_common/scan_utils.py` for scanning interfaces

3. **Testing Components**
   - Look at the Defender test app to understand scanner compatibility

## Common Issues to Watch For

1. **Configuration Path Resolution**
   - The app looks for config files in multiple locations
   - Pay attention to path handling across different operating systems

2. **File Integrity Verification**
   - File hashing and verification are critical security components
   - Changes here require careful testing

3. **Scanner Integration**
   - ClamAV and Microsoft Defender have different interfaces
   - Threading issues exist when using Microsoft Defender

4. **Error Handling**
   - Check for proper error handling around file operations
   - Ensure logging is properly configured

## Modification Guidelines

1. **Configuration Changes**
   - Ensure proper type handling (booleans, paths, etc.)

2. **Code Structure**
   - Preserve the separation between common and app-specific code
   - Maintain the quarantine-first security model

3. **Scanning Logic**
   - Be careful with changes to scanning logic or result handling
   - Ensure proper cleanup of temporary files

4. **Testing**
   - Run both scanner tests after any significant changes
   - Test with limited disk space to verify throttling

5. **Development Process**
   - Plan changes in a markdown file and discuss before implementing

## Project Conventions

1. **Documentation**
   - Keep documentation straightforward and buzzword-free
   - Focus on technical accuracy over verbose explanations

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

1. **Configuration Refactoring**
   - Refactored configuration handling to avoid redundant file reading
   - Modified `ShuttleConfig` to inherit from `CommonConfig` properly
   - Updated `parse_common_config` to return both the config object and ConfigParser

2. **Bug Fixes**
   - Fixed import in `shuttle/__init__.py` to reference `shuttle_config.py`
   - Corrected parameter passing in scanning.py (logger vs logging_options)
   - Fixed variable scope issues with throttle_result

3. **Logging Improvements**
   - Enhanced logging format to include filename, line number, and function name
   - Fixed logging setup to properly handle logging options

## User Preferences

1. **Documentation Style**
   - Prefers straightforward, technical documentation without buzzwords
   - Values concise explanations over verbose descriptions
   - Likes ASCII diagrams for visualizing workflows

2. **Development Approach**
   - Appreciates incremental, focused improvements
   - Prefers discussing changes before implementation
   - Values attention to error handling and edge cases
