import numpy as np
import pickle
import json
import os
from collections import deque

PROB_PATH = "outputs/prob_evolution.npy"
DB_PATH   = "database/master_db_features_norm.pkl"
OUT_PATH  = "outputs/quantum_path.json"

os.makedirs("outputs", exist_ok=True)

# Load probability evolution
prob = np.load(PROB_PATH)   # shape: (T, N)
T, N = prob.shape
print(f"[LOAD] Probability evolution loaded: T={T}, N={N}")

# Load DB
with open(DB_PATH, "rb") as f:
    db = pickle.load(f)

assert len(db) == N, "DB size mismatch with probability matrix!"
# -------------------------
# Constraints
# -------------------------
EXCLUSION_WINDOW = 3      # no repeats within last K steps
KEY_CONTINUITY   = False  # optional, keep False for v0
def key_compatible(seg_a, seg_b):
    if seg_a.key is None or seg_b.key is None:
        return True
    return seg_a.key == seg_b.key
def extract_path_argmax(prob, db):
    path = []
    recent = deque(maxlen=EXCLUSION_WINDOW)

    for t in range(T):
        ranked = np.argsort(prob[t])[::-1]

        chosen = None
        for idx in ranked:
            if idx in recent:
                continue
            if KEY_CONTINUITY and path:
                if not key_compatible(db[path[-1]], db[idx]):
                    continue
            chosen = idx
            break

        if chosen is None:
            chosen = ranked[0]  # fallback

        path.append(chosen)
        recent.append(chosen)

    return path
def extract_path_sampling(prob, db):
    path = []
    recent = deque(maxlen=EXCLUSION_WINDOW)

    for t in range(T):
        p = prob[t].copy()

        # Exclude recent states
        for r in recent:
            p[r] = 0.0

        if p.sum() < 1e-12:
            p = prob[t].copy()  # fallback

        p /= p.sum()

        chosen = np.random.choice(N, p=p)

        if KEY_CONTINUITY and path:
            if not key_compatible(db[path[-1]], db[chosen]):
                chosen = np.argmax(p)

        path.append(chosen)
        recent.append(chosen)

    return path
FINAL_MODE = "argmax"   # or "sampling"
if FINAL_MODE == "argmax":
    path_idx = extract_path_argmax(prob, db)
else:
    path_idx = extract_path_sampling(prob, db)

print(f"[DONE] Path extracted using mode = {FINAL_MODE}")
quantum_path = []

for step, idx in enumerate(path_idx):
    seg = db[idx]
    quantum_path.append({
        "step": step,
        "segment_id": seg.id,
        "parent_song": seg.parent_song,
        "start_time": float(seg.start),
        "end_time": float(seg.end),
        "key": seg.key
    })
with open(OUT_PATH, "w") as f:
    json.dump({
        "selection_mode": FINAL_MODE,
        "exclusion_window": EXCLUSION_WINDOW,
        "key_continuity": KEY_CONTINUITY,
        "path": quantum_path
    }, f, indent=2)

print(f"[SAVE] Quantum music path → {OUT_PATH}")
