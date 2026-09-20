import numpy as np, librosa, soundfile as sf, os, argparse
from w3_segment_index import load_segments
from scipy.signal import resample

PROB_PATH_COH   = "outputs/prob_coherent.npy"
PROB_PATH_ENAQT = "outputs/prob_enaqt.npy"
PROB_PATH_NOISE = "outputs/prob_noisy.npy"
OUT = "outputs/"

def extract_path(prob, mode="coherent", L=20, avoid_recent=3):
    probs = prob[-1]           # final distribution → shape (N,)
    probs = probs / probs.sum()

    path = []
    used = set()

    for _ in range(L):
        if mode == "coherent":
            idx = np.argmax(probs)

        elif mode == "enaqt":   # soft stochastic
            p = probs.copy()
            p[list(used)] = 0.0
            p = p / p.sum()
            idx = np.random.choice(len(p), p=p)

        elif mode == "noisy":
            idx = np.random.choice(len(probs))  # random walk

        if idx in used: break
        used.add(idx)
        path.append(idx)

        # decay probability of chosen one
        probs[idx] *= 0.1
        probs = probs / probs.sum()

        if len(used) > avoid_recent:
            used.remove(list(used)[0])

    return path


def build_mix(indices, sr=22050, crossfade_ms=120):
    segs = load_segments()
    audio = np.array([])

    for ix in indices:
        file = segs[ix]["wav"]
        y,_ = librosa.load(file, sr=sr)

        if len(audio) == 0:
            audio = y
        else:
            cf = int(sr*crossfade_ms/1000)
            fade_in  = np.linspace(0,1,cf)
            fade_out = np.linspace(1,0,cf)
            audio[-cf:] = audio[-cf:]*fade_out + y[:cf]*fade_in
            audio = np.concatenate([audio, y[cf:]])

    return audio


def build(mode):
    print(f"\n=== Building {mode.upper()} Mix ===")

    prob_file = {
        "coherent": PROB_PATH_COH,
        "enaqt"   : PROB_PATH_ENAQT,
        "noisy"   : PROB_PATH_NOISE
    }[mode]

    prob = np.load(prob_file)
    indices = extract_path(prob, mode)
    print("Selected indices:", indices)

    if len(indices)==0:
        print("[ERR] No indices selected! Probabilities likely uniform or all zero.")
        return

    audio = build_mix(indices)
    out = f"{OUT}/mix_{mode}.wav"
    sf.write(out, audio, 22050)
    print("DONE →", out)


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["coherent","enaqt","noisy"], required=True)
    args = parser.parse_args()
    build(args.mode)
