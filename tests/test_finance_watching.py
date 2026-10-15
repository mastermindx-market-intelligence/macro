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
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping

import jsonschema
import pytest

import engine.sector_intelligence.finance_watching as finance_watching
from engine.sector_intelligence.finance_page_signal import (
    SynthesisAdmissionRefusal,
    apply_page_signal,
)
from engine.sector_intelligence.finance_witness_hints import (
    FinanceWitnessHintRefusal,
    hint_binding,
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


_JS_CHIP_PAIR_RE = re.compile(
    r"NOT_YET_EVALUABLE:\s*\['([^']*)',\s*'([^']*)'\]"
)


def _js_chip_pair() -> tuple[str, str]:
    """Parse the governed EN/ZH chip label pair out of the page JS.

    ``templates/finance_intelligence.js`` D.18 ``falsifier_state`` is the
    canonical bilingual chip copy; the include must match it exactly, so
    the label test reads the pair back out of that file instead of
    hardcoding a second copy that could drift.
    """
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    match = _JS_CHIP_PAIR_RE.search(js)
    assert match, "NOT_YET_EVALUABLE chip pair not found in the page JS"
    return match.group(1), match.group(2)


class _VisibleTextCollector(HTMLParser):
    """Collect visible text nodes; <script>/<style> bodies are not visible."""

    def __init__(self) -> None:
        super().__init__()
        self.texts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.texts.append(data)


def _visible_texts(html: str) -> list[str]:
    collector = _VisibleTextCollector()
    collector.feed(html)
    return collector.texts


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


def test_shell_watching_items_raises_on_refused_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production fail-closed: the shell path lets the refusal propagate.

    Reviewer mutant mC2 wrapped ``apply_page_signal`` inside
    ``shell_watching_items`` in ``try/except Exception: return []``.
    This test pins the shipped behaviour: sabotage the module's shell
    document exactly the way the review gate refuses (formal count 1),
    reset the memo, and require ``SynthesisAdmissionRefusal`` to surface
    while the memo stays unset (nothing partially memoized, page intact).
    """
    sabotaged = copy.deepcopy(finance_watching._SHELL_DOCUMENT)
    sabotaged["formal_causal_outcomes_measured"] = 1
    monkeypatch.setattr(finance_watching, "_SHELL_DOCUMENT", sabotaged)
    monkeypatch.setattr(finance_watching, "_WATCHING_ITEMS", None)
    with pytest.raises(SynthesisAdmissionRefusal) as caught:
        finance_watching.shell_watching_items()
    assert str(caught.value) == "formal_causal_outcomes_measured"
    assert finance_watching._WATCHING_ITEMS is None


def test_finance_watching_module_has_no_try() -> None:
    """AST pin: no ``try`` block anywhere in finance_watching.py.

    The module's contract is propagation: an admission refusal reaches
    the caller and the page stays as it was. Any ``try/except`` is a
    fail-open hole that turns a refusal into a silent empty watching
    list (mC2). Version-robust: ``ast.TryStar`` is checked when present.
    """
    tree = ast.parse(Path(finance_watching.__file__).read_text(encoding="utf-8"))
    node_types: tuple[type, ...] = (ast.Try,)
    if hasattr(ast, "TryStar"):
        node_types += (ast.TryStar,)
    found = [node for node in ast.walk(tree) if isinstance(node, node_types)]
    assert not found, f"{len(found)} try block(s) in finance_watching.py"


def test_shell_watching_items_raises_on_unexpected_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P3 pin: a placed falsifier in a foreign state raises, never vanishes.

    The state filter used to ``continue`` silently; a placement that is
    not NOT_YET_EVALUABLE breaks the review-gate contract, so the bridge
    raises ``ValueError`` naming the state and leaves the memo unset.
    """

    def _fake_apply(document, page):
        page["slices"][0]["falsifiers"].append(
            {
                "falsifier_id": "syn-fake-watcher",
                "statement": "Synthetic foreign placement.",
                "window": "2024-01-01",
                "state": "WATCHING",
            }
        )

    monkeypatch.setattr(finance_watching, "apply_page_signal", _fake_apply)
    monkeypatch.setattr(finance_watching, "_WATCHING_ITEMS", None)
    with pytest.raises(ValueError) as caught:
        finance_watching.shell_watching_items()
    assert "WATCHING" in str(caught.value)
    assert finance_watching._WATCHING_ITEMS is None


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


def test_shell_watching_items_returns_independent_copies() -> None:
    """P3 pin: callers get copies of the memo's dicts, not the dicts.

    ``list(memo)`` shared every dict object, so a caller mutation leaked
    into the memo and every later call. Mutate the returned items; a
    fresh call must still return the pristine frozen projections.
    """
    first = finance_watching.shell_watching_items()
    snapshot = copy.deepcopy(first)
    first[0]["statement"] = "MUTATED-BY-CALLER"
    first[0]["state"] = "WATCHING"
    first[1]["injected_key"] = "leak"
    second = finance_watching.shell_watching_items()
    assert second == snapshot
    assert "injected_key" not in second[1]


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
    # Mirror the existing renderer test: symlink the templates dir so
    # the builder sees the same templates as the worktree.
    (tmp_path / "templates").symlink_to(TEMPLATES, target_is_directory=True)
    page = render_shell(tmp_path)
    html = page.read_text(encoding="utf-8")

    # The worktree site/ is untouched — render_shell wrote only tmp_path.
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


def test_watching_chip_label_is_localized(tmp_path: Path) -> None:
    """P2: the visible chip text is the governed pair, not the raw enum.

    The chip keeps the machine token in ``data-state-falsifier`` (the
    render test above reads it) while the visible text becomes the D.18
    ``falsifier_state`` pair from ``templates/finance_intelligence.js``.
    The pair is parsed back out of that file, so template and JS can
    never drift silently.
    """
    en, zh = _js_chip_pair()
    (tmp_path / "templates").symlink_to(TEMPLATES, target_is_directory=True)
    html = render_shell(tmp_path).read_text(encoding="utf-8")
    # Literal visible pair, as commissioned ...
    assert ">Not yet evaluable<" in html
    assert ">暂无法评估<" in html
    # ... and the same pair parsed from the governed JS map (drift guard).
    assert f">{en}<" in html
    assert f">{zh}<" in html
    # No element's visible text equals the machine token (attributes ok).
    hits = [t for t in _visible_texts(html) if t.strip() == "NOT_YET_EVALUABLE"]
    assert not hits, "raw enum leaking as visible chip text"
    # The machine token stays in the data attribute the render test reads.
    assert 'data-state-falsifier="NOT_YET_EVALUABLE"' in html


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


# ──────────────────────────────────────────────────────────────────────────
# W10-FIN-2 — hint roster with record-id citations (no source_record)
# ──────────────────────────────────────────────────────────────────────────

# Plain strings transcribed from refs/grok/pr/7786 preflight witnesses
# (FINANCE_R12_INTEGRATION_PREFLIGHT_V0_1_2026-09-24.json lines 266-318).
# Same table as tests/test_finance_witness_hints.py:33-45; this test does
# not open the preflight file. BNY keeps fin-research-bk-2025; BK is not a
# symbol.
_PREFLIGHT_RECORD_IDS = {
    "V": "fin-research-v-2025",
    "MA": "fin-research-ma-2025",
    "FI": "fin-research-fi-2025",
    "FIS": "fin-research-fis-2025",
    "CME": "fin-research-cme-2025",
    "ICE": "fin-research-ice-2025",
    "NDAQ": "fin-research-ndaq-2025",
    "BNY": "fin-research-bk-2025",
    "STT": "fin-research-stt-2025",
    "SPGI": "fin-research-spgi-2025",
    "MCO": "fin-research-mco-2025",
}


def test_shell_hint_rows_match_transcribed_preflight() -> None:
    """``shell_hint_rows()`` returns the eleven roster rows, ids verbatim.

    The row dict's ``record_id`` is the binding's id (``hint_binding``'s
    ``record_id``), not an identity key: the row carries exactly
    ``symbol``/``record_id``/``state`` — no ``href``, no identity fields,
    nothing copied from measurement JSON. State is
    ``RESEARCH_HINT_UNVALIDATED``; ``BK`` and ``GHOST`` are not rows.
    """
    rows = finance_watching.shell_hint_rows()
    assert isinstance(rows, list)
    assert len(rows) == 11
    assert [row["symbol"] for row in rows] == list(_PREFLIGHT_RECORD_IDS)
    for row in rows:
        assert set(row) == {"symbol", "record_id", "state"}
        assert row["record_id"] == _PREFLIGHT_RECORD_IDS[row["symbol"]]
        assert row["record_id"] == hint_binding(row["symbol"])["record_id"]
        assert row["state"] == "RESEARCH_HINT_UNVALIDATED"
    assert not any(row["symbol"] in ("BK", "GHOST") for row in rows)
    # BK is not an alias/symbol of the roster — the binding refuses it.
    with pytest.raises(FinanceWitnessHintRefusal):
        hint_binding("BK")


def test_hint_roster_html_has_no_stock_route(tmp_path: Path) -> None:
    """The builder temp render shows the roster inside #company-exposure.

    Eleven ``fi-hint-row`` items carry ``data-record-id`` equal to the
    transcribed preflight ids and ``data-state-identity=
    "RESEARCH_HINT_UNVALIDATED"``. The roster emits no stock route
    (``company_route.href`` is not rendered; no href at all) and no
    ``IDENTITY_VALIDATED``. As in the FIN-1 render test, the worktree
    ``site/`` is never written.
    """
    worktree_site = ROOT / "site" / "finance_intelligence.html"
    backup = worktree_site.read_bytes() if worktree_site.exists() else None
    try:
        (tmp_path / "templates").symlink_to(TEMPLATES, target_is_directory=True)
        page = render_shell(tmp_path)
        html = page.read_text(encoding="utf-8")

        if backup is not None:
            assert worktree_site.read_bytes() == backup
        else:
            assert not worktree_site.exists()

        section_match = re.search(
            r'<section id="company-exposure".*?</section>', html, re.S
        )
        assert section_match, "#company-exposure section missing from render"
        block = section_match.group(0)

        roster_match = re.search(
            r'<ul class="fi-hint-roster".*?</ul>', block, re.S
        )
        assert roster_match, "no ul.fi-hint-roster inside #company-exposure"
        roster = roster_match.group(0)

        row_tags = re.findall(r'<li class="fi-hint-row"[^>]*>', roster)
        assert len(row_tags) == 11, f"expected 11 hint rows, got {len(row_tags)}"

        # The binding's ids are copied into HTML attributes …
        assert 'data-record-id="fin-research-v-2025"' in block
        assert 'data-state-identity="RESEARCH_HINT_UNVALIDATED"' in block
        for symbol, record_id in _PREFLIGHT_RECORD_IDS.items():
            assert f'data-record-id="{record_id}"' in block, symbol
        # … and into visible citation text (each id appears in its row body).
        for symbol, record_id in _PREFLIGHT_RECORD_IDS.items():
            assert f">{record_id}<" in roster, symbol

        # No stock route, no validated identity on those rows.
        assert "href=" not in roster
        assert "https://example.invalid/stock.html" not in block
        assert "stock.html" not in block
        assert "IDENTITY_VALIDATED" not in block
    finally:
        pass


def _assert_ast_no_research_reads(module) -> None:
    """AST pin for one engine module: no research/finance reads at runtime.

    Forbidden: a call whose function name is ``open``, ``Path`` or
    ``read_text`` (Name or Attribute form), and any import whose root is
    ``pathlib``, ``os``, ``socket`` or ``subprocess``. The substring
    ``research/finance`` is NOT banned — the module docstrings legitimately
    name it as a promise.
    """
    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {"pathlib", "os", "socket", "subprocess"}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    offenders = sorted(
        name for name in imported if name.split(".")[0] in forbidden_import_roots
    )
    assert not offenders, f"{module.__name__} imports {offenders}"
    bad_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        else:
            continue
        if name in {"open", "Path", "read_text"}:
            bad_calls.append(f"{module.__name__}:{node.lineno}:{name}")
    assert not bad_calls, bad_calls


def test_watching_and_hint_modules_do_not_read_research() -> None:
    """``finance_watching`` and ``finance_witness_hints`` are AST-clean.

    Closes the W8-B / W9-V proposal-6 pin: the two engine modules that
    carry the shell constants never open ``research/finance`` (no
    ``open``/``Path``/``read_text`` call, no filesystem/network import).
    """
    import engine.sector_intelligence.finance_witness_hints as finance_witness_hints

    _assert_ast_no_research_reads(finance_watching)
    _assert_ast_no_research_reads(finance_witness_hints)
