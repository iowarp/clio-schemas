"""Canonicalise the 25 factory-built CLIO components to official catalog style.

Reads the exact declarative ``required``/``optional`` field-type mapping
(:data:`clio_schemas.a2ui.v0_9_1.components.COMPONENT_SPECS`) that builds
each pydantic component model — not the models' *rendered JSON Schema*,
which would make this fragile (pydantic's own encoding of a union like
``DynamicString`` is an implementation detail, not a public contract). Each
declared field type is recognised once, by identity/equality, and rendered
into the matching official ``common_types.json`` ``$ref`` (or a local
``$defs`` entry for a CLIO-only nested shape: option/tab/card-action). Each
component's one-sentence :data:`COMPONENT_DESCRIPTIONS` entry is rendered
onto its schema's top-level ``description``.

The 7 components with bounded lists or cross-field rules (``clio.map.v1``,
``clio.data-table.v1``, ``clio.code.v1``, ``clio.mermaid.v1``,
``clio.diff.v1``, ``clio.workflow.v1``, ``clio.chart.v1``) are not built
through ``COMPONENT_SPECS`` at all — see ``catalog_bounded.py``.
"""

from __future__ import annotations

import types
import typing
from typing import Annotated, Any, Literal

import annotated_types
from pydantic import JsonValue
from pydantic.fields import FieldInfo

from clio_schemas.a2ui.v0_9_1.components import (
    ARTIFACT_URI_PATTERN,
    COMPONENT_DESCRIPTIONS,
    COMPONENT_SPECS,
    SYNC_GROUP_PATTERN,
    Action,
    ArtifactUri,
    ChildList,
    ComponentId,
    DynamicBoolean,
    DynamicNumber,
    DynamicString,
    DynamicStringList,
    DynamicValue,
    IconValue,
    SyncGroup,
    _CardAction,
    _ChoiceOption,
    _ClosedModel,
    _TabDefinition,
)

COMMON_TYPES_ID = "https://a2ui.org/specification/v0_9/common_types.json"

# type object (by identity/equality) -> the common_types.json $defs name it renders to.
_DYNAMIC_REF_BY_TYPE: dict[Any, str] = {
    DynamicString: "DynamicString",
    DynamicNumber: "DynamicNumber",
    DynamicBoolean: "DynamicBoolean",
    DynamicStringList: "DynamicStringList",
    DynamicValue: "DynamicValue",
    ChildList: "ChildList",
    Action: "Action",
    ComponentId: "ComponentId",
}

_ICON_SVG_PATH_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {"svgPath": {"type": "string"}},
    "required": ["svgPath"],
    "additionalProperties": False,
}

CATALOG_COMPONENT_COMMON_DEF: dict[str, Any] = {
    "type": "object",
    "properties": {
        "weight": {
            "type": "number",
            "description": (
                "Relative flex weight of this component inside a Row or Column. "
                "Only meaningful as a direct child of one."
            ),
        }
    },
}


_UNION_ORIGINS = (types.UnionType, typing.Union)


