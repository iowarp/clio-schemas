"""Hand-authored catalog definitions for the 7 bounded/cross-field components.

``clio.map.v1``, ``clio.data-table.v1``, ``clio.code.v1``, ``clio.mermaid.v1``,
``clio.diff.v1``, ``clio.workflow.v1``, and ``clio.chart.v1`` mirror
``MapComponent`` / ``DataTableComponent`` / ``CodeComponent`` /
``MermaidComponent`` / ``DiffComponent`` / ``WorkflowComponent`` /
``ChartComponent`` (``a2ui/v0_9_1/bounded_components.py``): bounded list
lengths and "exactly one of inline values or ``dataUri``" cross-field rules
expressed as extra ``oneOf``/``allOf`` branches. The chart's per-preset
required fields are derived from the shipped preset templates. Most of the
Vega-Lite spec guard IS expressible in JSON Schema and is included on
``spec`` below: the top-level key allowlist (``propertyNames``), a recursive
ban on ``url``/``usermeta`` keys at any depth (``$defs/SpecNoForbiddenKeys``),
a recursive ban on ``element`` inside any ``bind`` object at any depth
(``$defs/SpecNoBindElement`` — ``bind.element`` is a CSS selector that could
mount a Vega input widget into any element of the host page), and the rule
that every ``data`` key at any depth is absent or exactly ``{"name":
"source"}`` (``$defs/SpecDataNamedSource``). Three rules are NOT expressible
in plain JSON Schema and stay pydantic/renderer-only: the serialized-size cap
(65536 UTF-8 bytes — JSON Schema has no "byte length of my own re-encoding"
assertion), the UTF-8-encodability of that same serialisation (a lone
surrogate is a JSON Schema ``string``, just not a valid UTF-8 one), and the
view-composition count (recursively counting mark-bearing views across
``layer``/``concat``/``facet``/``repeat`` — JSON Schema cannot count matches
across a recursive structure). All three still run in
:mod:`clio_schemas.a2ui.chart_spec`, in the pydantic model and the renderer.
These are not built through the generic canonicaliser
(``catalog_render.py``) because ``Field(min_length=/max_length=)`` bounds and
cross-field ``model_validator``s are pydantic *business rules*, not
field-type shapes.

``clio.chart.v1``'s ``data`` cell type IS fully expressible in JSON Schema,
though: a cell is a scalar OR a strictly-shaped GeoJSON Geometry object
(``$defs/GeoJsonGeometry``, a ``oneOf`` keyed on ``type``, mirroring
``bounded_components.GeoJsonGeometry``'s discriminated pydantic union) — so a
``geoshape`` mark can draw real shapes from inline rows (issue #1549 G4,
owner ruling). Reading geometry from a ``.geojson`` artifact by ``dataUri``
is a later slice (#1549 G7).

Every data-carrying component here follows one contract (the
``a2ui-component-design`` skill's rule #1): inline values OR ``dataUri``,
never both, never neither. The three tabular ones (map, table, chart) share
one ``$defs/DataQuery`` shape — reused, never duplicated per component.
"""

from __future__ import annotations

from typing import Any

from clio_schemas.a2ui.catalog_render import COMMON_TYPES_ID
from clio_schemas.a2ui.chart_spec import (
    ALLOWED_TOP_LEVEL_KEYS,
    DEFAULT_SELECTION_PARAM,
    MAX_INLINE_ROWS,
    PRESET_NAMES,
    SELECTION_PARAM_PATTERN,
    X_TYPES,
    load_preset,
)
from clio_schemas.a2ui.v0_9_1.bounded_components import (
    CHART_PRESET_FIELDS,
    DEFAULT_QUERY_PER_ENTITY,
    MAX_CHART_HEIGHT,
    MAX_FIELD_NAME_LENGTH,
    MAX_QUERY_COLUMNS,
    MAX_QUERY_FILTERS,
    MAX_QUERY_IN_VALUES,
    MAX_QUERY_LIMIT,
    MAX_QUERY_METRICS,
    MAX_QUERY_PER_ENTITY,
    MIN_CHART_HEIGHT,
)
from clio_schemas.a2ui.v0_9_1.components import (
    ARTIFACT_URI_PATTERN,
    MAX_MAP_POINTS,
    MAX_SELECTION_VALUES,
    MAX_WORKFLOW_EDGES,
    MAX_WORKFLOW_NODES,
)

