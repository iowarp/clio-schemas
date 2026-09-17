"""JSON Schema validation for the A2UI 0.9.1 wire (``jsonschema`` + ``referencing``).

Builds a :class:`referencing.Registry` preloaded with every vendored schema's
``$id`` (see ``src/clio_schemas/schemas/a2ui/v0_9_1/``), so no ``$ref`` is
ever fetched over the network or from an unexpected path — the registry has
no ``retrieve`` callable, so an unresolvable ``$ref`` raises
(``referencing.exceptions.Unresolvable``) instead of silently validating
against a partial schema. This module never decides validity itself; it only
compiles schemas so callers (this repo's corpus runner, clio-agent S2) can.
"""

from __future__ import annotations

import functools
import importlib.resources
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

#: Enforces "format" keywords (e.g. ``"format": "uri"`` on
#: ``functions.openUrl.args.url`` in the vendored Basic catalog) as real
#: assertions — jsonschema treats "format" as annotation-only by default, so
#: a validator built without this would silently accept a malformed URL
#: instead of rejecting it. Requires the ``jsonschema[format]`` extra.
_FORMAT_CHECKER = FormatChecker()

_SPEC_BASE = "https://a2ui.org/specification/v0_9"

#: Where ``server_to_client.json``'s relative ``"catalog.json"`` $ref
#: resolves to (same directory as the core spec files). A catalog passed to
#: :func:`message_validator` / :func:`catalog_validators` is registered here
#: in addition to its own ``$id`` — mirroring the upstream test harness's
#: catalog alias (``tests/a2ui_corpus/v0_9_1/run_tests.py::setup_catalog_alias``).
CATALOG_ALIAS_URI = f"{_SPEC_BASE}/catalog.json"

# filename stem -> canonical $id. `client_to_server` carries no `$id` of its
# own in the vendored file; every other vendored schema's relative
# "client_to_server.json" reference resolves to this URI (its own directory),
# so that is where it must be registered.
_SCHEMA_URIS: dict[str, str] = {
    "client_capabilities": f"{_SPEC_BASE}/client_capabilities.json",
    "client_data_model": f"{_SPEC_BASE}/client_data_model.json",
    "client_to_server": f"{_SPEC_BASE}/client_to_server.json",
    "client_to_server_list": f"{_SPEC_BASE}/client_to_server_list.json",
    "client_to_server_list_wrapper": f"{_SPEC_BASE}/client_to_server_list_wrapper.json",
    "common_types": f"{_SPEC_BASE}/common_types.json",
    "server_capabilities": f"{_SPEC_BASE}/server_capabilities.json",
    "server_to_client": f"{_SPEC_BASE}/server_to_client.json",
    "server_to_client_list": f"{_SPEC_BASE}/server_to_client_list.json",
    "server_to_client_list_wrapper": f"{_SPEC_BASE}/server_to_client_list_wrapper.json",
}

#: Schemas that transitively $ref "catalog.json" (they validate messages that
#: carry catalog-defined component/theme payloads) and therefore require a
#: catalog to be supplied — never silently validated without one.
_REQUIRES_CATALOG = frozenset(
    {"server_to_client", "server_to_client_list", "server_to_client_list_wrapper"}
)


def _vendored_schema_dir() -> Path:
    """Filesystem path to the vendored 0.9.1 core schema resources."""

    return Path(str(importlib.resources.files("clio_schemas") / "schemas" / "a2ui" / "v0_9_1"))


@functools.lru_cache(maxsize=1)
def _vendored_schemas() -> dict[str, dict[str, Any]]:
    """Load every vendored 0.9.1 core schema file once, keyed by filename stem."""

    schema_dir = _vendored_schema_dir()
    schemas: dict[str, dict[str, Any]] = {}
    for stem in _SCHEMA_URIS:
        path = schema_dir / f"{stem}.json"
        if not path.is_file():
            raise FileNotFoundError(
                f"vendored A2UI schema missing: {path} — run `python scripts/vendor_a2ui_spec.py`"
            )
        schemas[stem] = json.loads(path.read_text(encoding="utf-8"))
    return schemas


