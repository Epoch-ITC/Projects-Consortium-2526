import torch 

def LayerEntropyRegularizedCrossEntropy(logits, y, model, loss_fn, alpha=0.01):
    ce_loss = loss_fn(logits.view(-1, 3), y.view(-1))
    weights = torch.softmax(model.layer_weights, dim=0)
    entropy = -(weights * torch.log(weights + 1e-8)).sum()
    return ce_loss + alpha * entropy