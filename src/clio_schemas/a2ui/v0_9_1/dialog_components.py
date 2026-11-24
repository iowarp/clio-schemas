"""The dialog frame and the picker: a modal with tabs and a footer, and a list to pick from.

``clio.dialog.v1`` is a trigger drawn in place in the page that opens a modal
with a title, optional tabs or one body, a step rail, a status line and a
footer of Test, Cancel and confirm. Its ``open`` and ``activeTab`` are
data-model bindings the client writes. ``clio.picker.v1`` is a searchable list,
or a compact select, of items with a title, subtitle and chips; a pick writes
the ``value`` binding and fires ``onPick``. Both carry no domain vocabulary.
"""

from __future__ import annotations

from typing import Annotated, Literal, get_args

from pydantic import Field, StringConstraints, model_validator

from clio_schemas.a2ui.v0_9_1.components import (
    Action,
    ComponentId,
    _ClosedModel,
    _ComponentBase,
    _DataBinding,
)

MAX_DIALOG_TABS = 6
MIN_DIALOG_STEPS = 2
MAX_DIALOG_STEPS = 6
MAX_PICKER_ITEMS = 200
MAX_PICKER_CHIPS = 8
DialogStatusTone = Literal["neutral", "positive", "warning", "negative", "busy"]
DialogConfirmTone = Literal["default", "destructive"]
DialogWidth = Literal["narrow", "default"]
PickerVariant = Literal["list", "select"]
DIALOG_STATUS_TONES: tuple[str, ...] = get_args(DialogStatusTone)
DIALOG_CONFIRM_TONES: tuple[str, ...] = get_args(DialogConfirmTone)
DIALOG_WIDTHS: tuple[str, ...] = get_args(DialogWidth)
PICKER_VARIANTS: tuple[str, ...] = get_args(PickerVariant)
_Name = Annotated[str, StringConstraints(min_length=1)]


class DialogButton(_ClosedModel):
    """A footer or status button: a label, its action, and whether it can be pressed."""

    label: _Name
    action: Action
    enabled: bool | None = None


class DialogTest(DialogButton):
    """The Test button at the footer's start."""

    keyboard: str | None = None


class DialogConfirm(DialogButton):
    """The main button at the footer's end."""

    tone: DialogConfirmTone | None = None


class DialogCancel(_ClosedModel):
    """Cancel: with an action it fires it; without, it closes the dialog and fires onClose."""

    label: _Name
    action: Action | None = None


class DialogTab(_ClosedModel):
    """One tab: its id, title, icon and the component it shows."""

    id: _Name
    title: _Name
    icon: str | None = None
    child: ComponentId


class DialogRail(_ClosedModel):
    """The numbered steps the dialog walks through, and the one it is on."""

    steps: list[_Name] = Field(min_length=MIN_DIALOG_STEPS, max_length=MAX_DIALOG_STEPS)
    step: Annotated[int, Field(ge=0)]
    tabs: list[_Name] | None = None


class DialogStatus(_ClosedModel):
    """The line above the footer: a test's result or progress."""

    tone: DialogStatusTone
    text: _Name
    detail: str | None = None
    action: DialogButton | None = None


class DialogComponent(_ComponentBase):
    """A trigger in the page that opens a modal with tabs, a step rail, a status and a footer."""

    component: Literal["clio.dialog.v1"] = "clio.dialog.v1"
    title: _Name
    description: str | None = None
    open: _DataBinding
    trigger: ComponentId | None = None
    content: ComponentId | None = None
    tabs: list[DialogTab] | None = Field(default=None, min_length=1, max_length=MAX_DIALOG_TABS)
    activeTab: _DataBinding | None = None
    rail: DialogRail | None = None
    status: DialogStatus | None = None
    test: DialogTest | None = None
    cancel: DialogCancel | None = None
    confirm: DialogConfirm | None = None
    onClose: Action | None = None
    width: DialogWidth | None = None

    @model_validator(mode="after")
    def _known_tabs(self) -> DialogComponent:
        ids = [tab.id for tab in self.tabs or []]
        if len(set(ids)) != len(ids):
            raise ValueError("tab ids must be unique")
        if self.rail is not None:
            unknown = sorted(set(self.rail.tabs or []) - set(ids))
            if unknown:
                raise ValueError(f"rail.tabs: {unknown} are not tab ids")
        return self


class PickerItem(_ClosedModel):
    """One item: what a pick writes, its title, subtitle, chips, meta and group."""

    value: _Name
    title: _Name
    subtitle: str | None = None
    chips: list[_Name] | None = Field(default=None, max_length=MAX_PICKER_CHIPS)
    meta: str | None = None
    group: str | None = None


class PickerComponent(_ComponentBase):
    """A searchable list, or a compact select, of items with a title, subtitle and chips."""

    component: Literal["clio.picker.v1"] = "clio.picker.v1"
    label: _Name
    search: str | None = None
    hint: str | None = None
    error: str | None = None
    value: _DataBinding
    items: list[PickerItem] = Field(max_length=MAX_PICKER_ITEMS)
    limit: Annotated[int, Field(ge=1)] | None = None
    variant: PickerVariant | None = None
    empty: str | None = None
    onPick: Action | None = None


DIALOG_COMPONENT_MODELS = (DialogComponent, PickerComponent)
