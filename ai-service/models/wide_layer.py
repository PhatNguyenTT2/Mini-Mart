"""Masked Wide MLP Layer module for ai-service.

Processes log1p-normalized Apriori lift inputs via a 2-layer MLP (1 -> 16 -> ReLU -> 16 -> 1).
Applies an explicit presence mask to guarantee WideLayer(0) = 0 (no rule = exactly zero score contribution), and uses zero-initialization on the final layer to prevent scale mismatch in early epochs.
"""

from typing import Optional
import torch
import torch.nn as nn

from config import get_settings, Settings


class WideLayer(nn.Module):
    """Masked Wide MLP layer for Apriori association rule scoring."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()

        # Wide MLP: 1 -> 16 -> ReLU -> 1
        self.fc1 = nn.Linear(1, 16)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(16, 1)

        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize FC1 with uniform weights and FC2 with zeros so training starts as Deep-only."""
        nn.init.kaiming_uniform_(self.fc1.weight, a=1)
        nn.init.zeros_(self.fc1.bias)
        nn.init.zeros_(self.fc2.weight)
        nn.init.zeros_(self.fc2.bias)

    def forward(self, log_lift: torch.Tensor) -> torch.Tensor:
        """Forward pass for dense or batched log1p(lift) tensors.

        Args:
            log_lift: Tensor of shape [..., 1] containing log1p(lift) values >= 0

        Returns:
            Tensor of scalar Wide score contributions [...] matching leading dimensions
        """
        # Presence mask: 1.0 if log_lift > 0, else 0.0
        mask = (log_lift > 0.0).to(dtype=log_lift.dtype)

        h1 = self.fc1(log_lift)  # [..., 16]
        h1_act = self.relu(h1)  # [..., 16]
        h2 = self.fc2(h1_act)  # [..., 1]

        # Apply presence mask so log_lift = 0 yields EXACT zero output despite bias
        masked_output = h2 * mask  # [..., 1]

        return masked_output.squeeze(-1)
