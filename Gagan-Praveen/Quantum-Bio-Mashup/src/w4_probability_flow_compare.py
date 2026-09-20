import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

prob_no   = np.load("outputs/prob_no_bio.npy")
prob_bio  = np.load("outputs/prob_with_bio.npy")

plt.figure(figsize=(16,6))

plt.subplot(1,2,1)
sns.heatmap(prob_no.T, cmap="viridis", cbar=False)
plt.title("Without Bio Modulation")
plt.xlabel("Time")
plt.ylabel("Segment index")

plt.subplot(1,2,2)
sns.heatmap(prob_bio.T, cmap="viridis", cbar=True)
plt.title("With Bio Modulation")
plt.xlabel("Time")

plt.tight_layout()
plt.savefig("outputs/probability_flow_bio_vs_nobio.png", dpi=300)
plt.close()

print("[SAVE] outputs/probability_flow_bio_vs_nobio.png")
