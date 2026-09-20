import pickle

db = pickle.load(open("database/master_db.pkl", "rb"))

seg = db[0]

print(seg.id)
print(seg.spectrogram.shape)     # EXPECT: (1025, 128)
print(seg.wavelet_energy.shape)  # EXPECT: (4,)
print(seg.key)
print(seg.global_index)
