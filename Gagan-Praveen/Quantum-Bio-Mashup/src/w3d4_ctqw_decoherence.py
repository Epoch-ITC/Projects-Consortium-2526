import numpy as np
import pickle

ADJ = "database/adjacency_sym.npy"
DB  = "database/master_db_features_norm.pkl"
OUT_PREFIX = "outputs/prob_evolution_"

T = 200           # time steps
dt = 0.05         # step size
LAMBDA_VALUES = [0.0, 0.15, 0.80]   # coherent / ENAQT / noisy

print("[LOAD] adjacency -> Hamiltonian")
A = np.load(ADJ)
H = -A  # adjacency Hamiltonian (simple choice)

# load DB to enforce consistent ordering
with open(DB,"rb") as f:
    segs = sorted(pickle.load(f), key=lambda s: s.global_index)

N = len(segs)

# classical noise vector
deg = A.sum(axis=1)
eta_deg = deg / deg.sum()          # prefer high-degree nodes
eta_uniform = np.ones(N)/N         # full random reference

# ==== EVOLUTION FUNCTION ====

def evolve(lambda_noise):

    psi = np.zeros(N, dtype=complex)
    psi[0] = 1.0                    # start at segment 0 (change if needed)

    prob = np.zeros((T,N))

    for t in range(T):
        # record probability distribution
        prob[t] = np.abs(psi)**2

        # quantum evolution step
        psi = psi - 1j * (H @ psi) * dt

        # decoherence mix
        if lambda_noise > 0:
            noise = eta_deg if lambda_noise<0.5 else eta_uniform
            psi = (1-lambda_noise)*psi + lambda_noise*noise

        # re-normalize
        psi = psi / np.linalg.norm(psi)

    return prob


# ==== RUN ALL 3 REGIMES ====

for lam in LAMBDA_VALUES:
    print(f"[RUN] lambda={lam} ...")
    prob_matrix = evolve(lam)
    np.save(f"{OUT_PREFIX}{lam}.npy", prob_matrix)

print("\n[DONE] Generated probability matrices:")
print(" - coherent:", OUT_PREFIX+"0.0.npy")
print(" - enaqt   :", OUT_PREFIX+"0.15.npy")
print(" - noisy   :", OUT_PREFIX+"0.80.npy")
