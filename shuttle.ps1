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
#   -DeleteSourceFilesAfterCopying: (Optional) Delete the source files after copying them to the destination (default: $false)
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
    [switch]$TestSourceWriteAccess = $false,

    [Parameter(Mandatory=$false)]
    [switch]$DeleteSourceFilesAfterCopying = $false
)

# Function to get path from settings or parameter
function Get-PathValue {
    param (
        [string]$ParameterValue,
        [string]$SettingsKey
    )
    Write-Host "ParameterValue: $ParameterValue"
    Write-Host "SettingsKey: $SettingsKey"


    if ($ParameterValue) {
        Write-Host "ParameterValue is not null"
        return $ParameterValue
    } elseif ($Settings.ContainsKey($SettingsKey)) {

        Write-Host $SettingsKey
        Write-Host $Settings[$SettingsKey]

        $Settings[$SettingsKey] | Out-String | Write-Host

        Write-Host "SettingsKey is in settings: $Settings[$SettingsKey]"
        return $Settings[$SettingsKey]
    }
    return $null
}

function Get-FileHashValue {
    param (
        [Parameter(Mandatory=$true)]
        [string]$FilePath,
        [string]$Algorithm = "SHA256"
    )

    try {
        $hash = Get-FileHash -Path $FilePath -Algorithm $Algorithm
        return $hash.Hash
    }
    catch {
        Write-Error "Error calculating hash for $FilePath : $_"
        return $null
    }
}

function Compare-FileHashes {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Hash1,
        [Parameter(Mandatory=$true)]
        [string]$Hash2
    )

    if ($Hash1 -eq $Hash2) {
        return $true
    } else {
        return $false
    }
}

function Test-FileExists {
    param (
        [Parameter(Mandatory=$true)]
        [string]$FilePath
    )

     Write-Host "FilePath: $FilePath"
    if (Test-Path -Path $FilePath -PathType Leaf) {
        Write-Host "File exists: $FilePath"
        return $true
    } else {
        Write-Host "File does not exist: $FilePath"
        return $false
    }
}


function Remove-FileWithLogging {
    param (
        [Parameter(Mandatory=$true)]
        [string]$FilePath
    )

    try {
        Remove-Item -Path $FilePath -Force | Out-Null
        if (-not (Test-Path $FilePath)) {
            #Delete succeeded
            Write-Host "Delete succeeded: $FilePath"
            return $true
        }
    }
    catch {
        #Delete failed
        Write-Host "Delete failed: $FilePath"
    }
    return $false
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
    $sourceDrive = "V:"  # Choose an available drive letter
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
    
    Copy-Item -Path "$sourceDrive\*" -Destination $TempPath -Recurse -Force -Verbose
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

    $tempFiles  = Get-ChildItem -Path $TempPath -Recurse -File

    foreach ($tempFile in $tempFiles) {

        $relativePath = $tempFile.FullName.Substring($TempPath.Length)

        Write-Host "$relativePath"

        $tempFilePath = $tempFile.FullName
        $destinationFilePath = Join-Path -Path $DestinationPath -ChildPath $relativePath
        $sourceFilePath = Join-Path -Path $SourcePath -ChildPath $relativePath

        Write-Host "tempFilePath: $tempFilePath"
        Write-Host "destinationFilePath: $destinationFilePath"
        Write-Host "sourceFilePath: $sourceFilePath"    

        # Ensure the destination directory exists
        $destinationDir = Split-Path -Path $destinationFilePath -Parent
        if (-not (Test-Path -Path $destinationDir)) {
            New-Item -Path $destinationDir -ItemType Directory -Force | Out-Null
        }

        # Copy file to destination
        Copy-Item -Path $tempFilePath -Destination $destinationFilePath -Force -ErrorAction Stop

        # Verify if the file was copied 
        if (-not (Test-Path -Path $destinationFilePath)) {
            throw "Failed to copy file to destination: $($tempFilePath)"
        }

        # Get the hash of the destination file  
        $DestinationFileHash = Get-FileHashValue -FilePath $destinationFilePath

        # Get the hash of the source file
        $SourceFileHash = Get-FileHashValue -FilePath $sourceFilePath

        # Get the hash of the temp file
        $TempFileHash = Get-FileHashValue -FilePath $tempFilePath

        # Verify if the file was copied successfully!
        if(
            (-Not (Compare-FileHashes -Hash1 $SourceFileHash -Hash2 $DestinationFileHash))
        ) {
            throw "After copying files, source and destination files do not match: $relativePath "
        }

        if (
            -Not (Compare-FileHashes -Hash1 $DestinationFileHash -Hash2 $TempFileHash)  
         ) {
            throw "After copying files, temp and destination files do not match: $relativePath "
         }

        Write-Host "Copied to destination successfully: $destinationFilePath"

        # Delete the file from temp directory
        Remove-FileWithLogging -FilePath $tempFilePath

        if ($DeleteSourceFilesAfterCopying) {
            # Delete the file from source directory
            Remove-FileWithLogging -FilePath $sourceFilePath
        }
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