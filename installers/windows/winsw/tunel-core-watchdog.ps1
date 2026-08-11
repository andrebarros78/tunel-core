$ErrorActionPreference='SilentlyContinue'
$TaskName='WINDOWS-MCP-PERSISTENT-GUARD'
$GuardScript='D:\Projetos\WINDOWS-MCP-TEST\.tunnel-client\guardian\windows-mcp-persistent-guard.ps1'
$Log='D:\Projetos\TUNEL-CORE\logs\windows-service-watchdog.log'
function Log([string]$m){"$(Get-Date -Format o) $m" | Add-Content -LiteralPath $Log -Encoding UTF8}
Log 'SERVICE_WATCHDOG_START'
while($true){
  try{
    $sessions = @(Get-CimInstance Win32_LogonSession -ErrorAction SilentlyContinue | Where-Object {$_.LogonType -in 2,10})
    if($sessions.Count -gt 0 -and (Test-Path -LiteralPath $GuardScript)){
      $guard = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {$_.Name -eq 'powershell.exe' -and $_.CommandLine -match 'windows-mcp-persistent-guard\.ps1'} | Select-Object -First 1
      if(-not $guard){
        schtasks.exe /Run /TN $TaskName 2>&1 | Out-Null
        Start-Sleep -Seconds 3
        $guard = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {$_.Name -eq 'powershell.exe' -and $_.CommandLine -match 'windows-mcp-persistent-guard\.ps1'} | Select-Object -First 1
        if($guard){Log "GUARD_RECOVERED PID=$($guard.ProcessId)"}else{Log 'GUARD_RECOVERY_DEFERRED'}
      }
    }
  }catch{Log "WATCHDOG_ERROR $($_.Exception.Message)"}
  Start-Sleep -Seconds 20
}
