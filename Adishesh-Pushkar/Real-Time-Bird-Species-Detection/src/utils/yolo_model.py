import numpy as np
import pandas as pd
import PIL
import gc
import torch
import torch.nn as nn

import torch.nn.functional as F
from torch.utils.data import DataLoader
import torchvision.datasets as datasets
import torchvision.transforms as transforms
import torchvision.models as models


class customYOLO(nn.Module):
    def __init__(self, in_channels=3, num_classes=5):
        """
            We implement a YOLO model from the original paper
            Input : Tensor of size (B, 448, 448, 3)
            Output : Tensor of size (B, 7, 7, 5)

            Each cell contains [x, y, w, h, confidence]
        """
        super(customYOLO, self).__init__()

        # Load pretrained resnet
        resnet = models.resnet50(pretrained=True)

        # Use resnet layers
        self.backbone = nn.Sequential(
            resnet.conv1,
            resnet.bn1,
            resnet.relu,
            resnet.maxpool,
            resnet.layer1,
            resnet.layer2,
            resnet.layer3,
            resnet.layer4
        )

        self.detection_layers = nn.Sequential(
            nn.Conv2d(2048, 1024, kernel_size=3, padding=1),
            nn.BatchNorm2d(1024),
            nn.LeakyReLU(0.1),

            nn.Conv2d(1024, 1024, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(1024),
            nn.LeakyReLU(0.1),

            nn.Conv2d(1024, 1024, kernel_size=3, padding=1),
            nn.BatchNorm2d(1024),
            nn.LeakyReLU(0.1),
        )
        

        self.conv_head = nn.Sequential(
            nn.Conv2d(1024, 512, kernel_size=3, padding=1),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.1),
            nn.Conv2d(512, 5, kernel_size=1) # The 5 represents [x, y, w, h, conf]
        )


    # Pass the input through the model
    def forward(self, x):

        # Pass through resnet backbone
        x = self.backbone(x)

        # Pass through detection layers
        x = self.detection_layers(x)
        
        # Flatten before passing to mlp
        x = self.conv_head(x)

        # Reshape final output
        x = x.permute(0, 2, 3, 1)

        output = torch.sigmoid(x)
        
        return output
