"""
Generic API-Sports client for non-football sports.

Each API-Sports product (rugby, NFL, NBA, NHL, MMA) uses the same API
structure with a different base URL and API key. This module provides a
unified interface for all of them.

Football continues to use the existing api_football.py — this module
handles everything else.

Docs: https://api-sports.io/documentation
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import requests

from src.config import Config

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "api_cache"

# Sport configurations: base URL, API key config attr, priority league IDs
SPORT_CONFIG = {
    "rugby": {
        "base_url": "https://v1.rugby.api-sports.io",
        "api_key_attr": "API_RUGBY_KEY",
        "priority_leagues": [],  # Empty = accept all leagues
    },
    "nfl": {
        "base_url": "https://v1.american-football.api-sports.io",
        "api_key_attr": "API_NFL_KEY",
        "priority_leagues": [1],  # NFL
    },
    "nba": {
        "base_url": "https://v1.basketball.api-sports.io",
        "api_key_attr": "API_NBA_KEY",
        "priority_leagues": [12],  # NBA
    },
    "nhl": {
        "base_url": "https://v1.hockey.api-sports.io",
        "api_key_attr": "API_NHL_KEY",
        "priority_leagues": [57],  # NHL
    },
    "mma": {
        "base_url": "https://v1.mma.api-sports.io",
        "api_key_attr": "API_MMA_KEY",
        "priority_leagues": [],
    },
    "formula1": {
        "base_url": "https://v1.formula-1.api-sports.io",
        "api_key_attr": "API_F1_KEY",
        "priority_leagues": [],
    },
}


def _get_api_key(sport):
    """Get the API key for a sport from config.

    Tries the sport-specific key first, then falls back to the shared
    API_FOOTBALL_KEY (api-sports.io uses a single key across all sports).
    """
    config = SPORT_CONFIG.get(sport)
    if not config:
        return ""
    return getattr(Config, config["api_key_attr"], "") or Config.API_FOOTBALL_KEY


def is_configured(sport):
    """Check if a sport's API key is configured."""
    return bool(_get_api_key(sport))


def get_configured_sports():
    """Return list of sports that have API keys configured."""
    return [sport for sport in SPORT_CONFIG if is_configured(sport)]


