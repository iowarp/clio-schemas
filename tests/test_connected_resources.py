"""Cross-client resource contracts reject unsupported modes and invalid coordinates."""

import pytest
from pydantic import ValidationError

from clio_schemas.connected_resources import (
    ConnectedSource,
    ContentSelection,
    HostStorageLocations,
    ImageSelection,
    SourceCapabilities,
)


@pytest.mark.parametrize("path", ["/", "C:\\", "relative", "/data/../etc", "/data/\nsecret"])
def test_storage_requires_dedicated_absolute_paths(path: str) -> None:
    with pytest.raises(ValidationError):
        HostStorageLocations(root=path)


def test_storage_preserves_remote_paths() -> None:
    assert HostStorageLocations(root="/data/clio").root == "/data/clio"
    assert HostStorageLocations(models="D:\\Models").models == "D:\\Models"


def test_mode_cannot_claim_mount_or_conflict_support() -> None:
    for mode in ("write_enabled", "working_copy"):
        with pytest.raises(ValidationError):
            SourceCapabilities(supported_modes=[mode])
    with pytest.raises(ValidationError):
        ConnectedSource(
            id="drive-input",
            owner={"clio_id": "delta", "host_id": "local"},
            provider="google_drive",
            label="OPAL",
            root="folder-id",
            mode="write_enabled",
            capabilities=SourceCapabilities(),
        )


def test_selection_roundtrip_and_bounds() -> None:
    selection = ContentSelection.model_validate(
        {
            "session_id": "s",
            "message_id": "m",
            "part_id": "p",
            "content_revision": "sha256:x",
            "selection": {"kind": "text", "start": 0, "end": 5},
        }
    )
    assert ContentSelection.model_validate_json(selection.model_dump_json()) == selection
    assert selection.field == "text"
    thought = ContentSelection.model_validate({**selection.model_dump(), "field": "thought"})
    assert thought.field != selection.field
    with pytest.raises(ValidationError):
        ContentSelection.model_validate({**selection.model_dump(), "field": "made-up"})
    with pytest.raises(ValidationError):
        ImageSelection(x=0.9, y=0, width=0.2, height=0.1)
    with pytest.raises(ValidationError):
        ContentSelection.model_validate(
            {
                **selection.model_dump(),
                "selection": {
                    "kind": "text",
                    "start": 5,
                    "end": 2,
                },
            }
        )
