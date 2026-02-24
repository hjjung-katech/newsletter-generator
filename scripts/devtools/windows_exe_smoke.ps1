param(
    [string]$ExePath = "dist\\newsletter_web.exe",
    [string]$BaseUrl = "http://127.0.0.1:5000",
    [int]$TimeoutSeconds = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -Path $ExePath -PathType Leaf)) {
    throw "EXE not found: $ExePath"
}

Write-Host "[SMOKE] Starting EXE: $ExePath"
$process = $null
$healthOk = $false

try {
    $process = Start-Process -FilePath $ExePath -PassThru
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        if ($process.HasExited) {
            throw "EXE exited early with code $($process.ExitCode)"
        }

        try {
            $response = Invoke-WebRequest -Uri "$BaseUrl/health" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200 -and $response.Content) {
                $payload = $response.Content | ConvertFrom-Json
                $status = "$($payload.status)"
                if ($status -in @("healthy", "degraded")) {
                    $healthOk = $true
                    Write-Host "[SMOKE] /health OK with status=$status"
                    break
                }
            }
        } catch {
            # warm-up period: retry until timeout
        }

        Start-Sleep -Seconds 1
    }

    if (-not $healthOk) {
        throw "Health smoke timed out after ${TimeoutSeconds}s"
    }
} finally {
    if ($null -ne $process -and -not $process.HasExited) {
        Write-Host "[SMOKE] Stopping EXE process id=$($process.Id)"
        Stop-Process -Id $process.Id -Force
        Start-Sleep -Seconds 2
    }
}

Write-Host "[SMOKE] PASS"
