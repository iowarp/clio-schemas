"""Versioned attention profiles and a transport-independent sparse reducer.

CLIO REST and direct-store reviewers use this implementation. No tokenizer,
filesystem, network or model dependency is needed to recompute a captured view.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AttentionProfile(BaseModel):
    """Resolved, immutable assumptions for one selected item's heat display."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    name: str = Field(default="uniform-mean", min_length=1, max_length=100)
    version: Literal[1] = 1
    metric: Literal["mean", "max"] = "mean"
    weighting: Literal["uniform", "exponential"] = "uniform"
    decay_base: float = Field(default=0.5, gt=0, le=1, allow_inf_nan=False)
    direction: Literal["forward", "reverse"] = "forward"
    weight_normalization: Literal["sum", "none"] = "sum"
    block_reduction: Literal["sum", "mean", "max"] = "sum"
    display_scaling: Literal["max", "none"] = "max"
    content_steps: Literal["all_selected_captured_steps"] = "all_selected_captured_steps"

    @property
    def revision(self) -> str:
        """Hash every resolved assumption, independent of serialization order."""
        encoded = json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()


UNIFORM_MEAN = AttentionProfile()
DECAYED_MAX = AttentionProfile(
    name="decayed-max", metric="max", weighting="exponential", block_reduction="max"
)


@dataclass(frozen=True)
class SparseAttentionRow:
    """One captured decode step, in a single request's prompt coordinate space."""

    step: int
    positions: tuple[int, ...]
    mean: tuple[float, ...]
    peak: tuple[float, ...]
    residual: float


@dataclass(frozen=True)
class AttentionReduction:
    """Observed heat, coverage and independent uniform mean-mass accounting."""

    scores: tuple[float, ...]
    mean_mass: tuple[float, ...]
    retained_steps: tuple[int, ...]
    residual: float
    steps: tuple[int, ...]
    weights: tuple[float, ...]
    profile: AttentionProfile

    def block_score(self, positions: Iterable[int]) -> float:
        """Reduce unique source positions; unretained positions remain unobserved."""
        indices = sorted(set(positions))
        if any(index < 0 or index >= len(self.scores) for index in indices):
            raise ValueError("Source positions lie outside this request's prompt")
        values = [self.scores[index] for index in indices]
        if not values:
            return 0.0
        if self.profile.block_reduction == "max":
            return max(values)
        total = math.fsum(values)
        return total / len(indices) if self.profile.block_reduction == "mean" else total


def _validate_row(row: SparseAttentionRow, total: int) -> None:
    if row.step < 0 or len(row.positions) != len(row.mean) or len(row.mean) != len(row.peak):
        raise ValueError("Malformed sparse attention row")
    if len(set(row.positions)) != len(row.positions):
        raise ValueError("A decode row repeats a prompt position")
    if any(position < 0 or position >= total for position in row.positions):
        raise ValueError("Captured positions lie outside this request's prompt")
    if any(not math.isfinite(value) or value < 0 for value in (*row.mean, *row.peak, row.residual)):
        raise ValueError("Captured attention must be finite and nonnegative")


def reduce_attention(
    rows: Iterable[SparseAttentionRow],
    prompt_tokens: int,
    profile: AttentionProfile = UNIFORM_MEAN,
) -> AttentionReduction:
    """Combine unique output steps before reducing source blocks.

    Repeated identical rows (overlapping selections) count once. Conflicting rows
    for the same step are refused. The caller must keep separate LM requests in
    separate reductions. Zero observed score does not imply measured zero: consult
    ``retained_steps``. Mass and residual always use uniform mean accounting.
    """
    if prompt_tokens < 1:
        raise ValueError("A capture must contain prompt tokens")
    unique: dict[int, SparseAttentionRow] = {}
    for row in rows:
        _validate_row(row, prompt_tokens)
        if row.step in unique and unique[row.step] != row:
            raise ValueError("Conflicting captures for one decode step")
        unique[row.step] = row
    ordered = [unique[index] for index in sorted(unique)]
    if not ordered:
        raise ValueError("Select at least one captured decode step")
    ranks = range(len(ordered))
    if profile.direction == "reverse":
        ranks = range(len(ordered) - 1, -1, -1)
    weights = [
        profile.decay_base**rank if profile.weighting == "exponential" else 1.0 for rank in ranks
    ]
    if profile.weight_normalization == "sum":
        denominator = math.fsum(weights)
        weights = [weight / denominator for weight in weights]
    scores, mass = [0.0] * prompt_tokens, [0.0] * prompt_tokens
    observed = [0] * prompt_tokens
    for row, weight in zip(ordered, weights, strict=True):
        values = row.mean if profile.metric == "mean" else row.peak
        for position, value, mean in zip(row.positions, values, row.mean, strict=True):
            scores[position] += weight * value
            mass[position] += mean / len(ordered)
            observed[position] += 1
    return AttentionReduction(
        tuple(scores),
        tuple(mass),
        tuple(observed),
        math.fsum(row.residual for row in ordered) / len(ordered),
        tuple(row.step for row in ordered),
        tuple(weights),
        profile,
    )


def display_intensities(scores: Sequence[float], profile: AttentionProfile) -> tuple[float, ...]:
    """Scale one item's displayed source set, never labeling maxima as mass."""
    denominator = max(scores, default=0.0) if profile.display_scaling == "max" else 1.0
    return tuple(value / denominator if denominator else 0.0 for value in scores)
