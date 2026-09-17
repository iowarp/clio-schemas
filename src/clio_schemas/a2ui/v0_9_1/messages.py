"""Official A2UI 0.9.1 server<->client envelope models.

Mirrors ``server_to_client.json`` and ``client_to_server.json`` in the
vendored spec (``src/clio_schemas/schemas/a2ui/v0_9_1/``) verbatim: the
server->client envelope is exactly one of ``createSurface`` /
``updateComponents`` / ``updateDataModel`` / ``deleteSurface``; the
client->server envelope is exactly two top-level keys, ``version`` plus
either ``action`` or ``error``. Component payloads inside
``updateComponents`` are intentionally typed as plain dicts — their shape is
validated against a *catalog* (see :mod:`clio_schemas.a2ui.validation`), not
by a closed pydantic union.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)

A2UI_PROTOCOL_VERSIONS = ("v0.9", "v0.9.1")
_ProtocolVersion = Literal["v0.9", "v0.9.1"]

#: RFC 3339 ``date-time`` (the vendored ``client_to_server.json``'s
#: ``action.timestamp`` declares ``"format": "date-time"``, not just any ISO
#: 8601 string — a bare date like ``"2026-01-01"`` is valid ISO 8601 but not
#: a valid RFC 3339 date-time, so ``datetime.fromisoformat`` alone is too
#: lenient).
_RFC3339_DATE_TIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$"
)


class _ServerOpBase(BaseModel):
    """Shared strict config for every server->client operation payload."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class CreateSurfacePayload(_ServerOpBase):
    """``createSurface``: begin rendering a new surface against one catalog."""

    surfaceId: str
    catalogId: str
    theme: dict[str, JsonValue] | None = None
    sendDataModel: bool | None = None


class UpdateComponentsPayload(_ServerOpBase):
    """``updateComponents``: replace a surface's component tree.

    Component shape is validated separately, against the surface's catalog
    (:func:`clio_schemas.a2ui.validation.catalog_validators`) — not here.
    """

    surfaceId: str
    components: list[dict[str, JsonValue]] = Field(min_length=1)


class UpdateDataModelPayload(_ServerOpBase):
    """``updateDataModel``: set or delete one path in a surface's data model.

    Per the vendored schema, an *omitted* ``value`` deletes the key at
    ``path``; a present ``value`` (including an explicit ``null``) replaces
    it. :attr:`value_provided` distinguishes the two cases.
    """

    surfaceId: str
    path: str | None = None
    value: Any = None

    @property
    def value_provided(self) -> bool:
        """True if ``value`` was present on the wire (vs. omitted -> delete).

        The default (``None``) is only a placeholder for the omitted case;
        presence is tracked via ``model_fields_set``, so an explicit
        ``value: null`` on the wire is still reported as provided.
        """

        return "value" in self.model_fields_set

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """Drop ``value`` from the dump when it was never set — wire-valid delete semantics.

        Without this, ``model_dump()``/``model_dump_json()`` would emit
        ``"value": null`` for an omitted value, which the wire schema reads
        as "replace with null", not "delete the key at path".
        """

        data = handler(self)
        if not self.value_provided:
            data.pop("value", None)
        return data


class DeleteSurfacePayload(_ServerOpBase):
    """``deleteSurface``: remove a previously created surface."""

    surfaceId: str


class A2UIServerMessage(BaseModel):
    """The server->client envelope: ``version`` plus exactly one operation."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    version: _ProtocolVersion
    createSurface: CreateSurfacePayload | None = None
    updateComponents: UpdateComponentsPayload | None = None
    updateDataModel: UpdateDataModelPayload | None = None
    deleteSurface: DeleteSurfacePayload | None = None

    _OP_FIELDS = ("createSurface", "updateComponents", "updateDataModel", "deleteSurface")

    @model_validator(mode="after")
    def _exactly_one_operation(self) -> A2UIServerMessage:
        ops = (self.createSurface, self.updateComponents, self.updateDataModel, self.deleteSurface)
        if sum(op is not None for op in ops) != 1:
            raise ValueError(
                "exactly one of createSurface/updateComponents/updateDataModel/"
                "deleteSurface is required"
            )
        return self

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """Emit only ``version`` and the one present operation key.

        Without this, ``model_dump()``/``model_dump_json()`` would emit the
        three absent operations as ``null``, which is not a valid
        ``server_to_client.json`` message (it declares ``additionalProperties:
        false`` with exactly one operation key required alongside ``version``).
        """

        data = handler(self)
        for key in self._OP_FIELDS:
            if data.get(key) is None:
                data.pop(key, None)
        return data


class A2UIClientAction(BaseModel):
    """A client-reported user action. ``name`` is any non-empty string.

    The vendored ``client_to_server.json`` does not forbid extra keys on the
    action object, so protocol extensions are tolerated (``extra="allow"``).
    """

    model_config = ConfigDict(extra="allow", strict=True, frozen=True)

    name: str = Field(min_length=1)
    surfaceId: str
    sourceComponentId: str
    timestamp: str
    context: dict[str, Any]

    @model_validator(mode="after")
    def _validate_timestamp(self) -> A2UIClientAction:
        if not _RFC3339_DATE_TIME.match(self.timestamp):
            raise ValueError(
                "timestamp must be an RFC 3339 date-time (e.g. 2026-01-01T00:00:00Z), "
                "not a bare date"
            )
        normalized = self.timestamp
        if normalized.endswith(("Z", "z")):
            normalized = normalized[:-1] + "+00:00"
        try:
            datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("timestamp must be a valid RFC 3339 date-time") from exc
        return self


class A2UIValidationError(BaseModel):
    """The client's ``VALIDATION_FAILED`` error report. Strict, closed shape."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    code: Literal["VALIDATION_FAILED"]
    surfaceId: str
    path: str
    message: str


class A2UIGenericError(BaseModel):
    """Any other client-reported error. Tolerates protocol extensions."""

    model_config = ConfigDict(extra="allow", strict=True, frozen=True)

    code: str
    surfaceId: str
    message: str

    @model_validator(mode="after")
    def _reject_validation_failed_code(self) -> A2UIGenericError:
        if self.code == "VALIDATION_FAILED":
            raise ValueError("code=VALIDATION_FAILED is reported via A2UIValidationError")
        return self


class A2UIClientMessage(BaseModel):
    """The client->server envelope: ``version`` plus exactly one of ``action``/``error``."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    version: _ProtocolVersion
    action: A2UIClientAction | None = None
    error: A2UIValidationError | A2UIGenericError | None = None

    @model_validator(mode="after")
    def _exactly_one_of_action_or_error(self) -> A2UIClientMessage:
        if (self.action is None) == (self.error is None):
            raise ValueError("exactly one of action or error is required")
        return self
