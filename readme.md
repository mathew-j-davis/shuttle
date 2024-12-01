powershell script to move files from a network share, scan for malware, then move to destination location

USE AT OWN RISK, THIS IS STILL UNDER DEVELOPMENT, AND NOT FULLY TESTED.

Roboshuttle.ps1 - Robocopy wrapper script

Usage:
.\roboshuttle.ps1 -SourcePath <network_share_path> -DestinationPath <path> -QuarantinePath <path> -SettingsPath <path> -TestSourceWriteAccess

Ronoshuttle is simpler than shuttle, as it uses robocopy under the hood to move files from source to destination.
However, because of the need to scan the files while they are in the quarantine directory, we cannot rely on robocopy's move feature to delete the source files.

At present the 'delete on successful copy' function is not implemented in roboshuttle.




Shuttle.ps1 - File Transfer Script

Usage:
.\shuttle.ps1 [-SourcePath <network_share_path>] [-DestinationPath <path>] [-QuarantinePath <path>] [-SettingsPath <path>] [-TestSourceWriteAccess]

Description:
This script facilitates file transfer operations from a network file share to a destination.
It requires write access to the source directory for file deletion after successful transfer.

Parameters:
-SourcePath           : (Optional) Path to the source network file share (e.g., \\server\share)
-DestinationPath      : (Optional) Path to the destination directory
-QuarantinePath             : (Optional) Path to the temporary quarantine directory
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



```

  mdatp health

    mdatp definition update

      mdatp threat list


        mdatp scan quick



          mdatp scan full



            mdatp config telemetry --value-enabled | --value-disabled


```