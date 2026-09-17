"""Hand-authored catalog definitions for the 3 bounded/cross-field components.

``clio.map.v1``, ``clio.time-series.v1``, and ``clio.workflow.v1`` mirror
``MapComponent`` / ``TimeSeriesComponent`` / ``WorkflowComponent``
(``a2ui/v0_9_1/bounded_components.py``) exactly: bounded list lengths and, for
the time series, an "exactly one of series or dataUri" cross-field rule
expressed as an extra ``oneOf`` ``allOf`` branch. These are not built through
the generic canonicaliser (``catalog_render.py``) because
``Field(min_length=/max_length=)`` bounds and cross-field
``model_validator``s are pydantic *business rules*, not field-type shapes.
"""

from __future__ import annotations

from typing import Any

from clio_schemas.a2ui.catalog_render import COMMON_TYPES_ID
from clio_schemas.a2ui.v0_9_1.components import (
    MAX_MAP_POINTS,
    MAX_TIME_SERIES_ROWS,
    MAX_WORKFLOW_EDGES,
    MAX_WORKFLOW_NODES,
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
                    "items": {"type": "object"},
                },
                "dataUri": {"type": "string", "pattern": r"^artifact://artifact_[A-Za-z0-9_-]+$"},
                "xKey": {"type": "string", "minLength": 1},
                "yKeys": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 5,
                    "items": {"type": "string", "minLength": 1},
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


def hand_authored_components() -> tuple[dict[str, Any], dict[str, Any]]:
    """The 3 bounded components and their local ``$defs``."""

    components = {
        "clio.map.v1": _MAP_COMPONENT_SCHEMA,
        "clio.time-series.v1": _TIME_SERIES_COMPONENT_SCHEMA,
        "clio.workflow.v1": _WORKFLOW_COMPONENT_SCHEMA,
    }
    defs = {
        "MapPoint": _MAP_POINT_DEF,
        "WorkflowNode": _WORKFLOW_NODE_DEF,
        "WorkflowEdge": _WORKFLOW_EDGE_DEF,
    }
    return components, defs
