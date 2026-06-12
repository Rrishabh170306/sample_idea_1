Param(
    [switch]$NoDocker,
    [int]$BackendPort = 8000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Log {
    param([string]$msg)
    $t = Get-Date -Format o
    "$t`t$msg" | Tee-Object -FilePath pipeline_log.txt -Append
}

Log "Starting pipeline run"

Push-Location (Join-Path $PSScriptRoot "..")

# detect workspace venv python
$workspaceRoot = (Resolve-Path "$(Join-Path $PSScriptRoot ".." )\..\.." -ErrorAction SilentlyContinue)
if ($workspaceRoot) { $workspaceRoot = $workspaceRoot.ProviderPath } else { $workspaceRoot = (Get-Location).Path }
$venvPython = Join-Path $workspaceRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) { $PY = $venvPython } else { $PY = "python" }

# 1) Run backend tests
Log "Running backend unit tests"
if (Test-Path "backend/tests") {
    try {
        & $PY -m pytest "backend/tests" -q | Tee-Object -FilePath pytest_backend.log
        Log "Backend tests passed"
    } catch {
        Log "Backend tests failed"
        exit 1
    }
} else {
    Log "No backend tests folder found; skipping pytest"
}

# 2) Apply migrations if alembic present
if (Test-Path "backend/alembic") {
    Log "Applying alembic migrations"
    Push-Location "backend"
    try {
        # prefer alembic CLI in venv Scripts folder
        $venvScripts = Split-Path $PY -Parent
        $alembicExe = Join-Path $venvScripts "alembic.exe"
        $alembicScript = Join-Path $venvScripts "alembic"
        if (Test-Path $alembicExe) {
            & $alembicExe upgrade head | Tee-Object -FilePath alembic_upgrade.log
        } elseif (Test-Path $alembicScript) {
            & $alembicScript upgrade head | Tee-Object -FilePath alembic_upgrade.log
        } else {
            # fallback: try python -m alembic, but if it fails, skip gracefully
            try {
                & $PY -m alembic upgrade head | Tee-Object -FilePath alembic_upgrade.log
            } catch {
                Log "Alembic CLI not found in venv; skipping migrations"
                Pop-Location
                goto AfterMigrations
            }
        }
        Log "Migrations applied"
    } catch {
        Log "Migrations failed"
        Pop-Location
        exit 1
    }
    Pop-Location
} else {
    Log "No alembic folder; skipping migrations"
}
AfterMigrations:

# 3) Start backend server in background
Log "Starting backend server"
Push-Location "backend"
$startArgs = "-m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort"
        $proc = Start-Process -FilePath $PY -ArgumentList $startArgs -PassThru -WindowStyle Hidden
Log "Started backend pid $($proc.Id)"

# wait for server port
$maxWait = 60
$waited = 0
while ($waited -lt $maxWait) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Log "Backend responded: $($r.StatusCode)"
        break
    } catch {
        Start-Sleep -Seconds 1
        $waited++
    }
}

if ($waited -ge $maxWait) {
    Log "Backend did not start within timeout"
    Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue
    Pop-Location
    exit 1
}

Pop-Location

# 4) Run smoke/integration tests
Log "Running backend smoke tests"
try {
    if (Test-Path "backend/tests/test_smoke.py") {
        & $PY -m pytest "backend/tests/test_smoke.py" -q | Tee-Object -FilePath pytest_smoke.log
    } else {
        # run any tests matching smoke
        & $PY -m pytest "backend/tests" -k smoke -q | Tee-Object -FilePath pytest_smoke.log
    }
    Log "Smoke tests passed"
} catch {
    Log "Smoke tests failed"
    Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue
    exit 1
}

# 5) Build frontend
if (Test-Path "frontend/package.json") {
    Log "Building frontend"
    Push-Location "frontend"
    try {
        npm install | Tee-Object -FilePath npm_install_frontend.log
        npm run build | Tee-Object -FilePath npm_build.log
        Log "Frontend build succeeded"
    } catch {
        Log "Frontend build failed"
        Pop-Location
        Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue
        exit 1
    }
    Pop-Location
} else {
    Log "No frontend found; skipping frontend build"
}

# 6) Stop backend
Log "Stopping backend pid $($proc.Id)"
try { Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue } catch {}

if (-not $NoDocker) {
    Log "Bringing up docker-compose"
    Push-Location "gov-scheme-navigator"
    try {
        docker compose up --build -d | Tee-Object -FilePath docker_compose_up.log
        Log "Docker compose started"
    } catch {
        Log "Docker compose failed"
        Pop-Location
        exit 1
    }
    Pop-Location

    Log "Running container smoke tests"
    Push-Location "scripts"
    try {
        & "$PSScriptRoot/docker_smoke_test.ps1" | Tee-Object -FilePath docker_smoke_test.log
        if ($LASTEXITCODE -ne 0) { throw "docker smoke failed" }
        Log "Container smoke tests passed"
    } catch {
        Log "Container smoke tests failed"
        Pop-Location
        exit 1
    }
    Pop-Location
}

Log "Pipeline completed successfully"
Pop-Location
exit 0
