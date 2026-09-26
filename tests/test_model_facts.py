"""ModelFacts: descriptive model facts with evidence, slider-friendly, null when unstated."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from pydantic import ValidationError

from clio_schemas import ModelFacts

_EVIDENCE = [{"source": "openrouter", "detail": "openrouter created=1776747900", "observed_at": ""}]


def _record() -> dict[str, Any]:
    """The shape clio-agent serves as a catalog row's ``model_facts``."""
    return {
        "model_key": "qwen/qwen3.6-35b-a3b",
        "description": {
            "value": {
                "text": "Ranked by [Artificial Analysis](https://artificialanalysis.ai/).",
                "plain": "Ranked by Artificial Analysis.",
                "links": [{"text": "Artificial Analysis", "url": "https://artificialanalysis.ai/"}],
            },
            "evidence": [
                {"source": "openrouter", "detail": "openrouter description", "observed_at": ""}
            ],
        },
        "released_at": {"value": {"date": "2026-04-21", "precision": "day"}, "evidence": _EVIDENCE},
        "recent": {"value": True, "window_months": 6, "as_of": "2026-09-26", "evidence": _EVIDENCE},
        "pricing": {
            "value": {
                "unit": "usd_per_1m_tokens",
                "input": {"kind": "usd", "per_1m": 0.15},
                "output": {"kind": "usd", "per_1m": 1.5},
            },
            "evidence": [
                {"source": "server_report", "detail": "openrouter pricing", "observed_at": ""}
            ],
            "alternatives": [
                {
                    "value": {
                        "unit": "usd_per_1m_tokens",
                        "input": {"kind": "usd", "per_1m": 0.2},
                        "output": {"kind": "usd", "per_1m": 2.0},
                    },
                    "evidence": [
                        {"source": "litellm", "detail": "litellm list price", "observed_at": ""}
                    ],
                }
            ],
        },
        "parameters": {
            "value": {
                "total": 35951822704,
                "active": None,
                "experts_total": 256,
                "experts_active": 8,
                "precision": "exact",
            },
            "evidence": [{"source": "hf_repo", "detail": "safetensors.total", "observed_at": ""}],
        },
    }


def test_the_served_shape_validates() -> None:
    facts = ModelFacts.model_validate(_record())
    assert facts.parameters is not None and facts.parameters.value.total == 35951822704
    assert facts.pricing is not None and facts.pricing.value.input.per_1m == 0.15


def test_every_fact_may_be_null_when_no_source_states_it() -> None:
    record = {
        "model_key": "m",
        "description": None,
        "released_at": None,
        "recent": None,
        "pricing": None,
        "parameters": None,
    }
    assert ModelFacts.model_validate(record).parameters is None


@pytest.mark.parametrize("kind", ["variable", "subscription"])
def test_a_non_metered_price_has_no_number(kind: str) -> None:
    record = _record()
    record["pricing"]["value"]["input"] = {"kind": kind, "per_1m": None}
    ModelFacts.model_validate(record)
    record["pricing"]["value"]["input"] = {"kind": kind, "per_1m": 0.0}
    with pytest.raises(ValidationError):
        ModelFacts.model_validate(record)


def test_a_metered_price_needs_a_non_negative_number() -> None:
    record = _record()
    record["pricing"]["value"]["output"] = {"kind": "usd", "per_1m": None}
    with pytest.raises(ValidationError):
        ModelFacts.model_validate(record)


def test_release_precision_must_match_the_date() -> None:
    record = _record()
    record["released_at"]["value"] = {"date": "2026-02", "precision": "month"}
    ModelFacts.model_validate(record)
    record["released_at"]["value"] = {"date": "2026-02", "precision": "day"}
    with pytest.raises(ValidationError):
        ModelFacts.model_validate(record)


def test_recent_without_a_release_date_is_refused() -> None:
    record = _record()
    record["released_at"] = None
    with pytest.raises(ValidationError):
        ModelFacts.model_validate(record)


def test_a_fact_needs_evidence_and_parameters_must_state_a_count() -> None:
    record = _record()
    record["parameters"]["evidence"] = []
    with pytest.raises(ValidationError):
        ModelFacts.model_validate(record)
    record = _record()
    record["parameters"]["value"].update(total=None, experts_total=None, experts_active=None)
    with pytest.raises(ValidationError):
        ModelFacts.model_validate(record)


def test_unknown_keys_are_refused() -> None:
    record = copy.deepcopy(_record())
    record["parameters"]["value"]["guessed_from_name"] = 35
    with pytest.raises(ValidationError):
        ModelFacts.model_validate(record)
