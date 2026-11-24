"""clio.dialog.v1 and clio.picker.v1: the pydantic models and the rendered catalog agree.

Every case is checked against both sides, so a surface is accepted or refused
the same way by the validator and the renderer's contract. Rules JSON Schema
cannot express (unique tab ids, rail tabs naming declared tabs, a choice-table
row's options naming that column's values) are model-only. The relay cases are
shaped as clio-relay's Compute page builds them, so the kernel never refuses
the page its pack catalog accepts.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from clio_schemas.a2ui.catalog_export import (
    _load_basic_catalog,
    render_workspace_catalog,
    render_workspace_sidecar,
)
from clio_schemas.a2ui.v0_9_1.bounded_components import COMPONENT_MODELS
from clio_schemas.a2ui.v0_9_1.choice_components import ChoiceTableComponent
from clio_schemas.a2ui.v0_9_1.dialog_components import (
    MAX_DIALOG_TABS,
    MAX_PICKER_CHIPS,
    MAX_PICKER_ITEMS,
    DialogComponent,
    PickerComponent,
)
from clio_schemas.a2ui.validation import catalog_validators, message_validator

CATALOG = render_workspace_catalog()
VALIDATORS = catalog_validators(CATALOG)
MODELS: dict[str, type[BaseModel]] = {
    m.model_fields["component"].default: m for m in COMPONENT_MODELS
}
ACT = {"event": {"name": "act", "context": {"token": "t1", "values": {"path": "/add"}}}}
OPEN_URL = {"functionCall": {"call": "openUrl", "args": {"url": "https://example.org/login"}}}
#: Every component clio-relay's pack catalog (``clio-relay-compute/v1``) maps to
#: the kernel component of the same name.
RELAY_PACK_COMPONENTS = (
    "Text",
    "Row",
    "Column",
    "Card",
    "Tabs",
    "Divider",
    "Button",
    "Icon",
    "TextField",
    "CheckBox",
    "ChoicePicker",
    "clio.choice-table.v1",
    "clio.dialog.v1",
    "clio.picker.v1",
)
TABS = [
    {"id": "catalog", "title": "Catalog", "icon": "book", "child": "catalog"},
    {"id": "saved", "title": "Saved", "icon": "bookmark", "child": "saved"},
    {"id": "own", "title": "Your own", "icon": "link", "child": "own"},
]


def _dialog(**extra: Any) -> dict[str, Any]:
    return {
        "id": "d",
        "component": "clio.dialog.v1",
        "title": "Add endpoint",
        "open": {"path": "/dialogs/add"},
        **extra,
    }


def _picker(**extra: Any) -> dict[str, Any]:
    return {
        "id": "p",
        "component": "clio.picker.v1",
        "label": "Site",
        "value": {"path": "/add/site"},
        "items": [{"value": "alpha", "title": "Alpha"}],
        **extra,
    }


ADD_TABBED = _dialog(
    description="Pick a site, then how relay reaches it. Test it, then save it.",
    trigger="add-open",
    tabs=TABS,
    activeTab={"path": "/add/tab"},
    rail={"steps": ["Site", "Protocol", "Test", "Save"], "step": 0, "tabs": ["catalog"]},
    test={"label": "Test", "action": ACT},
    cancel={"label": "Cancel"},
    confirm={"label": "Save endpoint", "action": ACT, "enabled": False},
    onClose={"event": {"name": "close", "context": {"token": "t2"}}},
)
ADD_TESTING = _dialog(
    content="add-test",
    rail={"steps": ["Site", "Protocol", "Test", "Save"], "step": 3},
    status={
        "tone": "warning",
        "text": "Needs your sign-in",
        "detail": "The token expired.",
        "action": {"label": "Sign in", "action": OPEN_URL},
    },
    test={"label": "Test again", "action": ACT, "enabled": True, "keyboard": "Ctrl+Shift+Enter"},
    cancel={"label": "Back", "action": ACT},
    confirm={"label": "Save endpoint", "action": ACT, "enabled": True, "tone": "default"},
)
DEFAULTS = _dialog(
    title="Defaults for new endpoints",
    open={"path": "/dialogs/defaults"},
    trigger="defaults-open",
    content="defaults-body",
    width="narrow",
    cancel={"label": "Cancel"},
    confirm={"label": "Save", "action": ACT},
    status={"tone": "negative", "text": "Could not save."},
    accessibility={"label": "Defaults"},
    weight=1,
)
SITES = _picker(
    search="Search sites",
    limit=4,
    empty="No sites match",
    error="Pick a site.",
    items=[
        {"value": "alpha", "title": "Alpha", "subtitle": "A cluster", "chips": ["SSH", "Globus"]},
        {"value": "beta", "title": "Beta", "subtitle": "", "meta": "Suggested"},
    ],
    onPick=ACT,
)
SAVED = _picker(
    label="Computer",
    value={"path": "/add/saved"},
    items=[
        {"value": "clio:a", "title": "a", "chips": ["SSH"], "group": "Saved SSH hosts"},
        {"value": "ssh:b", "title": "b", "subtitle": "me@b", "group": "From ~/.ssh/config"},
    ],
    onPick=ACT,
)
SELECT = _picker(label="Protocol", variant="select", hint="SSH or Globus", onPick=ACT)

DIALOG_CASES = [
    pytest.param(_dialog(), True, id="minimal"),
    pytest.param(ADD_TABBED, True, id="relay-add-tabbed"),
    pytest.param(ADD_TESTING, True, id="relay-add-testing"),
    pytest.param(DEFAULTS, True, id="relay-defaults"),
    pytest.param(_dialog(status={"tone": "busy", "text": "Testing"}), True, id="busy-status"),
    pytest.param({k: v for k, v in _dialog().items() if k != "open"}, False, id="missing-open"),
    pytest.param(_dialog(open=True), False, id="literal-open"),
    pytest.param(_dialog(title=""), False, id="empty-title"),
    pytest.param(_dialog(tabs=[]), False, id="no-tabs"),
    pytest.param(
        _dialog(tabs=[{**TABS[0], "id": f"t{i}"} for i in range(MAX_DIALOG_TABS + 1)]),
        False,
        id="too-many-tabs",
    ),
    pytest.param(_dialog(tabs=[{"id": "t", "title": "T"}]), False, id="tab-without-child"),
    pytest.param(_dialog(tabs=[{**TABS[0], "child": 3}]), False, id="numeric-child"),
    pytest.param(_dialog(rail={"steps": ["Only"], "step": 0}), False, id="one-step"),
    pytest.param(_dialog(rail={"steps": ["A", "B"], "step": -1}), False, id="negative-step"),
    pytest.param(_dialog(status={"tone": "loud", "text": "x"}), False, id="unknown-tone"),
    pytest.param(_dialog(confirm={"label": "Save"}), False, id="confirm-without-action"),
    pytest.param(
        _dialog(confirm={"label": "Save", "action": ACT, "tone": "loud"}),
        False,
        id="unknown-confirm-tone",
    ),
    pytest.param(_dialog(cancel={"action": ACT}), False, id="cancel-without-label"),
    pytest.param(_dialog(width="wide"), False, id="unknown-width"),
    pytest.param(_dialog(bogus=True), False, id="unknown-key"),
]

PICKER_CASES = [
    pytest.param(_picker(), True, id="minimal"),
    pytest.param(_picker(items=[]), True, id="no-items"),
    pytest.param(SITES, True, id="relay-sites"),
    pytest.param(SAVED, True, id="relay-saved"),
    pytest.param(SELECT, True, id="relay-select"),
    pytest.param({k: v for k, v in _picker().items() if k != "value"}, False, id="missing-value"),
    pytest.param({k: v for k, v in _picker().items() if k != "items"}, False, id="missing-items"),
    pytest.param(_picker(value="alpha"), False, id="literal-value"),
    pytest.param(_picker(label=""), False, id="empty-label"),
    pytest.param(_picker(items=[{"value": "", "title": "X"}]), False, id="empty-item-value"),
    pytest.param(_picker(items=[{"value": "x"}]), False, id="item-without-title"),
    pytest.param(
        _picker(items=[{"value": "x", "title": "X", "chips": ["c"] * (MAX_PICKER_CHIPS + 1)}]),
        False,
        id="too-many-chips",
    ),
    pytest.param(
        _picker(items=[{"value": f"v{i}", "title": "V"} for i in range(MAX_PICKER_ITEMS + 1)]),
        False,
        id="too-many-items",
    ),
    pytest.param(_picker(limit=0), False, id="zero-limit"),
    pytest.param(_picker(variant="grid"), False, id="unknown-variant"),
    pytest.param(_picker(onPick="pick"), False, id="string-action"),
]


def _check(payload: dict[str, Any], valid: bool) -> None:  # noqa: FBT001
    name = payload["component"]
    assert VALIDATORS[name].is_valid(payload) == valid
    if valid:
        MODELS[name].model_validate(payload)
    else:
        with pytest.raises(ValidationError):
            MODELS[name].model_validate(payload)


@pytest.mark.parametrize(("payload", "valid"), DIALOG_CASES)
def test_dialog_schema_and_model_agree(payload: dict[str, Any], valid: bool) -> None:  # noqa: FBT001
    _check(payload, valid)


@pytest.mark.parametrize(("payload", "valid"), PICKER_CASES)
def test_picker_schema_and_model_agree(payload: dict[str, Any], valid: bool) -> None:  # noqa: FBT001
    _check(payload, valid)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (_dialog(tabs=[TABS[0], TABS[0]]), "tab ids"),
        (_dialog(tabs=TABS, rail={"steps": ["A", "B"], "step": 0, "tabs": ["x"]}), "x"),
        (_dialog(rail={"steps": ["A", "B"], "step": 0, "tabs": ["catalog"]}), "catalog"),
    ],
)
def test_dialog_model_only_rules(payload: dict[str, Any], match: str) -> None:
    assert VALIDATORS["clio.dialog.v1"].is_valid(payload)
    with pytest.raises(ValidationError, match=match):
        DialogComponent.model_validate(payload)


PROTOCOL = {
    "id": "protocol",
    "title": "Protocol",
    "help": "How relay reaches the endpoint.",
    "options": [
        {"value": "ssh", "label": "SSH", "icon": "terminal"},
        {"value": "globus", "label": "Globus", "icon": "public"},
    ],
}
SECURITY = {
    "id": "security",
    "title": "Security",
    "options": [
        {"value": "guarded", "label": "Guarded", "icon": "lock", "tone": "positive"},
        {"value": "open", "label": "Open", "icon": "lockOpen", "tone": "warning"},
    ],
}
RELAY_ROW = {
    "id": "alpha",
    "title": "Alpha",
    "subtitle": "alpha.example",
    "caption": "The last test found it ready",
    "error": "Could not save.",
    "values": {"protocol": "ssh", "security": "guarded"},
    "options": {"protocol": ["ssh"]},
    "inherited": ["security"],
    "context": {"token": "t3"},
    "menu": [
        {"id": "test", "label": "Test", "action": ACT},
        {"id": "remove", "label": "Remove", "destructive": True, "action": ACT},
    ],
}


def _table(*rows: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "id": "endpoints",
        "component": "clio.choice-table.v1",
        "label": "Endpoints",
        "columns": [PROTOCOL, SECURITY],
        "rows": list(rows),
        "onChoose": {"event": {"name": "set", "context": {}}},
        "empty": "No endpoints yet",
        **extra,
    }


@pytest.mark.parametrize(
    ("payload", "valid"),
    [
        pytest.param(_table(RELAY_ROW), True, id="relay-row"),
        pytest.param(_table(), True, id="relay-no-rows"),
        pytest.param(_table({**RELAY_ROW, "options": {}}), True, id="empty-options"),
        pytest.param(_table({**RELAY_ROW, "options": {"protocol": []}}), True, id="no-offer"),
        pytest.param(
            _table({**RELAY_ROW, "options": {"protocol": "ssh"}}), False, id="options-not-list"
        ),
        pytest.param(
            _table({**RELAY_ROW, "options": {"protocol": [""]}}), False, id="empty-option-value"
        ),
    ],
)
def test_choice_table_row_options(payload: dict[str, Any], valid: bool) -> None:  # noqa: FBT001
    _check(payload, valid)


@pytest.mark.parametrize(
    ("row", "match"),
    [
        ({**RELAY_ROW, "options": {"speed": ["fast"]}}, "speed"),
        ({**RELAY_ROW, "options": {"protocol": ["ssh", "tapis"]}}, "tapis"),
    ],
)
def test_choice_table_row_options_name_declared_values(row: dict[str, Any], match: str) -> None:
    payload = _table(row)
    assert VALIDATORS["clio.choice-table.v1"].is_valid(payload)
    with pytest.raises(ValidationError, match=match):
        ChoiceTableComponent.model_validate(payload)


def test_every_relay_pack_component_is_a_kernel_component() -> None:
    kernel = set(CATALOG["components"]) | set(_load_basic_catalog()["components"])
    assert not [name for name in RELAY_PACK_COMPONENTS if name not in kernel]
    implements = render_workspace_sidecar()["implements"]
    for name in ("clio.choice-table.v1", "clio.dialog.v1", "clio.picker.v1"):
        assert implements[name] == {"kernel": name}
        assert MODELS[name] in (ChoiceTableComponent, DialogComponent, PickerComponent)


def test_relay_compute_page_validates_as_one_message() -> None:
    """The page as relay sends it: a trigger, dialogs with pickers, and the table."""

    text = {"component": "Text", "variant": "body"}
    components = [
        {"id": "root", "component": "Column", "children": ["page-head", "endpoints"]},
        {"id": "page-head", "component": "Row", "children": ["add-open", "defaults-open"]},
        {"id": "add-open-text", **text, "text": "Add endpoint"},
        {"id": "add-open", "component": "Button", "child": "add-open-text", "action": ACT},
        {"id": "defaults-open-icon", "component": "Icon", "name": "settings"},
        {
            "id": "defaults-open",
            "component": "Button",
            "child": "defaults-open-icon",
            "action": ACT,
            "variant": "borderless",
            "accessibility": {"label": "Defaults for new endpoints"},
        },
        {**ADD_TABBED, "id": "add-dialog"},
        {"id": "catalog", "component": "Column", "children": ["add-site"]},
        {**SITES, "id": "add-site"},
        {"id": "saved", "component": "Column", "children": ["add-saved-list"]},
        {**SAVED, "id": "add-saved-list"},
        {"id": "own", "component": "Column", "children": ["add-own-protocol"]},
        {**SELECT, "id": "add-own-protocol"},
        {**DEFAULTS, "id": "defaults-dialog"},
        {"id": "defaults-body", "component": "Column", "children": []},
        _table(RELAY_ROW),
    ]
    message = {
        "version": "v0.9.1",
        "updateComponents": {"surfaceId": "relay-sites", "components": components},
    }
    message_validator("server_to_client.json", catalog=CATALOG).validate(message)
    for component in components:
        MODELS[component["component"]].model_validate(component)


def test_registered_with_their_defs() -> None:
    assert DialogComponent in COMPONENT_MODELS
    assert PickerComponent in COMPONENT_MODELS
    assert {"clio.dialog.v1", "clio.picker.v1"} <= set(CATALOG["components"])
    assert {"DialogTab", "PickerItem"} <= set(CATALOG["$defs"])
