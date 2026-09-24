import argparse
import os
import pandas as pd
import numpy as np
from Bio import SeqIO
import biotite.structure as struc
import biotite.structure.io as strucio
from utils import *
import torch
import torch.nn as nn

def parse_args():
    parser = argparse.ArgumentParser(description="Mutation Analysis")

    parser.add_argument("--pdb_path", type=str, required=True, help="PDB file path eg. 1P7E.pdb")
    parser.add_argument("--dssp_model_path", type=str, required=True, help="path to your trained TriESM-DSSP model")
    parser.add_argument("--results_folder_name", type=str, required=True)

    args = parser.parse_args()

    os.makedirs(args.results_folder_name, exist_ok=True)

    return args

def main():
    args = parse_args()
    pdb_path = args.pdb_path
    model_path = args.dssp_model_path
    result_folder = args.results_folder_name


    if not os.path.exists(pdb_path):
        print("PDB File not found")
        return

    if not os.path.exists(model_path):
        print("Trained DSSP Model not found")
        return 

    with open(pdb_path, 'r') as pdb_handle:
        records = list(SeqIO.parse(pdb_handle, "pdb-atom"))

    seq = str(records[0].seq)

    atom_array = strucio.load_structure(pdb_path)
    atom_array = atom_array[atom_array.chain_id == "A"]

    phi, psi, _ = struc.dihedral_backbone(atom_array)
    sse = struc.annotate_sse(atom_array)
    valid = ~np.isnan(phi) & ~np.isnan(psi)
    phi = np.rad2deg(phi)[valid]
    psi = np.rad2deg(psi)[valid]
    sse = sse[valid]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = DSSPModel().to(device)

    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))

    sensitivity = calc_sensitivity(model, seq, device)
    importance = sensitivity.mean(dim = 1)
    importance = importance[1:-1]

    colors = []
    for ss in sse:
        if ss == "a":
            colors.append("red")
        elif ss == "b":
            colors.append("blue")
        else:
            colors.append("gray")

    plot_residue_sensitivity(imp=importance, save_path=result_folder)
    ramachandran_plot(imp=importance, phi=phi, psi=psi, colors=colors, save_path=result_folder)

    filename = os.path.join(result_folder, f"sensitivity.txt")

    with open(filename, "w") as f:
        for i, val in enumerate(importance, start=1):
            f.write(f"{i} {val}\n")


if __name__ == "__main__":
    main()