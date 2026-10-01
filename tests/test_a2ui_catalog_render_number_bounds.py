"""Unit tests for ``clio_schemas.a2ui.catalog_render``'s numeric-bound rendering.

G2 (#23, adversarial review F7): the original ``_number_bounds`` only
recognised ``Ge``/``Le`` (``ge=``/``le=``) ``annotated_types`` constraints,
so ``gt=``/``lt=``/``multiple_of=`` would have been silently dropped --
a numeric field would render as unbounded (``{"type": "number"}``) rather
than as a visibly wrong bound, exactly the kind of degradation the
no-silent-fallback rule forbids. These tests exercise every numeric
constraint directly, independent of whether any current catalog component
happens to declare ``gt``/``lt``/``multiple_of`` today (only ``Grid``'s
``columns``/``gap`` currently use ``ge``/``le``,
see ``test_grid_gap_and_columns_match_the_client_catalog_bounds``).
"""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import Field

from clio_schemas.a2ui.catalog_render import _number_bounds, render_type


def test_render_type_renders_inclusive_bounds() -> None:
    rendered = render_type(Annotated[int, Field(ge=1, le=12)], "value", {})
    assert rendered == {"type": "integer", "minimum": 1, "maximum": 12}


def test_render_type_renders_exclusive_bounds_and_multiple_of() -> None:
    rendered = render_type(Annotated[float, Field(gt=0, lt=100, multiple_of=0.5)], "value", {})
    assert rendered == {
        "type": "number",
        "exclusiveMinimum": 0,
        "exclusiveMaximum": 100,
        "multipleOf": 0.5,
    }


def test_render_type_renders_every_numeric_constraint_at_once() -> None:
    rendered = render_type(
        Annotated[float, Field(ge=1, gt=0, le=10, lt=11, multiple_of=0.5)],
        "value",
        {},
    )
    assert rendered == {
        "type": "number",
        "minimum": 1,
        "exclusiveMinimum": 0,
        "maximum": 10,
        "exclusiveMaximum": 11,
        "multipleOf": 0.5,
    }


def test_number_bounds_ignores_length_constraints_rendered_elsewhere() -> None:
    """``MinLen``/``MaxLen`` are `_list_bounds`'s job, not an unrecognised constraint."""

    field_info = Field(min_length=1, max_length=5)
    assert _number_bounds(field_info) == {}


def test_number_bounds_raises_on_an_unrecognised_constraint() -> None:
    """A future ``annotated_types`` constraint with no rendering rule must raise, not drop."""

    field_info = Field(ge=1)
    field_info.metadata.append(object())
    with pytest.raises(NotImplementedError):
        _number_bounds(field_info)
