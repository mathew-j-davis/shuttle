# Shuttle Architecture

## System Design

Shuttle employs a modular architecture with clear separation of concerns:

```
shuttle_project/
├── src/
│   ├── shuttle_app/            # Main application
│   ├── shuttle_defender_test/  # Defender testing utility
│   └── shared_library/         # Common code
```

## Component Interaction

### File Processing Flow

1. **File Discovery** - Scans source directory for files
2. **Pre-Processing Checks** - Verifies file stability and safety
3. **Quarantine** - Copies files to quarantine area, calculates file hash
4. **File Tracking** - Registers files with DailyProcessingTracker
5. **Scanning** - Runs malware scans on quarantined files
6. **Processing** - Handles files based on scan results
   - Clean files → Move to destination
   - Suspect files → Archive or let Defender handle
7. **Metrics Update** - Updates processing metrics with final outcomes
8. **Cleanup** - Removes temporary files and source files (if configured)

### Security Model

The system uses a quarantine-first approach where all files are:
1. Copied to a secure quarantine area
2. Scanned for threats
3. Only moved to destination if clean

This ensures the destination directory only ever receives verified safe files.

### File Tracking System

The DailyProcessingTracker component:
1. Maintains individual file records using hash identifiers
2. Tracks processing status (pending, completed)
3. Categorizes outcomes (success, suspect, failed)
4. Maintains daily totals for all metrics
5. Provides reporting and summary generation
6. Ensures data persistence with transaction safety

### Throttling System

The throttling mechanism:
1. Checks available disk space in all relevant directories
2. Tracks daily file count and volume limits
3. Prevents file processing if any threshold is exceeded
4. Notifies administrators of throttling conditions
5. Provides detailed throttling reasons for diagnostics

## Configuration System

The configuration system uses a tiered approach to find settings:
1. Command-line arguments (highest priority)
2. Environment variables
3. User configuration files (XDG compliant)
4. System-wide configuration files
5. Default values (lowest priority)

## Notification System

Notifications are triggered for:
- Errors during processing
- Suspect file detection
- Disk space issues
- Throttling events
- Run completion (optional summary)

These can be delivered via email using SMTP configuration.

## Lifecycle Management

The application manages component lifecycles:
1. **Initialization** - Components created and configured
2. **Operation** - Normal processing of files
3. **Shutdown** - Graceful cleanup, including:
   - Saving metrics and tracking data
   - Completing pending file processing
   - Removing temporary files
   - Releasing resources
