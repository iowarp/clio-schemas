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

The `clio-workspace` catalog covers layout, input, and the CLIO scientific
components (`clio.*`). Every property shape is defined in `catalog.json` —
this page is about *when* and *how* to reach for each piece, not what its
fields are.

## The component tree

A surface is a flat array of components, each with a stable `id`. Containers
(`Row`, `Column`, `List`, `Frame`, `Tabs`, `Modal`, `Grid`) reference their
children by id rather than nesting them inline — this keeps individual
components independently addressable for later `updateComponents` calls.
Exactly one component in the array must carry the id `root`; that is the
surface's mount point.

## Binding values

A property that accepts a dynamic value (most `label`/`text`/`value` fields)
can be a literal, or `{"path": "/some/pointer"}` to bind it to the surface's
data model. Prefer literals for anything static (titles, fixed labels) and
reserve bindings for values that change after the surface is created — the
data model is a separate `updateDataModel` call, so a bound value can be
refreshed without re-sending the component tree.

## Routing actions

`Button`, checks, and several scientific components accept an `action`. Most
actions should be plain agent events (`{"event": {"name": "...", "context":
{...}}}`) — the agent receives them as an ordinary turn. Three action names
route elsewhere before the agent sees them: `approval.respond` goes to the
permission gate, and `run.cancel` / `run.retry` go to the run controller
(see this catalog's sidecar `events` map). Everything else, including
`agent.submit` and `form.submit`, is a plain agent event now — there is no
separate closed action vocabulary to satisfy.

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

**DataTable** — tabular rows; give a title via a sibling `Text`, not a
property on the table itself:
`{"id": "t1", "component": "clio.data-table.v1", "columns": ["station", "displacement_mm"], \
"rows": [{"station": "GNSS01", "displacement_mm": 3.1}]}`. Bind `selection`
to share selected rows with charts and maps (see Shared selection below).

**TimeSeries** — small inline series go in `series`; a registered artifact
goes in `dataUri` instead (never both):
`{"id": "ts1", "component": "clio.time-series.v1", "xKey": "t", "yKeys": ["value"], "series": \
[{"t": 0, "value": 1.0}, {"t": 1, "value": 1.4}]}`.

**Mermaid** — declarative diagram source only; no init directives or click
handlers:
`{"id": "d1", "component": "clio.mermaid.v1", "source": "graph TD; A-->B;"}`.

**Map** — a bounded set of labeled points; the renderer owns the basemap, so
never pass tile/style URLs:
`{"id": "map1", "component": "clio.map.v1", "points": [{"id": "s1", "label": "GNSS01", \
"latitude": 34.1, "longitude": -118.3}]}`. `selected` still marks one point by
id; bind `selection` instead to share a selection with charts and tables.

**Workflow** — a bounded node/edge graph, useful for showing a multi-step
plan's progress:
`{"id": "wf1", "component": "clio.workflow.v1", "nodes": [{"id": "fetch", "label": "Fetch"}, \
{"id": "process", "label": "Process"}], "edges": [{"source": "fetch", "target": "process"}]}`.

**Slider** — `clio.slider.v1` is a numeric control for a physical
parameter: it keeps a `step` (for example `0.01`), shows `unit`, and has a
number box so an exact value can be typed. The Basic `Slider` moves in whole
numbers only; use this one for thresholds, scale factors, or any fraction:
`{"id": "iso", "component": "clio.slider.v1", "label": "Density threshold", "min": 0, \
"max": 1, "step": 0.01, "value": {"path": "/iso"}}`.

**MeshViewport** — an orbitable 3D view of one registered mesh (`.glb`,
results stored as node or cell fields). The mesh always comes from an
artifact, never inline. `field` names the field to color by and `showField`
toggles it; `frame` picks the frame of a field that changes over time
(increments, design cycles); `thresholdField` with `thresholdMin`/
`thresholdMax` shows only the cells whose value is in range, like a
Threshold filter. Bind the dynamic ones to the data model and drive them
from a `Slider`, `CheckBox`, or `ChoicePicker`. Bind `camera` to a path and
the view keeps the current camera there (and follows it when it changes),
so a `Button` can send the scientist's chosen angle to the agent. Viewports
that share a `syncGroup` move one camera and one color range together:
`{"id": "vp1", "component": "clio.mesh-viewport.v1", "title": "Design", "meshUri": \
"artifact://artifact_abc123", "field": "DENSITY", "frame": {"path": "/cycle"}, \
"thresholdField": "DENSITY", "thresholdMin": {"path": "/iso"}, "thresholdMax": 1}`.

**Chart** — `clio.chart.v1` draws any Vega-Lite chart over tabular rows.
Prefer a `preset` over writing a `spec`: `trajectories` (one line per entity
over time or a step), `spectra` (one curve per entity over wavelength or
frequency), `scatter`, `boxplot` (distribution per category, with each entity
as a point), and `heatmap` (grid colored by a value). Fill a preset by naming
columns: `xField`, `yField`, `entityField` (what one line, point, or cell
belongs to — a run, a sample, a station), and optionally `colorField` (a
group), `facetField` (small multiples), and `xType` (`temporal`,
`quantitative`, `ordinal`). Every preset already highlights the clicked
entity and dims the rest. The rows come only from `data` (small inline
rows) or `dataUri` (a registered table artifact, optionally narrowed with
`dataQuery`: columns, filter, aggregate, downsample, limit) — never from the
spec. When no preset fits, a hand-written `spec` must leave `data` out (or
use exactly `{"name": "source"}`), must not contain `url`, and stays small
(64 KB, at most 8 views):
`{"id": "ch1", "component": "clio.chart.v1", "title": "Displacement", "preset": \
"trajectories", "xField": "t", "xType": "temporal", "yField": "disp_mm", "entityField": \
"station", "dataUri": "artifact://artifact_abc123", "selection": {"path": \
"/selection/stations"}}`.

**Shared selection** — `clio.chart.v1`, `clio.data-table.v1`, and
`clio.map.v1` accept `selection`. Bind it to `/selection/<key>`; the value
there is `{"field": "<column>", "values": [...], "source": "<component id>"}`.
Every component bound to the same path follows it: clicking a line in a
chart highlights the same stations in the table and on the map, with no
agent turn in between. Seed a selection with `updateDataModel` at that path,
and read the current one from the data model (or a `Button` whose event
context binds the path) when the scientist asks about "the selected" items.
A chart's selection covers `selectionField` (by default the preset's
`entityField`).

