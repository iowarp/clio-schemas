"""A stream is an artifact kind whose content lives in clio-core (custody ``clio-core``)."""

from __future__ import annotations

from clio_schemas import ArtifactKind, ArtifactVersion, Custody, Mechanism
from clio_schemas.models import EvidenceClass, IdentityEvidence


def test_a_stream_version_has_clio_core_custody_and_round_trips() -> None:
    version = ArtifactVersion(
        artifact_id="artifact_" + "0" * 32,
        version=1,
        kind=ArtifactKind.STREAM,
        custody=Custody.CLIO_CORE,
        mechanism=Mechanism.HARNESS,
        evidence=IdentityEvidence(evidence_class=EvidenceClass.AUTHORITY_ASSERTED),
        producer={"designation": "stream", "stream_id": "stream_1"},
        path="",
        created_at="2026-11-06T00:00:00Z",
    )
    again = ArtifactVersion.model_validate_json(version.model_dump_json())
    assert again.kind is ArtifactKind.STREAM and again.custody is Custody.CLIO_CORE
    assert ArtifactKind("stream") is ArtifactKind.STREAM
    assert Custody("clio-core") is Custody.CLIO_CORE
