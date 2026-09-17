"""Assemble and render the CLIO builtin A2UI catalog tree (``a2ui/catalogs/**``).

Two catalogs ship: ``clio-workspace`` (the 30 CLIO scientific-agent
components — 27 canonicalised by :mod:`clio_schemas.a2ui.catalog_render`, 3
hand-authored by :mod:`clio_schemas.a2ui.catalog_bounded`) and ``basic`` (the
vendored upstream catalog; only its CLIO sidecar/instructions are authored
here — the catalog file itself is vendored verbatim, untouched).
"""

from __future__ import annotations

import importlib.resources
import json
from pathlib import Path
from typing import Any

from clio_schemas.a2ui.catalog_bounded import hand_authored_components
from clio_schemas.a2ui.catalog_render import render_factory_components
from clio_schemas.a2ui.instructions import BASIC_INSTRUCTIONS_MD, WORKSPACE_INSTRUCTIONS_MD
from clio_schemas.a2ui.sidecar import CatalogSidecar
from clio_schemas.a2ui.v0_9_1.catalog_file import CatalogFile

WORKSPACE_CATALOG_ID = "https://iowarp.ai/a2ui/catalogs/clio-workspace/v1"

A2UI_CATALOGS_ROOT = "a2ui/catalogs"
WORKSPACE_RELDIR = f"{A2UI_CATALOGS_ROOT}/clio-workspace/v1"
BASIC_RELDIR = f"{A2UI_CATALOGS_ROOT}/basic"


def _render_workspace_functions() -> dict[str, Any]:
    """The three former client-local actions, as catalog function-call schemas."""

    def call_schema(
        name: str, args_properties: dict[str, Any], required: list[str], description: str
    ) -> dict[str, Any]:
        return {
            "type": "object",
            "description": description,
            "properties": {
                "call": {"const": name},
                "args": {
                    "type": "object",
                    "properties": args_properties,
                    "required": required,
                    "unevaluatedProperties": False,
                },
                "returnType": {"const": "void"},
            },
            "required": ["call", "args"],
            "unevaluatedProperties": False,
        }

    return {
        "openArtifact": call_schema(
            "openArtifact",
            {
                "uri": {
                    "type": "string",
                    "description": "The artifact:// or resource:// URI to open.",
                }
            },
            ["uri"],
            "Opens a registered artifact in the workspace artifact viewer.",
        ),
        "selectData": call_schema(
            "selectData",
            {
                "surfaceId": {
                    "type": "string",
                    "description": (
                        "The surface the selection applies to; defaults to the current surface."
                    ),
                },
                "rowIds": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The selected row identifiers.",
                },
            },
            ["rowIds"],
            "Reports a data-table or list row selection back to the workspace.",
        ),
        "focusWorkflow": call_schema(
            "focusWorkflow",
            {"stepId": {"type": "string", "description": "The workflow node id to focus."}},
            ["stepId"],
            "Focuses one node of a clio.workflow.v1 component.",
        ),
    }


def render_workspace_catalog() -> dict[str, Any]:
    """Render the ``clio-workspace`` catalog file: all 30 CLIO components.

    ``$defs.theme`` and the 14 Basic ``functions`` (``required``, ``regex``,
    ``formatString``, ...) are copied VERBATIM from the vendored Basic
    catalog at render time, never hand-typed: ``server_to_client.json``'s
    ``createSurface.theme`` and ``common_types.json``'s ``FunctionCall``
    both ``$ref`` ``catalog.json#/$defs/theme`` /
    ``catalog.json#/$defs/anyFunction`` for WHICHEVER catalog is aliased —
    without these, a themed ``createSurface`` can't resolve ``$defs/theme``
    against this catalog, and every ``Checkable``/dynamic-value function call
    (``checks[].condition``, ``formatString`` inside a ``DynamicString``,
    ...) is unsatisfiable even though the pydantic generator still accepts
    it. The 3 CLIO functions (``openArtifact``/``selectData``/
    ``focusWorkflow``) are added alongside them, in the same call-schema
    style.
    """

    components, defs = render_factory_components()
    hand_components, hand_defs = hand_authored_components()
    components.update(hand_components)
    defs.update(hand_defs)

    basic_catalog = _load_basic_catalog()
    defs["theme"] = basic_catalog["$defs"]["theme"]

    defs["anyComponent"] = {
        "oneOf": [{"$ref": f"#/components/{name}"} for name in sorted(components)],
        "discriminator": {"propertyName": "component"},
    }
    functions = {**basic_catalog["functions"], **_render_workspace_functions()}
    defs["anyFunction"] = {"oneOf": [{"$ref": f"#/functions/{name}"} for name in sorted(functions)]}

    catalog: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": WORKSPACE_CATALOG_ID,
        "title": "CLIO Workspace Catalog",
        "description": (
            "The 30 CLIO scientific-agent A2UI 0.9.1 components, in official catalog-file style."
        ),
        "catalogId": WORKSPACE_CATALOG_ID,
        "components": components,
        "functions": functions,
        "$defs": defs,
    }
    CatalogFile.model_validate(catalog)  # fail fast if the rendered shape drifts
    return catalog


def _load_basic_catalog() -> dict[str, Any]:
    path = Path(
        str(
            importlib.resources.files("clio_schemas")
            / "schemas"
            / "a2ui"
            / "v0_9_1"
            / "catalogs"
            / "basic"
            / "catalog.json"
        )
    )
    return json.loads(path.read_text(encoding="utf-8"))


def render_workspace_sidecar() -> dict[str, Any]:
    """Render ``clio-workspace``'s CLIO packaging sidecar."""

    catalog = render_workspace_catalog()
    sidecar: dict[str, Any] = {
        "catalogId": WORKSPACE_CATALOG_ID,
        "protocolVersion": "0.9.1",
        "trust": {"source": "builtin"},
        "implements": {name: {"kernel": name} for name in catalog["components"]},
        "events": {
            "approval.respond": {"destination": "permission"},
            "run.cancel": {"destination": "run", "operation": "cancel"},
            "run.retry": {"destination": "run", "operation": "retry"},
        },
        "instructions": "instructions.md",
    }
    CatalogSidecar.model_validate(sidecar)
    return sidecar


def render_basic_sidecar() -> dict[str, Any]:
    """Render the vendored Basic catalog's CLIO packaging sidecar."""

    catalog = _load_basic_catalog()
    sidecar: dict[str, Any] = {
        "catalogId": catalog["catalogId"],
        "protocolVersion": "0.9.1",
        "trust": {"source": "builtin"},
        "implements": {name: {"kernel": name} for name in catalog["components"]},
        "events": {},
        "instructions": "instructions.md",
    }
    CatalogSidecar.model_validate(sidecar)
    return sidecar


def _dumps(payload: object) -> str:
    """Deterministic JSON serialisation matching ``export.py``'s ``_dumps``."""

    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_a2ui_catalog_bundle() -> dict[str, str]:
    """Render every ``a2ui/catalogs/**`` file this repo owns, keyed by relative path."""

    return {
        f"{WORKSPACE_RELDIR}/catalog.json": _dumps(render_workspace_catalog()),
        f"{WORKSPACE_RELDIR}/catalog.clio.json": _dumps(render_workspace_sidecar()),
        f"{WORKSPACE_RELDIR}/instructions.md": WORKSPACE_INSTRUCTIONS_MD,
        f"{BASIC_RELDIR}/catalog.clio.json": _dumps(render_basic_sidecar()),
        f"{BASIC_RELDIR}/instructions.md": BASIC_INSTRUCTIONS_MD,
    }
