#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT_DIR/pipeline_log.txt"
echo "$(date -Iseconds)\tStarting pipeline" | tee -a "$LOG"

cd "$ROOT_DIR"

echo "$(date -Iseconds)\tRunning backend tests" | tee -a "$LOG"
if [ -d backend/tests ]; then
  python -m pytest backend/tests -q 2>&1 | tee pytest_backend.log
else
  echo "No backend tests; skipping" | tee -a "$LOG"
fi

if [ -d backend/alembic ]; then
  echo "$(date -Iseconds)\tApplying alembic migrations" | tee -a "$LOG"
  (cd backend && alembic upgrade head) 2>&1 | tee alembic_upgrade.log
fi

echo "$(date -Iseconds)\tStarting backend server" | tee -a "$LOG"
cd backend
nohup python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &
PID=$!
echo "started pid $PID" | tee -a "$LOG"

# wait for port
for i in {1..60}; do
  if curl -fsS http://127.0.0.1:8000/ > /dev/null 2>&1; then
    echo "backend up" | tee -a "$LOG"
    break
  fi
  sleep 1
done

echo "$(date -Iseconds)\tRunning smoke tests" | tee -a "$LOG"
if [ -f backend/tests/test_smoke.py ]; then
  python -m pytest backend/tests/test_smoke.py -q 2>&1 | tee pytest_smoke.log
else
  python -m pytest backend/tests -k smoke -q 2>&1 | tee pytest_smoke.log || true
fi

echo "$(date -Iseconds)\tBuilding frontend if present" | tee -a "$LOG"
cd "$ROOT_DIR"
if [ -f frontend/package.json ]; then
  (cd frontend && npm install && npm run build) 2>&1 | tee npm_build.log
else
  echo "No frontend" | tee -a "$LOG"
fi

echo "$(date -Iseconds)\tStopping backend" | tee -a "$LOG"
kill $PID || true

echo "$(date -Iseconds)\tBringing up docker-compose" | tee -a "$LOG"
cd "$ROOT_DIR"
docker compose up --build -d 2>&1 | tee docker_compose_up.log

echo "$(date -Iseconds)\tRunning container smoke-test" | tee -a "$LOG"
cd "$ROOT_DIR/scripts"
./docker_smoke_test.sh

echo "$(date -Iseconds)\tPipeline completed" | tee -a "$LOG"
