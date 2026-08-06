<#
.SYNOPSIS
    Windows equivalent of the Makefile — `make` is not available on Windows by default.

.EXAMPLE
    .\run.ps1 up
    .\run.ps1 logs
    .\run.ps1 test
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('help', 'up', 'down', 'restart', 'logs', 'build', 'migrate', 'revision',
                 'shell', 'psql', 'test', 'e2e', 'lint', 'fmt', 'backup', 'clean')]
    [string]$Command = 'help',

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

function Invoke-Compose {
    param([string[]]$ComposeArgs)
    & docker compose @ComposeArgs
    if ($LASTEXITCODE -ne 0) { throw "docker compose $($ComposeArgs -join ' ') failed with exit code $LASTEXITCODE" }
}

switch ($Command) {
    'help' {
        Write-Host ''
        Write-Host '  up        Build if needed and start the site on http://localhost:8000'
        Write-Host '  down      Stop the stack (photographs on .\data are untouched)'
        Write-Host '  restart   Restart the web container'
        Write-Host '  logs      Follow application logs'
        Write-Host '  build     Rebuild the image without cache'
        Write-Host '  migrate   Apply database migrations'
        Write-Host '  revision  Autogenerate a migration:  .\run.ps1 revision "add table"'
        Write-Host '  shell     Shell inside the web container'
        Write-Host '  psql      psql session on the database'
        Write-Host '  test      Run the pytest suite inside the container'
        Write-Host '  e2e       Run Playwright end-to-end tests from the host'
        Write-Host '  lint      Ruff lint + format check'
        Write-Host '  fmt       Ruff autofix + format'
        Write-Host '  backup    Dump the database and archive media into .\data\backups'
        Write-Host '  clean     Stop and remove the database volume (media is NOT deleted)'
        Write-Host ''
    }
    'up' {
        if (-not (Test-Path '.env')) {
            throw "No .env file. Copy .env.example to .env and fill in SECRET_KEY and ADMIN_PASSWORD first."
        }
        New-Item -ItemType Directory -Force -Path 'data\media', 'data\backups' | Out-Null
        Invoke-Compose @('up', '--build', '-d')
        Write-Host ''
        Write-Host '  -> http://localhost:8000   (admin login at /login)' -ForegroundColor Green
    }
    'down'     { Invoke-Compose @('down') }
    'restart'  { Invoke-Compose @('restart', 'web') }
    'logs'     { Invoke-Compose @('logs', '-f', 'web') }
    'build'    { Invoke-Compose @('build', '--no-cache') }
    'migrate'  { Invoke-Compose @('exec', 'web', 'alembic', 'upgrade', 'head') }
    'revision' {
        $message = if ($Rest) { $Rest -join ' ' } else { throw 'Provide a message: .\run.ps1 revision "add table"' }
        Invoke-Compose @('exec', 'web', 'alembic', 'revision', '--autogenerate', '-m', $message)
    }
    'shell'    { Invoke-Compose @('exec', 'web', 'bash') }
    'psql' {
        $pgUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { 'portfolio' }
        $pgDb   = if ($env:POSTGRES_DB)   { $env:POSTGRES_DB }   else { 'portfolio' }
        Invoke-Compose @('exec', 'db', 'psql', '-U', $pgUser, '-d', $pgDb)
    }
    'test'     { Invoke-Compose @('run', '--rm', 'tests') }
    'e2e'      { & uv run pytest e2e }
    'lint'     { & uv run ruff check .; if ($?) { & uv run ruff format --check . } }
    'fmt'      { & uv run ruff check --fix .; & uv run ruff format . }
    'backup'   { & docker compose exec -T db sh -c 'echo ok' | Out-Null; & bash scripts/backup.sh }
    'clean'    { Invoke-Compose @('down', '-v') }
}
