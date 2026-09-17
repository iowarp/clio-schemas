"""The CLIO catalog sidecar — packaging metadata that never appears on the wire.

A catalog FILE (``catalog.json``) is the official A2UI protocol shape — it is
sent to clients and is byte-for-byte what the protocol defines. The sidecar
(``catalog.clio.json``) sits *beside* it and carries CLIO's own packaging
concerns: which kernel renders each component, which client actions route to
a permission gate or a run controller instead of the plain agent event lane,
and where to find producer instructions. It is version-neutral (the
``protocolVersion`` field records which A2UI version the paired catalog
targets, but the sidecar's own shape does not change with the protocol).
"""

from __future__ import annotations

import json
import string
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Trust(BaseModel):
    """Where a catalog came from, for permission/provenance gating."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    source: Literal["builtin", "pack"]


class _Implementation(BaseModel):
    """Which renderer kernel implements one catalog component."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    kernel: str
    presets: dict[str, str] | None = None


class _EventRoute(BaseModel):
    """Where one client action name routes, beyond the default agent lane."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    destination: Literal["agent", "permission", "run"] = "agent"
    context_schema: dict[str, object] | None = None
    operation: Literal["cancel", "retry"] | None = None
    # Human-readable template describing WHAT this event means, rendered against
    # the resolved action context via `render_narration` below (A2UI 1.0's
    # `userMessage`, carried early as declared sidecar data — clio-agent#1363).
    # Free-form when no `context_schema` is declared; otherwise every
    # `{placeholder}` must name a declared context field (checked below).
    narration: str | None = None

    @model_validator(mode="after")
    def _check_narration_placeholders(self) -> _EventRoute:
        """``narration``'s placeholders must be declared ``context_schema`` fields.

        Without a declared ``context_schema`` the event's context shape is
        unconstrained, so ``narration`` may reference anything — the author
        is trusted. With one declared, an undeclared placeholder is almost
        certainly a typo that would silently render literal (never raise, by
        :func:`render_narration`'s contract) instead of the intended value,
        so it is caught here instead, at authoring time.
        """

        if self.narration is None or self.context_schema is None:
            return self
        properties = self.context_schema.get("properties")
        allowed = set(properties) if isinstance(properties, dict) else set()
        used = {
            field_name.split(".", 1)[0].split("[", 1)[0]
            for _, field_name, _, _ in string.Formatter().parse(self.narration)
            if field_name
        }
        unknown = sorted(used - allowed)
        if unknown:
            raise ValueError(
                f"narration references undeclared context field(s) {unknown!r}; "
                f"context_schema.properties only declares {sorted(allowed)!r}"
            )
        return self


class CatalogSidecar(BaseModel):
    """CLIO packaging metadata for one catalog. Never sent on the A2UI wire."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    catalogId: str
    protocolVersion: Literal["0.9.1"]
    trust: _Trust
    implements: dict[str, _Implementation] = Field(default_factory=dict)
    events: dict[str, _EventRoute] = Field(default_factory=dict)
    instructions: str = "instructions.md"

    @model_validator(mode="after")
    def _check_run_operation(self) -> CatalogSidecar:
        """``operation`` is required for ``run``-destination events, forbidden otherwise.

        The constraint spans two sibling fields of ``_EventRoute``
        (``destination`` and ``operation``), so it can only be checked here,
        where each event's name is still available for the error message —
        ``_EventRoute`` itself never sees its own dict key.
        """

        for name, route in self.events.items():
            if route.destination == "run" and route.operation is None:
                raise ValueError(
                    f"event {name!r} routes to 'run' and must declare an "
                    "'operation' ('cancel' or 'retry')"
                )
            if route.destination != "run" and route.operation is not None:
                raise ValueError(
                    f"event {name!r} routes to {route.destination!r}, not 'run' — "
                    "'operation' must be omitted"
                )
        return self


class _NarrationValues(dict):  # type: ignore[type-arg]
    """``str.format_map`` mapping for :func:`render_narration`.

    An unresolved placeholder is left literal instead of raising — the
    dispatcher renders narration best-effort, it never blocks delivery of the
    underlying event on a template/context mismatch. A ``list``/``dict``
    value is rendered as compact JSON so e.g. ``"{stationIds}"`` against
    ``{"stationIds": ["MTA1", "PKRD"]}`` renders ``["MTA1","PKRD"]`` rather
    than Python's ``repr``.
    """

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_narration(route: _EventRoute, context: Mapping[str, object]) -> str | None:
    """Render ``route.narration`` against the resolved action ``context``.

    Returns ``None`` when the route declares no ``narration``. Never raises:
    an unresolved placeholder is left literal (see :class:`_NarrationValues`).

    Args:
        route: The event's sidecar route (``CatalogSidecar.events[name]``).
        context: The resolved action context — the same mapping the plain
            "event name + context" narration was built from.

    Returns:
        The rendered narration string, or ``None`` if ``route.narration`` is
        unset.
    """

    if route.narration is None:
        return None

    def _render(value: object) -> object:
        if isinstance(value, (list, dict)):
            return json.dumps(value, separators=(",", ":"))
        return value

    values = _NarrationValues((key, _render(value)) for key, value in context.items())
    return route.narration.format_map(values)
