import numpy as np

# Load adjacency matrix
A = np.load("database/adjacency_sym.npy")

# Basic sanity
assert A.ndim == 2
assert A.shape[0] == A.shape[1]
assert np.allclose(A, A.T, atol=1e-8), "Adjacency not symmetric"

N = A.shape[0]
print(f"Loaded adjacency matrix of size {N} x {N}")

# Degree matrix
degrees = A.sum(axis=1)
D = np.diag(degrees)

# Sanity checks
assert np.all(degrees >= 0), "Negative degree detected"
H_adj = A.copy()
H_lap = D - A
# Both must be Hermitian
assert np.allclose(H_adj, H_adj.T, atol=1e-8)
assert np.allclose(H_lap, H_lap.T, atol=1e-8)
# Eigenvalues and eigenvectors
eigvals_adj, eigvecs_adj = np.linalg.eigh(H_adj)
eigvals_lap, eigvecs_lap = np.linalg.eigh(H_lap)
assert np.all(np.isreal(eigvals_adj))
assert np.all(np.isreal(eigvals_lap))
spread_adj = eigvals_adj.max() - eigvals_adj.min()
spread_lap = eigvals_lap.max() - eigvals_lap.min()
def count_degeneracies(eigvals, tol=1e-6):
    unique = []
    for v in eigvals:
        if not any(abs(v - u) < tol for u in unique):
            unique.append(v)
    return len(eigvals) - len(unique)

deg_adj = count_degeneracies(eigvals_adj)
deg_lap = count_degeneracies(eigvals_lap)
print("=== Spectrum Summary ===")
print(f"Adjacency: spread={spread_adj:.4f}, degeneracies={deg_adj}")
print(f"Laplacian: spread={spread_lap:.4f}, degeneracies={deg_lap}")
np.save("database/H_adjacency.npy", H_adj)
np.save("database/H_laplacian.npy", H_lap)
np.save("database/eigvals_adj.npy", eigvals_adj)
np.save("database/eigvals_lap.npy", eigvals_lap)
