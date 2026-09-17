[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Distribution,

    [string]$TaskName = 'Mastermind WSL Boot Recovery',
    [string]$InstallRoot = "$env:ProgramData\Mastermind\runner-recovery"
)

$ErrorActionPreference = 'Stop'

# This value is embedded in Task Scheduler's native command line. Keep the
# accepted registration name deliberately narrow so quotes or control syntax
# cannot alter unattended Highest/S4U argument boundaries.
if ($Distribution -notmatch '^[A-Za-z0-9._ -]+$') {
    throw "Refusing installation: WSL distribution '$Distribution' contains unsupported characters."
}

$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this installer from an elevated PowerShell session.'
}

$source = Join-Path $PSScriptRoot 'Start-MastermindWslBootRecovery.ps1'
if (-not (Test-Path -LiteralPath $source)) {
    throw "Recovery source is missing: $source"
}

$wsl = Join-Path $env:SystemRoot 'System32\wsl.exe'
$installed = @(& $wsl --list --quiet 2>$null) |
    ForEach-Object { ($_ -replace "`0", '').Trim() } |
    Where-Object { $_ }
if ($Distribution -notin $installed) {
    throw "Refusing installation: WSL distribution '$Distribution' is not visible to $($identity.Name)."
}

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
$destination = Join-Path $InstallRoot 'Start-MastermindWslBootRecovery.ps1'
Copy-Item -LiteralPath $source -Destination $destination -Force

$ps = Join-Path $PSHOME 'powershell.exe'
if (-not (Test-Path -LiteralPath $ps)) {
    $ps = 'powershell.exe'
}
$quotedScript = '"' + $destination + '"'
$quotedDistro = '"' + $Distribution + '"'
$arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $quotedScript -Distribution $quotedDistro"

$action = New-ScheduledTaskAction -Execute $ps -Argument $arguments
$startupTrigger = New-ScheduledTaskTrigger -AtStartup
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $identity.Name
# WSL distributions are per-Windows-user. S4U preserves the owner identity without
# storing a password and can run while that user is logged off. AtLogOn is a second
# trigger for machines where the per-user WSL registration is not yet usable at the
# earliest startup edge. IgnoreNew prevents that trigger from spawning a duplicate
# keepalive when the startup instance is already healthy.
$taskPrincipal = New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType S4U -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartCount 6 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

$task = New-ScheduledTask `
    -Action $action `
    -Trigger @($startupTrigger, $logonTrigger) `
    -Principal $taskPrincipal `
    -Settings $settings `
    -Description 'Keeps the existing Mastermind WSL distro resident after Windows boot/logon. Linux systemd remains runner lifecycle authority.'

if ($PSCmdlet.ShouldProcess("Task Scheduler/$TaskName", 'register WSL boot recovery')) {
    Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 3
    $state = Get-ScheduledTask -TaskName $TaskName
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    [pscustomobject]@{
        TaskName = $TaskName
        Principal = $identity.Name
        State = $state.State
        LastRunTime = $info.LastRunTime
        LastTaskResult = $info.LastTaskResult
        Distribution = $Distribution
        InstalledScript = $destination
    }
}
