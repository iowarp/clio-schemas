"""Provider-independent identities for indexed knowledge and explicit note relationships."""

from typing import Literal

from pydantic import Field

from clio_schemas.connected_resources import ResourceContract


class KnowledgeNote(ResourceContract):
    """A source-relative note or attachment, with the indexed content revision."""

    path: str = Field(min_length=1)
    title: str
    kind: Literal["note", "attachment"] = "note"
    revision: str
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    headings: list[str] = Field(default_factory=list)
    blocks: list[str] = Field(default_factory=list)
    excerpt: str = ""


class KnowledgeLink(ResourceContract):
    """An explicit link or embed; unresolved and ambiguous targets stay explicit."""

    source: str
    target: str
    selector: str = ""
    kind: Literal["link", "embed"] = "link"
    status: Literal["resolved", "unresolved", "ambiguous", "external"] = "resolved"
    candidates: list[str] = Field(default_factory=list)


class KnowledgeSnapshot(ResourceContract):
    """A bounded source view used by graph, list, reader, and agent operations."""

    source_id: str
    revision: str
    state: Literal["ready", "indexing", "failed"] = "ready"
    notes: list[KnowledgeNote] = Field(max_length=500)
    links: list[KnowledgeLink] = Field(max_length=2000)
    total: int = Field(ge=0)
    offset: int = Field(default=0, ge=0)
    next_offset: int | None = None
    truncated: bool = False
    relationships_truncated: bool = False
    warnings: list[str] = Field(default_factory=list)


class KnowledgeGraphSnapshot(KnowledgeSnapshot):
    """A whole-source topology overview, independent of paginated file/search reads."""

    notes: list[KnowledgeNote] = Field(max_length=5000)
    links: list[KnowledgeLink] = Field(max_length=20000)
