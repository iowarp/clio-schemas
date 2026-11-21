"""Model-written surfaces: no chart links, one level of GeoJSON collections, a closed theme."""

from __future__ import annotations

from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import TypeAdapter, ValidationError

from clio_schemas.a2ui.catalog_export import render_workspace_catalog
from clio_schemas.a2ui.v0_9_1.bounded_components import GeoJsonGeometry
from clio_schemas.a2ui.validation import catalog_validators, message_validator

WORKSPACE = render_workspace_catalog()
ENCODING = {
    "x": {"field": "t", "type": "quantitative"},
    "y": {"field": "v", "type": "quantitative"},
}


def _chart(spec: dict[str, Any]) -> dict[str, Any]:
    return {"id": "c", "component": "clio.chart.v1", "data": [{"t": 0, "v": 1}], "spec": spec}


@pytest.mark.parametrize(
    "spec",
    [
        {"mark": {"type": "point", "href": "javascript:alert(1)"}, "encoding": ENCODING},
        {"mark": "point", "encoding": {**ENCODING, "href": {"field": "v", "type": "nominal"}}},
    ],
)
def test_a_chart_spec_names_no_link(spec: dict[str, Any]) -> None:
    chart = catalog_validators(WORKSPACE)["clio.chart.v1"]
    assert chart.is_valid(_chart({"mark": "point", "encoding": ENCODING}))
    assert not chart.is_valid(_chart(spec))


POINT = {"type": "Point", "coordinates": [0, 0]}
FLAT = {"type": "GeometryCollection", "geometries": [POINT]}
NESTED = {"type": "GeometryCollection", "geometries": [FLAT]}


def test_a_geometry_collection_holds_no_collection() -> None:
    models = TypeAdapter(GeoJsonGeometry)
    schema = Draft202012Validator({"$ref": "#/$defs/GeoJsonGeometry", "$defs": WORKSPACE["$defs"]})
    models.validate_python(FLAT)
    assert schema.is_valid(FLAT)
    with pytest.raises(ValidationError):
        models.validate_python(NESTED)
    assert not schema.is_valid(NESTED)


def test_deep_nesting_is_a_validation_error_not_a_crash() -> None:
    deep: dict[str, Any] = POINT
    for _ in range(400):
        deep = {"type": "GeometryCollection", "geometries": [deep]}
    schema = Draft202012Validator({"$ref": "#/$defs/GeoJsonGeometry", "$defs": WORKSPACE["$defs"]})
    assert not schema.is_valid(deep)
    with pytest.raises(ValidationError):
        TypeAdapter(GeoJsonGeometry).validate_python(deep)


@pytest.mark.parametrize(
    "theme",
    [
        {"primaryColor": "#000000", "agentDisplayName": "CLIO Security"},
        {"iconUrl": "javascript:alert(1)"},
        {"anything": 1},
    ],
)
def test_the_theme_takes_only_a_color(theme: dict[str, Any]) -> None:
    validator = message_validator("server_to_client.json", catalog=WORKSPACE)

    def message(value: dict[str, Any]) -> dict[str, Any]:
        create = {"surfaceId": "s", "catalogId": WORKSPACE["catalogId"], "theme": value}
        return {"version": "v0.9.1", "createSurface": create}

    assert validator.is_valid(message({"primaryColor": "#000000"}))
    assert not validator.is_valid(message(theme))
