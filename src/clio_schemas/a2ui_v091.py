"""Canonical trusted A2UI 0.9.1 catalog vocabulary."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
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


class _ComponentBase(_ClosedModel):
    """Fields shared by every trusted catalog component."""

    id: str
    accessibility: Any | None = None
    weight: float | None = None


def _component_model(
    class_name: str,
    component_name: str,
    *,
    required: tuple[str, ...] = (),
    optional: tuple[str, ...] = (),
) -> type[BaseModel]:
    """Create one closed component model from the canonical property declaration."""

    fields: dict[str, tuple[Any, Any]] = {
        "component": (Literal[component_name], component_name),
    }
    fields.update({name: (Any, ...) for name in required})
    fields.update({name: (Any | None, None) for name in optional})
    model_factory = cast(Any, create_model)
    return cast(type[BaseModel], model_factory(class_name, __base__=_ComponentBase, **fields))


TextComponent = _component_model(
    "TextComponent", "Text", required=("text",), optional=("variant", "weight")
)
IconComponent = _component_model("IconComponent", "Icon", required=("name",), optional=("weight",))
ImageComponent = _component_model(
    "ImageComponent",
    "Image",
    required=("url",),
    optional=("description", "fit", "variant", "weight"),
)
RowComponent = _component_model(
    "RowComponent", "Row", required=("children",), optional=("justify", "align", "weight")
)
ColumnComponent = _component_model(
    "ColumnComponent",
    "Column",
    required=("children",),
    optional=("justify", "align", "weight"),
)
GridComponent = _component_model(
    "GridComponent",
    "Grid",
    required=("children", "columns"),
    optional=("gap", "weight"),
)
ListComponent = _component_model(
    "ListComponent",
    "List",
    required=("children",),
    optional=("direction", "align", "listStyle", "weight"),
)
FrameComponent = _component_model(
    "FrameComponent",
    "Frame",
    required=("child",),
    optional=("title", "description", "weight"),
)
TabsComponent = _component_model("TabsComponent", "Tabs", required=("tabs",), optional=("weight",))
ModalComponent = _component_model(
    "ModalComponent", "Modal", required=("trigger", "content"), optional=("weight",)
)
DividerComponent = _component_model("DividerComponent", "Divider", optional=("axis", "weight"))
ButtonComponent = _component_model(
    "ButtonComponent",
    "Button",
    required=("child",),
    optional=(
        "variant",
        "action",
        "checks",
        "isValid",
        "validationErrors",
        "weight",
    ),
)
CheckBoxComponent = _component_model(
    "CheckBoxComponent",
    "CheckBox",
    required=("label", "value"),
    optional=("checks", "isValid", "validationErrors", "weight"),
)
TextFieldComponent = _component_model(
    "TextFieldComponent",
    "TextField",
    required=("label", "value"),
    optional=(
        "variant",
        "validationRegexp",
        "checks",
        "isValid",
        "validationErrors",
        "weight",
    ),
)
ChoicePickerComponent = _component_model(
    "ChoicePickerComponent",
    "ChoicePicker",
    required=("label", "options", "value"),
    optional=(
        "variant",
        "displayStyle",
        "filterable",
        "checks",
        "isValid",
        "validationErrors",
        "weight",
    ),
)
SliderComponent = _component_model(
    "SliderComponent",
    "Slider",
    required=("label", "min", "max", "value"),
    optional=("checks", "isValid", "validationErrors", "weight"),
)
StatusComponent = _component_model(
    "StatusComponent",
    "clio.status.v1",
    required=("label", "state"),
    optional=("detail", "elapsedMs", "weight"),
)
MetricComponent = _component_model(
    "MetricComponent",
    "clio.metric.v1",
    required=("label", "value"),
    optional=("unit", "trend", "detail", "weight"),
)
ProgressComponent = _component_model(
    "ProgressComponent",
    "clio.progress.v1",
    required=("label",),
    optional=("value", "max", "state", "detail", "weight"),
)
CalloutComponent = _component_model(
    "CalloutComponent",
    "clio.callout.v1",
    required=("title", "body", "severity"),
    optional=("action", "weight"),
)
DataTableComponent = _component_model(
    "DataTableComponent",
    "clio.data-table.v1",
    required=("columns", "rows"),
    optional=("selection", "action", "weight"),
)
MermaidComponent = _component_model(
    "MermaidComponent",
    "clio.mermaid.v1",
    required=("source",),
    optional=("title", "weight"),
)
ArtifactComponent = _component_model(
    "ArtifactComponent",
    "clio.artifact.v1",
    required=("name", "uri", "mediaType"),
    optional=("size", "action", "weight"),
)
CodeComponent = _component_model(
    "CodeComponent",
    "clio.code.v1",
    required=("code", "language"),
    optional=("title", "weight"),
)
DiffComponent = _component_model(
    "DiffComponent",
    "clio.diff.v1",
    required=("path", "diff"),
    optional=("status", "action", "weight"),
)
ActionCardComponent = _component_model(
    "ActionCardComponent",
    "clio.action-card.v1",
    required=("title", "body", "severity", "actions"),
    optional=("weight",),
)
ApprovalComponent = _component_model(
    "ApprovalComponent",
    "clio.approval.v1",
    required=("title", "reason", "risk", "actions"),
    optional=("weight",),
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
    title: Any | None = None
    points: list[MapPoint] = Field(min_length=1, max_length=MAX_MAP_POINTS)
    selected: str | None = Field(default=None, max_length=128)
    action: Any | None = None
    actionLabel: Any | None = None


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
    title: Any | None = None

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
    action: Any | None = None


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


SERVER_ACTION_NAMES = (
    "agent.submit",
    "approval.respond",
    "form.submit",
    "run.retry",
    "run.cancel",
)


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
