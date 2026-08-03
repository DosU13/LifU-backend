# Wraps `cloudflared tunnel run` with its own retry loop, because Task
# Scheduler's RestartOnFailure setting doesn't cover this failure mode: it
# only restarts a task the *engine* couldn't launch, not one that launched
# fine and then exited on its own a few seconds later.
#
# That's exactly what happened at boot: the LifU-Tunnel task fired at
# system startup, cloudflared launched, then exited within ~8 seconds with
# 0x800700C1 -- almost certainly because the network stack wasn't fully up
# yet that early in boot. Manually re-running the same task moments later
# (network now up) worked immediately. Rather than guess a fixed startup
# delay, this actively waits for real connectivity first, then retries the
# launch itself if cloudflared still exits quickly.
#
# Uses Start-Process -RedirectStandardOutput/-RedirectStandardError rather
# than PowerShell's own `*>>`/`2>&1`: cloudflared logs routinely via stderr
# (every INF/WRN line), and merging that into PowerShell's error stream
# under $ErrorActionPreference = "Stop" turns its first ordinary log line
# into a terminating error, killing the wrapper before it ever connects.
# Start-Process's redirection is raw OS-level file redirection and doesn't
# go through PowerShell's stream machinery at all.

$ErrorActionPreference = "Stop"

$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$logDir = Join-Path $PSScriptRoot "..\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir "tunnel.log"
$stdout = Join-Path $logDir "tunnel-stdout.log"
$stderr = Join-Path $logDir "tunnel-stderr.log"

function Log($msg) {
    "[$(Get-Date -Format o)] $msg" | Add-Content -Path $log
}

Log "run_tunnel.ps1 starting"

$deadline = (Get-Date).AddMinutes(2)
$connected = $false
while ((Get-Date) -lt $deadline) {
    if (Test-Connection -ComputerName 1.1.1.1 -Count 1 -Quiet -ErrorAction SilentlyContinue) {
        $connected = $true
        break
    }
    Start-Sleep -Seconds 2
}
Log "network wait finished, connected=$connected"

$maxAttempts = 10
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    Log "launching cloudflared (attempt $attempt/$maxAttempts)"
    $proc = Start-Process -FilePath $cloudflared -ArgumentList "tunnel", "run", "lifu-backend" `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr -NoNewWindow -PassThru -Wait
    Log "cloudflared exited with code $($proc.ExitCode)"
    if ($attempt -lt $maxAttempts) {
        Start-Sleep -Seconds 10
    }
}

Log "run_tunnel.ps1 giving up after $maxAttempts attempts"
