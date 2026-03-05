"""Tests for early kickoff warning in butler.py."""

import src.butler as butler


class TestEarlyKickoffNote:
    """Tests for _early_kickoff_note — individual pick warning."""

    def test_friday_evening_is_early(self):
        """Friday 8PM kickoff should trigger a warning."""
        # Friday March 6, 2026 at 20:00 UTC (GMT, no DST)
        note = butler._early_kickoff_note("2026-03-06T20:00:00")
        assert note is not None
        assert "Friday" in note
        assert "8:00 PM" in note
        assert "all picks and the bet must be in before then" in note

    def test_saturday_3pm_no_warning(self):
        """Saturday 3PM kickoff should not trigger a warning."""
        # Saturday March 7, 2026 at 15:00 UTC
        note = butler._early_kickoff_note("2026-03-07T15:00:00")
        assert note is None

    def test_saturday_morning_is_early(self):
        """Saturday 11AM kickoff should trigger a warning (before 12:30)."""
        # Saturday March 7, 2026 at 11:00 UTC
        note = butler._early_kickoff_note("2026-03-07T11:00:00")
        assert note is not None
        assert "Saturday" in note
        assert "11:00 AM" in note

    def test_saturday_1230_no_warning(self):
        """Saturday 12:30 PM exactly should not trigger a warning."""
        note = butler._early_kickoff_note("2026-03-07T12:30:00")
        assert note is None

    def test_saturday_1229_is_early(self):
        """Saturday 12:29 PM should trigger a warning."""
        note = butler._early_kickoff_note("2026-03-07T12:29:00")
        assert note is not None
        assert "Saturday" in note

    def test_thursday_evening_is_early(self):
        """Thursday evening kickoff should trigger a warning."""
        # Thursday March 5, 2026 at 19:45 UTC
        note = butler._early_kickoff_note("2026-03-05T19:45:00")
        assert note is not None
        assert "Thursday" in note
        assert "7:45 PM" in note

    def test_sunday_no_warning(self):
        """Sunday kickoff is not early (past the deadline window)."""
        note = butler._early_kickoff_note("2026-03-08T15:00:00")
        assert note is None

    def test_none_kickoff(self):
        """None kickoff returns None."""
        assert butler._early_kickoff_note(None) is None

    def test_empty_string(self):
        """Empty string returns None."""
        assert butler._early_kickoff_note("") is None

    def test_bst_friday_evening(self):
        """During BST, UTC 19:00 Friday = Dublin 8:00 PM Friday."""
        # June 5, 2026 (Friday) at 19:00 UTC = 20:00 Dublin (BST)
        note = butler._early_kickoff_note("2026-06-05T19:00:00")
        assert note is not None
        assert "Friday" in note
        assert "8:00 PM" in note


class TestEarliestKickoffWarning:
    """Tests for earliest_kickoff_warning — week-level status warning."""

    def test_friday_pick_warns(self):
        """A Friday 8PM pick in the week should produce a warning."""
        picks = [
            {"kickoff": "2026-03-06T20:00:00"},
            {"kickoff": "2026-03-07T15:00:00"},
        ]
        warning = butler.earliest_kickoff_warning(picks)
        assert warning is not None
        assert "Friday" in warning
        assert "8:00 PM" in warning
        assert "all picks must be in before then" in warning

    def test_only_saturday_afternoon_no_warning(self):
        """Only Saturday 3PM picks — no warning."""
        picks = [
            {"kickoff": "2026-03-07T15:00:00"},
            {"kickoff": "2026-03-07T17:30:00"},
        ]
        warning = butler.earliest_kickoff_warning(picks)
        assert warning is None

    def test_earliest_of_multiple_early_picks(self):
        """When multiple early kickoffs exist, shows the earliest one."""
        picks = [
            {"kickoff": "2026-03-06T20:00:00"},  # Friday 8PM
            {"kickoff": "2026-03-06T19:00:00"},  # Friday 7PM — earlier
            {"kickoff": "2026-03-07T15:00:00"},  # Saturday 3PM
        ]
        warning = butler.earliest_kickoff_warning(picks)
        assert warning is not None
        assert "7:00 PM" in warning

    def test_empty_list(self):
        """Empty picks list returns None."""
        assert butler.earliest_kickoff_warning([]) is None

    def test_none_input(self):
        """None input returns None."""
        assert butler.earliest_kickoff_warning(None) is None

    def test_picks_without_kickoff(self):
        """Picks without kickoff data are ignored."""
        picks = [
            {"kickoff": None},
            {},
        ]
        warning = butler.earliest_kickoff_warning(picks)
        assert warning is None

    def test_mix_of_matched_and_unmatched(self):
        """Unmatched picks (no kickoff) are ignored, early matched picks warn."""
        picks = [
            {"kickoff": "2026-03-06T20:00:00"},  # Friday 8PM
            {"kickoff": None},  # unmatched
        ]
        warning = butler.earliest_kickoff_warning(picks)
        assert warning is not None
        assert "Friday" in warning

    def test_wednesday_kickoff_is_earliest(self):
        """Wednesday kickoff should be detected as early."""
        picks = [
            {"kickoff": "2026-03-04T19:45:00"},  # Wednesday 7:45PM
        ]
        warning = butler.earliest_kickoff_warning(picks)
        assert warning is not None
        assert "Wednesday" in warning
