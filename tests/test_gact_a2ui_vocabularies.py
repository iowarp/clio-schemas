"""Conformance tests for the GACT 0.3 and A2UI 0.9.1 vocabularies."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from clio_schemas.a2ui_v091 import (
    MAX_MAP_POINTS,
    MAX_TIME_SERIES_ROWS,
    MAX_WORKFLOW_EDGES,
    MAX_WORKFLOW_NODES,
    A2UIClientActionMessage,
    A2UIComponent,
    trusted_component_names,
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


def test_catalog_names_are_closed_and_preserve_official_checkbox_spelling() -> None:
    """The catalog rejects the historical Checkbox drift typo."""

    names = trusted_component_names()
    assert len(names) == 30
    assert "CheckBox" in names
    assert "Checkbox" not in names
    with pytest.raises(ValidationError):
        A2UIComponent.model_validate(
            {"id": "check_1", "component": "Checkbox", "label": "Ready", "value": True}
        )


def test_catalog_enforces_map_time_series_and_workflow_limits() -> None:
    """Renderer resource bounds are part of the cross-repository contract."""

    point = {"id": "p", "label": "Point", "latitude": 1.0, "longitude": 2.0}
    with pytest.raises(ValidationError):
        A2UIComponent.model_validate(
            {
                "id": "map_1",
                "component": "clio.map.v1",
                "points": [point] * (MAX_MAP_POINTS + 1),
            }
        )
    with pytest.raises(ValidationError):
        A2UIComponent.model_validate(
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
        A2UIComponent.model_validate(
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
        A2UIComponent.model_validate(
            {
                "id": "workflow_1",
                "component": "clio.workflow.v1",
                "nodes": [{"id": "a", "label": "A"}],
                "edges": [{"source": "a", "target": "a"} for _ in range(MAX_WORKFLOW_EDGES + 1)],
            }
        )


def test_client_action_requires_known_keys_but_tolerates_extensions() -> None:
    """0.9.1 actions retain mandatory identity while accepting protocol extensions."""

    message = A2UIClientActionMessage.model_validate(
        {
            "version": "v0.9.1",
            "traceId": "trace_1",
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
    assert message.action.surfaceId == "surface_1"
    with pytest.raises(ValidationError):
        A2UIClientActionMessage.model_validate(
            {
                "version": "v0.9.1",
                "action": {
                    "name": "run.cancel",
                    "surfaceId": "surface_1",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "context": {},
                },
            }
        )
