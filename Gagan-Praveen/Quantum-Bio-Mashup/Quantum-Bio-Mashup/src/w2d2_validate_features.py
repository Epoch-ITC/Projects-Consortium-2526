"""
Week 2 — Day 2 (Praveen)
Feature Degeneracy Validation

This script validates raw (unnormalized) feature vectors
before normalization and similarity computation.
"""

import pickle
import numpy as np

# =========================
# CONFIG
# =========================
RAW_FEATURE_DB = "database/master_db_features_raw.pkl"

VAR_THRESHOLD = 1e-6
NORM_RATIO_THRESHOLD = 10.0

# =========================
# LOAD RAW FEATURES
# =========================
with open(RAW_FEATURE_DB, "rb") as f:
    segments = pickle.load(f)

print(f"[INFO] Loaded {len(segments)} segments")

# =========================
# COLLECT STATS
# =========================
norms = []
variances = []

for seg in segments:
    v = seg.features

    # --- HARD FAILURES ---
    if not np.isfinite(v).all():
        raise ValueError(f"NaN or Inf detected in features of segment {seg.id}")

    norms.append(np.linalg.norm(v))
    variances.append(np.var(v))

norms = np.array(norms)
variances = np.array(variances)

# =========================
# CHECK 1 — NORM SPREAD
# =========================
norm_ratio = norms.max() / norms.min()

print(f"[CHECK] Norm ratio (max / min): {norm_ratio:.3f}")

if norm_ratio > NORM_RATIO_THRESHOLD:
    raise ValueError(
        f"Norm spread too large ({norm_ratio:.2f} > {NORM_RATIO_THRESHOLD}). "
        "Feature scale inconsistency detected."
    )

# =========================
# CHECK 2 — VARIANCE COLLAPSE
# =========================
low_var_count = np.sum(variances < VAR_THRESHOLD)

print(f"[CHECK] Low-variance vectors (< {VAR_THRESHOLD}): {low_var_count}")

if low_var_count > 0:
    print(
        "[WARNING] Some feature vectors have near-zero variance. "
        "This may reduce cosine similarity discriminability."
    )

# =========================
# SUMMARY
# =========================
print("\n[SUMMARY]")
print(f"  Feature dimension       : {segments[0].features.shape[0]}")
print(f"  Norm min / max          : {norms.min():.4f} / {norms.max():.4f}")
print(f"  Variance min / max      : {variances.min():.6e} / {variances.max():.6e}")

print("\n[SUCCESS] Day 2 feature validation passed.")
