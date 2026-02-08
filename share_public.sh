#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is not installed."
  echo ""
  echo "Install (macOS):   brew install cloudflare/cloudflare/cloudflared"
  echo "Install (Windows): winget install Cloudflare.cloudflared"
  echo "Install (Linux):   https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  echo ""
  exit 1
fi

PORT="${PORT:-8000}"

echo "Starting SignCraft locally on port ${PORT}..."
./run_local.sh &
APP_PID="$!"

cleanup() {
  echo ""
  echo "Stopping..."
  kill "${APP_PID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

echo ""
echo "Creating a public HTTPS URL (Cloudflare Quick Tunnel)..."
echo "When you see the https://*.trycloudflare.com URL, share it with judges."
echo ""

# This prints a public URL in the logs; user copies it.
cloudflared tunnel --no-autoupdate --url "http://localhost:${PORT}"

