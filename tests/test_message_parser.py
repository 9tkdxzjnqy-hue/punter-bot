import os

from src.parsers.message_parser import parse_message, extract_test_prefix


class TestCommandParsing:
    def test_help_command(self):
        result = parse_message("!help", "Kev")
        assert result["type"] == "command"
        assert result["parsed_data"]["command"] == "help"

    def test_stats_command(self):
        result = parse_message("!stats", "Ed")
        assert result["type"] == "command"
        assert result["parsed_data"]["command"] == "stats"

    def test_command_with_args(self):
        result = parse_message("!confirm penalty Nialler", "Ed")
        assert result["type"] == "command"
        assert result["parsed_data"]["command"] == "confirm"
        assert result["parsed_data"]["args"] == ["penalty", "Nialler"]

    def test_rotation_command(self):
        result = parse_message("!rotation", "Nug")
        assert result["type"] == "command"
        assert result["parsed_data"]["command"] == "rotation"


class TestPickParsing:
    def test_fractional_odds(self):
        result = parse_message("Manchester United 2/1", "Kev")
        assert result["type"] == "pick"
        assert result["parsed_data"]["odds_original"] == "2/1"
        assert result["parsed_data"]["odds_decimal"] == 3.0
        assert result["parsed_data"]["bet_type"] == "win"

    def test_fractional_odds_complex(self):
        result = parse_message("Arsenal 11/4", "DA")
        assert result["type"] == "pick"
        assert result["parsed_data"]["odds_original"] == "11/4"
        assert result["parsed_data"]["odds_decimal"] == 3.75

    def test_decimal_odds(self):
        result = parse_message("Liverpool 2.50", "Nug")
        assert result["type"] == "pick"
        assert result["parsed_data"]["odds_original"] == "2.50"
        assert result["parsed_data"]["odds_decimal"] == 2.50

    def test_evens(self):
        result = parse_message("Chelsea evens", "Pawn")
        assert result["type"] == "pick"
        assert result["parsed_data"]["odds_original"] == "evens"
        assert result["parsed_data"]["odds_decimal"] == 2.0

    def test_btts_detection(self):
        result = parse_message("Man City Brentford BTTS 8/11", "Ed")
        assert result["type"] == "pick"
        assert result["parsed_data"]["bet_type"] == "btts"

    def test_over_under_detection(self):
        result = parse_message("Ireland v England under 2.5 goals 6/4", "Kev")
        assert result["type"] == "pick"
        assert result["parsed_data"]["bet_type"] == "over_under"

    def test_handicap_detection(self):
        result = parse_message("Munster -13 at 4/5", "Nialler")
        assert result["type"] == "pick"
        assert result["parsed_data"]["bet_type"] == "handicap"

    def test_ht_ft_detection(self):
        result = parse_message("Liverpool HT/FT 3/1", "Pawn")
        assert result["type"] == "pick"
        assert result["parsed_data"]["bet_type"] == "ht_ft"

    def test_pick_with_emoji(self):
        result = parse_message("\u26bd Manchester United 2/1", "Kev")
        assert result["type"] == "pick"
        assert result["parsed_data"]["odds_original"] == "2/1"


class TestResultParsing:
    def test_win_result(self):
        result = parse_message("Kev \u2705", "Ed")
        assert result["type"] == "result"
        assert result["parsed_data"]["player_nickname"] == "kev"
        assert result["parsed_data"]["outcome"] == "win"

    def test_loss_result(self):
        result = parse_message("DA \u274c", "Ed")
        assert result["type"] == "result"
        assert result["parsed_data"]["player_nickname"] == "da"
        assert result["parsed_data"]["outcome"] == "loss"

    def test_nug_result(self):
        result = parse_message("Nug \u2705", "Ed")
        assert result["type"] == "result"
        assert result["parsed_data"]["player_nickname"] == "nug"

    def test_pawn_result(self):
        result = parse_message("Pawn \u274c", "Ed")
        assert result["type"] == "result"
        assert result["parsed_data"]["player_nickname"] == "pawn"

    def test_nialler_result(self):
        result = parse_message("Nialler \u2705", "Ed")
        assert result["type"] == "result"
        assert result["parsed_data"]["player_nickname"] == "nialler"


class TestGeneralMessages:
    def test_regular_chat(self):
        result = parse_message("hey lads, what's the story", "Kev")
        assert result["type"] == "general"

    def test_empty_message(self):
        result = parse_message("", "Kev")
        assert result["type"] == "general"

    def test_whitespace_only(self):
        result = parse_message("   ", "Kev")
        assert result["type"] == "general"

    def test_sender_preserved(self):
        result = parse_message("hello", "Nialler")
        assert result["sender"] == "Nialler"

    def test_raw_text_preserved(self):
        result = parse_message("!stats", "Ed")
        assert result["raw_text"] == "!stats"

    def test_sender_phone_preserved(self):
        result = parse_message("hello", "Kev", "353861234567@c.us")
        assert result["sender_phone"] == "353861234567@c.us"

    def test_sender_phone_default_empty(self):
        result = parse_message("hello", "Kev")
        assert result["sender_phone"] == ""


class TestTestMode:
    def test_prefix_extraction_when_enabled(self):
        os.environ["TEST_MODE"] = "true"
        from src.config import Config
        Config.TEST_MODE = True

        sender_override, body = extract_test_prefix("Kev: Manchester United 2/1")
        assert sender_override.lower() == "kev"
        assert body == "Manchester United 2/1"

    def test_prefix_extraction_with_command(self):
        from src.config import Config
        Config.TEST_MODE = True

        sender_override, body = extract_test_prefix("Ed: !confirm penalty Nialler")
        assert sender_override.lower() == "ed"
        assert body == "!confirm penalty Nialler"

    def test_prefix_extraction_result(self):
        from src.config import Config
        Config.TEST_MODE = True

        sender_override, body = extract_test_prefix("Ed: Kev \u2705")
        assert sender_override.lower() == "ed"
        assert body == "Kev \u2705"

    def test_no_prefix_when_disabled(self):
        from src.config import Config
        Config.TEST_MODE = False

        sender_override, body = extract_test_prefix("Kev: Manchester United 2/1")
        assert sender_override is None
        assert body == "Kev: Manchester United 2/1"

    def test_non_player_prefix_ignored(self):
        from src.config import Config
        Config.TEST_MODE = True

        sender_override, body = extract_test_prefix("John: Manchester United 2/1")
        assert sender_override is None
        assert body == "John: Manchester United 2/1"

    def test_full_parse_with_prefix(self):
        from src.config import Config
        Config.TEST_MODE = True

        result = parse_message("Kev: Manchester United 2/1", "Aidan")
        assert result["type"] == "pick"
        assert result["sender"].lower() == "kev"
        assert result["parsed_data"]["odds_original"] == "2/1"

        Config.TEST_MODE = False
