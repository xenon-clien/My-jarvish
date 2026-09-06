# JARVIS YouTube Grounding Provider Architecture

## 1. Provider Evaluation Hierarchy
To satisfy the mandatory requirement that user login, cookies, and history are preserved without launching a blank browser profile, JARVIS evaluates grounding providers in strict priority:

1. **Chrome DevTools Protocol (CDP)**:
   - Tested: Queried `http://127.0.0.1:9222/json/list`.
   - Assessment: When Chrome is launched normally by the user without `--remote-debugging-port=9222`, the CDP port is not open.
   - Truthful Policy: We do NOT force-kill the user's Chrome or launch an isolated empty `--remote-debugging-port` session that throws away cookies and account login.

2. **Windows UI Automation (UIA) & Accessibility Tree (Primary Production Provider)**:
   - Technology: Windows native `UIAutomationCore.dll` via `comtypes.client`.
   - Desktop Attachment: Uses `SetThreadDesktop(OpenDesktopW('default', ...))` to seamlessly bridge background agent processes with the user's interactive desktop.
   - Capabilities:
     - Real-time Omnibox address bar URL extraction (Edit control `50004`).
     - Window handle, active foreground status, and window title extraction.
     - Dynamic button discovery (Like, Subscribe, Share) without screen percentages.
     - Live bounding rectangle extraction `(left, top, right, bottom)` for rendered elements.

3. **Deterministic Semantic In-Place Tab Navigation**:
   - Technology: Hardware `Ctrl+L` -> clipboard paste URL -> `Enter` in the existing active tab.
   - Assessment: Preserves 100% of user cookies, YouTube Premium / account login, watch history, and volume preferences.

---

## 2. Provider Selection Summary
- **Primary Live Grounding Provider**: Windows UI Automation (UIA) with Interactive Desktop Attachment.
- **Session Cookie Preservation**: 100% Guaranteed (Real user Chrome session utilized).
- **Fake Profile Launching**: Strictly prohibited and avoided.
