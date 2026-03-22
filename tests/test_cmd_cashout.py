"""Tests for !cashout command."""

import pytest

from src.db import get_db
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


def _complete_week(week_id, placer_id):
    conn = get_db()
    conn.execute(
        "UPDATE weeks SET status = 'completed', placer_id = ? WHERE id = ?",
        (placer_id, week_id),
    )
    conn.commit()
    conn.close()


def _insert_bet_slip(week_id, placer_id, stake=10.0, potential_return=500.0):
    conn = get_db()
    conn.execute(
        "INSERT INTO bet_slips (week_id, placer_id, stake, potential_return) VALUES (?, ?, ?, ?)",
        (week_id, placer_id, stake, potential_return),
    )
    conn.commit()
    conn.close()


def _get_slip(week_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM bet_slips WHERE week_id = ?", (week_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr("src.config.Config.GROUP_CHAT_ID", GROUP)
    monkeypatch.setattr("src.config.Config.ADMIN_NICKNAMES", ["ed"])
    from src.app import create_app
    return create_app().test_client()


class TestCashoutCommand:
    def test_non_admin_rejected(self, client):
        resp = _post(client, "Kev", "!cashout 158")
        data = resp.get_json()
        assert data["action"] == "replied"
        assert "admin" in data["reply"].lower()

    def test_no_args_returns_usage(self, client):
        resp = _post(client, "Ed", "!cashout")
        data = resp.get_json()
        assert data["action"] == "replied"
        assert "Usage" in data["reply"]

    def test_invalid_amount_returns_error(self, client):
        resp = _post(client, "Ed", "!cashout notanumber")
        data = resp.get_json()
        assert data["action"] == "replied"
        assert "Invalid" in data["reply"]

    def test_cashout_updates_existing_slip(self, client):
        players = get_all_players()
        ed = next(p for p in players if p["nickname"] == "Ed")
        week = get_or_create_current_week(group_id=GROUP)
        _complete_week(week["id"], ed["id"])
        _insert_bet_slip(week["id"], ed["id"], stake=10.0, potential_return=500.0)

        resp = _post(client, "Ed", "!cashout 158")
        data = resp.get_json()

        assert data["action"] == "replied"
        assert "158" in data["reply"]
        slip = _get_slip(week["id"])
        assert slip["cashed_out"] == 1
        assert slip["reloaded"] == 0
        assert abs(slip["actual_return"] - 158.0) < 0.01

    def test_cashout_with_reload_flag(self, client):
        players = get_all_players()
        ed = next(p for p in players if p["nickname"] == "Ed")
        week = get_or_create_current_week(group_id=GROUP)
        _complete_week(week["id"], ed["id"])
        _insert_bet_slip(week["id"], ed["id"], stake=10.0, potential_return=500.0)

        resp = _post(client, "Ed", "!cashout 158 reload")
        data = resp.get_json()

        assert data["action"] == "replied"
        assert "reload" in data["reply"].lower()
        slip = _get_slip(week["id"])
        assert slip["cashed_out"] == 1
        assert slip["reloaded"] == 1
        assert abs(slip["actual_return"] - 158.0) < 0.01

    def test_cashout_with_explicit_week_number(self, client):
        players = get_all_players()
        ed = next(p for p in players if p["nickname"] == "Ed")
        week = get_or_create_current_week(group_id=GROUP)
        _complete_week(week["id"], ed["id"])
        _insert_bet_slip(week["id"], ed["id"], stake=10.0, potential_return=1231.0)

        resp = _post(client, "Ed", f"!cashout {week['week_number']} 158 reload")
        data = resp.get_json()

        assert data["action"] == "replied"
        assert str(week["week_number"]) in data["reply"]
        slip = _get_slip(week["id"])
        assert slip["cashed_out"] == 1
        assert abs(slip["actual_return"] - 158.0) < 0.01

    def test_cashout_no_completed_week_returns_error(self, client):
        # Open week exists but no completed weeks
        get_or_create_current_week(group_id=GROUP)
        resp = _post(client, "Ed", "!cashout 158")
        data = resp.get_json()
        assert data["action"] == "replied"
        assert "No week found" in data["reply"]
