import numpy as np
import soundfile as sf
import pickle, json, os
import matplotlib.pyplot as plt
from scipy.signal import stft, istft

# =========================
# CONFIG
# =========================
SR = 22050
N_FFT = 2048
HOP = 512
CROSSFADE_FRAMES = 12   # ~140 ms

DB_PATH   = "database/master_db.pkl"
PATH_JSON = "outputs/path_with_bio.json"
OUT_DIR   = "outputs"

os.makedirs(OUT_DIR, exist_ok=True)

# =========================
# LOAD DB + PATH
# =========================
with open(DB_PATH, "rb") as f:
    db = pickle.load(f)

id_to_seg = {seg.id: seg for seg in db}

path = json.load(open(PATH_JSON))

# Pick one transition (first divergence is ideal)
idx = 7
segA_id = path[idx]["segment"]
segB_id = path[idx+1]["segment"]

segA = id_to_seg[segA_id]
segB = id_to_seg[segB_id]

print(f"Transition: {segA_id} → {segB_id}")

# =========================
# LOAD AUDIO (NO LIBROSA)
# =========================
yA, srA = sf.read(segA.wav_path)
yB, srB = sf.read(segB.wav_path)

assert srA == SR and srB == SR, "Sample-rate mismatch!"

if yA.ndim > 1:
    yA = yA.mean(axis=1)
if yB.ndim > 1:
    yB = yB.mean(axis=1)

# =========================
# TIME-DOMAIN CROSSFADE
# =========================
def time_crossfade(a, b, ms=120):
    cf = int(SR * ms / 1000)
    fade_out = np.linspace(1, 0, cf)
    fade_in  = np.linspace(0, 1, cf)

    return np.concatenate([
        a[:-cf],
        a[-cf:] * fade_out + b[:cf] * fade_in,
        b[cf:]
    ])

y_time = time_crossfade(yA, yB)
sf.write(f"{OUT_DIR}/time_crossfade.wav", y_time, SR)
print("[SAVE] time_crossfade.wav")

# =========================
# SPECTRAL CROSSFADE (STFT)
# =========================
_, _, ZA = stft(yA, fs=SR, nperseg=N_FFT, noverlap=N_FFT-HOP)
_, _, ZB = stft(yB, fs=SR, nperseg=N_FFT, noverlap=N_FFT-HOP)

magA, phaseA = np.abs(ZA), np.angle(ZA)
magB = np.abs(ZB)

min_frames = min(magA.shape[1], magB.shape[1])
magA = magA[:, :min_frames]
magB = magB[:, :min_frames]
phaseA = phaseA[:, :min_frames]

mag_mix = magA.copy()

for i in range(CROSSFADE_FRAMES):
    alpha = i / CROSSFADE_FRAMES
    mag_mix[:, -CROSSFADE_FRAMES+i] = (
        (1 - alpha) * magA[:, -CROSSFADE_FRAMES+i] +
        alpha * magB[:, i]
    )

Z_mix = mag_mix * np.exp(1j * phaseA)
_, y_spec = istft(Z_mix, fs=SR, nperseg=N_FFT, noverlap=N_FFT-HOP)

sf.write(f"{OUT_DIR}/spectral_crossfade.wav", y_spec, SR)
print("[SAVE] spectral_crossfade.wav")

# =========================
# VISUAL COMPARISON
# =========================
plt.figure(figsize=(12,4))

plt.subplot(1,2,1)
plt.title("Time-domain Crossfade (STFT mag)")
plt.imshow(20*np.log10(np.abs(ZA)+1e-6), aspect="auto", origin="lower")

plt.subplot(1,2,2)
plt.title("Spectral Crossfade (STFT mag)")
plt.imshow(20*np.log10(np.abs(Z_mix)+1e-6), aspect="auto", origin="lower")

plt.tight_layout()
plt.savefig(f"{OUT_DIR}/crossfade_stft_comparison.png", dpi=300)
print("[SAVE] crossfade_stft_comparison.png")
