"""Purchase-aligned retrieval objectives for full-catalog ranking."""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class ObjectiveResult:
    loss: torch.Tensor
    sampled_pair_accuracy: float
    all_negative_win_rate: float
    deep_rms: float = 0.0
    wide_rms: float = 0.0
    hybrid_rms: float = 0.0


def multi_positive_sampled_softmax(
    user_vectors: torch.Tensor,
    positive_item_vectors: torch.Tensor,
    explicit_negative_vectors: torch.Tensor,
    *,
    positive_mask: torch.Tensor,
    denominator_mask: torch.Tensor,
    confidence: torch.Tensor,
    temperature: torch.Tensor,
    in_batch_wide_logits: torch.Tensor | None = None,
    explicit_wide_logits: torch.Tensor | None = None,
) -> ObjectiveResult:
    """InfoNCE with multi-positive in-batch labels, row-specific hard negatives, and joint Wide logits."""
    if user_vectors.ndim != 2 or positive_item_vectors.shape != user_vectors.shape:
        raise ValueError("user and positive item vectors must share shape [B,D]")
    batch, dimension = user_vectors.shape
    if explicit_negative_vectors.ndim != 3 or explicit_negative_vectors.shape[:1] != (batch,):
        raise ValueError("explicit negatives must have shape [B,R,D]")
    if explicit_negative_vectors.shape[2] != dimension:
        raise ValueError("explicit negative dimension differs from the towers")
    if positive_mask.shape != (batch, batch) or denominator_mask.shape != (batch, batch):
        raise ValueError("in-batch masks must have shape [B,B]")
    if confidence.shape != (batch,) or not bool((confidence > 0).all()):
        raise ValueError("confidence must be positive [B]")
    if temperature.numel() != 1 or not bool(torch.isfinite(temperature)):
        raise ValueError("temperature must be one finite scalar")
    in_batch_deep = torch.matmul(user_vectors, positive_item_vectors.T) / temperature
    explicit_deep = torch.einsum("bd,brd->br", user_vectors, explicit_negative_vectors) / temperature
    if in_batch_wide_logits is not None:
        if in_batch_wide_logits.shape != (batch, batch):
            raise ValueError("in_batch_wide_logits must have shape [B,B]")
        in_batch = in_batch_deep + in_batch_wide_logits
    else:
        in_batch_wide_logits = torch.zeros_like(in_batch_deep)
        in_batch = in_batch_deep
    if explicit_wide_logits is not None:
        if explicit_wide_logits.shape != explicit_deep.shape:
            raise ValueError("explicit_wide_logits shape differs from explicit deep logits")
        explicit = explicit_deep + explicit_wide_logits
    else:
        explicit_wide_logits = torch.zeros_like(explicit_deep)
        explicit = explicit_deep
    valid_denominator = denominator_mask | positive_mask
    if not bool(positive_mask.any(dim=1).all()):
        raise ValueError("every row requires at least one positive")
    numerator = torch.logsumexp(in_batch.masked_fill(~positive_mask, -torch.inf), dim=1)
    combined = torch.cat((in_batch.masked_fill(~valid_denominator, -torch.inf), explicit), dim=1)
    per_sample = torch.logsumexp(combined, dim=1) - numerator
    loss = (per_sample * confidence).sum() / confidence.sum()
    if not bool(torch.isfinite(loss)):
        raise ValueError("sampled softmax loss is not finite")

    with torch.no_grad():
        target_scores = in_batch.diagonal()
        in_batch_negative = in_batch.masked_fill(positive_mask | ~denominator_mask, -torch.inf)
        negatives = torch.cat((in_batch_negative, explicit), dim=1)
        comparisons = target_scores[:, None] > negatives
        valid = torch.isfinite(negatives)
        pair_accuracy = float(comparisons[valid].float().mean()) if bool(valid.any()) else 1.0
        row_wins = torch.where(valid, comparisons, torch.ones_like(comparisons)).all(dim=1)
        all_win = float(row_wins.float().mean())

        deep_rms = float(torch.sqrt(torch.mean(in_batch_deep ** 2)).cpu())
        wide_rms = float(torch.sqrt(torch.mean(in_batch_wide_logits ** 2)).cpu())
        hybrid_rms = float(torch.sqrt(torch.mean(in_batch ** 2)).cpu())

    return ObjectiveResult(
        loss=loss,
        sampled_pair_accuracy=pair_accuracy,
        all_negative_win_rate=all_win,
        deep_rms=deep_rms,
        wide_rms=wide_rms,
        hybrid_rms=hybrid_rms,
    )
