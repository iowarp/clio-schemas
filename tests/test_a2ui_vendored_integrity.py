"""Integrity checks for the vendored A2UI 0.9.1 specification artifacts.

These tests run entirely offline against the files written by
``scripts/vendor_a2ui_spec.py`` (see that script's module docstring for the
vendoring recipe): every path recorded in a ``SOURCE.json`` manifest must
exist with the recorded sha256, the basic catalog must have the shape the
rest of the codebase assumes, every vendored example must be valid JSON, and
the core client-to-server envelope must declare the expected protocol
version enum.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

PACKAGE_DATA_ROOT = REPO_ROOT / "src" / "clio_schemas" / "schemas" / "a2ui" / "v0_9_1"
CORPUS_ROOT = REPO_ROOT / "tests" / "a2ui_corpus" / "v0_9_1"

SOURCE_ROOTS: tuple[Path, ...] = (PACKAGE_DATA_ROOT, CORPUS_ROOT)


def _load_manifest(source_root: Path) -> dict[str, Any]:
    manifest_path = source_root / "SOURCE.json"
    assert manifest_path.is_file(), f"missing manifest: {manifest_path}"
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest_entries() -> list[tuple[Path, str, dict[str, str]]]:
    """Flatten every (source_root, relative_path, meta) triple across manifests."""

    entries: list[tuple[Path, str, dict[str, str]]] = []
    for source_root in SOURCE_ROOTS:
        manifest = _load_manifest(source_root)
        for relative_path, meta in manifest["files"].items():
            entries.append((source_root, relative_path, meta))
    return entries


class TestSourceManifests:
    """(a) Every path in both SOURCE.json manifests exists with a matching sha256."""

    @pytest.mark.parametrize(
        "source_root",
        SOURCE_ROOTS,
        ids=[str(root.relative_to(REPO_ROOT)) for root in SOURCE_ROOTS],
    )
    def test_manifest_pins_expected_commit(self, source_root: Path) -> None:
        manifest = _load_manifest(source_root)
        assert manifest["repository"] == "google/A2UI"
        assert manifest["commit"] == "0086493c40b119a4143fe15197006678467cad60"
        assert manifest["files"], "manifest lists no files"

    @pytest.mark.parametrize(
        "source_root,relative_path,meta",
        _manifest_entries(),
        ids=[f"{root.name}:{path}" for root, path, _ in _manifest_entries()],
    )
    def test_vendored_file_matches_manifest(
        self, source_root: Path, relative_path: str, meta: dict[str, str]
    ) -> None:
        file_path = source_root / relative_path
        assert file_path.is_file(), f"missing vendored file: {file_path}"
        actual = _sha256_hex(file_path.read_bytes())
        assert actual == meta["sha256"], (
            f"sha256 mismatch for {file_path}: expected {meta['sha256']}, got {actual}"
        )
        assert meta["upstream_path"], f"missing upstream_path for {relative_path}"


@pytest.fixture(scope="module")
def catalog() -> dict[str, Any]:
    catalog_path = PACKAGE_DATA_ROOT / "catalogs" / "basic" / "catalog.json"
    return json.loads(catalog_path.read_text(encoding="utf-8"))


class TestBasicCatalog:
    """(b) The basic catalog parses and matches the official 0.9.1 shape."""

    def test_catalog_id(self, catalog: dict[str, Any]) -> None:
        assert (
            catalog["catalogId"]
            == "https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json"
        )

    def test_component_count(self, catalog: dict[str, Any]) -> None:
        assert len(catalog["components"]) == 18

    def test_function_count(self, catalog: dict[str, Any]) -> None:
        assert len(catalog["functions"]) == 14


class TestExamplesParse:
    """(c) Every vendored example parses as JSON."""

    @pytest.mark.parametrize(
        "example_path",
        sorted((CORPUS_ROOT / "examples").glob("*.json")),
        ids=lambda p: p.name,
    )
    def test_example_parses(self, example_path: Path) -> None:
        payload = json.loads(example_path.read_text(encoding="utf-8"))
        assert payload is not None

    def test_examples_directory_is_non_empty(self) -> None:
        examples = sorted((CORPUS_ROOT / "examples").glob("*.json"))
        assert len(examples) == 43


class TestClientToServerVersion:
    """(d) client_to_server.json declares the expected protocol version enum."""

    def test_version_enum(self) -> None:
        schema_path = PACKAGE_DATA_ROOT / "client_to_server.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        assert schema["properties"]["version"]["enum"] == ["v0.9", "v0.9.1"]
