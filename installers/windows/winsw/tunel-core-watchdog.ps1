$ErrorActionPreference = 'Stop'

$Base = Split-Path -Parent $MyInvocation.MyCommand.Path
$HomeRoot = if ($env:TUNEL_CORE_HOME) { $env:TUNEL_CORE_HOME } else { Join-Path $env:ProgramData 'TUNEL-CORE' }
$ConfigPath = if ($env:TUNEL_CORE_WATCHDOG_CONFIG) { $env:TUNEL_CORE_WATCHDOG_CONFIG } else { Join-Path $Base 'tunel-core-watchdog.json' }
$LogRoot = Join-Path $HomeRoot 'logs'
$LogPath = Join-Path $LogRoot 'watchdog.log'

New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null

function Write-CoreLog([string]$Message) {
    "$(Get-Date -Format o) $Message" | Add-Content -LiteralPath $LogPath -Encoding UTF8
}

function Read-WatchdogConfig {
    if (-not (Test-Path -LiteralPath $ConfigPath)) { return $null }
    $cfg = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $cfg.supervisor.executable) { throw 'watchdog config missing supervisor.executable' }
    if (-not $cfg.supervisor.process_match) { throw 'watchdog config missing supervisor.process_match' }
    return $cfg
}

function Get-SupervisorProcess($Config) {
    $pattern = [string]$Config.supervisor.process_match
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -match $pattern } |
        Select-Object -First 1
}

function Start-Supervisor($Config) {
    $exe = [Environment]::ExpandEnvironmentVariables([string]$Config.supervisor.executable)
    $args = @()
    if ($Config.supervisor.arguments) { $args = @($Config.supervisor.arguments | ForEach-Object { [Environment]::ExpandEnvironmentVariables([string]$_) }) }
    $work = if ($Config.supervisor.working_directory) {
        [Environment]::ExpandEnvironmentVariables([string]$Config.supervisor.working_directory)
    } else {
        Split-Path -Parent $exe
    }
    Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory $work -WindowStyle Hidden | Out-Null
}

Write-CoreLog 'WATCHDOG_START'

while ($true) {
    try {
        $cfg = Read-WatchdogConfig
        if ($null -eq $cfg) {
            Write-CoreLog "WAIT_CONFIG path=$ConfigPath"
        } else {
            $supervisor = Get-SupervisorProcess $cfg
            if ($null -eq $supervisor) {
                Start-Supervisor $cfg
                Start-Sleep -Seconds 2
                $supervisor = Get-SupervisorProcess $cfg
                if ($supervisor) {
                    Write-CoreLog "SUPERVISOR_RECOVERED pid=$($supervisor.ProcessId)"
                } else {
                    Write-CoreLog 'SUPERVISOR_RECOVERY_DEFERRED'
                }
            }
        }
    } catch {
        Write-CoreLog "WATCHDOG_ERROR $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 20
}
