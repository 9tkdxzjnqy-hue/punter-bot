"""
The Odds API client (free tier: 500 requests/month).

Fetches market odds for recognised selections. Batch efficiently — one
request per sport per region returns all events, then match locally.

Docs: https://the-odds-api.com/liveapi/guides/v4/
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import requests

from src.config import Config

logger = logging.getLogger(__name__)

BASE_URL = "https://api.the-odds-api.com/v4"
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "api_cache"

# Sport keys for The Odds API — maps sport/competition names to API sport keys
SPORT_KEYS = {
    # Football (default)
    "football": "soccer_epl",
    "epl": "soccer_epl",
    "premier league": "soccer_epl",
    "la liga": "soccer_spain_la_liga",
    "serie a": "soccer_italy_serie_a",
    "bundesliga": "soccer_germany_bundesliga",
    "ligue 1": "soccer_france_ligue_one",
    "champions league": "soccer_uefa_champs_league",
    "europa league": "soccer_uefa_europa_league",
    "fa cup": "soccer_fa_cup",
    "scottish premiership": "soccer_spl",
    # Rugby
    "rugby": "rugbyunion_six_nations",
    "six nations": "rugbyunion_six_nations",
    # NFL
    "nfl": "americanfootball_nfl",
    "super bowl": "americanfootball_nfl_super_bowl_winner",
    # NBA
    "nba": "basketball_nba",
    # NHL
    "nhl": "icehockey_nhl",
    # MMA
    "mma": "mma_mixed_martial_arts",
    "ufc": "mma_mixed_martial_arts",
    # Tennis
    "tennis": "tennis_atp_french_open",
    "wimbledon": "tennis_atp_wimbledon",
    "australian open": "tennis_atp_aus_open",
    "french open": "tennis_atp_french_open",
    "us open tennis": "tennis_atp_us_open",
    # Golf
    "golf": "golf_masters_tournament_winner",
    "masters": "golf_masters_tournament_winner",
    "pga": "golf_pga_championship_winner",
    # Boxing
    "boxing": "boxing_boxing",
}

# Priority sport keys to fetch per sport (covers most picks)
PRIORITY_SPORTS = [
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_italy_serie_a",
    "soccer_germany_bundesliga",
    "soccer_france_ligue_one",
    "soccer_uefa_champs_league",
]

# Additional sport keys to search when a non-football sport is detected
SPORT_PRIORITY_KEYS = {
    "football": PRIORITY_SPORTS,
    "rugby": ["rugbyunion_six_nations"],
    "nfl": ["americanfootball_nfl"],
    "nba": ["basketball_nba"],
    "nhl": ["icehockey_nhl"],
    "mma": ["mma_mixed_martial_arts"],
    "tennis": [
        "tennis_atp_french_open", "tennis_atp_wimbledon",
        "tennis_atp_aus_open", "tennis_atp_us_open",
    ],
    "golf": ["golf_masters_tournament_winner", "golf_pga_championship_winner"],
    "boxing": ["boxing_boxing"],
}


def _cache_path(sport_key):
    """Build a cache file path for odds data."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"odds_{sport_key}.json"


def get_odds_for_sport(sport_key, regions="uk", markets="h2h"):
    """
    Fetch odds for all events in a sport.

    One request returns all events — do local matching, not per-pick calls.
    This is critical for staying within the 500 req/month free tier.

    Args:
        sport_key: The Odds API sport key (e.g. "soccer_epl")
        regions: Bookmaker region (uk, us, eu, au)
        markets: Market type (h2h = head-to-head/moneyline)

    Returns:
        list of event dicts with odds, or empty list.
    """
    if not Config.ODDS_API_KEY:
        logger.info("ODDS_API_KEY not configured — skipping odds fetch")
        return []

    cache_file = _cache_path(sport_key)

    # Check cache (2 hour TTL — odds change but we don't need real-time)
    if cache_file.exists():
        try:
            stat = cache_file.stat()
            age_hours = (datetime.now().timestamp() - stat.st_mtime) / 3600
            if age_hours < 2:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                logger.info("Odds cache hit: %s (%.1fh old)", sport_key, age_hours)
                return data
        except (json.JSONDecodeError, OSError):
            pass

    try:
        resp = requests.get(
            f"{BASE_URL}/sports/{sport_key}/odds",
            params={
                "apiKey": Config.ODDS_API_KEY,
                "regions": regions,
                "markets": markets,
                "oddsFormat": "decimal",
            },
            timeout=10,
        )

        if resp.status_code != 200:
            logger.warning("Odds API returned %d: %s", resp.status_code, resp.text[:200])
            return []

        data = resp.json()

        # Log remaining quota from headers
        remaining = resp.headers.get("x-requests-remaining", "?")
        used = resp.headers.get("x-requests-used", "?")
        logger.info("Odds API: %s requests remaining (%s used)", remaining, used)

        # Cache response
        try:
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.warning("Odds cache write failed: %s", e)

        return data

    except requests.Timeout:
        logger.warning("Odds API timed out")
        return []
    except requests.RequestException as e:
        logger.warning("Odds API request failed: %s", e)
        return []


