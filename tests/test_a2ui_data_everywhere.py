"""Cross-field "inline values or dataUri" coverage for issue #1533 (phase 2).

Every data-carrying component (``clio.map.v1``, ``clio.data-table.v1``,
``clio.workflow.v1``, ``clio.code.v1``, ``clio.mermaid.v1``,
``clio.diff.v1``, and the pre-existing ``clio.chart.v1``) accepts inline
values OR ``dataUri`` — never both, never neither — following the
``a2ui-component-design`` skill's rule #1. This module proves that contract
both at the pydantic level (:mod:`clio_schemas.a2ui.v0_9_1.bounded_components`)
and at the JSON Schema level (the rendered ``clio-workspace`` catalog), the
same two-sided proof pattern ``test_a2ui_corpus.py`` uses for the chart.

Each parametrized case in :data:`CASES` covers one of: valid inline, valid
dataUri (+ required fields), both present (invalid), neither present
(invalid), or a required field missing alongside dataUri (invalid).
:data:`DataQuery`-shape and one-definition-shared-by-three-components
coverage lives at the bottom.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from clio_schemas.a2ui.catalog_export import render_workspace_catalog
from clio_schemas.a2ui.v0_9_1.bounded_components import (
    ChartComponent,
    CodeComponent,
    DataTableComponent,
    DiffComponent,
    MapComponent,
    MermaidComponent,
    WorkflowComponent,
)
from clio_schemas.a2ui.validation import catalog_validators

WORKSPACE_CATALOG = render_workspace_catalog()
VALIDATORS = catalog_validators(WORKSPACE_CATALOG)

_URI = "artifact://artifact_stations01"

CASES: list[Any] = [
    # --- clio.map.v1 ---------------------------------------------------- #
    pytest.param(
        MapComponent,
        {
            "id": "m",
            "component": "clio.map.v1",
            "points": [{"id": "p", "label": "GNSS01", "latitude": 34.1, "longitude": -118.3}],
        },
        True,
        id="Map-inline-valid",
    ),
    pytest.param(
        MapComponent,
        {
            "id": "m",
            "component": "clio.map.v1",
            "dataUri": _URI,
            "latitudeField": "lat",
            "longitudeField": "lon",
            "labelField": "station",
        },
        True,
        id="Map-dataUri-valid",
    ),
    pytest.param(
        MapComponent,
        {
            "id": "m",
            "component": "clio.map.v1",
            "dataUri": _URI,
            "latitudeField": "lat",
            "longitudeField": "lon",
            "labelField": "station",
            "idField": "id",
            "detailField": "detail",
            "categoryField": "network",
            "dataQuery": {
                "limit": 500,
                "filter": [{"column": "network", "op": "eq", "value": "CI"}],
            },
        },
        True,
        id="Map-dataUri-with-dataQuery-and-optional-fields",
    ),
    pytest.param(
        MapComponent,
        {
            "id": "m",
            "component": "clio.map.v1",
            "points": [{"id": "p", "label": "GNSS01", "latitude": 34.1, "longitude": -118.3}],
            "dataUri": _URI,
            "latitudeField": "lat",
            "longitudeField": "lon",
            "labelField": "station",
        },
        False,
        id="Map-both-points-and-dataUri-invalid",
    ),
    pytest.param(
        MapComponent,
        {"id": "m", "component": "clio.map.v1"},
        False,
        id="Map-neither-points-nor-dataUri-invalid",
    ),
    pytest.param(
        MapComponent,
        {"id": "m", "component": "clio.map.v1", "dataUri": _URI, "latitudeField": "lat"},
        False,
        id="Map-dataUri-missing-longitudeField-and-labelField",
    ),
    pytest.param(
        MapComponent,
        {
            "id": "m",
            "component": "clio.map.v1",
            "points": [{"id": "p", "label": "GNSS01", "latitude": 34.1, "longitude": -118.3}],
            "dataQuery": {"limit": 5},
        },
        False,
        id="Map-dataQuery-without-dataUri-invalid",
    ),
    pytest.param(
        MapComponent,
        {
            "id": "m",
            "component": "clio.map.v1",
            "points": [{"id": "p", "label": "GNSS01", "latitude": 34.1, "longitude": -118.3}],
            "selection": {"path": "/selection/stations"},
        },
        False,
        id="Map-selection-bound-without-selectionField-invalid",
    ),
    pytest.param(
        MapComponent,
        {
            "id": "m",
            "component": "clio.map.v1",
            "points": [{"id": "p", "label": "GNSS01", "latitude": 34.1, "longitude": -118.3}],
            "selection": {"path": "/selection/stations"},
            "selectionField": "station",
        },
        True,
        id="Map-selection-bound-with-selectionField-valid",
    ),
    # --- clio.data-table.v1 --------------------------------------------- #
    pytest.param(
        DataTableComponent,
        {
            "id": "t",
            "component": "clio.data-table.v1",
            "columns": ["station"],
            "rows": [{"station": "GNSS01"}],
        },
        True,
        id="Table-inline-valid",
    ),
    pytest.param(
        DataTableComponent,
        {"id": "t", "component": "clio.data-table.v1", "dataUri": _URI},
        True,
        id="Table-dataUri-valid-columns-omitted",
    ),
    pytest.param(
        DataTableComponent,
        {
            "id": "t",
            "component": "clio.data-table.v1",
            "dataUri": _URI,
            "dataQuery": {"columns": ["station", "displacement_mm"], "limit": 500},
        },
        True,
        id="Table-dataUri-with-dataQuery",
    ),
    pytest.param(
        DataTableComponent,
        {
            "id": "t",
            "component": "clio.data-table.v1",
            "columns": ["station"],
            "rows": [{"station": "GNSS01"}],
            "dataUri": _URI,
        },
        False,
        id="Table-both-rows-and-dataUri-invalid",
    ),
    pytest.param(
        DataTableComponent,
        {"id": "t", "component": "clio.data-table.v1"},
        False,
        id="Table-neither-rows-nor-dataUri-invalid",
    ),
    pytest.param(
        DataTableComponent,
        {"id": "t", "component": "clio.data-table.v1", "rows": [{"station": "GNSS01"}]},
        False,
        id="Table-inline-rows-missing-required-columns",
    ),
    pytest.param(
        DataTableComponent,
        {
            "id": "t",
            "component": "clio.data-table.v1",
            "columns": ["station"],
            "rows": [{"station": "GNSS01"}],
            "dataQuery": {"limit": 5},
        },
        False,
        id="Table-dataQuery-without-dataUri-invalid",
    ),
    pytest.param(
        DataTableComponent,
        {
            "id": "t",
            "component": "clio.data-table.v1",
            "columns": ["station"],
            "rows": [{"station": "GNSS01"}],
            "selection": {"path": "/selection/stations"},
        },
        False,
        id="Table-selection-bound-without-selectionField-invalid",
    ),
    pytest.param(
        DataTableComponent,
        {
            "id": "t",
            "component": "clio.data-table.v1",
            "columns": ["station"],
            "rows": [{"station": "GNSS01"}],
            "selection": {"path": "/selection/stations"},
            "selectionField": "station",
        },
        True,
        id="Table-selection-bound-with-selectionField-valid",
    ),
    pytest.param(
        DataTableComponent,
        {
            "id": "t",
            "component": "clio.data-table.v1",
            "columns": ["station"],
            "rows": [{"station": "GNSS01"}],
            "selection": "single",
        },
        True,
        id="Table-selection-legacy-string-needs-no-selectionField",
    ),
    # --- clio.workflow.v1 ------------------------------------------------ #
    pytest.param(
        WorkflowComponent,
        {
            "id": "w",
            "component": "clio.workflow.v1",
            "nodes": [{"id": "fetch", "label": "Fetch"}],
            "edges": [],
        },
        True,
        id="Workflow-inline-valid",
    ),
    pytest.param(
        WorkflowComponent,
        {"id": "w", "component": "clio.workflow.v1", "dataUri": _URI},
        True,
        id="Workflow-dataUri-valid",
    ),
    pytest.param(
        WorkflowComponent,
        {
            "id": "w",
            "component": "clio.workflow.v1",
            "nodes": [{"id": "fetch", "label": "Fetch"}],
            "edges": [],
            "dataUri": _URI,
        },
        False,
        id="Workflow-both-inline-and-dataUri-invalid",
    ),
    pytest.param(
        WorkflowComponent,
        {"id": "w", "component": "clio.workflow.v1"},
        False,
        id="Workflow-neither-inline-nor-dataUri-invalid",
    ),
    pytest.param(
        WorkflowComponent,
        {"id": "w", "component": "clio.workflow.v1", "nodes": [{"id": "fetch", "label": "Fetch"}]},
        False,
        id="Workflow-nodes-without-edges-invalid",
    ),
    # --- clio.code.v1 ----------------------------------------------------- #
    pytest.param(
        CodeComponent,
        {"id": "c", "component": "clio.code.v1", "code": "print(1)", "language": "python"},
        True,
        id="Code-inline-valid",
    ),
    pytest.param(
        CodeComponent,
        {"id": "c", "component": "clio.code.v1", "dataUri": _URI, "language": "python"},
        True,
        id="Code-dataUri-valid",
    ),
    pytest.param(
        CodeComponent,
        {
            "id": "c",
            "component": "clio.code.v1",
            "code": "print(1)",
            "dataUri": _URI,
            "language": "python",
        },
        False,
        id="Code-both-code-and-dataUri-invalid",
    ),
    pytest.param(
        CodeComponent,
        {"id": "c", "component": "clio.code.v1", "language": "python"},
        False,
        id="Code-neither-code-nor-dataUri-invalid",
    ),
    pytest.param(
        CodeComponent,
        {"id": "c", "component": "clio.code.v1", "dataUri": _URI},
        False,
        id="Code-dataUri-missing-required-language",
    ),
    # --- clio.mermaid.v1 --------------------------------------------------- #
    pytest.param(
        MermaidComponent,
        {"id": "d", "component": "clio.mermaid.v1", "source": "graph TD; A-->B;"},
        True,
        id="Mermaid-inline-valid",
    ),
    pytest.param(
        MermaidComponent,
        {"id": "d", "component": "clio.mermaid.v1", "dataUri": _URI},
        True,
        id="Mermaid-dataUri-valid",
    ),
    pytest.param(
        MermaidComponent,
        {"id": "d", "component": "clio.mermaid.v1", "source": "graph TD;", "dataUri": _URI},
        False,
        id="Mermaid-both-source-and-dataUri-invalid",
    ),
    pytest.param(
        MermaidComponent,
        {"id": "d", "component": "clio.mermaid.v1"},
        False,
        id="Mermaid-neither-source-nor-dataUri-invalid",
    ),
    # --- clio.diff.v1 ----------------------------------------------------- #
    pytest.param(
        DiffComponent,
        {"id": "df", "component": "clio.diff.v1", "path": "src/model.py", "diff": "@@ -1 +1 @@"},
        True,
        id="Diff-inline-valid",
    ),
    pytest.param(
        DiffComponent,
        {"id": "df", "component": "clio.diff.v1", "path": "src/model.py", "dataUri": _URI},
        True,
        id="Diff-dataUri-valid",
    ),
    pytest.param(
        DiffComponent,
        {
            "id": "df",
            "component": "clio.diff.v1",
            "path": "src/model.py",
            "diff": "@@ -1 +1 @@",
            "dataUri": _URI,
        },
        False,
        id="Diff-both-diff-and-dataUri-invalid",
    ),
    pytest.param(
        DiffComponent,
        {"id": "df", "component": "clio.diff.v1", "path": "src/model.py"},
        False,
        id="Diff-neither-diff-nor-dataUri-invalid",
    ),
    pytest.param(
        DiffComponent,
        {"id": "df", "component": "clio.diff.v1", "diff": "@@ -1 +1 @@"},
        False,
        id="Diff-missing-required-path",
    ),
]


@pytest.mark.parametrize("model,payload,expect_valid", CASES)
def test_data_or_dataUri_case(
    model: type,
    payload: dict[str, Any],
    expect_valid: bool,  # noqa: FBT001
) -> None:
    """Every case agrees between the pydantic model and the rendered catalog's JSON Schema."""

    component_name = payload["component"]
    schema_valid = VALIDATORS[component_name].is_valid(payload)
    assert schema_valid == expect_valid, "catalog JSON Schema verdict mismatch"
    if expect_valid:
        model.model_validate(payload)
    else:
        with pytest.raises(ValidationError):
            model.model_validate(payload)


