import numpy as np

H_PATH     = "database/H.npy"
V_BIO_PATH = "database/V_bio.npy"
OUT_PATH   = "database/H_bio.npy"

LAMBDA_BIO = 0.3   # strength of bio influence

H     = np.load(H_PATH)
V_bio = np.load(V_BIO_PATH)

assert H.shape == V_bio.shape

H_bio = H + LAMBDA_BIO * V_bio

np.save(OUT_PATH, H_bio)
print(f"[DONE] Bio-modulated Hamiltonian saved → {OUT_PATH}")
