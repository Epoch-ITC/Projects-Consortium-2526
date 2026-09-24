import torch
from .loss_function import LayerEntropyRegularizedCrossEntropy

def train_one_epoch(model, loader, loss_fn, optimizer, device = "cpu"):
    model.train()
    total_loss = 0

    for (l10, l20, l33), y, mask in loader:
        l10, l20, l33 = l10.to(device), l20.to(device), l33.to(device)
        y = y.to(device)

        mask = mask.to(device)
        optimizer.zero_grad()
        logits = model((l10, l20, l33), mask)
        loss = LayerEntropyRegularizedCrossEntropy(logits, y, model, loss_fn)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    return total_loss / len(loader)

        
def evaluate(model, loader, loss_fn, device = "cpu"):
    model.eval()

    total_loss = 0
    correct = 0
    total = 0

    with torch.no_grad():
        for (l10, l20, l33), y, mask in loader:
            l10, l20, l33 = l10.to(device), l20.to(device), l33.to(device)
            y = y.to(device)
            mask = mask.to(device)
            logits = model((l10, l20, l33), mask)
            loss = loss_fn(logits.view(-1, 3),y.view(-1))
            total_loss += loss.item()
            preds = logits.argmax(dim=-1)
            correct += ((preds == y) & mask).sum().item()

            total += mask.sum().item()

    acc = correct / total
    return total_loss / len(loader), acc

def evaluate_layers(model, loader, device = "cpu"):
    model.eval()

    accs = {"full":0, "l10":0, "l20":0, "l33":0}
    total = 0

    with torch.no_grad():
        for (l10,l20,l33), y, mask in loader:
            l10,l20,l33 = l10.to(device), l20.to(device), l33.to(device)
            y,mask = y.to(device), mask.to(device)

            full = model.forward_with_mask((l10,l20,l33), mask, [1,1,1])
            p_full = full.argmax(-1)

            p10 = model.forward_with_mask((l10,l20,l33), mask, [1,0,0]).argmax(-1)
            p20 = model.forward_with_mask((l10,l20,l33), mask, [0,1,0]).argmax(-1)
            p33 = model.forward_with_mask((l10,l20,l33), mask, [0,0,1]).argmax(-1)

            m = mask

            accs["full"] += (p_full[m]==y[m]).sum().item()
            accs["l10"]  += (p10[m]==y[m]).sum().item()
            accs["l20"]  += (p20[m]==y[m]).sum().item()
            accs["l33"]  += (p33[m]==y[m]).sum().item()

            total += m.sum().item()

    for k in accs:
        accs[k] /= total

    print("Layer-wise performance:", accs)


def classwise_ablation(model, loader, device = "cpu"):
    model.eval()

    results = {0:[],1:[],2:[]}  # H,E,C

    with torch.no_grad():
        for (l10,l20,l33), y, mask in loader:
            l10,l20,l33 = l10.to(device), l20.to(device), l33.to(device)
            y,mask = y.to(device), mask.to(device)

            full = model.forward_with_mask((l10,l20,l33), mask, [1,1,1])
            full_pred = full.argmax(-1)

            for layer in range(3):
                mask_vec = [1,1,1]
                mask_vec[layer] = 0

                logits = model.forward_with_mask((l10,l20,l33), mask, mask_vec)
                pred = logits.argmax(-1)

                for cls in [0,1,2]:
                    m = (y==cls) & mask
                    if m.sum()==0: continue

                    acc_full = (full_pred[m]==y[m]).float().mean()
                    acc_new  = (pred[m]==y[m]).float().mean()

                    results[cls].append((layer, (acc_full-acc_new).item()))

    return results

def check_similarity(h10, h20, h33):
    h10f = h10.reshape(-1, h10.shape[-1])
    h20f = h20.reshape(-1, h20.shape[-1])
    h33f = h33.reshape(-1, h33.shape[-1])

    print("Layer Similarities")
    print("10-20:", torch.cosine_similarity(h10f, h20f, dim=1).mean().item())
    print("20-33:", torch.cosine_similarity(h20f, h33f, dim=1).mean().item())
    print("10-33:", torch.cosine_similarity(h10f, h33f, dim=1).mean().item())