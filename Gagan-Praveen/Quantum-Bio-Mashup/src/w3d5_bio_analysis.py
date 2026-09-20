import numpy as np
import matplotlib.pyplot as plt

P0 = np.load("outputs/prob_no_bio.npy")
P1 = np.load("outputs/prob_with_bio.npy")

T, N = P0.shape

# 1️⃣ L1 distance over time
l1 = np.sum(np.abs(P0 - P1), axis=1)

# 2️⃣ Shannon entropy
def entropy(p):
    p = p + 1e-12
    return -np.sum(p * np.log(p), axis=1)

H0 = entropy(P0)
H1 = entropy(P1)

plt.figure(figsize=(12,4))

plt.subplot(1,2,1)
plt.plot(l1)
plt.title("L1 Distance (Bio vs No Bio)")
plt.xlabel("Time")
plt.ylabel("Distance")

plt.subplot(1,2,2)
plt.plot(H0, label="No Bio")
plt.plot(H1, label="With Bio")
plt.legend()
plt.title("Entropy Evolution")

plt.tight_layout()
plt.savefig("outputs/bio_effect_analysis.png", dpi=300)
plt.show()

print("[RESULT] Mean L1 distance:", l1.mean())
print("[RESULT] Entropy shift:", (H1 - H0).mean())
