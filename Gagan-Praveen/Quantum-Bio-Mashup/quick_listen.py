# quick_listen.py
import json
import sys
import soundfile as sf
import numpy as np
import os

CROSSFADE = 0.05  # seconds overlap for smoother transitions

def load_wav(path):
    y, sr = sf.read(path)
    if y.ndim > 1:  # stereo → mono
        y = np.mean(y, axis=1)
    return y, sr

def crossfade_concat(tracks, sr):
    final = tracks[0]
    fade_samples = int(CROSSFADE * sr)

    for i in range(1, len(tracks)):
        a = final
        b = tracks[i]

        if fade_samples > len(a) or fade_samples > len(b):
            final = np.concatenate([a, b])
            continue

        fade_out = np.linspace(1, 0, fade_samples)
        fade_in  = np.linspace(0, 1, fade_samples)

        mixed = (a[-fade_samples:] * fade_out) + (b[:fade_samples] * fade_in)

        final = np.concatenate([a[:-fade_samples], mixed, b[fade_samples:]])

    return final

def main():
    if len(sys.argv) < 3:
        print("\nUsage:")
        print(" python quick_listen.py <path.json> <output.wav>\n")
        sys.exit(1)

    path_file = sys.argv[1]
    out_file  = sys.argv[2]

    with open(path_file, 'r') as f:
        segments = json.load(f)

    tracks = []
    sr_ref = None

    for seg in segments:
        wav = seg["wav"]
        if not os.path.exists(wav):
            print(f"[SKIP] Missing file: {wav}")
            continue

        y, sr = load_wav(wav)
        if sr_ref is None: sr_ref = sr

        tracks.append(y)
        print(f"[+ Added] {wav}")

    if len(tracks) == 0:
        print("No valid audio segments loaded!")
        return

    print("\n[PROCESS] Concatenating with crossfade...")
    final = crossfade_concat(tracks, sr_ref)

    sf.write(out_file, final, sr_ref)
    print(f"\n[DONE] Saved mashup → {out_file}\n")

if __name__ == "__main__":
    main()
