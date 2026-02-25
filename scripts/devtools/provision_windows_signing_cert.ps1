param(
    [string]$CertSha1 = "",
    [string]$PfxBase64 = "",
    [string]$PfxPassword = "",
    [string]$CertStoreLocation = "Cert:\CurrentUser\My",
    [switch]$RequireSignature
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Normalize-Thumbprint {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }
    return ($Value -replace "\s+", "").ToUpperInvariant()
}

function Find-Certificate {
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

function Mask-Thumbprint {
    param([string]$Thumbprint)
    $normalized = Normalize-Thumbprint $Thumbprint
    if ($normalized.Length -le 8) {
        return $normalized
    }
    return "{0}...{1}" -f $normalized.Substring(0, 4), $normalized.Substring($normalized.Length - 4)
}

$normalizedSha1 = Normalize-Thumbprint $CertSha1
$hasPfx = -not [string]::IsNullOrWhiteSpace($PfxBase64)
$required = $RequireSignature.IsPresent

if ($required -and [string]::IsNullOrWhiteSpace($normalizedSha1)) {
    throw "Signing is required but WINDOWS_OV_CERT_SHA1 is empty."
}

$existingCert = Find-Certificate $normalizedSha1
if ($null -ne $existingCert) {
    Write-Host ("[SIGN-PROVISION] Existing certificate found: {0}" -f (Mask-Thumbprint $normalizedSha1))
}

if ($null -eq $existingCert -and $hasPfx) {
    if ([string]::IsNullOrWhiteSpace($PfxPassword)) {
        throw "PFX password is required when WINDOWS_OV_CERT_PFX_BASE64 is configured."
    }

    $runnerTemp = [System.Environment]::GetEnvironmentVariable("RUNNER_TEMP")
    if ([string]::IsNullOrWhiteSpace($runnerTemp)) {
        $runnerTemp = [System.IO.Path]::GetTempPath()
    }
    $pfxPath = Join-Path $runnerTemp "windows-ov-signing-cert.pfx"

    try {
        try {
            $pfxBytes = [Convert]::FromBase64String(($PfxBase64 -replace "\s+", ""))
        } catch {
            throw "WINDOWS_OV_CERT_PFX_BASE64 is not valid base64."
        }

        [System.IO.File]::WriteAllBytes($pfxPath, $pfxBytes)
        $securePassword = ConvertTo-SecureString -String $PfxPassword -AsPlainText -Force
        $importedCerts = Import-PfxCertificate -FilePath $pfxPath -Password $securePassword -CertStoreLocation $CertStoreLocation -Exportable
        if ($null -eq $importedCerts -or $importedCerts.Count -eq 0) {
            throw "Import-PfxCertificate returned no certificates."
        }

        $importedCert = $importedCerts | Select-Object -First 1
        $importedThumb = Normalize-Thumbprint $importedCert.Thumbprint
        if ([string]::IsNullOrWhiteSpace($importedThumb)) {
            throw "Imported certificate thumbprint is empty."
        }

        if ([string]::IsNullOrWhiteSpace($normalizedSha1)) {
            $normalizedSha1 = $importedThumb
        } elseif ($normalizedSha1 -ne $importedThumb) {
            throw "WINDOWS_OV_CERT_SHA1 does not match the imported PFX thumbprint."
        }

        Write-Host ("[SIGN-PROVISION] Imported certificate: {0}" -f (Mask-Thumbprint $normalizedSha1))
    } finally {
        Remove-Item -Path $pfxPath -Force -ErrorAction SilentlyContinue
    }
}

if ($required -and -not $hasPfx -and $null -eq $existingCert) {
    throw "Signing is required but certificate material is missing. Configure WINDOWS_OV_CERT_PFX_BASE64 and WINDOWS_OV_CERT_PASSWORD."
}

if (-not [string]::IsNullOrWhiteSpace($normalizedSha1)) {
    $resolvedCert = Find-Certificate $normalizedSha1
    if ($null -eq $resolvedCert) {
        throw ("Certificate not found after provisioning: {0}" -f (Mask-Thumbprint $normalizedSha1))
    }
    Write-Host ("[SIGN-PROVISION] Certificate ready: {0}" -f (Mask-Thumbprint $normalizedSha1))
} elseif ($required) {
    throw "Signing is required but no certificate thumbprint is available."
} else {
    Write-Host "[SIGN-PROVISION] Signing optional and certificate is not configured."
}

if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_OUTPUT)) {
    "resolved_cert_sha1=$normalizedSha1" >> $env:GITHUB_OUTPUT
}
