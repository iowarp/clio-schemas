"""Accepted parameters: the request settings one model accepts, each with its evidence.

A catalog row carries ``accepted_parameters: list[AcceptedParameter]`` -- ONLY
the user-tunable request settings (temperature, top_p, top_k, min_p, penalties,
seed, output length, a local server's context size, ...) that the model and
its endpoint actually accept. A setting no source states the model accepts is
simply absent: a settings form renders a control for each row and nothing
else, so an empty list means "no response settings".

Each row says how to draw its control (``kind`` plus ``minimum``/``maximum``/
``step`` or ``options``), where it belongs (``group``) and what applies when
nothing is set (``default``: a stated value, or ``null`` for the provider's own
default). ``evidence`` names every source behind the row: the one that states
the endpoint accepts the setting, the one behind its range, and the one behind
its default.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from clio_schemas.model_capabilities import TagEvidence, _ClosedRecord, _evidence

#: How a setting's value is entered: a real number, a whole number, or one of
#: a fixed set of options.
ParameterKind = Literal["number", "integer", "enum"]

#: Where a setting sits in a settings form: how tokens are sampled, how long
#: the model reads and writes, or everything else.
ParameterGroup = Literal["sampling", "length", "advanced"]


class AcceptedParameter(_ClosedRecord):
    """One request setting the model accepts, how to enter it, and who says so."""

    name: str = Field(
        pattern=r"^[a-z][a-z0-9_]*$",
        description=(
            "The setting's key as the server stores it (e.g. `temperature`, "
            "`max_tokens`, `context_length`)."
        ),
    )
    label: str = Field(min_length=1, description="The setting's name for display.")
    description: str = Field(description="One sentence on what the setting changes.")
    group: ParameterGroup
    kind: ParameterKind
    minimum: float | None = Field(description="Smallest accepted value; null when unbounded.")
    maximum: float | None = Field(description="Largest accepted value; null when unbounded.")
    step: float | None = Field(
        gt=0, description="A sensible increment for the control; null for an enum."
    )
    options: list[str] = Field(
        default_factory=list, description="The accepted values of an enum; empty otherwise."
    )
    default: float | str | None = Field(
        description=(
            "The value that applies when nothing is set, when a source states one; "
            "null means the provider's own default."
        )
    )
    evidence: list[TagEvidence] = _evidence()

    @model_validator(mode="after")
    def _shape_matches_kind(self) -> AcceptedParameter:
        if self.kind == "enum":
            if not self.options:
                raise ValueError("an enum parameter lists its options")
            if self.minimum is not None or self.maximum is not None or self.step is not None:
                raise ValueError("an enum parameter has no minimum, maximum or step")
            if self.default is not None and self.default not in self.options:
                raise ValueError(f"default {self.default!r} is not one of the options")
            return self
        if self.options:
            raise ValueError(f"a {self.kind} parameter has no options")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum is greater than maximum")
        if self.default is None:
            return self
        if isinstance(self.default, str):
            raise ValueError(f"a {self.kind} parameter's default is a number")
        if self.kind == "integer" and not float(self.default).is_integer():
            raise ValueError("an integer parameter's default is a whole number")
        if self.minimum is not None and self.default < self.minimum:
            raise ValueError("default is below the minimum")
        if self.maximum is not None and self.default > self.maximum:
            raise ValueError("default is above the maximum")
        return self


__all__ = ["AcceptedParameter", "ParameterGroup", "ParameterKind"]
