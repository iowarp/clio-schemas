"""Every committed JSON Schema is itself a valid JSON Schema.

``export --verify`` proves the committed bytes are what the locked pydantic
renders, but not that what it renders is a valid schema. A pydantic upgrade
(or a hand-written ``json_schema_extra``) that emitted, say, a non-array
``required`` or a non-string ``pattern`` would be copied out to every
consumer unnoticed, and consumers' validators would reject it or misbehave.
This test checks each committed schema against the metaschema of the dialect
it declares, and against JSON Schema 2020-12 (what pydantic targets) when it
declares none. The ``format`` keywords in the schemas are checked too
(``check_schema`` applies the metaschema's format checker), for example that
a ``pattern`` is a regex the validator can compile.

The vendored A2UI spec files have their own integrity tests
(``test_a2ui_vendored_integrity.py``) and are not covered here.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from jsonschema import Draft202012Validator, validators

from clio_schemas.constants import AGGREGATE_FILENAME
from clio_schemas.export import package_schema_dir, schema_filename
from clio_schemas.models import EXPORTED_MODELS

#: The committed A2UI catalog that is a JSON Schema (the ``*.clio.json``
#: sidecars and the chart presets/fixtures are data, not schemas).
_CATALOG_SCHEMAS = ("a2ui/catalogs/clio-workspace/v1/catalog.json",)

SCHEMA_FILES: tuple[str, ...] = (
    *sorted(schema_filename(model) for model in EXPORTED_MODELS),
    AGGREGATE_FILENAME,
    *_CATALOG_SCHEMAS,
)


def _load(name: str) -> dict[str, Any]:
    return json.loads((package_schema_dir() / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", SCHEMA_FILES)
def test_committed_schema_is_valid_against_its_metaschema(name: str) -> None:
    schema = _load(name)
    validator_cls = validators.validator_for(schema, default=Draft202012Validator)
    # Fail rather than silently fall back if a file names a dialect we did not expect.
    assert validator_cls is Draft202012Validator, (
        f"{name} declares {schema.get('$schema')!r}; expected JSON Schema 2020-12"
    )
    validator_cls.check_schema(schema)


def test_metaschema_check_rejects_an_invalid_schema() -> None:
    """Negative control: the check is not a no-op."""

    with pytest.raises(Exception, match="is not of type 'array'"):
        Draft202012Validator.check_schema({"type": "object", "required": "id"})
    with pytest.raises(Exception, match="is not a 'regex'"):
        Draft202012Validator.check_schema({"type": "string", "pattern": "("})
