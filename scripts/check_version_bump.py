"""Fail CI if the schema hash manifest changed without a version increment.

The mechanical enforcement behind exact-pin lockstep (issue #1110): any change
to the canonical schema bytes (reflected in ``HASHES.json``) MUST be accompanied
by an increment of ``clio_schemas.__version__``, so consumers are forced to move
their exact pin. This script compares the current tree against a merge base
(default ``origin/main``) using ``git show`` and exits non-zero on a violation.

Run in CI::

    python scripts/check_version_bump.py --base origin/main

The comparison core (:func:`requires_bump` / :func:`is_increment`) is pure and
unit-tested; only :func:`main` touches git.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

HASHES_PATH = "src/clio_schemas/schemas/HASHES.json"
INIT_PATH = "src/clio_schemas/__init__.py"


def parse_version(text: str) -> tuple[int, int, int]:
    """Parse a ``MAJOR.MINOR.PATCH`` string into a comparable tuple."""

    parts = text.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"not a MAJOR.MINOR.PATCH version: {text!r}")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def is_increment(old: str, new: str) -> bool:
    """True if ``new`` is a strictly greater semantic version than ``old``."""

    return parse_version(new) > parse_version(old)


def extract_version(init_source: str) -> str:
    """Pull ``__version__ = "X.Y.Z"`` out of an ``__init__.py`` source string."""

    import re

    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_source, re.MULTILINE)
    if not match:
        raise ValueError("could not find __version__ in __init__.py")
    return match.group(1)


def requires_bump(
    old_hashes: str,
    new_hashes: str,
    old_version: str,
    new_version: str,
) -> str | None:
    """Return an error message if a version bump is required but missing.

    Returns ``None`` when the change is compliant: either the hashes are
    unchanged, or the version was incremented alongside a hash change.
    """

    if old_hashes == new_hashes:
        return None
    if is_increment(old_version, new_version):
        return None
    return (
        "schema HASHES.json changed but __version__ was not incremented "
        f"(base={old_version}, head={new_version}). Bump the version in lockstep."
    )


def _git_show(ref: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Path did not exist at the base ref (e.g. first commit of the file).
        return ""
    return result.stdout


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main", help="Git ref to diff against.")
    args = parser.parse_args(argv)

    old_hashes = _git_show(args.base, HASHES_PATH)
    new_hashes = _read(HASHES_PATH)
    old_init = _git_show(args.base, INIT_PATH)
    old_version = extract_version(old_init) if old_init else "0.0.0"
    new_version = extract_version(_read(INIT_PATH))

    problem = requires_bump(old_hashes, new_hashes, old_version, new_version)
    if problem:
        print(f"version-bump check failed: {problem}", file=sys.stderr)
        return 1
    print("version-bump check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
