"""
Week 2 — Day 6
Classical Greedy Baseline Path
"""

import numpy as np
import pickle

# =========================
# CONFIG
# =========================
ADJ_PATH = "database/adjacency_sym.npy"
DB_PATH = "database/master_db_features_norm.pkl"

MAX_PATH_LEN = 20
START_NODE = 0          # deterministic
KEY_PENALTY = 0.85      # optional, mild

# =========================
# LOAD DATA
# =========================
A = np.load(ADJ_PATH)

with open(DB_PATH, "rb") as f:
    segments = pickle.load(f)

N = len(segments)
print(f"[INFO] Loaded graph with {N} segments")

# =========================
# GREEDY WALK
# =========================
path = [START_NODE]
visited = set(path)

while len(path) < MAX_PATH_LEN:
    current = path[-1]
    weights = A[current].copy()

    # Mask visited nodes
    for v in visited:
        weights[v] = 0.0

    # Optional key continuity penalty
    curr_key = segments[current].key
    for j in range(N):
        if segments[j].key != curr_key:
            weights[j] *= KEY_PENALTY

    next_node = int(np.argmax(weights))

    if weights[next_node] == 0:
        print("[STOP] No valid neighbors left")
        break

    path.append(next_node)
    visited.add(next_node)

# =========================
# REPORT
# =========================
print("\n[RESULT] Classical Greedy Path:")
for idx in path:
    seg = segments[idx]
    print(f"{idx:02d} | {seg.id} | song={seg.parent_song} | key={seg.key}")

print(f"\nPath length: {len(path)}")
