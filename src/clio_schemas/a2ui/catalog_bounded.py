"""Hand-authored catalog definitions for the 4 bounded/cross-field components.

``clio.map.v1``, ``clio.time-series.v1``, ``clio.workflow.v1``, and
``clio.chart.v1`` mirror ``MapComponent`` / ``TimeSeriesComponent`` /
``WorkflowComponent`` / ``ChartComponent``
(``a2ui/v0_9_1/bounded_components.py``): bounded list lengths and, for the
time series and the chart, "exactly one of" cross-field rules expressed as
extra ``oneOf`` ``allOf`` branches. The chart's per-preset required fields
are derived from the shipped preset templates. Most of the Vega-Lite spec
guard IS expressible in JSON Schema and is included on ``spec`` below: the
top-level key allowlist (``propertyNames``), a recursive ban on ``url``/
``usermeta`` keys at any depth (``$defs/SpecNoForbiddenKeys``), and the rule
that every ``data`` key at any depth is absent or exactly ``{"name":
"source"}`` (``$defs/SpecDataNamedSource``). Two rules are NOT expressible in
plain JSON Schema and stay pydantic/renderer-only: the serialized-size cap
(65536 UTF-8 bytes — JSON Schema has no "byte length of my own re-encoding"
assertion) and the view-composition count (recursively counting
mark-bearing views across ``layer``/``concat``/``facet``/``repeat`` — JSON
Schema cannot count matches across a recursive structure). Both still run in
:mod:`clio_schemas.a2ui.chart_spec`, in the pydantic model and the renderer.
These are not built through
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
    DEFAULT_QUERY_PER_ENTITY,
    MAX_CHART_FIELD_LENGTH,
    MAX_CHART_HEIGHT,
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
    MAX_TIME_SERIES_ROWS,
    MAX_WORKFLOW_EDGES,
    MAX_WORKFLOW_NODES,
)

_SELECTION_DESCRIPTION = (
    "Bind to /selection/<key>; the bound value is a SelectionState "
    "({field, values[], source?}, see $defs/SelectionState). Components bound to the "
    "same path share one selection."
)
_DATA_URI_DESCRIPTION = (
    "A workspace file path or artifact:// reference; CLIO registers a path as an "
    "artifact before validation."
)


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
_QUERY_SCALAR: dict[str, Any] = {"type": ["string", "number", "boolean"]}


def _filter_op_rule(op: str, value: dict[str, Any], *, required: bool) -> dict[str, Any]:
    then: dict[str, Any] = {"properties": {"value": value}}
    if required:
        then["required"] = ["value"]
    return {"if": {"properties": {"op": {"const": op}}}, "then": then}


_CHART_QUERY_FILTER_DEF: dict[str, Any] = {
    "type": "object",
    "description": (
        "One predicate; all filter entries are AND-ed. eq: value is a non-null scalar. "
        "in: value is a non-empty list of scalars. range: value is [min, max], inclusive, "
        "either side may be null. isnull: value omitted or true matches nulls, false "
        "matches non-nulls. contains: value is a non-empty string, matched as a "
        "case-insensitive substring of a string column (a per-column text filter)."
    ),
    "properties": {
        "column": _CHART_FIELD_NAME,
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

_CHART_QUERY_SORT_DEF: dict[str, Any] = {
    "type": "object",
    "description": "One dataQuery.sort key; earlier entries in the list sort first.",
    "properties": {
        "column": _CHART_FIELD_NAME,
        "desc": {"type": "boolean", "default": False},
    },
    "required": ["column"],
    "additionalProperties": False,
}

_CHART_QUERY_AGGREGATE_DEF: dict[str, Any] = {
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
            "items": _CHART_FIELD_NAME,
        },
        "metrics": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_QUERY_METRICS,
            "uniqueItems": True,
            "items": {
                "type": "object",
                "properties": {
                    "column": _CHART_FIELD_NAME,
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

_CHART_QUERY_DOWNSAMPLE_DEF: dict[str, Any] = {
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
        "entityColumn": _nullable(_CHART_FIELD_NAME),
        "x": _nullable(_CHART_FIELD_NAME),
        "y": _nullable(_CHART_FIELD_NAME),
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

_CHART_DATA_QUERY_DEF: dict[str, Any] = {
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
        "filter/aggregate/downsample intent still applies underneath."
    ),
    "properties": {
        "columns": _nullable(
            {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_QUERY_COLUMNS,
                "uniqueItems": True,
                "items": _CHART_FIELD_NAME,
            }
        ),
        "filter": _nullable(
            {
                "type": "array",
                "maxItems": MAX_QUERY_FILTERS,
                "items": {"$ref": "#/$defs/ChartQueryFilter"},
            }
        ),
        "aggregate": _nullable({"$ref": "#/$defs/ChartQueryAggregate"}),
        "downsample": _nullable({"$ref": "#/$defs/ChartQueryDownsample"}),
        "sort": _nullable(
            {
                "type": "array",
                "maxItems": MAX_QUERY_COLUMNS,
                "items": {"$ref": "#/$defs/ChartQuerySort"},
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
                            "dataset 'source' — the spec is chart configuration, never a data "
                            "channel, and the dataset itself is unbounded via dataUri regardless "
                            "of this cap. This schema already enforces the top-level key "
                            "allowlist, no url/usermeta key at any depth, and data only as "
                            "{name: source} at any depth; the renderer additionally enforces the "
                            "config-size (65536 bytes) and view-count (8) caps that keep the spec "
                            "itself bounded and abuse-resistant, which JSON Schema cannot "
                            "express. See a2ui/chart/guard_rules.json."
                        ),
                        "propertyNames": {"enum": list(ALLOWED_TOP_LEVEL_KEYS)},
                        "allOf": [
                            {"$ref": "#/$defs/SpecNoForbiddenKeys"},
                            {"$ref": "#/$defs/SpecDataNamedSource"},
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
                                "type": ["string", "number", "boolean", "null"]
                            },
                        },
                        "description": (
                            f"Inline rows (at most {MAX_INLINE_ROWS}) — this array rides the "
                            "surface's own wire message, so it is capped for transfer size; "
                            "for a larger or growing dataset use dataUri instead, unbounded "
                            "and paged/downsampled by the viewer."
                        ),
                    },
                    "dataUri": {
                        "type": "string",
                        "pattern": ARTIFACT_URI_PATTERN,
                        "not": {"pattern": r"\s"},
                        "description": _DATA_URI_DESCRIPTION,
                    },
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
        "SpecNoForbiddenKeys": _SPEC_NO_FORBIDDEN_KEYS_DEF,
        "SpecDataNamedSource": _SPEC_DATA_NAMED_SOURCE_DEF,
        "ChartDataQuery": _CHART_DATA_QUERY_DEF,
        "ChartQueryFilter": _CHART_QUERY_FILTER_DEF,
        "ChartQuerySort": _CHART_QUERY_SORT_DEF,
        "ChartQueryAggregate": _CHART_QUERY_AGGREGATE_DEF,
        "ChartQueryDownsample": _CHART_QUERY_DOWNSAMPLE_DEF,
        "SelectionState": _SELECTION_STATE_DEF,
    }
    return components, defs
