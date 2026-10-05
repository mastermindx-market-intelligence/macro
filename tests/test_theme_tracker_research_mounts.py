"""tests/test_theme_tracker_research_mounts.py — shared hook 2 on the Theme Tracker.

The tracker page carried an inline COPY of the mount markup: one vertical's
anchor, both slice keys and its bilingual title/note typed into
`templates/state_of_themes.html.j2`, beside the same strings in the basket
partial and in the registration. Nothing covered their agreement, and a second
registered vertical could not appear on the board at all.

Now the page renders one section per registered vertical whose anchor is
ALREADY a theme row on the page, through the same partial the basket page
uses. What this suite pins:

a. The real registry + real rows → exactly ONE section, and every attribute
   equals the registration's own string.
b. A row nobody registered mounts nothing.
c. A SECOND registered vertical renders a second section, in page order, with
   distinct ids — and the incumbent's section is byte-identical to case (a).
d. A registered anchor that is not a row on this page mounts nothing and says
   so once in the log.
e. No registered row at all → no mount, and the board still renders.
f. The research layer raising → no mount, a warning, and the board still
   renders.
g. The client assets are included exactly once whatever the mount count.
h. The section partial missing → no mount, no exception.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
ANCHOR = "ai_semiconductors"


def _root(tmp_path: Path, theme_ids: list[str], *, with_partial: bool = True) -> Path:
    """A synthetic tracker root whose theme rows are exactly `theme_ids`."""
    from tests.test_state_of_themes import _make_sot_root

    tmp_path.mkdir(parents=True, exist_ok=True)  # the helper mkdirs without parents
    root = _make_sot_root(tmp_path)
    state = root / "site" / "neuralwebdata" / "theme_state.json"
    document = json.loads(state.read_text(encoding="utf-8"))
    template_row = document["themes"][0]
    document["themes"] = [
        {**template_row, "theme_id": theme_id, "name_en": theme_id, "name_zh": theme_id}
        for theme_id in theme_ids
    ]
    document["n_themes"] = len(theme_ids)
    state.write_text(json.dumps(document), encoding="utf-8")

    for partial in ("_theme_research_section.html.j2", "_theme_research_mounts.html.j2"):
        source = REPO_ROOT / "templates" / partial
        if with_partial and source.exists():
            (root / "templates" / partial).write_bytes(source.read_bytes())
    return root


def _render(root: Path) -> str:
    import scripts.build_state_of_themes as sot

    return sot.render(root)


def _sections(html: str) -> list[str]:
    return re.findall(r'<section class="theme-research".*?</section>', html, re.DOTALL)


def _mount(anchor: str = ANCHOR) -> dict:
    from engine.market_ontology.theme_research_mounts import mount_context

    context = mount_context(anchor)
    assert context is not None, anchor
    return dict(context)


# --------------------------------------------------------------------- a/b

def test_registered_row_mounts_once_with_the_registrations_strings(tmp_path):
    html = _render(_root(tmp_path, [ANCHOR, "diagnostics_lifesci"]))
    sections = _sections(html)
    assert len(sections) == 1, f"expected one mount, got {len(sections)}"
    block, mount = sections[0], _mount()
    assert f'data-anchor-theme-id="{mount["anchor_theme_id"]}"' in block
    assert f'data-slices="{mount["slices"]}"' in block
    assert f'data-schema-id="{mount["schema_id"]}"' in block
    assert f'data-evidence-schema-id="{mount["evidence_schema_id"]}"' in block
    assert f'id="theme-research-{mount["anchor_theme_id"]}"' in block
    assert "hidden" in block
    for key in ("title_en", "title_zh", "note_en", "note_zh"):
        assert mount[key] in block, key
    # The board still renders around it.
    assert "theme-row" in html


def test_a_row_nobody_registered_mounts_nothing(tmp_path):
    html = _render(_root(tmp_path, [ANCHOR, "memory_storage"]))
    assert len(_sections(html)) == 1, "memory_storage has no registration"


# ----------------------------------------------------------------------- c

def test_a_second_registered_vertical_renders_a_second_section(tmp_path, monkeypatch):
    """Two verticals, page order, distinct ids — and the incumbent unchanged."""
    from types import MappingProxyType

    import engine.market_ontology.theme_research_mounts as mounts_module

    synthetic = mounts_module.MountFacts(
        anchor_theme_id="synthetic_vertical",
        slice_keys=("alpha_slice", "beta_slice"),
        schema_id="synthetic_research.v1",
        evidence_schema_id="synthetic_research.evidence.v1",
        slice_labels=MappingProxyType({
            "alpha_slice": ("Alpha slice", "甲切片"),
            "beta_slice": ("Beta slice", "乙切片"),
        }),
        title_en="Synthetic industry research",
        title_zh="合成产业研究",
        note_en="Paid research context for members.",
        note_zh="会员研究内容。",
    )
    widened = MappingProxyType({**dict(mounts_module.MOUNTS), "synthetic_vertical": synthetic})
    monkeypatch.setattr(mounts_module, "MOUNTS", widened)
    import scripts.build_state_of_themes as sot

    monkeypatch.setattr(sot, "_RESEARCH_MOUNTS", widened)

    baseline = _sections(_render(_root(tmp_path / "one", [ANCHOR, "diagnostics_lifesci"])))
    html = _render(_root(tmp_path / "two", ["synthetic_vertical", ANCHOR]))
    sections = _sections(html)
    assert len(sections) == 2, f"expected two mounts, got {len(sections)}"
    assert 'data-anchor-theme-id="synthetic_vertical"' in sections[0], "page order"
    assert f'data-anchor-theme-id="{ANCHOR}"' in sections[1]
    assert 'id="theme-research-synthetic_vertical"' in sections[0]
    assert f'id="theme-research-{ANCHOR}"' in sections[1]
    assert "synthetic_research.v1" in sections[0]
    assert sections[0] != sections[1]
    assert sections[1] == baseline[0], (
        "adding a vertical changed the incumbent's rendered section"
    )


# ----------------------------------------------------------------------- d

def test_a_registered_anchor_with_no_row_mounts_nothing_and_says_so(tmp_path, caplog):
    with caplog.at_level(logging.INFO, logger="build_state_of_themes"):
        html = _render(_root(tmp_path, ["diagnostics_lifesci", "memory_storage"]))
    assert not _sections(html)
    assert any(ANCHOR in record.getMessage() for record in caplog.records), (
        "a registered anchor that is not a row on this page must be logged once"
    )
    assert "theme-row" in html


# ----------------------------------------------------------------------- e/f

def test_no_registered_row_renders_a_board_with_no_mount(tmp_path):
    html = _render(_root(tmp_path, ["diagnostics_lifesci"]))
    assert "data-theme-research-mount" not in html
    assert "theme-row" in html


def test_the_research_layer_raising_never_fails_the_page(tmp_path, monkeypatch, caplog):
    import scripts.build_state_of_themes as sot

    def _boom(_anchor):
        raise RuntimeError("registry fault")

    monkeypatch.setattr(sot, "_research_mount_context", _boom)
    with caplog.at_level(logging.WARNING, logger="build_state_of_themes"):
        html = _render(_root(tmp_path, [ANCHOR]))
    assert "data-theme-research-mount" not in html
    assert "theme-row" in html
    assert any("unavailable" in record.getMessage() for record in caplog.records)


def test_a_missing_engine_checkout_renders_the_board(tmp_path, monkeypatch, caplog):
    """And SAYS so: a silent empty board is the failure this warning exists for."""
    import scripts.build_state_of_themes as sot

    monkeypatch.setattr(sot, "_research_mount_context", None)
    monkeypatch.setattr(sot, "_RESEARCH_MOUNTS", None)
    with caplog.at_level(logging.WARNING, logger="build_state_of_themes"):
        html = _render(_root(tmp_path, [ANCHOR]))
    assert "data-theme-research-mount" not in html
    assert "theme-row" in html
    assert any("engine/ not in this checkout" in record.getMessage()
               for record in caplog.records), (
        "a build with no research layer must say so, not silently drop the mount"
    )


def test_a_research_layer_that_raises_at_import_never_darks_the_board():
    """The guarded import must catch MORE than ImportError.

    The import first executes engine/market_ontology/__init__.py, which pulls
    the exposure map, and a malformed registration raises ValueError out of
    MountFacts.__post_init__ at import time. An independent review proved a
    ValueError there killed the WHOLE Theme Tracker page — the board, not just
    the mount — because the guard caught ImportError alone.

    Run in a fresh interpreter: the failure is an IMPORT-time one, and
    simulating it inside this process would leave the module cache in a state
    later tests inherit (it did, when this test first patched sys.modules).
    """
    probe = (
        "import sys\n"
        "class RaisingFinder:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name == 'engine.market_ontology.theme_research_mounts':\n"
        "            raise ValueError('MountFacts.title_zh must be non-empty text')\n"
        "        return None\n"
        "sys.meta_path.insert(0, RaisingFinder())\n"
        "import scripts.build_state_of_themes as m\n"
        "print(m._research_mount_context is None, m._theme_research_mounts([{'theme_id': 'ai_semiconductors'}]) == [])\n"
    )
    run = subprocess.run(
        [sys.executable, "-B", "-c", probe], cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=300,
    )
    assert run.returncode == 0, (
        "a research layer that raises at import took the whole page down:\n"
        + run.stderr[-2000:]
    )
    assert run.stdout.strip() == "True True", run.stdout


# ----------------------------------------------------------------------- g/h

@pytest.mark.parametrize("theme_ids, expected", [
    (["diagnostics_lifesci"], 0),
    ([ANCHOR], 1),
])
def test_client_assets_are_included_exactly_once_whatever_the_mount_count(
    tmp_path, theme_ids, expected,
):
    html = _render(_root(tmp_path, theme_ids))
    assert len(_sections(html)) == expected
    assert html.count('href="assets/css/theme-research.css"') == 1
    assert html.count('src="assets/js/theme-research.js?v=20260924b"') == 1


def test_a_missing_section_partial_renders_no_mount_and_no_exception(tmp_path):
    html = _render(_root(tmp_path, [ANCHOR], with_partial=False))
    assert "data-theme-research-mount" not in html
    assert "theme-row" in html


def test_a_duplicate_row_mounts_once(tmp_path):
    """Two sections would share one DOM id; the client takes the first."""
    html = _render(_root(tmp_path, [ANCHOR, ANCHOR]))
    assert len(_sections(html)) == 1
