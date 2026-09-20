# src/stft_normalize_check.py

import os
import numpy as np
import librosa
import soundfile as sf
from dataclasses import dataclass

# =========================
# CONFIG (DO NOT CHANGE)
# =========================
SEGMENT_DIR = "database/audio_segments"
TARGET_SR = 22050

N_FFT = 2048
HOP_LENGTH = 512
EXPECTED_FREQ_BINS = N_FFT // 2 + 1
MAX_FRAMES = 128

# =========================
# SEGMENT CLASS (TEMP TEST)
# =========================
@dataclass
class Segment:
    id: str
    parent_song: str
    start: float
    end: float
    spectrogram: np.ndarray = None
    wavelet_energy: np.ndarray = None
    key: str = None
    features: np.ndarray = None
    global_index: int = None

# =========================
# STFT FUNCTIONS
# =========================
def compute_stft_mag(audio: np.ndarray):
    stft = librosa.stft(
        audio,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        center=True
    )
    mag = np.abs(stft)
    return mag

def normalize_stft_shape(mag: np.ndarray):
    freq_bins, time_frames = mag.shape

    if freq_bins != EXPECTED_FREQ_BINS:
        raise ValueError(
            f"Frequency bin mismatch: expected {EXPECTED_FREQ_BINS}, got {freq_bins}"
        )

    if time_frames > MAX_FRAMES:
        return mag[:, :MAX_FRAMES]

    if time_frames < MAX_FRAMES:
        pad = MAX_FRAMES - time_frames
        padding = np.zeros((freq_bins, pad), dtype=mag.dtype)
        return np.concatenate([mag, padding], axis=1)

    return mag

# =========================
# MAIN CHECK PIPELINE
# =========================
def main():
    files = sorted(
        f for f in os.listdir(SEGMENT_DIR)
        if f.endswith(".wav")
    )

    print(f"[INFO] Found {len(files)} segment WAV files")

    segments = []

    for idx, fname in enumerate(files):
        path = os.path.join(SEGMENT_DIR, fname)

        audio, sr = sf.read(path)
        if sr != TARGET_SR:
            raise ValueError(f"Sample rate mismatch in {fname}")

        mag = compute_stft_mag(audio)
        mag_norm = normalize_stft_shape(mag)

        seg = Segment(
            id=fname.replace(".wav", ""),
            parent_song=fname.split("_")[0],
            start=0.0,
            end=0.0
        )
        seg.spectrogram = mag_norm
        seg.global_index = idx

        segments.append(seg)

        # Shape check
        if mag_norm.shape != (EXPECTED_FREQ_BINS, MAX_FRAMES):
            raise RuntimeError(f"Shape error in {fname}: {mag_norm.shape}")

    print("[SUCCESS] All segments normalized correctly!")
    print(f"Example shape: {segments[0].spectrogram.shape}")
    print(f"Total segments: {len(segments)}")

if __name__ == "__main__":
    main()

