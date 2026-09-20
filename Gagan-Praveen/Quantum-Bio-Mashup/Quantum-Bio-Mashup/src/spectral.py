# src/spectral.py

import numpy as np
import librosa

# ======================================
# CANONICAL STFT GEOMETRY (LOCKED)
# ======================================
N_FFT = 2048
HOP_LENGTH = 512

EXPECTED_FREQ_BINS = N_FFT // 2 + 1  # 1025
MAX_FRAMES = 128                     # HARD LIMIT


# ======================================
# STEP 3 — STFT COMPUTATION
# ======================================
def compute_stft_mag(audio: np.ndarray) -> np.ndarray:
    """
    audio (1D) -> STFT magnitude (2D)
    """
    stft = librosa.stft(
        audio,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        center=True
    )
    mag = np.abs(stft)
    return mag


# ======================================
# STEP 4 — SHAPE NORMALIZATION
# ======================================
def normalize_stft_shape(mag: np.ndarray) -> np.ndarray:
    """
    Enforce shape: (EXPECTED_FREQ_BINS, MAX_FRAMES)
    Trim or zero-pad along TIME axis only.
    """
    freq_bins, time_frames = mag.shape

    if freq_bins != EXPECTED_FREQ_BINS:
        raise ValueError(
            f"Frequency bins mismatch: expected {EXPECTED_FREQ_BINS}, got {freq_bins}"
        )

    # Trim
    if time_frames > MAX_FRAMES:
        return mag[:, :MAX_FRAMES]

    # Pad
    if time_frames < MAX_FRAMES:
        pad = MAX_FRAMES - time_frames
        padding = np.zeros((freq_bins, pad), dtype=mag.dtype)
        return np.concatenate([mag, padding], axis=1)

    return mag


# ======================================
# STEP 2–5 — FULL PIPELINE
# ======================================
def extract_normalized_spectrogram(audio: np.ndarray) -> np.ndarray:
    """
    audio -> STFT -> normalized magnitude
    """
    mag = compute_stft_mag(audio)
    mag_norm = normalize_stft_shape(mag)
    return mag_norm

