#!/usr/bin/env bash
set -euo pipefail

urls=(
  "http://127.0.0.1:8000/"
  "http://127.0.0.1:8000/health"
  "http://127.0.0.1:8000/api/schemes"
)

ok=true
for u in "${urls[@]}"; do
  if curl -fsS "$u" >/dev/null 2>&1; then
    echo "$u -> OK"
  else
    echo "$u -> FAIL"
    ok=false
  fi
done

if [ "$ok" = true ]; then
  exit 0
else
  exit 1
fi
