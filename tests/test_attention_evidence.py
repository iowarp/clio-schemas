"""The shared finding receipt stays bounded and preserves exact inspection identity."""

import pytest
from pydantic import ValidationError

from clio_schemas.attention import UNIFORM_MEAN
from clio_schemas.attention_evidence import AttentionEvidenceInspection


def test_evidence_roundtrip_and_bounds() -> None:
    reference = {
        "session_id": "parent",
        "message_id": "message",
        "part_id": "part",
        "content_revision": "revision",
        "selection": {"kind": "whole"},
    }
    raw = {
        "schema_version": 1,
        "direction": "generated_to_source",
        "selections": [reference],
        "profile": UNIFORM_MEAN.model_dump(),
        "profile_revision": UNIFORM_MEAN.revision,
        "lm_call_id": "call",
        "capture_sha256": "c" * 64,
    }
    receipt = AttentionEvidenceInspection.model_validate(raw)
    assert AttentionEvidenceInspection.model_validate_json(receipt.model_dump_json()) == receipt
    for count in (0, 33):
        with pytest.raises(ValidationError):
            AttentionEvidenceInspection.model_validate({**raw, "selections": [reference] * count})
    with pytest.raises(ValidationError):
        AttentionEvidenceInspection.model_validate({**raw, "session_id": "other"})