_SELECTION_DESCRIPTION = (
    "Bind to /selection/<key>; the bound value is a SelectionState "
    "({field, values[], source?}, see $defs/SelectionState). Components bound to the "
    "same path share one selection."
)
#: selectionField names the dataset column a bound selection's values are drawn from.
#: Required whenever selection is a binding/function-call object (linking to another
#: component) — never when it is a literal (e.g. clio.data-table.v1's legacy plain
#: string selection modes, which are not a link and need no field name). The chart
#: does not need this rule: its selectionField already falls back to the preset's
#: entityField.
_SELECTION_FIELD_REQUIRED_WHEN_BOUND_RULE: dict[str, Any] = {
    "description": "selectionField is required when selection is bound (an object, not a literal).",
    "if": {
        "properties": {"selection": {"type": "object"}},
        "required": ["selection"],
    },
    "then": {"required": ["selectionField"]},
}
_DATA_URI_DESCRIPTION = (
    "A workspace file path or artifact:// reference; CLIO registers a path as an "
    "artifact before validation."
)
_DATA_QUERY_REF: dict[str, Any] = {"$ref": "#/$defs/DataQuery"}


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    """Wrap a property schema so JSON Schema also accepts an explicit ``null``.

    Matches a pydantic ``X | None = None`` field: the property may be omitted
    OR explicitly ``null`` OR a value of the wrapped shape. Without this, a
    client that writes ``{"aggregate": null}`` to explicitly clear a field
    passes pydantic (``Optional`` accepts ``None``) but fails a schema whose
    property is a bare ``$ref``/object shape with no ``null`` alternative.
    ``description``, if present on ``schema``, moves to the wrapper so it
    still describes the property regardless of which branch matched.
    """

    schema = dict(schema)
    description = schema.pop("description", None)
    wrapped: dict[str, Any] = {"anyOf": [schema, {"type": "null"}]}
    if description is not None:
        wrapped["description"] = description
    return wrapped


# Recursive rules for clio.chart.v1's `spec` (a Vega-Lite document): applied
# to every node regardless of depth, mirroring chart_spec.py's `_walk`. Both
# are pure structural JSON Schema (no size/count assertions needed), so
# clio-agent's JSON-Schema-only validation can enforce them without running
# clio_schemas.a2ui.chart_spec at all — see the module docstring.
_SPEC_NO_FORBIDDEN_KEYS_DEF: dict[str, Any] = {
    "description": "No `url` or `usermeta` key anywhere in a Vega-Lite spec, at any depth.",
    "if": {"type": "object"},
    "then": {
        "not": {"anyOf": [{"required": ["url"]}, {"required": ["usermeta"]}]},
        "additionalProperties": {"$ref": "#/$defs/SpecNoForbiddenKeys"},
    },
    "else": {
        "if": {"type": "array"},
        "then": {"items": {"$ref": "#/$defs/SpecNoForbiddenKeys"}},
    },
}
_SPEC_DATA_NAMED_SOURCE_DEF: dict[str, Any] = {
    "description": (
        "Every `data` key anywhere in a Vega-Lite spec is absent or exactly "
        '{"name": "source"} — rows come from the component\'s data/dataUri, never the spec.'
    ),
    "if": {"type": "object"},
    "then": {
        "properties": {"data": {"const": {"name": "source"}}},
        "additionalProperties": {"$ref": "#/$defs/SpecDataNamedSource"},
    },
    "else": {
        "if": {"type": "array"},
        "then": {"items": {"$ref": "#/$defs/SpecDataNamedSource"}},
    },
}
_SPEC_NO_BIND_ELEMENT_DEF: dict[str, Any] = {
    "description": (
        "No `element` key inside any `bind` object (params[].bind.element) anywhere in a "
        "Vega-Lite spec, at any depth — it is a CSS selector that could mount a Vega input "
        "widget into any element on the host page, not just this chart."
    ),
    "if": {"type": "object"},
    "then": {
        "properties": {
            "bind": {
                "allOf": [
                    {"if": {"type": "object"}, "then": {"not": {"required": ["element"]}}},
                    {"$ref": "#/$defs/SpecNoBindElement"},
                ]
            }
        },
        "additionalProperties": {"$ref": "#/$defs/SpecNoBindElement"},
    },
    "else": {
        "if": {"type": "array"},
        "then": {"items": {"$ref": "#/$defs/SpecNoBindElement"}},
    },
}

# --------------------------------------------------------------------------- #
# GeoJSON geometry cells (clio.chart.v1 inline rows, issue #1549 G4 — owner
# ruling: geoshape must actually draw over inline data). Mirrors the pydantic
# geometry models (clio_schemas.a2ui.v0_9_1.bounded_components.GeoJsonGeometry)
# strictly: a `oneOf` keyed on `type`, each branch closed
# (`additionalProperties: False`) with the exact RFC 7946 §3.1 coordinate
# nesting for that type. Never a Feature/FeatureCollection; reading geometry
# from a `.geojson` artifact by dataUri is a later slice (#1549 G7).
# --------------------------------------------------------------------------- #
_GEOJSON_POSITION_DEF: dict[str, Any] = {
    "type": "array",
    "items": {"type": "number"},
    "minItems": 2,
    "maxItems": 3,
}


def _geojson_ring_array(min_items: int) -> dict[str, Any]:
    return {"type": "array", "items": _GEOJSON_POSITION_DEF, "minItems": min_items}


