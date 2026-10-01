"""Spec guard and preset renderer for ``clio.chart.v1`` (pure Python, no pydantic).

A chart is a Vega-Lite spec, either written by the agent (``spec``) or
rendered from one of the shipped preset templates (``preset``). Either way
the spec only *describes* marks and encodings: the rows always come from the
component's ``data``/``dataUri``, which the renderer binds to the one named
dataset ``source``. The guard below keeps a spec to that contract, so it can
never fetch a URL, smuggle inline rows, mount a Vega input widget into an
arbitrary element of the host page, or grow without bound.

The rules are exported as data (:data:`CHART_SPEC_RULES`, also shipped as
``schemas/a2ui/chart/guard_rules.json``) so a TypeScript mirror can apply the
same limits and share the same fixtures (``tests/fixtures/chart/``).

Guard rules, each reported with a stable ``code``:

- ``spec_not_object``: the spec must be a JSON object.
- ``spec_too_deep``: objects and arrays nest at most :data:`MAX_SPEC_DEPTH`
  levels (the top-level object is depth 1). Checked first; a spec this deep
  is not measured or walked further.
- ``spec_too_large``: the compact UTF-8 JSON serialisation (``separators=(",",
  ":")``, no ASCII escaping, keys in their given order — what
  ``JSON.stringify`` produces) must be at most 65536 bytes.
- ``top_level_key_not_allowed``: only :data:`ALLOWED_TOP_LEVEL_KEYS` may
  appear at the top level. This includes data-free layout keys (``columns``,
  ``spacing``, ``padding``, ``align``, ``bounds``, ``center``) and
  ``projection`` (a geoshape mark's map projection, used with inline
  named-source GeoJSON rows — still no ``url``, still ``data: {"name":
  "source"}``) — owner ruling, issue #1549 G4.
- ``too_many_views``: at most :data:`MAX_VIEWS` views in total. A view is an
  object with ``mark`` that is not itself a composition; ``layer``/``concat``/
  ``hconcat``/``vconcat`` count their children, ``facet``/``repeat`` count
  their inner ``spec`` once.
- ``data_not_named_source``: every ``data`` key, at any depth, must hold
  exactly ``{"name": "source"}``.
- ``forbidden_key``: no ``url`` or ``usermeta`` key at any depth.
- ``bind_element_not_allowed``: no ``element`` key inside any ``bind`` object
  (``params[].bind.element``), at any depth. Vega-Lite's ``bind.element`` is a
  CSS selector naming where to mount the input widget in the HOST page's DOM —
  a model-authored spec could otherwise target any element on the app page,
  not just the chart's own container.

Preset templates use a two-construct grammar, small enough to mirror:

- a string ``"{{slot}}"`` (the whole string) is replaced by the slot value; a
  slot inside a longer string is interpolated in a single pass;
- an object ``{"$if": "slot", "then": X, "else": Y}`` becomes ``X`` when the
  slot is provided and ``Y`` otherwise; with no ``else`` the enclosing object
  key (or array element) is dropped.
"""

from __future__ import annotations

import functools
import importlib.resources
import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

#: Bumped whenever a rule below changes meaning (the TS mirror checks it).
CHART_SPEC_RULES_VERSION: Final = 2
MAX_SPEC_BYTES: Final = 65_536
MAX_VIEWS: Final = 8
MAX_SPEC_DEPTH: Final = 64
MAX_INLINE_ROWS: Final = 10_000
DATA_SOURCE_NAME: Final = "source"
ALLOWED_TOP_LEVEL_KEYS: Final[tuple[str, ...]] = (
    "$schema",
    "mark",
    "encoding",
    "layer",
    "facet",
    "hconcat",
    "vconcat",
    "concat",
    "repeat",
    "spec",
    "transform",
    "params",
    "width",
    "height",
    "title",
    "resolve",
    "config",
    "autosize",
    "description",
    # Data-free layout/view keys (owner ruling, issue #1549 G4): columns wraps
    # a facet/repeat/concat grid; spacing/align/bounds/center lay out a
    # concat/facet composition; padding is the whole spec's outer padding;
    # projection configures a geoshape mark's map projection. None of these
    # carry rows -- they are chart configuration, same as the keys above.
    "columns",
    "spacing",
    "padding",
    "align",
    "bounds",
    "center",
    "projection",
    # Allowed only as {"name": "source"} (the data rule); presets declare it.
    "data",
)
FORBIDDEN_KEYS: Final[tuple[str, ...]] = ("url", "usermeta")
COMPOSITION_ARRAY_KEYS: Final[tuple[str, ...]] = ("layer", "concat", "hconcat", "vconcat")

