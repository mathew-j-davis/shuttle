# Shuttle Modules

## Shared Library (shuttle_common)

### scan_utils.py
- Handles scanning operations using Microsoft Defender and ClamAV
- Defines scan result types and processing functions
- Implements the `DefenderScanResult` class to standardize scan results

### config.py
- Manages configuration with smart config file search
- Provides `CommonConfig` class for shared settings
- Implements `get_setting_from_arg_or_file` for prioritized settings retrieval

### files.py
- File handling utilities for safe file operations
- Implements file hashing, copying, and integrity verification
- Provides path normalization and safety checks

### logging_setup.py
- Configures logging with file and console output
- Implements `LoggingOptions` for consistent logging settings
- Formats logs with timestamps, levels, filenames, and function names

### logger_injection.py
- Provides `@with_logger` decorator for automatic logger injection
- Implements `get_logger()` for manual logger creation
- Shows call hierarchy in DEBUG mode for better debugging context
- Embeds call chain information into logger names

### notifier.py
- Email notification system for alerts and summaries
- Sends notifications about errors, scan results, and status updates

## Main Application (shuttle_app)

### shuttle.py
- Main entry point for the application
- Handles command-line arguments and initialization
- Manages the overall file processing workflow
- Implements Shuttle class with proper lifecycle management

### shuttle_config.py
- Extends common configuration with app-specific settings
- Manages path settings, processing options, and throttling
- Inherits from CommonConfig for shared settings

### scanning.py
- Implements file scanning and processing logic
- Manages the file transfer workflow
- Integrates with throttling and scan result handling
- Coordinates with DailyProcessingTracker for file metrics

### daily_processing_tracker.py
- Tracks all processed files with unique hash identifiers
- Maintains metrics by outcome (success/failure/suspect)
- Provides transaction-safe persistence for tracking data
- Generates detailed processing reports and summaries
- Handles proper shutdown with pending file management

### throttler.py
- Monitors disk space in critical directories
- Prevents processing when space is low
- Provides detailed space check results

### post_scan_processing.py
- Handles clean and suspect file processing
- Manages hazard archiving and encryption
- Implements source file cleanup

## Defender Test App (shuttle_defender_test_app)

### shuttle_defender_test.py
- Tests Microsoft Defender integration
- Verifies both clean and EICAR test file detection
- Updates ledger with compatibility information

### read_write_ledger.py
- Manages the ledger of tested Defender versions
- Records test results and compatibility information
