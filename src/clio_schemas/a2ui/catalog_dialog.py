"""Catalog definitions for the dialog frame and the picker.

Hand-authored JSON Schema mirroring ``DialogComponent`` and ``PickerComponent``
(``a2ui/v0_9_1/dialog_components.py``): ``clio.dialog.v1`` with its trigger,
tabs or body, step rail, status line and footer, and ``clio.picker.v1`` with
its items. A dialog's trigger, body and tab children are component ids. The
rules JSON Schema cannot express (unique tab ids, rail tabs naming declared
tabs) live on the model. Kept out of ``catalog_bounded.py`` so that module does
not grow.
"""

from __future__ import annotations

from typing import Any

from clio_schemas.a2ui.catalog_render import COMMON_TYPES_ID
from clio_schemas.a2ui.v0_9_1.dialog_components import (
    DIALOG_CONFIRM_TONES,
    DIALOG_STATUS_TONES,
    DIALOG_WIDTHS,
    MAX_DIALOG_STEPS,
    MAX_DIALOG_TABS,
    MAX_PICKER_CHIPS,
    MAX_PICKER_ITEMS,
    MIN_DIALOG_STEPS,
    PICKER_VARIANTS,
)

_ACTION = {"$ref": f"{COMMON_TYPES_ID}#/$defs/Action"}
_BINDING = {"$ref": f"{COMMON_TYPES_ID}#/$defs/DataBinding"}
_CHILD = {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentId"}
_NAME = {"type": "string", "minLength": 1}
_TEXT = {"type": "string"}
_COMMON = [
    {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
    {"$ref": "#/$defs/CatalogComponentCommon"},
]


def _button(**extra: Any) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"label": _NAME, "action": _ACTION, "enabled": {"type": "boolean"}, **extra},
        "required": ["label", "action"],
        "additionalProperties": False,
    }


_TAB_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": _NAME,
        "title": _NAME,
        "icon": {**_TEXT, "description": "An icon name. Narrow dialogs show only the icons."},
        "child": {**_CHILD, "description": "The component the tab shows."},
    },
    "required": ["id", "title", "child"],
    "additionalProperties": False,
}

_DIALOG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "A trigger drawn in the page that opens a modal dialog with optional tabs, a step rail, "
        "a status line and a footer of Test, Cancel and confirm."
    ),
    "allOf": [
        *_COMMON,
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.dialog.v1"},
                "title": _NAME,
                "description": _TEXT,
                "open": {
                    **_BINDING,
                    "description": (
                        "A boolean; the dialog is open while it is true. The client sets it when "
                        "the trigger is pressed and clears it on close."
                    ),
                },
                "trigger": {
                    **_CHILD,
                    "description": (
                        "Drawn in place; pressing it opens the dialog and fires its own action."
                    ),
                },
                "content": {**_CHILD, "description": "The body, when the dialog has no tabs."},
                "tabs": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_DIALOG_TABS,
                    "items": {"$ref": "#/$defs/DialogTab"},
                },
                "activeTab": {**_BINDING, "description": "The id of the tab shown."},
                "rail": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "minItems": MIN_DIALOG_STEPS,
                            "maxItems": MAX_DIALOG_STEPS,
                            "items": _NAME,
                        },
                        "step": {"type": "integer", "minimum": 0},
                        "tabs": {
                            "type": "array",
                            "items": _NAME,
                            "description": "The tabs the rail shows on; every tab when absent.",
                        },
                    },
                    "required": ["steps", "step"],
                    "additionalProperties": False,
                    "description": "The numbered steps the dialog walks through.",
                },
                "status": {
                    "type": "object",
                    "properties": {
                        "tone": {"type": "string", "enum": list(DIALOG_STATUS_TONES)},
                        "text": _NAME,
                        "detail": _TEXT,
                        "action": _button(),
                    },
                    "required": ["tone", "text"],
                    "additionalProperties": False,
                    "description": "A line above the footer: a test's result or progress.",
                },
                "test": {
                    **_button(keyboard=_TEXT),
                    "description": "At the footer's start. Ctrl+Shift+Enter presses it.",
                },
                "cancel": {
                    "type": "object",
                    "properties": {"label": _NAME, "action": _ACTION},
                    "required": ["label"],
                    "additionalProperties": False,
                    "description": (
                        "With an action it fires the action; without, it closes the dialog and "
                        "fires onClose."
                    ),
                },
                "confirm": {
                    **_button(tone={"type": "string", "enum": list(DIALOG_CONFIRM_TONES)}),
                    "description": "The main button. Ctrl+Enter presses it.",
                },
                "onClose": {
                    **_ACTION,
                    "description": (
                        "Fired when the person closes the dialog: Escape, the close button, or a "
                        "cancel without an action."
                    ),
                },
                "width": {
                    "type": "string",
                    "enum": list(DIALOG_WIDTHS),
                    "description": (
                        "narrow for a short form, wide for a dialog that walks through steps "
                        "and lists, such as adding something from a catalog."
                    ),
                },
            },
            "required": ["component", "title", "open"],
        },
    ],
    "unevaluatedProperties": False,
}

_PICKER_ITEM_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {
        "value": {**_NAME, "description": "What a pick writes to the value binding."},
        "title": _NAME,
        "subtitle": _TEXT,
        "chips": {"type": "array", "maxItems": MAX_PICKER_CHIPS, "items": _NAME},
        "meta": {**_TEXT, "description": "Shown at the item's end."},
        "group": {
            **_TEXT,
            "description": "Items with the same group sit under one heading, in order.",
        },
    },
    "required": ["value", "title"],
    "additionalProperties": False,
}

_PICKER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "A searchable list, or a compact select, of items with a title, subtitle and chips. "
        "A pick writes the value binding and fires onPick."
    ),
    "allOf": [
        *_COMMON,
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.picker.v1"},
                "label": _NAME,
                "search": {
                    **_TEXT,
                    "description": "A search box's placeholder; no search box when absent.",
                },
                "hint": _TEXT,
                "error": {**_TEXT, "description": "A problem with the pick, shown beneath."},
                "value": {
                    **_BINDING,
                    "description": "The picked item's value. The client writes it on a pick.",
                },
                "items": {
                    "type": "array",
                    "maxItems": MAX_PICKER_ITEMS,
                    "items": {"$ref": "#/$defs/PickerItem"},
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Without a search, show this many and name the rest.",
                },
                "variant": {"type": "string", "enum": list(PICKER_VARIANTS)},
                "empty": {**_TEXT, "description": "Shown when no item matches."},
                "onPick": {
                    **_ACTION,
                    "description": "Fired on a pick, with {value} merged into its context.",
                },
            },
            "required": ["component", "label", "items", "value"],
        },
    ],
    "unevaluatedProperties": False,
}


def dialog_components() -> tuple[dict[str, Any], dict[str, Any]]:
    """The dialog frame, the picker and their local ``$defs``."""
    return {"clio.dialog.v1": _DIALOG_SCHEMA, "clio.picker.v1": _PICKER_SCHEMA}, {
        "DialogTab": _TAB_DEF,
        "PickerItem": _PICKER_ITEM_DEF,
    }
