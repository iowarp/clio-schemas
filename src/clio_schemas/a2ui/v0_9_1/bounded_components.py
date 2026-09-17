"""The three CLIO components with bounded lists or cross-field business rules.

``clio.map.v1``, ``clio.time-series.v1``, and ``clio.workflow.v1`` are not
built through ``_component_model`` (see ``components.py``) because they need
``Field(min_length=/max_length=)`` bounds and, for the time series, a
cross-field ``model_validator`` ("exactly one of series or dataUri"). Their
catalog-file renderings are hand-authored to match, in
``clio_schemas.a2ui.catalog_bounded``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from clio_schemas.a2ui.v0_9_1.components import (
    MAX_MAP_POINTS,
    MAX_TIME_SERIES_ROWS,
    MAX_WORKFLOW_EDGES,
    MAX_WORKFLOW_NODES,
    Action,
    ActionCardComponent,
    ApprovalComponent,
    ArtifactComponent,
    ButtonComponent,
    CalloutComponent,
    CheckBoxComponent,
    ChoicePickerComponent,
    CodeComponent,
    ColumnComponent,
    DataTableComponent,
    DiffComponent,
    DividerComponent,
    DynamicString,
    FrameComponent,
    GridComponent,
    IconComponent,
    ImageComponent,
    ListComponent,
    MermaidComponent,
    MetricComponent,
    ModalComponent,
    ProgressComponent,
    RowComponent,
    SliderComponent,
    StatusComponent,
    TabsComponent,
    TextComponent,
    TextFieldComponent,
    _ClosedModel,
    _ComponentBase,
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


# All 30 CLIO catalog components, in the same order as the original
# hand-maintained union (a2ui_v091.py, pre-slice) so consumers see no churn.
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
