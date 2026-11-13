"""``clio.mcp-app.v1``: an MCP App view in a surface, its state tied to the data model."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from clio_schemas.a2ui.catalog_export import render_workspace_catalog, render_workspace_sidecar
from clio_schemas.a2ui.v0_9_1.bounded_components import COMPONENT_MODELS
from clio_schemas.a2ui.v0_9_1.components import McpAppComponent
from clio_schemas.a2ui.validation import catalog_validators

NAME = "clio.mcp-app.v1"
VALIDATOR = catalog_validators(render_workspace_catalog())[NAME]

BASE: dict[str, Any] = {
    "id": "app",
    "component": NAME,
    "server": "viewer",
    "tool": "open_view",
}

ACCEPT: list[Any] = [
    pytest.param(BASE, id="call-only"),
    pytest.param(
        {
            **BASE,
            "arguments": {"file": "run.vtu", "steps": 24, "follow": True, "range": [0, 1]},
            "state": [
                {"key": "time", "path": "/selection/time", "tool": "set_time"},
                {"key": "camera", "path": "/views/camera"},
            ],
            "height": 480,
            "weight": 2,
        },
        id="channels-arguments-height",
    ),
]

REJECT: list[Any] = [
    pytest.param({k: v for k, v in BASE.items() if k != "tool"}, id="missing-tool"),
    pytest.param({**BASE, "server": "has space"}, id="bad-server-name"),
    pytest.param({**BASE, "arguments": ["not", "an", "object"]}, id="arguments-not-object"),
    pytest.param({**BASE, "state": [{"key": "time"}]}, id="channel-missing-path"),
    pytest.param({**BASE, "state": [{"key": "time", "path": "time"}]}, id="relative-path"),
    pytest.param({**BASE, "state": [{"key": "1x", "path": "/x"}]}, id="bad-key"),
    pytest.param(
        {**BASE, "state": [{"key": "t", "path": "/t", "tool": "x", "every": 1}]},
        id="channel-extra-property",
    ),
    pytest.param(
        {**BASE, "state": [{"key": f"k{i}", "path": f"/k{i}"} for i in range(17)]},
        id="too-many-channels",
    ),
    pytest.param({**BASE, "height": 40}, id="height-too-small"),
    pytest.param({**BASE, "html": "<p>inline</p>"}, id="no-inline-view"),
]


@pytest.mark.parametrize("payload", ACCEPT)
def test_accepted_by_model_and_catalog(payload: dict[str, Any]) -> None:
    VALIDATOR.validate(payload)
    McpAppComponent.model_validate(payload)


@pytest.mark.parametrize("payload", REJECT)
def test_rejected_by_model_and_catalog(payload: dict[str, Any]) -> None:
    assert not VALIDATOR.is_valid(payload)
    with pytest.raises(ValidationError):
        McpAppComponent.model_validate(payload)


@pytest.mark.parametrize("attribute", ["key", "path"])
def test_channels_are_distinct(attribute: str) -> None:
    channels = [{"key": "a", "path": "/a"}, {"key": "b", "path": "/b"}]
    channels[1][attribute] = channels[0][attribute]
    with pytest.raises(ValidationError, match=f"state channel {attribute}s must be distinct"):
        McpAppComponent.model_validate({**BASE, "state": channels})


def test_component_is_in_the_catalog_models_and_kernel_map() -> None:
    assert McpAppComponent in COMPONENT_MODELS
    assert render_workspace_sidecar()["implements"][NAME] == {"kernel": NAME}
    schema = render_workspace_catalog()["components"][NAME]
    assert schema["description"].startswith("An MCP App view")
    properties = schema["allOf"][-1]["properties"]
    for name in ("server", "tool", "arguments", "state"):
        assert properties[name]["description"]
