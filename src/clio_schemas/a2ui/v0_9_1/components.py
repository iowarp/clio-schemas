"""CLIO's 30 trusted A2UI 0.9.1 catalog components — the pydantic generator.

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

from collections.abc import Mapping
from typing import Annotated, Any, Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    create_model,
)

# Bounds shared with bounded_components.py's clio.map.v1 / clio.time-series.v1
# / clio.workflow.v1 (and their catalog-render mirrors in catalog_bounded.py).
MAX_MAP_POINTS = 500
MAX_TIME_SERIES_ROWS = 10_000
MAX_WORKFLOW_NODES = 128
MAX_WORKFLOW_EDGES = 256


class _ClosedModel(BaseModel):
    """Strict immutable model used at the trusted catalog boundary."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, populate_by_name=True)


class _DataBinding(_ClosedModel):
    """A JSON Pointer into the A2UI surface data model."""

    path: str


class _FunctionCall(_ClosedModel):
    """A typed client-side function invocation."""

    call: str
    args: dict[str, JsonValue] = Field(default_factory=dict)
    returnType: Literal["string", "number", "boolean", "array", "object", "any", "void"] = "boolean"


class _StringFunctionCall(_ClosedModel):
    call: str
    args: dict[str, JsonValue] = Field(default_factory=dict)
    returnType: Literal["string"] = "string"


class _NumberFunctionCall(_ClosedModel):
    call: str
    args: dict[str, JsonValue] = Field(default_factory=dict)
    returnType: Literal["number"] = "number"


class _BooleanFunctionCall(_ClosedModel):
    call: str
    args: dict[str, JsonValue] = Field(default_factory=dict)
    returnType: Literal["boolean"] = "boolean"


class _ArrayFunctionCall(_ClosedModel):
    call: str
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
    optional={"selection": str, "action": Action},
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

# The three bounded/cross-field-validated components (clio.map.v1,
# clio.time-series.v1, clio.workflow.v1) are not built through
# `_component_model` — see bounded_components.py — but COMPONENT_MODELS
# there is the single list consumers should import.