PRESET_NAMES: Final[tuple[str, ...]] = ("trajectories", "heatmap", "spectra", "boxplot", "scatter")
#: Every slot a preset template may use; all are strings.
PRESET_SLOTS: Final[tuple[str, ...]] = (
    "xField",
    "yField",
    "entityField",
    "colorField",
    "facetField",
    "xType",
    "selectionParam",
)
X_TYPES: Final[tuple[str, ...]] = ("temporal", "quantitative", "ordinal")
DEFAULT_SELECTION_PARAM: Final = "sel"
SELECTION_PARAM_PATTERN: Final = r"^[A-Za-z_][A-Za-z0-9_]{0,63}$"

#: The rules above, as data. Rendered to ``a2ui/chart/guard_rules.json``.
CHART_SPEC_RULES: Final[dict[str, Any]] = {
    "version": CHART_SPEC_RULES_VERSION,
    "maxSpecBytes": MAX_SPEC_BYTES,
    "sizeMeasure": (
        "UTF-8 byte length of compact JSON: separators (',', ':'), no ASCII escaping, "
        "keys in their given order (JSON.stringify)."
    ),
    "allowedTopLevelKeys": list(ALLOWED_TOP_LEVEL_KEYS),
    "maxViews": MAX_VIEWS,
    "maxDepth": MAX_SPEC_DEPTH,
    "depthCounting": "The top-level object is depth 1; each nested object or array adds 1.",
    "viewCounting": (
        "An object with a layer/concat/hconcat/vconcat array counts its children; an object "
        "with facet or repeat and an object spec counts that spec; otherwise an object with "
        "mark counts 1."
    ),
    "compositionArrayKeys": list(COMPOSITION_ARRAY_KEYS),
    "requiredDataObject": {"name": DATA_SOURCE_NAME},
    "forbiddenKeys": list(FORBIDDEN_KEYS),
    "maxInlineRows": MAX_INLINE_ROWS,
    "presets": list(PRESET_NAMES),
    "presetSlots": list(PRESET_SLOTS),
    "xTypes": list(X_TYPES),
    "defaultSelectionParam": DEFAULT_SELECTION_PARAM,
    "selectionParamPattern": SELECTION_PARAM_PATTERN,
    "errorCodes": [
        "spec_not_object",
        "spec_too_deep",
        "spec_too_large",
        "top_level_key_not_allowed",
        "too_many_views",
        "data_not_named_source",
        "forbidden_key",
        "bind_element_not_allowed",
    ],
}

#: Package-relative directory of the shipped chart resources.
CHART_RESOURCE_DIR: Final = "a2ui/chart"
_SLOT = re.compile(r"\{\{([A-Za-z]+)\}\}")
_WHOLE_SLOT = re.compile(r"^\{\{([A-Za-z]+)\}\}$")


@dataclass(frozen=True, slots=True)
class ChartSpecViolation:
    """One guard failure: a stable ``code``, a JSON Pointer ``path``, a message."""

    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} at {self.path or '/'}: {self.message}"


class ChartSpecError(ValueError):
    """A chart spec (or preset rendering) broke the guard; carries every violation."""

    def __init__(self, violations: list[ChartSpecViolation]) -> None:
        self.violations = violations
        super().__init__("; ".join(str(v) for v in violations))


def _pointer(parent: str, token: str | int) -> str:
    escaped = str(token).replace("~", "~0").replace("/", "~1")
    return f"{parent}/{escaped}"


def _walk(node: Any) -> Iterator[tuple[str, Any]]:
    """Yield ``(pointer, value)`` for every node, iteratively (no recursion limit)."""

    stack: list[tuple[str, Any]] = [("", node)]
    while stack:
        path, value = stack.pop()
        yield path, value
        if isinstance(value, dict):
            children = [(_pointer(path, k), v) for k, v in value.items()]
        elif isinstance(value, list):
            children = [(_pointer(path, i), v) for i, v in enumerate(value)]
        else:
            continue
        stack.extend(reversed(children))