def find_market_price(event_name, competition=None, sport=None):
    """
    Look up the market price for an event across cached odds data.

    Args:
        event_name: e.g. "Arsenal vs Chelsea"
        competition: Optional competition name to narrow the sport key
        sport: Optional sport name (e.g. "football", "rugby")

    Returns:
        dict {"home": 1.95, "draw": 3.40, "away": 4.20} or None
    """
    # Determine which sport keys to search
    sport_key = _competition_to_sport_key(competition) if competition else None
    if sport_key:
        sport_keys = [sport_key]
    elif sport and sport in SPORT_PRIORITY_KEYS:
        sport_keys = SPORT_PRIORITY_KEYS[sport]
    else:
        sport_keys = PRIORITY_SPORTS

    for sk in sport_keys:
        events = get_odds_for_sport(sk)
        if not events:
            continue

        match = _find_event_in_odds(event_name, events)
        if match:
            return match

    return None


def get_best_odds_for_selection(event_name, team_name, competition=None, sport=None):
    """
    Get the best available odds for a specific team selection.

    Args:
        event_name: e.g. "Arsenal vs Chelsea"
        team_name: e.g. "Arsenal"
        competition: Optional competition name
        sport: Optional sport name (e.g. "football", "rugby")

    Returns:
        float — best decimal odds, or None.
    """
    prices = find_market_price(event_name, competition, sport=sport)
    if not prices:
        return None

    team_lower = team_name.lower()

    # Check home, draw, away
    for key in ("home", "away"):
        team = prices.get(f"{key}_team", "").lower()
        if team_lower in team or team in team_lower:
            return prices.get(key)

    # Fuzzy match on team name
    for key, team_field in (("home", "home_team"), ("away", "away_team")):
        team = prices.get(team_field, "").lower()
        first_word = team.split()[0] if team else ""
        if first_word and len(first_word) >= 4 and first_word in team_lower:
            return prices.get(key)

    return None


def _competition_to_sport_key(competition):
    """Map a competition name to an Odds API sport key."""
    if not competition:
        return None
    comp_lower = competition.lower()
    for name, key in SPORT_KEYS.items():
        if name in comp_lower or comp_lower in name:
            return key
    return None


def _find_event_in_odds(event_name, events):
    """
    Find a matching event in the odds API response.

    Returns dict with home/draw/away odds and team names, or None.
    """
    if not event_name or not events:
        return None

    event_lower = event_name.lower()

    for event in events:
        home = event.get("home_team", "")
        away = event.get("away_team", "")

        # Check if both teams appear in the event name
        home_match = home.lower() in event_lower or event_lower in home.lower()
        away_match = away.lower() in event_lower or event_lower in away.lower()

        # Or check first significant word
        if not home_match:
            first = home.split()[0].lower() if home else ""
            home_match = first and len(first) >= 4 and first in event_lower
        if not away_match:
            first = away.split()[0].lower() if away else ""
            away_match = first and len(first) >= 4 and first in event_lower

        if home_match or away_match:
            # Extract h2h odds from the first bookmaker
            bookmakers = event.get("bookmakers", [])
            if not bookmakers:
                continue

            for bookmaker in bookmakers:
                for market in bookmaker.get("markets", []):
                    if market.get("key") != "h2h":
                        continue
                    outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}
                    return {
                        "home": outcomes.get(home),
                        "draw": outcomes.get("Draw"),
                        "away": outcomes.get(away),
                        "home_team": home,
                        "away_team": away,
                        "bookmaker": bookmaker.get("title", "Unknown"),
                    }

    return None
