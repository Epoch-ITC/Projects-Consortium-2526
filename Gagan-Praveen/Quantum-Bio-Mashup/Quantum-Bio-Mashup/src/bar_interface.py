# src/bar_interface.py

from src.slicing import compute_bar_grid_for_song

def get_bar_segments(song_name: str):
    """
    Wrapper around slicing.py to convert bars into
    a clean list of dicts ready for Segment construction.

    Returns list like:
    [
        {"id": 0, "start": t0, "end": t1},
        {"id": 1, "start": t1, "end": t2},
        ...
    ]
    """

    tempo, bars = compute_bar_grid_for_song(song_name)

    segments = []
    for idx, (ts, te) in enumerate(bars):
        segments.append({
            "id": idx,
            "start": float(ts),
            "end": float(te)
        })
    assert segments, f"No bars detected for {song_name}. Beat tracking failed?"


    return segments

if __name__ == "__main__":
    print("Running bar interface test...")
    out = get_bar_segments("gorila-315977") 
    for seg in out[:5]:
        print(seg)
