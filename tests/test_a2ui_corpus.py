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

from clio_schemas.a2ui.catalog_export import render_workspace_catalog
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
]


@pytest.mark.parametrize("payload", CLIO_REJECT_CASES)
def test_clio_workspace_reject_case_fails(payload: dict[str, Any]) -> None:
    assert not WORKSPACE_VALIDATORS[payload["component"]].is_valid(payload)


def test_clio_workspace_catalog_is_closed() -> None:
    """A component name outside the catalog's 30 fails the whole-envelope validator."""

    validator = message_validator("server_to_client.json", catalog=WORKSPACE_CATALOG)
    message = {
        "version": "v0.9.1",
        "updateComponents": {
            "surfaceId": "s",
            "components": [{"id": "root", "component": "Checkbox", "label": "x", "value": True}],
        },
    }
    assert not validator.is_valid(message)
