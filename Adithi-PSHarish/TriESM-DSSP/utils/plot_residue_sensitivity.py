import torch
import numpy as np
from matplotlib import pyplot as plt
import seaborn as sns
import os

window = 5

def plot_residue_sensitivity(imp, save_path):
    importance_np = imp.detach().cpu().numpy()
    smoothed = np.convolve(importance_np, np.ones(window)/window, mode='same')
    threshold = np.percentile(importance_np, 95)
    high_idx = np.where(importance_np >= threshold)[0]

    filename = os.path.join(save_path,f"residue_importance.png")

    plt.rcParams.update({"font.family": "sans-serif","font.size": 10, "axes.titlesize": 12,"axes.labelsize": 10})

    fig, ax = plt.subplots(figsize=(10, 4), dpi=300)
    ax.plot(importance_np,linewidth=1, alpha=0.4,label="Raw")
    ax.plot(smoothed, linewidth=2, label="Smoothed")
    ax.scatter(high_idx, importance_np[high_idx], s=15, zorder=3, label="High importance")
    ax.set_title("Residue-wise Mutation Sensitivity", fontweight='bold')
    ax.set_xlabel("Residue Position")
    ax.set_ylabel("Sensitivity")
    ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.4)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=8)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.show()
