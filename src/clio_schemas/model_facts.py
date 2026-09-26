"""Model facts: description, release date, recency, pricing and size, each with its evidence.

One :class:`ModelFacts` record carries the descriptive facts a model picker
filters with sliders and shows in an info popover (a router's description is
how a person learns what it routes between). It sits next to
:class:`~clio_schemas.model_capabilities.ModelCapabilityTags` on a catalog row.

Every fact is ``{"value", "evidence"}`` -- the evidence rows are the same
:class:`~clio_schemas.model_capabilities.TagEvidence` a capability tag
carries -- or ``null`` when no source states it. A reader shows nothing for a
``null`` fact and never guesses (in particular, never reads a size off a model's
name).

Slider-friendly by construction: every number a slider filters on is a plain
JSON number (``pricing.value.input.per_1m``, ``parameters.value.total``), and a
price that is not a number is a typed ``kind`` (``variable`` -- depends on the
routed model; ``subscription`` -- billed through a plan) with ``per_1m: null``,
never 0.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from clio_schemas.model_capabilities import TagEvidence, _ClosedRecord, _evidence

#: How precisely a source states a release date.
DatePrecision = Literal["day", "month", "year"]

#: One side of a price: a metered USD rate, a price that depends on the routed
#: model, or a subscription plan.
PriceKind = Literal["usd", "variable", "subscription"]

#: Whether a parameter count is the exact tensor total or a server's rounded
#: display size (e.g. Ollama ``details.parameter_size='7.6B'``).
CountPrecision = Literal["exact", "rounded"]


class DescriptionLink(_ClosedRecord):
    """One markdown link found in a description, kept as data."""

    text: str = Field(description="The link's label as it reads in the text.")
    url: str = Field(description="The link target exactly as the source wrote it.")


class DescriptionValue(_ClosedRecord):
    """A description in its raw form and as plain text for display."""

    text: str = Field(min_length=1, description="The source's text, verbatim.")
    plain: str = Field(description="The text with each markdown link reduced to its label.")
    links: list[DescriptionLink] = Field(
        default_factory=list, description="The links reduced out of `plain`, in order."
    )


class DescriptionFact(_ClosedRecord):
    """What the model is, in its source's words."""

    value: DescriptionValue
    evidence: list[TagEvidence] = _evidence()


class ReleaseDateValue(_ClosedRecord):
    """A release date at the precision its source states it."""

    date: str = Field(
        pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$",
        description="YYYY-MM-DD, YYYY-MM or YYYY, matching `precision`.",
    )
    precision: DatePrecision

    @model_validator(mode="after")
    def _date_matches_precision(self) -> ReleaseDateValue:
        parts = len(self.date.split("-"))
        expected = {"year": 1, "month": 2, "day": 3}[self.precision]
        if parts != expected:
            raise ValueError(f"date {self.date!r} does not have {self.precision} precision")
        return self


class ReleaseDateFact(_ClosedRecord):
    """When the model was released."""

    value: ReleaseDateValue
    evidence: list[TagEvidence] = _evidence()


class RecentFact(_ClosedRecord):
    """Whether the release is recent, derived by the server at serve time (never stored)."""

    value: bool = Field(description="The release falls within `window_months` of `as_of`.")
    window_months: int = Field(gt=0, description="The recency window, in calendar months.")
    as_of: str = Field(
        pattern=r"^\d{4}-\d{2}-\d{2}$", description="The day recency was judged against."
    )
    evidence: list[TagEvidence] = _evidence()


class Price(_ClosedRecord):
    """One side (input or output) of a price, per 1M tokens."""

    kind: PriceKind
    per_1m: float | None = Field(
        description="USD per 1M tokens for kind `usd`; null for `variable` and `subscription`."
    )

    @model_validator(mode="after")
    def _number_only_when_metered(self) -> Price:
        if self.kind == "usd" and (self.per_1m is None or self.per_1m < 0):
            raise ValueError("a usd price needs a non-negative per_1m")
        if self.kind != "usd" and self.per_1m is not None:
            raise ValueError(f"a {self.kind} price has no per_1m number")
        return self


class PricingValue(_ClosedRecord):
    """Input and output prices."""

    unit: Literal["usd_per_1m_tokens"]
    input: Price
    output: Price


class PricingAlternative(_ClosedRecord):
    """Another source's price that did not win (e.g. a catalog list price)."""

    value: PricingValue
    evidence: list[TagEvidence] = _evidence()


class PricingFact(_ClosedRecord):
    """What the model costs: the endpoint's own price first, a catalog list price otherwise."""

    value: PricingValue
    evidence: list[TagEvidence] = _evidence()
    alternatives: list[PricingAlternative] = Field(
        default_factory=list, description="Other sources' prices, each with its evidence."
    )


class ParametersValue(_ClosedRecord):
    """A model's size in parameters."""

    total: int | None = Field(gt=0, description="Every parameter: the slider value.")
    active: int | None = Field(
        gt=0, description="Parameters used per token (mixture-of-experts), when stated."
    )
    experts_total: int | None = Field(gt=0, description="Routed experts per MoE layer.")
    experts_active: int | None = Field(gt=0, description="Experts chosen per token.")
    precision: CountPrecision

    @model_validator(mode="after")
    def _states_something(self) -> ParametersValue:
        if all(
            value is None
            for value in (self.total, self.active, self.experts_total, self.experts_active)
        ):
            raise ValueError("a parameters value states at least one count")
        return self


class ParametersFact(_ClosedRecord):
    """How big the model is."""

    value: ParametersValue
    evidence: list[TagEvidence] = _evidence()


class ModelFacts(_ClosedRecord):
    """Descriptive facts about one model, each with its evidence; ``null`` = no source stated it."""

    model_key: str = Field(
        min_length=1,
        description="The model identity the facts describe (as in ModelCapabilityTags).",
    )
    description: DescriptionFact | None = Field(description="What the model is.")
    released_at: ReleaseDateFact | None = Field(description="When it was released.")
    recent: RecentFact | None = Field(description="Whether that release is recent.")
    pricing: PricingFact | None = Field(description="What it costs, per 1M tokens.")
    parameters: ParametersFact | None = Field(description="How many parameters it has.")

    @model_validator(mode="after")
    def _recent_needs_a_release(self) -> ModelFacts:
        if self.recent is not None and self.released_at is None:
            raise ValueError("recent is derived from released_at, which is absent")
        return self


__all__ = [
    "CountPrecision",
    "DatePrecision",
    "DescriptionFact",
    "DescriptionLink",
    "DescriptionValue",
    "ModelFacts",
    "ParametersFact",
    "ParametersValue",
    "Price",
    "PriceKind",
    "PricingAlternative",
    "PricingFact",
    "PricingValue",
    "RecentFact",
    "ReleaseDateFact",
    "ReleaseDateValue",
]
