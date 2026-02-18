import os
import sqlite3
from pathlib import Path

from src.config import Config


def get_db():
    """Return a connection to the SQLite database."""
    db_path = Config.DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables from schema.sql if they don't exist, then seed players."""
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path) as f:
        schema_sql = f.read()

    conn = get_db()
    conn.executescript(schema_sql)
    conn.commit()

    seed_players(conn)
    conn.close()


def seed_players(conn):
    """Insert the 6 players if the table is empty."""
    count = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    if count > 0:
        return

    players = [
        ("Edmund", "Ed", "Mr Edmund", "🍋,🍋🍋🍋", None, 6),
        ("Kevin", "Kev", "Mr Kevin", "🧌", None, 1),
        ("Declan", "DA", "Mr Declan", "👴🏻", None, 5),
        ("Ronan", "Nug", "Mr Ronan", "🍗", None, 3),
        ("Nialler", "Nialler", "Mr Niall", "🔫", None, 2),
        ("Aidan", "Pawn", "Mr Aidan", "♟️", None, 4),
    ]

    conn.executemany(
        "INSERT INTO players (name, nickname, formal_name, emoji, phone, rotation_position) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        players,
    )
    conn.commit()
