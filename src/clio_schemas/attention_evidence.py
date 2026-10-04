"""Revision-bound attention inspections shared by transcript and reviewer surfaces."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from clio_schemas.attention import AttentionProfile
from clio_schemas.connected_resources import ContentSelection


class AttentionEvidenceInspection(BaseModel):
    """An exact inspection to revalidate against the owning session's capture."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1]
    selections: list[ContentSelection] = Field(min_length=1, max_length=32)
    direction: Literal["generated_to_source", "source_to_generation"]
    profile: AttentionProfile
    profile_revision: str = Field(min_length=1, max_length=256)
    lm_call_id: str = Field(min_length=1, max_length=256)
    capture_sha256: str = Field(min_length=1, max_length=256)