def spec_depth(spec: Any) -> int:
    """Deepest object/array nesting in ``spec`` (a scalar is 0, ``{}`` is 1)."""

    deepest = 0
    stack: list[tuple[Any, int]] = [(spec, 1)]
    while stack:
        node, depth = stack.pop()
        if isinstance(node, dict):
            children = node.values()
        elif isinstance(node, list):
            children = node
        else:
            continue
        deepest = max(deepest, depth)
        stack.extend((child, depth + 1) for child in children)
    return deepest


def serialized_size(spec: Any) -> int:
    """UTF-8 byte length of ``spec`` as compact JSON (the ``maxSpecBytes`` measure)."""

    return len(json.dumps(spec, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def count_views(spec: Any) -> int:
    """Count the views in a Vega-Lite spec (see the module docstring)."""

    views = 0
    stack: list[Any] = [spec]
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            continue
        composed = [node[k] for k in COMPOSITION_ARRAY_KEYS if isinstance(node.get(k), list)]
        if composed:
            for children in composed:
                stack.extend(children)
        elif ("facet" in node or "repeat" in node) and isinstance(node.get("spec"), dict):
            stack.append(node["spec"])
        elif "mark" in node:
            views += 1
    return views


def check_chart_spec(spec: Any) -> list[ChartSpecViolation]:
    """Return every guard violation in ``spec`` (empty when it is acceptable)."""

    if not isinstance(spec, dict):
        return [ChartSpecViolation("spec_not_object", "", "a chart spec must be a JSON object")]

    depth = spec_depth(spec)
    if depth > MAX_SPEC_DEPTH:
        return [
            ChartSpecViolation(
                "spec_too_deep", "", f"spec nests {depth} levels; the limit is {MAX_SPEC_DEPTH}"
            )
        ]
    violations: list[ChartSpecViolation] = []
    size = serialized_size(spec)
    if size > MAX_SPEC_BYTES:
        violations.append(
            ChartSpecViolation(
                "spec_too_large", "", f"spec is {size} bytes; the limit is {MAX_SPEC_BYTES}"
            )
        )
    for key in spec:
        if key not in ALLOWED_TOP_LEVEL_KEYS:
            violations.append(
                ChartSpecViolation(
                    "top_level_key_not_allowed",
                    _pointer("", key),
                    f"top-level key {key!r} is not allowed",
                )
            )
    views = count_views(spec)
    if views > MAX_VIEWS:
        violations.append(
            ChartSpecViolation(
                "too_many_views", "", f"spec has {views} views; the limit is {MAX_VIEWS}"
            )
        )
    for path, value in _walk(spec):
        if not isinstance(value, dict):
            continue
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                violations.append(
                    ChartSpecViolation(
                        "forbidden_key", _pointer(path, key), f"{key!r} is not allowed anywhere"
                    )
                )
            elif key == "data" and child != {"name": DATA_SOURCE_NAME}:
                violations.append(
                    ChartSpecViolation(
                        "data_not_named_source",
                        _pointer(path, key),
                        'data must be exactly {"name": "source"}; rows come from the '
                        "component's data or dataUri",
                    )
                )
            elif key == "bind" and isinstance(child, dict) and "element" in child:
                violations.append(
                    ChartSpecViolation(
                        "bind_element_not_allowed",
                        _pointer(_pointer(path, key), "element"),
                        "bind.element is not allowed; it is a CSS selector that could mount "
                        "an input widget anywhere on the host page, not just this chart",
                    )
                )
    return violations


def validate_chart_spec(spec: Any) -> dict[str, Any]:
    """Return ``spec`` unchanged if it passes the guard.

    Raises:
        ChartSpecError: With every violation, if any rule fails.
    """

    violations = check_chart_spec(spec)
    if violations:
        raise ChartSpecError(violations)
    return spec


# --------------------------------------------------------------------------- #
# Presets
# --------------------------------------------------------------------------- #
def _package_schema_root() -> Path:
    return Path(str(importlib.resources.files("clio_schemas") / "schemas"))


def preset_path(name: str) -> Path:
    """Filesystem path to one shipped preset template."""

    return _package_schema_root() / CHART_RESOURCE_DIR / "presets" / f"{name}.json"


@functools.cache
def _load_preset_text(name: str) -> str:
    if name not in PRESET_NAMES:
        raise ValueError(f"unknown chart preset {name!r}; expected one of {list(PRESET_NAMES)}")
    return preset_path(name).read_text(encoding="utf-8")


def load_preset(name: str) -> dict[str, Any]:
    """Return a fresh copy of one preset template document.

    Raises:
        ValueError: If ``name`` is not one of :data:`PRESET_NAMES`.
    """

    return json.loads(_load_preset_text(name))


_OMIT: Final = object()


def _fill(node: Any, fields: Mapping[str, str], preset: str) -> Any:
    if isinstance(node, dict):
        if "$if" in node:
            extra = set(node) - {"$if", "then", "else"}
            if extra or "then" not in node or node["$if"] not in PRESET_SLOTS:
                raise ValueError(f"preset {preset!r}: malformed $if node {node!r}")
            if node["$if"] in fields:
                return _fill(node["then"], fields, preset)
            return _fill(node["else"], fields, preset) if "else" in node else _OMIT
        out: dict[str, Any] = {}
        for key, value in node.items():
            filled = _fill(value, fields, preset)
            if filled is not _OMIT:
                out[key] = filled
        return out
    if isinstance(node, list):
        return [f for f in (_fill(v, fields, preset) for v in node) if f is not _OMIT]
    if isinstance(node, str):

        def slot_value(slot: str) -> str:
            if slot not in fields:
                raise ValueError(f"preset {preset!r}: slot {slot!r} used but not provided")
            return fields[slot]

        whole = _WHOLE_SLOT.match(node)
        if whole:
            return slot_value(whole.group(1))
        return _SLOT.sub(lambda m: slot_value(m.group(1)), node)
    return node


def render_preset(name: str, fields: Mapping[str, str | None]) -> dict[str, Any]:
    """Render preset ``name`` with ``fields`` into a guard-checked Vega-Lite spec.

    Args:
        name: One of :data:`PRESET_NAMES`.
        fields: Slot values (``xField``, ``yField``, ``entityField``,
            ``colorField``, ``facetField``, ``xType``, ``selectionParam``);
            a ``None`` value counts as not provided.

    Raises:
        ValueError: For an unknown preset, a missing required slot, a slot
            the preset does not use, or a bad ``xType``/``selectionParam``.
        ChartSpecError: If the rendered spec fails the guard (a template bug).
    """

    document = load_preset(name)
    provided = {k: v for k, v in fields.items() if v is not None}
    required = document["requiredFields"]
    allowed = set(required) | set(document["optionalFields"])
    unknown = sorted(set(provided) - allowed)
    if unknown:
        raise ValueError(f"preset {name!r} does not use field(s) {unknown}")
    missing = [slot for slot in required if slot not in provided]
    if missing:
        raise ValueError(f"preset {name!r} requires field(s) {missing}")
    for slot, value in provided.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"preset {name!r}: {slot} must be a non-empty string")
    if "xType" in provided and provided["xType"] not in X_TYPES:
        raise ValueError(f"xType must be one of {list(X_TYPES)}, got {provided['xType']!r}")
    if "selectionParam" in provided and not re.match(
        SELECTION_PARAM_PATTERN, provided["selectionParam"]
    ):
        raise ValueError(f"selectionParam {provided['selectionParam']!r} is not a valid name")
    filled_fields = {**document.get("defaults", {}), **provided}
    spec = _fill(document["template"], filled_fields, name)
    return validate_chart_spec(spec)


# --------------------------------------------------------------------------- #
# Committed resources (a2ui/chart/**), rendered by clio_schemas.export
# --------------------------------------------------------------------------- #
def _dumps(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_chart_resources() -> dict[str, str]:
    """Every committed ``a2ui/chart/**`` file, keyed by schema-root-relative path.

    ``guard_rules.json`` is rendered from :data:`CHART_SPEC_RULES`. The preset
    templates are hand-authored package data; they are re-emitted in the
    canonical JSON formatting so ``HASHES.json`` covers them and
    ``--verify`` catches an edit that skipped ``--regenerate``.
    """

    files = {f"{CHART_RESOURCE_DIR}/guard_rules.json": _dumps(CHART_SPEC_RULES)}
    for name in PRESET_NAMES:
        document = json.loads(preset_path(name).read_text(encoding="utf-8"))
        if document.get("preset") != name:
            raise ValueError(f"preset file {name}.json declares preset {document.get('preset')!r}")
        files[f"{CHART_RESOURCE_DIR}/presets/{name}.json"] = _dumps(document)
    return files
