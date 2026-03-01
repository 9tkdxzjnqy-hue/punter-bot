from src.services.player_service import lookup_player


class TestLookupPlayerAlias:
    def test_don_resolves_to_da(self):
        """'Don' is an alias for DA (Declan)."""
        player = lookup_player(sender_name="Don")
        assert player is not None
        assert player["nickname"] == "DA"

    def test_don_case_insensitive(self):
        player = lookup_player(sender_name="don")
        assert player is not None
        assert player["nickname"] == "DA"

    def test_nickname_still_works(self):
        player = lookup_player(sender_name="DA")
        assert player is not None
        assert player["nickname"] == "DA"

    def test_name_still_works(self):
        player = lookup_player(sender_name="Declan")
        assert player is not None
        assert player["nickname"] == "DA"

    def test_unknown_alias_returns_none(self):
        player = lookup_player(sender_name="BigD")
        assert player is None
