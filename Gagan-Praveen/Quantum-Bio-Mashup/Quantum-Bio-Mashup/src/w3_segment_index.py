# w3_segment_index.py
import pickle

DB_PATH = "database/master_db.pkl"

def load_segments():
    db = pickle.load(open(DB_PATH, "rb"))
    segments = []

    for seg in db:
        segments.append({
            "id": seg.id,
            "song": seg.parent_song,
            "start": seg.start,
            "end": seg.end,
            "wav": seg.wav_path,              # ✔ ACTUALLY STORED INSIDE SEGMENT
            "index": seg.global_index
        })

    print(f"[OK] Loaded {len(segments)} audio segments (using wav_path)")
    return segments
