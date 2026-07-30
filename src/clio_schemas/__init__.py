"""clio-schemas — the single source of truth for cross-service record shapes.

This package holds the canonical `pydantic` v2 models shared by clio-agent,
clio-relay, and gact-tui (TaskRecord / ArtifactRef / ArtifactUse / part-record
shapes — content arriving in slice P2.1, issue #1120). Consumers never
hand-write these shapes: Python consumers import the models directly, and
TypeScript consumers generate `.ts` types from the JSON Schema shipped with the
package.

The canonical JSON Schemas are **immutable package resources** committed under
`clio_schemas/schemas/`. Consumers *copy* those bytes
(`python -m clio_schemas.export --out <dir>`); they do not regenerate them, so a
consumer's pydantic version can never perturb the shapes. Regeneration from the
models is a repo-local developer command (`--regenerate`) pinned to the locked
pydantic version.

During the P0.6 bootstrap two placeholder models exist — `SchemaProbe` and
`ProbeBatch` (which references `SchemaProbe` and reuses the shared `ProbeKind`
enum) — proving the pydantic -> JSON Schema -> TypeScript loop end to end,
including shared-definition handling.
"""

from __future__ import annotations

from clio_schemas.constants import LOCKED_PYDANTIC_VERSION
from clio_schemas.models import (
    EXPORTED_MODELS,
    ClioSchemaBase,
    ProbeBatch,
    ProbeKind,
    SchemaProbe,
)

__all__ = [
    "EXPORTED_MODELS",
    "LOCKED_PYDANTIC_VERSION",
    "ClioSchemaBase",
    "ProbeBatch",
    "ProbeKind",
    "SchemaProbe",
    "__version__",
]

# Exact-pin lockstep versioning (see README "Versioning policy"): every
# consumer pins this exact version, and a schema change bumps it in lockstep.
__version__ = "0.1.0"
