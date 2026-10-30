"""Two block shapes clio-agent already emits: ``context_reference`` and notice ``metadata``.

Payloads are shaped exactly as clio-agent's ``part_to_v3_block`` emits them (a
``context_ref`` part; an answer-hook ``notice``), so gact-tui can drop its
hand-written bridge schemas for both.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaValidationError
from pydantic import ValidationError

from clio_schemas.gact_v3 import ContextReferenceMessageBlock, MessageBlock, NoticeMessageBlock

MESSAGE_BLOCK_SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "src/clio_schemas/schemas/message_block.json").read_text(
        encoding="utf-8"
    )
)

_FILE_REFERENCE: dict[str, object] = {
    "id": "part_ref_1",
    "type": "context_reference",
    "ref_kind": "workspace_file",
    "ref_id": "data/spectra.h5",
    "label": "spectra.h5",
    "revision": "sha256:9f2c",
    "media_type": "application/x-hdf5",
    "navigation": {"workspace_id": "ws_1", "path": "data/spectra.h5"},
}
_RUN_REFERENCE: dict[str, object] = {
    **_FILE_REFERENCE,
    "ref_kind": "agent_run",
    "ref_id": "task_7",
    "label": "Independent audit",
    "media_type": "application/json",
    "navigation": {"workspace_id": "ws_1", "task_id": "task_7", "session_id": "sess_2"},
    "agent_id": "main",
    "sequence": 2,
}
_HOOK_NOTICE: dict[str, object] = {
    "id": "part_answer_hook_1a2b3c4d5e",
    "type": "notice",
    "source": "answer_hook",
    "text": "The answer was revised by the citations hook.",
    "code": "answer_revised",
    "metadata": {"hook": "citations", "revises": "part_answer_9"},
    "agent_id": "main",
}


@pytest.mark.parametrize(
    "payload", [_FILE_REFERENCE, _RUN_REFERENCE], ids=["workspace-file", "agent-run"]
)
def test_context_reference_round_trips_through_model_and_schema(
    payload: dict[str, object],
) -> None:
    block = MessageBlock.model_validate(payload)
    assert isinstance(block.root, ContextReferenceMessageBlock)
    assert block.model_dump(mode="json", exclude_none=True) == payload
    Draft202012Validator(MESSAGE_BLOCK_SCHEMA).validate(payload)


@pytest.mark.parametrize(
    "kind",
    [
        "workspace_file",
        "artifact",
        "session",
        "agent_run",
        "evidence_source",
        "context_frame",
        "diff",
        "plan",
    ],
)
def test_every_context_reference_kind_is_accepted(kind: str) -> None:
    payload = {**_FILE_REFERENCE, "ref_kind": kind}
    assert MessageBlock.model_validate(payload).model_dump(exclude_none=True) == payload


def test_navigation_defaults_to_empty() -> None:
    payload = {k: v for k, v in _FILE_REFERENCE.items() if k != "navigation"}
    block = MessageBlock.model_validate(payload).root
    assert isinstance(block, ContextReferenceMessageBlock) and block.navigation == {}


def test_hook_notice_metadata_round_trips() -> None:
    block = MessageBlock.model_validate(_HOOK_NOTICE)
    assert isinstance(block.root, NoticeMessageBlock)
    assert block.model_dump(mode="json", exclude_none=True) == _HOOK_NOTICE
    Draft202012Validator(MESSAGE_BLOCK_SCHEMA).validate(_HOOK_NOTICE)


@pytest.mark.parametrize(
    "payload",
    [
        {**_FILE_REFERENCE, "ref_kind": "url"},
        {**_FILE_REFERENCE, "revision": 3},
        {**_FILE_REFERENCE, "navigation": {"line": 4}},
        {k: v for k, v in _FILE_REFERENCE.items() if k != "media_type"},
        {**_HOOK_NOTICE, "metadata": {"hook": "citations", "score": "1"}},
    ],
    ids=[
        "unknown-kind",
        "integer-revision",
        "non-string-navigation",
        "missing-media-type",
        "extra-notice-metadata-key",
    ],
)
def test_off_contract_payloads_are_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        MessageBlock.model_validate(payload)
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(MESSAGE_BLOCK_SCHEMA).validate(payload)
