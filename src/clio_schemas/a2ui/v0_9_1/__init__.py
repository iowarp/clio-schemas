"""Official A2UI 0.9.1 wire-shape models (envelopes, capabilities, catalog files)."""

from __future__ import annotations

from clio_schemas.a2ui.v0_9_1.bounded_components import COMPONENT_MODELS
from clio_schemas.a2ui.v0_9_1.capabilities import (
    A2UIAgentCapabilities,
    A2UIClientCapabilities,
    InlineCatalog,
)
from clio_schemas.a2ui.v0_9_1.catalog_file import CatalogFile, FunctionDefinition
from clio_schemas.a2ui.v0_9_1.components import COMPONENT_SPECS
from clio_schemas.a2ui.v0_9_1.data_model import A2UIClientDataModel
from clio_schemas.a2ui.v0_9_1.messages import (
    A2UIClientAction,
    A2UIClientMessage,
    A2UIGenericError,
    A2UIServerMessage,
    A2UIValidationError,
    CreateSurfacePayload,
    DeleteSurfacePayload,
    UpdateComponentsPayload,
    UpdateDataModelPayload,
)

__all__ = [
    "COMPONENT_MODELS",
    "COMPONENT_SPECS",
    "A2UIAgentCapabilities",
    "A2UIClientAction",
    "A2UIClientCapabilities",
    "A2UIClientDataModel",
    "A2UIClientMessage",
    "A2UIGenericError",
    "A2UIServerMessage",
    "A2UIValidationError",
    "CatalogFile",
    "CreateSurfacePayload",
    "DeleteSurfacePayload",
    "FunctionDefinition",
    "InlineCatalog",
    "UpdateComponentsPayload",
    "UpdateDataModelPayload",
]
