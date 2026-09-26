"""AcceptedParameter: one request setting a model accepts, how to enter it, and who says so."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from clio_schemas import AcceptedParameter


def _temperature() -> dict[str, Any]:
    """The shape clio-agent serves in a catalog row's ``accepted_parameters``."""
    return {
        "name": "temperature",
        "label": "Temperature",
        "description": "Higher values make replies more varied; lower values more focused.",
        "group": "sampling",
        "kind": "number",
        "minimum": 0.0,
        "maximum": 2.0,
        "step": 0.05,
        "default": 0.6,
        "evidence": [
            {
                "source": "openrouter",
                "detail": "openrouter supported_parameters (temperature)",
                "observed_at": "2026-09-26T00:00:00+00:00",
            },
            {"source": "dialect", "detail": "OpenAI API reference: 0 to 2", "observed_at": ""},
            {"source": "overlay", "detail": "recommended sampling (instruct)", "observed_at": ""},
        ],
    }


def _enum() -> dict[str, Any]:
    return {
        "name": "verbosity",
        "label": "Verbosity",
        "description": "How long replies run.",
        "group": "length",
        "kind": "enum",
        "minimum": None,
        "maximum": None,
        "step": None,
        "options": ["low", "medium", "high"],
        "default": None,
        "evidence": [{"source": "dialect", "detail": "text.verbosity", "observed_at": ""}],
    }


def test_the_served_shape_validates() -> None:
    parameter = AcceptedParameter.model_validate(_temperature())
    assert parameter.options == []
    assert parameter.default == 0.6


def test_an_unbounded_integer_with_the_provider_default() -> None:
    record = _temperature() | {
        "name": "seed",
        "label": "Seed",
        "group": "advanced",
        "kind": "integer",
        "minimum": 0.0,
        "maximum": None,
        "step": 1.0,
        "default": None,
    }
    assert AcceptedParameter.model_validate(record).maximum is None


def test_an_enum_lists_options_and_has_no_range() -> None:
    AcceptedParameter.model_validate(_enum())
    with pytest.raises(ValidationError):
        AcceptedParameter.model_validate(_enum() | {"options": []})
    with pytest.raises(ValidationError):
        AcceptedParameter.model_validate(_enum() | {"minimum": 0.0})
    with pytest.raises(ValidationError):
        AcceptedParameter.model_validate(_enum() | {"default": "extreme"})
    AcceptedParameter.model_validate(_enum() | {"default": "medium"})


def test_a_number_has_no_options_and_a_numeric_default_in_range() -> None:
    with pytest.raises(ValidationError):
        AcceptedParameter.model_validate(_temperature() | {"options": ["hot"]})
    with pytest.raises(ValidationError):
        AcceptedParameter.model_validate(_temperature() | {"default": "hot"})
    with pytest.raises(ValidationError):
        AcceptedParameter.model_validate(_temperature() | {"default": 2.5})
    with pytest.raises(ValidationError):
        AcceptedParameter.model_validate(_temperature() | {"minimum": 3.0})


def test_an_integer_default_is_whole() -> None:
    record = _temperature() | {"kind": "integer", "step": 1.0, "default": 1.5}
    with pytest.raises(ValidationError):
        AcceptedParameter.model_validate(record)


def test_evidence_is_required_and_unknown_keys_are_refused() -> None:
    with pytest.raises(ValidationError):
        AcceptedParameter.model_validate(_temperature() | {"evidence": []})
    with pytest.raises(ValidationError):
        AcceptedParameter.model_validate(_temperature() | {"guessed": True})
    with pytest.raises(ValidationError):
        AcceptedParameter.model_validate(_temperature() | {"name": "Top-P"})
