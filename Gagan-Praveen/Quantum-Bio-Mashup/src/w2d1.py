"""
Week 2 — Day 1
Feature Definition (Frozen Semantics)

Goal:
Attach a reproducible ℝ^40 feature vector to each segment
to be used for similarity graph construction.
"""

import pickle
import numpy as np
import librosa
from collections import defaultdict

# =========================
# CONFIG (FROZEN)
# =========================
MASTER_DB_PATH = "database/master_db.pkl"
OUT_PATH = "database/master_db_features_raw.pkl"

TARGET_SR = 22050
N_MELS = 40

MAX_SEGMENTS_PER_SONG = 8          # 8 × 8 songs = 64 total
EXPECTED_SEGMENT_RANGE = (60, 90)

# =========================
# LOAD DATABASE
# =========================
with open(MASTER_DB_PATH, "rb") as f:
    segments = pickle.load(f)

print(f"[INFO] Loaded {len(segments)} total segments from Week 1 DB")

# =========================
# GROUP BY SONG
# =========================
segments_by_song = defaultdict(list)
for seg in segments:
    segments_by_song[seg.parent_song].append(seg)

print("[INFO] Segment count per song (before filtering):")
for song, segs in segments_by_song.items():
    print(f"  {song}: {len(segs)}")

# =========================
# FILTER SEGMENTS (CRITICAL)
# Deterministic, reproducible
# =========================
filtered_segments = []

for song, segs in segments_by_song.items():
    segs_sorted = sorted(segs, key=lambda s: s.start)
    filtered_segments.extend(segs_sorted[:MAX_SEGMENTS_PER_SONG])

segments = filtered_segments

print(f"[INFO] Total segments after filtering: {len(segments)}")

# =========================
# HARD ASSERTIONS
# =========================
print(f"[INFO] Total segments: {len(segments)}")
assert len(segments) > 0, "No segments found."

ref_shape = segments[0].spectrogram.shape
for seg in segments:
    assert seg.spectrogram.shape == ref_shape, (
        f"Spectrogram shape mismatch in {seg.id}: "
        f"{seg.spectrogram.shape} vs {ref_shape}"
    )

print(f"[OK] All spectrograms have identical shape {ref_shape}")

# =========================
# FEATURE EXTRACTION
# =========================
for seg in segments:
    S_power = seg.spectrogram ** 2

    mel = librosa.feature.melspectrogram(
        S=S_power,
        sr=TARGET_SR,
        n_mels=N_MELS
    )

    mel_vec = mel.mean(axis=1)
    seg.features = mel_vec

print("[SUCCESS] Feature extraction complete")

# =========================
# FEATURE SANITY CHECK
# =========================
v = segments[0].features
print("[SANITY CHECK]")
print("  Feature shape:", v.shape)
print("  Min / Max:", float(v.min()), float(v.max()))
print("  Any NaN:", np.isnan(v).any())
print("  Any Inf:", np.isinf(v).any())

assert v.shape == (N_MELS,)
assert not np.isnan(v).any()
assert not np.isinf(v).any()

# =========================
# SAVE RAW FEATURE DB
# =========================
with open(OUT_PATH, "wb") as f:
    pickle.dump(segments, f)

print(f"[DONE] Raw feature DB saved → {OUT_PATH}")

