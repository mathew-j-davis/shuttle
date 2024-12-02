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
#   -QuarantinePath             : (Optional) Path to the quarantine directory
#   -SettingsPath         : (Optional) Path to the settings file (default: %USERPROFILE%\.shuttle\settings.txt)
#   -TestSourceWriteAccess: (Optional) Test write access to the source directory (default: $false)
#   -DeleteSourceFilesAfterCopying: (Optional) Delete the source files after copying them to the destination (default: $false)
#
# Settings File:
#   If not provided as parameters, the script will look for SourcePath, DestinationPath and QuarantinePath
#   in the settings file. A sample settings file (settings.txt) might look like this:
#
#   SourcePath=\\server\share
#   DestinationPath=C:\Users\YourUsername\Documents\Destination
#   QuarantinePath=C:\Temp\ShuttleTemp
#
# Note: Command-line parameters take precedence over settings file values.
#       SourcePath must be a network file share if provided.

param (
    [Parameter(Mandatory=$false)]
    [string]$SourcePath,

    [Parameter(Mandatory=$false)]
    [string]$DestinationPath,

    [Parameter(Mandatory=$false)]
    [string]$QuarantinePath,

    [Parameter(Mandatory=$false)]
    [string]$LogPath,

    [Parameter(Mandatory=$false)]
    [string]$SettingsPath = "C:/TestEnvironment/.shuttle/settings.txt",

    [Parameter(Mandatory=$false)]
    [switch]$TestSourceWriteAccess = $false,

    [Parameter(Mandatory=$false)]
    [switch]$DeleteSourceFilesAfterCopying = $false
)

