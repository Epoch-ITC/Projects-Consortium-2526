# src/build_segments.py

import os
import pickle
import csv
from src.segment import Segment    # adjust if your Segment class is in src/segment.py
from src.bar_interface import get_bar_segments

AUDIO_SEG_DIR = "database/audio_segments"
MASTER_DB_PKL = "database/master_db.pkl"
MASTER_DB_CSV = "database/master_db.csv"


def build_segments():
    """
    Build Segment objects for ALL songs,
    assuming Gagan already sliced and saved WAV files as:
        database/audio_segments/<song_base>_bar_XX.wav
    """

    # Detect songs by scanning .npy files in raw_songs
    raw_npy = sorted([
        os.path.splitext(f)[0]
        for f in os.listdir("raw_songs")
        if f.endswith(".npy")
    ])

    segment_list = []
    global_idx = 0

    for song_idx, song_base in enumerate(raw_npy, start=1):

        print(f"\n[PROCESS] Building segments for {song_base}")

        # Get bar segments from your Day-3 code
        bars = get_bar_segments(song_base)

        for bar in bars:

            bar_idx = bar["id"]

            # Your segment ID scheme
            seg_id = f"S{song_idx:02d}_{bar_idx:02d}"

            # Gagan's expected filename
            wav_name = f"{song_base}_bar_{bar_idx:02d}.wav"
            wav_path = os.path.join(AUDIO_SEG_DIR, wav_name)

            if not os.path.exists(wav_path):
                print(f"[WARN] Missing WAV file: {wav_path}")
                continue

            # Create Segment object (your responsibility)
            seg = Segment(
                id=seg_id,
                parent_song=song_base,
                start_time=bar["start"],
                end_time=bar["end"]
            )

            # Add convenience attribute
            seg.wav_path = wav_path
            seg.global_index = global_idx

            segment_list.append(seg)
            global_idx += 1

    # Save pickle database
    os.makedirs(os.path.dirname(MASTER_DB_PKL), exist_ok=True)

    with open(MASTER_DB_PKL, "wb") as f:
        pickle.dump(segment_list, f)

    print(f"\nmaster DB written → {MASTER_DB_PKL}")
    print(f"Total segments: {len(segment_list)}")

    # Optional CSV for quick inspection
    with open(MASTER_DB_CSV, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "parent_song", "start", "end", "global_index", "wav_path"])
        for s in segment_list:
            writer.writerow([
                s.id, s.parent_song, s.start, s.end, s.global_index, s.wav_path
            ])

    print(f"CSV summary written → {MASTER_DB_CSV}")

    return segment_list


if __name__ == "__main__":
    build_segments()
