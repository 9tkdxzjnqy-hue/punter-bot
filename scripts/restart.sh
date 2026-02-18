#!/usr/bin/env bash
# Kill Flask (5001) and Bridge (3000) processes. Use when testing hits
# "detached Frame" or port-in-use errors.
set -e

FLASK_PORT=${FLASK_PORT:-5001}
BRIDGE_PORT=${BRIDGE_PORT:-3000}

echo "Stopping Punter Bot services..."

# Kill any Chrome/Puppeteer using our session (fixes "browser already running")
SESSION_PATH="$(cd "$(dirname "$0")/.." && pwd)/bridge/.wwebjs_auth/session"
if pkill -9 -f "$SESSION_PATH" 2>/dev/null; then
  echo "  Killed stale Chrome process"
  sleep 2
fi

for port in $FLASK_PORT $BRIDGE_PORT; do
  pid=$(lsof -ti :$port 2>/dev/null || true)
  if [ -n "$pid" ]; then
    echo "  Killing process on port $port (PID $pid)"
    kill -9 $pid 2>/dev/null || true
    sleep 1
  else
    echo "  Port $port already free"
  fi
done

echo "Done. Start services with:"
echo "  ./scripts/start.sh          # one command (restart + start both)"
echo "  Or manually:"
echo "  Terminal 1: source venv/bin/activate && python -m src.app"
echo "  Terminal 2: cd bridge && npm start"
