import numpy as np
import pickle, json
from collections import deque

PROB_NO_BIO   = "outputs/prob_no_bio.npy"
PROB_WITH_BIO = "outputs/prob_with_bio.npy"
DB_PATH       = "database/master_db_features_norm.pkl"

OUT_NO_BIO   = "outputs/path_no_bio.json"
OUT_WITH_BIO = "outputs/path_with_bio.json"

MEMORY = 3
TOP_T  = 60

def extract_path(prob, segments):
    visited = deque(maxlen=MEMORY)
    path = []

    for t in range(min(TOP_T, prob.shape[0])):
        p = prob[t].copy()

        for idx in visited:
            p[idx] = -1

        idx = int(np.argmax(p))
        path.append(idx)
        visited.append(idx)

    return path

# Load DB
with open(DB_PATH, "rb") as f:
    segments = sorted(pickle.load(f), key=lambda s: s.global_index)

# Load probs
prob_no   = np.load(PROB_NO_BIO)
prob_bio  = np.load(PROB_WITH_BIO)

path_no  = extract_path(prob_no, segments)
path_bio = extract_path(prob_bio, segments)

def save(path, fname):
    out = []
    for t, idx in enumerate(path):
        seg = segments[idx]
        out.append({
            "t": t,
            "segment": seg.id,
            "song": seg.parent_song
        })
    with open(fname, "w") as f:
        json.dump(out, f, indent=2)

save(path_no, OUT_NO_BIO)
save(path_bio, OUT_WITH_BIO)

print("[DONE] Saved:")
print(" -", OUT_NO_BIO)
print(" -", OUT_WITH_BIO)


diffs = []
for t, (a, b) in enumerate(zip(path_no, path_bio)):
    if a != b:
        diffs.append(t)

print("\n=== TRANSITION COMPARISON ===")
print("First divergence at t =", diffs[0] if diffs else "NONE")
print(f"Differing steps: {len(diffs)}/{len(path_no)} "
      f"({100*len(diffs)/len(path_no):.2f}%)")

with open("outputs/transition_diff.txt", "w") as f:
    f.write(f"First divergence: {diffs[0] if diffs else 'NONE'}\n")
    f.write(f"Differing steps: {len(diffs)} / {len(path_no)}\n")
    f.write("Diff indices:\n")
    f.write(", ".join(map(str, diffs)))
