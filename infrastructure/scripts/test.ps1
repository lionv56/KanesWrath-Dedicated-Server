$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..\.."))

docker compose config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose configuratie ongeldig."
}

Write-Host "Docker Compose configuratie geldig." -ForegroundColor Green