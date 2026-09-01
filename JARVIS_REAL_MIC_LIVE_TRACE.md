# =====================================================================
# JARVIS REAL-MIC LIVE TRACE DIAGNOSTIC REPORT
# =====================================================================

## 1. Actual Desktop Entrypoint
- **Launcher File**: `JARVIS.bat`
- **Title**: `J.A.R.V.I.S. High-Speed AI Terminal`
- **Execution Target**: `scripts/voice_cli.py`
- **Runtime Environment**: Python 3.14.0 (64-bit) on Windows 10

---

## 2. Microphone Hardware State
- **Device Name**: `Microphone (Realtek High Definition Audio)`
- **Device Index**: `1`
- **Hardware Channels**: 2
- **Native Rate**: 44,100.0 Hz (captured at 16,000 Hz Mono int16)
- **Device Status**: **HEALTHY & STREAMING NON-ZERO AUDIO**

---

## 3. Ambient Room Noise Measurements (3.0s Live Baseline)
- **Ambient Mean RMS**: `211.85`
- **Ambient Median RMS**: `211.33`
- **Ambient p90 RMS**: `244.27 - 260.59`
- **Ambient Max RMS**: `270.89 - 370.34`
- **Ambient Max Peak**: `1,109`

---

## 4. Signal Separation & Threshold Analysis
- **Old Faulty Threshold (`max(mean*1.35, mean+35)`)**: `286.00`
- **Ambient Spike Level**: `289.44` RMS (Peak: `739`)
- **Fault Mechanism**: The ambient noise spikes ($289.44$) exceeded the trigger threshold ($286.00$), causing the VAD to falsely trigger on pure room/fan noise immediately upon loop initialization.
- **Calculated Silence Cutoff**: `243.63`
- **Resulting Behavior**: The engine entered `speech_started = True` on background noise, buffered 63 chunks (129 KB) of fan hum over 5–12 seconds, sent empty noise to Google STT, returned `None`, and immediately re-entered another 12-second false capture loop.

---

## 5. Live Speech Detection Results
- **User Speech Peak RMS During Test**: `289.44` (Ambient spike)
- **User Speech Crossed Threshold**: `YES (False Positive on Ambient Spike)`
- **VAD Speech Start**: `FAIL (Triggered on background air noise, not speech)`
- **Phrase Captured**: `FAIL (Captured 129,024 bytes of background noise)`
- **STT Candidate [en-IN]**: `None`
- **STT Candidate [hi-IN]**: `None`
- **Raw Transcript**: `None (Audio contained only ambient noise)`

---

## 6. Wake Word & State Machine Audit
- **Wake Word Mode Enabled on Startup**: `NO` (`is_standby == False` by default; direct commands supported)
- **Wake Word Required**: `NO`
- **Rejected by Wake Gate**: `NO`
- **Assistant Awake**: `YES`
- **TTS Blocking**: `NO` (`is_speaking == False`, last spoken age > 10.0s)

---

## 7. Command Processor & Exception Audit
- **CommandProcessor Entered**: `NO (Blocked by empty STT transcript from noise loop)`
- **Voice Loop Exceptions**: `None (Loop remained alive, but blocked in cyclic false-recording)`

---

## 8. First Real Failing Layer
**Layer 5: Voice Activity Detection (VAD) Threshold & Signal-to-Noise Ratio (SNR) Separation**.

---

## 9. Exact Root Cause
1. **Mathematical Under-Thresholding**: The dynamic threshold multiplier ($1.35\times$ mean) set the speech trigger point ($286$ RMS) directly inside the ambient room noise spike envelope ($270 - 370$ RMS).
2. **Noise Capture Trap**: Falsely triggered recordings consumed 5 to 12 seconds per cycle recording room hum. Real user speech was either spoken while the engine was waiting for STT API responses or drowned inside 12 seconds of leading fan noise.
3. **Missing Peak Energy Gating**: The VAD relied solely on chunk RMS without checking peak amplitude ($> 1,500$), allowing low-amplitude ambient noise ($peak < 800$) to masquerade as human vocal cord energy.
