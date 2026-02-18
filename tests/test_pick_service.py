"""Tests for pick_service."""

from src.services.pick_service import (
    submit_pick, get_picks_for_week, get_missing_players, all_picks_in, get_player_pick,
)
from src.services.player_service import get_all_players
from src.services.week_service import get_or_create_current_week


class TestSubmitPick:
    def test_submit_new_pick(self):
        week = get_or_create_current_week()
        players = get_all_players()
        player = players[0]

        pick, is_update, changed, _ = submit_pick(
            player_id=player["id"],
            week_id=week["id"],
            description="Man Utd to win",
            odds_decimal=3.0,
            odds_original="2/1",
            bet_type="win",
        )

        assert pick is not None
        assert pick["description"] == "Man Utd to win"
        assert pick["odds_original"] == "2/1"
        assert is_update is False
        assert changed is True

    def test_submit_pick_update(self):
        week = get_or_create_current_week()
        players = get_all_players()
        player = players[0]

        submit_pick(player["id"], week["id"], "Man Utd", 3.0, "2/1", "win")
        pick, is_update, changed, _ = submit_pick(player["id"], week["id"], "Arsenal", 2.5, "6/4", "win")

        assert pick["description"] == "Arsenal"
        assert pick["odds_original"] == "6/4"
        assert is_update is True
        assert changed is True

    def test_submit_pick_unchanged_resubmission(self):
        """Re-submitting same pick returns changed=False."""
        week = get_or_create_current_week()
        players = get_all_players()
        player = players[0]

        submit_pick(player["id"], week["id"], "Man Utd 2/1", 3.0, "2/1", "win")
        pick, is_update, changed, _ = submit_pick(player["id"], week["id"], "Man Utd 2/1", 3.0, "2/1", "win")

        assert is_update is True
        assert changed is False


class TestGetPicks:
    def test_get_picks_for_week(self):
        week = get_or_create_current_week()
        players = get_all_players()

        submit_pick(players[0]["id"], week["id"], "Pick 1", 2.0, "evens", "win")
        submit_pick(players[1]["id"], week["id"], "Pick 2", 3.0, "2/1", "win")

        picks = get_picks_for_week(week["id"])
        assert len(picks) == 2

    def test_get_missing_players(self):
        week = get_or_create_current_week()
        players = get_all_players()

        # Submit for first 2 players
        submit_pick(players[0]["id"], week["id"], "Pick 1", 2.0, "evens", "win")
        submit_pick(players[1]["id"], week["id"], "Pick 2", 3.0, "2/1", "win")

        missing = get_missing_players(week["id"])
        assert len(missing) == 4  # 6 total - 2 submitted

    def test_all_picks_in(self):
        week = get_or_create_current_week()
        players = get_all_players()

        # Submit for all players
        for i, player in enumerate(players):
            submit_pick(player["id"], week["id"], f"Pick {i}", 2.0, "evens", "win")

        assert all_picks_in(week["id"]) is True

    def test_not_all_picks_in(self):
        week = get_or_create_current_week()
        players = get_all_players()

        submit_pick(players[0]["id"], week["id"], "Pick 1", 2.0, "evens", "win")

        assert all_picks_in(week["id"]) is False

    def test_get_player_pick(self):
        week = get_or_create_current_week()
        players = get_all_players()

        submit_pick(players[0]["id"], week["id"], "Arsenal BTTS", 2.5, "6/4", "btts")

        pick = get_player_pick(week["id"], players[0]["id"])
        assert pick is not None
        assert pick["description"] == "Arsenal BTTS"

    def test_get_player_pick_none(self):
        week = get_or_create_current_week()
        players = get_all_players()

        pick = get_player_pick(week["id"], players[0]["id"])
        assert pick is None
