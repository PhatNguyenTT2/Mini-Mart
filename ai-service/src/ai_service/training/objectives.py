"""Purchase-aligned retrieval objectives for full-catalog ranking."""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class ObjectiveResult:
    loss: torch.Tensor
    rule_loss: torch.Tensor
    sampled_pair_accuracy: float
    all_negative_win_rate: float
    deep_rms: float = 0.0
    wide_rms: float = 0.0
    hybrid_rms: float = 0.0


def rule_pairwise_wide_loss(
    positive_wide_logits: torch.Tensor,
    negative_wide_logits: torch.Tensor,
    *,
    negative_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    """Wide-only pairwise loss for organic rule-positive versus rule-hard negatives."""
    if positive_wide_logits.ndim != 1 or negative_wide_logits.ndim != 2:
        raise ValueError("rule logits must have shapes [B] and [B,R]")
    if negative_wide_logits.shape[0] != positive_wide_logits.shape[0]:
        raise ValueError("rule logits batch dimensions differ")
    if negative_mask is None:
        negative_mask = torch.ones_like(negative_wide_logits, dtype=torch.bool)
    if negative_mask.shape != negative_wide_logits.shape:
        raise ValueError("rule negative mask shape differs from logits")
    if not bool(negative_mask.any()):
        return positive_wide_logits.sum() * 0.0
    margins = positive_wide_logits[:, None] - negative_wide_logits
    return -torch.nn.functional.logsigmoid(margins.masked_select(negative_mask)).mean()


def multi_positive_sampled_softmax(
    user_vectors: torch.Tensor,
    positive_item_vectors: torch.Tensor,
    explicit_negative_vectors: torch.Tensor,
    *,
    positive_mask: torch.Tensor,
    denominator_mask: torch.Tensor,
    confidence: torch.Tensor,
    temperature: torch.Tensor,
    in_batch_wide_logits: torch.Tensor,
    explicit_wide_logits: torch.Tensor,
    rule_positive_mask: torch.Tensor | None = None,
    rule_negative_mask: torch.Tensor | None = None,
    rule_weight: float = 0.0,
) -> ObjectiveResult:
    """InfoNCE with multi-positive labels, hard negatives, and Wide logits."""
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
    explicit_deep = (
        torch.einsum("bd,brd->br", user_vectors, explicit_negative_vectors) / temperature
    )
    if in_batch_wide_logits.shape != (batch, batch):
        raise ValueError("in_batch_wide_logits must have shape [B,B]")
    if explicit_wide_logits.shape != explicit_deep.shape:
        raise ValueError("explicit_wide_logits shape differs from explicit deep logits")
    in_batch = in_batch_deep + in_batch_wide_logits
    explicit = explicit_deep + explicit_wide_logits
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

        deep_rms = float(torch.sqrt(torch.mean(in_batch_deep**2)).cpu())
        wide_rms = float(torch.sqrt(torch.mean(in_batch_wide_logits**2)).cpu())
        hybrid_rms = float(torch.sqrt(torch.mean(in_batch**2)).cpu())

    rule_loss = loss.detach() * 0.0
    if rule_weight > 0.0:
        if rule_positive_mask is None or rule_positive_mask.shape != (batch, batch):
            raise ValueError("rule_positive_mask must have shape [B,B]")
        positive_wide = in_batch_wide_logits.diagonal()
        positive_rows = rule_positive_mask.diagonal()
        if not bool(positive_rows.any()):
            return ObjectiveResult(
                loss=loss,
                rule_loss=rule_loss,
                sampled_pair_accuracy=pair_accuracy,
                all_negative_win_rate=all_win,
                deep_rms=deep_rms,
                wide_rms=wide_rms,
                hybrid_rms=hybrid_rms,
            )
        selected_negative_mask = (
            rule_negative_mask
            if rule_negative_mask is not None
            else torch.ones_like(explicit_wide_logits, dtype=torch.bool)
        )
        rule_loss = rule_pairwise_wide_loss(
            positive_wide[positive_rows],
            explicit_wide_logits[positive_rows],
            negative_mask=selected_negative_mask[positive_rows],
        )
        loss = loss + float(rule_weight) * rule_loss

    return ObjectiveResult(
        loss=loss,
        rule_loss=rule_loss,
        sampled_pair_accuracy=pair_accuracy,
        all_negative_win_rate=all_win,
        deep_rms=deep_rms,
        wide_rms=wide_rms,
        hybrid_rms=hybrid_rms,
    )
