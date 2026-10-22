#!/usr/bin/env bash
# Developer shortcuts.  Usage: ./dev.sh <command>
#   up         run the whole stack in Docker
#   down       stop it
#   test       end-to-end tests in mock mode
#   sql        regenerate derived SQL (seed + procedures)
#   payer      run the payer service with hot reload (no Docker)
#   provider   run the provider service with hot reload (no Docker)
#   ui         run the Next.js dev server
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT/services/common:$ROOT/services/payer:$ROOT/services/provider"
load_env() { if [[ -f "$ROOT/.env" ]]; then set -a; . "$ROOT/.env"; set +a; fi; }
case "${1:-}" in
  up)       docker compose -f "$ROOT/docker-compose.yml" up --build ;;
  down)     docker compose -f "$ROOT/docker-compose.yml" down ;;
  test)     cd "$ROOT/services" && python -m pytest -q tests ;;
  sql)      python3 "$ROOT/snowflake/scripts/build_sql.py" ;;
  payer)    load_env; cd "$ROOT/services" && uvicorn payer_service.main:app --reload --port 8002 ;;
  provider) load_env; cd "$ROOT/services" && PAYER_BASE_URL=http://localhost:8002 uvicorn provider_service.main:app --reload --port 8001 ;;
  ui)       cd "$ROOT/ui" && npm run dev ;;
  *)        sed -n '2,10p' "$0"; exit 1 ;;
esac
