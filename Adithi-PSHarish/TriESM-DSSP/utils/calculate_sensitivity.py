import torch 
from .esm_extractor import extract_embeddings

AA_LIST = list("ACDEFGHIKLMNPQRSTVWY")

def mutate_sequence(seq, pos, new_aa):
    return seq[:pos] + new_aa + seq[pos+1:]


def get_prediction(model, seq, device = "cpu"):
    model.eval()
    
    with torch.no_grad():
        emb = extract_embeddings([seq])[0]

        l10 = emb[0].unsqueeze(0).to(device)
        l20 = emb[1].unsqueeze(0).to(device)
        l33 = emb[2].unsqueeze(0).to(device)

        mask = torch.ones(1, len(seq), dtype=torch.bool).to(device)

        logits = model((l10, l20, l33), mask)
        probs = torch.softmax(logits, dim=-1)

        return probs[0].cpu()

def calc_sensitivity(model, seq, device = "cpu"):
    L = len(seq)
    base_probs = get_prediction(model, seq, device)

    sens = torch.zeros(L, 20)

    for i in range(L):
        for j, aa in enumerate(AA_LIST):

            if seq[i] == aa:
                continue

            mut_seq = mutate_sequence(seq, i, aa)
            mut_probs = get_prediction(model, mut_seq, device)

            diff = torch.abs(mut_probs[i] - base_probs[i]).sum()
            sens[i, j] = diff

    return sens