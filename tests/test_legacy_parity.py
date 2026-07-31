"""Golden byte parity and legacy-tolerance tests for the P2.1 extraction."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from clio_schemas import (
    AgentRole,
    ArtifactKind,
    ArtifactRecord,
    ArtifactVersion,
    Custody,
    EdgeEvidence,
    EdgeRole,
    EnvironmentRecord,
    EnvironmentTier,
    EvidenceClass,
    IdentityEvidence,
    Instrument,
    Mechanism,
    ProvEdge,
    ReplayContract,
    TransformKind,
    TransformRecord,
    TransformStatus,
)

GOLDEN_DIR = Path(__file__).parent / "legacy_golden_json"
GOLDEN_FILES = {
    "ArtifactRecord": "artifact_record.json",
    "ArtifactVersion": "artifact_version.json",
    "IdentityEvidence": "identity_evidence.json",
    "Instrument": "instrument.json",
    "ProvEdge": "prov_edge.json",
    "TransformRecord": "transform_record.json",
}


def _fixture_models() -> list[BaseModel]:
    """Build deterministic canonical records matching the pre-extraction fixtures."""

    evidence = IdentityEvidence(
        evidence_class=EvidenceClass.HASHED_AT_USE,
        sha256="a" * 64,
        size_bytes=17,
        mtime=1234.5,
        authority="catalog:fixture",
    )
    version = ArtifactVersion(
        artifact_id="artifact_0123456789abcdef0123456789abcdef",
        version=2,
        kind=ArtifactKind.DATASET,
        custody=Custody.CAS,
        mechanism=Mechanism.HARNESS,
        evidence=evidence,
        producer={"call_id": "call_fixture", "nested": {"n": 1}},
        path="data/input.csv",
        created_at="2026-07-31T12:34:56Z",
        annotation="fixture",
        prior_version=1,
        prior_sha256="b" * 64,
        kind_warning="kept dataset",
        custody_gap={"reason": "relink", "version": 1},
        not_ingested_size=999,
    )
    record = ArtifactRecord(
        workspace_id="ws_fixture",
        name="input.csv",
        versions=[version],
        aliases={"latest": 2, "stable": 2},
    )
    used = ProvEdge(
        role=EdgeRole.USED,
        evidence=EdgeEvidence.HASH_PAIR,
        artifact_id=version.artifact_id,
        sha256=version.sha256,
        external_ref="external:data/input.csv",
        authority="catalog:fixture",
        name="input.csv",
        version=2,
        path="data/input.csv",
        arg="input",
        note="relink",
        net_domain="data.example.org",
        net_mechanism="proxy-enforced",
        net_at="2026-07-31T12:34:55Z",
        net_resolved_ip="192.0.2.10",
        fence_proven=False,
        cross_workspace_bind=True,
    )
    generated = ProvEdge(
        role=EdgeRole.GENERATED,
        evidence=EdgeEvidence.LEASE_WINDOW,
        artifact_id="artifact_fedcba9876543210fedcba9876543210",
        sha256="c" * 64,
        name="output.csv",
        version=1,
        path="data/output.csv",
        fence_proven=True,
    )
    instrument = Instrument(
        tool="fs_write",
        args={"path": "data/output.csv", "rows": 3, "options": ["x", 2]},
        cmd="python make.py",
        script_hash="d" * 64,
        script_artifact_id="artifact_script_fixture",
    )
    environment = EnvironmentRecord(
        tier=EnvironmentTier.LOCKFILE_HASH,
        clio_version="0.9.0",
        lockfile_sha256="e" * 64,
        launcher_fingerprint="42:1234567890",
        provider_id="argonne",
        model_id="openai/gpt-oss-120b",
        model_variant="fp8",
        model_source="executing_lm",
        os="Linux",
        arch="x86_64",
        python_version="3.12.11",
        image_digest="",
        sandbox_mechanism="landlock",
        sandbox_reason="fence_active",
    )
    transform = TransformRecord(
        call_id="call_fixture",
        event_id="evt_fixture",
        session_id="sess_fixture",
        turn_id="turn_fixture",
        workspace_id="ws_fixture",
        status=TransformStatus.FAILED,
        kind=TransformKind.CONTENDED,
        agent_role=AgentRole.ANNOTATING,
        agent_id="agent_fixture",
        instrument=instrument,
        environment=environment,
        replay=ReplayContract.RE_RUNNABLE,
        replay_reason="contended",
        used=[used],
        generated=[generated],
        started_at="2026-07-31T12:34:50Z",
        ended_at="2026-07-31T12:35:00Z",
        annotation="fixture",
        candidates=["sess_other"],
        notes=[{"reason": "unresolved_path_arg", "arg": "missing"}],
    )
    return [evidence, version, record, used, instrument, transform]


@pytest.mark.parametrize("model", _fixture_models(), ids=lambda item: type(item).__name__)
def test_extracted_model_json_matches_original_golden(model: BaseModel) -> None:
    """Every moved model emits the exact bytes captured from its original class."""

    expected = (
        (GOLDEN_DIR / GOLDEN_FILES[type(model).__name__]).read_text(encoding="utf-8").rstrip("\n")
    )
    assert model.model_dump_json() == expected


def test_legacy_models_keep_coercion_and_ignore_unknown_keys() -> None:
    """LegacyToleranceBase preserves the old accepted-input behavior exactly."""

    evidence = IdentityEvidence.model_validate(
        {"evidence_class": "hashed-at-use", "size_bytes": "17", "future": "ignored"}
    )
    assert evidence.size_bytes == 17
    assert "future" not in evidence.model_dump()


def test_immutable_legacy_records_remain_frozen() -> None:
    """Extracted immutable records still reject assignment."""

    evidence = IdentityEvidence(evidence_class=EvidenceClass.STAT_PINNED)
    with pytest.raises(ValidationError):
        evidence.authority = "changed"


def test_artifact_record_remains_mutable() -> None:
    """ArtifactRecord retains the original mutable chain semantics."""

    record = ArtifactRecord(workspace_id="ws", name="before")
    record.name = "after"
    assert record.name == "after"
