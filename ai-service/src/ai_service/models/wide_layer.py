"""Masked Wide MLP Layer module for Apriori lift score processing."""

from typing import Optional
import torch
import torch.nn as nn

from ai_service.config import Settings


class WideLayer(nn.Module):
    """Masked Wide MLP layer for Apriori association rule scoring."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()

        self.fc1 = nn.Linear(1, 16)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(16, 1)

        self._init_weights()

    def _init_weights(self) -> None:
        """Zero-initialize FC2 weights so training starts as Deep-only."""
        nn.init.kaiming_uniform_(self.fc1.weight, a=1)
        nn.init.zeros_(self.fc1.bias)
        nn.init.zeros_(self.fc2.weight)
        nn.init.zeros_(self.fc2.bias)

    def forward(self, log_lift: torch.Tensor, context_present: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Forward pass for log1p(lift) inputs.
        
        Args:
            log_lift: Tensor [..., 1] containing log1p(lift) >= 0
            context_present: Optional boolean mask [B] indicating context validity
        """
        # Presence mask based on positive lift value
        mask = (log_lift > 0.0).to(dtype=log_lift.dtype)

        h1 = self.fc1(log_lift)   # [..., 16]
        h1_act = self.relu(h1)   # [..., 16]
        h2 = self.fc2(h1_act)   # [..., 1]

        masked_output = h2 * mask # [..., 1]
        out = masked_output.squeeze(-1)

        if context_present is not None:
            if context_present.dim() < out.dim():
                # Broadcast context_present across candidate dimension if necessary
                ctx_mask = context_present.unsqueeze(-1).to(dtype=out.dtype)
                out = out * ctx_mask
            else:
                out = out * context_present.to(dtype=out.dtype)

        return out
