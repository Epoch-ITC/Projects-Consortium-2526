import os
import numpy as np
import librosa

RAW_SONGS_DIR = "raw_songs"
TARGET_SR = 22050

# how many beats per bar (house/techno usually 4/4)
BEATS_PER_BAR = 4

# *** IMPORTANT LIMIT ***
MAX_BARS_PER_SONG = 32    # Option A (recommended)
# If a song has fewer than this, we'll just use whatever we get.
def load_normalized_song(song_name: str) -> tuple[np.ndarray, int]:
    """
    Load the normalized audio (.npy) for a given song base name.
    Example: song_name = 'song1' expects 'raw_songs/song1.npy'.
    """
    npy_path = os.path.join(RAW_SONGS_DIR, song_name + ".npy")
    if not os.path.exists(npy_path):
        raise FileNotFoundError(f"Could not find {npy_path}. Did you run audio_io.py?")

    y = np.load(npy_path)
    sr = TARGET_SR
    return y, sr

def get_beats(y: np.ndarray, sr: int):
    """
    Run beat tracking to get tempo and beat times (in seconds).
    Handles numpy array return issues for tempo.
    """
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

    # Convert tempo to float if numpy array
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo.mean())

    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    print(f"[INFO] Detected tempo: {tempo:.2f} BPM, beats: {len(beat_times)}")
    return tempo, beat_times


def beats_to_bars(beat_times: np.ndarray,
                  beats_per_bar: int = BEATS_PER_BAR,
                  max_bars: int = MAX_BARS_PER_SONG):
    """
    Convert a 1D array of beat_times into a list of bar intervals.
    Each bar = group of `beats_per_bar` beats.
    We then LIMIT the total number of bars per song to `max_bars`.
    """
    num_beats = len(beat_times)
    if num_beats < beats_per_bar:
        print("[WARN] Not enough beats to form even one bar.")
        return []

    # Number of full bars we can form
    full_bars = num_beats // beats_per_bar

    # Apply the LIMIT here
    full_bars = min(full_bars, max_bars)

    bars = []
    for b in range(full_bars):
        start_beat_idx = b * beats_per_bar
        end_beat_idx = start_beat_idx + beats_per_bar

        # bar starts at time of first beat in group
        t_start = beat_times[start_beat_idx]
        # bar ends at time of *next* beat after the group, if it exists
        if end_beat_idx < len(beat_times):
            t_end = beat_times[end_beat_idx]
        else:
            # if we don't have the next beat, just end at last beat + small epsilon
            t_end = beat_times[-1] + 60.0 / 120.0  # assume ~120 BPM as fallback

        bars.append((t_start, t_end))

    print(f"[INFO] Created {len(bars)} bars (limited to max {max_bars}).")
    return bars
def compute_bar_grid_for_song(song_name: str):
    """
    For a given song base name ('song1'), this:
        - loads normalized audio (.npy)
        - runs beat tracking
        - computes bar intervals with a max limit
    Returns:
        tempo, bars  where bars is a list of (start_time, end_time).
    """
    print(f"\n[PROCESS] Building bar grid for {song_name}")
    y, sr = load_normalized_song(song_name)
    tempo, beat_times = get_beats(y, sr)
    bars = beats_to_bars(beat_times)

    # Debug print first few bars
    for i, (ts, te) in enumerate(bars[:5]):
        print(f"  Bar {i}: {ts:.3f}s -> {te:.3f}s")

    return tempo, bars
def list_song_basenames():
    """
    Find all .npy songs in RAW_SONGS_DIR and return their base names.
    """
    basenames = []
    for fname in os.listdir(RAW_SONGS_DIR):
        if fname.lower().endswith(".npy"):
            basenames.append(os.path.splitext(fname)[0])
    return sorted(basenames)
## newly added fxns on day 4 - fade and slice_saving
def apply_fade(audio, sr, fade_ms=10):
    """
    Apply fade-in and fade-out of fade_ms milliseconds.
    Prevents popping sounds due to abrupt cuts.
    """
    fade_samples = int(sr * fade_ms / 1000)

    if len(audio) < 2 * fade_samples:
        return audio  # too small to fade

    # Fade-in
    fade_in_curve = np.linspace(0.0, 1.0, fade_samples)
    audio[:fade_samples] *= fade_in_curve

    # Fade-out
    fade_out_curve = np.linspace(1.0, 0.0, fade_samples)
    audio[-fade_samples:] *= fade_out_curve

    return audio

import soundfile as sf

AUDIO_SEG_DIR = "database/audio_segments"

def slice_and_save_segment(y, sr, start_time, end_time, segment_name):
    """
    Slice audio using time boundaries and save as a clean WAV file.
    """
    os.makedirs(AUDIO_SEG_DIR, exist_ok=True)

    start_sample = int(start_time * sr)
    end_sample = int(end_time * sr)

    # Extract raw slice
    segment_audio = y[start_sample:end_sample]

    # Safety check
    if len(segment_audio) == 0:
        print(f"[WARN] Empty segment: {segment_name}")
        return None

    # Apply fade-in/out
    segment_audio = apply_fade(segment_audio, sr, fade_ms=10)

    # Save WAV
    out_path = os.path.join(AUDIO_SEG_DIR, f"{segment_name}.wav")
    sf.write(out_path, segment_audio, sr)

    return out_path

def process_song_segments(song_name, bars):
    """
    For one song:
      - loads normalized .npy
      - slices each bar into audio files
      - returns list of segment file paths
    """
    print(f"[PROCESS] Slicing segments for {song_name}")

    y, sr = load_normalized_song(song_name)

    segment_paths = []
    for idx, (start, end) in enumerate(bars):
        seg_name = f"{song_name}_bar_{idx:02d}"
        out = slice_and_save_segment(y, sr, start, end, seg_name)
        if out:
            segment_paths.append(out)

    print(f"[DONE] {song_name}: Saved {len(segment_paths)} segments.")
    return segment_paths


if __name__ == "__main__":
    song_names = list_song_basenames()
    print("[INFO] Found songs:", song_names)

    for name in song_names:
        tempo, bars = compute_bar_grid_for_song(name)
        #print(f"[SUMMARY] {name}: tempo={tempo:.2f}, bars_kept={len(bars)}")
        process_song_segments(name, bars)

