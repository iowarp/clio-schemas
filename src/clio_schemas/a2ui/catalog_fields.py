"""Catalog definitions for the field components: layered map, section, profile stack.

Hand-authored JSON Schema mirroring ``LayeredMapComponent``,
``SectionComponent`` and ``ProfileStackComponent``
(``a2ui/v0_9_1/field_components.py``): bounded lists, per-kind layer rules and
the "exactly one of inline rows or ``dataUri``" rule as ``oneOf``/``allOf``
branches. Kept out of ``catalog_bounded.py`` so that module does not grow.
"""

from __future__ import annotations

from typing import Any

from clio_schemas.a2ui.catalog_render import COMMON_TYPES_ID
from clio_schemas.a2ui.v0_9_1.components import ARTIFACT_URI_PATTERN, TABLE_DATA_URI_PATTERN
from clio_schemas.a2ui.v0_9_1.field_components import (
    FIELD_COLORMAPS,
    LAYER_ID_PATTERN,
    MAX_INLINE_PROFILE_ROWS,
    MAX_MAP_LAYERS,
    MAX_SWITCH_VARIABLES,
)

_SELECTION = (
    "Bind to /selection/<key>; the bound value is a SelectionState ({field, values[], source?}). "
    "Views bound to the same path share one selection."
)
_FIELD = {"$ref": "#/$defs/FieldName"}
_COLORMAP = {
    "type": "string",
    "enum": list(FIELD_COLORMAPS),
    "description": "Colour ramp; balance is diverging (anomalies, biases).",
}
_RANGE = {
    "type": "array",
    "minItems": 2,
    "maxItems": 2,
    "items": {"type": "number"},
    "description": "[low, high] of the colour scale.",
}
_HEIGHT = {"type": "integer", "minimum": 160, "maximum": 2000}
_BINDING = {"$ref": f"{COMMON_TYPES_ID}#/$defs/DataBinding"}
_VARIABLES = {
    "type": "array",
    "minItems": 1,
    "maxItems": MAX_SWITCH_VARIABLES,
    "uniqueItems": True,
    "items": _FIELD,
    "description": "Variables the person can switch between.",
}
_GRID_URI = {"type": "string", "pattern": ARTIFACT_URI_PATTERN, "not": {"pattern": r"\s"}}
_TABLE_URI = {"type": "string", "pattern": TABLE_DATA_URI_PATTERN, "not": {"pattern": r"\s"}}


def _field(description: str) -> dict[str, Any]:
    return {"$ref": "#/$defs/FieldName", "description": description}


