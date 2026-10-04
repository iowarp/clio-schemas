"""Numerical conformance shared by CLIO and the direct-store SPOTTER reader."""

from dataclasses import replace

import pytest
from pydantic import ValidationError

from clio_schemas.attention import (
    DECAYED_MAX,
    UNIFORM_MEAN,
    AttentionProfile,
    SparseAttentionRow,
    display_intensities,
    reduce_attention,
)

ROWS = [
    SparseAttentionRow(3, (0, 1), (0.2, 0.3), (0.8, 0.4), 0.5),
    SparseAttentionRow(7, (1, 2), (0.4, 0.1), (0.6, 0.9), 0.5),
]


def test_uniform_mass_and_provisional_decay_conformance() -> None:
    uniform = reduce_attention(ROWS, 4)
    assert uniform.mean_mass == pytest.approx((0.1, 0.35, 0.05, 0))
    assert sum(uniform.mean_mass) + uniform.residual == pytest.approx(1)
    decayed = reduce_attention(ROWS, 4, DECAYED_MAX)
    assert decayed.weights == pytest.approx((2 / 3, 1 / 3))
    assert decayed.scores == pytest.approx((8 / 15, 7 / 15, 0.3, 0))
    assert decayed.mean_mass == uniform.mean_mass
    assert decayed.block_score([0, 1]) == pytest.approx(8 / 15)
    assert decayed.retained_steps == (1, 2, 1, 0)
    assert display_intensities(decayed.scores, DECAYED_MAX) == pytest.approx((1, 0.875, 0.5625, 0))


def test_union_deduplicates_steps_and_source_positions_before_reducing() -> None:
    result = reduce_attention([ROWS[1], *ROWS, ROWS[0]], 4)
    assert result == reduce_attention(ROWS, 4)
    assert result.block_score([0, 1, 1]) == pytest.approx(0.45)
    with pytest.raises(ValueError, match="Conflicting"):
        reduce_attention([ROWS[0], replace(ROWS[0], residual=0.4)], 4)


def test_editable_direction_normalization_block_and_display_semantics() -> None:
    profile = AttentionProfile(**{**DECAYED_MAX.model_dump(), "direction": "reverse"})
    result = reduce_attention(ROWS, 4, profile)
    assert result.weights == pytest.approx((1 / 3, 2 / 3))
    assert result.scores == pytest.approx((4 / 15, 8 / 15, 0.6, 0))
    raw = AttentionProfile(
        **{
            **profile.model_dump(),
            "weight_normalization": "none",
            "block_reduction": "mean",
            "display_scaling": "none",
        }
    )
    raw_result = reduce_attention(ROWS, 4, raw)
    assert raw_result.block_score([0, 1]) == pytest.approx(0.6)
    assert display_intensities(raw_result.scores, raw) == raw_result.scores
    assert raw.revision != profile.revision != UNIFORM_MEAN.revision


def test_retained_zero_is_distinct_from_unretained() -> None:
    row = SparseAttentionRow(0, (0,), (0.0,), (0.0,), 1.0)
    result = reduce_attention([row], 2)
    assert result.scores == (0.0, 0.0)
    assert result.retained_steps == (1, 0)


@pytest.mark.parametrize("base", [0, -1, 1.1, float("nan"), float("inf")])
def test_profile_refuses_invalid_decay(base: float) -> None:
    with pytest.raises(ValidationError):
        AttentionProfile(decay_base=base)


@pytest.mark.parametrize(
    "row",
    [
        replace(ROWS[0], positions=(0, 0)),
        replace(ROWS[0], positions=(0, 4)),
        replace(ROWS[0], mean=(0.2,)),
        replace(ROWS[0], peak=(float("nan"), 0.2)),
        replace(ROWS[0], residual=-1),
    ],
)
def test_capture_refuses_invalid_sparse_values(row: SparseAttentionRow) -> None:
    with pytest.raises(ValueError):
        reduce_attention([row], 4)
