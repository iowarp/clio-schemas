"""Catalog definition for the choice table (``clio.choice-table.v1``).

Hand-authored JSON Schema mirroring ``ChoiceTableComponent``
(``a2ui/v0_9_1/choice_components.py``): bounded columns, options, rows and
menus, one icon vocabulary, and rows inline or bound to the data model. The
rules JSON Schema cannot express (unique ids, value keys naming declared
columns, a row's options naming that column's values) live on the model. Kept
out of ``catalog_bounded.py`` so that module does not grow.
"""

from __future__ import annotations

from typing import Any

from clio_schemas.a2ui.catalog_render import COMMON_TYPES_ID
from clio_schemas.a2ui.v0_9_1.choice_components import (
    CHOICE_ICONS,
    CHOICE_TONES,
    MAX_CHOICE_COLUMNS,
    MAX_CHOICE_ID_LENGTH,
    MAX_CHOICE_LABEL_LENGTH,
    MAX_CHOICE_MENU,
    MAX_CHOICE_OPTIONS,
    MAX_CHOICE_ROWS,
    MAX_CHOICE_TEXT_LENGTH,
)

_ACTION = {"$ref": f"{COMMON_TYPES_ID}#/$defs/Action"}
_ID = {"type": "string", "minLength": 1, "maxLength": MAX_CHOICE_ID_LENGTH}
_LABEL = {"type": "string", "minLength": 1, "maxLength": MAX_CHOICE_LABEL_LENGTH}
_TEXT = {"type": "string", "maxLength": MAX_CHOICE_TEXT_LENGTH}
_ICON = {"$ref": "#/$defs/ChoiceIcon"}
_VALUES = {
    "type": "object",
    "additionalProperties": {"type": "string", "maxLength": MAX_CHOICE_ID_LENGTH},
    "description": "Column id to the picked option's value.",
}
_CONTEXT = {"type": "object", "additionalProperties": True}
_MENU = {
    "type": "array",
    "maxItems": MAX_CHOICE_MENU,
    "items": {"$ref": "#/$defs/ChoiceMenuItem"},
}

_ICON_DEF: dict[str, Any] = {
    "type": "string",
    "enum": list(CHOICE_ICONS),
    "description": "Icon name, camelCase.",
}

_OPTION_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {
        "value": {**_ID, "description": "What a pick sends as value."},
        "label": _LABEL,
        "description": {**_TEXT, "description": "One line on what this option means."},
        "icon": _ICON,
        "tone": {"type": "string", "enum": list(CHOICE_TONES)},
    },
    "required": ["value", "label"],
    "additionalProperties": False,
}

_COLUMN_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": _ID,
        "title": _LABEL,
        "help": {**_TEXT, "description": "Shown beside the column title."},
        "editable": {
            "type": "boolean",
            "description": "false shows the column as a read-only status. Default true.",
        },
        "options": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_CHOICE_OPTIONS,
            "items": {"$ref": "#/$defs/ChoiceOption"},
        },
    },
    "required": ["id", "title", "options"],
    "additionalProperties": False,
}

_MENU_ITEM_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": _ID,
        "label": _LABEL,
        "destructive": {"type": "boolean"},
        "action": {**_ACTION, "description": "Its context gets {row}."},
    },
    "required": ["id", "label", "action"],
    "additionalProperties": False,
}

_ROW_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": _ID,
        "title": _LABEL,
        "subtitle": _TEXT,
        "caption": _TEXT,
        "icon": _ICON,
        "values": _VALUES,
        "inherited": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Column ids whose value follows the defaults row.",
        },
        "error": {**_TEXT, "description": "A problem with this row, shown on it."},
        "context": {
            **_CONTEXT,
            "description": "Merged into this row's onChoose context; row, column and value win.",
        },
        "menu": {**_MENU, "description": "Replaces rowMenu for this row."},
        "options": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "maxItems": MAX_CHOICE_OPTIONS,
                "items": _ID,
            },
            "description": (
                "Column id to the option values this row offers; every option when absent."
            ),
        },
    },
    "required": ["id", "title", "values"],
    "additionalProperties": False,
}

_CHOICE_TABLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "Rows of items that each pick one option per column, with icons and descriptions on the "
        "options, an optional defaults row, a row menu and Add. Picks and menu entries are "
        "actions; the owner applies them and re-sends the surface."
    ),
    "allOf": [
        {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
        {"$ref": "#/$defs/CatalogComponentCommon"},
        {
            "type": "object",
            "properties": {
                "component": {"const": "clio.choice-table.v1"},
                "label": {**_LABEL, "description": "Accessible name of the table."},
                "columns": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_CHOICE_COLUMNS,
                    "items": {"$ref": "#/$defs/ChoiceColumn"},
                    "description": "The settings, one column each.",
                },
                "rows": {
                    "description": (
                        f"Inline rows (at most {MAX_CHOICE_ROWS}) or a binding to a data-model "
                        "array of the same row shape."
                    ),
                    "oneOf": [
                        {
                            "type": "array",
                            "maxItems": MAX_CHOICE_ROWS,
                            "items": {"$ref": "#/$defs/ChoiceRow"},
                        },
                        {"$ref": f"{COMMON_TYPES_ID}#/$defs/DataBinding"},
                    ],
                },
                "defaults": {
                    "type": "object",
                    "properties": {
                        "title": _LABEL,
                        "values": _VALUES,
                        "context": {
                            **_CONTEXT,
                            "description": "Merged into the defaults row's onChoose context.",
                        },
                    },
                    "required": ["title", "values"],
                    "additionalProperties": False,
                    "description": 'The defaults row; a pick on it sends row "".',
                },
                "onChoose": {
                    **_ACTION,
                    "description": (
                        "Fired on a pick. Its context is the action's context, then the row's "
                        "context, then {row, column, value}."
                    ),
                },
                "rowMenu": {**_MENU, "description": "Entries on every row's menu."},
                "add": {
                    "type": "object",
                    "properties": {"label": _LABEL, "action": _ACTION},
                    "required": ["label", "action"],
                    "additionalProperties": False,
                    "description": "The Add control under the rows.",
                },
                "empty": {**_TEXT, "description": "Shown when there are no rows."},
            },
            "required": ["component", "label", "columns", "rows"],
        },
    ],
    "unevaluatedProperties": False,
}


def choice_components() -> tuple[dict[str, Any], dict[str, Any]]:
    """The choice table and its local ``$defs``."""
    return {"clio.choice-table.v1": _CHOICE_TABLE_SCHEMA}, {
        "ChoiceIcon": _ICON_DEF,
        "ChoiceOption": _OPTION_DEF,
        "ChoiceColumn": _COLUMN_DEF,
        "ChoiceMenuItem": _MENU_ITEM_DEF,
        "ChoiceRow": _ROW_DEF,
    }
