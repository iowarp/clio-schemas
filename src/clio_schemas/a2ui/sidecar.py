"""The CLIO catalog sidecar — packaging metadata that never appears on the wire.

A catalog FILE (``catalog.json``) is the official A2UI protocol shape — it is
sent to clients and is byte-for-byte what the protocol defines. The sidecar
(``catalog.clio.json``) sits *beside* it and carries CLIO's own packaging
concerns: which kernel renders each component, which client actions route to
a permission gate or a run controller instead of the plain agent event lane,
and where to find producer instructions. It is version-neutral (the
``protocolVersion`` field records which A2UI version the paired catalog
targets, but the sidecar's own shape does not change with the protocol).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Trust(BaseModel):
    """Where a catalog came from, for permission/provenance gating."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    source: Literal["builtin", "pack"]


class _Implementation(BaseModel):
    """Which renderer kernel implements one catalog component."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    kernel: str
    presets: dict[str, str] | None = None


class _EventRoute(BaseModel):
    """Where one client action name routes, beyond the default agent lane."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    destination: Literal["agent", "permission", "run"] = "agent"
    context_schema: dict[str, object] | None = None


class CatalogSidecar(BaseModel):
    """CLIO packaging metadata for one catalog. Never sent on the A2UI wire."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    catalogId: str
    protocolVersion: Literal["0.9.1"]
    trust: _Trust
    implements: dict[str, _Implementation] = Field(default_factory=dict)
    events: dict[str, _EventRoute] = Field(default_factory=dict)
    instructions: str = "instructions.md"
