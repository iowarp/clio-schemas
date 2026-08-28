"""Canonical shared record models.

The artifact and provenance records were extracted from clio-agent in P2.1
(iowarp/clio-agent#1120). Their historical validation behavior is deliberately
preserved by :class:`LegacyToleranceBase`; tightening those wire contracts is a
separate, coordinated convergence tracked by iowarp/clio-agent#1121.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from clio_schemas.a2ui_v091 import A2UIClientActionMessage, A2UIComponent
from clio_schemas.gact_v3 import MessageBlock


class ClioSchemaBase(BaseModel):
    """Base for new canonical wire records.

    New records reject unknown keys, disable coercion, and are immutable. The
    extracted legacy records below cannot adopt those rules without changing
    their accepted wire inputs, so they use :class:`LegacyToleranceBase`.
    """

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class LegacyToleranceBase(BaseModel):
    """Compatibility base preserving the extracted models' legacy semantics.

    clio-agent's original Pydantic models ignored unknown keys and used normal
    coercive validation. Those behaviors remain exact here; convergence on the
    stricter :class:`ClioSchemaBase` contract is tracked by
    iowarp/clio-agent#1121 and must be coordinated across all consumers.
    Individual records override only their historical mutability setting.
    """

    model_config = ConfigDict(extra="ignore", strict=False, frozen=True)


class ArtifactKind(str, Enum):  # noqa: UP042 - legacy str() semantics preserved (clio-agent#1121)
    """The curated kinds an artifact version may take."""

    DATASET = "dataset"
    IMAGE = "image"
    REPORT = "report"
    PLAN = "plan"
    SCRIPT = "script"
    CONFIG = "config"
    MODEL = "model"
    UI_PAYLOAD = "ui_payload"
    OTHER = "other"


RESERVED_KINDS: frozenset[ArtifactKind] = frozenset({ArtifactKind.PLAN})


class Custody(str, Enum):  # noqa: UP042 - legacy str() semantics preserved (clio-agent#1121)
    """Where artifact bytes live and what custody guarantee applies."""

    CAS = "cas"
    WORKSPACE_REFERENCED = "workspace-referenced"
    EXTERNAL_REFERENCED = "external-referenced"


class Mechanism(str, Enum):  # noqa: UP042 - legacy str() semantics preserved (clio-agent#1121)
    """What produced an artifact record."""

    HARNESS = "harness"
    TOOL_SCHEMA = "tool-schema"
    CHANGE_FEED = "change-feed"
    MODEL = "model"
    NONE = "none"


class EvidenceClass(str, Enum):  # noqa: UP042 - legacy str() semantics preserved (clio-agent#1121)
    """How an artifact version's identity is known."""

    HASHED_AT_USE = "hashed-at-use"
    AUTHORITY_ASSERTED = "authority-asserted"
    STAT_PINNED = "stat-pinned"


class IdentityEvidence(LegacyToleranceBase):
    """The evidence basis on which an artifact's content is pinned."""

    evidence_class: EvidenceClass
    sha256: str | None = None
    size_bytes: int | None = None
    mtime: float | None = None
    authority: str = ""

    @classmethod
    def hashed_at_use(
        cls, *, sha256: str, size_bytes: int, mtime: float | None = None
    ) -> IdentityEvidence:
        """Build locally computed hash evidence."""

        return cls(
            evidence_class=EvidenceClass.HASHED_AT_USE,
            sha256=sha256,
            size_bytes=size_bytes,
            mtime=mtime,
        )

    @classmethod
    def stat_pinned(cls, *, size_bytes: int, mtime: float | None = None) -> IdentityEvidence:
        """Build size-and-mtime-only evidence."""

        return cls(
            evidence_class=EvidenceClass.STAT_PINNED,
            size_bytes=size_bytes,
            mtime=mtime,
        )

    @classmethod
    def authority_asserted(
        cls,
        *,
        authority: str,
        sha256: str | None = None,
        size_bytes: int | None = None,
    ) -> IdentityEvidence:
        """Build authority-provided identity evidence."""

        return cls(
            evidence_class=EvidenceClass.AUTHORITY_ASSERTED,
            authority=authority,
            sha256=sha256,
            size_bytes=size_bytes,
        )


def new_artifact_id() -> str:
    """Return a fresh relay-format artifact id."""

    return f"artifact_{uuid.uuid4().hex}"


