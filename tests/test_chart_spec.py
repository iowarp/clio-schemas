"""The ``clio.chart.v1`` spec guard, preset renderer, and shared fixtures.

The fixtures under ``tests/fixtures/chart/`` are shared with gact-tui's
TypeScript mirror of :mod:`clio_schemas.a2ui.chart_spec`, so both sides run
the same cases:

- ``guard_cases.json``: specs with the expected guard verdict and error codes;
- ``preset_cases.json``: preset fields with the expected rendered spec, plus
  field sets that must be refused;
- ``component_cases.json``: whole ``clio.chart.v1`` payloads (see
  ``tests/test_a2ui_corpus.py``);
- ``selection_state_cases.json``: values a bound ``/selection/<key>`` holds.

``preset_cases.json``'s ``expected`` specs are golden output: after an
intentional template change, refresh them with ``render_preset`` and review
the diff.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

import pytest

from clio_schemas.a2ui.chart_spec import (
    ALLOWED_TOP_LEVEL_KEYS,
    CHART_SPEC_RULES,
    MAX_SPEC_BYTES,
    MAX_SPEC_DEPTH,
    MAX_VIEWS,
    PRESET_NAMES,
    ChartSpecError,
    check_chart_spec,
    count_views,
    load_preset,
    render_chart_resources,
    render_preset,
    serialized_size,
    spec_depth,
    validate_chart_spec,
)
from clio_schemas.export import package_schema_dir

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "chart"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


GUARD_CASES = _load("guard_cases.json")["cases"]
PRESET_FIXTURE = _load("preset_cases.json")


@pytest.mark.parametrize("case", GUARD_CASES, ids=lambda c: c["name"])
def test_guard_fixture(case: dict[str, Any]) -> None:
    """Each shared guard case gets exactly its expected verdict and error codes."""

    codes = sorted({violation.code for violation in check_chart_spec(case["spec"])})
    assert codes == case.get("codes", [])
    assert (not codes) == case["valid"]
    if case["valid"]:
        assert validate_chart_spec(case["spec"]) is case["spec"]
    else:
        with pytest.raises(ChartSpecError) as excinfo:
            validate_chart_spec(case["spec"])
        assert sorted({v.code for v in excinfo.value.violations}) == codes


def test_guard_fixtures_cover_every_error_code() -> None:
    covered = {code for case in GUARD_CASES for code in case.get("codes", [])}
    assert covered == set(CHART_SPEC_RULES["errorCodes"])


def test_size_limit_is_inclusive_and_measured_in_utf8_bytes() -> None:
    base = {"mark": "point", "description": ""}
    padding = MAX_SPEC_BYTES - serialized_size(base)
    at_limit = {"mark": "point", "description": "x" * padding}
    assert serialized_size(at_limit) == MAX_SPEC_BYTES
    assert check_chart_spec(at_limit) == []
    over = {"mark": "point", "description": "x" * (padding + 1)}
    assert [v.code for v in check_chart_spec(over)] == ["spec_too_large"]
    # A multi-byte character counts as its UTF-8 length, not as one character.
    multibyte = {"mark": "point", "description": "é" * (padding // 2 + 1)}
    assert [v.code for v in check_chart_spec(multibyte)] == ["spec_too_large"]


def test_violation_paths_are_json_pointers() -> None:
    spec = {"layer": [{"mark": "point", "data": {"url": "x"}}], "a/b": 1}
    paths = {(v.code, v.path) for v in check_chart_spec(spec)}
    assert ("data_not_named_source", "/layer/0/data") in paths
    assert ("forbidden_key", "/layer/0/data/url") in paths
    assert ("top_level_key_not_allowed", "/a~1b") in paths


def _nested(levels: int) -> dict[str, Any]:
    """A spec whose objects nest exactly ``levels`` deep."""

    spec: dict[str, Any] = {"mark": "point"}
    node = spec
    for _ in range(levels - 1):
        node["config"] = {}
        node = node["config"]
    return spec


def test_depth_limit_is_inclusive() -> None:
    assert spec_depth(_nested(MAX_SPEC_DEPTH)) == MAX_SPEC_DEPTH
    assert check_chart_spec(_nested(MAX_SPEC_DEPTH)) == []
    assert [v.code for v in check_chart_spec(_nested(MAX_SPEC_DEPTH + 1))] == ["spec_too_deep"]
    assert spec_depth({"a": [[]]}) == 3
    assert spec_depth("x") == 0


def test_very_deep_spec_is_refused_without_hitting_the_recursion_limit() -> None:
    assert [v.code for v in check_chart_spec(_nested(50_000))] == ["spec_too_deep"]


def test_view_counting() -> None:
    unit = {"mark": "point"}
    assert count_views(unit) == 1
    assert count_views({"layer": [unit, unit]}) == 2
    assert count_views({"facet": {"row": {"field": "f"}}, "spec": {"layer": [unit, unit]}}) == 2
    assert count_views({"repeat": ["a", "b"], "spec": unit}) == 1
    assert count_views({"vconcat": [{"hconcat": [unit, unit]}, {"concat": [unit]}]}) == 3
    assert count_views({"encoding": {}}) == 0
    assert count_views({"hconcat": [unit] * (MAX_VIEWS + 1)}) == MAX_VIEWS + 1


def test_rules_as_data_match_the_module_constants_and_the_shipped_file() -> None:
    assert CHART_SPEC_RULES["allowedTopLevelKeys"] == list(ALLOWED_TOP_LEVEL_KEYS)
    assert CHART_SPEC_RULES["maxSpecBytes"] == 65_536
    assert CHART_SPEC_RULES["maxViews"] == 8
    assert CHART_SPEC_RULES["forbiddenKeys"] == ["url", "usermeta"]
    assert CHART_SPEC_RULES["requiredDataObject"] == {"name": "source"}
    shipped = package_schema_dir() / "a2ui" / "chart" / "guard_rules.json"
    assert json.loads(shipped.read_text(encoding="utf-8")) == CHART_SPEC_RULES


def test_every_preset_is_shipped_and_committed_canonically() -> None:
    resources = render_chart_resources()
    for name in PRESET_NAMES:
        path = f"a2ui/chart/presets/{name}.json"
        committed = (package_schema_dir() / path).read_bytes().decode("utf-8")
        assert resources[path] == committed


# --------------------------------------------------------------------------- #
# Presets
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("case", PRESET_FIXTURE["cases"], ids=lambda c: c["name"])
def test_preset_fixture_renders_expected_spec(case: dict[str, Any]) -> None:
    assert render_preset(case["preset"], case["fields"]) == case["expected"]


@pytest.mark.parametrize("case", PRESET_FIXTURE["errorCases"], ids=lambda c: c["name"])
def test_preset_fixture_error_case_is_refused(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        render_preset(case["preset"], case["fields"])


def test_preset_fixtures_cover_every_preset() -> None:
    assert {case["preset"] for case in PRESET_FIXTURE["cases"]} == set(PRESET_NAMES)


def _field_combinations(name: str) -> list[dict[str, str]]:
    """Every subset of a preset's optional fields, filled with plausible values."""

    document = load_preset(name)
    values = {
        "xField": "x",
        "yField": "y",
        "entityField": "entity",
        "colorField": "group",
        "facetField": "panel",
        "xType": "temporal",
        "selectionParam": "sel",
    }
    required = {field: values[field] for field in document["requiredFields"]}
    optional = document["optionalFields"]
    combos = []
    for size in range(len(optional) + 1):
        for subset in itertools.combinations(optional, size):
            combos.append({**required, **{field: values[field] for field in subset}})
    return combos


