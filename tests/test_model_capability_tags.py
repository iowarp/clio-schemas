"""Conformance tests for the model-capability tag vocabulary (``ModelCapabilityTags``).

Pydantic-level and JSON-Schema-level: every accept/reject case below is run
through the strict model AND the committed ``model_capability_tags.json``
(Draft 2020-12), so the wire contract a TypeScript/Zod consumer generates from
cannot drift from the Python one.
"""

from __future__ import annotations

import json
from typing import Any

import jsonschema
import pytest
from pydantic import ValidationError

from clio_schemas import ModelCapabilityTags
from clio_schemas.export import package_schema_dir
from clio_schemas.model_capabilities import (
    HF_PIPELINE_TAGS,
    TaskTag,
    role_for_model_type,
)

OBSERVED = "2026-09-26T00:00:00+00:00"


def _ev(source: str = "openrouter", detail: str = "architecture.output_modalities") -> dict:
    return {"source": source, "detail": detail, "observed_at": OBSERVED}


def _tag(value: Any, source: str = "openrouter") -> dict:
    return {"value": value, "evidence": [_ev(source)]}


def _schema() -> dict:
    return json.loads((package_schema_dir() / "model_capability_tags.json").read_text("utf-8"))


def _schema_valid(payload: dict) -> bool:
    validator = jsonschema.Draft202012Validator(_schema())
    return not list(validator.iter_errors(payload))


JEV_LATEST = {
    "model_key": "~typesafe/jev-latest",
    "model_type": _tag("classification"),
    "role": _tag("surrogate"),
    "tasks": [_tag("text-classification")],
    "input_modalities": [_tag("text")],
    "output_modalities": [_tag("scores")],
    "free": _tag(False, "server_report"),
    "router": _tag(False, "server_report"),
}

IMAGE_GENERATOR = {
    "model_key": "black-forest-labs/flux-2",
    "model_type": _tag("image_generation"),
    "role": _tag("surrogate"),
    "tasks": [_tag("text-to-image")],
    "input_modalities": [_tag("text"), _tag("image")],
    "output_modalities": [_tag("image")],
}

SAM3 = {
    "model_key": "sam3",
    "model_type": _tag("segmentation", "server_report"),
    "role": _tag("surrogate", "server_report"),
    "tasks": [_tag("mask-generation", "server_report")],
}

WEATHER_SURROGATE = {
    "model_key": "microsoft/aurora",
    "model_type": _tag("scientific_surrogate", "overlay"),
    "role": _tag("surrogate", "overlay"),
    "tasks": [_tag("clio:weather-emulation", "overlay")],
    "output_modalities": [_tag("tensor", "overlay")],
    "domains": [_tag("climate", "overlay")],
}

CHAT = {
    "model_key": "google/gemma-4-31B-it",
    "model_type": _tag("chat", "overlay"),
    "role": _tag("general", "overlay"),
    "tasks": [_tag("image-text-to-text", "hf_repo")],
    "input_modalities": [_tag("text"), _tag("image"), _tag("video")],
    "output_modalities": [_tag("text")],
    "capabilities": [_tag("tool_calling"), _tag("reasoning"), _tag("structured_output")],
}

ACCEPT = {
    "jev-latest": JEV_LATEST,
    "image-generator": IMAGE_GENERATOR,
    "sam3": SAM3,
    "weather-surrogate": WEATHER_SURROGATE,
    "chat": CHAT,
    "nothing-known": {"model_key": "allenai/Llama-3.1-Tulu-3-405B"},
    "several-sources": {
        "model_key": "m",
        "input_modalities": [
            {"value": "image", "evidence": [_ev("overlay"), _ev("hf_repo", "pipeline_tag")]}
        ],
    },
}


def _with(base: dict, **changes: Any) -> dict:
    return {**base, **changes}


REJECT = {
    "unknown-key": _with(JEV_LATEST, guessed=True),
    "empty-model-key": _with(JEV_LATEST, model_key=""),
    "tag-without-evidence": _with(
        JEV_LATEST, model_type={"value": "classification", "evidence": []}
    ),
    "unknown-evidence-source": _with(JEV_LATEST, model_type=_tag("classification", "unknown")),
    "unknown-modality": _with(JEV_LATEST, input_modalities=[_tag("file")]),
    "unknown-model-type": _with(JEV_LATEST, model_type=_tag("classifier"), role=None),
    "unknown-capability": _with(CHAT, capabilities=[_tag("long_context")]),
    "unknown-domain": _with(WEATHER_SURROGATE, domains=[_tag("weather")]),
    "task-not-a-hub-id": _with(JEV_LATEST, tasks=[_tag("classification")]),
    "task-bad-clio-id": _with(WEATHER_SURROGATE, tasks=[_tag("clio:Weather_Emulation", "overlay")]),
    "string-flag": _with(JEV_LATEST, free=_tag("true")),
    "evidence-extra-key": _with(
        JEV_LATEST,
        model_type={"value": "classification", "evidence": [{**_ev(), "raw": "decisions"}]},
    ),
}


@pytest.mark.parametrize("name", sorted(ACCEPT))
def test_accepts(name: str) -> None:
    payload = ACCEPT[name]
    record = ModelCapabilityTags.model_validate(payload)
    assert record.model_dump(mode="json", exclude_defaults=True) == payload
    assert _schema_valid(payload), name
    assert ModelCapabilityTags.model_validate_json(json.dumps(payload)) == record


@pytest.mark.parametrize("name", sorted(REJECT))
def test_rejects_in_both_python_and_json_schema(name: str) -> None:
    payload = REJECT[name]
    with pytest.raises(ValidationError):
        ModelCapabilityTags.model_validate(payload)
    assert not _schema_valid(payload), name


def test_role_must_agree_with_model_type() -> None:
    """A classifier is never a general model (Python-level invariant)."""

    with pytest.raises(ValidationError, match="contradicts model_type"):
        ModelCapabilityTags.model_validate(_with(JEV_LATEST, role=_tag("general")))
    with pytest.raises(ValidationError, match="contradicts model_type"):
        ModelCapabilityTags.model_validate(_with(CHAT, role=_tag("surrogate", "overlay")))


@pytest.mark.parametrize(
    "field", ["tasks", "input_modalities", "output_modalities", "capabilities"]
)
def test_a_list_axis_never_repeats_a_value(field: str) -> None:
    value = {
        "tasks": "text-generation",
        "input_modalities": "text",
        "output_modalities": "text",
        "capabilities": "reasoning",
    }[field]
    with pytest.raises(ValidationError, match="repeats a value"):
        ModelCapabilityTags.model_validate({"model_key": "m", field: [_tag(value), _tag(value)]})


def test_records_are_frozen() -> None:
    record = ModelCapabilityTags.model_validate(JEV_LATEST)
    with pytest.raises(ValidationError):
        record.model_key = "other"  # type: ignore[misc]


def test_every_hub_pipeline_tag_is_a_valid_task() -> None:
    assert len(HF_PIPELINE_TAGS) == 57
    assert len(set(HF_PIPELINE_TAGS)) == 57
    for tag in HF_PIPELINE_TAGS:
        TaskTag.model_validate(_tag(tag))


def test_role_for_model_type() -> None:
    assert role_for_model_type("chat") == "general"
    for model_type in ("classification", "image_generation", "embedding", "segmentation"):
        assert role_for_model_type(model_type) == "surrogate"
