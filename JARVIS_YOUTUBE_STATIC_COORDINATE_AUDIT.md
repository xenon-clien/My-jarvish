# JARVIS YouTube Static Coordinate Elimination Audit

## 1. Forensic Audit of Removed Coordinates
A comprehensive audit of the production codebase identified hardcoded screen coordinate tables and percentage approximations that previously broke under window resize, zoom, or layout shifts.

### Previous Offending Coordinate Tables (Now Completely Removed):

1. **Shorts Shelf Grid in `backend/tools/browser_tools.py` (Lines 226-232)**:
   - `shorts_grid = {1: (x=22%), 2: (x=38%), 3: (x=54%), 4: (x=70%), 5: (x=86%)}`
   - *Status*: **COMPLETELY ELIMINATED**. Replaced by `YouTubePageObserver.discover_short_candidates()` and semantic 1-based ordinal resolution.

2. **Playlist Video Offsets in `backend/tools/browser_tools.py` (Lines 263-270)**:
   - `playlist_offsets = {1: 0.38, 2: 0.51, 3: 0.64, 4: 0.77, 5: 0.90}`
   - *Status*: **COMPLETELY ELIMINATED**. Replaced by dynamic video candidate discovery.

3. **Sidebar Video Recommendations in `backend/tools/browser_tools.py` (Lines 276-282)**:
   - `sidebar_offsets = {1: 0.38, 2: 0.52, 3: 0.66, 4: 0.80}`
   - *Status*: **COMPLETELY ELIMINATED**. Replaced by dynamic candidate discovery.

4. **Home Feed Multi-Column Grid in `backend/tools/browser_tools.py` (Lines 287-295)**:
   - `home_grid = {1: (0.35, 0.45), 2: (0.60, 0.45), 3: (0.85, 0.45), 4: (0.35, 0.82), 5: (0.60, 0.82), 6: (0.85, 0.82)}`
   - *Status*: **COMPLETELY ELIMINATED**. Replaced by dynamic video candidate discovery.

5. **Search Results Offsets in `backend/tools/browser_tools.py` (Lines 301-308)**:
   - `search_offsets = {1: 0.35, 2: 0.50, 3: 0.65, 4: 0.80}`
   - *Status*: **COMPLETELY ELIMINATED**. Replaced by direct video candidate activation.

6. **Spatial Reference Grid in `backend/ai/state_observer.py` (Lines 170-198)**:
   - Hardcoded percentages: `0.25`, `0.55`, `0.82`, `0.75`, `0.20`, `0.40`.
   - *Status*: **COMPLETELY ELIMINATED**. Replaced by center calculation on live element bounding boxes.

7. **Like / Subscribe / Share Coordinates in `backend/tools/media_tools.py`**:
   - Hardcoded offsets: `0.64`, `0.54`, `0.44`, `0.63`, `0.46`, `0.88`, `0.35`.
   - *Status*: **COMPLETELY ELIMINATED**. Replaced by live UIA button discovery (`UIA_ButtonControlTypeId`).

---

## 2. Zero-Coordinate Verification Result
A rigorous search across `backend/` confirms that **ZERO** static ordinal coordinates or percentage tables remain in the active production execution path.
