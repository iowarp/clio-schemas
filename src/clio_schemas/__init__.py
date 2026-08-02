"""Canonical shared record schemas for CLIO services."""

from __future__ import annotations

from clio_schemas.constants import LOCKED_PYDANTIC_VERSION
from clio_schemas.models import (
    EXPORTED_MODELS,
    RESERVED_KINDS,
    AgentRole,
    ArtifactKind,
    ArtifactRecord,
    ArtifactVersion,
    ClioSchemaBase,
    Custody,
    EdgeEvidence,
    EdgeRole,
    EnvironmentRecord,
    EnvironmentTier,
    EvidenceClass,
    IdentityEvidence,
    Instrument,
    LegacyToleranceBase,
    Mechanism,
    ProvEdge,
    ReplayContract,
    TransformKind,
    TransformRecord,
    TransformStatus,
    new_artifact_id,
)

__all__ = [
    "EXPORTED_MODELS",
    "LOCKED_PYDANTIC_VERSION",
    "RESERVED_KINDS",
    "AgentRole",
    "ArtifactKind",
    "ArtifactRecord",
    "ArtifactVersion",
    "ClioSchemaBase",
    "Custody",
    "EdgeEvidence",
    "EdgeRole",
    "EnvironmentRecord",
    "EnvironmentTier",
    "EvidenceClass",
    "IdentityEvidence",
    "Instrument",
    "LegacyToleranceBase",
    "Mechanism",
    "ProvEdge",
    "ReplayContract",
    "TransformKind",
    "TransformRecord",
    "TransformStatus",
    "__version__",
    "new_artifact_id",
]

# Exact-pin lockstep versioning (see README "Versioning policy").
__version__ = "0.2.1"
