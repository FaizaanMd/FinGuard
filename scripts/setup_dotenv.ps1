# Sets up the git-ignored .env file with your PostgreSQL credentials.
# Prompts for the password without echoing it to the screen.
#
# Usage:  powershell -ExecutionPolicy Bypass -File .\scripts\setup_dotenv.ps1

$envPath = Join-Path $PSScriptRoot "..\.env"
$envPath = [System.IO.Path]::GetFullPath($envPath)

Write-Host ""
Write-Host "=== FinGuard database configuration ===" -ForegroundColor Cyan
Write-Host "This writes $envPath (git-ignored, not committed)." -ForegroundColor DarkGray

$dbHost    = Read-Host "Database host [localhost]"
$dbPort    = Read-Host "Database port [5432]"
$dbName    = Read-Host "Database name [finguard]"
$dbUser    = Read-Host "Database user [postgres]"

if ([string]::IsNullOrWhiteSpace($dbHost)) { $dbHost = "localhost" }
if ([string]::IsNullOrWhiteSpace($dbPort)) { $dbPort = "5432" }
if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = "finguard" }
if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = "postgres" }

$secure = Read-Host "PostgreSQL password" -AsSecureString
$ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$dbPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)

if ([string]::IsNullOrWhiteSpace($dbPassword)) {
    Write-Host "Password cannot be empty. Aborting." -ForegroundColor Red
    exit 1
}

$lines = @(
    "# PostgreSQL connection details for FinGuard.",
    "# Written by setup_dotenv.ps1; this file is git-ignored.",
    "DB_HOST=$dbHost",
    "DB_PORT=$dbPort",
    "DB_NAME=$dbName",
    "DB_USER=$dbUser",
    "DB_PASSWORD=$dbPassword"
)

Set-Content -Path $envPath -Value $lines -Encoding UTF8
Write-Host ".env written successfully." -ForegroundColor Green

# Optional connectivity test.
$psql = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
if (Test-Path $psql) {
    $env:PGPASSWORD = $dbPassword
    & $psql -h $dbHost -p $dbPort -U $dbUser -d "postgres" -t -c "SELECT version();"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Connection to PostgreSQL OK." -ForegroundColor Green
    } else {
        Write-Host "Could not connect. Check host/port/user/password." -ForegroundColor Yellow
    }
}