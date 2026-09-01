"""Unit Tests for Acoustic Double-Clap Detection Engine."""
import os
import sys
import pytest
import time
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.voice.clap_detector import ClapDetector


class TestClapDetector:
    """Test clap transient detection and double-clap cadence recognition."""

    def test_single_clap_acoustic_transient_detection(self):
        detector = ClapDetector(energy_threshold=0.14)

        # 1. Impulsive clap signal (Sharp peak with high crest factor)
        clap_signal = np.zeros(1024, dtype="float32")
        clap_signal[100] = 0.85 # Sharp high impulse
        clap_signal[101] = 0.40
        clap_signal[102] = 0.15

        assert detector.is_clap(clap_signal) is True

        # 2. Continuous steady background noise / speech (Low crest factor)
        noise_signal = np.random.uniform(-0.05, 0.05, 1024).astype("float32")
        assert detector.is_clap(noise_signal) is False

    def test_double_clap_timing_window(self):
        detected_events = []
        detector = ClapDetector(
            on_double_clap=lambda: detected_events.append(True),
            energy_threshold=0.14,
            min_clap_interval=0.10,
            max_clap_interval=0.85,
        )

        clap_frame = np.zeros(1024, dtype="float32")
        clap_frame[50] = 0.80

        # Clap 1
        res1 = detector.process_audio_frame(clap_frame)
        assert res1 is False
        assert len(detected_events) == 0

        # Echo / Reverberation too fast (< 0.10s) -> Must be ignored
        time.sleep(0.02)
        res_echo = detector.process_audio_frame(clap_frame)
        assert res_echo is False
        assert len(detected_events) == 0

        # Clap 2 within valid window (0.15s later) -> Must trigger double-clap!
        time.sleep(0.15)
        res2 = detector.process_audio_frame(clap_frame)
        assert res2 is True
        assert len(detected_events) == 1

    def test_expired_single_clap_reset(self):
        detected_events = []
        detector = ClapDetector(
            on_double_clap=lambda: detected_events.append(True),
            energy_threshold=0.14,
            min_clap_interval=0.05,
            max_clap_interval=0.20,
        )

        clap_frame = np.zeros(1024, dtype="float32")
        clap_frame[50] = 0.80

        # Clap 1
        detector.process_audio_frame(clap_frame)
        assert len(detected_events) == 0

        # Wait past max_clap_interval (0.25s)
        time.sleep(0.25)

        # Clap 2 arrives too late -> Treated as new Clap 1, does NOT trigger double clap
        detector.process_audio_frame(clap_frame)
        assert len(detected_events) == 0


if __name__ == "__main__":
    t = TestClapDetector()
    t.test_single_clap_acoustic_transient_detection()
    print("✅ test_single_clap_acoustic_transient_detection passed")
    t.test_double_clap_timing_window()
    print("✅ test_double_clap_timing_window passed")
    t.test_expired_single_clap_reset()
    print("✅ test_expired_single_clap_reset passed")
    print("🎉 ALL CLAP DETECTOR TESTS PASSED SUCCESSFULLY!")
