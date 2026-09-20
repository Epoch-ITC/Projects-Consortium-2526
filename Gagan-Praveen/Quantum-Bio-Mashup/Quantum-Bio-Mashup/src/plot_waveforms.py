import librosa
import matplotlib.pyplot as plt
import os

RAW_DIR = "raw_songs"
OUT_DIR = "outputs"

def plot_waveform(file_path):
    y, sr = librosa.load(file_path, sr=22050)

    plt.figure(figsize=(12, 3))
    plt.plot(y, linewidth=0.8)
    plt.title(f"Waveform: {os.path.basename(file_path)} | sr={sr}")
    plt.xlabel("Samples")
    plt.ylabel("Amplitude")
    plt.tight_layout()

    out_path = os.path.join(OUT_DIR, os.path.basename(file_path) + "_waveform.png")
    plt.savefig(out_path)
    plt.close()

    print(f"Saved {out_path}")


if __name__ == "__main__":
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)

    wav_files = [f for f in os.listdir(RAW_DIR) if f.endswith(".wav")]

    if not wav_files:
        print("No .wav files found in raw_songs/.")
        exit()

    for f in wav_files:
        full_path = os.path.join(RAW_DIR, f)
        plot_waveform(full_path)
