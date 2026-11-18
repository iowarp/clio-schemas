"""clio.choice-table.v1: the pydantic model and the rendered catalog agree.

Every case is checked against both sides, so a surface is accepted or refused
the same way by the validator and the renderer's contract. Rules JSON Schema
cannot express (unique ids, value keys naming declared columns) are model-only.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from clio_schemas.a2ui.catalog_export import render_workspace_catalog
from clio_schemas.a2ui.v0_9_1.bounded_components import COMPONENT_MODELS
from clio_schemas.a2ui.v0_9_1.choice_components import (
    CHOICE_ICONS,
    MAX_CHOICE_COLUMNS,
    MAX_CHOICE_ROWS,
    ChoiceTableComponent,
)
from clio_schemas.a2ui.validation import catalog_validators

VALIDATORS = catalog_validators(render_workspace_catalog())
CHOOSE = {"event": {"name": "choose", "context": {"token": "t1"}}}
ACCESS = {
    "id": "access",
    "title": "Access",
    "help": "Who may use it.",
    "options": [
        {"value": "open", "label": "Open", "icon": "lockOpen", "tone": "warning"},
        {
            "value": "locked",
            "label": "Locked",
            "description": "Needs a key.",
            "icon": "verifiedUser",
            "tone": "positive",
        },
    ],
}
PROTOCOL = {
    "id": "protocol",
    "title": "Protocol",
    "editable": False,
    "options": [
        {"value": "ssh", "label": "SSH", "icon": "terminal"},
        {"value": "https", "label": "HTTPS", "icon": "public"},
    ],
}
ROW = {
    "id": "a",
    "title": "Alpha",
    "subtitle": "alpha.example",
    "icon": "dns",
    "values": {"access": "locked", "protocol": "ssh"},
    "inherited": ["access"],
    "context": {"kind": "endpoint"},
    "menu": [{"id": "rm", "label": "Remove", "destructive": True, "action": CHOOSE}],
}


def _table(**extra: Any) -> dict[str, Any]:
    return {
        "id": "c",
        "component": "clio.choice-table.v1",
        "label": "Endpoints",
        "columns": [ACCESS, PROTOCOL],
        "rows": [ROW],
        **extra,
    }


CASES = [
    pytest.param(_table(), True, id="minimal-inline"),
    pytest.param(
        _table(
            defaults={"title": "Defaults", "values": {"access": "open"}, "context": {"d": 1}},
            onChoose=CHOOSE,
            rowMenu=[{"id": "edit", "label": "Edit", "action": CHOOSE}],
            add={"label": "Add endpoint", "action": CHOOSE},
            empty="No endpoints yet.",
            accessibility={"label": "Endpoint settings"},
            weight=1,
        ),
        True,
        id="everything",
    ),
    pytest.param(_table(rows=[]), True, id="no-rows"),
    pytest.param(_table(rows={"path": "/endpoints"}), True, id="bound-rows"),
    pytest.param(_table(rows=None), False, id="null-rows"),
    pytest.param({k: v for k, v in _table().items() if k != "rows"}, False, id="missing-rows"),
    pytest.param(_table(rows={"path": "/e", "extra": 1}), False, id="bad-binding"),
    pytest.param(_table(columns=[]), False, id="no-columns"),
    pytest.param(
        _table(columns=[{**ACCESS, "id": f"c{i}"} for i in range(MAX_CHOICE_COLUMNS + 1)]),
        False,
        id="too-many-columns",
    ),
    pytest.param(_table(columns=[{**ACCESS, "options": []}]), False, id="no-options"),
    pytest.param(
        _table(
            columns=[{**ACCESS, "options": [{"value": "x", "label": "X", "icon": "lock-open"}]}]
        ),
        False,
        id="kebab-icon",
    ),
    pytest.param(
        _table(columns=[{**ACCESS, "options": [{"value": "x", "label": "X", "tone": "loud"}]}]),
        False,
        id="unknown-tone",
    ),
    pytest.param(_table(rows=[{**ROW, "values": {"access": 1}}]), False, id="non-string-value"),
    pytest.param(_table(rows=[{**ROW, "bogus": True}]), False, id="unknown-row-key"),
    pytest.param(_table(label=""), False, id="empty-label"),
    pytest.param(_table(defaults={"values": {}}), False, id="defaults-without-title"),
    pytest.param(_table(add={"label": "Add"}), False, id="add-without-action"),
    pytest.param(
        _table(rowMenu=[{"id": f"m{i}", "label": "M", "action": CHOOSE} for i in range(9)]),
        False,
        id="menu-too-long",
    ),
    pytest.param(_table(rows=[ROW] * (MAX_CHOICE_ROWS + 1)), False, id="too-many-rows"),
    pytest.param(_table(onChoose="choose"), False, id="string-action"),
]


@pytest.mark.parametrize(("payload", "valid"), CASES)
def test_schema_and_model_agree(payload: dict[str, Any], valid: bool) -> None:  # noqa: FBT001
    assert VALIDATORS["clio.choice-table.v1"].is_valid(payload) == valid
    if valid:
        ChoiceTableComponent.model_validate(payload)
    else:
        with pytest.raises(ValidationError):
            ChoiceTableComponent.model_validate(payload)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (_table(columns=[ACCESS, ACCESS]), "column ids"),
        (_table(rows=[ROW, ROW]), "row ids"),
        (_table(rows=[{**ROW, "values": {"speed": "fast"}}]), "speed"),
        (_table(rows=[{**ROW, "inherited": ["speed"]}]), "speed"),
        (_table(defaults={"title": "D", "values": {"speed": "fast"}}), "speed"),
        (
            _table(columns=[{**ACCESS, "options": ACCESS["options"] * 2}]),
            "option values must be unique",
        ),
    ],
)
def test_model_only_cross_rules(payload: dict[str, Any], match: str) -> None:
    assert VALIDATORS["clio.choice-table.v1"].is_valid(payload)
    with pytest.raises(ValidationError, match=match):
        ChoiceTableComponent.model_validate(payload)


def test_bound_rows_skip_the_column_check() -> None:
    model = ChoiceTableComponent.model_validate(
        _table(rows={"path": "/e"}, defaults={"title": "D", "values": {"access": "open"}})
    )
    assert model.rows.path == "/e"  # type: ignore[union-attr]


def test_registered_with_one_icon_vocabulary() -> None:
    catalog = render_workspace_catalog()
    assert ChoiceTableComponent in COMPONENT_MODELS
    assert "clio.choice-table.v1" in catalog["components"]
    assert catalog["$defs"]["ChoiceIcon"]["enum"] == list(CHOICE_ICONS)
    assert len(set(CHOICE_ICONS)) == len(CHOICE_ICONS) == 76
