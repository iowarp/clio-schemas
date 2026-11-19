"""Components for gridded and profiled fields: layered map, section, profile stack.

General views for any field with gridded or profiled data. Their names,
properties and modes carry no domain vocabulary: a layered map shows gridded
fields, points, tracks and shapes on one time axis; a section shows a field
along a path against a vertical coordinate; a profile stack shows many
vertical profiles from a table.

They follow the same contracts as the bounded components: tabular content is
inline rows OR ``dataUri`` (never both, never neither), gridded content is a
registered artifact (``gridUri``, ``sectionUri``) read through bounded server
routes, linking uses the shared ``/selection/<key>`` SelectionState, and
drawn geometry, moved points and excluded profiles are data-model bindings,
so the person's decisions travel to the agent with every action.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from clio_schemas.a2ui.v0_9_1.bounded_components import DataQuery, FieldName, MapCamera
from clio_schemas.a2ui.v0_9_1.components import (
    ARTIFACT_URI_PATTERN,
    TABLE_DATA_URI_PATTERN,
    Action,
    DynamicString,
    DynamicValue,
    _ClosedModel,
    _ComponentBase,
    _DataBinding,
    _FunctionCall,
)

#: Data colour ramps: the interface's perceptual scales plus one diverging ramp.
FIELD_COLORMAPS = ("viridis", "magma", "plasma", "cividis", "turbo", "grayscale", "balance")
MAX_MAP_LAYERS = 12
MAX_INLINE_PROFILE_ROWS = 5_000
MAX_SWITCH_VARIABLES = 12
LAYER_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
FieldColormap = Literal["viridis", "magma", "plasma", "cividis", "turbo", "grayscale", "balance"]
ViewHeight = Annotated[int, Field(ge=160, le=2000)]
ValueRange = Annotated[list[float], Field(min_length=2, max_length=2)]
SwitchVariables = Annotated[list[FieldName], Field(min_length=1, max_length=MAX_SWITCH_VARIABLES)]
Cell = str | float | int | bool | None


def _bound(value: object) -> bool:
    return isinstance(value, _DataBinding | _FunctionCall)


def _check_range(value_range: list[float] | None) -> None:
    if value_range is not None and not value_range[0] < value_range[1]:
        raise ValueError("valueRange must be [low, high] with low < high")


class MapLayer(_ClosedModel):
    """One layer of a layered map: a grid, points, tracks or shapes."""

    id: Annotated[str, StringConstraints(pattern=LAYER_ID_PATTERN)]
    kind: Literal["grid", "points", "tracks", "shapes"]
    label: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    visible: bool = True
    opacity: float = Field(default=1.0, ge=0, le=1)
    # grid
    gridUri: str | None = Field(default=None, pattern=ARTIFACT_URI_PATTERN)
    variable: FieldName | None = None
    timeDimension: FieldName | None = None
    fixed: dict[FieldName, str | float] | None = None
    # points and tracks
    dataUri: str | None = Field(default=None, pattern=TABLE_DATA_URI_PATTERN)
    dataQuery: DataQuery | None = None
    latitudeField: FieldName | None = None
    longitudeField: FieldName | None = None
    idField: FieldName | None = None
    labelField: FieldName | None = None
    timeField: FieldName | None = None
    trackField: FieldName | None = None
    categoryField: FieldName | None = None
    valueField: FieldName | None = None
    editable: bool = False
    # shapes
    geojsonUri: str | None = Field(default=None, pattern=ARTIFACT_URI_PATTERN)
    # colour
    colormap: FieldColormap | None = None
    valueRange: ValueRange | None = None
    unit: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def _kind_rules(self) -> MapLayer:
        _check_range(self.valueRange)
        sources = {
            "grid": self.gridUri,
            "points": self.dataUri,
            "tracks": self.dataUri,
            "shapes": self.geojsonUri,
        }
        if sources[self.kind] is None:
            need = {
                "grid": "gridUri",
                "points": "dataUri",
                "tracks": "dataUri",
                "shapes": "geojsonUri",
            }[self.kind]
            raise ValueError(f"a {self.kind} layer needs {need}")
        others = {"gridUri": self.gridUri, "dataUri": self.dataUri, "geojsonUri": self.geojsonUri}
        extra = [k for k, v in others.items() if v is not None and v != sources[self.kind]]
        if extra:
            raise ValueError(f"a {self.kind} layer takes no {extra}")
        if self.kind == "grid" and self.variable is None:
            raise ValueError("a grid layer needs variable")
        if self.kind in ("points", "tracks"):
            missing = [
                n
                for n in ("latitudeField", "longitudeField", "idField")
                if getattr(self, n) is None
            ]
            if missing:
                raise ValueError(f"a {self.kind} layer needs {missing}")
        if self.kind == "tracks" and (self.trackField is None or self.timeField is None):
            raise ValueError("a tracks layer needs trackField and timeField")
        if self.editable and self.kind != "points":
            raise ValueError("only a points layer can be editable")
        if self.dataQuery is not None and self.dataUri is None:
            raise ValueError("dataQuery applies only to dataUri")
        return self


class MapDraw(_ClosedModel):
    """What the person may draw, and where the drawn GeoJSON geometry is written."""

    mode: Literal["box", "path", "point"]
    value: _DataBinding


class LayeredMapComponent(_ComponentBase):
    """Gridded fields, points, tracks and shapes on one flat map with a shared time axis."""

    component: Literal["clio.layered-map.v1"] = "clio.layered-map.v1"
    title: DynamicString | None = None
    camera: MapCamera | _DataBinding | None = None
    layers: list[MapLayer] = Field(min_length=1, max_length=12)
    time: DynamicValue | None = None
    timeField: FieldName | None = None
    selection: DynamicValue | None = None
    selectionField: FieldName | None = None
    draw: MapDraw | None = None
    edits: _DataBinding | None = None
    action: Action | None = None
    actionLabel: DynamicString | None = None
    height: ViewHeight | None = None

    @model_validator(mode="after")
    def _rules(self) -> LayeredMapComponent:
        ids = [layer.id for layer in self.layers]
        if len(ids) != len(set(ids)):
            raise ValueError("layer ids must be unique")
        if _bound(self.time) and self.timeField is None:
            raise ValueError("timeField is required when time is bound")
        if _bound(self.selection) and self.selectionField is None:
            raise ValueError("selectionField is required when selection is bound")
        editable = any(layer.editable for layer in self.layers)
        if editable and self.edits is None:
            raise ValueError("an editable points layer needs edits bound to a data-model path")
        if self.edits is not None and not editable:
            raise ValueError("edits needs an editable points layer")
        return self


class SectionComponent(_ComponentBase):
    """A field along a path against depth, pressure or height, with contours and stations."""

    component: Literal["clio.section.v1"] = "clio.section.v1"
    title: DynamicString | None = None
    sectionUri: str = Field(pattern=ARTIFACT_URI_PATTERN)
    variable: FieldName | None = None
    variables: SwitchVariables | None = None
    colormap: FieldColormap | None = None
    valueRange: ValueRange | None = None
    unit: str | None = Field(default=None, max_length=40)
    contourInterval: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    invertVertical: bool | None = None
    selection: DynamicValue | None = None
    selectionField: FieldName | None = None
    pointer: _DataBinding | None = None
    height: ViewHeight | None = None

    @model_validator(mode="after")
    def _rules(self) -> SectionComponent:
        _check_range(self.valueRange)
        if _bound(self.selection) and self.selectionField is None:
            raise ValueError("selectionField is required when selection is bound")
        return self


class ProfileStackComponent(_ComponentBase):
    """Many vertical profiles from a table against depth, pressure or height."""

    component: Literal["clio.profile-stack.v1"] = "clio.profile-stack.v1"
    title: DynamicString | None = None
    data: list[dict[str, Cell]] | None = Field(
        default=None, min_length=1, max_length=MAX_INLINE_PROFILE_ROWS
    )
    dataUri: str | None = Field(default=None, pattern=TABLE_DATA_URI_PATTERN)
    dataQuery: DataQuery | None = None
    profileField: FieldName
    verticalField: FieldName
    valueField: FieldName
    variables: SwitchVariables | None = None
    overlayField: FieldName | None = None
    labelField: FieldName | None = None
    categoryField: FieldName | None = None
    invertVertical: bool = True
    unit: str | None = Field(default=None, max_length=40)
    verticalUnit: str | None = Field(default=None, max_length=40)
    selection: DynamicValue | None = None
    selectionField: FieldName | None = None
    excluded: _DataBinding | None = None
    action: Action | None = None
    actionLabel: DynamicString | None = None
    height: ViewHeight | None = None

    @model_validator(mode="after")
    def _rules(self) -> ProfileStackComponent:
        if (self.data is None) == (self.dataUri is None):
            raise ValueError("exactly one of data or dataUri is required")
        if self.dataQuery is not None and self.dataUri is None:
            raise ValueError("dataQuery applies only to dataUri")
        if _bound(self.selection) and self.selectionField is None:
            raise ValueError("selectionField is required when selection is bound")
        return self


FIELD_COMPONENT_MODELS = (LayeredMapComponent, SectionComponent, ProfileStackComponent)