**Artifact** — reference a registered artifact by its returned URI (an
`artifact://` id if that is all registration returned), never a bare
filesystem path:
`{"id": "a1", "component": "clio.artifact.v1", "name": "results.csv", "uri": \
"artifact://artifact_abc123", "mediaType": "text/csv"}`.

**Code** — syntax-highlighted source, not wrapped in a `Text` block:
`{"id": "code1", "component": "clio.code.v1", "code": "print('hello')", "language": "python"}`.

**Diff** — a unified diff for one path:
`{"id": "diff1", "component": "clio.diff.v1", "path": "src/model.py", "diff": "@@ -1,2 +1,2 \
@@..."}`.

**ActionCard** — up to six labeled actions attached to a short pitch:
`{"id": "ac1", "component": "clio.action-card.v1", "title": "Rerun with corrected offsets?", \
"body": "The last run used a stale baseline.", "severity": "info", "actions": [{"label": "Rerun", \
"action": {"event": {"name": "run.retry"}}}]}`.

**Approval** — a gated decision, one to four actions:
`{"id": "ap1", "component": "clio.approval.v1", "title": "Delete 3 stale checkpoints?", "reason": \
"Disk pressure on the run volume.", "risk": "Checkpoints cannot be recovered once removed.", \
"actions": [{"label": "Approve", "action": {"event": {"name": "approval.respond", "context": \
{"approved": true}}}}]}`.

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
