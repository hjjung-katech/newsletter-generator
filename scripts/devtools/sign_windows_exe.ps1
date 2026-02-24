param(
    [string]$ExePath = "dist\\newsletter_web.exe",
    [string]$CertSha1 = "",
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [string]$SignToolPath = "signtool.exe",
    [switch]$RequireSignature
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -Path $ExePath -PathType Leaf)) {
    throw "EXE not found: $ExePath"
}

if ([string]::IsNullOrWhiteSpace($CertSha1)) {
    if ($RequireSignature.IsPresent) {
        throw "Signing is required but CertSha1 is empty."
    }
    Write-Host "[SIGN] No certificate configured. Skipping signing."
    exit 0
}

$signtool = Get-Command $SignToolPath -ErrorAction SilentlyContinue
if ($null -eq $signtool) {
    throw "signtool not found. Install Windows SDK and ensure signtool.exe is on PATH."
}

Write-Host "[SIGN] Signing EXE: $ExePath"
& $signtool.Source sign /sha1 $CertSha1 /fd SHA256 /td SHA256 /tr $TimestampUrl /d "Newsletter Generator" /v $ExePath
if ($LASTEXITCODE -ne 0) {
    throw "signtool sign failed with exit code $LASTEXITCODE"
}

Write-Host "[SIGN] Verifying signature: $ExePath"
& $signtool.Source verify /pa /v $ExePath
if ($LASTEXITCODE -ne 0) {
    throw "signtool verify failed with exit code $LASTEXITCODE"
}

Write-Host "[SIGN] PASS"
