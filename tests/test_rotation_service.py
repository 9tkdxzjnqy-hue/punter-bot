"""Tests for rotation_service."""

from src.services.rotation_service import (
    get_next_placer, add_to_penalty_queue, advance_rotation, get_rotation_display,
)
from src.services.player_service import get_all_players
from src.services.week_service import get_or_create_current_week


class TestGetNextPlacer:
    def test_first_placer_is_kev(self):
        """With no history, the first in rotation (Kev, position 1) should be next."""
        placer = get_next_placer()
        assert placer is not None
        assert placer["nickname"] == "Kev"

    def test_rotation_advances(self):
        """After Kev places, Nialler (position 2) should be next."""
        week = get_or_create_current_week()
        players = get_all_players()

        # Kev is first (rotation_position=1)
        kev = next(p for p in players if p["nickname"] == "Kev")
        advance_rotation(week["id"], kev["id"])

        # Complete the week so rotation advances
        from src.db import get_db
        conn = get_db()
        conn.execute("UPDATE weeks SET status = 'completed' WHERE id = ?", (week["id"],))
        conn.commit()
        conn.close()

        placer = get_next_placer()
        assert placer["nickname"] == "Nialler"


class TestPenaltyQueue:
    def test_penalty_queue_takes_priority(self):
        """Penalty queue entries should come before standard rotation."""
        players = get_all_players()
        nug = next(p for p in players if p["nickname"] == "Nug")

        add_to_penalty_queue(nug["id"], "3 consecutive losses")

        placer = get_next_placer()
        assert placer["nickname"] == "Nug"

    def test_penalty_queue_processed(self):
        """After advancing, penalty entry should be marked processed."""
        week = get_or_create_current_week()
        players = get_all_players()
        nug = next(p for p in players if p["nickname"] == "Nug")

        add_to_penalty_queue(nug["id"], "3 consecutive losses")
        advance_rotation(week["id"], nug["id"])

        from src.db import get_db
        conn = get_db()
        conn.execute("UPDATE weeks SET status = 'completed' WHERE id = ?", (week["id"],))
        conn.commit()
        conn.close()

        # After processing, standard rotation resumes from after Nug (position 3)
        placer = get_next_placer()
        # Next after Nug in rotation is Pawn (position 4)
        assert placer["nickname"] == "Pawn"


class TestRotationDisplay:
    def test_display_returns_data(self):
        data = get_rotation_display()
        assert data["next_placer"] is not None
        assert isinstance(data["queue"], list)
        assert len(data["queue"]) > 0

    def test_display_has_all_players_in_queue(self):
        data = get_rotation_display()
        players = get_all_players()
        assert len(data["queue"]) == len(players)
