"""BC-2's merge-gate half: ``check_validated_claims --scope source``.

The full scan reads trees a nightly rewrites — the rendered site, the Prophet JSON and
the published registries — so it runs on the data gate, and for that reason it never
graded a claim before merge: 75 unearned claims reached main that way and were healed in
one batch (#7979). ``--scope source`` walks only the PR-authored roots and refuses
artifact backing, so its verdict is a function of the PR tree and it runs in every pull
request's merge gate (the ``validated-claims-source`` pack job). These tests pin the
three properties that make that true: every scan root is classified, the source scope
walks exactly the source roots with the SAME matcher, and no source claim can rest on a
data file. scripts/ is a source root through its top-level page builders alone
(``build_*`` / ``render_*``, PAGE BUILDERS in the checker), never the whole directory.

Hermetic: every tree is built under tmp_path and graded against the real allowlist, so
nothing here reads the live rendered or data trees.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import scripts.check_validated_claims as gate

# Earned nowhere: no allowlist entry names this phrase, on any surface.
CLAIM = "The validated moon-phase rotation gate."
# Earned on the discovery page only (the same entry the surfaces suite pins).
ALLOWLISTED = "Gated by the validated MACD-2D × StochRSI-3D confluence."

SOURCE_FILES = {
    ("templates", "probe_card.html.j2"): f'<p class="lede">{CLAIM}</p>\n',
    ("engine", "probe_copy.py"): f'CARD = {{"label_en": {CLAIM!r}}}\n',
    ("lib", "probe_copy.py"): f"def panel():\n    return dict(caveat={CLAIM!r})\n",
    ("scripts", "build_probe_page.py"): f"note_en, note_zh = {CLAIM!r}, '无'\n",
}
DATA_FILES = {
    ("site", "probe_card.html"): f"<p>{CLAIM}</p>\n",
    ("site", "prophet", "probe.json"): json.dumps({"headline": CLAIM}) + "\n",
    ("data", "cycle_pattern", "truths.jsonl"): json.dumps({"id": "probe", "notes": CLAIM}) + "\n",
}


def _write(root: Path, parts: tuple[str, ...], body: str) -> str:
    path = root.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return "/".join(parts)


def _files(findings: list[dict]) -> set[str]:
    return {finding["file"] for finding in findings}


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    return tmp_path


def _cli(monkeypatch: pytest.MonkeyPatch, *argv: str) -> None:
    monkeypatch.setattr(sys, "argv", ["check_validated_claims", *argv])
    gate.main()


# ── every scan root sits on one side of the gate line ────────────────────────────────

def test_every_scan_root_is_classified_as_source_or_rendered() -> None:
    """A root added without a decision would silently fall out of the merge gate."""
    roots = {sub for sub, _ in gate.SCAN_GLOBS} | {sub for sub, _ in gate.PY_COPY_GLOBS}
    rendered = {root for root in roots if root.split("/")[0] == "site"}
    unclassified = sorted(roots - gate.SOURCE_ROOTS - rendered)
    assert not unclassified, (
        f"scan root(s) {unclassified} are neither a SOURCE_ROOTS member nor rendered "
        "output. Decide which gate owns each: add it to SOURCE_ROOTS only if no data "
        "commit can write it (see the SCAN SCOPE block comment)."
    )
    assert gate.SOURCE_ROOTS <= roots, "a source root that is not a scan root gates nothing"
    assert not {root.split("/")[0] for root in gate.SOURCE_ROOTS} & {"site", "data"}


def test_every_registry_spec_is_data_so_the_source_scope_may_skip_them() -> None:
    assert all(spec.glob.startswith("data/") for spec in gate.DATA_COPY_SPECS)


def test_an_unknown_scope_is_refused() -> None:
    with pytest.raises(ValueError, match="scope"):
        gate.scan(scope="sources")


# ── the source scope walks exactly the PR-authored roots, with the SAME matcher ──────

def test_the_source_scope_walks_only_the_pr_authored_roots(tree: Path) -> None:
    for parts, body in {**SOURCE_FILES, **DATA_FILES}.items():
        _write(tree, parts, body)
    source = {"/".join(parts) for parts in SOURCE_FILES}
    data = {"/".join(parts) for parts in DATA_FILES}

    assert _files(gate.scan()) == source | data, "the data gate's full scan must see them all"
    assert _files(gate.scan(scope="source")) == source


def test_scripts_is_walked_only_at_its_top_level_page_builders(tree: Path) -> None:
    """A top-level build_* / render_* authors page copy. A checker, an evidence capture,
    or a builder one directory down (scripts/research/ writes no site/ output) does not,
    so gating their copy fields would grade text no page shows."""
    body = f'CARD = {{"note": {CLAIM!r}}}\n'
    builders = {_write(tree, ("scripts", name), body)
                for name in ("build_probe_page.py", "render_probe_page.py")}
    for parts in (("scripts", "check_probe.py"), ("scripts", "capture_probe_evidence.py"),
                  ("scripts", "research", "build_probe_study.py"),
                  ("scripts", "lanes", "render_probe_lane.py")):
        _write(tree, parts, body)

    assert _files(gate.scan(scope="source")) == builders
    assert _files(gate.scan()) == builders, "the full scan walks the same builder cut"


def test_both_scopes_grade_a_source_line_identically(tree: Path) -> None:
    """Same matcher, negation, masks and allowlist — `surfaces` enforced in both."""
    for parts, body in SOURCE_FILES.items():
        _write(tree, parts, body)
    earned = _write(tree, ("templates", "discovery.html.j2"), f"<p>{ALLOWLISTED}</p>\n")
    wrong_page = _write(tree, ("templates", "forex.html.j2"), f"<p>{ALLOWLISTED}</p>\n")
    _write(tree, ("templates", "hedged.html.j2"), "<p>This rotation is not validated.</p>\n")

    source = gate.scan(scope="source")
    assert source == gate.scan()
    assert earned not in _files(source)
    assert wrong_page in _files(source), "an entry for one page must not license another"
    assert len(source) == len(SOURCE_FILES) + 1


# ── no source claim can rest on a file a nightly rewrites ────────────────────────────

def test_a_source_claim_never_rests_on_a_data_artifact(tree: Path) -> None:
    """The full scan accepts a cited data JSON with ``validated: true``. The merge gate
    must not: a nightly rewrite of that file would flip the gate with no pull request."""
    artifact = ("data", "probe", "verdict.json")
    _write(tree, artifact, json.dumps({"validated": True}))
    rel = _write(tree, ("templates", "probe_card.html.j2"),
                 f"<p>A validated edge, see {'/'.join(artifact)}.</p>\n")

    assert gate.scan() == [], "the data gate's reading: backed by the artifact"
    (refused,) = gate.scan(scope="source")
    assert (refused["file"], refused["line_no"]) == (rel, 1)
    assert "allowlist alone" in refused["text"]

    # The verdict is the same whichever way the nightly writes the artifact.
    _write(tree, artifact, json.dumps({"validated": False}))
    assert _files(gate.scan(scope="source")) == {rel}


# ── the CLI the merge gate runs ──────────────────────────────────────────────────────

def test_the_cli_fails_a_source_claim_and_names_its_scope(
        tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    rel = _write(tree, ("templates", "probe_card.html.j2"), f"<p>{CLAIM}</p>\n")
    rendered = _write(tree, ("site", "probe_card.html"), f"<p>{CLAIM}</p>\n")

    with pytest.raises(SystemExit) as excinfo:
        _cli(monkeypatch, "--scope", "source")
    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    annotations = [line for line in err.splitlines() if line.startswith("::error::")]
    assert annotations, "GitHub drops an annotation that does not start the line"
    assert "scope=source" in annotations[0]
    assert "backing artifact" not in annotations[0], "the source scope refuses that remedy"
    assert rel in err
    assert rendered not in err, "rendered output is the data gate's, never the merge gate's"


def test_the_cli_passes_a_clean_source_tree_and_keeps_the_full_scan_default(
        tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    _write(tree, ("site", "probe_card.html"), f"<p>{CLAIM}</p>\n")  # data-gate debt only

    _cli(monkeypatch, "--scope", "source")
    assert ("OK [scope=source: engine/, lib/, scripts/build_*.py, scripts/render_*.py, "
            "templates/]") in capsys.readouterr().out

    with pytest.raises(SystemExit) as excinfo:
        _cli(monkeypatch)
    assert excinfo.value.code == 1, "with no --scope the CLI is still the full scan"
