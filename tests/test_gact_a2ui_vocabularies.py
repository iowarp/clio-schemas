"""Conformance tests for the GACT 0.3 and A2UI 0.9.1 vocabularies.

Component-shape coverage that used to run through the deleted
``A2UIComponent`` closed union now runs two ways: pydantic-level (this file,
against the individual component models — still the catalog generator) and
JSON-Schema-level, through the *same* corpus-runner machinery as the
vendored spec, in ``tests/test_a2ui_corpus.py`` (``CLIO_ACCEPT_CASES`` /
``CLIO_REJECT_CASES``).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from clio_schemas.a2ui.v0_9_1.bounded_components import (
    MAX_CHART_HEIGHT,
    MAX_FIELD_NAME_LENGTH,
    MAX_MAP_POINTS,
    MAX_QUERY_COLUMNS,
    MAX_QUERY_FILTERS,
    MAX_QUERY_IN_VALUES,
    MAX_QUERY_LIMIT,
    MAX_QUERY_METRICS,
    MAX_QUERY_PER_ENTITY,
    MAX_WORKFLOW_EDGES,
    MAX_WORKFLOW_NODES,
    MIN_CHART_HEIGHT,
    ChartComponent,
    CodeComponent,
    DataTableComponent,
    MapComponent,
    WorkflowComponent,
)
from clio_schemas.a2ui.v0_9_1.capabilities import (
    A2UIAgentCapabilities,
    A2UIClientCapabilities,
    InlineCatalog,
)
from clio_schemas.a2ui.v0_9_1.components import (
    COMPONENT_SPECS,
    ButtonComponent,
    GridComponent,
    ListComponent,
    SelectionState,
    SliderComponent,
    TextComponent,
    TextFieldComponent,
)
from clio_schemas.a2ui.v0_9_1.data_model import A2UIClientDataModel
from clio_schemas.a2ui.v0_9_1.messages import (
    A2UIClientAction,
    A2UIClientMessage,
    A2UIServerMessage,
)
from clio_schemas.a2ui.validation import message_validator
from clio_schemas.gact_v3 import InjectionMessageBlock, MessageBlock, NoticeMessageBlock

REPO_ROOT = Path(__file__).resolve().parents[1]
BASIC_CATALOG_PATH = (
    REPO_ROOT
    / "src"
    / "clio_schemas"
    / "schemas"
    / "a2ui"
    / "v0_9_1"
    / "catalogs"
    / "basic"
    / "catalog.json"
)
BASIC_CATALOG = json.loads(BASIC_CATALOG_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("block_type", "payload"),
    [
        ("text", {"text": "answer"}),
        ("reasoning", {"text": "reasoning"}),
        ("tool", {"tool_id": "tool_1"}),
        ("plan", {"title": "Plan"}),
        ("task", {"task_id": "task_1"}),
        ("subagent", {"subagent_id": "agent_1"}),
        ("artifact", {"artifact_id": "artifact_1"}),
        (
            "action_card",
            {
                "title": "Review",
                "actions": [
                    {
                        "id": "approve",
                        "label": "Approve",
                        "behavior": {"kind": "approval.respond"},
                    }
                ],
            },
        ),
        ("a2ui", {"surface_id": "surface_1"}),
        ("citation", {"label": "Source", "uri": "https://example.test"}),
        ("diff", {"path": "file.py", "unified_diff": "@@"}),
        ("error", {"code": "failed", "message": "Failed", "recoverable": False}),
        ("routing", {"label": "Compacted"}),
        ("injection", {"source": "todos", "text": "- [ ] load the data"}),
        ("injection", {"source": "path_hint", "text": "did you mean a.csv?", "call_id": "c1"}),
        ("notice", {"source": "compaction_failed", "text": "Compaction failed."}),
    ],
)
def test_message_block_union_accepts_exactly_the_fifteen_v3_types(
    block_type: str,
    payload: dict[str, object],
) -> None:
    """Every canonical v3 discriminator resolves through one schema root."""

    block = MessageBlock.model_validate({"id": "block_1", "type": block_type, **payload})
    assert block.root.type == block_type


def test_an_injection_names_its_source_and_carries_the_exact_text() -> None:
    """What the harness gave the agent, shown to the user as exactly what it got."""

    with pytest.raises(ValidationError):
        MessageBlock.model_validate({"id": "b", "type": "injection", "text": "no source"})
    block = MessageBlock.model_validate(
        {"id": "b", "type": "injection", "source": "plan_mode", "text": "Plan mode is on."}
    )
    assert isinstance(block.root, InjectionMessageBlock)
    assert (block.root.source, block.root.call_id) == ("plan_mode", None)


_SUMMARIZATION_INJECTION: dict[str, object] = {
    "id": "b",
    "type": "injection",
    "source": "summarization",
    "text": "Summary of the earlier conversation.",
    "call_id": "",
    "trigger": "auto",
    "compaction_id": "cmp_1",
    "sequence": 3,
}
_VARIANT_INJECTION: dict[str, object] = {
    "id": "b",
    "type": "injection",
    "source": "refine_advice",
    "text": "Tighten the axis labels.",
    "variants_id": "var_1",
    "try_index": 2,
}
_FAILED_COMPACTION_NOTICE: dict[str, object] = {
    "id": "n",
    "type": "notice",
    "source": "compaction_failed",
    "text": "Compaction failed: the provider timed out.",
    "code": "provider_timeout",
    "trigger": "manual",
    "compaction_id": "cmp_2",
}
MESSAGE_BLOCK_SCHEMA = json.loads(
    (REPO_ROOT / "src" / "clio_schemas" / "schemas" / "message_block.json").read_text(
        encoding="utf-8"
    )
)


@pytest.mark.parametrize(
    "payload",
    [_SUMMARIZATION_INJECTION, _VARIANT_INJECTION, _FAILED_COMPACTION_NOTICE],
    ids=["summarization-injection", "variant-try-injection", "failed-compaction-notice"],
)
def test_compaction_and_variant_blocks_round_trip(payload: dict[str, object]) -> None:
    """The blocks clio-agent emits for compactions and variant tries survive a round trip,
    through both the pydantic model and the committed JSON Schema."""

    block = MessageBlock.model_validate(payload)
    assert block.model_dump(mode="json", exclude_none=True) == payload
    assert MessageBlock.model_validate_json(block.model_dump_json()) == block
    Draft202012Validator(MESSAGE_BLOCK_SCHEMA).validate(payload)


def test_a_notice_names_its_source_and_has_only_optional_compaction_fields() -> None:
    """A notice needs a source and text; code/trigger/compaction_id are optional."""

    block = MessageBlock.model_validate(
        {"id": "n", "type": "notice", "source": "compaction_failed", "text": "failed"}
    )
    assert isinstance(block.root, NoticeMessageBlock)
    assert (block.root.code, block.root.trigger, block.root.compaction_id) == (None, None, None)
    with pytest.raises(ValidationError):
        MessageBlock.model_validate({"id": "n", "type": "notice", "text": "no source"})


@pytest.mark.parametrize(
    "payload",
    [
        {**_SUMMARIZATION_INJECTION, "trigger": "scheduled"},
        {**_VARIANT_INJECTION, "try_index": -1},
        {**_VARIANT_INJECTION, "try_index": "2"},
        {**_FAILED_COMPACTION_NOTICE, "trigger": "sometimes"},
        {**_SUMMARIZATION_INJECTION, "invented": True},
        {**_FAILED_COMPACTION_NOTICE, "invented": True},
        {**_FAILED_COMPACTION_NOTICE, "variants_id": "var_1"},
    ],
    ids=[
        "injection-bad-trigger",
        "injection-negative-try",
        "injection-string-try",
        "notice-bad-trigger",
        "injection-unknown-field",
        "notice-unknown-field",
        "notice-has-no-variant-fields",
    ],
)
def test_injection_and_notice_blocks_are_closed_and_typed(payload: dict[str, Any]) -> None:
    """Both blocks reject unknown fields, invalid triggers and bad try indexes,
    in the pydantic model and the committed JSON Schema alike."""

    with pytest.raises(ValidationError):
        MessageBlock.model_validate(payload)
    assert not Draft202012Validator(MESSAGE_BLOCK_SCHEMA).is_valid(payload)


def test_message_block_union_rejects_unknown_types_and_properties() -> None:
    """The canonical vocabulary is closed even though clients may degrade unknown future blocks."""

    with pytest.raises(ValidationError):
        MessageBlock.model_validate({"id": "block_1", "type": "future"})
    with pytest.raises(ValidationError):
        MessageBlock.model_validate(
            {"id": "block_1", "type": "text", "text": "hello", "invented": True}
        )


def test_catalog_declares_thirty_two_components_and_preserves_checkbox_spelling() -> None:
    """The 32 CLIO catalog components (25 factory-built + 7 bounded) are closed and correct."""

    factory_names = set(COMPONENT_SPECS)
    bounded_names = {
        "clio.map.v1",
        "clio.data-table.v1",
        "clio.code.v1",
        "clio.mermaid.v1",
        "clio.diff.v1",
        "clio.workflow.v1",
        "clio.chart.v1",
    }
    names = factory_names | bounded_names
    assert len(names) == 32
    assert factory_names.isdisjoint(bounded_names)
    assert "CheckBox" in names
    assert "Checkbox" not in names
    assert "clio.time-series.v1" not in names


def test_catalog_rejects_wrong_types_and_unsupported_properties() -> None:
    """The producer boundary rejects values the React catalog cannot render."""

    cases: list[tuple[type, dict[str, object]]] = [
        (TextComponent, {"id": "text_1", "component": "Text", "text": 42}),
        (
            GridComponent,
            {"id": "grid_1", "component": "Grid", "children": ["text_1"], "columns": "two"},
        ),
        (
            DataTableComponent,
            {
                "id": "table_1",
                "component": "clio.data-table.v1",
                "columns": ["station"],
                "rows": "not rows",
            },
        ),
        (
            SliderComponent,
            {
                "id": "slider_1",
                "component": "Slider",
                "label": "Effort",
                "min": "zero",
                "max": 5,
                "value": 2,
            },
        ),
        (
            CodeComponent,
            {
                "id": "code_1",
                "component": "clio.code.v1",
                "code": "print('hello')",
                "language": {"name": "python"},
            },
        ),
        (
            TextComponent,
            {"id": "text_1", "component": "Text", "text": "hello", "weight": "heavy"},
        ),
        (
            ButtonComponent,
            {"id": "button_1", "component": "Button", "child": "text_1", "action": "agent.submit"},
        ),
        (
            ListComponent,
            {"id": "list_1", "component": "List", "children": ["text_1"], "listStyle": "invented"},
        ),
        (
            TextFieldComponent,
            {
                "id": "field_1",
                "component": "TextField",
                "label": "Query",
                "value": "value",
                "isValid": True,
            },
        ),
    ]
    for model, component in cases:
        with pytest.raises(ValidationError):
            model.model_validate(component)


def test_grid_gap_and_columns_match_the_client_catalog_bounds() -> None:
    """G2 (#23): the server must reject what the client already rejects.

    gact-tui's kernel catalog (``kernel-catalog.tsx``) caps Grid at
    ``columns: z.number().int().min(1).max(12)`` and
    ``gap: z.number().min(0).max(12)``. Before this bound existed here, the
    producer accepted any ``columns``/``gap`` and returned ``rendered: true``
    for a Grid the client's own catalog validation then threw on, stranding
    the surface in a permanent failure (the schema-drift half of #23).
    """

    base = {"id": "grid_1", "component": "Grid", "children": ["text_1"]}
    GridComponent.model_validate({**base, "columns": 1, "gap": 0})
    GridComponent.model_validate({**base, "columns": 12, "gap": 12})
    for bad in (
        {"columns": 0},
        {"columns": 13},
        {"gap": -1},
        {"gap": 13},
    ):
        with pytest.raises(ValidationError):
            GridComponent.model_validate({**base, **bad})


def test_catalog_accepts_official_dynamic_bindings_and_actions() -> None:
    """Official bindings and event actions remain valid after closing property types."""

    text = TextComponent.model_validate(
        {
            "id": "text_1",
            "component": "Text",
            "text": {"path": "/summary"},
            "accessibility": {"label": {"path": "/summaryLabel"}},
        }
    )
    button = ButtonComponent.model_validate(
        {
            "id": "button_1",
            "component": "Button",
            "child": "text_1",
            "action": {
                "event": {
                    "name": "agent.submit",
                    "context": {"prompt": {"path": "/prompt"}},
                }
            },
        }
    )

    assert text.model_dump()["component"] == "Text"
    assert button.model_dump()["component"] == "Button"


def test_catalog_enforces_map_and_workflow_limits() -> None:
    """Renderer resource bounds are part of the cross-repository contract."""

    point = {"id": "p", "label": "Point", "latitude": 1.0, "longitude": 2.0}
    with pytest.raises(ValidationError):
        MapComponent.model_validate(
            {
                "id": "map_1",
                "component": "clio.map.v1",
                "points": [point] * (MAX_MAP_POINTS + 1),
            }
        )
    with pytest.raises(ValidationError):
        WorkflowComponent.model_validate(
            {
                "id": "workflow_1",
                "component": "clio.workflow.v1",
                "nodes": [
                    {"id": f"node_{index}", "label": "Node"}
                    for index in range(MAX_WORKFLOW_NODES + 1)
                ],
                "edges": [],
            }
        )
    with pytest.raises(ValidationError):
        WorkflowComponent.model_validate(
            {
                "id": "workflow_1",
                "component": "clio.workflow.v1",
                "nodes": [{"id": "a", "label": "A"}],
                "edges": [{"source": "a", "target": "a"} for _ in range(MAX_WORKFLOW_EDGES + 1)],
            }
        )


def test_chart_enforces_height_query_and_selection_param_bounds() -> None:
    """clio.chart.v1's scalar bounds, independent of the spec guard."""

    base = {
        "id": "chart_1",
        "component": "clio.chart.v1",
        "preset": "scatter",
        "xField": "x",
        "yField": "y",
        "entityField": "e",
        "dataUri": "artifact://artifact_1",
    }
    chart = ChartComponent.model_validate(
        {**base, "height": MAX_CHART_HEIGHT, "dataQuery": {"limit": MAX_QUERY_LIMIT}}
    )
    assert chart.selectionParam is None  # the renderer's default is "sel"
    for bad in (
        {"height": MIN_CHART_HEIGHT - 1},
        {"height": MAX_CHART_HEIGHT + 1},
        {"dataQuery": {"limit": 0}},
        {"dataQuery": {"limit": MAX_QUERY_LIMIT + 1}},
        {"dataQuery": {"columns": [f"c{i}" for i in range(MAX_QUERY_COLUMNS + 1)]}},
        {"dataQuery": {"filter": [{"column": "e", "op": "isnull"}] * (MAX_QUERY_FILTERS + 1)}},
        {
            "dataQuery": {
                "filter": [{"column": "e", "op": "in", "value": [0] * (MAX_QUERY_IN_VALUES + 1)}]
            }
        },
        {
            "dataQuery": {
                "aggregate": {
                    "metrics": [
                        {"column": f"c{i}", "fn": "sum"} for i in range(MAX_QUERY_METRICS + 1)
                    ]
                }
            }
        },
        {"dataQuery": {"downsample": {"mode": "stride", "maxPerEntity": MAX_QUERY_PER_ENTITY + 1}}},
        {"dataQuery": {"downsample": {"mode": "stride", "maxPerEntity": 0}}},
        {"selectionParam": "9lives"},
        {"xField": ""},
        {"xField": "x" * (MAX_FIELD_NAME_LENGTH + 1)},
    ):
        with pytest.raises(ValidationError):
            ChartComponent.model_validate({**base, **bad})


def test_selection_is_a_dynamic_value_on_table_map_and_chart() -> None:
    """``selection`` binds to a path on all three; the table's legacy string still validates."""

    binding = {"path": "/selection/stations"}
    table = {
        "id": "t",
        "component": "clio.data-table.v1",
        "columns": ["station"],
        "rows": [{"station": "GNSS01"}],
    }
    point = {"id": "p", "label": "Point", "latitude": 1.0, "longitude": 2.0}
    assert DataTableComponent.model_validate(
        {**table, "selection": binding, "selectionField": "station"}
    )
    assert DataTableComponent.model_validate({**table, "selection": "multiple"})
    map_component = MapComponent.model_validate(
        {
            "id": "m",
            "component": "clio.map.v1",
            "points": [point],
            "selection": binding,
            "selectionField": "station",
        }
    )
    assert map_component.selected is None
    with pytest.raises(ValidationError):
        DataTableComponent.model_validate(
            {**table, "selection": {"field": "station", "values": ["GNSS01"]}}
        )
    state = SelectionState.model_validate(
        {"field": "station", "values": ["GNSS01", 7], "source": "chart_1"}
    )
    assert state.values == ["GNSS01", 7]


def test_client_action_requires_known_keys_but_tolerates_extensions() -> None:
    """0.9.1 actions retain mandatory identity while accepting protocol extensions."""

    message = A2UIClientMessage.model_validate(
        {
            "version": "v0.9.1",
            "action": {
                "name": "run.cancel",
                "surfaceId": "surface_1",
                "sourceComponentId": "cancel",
                "timestamp": datetime.now(UTC).isoformat(),
                "context": {},
                "extension": {"reason": "user"},
            },
        }
    )
    assert message.action is not None
    assert message.action.surfaceId == "surface_1"
    with pytest.raises(ValidationError):
        A2UIClientAction.model_validate(
            {
                "name": "run.cancel",
                "timestamp": datetime.now(UTC).isoformat(),
                "context": {},
            }
        )


def test_client_action_name_is_open_not_a_closed_literal() -> None:
    """``action.name`` accepts any non-empty string — CLIO names are not special-cased."""

    action = A2UIClientAction.model_validate(
        {
            "name": "earthscope.stations.selected",
            "surfaceId": "s",
            "sourceComponentId": "c",
            "timestamp": datetime.now(UTC).isoformat(),
            "context": {},
        }
    )
    assert action.name == "earthscope.stations.selected"
    with pytest.raises(ValidationError):
        A2UIClientAction.model_validate(
            {
                "name": "",
                "surfaceId": "s",
                "sourceComponentId": "c",
                "timestamp": datetime.now(UTC).isoformat(),
                "context": {},
            }
        )


def test_server_message_requires_exactly_one_operation() -> None:
    with pytest.raises(ValidationError):
        A2UIServerMessage.model_validate({"version": "v0.9.1"})
    with pytest.raises(ValidationError):
        A2UIServerMessage.model_validate(
            {
                "version": "v0.9.1",
                "createSurface": {"surfaceId": "s", "catalogId": "c"},
                "deleteSurface": {"surfaceId": "s"},
            }
        )
    message = A2UIServerMessage.model_validate(
        {"version": "v0.9.1", "deleteSurface": {"surfaceId": "s"}}
    )
    assert message.deleteSurface is not None


# --------------------------------------------------------------------------- #
# Adversarial-review fixups: wire-valid serialization, required surfaces,
# RFC 3339 timestamps, tolerant capabilities, boolean-schema inline catalogs.
# --------------------------------------------------------------------------- #
def test_server_message_dump_emits_only_the_present_operation_key() -> None:
    """``model_dump()`` never emits the three absent op keys as null."""

    message = A2UIServerMessage.model_validate(
        {"version": "v0.9", "updateDataModel": {"surfaceId": "s", "path": "/k"}}
    )
    dump = message.model_dump()
    assert "value" not in dump["updateDataModel"]
    assert set(dump) == {"version", "updateDataModel"}

    validator = message_validator("server_to_client", catalog=BASIC_CATALOG)
    assert validator.is_valid(dump)
    assert "null" not in message.model_dump_json()


def test_server_message_dump_keeps_an_explicit_null_value() -> None:
    """An explicit ``value: null`` round-trips; it is not confused with an omitted value."""

    message = A2UIServerMessage.model_validate(
        {"version": "v0.9", "updateDataModel": {"surfaceId": "s", "path": "/k", "value": None}}
    )
    dump = message.model_dump()
    assert "value" in dump["updateDataModel"]
    assert dump["updateDataModel"]["value"] is None


def test_client_data_model_requires_surfaces() -> None:
    with pytest.raises(ValidationError):
        A2UIClientDataModel.model_validate({"version": "v0.9"})
    model = A2UIClientDataModel.model_validate({"version": "v0.9", "surfaces": {}})
    assert model.surfaces == {}


def test_client_action_timestamp_must_be_rfc3339_date_time() -> None:
    """A bare date (no time component) is not a valid A2UI action timestamp."""

    with pytest.raises(ValidationError):
        A2UIClientAction.model_validate(
            {
                "name": "run.cancel",
                "surfaceId": "s",
                "sourceComponentId": "c",
                "timestamp": "2026-01-01",
                "context": {},
            }
        )


def test_capabilities_tolerate_extra_keys_like_the_vendored_schema() -> None:
    """client_capabilities.json / server_capabilities.json do not forbid extras."""

    client = A2UIClientCapabilities.model_validate(
        {"v0.9": {"supportedCatalogIds": ["c"], "future": "ignored-by-schema-not-us"}}
    )
    assert client.v0_9.supportedCatalogIds == ["c"]
    agent = A2UIAgentCapabilities.model_validate({"v0.9": {"future": True}})
    assert agent.v0_9.supportedCatalogIds == []


def test_inline_catalog_accepts_boolean_component_schema() -> None:
    """A component/theme value may be the boolean JSON Schema ``true``/``false``."""

    catalog = InlineCatalog.model_validate(
        {"catalogId": "c", "components": {"Anything": True}, "theme": {"free": False}}
    )
    assert catalog.components["Anything"] is True
