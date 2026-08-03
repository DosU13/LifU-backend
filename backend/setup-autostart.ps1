# Run this once, as Administrator, to make the backend and the Cloudflare
# Tunnel start automatically on boot -- independent of anyone actually
# logging into Windows interactively.
#
# Why this needs re-running: the tasks were originally created with an
# "At log on" trigger, which only fires for a real interactive desktop
# logon. Remote/automation access to this machine doesn't count as one, so
# after the processes died once, nothing brought them back. This switches
# both to an "At startup" trigger under an S4U logon (runs as this user,
# without needing the account password stored anywhere) so they come up
# with Windows itself.
#
#     Right-click PowerShell -> Run as Administrator, then:
#     cd D:\Doslan\Desktop\LifU\backend
#     .\setup-autostart.ps1

$ErrorActionPreference = "Stop"

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Not running as Administrator. Right-click PowerShell -> Run as Administrator, then re-run this script."
    exit 1
}

$user = $env:USERNAME
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType S4U -RunLevel Limited

Write-Output "Registering LifU-Backend (at startup, user $user)..."
$backendAction = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument '-NoProfile -ExecutionPolicy Bypass -File "D:\Doslan\Desktop\LifU\backend\run_prod.ps1"'
$backendTrigger = New-ScheduledTaskTrigger -AtStartup
$backendSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "LifU-Backend" -Action $backendAction -Trigger $backendTrigger `
    -Settings $backendSettings -Principal $principal -Force | Out-Null

Write-Output "Registering LifU-Tunnel (at startup, user $user)..."
# Goes through run_tunnel.ps1, not cloudflared.exe directly: at boot, the
# network stack isn't always up yet by the time this trigger fires, and
# Task Scheduler's own RestartOnFailure setting does NOT cover "the process
# launched fine and then exited a few seconds later" -- only "the task
# engine couldn't launch it at all". The wrapper waits for real
# connectivity and retries the launch itself. See run_tunnel.ps1.
$tunnelAction = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument '-NoProfile -ExecutionPolicy Bypass -File "D:\Doslan\Desktop\LifU\backend\run_tunnel.ps1"'
$tunnelTrigger = New-ScheduledTaskTrigger -AtStartup
$tunnelSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "LifU-Tunnel" -Action $tunnelAction -Trigger $tunnelTrigger `
    -Settings $tunnelSettings -Principal $principal -Force | Out-Null

Write-Output ""
Write-Output "Done. Current configuration:"
Get-ScheduledTask -TaskName "LifU-Backend", "LifU-Tunnel" |
    ForEach-Object {
        $trig = $_.Triggers[0]
        [PSCustomObject]@{
            Task    = $_.TaskName
            State   = $_.State
            Trigger = $trig.CimClass.CimClassName
            User    = $_.Principal.UserId
            Logon   = $_.Principal.LogonType
        }
    } | Format-Table -AutoSize

Write-Output "Starting both now so they're live immediately (not just at next boot)..."
Start-ScheduledTask -TaskName "LifU-Backend"
Start-ScheduledTask -TaskName "LifU-Tunnel"
Start-Sleep -Seconds 5

Write-Output ""
Write-Output "Health check:"
try {
    $response = Invoke-WebRequest -Uri "https://lifu-api.doslan.com/api/health" -TimeoutSec 10 -UseBasicParsing
    Write-Output "$($response.StatusCode) $($response.Content)"
} catch {
    Write-Output "Not reachable yet -- give the tunnel a few seconds and check https://lifu-api.doslan.com/api/health manually."
}
