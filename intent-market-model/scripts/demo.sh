#!/usr/bin/env bash
set -euo pipefail

RESET=0
for arg in "$@"; do
  if [[ "$arg" == "--reset" ]]; then
    RESET=1
  fi
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$RESET" -eq 1 ]]; then
  docker-compose down -v
fi

docker-compose up --build -d

curl_retry() {
  local url="$1"
  shift
  for _ in {1..10}; do
    if curl -fsS --retry 3 --retry-connrefused --retry-delay 1 "$url" "$@" 2>/tmp/curl_err; then
      return 0
    fi
    sleep 1
  done
  cat /tmp/curl_err >&2
  return 1
}

for i in {1..30}; do
  if curl_retry http://localhost:8000/health >/dev/null; then
    break
  fi
  sleep 1
done

TENANT_JSON=$(curl_retry http://localhost:8000/tenants \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo Workspace"}')

TENANT_ID=$(TENANT_JSON="$TENANT_JSON" python - <<'PY'
import json, os
print(json.loads(os.environ["TENANT_JSON"])["id"])
PY
)

API_JSON=$(curl_retry "http://localhost:8000/tenants/${TENANT_ID}/api-keys" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"demo-key","rate_limit_per_min":120}')

API_KEY=$(API_JSON="$API_JSON" python - <<'PY'
import json, os
print(json.loads(os.environ["API_JSON"])["key"])
PY
)

COMPANY_JSON=$(curl_retry "http://localhost:8000/tenants/${TENANT_ID}/companies/" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{"name":"Acme AI","domain":"acme-ai.com"}')

COMPANY_ID=$(COMPANY_JSON="$COMPANY_JSON" python - <<'PY'
import json, os
print(json.loads(os.environ["COMPANY_JSON"])["id"])
PY
)

curl_retry "http://localhost:8000/tenants/${TENANT_ID}/companies/ingest/${COMPANY_ID}?source=mock&infer=true" \
  -X POST \
  -H "X-API-Key: ${API_KEY}" >/dev/null
curl_retry "http://localhost:8000/tenants/${TENANT_ID}/companies/ingest/${COMPANY_ID}?source=sec_mock&infer=true" \
  -X POST \
  -H "X-API-Key: ${API_KEY}" >/dev/null

curl_retry "http://localhost:8000/tenants/${TENANT_ID}/companies/${COMPANY_ID}/outcomes" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"outcome_type\":\"IPO\",\"timestamp\":\"$(python - <<'PY'
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) + timedelta(days=90)).isoformat())
PY
)\",\"source\":\"demo\"}" >/dev/null

curl_retry "http://localhost:8000/tenants/${TENANT_ID}/companies/${COMPANY_ID}/outcomes" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"outcome_type\":\"LAYOFF\",\"timestamp\":\"$(python - <<'PY'
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) + timedelta(days=60)).isoformat())
PY
)\",\"source\":\"demo\"}" >/dev/null

curl_retry "http://localhost:8000/tenants/${TENANT_ID}/companies/${COMPANY_ID}/outcomes" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d "{\"outcome_type\":\"FUNDING\",\"timestamp\":\"$(python - <<'PY'
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) + timedelta(days=30)).isoformat())
PY
)\",\"source\":\"demo\"}" >/dev/null

curl_retry "http://localhost:8000/tenants/${TENANT_ID}/companies/${COMPANY_ID}/backtest/run?lookback_days=365" \
  -X POST \
  -H "X-API-Key: ${API_KEY}" >/dev/null

echo ""
echo "Demo ready"
echo "Tenant ID: ${TENANT_ID}"
echo "Company ID: ${COMPANY_ID}"
echo "API Key: ${API_KEY}"
echo ""
echo "Frontend: http://localhost:8000/"
echo "Watchlist: http://localhost:8000/tenants/${TENANT_ID}/watchlist"
echo "IPO Timeline: http://localhost:8000/tenants/${TENANT_ID}/companies/${COMPANY_ID}/timeline/ipo_prep"
echo "Explainability: http://localhost:8000/tenants/${TENANT_ID}/companies/${COMPANY_ID}/explain"
echo "Backtest KPIs: http://localhost:8000/tenants/${TENANT_ID}/companies/${COMPANY_ID}/backtest/kpis"
echo ""
echo "Sample curl:"
echo "curl -H \"X-API-Key: ${API_KEY}\" http://localhost:8000/tenants/${TENANT_ID}/watchlist"
