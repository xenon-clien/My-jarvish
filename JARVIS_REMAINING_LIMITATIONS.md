# =====================================================================
# JARVIS REMAINING LIMITATIONS & FUTURE ROADMAP
# =====================================================================

## Honest Technical Boundaries
1. **Tier 3 vs Deep Tier 1 Support for 144 Desktop Applications**:
   - Applications like Photoshop, Blender, and Excel can be launched, focused, minimized, and closed via OS APIs.
   - Deep in-app actions (e.g., manipulating layers in Photoshop or formulas in Excel) require dedicated Tier 1 UIAutomation adapters.
2. **Browser DOM Access Dependent on Foreground Window**:
   - For web apps (YouTube), key shortcuts require foreground focus via Win32 API.
3. **Continuous Integration Audio Mocking**:
   - Tests requiring hardware audio input streams (`sounddevice`) must use mock fixtures in headless CI environments.
4. **Parallel `3.0/` Directory**:
   - Remains as an unintegrated experimental reference and should be archived in future maintenance releases.
