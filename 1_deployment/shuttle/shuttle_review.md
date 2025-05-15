# Shuttle Module Review

## Entry Point Functionality
- **Main Function**: Ensure the `main()` function correctly orchestrates the startup sequence.
  - Parses configuration.
  - Handles lock file creation and deletion.
  - Sets up logging.
  - Initializes notifier if required.
  - Checks for required external commands.
  - Validates required paths.
  - Ensures at least one virus scanner is specified.
  - Loads and checks the defender ledger if necessary.
  - Calls `process_files()` with the correct arguments.

## Configuration Parsing
- **parse_config()**: Verify that this function correctly parses and validates the configuration settings.

## File Processing
- **process_files()**: Ensure this function handles file transfers and scanning as expected.

## Logging
- **setup_logging()**: Confirm that logging is set up correctly with the specified log level and file path.

## Notification
- **Notifier**: Ensure the notifier is correctly initialized and used to send notifications if required.

## Defender Utilities
- **defender_utils.get_mdatp_version()**: Verify that this function correctly retrieves the Microsoft Defender version.

## Ledger
- **Ledger**: Ensure the ledger is correctly loaded and used to check if the current version of Microsoft Defender has been tested.

# Common Modules Review

## Defender Utilities
- **defender_utils**: Review the utility functions related to Microsoft Defender to ensure they work as intended.

## Ledger
- **Ledger**: Ensure the ledger class correctly handles loading and checking of versions.

## Notifier
- **Notifier**: Verify that the notifier class correctly sends emails with the provided configuration.

## Logging Setup
- **logging_setup**: Ensure that the logging setup is correctly configured and used throughout the application.

## Additional Considerations
- **Error Handling**: Review the error handling in `main()` to ensure all exceptions are caught and logged appropriately.
- **External Commands**: Ensure that the checks for external commands (`lsof`, `mdatp`, `gpg`) are correctly implemented.
- **File Path Validations**: Verify that all file path validations are correctly implemented and handle edge cases appropriately.
- **Virus Scanning**: Ensure that both Microsoft Defender and ClamAV scanning are correctly implemented and integrated.
- **Quarantine Process**: Verify that the quarantine process is correctly implemented and files are moved to the quarantine path as expected.
- **Hazard Archive Encryption**: Ensure that hazard archive encryption is correctly implemented and the encryption key file is handled properly.
