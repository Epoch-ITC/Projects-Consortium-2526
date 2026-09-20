import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# ===============================
# PATHS
# ===============================
ADJ_PATH = "database/adjacency_sym.npy"
SAVE_H_PATH = "database/H.npy"         # final hamiltonian saved here
NOTES_DIR = "notes"                    # optional folder
os.makedirs(NOTES_DIR, exist_ok=True)

# ===============================
# 1. Load adjacency
# ===============================
A = np.load(ADJ_PATH)   # already symmetrised
N = A.shape[0]

print(f"[LOAD] Adjacency loaded: shape = {A.shape}")
assert A.shape[0] == A.shape[1], "Adjacency must be square!"
assert np.allclose(A, A.T), "[ERROR] A is not symmetric — CTQW invalid!"

print("[OK] Symmetry check passed ✔")


# ===============================
# 2. Degree matrix D
# ===============================
deg = np.sum(A, axis=1)
D = np.diag(deg)

print(f"[INFO] Degree stats → min={deg.min():.4f}, max={deg.max():.4f}, mean={deg.mean():.4f}")


# ===============================
# 3. Generate Hamiltonians
# ===============================
HA = A.copy()
HL = D - A

# sanity checks
assert np.allclose(HA, HA.T), "HA not symmetric!"
assert np.allclose(HL, HL.T), "HL not symmetric!"

print("[OK] Hamiltonian symmetry verified ✔")


# ===============================
# 4. Eigenvalues
# ===============================
print("\n[!] Computing eigenvalues... may take a moment.")
eig_A, _ = np.linalg.eigh(HA)
eig_L, _ = np.linalg.eigh(HL)

print("\n====== EIGEN SUMMARY ======")
print(f"Adjacency H_A spectrum: min={eig_A.min():.4f}, max={eig_A.max():.4f}")
print(f"Laplacian H_L spectrum: min={eig_L.min():.4f}, max={eig_L.max():.4f}")
print("===========================\n")

# ===============================
# 5. Plots
# ===============================
sns.set_theme(style="whitegrid")

plt.figure(figsize=(10,5))
sns.histplot(eig_A, kde=True, color="blue")
plt.title("Spectrum of Adjacency Hamiltonian H_A")
plt.xlabel("Eigenvalue")
plt.ylabel("Density")
plt.savefig("outputs/hist_HA_spectrum.png")
print("[SAVE] outputs/hist_HA_spectrum.png")

plt.figure(figsize=(10,5))
sns.histplot(eig_L, kde=True, color="red")
plt.title("Spectrum of Laplacian Hamiltonian H_L")
plt.xlabel("Eigenvalue")
plt.ylabel("Density")
plt.savefig("outputs/hist_HL_spectrum.png")
print("[SAVE] outputs/hist_HL_spectrum.png")


# ===============================
# 6. Decision Protocol
# ===============================
# You choose based on Praveen's note
# Here we assume you choose HL (common for diffusion/transport)
H_final = HL   # <--- switch to HA if needed

np.save(SAVE_H_PATH, H_final)
print(f"[DONE] Saved chosen Hamiltonian → {SAVE_H_PATH}")
