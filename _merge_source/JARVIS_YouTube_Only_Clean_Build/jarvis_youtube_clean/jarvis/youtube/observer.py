from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs


class YouTubePageObserver:
    def __init__(self, page):
        self.page = page

    async def snapshot(self) -> dict:
        data = await self.page.evaluate("""
        () => {
          const v = document.querySelector('video');
          const flexy = document.querySelector('ytd-watch-flexy');
          const cc = document.querySelector('.ytp-subtitles-button');
          const mini = document.querySelector('.ytp-miniplayer-button');
          const fs = !!document.fullscreenElement;
          return {
            url: location.href,
            title: document.title,
            playback_state: v ? (v.paused ? 'PAUSED' : 'PLAYING') : 'UNKNOWN',
            current_time: v ? Number(v.currentTime || 0) : null,
            duration: v && Number.isFinite(v.duration) ? Number(v.duration) : null,
            volume: v ? Math.round(Number(v.volume || 0) * 100) : null,
            muted: v ? !!v.muted : null,
            playback_rate: v ? Number(v.playbackRate || 1) : null,
            fullscreen: fs,
            theater_mode: flexy ? !!(flexy.hasAttribute('theater') || flexy.hasAttribute('theater-requested_')) : null,
            miniplayer: !!document.querySelector('ytd-miniplayer, .ytp-player-minimized'),
            captions: cc ? cc.getAttribute('aria-pressed') === 'true' : null,
          };
        }
        """)
        url = data.get("url") or ""
        data["page_type"] = self._page_type(url)
        data["current_video_id"] = self.video_id(url)
        return data

    @staticmethod
    def _page_type(url: str) -> str:
        if "/shorts/" in url:
            return "SHORTS"
        if "/watch" in url:
            return "VIDEO"
        if "/results" in url:
            return "SEARCH_RESULTS"
        host = urlparse(url).netloc.lower()
        if "youtube.com" in host:
            return "HOME"
        return "OTHER"

    @staticmethod
    def video_id(url: str) -> str | None:
        if "/shorts/" in url:
            m = re.search(r"/shorts/([^?&#/]+)", url)
            return m.group(1) if m else None
        try:
            return parse_qs(urlparse(url).query).get("v", [None])[0]
        except Exception:
            return None

    async def candidates(self, kind: str) -> list[dict]:
        selector = 'a[href^="/shorts/"]' if kind == "short" else 'a[href^="/watch"]'
        raw = await self.page.evaluate("""
        (selector) => {
          const out = [];
          for (const a of document.querySelectorAll(selector)) {
            const r = a.getBoundingClientRect();
            const s = getComputedStyle(a);
            const visible = r.width > 20 && r.height > 20 && s.visibility !== 'hidden' && s.display !== 'none' && r.bottom > 0 && r.top < innerHeight;
            if (!visible) continue;
            const href = a.href || '';
            let title = a.getAttribute('title') || a.getAttribute('aria-label') || '';
            if (!title) {
              const container = a.closest('ytd-video-renderer, ytd-rich-item-renderer, ytd-reel-item-renderer, ytd-grid-video-renderer');
              title = container?.querySelector('#video-title, yt-formatted-string#video-title')?.textContent?.trim() || '';
            }
            out.push({href, title, x:r.x, y:r.y, width:r.width, height:r.height});
          }
          out.sort((a,b) => Math.abs(a.y-b.y) > 8 ? a.y-b.y : a.x-b.x);
          return out;
        }
        """, selector)
        seen = set()
        result = []
        for item in raw:
            vid = self.video_id(item.get("href", ""))
            if not vid or vid in seen:
                continue
            seen.add(vid)
            item["video_id"] = vid
            result.append(item)
        return result

    async def like_state(self) -> bool | None:
        return await self.page.evaluate("""
        () => {
          const candidates = [...document.querySelectorAll('button, yt-button-shape button')];
          for (const b of candidates) {
            const a = (b.getAttribute('aria-label') || '').toLowerCase();
            const t = (b.getAttribute('title') || '').toLowerCase();
            if (a.startsWith('like') || t === 'i like this') {
              const p = b.getAttribute('aria-pressed');
              if (p === 'true') return true;
              if (p === 'false') return false;
            }
          }
          return null;
        }
        """)
