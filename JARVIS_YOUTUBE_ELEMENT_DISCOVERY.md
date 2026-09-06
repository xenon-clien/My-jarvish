# JARVIS YouTube Dynamic Element Discovery Specification

## 1. Discovery Architecture
Rather than assuming where elements render on screen, `YouTubePageObserver` dynamically discovers visible candidates from the running browser window.

```python
@dataclass
class YouTubeCandidate:
    candidate_type: str        # "short" or "video"
    video_id: str              # 11-character YouTube video ID
    title: str                 # Rendered video/short title
    canonical_url: str         # Full URL (e.g. https://www.youtube.com/shorts/ID)
    href: str                  # Relative path (e.g. /shorts/ID)
    bounding_rect: Optional[Tuple[int, int, int, int]]  # (left, top, right, bottom)
    visual_order: int          # 1-based order in which element appears visually
    is_visible: bool           # Filtered for visible render nodes
    is_interactable: bool      # Sized and non-zero area
```

---

## 2. Filtering & Deduplication Rules
- **Non-Visible Node Rejection**: Elements with width <= 0 or height <= 0 are rejected.
- **Deduplication by Video ID**: YouTube frequently renders multiple links to the same video (thumbnail link, title link, channel avatar). The candidate extractor deduplicates using unique 11-character `video_id`.
- **Visual Order Sorting**: Candidates are indexed sequentially by rendering position (`visual_order`), guaranteeing that user ordinal `N` maps directly to candidate index `N - 1`.
