"""The workspace catalog runs no regular expression the model chooses.

A regex in a ``checks`` condition runs in the renderer when the component mounts, so a
catastrophic pattern blocks the page; ``TextField.validationRegexp`` runs on its value.
"""

from __future__ import annotations

from typing import Any

import pytest

from clio_schemas.a2ui.catalog_export import render_workspace_catalog
from clio_schemas.a2ui.validation import catalog_validators


@pytest.fixture(scope="module")
def validators() -> dict[str, Any]:
    return catalog_validators(render_workspace_catalog())


def _button(condition: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "b",
        "component": "Button",
        "child": "t",
        "action": {"event": {"name": "go"}},
        "checks": [{"condition": condition, "message": "m"}],
    }


def test_a_regex_check_is_refused(validators: dict[str, Any]) -> None:
    regex = {"call": "regex", "args": {"value": "aaaa!", "pattern": "^(a+)+$"}}
    assert "regex" not in render_workspace_catalog()["functions"]
    assert not validators["Button"].is_valid(_button(regex))
    # The other checks stay.
    required = {"call": "required", "args": {"value": "x"}}
    assert validators["Button"].is_valid(_button(required))


def test_a_text_field_takes_no_regex(validators: dict[str, Any]) -> None:
    field = {"id": "f", "component": "TextField", "label": "Phone"}
    assert validators["TextField"].is_valid(field)
    assert not validators["TextField"].is_valid({**field, "validationRegexp": "^(a+)+$"})
