import numpy as np
import pickle, json, os

# ==== CONFIG ====
PKL_DB   = "database/master_db_features_norm.pkl"     # Final 64 clean segments
PROB_NPY = "outputs/prob_evolution.npy"               # From CTQW step
OUT_JSON = "outputs/quantum_path.json"

MEMORY_BLOCK = 3       # no immediate repeats
TOP_T        = 60      # first 60 timesteps enough for 10-20 segments

print("[LOAD] Loading segment DB...")
with open(PKL_DB, "rb") as f:
    segments = pickle.load(f)

# Sort by global_index to match matrix ordering
segments = sorted(segments, key=lambda s: s.global_index)

segment_ids   = [s.id for s in segments]
segment_songs = [s.parent_song for s in segments]

prob = np.load(PROB_NPY)         # shape (T,N)
T, N = prob.shape

assert N == len(segments), "Mismatch between DB and probability matrix!"

print(f"[INFO] Probabilities loaded: T={T}, N={N}")
print("[INFO] Selecting quantum path using argmax-with-memory...")

visited = []
path = []

for t in range(min(TOP_T, T)):
    p = prob[t].copy()

    # Exclude recently used segments
    for idx in visited[-MEMORY_BLOCK:]:
        p[idx] = -1

    next_idx = int(np.argmax(p))
    visited.append(next_idx)
    path.append(next_idx)

print(f"[SUCCESS] Extracted path length = {len(path)} segments")

# ==== Build metadata JSON ====

result = []
for idx in path:
    seg = segments[idx]

    entry = {
        "segment": seg.id,
        "song": seg.parent_song,
        "wav_path": f"database/audio_segments/{seg.id}.wav",
        "index": int(seg.global_index)
    }

    result.append(entry)

# ==== Save ====
os.makedirs("outputs", exist_ok=True)
with open(OUT_JSON, "w") as f:
    json.dump(result, f, indent=4)

print(f"[DONE] Path saved → {OUT_JSON}")

# Display first few to inspect
print("\nFirst 8 sample selections:\n")
for r in result[:8]:
    print(r)
