# Build portable Windows EXE. Sources and final artifacts can stay in OneDrive;
# PyInstaller temporary work/spec files are kept in LOCALAPPDATA to avoid sync locks.
param([switch]$SkipInstall)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$localBase = Join-Path $env:LOCALAPPDATA "NoraShot\Build"
$runPath = Join-Path $localBase ([guid]::NewGuid().ToString("N"))
$workPath = Join-Path $runPath "work"
$specPath = Join-Path $runPath "spec"
$distPath = Join-Path $root "dist"
$buildSucceeded = $false

New-Item -ItemType Directory -Path $workPath, $specPath, $distPath -Force | Out-Null
Push-Location $root
try {
    Write-Host "[NoraShot] Build started | root=$root"
    Write-Host "[NoraShot] Temporary work path | path=$workPath"
    Write-Host "[NoraShot] Temporary spec path | path=$specPath"
    Write-Host "[NoraShot] Output directory | path=$distPath"

    if (-not $SkipInstall) {
        python -m pip install -e ".[dev]"
        if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
    }

    python -m pip check
    if ($LASTEXITCODE -ne 0) { throw "Dependency check failed." }

    $pyiArgs = @(
        "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "NoraShot",
        "--collect-all", "keyring",
        "--collect-data", "botocore",
        "--collect-data", "certifi",
        "--hidden-import", "keyring.backends.Windows",
        "--distpath", $distPath,
        "--workpath", $workPath,
        "--specpath", $specPath,
        "src/norashot/__main__.py"
    )

    & python @pyiArgs
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE." }

    $binary = Join-Path $distPath "NoraShot.exe"
    if (-not (Test-Path -LiteralPath $binary)) { throw "NoraShot.exe was not produced." }

    $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $binary
    $checksumFile = Join-Path $distPath "NoraShot.exe.sha256"
    ($hash.Hash.ToLowerInvariant() + "  NoraShot.exe") |
        Set-Content -LiteralPath $checksumFile -Encoding ascii

    Write-Host "[NoraShot] EXE ready | path=$binary | size=$((Get-Item -LiteralPath $binary).Length) | sha256=$($hash.Hash)"
    Write-Host "[NoraShot] Checksum ready | path=$checksumFile"
    $buildSucceeded = $true
}
finally {
    Pop-Location
    if ($buildSucceeded) {
        try {
            Remove-Item -LiteralPath $runPath -Recurse -Force -ErrorAction Stop
            Write-Host "[NoraShot] Temporary build files cleaned | path=$runPath"
        }
        catch {
            Write-Warning "[NoraShot] Could not clean temporary build folder | path=$runPath | error_type=$($_.Exception.GetType().Name)"
        }
    }
    else {
        Write-Warning "[NoraShot] Build failed; diagnostics retained at $runPath"
    }
}
