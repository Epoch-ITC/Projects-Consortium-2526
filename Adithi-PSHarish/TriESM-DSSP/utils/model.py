import torch
import torch.nn as nn
from .positional_encoding import PositionalEncoding

class DSSPModel(nn.Module):
    def __init__(self, d_model=384, n_classes=3):
        super().__init__()

        self.proj10 = nn.Linear(1280, d_model)
        self.proj20 = nn.Linear(1280, d_model)
        self.proj33 = nn.Linear(1280, d_model)
        self.layer_weights = nn.Parameter(torch.ones(3))
        self.pos_enc = PositionalEncoding(d_model)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=6,
            dim_feedforward=768,
            dropout=0.1,
            batch_first=True,
            norm_first=True
        )

        self.encoder = nn.TransformerEncoder(encoder_layer,num_layers=3)
        self.norm = nn.LayerNorm(d_model)
        self.classifier = nn.Linear(d_model, n_classes)

    def forward(self, x_tuple, mask):
        l10, l20, l33 = x_tuple

        def norm(x):
            return (x - x.mean(dim=-1, keepdim=True)) / (x.std(dim=-1, keepdim=True) + 1e-6)

        l10 = norm(l10)
        h10 = self.proj10(l10)

        l20 = norm(l20)
        h20 = self.proj20(l20)

        l33 = norm(l33)
        h33 = self.proj33(l33)

        weights = torch.softmax(self.layer_weights, dim=0)
        x = (weights[0] * h10 +weights[1] * h20 + weights[2] * h33)
        x = self.pos_enc(x)
        x = self.encoder(x, src_key_padding_mask=~mask)
        x = self.norm(x)

        return self.classifier(x)

    def forward_with_mask(self, x_tuple, mask, layer_mask=[1,1,1]):
        l10, l20, l33 = x_tuple
    
        def norm(x):
            return (x - x.mean(dim=-1, keepdim=True)) / (x.std(dim=-1, keepdim=True) + 1e-6)
    
        l10 = norm(l10)
        l20 = norm(l20)
        l33 = norm(l33)
    
        h10 = self.proj10(l10)
        h20 = self.proj20(l20)
        h33 = self.proj33(l33)
    
        weights = torch.softmax(self.layer_weights, dim=0)
    
        x = (layer_mask[0] * weights[0] * h10 + layer_mask[1] * weights[1] * h20 + layer_mask[2] * weights[2] * h33)
    
        x = self.pos_enc(x)
        x = self.encoder(x, src_key_padding_mask=~mask)
        x = self.norm(x)
    
        return self.classifier(x)