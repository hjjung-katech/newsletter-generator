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
$stdoutLog = Join-Path -Path ([System.IO.Path]::GetTempPath()) -ChildPath "newsletter_web_smoke_stdout.log"
$stderrLog = Join-Path -Path ([System.IO.Path]::GetTempPath()) -ChildPath "newsletter_web_smoke_stderr.log"
$uri = [Uri]$BaseUrl
$smokePort = $uri.Port
$previousPort = $env:PORT

if (Test-Path -Path $stdoutLog -PathType Leaf) {
    Remove-Item -Path $stdoutLog -Force
}
if (Test-Path -Path $stderrLog -PathType Leaf) {
    Remove-Item -Path $stderrLog -Force
}

try {
    $env:PORT = "$smokePort"
    $process = Start-Process -FilePath $ExePath -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
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
    if ($null -eq $previousPort) {
        Remove-Item Env:PORT -ErrorAction SilentlyContinue
    } else {
        $env:PORT = $previousPort
    }

    if ($null -ne $process -and -not $process.HasExited) {
        Write-Host "[SMOKE] Stopping EXE process id=$($process.Id)"
        Stop-Process -Id $process.Id -Force
        Start-Sleep -Seconds 2
    }

    if ($null -ne $process -and $process.HasExited -and -not $healthOk) {
        Write-Host "[SMOKE] Process exited with code $($process.ExitCode)"
        if (Test-Path -Path $stdoutLog -PathType Leaf) {
            Write-Host "[SMOKE] --- stdout ---"
            Get-Content -Path $stdoutLog
        }
        if (Test-Path -Path $stderrLog -PathType Leaf) {
            Write-Host "[SMOKE] --- stderr ---"
            Get-Content -Path $stderrLog
        }
    }
}

Write-Host "[SMOKE] PASS"
