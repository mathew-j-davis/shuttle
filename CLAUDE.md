# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Shuttle is a secure file transfer system with integrated malware scanning. It uses a quarantine-first approach where files are hashed, quarantined, scanned, and then moved to their destination or hazard archive based on scan results.

## Key Commands

### Environment Setup
```bash
# Create and activate virtual environment
./scripts/1_deployment/04_create_venv.sh
source ./scripts/1_deployment/05_activate_venv_CALL_BY_SOURCE.sh

# Install development dependencies
./scripts/1_deployment/06_install_python_dev_dependencies.sh

# Install modules in development mode (-e flag)
./scripts/1_deployment/08_install_shared.sh -e
./scripts/1_deployment/09_install_defender_test.sh -e
./scripts/1_deployment/10_install_shuttle.sh -e
```

### Running Tests
```bash
# Run all tests
python tests/run_tests.py

# Run specific test modules
python -m unittest tests.test_notifier
python -m unittest tests.test_shuttle
python -m unittest tests.test_daily_processing_tracker
python -m unittest tests.test_hierarchy_logging
python -m unittest tests.test_shuttle_hierarchy_integration

# Run configurable test
python tests/run_configurable_shuttle_test.py --thread-count 4 --clean-file-count 10

# Run with MDATP simulator
python tests/run_shuttle_with_simulator.py --source /tmp/src --destination /tmp/dest
```

### Running Shuttle
```bash
# Module method
python3 -m shuttle.shuttle

# Installed command
run-shuttle

# With arguments
run-shuttle --source-path /src --destination-path /dest --quarantine-path /quarantine
```

### Linting and Type Checking
Currently no linting tools are configured in the project.

## Architecture

### Module Structure
- **shuttle_common**: Shared utilities (config, logging, notifications, scanning)
- **shuttle**: Main application with file processing pipeline
- **shuttle_defender_test**: Standalone Microsoft Defender testing utility

### File Processing Pipeline
```
Source → Quarantine (with hash) → Scan → Clean/Suspect → Destination/Hazard Archive
```

### Key Design Patterns
1. **Single Instance**: Lock file prevents concurrent runs
2. **Parallel Processing**: Uses ProcessPoolExecutor with configurable threads
3. **Configuration Hierarchy**: CLI args > config file > defaults
4. **Quarantine-First**: All files quarantined before scanning
5. **Throttling**: Monitors disk space and enforces daily limits

### Important Classes
- `ShuttleConfig`: Main configuration management
- `ShuttleApp`: Core application logic and lifecycle
- `DailyProcessingTracker`: Thread-safe file tracking
- `Throttler`: Disk space and limit monitoring
- `Scanner`: Abstraction for ClamAV/Defender integration
- `get_logger()`: Logger factory with hierarchy support
- `@with_logger`: Decorator for automatic logging injection

### Testing Approach
- Unit tests for individual components
- Integration tests using MDATP simulator
- Configurable tests for different scenarios
- No mocking of file operations - tests use real filesystem

## Development Notes

### Virtual Environment
Always activate the virtual environment before development:
```bash
source src/activate_venv_CALL_BY_SOURCE.sh
```

### Module Installation
Use `-e` flag for editable installs during development to avoid reinstalling after code changes.

### Configuration
- Config file locations: `~/.config/shuttle/`, `/etc/shuttle/`, or via `SHUTTLE_CONFIG_PATH`
- Test configs in `tests/` directory
- Production config example in `example/shuttle_config/`

### Logging
- Logs to syslog and file simultaneously
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- File logs in tracking directory with rotation
- Hierarchy logging with decorators (`@with_logger`) shows call chains in DEBUG mode
- Manual logging available via `get_logger()` for debugging-critical functions
- Logger injection pattern for cross-cutting concerns

### Error Handling
- All exceptions logged with full context
- Email notifications for errors and suspect files
- Graceful shutdown on errors with cleanup

## Recent Changes

### Email Notification Enhancement (December 2024)
Added support for different recipient emails for different notification types:

#### Configuration Changes
- Added to `CommonConfig` dataclass:
  - `notify_recipient_email_error`: Email for error notifications
  - `notify_recipient_email_summary`: Email for summary notifications  
  - `notify_recipient_email_hazard`: Email for hazard/malware notifications
- New CLI arguments: `--notify-recipient-email-error`, `--notify-recipient-email-summary`, `--notify-recipient-email-hazard`
- Config file options: `recipient_email_error`, `recipient_email_summary`, `recipient_email_hazard` in `[notifications]` section

#### Notifier Class Updates
- Constructor now accepts specific email parameters that fallback to main `recipient_email` if not provided
- Refactored `notify()` method to use internal `_send_notification()` helper
- Added new methods:
  - `notify_error()`: Sends to error recipient
  - `notify_summary()`: Sends to summary recipient
  - `notify_hazard()`: Sends to hazard recipient
- Full backwards compatibility maintained

#### Usage Example
```python
# Config file
[notifications]
recipient_email = admin@example.com
recipient_email_error = errors@example.com
recipient_email_summary = reports@example.com
recipient_email_hazard = security@example.com

# Code usage
notifier.notify_error("Critical Error", "Details...")  # Goes to errors@example.com
notifier.notify_summary("Daily Summary", "...")       # Goes to reports@example.com
notifier.notify_hazard("Malware Found", "...")       # Goes to security@example.com
notifier.notify("General Info", "...")               # Goes to admin@example.com
```

#### Updated Files
- `src/shared_library/shuttle_common/config.py`: Added new config fields and parsing
- `src/shared_library/shuttle_common/notifier.py`: Added new methods and fallback logic
- `src/shuttle_app/shuttle/shuttle.py`: Updated Notifier instantiation
- `src/shuttle_defender_test_app/shuttle_defender_test/shuttle_defender_test.py`: Updated Notifier instantiation
- `tests/test_notifier.py`: Added comprehensive tests for new functionality

### Environment Variables Documentation
Created comprehensive documentation for running shuttle via cron/service:
- `/docs/run-cron-service-config.md`: Details on environment variable handling
- Recommended environment file location: `/etc/shuttle/shuttle_env.sh`
- Three methods for cron jobs: source in command, set in crontab, or wrapper script
- Phased deployment approach: manual → cron → systemd service