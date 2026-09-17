"""``CatalogSidecar`` event-route ``operation`` field (clio-agent#1363 slice S5).

A sidecar event routed to ``destination: "run"`` (``run.cancel``,
``run.retry``) must declare WHICH run operation it performs, so a consumer
never has to guess from the event name. The constraint is enforced both
ways: required when ``destination == "run"``, forbidden otherwise — checked
in :class:`~clio_schemas.a2ui.sidecar.CatalogSidecar`'s model validator
because only there is each event's name (the dict key) available for the
error message.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from clio_schemas.a2ui.catalog_export import render_workspace_sidecar
from clio_schemas.a2ui.sidecar import CatalogSidecar, render_narration

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_SIDECAR_PATH = (
    REPO_ROOT
    / "src"
    / "clio_schemas"
    / "schemas"
    / "a2ui"
    / "catalogs"
    / "clio-workspace"
    / "v1"
    / "catalog.clio.json"
)


def _base_payload(**event_overrides: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalogId": "https://example.test/catalog",
        "protocolVersion": "0.9.1",
        "trust": {"source": "builtin"},
        "events": event_overrides,
    }


class TestOperationRequiredForRun:
    """A ``run``-destination event without ``operation`` is rejected."""

    def test_run_event_without_operation_raises(self) -> None:
        payload = _base_payload(**{"run.cancel": {"destination": "run"}})
        with pytest.raises(ValidationError, match="run.cancel"):
            CatalogSidecar.model_validate(payload)

    def test_run_event_with_operation_validates(self) -> None:
        payload = _base_payload(**{"run.cancel": {"destination": "run", "operation": "cancel"}})
        sidecar = CatalogSidecar.model_validate(payload)
        assert sidecar.events["run.cancel"].operation == "cancel"

    def test_run_event_operation_must_be_cancel_or_retry(self) -> None:
        payload = _base_payload(**{"run.cancel": {"destination": "run", "operation": "pause"}})
        with pytest.raises(ValidationError):
            CatalogSidecar.model_validate(payload)


class TestOperationForbiddenForNonRun:
    """A non-``run``-destination event carrying ``operation`` is rejected."""

    def test_agent_event_with_operation_raises(self) -> None:
        payload = _base_payload(**{"some.event": {"destination": "agent", "operation": "cancel"}})
        with pytest.raises(ValidationError, match="some.event"):
            CatalogSidecar.model_validate(payload)

    def test_permission_event_with_operation_raises(self) -> None:
        payload = _base_payload(
            **{"approval.respond": {"destination": "permission", "operation": "retry"}}
        )
        with pytest.raises(ValidationError, match="approval.respond"):
            CatalogSidecar.model_validate(payload)

    def test_agent_event_without_operation_validates(self) -> None:
        payload = _base_payload(**{"some.event": {"destination": "agent"}})
        sidecar = CatalogSidecar.model_validate(payload)
        assert sidecar.events["some.event"].operation is None

    def test_default_destination_without_operation_validates(self) -> None:
        payload = _base_payload(**{"some.event": {}})
        sidecar = CatalogSidecar.model_validate(payload)
        assert sidecar.events["some.event"].destination == "agent"
        assert sidecar.events["some.event"].operation is None


class TestRenderedWorkspaceSidecar:
    """``render_workspace_sidecar`` (the source of truth) sets the right operations."""

    def test_renders_and_validates(self) -> None:
        sidecar = CatalogSidecar.model_validate(render_workspace_sidecar())
        assert sidecar.events["run.cancel"].destination == "run"
        assert sidecar.events["run.cancel"].operation == "cancel"
        assert sidecar.events["run.retry"].destination == "run"
        assert sidecar.events["run.retry"].operation == "retry"
        assert sidecar.events["approval.respond"].destination == "permission"
        assert sidecar.events["approval.respond"].operation is None


@pytest.fixture(scope="module")
def committed_workspace_sidecar_payload() -> dict[str, Any]:
    assert WORKSPACE_SIDECAR_PATH.is_file(), f"missing: {WORKSPACE_SIDECAR_PATH}"
    return json.loads(WORKSPACE_SIDECAR_PATH.read_text(encoding="utf-8"))


class TestCommittedWorkspaceSidecar:
    """The committed ``clio-workspace`` sidecar file parses and carries operations."""

    @pytest.fixture
    def payload(self, committed_workspace_sidecar_payload: dict[str, Any]) -> dict[str, Any]:
        return committed_workspace_sidecar_payload

    def test_parses_as_catalog_sidecar(self, payload: dict[str, Any]) -> None:
        CatalogSidecar.model_validate(payload)

    def test_run_cancel_operation(self, payload: dict[str, Any]) -> None:
        assert payload["events"]["run.cancel"] == {
            "destination": "run",
            "operation": "cancel",
        }

    def test_run_retry_operation(self, payload: dict[str, Any]) -> None:
        assert payload["events"]["run.retry"] == {
            "destination": "run",
            "operation": "retry",
        }

    def test_approval_respond_has_no_operation(self, payload: dict[str, Any]) -> None:
        assert payload["events"]["approval.respond"] == {"destination": "permission"}

    def test_no_event_declares_narration(self, payload: dict[str, Any]) -> None:
        """No declared meaning for builtin events yet — only the schema changes (0.3.2)."""

        for route in payload["events"].values():
            assert "narration" not in route


class TestNarrationPlaceholderValidation:
    """``narration``'s placeholders must be declared ``context_schema`` fields, when one exists."""

    def test_placeholder_outside_context_schema_raises(self) -> None:
        payload = _base_payload(
            **{
                "earthscope.stations.selected": {
                    "destination": "agent",
                    "context_schema": {
                        "type": "object",
                        "properties": {"stationIds": {"type": "array"}},
                    },
                    "narration": "User requested to stage stations {bogusField}",
                }
            }
        )
        with pytest.raises(ValidationError, match="bogusField"):
            CatalogSidecar.model_validate(payload)

    def test_placeholder_subset_of_context_schema_validates(self) -> None:
        payload = _base_payload(
            **{
                "earthscope.stations.selected": {
                    "destination": "agent",
                    "context_schema": {
                        "type": "object",
                        "properties": {"stationIds": {"type": "array"}},
                    },
                    "narration": "User requested to stage stations {stationIds}",
                }
            }
        )
        sidecar = CatalogSidecar.model_validate(payload)
        assert sidecar.events["earthscope.stations.selected"].narration == (
            "User requested to stage stations {stationIds}"
        )

    def test_narration_without_context_schema_allows_any_placeholder(self) -> None:
        payload = _base_payload(
            **{"some.event": {"destination": "agent", "narration": "Anything goes: {whatever}"}}
        )
        sidecar = CatalogSidecar.model_validate(payload)
        assert sidecar.events["some.event"].narration == "Anything goes: {whatever}"

    def test_narration_defaults_to_none(self) -> None:
        payload = _base_payload(**{"some.event": {"destination": "agent"}})
        sidecar = CatalogSidecar.model_validate(payload)
        assert sidecar.events["some.event"].narration is None


