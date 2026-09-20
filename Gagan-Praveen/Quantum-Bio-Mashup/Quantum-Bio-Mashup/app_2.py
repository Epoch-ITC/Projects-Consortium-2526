# ============================================================
# QUANTUM BIO MASHUP - FULL DEPLOYMENT (SINGLE FILE)
# ============================================================

from flask import Flask, request, send_file, render_template_string
import numpy as np
import pickle
import soundfile as sf
import tempfile
import os
import gdown

# ============================================================
# CONFIG
# ============================================================

DRIVE_FOLDER = "https://drive.google.com/drive/folders/1KL9tJkIV01uWLA9rGVknht3CPgfMwBka"
DATA_DIR = "database"

SR = 22050
DT = 0.05
CROSSFADE_MS = 80

app = Flask(__name__)

# ============================================================
# DOWNLOAD DATA (ONCE)
# ============================================================

def download_data():
    if os.path.exists(DATA_DIR):
        print("[INFO] Database already exists.")
        return

    print("[INFO] Downloading dataset from Google Drive...")
    gdown.download_folder(DRIVE_FOLDER, output=DATA_DIR, quiet=False)

download_data()

# ============================================================
# LOAD DATABASE
# ============================================================

print("[INFO] Loading database...")

DB_PATH = os.path.join(DATA_DIR, "master_db_features_norm.pkl")
ADJ_PATH = os.path.join(DATA_DIR, "adjacency_sym.npy")

with open(DB_PATH, "rb") as f:
    db = pickle.load(f)

A = np.load(ADJ_PATH)
N = len(db)

print(f"[INFO] Loaded {N} segments")

# ============================================================
# QUANTUM BIO FUNCTIONS
# ============================================================

def build_bio_operator(N):
    rng = np.random.default_rng(42)
    v = rng.normal(0, 1, N)
    v /= np.linalg.norm(v) + 1e-12
    return np.diag(v)

def enaqt_dephasing_step(psi, gamma, dt):
    phase_noise = np.exp(
        1j * np.random.normal(0, np.sqrt(gamma * dt), size=len(psi))
    )
    return psi * phase_noise

def ou_noise(prev, theta=0.15, sigma=0.3, dt=0.05):
    return (
        prev
        + theta * (-prev) * dt
        + sigma * np.sqrt(dt) * np.random.normal(size=len(prev))
    )

def run_quantum_walk(H, start_idx, T, dt, lambda_noise):
    psi = np.zeros(N, dtype=complex)
    psi[start_idx] = 1.0

    probs = np.zeros((T, N))
    ou_state = np.zeros(N)

    for t in range(T):
        probs[t] = np.abs(psi)**2
        psi = psi - 1j * (H @ psi) * dt

        if lambda_noise > 0:
            psi = enaqt_dephasing_step(psi, lambda_noise, dt)
            ou_state[:] = ou_noise(ou_state, dt=dt)
            psi *= np.exp(1j * ou_state * dt)

        psi /= np.linalg.norm(psi)

    return probs

def extract_path(prob, A, L, stochastic, lambda_noise):
    path, recent = [], []

    for t in range(prob.shape[0]):
        p = prob[t].copy()

        for r in recent:
            p[r] = 0.0

        if stochastic:
            p = p / (p.sum() + 1e-12)
            idx = int(np.random.choice(N, p=p))
        else:
            temperature = 0.2 + 0.8 * lambda_noise
            logits = np.log(p + 1e-12) / temperature
            w = np.exp(logits)
            w /= w.sum()
            idx = int(np.random.choice(N, p=w))

        path.append(idx)
        recent.append(idx)

        if len(recent) > 3:
            recent.pop(0)
        if len(path) >= L:
            break

    return path

def crossfade(a, b, cf):
    fade_out = np.linspace(1, 0, cf)
    fade_in  = np.linspace(0, 1, cf)

    a[-cf:] *= fade_out
    b[:cf]  *= fade_in

    return np.concatenate([a[:-cf], a[-cf:] + b[:cf], b[cf:]])

def build_audio(path):
    audio = None
    cf = int(CROSSFADE_MS * SR / 1000)

    for idx in path:
        y, _ = sf.read(db[idx].wav_path)
        audio = y if audio is None else crossfade(audio, y, cf)

    return audio / (np.max(np.abs(audio)) + 1e-9)

# ============================================================
# FRONTEND (MINIMAL)
# ============================================================

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Quantum Bio Mashup</title>
</head>
<body style="font-family: Arial; text-align:center;">

<h1>Quantum–Biological Mashup Generator</h1>

<label>Start Index:</label>
<input id="start" type="number" value="0"><br><br>

<label>Decoherence λ:</label>
<input id="noise" type="number" step="0.05" value="0.2"><br><br>

<label>Bio λ:</label>
<input id="bio" type="number" step="0.05" value="0.3"><br><br>

<label>Steps:</label>
<input id="steps" type="number" value="150"><br><br>

<label>Path Length:</label>
<input id="length" type="number" value="20"><br><br>

<button onclick="generate()">Generate</button>

<br><br>

<audio id="player" controls></audio>

<script>
function generate() {

    fetch("/generate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            start_idx: parseInt(start.value),
            lambda_noise: parseFloat(noise.value),
            lambda_bio: parseFloat(bio.value),
            T_steps: parseInt(steps.value),
            PATH_LEN: parseInt(length.value),
            stochastic: true
        })
    })
    .then(res => res.blob())
    .then(blob => {
        const url = URL.createObjectURL(blob);
        player.src = url;
        player.play();
    });
}
</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

# ============================================================
# API
# ============================================================

@app.route("/generate", methods=["POST"])
def generate():

    data = request.json

    start_idx = data["start_idx"]
    lambda_noise = data["lambda_noise"]
    lambda_bio = data["lambda_bio"]
    T_steps = data["T_steps"]
    PATH_LEN = data["PATH_LEN"]
    stochastic = data["stochastic"]

    D = np.diag(A.sum(axis=1))
    H_base = D - A
    H_bio  = H_base + lambda_bio * build_bio_operator(N)

    prob = run_quantum_walk(H_bio, start_idx, T_steps, DT, lambda_noise)

    path = extract_path(prob, A, PATH_LEN, stochastic, lambda_noise)

    audio = build_audio(path)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, audio, SR)

    return send_file(tmp.name, mimetype="audio/wav")

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)