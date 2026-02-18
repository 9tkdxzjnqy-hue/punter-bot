#!/usr/bin/env bash
# One command to restart (clean up) and start the bot. Run from project root.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Clean up first
"$ROOT/scripts/restart.sh"

# Start Flask in background
echo ""
echo "Starting Flask..."
source venv/bin/activate
python -m src.app &
FLASK_PID=$!

# Wait for Flask to be ready
for i in {1..15}; do
  curl -s -o /dev/null http://127.0.0.1:5001/health 2>/dev/null && break
  sleep 1
done

# Start bridge in foreground (user sees logs, Ctrl+C stops both)
echo "Starting bridge..."
trap "kill $FLASK_PID 2>/dev/null; exit" INT TERM
cd bridge && npm start
