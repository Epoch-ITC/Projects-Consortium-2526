import numpy as np

NODES = 64
OUT_PATH = "database/V_bio.npy"

# Toy bio spectrum: slow + fast vibrational modes
np.random.seed(42)

low_freq  = np.linspace(0.1, 0.5, NODES//2)
high_freq = np.linspace(1.0, 2.0, NODES//2)

bio_spectrum = np.concatenate([low_freq, high_freq])
np.random.shuffle(bio_spectrum)

# Diagonal operator
V_bio = np.diag(bio_spectrum)

np.save(OUT_PATH, V_bio)
print(f"[DONE] Bio operator saved → {OUT_PATH}")
