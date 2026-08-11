param(
    [string]$InstallRoot = "$env:ProgramData\TUNEL-CORE",
    [string]$SourceRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
)

$ErrorActionPreference = 'Stop'
$ServiceDir = Join-Path $InstallRoot 'service'
$StateDir = Join-Path $InstallRoot 'state'
$LogDir = Join-Path $InstallRoot 'logs'
$ConfigDir = Join-Path $InstallRoot 'config'
$RuntimeDir = Join-Path $InstallRoot 'runtime'
$Venv = Join-Path $RuntimeDir 'venv'

foreach ($dir in @($InstallRoot,$ServiceDir,$StateDir,$LogDir,$ConfigDir,$RuntimeDir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

$Python = $null
foreach ($candidate in @('py.exe','python.exe')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) { $Python = $cmd.Source; break }
}
if (-not $Python) { throw 'Python 3.11+ not found' }

if (-not (Test-Path -LiteralPath (Join-Path $Venv 'Scripts\python.exe'))) {
    if ([IO.Path]::GetFileName($Python) -ieq 'py.exe') {
        & $Python -3 -m venv $Venv
    } else {
        & $Python -m venv $Venv
    }
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create TUNEL-CORE virtual environment' }
}

$VenvPython = Join-Path $Venv 'Scripts\python.exe'
$VenvPythonW = Join-Path $Venv 'Scripts\pythonw.exe'
& $VenvPython -m pip install --disable-pip-version-check --no-deps --upgrade $SourceRoot
if ($LASTEXITCODE -ne 0) { throw 'Failed to install TUNEL-CORE package' }

foreach ($name in @('tunel-core-watchdog.exe','tunel-core-watchdog.ps1','tunel-core-watchdog.xml')) {
    $src = Join-Path $PSScriptRoot "winsw\$name"
    if (-not (Test-Path -LiteralPath $src)) { throw "Missing installer payload: $src" }
    Copy-Item -LiteralPath $src -Destination (Join-Path $ServiceDir $name) -Force
}

$RuntimeConfig = Join-Path $ConfigDir 'runtime.json'
if (-not (Test-Path -LiteralPath $RuntimeConfig)) {
    @{
        schema_version = 1
        supervisor_plugin = $null
        state = 'waiting_runtime_adapter'
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $RuntimeConfig -Encoding UTF8
}

$WatchdogConfig = Join-Path $ConfigDir 'watchdog.json'
$Watchdog = @{
    schema_version = 1
    supervisor = @{
        executable = $VenvPythonW
        arguments = @('-m','tunel_core.runner','--config',$RuntimeConfig,'--interval','5')
        working_directory = $InstallRoot
        process_match = 'tunel_core\.runner'
        heartbeat_timeout_seconds = 30
    }
}
$Watchdog | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $WatchdogConfig -Encoding UTF8

[Environment]::SetEnvironmentVariable('TUNEL_CORE_HOME', $InstallRoot, 'Machine')
[Environment]::SetEnvironmentVariable('TUNEL_CORE_WATCHDOG_CONFIG', $WatchdogConfig, 'Machine')

$Exe = Join-Path $ServiceDir 'tunel-core-watchdog.exe'
Push-Location $ServiceDir
try {
    & $Exe stop 2>$null | Out-Null
    & $Exe uninstall 2>$null | Out-Null
    & $Exe install | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install watchdog service' }
    & $Exe start | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Failed to start watchdog service' }
} finally {
    Pop-Location
}

Set-Service -Name 'TUNELCOREWatchdog' -StartupType Automatic
$service = Get-Service -Name 'TUNELCOREWatchdog' -ErrorAction Stop
if ($service.Status -ne 'Running') { Start-Service -Name 'TUNELCOREWatchdog' }

Start-Sleep -Seconds 3
$Heartbeat = Join-Path $StateDir 'supervisor-heartbeat.json'
Write-Host 'TUNEL_CORE_INSTALLED=True'
Write-Host "INSTALL_ROOT=$InstallRoot"
Write-Host "WATCHDOG_SERVICE=$((Get-Service 'TUNELCOREWatchdog').Status)"
Write-Host "SUPERVISOR_HEARTBEAT=$([bool](Test-Path -LiteralPath $Heartbeat))"
