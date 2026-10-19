"""ResNet-18 whose parameter names match the training checkpoints.

Torchvision is intentionally not imported. The CPU lab image pins a CPU
PyTorch wheel, and a later torchvision install can replace it.
"""
from __future__ import annotations

import torch
from torch import nn


class _BasicBlock(nn.Module):
    def __init__(self, in_planes: int, planes: int, stride: int = 1, downsample: nn.Module | None = None):
        super().__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, 3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(planes, planes, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x if self.downsample is None else self.downsample(x)
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        return self.relu(out + identity)


def _layer(in_planes: int, planes: int, blocks: int, stride: int) -> nn.Sequential:
    downsample = None
    if stride != 1 or in_planes != planes:
        downsample = nn.Sequential(
            nn.Conv2d(in_planes, planes, 1, stride=stride, bias=False),
            nn.BatchNorm2d(planes),
        )
    layers = [_BasicBlock(in_planes, planes, stride, downsample)]
    layers += [_BasicBlock(planes, planes) for _ in range(1, blocks)]
    return nn.Sequential(*layers)


class _ResNet18(nn.Module):
    def __init__(self, in_channels: int, small_input: bool):
        super().__init__()
        if small_input:
            self.conv1 = nn.Conv2d(in_channels, 64, 3, stride=1, padding=1, bias=False)
            self.maxpool = nn.Identity()
        else:
            self.conv1 = nn.Conv2d(in_channels, 64, 7, stride=2, padding=3, bias=False)
            self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.layer1 = _layer(64, 64, 2, 1)
        self.layer2 = _layer(64, 128, 2, 2)
        self.layer3 = _layer(128, 256, 2, 2)
        self.layer4 = _layer(256, 512, 2, 2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512, 1000)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.maxpool(self.relu(self.bn1(self.conv1(x))))
        x = self.layer4(self.layer3(self.layer2(self.layer1(x))))
        x = torch.flatten(self.avgpool(x), 1)
        return self.fc(x)


class _MLP(nn.Module):
    def __init__(self, output_size: int, dropout: float):
        super().__init__()
        self.fc1 = nn.Linear(512, 512)
        self.relu1 = nn.ReLU()
        self.drop = nn.Dropout(p=dropout) if dropout > 0 else nn.Identity()
        self.fc2 = nn.Linear(512, output_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(self.drop(self.relu1(self.fc1(x))))


class ResNet18Classifier(nn.Module):
    """``linear`` is the CUB head. ``mlp`` is the EuroSAT head, with a 3x3 stem."""

    def __init__(self, in_channels: int, n_classes: int, *, head: str, small_input: bool, dropout: float = 0.0):
        super().__init__()
        if head not in ("linear", "mlp"):
            raise ValueError("head must be linear or mlp")
        self.head = head
        self.resnet18 = _ResNet18(in_channels, small_input)
        if head == "linear":
            self.resnet18.fc = nn.Linear(512, n_classes)
            self.mlp = None
        else:
            self.resnet18.fc = nn.Identity()
            self.mlp = _MLP(n_classes, dropout)
        self.backbone_drop = nn.Dropout(p=dropout) if dropout > 0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.head == "mlp":
            assert self.mlp is not None
            return self.mlp(self.backbone_drop(self.resnet18(x)))
        x = self.resnet18.maxpool(self.resnet18.relu(self.resnet18.bn1(self.resnet18.conv1(x))))
        x = self.resnet18.layer4(self.resnet18.layer3(self.resnet18.layer2(self.resnet18.layer1(x))))
        x = torch.flatten(self.resnet18.avgpool(x), 1)
        return self.resnet18.fc(self.backbone_drop(x))