def _cache_path(sport, endpoint, params):
    """Build a cache file path from sport, endpoint and params."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = f"{sport}_{endpoint.strip('/').replace('/', '_')}"
    param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
    return CACHE_DIR / f"{key}_{param_str}.json"


def _get(sport, endpoint, params, cache_ttl_hours=6):
    """
    Make a GET request to an API-Sports endpoint with local file caching.

    Args:
        sport: Sport name (e.g. "rugby", "nfl")
        endpoint: API endpoint path (e.g. "/games")
        params: Query parameters dict
        cache_ttl_hours: How long to use cached response

    Returns:
        dict — the API response, or None on failure.
    """
    config = SPORT_CONFIG.get(sport)
    if not config:
        logger.warning("Unknown sport: %s", sport)
        return None

    api_key = _get_api_key(sport)
    cache_file = _cache_path(sport, endpoint, params)

    # Check cache
    if cache_ttl_hours > 0 and cache_file.exists():
        try:
            stat = cache_file.stat()
            age_hours = (datetime.now().timestamp() - stat.st_mtime) / 3600
            if age_hours < cache_ttl_hours:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                logger.info("API-Sports cache hit: %s %s (%.1fh old)", sport, cache_file.name, age_hours)
                return data
        except (json.JSONDecodeError, OSError):
            pass

    if not api_key:
        logger.debug("API key not configured for %s — skipping", sport)
        return None

    try:
        resp = requests.get(
            f"{config['base_url']}{endpoint}",
            headers={"x-apisports-key": api_key},
            params=params,
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("API-Sports %s returned %d: %s", sport, resp.status_code, resp.text[:200])
            return None

        data = resp.json()

        errors = data.get("errors", {})
        if errors:
            logger.warning("API-Sports %s errors: %s", sport, errors)
            return None

        # Cache the response
        try:
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.warning("Cache write failed: %s", e)

        return data

    except requests.Timeout:
        logger.warning("API-Sports %s request timed out", sport)
        return None
    except requests.RequestException as e:
        logger.warning("API-Sports %s request failed: %s", sport, e)
        return None


def get_fixtures(sport, date_str):
    """
    Fetch fixtures for a specific date.

    The endpoint varies by sport but follows the same pattern.

    Args:
        sport: Sport name (e.g. "rugby", "nfl")
        date_str: Date in YYYY-MM-DD format

    Returns:
        list of fixture dicts, or empty list.
    """
    # MMA uses /fights endpoint, others use /games
    endpoint = "/fights" if sport == "mma" else "/games"
    data = _get(sport, endpoint, {"date": date_str}, cache_ttl_hours=6)
    if not data:
        return []
    return data.get("response", [])


def get_fixture(sport, fixture_id):
    """
    Fetch a single fixture by its API ID.

    Args:
        sport: Sport name
        fixture_id: API fixture ID

    Returns:
        fixture dict, or None.
    """
    endpoint = "/fights" if sport == "mma" else "/games"
    data = _get(sport, endpoint, {"id": str(fixture_id)}, cache_ttl_hours=1)
    if not data:
        return None
    response = data.get("response", [])
    return response[0] if response else None


def normalize_fixture(sport, raw_fixture):
    """
    Normalize an API-Sports fixture response into a standard format
    matching the football fixture structure.

    Returns a dict with: api_id, sport, competition, home_team, away_team,
    kickoff, status, home_score, away_score, raw_json.
    Returns None if the fixture can't be normalized.
    """
    if not raw_fixture:
        return None

    try:
        if sport == "mma":
            return _normalize_mma(raw_fixture)
        return _normalize_team_sport(sport, raw_fixture)
    except Exception as e:
        logger.warning("Failed to normalize %s fixture: %s", sport, e)
        return None


def _normalize_team_sport(sport, fixture_data):
    """Normalize a team sport (rugby/NFL/NBA/NHL) fixture."""
    # API-Sports team sport responses follow a similar structure:
    # {game/id, league, teams: {home, away}, scores}
    game = fixture_data.get("game", fixture_data.get("fixture", {}))
    league = fixture_data.get("league", {})
    teams = fixture_data.get("teams", {})
    scores = fixture_data.get("scores", fixture_data.get("goals", {}))

    api_id = game.get("id") if isinstance(game, dict) else fixture_data.get("id")
    if not api_id:
        return None

    home_team = teams.get("home", {})
    away_team = teams.get("away", {})

    # Score extraction varies by sport
    home_score = scores.get("home", {})
    away_score = scores.get("away", {})
    if isinstance(home_score, dict):
        home_score = home_score.get("total")
    if isinstance(away_score, dict):
        away_score = away_score.get("total")

    # Status
    status_data = game.get("status", {}) if isinstance(game, dict) else fixture_data.get("status", {})
    status = status_data.get("short", "NS") if isinstance(status_data, dict) else "NS"

    return {
        "api_id": api_id,
        "sport": sport,
        "competition": league.get("name", "Unknown"),
        "competition_id": league.get("id"),
        "home_team": home_team.get("name", "Unknown") if isinstance(home_team, dict) else str(home_team),
        "away_team": away_team.get("name", "Unknown") if isinstance(away_team, dict) else str(away_team),
        "kickoff": game.get("date", "") if isinstance(game, dict) else fixture_data.get("date", ""),
        "status": status,
        "home_score": home_score,
        "away_score": away_score,
        "raw_json": json.dumps(fixture_data),
    }


def _normalize_mma(fight_data):
    """Normalize an MMA fight."""
    fight_id = fight_data.get("id")
    if not fight_id:
        return None

    fighters = fight_data.get("fighters", {})
    first = fighters.get("first", {})
    second = fighters.get("second", {})

    league = fight_data.get("league", {})

    return {
        "api_id": fight_id,
        "sport": "mma",
        "competition": league.get("name", "UFC"),
        "competition_id": league.get("id"),
        "home_team": first.get("name", "Unknown"),
        "away_team": second.get("name", "Unknown"),
        "kickoff": fight_data.get("date", ""),
        "status": fight_data.get("status", {}).get("short", "NS") if isinstance(fight_data.get("status"), dict) else "NS",
        "home_score": None,
        "away_score": None,
        "raw_json": json.dumps(fight_data),
    }
