"""
Week 2 — Day 5 (Praveen)
Graph Symmetrization & Validation

Ensures:
- Symmetric adjacency (Hermitian Hamiltonian)
- No self-loops
- No isolated nodes
- Sparse degree distribution
"""

import numpy as np

# =========================
# CONFIG
# =========================
RAW_PATH = "database/adjacency_raw.npy"
OUT_PATH = "database/adjacency_sym.npy"

# =========================
# LOAD RAW GRAPH
# =========================
A_raw = np.load(RAW_PATH)
N = A_raw.shape[0]

assert A_raw.shape == (N, N)
print(f"[INFO] Loaded raw adjacency matrix ({N} nodes)")

# =========================
# SYMMETRIZATION (CORE STEP)
# =========================
A_sym = np.maximum(A_raw, A_raw.T)

# Remove self-loops explicitly
np.fill_diagonal(A_sym, 0.0)

print("[OK] Graph symmetrized using max(A_ij, A_ji)")

# =========================
# VALIDATION CHECKS
# =========================
# 1. Symmetry
assert np.allclose(A_sym, A_sym.T, atol=1e-10), "Graph is not symmetric!"

# 2. No self-loops
assert np.all(np.diag(A_sym) == 0.0), "Self-loops detected!"

# 3. No isolated nodes
degrees = np.count_nonzero(A_sym, axis=1)
isolated = np.where(degrees == 0)[0]
assert len(isolated) == 0, f"Isolated nodes detected: {isolated}"

# 4. Sparsity check
avg_degree = degrees.mean()
density = np.count_nonzero(A_sym) / (N * N)

print("[GRAPH STATS]")
print(f"  Avg degree: {avg_degree:.2f}")
print(f"  Min degree: {degrees.min()}")
print(f"  Max degree: {degrees.max()}")
print(f"  Density: {density:.4f}")

assert density < 0.2, "Graph too dense — quantum walk will be meaningless!"

print("[SUCCESS] Graph passed all sanity checks")

# =========================
# SAVE SYMMETRIC GRAPH
# =========================
np.save(OUT_PATH, A_sym)
print(f"[SAVED] Symmetric adjacency matrix → {OUT_PATH}")
