# MDATP Simulator

A simulator for Microsoft Defender for Endpoint (MDATP) command-line interface for testing purposes. This simulator mimics the behavior of the real `mdatp` command-line tool but in a controlled, predictable way for development and testing.

## Features

- Responds to common mdatp commands (`version`, `scan`, `status`)
- Returns a fixed version string: `SIMULATOR.ONLY.DO.NOT.USE`
- Flags files with names matching `EICAR*.TXT` as malware (case insensitive)
- Simulates scanning with appropriate output and return codes

## Installation

```bash
# From the tests directory
pip install -e .
```

This will install the `mdatp-simulator` command in your environment.

## Usage

Once installed, you can use the simulator with the same command syntax as the real mdatp:

```bash
# Get version
mdatp-simulator version

# Scan a file
mdatp-simulator scan custom --path /path/to/file

# Get status
mdatp-simulator status
```

## Scan Behavior

When scanning files:
- Files with names matching the pattern `EICAR*.TXT` (case insensitive) will be flagged as malware
- All other files will be reported as clean
- Scanning time is simulated based on file size (larger files take slightly longer)
- Return codes match the real mdatp scanner (0 for clean, 2 for threats found)

## Warning

This simulator is for development and testing purposes only. It does not perform any actual malware scanning and should never be used in production environments or for security validation.
