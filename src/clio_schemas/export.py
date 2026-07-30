"""Deterministic JSON Schema export + immutable-artifact distribution.

Design (post-review, issue #1110): an exact ``clio-schemas`` pin does **not**
determine schema *bytes* if consumers regenerate under their own resolved
``pydantic`` — different pydantic versions can emit slightly different JSON
Schema. So the canonical schemas are shipped as **immutable package resources**
inside the wheel (``clio_schemas/schemas/*.json``), together with a canonical
hash manifest (``HASHES.json``). Consumers *copy* those committed bytes; their
exact pin therefore *does* determine bytes. Regeneration from the pydantic
models is a repo-local developer command, restricted to the locked pydantic
version, so the committed artifacts stay canonical.

Modes (``python -m clio_schemas.export ...``)::

    --out DIR              Copy the committed schemas (incl. HASHES.json) to DIR.
    --out DIR --check      Verify DIR matches the committed schemas exactly
                           (file-set + bytes); reject extra/missing/stale files.
    --regenerate           DEV: re-render the committed package resources from
                           the models. Refuses unless the installed pydantic
                           equals LOCKED_PYDANTIC_VERSION.
    --verify               REPO CI: assert the committed resources are byte-
                           identical to a fresh render under the locked pydantic
                           and that HASHES.json matches their content.

Determinism: every JSON file is emitted with ``sort_keys=True`` (which also
stabilises ``$defs`` ordering), two-space indent, and a trailing newline.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.resources
import json
import re
import sys
from importlib.metadata import version as _dist_version
from pathlib import Path

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from clio_schemas.constants import (
    AGGREGATE_FILENAME,
    HASH_ALGORITHM,
    HASHES_FILENAME,
    LOCKED_PYDANTIC_VERSION,
)
from clio_schemas.models import EXPORTED_MODELS

__all__ = [
    "AGGREGATE_FILENAME",
    "HASHES_FILENAME",
    "HASH_ALGORITHM",
    "LOCKED_PYDANTIC_VERSION",
    "compute_hashes",
    "do_check_out",
    "do_copy",
    "do_regenerate",
    "do_verify",
    "main",
    "package_schema_dir",
    "read_committed",
    "render_aggregate_schema",
    "render_all",
    "render_bundle",
    "render_model_schema",
    "schema_filename",
]

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


# --------------------------------------------------------------------------- #
# Rendering (from models — dev/CI only)
# --------------------------------------------------------------------------- #
def schema_filename(model: type[BaseModel]) -> str:
    """Return the deterministic snake_case ``.json`` filename for a model.

    ``SchemaProbe`` -> ``schema_probe.json``.
    """

    return f"{_CAMEL_BOUNDARY.sub('_', model.__name__).lower()}.json"


def _dumps(payload: object) -> str:
    """Deterministic JSON serialisation used for every emitted file."""

    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_model_schema(model: type[BaseModel]) -> str:
    """Render one model's self-contained JSON Schema as a deterministic string."""

    return _dumps(model.model_json_schema())


def render_aggregate_schema(
    models: tuple[type[BaseModel], ...] = EXPORTED_MODELS,
) -> str:
    """Render the aggregate schema with a single shared ``$defs`` for all models.

    Shared definitions (e.g. an enum referenced by two models, or a nested
    model) appear exactly once, so the TypeScript generator emits each
    declaration once. The root object references every top-level model.
    """

    _, defs = models_json_schema(
        [(model, "validation") for model in models],
        ref_template="#/$defs/{model}",
    )
    aggregate = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://schemas.iowarp.dev/clio-schemas/index.json",
        "title": "ClioSchemaRegistry",
        "description": (
            "Aggregate of all canonical clio-schemas records with shared "
            "definitions emitted once. Used to generate TypeScript without "
            "duplicate declarations."
        ),
        "type": "object",
        "additionalProperties": False,
        "$defs": defs["$defs"],
        "properties": {model.__name__: {"$ref": f"#/$defs/{model.__name__}"} for model in models},
    }
    return _dumps(aggregate)


def render_all(
    models: tuple[type[BaseModel], ...] = EXPORTED_MODELS,
) -> dict[str, str]:
    """Render every schema file (per-model + aggregate) — excludes HASHES.json."""

    rendered = {schema_filename(model): render_model_schema(model) for model in models}
    rendered[AGGREGATE_FILENAME] = render_aggregate_schema(models)
    return rendered


def compute_hashes(rendered: dict[str, str]) -> dict[str, object]:
    """Return the canonical hash manifest for the rendered schema files."""

    files = {
        name: hashlib.sha256(content.encode("utf-8")).hexdigest()
        for name, content in sorted(rendered.items())
    }
    return {"algorithm": HASH_ALGORITHM, "files": files}


def render_hashes(rendered: dict[str, str]) -> str:
    """Render the hash manifest as a deterministic string."""

    return _dumps(compute_hashes(rendered))


