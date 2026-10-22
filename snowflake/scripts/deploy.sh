#!/usr/bin/env bash
# Run the AuthBridge SQL files in order with the Snowflake CLI.
#   snow connection add            # once, creates a connection named e.g. "authbridge"
#   ./snowflake/scripts/deploy.sh authbridge           # everything except 00_setup
#   ./snowflake/scripts/deploy.sh authbridge --setup   # include 00_setup (needs ACCOUNTADMIN)
set -euo pipefail
CONN="${1:?usage: deploy.sh <snow-connection-name> [--setup]}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$HERE/scripts/build_sql.py"
FILES=(01_tables 02_seed 03_crd_procedures 04_pas_procedures 05_ai 06_streams_tasks 07_analytics 08_agents 09_governance)
if [[ "${2:-}" == "--setup" ]]; then FILES=(00_setup "${FILES[@]}"); fi
for f in "${FILES[@]}"; do
  echo "==> $f.sql"
  snow sql -c "$CONN" -f "$HERE/sql/$f.sql"
done
echo "Done. Smoke test: snow sql -c $CONN -q \"CALL AUTHBRIDGE.PAYER.SP_CRD_EVALUATE('M100002','pt-002','72148','CPT','1477589632','order-sign')\""
