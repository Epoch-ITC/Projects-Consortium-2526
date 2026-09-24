import esm
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"

esm_model, alphabet = esm.pretrained.esm2_t33_650M_UR50D()
esm_model = esm_model.to(device).eval()

batch_converter = alphabet.get_batch_converter()

@torch.no_grad()
def extract_embeddings(sequences):
    """
    sequences: list[str]
    returns: list of (layer10, layer20, layer33)
    """

    batch = [(f"seq{i}", seq) for i, seq in enumerate(sequences)]
    _, _, tokens = batch_converter(batch)

    tokens = tokens.to(device)
    outputs = esm_model(tokens, repr_layers=[10, 20, 33])
    reps = outputs["representations"]

    embeddings = []

    for i, seq in enumerate(sequences):
        L = len(seq)
        layer10 = reps[10][i, 1:L+1].cpu()
        layer20 = reps[20][i, 1:L+1].cpu()
        layer33 = reps[33][i, 1:L+1].cpu()
        embeddings.append((layer10, layer20, layer33))

    return embeddings


@torch.no_grad()
def embed_all(sequences, batch_size=8):
    """
    sequences: list[str]
    returns: list of (layer10, layer20, layer33)
    """
    all_embeddings = []
    total = len(sequences)

    for i in range(0, total, batch_size):
        batch_seqs = sequences[i:i+batch_size]

        batch = [(f"seq{j}", s) for j, s in enumerate(batch_seqs)]
        _, _, tokens = batch_converter(batch)

        tokens = tokens.to(device)
        outputs = esm_model(tokens, repr_layers=[10, 20, 33])
        reps = outputs["representations"]

        for k, seq in enumerate(batch_seqs):
            L = len(seq)

            l10 = reps[10][k, 1:L+1].cpu()
            l20 = reps[20][k, 1:L+1].cpu()
            l33 = reps[33][k, 1:L+1].cpu()

            all_embeddings.append((l10, l20, l33))

    return all_embeddings