import torch
from torch.utils.data import Dataset, DataLoader
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import DataLoader
from .label_mapping import SS3_MAP

class ProteinSSPDataset(Dataset):
    def __init__(self, sequences, labels, embeddings):
        self.sequences = sequences
        self.labels = labels
        self.embeddings = embeddings 

    def __len__(self): 
        return len(self.sequences)

    def __getitem__(self, idx):
        layer10, layer20, layer33 = self.embeddings[idx]

        dssp = self.labels[idx]
        y = torch.tensor([SS3_MAP[c] for c in dssp], dtype=torch.long)

        return (layer10, layer20, layer33), y
    
def collate_fn(batch):
    xs, ys = zip(*batch)
    l10, l20, l33 = zip(*xs)

    l10 = pad_sequence(l10, batch_first=True)
    l20 = pad_sequence(l20, batch_first=True)
    l33 = pad_sequence(l33, batch_first=True)

    ys_pad = pad_sequence(ys, batch_first=True, padding_value=-1)
    mask = (ys_pad != -1)

    return (l10, l20, l33), ys_pad, mask
