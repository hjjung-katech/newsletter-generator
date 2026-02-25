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

function Normalize-Thumbprint {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }
    return ($Value -replace "\s+", "").ToUpperInvariant()
}

function Find-CertificateByThumbprint {
    param([string]$Thumbprint)

    $normalized = Normalize-Thumbprint $Thumbprint
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        return $null
    }

    $stores = @("Cert:\CurrentUser\My", "Cert:\LocalMachine\My")
    foreach ($store in $stores) {
        try {
            $cert = Get-ChildItem -Path $store -ErrorAction Stop |
                Where-Object { (Normalize-Thumbprint $_.Thumbprint) -eq $normalized } |
                Select-Object -First 1
            if ($null -ne $cert) {
                return $cert
            }
        } catch {
            continue
        }
    }

    return $null
}

function Verify-SelfSignedDryRunSignature {
    param(
        [string]$Path,
        [string]$ExpectedSha1
    )

    $expected = Normalize-Thumbprint $ExpectedSha1
    if ([string]::IsNullOrWhiteSpace($expected)) {
        return $false
    }

    $signingCert = Find-CertificateByThumbprint $expected
    if ($null -eq $signingCert -or $signingCert.Subject -ne $signingCert.Issuer) {
        return $false
    }

    $signature = Get-AuthenticodeSignature -FilePath $Path
    if ($null -eq $signature -or $null -eq $signature.SignerCertificate) {
        throw "Self-signed fallback verify failed: signer certificate not found."
    }

    $actual = Normalize-Thumbprint $signature.SignerCertificate.Thumbprint
    if ($actual -ne $expected) {
        throw "Self-signed fallback verify failed: signer thumbprint mismatch."
    }
    if ("$($signature.Status)" -eq "NotSigned") {
        throw "Self-signed fallback verify failed: file is not signed."
    }

    Write-Host "[SIGN] Self-signed dry-run signature verified by signer thumbprint."
    return $true
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
$verifyExitCode = $LASTEXITCODE
if ($verifyExitCode -ne 0) {
    Write-Host "[SIGN] /pa verification failed. Checking self-signed dry-run fallback."
    $fallbackVerified = Verify-SelfSignedDryRunSignature -Path $ExePath -ExpectedSha1 $CertSha1
    if (-not $fallbackVerified) {
        throw "signtool verify failed with exit code $verifyExitCode"
    }
}

Write-Host "[SIGN] PASS"
