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
- `FLASK_PORT` — Python backend port (default: 5000)
- `BRIDGE_URL` — Bridge URL (default: http://localhost:3000)
- `DB_PATH` — SQLite database path (default: data/punter_bot.db)
- `TIMEZONE` — Your timezone (default: Europe/Dublin)

## Running

Start both processes in separate terminals:

**Terminal 1 — Python backend:**
```bash
source venv/bin/activate
python -m src.app
```

**Terminal 2 — WhatsApp bridge:**
```bash
cd bridge
npm start
```

On first run, scan the QR code displayed in Terminal 2 with WhatsApp (Linked Devices). The session persists after the initial scan.

## Testing

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

## Project Structure

```
punter-bot/
├── bridge/           # Node.js WhatsApp bridge
│   └── index.js
├── src/              # Python backend
│   ├── app.py        # Flask app + webhook routes
│   ├── config.py     # Environment config
│   ├── db.py         # Database helpers
│   ├── schema.sql    # SQLite schema
│   └── parsers/
│       └── message_parser.py
├── tests/
├── data/             # SQLite DB (gitignored)
└── requirements.txt
```
