# Shuttle.ps1 - File Transfer Script
#
# Usage:
#   .\shuttle.ps1 [-SourcePath <network_share_path>] [-DestinationPath <path>] [-TempPath <path>] [-SettingsPath <path>] [-TestSourceWriteAccess]
#
# Description:
#   This script facilitates file transfer operations from a network file share to a destination.
#   It requires write access to the source directory for file deletion after successful transfer.
#
# Parameters:
#   -SourcePath           : (Optional) Path to the source network file share (e.g., \\server\share)
#   -DestinationPath      : (Optional) Path to the destination directory
#   -TempPath             : (Optional) Path to the temporary directory
#   -SettingsPath         : (Optional) Path to the settings file (default: %USERPROFILE%\.shuttle\settings.txt)
#   -TestSourceWriteAccess: (Optional) Test write access to the source directory (default: $false)
#
# Settings File:
#   If not provided as parameters, the script will look for SourcePath, DestinationPath and TempPath
#   in the settings file. A sample settings file (settings.txt) might look like this:
#
#   SourcePath=\\server\share
#   DestinationPath=C:\Users\YourUsername\Documents\Destination
#   TempPath=C:\Temp\ShuttleTemp
#
# Note: Command-line parameters take precedence over settings file values.
#       SourcePath must be a network file share if provided.

param (
    [Parameter(Mandatory=$false)]
    [string]$SourcePath,

    [Parameter(Mandatory=$false)]
    [string]$DestinationPath,

    [Parameter(Mandatory=$false)]
    [string]$TempPath,

    [Parameter(Mandatory=$false)]
    [string]$SettingsPath = "C:/TestEnvironment/.shuttle/settings.txt",

    [Parameter(Mandatory=$false)]
    [switch]$TestSourceWriteAccess = $false
)

# Function to get path from settings or parameter
function Get-PathValue {
    param (
        [string]$ParameterValue,
        [string]$SettingsKey
    )
    Write-Host "ParameterValue: $ParameterValue"
    Write-Host "SettingsKey: $SettingsKey"
    Write-Host "Settings: $Settings"

    
    if ($ParameterValue) {
        Write-Host "ParameterValue is not null"
        return $ParameterValue
    } elseif ($Settings.ContainsKey($SettingsKey)) {

        	
        #$Settings.Get_Item("SettingsKey")
        #Write-Host $Settings.Get_Item($SettingsKey)

        Write-Host $Settings
        Write-Host $SettingsKey
        Write-Host $Settings[$SettingsKey]

        $Settings[$SettingsKey] | Out-String | Write-Host

        Write-Host "SettingsKey is in settings: $Settings[$SettingsKey]"
        return $Settings[$SettingsKey]
    }
    return $null
}

# Initialize $Settings as an empty hashtable
$Settings = @{}

# Check if the settings file exists
if (Test-Path $SettingsPath) {
    # Read settings from the file
    $SettingsContent =  Get-Content $SettingsPath  
    $SettingsTemp = $SettingsContent | ConvertFrom-StringData   

    # Convert the hashtable to a proper hashtable
    # not really sure why I need to do this to be honest, but it works
    # if you know powershell better, could youplease fix it
    # cheers, mat.davis

    For ($i=0; $i -lt $SettingsTemp.Keys.Count; $i++) {
        $Settings[$SettingsTemp.Keys[$i]] = $SettingsTemp.Values[$i]
    }


}

# Get values for SourcePath, DestinationPath and TempPath
$SourcePath = Get-PathValue -ParameterValue $SourcePath -SettingsKey 'SourcePath'
$DestinationPath = Get-PathValue -ParameterValue $DestinationPath -SettingsKey 'DestinationPath'
$TempPath = Get-PathValue -ParameterValue $TempPath -SettingsKey 'TempPath'

# Check if SourcePath is a network path
if ($SourcePath -and -not ($SourcePath -match '^\\\\')) {
    throw "SourcePath must be a network file share (e.g., \\server\share)."
}

Write-Host "SourcePath: $SourcePath"
Write-Host "DestinationPath: $DestinationPath"
Write-Host "TempPath: $TempPath"    

# Check if required paths are provided
if (-not ($SourcePath -and $DestinationPath -and $TempPath)) {
    throw "SourcePath, DestinationPath, and TempPath must all be provided either as parameters or in the settings file."
}

# Prompt for username and password
$Username = Read-Host "Enter username"
$Password = Read-Host "Enter password" -AsSecureString

# Create a PSCredential object
$Credential = New-Object System.Management.Automation.PSCredential ($Username, $Password)