def _base_registry() -> Registry:
    """A registry preloaded with every vendored core schema's ``$id``."""

    registry = Registry()
    for stem, schema in _vendored_schemas().items():
        uri = schema.get("$id", _SCHEMA_URIS[stem])
        resource = Resource.from_contents(schema, default_specification=DRAFT202012)
        registry = registry.with_resource(uri, resource)
    return registry


def _catalog_id(catalog: Mapping[str, Any]) -> str:
    """Return a catalog document's own identifying URI.

    Raises:
        ValueError: If the catalog has neither ``$id`` nor ``catalogId``.
    """

    catalog_id = catalog.get("$id") or catalog.get("catalogId")
    if not catalog_id:
        raise ValueError("catalog is missing both '$id' and 'catalogId'")
    return str(catalog_id)


def _registry_for(catalog: Mapping[str, Any] | None) -> Registry:
    """The base registry, plus ``catalog`` registered under its id and the alias URI."""

    registry = _base_registry()
    if catalog is None:
        return registry
    resource = Resource.from_contents(dict(catalog), default_specification=DRAFT202012)
    registry = registry.with_resource(_catalog_id(catalog), resource)
    registry = registry.with_resource(CATALOG_ALIAS_URI, resource)
    return registry


def catalog_validators(catalog: Mapping[str, Any]) -> dict[str, Draft202012Validator]:
    """Compile one validator per component declared in ``catalog``.

    Each validator is built as ``{"$ref": "<catalogId>#/components/<name>"}``
    against a registry containing the vendored ``common_types.json`` and
    ``catalog`` itself — so every internal ``$ref`` (to
    ``common_types.json#/$defs/...`` and to the catalog's own local
    ``$defs``) resolves without any base-URI ambiguity.

    Args:
        catalog: A catalog FILE document (``components`` maps a component
            name to its JSON Schema definition; see
            ``catalogs/basic/catalog.json`` for the shape).

    Returns:
        ``{component_name: validator}`` for every key in ``catalog["components"]``.

    Raises:
        KeyError: If ``catalog`` has no ``"components"`` key.
        ValueError: If ``catalog`` has neither ``$id`` nor ``catalogId``.
    """

    registry = _registry_for(catalog)
    catalog_id = _catalog_id(catalog)
    return {
        name: Draft202012Validator(
            {"$ref": f"{catalog_id}#/components/{name}"},
            registry=registry,
            format_checker=_FORMAT_CHECKER,
        )
        for name in catalog["components"]
    }


def message_validator(
    name: str, *, catalog: Mapping[str, Any] | None = None
) -> Draft202012Validator:
    """Build a validator for one of the ten official A2UI 0.9.1 schema files.

    Args:
        name: A vendored schema filename, with or without the ``.json``
            suffix (e.g. ``"server_to_client.json"`` or ``"server_to_client"``).
        catalog: The catalog to resolve ``catalog.json`` $refs against.
            Required for the ``server_to_client*`` family (they reference a
            catalog's component/theme definitions); ignored otherwise.

    Returns:
        A compiled validator for the requested schema.

    Raises:
        KeyError: If ``name`` is not one of the ten vendored schema files.
        ValueError: If ``catalog`` is required but was not supplied — a
            validator that cannot resolve a ``$ref`` must raise, never
            silently validate against an incomplete schema.
    """

    stem = name[:-5] if name.endswith(".json") else name
    if stem not in _SCHEMA_URIS:
        raise KeyError(f"unknown A2UI schema {name!r}; expected one of {sorted(_SCHEMA_URIS)}")
    if stem in _REQUIRES_CATALOG and catalog is None:
        raise ValueError(
            f"{stem}.json references a catalog's component/theme definitions "
            "(catalog.json#/$defs/...) — pass catalog= to resolve them"
        )
    registry = _registry_for(catalog)
    uri = _vendored_schemas()[stem].get("$id", _SCHEMA_URIS[stem])
    return Draft202012Validator({"$ref": uri}, registry=registry, format_checker=_FORMAT_CHECKER)
