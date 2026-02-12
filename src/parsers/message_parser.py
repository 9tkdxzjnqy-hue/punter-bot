import re

from src.config import Config

# Player nicknames used for result detection and test mode prefix matching
PLAYER_NICKNAMES = {"ed", "kev", "da", "don", "nug", "nialler", "pawn", "nugget"}

# Test mode prefix pattern: "Kev: some message" or "Ed: !stats"
TEST_PREFIX = re.compile(
    r"^(" + "|".join(PLAYER_NICKNAMES) + r")\s*:\s*(.+)$",
    re.IGNORECASE | re.DOTALL,
)

# Odds patterns
FRACTIONAL_ODDS = re.compile(r"\b(\d+/\d+)\b")
DECIMAL_ODDS = re.compile(r"\b(\d+\.\d{1,2})\b")
EVENS = re.compile(r"\bevens?\b", re.IGNORECASE)

# Result emojis
WIN_EMOJI = "\u2705"  # green check
LOSS_EMOJI = "\u274c"  # red cross

# Bet type keywords
BET_TYPE_PATTERNS = {
    "btts": re.compile(r"\bbtts\b", re.IGNORECASE),
    "over_under": re.compile(r"\b(over|under)\s+\d+\.?\d*\b", re.IGNORECASE),
    "handicap": re.compile(r"(?<!\d)[+-]\d+\.?\d*\b"),
    "ht_ft": re.compile(r"\bht[/_]?ft\b", re.IGNORECASE),
}


def extract_test_prefix(text):
    """
    In test mode, extract player prefix from messages like 'Kev: Manchester United 2/1'.

    Returns (sender_override, remaining_text) or (None, original_text).
    """
    if not Config.TEST_MODE:
        return None, text

    match = TEST_PREFIX.match(text.strip())
    if match:
        return match.group(1), match.group(2).strip()

    return None, text


def parse_message(text, sender="", sender_phone=""):
    """
    Classify a message and extract relevant data.

    Returns a dict with:
        type: 'command' | 'pick' | 'result' | 'general'
        raw_text: the original message
        sender: who sent it
        sender_phone: sender's phone number
        parsed_data: dict with type-specific fields
    """
    text = text.strip()

    if not text:
        return _make_result("general", text, sender, {}, sender_phone)

    # In test mode, extract player prefix (e.g., "Kev: Manchester United 2/1")
    sender_override, text = extract_test_prefix(text)
    if sender_override:
        sender = sender_override

    # Commands: starts with !
    if text.startswith("!"):
        return _parse_command(text, sender, sender_phone)

    # Results: player name + win/loss emoji
    result = _parse_result(text, sender, sender_phone)
    if result:
        return result

    # Picks: contains odds
    pick = _parse_pick(text, sender, sender_phone)
    if pick:
        return pick

    return _make_result("general", text, sender, {}, sender_phone)


def _parse_command(text, sender, sender_phone=""):
    """Parse a !command message."""
    parts = text[1:].strip().split()
    command = parts[0].lower() if parts else ""
    args = parts[1:] if len(parts) > 1 else []

    return _make_result("command", text, sender, {
        "command": command,
        "args": args,
    }, sender_phone)


def _parse_result(text, sender, sender_phone=""):
    """Detect result messages like 'Kev check_emoji' or 'DA cross_emoji'."""
    if WIN_EMOJI not in text and LOSS_EMOJI not in text:
        return None

    text_lower = text.lower()
    for nickname in PLAYER_NICKNAMES:
        if nickname in text_lower:
            outcome = "win" if WIN_EMOJI in text else "loss"
            return _make_result("result", text, sender, {
                "player_nickname": nickname,
                "outcome": outcome,
            }, sender_phone)

    return None


def _parse_pick(text, sender, sender_phone=""):
    """Detect pick submissions containing odds."""
    odds_original = None
    odds_decimal = None

    # Check for fractional odds (e.g. 2/1, 11/4)
    match = FRACTIONAL_ODDS.search(text)
    if match:
        odds_original = match.group(1)
        num, den = odds_original.split("/")
        odds_decimal = round(int(num) / int(den) + 1, 4)

    # Check for "evens"
    if not odds_original and EVENS.search(text):
        odds_original = "evens"
        odds_decimal = 2.0

    # Check for decimal odds (e.g. 2.0, 3.75)
    if not odds_original:
        match = DECIMAL_ODDS.search(text)
        if match:
            odds_original = match.group(1)
            odds_decimal = float(odds_original)

    if not odds_original:
        return None

    # Detect bet type
    bet_type = "win"
    for bt, pattern in BET_TYPE_PATTERNS.items():
        if pattern.search(text):
            bet_type = bt
            break

    # Description is the full text minus the odds
    description = text

    return _make_result("pick", text, sender, {
        "description": description,
        "odds_original": odds_original,
        "odds_decimal": odds_decimal,
        "bet_type": bet_type,
    }, sender_phone)


def _make_result(msg_type, text, sender, parsed_data, sender_phone=""):
    return {
        "type": msg_type,
        "raw_text": text,
        "sender": sender,
        "sender_phone": sender_phone,
        "parsed_data": parsed_data,
    }
