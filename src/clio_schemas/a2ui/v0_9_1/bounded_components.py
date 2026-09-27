"""The four CLIO components with bounded lists or cross-field business rules.

``clio.map.v1``, ``clio.time-series.v1``, ``clio.workflow.v1``, and
``clio.chart.v1`` are not built through ``_component_model`` (see
``components.py``) because they need ``Field(min_length=/max_length=)``
bounds and, for the time series and the chart, cross-field
``model_validator``s ("exactly one of series or dataUri"; for the chart,
exactly one of spec/preset and of data/dataUri plus the Vega-Lite spec guard
in :mod:`clio_schemas.a2ui.chart_spec`). Their catalog-file renderings are
hand-authored to match, in ``clio_schemas.a2ui.catalog_bounded``.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, JsonValue, StringConstraints, model_validator

from clio_schemas.a2ui.chart_spec import (
    MAX_INLINE_ROWS,
    SELECTION_PARAM_PATTERN,
    ChartSpecError,
    check_chart_spec,
    render_preset,
)
from clio_schemas.a2ui.v0_9_1.components import (
    ARTIFACT_URI_PATTERN,
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
    DynamicValue,
    FrameComponent,
    GridComponent,
    IconComponent,
    ImageComponent,
    ListComponent,
    MermaidComponent,
    MeshViewportComponent,
    MetricComponent,
    ModalComponent,
    NumberSliderComponent,
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
    selection: DynamicValue | None = None
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


#: Bounds for clio.chart.v1 (mirrored by catalog_bounded.py).
MAX_CHART_FIELD_LENGTH = 128
MIN_CHART_HEIGHT = 80
MAX_CHART_HEIGHT = 2000
MAX_QUERY_COLUMNS = 256
MAX_QUERY_FILTERS = 64
MAX_QUERY_OBJECT_KEYS = 16
MAX_QUERY_LIMIT = 1_000_000

ChartFieldName = Annotated[str, StringConstraints(min_length=1, max_length=MAX_CHART_FIELD_LENGTH)]
ChartRowValue = str | int | float | bool | None
ChartPreset = Literal["trajectories", "heatmap", "spectra", "boxplot", "scatter"]

#: The preset fill props, in the order render_preset receives them.
CHART_PRESET_FIELDS: tuple[str, ...] = (
    "xField",
    "yField",
    "entityField",
    "colorField",
    "facetField",
    "xType",
)


class ChartDataQuery(_ClosedModel):
    """A server-side table query applied to ``dataUri`` before the rows reach the chart.

    Mirrors a table-query request (projection, filters, aggregation,
    downsampling, row limit). The top level is closed; the filter, aggregate
    and downsample entries are open objects the server interprets, bounded
    in size.
    """

    columns: list[ChartFieldName] | None = Field(default=None, max_length=MAX_QUERY_COLUMNS)
    filter: (
        list[Annotated[dict[str, JsonValue], Field(max_length=MAX_QUERY_OBJECT_KEYS)]] | None
    ) = Field(default=None, max_length=MAX_QUERY_FILTERS)
    aggregate: dict[str, JsonValue] | None = Field(default=None, max_length=MAX_QUERY_OBJECT_KEYS)
    downsample: dict[str, JsonValue] | None = Field(default=None, max_length=MAX_QUERY_OBJECT_KEYS)
    limit: int | None = Field(default=None, ge=1, le=MAX_QUERY_LIMIT)


class ChartComponent(_ComponentBase):
    """A Vega-Lite chart over inline rows or an artifact, with a bindable selection."""

    component: Literal["clio.chart.v1"] = "clio.chart.v1"
    spec: dict[str, JsonValue] | None = None
    preset: ChartPreset | None = None
    xField: ChartFieldName | None = None
    yField: ChartFieldName | None = None
    entityField: ChartFieldName | None = None
    colorField: ChartFieldName | None = None
    facetField: ChartFieldName | None = None
    xType: Literal["temporal", "quantitative", "ordinal"] | None = None
    data: list[dict[str, ChartRowValue]] | None = Field(default=None, max_length=MAX_INLINE_ROWS)
    dataUri: str | None = Field(default=None, pattern=ARTIFACT_URI_PATTERN)
    dataQuery: ChartDataQuery | None = None
    selection: DynamicValue | None = None
    selectionParam: str | None = Field(default=None, pattern=SELECTION_PARAM_PATTERN)
    selectionField: ChartFieldName | None = None
    title: DynamicString | None = None
    height: float | None = Field(
        default=None, ge=MIN_CHART_HEIGHT, le=MAX_CHART_HEIGHT, allow_inf_nan=False
    )

    @model_validator(mode="after")
    def _validate_chart(self) -> ChartComponent:
        if (self.spec is None) == (self.preset is None):
            raise ValueError("exactly one of spec or preset is required")
        if (self.data is None) == (self.dataUri is None):
            raise ValueError("exactly one of data or dataUri is required")
        if self.dataQuery is not None and self.dataUri is None:
            raise ValueError("dataQuery applies only to dataUri")
        fields: dict[str, Any] = {name: getattr(self, name) for name in CHART_PRESET_FIELDS}
        if self.spec is not None:
            given = sorted(name for name, value in fields.items() if value is not None)
            if given:
                raise ValueError(f"{given} fill a preset and are not allowed with spec")
            violations = check_chart_spec(self.spec)
            if violations:
                raise ChartSpecError(violations)
        else:
            assert self.preset is not None
            render_preset(self.preset, {**fields, "selectionParam": self.selectionParam})
        return self


# All 33 CLIO catalog components, in the same order as the original
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
    MeshViewportComponent,
    NumberSliderComponent,
    ChartComponent,
)
