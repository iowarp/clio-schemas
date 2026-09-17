"""Official A2UI 0.9.1 client data-model transport model.

Mirrors ``client_data_model.json`` verbatim: the ``a2uiClientDataModel`` A2A
metadata object, mapping surface id -> that surface's current data model.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class A2UIClientDataModel(BaseModel):
    """The ``a2uiClientDataModel`` A2A metadata object a client may attach."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    version: Literal["v0.9", "v0.9.1"]
    surfaces: dict[str, dict[str, JsonValue]] = Field(default_factory=dict)
