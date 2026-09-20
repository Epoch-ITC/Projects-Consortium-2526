import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import pickle

PROB_PATH = "outputs/prob_evolution.npy"
PKL_DB     = "database/master_db_features_norm.pkl"
H_PATH     = "database/H.npy"
SAVE_HEAT  = "outputs/probability_heatmap.png"
SAVE_TOP   = "outputs/top_state_trajectories.png"
SAVE_LABEL = "outputs/segment_labels.txt"

os.makedirs("outputs", exist_ok=True)

# Load probability evolution & DB
prob = np.load(PROB_PATH)
H    = np.load(H_PATH)
with open(PKL_DB, "rb") as f:
    db = pickle.load(f)

T, N = prob.shape
print(f"[LOAD] Probabilities shape = {prob.shape}")

# ---------------------------------------------------------
# FIXED SECTION FOR YOUR DB STRUCTURE
# ---------------------------------------------------------
segment_ids = [seg.id for seg in db]    # <--- FIX

assert len(segment_ids) == N, \
    "Segment count mismatch with Hamiltonian / probability matrix!"

# save index mapping
with open(SAVE_LABEL, "w") as f:
    for i, sid in enumerate(segment_ids):
        f.write(f"{i} -> {sid}\n")
print(f"[SAVE] Label index map → {SAVE_LABEL}")

# derive song names for grouping
def parent_from_id(segid):
    return segid.rsplit("_bar_", 1)[0]

song_of = [parent_from_id(s) for s in segment_ids]
unique_songs = sorted(set(song_of))
song_color_map = {s:i for i, s in enumerate(unique_songs)}

# ---------------------------------------------------------
# 1. Probability Heatmap
# ---------------------------------------------------------
plt.figure(figsize=(14,6))
sns.heatmap(prob.T, cmap="viridis")
plt.title("Quantum Walk — Probability Evolution Over Time")
plt.xlabel("Time Step")
plt.ylabel("Segment Index")
plt.tight_layout()
plt.savefig(SAVE_HEAT, dpi=300)
print("[SAVE] Heatmap:", SAVE_HEAT)


# ---------------------------------------------------------
# 2. Top-K state trajectory visualization
# ---------------------------------------------------------
K = 5
top_states = prob.argsort(axis=1)[:, -K:]

plt.figure(figsize=(12,6))
for k in range(K):
    series = top_states[:, K-1-k]
    plt.plot(series, label=f"Rank {k+1}")

plt.title("Top-K Most Probable Segments Over Time")
plt.xlabel("Time Step")
plt.ylabel("Segment Index")
plt.legend()
plt.tight_layout()
plt.savefig(SAVE_TOP, dpi=300)
print("[SAVE] Top-K plot:", SAVE_TOP)

print("\n[DONE] Visualization complete! Check outputs folder 👀🎶")