_GEOJSON_GEOMETRY_DEF: dict[str, Any] = {
    "type": "object",
    "description": (
        "A GeoJSON Geometry object (RFC 7946 §3.1), strictly shaped: Point/MultiPoint/"
        "LineString/MultiLineString/Polygon/MultiPolygon carry coordinates; GeometryCollection "
        "carries geometries. Never a Feature/FeatureCollection, never a bare coordinate array."
    ),
    "oneOf": [
        {
            "type": "object",
            "properties": {"type": {"const": "Point"}, "coordinates": _GEOJSON_POSITION_DEF},
            "required": ["type", "coordinates"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "MultiPoint"},
                "coordinates": {"type": "array", "items": _GEOJSON_POSITION_DEF},
            },
            "required": ["type", "coordinates"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {"type": {"const": "LineString"}, "coordinates": _geojson_ring_array(2)},
            "required": ["type", "coordinates"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "MultiLineString"},
                "coordinates": {"type": "array", "items": _geojson_ring_array(2)},
            },
            "required": ["type", "coordinates"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "Polygon"},
                "coordinates": {"type": "array", "items": _geojson_ring_array(4)},
            },
            "required": ["type", "coordinates"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "MultiPolygon"},
                "coordinates": {
                    "type": "array",
                    "items": {"type": "array", "items": _geojson_ring_array(4)},
                },
            },
            "required": ["type", "coordinates"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "GeometryCollection"},
                "geometries": {"type": "array", "items": {"$ref": "#/$defs/GeoJsonGeometry"}},
            },
            "required": ["type", "geometries"],
            "additionalProperties": False,
        },
    ],
}

_MAP_POINT_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "minLength": 1, "maxLength": 128},
        "label": {"type": "string", "minLength": 1, "maxLength": 240},
        "latitude": {"type": "number", "minimum": -90, "maximum": 90},
        "longitude": {"type": "number", "minimum": -180, "maximum": 180},
        "detail": {"type": "string", "maxLength": 2000},
        "category": {
            "type": "string",
            "maxLength": 120,
            "description": "Nominal group, such as station type. Use value for measured numbers.",
        },
        "value": {
            "type": "number",
            "description": "Optional measured magnitude for a continuous colour scale and legend.",
        },
    },
    "required": ["id", "label", "latitude", "longitude"],
    "additionalProperties": False,
}

_MAP_COMPONENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Interactive points, ordered trajectories, or GeoJSON geometry on a map.",
    "allOf": [
        {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
        {"$ref": "#/$defs/CatalogComponentCommon"},
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.map.v1"},
                "title": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
                "points": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_MAP_POINTS,
                    "items": {"$ref": "#/$defs/MapPoint"},
                    "description": (
                        f"Inline points (at most {MAX_MAP_POINTS}) — this array rides the "
                        "surface's own wire message, so it is capped for transfer size; "
                        "for a larger dataset use dataUri instead, unbounded and "
                        "paged/downsampled by the viewer."
                    ),
                },
                "dataUri": {
                    "type": "string",
                    "pattern": ARTIFACT_URI_PATTERN,
                    "not": {"pattern": r"\s"},
                    "description": (
                        f"{_DATA_URI_DESCRIPTION} Requires latitudeField/longitudeField/"
                        "labelField; a referenced dataset is bounded by dataQuery/limit, "
                        "not the inline point cap."
                    ),
                },
                "geojsonUri": {
                    "type": "string",
                    "pattern": ARTIFACT_URI_PATTERN,
                    "not": {"pattern": r"\s"},
                    "description": (
                        "Artifact URI of a GeoJSON FeatureCollection. Geometry is read by "
                        "reference and drawn as points, lines, and polygons; feature properties "
                        "supply labelField, categoryField, or valueField when named."
                    ),
                },
                "dataQuery": _DATA_QUERY_REF,
                "latitudeField": {
                    "$ref": "#/$defs/FieldName",
                    "description": "Dataset column holding latitude (required with dataUri).",
                },
                "longitudeField": {
                    "$ref": "#/$defs/FieldName",
                    "description": "Dataset column holding longitude (required with dataUri).",
                },
                "labelField": {
                    "$ref": "#/$defs/FieldName",
                    "description": (
                        "Dataset column holding each point's label (required with dataUri)."
                    ),
                },
                "idField": {
                    "$ref": "#/$defs/FieldName",
                    "description": "Dataset column holding each point's stable id.",
                },
                "trackField": {
                    "$ref": "#/$defs/FieldName",
                    "description": (
                        "With dataUri, column identifying each trajectory (for example "
                        "storm_id). Rows with the same value form one path."
                    ),
                },
                "orderField": {
                    "$ref": "#/$defs/FieldName",
                    "description": (
                        "With trackField, time or numeric sequence column ordering "
                        "positions along each trajectory."
                    ),
                },
                "filterFields": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 12,
                    "uniqueItems": True,
                    "items": {"$ref": "#/$defs/FieldName"},
                    "description": (
                        "With dataUri, columns worth filtering while exploring this map. "
                        "Choose one or more real columns from the task and dataset, such as a "
                        "category, magnitude, or time column. Use a registered table even for "
                        "small maps when these native filters matter. The viewer creates typed "
                        "controls and applies them to "
                        "the map and Reference this; omit for the viewer's default fields."
                    ),
                },
                "detailField": {
                    "$ref": "#/$defs/FieldName",
                    "description": "Dataset column holding each point's detail text.",
                },
                "categoryField": {
                    "$ref": "#/$defs/FieldName",
                    "description": "Dataset column grouping points into categories.",
                },
                "valueField": {
                    "$ref": "#/$defs/FieldName",
                    "description": (
                        "Numeric dataset column used for a continuous colour scale and legend."
                    ),
                },
                "valueLabel": {
                    "type": "string",
                    "maxLength": 80,
                    "description": (
                        "Human-readable name for the numeric map legend, such as Displacement."
                    ),
                },
                "valueUnit": {
                    "type": "string",
                    "maxLength": 40,
                    "description": "Unit shown beside a continuous-colour legend's values.",
                },
                "selected": {"type": "string", "maxLength": 128},
                "selection": {
                    "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicValue",
                    "description": _SELECTION_DESCRIPTION,
                },
                "selectionField": {
                    "$ref": "#/$defs/FieldName",
                    "description": (
                        "Dataset column the shared selection's values are drawn from; "
                        "required when selection is bound."
                    ),
                },
                "action": {"$ref": f"{COMMON_TYPES_ID}#/$defs/Action"},
                "actionLabel": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
            },
            "required": ["component"],
            "dependentRequired": {
                "dataQuery": ["dataUri"],
                "trackField": ["dataUri", "orderField"],
                "orderField": ["trackField"],
                "filterFields": ["dataUri"],
            },
        },
        {
            "description": "Exactly one of points, dataUri, or geojsonUri is required.",
            "oneOf": [
                {
                    "required": ["points"],
                    "not": {"anyOf": [{"required": ["dataUri"]}, {"required": ["geojsonUri"]}]},
                },
                {
                    "required": ["dataUri"],
                    "not": {"anyOf": [{"required": ["points"]}, {"required": ["geojsonUri"]}]},
                },
                {
                    "required": ["geojsonUri"],
                    "not": {"anyOf": [{"required": ["points"]}, {"required": ["dataUri"]}]},
                },
            ],
        },
        {
            "description": "dataUri requires the point field names.",
            "if": {"required": ["dataUri"]},
            "then": {"required": ["latitudeField", "longitudeField", "labelField"]},
        },
        {"not": {"required": ["categoryField", "valueField"]}},
        _SELECTION_FIELD_REQUIRED_WHEN_BOUND_RULE,
    ],
    "unevaluatedProperties": False,
}

