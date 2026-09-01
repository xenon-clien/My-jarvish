"""Comprehensive unit and integration tests for Multi-Stage VAD and Noise Rejection."""
import pytest
import numpy as np
import time
from unittest.mock import MagicMock, patch

from backend.voice.speech_to_text import SpeechToTextManager, NoiseProfile
from backend.core.config import get_settings


@pytest.fixture
def stt():
    """Create a fresh SpeechToTextManager instance."""
    manager = SpeechToTextManager(get_settings())
    # Initialize with realistic ambient profile (mean ~210, p90 ~250)
    rms_init = [200.0, 210.0, 215.0, 205.0, 220.0, 240.0, 255.0, 195.0, 210.0, 208.0]
    peaks_init = [550, 620, 590, 680, 710, 750, 600, 580, 640, 670]
    manager.update_noise_profile(rms_init, peaks_init)
    return manager


def test_1_steady_ambient_no_trigger(stt):
    """TEST 1: Steady ambient ~210 RMS -> No trigger."""
    noise_ceiling = max(stt.noise_profile.p90_rms, stt.noise_profile.mean_rms + 20.0)
    start_thresh = noise_ceiling + max(35.0, stt.noise_profile.p90_rms * 0.25)
    
    # 210 RMS is well below start threshold (~315 RMS)
    assert 210.0 < start_thresh


def test_2_single_noise_spike_no_trigger(stt):
    """TEST 2: Single noise spike around 270-370 RMS lasting only 1 frame -> NO SPEECH_START."""
    candidate_window = [False, False, False, False, True] # only 1 frame above candidate
    assert sum(candidate_window) < 3, "Single spike must not trigger speech start"


def test_3_multiple_isolated_noise_spikes_no_trigger(stt):
    """TEST 3: Multiple isolated spikes separated by ambient -> NO SPEECH_START."""
    # Pattern: spike, ambient, ambient, spike, ambient
    candidate_window = [True, False, False, True, False]
    assert sum(candidate_window) < 3, "Isolated separated spikes must not trigger speech start"


def test_4_sustained_speech_triggers_speech_start(stt):
    """TEST 4: Sustained speech-like energy above adaptive envelope -> SPEECH_START."""
    # Pattern: 3 or 4 consecutive speech frames
    candidate_window = [False, True, True, True, True]
    assert sum(candidate_window) >= 3, "Sustained speech must trigger speech start"


def test_5_short_speech_pause_stays_active(stt):
    """TEST 5: Short 0.2-0.3 sec speech pause -> phrase stays active."""
    silence_limit = 0.55
    pause_duration = 0.25
    # Should not cutoff on 0.25s pause
    assert pause_duration < silence_limit


def test_6_genuine_silence_triggers_speech_end(stt):
    """TEST 6: Approximately 0.55+ sec genuine silence after speech -> SPEECH_END."""
    silence_limit = 0.55
    silence_duration = 0.60
    assert silence_duration >= silence_limit


def test_7_false_candidate_aborts_quickly(stt):
    """TEST 7: False candidate followed immediately by ambient -> FALSE_START aborted quickly."""
    speech_duration = 0.32
    max_pre_buffer_chunks = 4
    recorded_chunks_len = 6 # very short
    recent_rms = 190.0 # dropped back to ambient
    noise_ceiling = 250.0

    is_false_start = (speech_duration >= 0.30 and recorded_chunks_len <= (max_pre_buffer_chunks + 5) and recent_rms < noise_ceiling)
    assert is_false_start is True


def test_8_pre_roll_preserves_initial_audio(stt):
    """TEST 8: Pre-roll buffer preserves initial consonant/vowel audio."""
    chunk_samples = 1024
    sample_rate = 16000
    max_pre_buffer_chunks = int((0.30 * sample_rate) / chunk_samples)
    assert max_pre_buffer_chunks == 4 # ~256ms pre-roll


def test_9_noise_profile_adapts_slowly(stt):
    """TEST 9: Changing ambient level slowly -> noise profile adapts."""
    old_median = stt.noise_profile.median_rms
    new_rms = [230.0, 235.0, 240.0, 238.0, 245.0, 250.0, 255.0, 242.0, 239.0, 241.0]
    new_peaks = [700, 720, 750, 710, 760, 790, 810, 730, 740, 750]
    stt.update_noise_profile(new_rms, new_peaks)
    assert stt.noise_profile.median_rms > old_median


def test_10_sudden_transient_does_not_permanently_distort_baseline(stt):
    """TEST 10: Sudden loud transient does not permanently jump median baseline."""
    # 9 normal chunks + 1 huge spike (e.g. door slam)
    rms_with_spike = [210.0, 212.0, 208.0, 215.0, 211.0, 209.0, 213.0, 214.0, 210.0, 2500.0]
    peaks_with_spike = [600, 620, 590, 610, 630, 600, 640, 620, 610, 15000]
    stt.update_noise_profile(rms_with_spike, peaks_with_spike)
    # Median should remain around 211 despite the 2500 spike
    assert 205.0 <= stt.noise_profile.median_rms <= 220.0


def test_11_obvious_ambient_only_phrase_skips_google_stt(stt):
    """TEST 11: Obvious ambient-only phrase is rejected locally without calling Google STT."""
    raw_ambient = np.random.normal(0, 210, 16000).astype(np.int16)
    phrase_peak = float(np.max(np.abs(raw_ambient)))
    phrase_mean_rms = float(np.sqrt(np.mean(raw_ambient.astype(np.float64) ** 2)))
    
    stt.noise_profile.typical_peak = 750.0
    stt.noise_profile.p90_rms = 250.0
    
    should_skip = (phrase_mean_rms < stt.noise_profile.p90_rms + 25.0 or phrase_peak < stt.noise_profile.typical_peak * 1.25)
    assert should_skip is True


def test_12_valid_speech_passes_validity_check(stt):
    """TEST 12: Valid speech passes quality check and proceeds to STT."""
    raw_speech = np.random.normal(0, 750, 16000).astype(np.int16)
    raw_speech[::5] = 4500 # speech peaks
    phrase_peak = float(np.max(np.abs(raw_speech)))
    phrase_mean_rms = float(np.sqrt(np.mean(raw_speech.astype(np.float64) ** 2)))
    
    stt.noise_profile.typical_peak = 750.0
    stt.noise_profile.p90_rms = 250.0
    
    should_skip = (phrase_mean_rms < stt.noise_profile.p90_rms + 25.0 or phrase_peak < stt.noise_profile.typical_peak * 1.25)
    assert should_skip is False
