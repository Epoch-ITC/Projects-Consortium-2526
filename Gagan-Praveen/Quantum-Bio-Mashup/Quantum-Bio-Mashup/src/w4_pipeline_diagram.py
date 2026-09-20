import matplotlib.pyplot as plt

stages = [
    "Audio\n(WAV Tracks)",
    "Spectral DB\n(STFT + Wavelets)",
    "Similarity Graph\n(KNN, Cosine)",
    "Hamiltonian\n(Laplacian / Bio)",
    "Quantum Evolution\n(CTQW / ENAQT)",
    "Path Extraction\n(Argmax + Memory)",
    "Audio Mashup\n(Crossfade)"
]

x = list(range(len(stages)))
y = [0]*len(stages)

plt.figure(figsize=(16,3))

for i, stage in enumerate(stages):
    plt.text(
        x[i], y[i], stage,
        ha="center", va="center",
        bbox=dict(boxstyle="round,pad=0.4"),
        fontsize=10
    )
    if i > 0:
        plt.arrow(
            x[i-1]+0.3, 0,
            0.4, 0,
            length_includes_head=True,
            head_width=0.05,
            head_length=0.05
        )

plt.axis("off")
plt.title("Quantum-Bio Mashup Generation Pipeline")
plt.tight_layout()
plt.savefig("outputs/pipeline_diagram.png", dpi=300)
plt.close()

print("[SAVE] outputs/pipeline_diagram.png")
