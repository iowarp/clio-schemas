"""The v3 ``resource`` block: a workspace resource attached to a message (issue #6).

Payloads are shaped exactly as clio-agent's ``part_to_v3_block`` emits them for a
``resource_ref`` part, so gact-tui can drop its hand-written bridge schema.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaValidationError
from pydantic import ValidationError

from clio_schemas.gact_v3 import MessageBlock, ResourceMessageBlock

MESSAGE_BLOCK_SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "src/clio_schemas/schemas/message_block.json").read_text(
        encoding="utf-8"
    )
)

_RESOURCE: dict[str, object] = {
    "id": "part_1",
    "type": "resource",
    "resource_id": "res_1",
    "resource_revision": "3",
    "workspace_id": "ws_1",
    "name": "spectra.h5",
    "media_type": "application/x-hdf5",
}
_DELIVERED: dict[str, object] = {
    **_RESOURCE,
    "delivery": {
        "representation": "bounded_tools",
        "evidence_source": "probe",
        "reason": "Too large to inline; read through the HDF5 tools.",
    },
    "agent_id": "main",
    "sequence": 4,
}


@pytest.mark.parametrize("payload", [_RESOURCE, _DELIVERED], ids=["plain", "with-delivery"])
def test_resource_block_round_trips_through_model_and_schema(payload: dict[str, object]) -> None:
    block = MessageBlock.model_validate(payload)
    assert isinstance(block.root, ResourceMessageBlock)
    assert block.model_dump(mode="json", exclude_none=True) == payload
    Draft202012Validator(MESSAGE_BLOCK_SCHEMA).validate(payload)


@pytest.mark.parametrize(
    "representation",
    ["native", "bounded_tools", "structured_document", "sandbox", "retrieval", "metadata_only"],
)
def test_every_delivery_representation_is_accepted(representation: str) -> None:
    payload = {**_RESOURCE, "delivery": {"representation": representation}}
    assert MessageBlock.model_validate(payload).model_dump(exclude_none=True) == payload


@pytest.mark.parametrize(
    "payload",
    [
        {**_RESOURCE, "resource_revision": 3},
        {**_RESOURCE, "delivery": {"representation": "inline"}},
        {**_RESOURCE, "delivery": {"representation": "native", "detail": "x"}},
        {k: v for k, v in _RESOURCE.items() if k != "workspace_id"},
        {**_RESOURCE, "uri": "file:///tmp/spectra.h5"},
    ],
    ids=[
        "integer-revision",
        "unknown-representation",
        "extra-delivery-key",
        "missing-workspace",
        "extra-block-key",
    ],
)
def test_resource_block_rejects_off_contract_payloads(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        MessageBlock.model_validate(payload)
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(MESSAGE_BLOCK_SCHEMA).validate(payload)
