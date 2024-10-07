# Define directories
$sourceDir = "C:\TestEnvironment\Source"
$quarantineDir = "C:\TestEnvironment\Quarantine"
$destDir = "C:\TestEnvironment\Destination"
$logDir = "C:\TestEnvironment\Logs"
$settingsDir = "C:\TestEnvironment\.shuttle"





$settingsFile = Join-Path $settingsDir "settings.txt"

# Create directories
New-Item -ItemType Directory -Force -Path $sourceDir
New-Item -ItemType Directory -Force -Path $tempDir
New-Item -ItemType Directory -Force -Path $destDir
New-Item -ItemType Directory -Force -Path $settingsDir
New-Item -ItemType Directory -Force -Path $logDir
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name


# Create file share for source directory
$shareName = "TestShare"
New-SmbShare -Name $shareName -Path $sourceDir -FullAccess $CurrentUser

# Function to generate random content
function Get-RandomContent {
    # Generate random c alphbetic content
    -join ((65..90) + (97..122) | Get-Random -Count 1000 | ForEach-Object {[char]$_})
}

# Create text files with random content
'a', 'b', 'c' | ForEach-Object {
    $content = Get-RandomContent
    $content | Out-File -FilePath "$sourceDir\$_.txt"
}

# Create settings file
$settings = @"
SourcePath=\\LOCALHOST\$shareName
QuarantinePath=$quarantineDir
DestinationPath=$destDir
LogPath=$logDir
"@

$settings | Out-File -FilePath $settingsFile -Encoding utf8

Write-Host "Test environment setup complete:"
Write-Host "Source directory (shared as $shareName): $sourceDir"
Write-Host "Temp directory: $tempDir"
Write-Host "Destination directory: $destDir"
Write-Host "Files created: a.txt, b.txt, c.txt in the source directory"
Write-Host "Settings file created: $settingsFile"

