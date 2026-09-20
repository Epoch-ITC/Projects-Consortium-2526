import os
import librosa
import numpy as np

RAW_SONGS_DIR = "raw_songs"
NPY_SONGS_DIR = "raw_songs"  # saving .npy alongside, or change to a new folder if you like

TARGET_SR = 22050
TARGET_PEAK = 0.99  # max amplitude after normalization


def load_and_normalize_audio(path: str, sr: int = TARGET_SR) -> tuple[np.ndarray, int]:
    """
    Load a song at a fixed sample rate and normalize amplitude.

    Returns:
        y_norm: normalized mono waveform (float32)
        sr:     sample rate (int)
    """
    # 1. Load audio (librosa loads as mono by default)
    y, loaded_sr = librosa.load(path, sr=sr)

    # 2. Normalize amplitude to TARGET_PEAK
    peak = np.max(np.abs(y))
    if peak > 0:
        y = (y / peak) * TARGET_PEAK

    # Ensure float32 to save some memory
    y = y.astype(np.float32)

    return y, sr


def process_all_raw_songs():
    """
    For each .wav file in RAW_SONGS_DIR:
        - load at TARGET_SR
        - normalize amplitude
        - save as .npy in the same folder (or NPY_SONGS_DIR)
    """
    os.makedirs(NPY_SONGS_DIR, exist_ok=True)

    for fname in os.listdir(RAW_SONGS_DIR):
        if not fname.lower().endswith(".wav"):
            continue

        wav_path = os.path.join(RAW_SONGS_DIR, fname)
        base_name = os.path.splitext(fname)[0]
        npy_path = os.path.join(NPY_SONGS_DIR, base_name + ".npy")

        print(f"[INFO] Processing {wav_path} -> {npy_path}")

        y_norm, sr = load_and_normalize_audio(wav_path, sr=TARGET_SR)

        # Save numpy file
        np.save(npy_path, y_norm)

        print(f"[DONE] {fname}: length = {len(y_norm)} samples, sr = {sr}")


if __name__ == "__main__":
    process_all_raw_songs()
