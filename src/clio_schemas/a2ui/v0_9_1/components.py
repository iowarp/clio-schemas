"""CLIO's 33 trusted A2UI 0.9.1 catalog components — the pydantic generator.

These models are the *source of truth* for the ``clio-workspace`` catalog file
rendered by :mod:`clio_schemas.a2ui.catalog_export` (``catalog.json``, in the
official A2UI style — see ``catalogs/basic/catalog.json`` in the vendored
tree). ``COMPONENT_SPECS`` records, for every component built through
:func:`_component_model`, the exact ``required``/``optional`` field-type
declaration used to build both the pydantic model *and* the catalog's JSON
Schema component definition — one declaration, two renderings, so they can
never drift from each other.

Field types that must resolve to an official ``common_types.json`` shape
(dynamic bindings, component-id references, child lists, actions) are
declared with the small marker types below (:data:`ComponentId`,
:data:`DynamicString`, ...) so the canonicaliser in ``catalog_export.py`` can
recognise them by identity/equality rather than by pattern-matching rendered
JSON Schema.
"""

from __future__ import annotations

import functools
import importlib.resources
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    create_model,
    field_validator,
)

# Bounds shared with bounded_components.py's clio.map.v1 / clio.time-series.v1
# / clio.workflow.v1 (and their catalog-render mirrors in catalog_bounded.py).
MAX_MAP_POINTS = 500
MAX_TIME_SERIES_ROWS = 10_000
MAX_WORKFLOW_NODES = 128
MAX_WORKFLOW_EDGES = 256
MAX_SELECTION_VALUES = 10_000
#: Where a selection lives in a surface's data model: ``/selection/<key>``.
SELECTION_PATH_PATTERN = r"^/selection/[^/]+$"

#: A registered-artifact reference (the only form bulk data may take on the wire).
ARTIFACT_URI_PATTERN = r"^artifact://artifact_[A-Za-z0-9_-]+$"
#: Name shared by components that coordinate client-side (camera, color range).
SYNC_GROUP_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"

#: The 3 CLIO-authored functions (see ``catalog_export.py::_render_workspace_functions``).
#: Kept here, not just there, so the pydantic ``call`` validator below and the
#: rendered catalog's function names can never drift apart.
CLIO_FUNCTION_NAMES: frozenset[str] = frozenset({"openArtifact", "selectData", "focusWorkflow"})


@functools.lru_cache(maxsize=1)
def _known_function_names() -> frozenset[str]:
    """Every function name a ``FunctionCall.call`` may reference.

    The vendored Basic catalog's 14 functions (``required``, ``regex``,
    ``formatString``, ...), read verbatim at call time — never hand-typed, so
    it can't drift from ``catalog_export.py``'s copy of the same file — plus
    :data:`CLIO_FUNCTION_NAMES`.
    """

    basic_path = Path(
        str(
            importlib.resources.files("clio_schemas")
            / "schemas"
            / "a2ui"
            / "v0_9_1"
            / "catalogs"
            / "basic"
            / "catalog.json"
        )
    )
    basic = json.loads(basic_path.read_text(encoding="utf-8"))
    return frozenset(basic["functions"]) | CLIO_FUNCTION_NAMES


