"""Unit tests for the version-bump enforcement core (scripts/check_version_bump.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_version_bump",
    Path(__file__).resolve().parents[1] / "scripts" / "check_version_bump.py",
)
assert _SPEC and _SPEC.loader
cvb = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cvb)


def test_unchanged_hashes_never_requires_bump() -> None:
    assert cvb.requires_bump("H", "H", "0.1.0", "0.1.0") is None


def test_changed_hashes_without_bump_fails() -> None:
    assert cvb.requires_bump("H1", "H2", "0.1.0", "0.1.0") is not None


def test_changed_hashes_with_bump_passes() -> None:
    assert cvb.requires_bump("H1", "H2", "0.1.0", "0.1.1") is None


def test_downgrade_is_not_an_increment() -> None:
    assert cvb.requires_bump("H1", "H2", "0.2.0", "0.1.0") is not None


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ("0.1.0", "0.1.1", True),
        ("0.1.0", "0.2.0", True),
        ("0.1.0", "1.0.0", True),
        ("0.1.0", "0.1.0", False),
        ("0.2.0", "0.1.9", False),
    ],
)
def test_is_increment(old: str, new: str, expected: bool) -> None:
    assert cvb.is_increment(old, new) is expected


def test_extract_version() -> None:
    src = 'x = 1\n__version__ = "1.2.3"\n'
    assert cvb.extract_version(src) == "1.2.3"
