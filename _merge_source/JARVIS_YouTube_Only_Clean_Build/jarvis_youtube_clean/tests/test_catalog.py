from jarvis.youtube.catalog import ACTIONS


def test_exact_25_actions():
    assert len(ACTIONS) == 25
    assert "play_short" in ACTIONS
    assert "set_like" in ACTIONS
    assert "seek_timestamp" in ACTIONS
