import json
import matplotlib.pyplot as plt

with open("outputs/path_no_bio.json") as f:
    no_bio = json.load(f)

with open("outputs/path_with_bio.json") as f:
    bio = json.load(f)

t = [x["t"] for x in no_bio]
idx_no  = [x["segment"] for x in no_bio]
idx_bio = [x["segment"] for x in bio]

plt.figure(figsize=(12,5))
plt.plot(t, idx_no, label="No Bio", alpha=0.8)
plt.plot(t, idx_bio, label="With Bio", alpha=0.8)

plt.xlabel("Time step")
plt.ylabel("Segment ID")
plt.title("Quantum Path Divergence (Bio vs No Bio)")
plt.legend()
plt.tight_layout()
plt.savefig("outputs/transition_diff.png", dpi=300)
plt.show()

print("[SAVE] outputs/transition_diff.png")
