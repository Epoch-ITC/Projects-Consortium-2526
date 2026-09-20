# ==========================================
#   w3_core_quantum_evolution.py
#   Make coherent + enaqt + noisy evolutions
# ==========================================

import numpy as np
from scipy.linalg import expm

H_PATH = "database/H.npy"
P_OUT = "outputs/probabilities_base.npy"

def evolve_ctqw(T=200, dt=0.05):
    H = np.load(H_PATH)
    N = H.shape[0]

    psi = np.zeros(N, dtype=complex)
    psi[0] = 1.0  # start at segment-0, you can change later

    probs = []

    for _ in range(T):
        psi = expm(-1j * H * dt) @ psi
        psi = psi / np.linalg.norm(psi)
        probs.append(np.abs(psi)**2)

    probs = np.array(probs)
    np.save(P_OUT, probs)
    print(f"[DONE] Probabilities saved → {P_OUT}")
    return probs

if __name__ == "__main__":
    evolve_ctqw()
