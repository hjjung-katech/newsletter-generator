param(
    [string]$ExePath = "dist\\newsletter_web.exe",
    [string]$CertSha1 = "",
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [string]$SignToolPath = "signtool.exe",
    [switch]$RequireSignature
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-SignToolPath {
    param([string]$CandidatePath)

    $cmd = Get-Command $CandidatePath -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        return $cmd.Source
    }

    $searchPatterns = @(
        "C:\\Program Files (x86)\\Windows Kits\\10\\bin\\*\\x64\\signtool.exe",
        "C:\\Program Files (x86)\\Windows Kits\\10\\bin\\*\\x86\\signtool.exe"
    )
    foreach ($pattern in $searchPatterns) {
        $matches = @(
            Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue |
                Sort-Object -Property FullName -Descending
        )
        if ($matches.Count -gt 0) {
            return $matches[0].FullName
        }
    }

    return ""
}

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

$signtoolPath = Resolve-SignToolPath $SignToolPath
if ([string]::IsNullOrWhiteSpace($signtoolPath)) {
    throw "signtool not found. Install Windows SDK and ensure signtool.exe is on PATH."
}
Write-Host "[SIGN] Using signtool: $signtoolPath"

Write-Host "[SIGN] Signing EXE: $ExePath"
& $signtoolPath sign /sha1 $CertSha1 /fd SHA256 /td SHA256 /tr $TimestampUrl /d "Newsletter Generator" /v $ExePath
if ($LASTEXITCODE -ne 0) {
    throw "signtool sign failed with exit code $LASTEXITCODE"
}

Write-Host "[SIGN] Verifying signature: $ExePath"
& $signtoolPath verify /pa /v $ExePath
if ($LASTEXITCODE -ne 0) {
    throw "signtool verify failed with exit code $LASTEXITCODE"
}

Write-Host "[SIGN] PASS"