class _ClosedModel(BaseModel):
    """Strict immutable model used at the trusted catalog boundary."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, populate_by_name=True)


class _DataBinding(_ClosedModel):
    """A JSON Pointer into the A2UI surface data model."""

    path: str


class _FunctionCallBase(_ClosedModel):
    """Shared identity check for every FunctionCall shape: ``call`` must be known.

    Mirrors what the catalog enforces via ``common_types.json``'s
    ``FunctionCall.oneOf: [{"$ref": "catalog.json#/$defs/anyFunction"}]`` — an
    unregistered function name is invalid on the wire, not just structurally
    malformed, so the pydantic side must reject it too.
    """

    call: str

    @field_validator("call")
    @classmethod
    def _call_is_known(cls, value: str) -> str:
        if value not in _known_function_names():
            raise ValueError(
                f"unknown function call {value!r}: not declared by any builtin catalog"
            )
        return value


class _FunctionCall(_FunctionCallBase):
    """A typed client-side function invocation."""

    args: dict[str, JsonValue] = Field(default_factory=dict)
    returnType: Literal["string", "number", "boolean", "array", "object", "any", "void"] = "boolean"


class _StringFunctionCall(_FunctionCallBase):
    args: dict[str, JsonValue] = Field(default_factory=dict)
    returnType: Literal["string"] = "string"


class _NumberFunctionCall(_FunctionCallBase):
    args: dict[str, JsonValue] = Field(default_factory=dict)
    returnType: Literal["number"] = "number"


class _BooleanFunctionCall(_FunctionCallBase):
    args: dict[str, JsonValue] = Field(default_factory=dict)
    returnType: Literal["boolean"] = "boolean"


class _ArrayFunctionCall(_FunctionCallBase):
    args: dict[str, JsonValue] = Field(default_factory=dict)
    returnType: Literal["array"] = "array"


# Component-id reference marker: a plain string on the wire, but a field
# declared with this type is a *reference to another component's id*, which
# the catalog canonicaliser renders as ``common_types.json#/$defs/ComponentId``
# instead of a bare ``{"type": "string"}``. Plain ``str`` stays plain (e.g. a
# severity string or a URI) — only fields declared with this marker get the
# ComponentId treatment.
ComponentId = Annotated[str, "a2ui:ComponentId"]

DynamicString = str | _DataBinding | _StringFunctionCall
DynamicNumber = float | _DataBinding | _NumberFunctionCall
DynamicBoolean = bool | _DataBinding | _BooleanFunctionCall
DynamicStringList = list[str] | _DataBinding | _ArrayFunctionCall
DynamicValue = str | float | bool | list[JsonValue] | _DataBinding | _FunctionCall


class _Accessibility(_ClosedModel):
    """Supplemental accessible name and description for one component."""

    label: DynamicString | None = None
    description: DynamicString | None = None


class _ChildTemplate(_ClosedModel):
    """Template for generating repeated child components from bound data."""

    componentId: ComponentId
    path: str


ChildList = list[str] | _ChildTemplate

# Pattern-constrained string markers: plain strings on the wire, rendered by
# the catalog canonicaliser as ``{"type": "string", "pattern": ...}``.
ArtifactUri = Annotated[str, Field(pattern=ARTIFACT_URI_PATTERN)]
SyncGroup = Annotated[str, Field(pattern=SYNC_GROUP_PATTERN)]


class SelectionState(_ClosedModel):
    """The value a bound ``selection`` path holds: ``/selection/<key>``.

    ``selection`` props (``clio.chart.v1``, ``clio.data-table.v1``,
    ``clio.map.v1``) are declared as :data:`DynamicValue` so they can be a
    ``{"path": ...}`` binding; the value *at* that path follows this shape.
    Every component bound to the same path reads and writes it, so a click
    in one (a chart line, a table row, a map point) highlights the same
    entities in the others without an agent turn. ``source`` is the id of
    the component that made the selection, so it can skip its own echo.
    Rendered into the workspace catalog as ``$defs/SelectionState``.
    """

    field: Annotated[str, Field(min_length=1, max_length=128)]
    values: Annotated[list[str | float], Field(max_length=MAX_SELECTION_VALUES)]
    source: Annotated[str, Field(min_length=1, max_length=128)] | None = None


class _IconSvgPath(_ClosedModel):
    svgPath: str


IconValue = str | _IconSvgPath | _DataBinding


class _ServerEvent(_ClosedModel):
    """Official server-side A2UI event action."""

    name: str
    context: dict[str, DynamicValue] | None = None


class _EventAction(_ClosedModel):
    event: _ServerEvent


class _FunctionAction(_ClosedModel):
    functionCall: _FunctionCall


Action = _EventAction | _FunctionAction


class _CheckRule(_ClosedModel):
    """One official client-side component validation rule."""

    condition: DynamicBoolean
    message: str


Checks = list[_CheckRule]


class _TabDefinition(_ClosedModel):
    title: DynamicString
    child: ComponentId


class _ChoiceOption(_ClosedModel):
    label: DynamicString
    value: str


class _DataTableColumn(_ClosedModel):
    key: str
    label: str


class _CardAction(_ClosedModel):
    label: str
    action: Action
    tone: Literal["default", "destructive"] | None = None


class _ComponentBase(_ClosedModel):
    """Fields shared by every trusted catalog component."""

    id: str
    accessibility: _Accessibility | None = None
    weight: float | None = None


# component_name -> (required, optional) field-type declarations, populated
# as a side effect of every :func:`_component_model` call. This is the single
# declaration the catalog canonicaliser (``catalog_export.py``) renders from —
# the same data that builds the pydantic model below it.
COMPONENT_SPECS: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}


def _component_model(
    class_name: str,
    component_name: str,
    *,
    required: Mapping[str, Any] | None = None,
    optional: Mapping[str, Any] | None = None,
) -> type[BaseModel]:
    """Create one closed component model from the canonical property declaration."""

    COMPONENT_SPECS[component_name] = (dict(required or {}), dict(optional or {}))
    fields: dict[str, tuple[Any, Any]] = {
        "component": (Literal[component_name], component_name),
    }
    fields.update({name: (field_type, ...) for name, field_type in (required or {}).items()})
    fields.update(
        {name: (field_type | None, None) for name, field_type in (optional or {}).items()}
    )
    model_factory = cast(Any, create_model)
    return cast(type[BaseModel], model_factory(class_name, __base__=_ComponentBase, **fields))


TextComponent = _component_model(
    "TextComponent",
    "Text",
    required={"text": DynamicString},
    optional={"variant": Literal["h1", "h2", "h3", "h4", "h5", "caption", "body"]},
)
IconComponent = _component_model(
    "IconComponent",
    "Icon",
    required={"name": IconValue},
)
ImageComponent = _component_model(
    "ImageComponent",
    "Image",
    required={"url": DynamicString},
    optional={
        "description": DynamicString,
        "fit": Literal["contain", "cover", "fill", "none", "scaleDown"],
        "variant": Literal[
            "icon", "avatar", "smallFeature", "mediumFeature", "largeFeature", "header"
        ],
    },
)
RowComponent = _component_model(
    "RowComponent",
    "Row",
    required={"children": ChildList},
    optional={
        "justify": Literal[
            "start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly", "stretch"
        ],
        "align": Literal["start", "center", "end", "stretch"],
    },
)
ColumnComponent = _component_model(
    "ColumnComponent",
    "Column",
    required={"children": ChildList},
    optional={
        "justify": Literal[
            "start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly", "stretch"
        ],
        "align": Literal["start", "center", "end", "stretch"],
    },
)
GridComponent = _component_model(
    "GridComponent",
    "Grid",
    required={"children": list[ComponentId]},
    optional={"columns": int, "gap": float},
)
ListComponent = _component_model(
    "ListComponent",
    "List",
    required={"children": ChildList},
    optional={
        "direction": Literal["vertical", "horizontal"],
        "align": Literal["start", "center", "end", "stretch"],
    },
)
FrameComponent = _component_model(
    "FrameComponent",
    "Frame",
    required={"child": ComponentId},
    optional={"title": DynamicString, "description": DynamicString},
)
TabsComponent = _component_model(
    "TabsComponent",
    "Tabs",
    required={"tabs": Annotated[list[_TabDefinition], Field(min_length=1)]},
)
ModalComponent = _component_model(
    "ModalComponent", "Modal", required={"trigger": ComponentId, "content": ComponentId}
)
DividerComponent = _component_model(
    "DividerComponent", "Divider", optional={"axis": Literal["horizontal", "vertical"]}
)
ButtonComponent = _component_model(
    "ButtonComponent",
    "Button",
    required={"child": ComponentId, "action": Action},
    optional={
        "variant": Literal["default", "primary", "borderless"],
        "checks": Checks,
    },
)
CheckBoxComponent = _component_model(
    "CheckBoxComponent",
    "CheckBox",
    required={"label": DynamicString, "value": DynamicBoolean},
    optional={"checks": Checks},
)
TextFieldComponent = _component_model(
    "TextFieldComponent",
    "TextField",
    required={"label": DynamicString},
    optional={
        "value": DynamicString,
        "variant": Literal["longText", "number", "shortText", "obscured"],
        "validationRegexp": str,
        "checks": Checks,
    },
)
ChoicePickerComponent = _component_model(
    "ChoicePickerComponent",
    "ChoicePicker",
    required={"options": list[_ChoiceOption], "value": DynamicStringList},
    optional={
        "label": DynamicString,
        "variant": Literal["multipleSelection", "mutuallyExclusive"],
        "displayStyle": Literal["checkbox", "chips"],
        "filterable": bool,
        "checks": Checks,
    },
)
SliderComponent = _component_model(
    "SliderComponent",
    "Slider",
    required={"max": float, "value": DynamicNumber},
    optional={"label": DynamicString, "min": float, "checks": Checks},
)
StatusComponent = _component_model(
    "StatusComponent",
    "clio.status.v1",
    required={"label": DynamicString, "state": DynamicString},
    optional={"detail": DynamicString, "elapsedMs": DynamicNumber},
)
MetricComponent = _component_model(
    "MetricComponent",
    "clio.metric.v1",
    required={"label": DynamicString, "value": DynamicValue},
    optional={"unit": DynamicString, "trend": DynamicString, "detail": DynamicString},
)
ProgressComponent = _component_model(
    "ProgressComponent",
    "clio.progress.v1",
    required={"label": DynamicString},
    optional={
        "value": DynamicNumber,
        "max": DynamicNumber,
        "state": DynamicString,
        "detail": DynamicString,
    },
)
CalloutComponent = _component_model(
    "CalloutComponent",
    "clio.callout.v1",
    required={"title": DynamicString, "body": DynamicString, "severity": str},
    optional={"action": Action},
)
DataTableComponent = _component_model(
    "DataTableComponent",
    "clio.data-table.v1",
    required={
        "columns": list[str | _DataTableColumn],
        "rows": list[dict[str, JsonValue]],
    },
    # DynamicValue (not a static string): bind it to /selection/<key>, whose
    # value is a SelectionState. A plain string stays valid (backward compatible).
    optional={"selection": DynamicValue, "action": Action},
)
MermaidComponent = _component_model(
    "MermaidComponent",
    "clio.mermaid.v1",
    required={"source": DynamicString},
    optional={"title": DynamicString},
)
ArtifactComponent = _component_model(
    "ArtifactComponent",
    "clio.artifact.v1",
    required={"name": DynamicString, "uri": str, "mediaType": str},
    optional={"size": DynamicNumber, "action": Action},
)
CodeComponent = _component_model(
    "CodeComponent",
    "clio.code.v1",
    required={"code": DynamicString, "language": str},
    optional={"title": DynamicString},
)
DiffComponent = _component_model(
    "DiffComponent",
    "clio.diff.v1",
    required={"path": str, "diff": DynamicString},
    optional={"status": DynamicString, "action": Action},
)
ActionCardComponent = _component_model(
    "ActionCardComponent",
    "clio.action-card.v1",
    required={
        "title": DynamicString,
        "body": DynamicString,
        "severity": str,
        "actions": Annotated[list[_CardAction], Field(max_length=6)],
    },
)
ApprovalComponent = _component_model(
    "ApprovalComponent",
    "clio.approval.v1",
    required={
        "title": DynamicString,
        "reason": DynamicString,
        "risk": DynamicString,
        "actions": Annotated[list[_CardAction], Field(min_length=1, max_length=4)],
    },
)
NumberSliderComponent = _component_model(
    "NumberSliderComponent",
    "clio.slider.v1",
    required={"label": DynamicString, "value": DynamicNumber, "min": float, "max": float},
    optional={"step": float, "unit": str},
)
MeshViewportComponent = _component_model(
    "MeshViewportComponent",
    "clio.mesh-viewport.v1",
    required={"meshUri": ArtifactUri},
    optional={
        "title": DynamicString,
        "field": DynamicString,
        "showField": DynamicBoolean,
        "frame": DynamicNumber,
        "thresholdField": str,
        "thresholdMin": DynamicNumber,
        "thresholdMax": DynamicNumber,
        "camera": DynamicValue,
        "syncGroup": SyncGroup,
        "upAxis": Literal["x", "y", "z"],
    },
)

# The four bounded/cross-field-validated components (clio.map.v1,
# clio.time-series.v1, clio.workflow.v1, clio.chart.v1) are not built through
# `_component_model` — see bounded_components.py — but COMPONENT_MODELS
# there is the single list consumers should import.
