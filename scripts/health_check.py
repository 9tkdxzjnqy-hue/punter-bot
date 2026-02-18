#!/usr/bin/env python3
"""
Health check script for Punter Bot.

Pings the Flask /health endpoint every 5 minutes. On failure, logs to file
and (on macOS) shows a desktop notification.

Run standalone: python scripts/health_check.py
Or via PM2: pm2 start ecosystem.config.js (includes health-check)
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path so we can load .env and config
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Load env before importing config
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

import requests

# Config
HEALTH_URL = os.getenv("FLASK_URL", "http://127.0.0.1:5001") + "/health"
INTERVAL_SECONDS = int(os.getenv("HEALTH_CHECK_INTERVAL", "300"))  # 5 minutes
LOG_PATH = PROJECT_ROOT / "logs" / "health-check.log"
TIMEOUT_SECONDS = 10

# Logging
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def notify_desktop(message: str, title: str = "Punter Bot Health Check") -> None:
    """Show macOS desktop notification."""
    if sys.platform != "darwin":
        return
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display notification "{message}" with title "{title}"',
            ],
            capture_output=True,
            timeout=5,
        )
    except Exception as e:
        logger.warning("Desktop notification failed: %s", e)


def check_health() -> bool:
    """Ping /health endpoint. Return True if OK, False otherwise."""
    try:
        resp = requests.get(HEALTH_URL, timeout=TIMEOUT_SECONDS)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "ok":
                return True
        logger.warning("Health check failed: status=%d body=%s", resp.status_code, resp.text[:200])
        return False
    except requests.RequestException as e:
        logger.warning("Health check failed: %s", e)
        return False


def main() -> None:
    logger.info("Health check started (interval=%ds, url=%s)", INTERVAL_SECONDS, HEALTH_URL)
    while True:
        if check_health():
            pass  # Silent on success
        else:
            logger.error("Punter Bot is unresponsive at %s", HEALTH_URL)
            notify_desktop("Bot is unresponsive! Check logs.", "Punter Bot Alert")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
