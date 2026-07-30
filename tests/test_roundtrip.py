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

The TS-generating tests skip (never silently pass) if Node.js or the TS-gen
``node_modules`` are absent. Install the JS side with
``cd tools/ts-gen && npm install`` to run them.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from clio_schemas.constants import HASHES_FILENAME
from clio_schemas.export import (
    read_committed,
    render_bundle,
    schema_filename,
)
from clio_schemas.models import EXPORTED_MODELS, ProbeBatch, ProbeKind, SchemaProbe

REPO_ROOT = Path(__file__).resolve().parents[1]
TS_GEN_DIR = REPO_ROOT / "tools" / "ts-gen"
GENERATOR = TS_GEN_DIR / "schemas-to-ts.mjs"
NODE_MODULES = TS_GEN_DIR / "node_modules"
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
# TypeScript round-trip (needs Node)
# --------------------------------------------------------------------------- #
def _node_available() -> bool:
    return shutil.which("node") is not None


requires_node = pytest.mark.skipif(
    not _node_available() or not NODE_MODULES.exists(),
    reason="node / tools/ts-gen/node_modules missing (run `npm install` in tools/ts-gen)",
)


def _generate_ts(tmp_path: Path) -> Path:
    """Copy committed schemas + generate the TS graph into a clean temp dir."""

    schema_dir = tmp_path / "schemas"
    ts_dir = tmp_path / "generated-ts"
    schema_dir.mkdir()
    for name, content in read_committed().items():
        (schema_dir / name).write_text(content, encoding="utf-8")

    result = subprocess.run(
        ["node", str(GENERATOR), "--in", str(schema_dir), "--out", str(ts_dir)],
        cwd=str(TS_GEN_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"TS generation failed:\n{result.stderr}"
    return ts_dir


@requires_node
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


@requires_node
@pytest.mark.parametrize("model", EXPORTED_MODELS, ids=lambda m: m.__name__)
def test_every_model_has_a_golden_ts_module(tmp_path: Path, model: type) -> None:
    """Each exported model has a generated (and golden) per-model .ts module."""

    ts_dir = _generate_ts(tmp_path)
    stem = schema_filename(model)[: -len(".json")]
    assert (ts_dir / f"{stem}.ts").exists()
    assert (GOLDEN_DIR / f"{stem}.ts").exists()


@requires_node
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
    # The shared enum must be present and singular.
    assert counts.get("ProbeKind") == 1


# --------------------------------------------------------------------------- #
# Strict wire conformance (negative tests)
# --------------------------------------------------------------------------- #
def test_string_for_int_is_rejected() -> None:
    """strict=True: a string is not coerced into the int `sequence` field."""

    with pytest.raises(ValidationError):
        SchemaProbe(probe_id="p", sequence="7")  # type: ignore[arg-type]


def test_unknown_key_is_rejected() -> None:
    """extra='forbid': unknown keys are rejected, never silently dropped."""

    with pytest.raises(ValidationError):
        SchemaProbe(probe_id="p", bogus=1)  # type: ignore[call-arg]


def test_records_are_frozen() -> None:
    """frozen=True: received records are immutable value objects."""

    probe = SchemaProbe(probe_id="p")
    with pytest.raises(ValidationError):
        probe.sequence = 5  # type: ignore[misc]


def test_valid_record_roundtrips() -> None:
    """A well-formed record validates and nests correctly."""

    probe = SchemaProbe(probe_id="p", kind=ProbeKind.ECHO, sequence=3)
    batch = ProbeBatch(batch_id="b", probes=(probe,))
    assert batch.probes[0].kind is ProbeKind.ECHO
    assert batch.default_kind is ProbeKind.PING