_WORKFLOW_NODE_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "label": {"type": "string"},
        "state": {"type": "string"},
        "detail": {"type": "string"},
    },
    "required": ["id", "label"],
    "additionalProperties": False,
}

_WORKFLOW_EDGE_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {
        "source": {"type": "string"},
        "target": {"type": "string"},
        "label": {"type": "string"},
    },
    "required": ["source", "target"],
    "additionalProperties": False,
}

_WORKFLOW_COMPONENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A step/edge graph showing a multi-step plan's progress.",
    "allOf": [
        {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
        {"$ref": "#/$defs/CatalogComponentCommon"},
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.workflow.v1"},
                "nodes": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_WORKFLOW_NODES,
                    "items": {"$ref": "#/$defs/WorkflowNode"},
                    "description": (
                        f"Inline nodes (at most {MAX_WORKFLOW_NODES}) — rides the surface's own "
                        "wire message; give edges too, or use dataUri instead of both for a "
                        "larger graph, unbounded."
                    ),
                },
                "edges": {
                    "type": "array",
                    "maxItems": MAX_WORKFLOW_EDGES,
                    "items": {"$ref": "#/$defs/WorkflowEdge"},
                    "description": f"Inline edges (at most {MAX_WORKFLOW_EDGES}), alongside nodes.",
                },
                "dataUri": {
                    "type": "string",
                    "pattern": ARTIFACT_URI_PATTERN,
                    "not": {"pattern": r"\s"},
                    "description": (
                        f'{_DATA_URI_DESCRIPTION} A JSON file shaped {{"nodes": [...], '
                        '"edges": [...]}.'
                    ),
                },
                "selected": {"type": "string"},
                "action": {"$ref": f"{COMMON_TYPES_ID}#/$defs/Action"},
            },
            "required": ["component"],
        },
        {
            "description": "Exactly one of nodes+edges or dataUri is required.",
            "oneOf": [
                {"required": ["nodes", "edges"], "not": {"required": ["dataUri"]}},
                {
                    "required": ["dataUri"],
                    "not": {"anyOf": [{"required": ["nodes"]}, {"required": ["edges"]}]},
                },
            ],
        },
    ],
    "unevaluatedProperties": False,
}

_DATA_TABLE_COLUMN_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {"key": {"type": "string"}, "label": {"type": "string"}},
    "required": ["key", "label"],
    "additionalProperties": False,
}

