"""
Week 2 — Day 4
Compatibility Score Computation (Frozen Definition)

Similarity:
- Cosine similarity on ℓ2-normalized features
- SAME_SONG_PENALTY applied for same parent_song
"""

import pickle
import numpy as np

# =========================
# CONFIG
# =========================
IN_PATH = "database/master_db_features_norm.pkl"
OUT_PATH = "database/similarity_matrix.npy"

SAME_SONG_PENALTY = 0.7

# =========================
# LOAD NORMALIZED FEATURES
# =========================
with open(IN_PATH, "rb") as f:
    segments = pickle.load(f)

N = len(segments)
print(f"[INFO] Loaded {N} segments")

# =========================
# BUILD FEATURE MATRIX
# =========================
X = np.stack([seg.features for seg in segments])  # (N, 40)

# Sanity: unit norm
norms = np.linalg.norm(X, axis=1)
assert np.allclose(norms, 1.0, atol=1e-6), "Features are not unit-normalized"

# =========================
# COSINE SIMILARITY
# =========================
S = X @ X.T  # (N, N)

# =========================
# APPLY SAME-SONG PENALTY
# =========================
for i in range(N):
    for j in range(N):
        if segments[i].parent_song == segments[j].parent_song:
            S[i, j] *= SAME_SONG_PENALTY

print("[OK] Same-song penalty applied")

# =========================
# SANITY CHECKS
# =========================
assert np.allclose(S, S.T, atol=1e-8), "Similarity matrix not symmetric"
assert np.all(np.isfinite(S)), "NaN or Inf in similarity matrix"

print("[SANITY CHECK]")
print("  Min similarity:", float(S.min()))
print("  Max similarity:", float(S.max()))

# =========================
# SAVE
# =========================
np.save(OUT_PATH, S)
print(f"[DONE] Similarity matrix saved → {OUT_PATH}")
