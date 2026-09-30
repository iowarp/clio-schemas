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

from pydantic import (
    BaseModel,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

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
#: dataQuery bounds, copied from the table-query server's request model
#: (clio-agent ``gact/artifacts/table_query.py``). MAX_QUERY_LIMIT is a
#: generous schema-level safety ceiling on ``limit`` (a client cannot ask
#: for an unbounded response), not the server's actual per-response cap —
#: that is server-configured (``artifacts.table_query_max_rows``) and may be
#: lower.
MAX_QUERY_COLUMNS = 64
MAX_QUERY_FILTERS = 64
MAX_QUERY_IN_VALUES = 10_000
MAX_QUERY_METRICS = 64
MAX_QUERY_PER_ENTITY = 2_000
DEFAULT_QUERY_PER_ENTITY = 500
MAX_QUERY_LIMIT = 50_000

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


QueryFilterOp = Literal["eq", "in", "range", "isnull", "contains"]
QueryMetricFn = Literal["mean", "min", "max", "count", "sum", "median"]
DownsampleMode = Literal["none", "stride", "per_entity_lttb"]


def _is_query_scalar(value: object) -> bool:
    return isinstance(value, str | int | float | bool)


def _int_from_whole_number(value: object) -> object:
    """Coerce a whole-number ``float`` (e.g. ``5.0``) to ``int`` before strict validation.

    JSON Schema's ``"type": "integer"`` accepts any JSON number without a
    fractional part, so a producer that serializes an integer as ``5.0`` (a
    legitimate JSON number) passes catalog validation but was then rejected
    by this model's ``strict=True`` config, which does not coerce ``float``
    to ``int`` even losslessly. Used as a ``field_validator(mode="before")``
    on ``limit``/``maxPerEntity`` so the two validators agree: a bare
    ``int`` passes through untouched, a fractional ``float`` (``5.5``) is
    left for strict ``int`` validation to reject, and any other type
    (``str``, ``bool``, ...) is also left alone so strict validation still
    rejects it exactly as before.
    """

    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


class ChartQueryFilter(_ClosedModel):
    """One ``dataQuery.filter`` predicate; all predicates are AND-ed together.

    * ``eq``: ``value`` is a non-null scalar.
    * ``in``: ``value`` is a non-empty list of non-null scalars.
    * ``range``: ``value`` is ``[min, max]``, inclusive; either side may be null.
    * ``isnull``: ``value`` is omitted/``true`` (match nulls) or ``false``
      (match non-nulls).
    * ``contains``: ``value`` is a non-empty string; matches a case-insensitive
      substring of a string column (the table viewer's per-column text filter).
    """

    column: ChartFieldName
    op: QueryFilterOp
    value: JsonValue = None

    @model_validator(mode="after")
    def _check_value(self) -> ChartQueryFilter:
        value = self.value
        if self.op == "eq":
            if not _is_query_scalar(value):
                raise ValueError("eq filter requires a non-null scalar value")
        elif self.op == "in":
            if not isinstance(value, list) or not 1 <= len(value) <= MAX_QUERY_IN_VALUES:
                raise ValueError(f"in filter requires a list of 1..{MAX_QUERY_IN_VALUES} values")
            if not all(_is_query_scalar(item) for item in value):
                raise ValueError("in filter values must be non-null scalars")
        elif self.op == "range":
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError("range filter requires [min, max]")
            if not all(item is None or _is_query_scalar(item) for item in value):
                raise ValueError("range bounds must be scalars or null")
        elif self.op == "contains":
            if not isinstance(value, str) or not value:
                raise ValueError("contains filter requires a non-empty string value")
        elif value is not None and not isinstance(value, bool):
            raise ValueError("isnull filter value must be a boolean when given")
        return self


class ChartQueryMetric(_ClosedModel):
    """One aggregate output column; the server names it ``{column}_{fn}``."""

    column: ChartFieldName
    fn: QueryMetricFn


class ChartQueryAggregate(_ClosedModel):
    """Group rows by ``groupBy`` (empty: one global group) and reduce with ``metrics``."""

    groupBy: list[ChartFieldName] = Field(default_factory=list, max_length=MAX_QUERY_COLUMNS)
    metrics: list[ChartQueryMetric] = Field(min_length=1, max_length=MAX_QUERY_METRICS)

    @model_validator(mode="after")
    def _check_names(self) -> ChartQueryAggregate:
        if len(set(self.groupBy)) != len(self.groupBy):
            raise ValueError("groupBy columns must be distinct")
        names = [f"{metric.column}_{metric.fn}" for metric in self.metrics]
        if len(set(names)) != len(names):
            raise ValueError("aggregate metrics must be distinct")
        clash = sorted(set(names) & set(self.groupBy))
        if clash:
            raise ValueError(f"metric output names collide with groupBy columns: {clash}")
        return self


class ChartQuerySort(_ClosedModel):
    """One ``dataQuery.sort`` key; earlier entries in the list sort first."""

    column: ChartFieldName
    desc: bool = False


class ChartQueryDownsample(_ClosedModel):
    """How the server thins the filtered/aggregated rows before ``limit`` applies.

    ``none`` keeps every row; ``stride`` keeps evenly spaced rows (per
    ``entityColumn`` up to ``maxPerEntity`` when set, else overall up to
    ``limit``); ``per_entity_lttb`` runs Largest-Triangle-Three-Buckets on
    ``(x, y)`` per entity and needs both ``x`` and ``y``.
    """

    mode: DownsampleMode = "none"
    entityColumn: ChartFieldName | None = None
    x: ChartFieldName | None = None
    y: ChartFieldName | None = None
    maxPerEntity: int = Field(default=DEFAULT_QUERY_PER_ENTITY, ge=1, le=MAX_QUERY_PER_ENTITY)

    @field_validator("maxPerEntity", mode="before")
    @classmethod
    def _coerce_max_per_entity(cls, value: object) -> object:
        return _int_from_whole_number(value)

    @model_validator(mode="after")
    def _check_mode(self) -> ChartQueryDownsample:
        if self.mode == "per_entity_lttb" and (self.x is None or self.y is None):
            raise ValueError("per_entity_lttb requires both x and y")
        return self


class ChartDataQuery(_ClosedModel):
    """A server-side table query applied to ``dataUri`` before the rows reach the chart.

    The request body of ``POST /v1/artifacts/{id}/table-query`` (clio-agent
    ``TableQueryRequest``) minus ``format``, which the renderer always sends
    as ``json``. ``columns`` may be omitted to request every column of
    ``dataUri`` — except alongside ``aggregate``, where ``columns`` is
    required: an aggregate's output columns (e.g. ``price_mean``) don't
    exist in the source and so cannot be inferred. The server runs filter,
    then aggregate, then downsample, then sort, then offset/limit.

    ``limit`` bounds the rows in ONE response (a transfer size), not the
    underlying data: ``offset`` pages through a larger result across several
    requests. When a chart or map query would otherwise exceed ``limit``
    without an explicit ``downsample``, the server instead samples evenly
    across the full range and reports that it did, rather than silently
    truncating to the first rows. The schema's own maximum on ``limit`` is a
    generous safety ceiling, not the deployment's real per-response cap,
    which is server-configured. A viewer (e.g. an interactive data-table)
    may layer its own user-driven paging/filtering/sorting on top of this
    ``dataQuery`` without replacing it — the agent's own filter/aggregate/
    downsample intent still applies underneath.
    """

    columns: list[ChartFieldName] | None = Field(
        default=None, min_length=1, max_length=MAX_QUERY_COLUMNS
    )
    filter: list[ChartQueryFilter] | None = Field(default=None, max_length=MAX_QUERY_FILTERS)
    aggregate: ChartQueryAggregate | None = None
    downsample: ChartQueryDownsample | None = None
    sort: list[ChartQuerySort] | None = Field(default=None, max_length=MAX_QUERY_COLUMNS)
    offset: int | None = Field(default=None, ge=0)
    limit: int | None = Field(default=None, ge=1, le=MAX_QUERY_LIMIT)

    @field_validator("offset", "limit", mode="before")
    @classmethod
    def _coerce_offset_and_limit(cls, value: object) -> object:
        return _int_from_whole_number(value)

    @model_validator(mode="after")
    def _check_columns(self) -> ChartDataQuery:
        if self.columns is not None and len(set(self.columns)) != len(self.columns):
            raise ValueError("columns must be distinct")
        if self.aggregate is not None and self.columns is None:
            raise ValueError("columns is required when aggregate is set")
        return self


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
