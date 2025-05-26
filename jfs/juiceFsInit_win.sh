# Windows PowerShell script to install and mount JuiceFS in standalone mode
# Requires: PowerShell 5.1+ on Windows 10/11

# Stop on any error
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

<#
 Configuration block
#>
# JuiceFS version to use (must match Windows binary release tag)
$JuiceVersion = '1.2.3'
# Local mount point (directory to mount to)
$MountPoint = "Z:\\juicefs_mount"
# Directory to store the juicefs.exe binary
$BinDir = ".\\jfs\\juicefs"
# Directory for local cache
$CacheDir = ".\\jfs\\juicefs_cache"
# Path to local metadata DB (absolute path)
$LocalMeta = "${PWD.Path}\\jfs\\meta\\jfs.db"
# Path to storage directory (absolute path)
$LocalStorage = "${PWD.Path}\\jfs\\storage"
# File system name (must be DNS-compatible)
$FsName = 'myjfs'

function Cleanup-Bin {
    # Remove any leftover files except juicefs.exe
    Get-ChildItem -Path $BinDir -File | Where-Object { $_.Name -ne 'juicefs.exe' } | Remove-Item -Force
}

# 1. Ensure WinFsp is installed
Write-Host "Checking WinFsp installation..."
try {
    Get-Command fsptool -ErrorAction Stop | Out-Null
    Write-Host "WinFsp already installed."
} catch {
    Write-Host "Installing WinFsp..."
    $msiUrl = 'https://github.com/winfsp/winfsp/releases/download/v1.11.22373/WinFsp-1.11.22373.msi'
    $msiPath = "$env:TEMP\\WinFsp.msi"
    Invoke-WebRequest -Uri $msiUrl -OutFile $msiPath
    Start-Process msiexec.exe -Wait -ArgumentList '/i', $msiPath, '/quiet', '/norestart'
    Write-Host "WinFsp installation complete."
}

# 2. Download and extract JuiceFS client
Write-Host "Downloading JuiceFS v$JuiceVersion..."
if (-not (Test-Path $BinDir)) { New-Item -Path $BinDir -ItemType Directory | Out-Null }
$zipUrl = "https://github.com/juicedata/juicefs/releases/download/v$JuiceVersion/juicefs-$JuiceVersion-windows-amd64.tar.gz"
$archive = "$env:TEMP\\juicefs.tar.gz"
Invoke-WebRequest -Uri $zipUrl -OutFile $archive
# Extract only juicefs.exe
Write-Host "Extracting juicefs.exe..."
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::ExtractToDirectory($archive, $BinDir)
# Ensure the directory is in PATH
if (-not ($env:PATH -split ';' | Where-Object { $_ -eq $BinDir })) {
    Write-Host "Adding $BinDir to system PATH..."
    [Environment]::SetEnvironmentVariable('Path', $env:Path + ";" + $BinDir, [EnvironmentVariableTarget]::Machine)
}
Cleanup-Bin
Write-Host "JuiceFS client ready in $BinDir"

# 3. Create required directories
Write-Host "Ensuring directories exist..."
$dirs = @($MountPoint, $CacheDir, (Split-Path $LocalMeta), $LocalStorage)
foreach ($d in $dirs) {
    if (-not (Test-Path $d)) { New-Item -Path $d -ItemType Directory | Out-Null }
}

# 4. Initialize standalone file system
Write-Host "Initializing standalone JuiceFS file system..."\& "$BinDir\\juicefs.exe" format `
    --storage "file" `
    --bucket "$LocalStorage" `
    "sqlite:///$LocalMeta?mode=rwc" `
    $FsName

# 5. Mount the file system
Write-Host "Mounting JuiceFS to $MountPoint..."\& "$BinDir\\juicefs.exe" mount `
    --cache-dir "$CacheDir" `
    --cache-size 1024 `
    --background `
    "sqlite:///$LocalMeta" `
    "$MountPoint"

Write-Host "Mount complete!"
Write-Host "Usage:`n  Unmount: juicefs umount $MountPoint`n  Status: juicefs status sqlite:///$LocalMeta"