def _params(spec: dict[str, Any]) -> list[dict[str, Any]]:
    params = list(spec.get("params", []))
    for layer in spec.get("layer", []):
        params.extend(layer.get("params", []))
    return params


def _encodings(spec: dict[str, Any]) -> list[dict[str, Any]]:
    if "encoding" in spec:
        return [spec["encoding"]]
    return [layer["encoding"] for layer in spec.get("layer", []) if "encoding" in layer]


@pytest.mark.parametrize(
    ("name", "fields"),
    [(name, fields) for name in PRESET_NAMES for fields in _field_combinations(name)],
)
def test_every_preset_field_combination_passes_the_guard(name: str, fields: dict[str, str]) -> None:
    """Every preset x optional-field subset renders to a spec the guard accepts."""

    spec = render_preset(name, fields)
    assert check_chart_spec(spec) == []
    assert spec["data"] == {"name": "source"}
    assert "{{" not in json.dumps(spec)
    assert "$if" not in json.dumps(spec)
    # A point selection named `sel` on entityField: click selects, dblclick clears.
    (param,) = _params(spec)
    assert param == {
        "name": "sel",
        "select": {"type": "point", "fields": ["entity"], "on": "click", "clear": "dblclick"},
    }
    # The selected entity is highlighted and the rest dimmed.
    conditional = [
        channel
        for encoding in _encodings(spec)
        for channel in ("opacity", "strokeWidth", "size")
        if encoding.get(channel, {}).get("condition", {}).get("param") == "sel"
    ]
    assert "opacity" in conditional
    assert len(conditional) >= 2
    if "facetField" in fields:
        assert _encodings(spec)[0]["facet"]["field"] == "panel"
    if "colorField" in fields:
        assert any(e.get("color", {}).get("field") == "group" for e in _encodings(spec))


def test_selection_param_renames_the_param_and_every_condition() -> None:
    spec = render_preset(
        "trajectories",
        {"xField": "t", "yField": "v", "entityField": "run", "selectionParam": "picked"},
    )
    text = json.dumps(spec)
    assert '"sel"' not in text
    assert spec["params"][0]["name"] == "picked"
    assert spec["encoding"]["opacity"]["condition"]["param"] == "picked"


def test_none_fields_count_as_not_provided() -> None:
    with_none = render_preset(
        "scatter", {"xField": "x", "yField": "y", "entityField": "e", "colorField": None}
    )
    assert with_none == render_preset("scatter", {"xField": "x", "yField": "y", "entityField": "e"})
    assert "color" not in with_none["encoding"]


def test_trajectories_default_x_type_is_quantitative() -> None:
    spec = render_preset("trajectories", {"xField": "t", "yField": "v", "entityField": "e"})
    assert spec["encoding"]["x"] == {"field": "t", "type": "quantitative"}
    assert spec["encoding"]["color"] == {"field": "e", "type": "nominal", "legend": None}
    assert "facet" not in spec["encoding"]


def test_load_preset_refuses_unknown_names() -> None:
    with pytest.raises(ValueError, match="unknown chart preset"):
        load_preset("../catalogs/clio-workspace/v1/catalog")
