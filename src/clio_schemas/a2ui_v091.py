"""Canonical trusted A2UI 0.9.1 catalog vocabulary."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Any, Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    RootModel,
    StringConstraints,
    create_model,
    field_validator,
    model_validator,
)

A2UI_WIRE_VERSION = "v0.9.1"
A2UI_CATALOG_ID = "https://iowarp.ai/a2ui/catalogs/clio-workspace/v1"
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

    componentId: str
    path: str


ChildList = list[str] | _ChildTemplate


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


class _TabDefinition(_ClosedModel):
    title: DynamicString
    child: str


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


class _IconSvgPath(_ClosedModel):
    svgPath: str


class _ComponentBase(_ClosedModel):
    """Fields shared by every trusted catalog component."""

    id: str
    accessibility: _Accessibility | None = None
    weight: float | None = None


def _component_model(
    class_name: str,
    component_name: str,
    *,
    required: Mapping[str, Any] | None = None,
    optional: Mapping[str, Any] | None = None,
) -> type[BaseModel]:
    """Create one closed component model from the canonical property declaration."""

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
    required={"name": str | _IconSvgPath | _DataBinding},
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
    required={"children": list[str]},
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
    required={"child": str},
    optional={"title": DynamicString, "description": DynamicString},
)
TabsComponent = _component_model(
    "TabsComponent",
    "Tabs",
    required={"tabs": Annotated[list[_TabDefinition], Field(min_length=1)]},
)
ModalComponent = _component_model(
    "ModalComponent", "Modal", required={"trigger": str, "content": str}
)
DividerComponent = _component_model(
    "DividerComponent", "Divider", optional={"axis": Literal["horizontal", "vertical"]}
)
ButtonComponent = _component_model(
    "ButtonComponent",
    "Button",
    required={"child": str, "action": Action},
    optional={
        "variant": Literal["default", "primary", "borderless"],
        "checks": list[_CheckRule],
    },
)
CheckBoxComponent = _component_model(
    "CheckBoxComponent",
    "CheckBox",
    required={"label": DynamicString, "value": DynamicBoolean},
    optional={"checks": list[_CheckRule]},
)
TextFieldComponent = _component_model(
    "TextFieldComponent",
    "TextField",
    required={"label": DynamicString},
    optional={
        "value": DynamicString,
        "variant": Literal["longText", "number", "shortText", "obscured"],
        "validationRegexp": str,
        "checks": list[_CheckRule],
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
        "checks": list[_CheckRule],
    },
)
SliderComponent = _component_model(
    "SliderComponent",
    "Slider",
    required={"max": float, "value": DynamicNumber},
    optional={"label": DynamicString, "min": float, "checks": list[_CheckRule]},
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


class MapPoint(_ClosedModel):
    """One bounded point in the interactive map component."""

    id: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    label: Annotated[str, StringConstraints(min_length=1, max_length=240)]
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    detail: str | None = Field(default=None, max_length=2_000)
    category: str | None = Field(default=None, max_length=120)


class MapComponent(_ComponentBase):
    """Interactive bounded geospatial component."""

    component: Literal["clio.map.v1"] = "clio.map.v1"
    title: DynamicString | None = None
    points: list[MapPoint] = Field(min_length=1, max_length=MAX_MAP_POINTS)
    selected: str | None = Field(default=None, max_length=128)
    action: Action | None = None
    actionLabel: DynamicString | None = None


class TimeSeriesComponent(_ComponentBase):
    """Inline or artifact-backed interactive time-series component."""

    component: Literal["clio.time-series.v1"] = "clio.time-series.v1"
    series: list[dict[str, str | float | int | None]] | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_TIME_SERIES_ROWS,
    )
    dataUri: str | None = Field(
        default=None,
        pattern=r"^artifact://artifact_[A-Za-z0-9_-]+$",
    )
    xKey: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    yKeys: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]] = Field(
        min_length=1,
        max_length=5,
    )
    title: DynamicString | None = None

    @model_validator(mode="after")
    def _validate_data_source_and_columns(self) -> TimeSeriesComponent:
        if (self.series is None) == (self.dataUri is None):
            raise ValueError("exactly one of series or dataUri is required")
        if len(set(self.yKeys)) != len(self.yKeys):
            raise ValueError("yKeys must contain distinct column names")
        return self


class WorkflowNode(_ClosedModel):
    """One node in a bounded workflow graph."""

    id: str
    label: str
    state: str | None = None
    detail: str | None = None


class WorkflowEdge(_ClosedModel):
    """One directed relationship in a workflow graph."""

    source: str
    target: str
    label: str | None = None


class WorkflowComponent(_ComponentBase):
    """Bounded interactive workflow topology."""

    component: Literal["clio.workflow.v1"] = "clio.workflow.v1"
    nodes: list[WorkflowNode] = Field(min_length=1, max_length=MAX_WORKFLOW_NODES)
    edges: list[WorkflowEdge] = Field(max_length=MAX_WORKFLOW_EDGES)
    selected: str | None = None
    action: Action | None = None


COMPONENT_MODELS: tuple[type[BaseModel], ...] = (
    TextComponent,
    IconComponent,
    ImageComponent,
    RowComponent,
    ColumnComponent,
    GridComponent,
    ListComponent,
    FrameComponent,
    TabsComponent,
    ModalComponent,
    DividerComponent,
    ButtonComponent,
    CheckBoxComponent,
    TextFieldComponent,
    ChoicePickerComponent,
    SliderComponent,
    StatusComponent,
    MetricComponent,
    ProgressComponent,
    CalloutComponent,
    DataTableComponent,
    TimeSeriesComponent,
    MermaidComponent,
    MapComponent,
    WorkflowComponent,
    ArtifactComponent,
    CodeComponent,
    DiffComponent,
    ActionCardComponent,
    ApprovalComponent,
)

A2UIComponentValue = Annotated[
    TextComponent
    | IconComponent
    | ImageComponent
    | RowComponent
    | ColumnComponent
    | GridComponent
    | ListComponent
    | FrameComponent
    | TabsComponent
    | ModalComponent
    | DividerComponent
    | ButtonComponent
    | CheckBoxComponent
    | TextFieldComponent
    | ChoicePickerComponent
    | SliderComponent
    | StatusComponent
    | MetricComponent
    | ProgressComponent
    | CalloutComponent
    | DataTableComponent
    | TimeSeriesComponent
    | MermaidComponent
    | MapComponent
    | WorkflowComponent
    | ArtifactComponent
    | CodeComponent
    | DiffComponent
    | ActionCardComponent
    | ApprovalComponent,
    Field(discriminator="component"),
]


class A2UIComponent(RootModel[A2UIComponentValue]):
    """Closed union of every trusted A2UI 0.9.1 catalog component."""


class A2UIClientAction(BaseModel):
    """Known client-action fields with tolerated protocol extensions."""

    model_config = ConfigDict(extra="allow", strict=True, frozen=True)

    name: Literal[
        "agent.submit",
        "approval.respond",
        "form.submit",
        "run.retry",
        "run.cancel",
    ]
    surfaceId: str
    sourceComponentId: str = Field(min_length=1)
    timestamp: str
    context: dict[str, Any]

    @field_validator("timestamp")
    @classmethod
    def _validate_timestamp(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("timestamp must be ISO 8601") from exc
        return value


class A2UIClientActionMessage(BaseModel):
    """Official 0.9.1 client action envelope with extension-key tolerance."""

    model_config = ConfigDict(extra="allow", strict=True, frozen=True)

    version: Literal["v0.9.1"]
    action: A2UIClientAction


def trusted_component_names() -> tuple[str, ...]:
    """Return the canonical trusted component names in catalog order."""

    return tuple(model.model_fields["component"].default for model in COMPONENT_MODELS)
