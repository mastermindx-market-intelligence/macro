[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Distribution,

    [int]$RetrySeconds = 15,
    [int]$MaxRetrySeconds = 60,
    [string]$LogPath = "$env:ProgramData\Mastermind\wsl-boot-recovery.log"
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Write-RecoveryLog {
    param([string]$Message)
    try {
        $parent = Split-Path -Parent $LogPath
        if ($parent) {
            New-Item -ItemType Directory -Force -Path $parent | Out-Null
        }
        $stamp = (Get-Date).ToUniversalTime().ToString('o')
        Add-Content -LiteralPath $LogPath -Value "$stamp $Message"
    }
    catch {
        # Logging is evidence, not lifecycle authority. A transient filesystem
        # problem must never terminate the only WSL residency supervisor.
    }
}

if ($RetrySeconds -lt 1 -or $RetrySeconds -gt 300) {
    throw 'RetrySeconds must be between 1 and 300.'
}
if ($MaxRetrySeconds -lt $RetrySeconds -or $MaxRetrySeconds -gt 900) {
    throw 'MaxRetrySeconds must be >= RetrySeconds and <= 900.'
}

$wsl = Join-Path $env:SystemRoot 'System32\wsl.exe'
$keepalive = 'while :; do sleep 3600; done'
$failureCount = 0
Write-RecoveryLog "boot-recovery supervisor-start principal=$([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) distribution=$Distribution"

# This task is the existing Windows-side WSL residency owner. It intentionally
# never exhausts a retry budget: if WSL crashes or its launcher is transiently
# unavailable, the supervisor keeps retrying until Windows itself stops the task.
# Linux systemd remains the runner/service lifecycle authority; this process never
# registers, relabels, starts, stops, or dispatches a GitHub runner.
while ($true) {
    try {
        if (-not (Test-Path -LiteralPath $wsl)) {
            throw "wsl.exe not found at $wsl"
        }

        $rawInstalled = @(& $wsl --list --quiet 2>$null)
        $listExitCode = $LASTEXITCODE
        if ($listExitCode -ne 0) {
            throw "wsl.exe --list failed code=$listExitCode"
        }
        $installed = $rawInstalled |
            ForEach-Object { ($_.Replace([string][char]0, '')).Trim() } |
            Where-Object { $_ }
        if ($Distribution -notin $installed) {
            $visible = $installed -join ', '
            throw "WSL distribution '$Distribution' is not visible to task principal '$([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)'. Visible distributions: $visible"
        }

        Write-RecoveryLog "boot-recovery keepalive-launch failures_before_start=$failureCount"
        $started = Get-Date
        & $wsl --distribution $Distribution --exec /bin/sh -c $keepalive
        $exitCode = $LASTEXITCODE
        $runtimeSeconds = [int]((Get-Date) - $started).TotalSeconds
        if ($runtimeSeconds -ge 300) {
            $failureCount = 0
        }
        throw "WSL keepalive exited unexpectedly code=$exitCode runtime_seconds=$runtimeSeconds"
    }
    catch {
        $failureCount++
        $multiplier = [Math]::Min($failureCount, 4)
        $delaySeconds = [Math]::Min($MaxRetrySeconds, $RetrySeconds * $multiplier)
        Write-RecoveryLog "boot-recovery retry failure_count=$failureCount delay_seconds=$delaySeconds error=$($_.Exception.Message)"
        Start-Sleep -Seconds $delaySeconds
    }
}