function Test-ForMalware {
    param (
        [string]$ScanPath,
        [bool]$DeleteFilesOnThreat
    )

    try {
        Write-Host "Scanning files in $ScanPath for malware..."
        $scanResult = Start-Process -FilePath "C:\Program Files\Windows Defender\MpCmdRun.exe" -ArgumentList "-Scan -ScanType 3 -File `"$ScanPath`"" -Wait -PassThru -NoNewWindow
        
        if ($scanResult.ExitCode -eq 0) {
            Write-Host "Malware scan completed successfully. No threats detected."
           return $false
        } else {
            Write-Error "Malware scan failed with exit code: $($scanResult.ExitCode) or threats detected."
        }
    } catch {
        Write-Error "Failed to perform malware scan. Error: $_"
    }

    if ($DeleteFilesOnThreat) {
        Write-Host "Deleting all files in $ScanPath"
        Remove-Item -Path "$ScanPath\*" -Recurse -Force
    }
    return $true
}

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

# Get values for SourcePath, DestinationPath and QuarantinePath
$SourcePath = Get-PathValue -ParameterValue $SourcePath -SettingsKey 'SourcePath'
$DestinationPath = Get-PathValue -ParameterValue $DestinationPath -SettingsKey 'DestinationPath'
$QuarantinePath = Get-PathValue -ParameterValue $QuarantinePath -SettingsKey 'QuarantinePath'
$QuarantineContentsPath = Join-Path -Path $QuarantinePath -ChildPath "/*"
$LogPath = Get-PathValue -ParameterValue $LogPath -SettingsKey 'LogPath'
$LogFile = Join-Path -Path $LogPath -ChildPath "shuttle-$(((get-date).ToUniversalTime()).ToString("yyyyMMddTHHmmssZ")).log"


Write-Host "SourcePath: $SourcePath"
Write-Host "DestinationPath: $DestinationPath"
Write-Host "QuarantinePath: $QuarantinePath"    
Write-Host "LogFile: $LogFile"

# Check if required paths are provided
if (-not ($SourcePath -and $DestinationPath -and $QuarantinePath -and $LogPath)) {
    throw "SourcePath, DestinationPath,  QuarantinePath and LogPathmust all be provided either as parameters or in the settings file."
}

Write-Host "Scanning Source Files for malware..."
$TestSourceForMalwareResult = Test-ForMalware -ScanPath $SourcePath -DeleteFilesOnThreat $false    

if($TestSourceForMalwareResult) {
    Write-Error "Malware detected in Source Files. Exiting..."
    exit 1
}

# Use robocopy to move files from source to quarantine
$robocopyToQuarantineParams = @(
    $SourcePath,
    $QuarantinePath,
    "/E",
    "/DCOPY:DAT",
    "/R:3",
    "/W:10",
    "/j",
    "/UNILOG+:$LogFile"
)

# move logic won't work if we need to scan quarantine and delete if scan fails!!!
# # Add /MOV and /S parameter if DeleteSourceFiles is true
# if ($deleteSourceFiles) {
#     $robocopyToQuarantineParams += 
# }


$robocopyToDestinationParams = @(
    $QuarantinePath,
    $DestinationPath,
    "/E",
    "/DCOPY:DAT",
    "/R:3",
    "/W:10",
    "/j",
    "/UNILOG+:$LogFile",
    "/mov",
    "/s"
)

# Execute robocopy
Write-Host "Copying files from Source to Quarantine..."
$robocopyToQuarantineResult = robocopy @robocopyToQuarantineParams

# Check robocopy exit code
switch ($robocopyToQuarantineResult) {
    {$_ -lt 8} { 
        Write-Host "Files successfully copied/moved from source to quarantine." 
    }
    default { 
        Write-Error "Robocopy encountered errors. Exit code: $_" 
        exit 1
    }
}

Write-Host "Scanning Quarantined Files for malware..."
$TestQuarantineForMalwareResult = Test-ForMalware -ScanPath $QuarantinePath -DeleteFilesOnThreat $true    

if($TestQuarantineForMalwareResult) {
    Write-Error "Malware detected in Quarantined Files. Exiting..."
    exit 1
}

#   Write-Host "Scanning files in $QuarantinePath for malware..."
Write-Host "Copying files from Quarantine to Destination..."
$robocopyToDestinationResult = robocopy @robocopyToDestinationParams

switch ($robocopyToDestinationResult) {
    {$_ -lt 8} { 
        Write-Host "Files successfully moved from quarantine to destination." 
    }
    default { 
        Write-Error "Robocopy encountered errors. Exit code: $_" 
        exit 1
    }
}




# function Get-FileHashValue {
#     param (
#         [Parameter(Mandatory=$true)]
#         [string]$FilePath,
#         [string]$Algorithm = "SHA256"
#     )

#     try {
#         $hash = Get-FileHash -Path $FilePath -Algorithm $Algorithm
#         return $hash.Hash
#     }
#     catch {
#         Write-Error "Error calculating hash for $FilePath : $_"
#         return $null
#     }
# }


# function Compare-FileHashes {
#     param (
#         [Parameter(Mandatory=$true)]
#         [string]$Hash1,
#         [Parameter(Mandatory=$true)]
#         [string]$Hash2
#     )

#     if ($Hash1 -eq $Hash2) {
#         return $true
#     } else {
#         return $false
#     }
# }

# function Test-FileExists {
#     param (
#         [Parameter(Mandatory=$true)]
#         [string]$FilePath
#     )

#      Write-Host "FilePath: $FilePath"
#     if (Test-Path -Path $FilePath -PathType Leaf) {
#         Write-Host "File exists: $FilePath"
#         return $true
#     } else {
#         Write-Host "File does not exist: $FilePath"
#         return $false
#     }
# }


# function Remove-FileWithLogging {
#     param (
#         [Parameter(Mandatory=$true)]
#         [string]$FilePath
#     )

#     try {
#         Remove-Item -Path $FilePath -Force | Out-Null
#         if (-not (Test-Path $FilePath)) {
#             #Delete succeeded
#             Write-Host "Delete succeeded: $FilePath"
#             return $true
#         }
#     }
#     catch {
#         #Delete failed
#         Write-Host "Delete failed: $FilePath"
#     }
#     return $false
# }


# # Add /MOVE parameter if DeleteSourceFiles is true
# if ($deleteSourceFiles) {
#     $robocopyToQuarantineParams += 
# }






# # Prompt for username and password
# $Username = Read-Host "Enter username"
# $Password = Read-Host "Enter password" -AsSecureString

# # Create a PSCredential object
# $Credential = New-Object System.Management.Automation.PSCredential ($Username, $Password)

# # Attempt to connect to the source path (network file share)
# try {
#     $sourceDrive = "V:"  # Choose an available drive letter
#     New-PSDrive -Name $sourceDrive.TrimEnd(':') -PSProvider FileSystem -Root $SourcePath -Credential $Credential -ErrorAction Stop
#     Write-Host "Successfully connected to $SourcePath"
# } catch {
#     Write-Error "Failed to connect to $SourcePath. Error: $_"
#     exit 1
# }

# # Test write access to the source directory if TestSourceWriteAccess is true
# if ($TestSourceWriteAccess) {
#     try {
#         $testFile = Join-Path -Path $sourceDrive -ChildPath "write_test.tmp"
#         New-Item -Path $testFile -ItemType File -ErrorAction Stop | Out-Null
#         Remove-Item -Path $testFile -ErrorAction Stop
#         Write-Host "Write access confirmed for $SourcePath"
#     } catch {
#         Write-Error "No write access to $SourcePath. Error: $_"
#         Remove-PSDrive -Name $sourceDrive.TrimEnd(':') -Force
#         exit 1
#     }
# }

# # Copy all files from source path to temp directory
# try {
#     if (-not (Test-Path $QuarantinePath)) {
#         New-Item -Path $QuarantinePath -ItemType Directory -Force | Out-Null
#     }
    
#     Copy-Item -Path "$sourceDrive\*" -Destination $QuarantinePath -Recurse -Force -Verbose
#     Write-Host "Successfully copied files from $SourcePath to $QuarantinePath"
    
# } catch {
#     Write-Error "Failed to copy files from $SourcePath to $QuarantinePath. Error: $_"
#     Remove-PSDrive -Name $sourceDrive.TrimEnd(':') -Force
#     exit 1
# }

# Scan files in the temp location for malware using Windows Defender


# Copy files from temp to destination and manage source files

# try {

#     $tempFiles  = Get-ChildItem -Path $QuarantinePath -Recurse -File

#     foreach ($tempFile in $tempFiles) {

#         $relativePath = $tempFile.FullName.Substring($QuarantinePath.Length)

#         Write-Host "$relativePath"

#         $tempFilePath = $tempFile.FullName
#         $destinationFilePath = Join-Path -Path $DestinationPath -ChildPath $relativePath
#         $sourceFilePath = Join-Path -Path $SourcePath -ChildPath $relativePath

#         Write-Host "tempFilePath: $tempFilePath"
#         Write-Host "destinationFilePath: $destinationFilePath"
#         Write-Host "sourceFilePath: $sourceFilePath"    

#         # Ensure the destination directory exists
#         $destinationDir = Split-Path -Path $destinationFilePath -Parent
#         if (-not (Test-Path -Path $destinationDir)) {
#             New-Item -Path $destinationDir -ItemType Directory -Force | Out-Null
#         }

#         # Copy file to destination
#         Copy-Item -Path $tempFilePath -Destination $destinationFilePath -Force -ErrorAction Stop

#         # Verify if the file was copied 
#         if (-not (Test-Path -Path $destinationFilePath)) {
#             throw "Failed to copy file to destination: $($tempFilePath)"
#         }

#         # Get the hash of the destination file  
#         $DestinationFileHash = Get-FileHashValue -FilePath $destinationFilePath

#         # Get the hash of the source file
#         $SourceFileHash = Get-FileHashValue -FilePath $sourceFilePath

#         # Get the hash of the temp file
#         $TempFileHash = Get-FileHashValue -FilePath $tempFilePath

#         # Verify if the file was copied successfully!
#         if(
#             (-Not (Compare-FileHashes -Hash1 $SourceFileHash -Hash2 $DestinationFileHash))
#         ) {
#             throw "After copying files, source and destination files do not match: $relativePath "
#         }

#         if (
#             -Not (Compare-FileHashes -Hash1 $DestinationFileHash -Hash2 $TempFileHash)  
#          ) {
#             throw "After copying files, temp and destination files do not match: $relativePath "
#          }

#         Write-Host "Copied to destination successfully: $destinationFilePath"

#         # Delete the file from temp directory
#         Remove-FileWithLogging -FilePath $tempFilePath

#         if ($DeleteSourceFilesAfterCopying) {
#             # Delete the file from source directory
#             Remove-FileWithLogging -FilePath $sourceFilePath
#         }
#     }
#     Write-Host "All files processed successfully."

# } catch {
#     Write-Error "Error during file processing: $_"
#     exit 1
# } finally {
#     # Clean up any remaining files in temp directory
#     Remove-Item -Path "$QuarantinePath\*" -Recurse -Force
#     # Remove the temporary PSDrive
#     Remove-PSDrive -Name $sourceDrive.TrimEnd(':') -Force
# }