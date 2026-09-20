"""
Week 2 — Day 3
Feature Normalization (ROBUST VERSION)

Goal:
Convert raw ℝ^40 feature vectors into unit-norm vectors
with explicit degeneracy rejection.

This step is mathematically mandatory for cosine similarity
and quantum Hamiltonian construction.
"""

import pickle
import numpy as np

# =========================
# CONFIG (FROZEN)
# =========================
IN_PATH = "database/master_db_features_raw.pkl"
OUT_PATH = "database/master_db_features_norm.pkl"

NORM_EPS = 1e-8
UNIT_NORM_TOL = 1e-3

# =========================
# LOAD RAW FEATURE DB
# =========================
with open(IN_PATH, "rb") as f:
    segments = pickle.load(f)

print(f"[INFO] Loaded {len(segments)} segments")

# =========================
# NORMALIZATION
# =========================
norms = []

for seg in segments:
    v = seg.features

    if v is None:
        raise ValueError(f"Missing features in segment {seg.id}")

    norm = np.linalg.norm(v)
    norms.append(norm)

    if not np.isfinite(norm):
        raise ValueError(f"Non-finite norm in segment {seg.id}")

    if norm < NORM_EPS:
        raise ValueError(
            f"Degenerate feature vector detected in segment {seg.id} "
            f"(norm={norm:.2e})"
        )

    seg.features = v / norm

# =========================
# VERIFICATION
# =========================
for seg in segments:
    n = np.linalg.norm(seg.features)
    if not np.allclose(n, 1.0, atol=UNIT_NORM_TOL):
        raise RuntimeError(
            f"Normalization failed for segment {seg.id}: norm={n}"
        )

print("[OK] All feature vectors normalized to unit norm")

print(
    f"[STATS] Raw norm range: "
    f"min={min(norms):.3e}, max={max(norms):.3e}, "
    f"ratio={max(norms)/min(norms):.2f}"
)

# =========================
# SAVE NORMALIZED DB
# =========================
with open(OUT_PATH, "wb") as f:
    pickle.dump(segments, f)

print(f"[DONE] Normalized feature DB saved → {OUT_PATH}")
