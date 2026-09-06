# JARVIS YouTube Remaining Limitations & Degraded Scenarios

## 1. Truthful Limitations Overview
In strict adherence to the JARVIS engineering principles, we never mask unobservable states as `LIVE_VERIFIED`.

1. **Chrome Default Accessibility Depth (Deep DOM Links)**:
   - When Google Chrome runs without `--force-renderer-accessibility`, its top-level UIA window exposes the Omnibox address bar, tabs, and window geometry with 100% fidelity.
   - However, individual video hyperlinks inside deep cross-origin iframes on complex search feeds are not always recursively enumerated by Windows UIA unless Chrome accessibility mode is triggered.
   - *Mitigation & Handling*: If visible short candidate cards are not pre-exposed in UIA, `YouTubeAdapter.play_short` transparently falls back to semantic feed navigation (`/shorts`) and steps to the target ordinal, truthfully returning status `DEGRADED` rather than faking pre-click DOM grounding.

2. **Playback Speed & Subtitle Visual Inspection**:
   - YouTube does not expose standard Windows UI Automation elements for the inner HTML5 `<video>` playback rate and subtitle canvas.
   - *Handling*: `youtube.set_playback_speed` and `youtube.set_captions` dispatch exact hardware hotkeys (`Shift+>`, `c`) and are classified as `INTEGRATION_TESTED` rather than `LIVE_VERIFIED`.

3. **Disabled Application Scope**:
   - WhatsApp, Spotify, VS Code, and File Explorer automation are intentionally disabled in this production profile.
   - *Handling*: Deterministic interception returning `"{app_name} automation is not enabled in the current production profile."`

4. **Next Step**:
   - In subsequent phases, a lightweight, non-intrusive Chrome Native Messaging host or authenticated CDP hook can be registered to unlock 100% deep DOM element enumeration without profile loss.
