"""
Week 2 — Day 5 (Gagan)
KNN Graph Construction (RAW)

- Builds a weighted KNN graph from similarity matrix
- Graph may be asymmetric (expected)
"""

import numpy as np
import pickle

# =========================
# CONFIG
# =========================
SIM_PATH = "database/similarity_matrix.npy"
DB_PATH = "database/master_db_features_norm.pkl"
OUT_PATH = "database/adjacency_raw.npy"

K = 7  # allowed: 5 or 7

# =========================
# LOAD DATA
# =========================
S = np.load(SIM_PATH)
with open(DB_PATH, "rb") as f:
    segments = pickle.load(f)

N = S.shape[0]
assert S.shape == (N, N)

print(f"[INFO] Loaded similarity matrix ({N} x {N})")

# =========================
# BUILD KNN GRAPH (RAW)
# =========================
A_raw = np.zeros_like(S)

for i in range(N):
    # Exclude self
    scores = S[i].copy()
    scores[i] = -np.inf

    # Top-K neighbors
    knn_idx = np.argsort(scores)[-K:]

    for j in knn_idx:
        A_raw[i, j] = S[i, j]

print(f"[DONE] KNN graph built (K={K})")

# =========================
# SAVE
# =========================
np.save(OUT_PATH, A_raw)
print(f"[SAVED] Raw adjacency matrix → {OUT_PATH}")