class ArtifactVersion(LegacyToleranceBase):
    """One immutable version of a logical artifact."""

    artifact_id: str = Field(default_factory=new_artifact_id)
    version: int = 1
    kind: ArtifactKind = ArtifactKind.OTHER
    custody: Custody = Custody.WORKSPACE_REFERENCED
    mechanism: Mechanism = Mechanism.TOOL_SCHEMA
    evidence: IdentityEvidence
    producer: dict[str, Any] = Field(default_factory=dict)
    path: str = ""
    created_at: str = ""
    annotation: str = ""
    prior_version: int | None = None
    prior_sha256: str | None = None
    kind_warning: str = ""
    custody_gap: dict[str, Any] | None = None
    not_ingested_size: int | None = None

    @property
    def sha256(self) -> str | None:
        """Return the content hash, if present."""

        return self.evidence.sha256

    @property
    def size_bytes(self) -> int | None:
        """Return the recorded byte size, if present."""

        return self.evidence.size_bytes

    def to_artifact_ref(self) -> dict[str, Any]:
        """Project to the relay ArtifactRef/ArtifactUse edge shape."""

        return {
            "artifact_id": self.artifact_id,
            "sha256": self.sha256,
            "metadata": {
                "kind": self.kind.value,
                "version": self.version,
                "custody": self.custody.value,
                "mechanism": self.mechanism.value,
                "evidence_class": self.evidence.evidence_class.value,
            },
        }


class ArtifactRecord(LegacyToleranceBase):
    """A mutable logical artifact chain keyed by workspace and name."""

    model_config = ConfigDict(extra="ignore", strict=False, frozen=False)

    workspace_id: str
    name: str
    versions: list[ArtifactVersion] = Field(default_factory=list)
    aliases: dict[str, int] = Field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str]:
        """Return the logical artifact identity."""

        return (self.workspace_id, self.name)

    @property
    def kind(self) -> ArtifactKind:
        """Return the head kind, or ``other`` for an empty chain."""

        head = self.head
        return head.kind if head is not None else ArtifactKind.OTHER

    @property
    def locked_kind(self) -> ArtifactKind | None:
        """Return the kind locked by the first version."""

        return self.versions[0].kind if self.versions else None

    @property
    def head(self) -> ArtifactVersion | None:
        """Return the newest version, if any."""

        return self.versions[-1] if self.versions else None

    def version_for_sha(self, sha256: str | None) -> ArtifactVersion | None:
        """Return the version matching ``sha256``, if any."""

        if not sha256:
            return None
        for version in self.versions:
            if version.sha256 == sha256:
                return version
        return None

    def add_version(self, version: ArtifactVersion) -> ArtifactVersion:
        """Insert a version in order and move ``latest`` to the head."""

        self.versions.append(version)
        self.versions.sort(key=lambda item: item.version)
        self.aliases["latest"] = self.versions[-1].version
        return version

    def next_version_number(self) -> int:
        """Return the version number a new head would take."""

        return (self.head.version + 1) if self.head is not None else 1


class EdgeRole(str, Enum):  # noqa: UP042 - legacy str() semantics preserved (clio-agent#1121)
    """Which side of a transform a provenance edge sits on."""

    USED = "used"
    GENERATED = "generated"


class EdgeEvidence(str, Enum):  # noqa: UP042 - legacy str() semantics preserved (clio-agent#1121)
    """How a provenance edge's identity is known."""

    SCHEMA_ARG = "schema-arg"
    HASH_PAIR = "hash-pair"
    LEASE_WINDOW = "lease-window"
    AUTHORITY = "authority"
    ASSERTION = "assertion"


class TransformStatus(str, Enum):  # noqa: UP042 - legacy str() semantics preserved (clio-agent#1121)
    """Whether the producing call succeeded."""

    SUCCESS = "success"
    FAILED = "failed"


class AgentRole(str, Enum):  # noqa: UP042 - legacy str() semantics preserved (clio-agent#1121)
    """Whether the agent executed or annotated the transform."""

    EXECUTING = "executing"
    ANNOTATING = "annotating"


class TransformKind(str, Enum):  # noqa: UP042 - legacy str() semantics preserved (clio-agent#1121)
    """Whether provenance was observed under exclusive or contended custody."""

    ORDINARY = "ordinary"
    CONTENDED = "contended"


class ReplayContract(str, Enum):  # noqa: UP042 - legacy str() semantics preserved (clio-agent#1121)
    """The permanent replay guarantee stamped on a transform."""

    REPRODUCIBLE = "reproducible"
    RE_RUNNABLE = "re-runnable"


class ProvEdge(LegacyToleranceBase):
    """One used or generated provenance edge with its own evidence."""

    role: EdgeRole
    evidence: EdgeEvidence
    artifact_id: str = ""
    sha256: str | None = None
    external_ref: str = ""
    authority: str = ""
    name: str = ""
    version: int | None = None
    path: str = ""
    arg: str = ""
    note: str = ""
    net_domain: str = ""
    net_mechanism: str = ""
    net_at: str = ""
    net_resolved_ip: str = ""
    fence_proven: bool = False
    cross_workspace_bind: bool = False

    def to_artifact_use(self) -> dict[str, Any] | None:
        """Project a hash-pinned registered edge to relay ArtifactUse."""

        if not self.artifact_id or not self.sha256:
            return None
        return {"artifact_id": self.artifact_id, "sha256": self.sha256}


