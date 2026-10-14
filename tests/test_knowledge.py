"""Knowledge contracts preserve provider semantics and reject unsupported access promises."""

import pytest
from pydantic import ValidationError

from clio_schemas.connected_resources import ConnectedSource, ResourceOwner, SourceCapabilities
from clio_schemas.knowledge import (
    KnowledgeGraphSnapshot,
    KnowledgeLink,
    KnowledgeNote,
    KnowledgeSnapshot,
)


def test_obsidian_requires_vault_knowledge_semantics() -> None:
    """A vault cannot silently acquire generic folder or OAuth semantics."""
    values = {
        "id": "source",
        "provider": "obsidian",
        "owner": ResourceOwner(clio_id="c", host_id="local"),
        "label": "Research",
        "root": "/vault",
        "capabilities": SourceCapabilities(note_read=True),
    }
    with pytest.raises(ValidationError, match="knowledge source"):
        ConnectedSource(**values)
    source = ConnectedSource(**values, source_kind="knowledge", connection="local_vault")
    assert source.mode == "read_only" and not source.capabilities.note_write
    with pytest.raises(ValidationError, match="conditional"):
        ConnectedSource(
            **{**values, "capabilities": SourceCapabilities(note_write=True)},
            source_kind="knowledge",
            connection="headless_sync",
        )


def test_bounded_snapshot_rejects_invalid_offsets_and_extra_fields() -> None:
    """Clients share a strict bounded graph/list contract."""
    snapshot = KnowledgeSnapshot(source_id="source", revision="r", notes=[], links=[], total=0)
    assert snapshot.state == "ready" and not snapshot.truncated
    with pytest.raises(ValidationError):
        KnowledgeSnapshot.model_validate({**snapshot.model_dump(), "offset": -1})
    with pytest.raises(ValidationError):
        KnowledgeSnapshot.model_validate({**snapshot.model_dump(), "credential": "forbidden"})
    with pytest.raises(ValidationError, match="500"):
        KnowledgeSnapshot(
            source_id="s",
            revision="r",
            notes=[KnowledgeNote(path="a.md", title="A", revision="h")] * 501,
            links=[],
            total=501,
        )
    with pytest.raises(ValidationError, match="2000"):
        KnowledgeSnapshot(
            source_id="s",
            revision="r",
            notes=[],
            links=[KnowledgeLink(source="a.md", target="b.md")] * 2001,
            total=0,
        )


def test_graph_overview_has_separate_bounded_capacity() -> None:
    """A full graph fits across file pages without widening agent search results."""
    note = KnowledgeNote(path="a.md", title="A", revision="h")
    graph = KnowledgeGraphSnapshot(
        source_id="s", revision="r", notes=[note] * 1961, links=[], total=1961
    )
    assert len(graph.notes) == 1961
    with pytest.raises(ValidationError, match="5000"):
        KnowledgeGraphSnapshot.model_validate({**graph.model_dump(), "notes": [note] * 5001})
    with pytest.raises(ValidationError, match="20000"):
        KnowledgeGraphSnapshot.model_validate(
            {**graph.model_dump(), "links": [KnowledgeLink(source="a.md", target="b.md")] * 20001}
        )
