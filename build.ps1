param(
    [string]$Version = "0.2.0-dev"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw ".venv Python was not found."
}

Write-Host "=== OBS Now Playing Lite Build ==="
Write-Host "Version: $Version"

# ------------------------------------------------------------
# 1. Clean previous build outputs
# ------------------------------------------------------------

Write-Host "`n[1/4] Cleaning previous build..."

Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue

# ------------------------------------------------------------
# 2. Build executable
# ------------------------------------------------------------

Write-Host "`n[2/4] Building executable..."

& $Python -m PyInstaller `
    --clean `
    --noconfirm `
    OBSNowPlayingLite.spec

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$ExePath = Join-Path $ProjectRoot "dist\OBSNowPlayingLite.exe"

if (-not (Test-Path $ExePath)) {
    throw "Built executable was not found."
}

# ------------------------------------------------------------
# 3. Create release package
# ------------------------------------------------------------

Write-Host "`n[3/4] Creating release package..."

$PackageName = "OBSNowPlayingLite-v$Version"
$PackageDir = Join-Path $ProjectRoot "dist\$PackageName"
$ZipPath = Join-Path $ProjectRoot "dist\$PackageName.zip"

New-Item -ItemType Directory -Path $PackageDir | Out-Null

Copy-Item $ExePath $PackageDir
Copy-Item "README.md" $PackageDir

Compress-Archive `
    -Path "$PackageDir\*" `
    -DestinationPath $ZipPath `
    -Force

# ------------------------------------------------------------
# 4. Show result
# ------------------------------------------------------------

Write-Host "`n[4/4] Build complete."

Write-Host ""
Write-Host "Executable:"
Write-Host "  $ExePath"

Write-Host ""
Write-Host "Release package:"
Write-Host "  $ZipPath"
