import argparse
import os
import torch
import pandas as pd
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from utils import *
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="Protein Secondary Structure Prediction")

    parser.add_argument("--train_dataset", type=str, required=True, help="Path to the training dataset (.csv) with columns sequence, dssp3")
    parser.add_argument("--val_dataset", type=str, required=True, help="Path to the validation dataset (.csv) with columns sequence, dssp3")
    parser.add_argument("--test_dataset", type=str, required=True, help="Path to the testing dataset (.csv) with columns sequence, dssp3")

    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--num_workers", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--save_path", type=str, default="model.pt")

    args = parser.parse_args()

    os.makedirs("models", exist_ok=True)
    args.save_path = os.path.join("models", args.save_path)

    return args

def main():
    args = parse_args()
    epochs = args.epochs

    train_df = pd.read_csv(args.train_dataset)
    train_seqs, train_labels = build_dataset(train_df)
    train_seqs = train_seqs[0:6000]
    train_labels = train_labels[0:6000]
    print("Embedding train sequences")
    train_embs = embed_all(train_seqs, batch_size=args.batch_size)
    train_dataset = ProteinSSPDataset(train_seqs, train_labels, train_embs)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, collate_fn=collate_fn)

    
    val_df = pd.read_csv(args.val_dataset)
    val_seqs,   val_labels   = build_dataset(val_df)   
    print("Embedding val sequences")
    val_embs   = embed_all(val_seqs, batch_size=args.batch_size)
    val_dataset   = ProteinSSPDataset(val_seqs, val_labels, val_embs)
    val_loader = DataLoader(val_dataset, batch_size = args.batch_size, shuffle = False, collate_fn=collate_fn)

    test_df = pd.read_csv(args.test_dataset)
    test_seqs,  test_labels  = build_dataset(test_df)
    print("Embedding test sequences")
    test_embs  = embed_all(test_seqs, batch_size=args.batch_size)
    test_dataset  = ProteinSSPDataset(test_seqs, test_labels, test_embs)
    test_loader  = DataLoader(test_dataset, batch_size=args.batch_size , shuffle=False, collate_fn=collate_fn)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = DSSPModel().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    loss_fn = nn.CrossEntropyLoss(ignore_index=-1)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', patience=3, factor=0.5)

    best_val = 0
    patience = 5
    counter = 0

    for epoch in range(args.epochs):

        train_loss = train_one_epoch(model, train_loader, loss_fn, optimizer, device)
        val_loss, val_acc = evaluate(model, val_loader, loss_fn, device)

        scheduler.step(val_acc)

        print(f"\nEpoch {epoch+1}")
        print(f"Train Loss: {train_loss:.4f}")
        print(f"Val Loss: {val_loss:.4f} | Val Q3: {val_acc:.4f}")
        print("Layer Weights:", torch.softmax(model.layer_weights, dim=0).detach().cpu().numpy())

        if val_acc > best_val:
            best_val = val_acc
            torch.save(model.state_dict(), "best_model.pt")
            counter = 0
        else:
            counter += 1

        if counter >= patience:
            print("Early stopping triggered")
            break

    test_loss, test_acc = evaluate(model, test_loader)
    print(f"\nTest Q3 Accuracy: {test_acc:.4f}")
    weights = torch.softmax(model.layer_weights, dim=0).detach().cpu()
    print("Layer importance:")
    print("L10:", weights[0].item())
    print("L20:", weights[1].item())
    print("L33:", weights[2].item())

    model.eval()
    evaluate_layers(model, val_loader)
    results = classwise_ablation(model, val_loader)

    for cls, name in zip([0,1,2], ["Helix","Sheet","Coil"]):
        arr = np.array(results[cls])
        print(f"\n{name}")
        for layer in range(3):
            vals = arr[arr[:,0]==layer][:,1]
            print(f"L{[10,20,33][layer]} drop:", vals.mean())


    (l10, l20, l33), y, mask = next(iter(val_loader))

    l10 = l10.to(device)
    l20 = l20.to(device)
    l33 = l33.to(device)
    mask = mask.to(device)
    y = y.to(device)

    h10 = model.proj10(l10)
    h20 = model.proj20(l20)
    h33 = model.proj33(l33)

    check_similarity(h10, h20, h33)

    full = model.forward_with_mask((l10,l20,l33), mask, [1,1,1])
    l33  = model.forward_with_mask((l10,l20,l33), mask, [0,0,1])

    full_pred = full.argmax(-1)
    l33_pred  = l33.argmax(-1)

    improved_mask = (full_pred == y) & (l33_pred != y) & mask

    print("Positions improved by adding L10 or L20:", improved_mask.sum().item())

    for cls, name in zip([0,1,2], ["Helix","Sheet","Coil"]):
        count = ((y == cls) & improved_mask).sum().item()
        print(name, count)

if __name__ == "__main__":
    main()