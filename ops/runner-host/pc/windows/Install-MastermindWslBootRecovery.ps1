[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Distribution,

    [string]$TaskName = 'Mastermind WSL Boot Recovery',
    [string]$InstallRoot = "$env:ProgramData\Mastermind\runner-recovery"
)

$ErrorActionPreference = 'Stop'

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
$quotedDistro = '"' + $Distribution.Replace('"', '""') + '"'
$arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $quotedScript -Distribution $quotedDistro"

$action = New-ScheduledTaskAction -Execute $ps -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtStartup
# WSL distributions are per-Windows-user. S4U preserves the owner identity without
# storing a password and can run while that user is logged off. The action only
# accesses local resources; network traffic belongs to services inside the WSL VM.
$taskPrincipal = New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType S4U -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartCount 6 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $taskPrincipal -Settings $settings `
    -Description 'Starts the existing Mastermind WSL distro after Windows boot. Linux systemd remains runner lifecycle authority.'

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
