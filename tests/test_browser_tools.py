"""Unit tests for web, YouTube, and browser automation tools."""
import pytest
from backend.tools.browser_tools import (
    close_browser_tab,
    get_quick_answer,
    open_website,
    play_youtube_video,
    search_spotify,
    search_web,
)


def test_play_youtube_video(monkeypatch):
    """Test YouTube direct video playback and URL resolution."""
    opened_urls = []
    monkeypatch.setattr("backend.tools.browser_tools.is_live_browser_automation_allowed", lambda: True)
    monkeypatch.setattr("backend.tools.browser_tools.launch_in_google_chrome", lambda url: opened_urls.append(url))
    monkeypatch.setattr("webbrowser.open", lambda url, new=0, autoraise=True: opened_urls.append(url))
    monkeypatch.setattr("subprocess.Popen", lambda cmd, shell=True: opened_urls.append(cmd))

    res = play_youtube_video("Boyfriend song")
    assert res["status"] == "success"
    assert "youtube.com" in res["url"]
    assert "Boss" in res["message"]

    res_empty = play_youtube_video("")
    assert res_empty["status"] == "success"
    assert "Boss" in res_empty["message"]


def test_close_browser_tab():
    """Test sending close tab shortcut command."""
    res = close_browser_tab(target="youtube")
    assert res["status"] in ["success", "unsupported", "SIMULATED"]
    assert "Boss" in res["message"] or "Tab" in res["message"] or "tab" in res["message"] or "Simulation" in res["message"]


def test_search_web(monkeypatch):
    """Test Google and DuckDuckGo search URL generation."""
    opened_urls = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened_urls.append(url))
    monkeypatch.setattr("backend.tools.browser_tools.launch_in_google_chrome", lambda url: opened_urls.append(url))

    res_google = search_web("FastAPI python", search_engine="google")
    assert res_google["status"] == "success"
    assert "google.com/search?q=" in res_google["url"]

    res_ddg = search_web("Python tutorial", search_engine="duckduckgo")
    assert res_ddg["status"] == "success"
    assert "duckduckgo.com/?q=" in res_ddg["url"]


def test_open_website(monkeypatch):
    """Test URL prepending and navigation."""
    opened_urls = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened_urls.append(url))
    monkeypatch.setattr("backend.tools.browser_tools.launch_in_google_chrome", lambda url: opened_urls.append(url))

    res = open_website("github.com")
    assert res["status"] == "success"
    assert res["url"] == "https://github.com"


def test_search_spotify(monkeypatch):
    """Test Spotify search URL formatting."""
    opened_urls = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened_urls.append(url))

    res = search_spotify("Arijit Singh")
    assert res["status"] == "success"
    assert "open.spotify.com/search" in res["url"]


def test_get_quick_answer():
    """Test Wikipedia instant summary API."""
    res = get_quick_answer("Python (programming language)")
    assert "status" in res
    if res["status"] == "success":
        assert "Python" in res["title"]
        assert len(res["summary"]) > 20


def test_click_screen_video():
    """Test click screen video tool execution."""
    from backend.tools.browser_tools import click_screen_video
    res = click_screen_video(index=1)
    assert res["status"] in ["success", "unsupported", "SIMULATED"]
    assert "Boss" in res["message"] or "requires" in res["message"] or "Simulation" in res["message"]
