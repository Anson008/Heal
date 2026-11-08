<#
.SYNOPSIS
    Builds the HEAL Tool Windows installer and portable zip locally.

.EXAMPLE
    .\build-desktop.ps1 -Version 0.1.0

.NOTES
    Requires Node, uv and Inno Setup 7 or 6 (https://jrsoftware.org/isdl.php).
    Models are taken from api\models. If that folder is missing they are
    downloaded from Hugging Face, which needs $env:HF_TOKEN. Use -FetchModels
    to force a fresh download.
#>
param(
    [string]$Version = "0.1.0",
    [switch]$FetchModels,
    [switch]$SkipSmokeTest
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$web = Join-Path $root "web"
$api = Join-Path $root "api"
$dist = Join-Path $api "dist"

function Invoke-Step([string]$Title, [scriptblock]$Action) {
    Write-Host "`n==> $Title" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Title (exit code $LASTEXITCODE)" }
}

function Find-InnoSetup {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    # Prefer version 7; version 6 still works.
    $candidates = @(
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    throw "Inno Setup not found. Install version 7 from https://jrsoftware.org/isdl.php"
}

foreach ($tool in "node", "npm", "uv") {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "'$tool' was not found on PATH."
    }
}
$iscc = Find-InnoSetup
$env:HEAL_VERSION = $Version

Invoke-Step "Build web UI" {
    Push-Location $web
    try {
        npm ci
        if ($LASTEXITCODE -eq 0) { npm run build:desktop }
    } finally { Pop-Location }
}

Push-Location $api
try {
    Invoke-Step "Install Python dependencies" {
        uv sync --group desktop --no-group training
    }

    if ($FetchModels -or -not (Test-Path (Join-Path $api "models"))) {
        if (-not $env:HF_TOKEN) { throw "Models are missing or a fetch was requested, but HF_TOKEN is not set." }
        Invoke-Step "Fetch models" { uv run python desktop/fetch_models.py }
    } else {
        Write-Host "`n==> Using existing api\models" -ForegroundColor Cyan
    }

    Remove-Item -Recurse -Force (Join-Path $api "build"), $dist -ErrorAction SilentlyContinue

    Invoke-Step "Package with PyInstaller" {
        uv run pyinstaller desktop/heal_tool.spec --noconfirm
    }

    if (-not $SkipSmokeTest) {
        Write-Host "`n==> Smoke test" -ForegroundColor Cyan
        $env:HEALTOOL_SMOKE_TEST = "1"
        $log = Join-Path $env:LOCALAPPDATA "HEALTool\Logs\heal-tool.log"
        Remove-Item $log -ErrorAction SilentlyContinue
        try {
            $process = Start-Process -FilePath (Join-Path $dist "HEALTool\HEALTool.exe") -PassThru
            $finished = $process.WaitForExit(120000)
            if (-not $finished) { $process.Kill() }
            if (-not $finished -or $process.ExitCode -ne 0) {
                # The windowed app has no console, so its errors are in the log.
                if (Test-Path $log) {
                    Write-Host "--- $log ---" -ForegroundColor Yellow
                    Get-Content $log -Tail 40
                }
                throw "Smoke test failed: the packaged app did not start cleanly."
            }
        } finally {
            Remove-Item Env:\HEALTOOL_SMOKE_TEST -ErrorAction SilentlyContinue
        }
    }

    Invoke-Step "Build installer" {
        & $iscc "/DAppVersion=$Version" "desktop\installer\heal_tool.iss"
    }

    Write-Host "`n==> Build portable zip" -ForegroundColor Cyan
    $zip = Join-Path $dist "HEALTool-$Version-windows-portable.zip"
    Compress-Archive -Path (Join-Path $dist "HEALTool") -DestinationPath $zip -Force

    Write-Host "`n==> Checksums" -ForegroundColor Cyan
    $files = Get-ChildItem $dist -File | Where-Object { $_.Name -like "HEALTool-*" -and $_.Extension -in ".exe", ".zip" }
    $lines = foreach ($file in $files) {
        $hash = (Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLower()
        "$hash  $($file.Name)"
    }
    $lines | Set-Content -Path (Join-Path $dist "checksums.txt") -Encoding ascii
} finally {
    Pop-Location
}

Write-Host "`nDone. Release files in $dist :" -ForegroundColor Green
Get-ChildItem $dist -File | ForEach-Object { "{0,10:N1} MB  {1}" -f ($_.Length / 1MB), $_.Name }
