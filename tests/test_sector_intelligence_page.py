"""Sector Intelligence consolidation invariants (2026-08 merge of baskets +
subsector_rotation into sector_central.html).

Pins the merge's load-bearing properties so a later template edit cannot silently
undo them: the two redirect stubs, the merged page's section skeleton, the
payload externalization (no inline BASKETS embed), the live-quote member-symbol
registry, and the China contract (its templates untouched by the shared-JS edit).
Charter: research/SECTOR_INTELLIGENCE_CONSOLIDATION_MASTERPLAN_BY_FABLE.md §0.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates"


def _read(p: Path) -> str:
    assert p.exists(), f"{p} missing"
    return p.read_text(encoding="utf-8")


def _view_body(src: str, view: str) -> str:
    """The markup between `<section class="si-view" data-view="<view>">` and the next
    view's open tag (V2 workspace shell). Views are display-toggled siblings, so
    "inside view X" is a slice between two sibling opens, not a nesting question."""
    opens = re.split(r'<section class="si-view[^"]*" data-view="([a-z]+)"', src)
    # re.split with one group → [pre, name, body, name, body, ...]
    names, bodies = opens[1::2], opens[2::2]
    assert view in names, f"no si-view for {view!r} (found {names})"
    return bodies[names.index(view)]


# ---------------------------------------------------------------- stubs

@pytest.mark.parametrize("name,target", [
    ("baskets.html.j2", "sector_central.html#actnow-section"),
    ("subsector_rotation.html.j2", "sector_central.html#si-movement"),
])
def test_redirect_stub(name: str, target: str) -> None:
    s = _read(TPL / name)
    assert f'content="0;url={target}"' in s, "meta refresh missing/retargeted"
    assert 'name="robots" content="noindex,follow"' in s
    assert f'location.replace("{target}")' in s
    assert 'seo_path = "sector_central.html"' in s, "canonical must point at the merged page"
    # A stub must never regrow page content
    assert len(s) < 4000, f"{name} is {len(s)} chars — no longer a stub?"


@pytest.mark.parametrize("name,target", [
    ("baskets.html", "sector_central.html#actnow-section"),
    ("subsector_rotation.html", "sector_central.html#si-movement"),
])
def test_redirect_stub_rendered(name: str, target: str) -> None:
    """The RENDERED stubs must hold too — the template pin above cannot see this
    failure mode. A scope=all render that raced the #4237 merge (04946ac459d,
    2026-08-02: pre-merge checkout replayed over main with `pull --rebase -X
    theirs`) resurrected the old 1,379-line baskets body under the stub's head,
    shipping a chimera to direct visitors for a day.
    """
    s = _read(ROOT / "site" / name)
    assert f'content="0;url={target}"' in s, "meta refresh missing/retargeted"
    assert f'location.replace("{target}")' in s, "JS redirect fallback missing"
    assert '<body class="macro-desk' not in s, "absorbed page body regrew in the render"
    assert "macro-desk.css" not in s, "stub must not re-join the macro-desk surface"
    # Headroom over the ~4.1KB healthy render for future head-injected chrome
    # (shim/preload/stamps); the resurrected chimera weighed ~840KB.
    assert len(s) < 12000, f"site/{name} is {len(s)} chars — stub body regrew?"


# ---------------------------------------------------- merged template skeleton

def test_merged_template_sections() -> None:
    s = _read(TPL / "sector_central.html.j2")
    for anchor in ('id="actnow-section"', 'id="si-map"', 'id="si-movement"',
                   'id="si-money"', 'id="explore-section"', 'id="rotation-app"',
                   'id="sc-cyclemap"', 'id="board"', 'id="grader"',
                   'id="heatmap-scorecard"', 'id="scc-leadership"',
                   'id="table-section"', 'id="chart-section"'):
        assert anchor in s, f"merged page lost {anchor}"
    # legacy deep-link anchors survive
    assert 'id="rotmap-section"' in s
    # S2 §1.4 demotion landings — nested span anchors, not new L1 sections
    assert 'id="accumulation-section"' in s
    assert 'id="theme-heat-section"' in s
    # live-quote scraper contract (FTR W2a): member-symbol registry must ship
    assert 'ftr-member-sym-registry' in s
    assert "basket_member_syms" in s


# V2 workspace partition (SI_WORKSPACE_V2_MASTERPLAN_BY_FABLE §2b). The V1 pin above
# only proved these ids EXIST somewhere on the page — which stayed true even while an
# organ sat in the wrong view. Membership is the property the shell actually depends
# on: the router sends every legacy anchor to a specific view, so an organ in the wrong
# view means a deep link that scrolls to a hidden element and shows the user nothing.
VIEW_MEMBERSHIP = {
    # 'id="actnow"' was the OLD client-rendered lanes div; the SI-central transplant
    # (2026-08) replaced it with the shared server-rendered board include (#action-board
    # lives inside the include, invisible to raw-source scanning) — pin the include filename,
    # mirroring how the explore view pins "_forming_narratives.html.j2".
    "overview": ('id="ftr-tape-strip"', 'id="ftr-tape-band"', 'id="regime"',
                 'id="actnow-section"', '_us_act_now_board.html.j2', 'id="grader"'),
    "map": ('id="rotmap-section"', 'id="si-map"', 'id="rvx-rmap"', 'id="rvx-board"',
            'id="sc-cyclemap"', 'id="sc-chart"', 'id="board"'),
    "moving": ('id="si-movement"', 'id="rc-events-mount"', 'id="rotation-app"',
               'id="desk-watch-mount"', 'id="accumulation-section"',
               "_accumulation_watch.html.j2"),
    "money": ('id="si-money"', 'id="internals-section"', 'id="sc-heatmap"',
              'id="heatmap-scorecard"', 'id="scc-leadership"'),
    "explore": ('id="explore-section"', 'id="table-section"', 'id="chart-section"',
                'id="btable"', 'id="chart"', 'id="tm-mount"',
                "_forming_narratives.html.j2", "ftr-member-sym-registry",
                'id="theme-heat-section"', "_theme_tape.html.j2"),
}


@pytest.mark.parametrize("view,anchors", sorted(VIEW_MEMBERSHIP.items()))
def test_organs_sit_in_their_assigned_view(view: str, anchors: tuple) -> None:
    body = _view_body(_read(TPL / "sector_central.html.j2"), view)
    for a in anchors:
        assert a in body, f"{a} is not inside the {view} view"


def test_view_order_is_the_sidebar_order() -> None:
    """Six views, in the pinned order, each driven by a sidebar button of the same
    name. Order is load-bearing twice over: it is the reading order of the product
    (overview → map → moving → money → explore → confluence) and it is the tab order of
    the mobile switcher. Confluence sits LAST on purpose: it is the entry-timing funnel
    you reach after the rotation read, not a lens on the desk itself, and appending it
    leaves the five original tab positions where returning readers left them."""
    s = _read(TPL / "sector_central.html.j2")
    order = ["overview", "map", "moving", "money", "explore", "confluence"]
    assert re.findall(r'<section class="si-view[^"]*" data-view="([a-z]+)"', s) == order
    assert re.findall(r'class="si-view-btn[^"]*" data-view="([a-z]+)"', s) == order
    # The funnel exit link is gone: it pointed at subsectors.html from one row below the
    # #confluence button, wearing the same glyph — two rail entries to the same board.
    assert 'class="si-side-out"' not in s, \
        "the old funnel exit LINK survived — it should be the routed #confluence view now"
    assert 'href="subsectors.html"' not in s, \
        "the sidebar still links the standalone page the confluence view absorbed"

    # the V1 sticky anchor rail is retired — the sidebar replaced it
    assert 'id="si-rail"' not in s, "the V1 anchor rail came back"
    assert 'class="scc-rail"' not in s


def test_forming_narratives_mounted_at_end_of_explore() -> None:
    """The Forming Narratives panel ships on the US page (PR-A1).

    engine.narrative_emergence has emitted site/basketdata/narrative_emergence.json for
    US nightly all along, but the shared panel was mounted only on the non-US baskets
    pages — the US read was computed and never shown.

    RETARGETED by the V2 workspace (SI_WORKSPACE_V2_MASTERPLAN_BY_FABLE §2b): the panel
    and the Time Machine both moved out of MOVEMENT into EXPLORE, because both are reads
    you go looking for rather than heads-up context. The ordering law is unchanged — the
    Time Machine still precedes the forming panel, which is still the LAST read of its
    view — only the view it ends changed. Mount ids are preserved so #tm-mount and
    #forming-narratives keep resolving through the router.
    """
    s = _read(TPL / "sector_central.html.j2")
    assert '{% include "_forming_narratives.html.j2" %}' in s, "panel not mounted"
    explore = _view_body(s, "explore")
    assert '{% include "_forming_narratives.html.j2" %}' in explore, \
        "panel escaped the EXPLORE view"
    assert 'id="tm-mount"' in explore, "time machine escaped the EXPLORE view"
    assert explore.index('id="tm-mount"') < explore.index("_forming_narratives"), \
        "panel must come after the time machine — it is the last read in EXPLORE"
    # …and both must have LEFT movement: a copy left behind would double-mount and the
    # second mount would silently win.
    movement = _view_body(s, "moving")
    assert 'id="tm-mount"' not in movement, "time machine still mounted in MOVEMENT too"
    assert "_forming_narratives" not in movement, "forming panel still in MOVEMENT too"


def test_forming_narratives_asset_copied_by_builder() -> None:
    """The panel loads forming_narratives.js relative to the page, so the US builder
    must copy it into site/ like its sibling MOVEMENT donors."""
    s = _read(ROOT / "scripts" / "build_sector_central.py")
    assert '"forming_narratives.js"' in s, "asset missing from the copy tuple"
    # it must sit in the SAME tuple as the other MOVEMENT donors (one copy loop)
    tup = s.split('for asset in (', 1)[1].split("):", 1)[0]
    assert "forming_narratives.js" in tup, "asset added outside the asset-copy tuple"


def test_payload_externalized_not_embedded() -> None:
    s = _read(TPL / "sector_central.html.j2")
    assert "baskets_json|safe" not in s, "inline BASKETS embed came back"
    assert "chart_json|safe" not in s, "inline CHART embed came back"
    assert "theme_alerts_json|safe" not in s, "inline THEME_ALERTS embed came back"
    assert "basketdata/baskets.json" in s, "payload fetch missing"
    # bell + theme_alerts payload removed sitewide (#4232, re-applied on rebase)
    assert "theme_alerts" not in s, "bell alerts plumbing resurfacing"


def test_dead_v1_desk_stays_dead() -> None:
    # renderStanceChips is NOT in this list: PR #4241 (MLC-W2b) rebuilt it as a LIVE
    # act-board surface (invocation pinned in test_theme_scoring_conflicted) — only
    # the V1 fork's members stay banned.
    s = _read(TPL / "sector_central.html.j2")
    for fn in ("renderThemeDesk", "renderConcentration", "renderScorecards",
               "renderMacroCtx", "decorateRealActivity",
               "renderActNow", "_fetchRadar"):
        assert fn not in s, f"dead V1 desk function {fn} resurrected"


def test_gated_read_and_movement_posture() -> None:
    s = _read(TPL / "sector_central.html.j2")
    # The lanes stay the only gated/graded surface; movement stays display-only.
    assert "Lanes are the only gated, graded calls on this page" in s
    assert "display-only" in s


# ------------------------------------------------------------- shared JS + China

def test_sr_js_themes_unit_flag_is_backward_compatible() -> None:
    js = _read(TPL / "subsector_rotation.js")
    # US hides the unit via flag; absent flag (China feed) keeps the button.
    assert "_data.themes_unit !== false" in js
    assert "data-u=\"subsectors\"" in js


def test_china_consolidation_landed_on_its_own_page() -> None:
    """The follow-up program this test was waiting for has landed.

    Was test_china_templates_untouched_by_consolidation: while the US merge shipped
    alone, the China siblings had to keep their own pages, so it asserted none of the
    three was a stub. The China Sector Intelligence consolidation (2026-08) ported the
    merge, so the premise inverts for the two absorbed pages — but the guard it was
    really providing survives, and is what matters now: the US merge must not have
    reached across and stubbed China's HUB. Full China invariants live in
    tests/test_china_sector_intelligence_page.py.
    """
    hub = _read(TPL / "sector_central_china.html.j2")
    assert "http-equiv=\"refresh\"" not in hub, (
        "sector_central_china.html.j2 is the China hub — it must never be a stub"
    )
    for name in ("baskets_china.html.j2", "subsector_rotation_china.html.j2"):
        s = _read(TPL / name)
        assert "http-equiv=\"refresh\"" in s, (
            f"{name} is an absorbed page and must stay a redirect stub"
        )
        assert "sector_central_china.html" in s, f"{name} retargeted off the China hub"


def test_us_builder_flags_themes_unit_hidden() -> None:
    s = _read(ROOT / "scripts" / "build_subsector_rotation.py")
    assert 'payload["themes_unit"] = False' in s
    # the themes ARRAY must survive for engine/neuralweb/thematic_state.py
    assert "payload.pop(\"themes\"" not in s


# ------------------------------------------------------------------ nav

def test_nav_flyout_collapsed_to_two_entries() -> None:
    s = _read(TPL / "_navlinks.html.j2")
    assert "Sector Intelligence" in s
    # the two absorbed pages have no US nav entry anymore (stubs are reachable
    # only via old bookmarks/links); China entries survive.
    us_zone = s.split("China")[0]
    assert 'href="{{ NP }}baskets.html"' not in us_zone
    assert 'href="{{ NP }}subsector_rotation.html"' not in us_zone
    # The confluence funnel stays in the nav, but as a DEEP LINK into the merged page's
    # rail view rather than a link out to the standalone page — the same move #4637 made
    # for China, whose note deferred this US half. The standalone subsectors.html keeps
    # only its internal links; it is no longer a nav destination.
    assert 'href="{{ NP }}sector_central.html#confluence"' in s
    assert 'href="{{ NP }}subsectors.html"' not in s, \
        "the old funnel exit LINK survived — it should be a routed #confluence view now"


# ------------------------------------------------ semantic freshness contract

import hashlib
import json
from datetime import datetime, timezone


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _write_sector_intelligence_generation(
    root: Path,
    *,
    baskets_asof: str = "2026-09-14",
    theme_asof: str | None = None,
    action_asof: str | None = None,
    sector_asof: str | None = None,
    html_asof: str | None = None,
    action_total: int = 1,
    corrupt_baskets_hash: bool = False,
) -> None:
    site = root / "site"
    for rel in ("basketdata", "sectordata", "premiumdata"):
        (site / rel).mkdir(parents=True, exist_ok=True)
    theme_asof = theme_asof or baskets_asof
    sector_asof = sector_asof or baskets_asof
    html_asof = html_asof or baskets_asof
    baskets = {
        "as_of": baskets_asof,
        "theme_intel": {"as_of": theme_asof},
        "baskets": [{"id": "theme-a"}],
    }
    baskets_path = site / "basketdata" / "baskets.json"
    baskets_path.write_bytes(_json_bytes(baskets))
    baskets_sha = hashlib.sha256(baskets_path.read_bytes()).hexdigest()
    recorded_baskets_sha = "0" * 64 if corrupt_baskets_hash else baskets_sha

    action = {
        "schema": "sector_intelligence_action_board.v1",
        "generated_utc": "2026-09-16T06:00:00Z",
        "baskets_sha256": recorded_baskets_sha,
        "action_board": {
            "total": action_total,
            "buy_now": ([{"ticker": "XLK"}] if action_total else []),
        },
    }
    if action_asof is not None:
        action["as_of"] = action_asof
    action_path = site / "basketdata" / "action_board.json"
    action_path.write_bytes(_json_bytes(action))
    action_sha = hashlib.sha256(action_path.read_bytes()).hexdigest()

    (site / "sectordata" / "sector_central.json").write_bytes(
        _json_bytes({"as_of": sector_asof, "sectors": [{"ticker": "XLK"}]})
    )
    premium = {
        "schema": "tier_payload.v1",
        "page": "sector_central",
        "as_of": sector_asof,
        "baskets_sha256": baskets_sha,
        "action_board_sha256": action_sha,
    }
    (site / "premiumdata" / "sector_central.json").write_bytes(_json_bytes(premium))
    (site / "sector_central.html").write_text(
        '<section class="rvx-hero" '
        f'data-si-as-of="{html_asof}" '
        f'data-si-baskets-sha256="{baskets_sha}" '
        f'data-si-action-board-sha256="{action_sha}"></section>',
        encoding="utf-8",
    )


def _evaluate_sector_intelligence(root: Path) -> dict:
    from scripts.check_sector_intelligence_freshness import evaluate

    return evaluate(
        root,
        now=datetime(2026, 9, 16, 6, tzinfo=timezone.utc),
        max_sessions_behind=1,
    )


def test_semantic_freshness_accepts_one_session_lag(tmp_path: Path) -> None:
    _write_sector_intelligence_generation(tmp_path, action_asof="2026-09-14")
    report = _evaluate_sector_intelligence(tmp_path)
    assert report["ok"] is True, report
    assert report["facts"]["as_of"] == "2026-09-14"
    assert report["facts"]["sessions_behind"] == 1


def test_semantic_freshness_rejects_individually_fresh_vintage_split(
    tmp_path: Path,
) -> None:
    _write_sector_intelligence_generation(
        tmp_path,
        action_asof="2026-09-14",
        sector_asof="2026-09-15",
        html_asof="2026-09-15",
    )
    report = _evaluate_sector_intelligence(tmp_path)
    assert report["ok"] is False
    assert any("VINTAGE SPLIT" in error for error in report["errors"]), report


def test_semantic_freshness_rejects_unstamped_action_board(tmp_path: Path) -> None:
    _write_sector_intelligence_generation(tmp_path, action_asof=None)
    report = _evaluate_sector_intelligence(tmp_path)
    assert report["ok"] is False
    assert any("action_board.json" in error and "as_of" in error
               for error in report["errors"]), report


def test_semantic_freshness_rejects_source_hash_mismatch(tmp_path: Path) -> None:
    _write_sector_intelligence_generation(
        tmp_path,
        action_asof="2026-09-14",
        corrupt_baskets_hash=True,
    )
    report = _evaluate_sector_intelligence(tmp_path)
    assert report["ok"] is False
    assert any("baskets_sha256" in error for error in report["errors"]), report


def test_semantic_freshness_rejects_empty_action_board(tmp_path: Path) -> None:
    _write_sector_intelligence_generation(
        tmp_path, action_asof="2026-09-14", action_total=0
    )
    report = _evaluate_sector_intelligence(tmp_path)
    assert report["ok"] is False
    assert any("action board is empty" in error.lower()
               for error in report["errors"]), report


def test_action_board_writer_binds_exact_basket_bytes(tmp_path: Path) -> None:
    from scripts.build_sector_action_board import write_action_board

    site = tmp_path / "site"
    baskets_path = site / "basketdata" / "baskets.json"
    baskets_path.parent.mkdir(parents=True)
    baskets_path.write_bytes(
        _json_bytes({
            "as_of": "2026-09-14",
            "theme_intel": {"as_of": "2026-09-14"},
            "baskets": [{"id": "theme-a"}],
        })
    )
    output = site / "basketdata" / "action_board.json"
    board = {"total": 1, "buy_now": [{"ticker": "XLK"}]}

    write_action_board(
        output,
        baskets_path=baskets_path,
        action_board=board,
        generated_utc="2026-09-16T06:00:00Z",
    )

    payload = json.loads(output.read_text())
    assert payload["schema"] == "sector_intelligence_action_board.v1"
    assert payload["as_of"] == "2026-09-14"
    assert payload["generated_utc"] == "2026-09-16T06:00:00Z"
    assert payload["baskets_sha256"] == hashlib.sha256(
        baskets_path.read_bytes()
    ).hexdigest()
    assert payload["action_board"] == board


def test_focused_action_builder_uses_fresh_baskets_and_canonical_board_logic(
    tmp_path: Path,
) -> None:
    from scripts.build_sector_action_board import build_action_board

    site = tmp_path / "site"
    baskets_path = site / "basketdata" / "baskets.json"
    baskets_path.parent.mkdir(parents=True)
    baskets_path.write_bytes(_json_bytes({
        "as_of": "2026-09-14",
        "theme_intel": {"as_of": "2026-09-14"},
        "baskets": [{"id": "theme-a"}],
    }))
    regime = tmp_path / "data" / "regime" / "latest.json"
    regime.parent.mkdir(parents=True)
    regime.write_text(json.dumps({
        "dislocation": {"put_state": "normal"},
        "playbook": {"stages": []},
    }))

    calls: list[str] = []

    class Canonical:
        @staticmethod
        def build_alpha_data(_site):
            calls.append("alpha")
            return {"per_ticker": {}}

        @staticmethod
        def build_insider_data(_site):
            calls.append("insider")
        @staticmethod
        def build_sector_pages(_env, _site, _generated, **kwargs):
            calls.append("sector_pages")
            assert kwargs["alpha"] == {"per_ticker": {}}
            return ({"XLK": {"label": "Leader", "entry": {"urgency": "now"}}}, [])

        @staticmethod
        def sector_setup_view(_latest, _timing):
            calls.append("sector_setup")
            return {"sectors": [{
                "ticker": "XLK",
                "two_reads_chip": {"cycle_label_en": "LEADER"},
            }]}

        @staticmethod
        def basket_action_items(_site):
            calls.append("basket_items")
            return {"sector_overlay": {}}

        @staticmethod
        def action_board(_timing, _notable, _basket_items, **kwargs):
            calls.append("action_board")
            assert "XLK" in kwargs["sector_setup_lookup"]
            return {
                "total": 1,
                "buy_now": [{"kind": "sector", "ticker": "XLK"}],
                "buy_soon": [], "on_the_run": [], "take_profits": [],
                "hold": [], "avoid": [], "notable": [],
            }

    payload = build_action_board(
        root=tmp_path,
        canonical=Canonical,
        generated_utc="2026-09-16T06:00:00Z",
    )
    assert calls == [
        "alpha", "insider", "sector_pages", "sector_setup",
        "basket_items", "action_board",
    ]
    assert payload["as_of"] == "2026-09-14"
    row = payload["action_board"]["buy_now"][0]
    assert row["two_reads_chip"] == {"cycle_label_en": "LEADER"}
    written = json.loads(
        (site / "basketdata" / "action_board.json").read_text()
    )
    assert written == payload


def test_focused_basket_build_fails_closed_when_engine_raises(monkeypatch) -> None:
    from engine import baskets as basket_engine
    from scripts import build_baskets

    def boom():
        raise RuntimeError("basket engine unavailable")

    monkeypatch.setattr(basket_engine, "compute_baskets", boom)
    assert build_baskets.main(sector_intelligence_only=True) == 1
    assert build_baskets.main(sector_intelligence_only=False) == 0


def test_focused_basket_build_fails_closed_when_engine_returns_no_data(monkeypatch) -> None:
    from engine import baskets as basket_engine
    from scripts import build_baskets

    monkeypatch.setattr(basket_engine, "compute_baskets", lambda: None)
    assert build_baskets.main(sector_intelligence_only=True) == 1
    assert build_baskets.main(sector_intelligence_only=False) == 0


def test_sector_central_strict_mode_refuses_engine_failure(
    monkeypatch, tmp_path: Path,
) -> None:
    from engine import sector_central as sector_engine
    from scripts import build_sector_central

    monkeypatch.setattr(build_sector_central.config, "ROOT", tmp_path)
    monkeypatch.setattr(
        build_sector_central.config,
        "load",
        lambda: {"storage": {"site_dir": "site"}},
    )

    def boom():
        raise RuntimeError("sector engine unavailable")

    monkeypatch.setattr(sector_engine, "compute", boom)
    assert build_sector_central.main(strict=True) == 1
    assert build_sector_central.main(strict=False) == 0


def test_focused_allocation_gate_rejects_failed_or_split_generation(
    tmp_path: Path,
) -> None:
    from scripts.build_baskets import _focused_allocation_is_current

    allocation = tmp_path / "allocation.json"
    allocation.write_text(json.dumps({"as_of": "2026-09-11"}))

    assert _focused_allocation_is_current(
        allocation, theme_as_of="2026-09-14", allocation_failed=True
    ) is False
    assert _focused_allocation_is_current(
        allocation, theme_as_of="2026-09-14", allocation_failed=False
    ) is False

    allocation.write_text(json.dumps({"as_of": "2026-09-14"}))
    assert _focused_allocation_is_current(
        allocation, theme_as_of="2026-09-14", allocation_failed=False
    ) is True


# ------------------------------------------------ independent publication lane

WORKFLOW = ROOT / ".github" / "workflows" / "sector-intelligence.yml"


def test_orchestrator_runs_producers_then_validator_in_strict_order() -> None:
    from scripts.build_sector_intelligence import run_steps

    calls: list[str] = []

    def step(name: str, rc: int = 0):
        def invoke() -> int:
            calls.append(name)
            return rc
        return invoke

    rc = run_steps([
        ("baskets", step("baskets")),
        ("action_board", step("action_board")),
        ("sector_central", step("sector_central")),
        ("validate", step("validate")),
    ])
    assert rc == 0
    assert calls == ["baskets", "action_board", "sector_central", "validate"]


def test_orchestrator_stops_before_publishing_a_partial_generation() -> None:
    from scripts.build_sector_intelligence import run_steps

    calls: list[str] = []
    def step(name: str, rc: int = 0):
        def invoke() -> int:
            calls.append(name)
            return rc
        return invoke

    rc = run_steps([
        ("baskets", step("baskets")),
        ("action_board", step("action_board", rc=1)),
        ("sector_central", step("sector_central")),
        ("validate", step("validate")),
    ])
    assert rc == 1
    assert calls == ["baskets", "action_board"]


def test_workflow_has_independent_reconciliation_and_manual_paths() -> None:
    src = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in src
    assert "schedule:" in src
    assert "push:" in src
    assert "pipeline-sector-intelligence" in src
    assert "cancel-in-progress: false" in src
    assert "python -m scripts.build_sector_intelligence" in src
    assert "python -m scripts.check_sector_intelligence_freshness --quiet" in src


def test_own_publication_noop_cannot_supersede_a_real_pending_rebuild() -> None:
    src = WORKFLOW.read_text(encoding="utf-8")
    assert "pipeline-sector-intelligence-self-publish" in src
    concurrency = src[src.index("concurrency:"):src.index("jobs:")]
    assert "startsWith(github.event.head_commit.message, 'sector-intelligence: publish')" in concurrency
    assert "pipeline-sector-intelligence" in concurrency
    assert "cancel-in-progress: false" in concurrency


def test_workflow_clears_inherited_sparse_checkout_before_checkout() -> None:
    src = WORKFLOW.read_text(encoding="utf-8")
    guard = src.index("clear any sparse checkout")
    checkout = src.index("uses: actions/checkout@v4")
    assert guard < checkout
    assert "sparse-checkout disable" in src[guard:checkout]
    assert "config --unset-all core.sparseCheckout" in src[guard:checkout]


def test_workflow_uses_existing_main_publication_contract() -> None:
    src = WORKFLOW.read_text(encoding="utf-8")
    assert "ADMIN_GH_TOKEN" in src
    assert 'scripts/ci/push_retry.sh' in src
    assert "push_metadata_replay_commit" in src
    assert "sector-intelligence: publish" in src
    assert "git add site/" not in src, "targeted lane must never stage the whole site"


def test_scoped_publication_directories_are_real_and_owned_by_the_build() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    action_builder = (ROOT / "scripts" / "build_sector_action_board.py").read_text()
    basket_builder = (ROOT / "scripts" / "build_baskets.py").read_text()

    assert (ROOT / "site" / "basket").is_dir()
    assert (ROOT / "site" / "sectors").is_dir()
    # Stock details remain a real broad-build output, not a focused publication.
    # The exact staged-path exclusion is separately exercised below.
    assert "build_detail_pages" in basket_builder
    assert "if not sector_intelligence_only:" in basket_builder
    assert "site/sectors" in workflow and "canonical.build_sector_pages" in action_builder


def test_workflow_runs_exact_builder_order() -> None:
    src = WORKFLOW.read_text(encoding="utf-8")
    # The orchestrator owns the order; the workflow must not bypass one producer.
    for module in (
        "scripts.build_baskets",
        "scripts.build_sector_action_board",
        "scripts.build_sector_central",
        "scripts.check_sector_intelligence_freshness",
    ):
        assert module in (ROOT / "scripts" / "build_sector_intelligence.py").read_text()


def test_orchestrator_uses_focused_basket_mode(monkeypatch) -> None:
    from scripts import build_baskets
    from scripts.build_sector_intelligence import default_steps

    seen: list[bool] = []

    def fake_main(*, sector_intelligence_only: bool = False) -> int:
        seen.append(sector_intelligence_only)
        return 0

    monkeypatch.setattr(build_baskets, "main", fake_main)
    steps = default_steps()
    assert steps[0][0] == "scripts.build_baskets"
    assert steps[0][1]() == 0
    assert seen == [True]


def test_orchestrator_uses_strict_sector_central_mode(monkeypatch) -> None:
    from scripts import build_sector_central
    from scripts.build_sector_intelligence import default_steps

    seen: list[bool] = []

    def fake_main(*, strict: bool = False) -> int:
        seen.append(strict)
        return 0

    monkeypatch.setattr(build_sector_central, "main", fake_main)
    steps = default_steps()
    assert steps[2][0] == "scripts.build_sector_central"
    assert steps[2][1]() == 0
    assert seen == [True]


def test_targeted_allocation_skips_auxiliary_and_ai(monkeypatch, tmp_path) -> None:
    from scripts import build_allocation

    calls: list[str] = []
    monkeypatch.setattr(build_allocation.config, "ROOT", tmp_path)
    monkeypatch.setattr(
        build_allocation,
        "build_region",
        lambda region, _env, _built, _site: calls.append(f"region:{region}") or True,
    )
    monkeypatch.setattr(
        build_allocation,
        "_run_macro_narrative",
        lambda: calls.append("macro_narrative"),
    )
    monkeypatch.setattr(
        build_allocation,
        "_run_theme_discovery",
        lambda: calls.append("theme_discovery"),
    )
    monkeypatch.setattr(
        build_allocation,
        "_run_thematic_desk",
        lambda regions: calls.append("thematic_desk:" + ",".join(regions)),
    )

    stale = build_allocation.main(
        ["us"], run_auxiliary=False, run_ai=False
    )
    assert stale is False
    assert calls == ["region:us"]


def test_focused_basket_mode_stops_before_unrelated_tail() -> None:
    src = (ROOT / "scripts" / "build_baskets.py").read_text(encoding="utf-8")
    guard = src.index("if sector_intelligence_only:")
    tail = src.index("from scripts.build_anticipation import main as _build_anticipation")
    assert guard < tail
    assert "return 0" in src[guard:tail]


def _execute_native_stock_detail_boundary(monkeypatch, site, *, focused, callback):
    """Execute the actual detail-emission statement from the real producer.

    This isolates its publication boundary without running prices, models, R2,
    notifications or unrelated nightly work. Both old unguarded and new guarded
    statements are executable, so the tests discriminate the regression itself.
    """
    import ast
    import logging
    from pathlib import Path
    from scripts import build_theme_detail

    source = Path(__file__).resolve().parents[1] / 'scripts/build_baskets.py'
    parsed = ast.parse(source.read_text())
    main = next(n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    blocks = [n for n in main.body if any(isinstance(c, ast.Call)
              and isinstance(c.func, ast.Name) and c.func.id == 'build_detail_pages'
              for c in ast.walk(n))]
    assert len(blocks) == 1
    monkeypatch.setattr(build_theme_detail, 'build_detail_pages', callback)
    data, env, chart = {'source': 'same dated input'}, object(), {'dates': []}
    namespace = {'sector_intelligence_only': focused, 'data': data,
                 'site': site, 'env': env, 'chart': chart, 'log': logging.getLogger(__name__)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=blocks, type_ignores=[])),
                 str(source), 'exec'), namespace)
    return data, env, chart


def test_focused_publication_preserves_existing_stock_detail_without_dossiers(monkeypatch, tmp_path):
    page = tmp_path / 'basket' / 'semis.html'
    page.parent.mkdir()
    page.write_text('dated complete page with eleven available stock assessments')
    original = page.read_bytes()
    calls = []
    def missing_dossier_render(*args):
        calls.append(args)
        page.write_text('same-date page with zero stock assessments')
    assert not (tmp_path / 'stockdata').exists()
    _execute_native_stock_detail_boundary(monkeypatch, tmp_path, focused=True, callback=missing_dossier_render)
    assert calls == []
    assert page.read_bytes() == original


def test_focused_generation_does_not_use_incidental_stale_host_dossiers(monkeypatch, tmp_path):
    (tmp_path / 'stockdata').mkdir()
    (tmp_path / 'stockdata' / 'AMD.json').write_text('{"as_of":"old","conviction":{"score":80}}')
    calls = []
    _execute_native_stock_detail_boundary(monkeypatch, tmp_path, focused=True, callback=lambda *args: calls.append(args))
    assert calls == []  # host residue does not expand this lane's authority


def test_broad_build_retains_its_existing_stock_detail_call(monkeypatch, tmp_path):
    calls = []
    data, env, chart = _execute_native_stock_detail_boundary(
        monkeypatch, tmp_path, focused=False, callback=lambda *args: calls.append(args))
    assert len(calls) == 1
    assert calls[0] == (data, tmp_path, env, 'us', chart)


def test_broad_detail_error_keeps_existing_additive_behavior(monkeypatch, tmp_path, caplog):
    def unavailable(*args):
        raise RuntimeError('deliberate unavailable detail')
    _execute_native_stock_detail_boundary(monkeypatch, tmp_path, focused=False, callback=unavailable)
    assert 'theme detail pages failed' in caplog.text


def test_focused_workflow_stages_sector_outputs_not_stock_detail_pages():
    import shlex
    import yaml
    from pathlib import Path
    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] / '.github/workflows/sector-intelligence.yml').read_text())
    staged = []
    for job in workflow['jobs'].values():
        for step in job.get('steps', []):
            for line in str(step.get('run', '')).replace('\\\n', ' ').splitlines():
                if line.strip().startswith('git add '):
                    staged.extend(shlex.split(line, comments=True)[2:])
    assert 'site/basket' not in staged and 'site/basket/' not in staged
    for required in ['site/basketdata', 'site/sectors', 'site/sector_central.html',
                     'site/sectordata/sector_central.json', 'site/premiumdata/sector_central.json']:
        assert required in staged
