# Build portable Windows EXE with detailed output.
param([switch]$SkipInstall)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $root
try {
    Write-Host "[NoraShot] Build started | root=$root"
    if (-not $SkipInstall) {
        python -m pip install -e ".[dev]"
        if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
    }
    python -m pip check
    if ($LASTEXITCODE -ne 0) { throw "Dependency check failed." }
    python -m PyInstaller --noconfirm --clean --onefile --windowed --name NoraShot --collect-all keyring --collect-data botocore --collect-data certifi --hidden-import keyring.backends.Windows --distpath dist --workpath build/pyinstaller --specpath build src/norashot/__main__.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }
    $binary = Join-Path $root "dist/NoraShot.exe"
    if (-not (Test-Path -LiteralPath $binary)) { throw "NoraShot.exe was not produced." }
    $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $binary
    Write-Host "[NoraShot] EXE ready | path=$binary | size=$((Get-Item $binary).Length) | sha256=$($hash.Hash)"
    $hash.Hash.ToLowerInvariant() + "  NoraShot.exe" | Set-Content -Path (Join-Path $root "dist/NoraShot.exe.sha256") -Encoding ascii
} finally {
    Pop-Location
}
