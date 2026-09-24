import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import os 

def ramachandran_plot(imp, save_path, phi, psi, colors):
    importance_norm = (imp - imp.min()) / (imp.max() - imp.min())
    filename = os.path.join(save_path, f"ramachandran_plot.png")

    plt.rcParams.update({"font.family": "sans-serif", "font.size": 10, "axes.titlesize": 12, "axes.labelsize": 10})
    fig, axs = plt.subplots(1, 2, figsize=(13, 5), dpi=300)
    sns.kdeplot(x=phi, y=psi,ax=axs[0],fill=True,cmap="Greys",levels=30,thresh=0.05,alpha=0.4)
    axs[0].scatter(phi, psi,c=colors,s=10,alpha=0.9,edgecolors='none')
    axs[0].set_title("Secondary Structure Landscape", fontweight='bold')
    sns.kdeplot(x=phi, y=psi, ax=axs[1], fill=True, cmap="Greys", levels=30, thresh=0.05,alpha=0.3)
    axs[1].scatter(phi, psi,c=importance_norm,cmap="viridis",s=20,alpha=0.15,edgecolors='none')
    scatter = axs[1].scatter(phi, psi,c=importance_norm,cmap="viridis",s=8,alpha=0.95,edgecolors='none')
    axs[1].set_title("Mutation Sensitivity Landscape", fontweight='bold')
    cbar = fig.colorbar(scatter, ax=axs[1], fraction=0.046, pad=0.04)
    cbar.set_label("Normalized Sensitivity")

    for i, ax in enumerate(axs):
        ax.set_xlim(-180, 180)
        ax.set_ylim(-180, 180)
        ax.set_xlabel("ϕ (Phi)")
        ax.set_ylabel("ψ (Psi)")
        ax.axhline(0, color='black', linewidth=0.5, alpha=0.3)
        ax.axvline(0, color='black', linewidth=0.5, alpha=0.3)
        ax.grid(True, linestyle='--', linewidth=0.4, alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.text(-0.15, 1.05, chr(65 + i), transform=ax.transAxes, fontsize=14, fontweight='bold')

    axs[0].annotate("α-helix", xy=(-60, -40), fontsize=9)
    axs[0].annotate("β-sheet", xy=(-130, 130), fontsize=9)
    axs[0].annotate("Left-handed helix", xy=(60, 40), fontsize=8)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')

    plt.show()