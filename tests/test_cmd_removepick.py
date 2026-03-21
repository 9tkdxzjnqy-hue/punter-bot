"""Tests for !removepick command and post-placement pick locks."""

import pytest

from src.db import get_db
from src.services.pick_service import submit_pick, get_player_pick
from src.services.player_service import get_all_players
from src.services.week_service import get_or_create_current_week

GROUP = "test-group@g.us"


def _post(client, sender, body):
    return client.post(
        "/webhook",
        json={
            "sender": sender,
            "sender_phone": "",
            "body": body,
            "group_id": GROUP,
            "has_media": False,
        },
        content_type="application/json",
    )


def _set_placer_id(week_id, player_id):
    conn = get_db()
    conn.execute("UPDATE weeks SET placer_id = ? WHERE id = ?", (player_id, week_id))
    conn.commit()
    conn.close()


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr("src.app.is_within_submission_window", lambda group_id="default": True)
    monkeypatch.setattr("src.config.Config.GROUP_CHAT_ID", GROUP)
    from src.app import create_app
    return create_app().test_client()


class TestRemovePick:
    def test_removes_existing_pick(self, client):
        week = get_or_create_current_week(group_id=GROUP)
        players = get_all_players()
        kev = next(p for p in players if p["nickname"] == "Kev")
        submit_pick(kev["id"], week["id"], "Liverpool to win", 3.0, "2/1", "win")

        resp = _post(client, "Kev", "!removepick")
        data = resp.get_json()

        assert data["action"] == "replied"
        assert "removed" in data["reply"].lower()
        assert get_player_pick(week["id"], kev["id"]) is None

    def test_no_pick_to_remove(self, client):
        get_or_create_current_week(group_id=GROUP)

        resp = _post(client, "Kev", "!removepick")
        data = resp.get_json()

        assert data["action"] == "replied"
        assert "no pick" in data["reply"].lower()

    def test_locked_when_bet_placed(self, client):
        week = get_or_create_current_week(group_id=GROUP)
        players = get_all_players()
        kev = next(p for p in players if p["nickname"] == "Kev")
        ed = next(p for p in players if p["nickname"] == "Ed")
        submit_pick(kev["id"], week["id"], "Liverpool to win", 3.0, "2/1", "win")
        _set_placer_id(week["id"], ed["id"])

        resp = _post(client, "Kev", "!removepick")
        data = resp.get_json()

        assert data["action"] == "replied"
        assert "placed" in data["reply"].lower() or "locked" in data["reply"].lower()
        assert get_player_pick(week["id"], kev["id"]) is not None

    def test_unknown_player_silent(self, client):
        resp = _post(client, "Stranger", "!removepick")
        data = resp.get_json()

        assert data["action"] == "no_reply"


class TestPostPlacementLock:
    def test_single_pick_ignored_after_placement(self, client):
        """Regular pick submission is silently ignored once bet is placed."""
        week = get_or_create_current_week(group_id=GROUP)
        players = get_all_players()
        kev = next(p for p in players if p["nickname"] == "Kev")
        ed = next(p for p in players if p["nickname"] == "Ed")
        _set_placer_id(week["id"], ed["id"])

        resp = _post(client, "Kev", "Liverpool 2/1")
        data = resp.get_json()

        assert data["action"] == "no_reply"
        assert get_player_pick(week["id"], kev["id"]) is None

    def test_cumulative_pick_ignored_after_placement(self, client):
        """Emoji-prefix pick is silently ignored once bet is placed."""
        conn = get_db()
        conn.execute("UPDATE players SET emoji = '🧌' WHERE nickname = 'Kev'")
        conn.commit()
        conn.close()

        week = get_or_create_current_week(group_id=GROUP)
        players = get_all_players()
        kev = next(p for p in players if p["nickname"] == "Kev")
        ed = next(p for p in players if p["nickname"] == "Ed")
        _set_placer_id(week["id"], ed["id"])

        resp = _post(client, "Kev", "🧌 Arsenal 2/1")
        data = resp.get_json()

        assert data["action"] == "no_reply"
        assert get_player_pick(week["id"], kev["id"]) is None
