import numpy as np
from scipy.linalg import expm

H_PATH     = "database/H.npy"
H_BIO_PATH = "database/H_bio.npy"

OUT_NO_BIO  = "outputs/prob_no_bio.npy"
OUT_WITH_BIO = "outputs/prob_with_bio.npy"

T  = 200
dt = 0.05

def evolve(H):
    N = H.shape[0]
    psi = np.zeros(N, dtype=complex)
    psi[0] = 1.0

    probs = np.zeros((T, N))

    for t in range(T):
        psi = expm(-1j * H * dt) @ psi
        psi /= np.linalg.norm(psi)
        probs[t] = np.abs(psi)**2

    return probs

H      = np.load(H_PATH)
H_bio  = np.load(H_BIO_PATH)

prob_no_bio   = evolve(H)
prob_with_bio = evolve(H_bio)

np.save(OUT_NO_BIO, prob_no_bio)
np.save(OUT_WITH_BIO, prob_with_bio)

print("[DONE] Saved bio vs no-bio probability evolutions")
