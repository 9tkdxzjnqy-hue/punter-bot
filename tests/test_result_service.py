"""Tests for result_service."""

from src.services.pick_service import submit_pick
from src.services.player_service import get_all_players
from src.services.result_service import (
    record_result, get_consecutive_losses, get_week_results,
    all_results_in, override_result,
)
from src.services.week_service import get_or_create_current_week


def _setup_pick(player_idx=0):
    """Helper: create a week and submit a pick for a player."""
    week = get_or_create_current_week()
    players = get_all_players()
    player = players[player_idx]
    pick, _, _, _ = submit_pick(player["id"], week["id"], "Test pick", 2.0, "evens", "win")
    return week, player, pick


class TestRecordResult:
    def test_record_win(self):
        week, player, pick = _setup_pick()
        result = record_result(pick["id"], "win", confirmed_by="Ed")
        assert result["outcome"] == "win"
        assert result["confirmed_by"] == "Ed"

    def test_record_loss(self):
        _, _, pick = _setup_pick()
        result = record_result(pick["id"], "loss")
        assert result["outcome"] == "loss"

    def test_update_existing_result(self):
        _, _, pick = _setup_pick()
        record_result(pick["id"], "loss")
        result = record_result(pick["id"], "win", confirmed_by="Ed")
        assert result["outcome"] == "win"


class TestConsecutiveLosses:
    def test_no_results(self):
        players = get_all_players()
        assert get_consecutive_losses(players[0]["id"]) == 0

    def test_streak_of_losses(self):
        week = get_or_create_current_week()
        players = get_all_players()
        player = players[0]

        # Create 3 weeks with losses
        from src.db import get_db
        conn = get_db()
        for i in range(3):
            wk_num = i + 10
            conn.execute(
                "INSERT INTO weeks (week_number, season, deadline, status) VALUES (?, '2026', '2026-01-01', 'completed')",
                (wk_num,),
            )
            wk_id = conn.execute("SELECT id FROM weeks WHERE week_number = ?", (wk_num,)).fetchone()[0]
            conn.execute(
                "INSERT INTO picks (week_id, player_id, description, odds_decimal, odds_original) VALUES (?, ?, 'test', 2.0, 'evens')",
                (wk_id, player["id"]),
            )
            pick_id = conn.execute(
                "SELECT id FROM picks WHERE week_id = ? AND player_id = ?",
                (wk_id, player["id"]),
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO results (pick_id, outcome, confirmed_at) VALUES (?, 'loss', datetime('now', ? || ' minutes'))",
                (pick_id, str(i)),
            )
        conn.commit()
        conn.close()

        assert get_consecutive_losses(player["id"]) == 3

    def test_streak_broken_by_win(self):
        week = get_or_create_current_week()
        players = get_all_players()
        player = players[0]

        from src.db import get_db
        conn = get_db()
        outcomes = ["loss", "loss", "win"]  # most recent first (loss, loss, win)
        for i, outcome in enumerate(outcomes):
            wk_num = 20 + i
            conn.execute(
                "INSERT INTO weeks (week_number, season, deadline, status) VALUES (?, '2026', '2026-01-01', 'completed')",
                (wk_num,),
            )
            wk_id = conn.execute("SELECT id FROM weeks WHERE week_number = ?", (wk_num,)).fetchone()[0]
            conn.execute(
                "INSERT INTO picks (week_id, player_id, description, odds_decimal, odds_original) VALUES (?, ?, 'test', 2.0, 'evens')",
                (wk_id, player["id"]),
            )
            pick_id = conn.execute(
                "SELECT id FROM picks WHERE week_id = ? AND player_id = ?",
                (wk_id, player["id"]),
            ).fetchone()[0]
            # Most recent first: i=0 is newest, so use negative offset
            conn.execute(
                "INSERT INTO results (pick_id, outcome, confirmed_at) VALUES (?, ?, datetime('now', ? || ' minutes'))",
                (pick_id, outcome, str(-i)),
            )
        conn.commit()
        conn.close()

        assert get_consecutive_losses(player["id"]) == 2


class TestWeekResults:
    def test_get_week_results(self):
        week, player, pick = _setup_pick(0)
        record_result(pick["id"], "win")

        results = get_week_results(week["id"])
        assert len(results) == 1
        assert results[0]["outcome"] == "win"
        assert results[0]["nickname"] is not None

    def test_all_results_in(self):
        week = get_or_create_current_week()
        players = get_all_players()

        # Submit and record results for all players
        for player in players:
            pick, _, _, _ = submit_pick(player["id"], week["id"], "Test", 2.0, "evens", "win")
            record_result(pick["id"], "win")

        assert all_results_in(week["id"]) is True

    def test_not_all_results_in(self):
        week = get_or_create_current_week()
        players = get_all_players()

        pick, _, _, _ = submit_pick(players[0]["id"], week["id"], "Test", 2.0, "evens", "win")
        submit_pick(players[1]["id"], week["id"], "Test 2", 3.0, "2/1", "win")
        record_result(pick["id"], "win")

        assert all_results_in(week["id"]) is False


class TestOverrideResult:
    def test_override(self):
        week, player, pick = _setup_pick()
        record_result(pick["id"], "loss")

        result = override_result(player["id"], week["id"], "win", confirmed_by="Ed")
        assert result["outcome"] == "win"

    def test_override_no_pick(self):
        week = get_or_create_current_week()
        players = get_all_players()
        result = override_result(players[0]["id"], week["id"], "win")
        assert result is None
