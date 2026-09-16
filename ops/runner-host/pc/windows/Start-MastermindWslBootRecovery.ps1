[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Distribution,

    [int]$Attempts = 12,
    [int]$RetrySeconds = 10,
    [string]$LogPath = "$env:ProgramData\Mastermind\wsl-boot-recovery.log"
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Write-RecoveryLog {
    param([string]$Message)
    $parent = Split-Path -Parent $LogPath
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $stamp = (Get-Date).ToUniversalTime().ToString('o')
    Add-Content -LiteralPath $LogPath -Value "$stamp $Message"
}

if ($Attempts -lt 1 -or $Attempts -gt 60) {
    throw 'Attempts must be between 1 and 60.'
}
if ($RetrySeconds -lt 1 -or $RetrySeconds -gt 300) {
    throw 'RetrySeconds must be between 1 and 300.'
}

$wsl = Join-Path $env:SystemRoot 'System32\wsl.exe'
if (-not (Test-Path -LiteralPath $wsl)) {
    throw "wsl.exe not found at $wsl"
}

$installed = @(& $wsl --list --quiet 2>$null) |
    ForEach-Object { ($_ -replace "`0", '').Trim() } |
    Where-Object { $_ }
if ($Distribution -notin $installed) {
    $visible = $installed -join ', '
    throw "WSL distribution '$Distribution' is not visible to task principal '$([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)'. Visible distributions: $visible"
}

Write-RecoveryLog "boot-recovery start principal=$([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) distribution=$Distribution"

for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    try {
        # This is intentionally the only mutation. Starting the existing WSL distro
        # lets its already-installed systemd units remain the sole runner lifecycle
        # authority; Windows does not start, stop, relabel, or register runners.
        & $wsl --distribution $Distribution --exec /bin/true
        if ($LASTEXITCODE -ne 0) {
            throw "wsl.exe exited $LASTEXITCODE"
        }

        $running = @(& $wsl --list --running --quiet 2>$null) |
            ForEach-Object { ($_ -replace "`0", '').Trim() } |
            Where-Object { $_ }
        if ($Distribution -notin $running) {
            throw "distribution did not remain in the running census"
        }

        Write-RecoveryLog "boot-recovery healthy attempt=$attempt"
        exit 0
    }
    catch {
        Write-RecoveryLog "boot-recovery retry attempt=$attempt error=$($_.Exception.Message)"
        if ($attempt -lt $Attempts) {
            Start-Sleep -Seconds $RetrySeconds
        }
    }
}

Write-RecoveryLog "boot-recovery failed attempts=$Attempts"
exit 1
