"""
Fixture caching and management service.

Fetches fixtures from API-Football and stores them locally in the fixtures
table. Provides lookup methods for pick matching and auto-resulting.
"""

import json
import logging
from datetime import datetime, timedelta

import pytz

from src.config import Config
from src.db import get_db
from src.api.api_football import (
    get_fixtures_by_date_range,
    get_fixture_by_id,
    PRIORITY_LEAGUES,
)

logger = logging.getLogger(__name__)


def fetch_weekend_fixtures():
    """
    Fetch fixtures for the upcoming weekend (Friday to Monday).

    Called by the scheduler on Wednesday evening. Fetches from priority leagues
    to keep within the free tier budget (~3-5 requests per cycle).

    Returns:
        int — number of fixtures cached.
    """
    tz = pytz.timezone(Config.TIMEZONE)
    now = datetime.now(tz)

    # Calculate next Friday to Monday
    days_to_friday = (4 - now.weekday()) % 7
    if days_to_friday == 0 and now.hour >= 22:
        days_to_friday = 7
    friday = (now + timedelta(days=days_to_friday)).date()
    monday = friday + timedelta(days=3)

    start_date = friday.isoformat()
    end_date = monday.isoformat()
    logger.info("Fetching fixtures for %s to %s", start_date, end_date)

    total_cached = 0
    for league_id in PRIORITY_LEAGUES:
        fixtures = get_fixtures_by_date_range(start_date, end_date, league_id=league_id)
        if fixtures:
            cached = _cache_fixtures(fixtures)
            total_cached += cached
            logger.info("Cached %d fixtures for league %d", cached, league_id)

    logger.info("Total fixtures cached: %d", total_cached)
    return total_cached


def _cache_fixtures(api_fixtures):
    """
    Store API-Football fixtures in the local database.

    Uses INSERT OR REPLACE to update existing fixtures (e.g. when scores come in).

    Args:
        api_fixtures: List of fixture dicts from API-Football response.

    Returns:
        int — number of fixtures stored.
    """
    conn = get_db()
    count = 0

    for fixture_data in api_fixtures:
        try:
            fixture = fixture_data.get("fixture", {})
            league = fixture_data.get("league", {})
            teams = fixture_data.get("teams", {})
            goals = fixture_data.get("goals", {})
            score = fixture_data.get("score", {})

            api_id = fixture.get("id")
            if not api_id:
                continue

            # Extract half-time scores
            ht = score.get("halftime", {})
            ht_home = ht.get("home")
            ht_away = ht.get("away")

            conn.execute(
                """INSERT OR REPLACE INTO fixtures
                   (api_id, sport, competition, competition_id,
                    home_team, away_team, kickoff, status,
                    home_score, away_score, ht_home_score, ht_away_score,
                    fetched_at, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    api_id,
                    "football",
                    league.get("name", "Unknown"),
                    league.get("id"),
                    teams.get("home", {}).get("name", "Unknown"),
                    teams.get("away", {}).get("name", "Unknown"),
                    fixture.get("date", ""),
                    fixture.get("status", {}).get("short", "NS"),
                    goals.get("home"),
                    goals.get("away"),
                    ht_home,
                    ht_away,
                    datetime.utcnow().isoformat(),
                    json.dumps(fixture_data),
                ),
            )
            count += 1
        except Exception as e:
            logger.warning("Failed to cache fixture: %s", e)

    conn.commit()
    conn.close()
    return count


def get_upcoming_fixtures(days_ahead=4):
    """
    Get cached fixtures that haven't started yet, within the next N days.

    Returns:
        list of fixture dicts from the local database.
    """
    tz = pytz.timezone(Config.TIMEZONE)
    now = datetime.now(tz)
    cutoff = (now + timedelta(days=days_ahead)).isoformat()

    conn = get_db()
    fixtures = conn.execute(
        "SELECT * FROM fixtures WHERE kickoff > ? AND kickoff < ? "
        "AND status IN ('NS', 'TBD') ORDER BY kickoff",
        (now.isoformat(), cutoff),
    ).fetchall()
    conn.close()
    return [dict(f) for f in fixtures]


def get_completed_fixtures():
    """
    Get cached fixtures that have finished (for auto-resulting).

    Returns fixtures with status FT (full time), AET (after extra time),
    or PEN (penalties).
    """
    conn = get_db()
    fixtures = conn.execute(
        "SELECT * FROM fixtures WHERE status IN ('FT', 'AET', 'PEN') "
        "ORDER BY kickoff DESC"
    ).fetchall()
    conn.close()
    return [dict(f) for f in fixtures]


def get_fixture_by_api_id(api_id):
    """Look up a cached fixture by its API-Football ID."""
    conn = get_db()
    fixture = conn.execute(
        "SELECT * FROM fixtures WHERE api_id = ?", (api_id,)
    ).fetchone()
    conn.close()
    return dict(fixture) if fixture else None


def refresh_fixture(api_id):
    """
    Re-fetch a single fixture from API-Football and update the cache.
    Used to check for score updates during auto-resulting.
    """
    fixture_data = get_fixture_by_id(api_id)
    if fixture_data:
        _cache_fixtures([fixture_data])
        return get_fixture_by_api_id(api_id)
    return None


def get_fixture_list_for_matching():
    """
    Build a concise fixture list string for LLM matching.
    Used as context when the LLM tries to match a pick to a fixture.

    Returns:
        str — formatted list like "1. Arsenal vs Chelsea (EPL, Sat 3pm)\n2. ..."
    """
    fixtures = get_upcoming_fixtures()
    if not fixtures:
        return ""

    lines = []
    for i, f in enumerate(fixtures, 1):
        try:
            kickoff = datetime.fromisoformat(f["kickoff"])
            time_str = kickoff.strftime("%a %H:%M")
        except (ValueError, TypeError):
            time_str = "TBD"
        lines.append(
            f"{i}. {f['home_team']} vs {f['away_team']} "
            f"({f['competition']}, {time_str}) [id:{f['api_id']}]"
        )
    return "\n".join(lines)
