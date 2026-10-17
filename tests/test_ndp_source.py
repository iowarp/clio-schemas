"""NDP source identity is shared while upstream access remains read-only."""

import pytest
from pydantic import ValidationError

from clio_schemas.connected_resources import ConnectedSource, ResourceOwner, SourceCapabilities


def test_ndp_source_is_read_only() -> None:
    """Even a provider claiming write capabilities cannot authorize NDP mutations."""
    source = ConnectedSource(
        id="ndp",
        owner=ResourceOwner(clio_id="clio", host_id="local"),
        provider="ndp",
        root="dataset",
        label="Dataset",
        capabilities=SourceCapabilities(),
    )
    assert source.provider == "ndp"
    with pytest.raises(ValidationError, match="read-only"):
        ConnectedSource(
            **{
                **source.model_dump(),
                "capabilities": SourceCapabilities(
                    writable_folder=True, supported_modes=["read_only", "write_enabled"]
                ),
                "mode": "write_enabled",
            }
        )
