"""A2UI protocol package: official 0.9.1 wire shapes, catalog rendering, validation.

Sub-packages:

- ``v0_9_1``: the official protocol-version-specific pydantic models
  (envelopes, capabilities, data model, catalog file shape) plus the 30 CLIO
  catalog component models (the generator for ``catalog_export.py``).
- ``sidecar``: CLIO's version-neutral catalog packaging metadata (never sent
  on the wire).
- ``validation``: ``jsonschema`` + ``referencing`` validators built from the
  vendored spec and a supplied catalog.
- ``catalog_render`` / ``catalog_bounded`` / ``catalog_export``: the
  canonicaliser that renders CLIO's pydantic component models into official
  catalog-file JSON Schema.
"""

from __future__ import annotations
