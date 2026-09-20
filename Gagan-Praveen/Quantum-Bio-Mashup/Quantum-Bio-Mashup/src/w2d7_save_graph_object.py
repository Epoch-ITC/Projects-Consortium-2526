"""
Week 2 — Day 7
Save finalized graph object for Week 3 quantum walk
"""

import pickle
import numpy as np

GRAPH_PATH = "database/graph_object.pkl"

adj = np.load("database/adjacency_sym.npy")

graph = {
    "adjacency": adj,
    "num_nodes": adj.shape[0],
    "type": "knn_similarity_graph",
    "symmetrization": "A[i,j] = max(A_ij, A_ji)",
}

with open(GRAPH_PATH, "wb") as f:
    pickle.dump(graph, f)

print(f"[DONE] Graph object saved → {GRAPH_PATH}")
