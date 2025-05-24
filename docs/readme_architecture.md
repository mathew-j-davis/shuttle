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
3. **Quarantine** - Copies files to quarantine area
4. **Scanning** - Runs malware scans on quarantined files
5. **Processing** - Handles files based on scan results
   - Clean files → Move to destination
   - Suspect files → Archive or let Defender handle

### Security Model

The system uses a quarantine-first approach where all files are:
1. Copied to a secure quarantine area
2. Scanned for threats
3. Only moved to destination if clean

This ensures the destination directory only ever receives verified safe files.

### Throttling System

The throttling mechanism:
1. Checks available disk space in all relevant directories
2. Prevents file processing if any directory is below threshold
3. Notifies administrators of space issues

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
- Run completion (optional summary)

These can be delivered via email using SMTP configuration.
