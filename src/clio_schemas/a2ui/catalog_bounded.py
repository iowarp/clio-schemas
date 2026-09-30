"""Hand-authored catalog definitions for the 7 bounded/cross-field components.

``clio.map.v1``, ``clio.data-table.v1``, ``clio.code.v1``, ``clio.mermaid.v1``,
``clio.diff.v1``, ``clio.workflow.v1``, and ``clio.chart.v1`` mirror
``MapComponent`` / ``DataTableComponent`` / ``CodeComponent`` /
``MermaidComponent`` / ``DiffComponent`` / ``WorkflowComponent`` /
``ChartComponent`` (``a2ui/v0_9_1/bounded_components.py``): bounded list
lengths and "exactly one of inline values or ``dataUri``" cross-field rules
expressed as extra ``oneOf``/``allOf`` branches. The chart's per-preset
required fields are derived from the shipped preset templates. The Vega-Lite
spec guard (size, view count, ``data``/``url`` rules) cannot be written in
JSON Schema beyond the top-level key allowlist; it lives in
:mod:`clio_schemas.a2ui.chart_spec` and runs in the pydantic model and the
renderer. These are not built through the generic canonicaliser
(``catalog_render.py``) because ``Field(min_length=/max_length=)`` bounds and
cross-field ``model_validator``s are pydantic *business rules*, not
field-type shapes.

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
_DATA_URI_DESCRIPTION = "A registered artifact reference (artifact://...); never a raw path."
_DATA_QUERY_REF: dict[str, Any] = {"$ref": "#/$defs/DataQuery"}

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
    "description": "Points on an interactive map (stations, sites, epicenters).",
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
                        f"Inline points (at most {MAX_MAP_POINTS}); use dataUri for more."
                    ),
                },
                "dataUri": {
                    "type": "string",
                    "pattern": ARTIFACT_URI_PATTERN,
                    "description": (
                        f"{_DATA_URI_DESCRIPTION} Requires latitudeField/longitudeField/"
                        "labelField; a referenced dataset is bounded by dataQuery/limit, "
                        "not the inline point cap."
                    ),
                },
                "dataQuery": {
                    **_DATA_QUERY_REF,
                    "description": "Server-side table query narrowing dataUri; ignored without it.",
                },
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
                "detailField": {
                    "$ref": "#/$defs/FieldName",
                    "description": "Dataset column holding each point's detail text.",
                },
                "categoryField": {
                    "$ref": "#/$defs/FieldName",
                    "description": "Dataset column grouping points into categories.",
                },
                "selected": {"type": "string", "maxLength": 128},
                "selection": {
                    "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicValue",
                    "description": _SELECTION_DESCRIPTION,
                },
                "action": {"$ref": f"{COMMON_TYPES_ID}#/$defs/Action"},
                "actionLabel": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
            },
            "required": ["component"],
            "dependentRequired": {"dataQuery": ["dataUri"]},
        },
        {
            "description": "Exactly one of points or dataUri is required.",
            "oneOf": [
                {"required": ["points"], "not": {"required": ["dataUri"]}},
                {"required": ["dataUri"], "not": {"required": ["points"]}},
            ],
        },
        {
            "description": "dataUri requires the point field names.",
            "if": {"required": ["dataUri"]},
            "then": {"required": ["latitudeField", "longitudeField", "labelField"]},
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
                    "description": "Inline nodes; give edges too, or use dataUri instead of both.",
                },
                "edges": {
                    "type": "array",
                    "maxItems": MAX_WORKFLOW_EDGES,
                    "items": {"$ref": "#/$defs/WorkflowEdge"},
                    "description": "Inline edges, alongside nodes.",
                },
                "dataUri": {
                    "type": "string",
                    "pattern": ARTIFACT_URI_PATTERN,
                    "description": (
                        f'{_DATA_URI_DESCRIPTION} A JSON file shaped {{"nodes": [...], '
                        '"edges": [...]}}.'
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
                    "description": _DATA_URI_DESCRIPTION,
                },
                "dataQuery": {
                    **_DATA_QUERY_REF,
                    "description": "Server-side table query narrowing dataUri; ignored without it.",
                },
                # DynamicValue (not a static string): bind it to /selection/<key>, whose
                # value is a SelectionState. A plain string stays valid (backward compatible).
                "selection": {
                    "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicValue",
                    "description": _SELECTION_DESCRIPTION,
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
    then: dict[str, Any] = {"properties": {"value": value}}
    if required:
        then["required"] = ["value"]
    return {"if": {"properties": {"op": {"const": op}}}, "then": then}


_QUERY_FILTER_DEF: dict[str, Any] = {
    "type": "object",
    "description": (
        "One predicate; all filter entries are AND-ed. eq: value is a non-null scalar. "
        "in: value is a non-empty list of scalars. range: value is [min, max], inclusive, "
        "either side may be null. isnull: value omitted or true matches nulls, false "
        "matches non-nulls."
    ),
    "properties": {
        "column": {"$ref": "#/$defs/FieldName"},
        "op": {"type": "string", "enum": ["eq", "in", "range", "isnull"]},
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
    ],
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
        "entityColumn": {"$ref": "#/$defs/FieldName"},
        "x": {"$ref": "#/$defs/FieldName"},
        "y": {"$ref": "#/$defs/FieldName"},
        "maxPerEntity": {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_QUERY_PER_ENTITY,
            "default": DEFAULT_QUERY_PER_ENTITY,
        },
    },
    "additionalProperties": False,
    "if": {"properties": {"mode": {"const": "per_entity_lttb"}}, "required": ["mode"]},
    "then": {"required": ["x", "y"]},
}

_DATA_QUERY_DEF: dict[str, Any] = {
    "type": "object",
    "description": (
        "A server-side table query applied to dataUri: the table-query request body "
        "(POST /v1/artifacts/{id}/table-query) without format. The server runs filter, "
        "then aggregate, then downsample, then limit. Omit columns to request the columns "
        "implied by the component (its named *Field properties and its selection field). "
        "Shared by clio.chart.v1, clio.map.v1, and clio.data-table.v1."
    ),
    "properties": {
        "columns": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_QUERY_COLUMNS,
            "uniqueItems": True,
            "items": {"$ref": "#/$defs/FieldName"},
        },
        "filter": {
            "type": "array",
            "maxItems": MAX_QUERY_FILTERS,
            "items": {"$ref": "#/$defs/QueryFilter"},
        },
        "aggregate": {"$ref": "#/$defs/QueryAggregate"},
        "downsample": {"$ref": "#/$defs/QueryDownsample"},
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
                        "description": (
                            f"Inline rows (at most {MAX_INLINE_ROWS}); use dataUri for more."
                        ),
                    },
                    "dataUri": {
                        "type": "string",
                        "pattern": ARTIFACT_URI_PATTERN,
                        "description": _DATA_URI_DESCRIPTION,
                    },
                    "dataQuery": {
                        **_DATA_QUERY_REF,
                        "description": (
                            "Server-side table query narrowing dataUri; ignored without it."
                        ),
                    },
                    "selection": {
                        "$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicValue",
                        "description": _SELECTION_DESCRIPTION,
                    },
                    "selectionParam": {
                        "type": "string",
                        "pattern": SELECTION_PARAM_PATTERN,
                        "default": DEFAULT_SELECTION_PARAM,
                    },
                    "selectionField": {"$ref": "#/$defs/FieldName"},
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
        "DataQuery": _DATA_QUERY_DEF,
        "QueryFilter": _QUERY_FILTER_DEF,
        "QueryAggregate": _QUERY_AGGREGATE_DEF,
        "QueryDownsample": _QUERY_DOWNSAMPLE_DEF,
        "SelectionState": _SELECTION_STATE_DEF,
    }
    return components, defs
