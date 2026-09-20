import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

PROB_PATH = "outputs/prob_evolution.npy"   # or prob_with_bio.npy
OUT_PATH  = "outputs/probability_flow.png"

os.makedirs("outputs", exist_ok=True)

prob = np.load(PROB_PATH)   # shape (T, N)
T, N = prob.shape

plt.figure(figsize=(14,6))
sns.heatmap(
    prob.T,
    cmap="viridis",
    cbar_kws={"label": "Probability"},
    xticklabels=20,
    yticklabels=10
)

plt.xlabel("Time step")
plt.ylabel("Segment index")
plt.title("Quantum Probability Flow Across Music Segments")
plt.tight_layout()
plt.savefig(OUT_PATH, dpi=300)
plt.close()

print(f"[SAVE] {OUT_PATH}")