def render_bundle(
    models: tuple[type[BaseModel], ...] = EXPORTED_MODELS,
) -> dict[str, str]:
    """Render the complete committed set: schemas + HASHES.json."""

    rendered = render_all(models)
    bundle = dict(rendered)
    bundle[HASHES_FILENAME] = render_hashes(rendered)
    return bundle


# --------------------------------------------------------------------------- #
# Committed package resources (what consumers copy)
# --------------------------------------------------------------------------- #
def package_schema_dir() -> Path:
    """Filesystem path to the committed schema resources inside the package."""

    return Path(str(importlib.resources.files("clio_schemas") / "schemas"))


def read_committed() -> dict[str, str]:
    """Read every committed ``.json`` schema resource as ``{filename: content}``."""

    schema_dir = package_schema_dir()
    if not schema_dir.is_dir():
        raise FileNotFoundError(
            f"committed schema resources missing at {schema_dir} — run "
            "`python -m clio_schemas.export --regenerate`"
        )
    return {
        path.name: path.read_text(encoding="utf-8") for path in sorted(schema_dir.glob("*.json"))
    }


def _write_dir(out_dir: Path, files: dict[str, str]) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, content in sorted(files.items()):
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def _diff_dirs(expected: dict[str, str], actual_dir: Path) -> list[str]:
    """Compare an on-disk directory of ``.json`` files against ``expected``.

    Reports missing, unexpected (extra/untracked), and stale (content-mismatch)
    files — exact file-set + byte equality.
    """

    problems: list[str] = []
    actual_names = {p.name for p in actual_dir.glob("*.json")} if actual_dir.is_dir() else set()
    expected_names = set(expected)

    for name in sorted(expected_names - actual_names):
        problems.append(f"missing: {name}")
    for name in sorted(actual_names - expected_names):
        problems.append(f"unexpected: {name} (not a canonical schema file)")
    for name in sorted(expected_names & actual_names):
        if (actual_dir / name).read_text(encoding="utf-8") != expected[name]:
            problems.append(f"stale: {name} (does not match committed bytes)")
    return problems


# --------------------------------------------------------------------------- #
# Modes
# --------------------------------------------------------------------------- #
def _require_locked_pydantic() -> None:
    installed = _dist_version("pydantic")
    if installed != LOCKED_PYDANTIC_VERSION:
        raise SystemExit(
            f"refusing to render schemas under pydantic {installed}; the "
            f"canonical artifacts are locked to pydantic "
            f"{LOCKED_PYDANTIC_VERSION}. Install the locked version "
            "(uv sync) and retry."
        )


def do_copy(out_dir: Path) -> int:
    """Consumer mode: copy the immutable committed schemas to ``out_dir``."""

    committed = read_committed()
    for path in _write_dir(out_dir, committed):
        print(f"copied {path}")
    return 0


def do_check_out(out_dir: Path) -> int:
    """Consumer CI: verify ``out_dir`` matches the committed schemas exactly."""

    committed = read_committed()
    problems = _diff_dirs(committed, out_dir)
    if problems:
        print("Schema copy drift detected:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"OK: {out_dir} matches {len(committed)} committed schema file(s)")
    return 0


def do_regenerate() -> int:
    """Dev mode: re-render the committed package resources from the models."""

    _require_locked_pydantic()
    bundle = render_bundle()
    schema_dir = package_schema_dir()
    # Remove orphaned committed files no longer produced by the models.
    if schema_dir.is_dir():
        for path in schema_dir.glob("*.json"):
            if path.name not in bundle:
                path.unlink()
                print(f"removed orphan {path}")
    for path in _write_dir(schema_dir, bundle):
        print(f"wrote {path}")
    return 0


def do_verify() -> int:
    """Repo CI: committed resources are canonical (match models + hashes)."""

    _require_locked_pydantic()
    expected = render_bundle()
    committed = read_committed()
    problems = _diff_dirs(expected, package_schema_dir())
    # Also confirm HASHES.json is internally consistent with the schema files.
    if HASHES_FILENAME in committed:
        recorded = json.loads(committed[HASHES_FILENAME])
        actual = compute_hashes({k: v for k, v in committed.items() if k != HASHES_FILENAME})
        if recorded != actual:
            problems.append(f"{HASHES_FILENAME} does not match the committed schema bytes")
    if problems:
        print("Committed schemas are not canonical:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "Regenerate with `python -m clio_schemas.export --regenerate`.",
            file=sys.stderr,
        )
        return 1
    print(f"OK: {len(expected)} committed schema file(s) are canonical")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m clio_schemas.export",
        description="Distribute / verify canonical JSON Schema for shared clio records.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Directory to copy the committed schemas into (consumer mode).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="With --out: verify the directory matches the committed schemas.",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="DEV: re-render committed package resources from the models (locked pydantic).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="REPO CI: assert committed resources are canonical (match models + hashes).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.regenerate:
        return do_regenerate()
    if args.verify:
        return do_verify()
    if args.out is not None:
        return do_check_out(args.out) if args.check else do_copy(args.out)

    parser.error("nothing to do: pass --out DIR, --regenerate, or --verify")
    return 2  # unreachable; argparse.error exits


if __name__ == "__main__":
    raise SystemExit(main())
