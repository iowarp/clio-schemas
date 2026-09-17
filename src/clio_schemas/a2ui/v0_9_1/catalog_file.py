"""The official A2UI catalog FILE shape.

Mirrors the vendored ``catalogs/basic/catalog.json`` document shape exactly:
``$schema``, ``$id``, ``title``, ``description``, ``catalogId``,
``components`` (name -> JSON Schema component definition), ``functions``
(name -> JSON Schema validating a *call* to that function), ``$defs``.

Deviation from the campaign issue (vendored schema wins, per the working
rules): the issue's deliverable text describes ``functions`` as
``{<name>: FunctionDefinition}`` where ``FunctionDefinition`` is
``{name, description?, parameters, returnType}``. That shape does not match
the vendored catalog file — ``catalogs/basic/catalog.json``'s ``functions``
entries are full JSON Schemas validating a *function-call wire object*
(``{call, args, returnType}``), e.g. ``functions.required`` requires
``properties.call.const == "required"``. ``FunctionDefinition`` *is* real —
it is ``client_capabilities.json#/$defs/FunctionDefinition``, used to
describe functions inside an *inline* catalog sent by a client
(:class:`clio_schemas.a2ui.v0_9_1.capabilities.InlineCatalog`), a distinct
concept from a catalog file's ``functions`` map. ``CatalogFile.functions`` is
therefore typed as ``dict[str, dict[str, Any]]`` (raw JSON Schema), matching
the vendored catalog file; ``FunctionDefinition`` is defined here (per the
issue's file placement) but consumed by ``capabilities.py``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FunctionDefinition(BaseModel):
    """Interface metadata for one function in an *inline* catalog.

    Matches ``client_capabilities.json#/$defs/FunctionDefinition`` verbatim.
    Not used by :class:`CatalogFile` — see the module docstring.
    """

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    name: str
    description: str | None = None
    parameters: dict[str, Any]
    returnType: Literal["string", "number", "boolean", "array", "object", "any", "void"]


class CatalogFile(BaseModel):
    """One official-shape A2UI catalog document (a ``catalog.json`` file)."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, populate_by_name=True)

    schema_: str = Field(alias="$schema")
    id_: str = Field(alias="$id")
    title: str
    description: str
    catalogId: str
    components: dict[str, dict[str, Any]]
    functions: dict[str, dict[str, Any]] = Field(default_factory=dict)
    defs_: dict[str, dict[str, Any]] = Field(default_factory=dict, alias="$defs")
