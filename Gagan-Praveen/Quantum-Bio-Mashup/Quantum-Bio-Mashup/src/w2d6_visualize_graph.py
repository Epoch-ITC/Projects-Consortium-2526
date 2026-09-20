"""
Week 2 — Day 6
Graph Visualization (Classical Sanity Check)
"""

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import os

# =========================
# CONFIG
# =========================
ADJ_PATH = "database/adjacency_sym.npy"
OUT_DIR = "outputs"
OUT_IMG = os.path.join(OUT_DIR, "graph_visualization.png")

os.makedirs(OUT_DIR, exist_ok=True)

# =========================
# LOAD GRAPH
# =========================
A = np.load(ADJ_PATH)
N = A.shape[0]

print(f"[INFO] Loaded symmetric adjacency matrix ({N} nodes)")

# =========================
# BUILD NETWORKX GRAPH
# =========================
G = nx.Graph()

for i in range(N):
    G.add_node(i)

for i in range(N):
    for j in range(i + 1, N):
        if A[i, j] > 0:
            G.add_edge(i, j, weight=A[i, j])

print(f"[INFO] Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")

# =========================
# DRAW
# =========================
plt.figure(figsize=(10, 10))
pos = nx.spring_layout(G, seed=42)

nx.draw(
    G,
    pos,
    node_size=40,
    alpha=0.85,
    with_labels=False
)

plt.title("Segment Similarity Graph (Symmetric KNN)")
plt.tight_layout()
plt.savefig(OUT_IMG, dpi=300)
plt.close()

print(f"[DONE] Graph visualization saved → {OUT_IMG}")
