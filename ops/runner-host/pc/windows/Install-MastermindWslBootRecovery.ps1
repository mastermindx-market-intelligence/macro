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

function Assert-NotReparsePoint {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    $item = Get-Item -LiteralPath $Path -Force
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing privileged recovery path through a reparse point: $Path"
    }
}

function Set-SealedAcl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [switch]$Directory
    )

    $systemSid = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')
    $adminsSid = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')
    if ($Directory) {
        $acl = New-Object System.Security.AccessControl.DirectorySecurity
        $inheritance = [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
    }
    else {
        $acl = New-Object System.Security.AccessControl.FileSecurity
        $inheritance = [System.Security.AccessControl.InheritanceFlags]::None
    }

    $acl.SetOwner($adminsSid)
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($sid in @($systemSid, $adminsSid)) {
        $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
            $sid,
            [System.Security.AccessControl.FileSystemRights]::FullControl,
            $inheritance,
            [System.Security.AccessControl.PropagationFlags]::None,
            [System.Security.AccessControl.AccessControlType]::Allow
        )
        [void]$acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}

function Assert-SealedAcl {
    param([Parameter(Mandatory = $true)][string]$Path)

    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected) {
        throw "Privileged recovery ACL still inherits permissions: $Path"
    }
    $allowed = @('S-1-5-18', 'S-1-5-32-544')
    $seen = @{}
    foreach ($rule in $acl.Access) {
        $sid = $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
        if (
            $rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow -or
            $sid -notin $allowed
        ) {
            throw "Unexpected principal or deny rule remains on privileged recovery path '$Path': $sid"
        }
        $seen[$sid] = $true
    }
    foreach ($sid in $allowed) {
        if (-not $seen.ContainsKey($sid)) {
            throw "Required privileged principal '$sid' is missing from recovery ACL: $Path"
        }
    }
}

$wsl = Join-Path $env:SystemRoot 'System32\wsl.exe'
$installed = @(& $wsl --list --quiet 2>$null) |
    ForEach-Object { ($_.Replace([string][char]0, '')).Trim() } |
    Where-Object { $_ }
if ($Distribution -notin $installed) {
    throw "Refusing installation: WSL distribution '$Distribution' is not visible to $($identity.Name)."
}

$destination = Join-Path $InstallRoot 'Start-MastermindWslBootRecovery.ps1'
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
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

$task = New-ScheduledTask -Action $action -Trigger @($startupTrigger, $logonTrigger) -Principal $taskPrincipal -Settings $settings -Description 'Keeps the existing Mastermind WSL distro resident after Windows boot/logon. Linux systemd remains runner lifecycle authority.'

if ($PSCmdlet.ShouldProcess("Task Scheduler/$TaskName and $InstallRoot", 'install sealed WSL boot recovery')) {
    # A Highest/S4U task must never execute through an inherited user-writable path.
    # Refuse reparse substitution, replace inherited ACLs with SYSTEM/Admins-only
    # rules, and verify the installed bytes before task registration.
    Assert-NotReparsePoint -Path $InstallRoot
    $null = New-Item -ItemType Directory -Force -Path $InstallRoot
    Assert-NotReparsePoint -Path $InstallRoot
    Set-SealedAcl -Path $InstallRoot -Directory
    Assert-SealedAcl -Path $InstallRoot

    Assert-NotReparsePoint -Path $destination
    Copy-Item -LiteralPath $source -Destination $destination -Force
    Assert-NotReparsePoint -Path $destination
    Set-SealedAcl -Path $destination
    Assert-SealedAcl -Path $destination

    $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    $installedHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
    if ($sourceHash -ne $installedHash) {
        throw "Installed recovery script hash mismatch: source=$sourceHash installed=$installedHash"
    }

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
        InstalledSha256 = $installedHash.ToLowerInvariant()
    }
}
