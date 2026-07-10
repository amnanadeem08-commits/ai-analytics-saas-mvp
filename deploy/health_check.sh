#!/usr/bin/env sh
set -eu

BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"

echo "Checking liveness..."
curl -sf "$BASE_URL/api/v1/live" | python -m json.tool

echo "Checking readiness..."
curl -sf "$BASE_URL/api/v1/ready" | python -m json.tool

echo "Checking health..."
curl -sf "$BASE_URL/api/v1/monitoring/health" | python -m json.tool

echo "All health probes succeeded."
