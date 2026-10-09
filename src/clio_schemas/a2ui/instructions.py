"""Producer guidance shipped alongside each builtin catalog's sidecar.

Rewritten from the lore in clio-agent's ``gact/a2ui_tools.py`` tool docstring
as *guidance* — when to reach for a component and how to bind it — never as
``EXACTLY``/``never`` behavioral handcuffs, and never restating a component's
property shape (the catalog file, validated by JSON Schema, is the contract;
duplicating it here would only drift).
"""

from __future__ import annotations

WORKSPACE_INSTRUCTIONS_MD = """\
# Producing CLIO workspace surfaces

Charts, maps, and tables built from the components below render inline in
the chat as interactive views — hoverable, clickable, linkable to each
other — the moment a surface carries one. Saving the same data as a `.json`
or image file through the artifact tools instead produces a file in the
workspace, not a rendered chart; the user sees a file attachment, never the
chart itself, unless a surface also exists. The `clio-workspace` catalog
covers layout, input, and the CLIO scientific components (`clio.*`). Every
property shape is defined in `catalog.json` — this page is about *when* and
*how* to reach for each piece, not what its fields are.

## The component tree

A surface is a flat array of components, each with a stable `id`. Containers
(`Row`, `Column`, `List`, `Frame`, `Tabs`, `Modal`, `Grid`) reference their
children by id rather than nesting them inline — this keeps individual
components independently addressable for later `updateComponents` calls.
Exactly one component in the array must carry the id `root`; that is the
surface's mount point. A surface made of just one component — a single
chart or map with no surrounding container — still needs that rule: give
the lone component id `root` itself. The short ids in the one-component
examples below (`ch1`, `map1`, `t1`, ...) are naming the component's own
shape for this page's purposes, not a complete surface.
For several views, make `root` a layout component and reference every view
from its child tree. A component that is not connected to `root` cannot
appear in the rendered surface; the producer rejects it with the missing ids.

## Binding values

For a report with several views, bind `Tabs.activeTab` when the agent should
review each tab or a shared control should navigate it. The value names the
tab's child id. A map's declared `camera` binding moves its real view and is
also updated by human navigation. Keep shared cameras and filters on shared
paths; do not infer control from arbitrary unbound paths. After a complex
change, use the available capture tool to inspect actual rendered pixels.

A property that accepts a dynamic value (most `label`/`text`/`value` fields)
can be a literal, or `{"path": "/some/pointer"}` to bind it to the surface's
data model. Prefer literals for anything static (titles, fixed labels) and
reserve bindings for values that change after the surface is created — the
data model is a separate `updateDataModel` call, so a bound value can be
refreshed without re-sending the component tree.

## Inline values or a dataset

Every component that carries rows, points, a diagram, source code, or a diff
takes its content two ways — inline (`data`/`rows`/`points`/`source`/`code`/
`diff`, small and bounded) or `dataUri` (a reference to a registered
artifact) — never both, never neither. Like `plot([1, 2, 3])` versus
`plot(dataset.x)`: inline is enough for what the agent already holds in the
turn; `dataUri` is for anything read from a file or a prior tool result, of
any size — an inline cap (e.g. the map's 500 points) limits what can be
drawn inline, never what can be referenced.

The three tabular components — `clio.chart.v1`, `clio.map.v1`,
`clio.data-table.v1` — additionally accept `dataQuery` alongside `dataUri`
(never with inline values): one shared shape (`$defs/DataQuery`) that
filters, aggregates, downsamples, and limits the referenced table
server-side before it reaches the component. Their `dataUri` names a registered
CSV or Parquet table, not a source JSON file. Check relevant workspace
artifacts before seeking a new external source; reuse a suitable table when
its provenance and columns answer the question. Preserve numeric columns as
numbers and timestamps as ISO-8601 strings with an offset when converting
source data; inspect the registered table's schema and a sample row before
building a view so a locale-formatted timestamp does not become a text
filter. When a component reads a dataset, it names columns with `*Field` properties (`xField`,
`latitudeField`, `entityField`, ...) instead of assuming a shape; the
validator checks these names against the dataset's real columns, so a wrong
one is a typed error, not a blank view.
For a control that updates a view locally, bind a filter's complete `value`
to the control's data-model path, for example `{"column": "depth", "op":
"range", "value": {"path": "/controls/depth"}}`. Initialize the path to a
two-value range before rendering. The renderer resolves changes into a fresh
data query; the bound value must satisfy the chosen filter operator.

When multiple views on one surface show the same observations, keep one
dataset identity across them. Components pointing at the same artifact
automatically share selection through the renderer's stable `__row` key. Small
inline views also link when each contains the same set of unique entity values,
even when their row order differs. The person need not request linking, and
ordinary same-dataset views need no producer-authored selection control or
path. For larger or evolving data, prefer one shared artifact so filtering,
sorting and pagination preserve row identity. For example, a script writes `stations.csv`
(columns `station`, `lat`, `lon`, `displacement_mm`), registered as
`artifact://artifact_stations01`; a `clio.chart.v1` `scatter` preset
(`"entityField": "station"`) and a `clio.map.v1`
(`"latitudeField": "lat"`, `"longitudeField": "lon"`, `"labelField":
"station"`) both set `"dataUri": "artifact://artifact_stations01"` —
clicking a point on the map highlights the matching row in the chart, and
vice versa, with no agent turn in between. Use an explicit `selection` path
and `selectionField` when views of different artifacts share a concept such
as the same station name.

## Choosing filters for exploratory views

Start with the scientific question and inspect the dataset's fields, units,
distinct values, and range. Offer a small number of dimensions that let a
reader isolate a phenomenon, compare groups, or inspect outliers. Row IDs and
nearly unique labels seldom help; spatial position, a measurement, or time
may help when the question calls for that kind of range. Match temporal
precision to the data and question rather than assuming every time field
should become a year filter.

Keep each chosen field in the registered artifact and the view's projected
`dataQuery.columns`. Maps can name useful columns with `filterFields`;
charts expose native filters for encoded fields, and tables for displayed
columns. The renderer owns the filter controls, so do not create buttons or
actions for them. Use `dataQuery.filter` for the initial scientific slice;
the reader's later filters narrow that slice. Check that the visible data,
counts, and `Reference this` agree after filtering.

## Routing actions

`Button`, checks, and several scientific components accept an `action`. Most
actions should be plain agent events (`{"event": {"name": "...", "context":
{...}}}`) — the agent receives them as an ordinary turn. Three action names
route elsewhere before the agent sees them: `approval.respond` goes to the
permission gate, and `run.cancel` / `run.retry` go to the run controller
(see this catalog's sidecar `events` map). Everything else, including
`agent.submit` and `form.submit`, is a plain agent event now — there is no
separate closed action vocabulary to satisfy.

When CLIO reports that a needed provider account is signed out, explain the
need in your answer and show an ordinary `Button` with the returned
`login_action` as its event. The declared `data_source/login/github`,
`data_source/login/google_drive` and `data_source/login/globus` events open
CLIO's private account UI on the client. Their context must contain the exact
`clio_id` and `workspace_id` returned by source status. Sign-in is performed
by the user; credentials never enter the surface or the agent's context.
Show the button in the answer, not only inside Activity. A click requests the
sign-in UI; it does not establish that sign-in or source connection succeeded.
Read source status after the user returns. Existing workspace files need no
remote source connection. Unsupported clients and offline archives cannot sign in.

`approval.respond` only reaches the permission gate when its `context`
carries a `permission_id` — that is, when the card is answering a REAL
pending native permission (a tool call CLIO already paused on; the agent
got the surface and its `permission_id` from that pause, not from writing
them itself). A `clio.approval.v1` card the agent builds and shows on its
own — asking the user a plain yes/no with no underlying paused tool call —
carries no `permission_id` at all, so its `approval.respond` is a plain
agent event like any other: the resolved `context` (e.g. `{"approved":
true}`) is delivered to the agent as the next turn's input, same as
`agent.submit`. Both are the SAME event name and the SAME component; which
lane it takes is decided structurally by whether `permission_id` is present,
never by wording. A `permission_id` that names no real pending permission
(unknown, already resolved, or expired) is a typed error either way — it is
never silently delivered to the agent instead.

## The scientific components, one example each

**Status** — a single labeled state, e.g. a running step:
`{"id": "s1", "component": "clio.status.v1", "label": "Ingest", "state": "running"}`.

**Metric** — exactly one number; compose several inside a `Row` or `Grid`
rather than reaching for an aggregate shape:
`{"id": "m1", "component": "clio.metric.v1", "label": "Peak displacement", "value": 4.2, "unit": \
"mm"}`.

**Progress** — a bounded or indeterminate operation:
`{"id": "p1", "component": "clio.progress.v1", "label": "Rendering", "value": 60, "max": 100}`.

**Callout** — a short flagged note, distinct from a plain `Text`:
`{"id": "c1", "component": "clio.callout.v1", "title": "Heads up", "body": "Station GNSS01 has a \
data gap.", "severity": "warning"}`.

**DataTable** — tabular rows, inline or from a dataset (see Inline values or
a dataset above); give a title via a sibling `Text`, not a property on the
table itself. Inline rows require `columns`; a `dataUri` table takes
`columns` from the dataset when omitted:
`{"id": "t1", "component": "clio.data-table.v1", "columns": ["station", "displacement_mm"], \
"rows": [{"station": "GNSS01", "displacement_mm": 3.1}]}`, or `{"id": "t1", "component": \
"clio.data-table.v1", "dataUri": "artifact://artifact_stations01", "dataQuery": {"limit": \
500}}`. Views over the same artifact link selected rows automatically. Use
`selection` with a matching `selectionField` for an explicit cross-artifact
link (see Shared selection below).

**Mermaid** — declarative diagram source only; no init directives or click
handlers. Inline `source`, or `dataUri` to a registered `.mmd`/text file:
`{"id": "d1", "component": "clio.mermaid.v1", "source": "graph TD; A-->B;"}`.

**Map** — labeled points or GeoJSON geometry; the renderer owns the
basemap, so never pass tile/style URLs. Inline points are capped at 500; a
`dataUri` map names its columns with `latitudeField`/`longitudeField`/
`labelField` (required) and optionally `idField`/`detailField`/
`categoryField` for categorical colours or `valueField` for a numeric colour
scale (with optional `valueLabel` and `valueUnit`), and is bounded by
`dataQuery`/`limit` instead.
The renderer supplies the corresponding legend; inline points may carry a
numeric `value` for the same continuous scale. Keep measured magnitudes numeric
in `value`/`valueField` rather than making each distinct number a category.
For exploratory maps, `filterFields` names columns worth narrowing; omit it
for the default map fields. A map needing filters on measured columns should
use a registered table even when only a few rows are shown: inline points do
not retain arbitrary measurement columns.
For time-ordered paths such as storm tracks, give `trackField` (the track ID)
and `orderField` (an ISO-8601 timestamp or numeric sequence) with a `dataUri` map.
The renderer joins positions within each track, keeps the observations
selectable, and colours paths by track when no other colour field is set.
For a large track archive, choose a meaningful period or named subset with
`dataQuery` so people can distinguish paths. Keep the full file as an artifact;
an arbitrary row limit can cut a track in half.
Check a few parsed coordinates against the source before registering a path
dataset. A swapped or repeated latitude/longitude column produces a plausible
looking file but a misleading map.
For a registered GeoJSON FeatureCollection of points, lines, or polygons,
use `geojsonUri` and optionally name feature-property fields with `labelField`,
`detailField`, `categoryField`, or `valueField`. The renderer fits the geometry,
colours it, and provides feature selection. Do not also pass `points` or `dataUri`.
`{"id": "map1", "component": "clio.map.v1", "points": [{"id": "s1", "label": "GNSS01", \
"latitude": 34.1, "longitude": -118.3}]}`, or `{"id": "map1", "component": "clio.map.v1", \
"dataUri": "artifact://artifact_stations01", "latitudeField": "lat", "longitudeField": "lon", \
"labelField": "station"}`. `selected` still marks one point by id. Views over
the same artifact link selected rows automatically; bind `selection` with a
matching `selectionField` for an explicit cross-artifact link.

**Workflow** — a bounded node/edge graph, useful for showing a multi-step
plan's progress. Inline `nodes` and `edges` together, or `dataUri` to a
registered JSON file shaped `{"nodes": [...], "edges": [...]}` (never both,
never neither):
`{"id": "wf1", "component": "clio.workflow.v1", "nodes": [{"id": "fetch", "label": "Fetch"}, \
{"id": "process", "label": "Process"}], "edges": [{"source": "fetch", "target": "process"}]}`.

**Slider** — `clio.slider.v1` is a numeric control for a physical
parameter: it keeps a `step` (for example `0.01`), shows `unit`, and has a
number box so an exact value can be typed. Set `range: true` with a pair of
values for a lower and upper bound. The Basic `Slider` moves in whole
numbers only; use this one for thresholds, scale factors, intervals, or any fraction:
`{"id": "iso", "component": "clio.slider.v1", "label": "Density threshold", "min": 0, \
"max": 1, "step": 0.01, "value": {"path": "/iso"}}`.

**Date and time** — `DateTimeInput` accepts an ISO 8601 string (or a bound
string path). Set `enableDate` and/or `enableTime` for the parts the person
needs to edit; optional `min` and `max` constrain the allowed value.

**Message drafts** — `clio.message-draft.v1` presents labelled alternatives
for an email, Slack message, or text when the person asks for wording they can
review or adapt. Supply one to eight versions with distinct labels and bodies;
email versions can include recipients and subjects. The viewer can edit the
displayed draft directly, switch between alternatives without losing those
edits, copy it, choose a mail destination for an email draft, or put the edited
version into the composer. The mail links carry recipients, subject, and body,
but not file attachments. None of those actions sends the message from CLIO.

**Weather** — `clio.weather.v1` presents observed conditions and hourly or
daily forecasts for a location, including field sites. Supply the source,
observation time, IANA time zone, units, and structured forecast values from
the evidence already gathered. Longer hourly and daily series remain browsable
in the viewer; the renderer makes no weather request. An
ordinary weather question may benefit from this compact view alongside a
short answer to the person's actual decision.
Use an explicit UTC offset or Z in `observedAt` and every hourly `time`
(for example `2026-10-03T08:00:00-07:00`); daily `date` is `YYYY-MM-DD`.

**Steps** — `clio.steps.v1` presents a protocol, setup guide, or recipe when
the person will work through several actions. Supply numbered steps, optional
warnings, durations, and scalable quantities. Bind `progress` to a data-model
path when progress should remain part of the surface's state; the renderer
handles checkboxes, timers, and rescaling without another agent turn.
For a recipe, put measured materials in `ingredients` and cooking actions in
`steps`. Ingredients scale with servings but do not count toward completed
steps. Keep the title independent of the starting servings, since that value
can change in the viewer. A protocol without a separate materials list can keep quantities on
the steps that consume them.
Put variable amounts in `quantity` and `quantityUnit`; keep `detail` valid
after the person changes the scale. For four samples at 2 mL each, use
`baseAmount: 4`, `quantity: 8`, and detail “Add 2 mL to each tube.” A detail
saying “8 mL total for 4 samples” becomes false when scaled; omitting the
2 mL per-tube instruction leaves the procedure ambiguous.
For countable items, set `quantityUnit` to the singular label and
`quantityUnitPlural` to the plural label so 1 egg and 2 eggs both read well.
For recipes, do not repeat starting cup, tablespoon, or egg amounts in `detail`
beside a scaled gram or count quantity; those fixed equivalents become false
when servings change. Keep checkboxes for actions the person performs, and
combine closely related preparation where that makes the guide easier to scan.

**MeshViewport** — an orbitable 3D view of one registered triangle mesh.
It reads GLB/glTF, OBJ (optionally with `materialUri` for an MTL artifact),
STL, PLY, FBX, 3MF, VTK, VTP, and Draco. Put the file in an artifact and
set `meshUri`; set `format` when the file cannot be recognized from its
bytes, especially 3MF or binary STL. Parsing failures name the format and
the missing or invalid shape. Generic files show geometry and material
colours; texture images are reported as unavailable. A CLIO FEA GLB can
also carry node or cell results: `field` colors by one result, `frame`
chooses a result frame, and `thresholdField` with `thresholdMin`/
`thresholdMax` shows cells in range. Bind those values to controls when
the person should explore them. Bind `camera` to a path when a later action
should retain the chosen angle. Viewports with a `syncGroup` share camera
and color range:
`{"id": "vp1", "component": "clio.mesh-viewport.v1", "title": "Design", "meshUri": \
"artifact://artifact_abc123", "field": "DENSITY", "frame": {"path": "/cycle"}, \
"thresholdField": "DENSITY", "thresholdMin": {"path": "/iso"}, "thresholdMax": 1}`.

**RasterViewport** — `clio.raster-viewport.v1` presents a registered
two-dimensional NPY, numeric CSV grid, GeoTIFF, NetCDF, or zipped Zarr
artifact. Set `rasterUri`; for a NetCDF or Zarr file with several arrays,
set `variable`, or `band` for a multiband GeoTIFF. Optionally set `unit`
and a `colormap`. The viewer queries a bounded sample for its visible
extent and supplies hover values, a colour legend, pan, zoom, region
selection, export, and Reference this without renderer actions in the spec.
Use this when the spatial pattern or grid cells matter more than a table
of sampled values.

**Chart** — `clio.chart.v1` draws any Vega-Lite chart over tabular rows.
Prefer a `preset` over writing a `spec`: `trajectories` (one line per entity
over time or a step), `spectra` (one curve per entity over wavelength or
frequency), `scatter`, `boxplot` (distribution per category, with each entity
as a point), and `heatmap` (grid colored by a value). Fill a preset by naming
columns: `xField`, `yField`, `entityField` (what one line, point, or cell
belongs to — a run, a sample, a station), and optionally `colorField` (a
group), `facetField` (small multiples), and `xType` (`temporal`,
`quantitative`, `ordinal`). The renderer highlights selected data and dims
the rest. For trajectories and spectra, a dot selects one observation;
Ctrl-click selects the whole curve; Shift adds or removes at either level.
When comparing series from different
calendar periods, an elapsed-time or sample-index `xField` from each series'
own start makes their shapes comparable. Keep absolute timestamps in the
dataset for map, table, and hover context. If a few series are requested
without names, choose a representative subset, state the criterion, and let
the reader refine it. The rows come only from `data`
(small inline rows) or `dataUri` (a registered table artifact, optionally narrowed with
`dataQuery`) — never from the spec. `dataQuery` is the server's table query:
`columns`, `filter` (`{column, op, value}` with `op` one of `eq`, `in`,
`range`, `isnull`), `aggregate` (`groupBy` plus `metrics` of `{column, fn}`),
`downsample` (`mode` `none`, `stride`, or `per_entity_lttb` with `x`, `y`,
`entityColumn`, `maxPerEntity`), and `limit`. For many long series, keep
each entity's shape with `per_entity_lttb`:
`"dataQuery": {"columns": ["t", "disp_mm", "station"], "filter": [{"column": \
"network", "op": "eq", "value": "CI"}], "downsample": {"mode": "per_entity_lttb", \
"entityColumn": "station", "x": "t", "y": "disp_mm", "maxPerEntity": 500}}`.
When no preset fits, a hand-written `spec` must leave `data` out (or
use exactly `{"name": "source"}`), must not contain `url`, and stays small
(64 KB, at most 8 views). Its top level takes the usual Vega-Lite grammar
(`mark`, `encoding`, `layer`, `facet`, `hconcat`, `vconcat`, `concat`,
`repeat`, `spec`, `transform`, `params`, `width`, `height`, `title`,
`resolve`, `config`, `autosize`, `description`, `$schema`, `data`), plus
the data-free layout keys `columns` (wraps a facet/repeat/concat grid),
`spacing`, `padding`, `align`, `bounds`, `center`, and `projection` (a
geoshape or point-map projection) — never `url`, anywhere. A wrapped
facet, three columns per row:
`{"facet": {"field": "category", "type": "nominal"}, "columns": 3, \
"spec": {"mark": "point", "encoding": {"x": {"field": "t", "type": \
"quantitative"}, "y": {"field": "v", "type": "quantitative"}}}}`.

A row cell can also hold a GeoJSON Geometry object (`Point`, `MultiPoint`,
`LineString`, `MultiLineString`, `Polygon`, `MultiPolygon`, or
`GeometryCollection`) instead of a scalar — enough for a real choropleth
over rows the agent already holds, no artifact needed: a `geoshape` mark
reads a `shape` encoding typed `geojson`, with `projection` for the map
projection:
`"data": [{"geometry": {"type": "Polygon", "coordinates": [[[-100.0, \
40.0], [-99.0, 40.0], [-99.0, 41.0], [-100.0, 41.0], [-100.0, 40.0]]]}, \
"value": 12}]` with spec `{"mark": "geoshape", "encoding": {"shape": \
{"field": "geometry", "type": "geojson"}, "color": {"field": "value", \
"type": "quantitative"}}, "projection": {"type": "mercator"}}` — no
`projection.fit` needed; the renderer fits the map to the geometry
present in the rows. A lon/lat point map needs no geometry cells, just
`latitude`/`longitude` encodings plus `projection`:
`{"mark": "circle", "encoding": {"latitude": {"field": "lat", "type": \
"quantitative"}, "longitude": {"field": "lon", "type": "quantitative"}, \
"size": {"field": "value", "type": "quantitative"}}, "projection": \
{"type": "equirectangular"}}`.

A complete preset-based component, for comparison:
`{"id": "ch1", "component": "clio.chart.v1", "title": "Displacement", "preset": \
"trajectories", "xField": "t", "xType": "temporal", "yField": "disp_mm", "entityField": \
"station", "dataUri": "artifact://artifact_abc123"}`.

**Shared selection** — `clio.chart.v1`, `clio.data-table.v1`, and
`clio.map.v1` automatically link rows when they read the same `dataUri` on
one surface. The renderer uses the server's stable `__row` key. For links
across different artifacts, bind `selection` to `/selection/<key>`; the value
there is `{"field": "<column>", "values": [...], "source": "<component id>"}`.
Every component bound to the same path follows it: clicking a point in a
chart highlights the same observation in the table and on the map, with no
agent turn in between. Seed an explicit selection with `updateDataModel` at that path,
and read the current one from the data model (or a `Button` whose event
context binds the path) when the scientist asks about "the selected" items.
A chart's selection covers `selectionField`; trajectory and spectra presets
default to `__row` for exact point selection while retaining `entityField`
for line geometry. `clio.map.v1` and `clio.data-table.v1` have no such default,
so `selectionField` is required on either whenever `selection` is bound to
a path — name the same dataset column every linked component uses, or the
values on each side won't actually match up. To set a selection from an
action instead, call
`selectData` with the path, the field, and the ids; it writes
`{"field": ..., "values": rowIds, "source": "selectData"}` there:
`{"functionCall": {"call": "selectData", "args": {"path": "/selection/stations", \
"field": "station", "rowIds": ["GNSS01", "GNSS07"]}, "returnType": "void"}}`.

**Artifact** — reference a registered artifact by its returned URI (an
`artifact://` id if that is all registration returned), never a bare
filesystem path:
`{"id": "a1", "component": "clio.artifact.v1", "name": "results.csv", "uri": \
"artifact://artifact_abc123", "mediaType": "text/csv"}`.

**Code** — syntax-highlighted source, not wrapped in a `Text` block. Inline
`code`, or `dataUri` to a registered source file (`language` is always
required, since it can't be inferred from either):
`{"id": "code1", "component": "clio.code.v1", "code": "print('hello')", "language": "python"}`.

**Diff** — a unified diff for one path. Inline `diff`, or `dataUri` to a
registered diff/patch file:
`{"id": "diff1", "component": "clio.diff.v1", "path": "src/model.py", "diff": "@@ -1,2 +1,2 \
@@..."}`.

**ActionCard** — up to six labeled actions attached to a short pitch:
`{"id": "ac1", "component": "clio.action-card.v1", "title": "Rerun with corrected offsets?", \
"body": "The last run used a stale baseline.", "severity": "info", "actions": [{"label": "Rerun", \
"action": {"event": {"name": "run.retry"}}}]}`.

**Approval** — a gated decision, one to four actions, in two modes (see
Routing actions above):
- **Standalone** — the agent's own yes/no question, with no paused tool call
  behind it. `context` carries only the decision, and the answer comes back
  as a plain agent turn:
  `{"id": "ap1", "component": "clio.approval.v1", "title": "Delete 3 stale \
checkpoints?", "reason": "Disk pressure on the run volume.", "risk": \
"Checkpoints cannot be recovered once removed.", "actions": [{"label": \
"Approve", "action": {"event": {"name": "approval.respond", "context": \
{"approved": true}}}}, {"label": "Cancel", "action": {"event": {"name": \
"approval.respond", "context": {"approved": false}}}}]}`.
- **Bound to a pending permission** — answering a real paused tool call.
  `context` carries the `permission_id` CLIO handed the surface plus the
  decision as `action` (`allow` / `deny` / `allow_session` /
  `allow_workspace`), and the answer resolves that permission instead of
  starting a turn:
  `{"id": "ap2", "component": "clio.approval.v1", "title": "Allow deleting \
scratch.txt?", "reason": "The agent wants to remove a working file.", \
"risk": "The file cannot be recovered once removed.", "actions": \
[{"label": "Allow", "action": {"event": {"name": "approval.respond", \
"context": {"permission_id": "perm_abc123", "action": "allow"}}}}, \
{"label": "Deny", "action": {"event": {"name": "approval.respond", \
"context": {"permission_id": "perm_abc123", "action": "deny"}}}}]}`.

## Accessibility

`accessibility.label`/`.description` are always objects (or a data binding),
never a bare string on their own — wrap the text: `{"label": "Submit"}`.
"""

BASIC_INSTRUCTIONS_MD = """\
# Producing surfaces on the official Basic catalog

This is the upstream A2UI 0.9.1 `catalogs/basic/catalog.json` catalog,
vendored verbatim — general-purpose layout, text, media, and input
components with no CLIO-specific additions. See `rules.txt` in this
directory for the upstream authoring rules (required properties per
component); the catalog file itself is the full contract.
"""