class TestRenderNarration:
    """:func:`render_narration` renders a route's template against resolved context."""

    def test_returns_none_when_narration_unset(self) -> None:
        payload = _base_payload(**{"some.event": {"destination": "agent"}})
        sidecar = CatalogSidecar.model_validate(payload)
        assert render_narration(sidecar.events["some.event"], {}) is None

    def test_renders_list_context_as_compact_json(self) -> None:
        payload = _base_payload(
            **{
                "earthscope.stations.selected": {
                    "destination": "agent",
                    "context_schema": {
                        "type": "object",
                        "properties": {"stationIds": {"type": "array"}},
                    },
                    "narration": "User selected stations {stationIds}",
                }
            }
        )
        sidecar = CatalogSidecar.model_validate(payload)
        route = sidecar.events["earthscope.stations.selected"]
        rendered = render_narration(route, {"stationIds": ["MTA1", "PKRD"]})
        assert rendered == 'User selected stations ["MTA1","PKRD"]'

    def test_missing_key_renders_literally(self) -> None:
        payload = _base_payload(
            **{"some.event": {"destination": "agent", "narration": "Value is {missing}"}}
        )
        sidecar = CatalogSidecar.model_validate(payload)
        route = sidecar.events["some.event"]
        assert render_narration(route, {}) == "Value is {missing}"

    def test_renders_dict_context_as_compact_json(self) -> None:
        payload = _base_payload(
            **{"some.event": {"destination": "agent", "narration": "Context: {payload}"}}
        )
        sidecar = CatalogSidecar.model_validate(payload)
        route = sidecar.events["some.event"]
        rendered = render_narration(route, {"payload": {"a": 1, "b": 2}})
        assert rendered == 'Context: {"a":1,"b":2}'

    def test_scalar_value_renders_plainly(self) -> None:
        payload = _base_payload(
            **{"some.event": {"destination": "agent", "narration": "Count: {n}"}}
        )
        sidecar = CatalogSidecar.model_validate(payload)
        route = sidecar.events["some.event"]
        assert render_narration(route, {"n": 3}) == "Count: 3"