def _strip_optional(annotation: Any) -> Any:
    """Return ``annotation`` with a trailing ``| None`` removed, if present.

    A field declared as ``X | None`` under ``from __future__ import
    annotations`` may come back from pydantic's ``FieldInfo.annotation`` as
    either a ``types.UnionType`` (``X | None``) or a ``typing.Union`` special
    form (``typing.Optional[X]``) depending on how it was resolved — both are
    handled identically here.
    """

    if typing.get_origin(annotation) in _UNION_ORIGINS:
        args = [arg for arg in typing.get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def _list_bounds(field_info: FieldInfo) -> tuple[int | None, int | None]:
    """Extract ``(min_items, max_items)`` from a ``Field(min_length=, max_length=)``."""

    min_items = max_items = None
    for constraint in field_info.metadata:
        if getattr(constraint, "min_length", None) is not None:
            min_items = constraint.min_length
        if getattr(constraint, "max_length", None) is not None:
            max_items = constraint.max_length
    return min_items, max_items


# annotated_types constraint type -> (rendered JSON Schema key, value attribute).
# G2 (#23, adversarial review F7): every numeric `annotated_types` constraint
# pydantic's `Field()` can attach is rendered here, or the field is unrecognised
# and raises -- `gt`/`lt`/`multiple_of` must never be silently dropped the way
# a `minimum`/`maximum`-only reader would drop them.
_NUMBER_CONSTRAINT_RENDER: dict[type, tuple[str, str]] = {
    annotated_types.Ge: ("minimum", "ge"),
    annotated_types.Gt: ("exclusiveMinimum", "gt"),
    annotated_types.Le: ("maximum", "le"),
    annotated_types.Lt: ("exclusiveMaximum", "lt"),
    annotated_types.MultipleOf: ("multipleOf", "multiple_of"),
}


def _number_bounds(field_info: FieldInfo) -> dict[str, float]:
    """Extract numeric JSON Schema bounds from a ``Field(ge=, le=, gt=, lt=, multiple_of=)``.

    Mirrors :func:`_list_bounds` for the ``annotated_types`` numeric
    constraints instead of ``MinLen``/``MaxLen`` -- G2 (#23): a bound
    declared this way on a plain ``int``/``float`` field (e.g. ``Grid.gap``)
    previously rendered as an unbounded ``{"type": "number"}``, accepting
    values the client's own catalog already rejects.

    Adversarial review (F7): the original version of this function only
    recognised ``Ge``/``Le`` (``ge=``/``le=``), so ``gt=``/``lt=``/
    ``multiple_of=`` would have been silently dropped -- a numeric field
    would render as unbounded rather than as a visibly wrong bound,
    exactly the kind of degradation the no-silent-fallback rule forbids.
    Every numeric constraint is now either rendered or raises.

    Raises:
        NotImplementedError: For a metadata object this canonicaliser has no
            rendering rule for (never silently dropped).
    """

    bounds: dict[str, float] = {}
    for constraint in field_info.metadata:
        render = _NUMBER_CONSTRAINT_RENDER.get(type(constraint))
        if render is not None:
            schema_key, value_attr = render
            bounds[schema_key] = getattr(constraint, value_attr)
            continue
        if isinstance(constraint, (annotated_types.MinLen, annotated_types.MaxLen)):
            continue  # length bounds -- rendered by `_list_bounds` instead
        raise NotImplementedError(
            f"no catalog rendering rule for numeric constraint {constraint!r}"
        )
    return bounds


def _string_constraints(field_info: FieldInfo) -> dict[str, str | int]:
    """Carry declared string length and pattern constraints into the catalog."""

    constraints: dict[str, str | int] = {}
    for constraint in field_info.metadata:
        if isinstance(constraint, annotated_types.MinLen):
            constraints["minLength"] = constraint.min_length
            continue
        if isinstance(constraint, annotated_types.MaxLen):
            constraints["maxLength"] = constraint.max_length
            continue
        pattern = getattr(constraint, "pattern", None)
        if isinstance(pattern, str):
            constraints["pattern"] = pattern
            continue
        if isinstance(constraint, str) and constraint.startswith("a2ui:"):
            continue  # A2UI marker already rendered through the field's declared type.
        raise NotImplementedError(f"no catalog rendering rule for string constraint {constraint!r}")
    if field_info.description:
        constraints["description"] = field_info.description
    return constraints


def _render_nested_model(fields: dict[str, FieldInfo]) -> dict[str, Any]:
    """Render one small CLIO-local nested shape (option/tab/column/action)."""

    properties: dict[str, Any] = {}
    required: list[str] = []
    scratch_defs: dict[str, Any] = {}
    for name, field_info in fields.items():
        field_type = _strip_optional(field_info.annotation)
        rendered = render_type(field_type, name, scratch_defs)
        if rendered is None:
            continue
        if typing.get_origin(field_type) is list:
            min_items, max_items = _list_bounds(field_info)
            if min_items is not None:
                rendered["minItems"] = min_items
            if max_items is not None:
                rendered["maxItems"] = max_items
        elif field_type in (int, float):
            rendered.update(_number_bounds(field_info))
        elif field_type is str and field_info.metadata:
            rendered.update(_string_constraints(field_info))
        if field_info.description:
            rendered["description"] = field_info.description
        properties[name] = rendered
        if field_info.is_required():
            required.append(name)
    if scratch_defs:
        raise NotImplementedError("nested CLIO shapes do not currently need further $defs")
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def render_type(t: Any, field_name: str, local_defs: dict[str, Any]) -> dict[str, Any] | None:
    """Render one declared field type to a catalog-style JSON Schema node.

    Returns ``None`` for the ``checks`` field name, which the caller renders
    as a ``common_types.json#/$defs/Checkable`` ``allOf`` branch instead of a
    plain property.

    Raises:
        NotImplementedError: For a field type this canonicaliser has no
            rendering rule for — never silently dropped.
    """

    if field_name == "checks":
        return None

    ref_name = _DYNAMIC_REF_BY_TYPE.get(t)
    if ref_name is not None:
        return {"$ref": f"{COMMON_TYPES_ID}#/$defs/{ref_name}"}

    if t == IconValue:
        local_defs.setdefault("IconSvgPath", _ICON_SVG_PATH_DEF)
        return {
            "oneOf": [
                {"type": "string"},
                {"$ref": "#/$defs/IconSvgPath"},
                {"$ref": f"{COMMON_TYPES_ID}#/$defs/DataBinding"},
            ]
        }

    if t == ArtifactUri:
        return {"type": "string", "pattern": ARTIFACT_URI_PATTERN}
    if t == SyncGroup:
        return {"type": "string", "pattern": SYNC_GROUP_PATTERN}

    origin = typing.get_origin(t)

    if origin in (typing.Union, types.UnionType):
        options = typing.get_args(t)
        dynamic_number_options = typing.get_args(DynamicNumber)
        range_options = [option for option in options if typing.get_origin(option) is Annotated]
        if (
            len(range_options) == 1
            and len(options) == len(dynamic_number_options) + 1
            and all(option in options for option in dynamic_number_options)
        ):
            return {
                "oneOf": [
                    {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicNumber"},
                    render_type(range_options[0], field_name, local_defs),
                ]
            }

    if origin is Annotated:
        inner, meta = typing.get_args(t)
        rendered = render_type(inner, field_name, local_defs)
        if rendered is None:
            return None
        if rendered.get("type") == "array":
            min_items, max_items = _list_bounds(meta)
            if min_items is not None:
                rendered["minItems"] = min_items
            if max_items is not None:
                rendered["maxItems"] = max_items
        if rendered.get("type") == "string":
            rendered.update(_string_constraints(meta))
        else:
            rendered.update(_number_bounds(meta))
        return rendered

    if origin is list:
        (item_type,) = typing.get_args(t)
        if item_type == ComponentId:
            return {"type": "array", "items": {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentId"}}
        if item_type == _ChoiceOption:
            local_defs.setdefault("ChoiceOption", _render_nested_model(_ChoiceOption.model_fields))
            return {"type": "array", "items": {"$ref": "#/$defs/ChoiceOption"}}
        if item_type == _TabDefinition:
            local_defs.setdefault(
                "TabDefinition", _render_nested_model(_TabDefinition.model_fields)
            )
            return {"type": "array", "items": {"$ref": "#/$defs/TabDefinition"}}
        if item_type == _CardAction:
            local_defs.setdefault("CardAction", _render_nested_model(_CardAction.model_fields))
            return {"type": "array", "items": {"$ref": "#/$defs/CardAction"}}
        if isinstance(item_type, type) and issubclass(item_type, _ClosedModel):
            local_defs.setdefault(
                item_type.__name__.lstrip("_"), _render_nested_model(item_type.model_fields)
            )
            return {"type": "array", "items": {"$ref": f"#/$defs/{item_type.__name__.lstrip('_')}"}}
        if item_type == dict[str, JsonValue]:
            return {"type": "array", "items": {"type": "object"}}
        if item_type is str:
            return {"type": "array", "items": {"type": "string"}}
        if item_type is float:
            return {"type": "array", "items": {"type": "number"}}
        raise NotImplementedError(
            f"no catalog rendering rule for list item type {item_type!r} (field {field_name!r})"
        )

    if origin is Literal:
        return {"type": "string", "enum": list(typing.get_args(t))}

    if t is str:
        return {"type": "string"}
    if t is float:
        return {"type": "number"}
    if t is bool:
        return {"type": "boolean"}
    if t is int:
        return {"type": "integer"}

    raise NotImplementedError(
        f"no catalog rendering rule for field type {t!r} (field {field_name!r})"
    )


def _render_factory_component(name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Render one component built through ``_component_model`` (25 of the 32)."""

    required, optional = COMPONENT_SPECS[name]
    properties: dict[str, Any] = {"component": {"const": name}}
    required_names = ["component"]
    needs_checkable = False
    local_defs: dict[str, Any] = {}

    for field_name, field_type in required.items():
        if field_name == "checks":
            needs_checkable = True
            continue
        properties[field_name] = render_type(field_type, field_name, local_defs)
        required_names.append(field_name)
    for field_name, field_type in optional.items():
        if field_name == "checks":
            needs_checkable = True
            continue
        properties[field_name] = render_type(field_type, field_name, local_defs)

    all_of: list[dict[str, Any]] = [
        {"$ref": f"{COMMON_TYPES_ID}#/$defs/ComponentCommon"},
        {"$ref": "#/$defs/CatalogComponentCommon"},
    ]
    if needs_checkable:
        all_of.append({"$ref": f"{COMMON_TYPES_ID}#/$defs/Checkable"})
    all_of.append({"type": "object", "properties": properties, "required": required_names})

    schema = {
        "type": "object",
        "description": COMPONENT_DESCRIPTIONS[name],
        "allOf": all_of,
        "unevaluatedProperties": False,
    }
    return schema, local_defs


def render_factory_components() -> tuple[dict[str, Any], dict[str, Any]]:
    """Render all 25 factory-built components: ``(components, shared $defs)``."""

    components: dict[str, Any] = {}
    defs: dict[str, Any] = {"CatalogComponentCommon": CATALOG_COMPONENT_COMMON_DEF}
    for name in COMPONENT_SPECS:
        schema, local_defs = _render_factory_component(name)
        components[name] = schema
        defs.update(local_defs)
    return components, defs
