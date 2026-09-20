# ============================================================
# Quantum–Biological Mashup Generator (FINAL RESEARCH MVP)
# ============================================================

import streamlit as st
import numpy as np
import pickle
import soundfile as sf
import tempfile
import matplotlib.pyplot as plt
import networkx as nx
import time

# ============================================================
# CONFIG (HARD LOCKED)
# ============================================================

DB_PATH  = "database/master_db_features_norm.pkl"   # 64 segments ONLY
ADJ_PATH = "database/adjacency_sym.npy"             # 64 x 64 ONLY

SR = 22050
DT = 0.05
CROSSFADE_MS = 80

st.set_page_config(layout="wide")
st.title("Quantum–Biological Mashup Generator")

# ============================================================
# LOAD DATABASE + GRAPH
# ============================================================

@st.cache_resource
def load_db_and_graph():
    with open(DB_PATH, "rb") as f:
        db = pickle.load(f)
    A = np.load(ADJ_PATH)

    if len(db) != A.shape[0]:
        raise ValueError("DB and adjacency size mismatch")

    db = sorted(db, key=lambda s: s.global_index)
    return db, A

db, A = load_db_and_graph()
N = len(db)

@st.cache_resource
def build_graph(A):
    G = nx.from_numpy_array(A)
    pos = nx.spring_layout(G, seed=42)
    return G, pos

G, POS = build_graph(A)

# ============================================================
# SIDEBAR CONTROLS
# ============================================================

st.sidebar.header("Quantum Controls")

start_idx = st.sidebar.selectbox(
    "Initial Segment",
    range(N),
    format_func=lambda i: db[i].id
)

selection_mode = st.sidebar.radio(
    "Selection Strategy",
    ["Argmax (Deterministic)", "Stochastic (Softmax)"]
)

graph_mode = st.sidebar.selectbox(
    "Graph Visualization",
    [
        "Hamiltonian (Laplacian)",
        "Adjacency (Similarity)",
        "Probability-Weighted"
    ]
)

lambda_noise = st.sidebar.slider("Decoherence λ (Environmentally Assisted Quantum Transport - ENAQT)", 0.0, 1.0, 0.15)
lambda_bio   = st.sidebar.slider("Bio Modulation λ", 0.0, 1.0, 0.3)

T_steps  = st.sidebar.slider("Quantum Walk Length", 60, 300, 150)
PATH_LEN = st.sidebar.slider("Mashup Length (segments)", 8, 40, 20)
STEP_DELAY = st.sidebar.slider("Graph Animation Speed", 0.05, 0.6, 0.25)

generate = st.sidebar.button("Generate Mashup")

# ============================================================
# BIO OPERATOR
# ============================================================

def build_bio_operator(N):
    rng = np.random.default_rng(42)
    v = rng.normal(0, 1, N)
    v /= np.linalg.norm(v) + 1e-12
    return np.diag(v)

# ============================================================
# CTQW + ENAQT
# ============================================================

def enaqt_dephasing_step(psi, gamma, dt):
    """
    ENAQT-style pure dephasing.
    - Preserves |psi|^2
    - Randomizes phase
    """
    phase_noise = np.exp(
        1j * np.random.normal(0, np.sqrt(gamma * dt), size=len(psi))
    )
    return psi * phase_noise
def ou_noise(prev, theta=0.15, sigma=0.3, dt=0.05):
    """
    Ornstein–Uhlenbeck noise (colored noise)
    Models structured vibrational environment
    """
    return (
        prev
        + theta * (-prev) * dt
        + sigma * np.sqrt(dt) * np.random.normal(size=len(prev))
    )


def run_quantum_walk(H, start_idx, T, dt, lambda_noise):
    """
    CTQW + ENAQT-style biological dephasing
    """
    N = H.shape[0]

    psi = np.zeros(N, dtype=complex)
    psi[start_idx] = 1.0

    probs = np.zeros((T, N))

    # OU noise state (for correlated environment)
    ou_state = np.zeros(N)

    for t in range(T):
        # Record probabilities
        probs[t] = np.abs(psi)**2

        # ---- Coherent quantum evolution ----
        psi = psi - 1j * (H @ psi) * dt

        # ---- ENAQT dephasing (BIO CORE) ----
        if lambda_noise > 0:
            psi = enaqt_dephasing_step(
                psi,
                gamma=lambda_noise,
                dt=dt
            )

            # OPTIONAL: correlated vibrational noise
            ou_state[:] = ou_noise(ou_state, dt=dt)
            psi *= np.exp(1j * ou_state * dt)

        # ---- Renormalize ----
        psi /= np.linalg.norm(psi)

    return probs


# ============================================================
# PATH EXTRACTION (FULL DIAGNOSTICS)
# ============================================================