# Attempt to connect to the source path (network file share)
try {
    $sourceDrive = "S:"  # Choose an available drive letter
    New-PSDrive -Name $sourceDrive.TrimEnd(':') -PSProvider FileSystem -Root $SourcePath -Credential $Credential -ErrorAction Stop
    Write-Host "Successfully connected to $SourcePath"
} catch {
    Write-Error "Failed to connect to $SourcePath. Error: $_"
    exit 1
}

# Test write access to the source directory if TestSourceWriteAccess is true
if ($TestSourceWriteAccess) {
    try {
        $testFile = Join-Path -Path $sourceDrive -ChildPath "write_test.tmp"
        New-Item -Path $testFile -ItemType File -ErrorAction Stop | Out-Null
        Remove-Item -Path $testFile -ErrorAction Stop
        Write-Host "Write access confirmed for $SourcePath"
    } catch {
        Write-Error "No write access to $SourcePath. Error: $_"
        Remove-PSDrive -Name $sourceDrive.TrimEnd(':') -Force
        exit 1
    }
}

# Copy all files from source path to temp directory
try {
    if (-not (Test-Path $TempPath)) {
        New-Item -Path $TempPath -ItemType Directory -Force | Out-Null
    }
    
    Copy-Item -Path "$sourceDrive\*" -Destination $TempPath -Recurse -Force
    Write-Host "Successfully copied files from $SourcePath to $TempPath"
} catch {
    Write-Error "Failed to copy files from $SourcePath to $TempPath. Error: $_"
    Remove-PSDrive -Name $sourceDrive.TrimEnd(':') -Force
    exit 1
}

# Scan files in the temp location for malware using Windows Defender
try {
    Write-Host "Scanning files in $TempPath for malware..."
    $scanResult = Start-Process -FilePath "C:\Program Files\Windows Defender\MpCmdRun.exe" -ArgumentList "-Scan -ScanType 3 -File `"$TempPath`"" -Wait -PassThru -NoNewWindow
    
    if ($scanResult.ExitCode -eq 0) {
        Write-Host "Malware scan completed successfully. No threats detected."
    } elseif ($scanResult.ExitCode -eq 2) {
        Write-Error "Malware scan detected threats. Deleting all files in $TempPath"
        Remove-Item -Path "$TempPath\*" -Recurse -Force
        Remove-PSDrive -Name $sourceDrive.TrimEnd(':') -Force
        exit 1
    } else {
        Write-Error "Malware scan failed with exit code: $($scanResult.ExitCode)"
        Remove-Item -Path "$TempPath\*" -Recurse -Force
        Remove-PSDrive -Name $sourceDrive.TrimEnd(':') -Force
        exit 1
    }
} catch {
    Write-Error "Failed to perform malware scan. Error: $_"
    Remove-Item -Path "$TempPath\*" -Recurse -Force
    Remove-PSDrive -Name $sourceDrive.TrimEnd(':') -Force
    exit 1
}

# Copy files from temp to destination and manage source files
try {
    $files = Get-ChildItem -Path $TempPath -Recurse -File

    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($TempPath.Length)
        $destinationFile = Join-Path -Path $DestinationPath -ChildPath $relativePath
        $sourceFile = Join-Path -Path $sourceDrive -ChildPath $relativePath

        # Ensure the destination directory exists
        $destinationDir = Split-Path -Path $destinationFile -Parent
        if (-not (Test-Path -Path $destinationDir)) {
            New-Item -Path $destinationDir -ItemType Directory -Force | Out-Null
        }

        # Copy file to destination
        Copy-Item -Path $file.FullName -Destination $destinationFile -Force -ErrorAction Stop

        # Verify if the file was copied successfully
        if (-not (Test-Path -Path $destinationFile)) {
            throw "Failed to copy file to destination: $($file.FullName)"
        }

        # Delete the file from source directory
        Remove-Item -Path $sourceFile -Force -ErrorAction Stop
        Write-Host "Deleted source file: $sourceFile"

        # Delete the file from temp directory
        Remove-Item -Path $file.FullName -Force
        Write-Host "Copied to destination and removed from temp: $($file.FullName)"
    }

    Write-Host "All files processed successfully."
} catch {
    Write-Error "Error during file processing: $_"
    exit 1
} finally {
    # Clean up any remaining files in temp directory
    Remove-Item -Path "$TempPath\*" -Recurse -Force
    # Remove the temporary PSDrive
    Remove-PSDrive -Name $sourceDrive.TrimEnd(':') -Force
}