from jarvis.core.parser import FastParser

p = FastParser()


def test_first_short_one_based():
    i = p.parse("pehli short chala")
    assert i and i.action == "play_short" and i.arguments["ordinal"] == 1


def test_third_short():
    i = p.parse("third short play karo")
    assert i and i.action == "play_short" and i.arguments["ordinal"] == 3


def test_search_query():
    i = p.parse("YouTube pe MrBeast search karo")
    assert i and i.action == "search" and "mrbeast" in i.arguments["query"]


def test_timestamp():
    i = p.parse("2 minute 30 second pe jao")
    assert i and i.action == "seek_timestamp" and i.arguments["seconds"] == 150


def test_volume():
    i = p.parse("volume 40 kar do")
    assert i and i.action == "set_volume" and i.arguments["level"] == 40


def test_context_next_short():
    i = p.parse("agli wali", {"application": "youtube", "page_type": "SHORTS"})
    assert i and i.action == "next_short"
