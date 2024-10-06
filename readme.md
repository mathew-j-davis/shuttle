powershell script to move files from a network share, scan for malware, then move to destination location


Shuttle.ps1 - File Transfer Script

Usage:
.\shuttle.ps1 [-SourcePath <network_share_path>] [-DestinationPath <path>] [-TempPath <path>] [-SettingsPath <path>] [-TestSourceWriteAccess]

Description:
This script facilitates file transfer operations from a network file share to a destination.
It requires write access to the source directory for file deletion after successful transfer.

Parameters:
-SourcePath           : (Optional) Path to the source network file share (e.g., \\server\share)
-DestinationPath      : (Optional) Path to the destination directory
-TempPath             : (Optional) Path to the temporary directory
-SettingsPath         : (Optional) Path to the settings file (default: %USERPROFILE%\.shuttle\settings.txt)
-TestSourceWriteAccess: (Optional) Test write access to the source directory (default: $false)

Settings File:
If not provided as parameters, the script will look for SourcePath, DestinationPath and TempPath
in the settings file. A sample settings file (settings.txt) might look like this:

SourcePath=\\server\share
DestinationPath=C:\Users\YourUsername\Documents\Destination
TempPath=C:\Temp\ShuttleTemp

Note: Command-line parameters take precedence over settings file values.
SourcePath must be a network file share if provided.