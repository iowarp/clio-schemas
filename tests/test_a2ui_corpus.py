"""Pure-Python port of the upstream A2UI 0.9.1 corpus runner.

Reproduces ``tests/a2ui_corpus/v0_9_1/run_tests.py`` semantics on top of
``jsonschema`` + ``referencing`` instead of shelling out to ``ajv``:

- ``cases/*.json`` suites: each has a ``schema`` (one of the four upstream
  target schemas) and a list of ``tests``, each with ``data`` and an expected
  ``valid`` flag (defaulting to ``True``, matching the upstream runner).
- ``contact_form_example.jsonl``: every line is one ``server_to_client.json``
  message, all expected valid.
- ``examples/*.json``: each has a ``messages`` array, every message expected
  valid against ``server_to_client.json``.

All of the above validate against the vendored Basic catalog, exactly like
upstream's ``setup_catalog_alias`` (this repo's
:func:`clio_schemas.a2ui.validation.message_validator` does the same
aliasing internally). The CLIO workspace catalog is exercised separately,
through the *same* ``catalog_validators``/``message_validator`` machinery,
using representative payloads from the former
``tests/test_gact_a2ui_vocabularies.py`` component-shape coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from clio_schemas.a2ui.catalog_export import render_workspace_catalog
from clio_schemas.a2ui.chart_spec import MAX_INLINE_ROWS, PRESET_NAMES, load_preset
from clio_schemas.a2ui.v0_9_1.bounded_components import COMPONENT_MODELS, ChartComponent
from clio_schemas.a2ui.v0_9_1.components import (
    SelectionState,
    TextComponent,
    TextFieldComponent,
)
from clio_schemas.a2ui.validation import catalog_validators, message_validator

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = REPO_ROOT / "tests" / "a2ui_corpus" / "v0_9_1"
PACKAGE_DATA_ROOT = REPO_ROOT / "src" / "clio_schemas" / "schemas" / "a2ui" / "v0_9_1"

BASIC_CATALOG: dict[str, Any] = json.loads(
    (PACKAGE_DATA_ROOT / "catalogs" / "basic" / "catalog.json").read_text(encoding="utf-8")
)
WORKSPACE_CATALOG: dict[str, Any] = render_workspace_catalog()

# Suite files: every tests/a2ui_corpus/v0_9_1/*.json that carries a "schema" +
# "tests" pair (excludes SOURCE.json, README.md, run_tests.py, contact_form_example_test.json
# uses the same shape too and IS included).
_CASE_SUITE_FILES = sorted(
    path for path in CORPUS_ROOT.glob("*.json") if path.name != "SOURCE.json"
)


def _iter_case_params() -> list[Any]:
    params = []
    for path in _CASE_SUITE_FILES:
        suite = json.loads(path.read_text(encoding="utf-8"))
        schema_name = suite["schema"]
        for index, case in enumerate(suite["tests"]):
            description = case.get("description", f"case_{index}")
            params.append(
                pytest.param(
                    schema_name,
                    case["data"],
                    case.get("valid", True),
                    id=f"{path.stem}::{index}::{description}",
                )
            )
    return params


CASE_PARAMS = _iter_case_params()


@pytest.mark.parametrize(("schema_name", "data", "expect_valid"), CASE_PARAMS)
def test_corpus_case(schema_name: str, data: Any, expect_valid: bool) -> None:  # noqa: FBT001
    """Every vendored ``cases/*.json`` test validates as the upstream suite expects."""

    validator = message_validator(schema_name, catalog=BASIC_CATALOG)
    assert validator.is_valid(data) == expect_valid


def _read_jsonl_messages(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


JSONL_MESSAGES = _read_jsonl_messages(CORPUS_ROOT / "contact_form_example.jsonl")


@pytest.mark.parametrize(
    "message", JSONL_MESSAGES, ids=[f"line_{i}" for i in range(len(JSONL_MESSAGES))]
)
def test_contact_form_jsonl_line_is_valid(message: dict[str, Any]) -> None:
    """Every line of the vendored contact-form JSONL example validates."""

    validator = message_validator("server_to_client.json", catalog=BASIC_CATALOG)
    validator.validate(message)


EXAMPLE_FILES = sorted((CORPUS_ROOT / "examples").glob("*.json"))


@pytest.mark.parametrize("example_path", EXAMPLE_FILES, ids=lambda p: p.name)
def test_example_messages_validate_against_basic_catalog(example_path: Path) -> None:
    """All 43 vendored gallery examples validate against the Basic catalog."""

    payload = json.loads(example_path.read_text(encoding="utf-8"))
    validator = message_validator("server_to_client.json", catalog=BASIC_CATALOG)
    for message in payload["messages"]:
        validator.validate(message)


def test_examples_directory_is_fully_covered() -> None:
    assert len(EXAMPLE_FILES) == 43


# --------------------------------------------------------------------------- #
# Protocol-level open/closed behaviour (issue exit-gate assertions)
# --------------------------------------------------------------------------- #
def test_open_action_name_validates() -> None:
    """``action.name`` is any string — a CLIO-specific name is not special-cased."""

    validator = message_validator("client_to_server.json")
    validator.validate(
        {
            "version": "v0.9.1",
            "action": {
                "name": "earthscope.stations.selected",
                "surfaceId": "s",
                "sourceComponentId": "c",
                "timestamp": "2026-01-01T00:00:00Z",
                "context": {},
            },
        }
    )


def test_validation_failed_error_validates() -> None:
    validator = message_validator("client_to_server.json")
    validator.validate(
        {
            "version": "v0.9.1",
            "error": {
                "code": "VALIDATION_FAILED",
                "surfaceId": "s",
                "path": "/components/0",
                "message": "m",
            },
        }
    )


def test_three_key_client_envelope_is_rejected() -> None:
    """``action`` and ``error`` are mutually exclusive; both together is invalid."""

    validator = message_validator("client_to_server.json")
    assert not validator.is_valid(
        {
            "version": "v0.9.1",
            "action": {
                "name": "x",
                "surfaceId": "s",
                "sourceComponentId": "c",
                "timestamp": "2026-01-01T00:00:00Z",
                "context": {},
            },
            "error": {"code": "boom", "surfaceId": "s", "message": "m"},
        }
    )


def test_server_to_client_requires_a_catalog() -> None:
    """A validator that cannot resolve catalog.json must raise, never skip."""

    with pytest.raises(ValueError, match="catalog"):
        message_validator("server_to_client.json")


# --------------------------------------------------------------------------- #
# CLIO workspace catalog: the SAME runner, against the SAME representative
# payloads the former A2UIComponent-union tests covered.
# --------------------------------------------------------------------------- #
WORKSPACE_VALIDATORS = catalog_validators(WORKSPACE_CATALOG)

CLIO_ACCEPT_CASES: list[Any] = [
    pytest.param(
        {
            "id": "text_1",
            "component": "Text",
            "text": {"path": "/summary"},
            "accessibility": {"label": {"path": "/summaryLabel"}},
        },
        id="Text-dynamic-binding",
    ),
    pytest.param(
        {
            "id": "button_1",
            "component": "Button",
            "child": "text_1",
            "action": {
                "event": {"name": "agent.submit", "context": {"prompt": {"path": "/prompt"}}}
            },
        },
        id="Button-event-action",
    ),
    pytest.param(
        {
            "id": "vp_1",
            "component": "clio.mesh-viewport.v1",
            "title": "Baseline",
            "meshUri": "artifact://artifact_abc123",
            "field": "S_MISES",
            "showField": {"path": "/showStress"},
            "syncGroup": "compare",
            "upAxis": "y",
        },
        id="MeshViewport-bound-field-toggle",
    ),
    pytest.param(
        {
            "id": "vp_2",
            "component": "clio.mesh-viewport.v1",
            "meshUri": "artifact://artifact_design",
            "field": "DENSITY",
            "frame": {"path": "/cycle"},
            "thresholdField": "DENSITY",
            "thresholdMin": {"path": "/iso"},
            "thresholdMax": 1,
            "camera": {"path": "/camera"},
        },
        id="MeshViewport-threshold-frames-camera",
    ),
    pytest.param(
        {
            "id": "iso",
            "component": "clio.slider.v1",
            "label": "Density threshold",
            "min": 0,
            "max": 1,
            "step": 0.01,
            "unit": "",
            "value": {"path": "/iso"},
        },
        id="Slider-fractional-step",
    ),
]


@pytest.mark.parametrize("payload", CLIO_ACCEPT_CASES)
def test_clio_workspace_accept_case_validates(payload: dict[str, Any]) -> None:
    WORKSPACE_VALIDATORS[payload["component"]].validate(payload)


CLIO_REJECT_CASES: list[Any] = [
    pytest.param({"id": "text_1", "component": "Text", "text": 42}, id="Text-wrong-type"),
    pytest.param(
        {"id": "grid_1", "component": "Grid", "children": ["text_1"], "columns": "two"},
        id="Grid-wrong-type",
    ),
    pytest.param(
        {
            "id": "table_1",
            "component": "clio.data-table.v1",
            "columns": ["station"],
            "rows": "not rows",
        },
        id="DataTable-wrong-type",
    ),
    pytest.param(
        {
            "id": "slider_1",
            "component": "Slider",
            "label": "Effort",
            "min": "zero",
            "max": 5,
            "value": 2,
        },
        id="Slider-wrong-type",
    ),
    pytest.param(
        {
            "id": "code_1",
            "component": "clio.code.v1",
            "code": "print('hello')",
            "language": {"name": "python"},
        },
        id="Code-wrong-type",
    ),
    pytest.param(
        {
            "id": "button_1",
            "component": "Button",
            "child": "text_1",
            "action": "agent.submit",
        },
        id="Button-action-not-object",
    ),
    pytest.param(
        {"id": "list_1", "component": "List", "children": ["text_1"], "listStyle": "invented"},
        id="List-unsupported-property",
    ),
    pytest.param(
        {
            "id": "field_1",
            "component": "TextField",
            "label": "Query",
            "value": "value",
            "isValid": True,
        },
        id="TextField-unsupported-property",
    ),
    pytest.param(
        {"id": "vp_1", "component": "clio.mesh-viewport.v1", "meshUri": "/scratch/run/part.glb"},
        id="MeshViewport-filesystem-path",
    ),
    pytest.param(
        {
            "id": "vp_1",
            "component": "clio.mesh-viewport.v1",
            "meshUri": "artifact://artifact_abc123",
            "vertices": [[0, 0, 0]],
        },
        id="MeshViewport-inline-geometry",
    ),
    pytest.param(
        {
            "id": "vp_1",
            "component": "clio.mesh-viewport.v1",
            "meshUri": "artifact://artifact_abc123",
            "syncGroup": "has spaces",
        },
        id="MeshViewport-bad-sync-group",
    ),
    pytest.param(
        {
            "id": "vp_1",
            "component": "clio.mesh-viewport.v1",
            "meshUri": "artifact://artifact_abc123",
            "upAxis": "w",
        },
        id="MeshViewport-bad-up-axis",
    ),
    pytest.param(
        {
            "id": "vp_1",
            "component": "clio.mesh-viewport.v1",
            "meshUri": "artifact://artifact_abc123",
            "thresholdMin": "low",
        },
        id="MeshViewport-non-numeric-threshold",
    ),
    pytest.param(
        {"id": "iso", "component": "clio.slider.v1", "label": "x", "value": 1, "max": 2},
        id="Slider-missing-min",
    ),
    pytest.param(
        {
            "id": "iso",
            "component": "clio.slider.v1",
            "label": "x",
            "value": 1,
            "min": 0,
            "max": 2,
            "step": "0.1",
        },
        id="Slider-string-step",
    ),
    pytest.param(
        {
            "id": "t1",
            "component": "clio.data-table.v1",
            "columns": ["station"],
            "rows": [{"station": "GNSS01"}],
            "selection": {"field": "station", "values": ["GNSS01"]},
        },
        id="DataTable-selection-literal-object",
    ),
    pytest.param(
        {
            "id": "map1",
            "component": "clio.map.v1",
            "points": [{"id": "s1", "label": "GNSS01", "latitude": 34.1, "longitude": -118.3}],
            "selection": {"field": "station", "values": ["GNSS01"]},
        },
        id="Map-selection-literal-object",
    ),
    pytest.param(
        {
            "id": "map1",
            "component": "clio.map.v1",
            "points": [{"id": "s1", "label": "GNSS01", "latitude": 34.1, "longitude": -118.3}],
            "selection": {"path": "/selection/stations", "extra": 1},
        },
        id="Map-selection-malformed-binding",
    ),
]

# Selection bindings on the existing components (the chart's are fixture-driven below).
CLIO_ACCEPT_CASES.extend(
    [
        pytest.param(
            {
                "id": "t1",
                "component": "clio.data-table.v1",
                "columns": ["station"],
                "rows": [{"station": "GNSS01"}],
                "selection": {"path": "/selection/stations"},
            },
            id="DataTable-selection-bound",
        ),
        pytest.param(
            {
                "id": "t1",
                "component": "clio.data-table.v1",
                "columns": ["station"],
                "rows": [{"station": "GNSS01"}],
                "selection": "single",
            },
            id="DataTable-selection-legacy-string",
        ),
        pytest.param(
            {
                "id": "map1",
                "component": "clio.map.v1",
                "points": [{"id": "s1", "label": "GNSS01", "latitude": 34.1, "longitude": -118.3}],
                "selected": "s1",
                "selection": {"path": "/selection/stations"},
            },
            id="Map-selected-and-selection-bound",
        ),
    ]
)


@pytest.mark.parametrize("payload", CLIO_REJECT_CASES)
def test_clio_workspace_reject_case_fails(payload: dict[str, Any]) -> None:
    assert not WORKSPACE_VALIDATORS[payload["component"]].is_valid(payload)


def test_clio_workspace_catalog_is_closed() -> None:
    """A component name outside the catalog's 33 fails the whole-envelope validator."""

    validator = message_validator("server_to_client.json", catalog=WORKSPACE_CATALOG)
    message = {
        "version": "v0.9.1",
        "updateComponents": {
            "surfaceId": "s",
            "components": [{"id": "root", "component": "Checkbox", "label": "x", "value": True}],
        },
    }
    assert not validator.is_valid(message)


# --------------------------------------------------------------------------- #
# Adversarial-review fixups: theme $defs, function-call $defs, pydantic/catalog
# parity (blocking findings #1 and #2, and the time-series hardening in #3).
# --------------------------------------------------------------------------- #
def test_theme_validates_against_workspace_catalog() -> None:
    """``createSurface.theme`` resolves ``catalog.json#/$defs/theme`` for the workspace catalog."""

    validator = message_validator("server_to_client.json", catalog=WORKSPACE_CATALOG)
    validator.validate(
        {
            "version": "v0.9.1",
            "createSurface": {
                "surfaceId": "s",
                "catalogId": WORKSPACE_CATALOG["catalogId"],
                "theme": {"primaryColor": "#000000"},
            },
        }
    )


def test_theme_rejects_malformed_primary_color_like_basic() -> None:
    """An unknown/malformed theme value behaves the same against both catalogs."""

    basic_validator = message_validator("server_to_client.json", catalog=BASIC_CATALOG)
    workspace_validator = message_validator("server_to_client.json", catalog=WORKSPACE_CATALOG)
    message = {
        "version": "v0.9.1",
        "createSurface": {
            "surfaceId": "s",
            "catalogId": "x",
            "theme": {"primaryColor": "not-a-hex-color"},
        },
    }
    basic_message = {
        **message,
        "createSurface": {**message["createSurface"], "catalogId": BASIC_CATALOG["catalogId"]},
    }
    workspace_message = {
        **message,
        "createSurface": {**message["createSurface"], "catalogId": WORKSPACE_CATALOG["catalogId"]},
    }
    assert basic_validator.is_valid(basic_message) == workspace_validator.is_valid(
        workspace_message
    )
    assert not workspace_validator.is_valid(workspace_message)


def test_checkable_function_call_validates_against_workspace_catalog() -> None:
    """A TextField ``checks[].condition`` FunctionCall (``required``) validates."""

    payload = {
        "id": "field_1",
        "component": "TextField",
        "label": "Name",
        "checks": [
            {
                "condition": {
                    "call": "required",
                    "args": {"value": {"path": "/name"}},
                    "returnType": "boolean",
                },
                "message": "Required",
            }
        ],
    }
    WORKSPACE_VALIDATORS["TextField"].validate(payload)
    TextFieldComponent.model_validate(payload)


def test_dynamic_string_function_call_validates_against_workspace_catalog() -> None:
    """A ``Text.text`` DynamicString FunctionCall (``formatString``) validates."""

    payload = {
        "id": "text_1",
        "component": "Text",
        "text": {"call": "formatString", "args": {"value": "x"}, "returnType": "string"},
    }
    WORKSPACE_VALIDATORS["Text"].validate(payload)
    TextComponent.model_validate(payload)


def test_unknown_function_call_is_rejected_by_both() -> None:
    """An unregistered function name (``nope``) fails both the catalog and the model."""

    payload = {
        "id": "text_1",
        "component": "Text",
        "text": {"call": "nope", "args": {}, "returnType": "string"},
    }
    assert not WORKSPACE_VALIDATORS["Text"].is_valid(payload)
    with pytest.raises(ValidationError):
        TextComponent.model_validate(payload)


CLIO_TIME_SERIES_REJECT_CASES: list[Any] = [
    pytest.param(
        {
            "id": "ts_1",
            "component": "clio.time-series.v1",
            "xKey": "t",
            "yKeys": ["a", "a"],
            "series": [{"t": 0, "a": 1}],
        },
        id="TimeSeries-duplicate-yKeys",
    ),
    pytest.param(
        {
            "id": "ts_1",
            "component": "clio.time-series.v1",
            "xKey": "t",
            "yKeys": ["  "],
            "series": [{"t": 0, "a": 1}],
        },
        id="TimeSeries-blank-yKey",
    ),
    pytest.param(
        {
            "id": "ts_1",
            "component": "clio.time-series.v1",
            "xKey": "t",
            "yKeys": ["a"],
            "series": [{"t": 0, "a": {"x": 1}}],
        },
        id="TimeSeries-non-scalar-series-value",
    ),
]


@pytest.mark.parametrize("payload", [*CLIO_REJECT_CASES, *CLIO_TIME_SERIES_REJECT_CASES])
def test_clio_reject_case_fails_pydantic_and_catalog(payload: dict[str, Any]) -> None:
    """Every reject payload fails BOTH the pydantic model and the catalog validator."""

    model_by_name = {m.model_fields["component"].default: m for m in COMPONENT_MODELS}
    model = model_by_name[payload["component"]]
    assert not WORKSPACE_VALIDATORS[payload["component"]].is_valid(payload)
    with pytest.raises(ValidationError):
        model.model_validate(payload)


@pytest.mark.parametrize("payload", CLIO_ACCEPT_CASES)
def test_clio_accept_case_validates_pydantic_and_catalog(payload: dict[str, Any]) -> None:
    """Every accept payload validates against BOTH the pydantic model and the catalog validator."""

    model_by_name = {m.model_fields["component"].default: m for m in COMPONENT_MODELS}
    model = model_by_name[payload["component"]]
    WORKSPACE_VALIDATORS[payload["component"]].validate(payload)
    model.model_validate(payload)


# --------------------------------------------------------------------------- #
# clio.chart.v1 — shared fixtures (tests/fixtures/chart/, mirrored by gact-tui)
# --------------------------------------------------------------------------- #
CHART_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "chart"
CHART_COMPONENT_CASES: list[dict[str, Any]] = json.loads(
    (CHART_FIXTURES / "component_cases.json").read_text(encoding="utf-8")
)["cases"]
SELECTION_STATE_CASES: list[dict[str, Any]] = json.loads(
    (CHART_FIXTURES / "selection_state_cases.json").read_text(encoding="utf-8")
)["cases"]
_URI = "artifact://artifact_runs01"


@pytest.mark.parametrize("case", CHART_COMPONENT_CASES, ids=lambda c: c["name"])
def test_chart_component_case(case: dict[str, Any]) -> None:
    """The pydantic model decides ``valid``; the catalog's JSON Schema, ``jsonSchemaValid``.

    Every case the JSON Schema rejects is also rejected by the model. The
    cases the JSON Schema alone accepts but the model rejects are the deep
    spec-guard rules (``data.url``, size, view count) that only
    :mod:`clio_schemas.a2ui.chart_spec` can check.
    """

    payload = case["payload"]
    assert WORKSPACE_VALIDATORS["clio.chart.v1"].is_valid(payload) == case["jsonSchemaValid"]
    if case["valid"]:
        ChartComponent.model_validate(payload)
    else:
        with pytest.raises(ValidationError):
            ChartComponent.model_validate(payload)
    assert case["valid"] <= case["jsonSchemaValid"]


def test_chart_component_cases_cover_the_required_rejections() -> None:
    names = {case["name"] for case in CHART_COMPONENT_CASES}
    assert {
        "reject-spec-data-url",
        "reject-oversized-spec",
        "reject-disallowed-top-level-key",
        "reject-both-spec-and-preset",
        "reject-neither-spec-nor-preset",
        "reject-both-data-and-data-uri",
        "reject-too-many-views",
    } <= names


def test_chart_spec_guard_error_names_the_rule() -> None:
    payload = next(c for c in CHART_COMPONENT_CASES if c["name"] == "reject-spec-data-url")
    with pytest.raises(ValidationError, match="data_not_named_source"):
        ChartComponent.model_validate(payload["payload"])


def test_chart_rejects_more_than_the_inline_row_limit() -> None:
    payload: dict[str, Any] = {
        "id": "ch",
        "component": "clio.chart.v1",
        "preset": "scatter",
        "xField": "x",
        "yField": "y",
        "entityField": "e",
        "data": [{"x": i, "y": i, "e": "a"} for i in range(MAX_INLINE_ROWS + 1)],
    }
    assert not WORKSPACE_VALIDATORS["clio.chart.v1"].is_valid(payload)
    with pytest.raises(ValidationError):
        ChartComponent.model_validate(payload)
    payload["data"] = payload["data"][:MAX_INLINE_ROWS]
    WORKSPACE_VALIDATORS["clio.chart.v1"].validate(payload)
    ChartComponent.model_validate(payload)


@pytest.mark.parametrize("preset", PRESET_NAMES)
def test_catalog_preset_rules_match_the_templates(preset: str) -> None:
    """Missing any one required field fails both sides; the full set passes both."""

    document = load_preset(preset)
    fields = {name: f"col_{name}" for name in document["requiredFields"]}
    payload = {
        "id": "ch",
        "component": "clio.chart.v1",
        "preset": preset,
        "dataUri": _URI,
        **fields,
    }
    WORKSPACE_VALIDATORS["clio.chart.v1"].validate(payload)
    ChartComponent.model_validate(payload)
    for name in document["requiredFields"]:
        partial = {k: v for k, v in payload.items() if k != name}
        assert not WORKSPACE_VALIDATORS["clio.chart.v1"].is_valid(partial)
        with pytest.raises(ValidationError):
            ChartComponent.model_validate(partial)


@pytest.mark.parametrize("case", SELECTION_STATE_CASES, ids=lambda c: c["name"])
def test_selection_state_case(case: dict[str, Any]) -> None:
    """The value at /selection/<key>: pydantic SelectionState and $defs/SelectionState agree."""

    validator = Draft202012Validator(WORKSPACE_CATALOG["$defs"]["SelectionState"])
    assert validator.is_valid(case["value"]) == case["valid"]
    if case["valid"]:
        SelectionState.model_validate(case["value"])
    else:
        with pytest.raises(ValidationError):
            SelectionState.model_validate(case["value"])


def test_chart_table_and_map_share_one_selection_path_in_one_surface() -> None:
    """A whole updateComponents message binding three components to one selection path."""

    binding = {"path": "/selection/stations"}
    components: list[dict[str, Any]] = [
        {"id": "root", "component": "Column", "children": ["chart", "table", "map"]},
        {
            "id": "chart",
            "component": "clio.chart.v1",
            "preset": "trajectories",
            "xField": "t",
            "xType": "temporal",
            "yField": "disp_mm",
            "entityField": "station",
            "dataUri": _URI,
            "dataQuery": {"columns": ["t", "disp_mm", "station"], "limit": 5000},
            "selection": binding,
        },
        {
            "id": "table",
            "component": "clio.data-table.v1",
            "columns": ["station"],
            "rows": [{"station": "GNSS01"}],
            "selection": binding,
        },
        {
            "id": "map",
            "component": "clio.map.v1",
            "points": [{"id": "GNSS01", "label": "GNSS01", "latitude": 34.1, "longitude": -118.3}],
            "selection": binding,
        },
    ]
    message = {
        "version": "v0.9.1",
        "updateComponents": {"surfaceId": "s", "components": components},
    }
    validator = message_validator("server_to_client.json", catalog=WORKSPACE_CATALOG)
    validator.validate(message)
    model_by_name = {m.model_fields["component"].default: m for m in COMPONENT_MODELS}
    for component in components:
        model_by_name[component["component"]].model_validate(component)


def test_chart_title_accepts_a_function_call_like_other_dynamic_strings() -> None:
    payload = {
        "id": "ch",
        "component": "clio.chart.v1",
        "spec": {"mark": "bar", "encoding": {"x": {"field": "k", "type": "nominal"}}},
        "data": [{"k": "a"}],
        "title": {"call": "formatString", "args": {"value": "x"}, "returnType": "string"},
    }
    WORKSPACE_VALIDATORS["clio.chart.v1"].validate(payload)
    ChartComponent.model_validate(payload)


def test_chart_aggregate_name_collision_is_a_model_rule() -> None:
    """A metric named like a groupBy column: JSON Schema cannot see it, the model refuses it."""

    payload = {
        "id": "ch",
        "component": "clio.chart.v1",
        "preset": "scatter",
        "xField": "run",
        "yField": "v_mean",
        "entityField": "run",
        "dataUri": _URI,
        "dataQuery": {
            "columns": ["run", "v_mean"],
            "aggregate": {"groupBy": ["run", "v_mean"], "metrics": [{"column": "v", "fn": "mean"}]},
        },
    }
    WORKSPACE_VALIDATORS["clio.chart.v1"].validate(payload)
    with pytest.raises(ValidationError, match="collide with groupBy"):
        ChartComponent.model_validate(payload)


# --------------------------------------------------------------------------- #
# Adversarial-review fixups round 2: aggregate-requires-columns, the dataUri
# whitespace hole, the spec guard now expressible in JSON Schema, explicit
# null on optional dataQuery fields, int-from-whole-number, offset/sort, and
# the contains filter op (issue #1533 phase-2 follow-up).
# --------------------------------------------------------------------------- #
def _chart_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "ch",
        "component": "clio.chart.v1",
        "preset": "scatter",
        "xField": "x",
        "yField": "y",
        "entityField": "e",
        "dataUri": _URI,
    }
    base.update(overrides)
    return base


def test_chart_query_aggregate_without_columns_is_rejected() -> None:
    """aggregate's output columns (e.g. v_mean) don't exist in the source without columns."""

    payload = _chart_payload(dataQuery={"aggregate": {"metrics": [{"column": "v", "fn": "mean"}]}})
    assert not WORKSPACE_VALIDATORS["clio.chart.v1"].is_valid(payload)
    with pytest.raises(ValidationError):
        ChartComponent.model_validate(payload)


def test_chart_query_aggregate_with_columns_is_valid() -> None:
    payload = _chart_payload(
        dataQuery={
            "columns": ["e", "v"],
            "aggregate": {"metrics": [{"column": "v", "fn": "mean"}]},
        }
    )
    WORKSPACE_VALIDATORS["clio.chart.v1"].validate(payload)
    ChartComponent.model_validate(payload)


def test_chart_query_aggregate_explicit_null_does_not_demand_columns() -> None:
    """An explicit ``aggregate: null`` is the same as omitting it — no columns demand."""

    payload = _chart_payload(dataQuery={"aggregate": None})
    WORKSPACE_VALIDATORS["clio.chart.v1"].validate(payload)
    ChartComponent.model_validate(payload)


@pytest.mark.parametrize("field", ["filter", "aggregate", "downsample", "limit", "columns"])
def test_data_query_optional_fields_accept_explicit_null(field: str) -> None:
    """Every ``X | None`` dataQuery field also validates an explicit ``null`` in the schema."""

    payload = _chart_payload(dataQuery={field: None})
    WORKSPACE_VALIDATORS["clio.chart.v1"].validate(payload)
    ChartComponent.model_validate(payload)


def test_downsample_x_and_y_accept_explicit_null_outside_per_entity_lttb() -> None:
    payload = _chart_payload(dataQuery={"downsample": {"mode": "none", "x": None, "y": None}})
    WORKSPACE_VALIDATORS["clio.chart.v1"].validate(payload)
    ChartComponent.model_validate(payload)


def test_downsample_per_entity_lttb_rejects_null_x_or_y() -> None:
    """``required`` alone would accept a present-but-null x/y; the schema must not."""

    payload = _chart_payload(
        dataQuery={"downsample": {"mode": "per_entity_lttb", "x": None, "y": "v"}}
    )
    assert not WORKSPACE_VALIDATORS["clio.chart.v1"].is_valid(payload)
    with pytest.raises(ValidationError):
        ChartComponent.model_validate(payload)


def test_data_uri_pattern_rejects_a_trailing_newline() -> None:
    """Python's ``$`` matches just before a trailing newline; the schema must not accept it."""

    payload = _chart_payload(dataUri=f"{_URI}\n")
    assert not WORKSPACE_VALIDATORS["clio.chart.v1"].is_valid(payload)
    with pytest.raises(ValidationError):
        ChartComponent.model_validate(payload)


def test_chart_query_limit_accepts_a_whole_number_float_like_json_schema_does() -> None:
    """JSON Schema's "type": "integer" accepts 5.0; the model must agree, not just 5."""

    payload = _chart_payload(dataQuery={"limit": 5.0})
    WORKSPACE_VALIDATORS["clio.chart.v1"].validate(payload)
    chart = ChartComponent.model_validate(payload)
    assert chart.dataQuery is not None
    assert chart.dataQuery.limit == 5
    assert isinstance(chart.dataQuery.limit, int)


def test_chart_query_limit_still_rejects_a_fractional_float() -> None:
    payload = _chart_payload(dataQuery={"limit": 5.5})
    assert not WORKSPACE_VALIDATORS["clio.chart.v1"].is_valid(payload)
    with pytest.raises(ValidationError):
        ChartComponent.model_validate(payload)


def test_spec_with_url_anywhere_is_rejected_by_the_json_validator_alone() -> None:
    """The forbidden-key ban is now real JSON Schema, not just a pydantic-side guard."""

    payload = {
        "id": "ch",
        "component": "clio.chart.v1",
        "spec": {"layer": [{"mark": "point", "encoding": {}, "usermeta": {"url": "x"}}]},
        "data": [{"x": 1}],
    }
    assert not WORKSPACE_VALIDATORS["clio.chart.v1"].is_valid(payload)
    with pytest.raises(ValidationError):
        ChartComponent.model_validate(payload)


def test_spec_data_named_source_at_any_depth_is_rejected_by_the_json_validator_alone() -> None:
    payload = {
        "id": "ch",
        "component": "clio.chart.v1",
        "spec": {"layer": [{"mark": "point", "data": {"values": [1, 2, 3]}}]},
        "data": [{"x": 1}],
    }
    assert not WORKSPACE_VALIDATORS["clio.chart.v1"].is_valid(payload)
    with pytest.raises(ValidationError):
        ChartComponent.model_validate(payload)


def test_spec_data_named_source_nested_still_validates() -> None:
    payload = {
        "id": "ch",
        "component": "clio.chart.v1",
        "spec": {"layer": [{"mark": "point", "data": {"name": "source"}}]},
        "data": [{"x": 1}],
    }
    WORKSPACE_VALIDATORS["clio.chart.v1"].validate(payload)
    ChartComponent.model_validate(payload)


def test_data_query_offset_and_sort_shape() -> None:
    payload = _chart_payload(
        dataQuery={
            "sort": [{"column": "e", "desc": True}, {"column": "x"}],
            "offset": 100,
            "limit": 50,
        }
    )
    WORKSPACE_VALIDATORS["clio.chart.v1"].validate(payload)
    ChartComponent.model_validate(payload)


def test_data_query_offset_rejects_negative() -> None:
    payload = _chart_payload(dataQuery={"offset": -1})
    assert not WORKSPACE_VALIDATORS["clio.chart.v1"].is_valid(payload)
    with pytest.raises(ValidationError):
        ChartComponent.model_validate(payload)


def test_data_query_sort_rejects_unknown_property() -> None:
    payload = _chart_payload(dataQuery={"sort": [{"column": "e", "ascending": True}]})
    assert not WORKSPACE_VALIDATORS["clio.chart.v1"].is_valid(payload)
    with pytest.raises(ValidationError):
        ChartComponent.model_validate(payload)


def test_query_filter_contains_op() -> None:
    payload = _chart_payload(
        dataQuery={"filter": [{"column": "name", "op": "contains", "value": "station"}]}
    )
    WORKSPACE_VALIDATORS["clio.chart.v1"].validate(payload)
    ChartComponent.model_validate(payload)


def test_query_filter_contains_requires_non_empty_string_value() -> None:
    for bad_value in ("", 1, ["a"], None):
        payload = _chart_payload(
            dataQuery={"filter": [{"column": "name", "op": "contains", "value": bad_value}]}
        )
        assert not WORKSPACE_VALIDATORS["clio.chart.v1"].is_valid(payload)
        with pytest.raises(ValidationError):
            ChartComponent.model_validate(payload)


def _select_data_button(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "pick",
        "component": "Button",
        "child": "pick_label",
        "action": {"functionCall": {"call": "selectData", "args": args, "returnType": "void"}},
    }


def test_select_data_writes_a_selection_path_and_field() -> None:
    """selectData names the /selection/<key> path and the field its rowIds are values of."""

    args = {"path": "/selection/stations", "field": "station", "rowIds": ["GNSS01", "GNSS07"]}
    WORKSPACE_VALIDATORS["Button"].validate(_select_data_button(args))
    WORKSPACE_VALIDATORS["Button"].validate(
        _select_data_button({**args, "surfaceId": "s", "rowIds": []})
    )
    for bad in (
        {"field": "station", "rowIds": ["GNSS01"]},
        {"path": "/selection/stations", "rowIds": ["GNSS01"]},
        {**args, "path": "/stations"},
        {**args, "path": "/selection/a/b"},
        {**args, "field": ""},
        {**args, "rowIds": [1]},
        {**args, "values": ["GNSS01"]},
    ):
        assert not WORKSPACE_VALIDATORS["Button"].is_valid(_select_data_button(bad)), bad
