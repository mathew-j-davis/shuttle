Write-Host "Current username: $env:USERNAME"
Write-Host "Full name: $((Get-WmiObject -Class Win32_ComputerSystem).Username)"
Write-Host "Current user (domain\username): $([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)"
Write-Host "Whoami output: $(whoami)"
Write-Host "User SID: $((Get-WmiObject -Class Win32_UserAccount -Filter "Name='$env:USERNAME'").SID)"