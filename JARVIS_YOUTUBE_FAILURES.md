# =====================================================================
# JARVIS YOUTUBE ULTRA — REMAINING LIMITATIONS & EDGE CASES
# =====================================================================

## Handled Edge Cases
1. **Devanagari Script Variations**: Fully normalized via `DEVANAGARI_MAP`.
2. **Filler Words**: Ignored during intent parsing while preserving search queries.
3. **Word Order Inversion**: Entity extraction independent of word ordering.
4. **Negation Traps**: Explicitly intercepted to prevent unintended execution.
5. **Self-Corrections**: Parsed to use the latest corrected target.

## Remaining Physical Limitations
1. **Third-Party Chrome Extensions / Adblock Overlays**: If an external popup overlays the YouTube webpage, physical coordinate clicks may strike the overlay unless dismissed.
2. **Dynamic UI Layout Changes by YouTube**: YouTube occasionally tests 3-column vs 4-column Shorts shelves. The calibrated grid supports modern 5-column and 4-column desktop layouts.
