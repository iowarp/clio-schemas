"""Canonical shared record models.

During the P0.6 bootstrap this module contains two placeholder models,
`SchemaProbe` and `ProbeBatch` (which references `SchemaProbe` and reuses the
shared `ProbeKind` enum), whose only job is to prove the export -> generate loop
including multi-root / shared-definition handling. The real record shapes
(TaskRecord / ArtifactRef / ArtifactUse / part-record) land in slice P2.1
(issue #1120). To add a model, define it here (inheriting `ClioSchemaBase`) and
append it to `EXPORTED_MODELS` — see the README ("How to add a model").
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ClioSchemaBase(BaseModel):
    """Base for every canonical wire record.

    Enforces strict wire semantics shared by all shapes:

    - ``extra="forbid"`` — unknown keys are rejected, never silently dropped.
    - ``strict=True`` — no lax coercion (a string ``"7"`` is *not* accepted for
      an ``int`` field), so Python validation matches the JSON Schema's declared
      types exactly. This is what keeps the pydantic model and the generated
      TypeScript in agreement about the wire.
    - ``frozen=True`` — records are immutable value objects; a consumer cannot
      mutate a received record in place.
    """

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ProbeKind(StrEnum):
    """Discriminator enum shared by more than one model.

    Exists so the bootstrap exercises enum handling through the whole
    pydantic -> JSON Schema -> TypeScript pipeline (enums are a common source of
    generator drift) and, because it is referenced by both `SchemaProbe` and
    `ProbeBatch`, proves that a shared definition is emitted exactly once.
    """

    PING = "ping"
    ECHO = "echo"
    NOOP = "noop"


class SchemaProbe(ClioSchemaBase):
    """Placeholder record proving the schema export pipeline works end to end.

    Intentionally trivial; removed once the real shared records land in P2.1. It
    carries one required string, one typed enum, and one integer with a default
    so required/optional handling, enum generation, and defaults are all
    exercised by the golden round-trip test.
    """

    probe_id: str = Field(description="Opaque identifier for this probe record.")
    kind: ProbeKind = Field(
        default=ProbeKind.PING,
        description="Which probe behaviour this record represents.",
    )
    sequence: int = Field(
        default=0,
        ge=0,
        description="Monotonic sequence number within a probe stream.",
    )


class ProbeBatch(ClioSchemaBase):
    """Placeholder aggregate proving multi-root / shared-definition handling.

    References `SchemaProbe` (a nested model) and reuses `ProbeKind` (a shared
    enum). The exporter emits both `ProbeKind` and `SchemaProbe` exactly once in
    the aggregate schema, and the TypeScript generator must not duplicate their
    declarations — the anti-duplication proof for P2.1's richer record graph.
    """

    batch_id: str = Field(description="Opaque identifier for this batch.")
    default_kind: ProbeKind = Field(
        default=ProbeKind.PING,
        description="Fallback probe behaviour for probes that omit their kind.",
    )
    probes: tuple[SchemaProbe, ...] = Field(
        default=(),
        description="The probe records in this batch (order-significant).",
    )


# The registry the exporter iterates. Keep it alphabetical by class name.
EXPORTED_MODELS: tuple[type[BaseModel], ...] = (ProbeBatch, SchemaProbe)
