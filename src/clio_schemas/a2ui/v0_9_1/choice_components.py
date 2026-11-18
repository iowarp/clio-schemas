"""The choice table: rows of items, each with one option picked per column.

A general settings grid with no domain vocabulary: each column is a setting
whose options carry a label, a description and an icon, each row is an item
that picks one option per column, and an optional defaults row holds the
values rows inherit. Picks, the row menu and Add are actions, so the owner of
the surface applies a change and re-sends the surface. Rows are inline or a
data-model binding to an array of the same row shape.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Annotated, Literal, get_args

from pydantic import Field, JsonValue, StringConstraints, model_validator

from clio_schemas.a2ui.v0_9_1.components import Action, _ClosedModel, _ComponentBase, _DataBinding

MAX_CHOICE_COLUMNS = 6
MAX_CHOICE_OPTIONS = 24
MAX_CHOICE_ROWS = 500
MAX_CHOICE_MENU = 8
MAX_CHOICE_ID_LENGTH = 128
MAX_CHOICE_LABEL_LENGTH = 120
MAX_CHOICE_TEXT_LENGTH = 500
#: The basic catalog's icon names plus the ones a settings grid needs (hosts,
#: networks, keys, trust). One spelling each: camelCase.
ChoiceIcon = Literal[
    "accountCircle",
    "add",
    "alertCircle",
    "alertTriangle",
    "arrowBack",
    "arrowForward",
    "attachFile",
    "calendarToday",
    "call",
    "camera",
    "cancel",
    "check",
    "checkCircle",
    "close",
    "cloud",
    "computer",
    "delete",
    "dns",
    "download",
    "edit",
    "error",
    "event",
    "fastForward",
    "favorite",
    "favoriteOff",
    "folder",
    "help",
    "home",
    "hub",
    "info",
    "key",
    "lan",
    "locationOn",
    "lock",
    "lockOpen",
    "mail",
    "memory",
    "menu",
    "moreHoriz",
    "moreVert",
    "notifications",
    "notificationsOff",
    "pause",
    "payment",
    "person",
    "phone",
    "photo",
    "play",
    "print",
    "public",
    "refresh",
    "rewind",
    "search",
    "security",
    "send",
    "settings",
    "share",
    "shield",
    "shoppingCart",
    "skipNext",
    "skipPrevious",
    "star",
    "starHalf",
    "starOff",
    "stop",
    "storage",
    "terminal",
    "upload",
    "verifiedUser",
    "visibility",
    "visibilityOff",
    "volumeDown",
    "volumeMute",
    "volumeOff",
    "volumeUp",
    "warning",
]
ChoiceTone = Literal["neutral", "positive", "warning", "negative"]
CHOICE_ICONS: tuple[str, ...] = get_args(ChoiceIcon)
CHOICE_TONES: tuple[str, ...] = get_args(ChoiceTone)
ChoiceId = Annotated[str, StringConstraints(min_length=1, max_length=MAX_CHOICE_ID_LENGTH)]
ChoiceLabel = Annotated[str, StringConstraints(min_length=1, max_length=MAX_CHOICE_LABEL_LENGTH)]
ChoiceText = Annotated[str, StringConstraints(max_length=MAX_CHOICE_TEXT_LENGTH)]
ChoiceValue = Annotated[str, StringConstraints(max_length=MAX_CHOICE_ID_LENGTH)]


class ChoiceOption(_ClosedModel):
    """One option of a column: its value, label, description, icon and tone."""

    value: ChoiceId
    label: ChoiceLabel
    description: ChoiceText | None = None
    icon: ChoiceIcon | None = None
    tone: ChoiceTone | None = None


class ChoiceColumn(_ClosedModel):
    """One setting: the options a row picks from."""

    id: ChoiceId
    title: ChoiceLabel
    help: ChoiceText | None = None
    editable: bool | None = None
    options: list[ChoiceOption] = Field(min_length=1, max_length=MAX_CHOICE_OPTIONS)

    @model_validator(mode="after")
    def _unique_values(self) -> ChoiceColumn:
        values = [option.value for option in self.options]
        if len(set(values)) != len(values):
            raise ValueError(f"column {self.id!r}: option values must be unique")
        return self


class ChoiceMenuItem(_ClosedModel):
    """One row-menu entry; its action's context gets ``{row}``."""

    id: ChoiceId
    label: ChoiceLabel
    destructive: bool | None = None
    action: Action


class ChoiceRow(_ClosedModel):
    """One item and the option it picks in each column."""

    id: ChoiceId
    title: ChoiceLabel
    subtitle: ChoiceText | None = None
    caption: ChoiceText | None = None
    icon: ChoiceIcon | None = None
    values: dict[str, ChoiceValue]
    inherited: list[str] | None = None
    error: ChoiceText | None = None
    context: dict[str, JsonValue] | None = None
    menu: list[ChoiceMenuItem] | None = Field(default=None, max_length=MAX_CHOICE_MENU)


class ChoiceDefaults(_ClosedModel):
    """The defaults row: values that rows listing a column in ``inherited`` follow."""

    title: ChoiceLabel
    values: dict[str, ChoiceValue]
    context: dict[str, JsonValue] | None = None


class ChoiceAdd(_ClosedModel):
    """The Add control under the rows."""

    label: ChoiceLabel
    action: Action


class ChoiceTableComponent(_ComponentBase):
    """Rows of items, each picking one option per column, with defaults, a row menu and Add."""

    component: Literal["clio.choice-table.v1"] = "clio.choice-table.v1"
    label: ChoiceLabel
    columns: list[ChoiceColumn] = Field(min_length=1, max_length=MAX_CHOICE_COLUMNS)
    rows: Annotated[list[ChoiceRow], Field(max_length=MAX_CHOICE_ROWS)] | _DataBinding
    defaults: ChoiceDefaults | None = None
    onChoose: Action | None = None
    rowMenu: list[ChoiceMenuItem] | None = Field(default=None, max_length=MAX_CHOICE_MENU)
    add: ChoiceAdd | None = None
    empty: ChoiceText | None = None

    @model_validator(mode="after")
    def _known_columns(self) -> ChoiceTableComponent:
        columns = [column.id for column in self.columns]
        if len(set(columns)) != len(columns):
            raise ValueError("column ids must be unique")
        known = set(columns)
        if self.defaults is not None:
            _check_keys("defaults.values", self.defaults.values, known)
        if isinstance(self.rows, list):
            ids = [row.id for row in self.rows]
            if len(set(ids)) != len(ids):
                raise ValueError("row ids must be unique")
            for row in self.rows:
                _check_keys(f"row {row.id!r} values", row.values, known)
                _check_keys(f"row {row.id!r} inherited", row.inherited or [], known)
        return self


def _check_keys(where: str, keys: Iterable[str], known: set[str]) -> None:
    unknown = sorted(set(keys) - known)
    if unknown:
        raise ValueError(f"{where}: {unknown} are not column ids")


CHOICE_COMPONENT_MODELS = (ChoiceTableComponent,)