_DATA_TABLE_COMPONENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Tabular rows, inline or from a referenced dataset.",
    "allOf": [
        {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
        {"$ref": "#/$defs/CatalogComponentCommon"},
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.data-table.v1"},
                "columns": {
                    "type": "array",
                    "items": {"oneOf": [{"type": "string"}, {"$ref": "#/$defs/DataTableColumn"}]},
                    "description": (
                        "Required with inline rows; optional with dataUri (defaults to the "
                        "queried/dataset columns)."
                    ),
                },
                "rows": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Inline rows; use dataUri instead for a registered dataset.",
                },
                "dataUri": {
                    "type": "string",
                    "pattern": ARTIFACT_URI_PATTERN,
                    "not": {"pattern": r"\s"},
                    "description": _DATA_URI_DESCRIPTION,
                },
                "dataQuery": _DATA_QUERY_REF,
                # DynamicValue (not a static string): bind it to /selection/<key>, whose
                # value is a SelectionState. A plain string stays valid (backward compatible).
                "selection": {
                    "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicValue",
                    "description": _SELECTION_DESCRIPTION,
                },
                "selectionField": {
                    "$ref": "#/$defs/FieldName",
                    "description": (
                        "Dataset column the shared selection's values are drawn from; "
                        "required when selection is bound."
                    ),
                },
                "action": {"$ref": f"{COMMON_TYPES_ID}#/$defs/Action"},
            },
            "required": ["component"],
            "dependentRequired": {"dataQuery": ["dataUri"]},
        },
        {
            "description": "Exactly one of rows or dataUri is required.",
            "oneOf": [
                {"required": ["rows"], "not": {"required": ["dataUri"]}},
                {"required": ["dataUri"], "not": {"required": ["rows"]}},
            ],
        },
        {
            "description": "columns is required alongside inline rows.",
            "if": {"required": ["rows"]},
            "then": {"required": ["columns"]},
        },
        _SELECTION_FIELD_REQUIRED_WHEN_BOUND_RULE,
    ],
    "unevaluatedProperties": False,
}

_CODE_COMPONENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Syntax-highlighted source, inline or from a referenced file.",
    "allOf": [
        {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
        {"$ref": "#/$defs/CatalogComponentCommon"},
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.code.v1"},
                "code": {
                    "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString",
                    "description": "Inline source; use dataUri instead for a referenced file.",
                },
                "dataUri": {
                    "type": "string",
                    "pattern": ARTIFACT_URI_PATTERN,
                    "not": {"pattern": r"\s"},
                    "description": f"{_DATA_URI_DESCRIPTION} Its file content is the source.",
                },
                "language": {"type": "string"},
                "title": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
            },
            "required": ["component", "language"],
        },
        {
            "description": "Exactly one of code or dataUri is required.",
            "oneOf": [
                {"required": ["code"], "not": {"required": ["dataUri"]}},
                {"required": ["dataUri"], "not": {"required": ["code"]}},
            ],
        },
    ],
    "unevaluatedProperties": False,
}

_MERMAID_COMPONENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A declarative Mermaid diagram, inline source or from a referenced file.",
    "allOf": [
        {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
        {"$ref": "#/$defs/CatalogComponentCommon"},
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.mermaid.v1"},
                "source": {
                    "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString",
                    "description": (
                        "Inline diagram source; use dataUri instead for a referenced file."
                    ),
                },
                "dataUri": {
                    "type": "string",
                    "pattern": ARTIFACT_URI_PATTERN,
                    "not": {"pattern": r"\s"},
                    "description": f"{_DATA_URI_DESCRIPTION} Its file content is the source.",
                },
                "title": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
            },
            "required": ["component"],
        },
        {
            "description": "Exactly one of source or dataUri is required.",
            "oneOf": [
                {"required": ["source"], "not": {"required": ["dataUri"]}},
                {"required": ["dataUri"], "not": {"required": ["source"]}},
            ],
        },
    ],
    "unevaluatedProperties": False,
}

_DIFF_COMPONENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A unified diff for one path, inline or from a referenced file.",
    "allOf": [
        {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
        {"$ref": "#/$defs/CatalogComponentCommon"},
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.diff.v1"},
                "path": {"type": "string"},
                "diff": {
                    "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString",
                    "description": (
                        "Inline unified diff text; use dataUri instead for a referenced file."
                    ),
                },
                "dataUri": {
                    "type": "string",
                    "pattern": ARTIFACT_URI_PATTERN,
                    "not": {"pattern": r"\s"},
                    "description": f"{_DATA_URI_DESCRIPTION} Its file content is the diff text.",
                },
                "status": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
                "action": {"$ref": f"{COMMON_TYPES_ID}#/$defs/Action"},
            },
            "required": ["component", "path"],
        },
        {
            "description": "Exactly one of diff or dataUri is required.",
            "oneOf": [
                {"required": ["diff"], "not": {"required": ["dataUri"]}},
                {"required": ["dataUri"], "not": {"required": ["diff"]}},
            ],
        },
    ],
    "unevaluatedProperties": False,
}