def test_data_query_shape_is_shared_not_duplicated_across_components() -> None:
    """clio.chart.v1, clio.map.v1, and clio.data-table.v1 $ref the SAME $defs/DataQuery."""

    components = WORKSPACE_CATALOG["components"]
    for name in ("clio.chart.v1", "clio.map.v1", "clio.data-table.v1"):
        # dataQuery lives on the third allOf branch (the plain-object properties block)
        # for every one of these hand-authored components.
        properties = components[name]["allOf"][2]["properties"]
        assert properties["dataQuery"]["$ref"] == "#/$defs/DataQuery"
    assert "DataQuery" in WORKSPACE_CATALOG["$defs"]
    # Only one DataQuery-shaped $def exists — never one per component.
    assert not any(
        name.startswith("Chart") and "Query" in name for name in WORKSPACE_CATALOG["$defs"]
    )


@pytest.mark.parametrize(
    ("query", "valid"),
    [
        ({"limit": 500}, True),
        ({"columns": ["a", "b"], "limit": 10}, True),
        (
            {
                "columns": ["station", "t", "v", "network"],
                "filter": [{"column": "network", "op": "in", "value": ["CI", "NC"]}],
                "aggregate": {"groupBy": ["station"], "metrics": [{"column": "v", "fn": "mean"}]},
                "downsample": {
                    "mode": "per_entity_lttb",
                    "entityColumn": "station",
                    "x": "t",
                    "y": "v",
                },
                "limit": 5000,
            },
            True,
        ),
        ({"limit": 0}, False),
        ({"columns": []}, False),
        ({"downsample": {"mode": "per_entity_lttb"}}, False),
    ],
)
def test_data_query_shape_via_data_table(query: dict[str, Any], valid: bool) -> None:  # noqa: FBT001
    """$defs/DataQuery (via clio.data-table.v1) validates the shared table-query shape."""

    payload = {"id": "t", "component": "clio.data-table.v1", "dataUri": _URI, "dataQuery": query}
    assert VALIDATORS["clio.data-table.v1"].is_valid(payload) == valid
    if valid:
        DataTableComponent.model_validate(payload)
    else:
        with pytest.raises(ValidationError):
            DataTableComponent.model_validate(payload)


def test_chart_still_validates_after_the_shared_rename() -> None:
    """The chart's own accept path (data/dataUri) still works after the DataQuery rename."""

    payload = {
        "id": "ch",
        "component": "clio.chart.v1",
        "preset": "scatter",
        "xField": "x",
        "yField": "y",
        "entityField": "e",
        "dataUri": _URI,
        "dataQuery": {"limit": 100},
    }
    VALIDATORS["clio.chart.v1"].validate(payload)
    ChartComponent.model_validate(payload)