class Instrument(LegacyToleranceBase):
    """The tool or script that produced a transform."""

    tool: str = ""
    args: dict[str, Any] = Field(default_factory=dict)
    cmd: str = ""
    script_hash: str = ""
    script_artifact_id: str = ""


class EnvironmentTier(str, Enum):  # noqa: UP042 - legacy str() semantics preserved (clio-agent#1121)
    """How precisely an execution environment is pinned."""

    DECLARED = "declared"
    LOCKFILE_HASH = "lockfile-hash"
    IMAGE_DIGEST = "image-digest"


class EnvironmentRecord(LegacyToleranceBase):
    """Nested schema for a transform's non-secret execution environment."""

    tier: EnvironmentTier = EnvironmentTier.DECLARED
    clio_version: str = ""
    lockfile_sha256: str = ""
    launcher_fingerprint: str = ""
    provider_id: str = ""
    model_id: str = ""
    model_variant: str = ""
    model_source: str = ""
    os: str = ""
    arch: str = ""
    python_version: str = ""
    image_digest: str = ""
    sandbox_mechanism: str = ""
    sandbox_reason: str = ""


if TYPE_CHECKING:
    _EnvironmentField = Any
else:
    _EnvironmentField = EnvironmentRecord


class TransformRecord(LegacyToleranceBase):
    """One coarse transform keyed by the observer call id."""

    call_id: str
    event_id: str = ""
    session_id: str = ""
    turn_id: str = ""
    workspace_id: str = ""
    status: TransformStatus = TransformStatus.SUCCESS
    kind: TransformKind = TransformKind.ORDINARY
    agent_role: AgentRole = AgentRole.EXECUTING
    agent_id: str = ""
    instrument: Instrument = Field(default_factory=Instrument)
    environment: _EnvironmentField = Field(default_factory=EnvironmentRecord)
    replay: ReplayContract = ReplayContract.RE_RUNNABLE
    replay_reason: str = ""
    used: list[ProvEdge] = Field(default_factory=list)
    generated: list[ProvEdge] = Field(default_factory=list)
    started_at: str = ""
    ended_at: str = ""
    annotation: str = ""
    candidates: list[str] = Field(default_factory=list)
    notes: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("environment", mode="before")
    @classmethod
    def _accept_legacy_environment(cls, value: Any) -> Any:
        """Normalize clio-agent's identical legacy environment value."""

        value_type = type(value)
        if (
            isinstance(value, BaseModel)
            and value_type.__name__ == "EnvironmentRecord"
            and value_type.__module__ == "clio_agent.gact.artifacts.environment"
        ):
            return EnvironmentRecord.model_validate(value.model_dump())
        return EnvironmentRecord.model_validate(value)

    def to_payload(self) -> dict[str, Any]:
        """Return the durable artifact.transform.recorded payload."""

        return {
            "event_id": self.event_id,
            "call_id": self.call_id,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "workspace_id": self.workspace_id,
            "status": self.status.value,
            "kind": self.kind.value,
            "agent_role": self.agent_role.value,
            "agent_id": self.agent_id,
            "instrument": self.instrument.model_dump(),
            "environment": self.environment.model_dump(),
            "replay": self.replay.value,
            "replay_reason": self.replay_reason,
            "used": [edge.model_dump() for edge in self.used],
            "generated": [edge.model_dump() for edge in self.generated],
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "annotation": self.annotation,
            "candidates": list(self.candidates),
            "notes": [dict(note) for note in self.notes],
        }

    def to_relay_provenance(self) -> dict[str, Any]:
        """Return the relay provenance metadata extension."""

        return {
            "activity_id": self.call_id,
            "instrument": self.instrument.model_dump(),
            "environment": self.environment.model_dump(),
            "replay": self.replay.value,
            "used_evidence": [
                {
                    "artifact_id": edge.artifact_id,
                    "external_ref": edge.external_ref,
                    "authority": edge.authority,
                    "evidence": edge.evidence.value,
                    "note": edge.note,
                }
                for edge in self.used
            ],
            "used_artifact_refs": [
                use for edge in self.used if (use := edge.to_artifact_use()) is not None
            ],
        }


# The registry the exporter iterates. Keep it alphabetical by class name.
EXPORTED_MODELS: tuple[type[BaseModel], ...] = (
    A2UIClientActionMessage,
    A2UIComponent,
    ArtifactRecord,
    ArtifactVersion,
    EnvironmentRecord,
    IdentityEvidence,
    Instrument,
    MessageBlock,
    ProvEdge,
    TransformRecord,
)
