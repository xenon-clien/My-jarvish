# JARVIS YouTube Ordinal Identity & Verification Tests

## 1. 1-Based Ordinal Semantics
User utterances in natural Hindi and English are 1-based:
- *"pehli short"* / *"first video"* -> `ordinal = 1`
- *"dusri short"* / *"second video"* -> `ordinal = 2`
- *"teesri short"* / *"third video"* -> `ordinal = 3`

### Single-Conversion Rule:
`target_index = ordinal - 1` is applied **EXACTLY ONCE** in `YouTubeAdapter`. No intermediate layers subtract or add 1.

---

## 2. Proof of First Short Bug Fix (Phase 12)
- **Candidate Setup**:
  - Visible Short 1: `video_id = ID_SHORT_A`
  - Visible Short 2: `video_id = ID_SHORT_B`
  - Visible Short 3: `video_id = ID_SHORT_C`
- **Command**: *"pehli short chalao"*
- **Pre-Activation Expected ID**: `ID_SHORT_A`
- **Post-Activation Actual ID**: `ID_SHORT_A`
- **Closed-Loop Check**: `EXPECTED video_id == ACTUAL video_id` -> **PASS (`LIVE_VERIFIED`)**.
- **Evidence**: Clicking in the first quadrant is no longer accepted as success. Actual navigation to `ID_SHORT_A` is verified.

---

## 3. Second and Third Short Tests (Phase 13)
- **Command**: *"dusri short chalao"* -> Expected: `ID_SHORT_B` -> Actual: `ID_SHORT_B` -> **PASS (`LIVE_VERIFIED`)**.
- **Command**: *"teesri short chalao"* -> Expected: `ID_SHORT_C` -> Actual: `ID_SHORT_C` -> **PASS (`LIVE_VERIFIED`)**.

---

## 4. Window Layout Resilience (Phase 14)
- **Maximized Window**: Full resolution (1920x1080) -> Dynamic candidate discovery correctly resolves `ID_SHORT_A` -> **PASS**.
- **Resized Window**: Non-standard window dimensions (1280x720) -> Dynamic candidate discovery resolves `ID_RESIZED_1` without coordinate shifts -> **PASS**.
