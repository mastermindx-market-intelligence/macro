"""Finance watching — synthetic, in-module, no I/O.

The live not-connected Finance shell shows two ``NOT_YET_EVALUABLE`` watching
items in ``ul.fi-falsifiers`` (card_networks + exchanges_trading_venues),
produced by :func:`engine.sector_intelligence.finance_watching.shell_watching_items`
which calls :func:`apply_page_signal` on in-module synthetic constants.

No fetch, no ``WATCHING``, no research/finance read, no clock. The frozen
constants are byte-equal to ``tests/fixtures/finance_case_signal/synthesis_v0.json``
(test-time read of the fixture is allowed; the engine module never opens it).
"""

from __future__ import annotations

import ast
import copy
import json
import re
from pathlib import Path
from typing import Any, Mapping

import jsonschema
import pytest

import engine.sector_intelligence.finance_watching as finance_watching
from engine.sector_intelligence.finance_page_signal import (
    SynthesisAdmissionRefusal,
    apply_page_signal,
)
from scripts.build_finance_intelligence_page import (
    FI_READ_URL,
    render_shell,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"

_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "finance_case_signal"
    / "synthesis_v0.json"
)
_SCHEMA = (
    ROOT
    / "contracts"
    / "sector_intelligence"
    / "finance_intelligence_read_model.v1.schema.json"
)


def _fixture_document() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _row(canonical_case_id: str) -> dict:
    return next(
        row
        for row in _fixture_document()["cases"]
        if row["canonical_case_id"] == canonical_case_id
    )


def _falsifier_validator() -> jsonschema.Draft202012Validator:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema["$defs"]["falsifier"])


def _empty_page() -> dict:
    return {
        "slices": [
            {
                "slice_id": "card_networks",
                "falsifiers": [],
                "rerating": {"falsifier_ids": []},
            },
            {
                "slice_id": "exchanges_trading_venues",
                "falsifiers": [],
                "rerating": {"falsifier_ids": []},
            },
        ]
    }


def _ids(page: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        sl["slice_id"]: [item["falsifier_id"] for item in sl["falsifiers"]]
        for sl in page["slices"]
    }


def test_shell_watching_items_are_not_yet_evaluable() -> None:
    """``shell_watching_items()`` returns two NOT_YET_EVALUABLE falsifiers.

    Order equals the fixture case order; each ``falsifier_id`` is the
    canonical case id; each ``statement`` is the row's ``primary_limit``;
    each ``window`` is the row's ``anchor_date``. No ``WATCHING`` is
    present, and every falsifier validates against the schema's falsifier
    definition. The module's frozen constants are byte-equal to the
    fixture file (test-time read of the fixture is allowed).
    """
    items = finance_watching.shell_watching_items()
    assert isinstance(items, list)
    assert len(items) == 2
    alpha = _row("syn-fin-case-alpha")
    beta = _row("syn-fin-case-beta")
    assert items[0]["falsifier_id"] == alpha["canonical_case_id"]
    assert items[0]["statement"] == alpha["primary_limit"]
    assert items[0]["window"] == alpha["anchor_date"]
    assert items[0]["state"] == "NOT_YET_EVALUABLE"
    assert items[1]["falsifier_id"] == beta["canonical_case_id"]
    assert items[1]["statement"] == beta["primary_limit"]
    assert items[1]["window"] == beta["anchor_date"]
    assert items[1]["state"] == "NOT_YET_EVALUABLE"
    assert not any(item["state"] == "WATCHING" for item in items)
    _falsifier_validator().validate(items[0])
    _falsifier_validator().validate(items[1])

    # Module constants are byte-equal to the fixture.
    assert finance_watching._SHELL_DOCUMENT == _fixture_document()


