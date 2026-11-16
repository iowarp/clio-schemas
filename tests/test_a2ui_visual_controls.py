"""Camera literals/bindings and named tabs stay canonical across both validators."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from clio_schemas.a2ui.catalog_export import render_workspace_catalog
from clio_schemas.a2ui.v0_9_1.bounded_components import MapCamera, MapComponent
from clio_schemas.a2ui.v0_9_1.components import TabsComponent


@pytest.mark.parametrize(
    "camera",
    [
        {"longitude": -87.63, "latitude": 41.88, "zoom": 8},
        {"longitude": 0, "latitude": 0, "zoom": 16, "bearing": -180, "pitch": 60},
    ],
)
def test_camera_literal_models_and_catalog_agree(camera: dict[str, Any]) -> None:
    MapCamera.model_validate(camera)
    schema = render_workspace_catalog()["$defs"]["MapCamera"]
    Draft202012Validator(schema).validate(camera)


@pytest.mark.parametrize(
    "camera",
    [
        {"longitude": 181, "latitude": 0, "zoom": 8},
        {"longitude": 0, "latitude": 86, "zoom": 8},
        {"longitude": 0, "latitude": 0, "zoom": 17},
        {"longitude": 0, "latitude": 0, "zoom": 8, "pitch": 61},
        {"longitude": 0, "latitude": 0, "zoom": 8, "surprise": 1},
    ],
)
def test_invalid_camera_shapes_fail_both_validators(camera: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        MapCamera.model_validate(camera)
    assert not Draft202012Validator(render_workspace_catalog()["$defs"]["MapCamera"]).is_valid(
        camera
    )


def test_camera_binding_and_tab_binding_are_declared_without_changing_basic() -> None:
    MapComponent.model_validate(
        {
            "id": "map",
            "component": "clio.map.v1",
            "camera": {"path": "/camera"},
            "points": [{"id": "p", "label": "Point", "latitude": 0, "longitude": 0}],
        }
    )
    TabsComponent.model_validate(
        {
            "id": "root",
            "component": "Tabs",
            "activeTab": {"path": "/tab"},
            "tabs": [{"title": "Overview", "child": "overview"}],
        }
    )
    basic_path = (
        Path(__file__).parents[1]
        / "src/clio_schemas/schemas/a2ui/v0_9_1/catalogs/basic/catalog.json"
    )
    basic = json.loads(basic_path.read_text(encoding="utf-8"))
    assert "activeTab" not in basic["components"]["Tabs"]["allOf"][-1]["properties"]


def test_a_mesh_view_takes_a_literal_camera_the_agent_can_aim() -> None:
    """Found live (KiCad footprints, the case view): the agent set a camera to look at the
    case's USB opening and the catalog refused it; the view could only be bound."""
    from clio_schemas.a2ui.v0_9_1.components import MeshCamera, MeshViewportComponent

    catalog = render_workspace_catalog()
    schema = catalog["$defs"]["MeshCamera"]
    for camera in (
        {"position": [30, 90, -170], "target": [30, 1.4, 32.5]},
        {"position": [0, 0, 50], "target": [0, 0, 0], "up": [0, 1, 0], "fov": 35, "zoom": 1},
    ):
        MeshCamera.model_validate(camera)
        Draft202012Validator(schema).validate(camera)
        MeshViewportComponent.model_validate(
            {
                "id": "v",
                "component": "clio.mesh-viewport.v1",
                "meshUri": "artifact://artifact_a",
                "camera": camera,
            }
        )
    MeshViewportComponent.model_validate(
        {
            "id": "v",
            "component": "clio.mesh-viewport.v1",
            "meshUri": "artifact://artifact_a",
            "camera": {"path": "/camera"},
        }
    )
    for bad in (
        {"position": [0, 0], "target": [0, 0, 0]},
        {"position": [0, 0, 1]},
        {"position": [0, 0, 1], "target": [0, 0, 0], "fov": 0},
        {"position": [0, 0, 1], "target": [0, 0, 0], "surprise": 1},
    ):
        with pytest.raises(ValidationError):
            MeshCamera.model_validate(bad)
        assert not Draft202012Validator(schema).is_valid(bad)
