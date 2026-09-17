"""Official A2UI 0.9.1 capability-negotiation models.

Mirrors ``client_capabilities.json`` and ``server_capabilities.json``
verbatim. Both are namespaced under a literal ``"v0.9"`` key (the protocol's
*capability generation*, distinct from the per-message ``version`` field),
modelled with a field alias since ``v0.9`` is not a valid Python identifier.

Neither vendored schema declares ``additionalProperties: false`` on the
``"v0.9"`` object (only ``client_capabilities.json`` forbids extras on the
nested ``Catalog``/``FunctionDefinition`` $defs, not on the capabilities
object itself) — so, unlike the strict envelope/catalog-file models
elsewhere in this package, the capability objects use ``extra="allow"`` to
match the wire contract instead of rejecting a forward-compatible field a
newer client/server might send.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from clio_schemas.a2ui.v0_9_1.catalog_file import FunctionDefinition

#: A JSON Schema node, per draft 2020-12: either a schema object, or the
#: boolean schemas ``true`` (anything is valid) / ``false`` (nothing is).
_JSONSchemaNode = dict[str, Any] | bool


class InlineCatalog(BaseModel):
    """One inline catalog a client bundles into its declared capabilities.

    Matches ``client_capabilities.json#/$defs/Catalog``. Only sent when the
    server declares ``acceptsInlineCatalogs: true``.
    """

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    catalogId: str
    components: dict[str, _JSONSchemaNode] = Field(default_factory=dict)
    functions: list[FunctionDefinition] = Field(default_factory=list)
    theme: dict[str, _JSONSchemaNode] = Field(default_factory=dict)


class _ClientCapabilitiesV09(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True, frozen=True)

    supportedCatalogIds: list[str]
    inlineCatalogs: list[InlineCatalog] | None = None


class _AgentCapabilitiesV09(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True, frozen=True)

    supportedCatalogIds: list[str] = Field(default_factory=list)
    acceptsInlineCatalogs: bool = False


class A2UIClientCapabilities(BaseModel):
    """The ``a2uiClientCapabilities`` A2A metadata object a client sends."""

    model_config = ConfigDict(extra="allow", strict=True, frozen=True, populate_by_name=True)

    v0_9: _ClientCapabilitiesV09 = Field(alias="v0.9")


class A2UIAgentCapabilities(BaseModel):
    """The server/agent capabilities object, advertised e.g. in an Agent Card."""

    model_config = ConfigDict(extra="allow", strict=True, frozen=True, populate_by_name=True)

    v0_9: _AgentCapabilitiesV09 = Field(alias="v0.9")
