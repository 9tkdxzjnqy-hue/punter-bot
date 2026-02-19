# Punter Bot — The Betting Butler

WhatsApp bot that manages a weekly accumulator betting pool for the lads.

## Setup

### Python backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit .env with your config
```

### Node.js bridge

```bash
cd bridge
npm install
```

### Configuration

Edit `.env` with your settings:

- `GROUP_CHAT_ID` — WhatsApp group ID (leave blank on first run, the bridge will log group IDs to help you find it)
- `FLASK_PORT` — Python backend port (default: 5001)
- `BRIDGE_URL` — Bridge URL (default: http://localhost:3000)
- `DB_PATH` — SQLite database path (default: data/punter_bot.db)
- `TIMEZONE` — Your timezone (default: Europe/Dublin)

## Running

**One command (recommended):**
```bash
./scripts/start.sh
```
This cleans up any stale processes, starts Flask in the background, and runs the bridge in the foreground. Ctrl+C stops both.

**Or manually in two terminals:**

Terminal 1 — Python backend:
```bash
source venv/bin/activate
python -m src.app
```

Terminal 2 — WhatsApp bridge:
```bash
cd bridge
npm start
```

On first run, scan the QR code displayed in Terminal 2 with WhatsApp (Linked Devices). The session persists after the initial scan.

### Restarting

The bridge now **auto-cleans** stale Chrome on startup, so `cd bridge && npm start` usually works even after a crash. If you hit "detached Frame" or port-in-use:

```bash
./scripts/restart.sh
```

Then run `./scripts/start.sh` or start both services manually. The bridge will auto-reconnect on detached Frame when possible; Flask retries up to 3 times if the bridge is reconnecting.

## Production (OCI Cloud)

The bot runs on an Oracle Cloud Always Free Ubuntu 22.04 VM, managed by PM2.

**Server:** `ssh -i ~/Documents/Oracle/ssh-key-2026-02-18.key ubuntu@193.123.179.96`

**SSH tunnel** (to access bridge locally): `ssh -L 3000:localhost:3000 -i ~/Documents/Oracle/ssh-key-2026-02-18.key ubuntu@193.123.179.96`

**PM2 commands (on server):**
```bash
pm2 list                    # Status of all processes
pm2 logs punter-bridge      # Bridge logs
pm2 logs punter-flask       # Flask logs
pm2 restart punter-bridge   # Restart bridge
pm2 restart all             # Restart everything
```

**Deploying changes:**
```bash
# Local: commit and push
git add . && git commit -m "message" && git push

# Server: pull and restart
cd ~/punter-bot && git pull && pm2 restart all
```

**Health check & alerting:**
- Pings Flask and Bridge `/health` every 5 minutes
- Sends Telegram alerts via @punteralerts_bot if a service goes down
- Sends recovery notification when it comes back
- Config: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`

**Key config (.env):**
- `TEST_MODE=false` for production
- `GROUP_CHAT_ID` or `GROUP_CHAT_IDS` for your group(s)
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` for health alerts
- See `MAIN_GROUP_READY.md` for the launch checklist

## Testing

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

## Project Structure

```
punter-bot/
├── bridge/                # Node.js WhatsApp bridge
│   ├── index.js
│   ├── package.json
│   └── run-with-node20.sh # nvm wrapper for OCI server
├── src/                   # Python backend
│   ├── app.py             # Flask app + webhook routes
│   ├── butler.py          # Butler-style message formatting
│   ├── config.py          # Environment config
│   ├── db.py              # Database helpers
│   ├── schema.sql         # SQLite schema
│   ├── parsers/
│   │   └── message_parser.py
│   └── services/          # Business logic (picks, results, stats, etc.)
├── scripts/
│   ├── health_check.py    # Health monitor + Telegram alerts
│   └── restart.sh
├── tests/
├── data/                  # SQLite DB (gitignored)
├── ecosystem.config.js    # PM2 process config
└── requirements.txt
```
