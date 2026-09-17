"""Conformance tests for the GACT 0.3 and A2UI 0.9.1 vocabularies.

Component-shape coverage that used to run through the deleted
``A2UIComponent`` closed union now runs two ways: pydantic-level (this file,
against the individual component models — still the catalog generator) and
JSON-Schema-level, through the *same* corpus-runner machinery as the
vendored spec, in ``tests/test_a2ui_corpus.py`` (``CLIO_ACCEPT_CASES`` /
``CLIO_REJECT_CASES``).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from clio_schemas.a2ui.v0_9_1.bounded_components import (
    MAX_MAP_POINTS,
    MAX_TIME_SERIES_ROWS,
    MAX_WORKFLOW_EDGES,
    MAX_WORKFLOW_NODES,
    MapComponent,
    TimeSeriesComponent,
    WorkflowComponent,
)
from clio_schemas.a2ui.v0_9_1.components import (
    COMPONENT_SPECS,
    ButtonComponent,
    CodeComponent,
    DataTableComponent,
    GridComponent,
    ListComponent,
    SliderComponent,
    TextComponent,
    TextFieldComponent,
)
from clio_schemas.a2ui.v0_9_1.messages import (
    A2UIClientAction,
    A2UIClientMessage,
    A2UIServerMessage,
)
from clio_schemas.gact_v3 import MessageBlock


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
    ],
)
def test_message_block_union_accepts_exactly_the_thirteen_v3_types(
    block_type: str,
    payload: dict[str, object],
) -> None:
    """Every canonical v3 discriminator resolves through one schema root."""

    block = MessageBlock.model_validate({"id": "block_1", "type": block_type, **payload})
    assert block.root.type == block_type


def test_message_block_union_rejects_unknown_types_and_properties() -> None:
    """The canonical vocabulary is closed even though clients may degrade unknown future blocks."""

    with pytest.raises(ValidationError):
        MessageBlock.model_validate({"id": "block_1", "type": "future"})
    with pytest.raises(ValidationError):
        MessageBlock.model_validate(
            {"id": "block_1", "type": "text", "text": "hello", "invented": True}
        )


def test_catalog_declares_thirty_components_and_preserves_checkbox_spelling() -> None:
    """The 30 CLIO catalog components (27 factory-built + 3 bounded) are closed and correct."""

    factory_names = set(COMPONENT_SPECS)
    bounded_names = {"clio.map.v1", "clio.time-series.v1", "clio.workflow.v1"}
    names = factory_names | bounded_names
    assert len(names) == 30
    assert "CheckBox" in names
    assert "Checkbox" not in names


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


def test_catalog_enforces_map_time_series_and_workflow_limits() -> None:
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
        TimeSeriesComponent.model_validate(
            {
                "id": "series_1",
                "component": "clio.time-series.v1",
                "series": [{"x": index, "y": index} for index in range(MAX_TIME_SERIES_ROWS + 1)],
                "dataUri": "artifact://artifact_1",
                "xKey": "x",
                "yKeys": ["y"],
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
