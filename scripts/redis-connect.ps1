param(
  [string]$Url
)
$ErrorActionPreference = "Stop"

# Prefer explicit parameter, then REDIS_URL env var
if (-not $Url -or $Url.Trim() -eq "") {
  $Url = $env:REDIS_URL
}

if (-not $Url -or $Url.Trim() -eq "") {
  Write-Host "REDIS_URL is not set and no -Url was provided." -ForegroundColor Yellow
  Write-Host "Usage: scripts\redis-connect.ps1 -Url redis://default:{{REDIS_PASSWORD}}@host:port" -ForegroundColor Yellow
  Write-Host "Or set: $env:REDIS_URL='redis://default:{{REDIS_PASSWORD}}@host:port' and run scripts\redis-connect.ps1" -ForegroundColor Yellow
  exit 1
}

# Basic sanity check
if ($Url -notmatch '^redis(s)?://') {
  Write-Host "Provided value does not look like a Redis URL (redis://...)." -ForegroundColor Yellow
}

# Ensure redis-cli is available
if (-not (Get-Command redis-cli -ErrorAction SilentlyContinue)) {
  Write-Host "redis-cli not found on PATH." -ForegroundColor Red
  Write-Host "Install Redis tools, or use Docker as a fallback:" -ForegroundColor Yellow
  Write-Host "  docker run -it --rm redis:7-alpine redis-cli -u `"$Url`"" -ForegroundColor Yellow
  exit 1
}

# Print a non-sensitive connection notice
try {
  $uri = [System.Uri]$Url
  $hostPort = if ($uri.Port -gt 0) { "$($uri.Host):$($uri.Port)" } else { $uri.Host }
  Write-Host ("Connecting to redis://" + $hostPort + " ...")
} catch {
  Write-Host "Connecting to Redis ..."
}

# Connect
& redis-cli -u $Url

