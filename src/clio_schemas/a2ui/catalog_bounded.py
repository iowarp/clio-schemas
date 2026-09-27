"""Hand-authored catalog definitions for the 4 bounded/cross-field components.

``clio.map.v1``, ``clio.time-series.v1``, ``clio.workflow.v1``, and
``clio.chart.v1`` mirror ``MapComponent`` / ``TimeSeriesComponent`` /
``WorkflowComponent`` / ``ChartComponent``
(``a2ui/v0_9_1/bounded_components.py``): bounded list lengths and, for the
time series and the chart, "exactly one of" cross-field rules expressed as
extra ``oneOf`` ``allOf`` branches. The chart's per-preset required fields
are derived from the shipped preset templates. The Vega-Lite spec guard
(size, view count, ``data``/``url`` rules) cannot be written in JSON Schema
beyond the top-level key allowlist; it lives in
:mod:`clio_schemas.a2ui.chart_spec` and runs in the pydantic model and the
renderer. These are not built through
the generic canonicaliser (``catalog_render.py``) because
``Field(min_length=/max_length=)`` bounds and cross-field
``model_validator``s are pydantic *business rules*, not field-type shapes.
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
    MAX_CHART_FIELD_LENGTH,
    MAX_CHART_HEIGHT,
    MAX_QUERY_COLUMNS,
    MAX_QUERY_FILTERS,
    MAX_QUERY_LIMIT,
    MAX_QUERY_OBJECT_KEYS,
    MIN_CHART_HEIGHT,
)
from clio_schemas.a2ui.v0_9_1.components import (
    ARTIFACT_URI_PATTERN,
    MAX_MAP_POINTS,
    MAX_SELECTION_VALUES,
    MAX_TIME_SERIES_ROWS,
    MAX_WORKFLOW_EDGES,
    MAX_WORKFLOW_NODES,
)

_SELECTION_DESCRIPTION = (
    "Bind to /selection/<key>; the bound value is a SelectionState "
    "({field, values[], source?}, see $defs/SelectionState). Components bound to the "
    "same path share one selection."
)

_MAP_POINT_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "minLength": 1, "maxLength": 128},
        "label": {"type": "string", "minLength": 1, "maxLength": 240},
        "latitude": {"type": "number", "minimum": -90, "maximum": 90},
        "longitude": {"type": "number", "minimum": -180, "maximum": 180},
        "detail": {"type": "string", "maxLength": 2000},
        "category": {"type": "string", "maxLength": 120},
    },
    "required": ["id", "label", "latitude", "longitude"],
    "additionalProperties": False,
}

_MAP_COMPONENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Interactive bounded geospatial component.",
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
                },
                "selected": {"type": "string", "maxLength": 128},
                "selection": {
                    "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicValue",
                    "description": _SELECTION_DESCRIPTION,
                },
                "action": {"$ref": f"{COMMON_TYPES_ID}#/$defs/Action"},
                "actionLabel": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
            },
            "required": ["component", "points"],
        },
    ],
    "unevaluatedProperties": False,
}

_TIME_SERIES_COMPONENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Inline or artifact-backed interactive time-series component.",
    "allOf": [
        {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
        {"$ref": "#/$defs/CatalogComponentCommon"},
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.time-series.v1"},
                "series": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_TIME_SERIES_ROWS,
                    "items": {
                        "type": "object",
                        "additionalProperties": {"type": ["string", "number", "null"]},
                    },
                },
                "dataUri": {"type": "string", "pattern": r"^artifact://artifact_[A-Za-z0-9_-]+$"},
                "xKey": {"type": "string", "minLength": 1, "pattern": r"\S"},
                "yKeys": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 5,
                    "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1, "pattern": r"\S"},
                },
                "title": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
            },
            "required": ["component", "xKey", "yKeys"],
        },
        {
            "description": "Exactly one of series or dataUri is required.",
            "oneOf": [
                {"required": ["series"], "not": {"required": ["dataUri"]}},
                {"required": ["dataUri"], "not": {"required": ["series"]}},
            ],
        },
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
    "description": "Bounded interactive workflow topology.",
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
                },
                "edges": {
                    "type": "array",
                    "maxItems": MAX_WORKFLOW_EDGES,
                    "items": {"$ref": "#/$defs/WorkflowEdge"},
                },
                "selected": {"type": "string"},
                "action": {"$ref": f"{COMMON_TYPES_ID}#/$defs/Action"},
            },
            "required": ["component", "nodes", "edges"],
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

_CHART_FIELD_NAME: dict[str, Any] = {
    "type": "string",
    "minLength": 1,
    "maxLength": MAX_CHART_FIELD_LENGTH,
}
_BOUNDED_OBJECT: dict[str, Any] = {"type": "object", "maxProperties": MAX_QUERY_OBJECT_KEYS}

_CHART_DATA_QUERY_DEF: dict[str, Any] = {
    "type": "object",
    "description": (
        "A server-side table query applied to dataUri: columns (projection), filter, "
        "aggregate, downsample, limit. Filter/aggregate/downsample entries are open "
        "objects the server interprets, bounded in size."
    ),
    "properties": {
        "columns": {"type": "array", "maxItems": MAX_QUERY_COLUMNS, "items": _CHART_FIELD_NAME},
        "filter": {"type": "array", "maxItems": MAX_QUERY_FILTERS, "items": _BOUNDED_OBJECT},
        "aggregate": _BOUNDED_OBJECT,
        "downsample": _BOUNDED_OBJECT,
        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_QUERY_LIMIT},
    },
    "additionalProperties": False,
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
    fill_fields = {field: _CHART_FIELD_NAME for field in CHART_PRESET_FIELDS if field != "xType"}
    return {
        "type": "object",
        "description": (
            "A Vega-Lite chart over inline rows (data) or an artifact (dataUri), from a preset "
            "or a guarded spec, with a selection bindable to /selection/<key>."
        ),
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
                            "dataset 'source'. The renderer also applies the spec guard "
                            "(size, view count, no url/usermeta keys, data only as "
                            "{name: source}); see a2ui/chart/guard_rules.json."
                        ),
                        "propertyNames": {"enum": list(ALLOWED_TOP_LEVEL_KEYS)},
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
                                "type": ["string", "number", "boolean", "null"]
                            },
                        },
                    },
                    "dataUri": {"type": "string", "pattern": ARTIFACT_URI_PATTERN},
                    "dataQuery": {"$ref": "#/$defs/ChartDataQuery"},
                    "selection": {
                        "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicValue",
                        "description": _SELECTION_DESCRIPTION,
                    },
                    "selectionParam": {
                        "type": "string",
                        "pattern": SELECTION_PARAM_PATTERN,
                        "default": DEFAULT_SELECTION_PARAM,
                    },
                    "selectionField": _CHART_FIELD_NAME,
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
    """The 4 bounded components and their local ``$defs``."""

    components = {
        "clio.map.v1": _MAP_COMPONENT_SCHEMA,
        "clio.time-series.v1": _TIME_SERIES_COMPONENT_SCHEMA,
        "clio.workflow.v1": _WORKFLOW_COMPONENT_SCHEMA,
        "clio.chart.v1": _chart_component_schema(),
    }
    defs = {
        "MapPoint": _MAP_POINT_DEF,
        "WorkflowNode": _WORKFLOW_NODE_DEF,
        "WorkflowEdge": _WORKFLOW_EDGE_DEF,
        "ChartDataQuery": _CHART_DATA_QUERY_DEF,
        "SelectionState": _SELECTION_STATE_DEF,
    }
    return components, defs
