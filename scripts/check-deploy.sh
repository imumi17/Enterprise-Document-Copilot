#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${1:-http://localhost:8000}"
API_BASE_URL="${API_BASE_URL%/}"

echo "Checking ${API_BASE_URL}/health ..."
response="$(curl -fsS "${API_BASE_URL}/health")"

if [[ "$response" != *"ok"* ]]; then
  echo "Unexpected health response: $response"
  exit 1
fi

echo "OK: backend health check passed"
echo "Next: open the frontend, sign in, and run the chat smoke test in docs/guides/railway-deploy.md"
