"""clio.layered-map.v1, clio.section.v1 and clio.profile-stack.v1: both sides agree.

Every case is checked against the pydantic model and the rendered catalog's
JSON Schema, so a payload the agent sends is accepted or refused the same way
by the validator and the renderer's contract.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from clio_schemas.a2ui.catalog_export import render_workspace_catalog
from clio_schemas.a2ui.v0_9_1.field_components import (
    LayeredMapComponent,
    ProfileStackComponent,
    SectionComponent,
)
from clio_schemas.a2ui.validation import catalog_validators

VALIDATORS = catalog_validators(render_workspace_catalog())
GRID = "artifact://artifact_grid01"
TABLE = "artifact://artifact_table01"

GRID_LAYER = {
    "id": "sst",
    "kind": "grid",
    "label": "SST",
    "gridUri": GRID,
    "variable": "analysed_sst",
    "colormap": "balance",
    "valueRange": [-3, 3],
}
TRACKS = {
    "id": "ev",
    "kind": "tracks",
    "label": "Events",
    "dataUri": TABLE,
    "latitudeField": "lat",
    "longitudeField": "lon",
    "idField": "event",
    "trackField": "event",
    "timeField": "time",
}
STATIONS = {
    "id": "st",
    "kind": "points",
    "label": "Stations",
    "dataUri": TABLE,
    "latitudeField": "lat",
    "longitudeField": "lon",
    "idField": "name",
    "editable": True,
}


def _map(**extra: Any) -> dict[str, Any]:
    return {"id": "m", "component": "clio.layered-map.v1", **extra}


CASES = [
    pytest.param(
        LayeredMapComponent,
        _map(
            layers=[GRID_LAYER, TRACKS],
            time={"path": "/selection/time"},
            timeField="time",
            selection={"path": "/selection/event"},
            selectionField="event",
            draw={"mode": "path", "value": {"path": "/view/path"}},
        ),
        True,
        id="map-full",
    ),
    pytest.param(
        LayeredMapComponent,
        _map(layers=[STATIONS], edits={"path": "/view/stations"}),
        True,
        id="map-editable",
    ),
    pytest.param(LayeredMapComponent, _map(layers=[]), False, id="map-no-layers"),
    pytest.param(
        LayeredMapComponent,
        _map(layers=[{**GRID_LAYER, "dataUri": TABLE}]),
        False,
        id="map-grid-two-sources",
    ),
    pytest.param(
        LayeredMapComponent,
        _map(layers=[{k: v for k, v in GRID_LAYER.items() if k != "variable"}]),
        False,
        id="map-grid-no-variable",
    ),
    pytest.param(
        LayeredMapComponent,
        _map(layers=[{k: v for k, v in TRACKS.items() if k != "trackField"}]),
        False,
        id="map-tracks-no-track",
    ),
    pytest.param(
        LayeredMapComponent,
        _map(layers=[{**GRID_LAYER, "colormap": "rainbow"}]),
        False,
        id="map-bad-colormap",
    ),
    pytest.param(
        LayeredMapComponent,
        _map(layers=[{**TRACKS, "editable": True}]),
        False,
        id="map-editable-tracks",
    ),
    pytest.param(
        LayeredMapComponent,
        _map(layers=[GRID_LAYER], draw={"mode": "lasso", "value": {"path": "/x"}}),
        False,
        id="map-bad-draw",
    ),
    pytest.param(
        SectionComponent,
        {
            "id": "s",
            "component": "clio.section.v1",
            "sectionUri": GRID,
            "variables": ["CT", "SA"],
            "contourInterval": 0.5,
            "selection": {"path": "/selection/profile"},
            "selectionField": "profile",
            "pointer": {"path": "/view/point"},
        },
        True,
        id="section-full",
    ),
    pytest.param(
        SectionComponent, {"id": "s", "component": "clio.section.v1"}, False, id="section-no-uri"
    ),
    pytest.param(
        SectionComponent,
        {"id": "s", "component": "clio.section.v1", "sectionUri": GRID, "contourInterval": 0},
        False,
        id="section-zero-interval",
    ),
    pytest.param(
        ProfileStackComponent,
        {
            "id": "p",
            "component": "clio.profile-stack.v1",
            "dataUri": TABLE,
            "profileField": "profile",
            "verticalField": "pressure",
            "valueField": "CT",
            "variables": ["CT", "SA"],
            "overlayField": "model",
            "excluded": {"path": "/view/excluded"},
        },
        True,
        id="profiles-uri",
    ),
    pytest.param(
        ProfileStackComponent,
        {
            "id": "p",
            "component": "clio.profile-stack.v1",
            "data": [{"profile": "a", "pressure": 10, "CT": 20.1}],
            "profileField": "profile",
            "verticalField": "pressure",
            "valueField": "CT",
        },
        True,
        id="profiles-inline",
    ),
    pytest.param(
        ProfileStackComponent,
        {
            "id": "p",
            "component": "clio.profile-stack.v1",
            "data": [{"profile": "a"}],
            "dataUri": TABLE,
            "profileField": "profile",
            "verticalField": "pressure",
            "valueField": "CT",
        },
        False,
        id="profiles-both",
    ),
    pytest.param(
        ProfileStackComponent,
        {
            "id": "p",
            "component": "clio.profile-stack.v1",
            "profileField": "profile",
            "verticalField": "pressure",
            "valueField": "CT",
        },
        False,
        id="profiles-neither",
    ),
    pytest.param(
        ProfileStackComponent,
        {
            "id": "p",
            "component": "clio.profile-stack.v1",
            "dataUri": TABLE,
            "verticalField": "pressure",
            "valueField": "CT",
        },
        False,
        id="profiles-no-profile-field",
    ),
]


@pytest.mark.parametrize(("model", "payload", "valid"), CASES)
def test_schema_and_model_agree(model: Any, payload: dict[str, Any], valid: bool) -> None:  # noqa: FBT001
    assert VALIDATORS[payload["component"]].is_valid(payload) == valid
    if valid:
        model.model_validate(payload)
    else:
        with pytest.raises(ValidationError):
            model.model_validate(payload)


def test_model_only_cross_rules() -> None:
    """Rules JSON Schema does not express: bound time/selection need their field, unique ids."""
    with pytest.raises(ValidationError, match="timeField"):
        LayeredMapComponent.model_validate(
            _map(layers=[GRID_LAYER], time={"path": "/selection/time"})
        )
    with pytest.raises(ValidationError, match="unique"):
        LayeredMapComponent.model_validate(_map(layers=[GRID_LAYER, GRID_LAYER]))
    with pytest.raises(ValidationError, match="edits"):
        LayeredMapComponent.model_validate(_map(layers=[STATIONS]))
    with pytest.raises(ValidationError, match="valueRange"):
        LayeredMapComponent.model_validate(_map(layers=[{**GRID_LAYER, "valueRange": [3, -3]}]))


def test_catalog_documents_every_new_property() -> None:
    catalog = render_workspace_catalog()
    for name in ("clio.layered-map.v1", "clio.section.v1", "clio.profile-stack.v1"):
        schema = catalog["components"][name]
        assert schema["description"]
        props = schema["allOf"][2]["properties"]
        undocumented = [
            k
            for k, v in props.items()
            if k
            not in (
                "component",
                "title",
                "action",
                "actionLabel",
                "height",
                "dataQuery",
                "layers",
                "draw",
                "camera",
                "invertVertical",
            )
            and "description" not in v
            and "$ref" not in v
        ]
        assert not undocumented, (name, undocumented)
