import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID", "")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5001"))
    BRIDGE_URL = os.getenv("BRIDGE_URL", "http://localhost:3000")
    DB_PATH = os.getenv("DB_PATH", "data/punter_bot.db")
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Dublin")
    ADMIN_PHONE = os.getenv("ADMIN_PHONE", "")
    SUPERADMIN_PHONE = os.getenv("SUPERADMIN_PHONE", "")
    TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
