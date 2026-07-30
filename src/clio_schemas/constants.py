"""Shared constants for clio-schemas.

Kept in a dependency-free module so that importing them (e.g. from the package
``__init__``) never triggers importing :mod:`clio_schemas.export`, which would
otherwise emit a ``runpy`` warning when the exporter is run via
``python -m clio_schemas.export``.
"""

from __future__ import annotations

# The single pydantic version under which the committed artifacts are canonical.
# ``--regenerate`` / ``--verify`` refuse to run under any other version, so the
# checked-in bytes cannot silently change with a pydantic bump.
LOCKED_PYDANTIC_VERSION = "2.13.4"

# Name of the aggregate schema (shared $defs, used for TS generation) and the
# hash manifest. Kept here so tests, the exporter, and CI agree on the names.
AGGREGATE_FILENAME = "index.json"
HASHES_FILENAME = "HASHES.json"
HASH_ALGORITHM = "sha256"
