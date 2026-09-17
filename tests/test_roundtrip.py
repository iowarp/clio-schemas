"""Golden round-trip + conformance anti-drift tests.

This is the failing-first proof from issue #1110, hardened after review:

- Round-trip: copy the committed JSON Schema, generate the TypeScript module
  graph into a *clean* temp dir, and assert the complete generated directory
  matches the complete committed golden directory — exact filename-set equality
  (catches added-untracked and removed-orphan files) plus byte-for-byte content
  for every file.
- Coverage: parameterised over ``EXPORTED_MODELS`` so every model has an
  asserted golden ``.ts`` re-export module.
- No-duplication: the generated barrel declares each exported type exactly once.
- Conformance: strict pydantic validation matches the JSON Schema (a string is
  rejected where an int is declared; unknown keys are forbidden; records are
  frozen).

The TS-generating tests require Node.js and the TS-gen ``node_modules`` — they
FAIL (never silently skip) if either is absent, so a node-less environment is
a red build, not a quietly-shrinking test count. Install the JS side with
``cd tools/ts-gen && npm ci`` before running this file. CI's ``roundtrip`` job
(``.github/workflows/ci.yml``) sets up Node and runs ``npm ci`` before pytest.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from clio_schemas.constants import HASHES_FILENAME
from clio_schemas.export import (
    read_committed,
    render_bundle,
    schema_filename,
)
from clio_schemas.models import EXPORTED_MODELS

REPO_ROOT = Path(__file__).resolve().parents[1]
TS_GEN_DIR = REPO_ROOT / "tools" / "ts-gen"
GENERATOR = TS_GEN_DIR / "schemas-to-ts.mjs"
GOLDEN_DIR = REPO_ROOT / "tests" / "golden"


# --------------------------------------------------------------------------- #
# Committed-schema canonicality (no Node required)
# --------------------------------------------------------------------------- #
def test_committed_schemas_are_canonical() -> None:
    """The committed package resources match a fresh render + their hashes."""

    expected = render_bundle()
    committed = read_committed()
    assert set(committed) == set(expected)
    for name, content in expected.items():
        assert committed[name] == content, f"{name} committed bytes are stale"


@pytest.mark.parametrize("model", EXPORTED_MODELS, ids=lambda m: m.__name__)
def test_every_model_has_a_committed_schema(model: type) -> None:
    """Each exported model has its own committed JSON Schema file."""

    assert schema_filename(model) in read_committed()


def test_hashes_manifest_lists_every_schema() -> None:
    """HASHES.json records a hash for every schema file (and nothing else)."""

    import json

    committed = read_committed()
    manifest = json.loads(committed[HASHES_FILENAME])
    schema_files = {n for n in committed if n != HASHES_FILENAME}
    assert set(manifest["files"]) == schema_files


# --------------------------------------------------------------------------- #
# TypeScript round-trip (requires Node — see module docstring: no skip)
# --------------------------------------------------------------------------- #
def _generate_ts(tmp_path: Path) -> Path:
    """Copy committed schemas + generate the TS graph into a clean temp dir.

    ts-gen only cares about the flat per-model schemas (+ the aggregate +
    HASHES.json) — the ``a2ui/catalogs/**`` tree from ``read_committed()``
    is a JSON Schema *catalog* tree, not a pydantic-model export, and is
    intentionally excluded here (its path keys contain ``/``).
    """

    schema_dir = tmp_path / "schemas"
    ts_dir = tmp_path / "generated-ts"
    schema_dir.mkdir()
    for name, content in read_committed().items():
        if "/" in name:
            continue
        (schema_dir / name).write_text(content, encoding="utf-8")

    result = subprocess.run(
        ["node", str(GENERATOR), "--in", str(schema_dir), "--out", str(ts_dir)],
        cwd=str(TS_GEN_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"TS generation failed:\n{result.stderr}"
    return ts_dir


def test_golden_directory_set_and_bytes(tmp_path: Path) -> None:
    """Complete generated dir == complete golden dir: filenames + bytes."""

    ts_dir = _generate_ts(tmp_path)
    generated = {p.name for p in ts_dir.glob("*.ts")}
    golden = {p.name for p in GOLDEN_DIR.glob("*.ts")}
    assert generated == golden, (
        f"file-set drift: extra={generated - golden}, missing={golden - generated}"
    )
    for name in sorted(golden):
        gen_text = (ts_dir / name).read_text(encoding="utf-8")
        golden_text = (GOLDEN_DIR / name).read_text(encoding="utf-8")
        assert gen_text == golden_text, (
            f"generated {name} drifted from the committed golden. If intended, "
            "regenerate: `python -m clio_schemas.export --out schemas` then "
            "`node tools/ts-gen/schemas-to-ts.mjs --in schemas --out tests/golden`."
        )


@pytest.mark.parametrize("model", EXPORTED_MODELS, ids=lambda m: m.__name__)
def test_every_model_has_a_golden_ts_module(tmp_path: Path, model: type) -> None:
    """Each exported model has a generated (and golden) per-model .ts module."""

    ts_dir = _generate_ts(tmp_path)
    stem = schema_filename(model)[: -len(".json")]
    assert (ts_dir / f"{stem}.ts").exists()
    assert (GOLDEN_DIR / f"{stem}.ts").exists()


def test_no_duplicate_declarations_in_barrel(tmp_path: Path) -> None:
    """Every exported type is *declared* exactly once across the module graph."""

    ts_dir = _generate_ts(tmp_path)
    decl = re.compile(r"^export (?:interface|type|enum|class) (\w+)", re.MULTILINE)
    counts: dict[str, int] = {}
    for path in ts_dir.glob("*.ts"):
        for name in decl.findall(path.read_text(encoding="utf-8")):
            counts[name] = counts.get(name, 0) + 1
    dupes = {name: n for name, n in counts.items() if n > 1}
    assert not dupes, f"duplicate declarations: {dupes}"
    # Shared definitions must be present and singular.
    for name in ("ArtifactKind", "EdgeEvidence", "EnvironmentTier"):
        assert counts.get(name) == 1


# --------------------------------------------------------------------------- #
# Exported-schema conformance
# --------------------------------------------------------------------------- #
def test_every_exported_model_forbids_schema_extras_only_when_configured() -> None:
    """The emitted additionalProperties value follows each model's runtime contract.

    A model configured ``extra="forbid"`` (the new closed A2UI envelope/
    capability/catalog models) must render ``additionalProperties: false``;
    every other exported model (the legacy-tolerant P2.1 records, and the
    RootModel-wrapped discriminated unions) must not.
    """

    for model in EXPORTED_MODELS:
        additional = model.model_json_schema().get("additionalProperties")
        if model.model_config.get("extra") == "forbid":
            assert additional is False, f"{model.__name__} is extra='forbid' but schema is open"
        else:
            assert additional is not False, f"{model.__name__} tolerates extras but schema closes"
