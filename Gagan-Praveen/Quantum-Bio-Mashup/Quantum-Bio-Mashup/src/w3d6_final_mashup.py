import os, json, pickle
import numpy as np
import librosa
import soundfile as sf

DB_FILE = "database/master_db.pkl"
PATH_FILE = "outputs/path_with_bio.json"     # modify if needed
OUT_FILE = "outputs/mashup_quantum.wav"

SR = 22050
CROSSFADE_MS = 80
CROSS = int(SR * CROSSFADE_MS / 1000)


def crossfade(base, new):
    """Smooth join with crossfade"""
    if base is None:
        return new.copy()

    if len(base) < CROSS or len(new) < CROSS:
        return np.concatenate([base, new])

    fade_out = np.linspace(1,0,CROSS)
    fade_in  = np.linspace(0,1,CROSS)

    base[-CROSS:] *= fade_out
    new[:CROSS]   *= fade_in

    return np.concatenate([base, new])


def build_final():
    print("\n🔍 Loading DB + Path ...")

    # load segment objects
    with open(DB_FILE,"rb") as f:
        db = pickle.load(f)

    print(f"📁 Segments loaded: {len(db)}")

    # Build ID → WAV lookup
    id_to_wav = {seg.id: seg.wav_path for seg in db}

    # load quantum path
    with open(PATH_FILE) as f:
        data = json.load(f)

    segment_ids = [x["segment"] for x in data]   # JSON format confirmed
    print(f"🎶 Track length: {len(segment_ids)} segments\n")

    track = None

    for i, seg_id in enumerate(segment_ids,1):
        if seg_id not in id_to_wav:
            print(f"⚠ {seg_id} missing — skipped")
            continue

        wav = id_to_wav[seg_id]
        audio,_ = librosa.load(wav, sr=SR)

        track = crossfade(track, audio)

        print(f" [{i}/{len(segment_ids)}] Mixed {seg_id}")

    # normalize audio
    track /= np.max(np.abs(track)) + 1e-9

    sf.write(OUT_FILE, track, SR)
    print(f"\n🎉 FINAL MASHUP CREATED → {OUT_FILE}")
    print("▶ Play with: ffplay outputs/mashup_quantum.wav\n")


if __name__ == "__main__":
    build_final()
