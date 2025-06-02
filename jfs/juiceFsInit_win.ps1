# 运行目录在iosys下
$baseDir    = (Get-Location).Path
$jfsDir     = Join-Path $baseDir 'jfs'
$juicefsDir = Join-Path $jfsDir 'juicefs'
$cacheDir   = Join-Path $jfsDir 'cache'
$storageDir = Join-Path $jfsDir 'storage'
$metaFile   = Join-Path $jfsDir 'jfs.db'
$mountPoint = Join-Path $baseDir 'fs'

# 创建目录结构
New-Item -Path $juicefsDir -ItemType Directory -Force | Out-Null
New-Item -Path $cacheDir   -ItemType Directory -Force | Out-Null
New-Item -Path $storageDir -ItemType Directory -Force | Out-Null
New-Item -Path $mountPoint -ItemType Directory -Force | Out-Null

# jfs下载
$juicefsTar = Join-Path $juicefsDir 'juicefs-1.2.3-windows-amd64.tar.gz'
$juicefsExe = Join-Path $juicefsDir 'juicefs.exe'
if (-not (Test-Path $juicefsExe)) {
    Write-Host "Downloading JuiceFS 1.2.3 client..."
    Invoke-WebRequest -Uri "https://d.juicefs.com/juicefs/releases/download/v1.2.3/juicefs-1.2.3-windows-amd64.tar.gz" `
                      -OutFile $juicefsTar -ErrorAction Stop
    Write-Host "Download complete. Extracting JuiceFS client..."
    try {
        tar -xf $juicefsTar -C $juicefsDir
    } catch {
        Write-Host "Error: Extraction failed. Please ensure 'tar' is available or extract the archive manually." -ForegroundColor Red
        throw
    }
    # 确保 juicefs.exe 存在
    if (-not (Test-Path $juicefsExe)) {
        Write-Host "Error: juicefs.exe was not found after extraction!" -ForegroundColor Red
        throw
    }
    # 移除 tar.gz 文件
    Remove-Item $juicefsTar -Force
    Write-Host "JuiceFS client extracted to $juicefsExe"
} else {
    Write-Host "JuiceFS client already exists at $juicefsExe. Skipping download."
}

# 检查 WinFsp (FUSE for Windows) 是否已安装
$winFspDir32 = "C:\Program Files (x86)\WinFsp"
$winFspDir64 = "C:\Program Files\WinFsp"
if (-not (Test-Path $winFspDir32) -and -not (Test-Path $winFspDir64)) {
    Write-Host "WinFsp (FUSE for Windows) not detected. Downloading and installing..."
    $winfspMsi = Join-Path $jfsDir 'WinFsp.msi'
    Invoke-WebRequest -Uri "https://github.com/winfsp/winfsp/releases/download/v2.0/winfsp-2.0.23075.msi" `
                      -OutFile $winfspMsi -ErrorAction Stop
    Write-Host "Installing WinFsp..."
    Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$winfspMsi`" /qn /norestart" -Wait
    # 移除安装包
    Remove-Item $winfspMsi -Force
    Write-Host "WinFsp installation completed."
} else {
    Write-Host "WinFsp is already installed. Skipping FUSE installation."
}


# 创建jfs文件
# 暂时使用sqlite3作为元数据存储
$metaPath = [System.IO.Path]::GetFullPath($metafile)
$metaURI  = "sqlite3:///$($metaPath -replace '\\','/')?mode=rwc"

Write-Host "Formatting JuiceFS file system (if not already formatted)..."



$formatArgs = @(
    "format",
    "--storage", "file",
    "--bucket",  $storageDir,
    $metaURI,
    "myjfs"
)
$formatProcess = Start-Process -FilePath $juicefsExe `
                               -ArgumentList $formatArgs `
                               -NoNewWindow -Wait -PassThru



if ($formatProcess.ExitCode -ne 0) {
    Write-Host "Error: 'juicefs format' failed with exit code $($formatProcess.ExitCode)." -ForegroundColor Red
    throw "JuiceFS format failed. Please check the output for details."
} else {
    Write-Host "JuiceFS format step completed (ExitCode 0)."
}

# 挂载（对于python sdk不是必要的）
Write-Host "Mounting JuiceFS file system at $mountPoint ..."
# 确保挂载点目录存在
# 使用后台运行方式挂载
$mountArgs = "mount --cache-dir `"$cacheDir`" --cache-size 1024 `$metaURI `"$mountPoint`" -d"
Start-Process -FilePath $juicefsExe -ArgumentList $mountArgs -WindowStyle Hidden
Write-Host "Mount command executed (running in background)."

# 清理旧的文件
Get-ChildItem -Path $juicefsDir -File | Where-Object { $_.Name -ne "juicefs.exe" } | Remove-Item -Force -Recurse


Write-Host ""
Write-Host "JuiceFS file system 'myjfs' has been mounted to $mountPoint."
Write-Host "To unmount the file system, run:`n  .\jfs\juicefs\juicefs.exe umount .\fs"
Write-Host "To check the status of the file system, run:`n  .\jfs\juicefs\juicefs.exe status sqlite3://./jfs/jfs.db"