_MAP_LAYER_DEF: dict[str, Any] = {
    "type": "object",
    "description": "One map layer: a grid (raster tiles), points, tracks or shapes (GeoJSON).",
    "properties": {
        "id": {"type": "string", "pattern": LAYER_ID_PATTERN},
        "kind": {"type": "string", "enum": ["grid", "points", "tracks", "shapes"]},
        "label": {"type": "string", "minLength": 1, "maxLength": 80},
        "visible": {"type": "boolean", "default": True},
        "opacity": {"type": "number", "minimum": 0, "maximum": 1, "default": 1},
        "gridUri": {
            **_GRID_URI,
            "description": (
                "Registered NetCDF or zipped Zarr grid with longitude and latitude, "
                "or a GeoTIFF, COG, VRT or IMG in any CRS (grid layers)."
            ),
        },
        "variable": _field(
            "Grid variable to draw; for a raster, the band (number, bandN or description)."
        ),
        "timeDimension": _field("Grid dimension the shared time selects (default time)."),
        "fixed": {
            "type": "object",
            "maxProperties": 8,
            "additionalProperties": {"type": ["string", "number"]},
            "description": "Other leading dimensions held at one value, e.g. {level: 500}.",
        },
        "dataUri": {**_TABLE_URI, "description": "Registered table of points or track positions."},
        "dataQuery": {"$ref": "#/$defs/DataQuery"},
        "latitudeField": _field("Column holding latitude."),
        "longitudeField": _field("Column holding longitude."),
        "idField": _field("Column holding each feature's stable id (selection, edits)."),
        "labelField": _field("Column holding each feature's label."),
        "timeField": _field(
            "Column holding each row's time; rows after the shared time are hidden."
        ),
        "trackField": _field("Column identifying each track (tracks layers)."),
        "categoryField": _field("Column whose values colour features by category."),
        "valueField": _field("Numeric column for a continuous colour scale."),
        "editable": {
            "type": "boolean",
            "default": False,
            "description": (
                "The person can move these points; moves are written to the map's edits path."
            ),
        },
        "geojsonUri": {
            **_GRID_URI,
            "description": "Registered GeoJSON FeatureCollection (shapes layers).",
        },
        "colormap": _COLORMAP,
        "valueRange": _RANGE,
        "unit": {
            "type": "string",
            "maxLength": 40,
            "description": "Unit shown on the layer's legend.",
        },
    },
    "required": ["id", "kind", "label"],
    "additionalProperties": False,
    "allOf": [
        {
            "if": {"properties": {"kind": {"const": "grid"}}},
            "then": {
                "required": ["gridUri", "variable"],
                "not": {"anyOf": [{"required": ["dataUri"]}, {"required": ["geojsonUri"]}]},
            },
        },
        {
            "if": {"properties": {"kind": {"const": "points"}}},
            "then": {
                "required": ["dataUri", "latitudeField", "longitudeField", "idField"],
                "not": {"anyOf": [{"required": ["gridUri"]}, {"required": ["geojsonUri"]}]},
            },
        },
        {
            "if": {"properties": {"kind": {"const": "tracks"}}},
            "then": {
                "required": [
                    "dataUri",
                    "latitudeField",
                    "longitudeField",
                    "idField",
                    "trackField",
                    "timeField",
                ],
                "not": {
                    "anyOf": [
                        {"required": ["gridUri"]},
                        {"required": ["geojsonUri"]},
                        {"properties": {"editable": {"const": True}}, "required": ["editable"]},
                    ]
                },
            },
        },
        {
            "if": {"properties": {"kind": {"const": "shapes"}}},
            "then": {
                "required": ["geojsonUri"],
                "not": {
                    "anyOf": [
                        {"required": ["gridUri"]},
                        {"required": ["dataUri"]},
                        {"properties": {"editable": {"const": True}}, "required": ["editable"]},
                    ]
                },
            },
        },
        {
            "if": {"properties": {"kind": {"const": "grid"}}},
            "then": {
                "not": {"properties": {"editable": {"const": True}}, "required": ["editable"]}
            },
        },
    ],
    "dependentRequired": {"dataQuery": ["dataUri"]},
}

_LAYERED_MAP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "Gridded fields, points, tracks and shapes on one flat map with a shared time axis; "
        "the person scrubs time, selects features, draws a box, path or point, and moves points."
    ),
    "allOf": [
        {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
        {"$ref": "#/$defs/CatalogComponentCommon"},
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.layered-map.v1"},
                "title": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
                "camera": {
                    "oneOf": [{"$ref": "#/$defs/MapCamera"}, _BINDING],
                    "description": "Camera literal or binding; navigation updates a bound camera.",
                },
                "layers": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_MAP_LAYERS,
                    "items": {"$ref": "#/$defs/MapLayer"},
                    "description": "Layers, drawn bottom to top.",
                },
                "time": {
                    "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicValue",
                    "description": (
                        "The shared time: bind to /selection/<key>; the time scrubber writes it"
                        " and grid layers draw the nearest frame."
                    ),
                },
                "timeField": {
                    **_FIELD,
                    "description": (
                        "Field name the shared time's SelectionState uses (required when time "
                        "is bound)."
                    ),
                },
                "selection": {
                    "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicValue",
                    "description": _SELECTION,
                },
                "selectionField": {
                    **_FIELD,
                    "description": (
                        "Field the selected features' ids are written under (required when "
                        "selection is bound)."
                    ),
                },
                "draw": {"$ref": "#/$defs/MapDraw"},
                "edits": {
                    **_BINDING,
                    "description": (
                        "Where moved points are written: [{layer, id, longitude, latitude}]."
                    ),
                },
                "action": {"$ref": f"{COMMON_TYPES_ID}#/$defs/Action"},
                "actionLabel": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
                "height": _HEIGHT,
            },
            "required": ["component", "layers"],
        },
    ],
    "unevaluatedProperties": False,
}

_MAP_DRAW_DEF: dict[str, Any] = {
    "type": "object",
    "description": (
        "What the person may draw; the GeoJSON geometry (Polygon box, "
        "LineString path or Point) is written at value."
    ),
    "properties": {"mode": {"type": "string", "enum": ["box", "path", "point"]}, "value": _BINDING},
    "required": ["mode", "value"],
    "additionalProperties": False,
}

_SECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "A field along a path against depth, pressure or height, with contours "
        "and the stations along it."
    ),
    "allOf": [
        {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
        {"$ref": "#/$defs/CatalogComponentCommon"},
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.section.v1"},
                "title": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
                "sectionUri": {
                    **_GRID_URI,
                    "description": (
                        "Registered section NetCDF (dimensions distance and a vertical)."
                    ),
                },
                "variable": _field("Variable shown first."),
                "variables": _VARIABLES,
                "colormap": _COLORMAP,
                "valueRange": _RANGE,
                "unit": {
                    "type": "string",
                    "maxLength": 40,
                    "description": "Unit shown on the colour legend.",
                },
                "contourInterval": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Spacing of contour lines in the variable's units.",
                },
                "invertVertical": {
                    "type": "boolean",
                    "description": (
                        "Draw the vertical increasing downward (default: from the data)."
                    ),
                },
                "selection": {
                    "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicValue",
                    "description": _SELECTION,
                },
                "selectionField": {
                    **_FIELD,
                    "description": "Field the selected station's profile id is written under.",
                },
                "pointer": {
                    **_BINDING,
                    "description": (
                        "Where the clicked point {distance, vertical, value} is written."
                    ),
                },
                "height": _HEIGHT,
            },
            "required": ["component", "sectionUri"],
        },
    ],
    "unevaluatedProperties": False,
}

_PROFILE_STACK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "Many vertical profiles from a table against depth, pressure or height; the person toggles "
        "and excludes profiles, switches variable and compares an overlay column."
    ),
    "allOf": [
        {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
        {"$ref": "#/$defs/CatalogComponentCommon"},
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.profile-stack.v1"},
                "title": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
                "data": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_INLINE_PROFILE_ROWS,
                    "items": {
                        "type": "object",
                        "additionalProperties": {"type": ["string", "number", "boolean", "null"]},
                    },
                    "description": (
                        f"Inline rows (at most {MAX_INLINE_PROFILE_ROWS}); use dataUri for more."
                    ),
                },
                "dataUri": {
                    **_TABLE_URI,
                    "description": "Registered profile table, one row per sample.",
                },
                "dataQuery": {"$ref": "#/$defs/DataQuery"},
                "profileField": _field("Column identifying each profile."),
                "verticalField": _field("Column holding depth, pressure or height."),
                "valueField": _field("Column drawn first."),
                "variables": _VARIABLES,
                "overlayField": _field(
                    "Second value column drawn dashed on the same profiles (model against "
                    "observation)."
                ),
                "labelField": _field("Column holding a profile's label."),
                "categoryField": _field("Column colouring profiles by category."),
                "invertVertical": {"type": "boolean", "default": True},
                "unit": {
                    "type": "string",
                    "maxLength": 40,
                    "description": "Unit of the value axis.",
                },
                "verticalUnit": {
                    "type": "string",
                    "maxLength": 40,
                    "description": "Unit of the vertical axis (dbar, m, hPa).",
                },
                "selection": {
                    "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicValue",
                    "description": _SELECTION,
                },
                "selectionField": {
                    **_FIELD,
                    "description": "Field the selected profiles' ids are written under.",
                },
                "excluded": {
                    **_BINDING,
                    "description": (
                        "Where the ids of profiles the person excludes are written (a list)."
                    ),
                },
                "action": {"$ref": f"{COMMON_TYPES_ID}#/$defs/Action"},
                "actionLabel": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
                "height": _HEIGHT,
            },
            "required": ["component", "profileField", "verticalField", "valueField"],
            "dependentRequired": {"dataQuery": ["dataUri"]},
        },
        {
            "description": "Exactly one of data or dataUri is required.",
            "oneOf": [
                {"required": ["data"], "not": {"required": ["dataUri"]}},
                {"required": ["dataUri"], "not": {"required": ["data"]}},
            ],
        },
    ],
    "unevaluatedProperties": False,
}


def field_components() -> tuple[dict[str, Any], dict[str, Any]]:
    """The three field components and their local ``$defs``."""
    components = {
        "clio.layered-map.v1": _LAYERED_MAP_SCHEMA,
        "clio.section.v1": _SECTION_SCHEMA,
        "clio.profile-stack.v1": _PROFILE_STACK_SCHEMA,
    }
    return components, {"MapLayer": _MAP_LAYER_DEF, "MapDraw": _MAP_DRAW_DEF}
