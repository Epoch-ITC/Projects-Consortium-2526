"""
    This function calculates residue level features given a protein sequence
    Input: Protein Sequence Length (L)
    Output: Physico-chemical features per residue
    Shape: L x f
"""

import numpy as np 
import torch
from .compute_physchem import compute_all

LABEL_MAP = {'H': 0, 'E': 1, 'C': 2}

def sequence_to_tensor(seq, dssp3):
    out = compute_all(seq)
    per = out["per_residue"]
    feats = np.stack([
        per['KD'],
        per['HW'],
        per['volume'],
        per['CF_helix'],
        per['CF_sheet'],
        per['CF_turn'],
        per['polarizability'],
        per['HBD_sidechain'],
        per['HBA_sidechain'],
        per['is_aromatic'],
    ], axis=1)   # shape: (L, F)

    labels = np.array([LABEL_MAP[c] for c in dssp3], dtype=np.int64)
    return torch.tensor(feats, dtype=torch.float32), torch.tensor(labels, dtype=torch.long)


def build_dataset(df):
    sequences = []
    labels = []

    for _, row in df.iterrows():
        seq = row["sequence"]     
        dssp = row["dssp3"]      #

        sequences.append(seq)
        labels.append(dssp)

    return sequences, labels