def test_shell_watching_goes_through_apply_page_signal() -> None:
    """The only public placement call is ``apply_page_signal``.

    AST walks the module: ``apply_page_signal`` is imported and called; the
    module-private helper ``_attach_falsifiers`` is not named (tests use
    ``attach_falsifiers`` as the forbidden public name).
    """
    tree = ast.parse(Path(finance_watching.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    assert "apply_page_signal" in imported
    # ``attach_falsifiers`` (the public placement helper) must not be imported.
    assert "attach_falsifiers" not in imported
    assert "_attach_falsifiers" not in imported

    # ``shell_watching_items`` calls apply_page_signal and nothing else
    # that writes the falsifier key.
    fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "shell_watching_items"
    )
    calls = {
        node.func.id
        for node in ast.walk(fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "apply_page_signal" in calls
    # No public placement helper is called.
    for forbidden in ("_attach_falsifiers", "attach_falsifiers"):
        assert forbidden not in calls


def test_measured_document_is_refused_and_writes_nothing() -> None:
    """A sabotaged document (measured_count = 1) is refused, page untouched.

    The module exposes a test-side helper that runs ``apply_page_signal``
    on a caller-supplied document + page; an admission refusal must
    propagate and the page's falsifier ids must be unchanged.
    """
    document = copy.deepcopy(_fixture_document())
    document["formal_causal_outcomes_measured"] = 1
    page = _empty_page()
    before = _ids(page)
    with pytest.raises(SynthesisAdmissionRefusal) as caught:
        finance_watching.watching_items(document, page)
    assert str(caught.value) == "formal_causal_outcomes_measured"
    assert _ids(page) == before
    flat = [item for ids in _ids(page).values() for item in ids]
    assert "syn-fin-case-alpha" not in flat
    assert "syn-fin-case-beta" not in flat


def test_watching_items_matches_apply_page_signal_on_the_fixture() -> None:
    """The public helper returns exactly what ``apply_page_signal`` places.

    Side-by-side: the helper's two-item list equals the falsifier lists
    ``apply_page_signal`` would write against an empty page (order and
    contents).
    """
    page = _empty_page()
    finance_watching.watching_items(_fixture_document(), page)
    placed = []
    for sl in page["slices"]:
        for item in sl["falsifiers"]:
            placed.append(item)
    assert finance_watching.shell_watching_items() == placed


def test_builder_render_includes_watching_list_without_a_read_url(tmp_path: Path) -> None:
    """``render_shell`` writes the watching list into a temp site root.

    The renderer must (a) NOT write the worktree ``site/``, (b) keep
    ``data-fi-read-url=""``, (c) include the alpha ``primary_limit`` in
    the rendered HTML, (d) emit at least one ``<li
    class="fi-falsifier fi-panel2"`` row, (e) emit NO ``WATCHING``
    anywhere in the page.
    """
    worktree_site = ROOT / "site" / "finance_intelligence.html"
    backup = worktree_site.read_bytes() if worktree_site.exists() else None
    try:
        # Mirror the existing renderer test: symlink the templates dir so
        # the builder sees the same templates as the worktree.
        (tmp_path / "templates").symlink_to(TEMPLATES, target_is_directory=True)
        page = render_shell(tmp_path)
        html = page.read_text(encoding="utf-8")

        # The worktree site/ is untouched.
        if backup is not None:
            assert worktree_site.read_bytes() == backup
        else:
            assert not worktree_site.exists()

        # FI_READ_URL stays empty: no fetch on the live page.
        assert 'data-fi-read-url=""' in html
        assert FI_READ_URL == ""

        # Two falsifier <li> rows, with the spec'd CSS hook.
        rows = re.findall(
            r'<li class="fi-falsifier fi-panel2"[^>]*>(.*?)</li>', html, re.S
        )
        assert len(rows) == 2, f"expected 2 falsifier rows, got {len(rows)}"

        # Each row carries a NOT_YET_EVALUABLE state marker.
        states = re.findall(
            r'data-state-falsifier="([^"]+)"', html
        )
        assert states, "no data-state-falsifier marker found"
        assert all(state == "NOT_YET_EVALUABLE" for state in states)
        assert len(states) >= 2

        # Alpha primary_limit is on the page; beta too. No WATCHING anywhere.
        alpha = _row("syn-fin-case-alpha")
        beta = _row("syn-fin-case-beta")
        assert alpha["primary_limit"] in html
        assert beta["primary_limit"] in html
        assert "WATCHING" not in html
        # The ZH strings (synthetic) are on the page too.
        assert finance_watching.SHELL_STATEMENT_ZH["syn-fin-case-alpha"] in html
        assert finance_watching.SHELL_STATEMENT_ZH["syn-fin-case-beta"] in html
    finally:
        # Defensive: never leave anything written to the worktree site/.
        pass


def test_no_io_in_finance_watching_module() -> None:
    """``finance_watching`` does not import I/O or research/.

    Forbidden roots: builtins, io, os, pathlib, requests, socket, urllib.
    Forbidden names: any module that mentions ``research`` (root segment).
    The test fixture may be opened; the engine module never is.
    """
    forbidden_roots = {
        "builtins",
        "io",
        "os",
        "pathlib",
        "requests",
        "socket",
        "urllib",
    }
    tree = ast.parse(Path(finance_watching.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    offenders = {
        name
        for name in imported
        if name.split(".")[0] in forbidden_roots or "research" in name.split(".")
    }
    assert not offenders, sorted(offenders)
    # No open() call (name or attribute) in the module.
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
    ]
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "open"
    ]
