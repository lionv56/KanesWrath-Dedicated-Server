param(
    [string]$Python = (Join-Path $env:LOCALAPPDATA 'KWDS-SSL3-Lab\venv\Scripts\python.exe'),
    [string]$Identity = (Join-Path $env:LOCALAPPDATA 'KWDS-SSL3-Lab\identity'),
    [switch]$PauseProjectGateway
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Prepared isolated Python is missing' }
$runtime = Split-Path (Split-Path (Split-Path $Python))
$logDirectory = Join-Path $runtime ('run-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $logDirectory | Out-Null
$gatewayId = $null
$paused = $false
try {
    if ($PauseProjectGateway) {
        $raw = & docker inspect kaneswrath-dedicated-server-gateway-1
        if ($LASTEXITCODE -ne 0) { throw 'Cannot identify project gateway' }
        $gateway = @($raw | ConvertFrom-Json)[0]
        if ($gateway.Config.Labels.'com.docker.compose.project' -ne 'kaneswrath-dedicated-server' -or
            $gateway.Config.Labels.'com.docker.compose.service' -ne 'gateway') {
            throw 'Gateway identity does not match; refusing to stop it'
        }
        $gatewayId = $gateway.Id
        if ($gateway.State.Running) {
            & docker stop $gatewayId | Out-File (Join-Path $logDirectory 'gateway-stop.txt')
            if ($LASTEXITCODE -ne 0) { throw 'Could not pause gateway' }
            $paused = $true
        }
    }
    if (@(Get-NetTCPConnection -LocalPort 18760 -ErrorAction SilentlyContinue).Count) {
        throw 'Port 18760 remains occupied; no unrelated process will be stopped'
    }
    Write-Host "Server log: $logDirectory\server.jsonl"
    Write-Host 'Starting only the local lab. No game or adapter is started. Stop with Ctrl+C.'
    & $Python -X utf8 -u (Join-Path $PSScriptRoot 'server.py') --identity $Identity --port 18760 2>&1 |
        Tee-Object -FilePath (Join-Path $logDirectory 'server.jsonl')
    if ($LASTEXITCODE -ne 0) { throw "Server exited with code $LASTEXITCODE" }
}
finally {
    if ($paused) {
        & docker start $gatewayId | Out-File (Join-Path $logDirectory 'gateway-restore.txt')
        if ($LASTEXITCODE -ne 0) { Write-Warning "Restore project gateway manually: docker start $gatewayId" }
    }
}