_SELECTION_STATE_DEF: dict[str, Any] = {
    "type": "object",
    "description": (
        "The value at a bound selection path (/selection/<key>): the selected values of "
        "one data field. source is the id of the component that made the selection."
    ),
    "properties": {
        "field": {"type": "string", "minLength": 1, "maxLength": 128},
        "values": {
            "type": "array",
            "maxItems": MAX_SELECTION_VALUES,
            "items": {"type": ["string", "number"]},
        },
        "source": {"type": "string", "minLength": 1, "maxLength": 128},
    },
    "required": ["field", "values"],
    "additionalProperties": False,
}

_FIELD_NAME_DEF: dict[str, Any] = {
    "type": "string",
    "minLength": 1,
    "maxLength": MAX_FIELD_NAME_LENGTH,
}
_QUERY_SCALAR: dict[str, Any] = {"type": ["string", "number", "boolean"]}


def _filter_op_rule(op: str, value: dict[str, Any], *, required: bool) -> dict[str, Any]:
    binding = {
        "type": "object",
        "properties": {"path": {"type": "string", "pattern": "^/"}},
        "required": ["path"],
        "additionalProperties": False,
    }
    then: dict[str, Any] = {"properties": {"value": {"anyOf": [value, binding]}}}
    if required:
        then["required"] = ["value"]
    return {"if": {"properties": {"op": {"const": op}}}, "then": then}


_QUERY_FILTER_DEF: dict[str, Any] = {
    "type": "object",
    "description": (
        "One predicate; all filter entries are AND-ed. eq: value is a non-null scalar. "
        "in: value is a non-empty list of scalars. range: value is [min, max], inclusive, "
        "either side may be null. isnull: value omitted or true matches nulls, false "
        "matches non-nulls. contains: value is a non-empty string, matched as a "
        "case-insensitive substring of a string column (a per-column text filter)."
    ),
    "properties": {
        "column": {"$ref": "#/$defs/FieldName"},
        "op": {"type": "string", "enum": ["eq", "in", "range", "isnull", "contains"]},
        "value": {},
    },
    "required": ["column", "op"],
    "additionalProperties": False,
    "allOf": [
        _filter_op_rule("eq", _QUERY_SCALAR, required=True),
        _filter_op_rule(
            "in",
            {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_QUERY_IN_VALUES,
                "items": _QUERY_SCALAR,
            },
            required=True,
        ),
        _filter_op_rule(
            "range",
            {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {"type": ["string", "number", "boolean", "null"]},
            },
            required=True,
        ),
        _filter_op_rule("isnull", {"type": ["boolean", "null"]}, required=False),
        _filter_op_rule("contains", {"type": "string", "minLength": 1}, required=True),
    ],
}

_QUERY_SORT_DEF: dict[str, Any] = {
    "type": "object",
    "description": "One dataQuery.sort key; earlier entries in the list sort first.",
    "properties": {
        "column": {"$ref": "#/$defs/FieldName"},
        "desc": {"type": "boolean", "default": False},
    },
    "required": ["column"],
    "additionalProperties": False,
}

