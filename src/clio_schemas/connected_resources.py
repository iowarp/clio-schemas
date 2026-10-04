"""Host-bound storage and content identities shared by CLIO clients and services."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ResourceContract(BaseModel):
    """Immutable wire records with explicit validation and no unknown fields."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ResourceOwner(ResourceContract):
    """The connected CLIO and execution host that own a resource or operation."""

    clio_id: str = Field(min_length=1)
    host_id: str = Field(min_length=1)


AccessMode = Literal["read_only", "working_copy", "write_enabled"]


class SourceCapabilities(ResourceContract):
    """Observed provider/node capabilities; file access does not imply an OS mount."""

    browse: bool = True
    search: bool = False
    download: bool = True
    native_transfer: bool = False
    revision_check: bool = False
    conditional_write: bool = False
    writable_folder: bool = False
    read_only_mount: bool = False
    supported_modes: list[AccessMode] = Field(default_factory=lambda: ["read_only"])
    unavailable_reasons: dict[AccessMode, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_modes(self) -> Self:
        """Do not promise writable folders or conflict review without support."""
        if "write_enabled" in self.supported_modes and not self.writable_folder:
            raise ValueError("Write enabled requires an actual writable source folder")
        if "working_copy" in self.supported_modes and not self.revision_check:
            raise ValueError("Working copies require upstream revision checks")
        return self


class ConnectedSource(ResourceContract):
    """Approved source identity without credentials or authorization codes."""

    schema_version: Literal[1] = 1
    id: str = Field(min_length=1)
    owner: ResourceOwner
    provider: Literal["local", "sftp", "google_drive", "globus"]
    label: str = Field(min_length=1)
    root: str = Field(min_length=1)
    mode: AccessMode = "read_only"
    capabilities: SourceCapabilities
    revision: str | None = None
    materialization: Literal["not_materialized", "transferring", "ready", "stale", "failed"] = (
        "not_materialized"
    )
    operation_id: str | None = None
    workspace_id: str | None = None
    local_path: str | None = None

    @model_validator(mode="after")
    def check_mode(self) -> Self:
        """Reject modes the selected provider/node cannot implement."""
        if self.mode not in self.capabilities.supported_modes:
            raise ValueError("The source does not support the selected access mode")
        return self


class HostStorageLocations(ResourceContract):
    """Persistent paths on one host; empty overrides inherit the root's subfolders."""

    root: str = ""
    models: str = ""
    service_data: str = ""
    captures: str = ""
    temporary: str = ""

    @field_validator("root", "models", "service_data", "captures", "temporary")
    @classmethod
    def dedicated_absolute_path(cls, value: str) -> str:
        """Accept target-native absolute paths without interpreting them locally."""
        value = value.strip()
        if not value:
            return ""
        if len(value) > 4096 or any(ord(char) < 32 for char in value):
            raise ValueError("Storage paths cannot contain control characters or exceed 4096 chars")
        path = PurePosixPath(value) if value.startswith("/") else PureWindowsPath(value)
        if not path.is_absolute() or str(path) == path.anchor or ".." in path.parts:
            raise ValueError("Choose a dedicated absolute storage directory")
        return value


class TextSelection(ResourceContract):
    """Character offsets within an identified content part, using Unicode code points."""

    kind: Literal["text"] = "text"
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        """Reject empty and reversed text intervals."""
        if self.end <= self.start:
            raise ValueError("Selection end must be after start")
        return self


class WholeSelection(ResourceContract):
    """The whole identified block or artifact."""

    kind: Literal["whole"] = "whole"


class ImageSelection(ResourceContract):
    """Normalized image coordinates, independent of display size."""

    kind: Literal["image_region"] = "image_region"
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def within_image(self) -> Self:
        """Keep the entire selected region inside the image."""
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("Image region extends outside the image")
        return self


class StructuredSelection(ResourceContract):
    """Stable A2UI component and source keys, never inferred from display order."""

    kind: Literal["structured"] = "structured"
    surface_id: str = Field(min_length=1)
    component_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    keys: list[str] = Field(min_length=1)


class ContentSelection(ResourceContract):
    """An inspectable transcript reference with revision-bound selection coordinates."""

    schema_version: Literal[1] = 1
    session_id: str = Field(min_length=1)
    message_id: str = Field(min_length=1)
    part_id: str = Field(min_length=1)
    content_revision: str = Field(min_length=1)
    call_id: str | None = None
    artifact_ref: str | None = None
    selection: Annotated[
        TextSelection | WholeSelection | ImageSelection | StructuredSelection,
        Field(discriminator="kind"),
    ]
