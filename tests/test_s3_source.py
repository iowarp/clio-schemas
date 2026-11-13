"""S3 sources are linked read-only; writing to a bucket is not supported."""

import pytest
from pydantic import ValidationError

from clio_schemas.connected_resources import ConnectedSource, ResourceOwner, SourceCapabilities


def test_s3_source_is_read_only() -> None:
    """Even a provider claiming write capabilities cannot authorize S3 mutations."""
    source = ConnectedSource(
        id="s3",
        owner=ResourceOwner(clio_id="clio", host_id="local"),
        provider="s3",
        root="bucket/prefix",
        label="Bucket",
        capabilities=SourceCapabilities(),
    )
    assert source.provider == "s3"
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