_QUERY_AGGREGATE_DEF: dict[str, Any] = {
    "type": "object",
    "description": (
        "Group rows by groupBy (empty or omitted: one global group) and reduce; each "
        "metric becomes a result column named {column}_{fn}, which must not repeat a "
        "groupBy column."
    ),
    "properties": {
        "groupBy": {
            "type": "array",
            "maxItems": MAX_QUERY_COLUMNS,
            "uniqueItems": True,
            "items": {"$ref": "#/$defs/FieldName"},
        },
        "metrics": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_QUERY_METRICS,
            "uniqueItems": True,
            "items": {
                "type": "object",
                "properties": {
                    "column": {"$ref": "#/$defs/FieldName"},
                    "fn": {
                        "type": "string",
                        "enum": ["mean", "min", "max", "count", "sum", "median"],
                    },
                },
                "required": ["column", "fn"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["metrics"],
    "additionalProperties": False,
}

_QUERY_DOWNSAMPLE_DEF: dict[str, Any] = {
    "type": "object",
    "description": (
        "How the server thins rows before limit applies. none keeps every row; stride "
        "keeps evenly spaced rows (per entityColumn up to maxPerEntity when set, else "
        "overall up to limit); per_entity_lttb runs LTTB on (x, y) per entityColumn "
        "(the whole table is one series without it) and needs x and y."
    ),
    "properties": {
        "mode": {
            "type": "string",
            "enum": ["none", "stride", "per_entity_lttb"],
            "default": "none",
        },
        "entityColumn": _nullable({"$ref": "#/$defs/FieldName"}),
        "x": _nullable({"$ref": "#/$defs/FieldName"}),
        "y": _nullable({"$ref": "#/$defs/FieldName"}),
        "maxPerEntity": {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_QUERY_PER_ENTITY,
            "default": DEFAULT_QUERY_PER_ENTITY,
        },
    },
    "additionalProperties": False,
    "if": {"properties": {"mode": {"const": "per_entity_lttb"}}, "required": ["mode"]},
    "then": {
        # required checks presence only; explicitly ban null too, since a null x/y is
        # not a usable column name (matches the pydantic model_validator's rejection).
        "properties": {"x": {"not": {"type": "null"}}, "y": {"not": {"type": "null"}}},
        "required": ["x", "y"],
    },
}

_DATA_QUERY_DEF: dict[str, Any] = {
    "type": "object",
    "description": (
        "A server-side table query applied to dataUri: the table-query request body "
        "(POST /v1/artifacts/{id}/table-query) without format. The server runs filter, "
        "then aggregate, then downsample, then sort, then offset/limit. Omit columns to "
        "request every column of dataUri — except alongside aggregate, where columns is "
        "required, since aggregate's output columns (e.g. price_mean) don't exist in "
        "the source and so cannot be inferred. limit bounds the rows in ONE response (a "
        "transfer size), not the underlying data; offset pages through a larger result "
        "across several requests. When a chart or map query would otherwise exceed "
        "limit without an explicit downsample, the server instead samples evenly across "
        "the full range and reports that it did, rather than silently truncating to the "
        "first rows. limit's own maximum here is a generous safety ceiling, not the "
        "deployment's real per-response cap, which is server-configured. A viewer (e.g. "
        "an interactive data-table) may layer its own user-driven paging/filtering/"
        "sorting on top of this dataQuery without replacing it — the agent's own "
        "filter/aggregate/downsample intent still applies underneath. Shared verbatim by "
        "clio.chart.v1, clio.map.v1, and clio.data-table.v1."
    ),
    "properties": {
        "columns": _nullable(
            {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_QUERY_COLUMNS,
                "uniqueItems": True,
                "items": {"$ref": "#/$defs/FieldName"},
            }
        ),
        "filter": _nullable(
            {
                "type": "array",
                "maxItems": MAX_QUERY_FILTERS,
                "items": {"$ref": "#/$defs/QueryFilter"},
            }
        ),
        "aggregate": _nullable({"$ref": "#/$defs/QueryAggregate"}),
        "downsample": _nullable({"$ref": "#/$defs/QueryDownsample"}),
        "sort": _nullable(
            {
                "type": "array",
                "maxItems": MAX_QUERY_COLUMNS,
                "items": {"$ref": "#/$defs/QuerySort"},
            }
        ),
        "offset": _nullable({"type": "integer", "minimum": 0}),
        "limit": _nullable({"type": "integer", "minimum": 1, "maximum": MAX_QUERY_LIMIT}),
    },
    "additionalProperties": False,
    # Presence-and-non-null, not bare `dependentRequired`: an explicit `aggregate: null`
    # is the same as omitting it (see _nullable) and must not itself demand columns.
    "if": {
        "properties": {"aggregate": {"not": {"type": "null"}}},
        "required": ["aggregate"],
    },
    "then": {"required": ["columns"]},
}


def _chart_preset_rules() -> list[dict[str, Any]]:
    """One ``if preset == X then required/forbidden fields`` branch per shipped preset."""

    rules: list[dict[str, Any]] = []
    for name in PRESET_NAMES:
        document = load_preset(name)
        usable = set(document["requiredFields"]) | set(document["optionalFields"])
        unused = [field for field in CHART_PRESET_FIELDS if field not in usable]
        then: dict[str, Any] = {"required": list(document["requiredFields"])}
        if unused:
            then["not"] = {"anyOf": [{"required": [field]} for field in unused]}
        rules.append(
            {
                "description": f"Fields used by the {name} preset.",
                "if": {"properties": {"preset": {"const": name}}, "required": ["preset"]},
                "then": then,
            }
        )
    return rules


def _chart_component_schema() -> dict[str, Any]:
    fill_fields = {
        field: {"$ref": "#/$defs/FieldName"} for field in CHART_PRESET_FIELDS if field != "xType"
    }
    return {
        "type": "object",
        "description": "Any chart over tabular rows: a preset or an Altair/Vega-Lite spec.",
        "allOf": [
            {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
            {"$ref": "#/$defs/CatalogComponentCommon"},
            {
                "type": "object",
                "properties": {
                    "component": {"const": "clio.chart.v1"},
                    "spec": {
                        "type": "object",
                        "description": (
                            "A Vega-Lite spec whose rows come from data/dataUri as the named "
                            "dataset 'source' — the spec is chart configuration, never a data "
                            "channel, and the dataset itself is unbounded via dataUri regardless "
                            "of this cap. This schema already enforces the top-level key "
                            "allowlist, no url/usermeta key at any depth, no bind.element at any "
                            "depth (a CSS selector that could mount an input widget anywhere on "
                            "the host page), and data only as {name: source} at any depth; the "
                            "renderer additionally enforces the config-size (65536 bytes) and "
                            "view-count (8) caps that keep the spec itself bounded and "
                            "abuse-resistant, which JSON Schema cannot express. See "
                            "a2ui/chart/guard_rules.json."
                        ),
                        "propertyNames": {"enum": list(ALLOWED_TOP_LEVEL_KEYS)},
                        "allOf": [
                            {"$ref": "#/$defs/SpecNoForbiddenKeys"},
                            {"$ref": "#/$defs/SpecDataNamedSource"},
                            {"$ref": "#/$defs/SpecNoBindElement"},
                        ],
                    },
                    "preset": {"type": "string", "enum": list(PRESET_NAMES)},
                    **fill_fields,
                    "xType": {"type": "string", "enum": list(X_TYPES)},
                    "data": {
                        "type": "array",
                        "maxItems": MAX_INLINE_ROWS,
                        "items": {
                            "type": "object",
                            "additionalProperties": {
                                "anyOf": [
                                    {"type": ["string", "number", "boolean", "null"]},
                                    {"$ref": "#/$defs/GeoJsonGeometry"},
                                ]
                            },
                        },
                        "description": (
                            f"Inline rows (at most {MAX_INLINE_ROWS}) — this array rides the "
                            "surface's own wire message, so it is capped for transfer size; "
                            "for a larger or growing dataset use dataUri instead, unbounded "
                            "and paged/downsampled by the viewer. A cell is a scalar OR a "
                            "strictly-shaped GeoJSON Geometry object ($defs/GeoJsonGeometry), "
                            "so a geoshape mark can draw real shapes from inline rows."
                        ),
                    },
                    "dataUri": {
                        "type": "string",
                        "pattern": ARTIFACT_URI_PATTERN,
                        "not": {"pattern": r"\s"},
                        "description": _DATA_URI_DESCRIPTION,
                    },
                    "dataQuery": _DATA_QUERY_REF,
                    "selection": {
                        "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicValue",
                        "description": _SELECTION_DESCRIPTION,
                    },
                    "selectionParam": {
                        "type": "string",
                        "pattern": SELECTION_PARAM_PATTERN,
                        "default": DEFAULT_SELECTION_PARAM,
                    },
                    "selectionField": {
                        "$ref": "#/$defs/FieldName",
                        "description": (
                            "Column used for an explicit selection binding. Ordinary views "
                            "of one dataUri link by __row without this property; trajectory "
                            "and spectra points select exact rows while entityField groups "
                            "each curve."
                        ),
                    },
                    "title": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
                    "height": {
                        "type": "number",
                        "minimum": MIN_CHART_HEIGHT,
                        "maximum": MAX_CHART_HEIGHT,
                    },
                },
                "required": ["component"],
                "dependentRequired": {"dataQuery": ["dataUri"]},
            },
            {
                "description": "Exactly one of spec or preset; preset fill fields need preset.",
                "oneOf": [
                    {
                        "required": ["spec"],
                        "not": {
                            "anyOf": [
                                {"required": [field]} for field in ("preset", *CHART_PRESET_FIELDS)
                            ]
                        },
                    },
                    {"required": ["preset"], "not": {"required": ["spec"]}},
                ],
            },
            {
                "description": "Exactly one of data or dataUri is required.",
                "oneOf": [
                    {"required": ["data"], "not": {"required": ["dataUri"]}},
                    {"required": ["dataUri"], "not": {"required": ["data"]}},
                ],
            },
            *_chart_preset_rules(),
        ],
        "unevaluatedProperties": False,
    }


def hand_authored_components() -> tuple[dict[str, Any], dict[str, Any]]:
    """The 7 bounded components and their local ``$defs``."""

    components = {
        "clio.map.v1": _MAP_COMPONENT_SCHEMA,
        "clio.data-table.v1": _DATA_TABLE_COMPONENT_SCHEMA,
        "clio.code.v1": _CODE_COMPONENT_SCHEMA,
        "clio.mermaid.v1": _MERMAID_COMPONENT_SCHEMA,
        "clio.diff.v1": _DIFF_COMPONENT_SCHEMA,
        "clio.workflow.v1": _WORKFLOW_COMPONENT_SCHEMA,
        "clio.chart.v1": _chart_component_schema(),
    }
    defs = {
        "FieldName": _FIELD_NAME_DEF,
        "MapPoint": _MAP_POINT_DEF,
        "WorkflowNode": _WORKFLOW_NODE_DEF,
        "WorkflowEdge": _WORKFLOW_EDGE_DEF,
        "DataTableColumn": _DATA_TABLE_COLUMN_DEF,
        "SpecNoForbiddenKeys": _SPEC_NO_FORBIDDEN_KEYS_DEF,
        "SpecDataNamedSource": _SPEC_DATA_NAMED_SOURCE_DEF,
        "SpecNoBindElement": _SPEC_NO_BIND_ELEMENT_DEF,
        "GeoJsonGeometry": _GEOJSON_GEOMETRY_DEF,
        "DataQuery": _DATA_QUERY_DEF,
        "QueryFilter": _QUERY_FILTER_DEF,
        "QuerySort": _QUERY_SORT_DEF,
        "QueryAggregate": _QUERY_AGGREGATE_DEF,
        "QueryDownsample": _QUERY_DOWNSAMPLE_DEF,
        "SelectionState": _SELECTION_STATE_DEF,
    }
    return components, defs
