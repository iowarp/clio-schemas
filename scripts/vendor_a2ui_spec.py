"""Vendor the official A2UI 0.9.1 specification artifacts from google/A2UI.

Downloads a pinned set of files from the upstream `google/A2UI
<https://github.com/google/A2UI>`_ repository, at a single locked commit
(:data:`A2UI_COMMIT`), and writes them verbatim (no newline normalisation,
binary write) into this repository:

* Package data (shipped in the wheel) under
  ``src/clio_schemas/schemas/a2ui/v0_9_1/``: the ten core JSON Schemas
  (everything under ``specification/v0_9_1/json/`` except ``sample.json``)
  plus the basic catalog (``catalogs/basic/catalog.json`` and
  ``catalogs/basic/rules.txt``).
* Test corpus (not shipped) under ``tests/a2ui_corpus/v0_9_1/``: every file
  under ``specification/v0_9_1/test/cases/``, the test ``README.md`` and
  ``run_tests.py`` (reference only, not executed by this repo's test suite),
  and every example under ``specification/v0_9_1/catalogs/basic/examples/``.
* The upstream ``LICENSE`` (Apache-2.0), copied to
  ``src/clio_schemas/schemas/a2ui/LICENSE``, plus a locally authored
  ``NOTICE`` describing the provenance of the vendored tree.

Each vendored root (the package-data ``v0_9_1/`` directory and the test-corpus
``v0_9_1/`` directory) gets its own ``SOURCE.json`` manifest recording the
repository, the pinned commit, the retrieval timestamp, and a sha256 of every
vendored file — the integrity record this script's ``--verify`` mode checks
against, offline.

Usage::

    # Download every vendored file and (re)write the SOURCE.json manifests.
    uv run python scripts/vendor_a2ui_spec.py

    # Recompute sha256 of every vendored file and compare against the
    # committed SOURCE.json manifests. No network access. Exits 1 on any
    # mismatch or missing file.
    uv run python scripts/vendor_a2ui_spec.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# The single commit the vendored tree is pinned to. Every download in this
# script is byte-addressed by this commit, so re-running it is reproducible.
A2UI_COMMIT = "0086493c40b119a4143fe15197006678467cad60"
A2UI_REPOSITORY = "google/A2UI"

_RAW_BASE = f"https://raw.githubusercontent.com/{A2UI_REPOSITORY}/{A2UI_COMMIT}"
_API_CONTENTS_TEMPLATE = (
    f"https://api.github.com/repos/{A2UI_REPOSITORY}/contents/{{path}}?ref={A2UI_COMMIT}"
)
_USER_AGENT = "clio-schemas-vendor-a2ui-spec-script"

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DATA_ROOT = REPO_ROOT / "src" / "clio_schemas" / "schemas" / "a2ui"
PACKAGE_DATA_VERSION_ROOT = PACKAGE_DATA_ROOT / "v0_9_1"
CORPUS_VERSION_ROOT = REPO_ROOT / "tests" / "a2ui_corpus" / "v0_9_1"

SOURCE_MANIFEST_NAME = "SOURCE.json"

# The ten core specification JSON Schemas (sample.json is deliberately
# excluded — it is example wire data, not a schema).
SPEC_JSON_STEMS = (
    "client_capabilities",
    "client_data_model",
    "client_to_server",
    "client_to_server_list",
    "client_to_server_list_wrapper",
    "common_types",
    "server_capabilities",
    "server_to_client",
    "server_to_client_list",
    "server_to_client_list_wrapper",
)

_SPEC_JSON_DIR = "specification/v0_9_1/json"
_CATALOG_BASIC_DIR = "specification/v0_9_1/catalogs/basic"
_TEST_DIR = "specification/v0_9_1/test"
_TEST_CASES_DIR = f"{_TEST_DIR}/cases"
_EXAMPLES_DIR = f"{_CATALOG_BASIC_DIR}/examples"


@dataclass(frozen=True)
class VendoredFile:
    """One file vendored verbatim from the upstream A2UI repository.

    Attributes:
        upstream_path: Path of the file inside the A2UI repository at the
            pinned commit (:data:`A2UI_COMMIT`).
        dest_path: Local filesystem path the file's bytes are written to.
        manifest_root: Directory whose ``SOURCE.json`` this file is recorded
            under; ``dest_path`` must be inside this directory.
    """

    upstream_path: str
    dest_path: Path
    manifest_root: Path


def _http_get(url: str) -> bytes:
    """Fetch raw bytes from ``url``.

    Args:
        url: Absolute HTTP(S) URL to fetch.

    Returns:
        The response body, unmodified.

    Raises:
        urllib.error.URLError: If the request fails (including HTTP errors,
            which subclass ``URLError``).
    """
    request = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return response.read()


def _list_directory_via_gh(path: str) -> bytes:
    """List an upstream directory via the authenticated ``gh api`` CLI.

    Fallback used ONLY for directory listings (never for vendored file
    bytes) when the anonymous GitHub contents API is rate-limited.

    Args:
        path: Directory path within the A2UI repository.

    Returns:
        The raw JSON response body from ``gh api``, matching the shape of
        the GitHub contents API.

    Raises:
        subprocess.CalledProcessError: If the ``gh`` CLI invocation fails.
    """
    endpoint = f"repos/{A2UI_REPOSITORY}/contents/{path}?ref={A2UI_COMMIT}"
    result = subprocess.run(  # noqa: S603
        ["gh", "api", endpoint],
        capture_output=True,
        check=True,
    )
    return result.stdout


def list_directory(path: str) -> list[str]:
    """List file names (non-recursive) in an upstream directory.

    Args:
        path: Directory path within the A2UI repository, at the pinned
            commit.

    Returns:
        Sorted file names directly inside ``path`` (sub-directories, if any,
        are excluded).

    Raises:
        urllib.error.URLError: If both the anonymous API call and the
            ``gh api`` fallback fail.
    """
    url = _API_CONTENTS_TEMPLATE.format(path=path)
    try:
        payload = _http_get(url)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            payload = _list_directory_via_gh(path)
        else:
            raise
    entries = json.loads(payload)
    return sorted(entry["name"] for entry in entries if entry["type"] == "file")


def sha256_hex(data: bytes) -> str:
    """Return the lowercase hex sha256 digest of ``data``."""

    return hashlib.sha256(data).hexdigest()


def _relative_key(dest_path: Path, manifest_root: Path) -> str:
    """Return ``dest_path`` as a POSIX-style path relative to ``manifest_root``."""

    return dest_path.relative_to(manifest_root).as_posix()


def build_manifest() -> list[VendoredFile]:
    """Enumerate every file this script vendors, with its destination.

    Performs the two directory listing calls (test cases, examples) against
    the live GitHub API — this is the only part of the manifest that
    requires network access before download.

    Returns:
        The full list of files to download and write.
    """
    files: list[VendoredFile] = []

    # (a) Package data: the ten core JSON Schemas.
    for stem in SPEC_JSON_STEMS:
        name = f"{stem}.json"
        files.append(
            VendoredFile(
                upstream_path=f"{_SPEC_JSON_DIR}/{name}",
                dest_path=PACKAGE_DATA_VERSION_ROOT / name,
                manifest_root=PACKAGE_DATA_VERSION_ROOT,
            )
        )

    # (a) Package data: the basic catalog + its rules.
    for name in ("catalog.json", "rules.txt"):
        files.append(
            VendoredFile(
                upstream_path=f"{_CATALOG_BASIC_DIR}/{name}",
                dest_path=PACKAGE_DATA_VERSION_ROOT / "catalogs" / "basic" / name,
                manifest_root=PACKAGE_DATA_VERSION_ROOT,
            )
        )

    # (b) Test corpus: every file under specification/v0_9_1/test/cases/.
    for name in list_directory(_TEST_CASES_DIR):
        files.append(
            VendoredFile(
                upstream_path=f"{_TEST_CASES_DIR}/{name}",
                dest_path=CORPUS_VERSION_ROOT / name,
                manifest_root=CORPUS_VERSION_ROOT,
            )
        )

    # (b) Test corpus: the test README and the reference-only runner.
    for name in ("README.md", "run_tests.py"):
        files.append(
            VendoredFile(
                upstream_path=f"{_TEST_DIR}/{name}",
                dest_path=CORPUS_VERSION_ROOT / name,
                manifest_root=CORPUS_VERSION_ROOT,
            )
        )

    # (b) Test corpus: every basic-catalog example.
    for name in list_directory(_EXAMPLES_DIR):
        files.append(
            VendoredFile(
                upstream_path=f"{_EXAMPLES_DIR}/{name}",
                dest_path=CORPUS_VERSION_ROOT / "examples" / name,
                manifest_root=CORPUS_VERSION_ROOT,
            )
        )

    return files


def _write_source_manifest(manifest_root: Path, files_meta: dict[str, dict[str, str]]) -> Path:
    """Write ``manifest_root/SOURCE.json`` deterministically.

    Args:
        manifest_root: Directory the manifest describes and is written into.
        files_meta: Mapping of relative path -> ``{"upstream_path", "sha256"}``.

    Returns:
        The path written.
    """
    retrieved_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "repository": A2UI_REPOSITORY,
        "commit": A2UI_COMMIT,
        "retrieved_at": retrieved_at,
        "files": files_meta,
    }
    manifest_path = manifest_root / SOURCE_MANIFEST_NAME
    # newline="" disables platform newline translation (e.g. \n -> \r\n on
    # Windows) so the manifest is byte-identical regardless of platform.
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="",
    )
    return manifest_path


def _write_license_and_notice() -> None:
    """Download the upstream LICENSE and author the NOTICE file."""

    license_bytes = _http_get(f"{_RAW_BASE}/LICENSE")
    PACKAGE_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    license_path = PACKAGE_DATA_ROOT / "LICENSE"
    license_path.write_bytes(license_bytes)
    print(f"vendored LICENSE -> {license_path}")

    notice = (
        "A2UI specification vendor notice\n"
        "=================================\n\n"
        f"The files under this directory are vendored verbatim from the\n"
        f"upstream {A2UI_REPOSITORY} repository "
        f"(https://github.com/{A2UI_REPOSITORY})\n"
        f"at commit {A2UI_COMMIT}, unmodified, under the terms of the\n"
        "Apache License, Version 2.0 (see LICENSE in this directory).\n\n"
        "Provenance (repository, commit, retrieval timestamp, and a sha256\n"
        "per file) is recorded in each vendored subtree's SOURCE.json, e.g.\n"
        "v0_9_1/SOURCE.json. Regenerate this tree with\n"
        "scripts/vendor_a2ui_spec.py; verify it offline with\n"
        "scripts/vendor_a2ui_spec.py --verify.\n"
    )
    notice_path = PACKAGE_DATA_ROOT / "NOTICE"
    notice_path.write_text(notice, encoding="utf-8", newline="")
    print(f"wrote {notice_path}")


def download_and_write(files: list[VendoredFile]) -> None:
    """Download every file in ``files`` verbatim and write the SOURCE.json manifests.

    Args:
        files: The manifest produced by :func:`build_manifest`.
    """
    manifests: dict[Path, dict[str, dict[str, str]]] = {}
    for vendored in files:
        data = _http_get(f"{_RAW_BASE}/{vendored.upstream_path}")
        vendored.dest_path.parent.mkdir(parents=True, exist_ok=True)
        # Verbatim bytes: binary write, no newline normalisation.
        vendored.dest_path.write_bytes(data)
        key = _relative_key(vendored.dest_path, vendored.manifest_root)
        manifests.setdefault(vendored.manifest_root, {})[key] = {
            "upstream_path": vendored.upstream_path,
            "sha256": sha256_hex(data),
        }
        print(f"vendored {vendored.upstream_path} -> {vendored.dest_path}")

    for manifest_root, files_meta in manifests.items():
        manifest_path = _write_source_manifest(manifest_root, files_meta)
        print(f"wrote {manifest_path} ({len(files_meta)} file(s))")

    _write_license_and_notice()


_DEFAULT_MANIFEST_ROOTS = (PACKAGE_DATA_VERSION_ROOT, CORPUS_VERSION_ROOT)


def verify(manifest_roots: tuple[Path, ...] = _DEFAULT_MANIFEST_ROOTS) -> int:
    """Recompute sha256 of every vendored file and compare against SOURCE.json.

    Performs no network access.

    Args:
        manifest_roots: Directories whose ``SOURCE.json`` manifests to check.

    Returns:
        ``0`` if every listed file exists and matches; ``1`` otherwise.
    """
    ok = True
    total_checked = 0
    for manifest_root in manifest_roots:
        manifest_path = manifest_root / SOURCE_MANIFEST_NAME
        if not manifest_path.is_file():
            print(f"ERROR: missing manifest {manifest_path}", file=sys.stderr)
            ok = False
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("commit") != A2UI_COMMIT:
            print(
                f"ERROR: {manifest_path} pins commit {manifest.get('commit')!r}, "
                f"expected {A2UI_COMMIT!r}",
                file=sys.stderr,
            )
            ok = False
        for rel_path, meta in sorted(manifest.get("files", {}).items()):
            total_checked += 1
            file_path = manifest_root / rel_path
            if not file_path.is_file():
                print(f"ERROR: missing vendored file {file_path}", file=sys.stderr)
                ok = False
                continue
            expected = meta["sha256"]
            actual = sha256_hex(file_path.read_bytes())
            if actual != expected:
                print(
                    f"ERROR: sha256 mismatch for {file_path}: expected {expected}, got {actual}",
                    file=sys.stderr,
                )
                ok = False

    if ok:
        print(f"OK: {total_checked} vendored file(s) match their SOURCE.json manifest")
    return 0 if ok else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/vendor_a2ui_spec.py",
        description=(
            "Vendor the official A2UI 0.9.1 specification artifacts from "
            f"{A2UI_REPOSITORY} at the pinned commit {A2UI_COMMIT}."
        ),
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help=(
            "Recompute sha256 of every vendored file and compare against "
            "SOURCE.json. No network access. Exits 1 on any mismatch."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.verify:
        return verify()

    files = build_manifest()
    download_and_write(files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
