"""
CTQW v0 — Continuous-Time Quantum Walk on Segment Graph
Date: Dec 26
Scope: Exact unitary evolution using Laplacian Hamiltonian
Note: Baseline implementation (no decoherence, no measurements)
"""


import numpy as np
import matplotlib.pyplot as plt
from scipy.linalg import expm
import os

# -----------------------
# Paths
# -----------------------
H_PATH = "database/H_laplacian.npy"
OUT_DIR = "outputs"
os.makedirs(OUT_DIR, exist_ok=True)

# -----------------------
# Load Hamiltonian
# -----------------------
H = np.load(H_PATH)

assert H.ndim == 2
assert H.shape[0] == H.shape[1]
assert np.allclose(H, H.T, atol=1e-8), "H must be Hermitian"

N = H.shape[0]
print(f"[LOAD] Hamiltonian loaded: {N} x {N}")
# -----------------------
# Initial state
# -----------------------
i0 = 0  # starting node index
psi0 = np.zeros(N, dtype=complex)
psi0[i0] = 1.0

# Sanity
assert np.isclose(np.linalg.norm(psi0), 1.0)
print(f"[INIT] Initial state localized at node {i0}")
# -----------------------
# Time grid
# -----------------------
t_max = 10.0
num_steps = 200
times = np.linspace(0, t_max, num_steps)
# -----------------------
# Evolution
# -----------------------
prob_evolution = np.zeros((num_steps, N))

print("[RUN] Starting CTQW evolution...")

for idx, t in enumerate(times):
    U = expm(-1j * H * t)
    psi_t = U @ psi0

    # Probability distribution
    probs = np.abs(psi_t) ** 2
    prob_evolution[idx] = probs

    # Probability conservation check
    if not np.isclose(probs.sum(), 1.0, atol=1e-6):
        raise RuntimeError("Probability not conserved!")

print("[DONE] Evolution complete")
# -----------------------
# Save probability evolution
# -----------------------
np.save(f"{OUT_DIR}/prob_evolution.npy", prob_evolution)
print(f"[SAVE] {OUT_DIR}/prob_evolution.npy")
# -----------------------
# Plot probabilities
# -----------------------
plt.figure(figsize=(10, 6))

nodes_to_plot = [i0, 5, 10, 20]  # arbitrary for v0

for node in nodes_to_plot:
    plt.plot(times, prob_evolution[:, node], label=f"Node {node}")

plt.xlabel("Time")
plt.ylabel("Probability")
plt.title("CTQW Probability Evolution (Laplacian Hamiltonian)")
plt.legend()
plt.grid(True)

plt.savefig(f"{OUT_DIR}/ctqw_prob_vs_time.png")
plt.show()

print(f"[SAVE] {OUT_DIR}/ctqw_prob_vs_time.png")
