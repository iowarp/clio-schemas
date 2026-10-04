"""Cross-client resource contracts reject unsupported modes and invalid coordinates."""

import pytest
from pydantic import ValidationError

from clio_schemas.connected_resources import (
    ConnectedSource,
    ContentSelection,
    HostStorageLocations,
    ImageSelection,
    ResourceOwner,
    SourceCapabilities,
    StructuredSelection,
    SurfaceSelectionIdentity,
)


@pytest.mark.parametrize("path", ["/", "C:\\", "relative", "/data/../etc", "/data/\nsecret"])
def test_storage_requires_dedicated_absolute_paths(path: str) -> None:
    with pytest.raises(ValidationError):
        HostStorageLocations(root=path)


def test_storage_preserves_remote_paths() -> None:
    assert HostStorageLocations(root="/data/clio").root == "/data/clio"
    assert HostStorageLocations(models="D:\\Models").models == "D:\\Models"


def test_github_can_link_without_a_download_backend() -> None:
    source = ConnectedSource(
        id="repository",
        owner=ResourceOwner(clio_id="c", host_id="local"),
        provider="github",
        label="Public repository",
        root="https://github.com/fsspec/filesystem_spec",
        capabilities=SourceCapabilities(link_folder=True, download=False),
    )
    assert source.capabilities.link_folder
    assert not source.capabilities.download
    assert not source.capabilities.read_only_mount


def test_mode_cannot_claim_mount_or_conflict_support() -> None:
    for mode in ("write_enabled", "working_copy"):
        with pytest.raises(ValidationError):
            SourceCapabilities(supported_modes=[mode])
    with pytest.raises(ValidationError):
        ConnectedSource(
            id="drive-input",
            owner=ResourceOwner(clio_id="delta", host_id="local"),
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


def test_surface_selection_retains_revision_and_definition_digest() -> None:
    identity = SurfaceSelectionIdentity(
        surface_id="chart", component_id="table", revision=2, sha256="a" * 64
    )
    ref = ContentSelection(
        session_id="s",
        message_id="m",
        part_id="p",
        content_revision="part-digest",
        field="content",
        surface=identity,
        selection=StructuredSelection(
            surface_id="chart",
            component_id="table",
            source_ref="artifact://rows",
            keys=['["id","a"]'],
        ),
    )
    assert ContentSelection.model_validate_json(ref.model_dump_json()) == ref
    with pytest.raises(ValidationError):
        SurfaceSelectionIdentity(surface_id="chart", component_id="table", revision=-1, sha256="x")
