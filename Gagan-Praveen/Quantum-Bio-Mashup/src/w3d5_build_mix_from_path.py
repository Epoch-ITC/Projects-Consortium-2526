import json
import pickle
import soundfile as sf
import numpy as np
import os

SR = 22050
CROSSFADE_MS = 120

DB_PATH = "database/master_db_features_norm.pkl"
PATH_NO_BIO  = "outputs/path_no_bio.json"
PATH_BIO     = "outputs/path_with_bio.json"

def load_db():
    with open(DB_PATH, "rb") as f:
        db = pickle.load(f)
    return {seg.id: seg for seg in db}

def load_path(path_json):
    with open(path_json) as f:
        return json.load(f)

def stitch(path, seg_db, out_wav):
    audio = np.array([], dtype=np.float32)
    cf = int(SR * CROSSFADE_MS / 1000)

    for step in path:
        seg_id = step["segment"]
        seg = seg_db[seg_id]

        wav_path = seg.wav_path   # 🔑 SINGLE SOURCE OF TRUTH

        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"Missing WAV: {wav_path}")

        y, sr = sf.read(wav_path)
        if y.ndim > 1:
            y = y.mean(axis=1)

        assert sr == SR, f"Sample rate mismatch in {wav_path}"

        if len(audio) == 0:
            audio = y
        else:
            fade_out = np.linspace(1, 0, cf)
            fade_in  = np.linspace(0, 1, cf)
            audio[-cf:] = audio[-cf:] * fade_out + y[:cf] * fade_in
            audio = np.concatenate([audio, y[cf:]])

    sf.write(out_wav, audio, SR)
    print("[SAVE]", out_wav)

if __name__ == "__main__":
    os.makedirs("outputs", exist_ok=True)

    seg_db = load_db()

    path_no  = load_path(PATH_NO_BIO)
    path_bio = load_path(PATH_BIO)

    stitch(path_no,  seg_db, "outputs/mix_no_bio.wav")
    stitch(path_bio, seg_db, "outputs/mix_with_bio.wav")
