#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "Starting SignCraft (single server)..."

# Load local env if present (never commit .env with keys)
if [[ -f "test-backend/.env" ]]; then
  # shellcheck disable=SC1091
  source "test-backend/.env"
  export GEMINI_API_KEY="${GEMINI_API_KEY:-}"
fi

PORT="${PORT:-8000}"

echo "Backend + frontend will be at: http://localhost:${PORT}"
echo "Press Ctrl+C to stop."

# Start FastAPI (serves frontend too)
cd "test-backend"
python3 -m uvicorn server:app --host 0.0.0.0 --port "${PORT}"

