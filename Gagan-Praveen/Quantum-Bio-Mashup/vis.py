import numpy as np
import matplotlib.pyplot as plt

y = np.load("raw_songs/SSvid.net--Taylor-Swift-Blank-Space.npy")
print(y.shape, y.dtype)   # e.g. (N,) float32

plt.plot(y)
plt.title("First 2000 samples of normalized song1")
plt.show()
