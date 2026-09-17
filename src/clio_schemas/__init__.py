"""Canonical shared record schemas for CLIO services."""

from __future__ import annotations

from clio_schemas.a2ui.sidecar import CatalogSidecar
from clio_schemas.a2ui.v0_9_1.bounded_components import COMPONENT_MODELS
from clio_schemas.a2ui.v0_9_1.capabilities import A2UIAgentCapabilities, A2UIClientCapabilities
from clio_schemas.a2ui.v0_9_1.catalog_file import CatalogFile, FunctionDefinition
from clio_schemas.a2ui.v0_9_1.data_model import A2UIClientDataModel
from clio_schemas.a2ui.v0_9_1.messages import (
    A2UIClientAction,
    A2UIClientMessage,
    A2UIGenericError,
    A2UIServerMessage,
    A2UIValidationError,
)
from clio_schemas.constants import LOCKED_PYDANTIC_VERSION
from clio_schemas.gact_v3 import MessageBlock
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
    "COMPONENT_MODELS",
    "EXPORTED_MODELS",
    "LOCKED_PYDANTIC_VERSION",
    "RESERVED_KINDS",
    "A2UIAgentCapabilities",
    "A2UIClientAction",
    "A2UIClientCapabilities",
    "A2UIClientDataModel",
    "A2UIClientMessage",
    "A2UIGenericError",
    "A2UIServerMessage",
    "A2UIValidationError",
    "AgentRole",
    "ArtifactKind",
    "ArtifactRecord",
    "ArtifactVersion",
    "CatalogFile",
    "CatalogSidecar",
    "ClioSchemaBase",
    "Custody",
    "EdgeEvidence",
    "EdgeRole",
    "EnvironmentRecord",
    "EnvironmentTier",
    "EvidenceClass",
    "FunctionDefinition",
    "IdentityEvidence",
    "Instrument",
    "LegacyToleranceBase",
    "Mechanism",
    "MessageBlock",
    "ProvEdge",
    "ReplayContract",
    "TransformKind",
    "TransformRecord",
    "TransformStatus",
    "__version__",
    "new_artifact_id",
]

# Exact-pin lockstep versioning (see README "Versioning policy").
__version__ = "0.3.0"
