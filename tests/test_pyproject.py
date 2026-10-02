# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""pyproject.toml and core/version.py must never disagree.

``core/version.py`` is the single source of truth for the application version
(it is what ``main.py`` prints, what ``ingetrazo.spec`` stamps into the Windows
resources and what the release workflows tag).  uv 0.12.5 offers no
``[tool.uv] version-path``, so ``pyproject.toml`` has to repeat the number
statically.  This test is what keeps that repetition honest: it fails the
moment someone bumps one file and forgets the other.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

from core.version import __version__

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_pyproject_version_matches_core_version():
    """The static version in pyproject.toml equals core.version.__version__."""
    with PYPROJECT.open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["version"] == __version__, (
        f"pyproject.toml says {data['project']['version']!r} but "
        f"core/version.py says {__version__!r}; bump them together"
    )


def test_openskp_stays_pinned_to_the_approved_commit():
    """openskp resolves to the exact approved SHA, by git + rev + subdirectory.

    Installers have to be reproducible, so a drifting or unpinned openskp is a
    release bug rather than a convenience.
    """
    with PYPROJECT.open("rb") as fh:
        data = tomllib.load(fh)
    source = data["tool"]["uv"]["sources"]["openskp"]
    assert source["git"] == "https://github.com/iamahsanmehmood/openskp"
    assert re.fullmatch(r"[0-9a-f]{40}", source["rev"]), (
        "openskp must be pinned to a full 40-character commit SHA"
    )
    assert source["rev"] == "291700bc213655a00461838de71e5f206311e619", (
        "openskp revision changed; that needs a deliberate contract decision"
    )
    assert source["subdirectory"] == "packages/python"


def test_runtime_dependencies_are_exactly_the_five_agreed():
    """No runtime dependency is added or dropped without a decision."""
    with PYPROJECT.open("rb") as fh:
        data = tomllib.load(fh)
    declared = data["project"]["dependencies"]
    names = sorted(re.split(r"[><=!~ ]", d, maxsplit=1)[0].lower() for d in declared)
    assert names == sorted(
        ["pyside6", "numpy", "openskp", "ezdxf", "manifold3d"]
    ), f"unexpected runtime dependency set: {names}"


def test_dev_group_is_pytest_only():
    """The migration adds no linter, type checker or extra build tooling."""
    with PYPROJECT.open("rb") as fh:
        data = tomllib.load(fh)
    dev = data["dependency-groups"]["dev"]
    assert [re.split(r"[><=!~ ]", d, maxsplit=1)[0].lower() for d in dev] == ["pytest"]


def test_project_is_not_configured_as_an_installable_package():
    """No build backend: the repo stays source-on-path, as the app expects."""
    text = PYPROJECT.read_text(encoding="utf-8")
    assert "[build-system]" not in text, (
        "pyproject.toml must not introduce a build backend"
    )