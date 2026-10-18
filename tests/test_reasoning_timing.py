"""Optional reasoning timing is canonical, bounded, and backward compatible."""

import math

import pytest
from pydantic import ValidationError

from clio_schemas.gact_v3 import MessageBlock


def test_reasoning_timing_round_trips_without_requiring_old_records_to_have_it() -> None:
    old = {"id": "r", "type": "reasoning", "text": "Inspecting the file."}
    assert MessageBlock.model_validate(old).model_dump(exclude_none=True) == old
    timed = {
        **old,
        "started_at": "2026-10-15T00:00:00Z",
        "completed_at": "2026-10-15T00:00:12Z",
        "duration_ms": 12_000.0,
    }
    assert MessageBlock.model_validate(timed).model_dump(exclude_none=True) == timed


@pytest.mark.parametrize("duration", [-1.0, math.inf, math.nan, "12"])
def test_reasoning_duration_rejects_negative_nonfinite_or_text_values(duration: object) -> None:
    with pytest.raises(ValidationError):
        MessageBlock.model_validate(
            {"id": "r", "type": "reasoning", "text": "Thinking", "duration_ms": duration}
        )