def extract_path(prob, A, prob_no_bio, L, stochastic):
    path, recent, rows = [], [], []

    for t in range(prob.shape[0]):
        p = prob[t].copy()
        for r in recent:
            p[r] = 0.0

        if stochastic:
            p = p / (p.sum() + 1e-12)
            idx = int(np.random.choice(N, p=p))
        else:
            temperature = 0.15 + 0.85 * lambda_noise
            logits = np.log(p + 1e-12) / temperature
            weights = np.exp(logits)
            weights /= weights.sum()
            idx = int(np.random.choice(N, p=weights))


        top5 = np.argsort(p)[-5:][::-1]

        rows.append({
            "step": len(path),
            "chosen": db[idx].id,
            "probability": float(p[idx]),
            "similarity_from_prev": None if not path else float(A[path[-1], idx]),
            "bio_influence": float(prob[t, idx] - prob_no_bio[t, idx]),
            "top5_candidates": [db[i].id for i in top5]
        })

        path.append(idx)
        recent.append(idx)
        if len(recent) > 3:
            recent.pop(0)
        if len(path) >= L:
            break

    return path, rows

# ============================================================
# AUDIO
# ============================================================

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
# GRAPH DRAWING (FULL PATH HIGHLIGHT)
# ============================================================

def draw_graph(step, prob_t, path, mode):
    fig, ax = plt.subplots(figsize=(6, 6))

    p = prob_t / (prob_t.max() + 1e-12)
    node_sizes = 120 + 350 * np.sqrt(p)

    # Background graph
    nx.draw_networkx_edges(
        G, POS, ax=ax, alpha=0.05, width=0.5, edge_color="gray"
    )

    # Highlight FULL selected path so far
    if step > 0:
        path_edges = [(path[i], path[i+1]) for i in range(step)]
        nx.draw_networkx_edges(
            G, POS,
            edgelist=path_edges,
            ax=ax,
            width=2.5,
            edge_color="red"
        )

    nx.draw_networkx_nodes(
        G, POS,
        node_size=node_sizes,
        node_color=p,
        cmap="viridis",
        ax=ax
    )

    ax.set_title(f"{mode} — Step {step}")
    ax.axis("off")
    return fig

# ============================================================
# RUN
# ============================================================

if generate:

    D = np.diag(A.sum(axis=1))
    H_base = D - A
    H_bio  = H_base + lambda_bio * build_bio_operator(N)

    prob_no = run_quantum_walk(H_base, start_idx, T_steps, DT, lambda_noise)
    prob_bi = run_quantum_walk(H_bio,  start_idx, T_steps, DT, lambda_noise)

    stochastic = selection_mode.startswith("Stochastic")
    path, table = extract_path(prob_bi, A, prob_no, PATH_LEN, stochastic)

    # ========================================================
    # PROBABILITY HEATMAPS
    # ========================================================

    col1, col2 = st.columns(2)
    with col1:
        fig, ax = plt.subplots()
        ax.imshow(prob_no.T, aspect="auto", origin="lower")
        ax.set_title("Probability Flow (No Bio)")
        st.pyplot(fig)

    with col2:
        fig, ax = plt.subplots()
        ax.imshow(prob_bi.T, aspect="auto", origin="lower")
        ax.set_title("Probability Flow (With Bio)")
        st.pyplot(fig)

    # ========================================================
    # CTQW TRAJECTORIES
    # ========================================================

    st.subheader("CTQW Probability Trajectories")

    fig, ax = plt.subplots()
    ax.plot(prob_bi[:, start_idx], label="Start Node", linewidth=2)

    for idx in path[:5]:
        ax.plot(prob_bi[:, idx], alpha=0.7, label=db[idx].id)

    ax.set_xlabel("Time step")
    ax.set_ylabel("Probability")
    ax.legend()
    st.pyplot(fig)

    # ========================================================
    # AUDIO
    # ========================================================

    st.subheader("Generated Mashup")
    audio = build_audio(path)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, audio, SR)
    st.audio(tmp.name)

    # ========================================================
    # GRAPH ANIMATION
    # ========================================================

    st.subheader("Graph Evolution")
    slot = st.empty()
    for i in range(len(path)):
        fig = draw_graph(i, prob_bi[i], path, graph_mode)
        slot.pyplot(fig)
        plt.close(fig)
        time.sleep(STEP_DELAY)

    # ========================================================
    # DIAGNOSTICS
    # ========================================================

    st.subheader("Transition Diagnostics")
    st.dataframe(table)

    st.subheader("Selected Path")
    st.write([db[i].id for i in path])

st.markdown("---")
st.markdown(
    "<center>Made by Gagan and Praveen, Epoch IIT Hyderabad</center>",
    unsafe_allow_html=True
)
