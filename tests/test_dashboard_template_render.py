"""Render smoke tests for templates/dashboard.html.j2 (macro.html + us_stocks.html).

Why this exists: the template is rendered ONLY by scripts/build_site.py's nightly
build — no test rendered it, so template-level Jinja errors (undefined filters,
missing-key crashes per the `{% if d.key is not none %}` gotcha) reached the
nightly uncaught.  Concrete incident: PR #1784's original commit shipped
`{{ _nbr | map('extract', _NBR_EN) }}` — 'extract' is not a Jinja2 filter — and
the full suite stayed green; the crash would have surfaced as a dead
us_stocks.html render.  This suite reproduces build_site.py's exact environment
and render calls against a small synthetic view-model so that class of bug fails
here first.

The environment mirrors scripts/build_site.py: FileSystemLoader on templates/,
filters['min'], and globals td / tr (engine.i18n) + zip.  The template is
rendered twice with the same vm — mode='macro' (macro.html) and mode='stocks'
(us_stocks.html) — exactly like the build.

The standout-board fixture row carries a `dossier` dict (action / why_now /
no_buy_reasons / stale_flags / authority_level) matching the Buy Decision Packet
producer shape (PR #1784, build_stock_library join) — a non-empty
`no_buy_reasons` list is what caught the 'extract' filter crash.  Do not trim
these keys.  NOTE (PR #3012, 2026-07-19): the dossier/details markup is now
gated `mode != 'stocks'` while the board itself is `mode != 'macro'`, so the
dossier renders in NEITHER mode — the fixture now proves intentional absence
(see test_stocks_mode_dossier_block_intentionally_absent) instead of reaching
the markup.
"""
from __future__ import annotations

import re
from pathlib import Path

import jinja2

ROOT = Path(__file__).resolve().parent.parent


def _env() -> jinja2.Environment:
    """Mirror scripts/build_site.py's Jinja env exactly (loader, filters, globals)."""
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.filters["min"] = lambda seq: min(seq)
    from engine import i18n  # noqa: PLC0415 — same import site as build_site.py
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    # P-MP1-SHELL: scripts/build_site.py registers this global for the migrated
    # Setups grid (templates/_us_prophet_plan_cards.html.j2) — mirrored here so
    # a render exercising us_prophet_book.plans does not crash on an undefined
    # global the real build always provides.
    from scripts.build_site import us_stance_projection  # noqa: PLC0415
    from engine.macro_news import CHANNEL_LABEL  # noqa: PLC0415
    env.globals["us_stance_projection"] = us_stance_projection
    env.globals["CHANNEL_LABEL"] = CHANNEL_LABEL
    return env


def _prophet_plan(**overrides) -> dict:
    """One plan row (site/prophet/index.json.plans shape) — the minimal fields
    templates/_us_prophet_plan_cards.html.j2 reads. Ticker defaults to ACME so
    it lines up with _board_row()'s default candidate join."""
    row = {
        "id": "ACME-BULL-20260701",
        "asset": "ACME",
        "lifecycle_state": "entered",
        "entry_status": "buy_now",
        "board_read": None,
        "_priority_score": 72.0,
        "entry_zone": None,
        "entry_zone_state": None,
        "closed": False,
        "plan_asof": "2026-07-04",
        "recorded_at": "2026-07-04",
        "entry_date": "2026-07-01",
        "signal_date": "2026-07-01",
    }
    row.update(overrides)
    return row


def _prophet_book(plans: "list | None" = None, **overrides) -> dict:
    # Two rows by default (not one): several suites assert "every board card"
    # properties (>= 2 occurrences) against the default fixture, matching the
    # pre-existing two-row (ACME + ZEUS) us_standouts.buy default this grid's
    # population moved off of.
    plans = plans if plans is not None else [
        _prophet_plan(),
        _prophet_plan(id="ZEUS-BULL-20260701", asset="ZEUS", lifecycle_state="ready",
                       entry_status="bounce_wait", _priority_score=48.0),
    ]
    from collections import Counter
    counts = Counter(p.get("lifecycle_state") for p in plans)
    book = {
        "asof": "2026-07-04",
        "intake": {"early_turn_watch": []},
        "lifecycle_counts": {k: counts.get(k, 0) for k in
                              ("watch", "ready", "entered", "delivering", "overtime",
                               "invalidated", "resolved")},
        "lifecycle_live_total": sum(v for k, v in counts.items() if k != "resolved"),
        "lifecycle_grand_total": sum(counts.values()),
        "plans": plans,
    }
    book.update(overrides)
    return book


# --------------------------------------------------------------------------- #
# Fixture — synthetic view-model
# --------------------------------------------------------------------------- #

def _board_row(**overrides) -> dict:
    """One standout-board card (us_standouts.buy item), field census from the
    template's card body.  Keys are set explicitly (None where inert) because
    dict-attribute access on a MISSING key yields Undefined and `n.field > 0`
    style guards then raise — explicit None keeps the honest-degradation
    branches rendering instead of crashing."""
    row = {
        "ticker": "ACME",
        "name": "Acme Corp",
        "sector": "Information Technology",
        "lane": "bottoming",
        "signal": None,
        "signal_date": "2026-07-01",
        "conviction": None,
        "alpha": 0.42,
        "alpha_z": 0.42,
        "alpha_entry": None,
        "alpha_sector_rank": 3,
        "alpha_sector_n": 25,
        "sector_rank": 3,
        "sector_n": 25,
        "price": 42.5,
        "off_high": -18.0,
        "ext_z": 0.1,
        "demand": None,
        "sue_z": None,
        "insider_buyers": None,
        "insider_net_mn": None,
        "insider_bps": None,
        "news_burst": None,
        "gex_confirm": None,
        "confluence_plus": None,
        "altdata": None,
        "smartmoney_chip": None,
        "eq_grade": None,
        "eq_grade_zh": None,
        "eq_dir": None,
        "eq_badge": None,
        "stop_guidance": None,
        "spark_svg": None,
        "sector_capitulating": None,
        "hold": None,
        "dir": None,
        "days": None,
        "count": None,
        "age_short": None,
        "age_short_zh": None,
        "align_tier": None,
        "urgency": None,
        "risk_sizing": None,
        "label": None,
        "entry_signal": None,
        "above_trend": None,
        # us_prophet_v1 row contract (research/PROPHET_BOARD_PRIORITY_ENGINE_
        # MASTERPLAN_BY_FABLE.md §3) — explicit None ON PURPOSE.  The committed
        # artifact does not carry these yet; the first nightly after the engine lane
        # merges fills them.  Keeping the whole census None here means the DEFAULT
        # fixture exercises the fail-soft branch (legacy lane partition, no filter
        # chips, no glow) on every test in this module and in the modules that import
        # _base_vm.  The populated shapes live in tests/test_us_board_priority_ui.py.
        "stage": None,            # live | setting_up | ran | blocked
        "prophet": None,          # {version, score, components{...}}
        "score_rank": None,
        "display_rank": None,
        "featured": None,         # the glow cohort (<=12 rows)
        "new": None,              # signal fired this session
        "days_since_signal": None,
        "theme": None,            # {id, name, name_zh, rank, reco}
        "theme_confirmed": None,
        # Buy Decision Packet dossier (PR #1784 shape) — see module docstring.
        "dossier": {
            "action": {"verb": "WAIT", "verb_zh": "等待", "tone": "wait"},
            "why_now": "Weekly cross fresh; daily reset underway.",
            "no_buy_reasons": ["freshness_expired", "risk_veto"],
            "stale_flags": ["insider stale 45d"],
            "authority_level": {"tier": "T2 calibrated", "css": "trust-t2"},
        },
    }
    row.update(overrides)
    return row


def _base_vm() -> dict:
    """Every key scripts/build_site.py passes to dashboard.html.j2 (the vm dict
    ahead of the macro.html render), populated with the smallest synthetic
    values that exercise the standout board in both modes."""
    return dict(
        latest={
            "date": "2026-07-04",
            "quad": "Q2",
            "quad_name": "Reflation",
            "label": "Q2 — Reflation",
            "confidence": 0.72,
            "fed_stance": None,
            "dislocation": None,
            "turning_point": None,
            "risk_radar": None,
            "rate_inflation_transmission": None,
            "cross_asset_confirm": None,
            "transition_state": "stable",
            "liquidity_overlay": "neutral",
            "conditions": None,
            "risk_state": None,
            "cycle_tag": "mid",
        },
        mtf=None,
        macro_catalysts=[],
        event_strip=[],
        event_risk=None,
        prediction_markets=None,
        narrative_regime=None,
        ndi=None,
        macro_news=None,
        macro_brief=None,
        macro_news_disclaimer="",
        macro_news_disclaimer_zh="",
        alerts=[],
        pb=None,
        month_name="July",
        commodities=[],
        sector_timing={},
        action_board={"hold": [], "avoid": [], "notable": [], "buy": []},
        top_setups=[],
        us_standouts={
            # ACME exercises the lane-grouped path + full dossier;
            # ZEUS exercises the ungrouped (lane=None) path + dossier-absent fail-soft.
            "buy": [
                _board_row(),
                _board_row(ticker="ZEUS", name="Zeus Industries", lane=None, dossier=None),
            ],
            "eligible": 2,
        },
        # P-MP1-SHELL central act: the migrated Setups grid's population
        # (defined below _base_vm — forward ref resolved by call, not import
        # time, since _prophet_book is a plain function).
        us_prophet_book=_prophet_book(),
        life_gate=None,
        us_prophet_episodes={},
        us_board_outcomes=None,
        market_gamma=None,
        components_confirming=[],
        components_contradicting=[],
        flip_plain=None,
        internals=[],
        size_style=[],
        breadth_div=None,
        breadth_panel=None,
        adv_breadth=None,
        sector_setups=None,
        generated_utc="2026-07-04 06:00",
        chart_liquidity=None,
        chart_credit_breadth=None,
        market_tiles=[],
        vix=None,
        chart_vix=None,
        positioning=[],
        holdings_changes=[],
        holdings_threshold=5.0,
        accumulation=[],
        flows_html="",
        health=[],
        factor_leadership=None,
        nowcast_hist=None,
        stance=None,
        index_health=[],
        alloc_card=None,
        risk_model=None,
        chart_risk_model=None,
        chart_curve=None,
        chart_vix_term=None,
        cross_asset=None,
        fear_euphoria=None,
        regime_snap=None,
        market_state=None,
        signal_stack=None,
        vol_shock=None,
        froth_fragility=None,
        fear_greed=None,
        sector_heat=None,
        dispersion_regime=None,
        policy_lever=None,
    )


def _render(mode: str) -> str:
    """The exact build_site.py call shape: render(**vm, mode=...)."""
    return _env().get_template("dashboard.html.j2").render(**_base_vm(), mode=mode)


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

def test_macro_mode_renders_without_exception():
    """macro.html render path — must not raise on the synthetic vm."""
    html = _render("macro")
    assert len(html) > 50_000  # full page, not a truncated shell


def test_stocks_mode_renders_without_exception():
    """us_stocks.html render path — must not raise on the synthetic vm."""
    html = _render("stocks")
    assert len(html) > 50_000


# --------------------------------------------------------------------------- #
# UD-B1 primary-route override (2026-09-20): keep the candidate component in
# source, but do not stack it above the established macro decision surface.
# --------------------------------------------------------------------------- #

def test_macro_mode_keeps_unified_dashboard_candidate_off_primary_route():
    """The primary macro route must open on the established regime radar."""
    html = _render("macro")
    assert 'id="ud-hero"' not in html, (
        "macro mode must not stack the held UD-B1 candidate above the current dashboard"
    )
    assert 'id="regime-radar"' in html, (
        "macro mode must retain the established #regime-radar decision surface"
    )


def test_stocks_mode_excludes_unified_dashboard_candidate():
    """The held UD-B1 candidate is not part of the stocks route either."""
    html = _render("stocks")
    assert 'id="ud-hero"' not in html


def _health_panel(html: str) -> str:
    match = re.search(r'<details class="[^"]*health-strip[^"]*" id="health".*?</details>', html, re.S)
    assert match, "macro render must contain the data-health panel"
    return match.group(0)


def test_macro_health_empty_is_unknown_not_green():
    panel = _health_panel(_render("macro"))
    opening = panel.split(">", 1)[0]
    assert "health-unknown" in opening
    assert "health-ok" not in opening
    assert "health unavailable" in panel
    assert "健康状态不可用" in panel
    assert "Source health data is unavailable for this build." in panel
    assert "all observed sources OK" not in panel


def test_macro_health_nonempty_all_ok_is_observed_healthy():
    vm = _base_vm()
    vm["health"] = [{
        "name": "Primary feed", "status": "ok", "rows": 12,
        "last_date": "2026-07-04", "error": None,
    }]
    panel = _health_panel(_env().get_template("dashboard.html.j2").render(**vm, mode="macro"))
    opening = panel.split(">", 1)[0]
    assert "health-ok" in opening
    assert "health-unknown" not in opening
    assert "health-neutral" not in opening
    assert "all observed sources OK" in panel
    assert "已观测数据源全部正常" in panel


def test_macro_health_blocked_only_is_neutral_not_observed_healthy():
    vm = _base_vm()
    vm["health"] = [{
        "name": "Known limitation", "status": "blocked", "rows": 0,
        "last_date": None, "error": "expected limitation",
    }]
    panel = _health_panel(_env().get_template("dashboard.html.j2").render(**vm, mode="macro"))
    opening = panel.split(">", 1)[0]
    assert "health-neutral" in opening
    assert "health-ok" not in opening
    assert "health-warn" not in opening
    assert "no active failures" in panel
    assert "无活动故障" in panel
    assert "all observed sources OK" not in panel


def test_macro_health_ok_plus_blocked_is_neutral_not_observed_healthy():
    vm = _base_vm()
    vm["health"] = [
        {"name": "Primary feed", "status": "ok", "rows": 12,
         "last_date": "2026-07-04", "error": None},
        {"name": "Known limitation", "status": "blocked", "rows": 0,
         "last_date": None, "error": "expected limitation"},
    ]
    panel = _health_panel(_env().get_template("dashboard.html.j2").render(**vm, mode="macro"))
    opening = panel.split(">", 1)[0]
    assert "health-neutral" in opening
    assert "health-ok" not in opening
    assert "health-warn" not in opening
    assert "no active failures" in panel
    assert "all observed sources OK" not in panel


def test_committed_macro_health_projection_carries_truth_state_contract():
    page = ROOT / "site" / "macro.html"
    html = page.read_text(encoding="utf-8")
    linked_css = []
    for href in re.findall(r'<link[^>]+href="([^"]+\.css(?:\?[^"#]*)?)"', html):
        rel = href.split("?", 1)[0]
        if rel.startswith(("/", "http://", "https://")):
            continue
        css_path = page.parent / rel
        if css_path.is_file():
            linked_css.append(css_path.read_text(encoding="utf-8"))
    projection = html + "\n" + "\n".join(linked_css)
    assert "health-unknown" in projection
    assert "health-neutral" in projection
    assert "Observed health entries for data sources this dashboard depends on." in html
    assert "No entries means health is unavailable, not healthy." in html
    assert "Every data source this dashboard depends on. OK = fresh." not in html


def test_macro_health_degraded_source_remains_attention_state():
    vm = _base_vm()
    vm["health"] = [{
        "name": "Primary feed", "status": "stale", "rows": 12,
        "last_date": "2026-07-03", "error": "late",
    }]
    panel = _health_panel(_env().get_template("dashboard.html.j2").render(**vm, mode="macro"))
    opening = panel.split(">", 1)[0]
    assert "health-warn" in opening
    assert "health-ok" not in opening
    assert "1" in panel and "need attention" in panel
    assert "需关注" in panel


def test_us_track_record_filter_bar_stays_in_document_flow():
    """The dense US ledger filters must scroll away instead of covering rows."""
    vm = _base_vm()
    vm["us_board_outcomes"] = {"rows": [{"ticker": "ACME"}], "as_of": "2026-07-04"}
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert (
        '.trd-dlg[data-market="us"] .trd-rail{ '
        'position:static;top:auto;z-index:auto; }'
    ) in html


def test_us_track_record_hold_value_keeps_languages_in_separate_blocks():
    """The hold unit must not leak Chinese into the English value line."""
    vm = _base_vm()
    vm["us_board_outcomes"] = {"rows": [{"ticker": "ACME"}], "as_of": "2026-07-04"}
    vm["us_track_ledger"] = {
        "state": "scored",
        "as_of": "2026-07-04",
        "summary": {"median_hold": 9, "horizon": 10},
    }
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert '<div class="trd-card-v l-en">9<span' in html
    assert 'class="trd-mut"> sessions</span></div>' in html
    assert '<div class="trd-card-v l-zh">9<span' in html
    assert 'class="trd-mut"> 个交易日</span></div>' in html
    assert '<span class="l-en">sessions</span><span class="l-zh">个交易日</span>' not in html


def test_stocks_mode_renders_standout_card_body():
    """The board-row loop body actually ran — this is where the template-crash
    class lives (per-card chips; the dossier/expander legs were removed from
    stocks mode by #3012).  An empty board would let a broken card body pass
    silently."""
    html = _render("stocks")
    assert "ACME" in html
    assert "ZEUS" in html  # ungrouped lane=None card renders too


def test_stocks_mode_keeps_existing_action_board_and_prophet_scorecards():
    """The declutter pass must preserve the two established decision surfaces.
    S2's surviving L1 panels stay in flow; only leftover research boards
    that are not in the frozen 7-panel list stay hidden."""
    html = _render("stocks")
    assert 'id="action-board"' in html
    assert 'class="panel span12 notable" id="us-standouts"' in html
    assert 'id="stocks-command"' not in html
    assert 'id="all-prophet-signals"' not in html
    assert "body.page-stocks #cross-asset-macro{display:none!important}" in html
    assert "body.page-stocks #holdings{display:none!important}" not in html
    assert "body.page-stocks #equity-scoreboard," not in html


def test_stocks_mode_dossier_block_intentionally_absent():
    """Supersedes test_stocks_mode_renders_dossier_block (the presence form)
    after PR #3012 — the removal its docstring warned about happened ON PURPOSE.

    Archaeology: the standout board renders only in stocks mode (the whole
    section sits under `mode != 'macro'`, ~L12886 — macro.html lost its Prophet
    cards to the macro-v2 grid).  PR #3012 (operator request 2026-07-19) then
    gated the Details dropdown + .nb-more panel — which contains the Buy
    Decision Packet dossier — behind `mode != 'stocks'`.  build_site.py renders
    only mode in {macro, stocks}, so the dossier markup is now unreachable in
    BOTH modes; #3012's "retained on macro.html" premise was wrong.

    This test pins the intentional absence: even a buy row carrying a FULL
    dossier (the ACME fixture — see test_fixture_row_carries_dossier_contract)
    must not emit the dossier or dropdown markup on stocks.  If the Buy
    Decision Packet is ever re-homed, flip these assertions back to presence
    so the 'extract'-filter crash class (#1784) is covered again."""
    html = _render("stocks")
    assert "ACME" in html  # board rendered — absence assertions are not vacuous
    assert "nb-dossier" not in html
    assert '<button class="nb-more-btn"' not in html  # dropdown toggle gone too


def test_fixture_row_carries_dossier_contract():
    """Pin the dossier fixture shape (Buy Decision Packet, PR #1784): a
    non-empty no_buy_reasons list is what exercised the reason-code mapping.
    Post-#3012 the markup no longer renders (see the absence test above), but
    the fixture stays full-shape: it keeps the producer contract documented and
    makes the absence assertion meaningful (dossier in, no dossier markup out)."""
    dossier = _base_vm()["us_standouts"]["buy"][0]["dossier"]
    for key in ("action", "no_buy_reasons", "stale_flags", "authority_level"):
        assert dossier.get(key), f"dossier fixture lost its {key!r} leg"
    assert isinstance(dossier["no_buy_reasons"], list) and dossier["no_buy_reasons"]


def test_both_modes_render_with_no_standouts():
    """us_standouts=None (older artifact / degraded build) must still render —
    the board falls back to the action_board.notable branch."""
    env = _env()
    vm = _base_vm()
    vm["us_standouts"] = None
    for mode in ("macro", "stocks"):
        html = env.get_template("dashboard.html.j2").render(**vm, mode=mode)
        assert len(html) > 50_000


# --------------------------------------------------------------------------- #
# P-MP1-SHELL RETIREMENT PROOF — the candidate stage/lane rail is GONE from the
# Setups grid (MP-1-prophet-board.md §6 row 4, §12 acceptance item 4). Prior to
# this packet, `us_standouts.buy` drove the Setups card grid directly and these
# three cases proved BOTH its artifact shapes (legacy `lane` vs priority
# `stage`) rendered correctly there. The grid's population moved to the plan
# book (site/prophet/index.json.plans, vm["us_prophet_book"]) — `us_standouts`
# is untouched data (still read by the Recently-fired/footnote sections below
# the grid) but no longer drives ANY card, heading, or filter bar on this page.
# The full candidate-board-schema rendered-HTML contract that used to live here
# now lives ONLY in tests/test_us_board_priority_ui.py, updated in the same PR
# to assert the same retirement.
# --------------------------------------------------------------------------- #

def _setups_section(html: str) -> str:
    """The Setups grid region ONLY — from its own marker up to the Candidates
    section that follows it.

    Scoping repair 2026-08-27.  These assertions used to grep the WHOLE page,
    which was correct only for as long as `nb-lane-hd` appeared nowhere on it.
    #6243 (shipping #6185) re-added `{% include "_us_board_cards.html.j2" %}`
    and with it a DELIBERATE lane rail — but in the *Candidates* section
    BELOW the migrated grid, not in the grid.  A page-wide grep cannot tell
    the retired rail from the restored one, so it read the restoration as a
    regression and this suite has been red on main ever since (invisibly: it
    was named by no `run:` step, wired in the same PR as this repair).
    tests/test_p0_prophet_candidate_board.py:282 pins that Candidates rail as
    REQUIRED, so a page-wide absence assertion here is not merely over-broad,
    it directly contradicts a live sibling contract.

    The retirement property MP-1 §12 item 4 actually claims is about the
    Setups grid, and slicing to it proves exactly that and nothing weaker.
    Both markers are asserted present so the slice can never silently become
    empty and turn every absence proof below into a vacuous pass.
    """
    start = html.find('id="us-life-grid"')
    assert start != -1, "Setups grid marker missing — absence proof would be vacuous"
    end = html.find('id="us-candidates"', start)
    assert end != -1, "Candidates section marker missing — slice would swallow it"
    return html[start:end]


def test_candidate_stage_rail_absent_from_setups_grid():
    """rail-absence proof (MP-1 §12 item 4): neither artifact shape — legacy
    `lane` (the default fixture) nor priority `stage` (the overlay) — puts a
    stage/lane heading or filter bar in the SETUPS GRID anymore, however the
    candidate board is shaped. `us_standouts` data is still read elsewhere
    (data-ticker sanity below), just never rendered as cards there.

    Scoped to the grid, not the page: the Candidates section below it carries
    its own lane rail on purpose (#6185/#6243) — see `_setups_section`."""
    from tests.test_us_board_priority_ui import priority_overlay, ran_overlay  # noqa: PLC0415

    # legacy-lane shape (the default _base_vm fixture)
    html_legacy = _render("stocks")
    setups_legacy = _setups_section(html_legacy)
    assert '<div class="nb-lane-hd"' not in setups_legacy
    assert '<div class="nb-stage-hd sg-' not in setups_legacy
    assert '<div class="pbf-bar" id="us-stage-filter"' not in setups_legacy
    # the filter bar's id is unique page-wide, so this one stays a whole-page
    # assertion: the rail's controls must not exist ANYWHERE, only its headings
    # moved to the Candidates section.
    assert 'id="us-stage-filter"' not in html_legacy

    # priority-stage shape (the overlaid fixture)
    vm = _base_vm()
    rows = [
        _board_row(ticker="ACME", entry_signal={"status": "buy_now"}, signal={"asof": "2026-07-04"}),
        _board_row(ticker="ZEUS", name="Zeus Industries", sector="Energy",
                   entry_signal={"status": "extended"}, signal={"asof": "2026-07-01"}),
        _board_row(ticker="NXE", name="NexGen Energy", sector="Energy", label="DOWNTREND",
                   entry_signal={"status": "avoid"}, signal={"asof": "2026-06-28"}),
    ]
    board = priority_overlay(rows)
    vm["us_standouts"] = {"buy": board, "ran": ran_overlay(board[-1:]), "eligible": 3}
    html_priority = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    setups_priority = _setups_section(html_priority)
    assert '<div class="nb-lane-hd"' not in setups_priority
    assert '<div class="nb-stage-hd sg-' not in setups_priority
    assert '<div class="pbf-bar" id="us-stage-filter"' not in setups_priority
    # the "Recently fired" ran-lane display (unaffected by the grid re-source —
    # it reads us_standouts.ran independently) still renders off this same data.
    # Page-wide on purpose: it lives OUTSIDE the grid, so slicing would make
    # this presence assertion fail for the wrong reason.
    assert '<div class="pbr" data-stage="ran">' in html_priority
    # candidate rows are simply not cards IN THE SETUPS GRID anymore: no
    # data-ticker for a name that exists ONLY in us_standouts.buy, not in
    # us_prophet_book. (NXE is still a legitimate Candidates-section card.)
    assert 'data-ticker="NXE"' not in setups_priority


def test_lifecycle_ladder_present_with_data_life_grid_marker():
    """The 7-cell lifecycle ladder (MP-1 §4b) + the migrated grid's W-L1
    neutralization marker (id="us-life-grid" data-mp1-grid="1") are what
    replaced the rail — both present on the default fixture, which carries
    one ACME plan (see _prophet_book())."""
    html = _render("stocks")
    assert 'class="mx-ladder mx-ladder--board"' in html
    assert 'id="us-life-grid"' in html and 'data-mp1-grid="1"' in html
    assert 'data-ticker="ACME"' in html
    assert 'data-life="entered"' in html


# --------------------------------------------------------------------------- #
# Live Tape strip (Phase 1 — research/LIVE_TAPE_SCOREBOARD_MASTERPLAN.md)
# --------------------------------------------------------------------------- #
# The macro.html MARKETS strip is a SIX-instrument futures tape:
#   ES=F, NQ=F, YM=F, RTY=F, ^TNX (10Y yield, data-fmt=tnx), DX-Y.NYB (DXY).
# The old SPY/QQQ/DJI/RUT spot tiles were removed FROM THE STRIP (the deep-dive
# dialog dlg-markets still carries the cash indices — that is the whole point of
# the "strip only" scope, and the presence check below guards the dialog stays).
# Absence assertions target ELEMENT markup (`mx5-mkt-tile ... data-sym="X"`), not
# bare class tokens (CSS rules always ship), per the harness note.

_TAPE_SYMS = ["ES=F", "NQ=F", "YM=F", "RTY=F", "^TNX", "DX-Y.NYB"]


def test_macro_strip_has_six_tape_tiles_in_order():
    """EXACTLY the six tape instruments, in D1 order, each as a live-patch tile
    (nb-px + data-sym + data-mkt=us). Order is pinned because the strip reads
    left-to-right as a macro tape (index futures -> yield -> dollar)."""
    html = _render("macro")
    # Each price tile exists with the live-patch contract intact.
    positions = []
    for sym in _TAPE_SYMS:
        m = re.search(
            rf'<div class="mx5-mkt-price nb-px[^"]*" data-sym="{re.escape(sym)}" data-mkt="us"',
            html,
        )
        assert m, f"tape price tile for {sym} missing from the strip"
        positions.append(m.start())
    # Strictly increasing => the six render in the specified order.
    assert positions == sorted(positions), f"tape tiles out of order: {positions}"


def test_macro_strip_tnx_display_transform_wired():
    """^TNX price AND delta carry data-fmt="tnx" so live.js divides the yield×10
    quote by 10 (%) and renders the delta in bps. Both nodes must be tagged."""
    html = _render("macro")
    assert re.search(r'<div class="mx5-mkt-price nb-px[^"]*" data-sym="\^TNX" data-mkt="us" data-fmt="tnx"', html)
    assert re.search(r'nb-chg[^"]*" data-sym="\^TNX" data-mkt="us" data-fmt="tnx"', html)


def test_macro_strip_labels_bilingual():
    """The six tiles carry their EN + ZH labels (bilingual UI law)."""
    html = _render("macro")
    for en, zh in [("S&amp;P fut", "标普期货"), ("Nasdaq fut", "纳指期货"),
                   ("Dow fut", "道指期货"), ("Russell fut", "罗素期货"),
                   ("10Y yield", "十年期收益率"), ("Dollar DXY", "美元指数")]:
        assert en in html, f"EN label {en!r} missing"
        assert zh in html, f"ZH label {zh!r} missing"


def test_macro_strip_spot_tiles_removed():
    """SPY/QQQ/DJI/RUT are GONE from the strip. Guard the exact strip-tile
    markup shape (mx5-mkt-tile price node), NOT bare symbols — the deep-dive
    dialog legitimately keeps ^DJI/^RUT/SPY/QQQ in mx5-dlg-idx-* nodes."""
    html = _render("macro")
    for spot in ["SPY", "QQQ", "^DJI", "^RUT", "DJI", "RUT"]:
        strip_tile = f'<div class="mx5-mkt-price nb-px" data-sym="{spot}" data-mkt="us"'
        assert strip_tile not in html, f"spot tile {spot} still in the strip"


def test_deep_dive_dialog_still_has_cash_indices():
    """Scope guard: only the STRIP changed. The dlg-markets deep-dive still
    carries the cash-index cards (mx5-dlg-idx-*) — if this ever goes empty the
    strip change over-reached into the dialog."""
    env = _env()
    vm = _base_vm()
    # Give the dialog a cash-index row to render (the strip is static regardless).
    # Keys mirror the dlg-markets card census (dd/above50/above200/rsi) — rsi is
    # accessed via `is not none`, which raises on a MISSING key, so it is set
    # explicitly (the harness's documented Undefined gotcha).
    vm["index_health"] = [{"ticker": "SPY", "price": 550.0, "chg": 0.3,
                           "dd": -1.2, "above50": True, "above200": True,
                           "rsi": 55.0, "label": "S&P 500"}]
    html = env.get_template("dashboard.html.j2").render(**vm, mode="macro")
    assert 'class="mx5-dlg-idx-px nb-px" data-sym="SPY"' in html


# --------------------------------------------------------------------------- #
# ⚡ Prophet × Top-setups presentation merge (2026-07-24 masterplan:
# research/PROPHET_TOPSETUPS_PRESENTATION_MERGE_MASTERPLAN.md).
# Contract under test: membership in the top_setups artifact IS the trigger gate
# (chip on the card), and the sub-board lists ONLY names not carded above.
# --------------------------------------------------------------------------- #


def _ts_row(ticker: str) -> str:
    """The clickable-row markup contract for the ⚡ trigger + 🏃 leaders tables.

    The <tr> carries the ticker for the delegated Terminal handler; asserting on
    this string is what the old `onclick="location.href='stock.html#…'"` pins
    became. The onclick form is the DEFECT, not an implementation detail:
    theme.js re-routes Terminal-covered analyzer links by intercepting <a href>
    clicks in the capture phase, and an inline location.href assignment is
    invisible to it — every row click landed on the retired stock.html analyzer.
    See test_ts_rows_are_terminal_routable, which pins that directly.
    """
    return f'<tr class="ts-row" data-tkr="{ticker}">'


def _ts_tkr_anchor(ticker: str) -> str:
    """The ticker cell is a real anchor so theme.js can see it (and so
    cmd-/middle-click keeps its native new-tab behaviour)."""
    return f'<a class="ts-tk-a" href="stock.html#{ticker}">'


def _setup_row(**overrides) -> dict:
    """One top_setups.buy row — field census from the sub-board table body.
    alpha/setup must be numeric ('%+.2f'|format crashes on Undefined); the
    guarded-but-`is not none`-tested keys (factor_z) must be EXPLICIT None
    (a MISSING key yields Undefined, and `Undefined is not none` is True, which
    then reaches the format filter — the same crash class the module docstring
    documents)."""
    row = {
        "ticker": "ZORB",
        "name": "Zorb Dynamics",
        "sector": "Industrials",
        "alpha": 0.61,
        "setup": 0.88,
        "sector_rank": None,
        "sector_n": None,
        "label": None,
        "alpha_entry": None,
        "factor_z": None,
        "insider_buyers": None,
        "insider_net_mn": None,
        "insider_bps": None,
        "sue_z": None,
        "signal": {"tier_cascade": "T1", "provisional": False},
    }
    row.update(overrides)
    return row


def _vm_with_setups(setup_rows: list) -> dict:
    vm = _base_vm()
    vm["top_setups"] = {"buy": setup_rows, "eligible": len(setup_rows)}
    return vm


def test_trigger_chip_renders_for_carded_overlap_ticker():
    """A board card whose ticker is also in top_setups.buy carries the ⚡ chip
    (fired form for T1), and — same render — the sub-board does NOT repeat the
    name as a table row: with full overlap the all-overlap empty state shows."""
    vm = _vm_with_setups([_setup_row(ticker="ACME", name="Acme Corp",
                                     sector="Information Technology")])
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert 'class="pv-trg"' in html            # chip rendered (fired = no -soon class)
    assert ">Triggered<" in html               # EN chip label (l-en span)
    assert ">已触发<" in html                   # ZH chip label (l-zh span)
    assert _ts_row("ACME") not in html          # no ts-row dupe
    assert "already on the board above" in html  # all-overlap empty state, not a bare table


def test_trigger_chip_imminent_variant_is_dashed():
    """T3 (about-to-cross) renders the dashed 'imminent' chip form."""
    vm = _vm_with_setups([_setup_row(ticker="ACME",
                                     signal={"tier_cascade": "T3", "provisional": True})])
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert "pv-trg-soon" in html
    assert ">Imminent<" in html and ">即将触发<" in html
    # provisional caveat reaches the chip tip (Tier 2), in plain words
    assert "about 1 in 10 of these vanish" in html


def test_no_chip_when_top_setups_absent():
    """Fail-soft (§0.5): top_setups None/empty -> cards render with no chip and
    no sub-board. This is the first-run / degraded-build shape."""
    env = _env()
    for absent in (None, []):
        vm = _base_vm()
        vm["top_setups"] = absent
        html = env.get_template("dashboard.html.j2").render(**vm, mode="stocks")
        assert "ACME" in html          # board itself still renders
        # element-level absence (the .pv-trg / .topsetups CSS rules always ship)
        assert '<span class="pv-trg' not in html   # no chip markup
        assert '<div class="topsetups"' not in html  # no sub-board wrapper


def test_subboard_lists_only_residual_names():
    """Filter runs before the display cap: the carded name (ACME) is excluded
    from the table, the non-carded name (ZORB) renders as a row, and the bridge
    count line states the split."""
    vm = _vm_with_setups([
        _setup_row(ticker="ACME", name="Acme Corp", sector="Information Technology"),
        _setup_row(),  # ZORB — not on the card board
    ])
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert _ts_row("ZORB") in html      # residual row shown
    assert _ts_row("ACME") not in html  # carded name filtered
    assert "Signals already shown on cards carry a ⚡." in html


def test_subboard_unfiltered_when_standouts_absent():
    """us_standouts=None -> empty carded set -> the sub-board falls back to the
    full unfiltered trigger list (no cards exist for the chips to live on).
    The panel gate is `_su or action_board.notable`, so the degraded shape needs
    a notable row for the panel (and with it the sub-board) to render at all —
    _board_row() already carries the notable branch's full key census."""
    vm = _vm_with_setups([_setup_row()])
    vm["us_standouts"] = None
    vm["action_board"]["notable"] = [_board_row(ticker="ZAPP", name="Zapp Co",
                                                spark_svg="<svg></svg>")]
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert _ts_row("ZORB") in html


def test_no_triggers_empty_state_preserved():
    """top_setups present but with zero buy rows keeps the original honest
    empty state (distinct from the all-overlap state)."""
    vm = _vm_with_setups([])
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert "No fresh buy triggers today" in html
    assert "already on the board above" not in html


# --------------------------------------------------------------------------- #
# SBX compact breadth scoreboard (Phase 2, LIVE_TAPE_SCOREBOARD_MASTERPLAN §4:
# 同花顺-style adv/dec glance bar + tiles; Size & Style removed by operator
# ruling D5; deep tables demoted into the #sbx-dlg dialog).
# --------------------------------------------------------------------------- #

def _breadth_vm() -> dict:
    vm = _base_vm()
    tier = {
        "key": "large", "label": "Large caps", "univ": "S&P 500", "n": 500,
        "adv": 180, "dec": 300, "adv_pct": 37.5, "pa50": 42.0, "pa200": 55.0,
        "nh": 8, "nl": 20, "net_nh": -12,
    }
    vm["breadth_panel"] = {
        "asof": "2026-07-24",
        "tiers": [tier],
        "comp": {"n": 1500, "adv": 412, "dec": 1044, "adv_pct": 28.3,
                 "pa50": 38.0, "pa200": 52.0, "net_nh": -37,
                 "label": "thin", "verdict": "Few names hold their trend", "tone": "neg"},
    }
    return vm


def test_sbx_glance_layer_renders_and_size_style_is_gone():
    """The compact layer renders (counts, bar, tiles, dialog) and the Size &
    Style section is fully removed from the dashboard (data stays upstream).
    The three alert deep-link anchors must survive the rebuild."""
    html = _env().get_template("dashboard.html.j2").render(**_breadth_vm(), mode="stocks")
    assert 'id="sbx-adv"' in html and ">412<" in html
    assert 'id="sbx-dec"' in html and ">1,044<" in html          # thousands-formatted
    assert 'id="sbx-bar-a"' in html and 'id="sbx-bar-d"' in html
    assert 'id="sbx-v50"' in html and ">38%<" in html
    assert 'id="sbx-nnh"' in html and ">-37<" in html.replace("−", "-")
    assert 'id="sbx-dlg"' in html                                 # demoted full board
    assert ">Large caps</b>" in html                              # tier table lives in dialog
    assert "Size &amp; style" not in html and "规模与风格" not in html
    for anchor in ('id="size-style"', 'id="breadth"', 'id="advanced-breadth"'):
        assert anchor in html, f"alert anchor {anchor} lost in rebuild"


def test_sbx_momentum_tile_states():
    """Momentum word derives from adv_breadth.mcc.summ_rising alone (mcc.band
    is already a translated object — never branch on it); absent internals
    degrade to an em-dash tile, never a crash."""
    env = _env()
    vm = _breadth_vm()
    html = env.get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert ">—<" in html                                          # adv_breadth=None → dash
    vm["adv_breadth"] = None  # explicit None, same path
    vm2 = _breadth_vm()
    # producer-shaped minimum: headline + footer keys are accessed UNGUARDED in
    # the dialog internals section; the optional sub-blocks (thrust/hl/div/par)
    # each guard themselves and may be absent
    vm2["adv_breadth"] = {
        "headline": {"tone": "muted", "label": "neutral", "verdict": "internals mixed"},
        "mcc": {"osc": "+12", "band": "positive", "svg": "",
                "summ_rising": True, "summ_chg20": "+120"},
        "asof": "2026-07-24", "deep_from": "1962",
    }
    html2 = env.get_template("dashboard.html.j2").render(**vm2, mode="stocks")
    assert ">Building<" in html2 and ">增强<" in html2


def test_sbx_fail_soft_without_breadth_panel():
    """breadth_panel=None (degraded nightly) renders the honest unavailable
    line — no bar, no crash, and the panel itself still exists."""
    vm = _base_vm()   # breadth_panel=None in the base fixture
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert 'id="equity-scoreboard"' in html
    assert "Breadth data unavailable" in html
    assert 'id="sbx-adv"' not in html


# --------------------------------------------------------------------------- #
# 🏃 Leaders strip (2026-07-28 gate-width order).
# Contract under test: us_standouts.leaders renders a SEPARATE coverage strip
# below the trigger sub-board; the entry column is always watch-don't-chase; and
# a pre-migration artifact (no `leaders` key) renders the page unchanged.
# Absence assertions target ELEMENT markup, not bare class tokens.
# --------------------------------------------------------------------------- #

_LEADERS_WRAPPER = '<div class="topsetups leaders-strip">'
# Chip markup, not bare phrases: "wait for pullback" also appears as prose inside an
# unrelated card-legend help popover, so a substring assertion would be vacuous.
_WAIT_CHIP = '<span class="ent-warn"><span class="l-en">wait for pullback</span>'
_ZONE_CHIP = '<span class="ent-good"><span class="l-en">pullback zone</span>'


def _leader_row(**overrides) -> dict:
    """One us_standouts.leaders row — field census from the strip's table body.
    alpha must be numeric ('%+.2f'|format crashes on Undefined); off_high / ext_z /
    entry_signal are tested with `is not none` after a `.get`, so they are set
    EXPLICITLY (a missing key yields Undefined, and the guards behave differently)."""
    row = {
        "ticker": "RUNR",
        "name": "Runner Industries",
        "sector": "Information Technology",
        "lane": "leader",
        "alpha": 2.31,
        "off_high": -1.4,
        "label": "advancing",
        "ext_z": None,
        "entry_signal": None,
    }
    row.update(overrides)
    return row


def _vm_with_leaders(leader_rows) -> dict:
    """leader_rows=None drops the key entirely (the pre-migration artifact shape)."""
    vm = _base_vm()
    if leader_rows is None:
        vm["us_standouts"].pop("leaders", None)
    else:
        vm["us_standouts"]["leaders"] = leader_rows
    return vm


def test_leaders_strip_renders_with_watch_dont_chase_stance():
    """One leaders row -> the strip renders, headed by 🏃, and the entry column
    reads 'wait for pullback' (no fresh trigger exists for any leader)."""
    vm = _vm_with_leaders([_leader_row()])
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert _LEADERS_WRAPPER in html
    # 🏃 anchored to the strip header — the emoji also appears on an unrelated
    # act-now header, so a bare `'🏃' in html` would be vacuous.
    assert '🏃 <span class="l-en">Market leaders</span>' in html
    assert ">市场领跑股<" in html                                  # ZH header (bilingual law)
    assert _WAIT_CHIP in html and ">等待回调<" in html
    assert _ts_row("RUNR") in html                                  # row is clickable
    assert "+2.31" in html                                         # α column formatted


def test_ts_rows_are_terminal_routable():
    """Both clickable tables (⚡ More fresh triggers, 🏃 Market leaders) must be
    reachable by theme.js's Terminal intercept.

    That intercept is a capture-phase listener on `a[href]` — it re-points
    stock.html#TKR at the Terminal portal. A `<tr onclick="location.href=…">`
    is invisible to it, so those rows navigated to the retired stock.html
    analyzer no matter what theme.js did (reported 2026-08-03). The pin is
    therefore two-sided: the anchor must exist AND the onclick form must be
    gone, on a render that has rows in BOTH tables (an empty table would make
    the absence half vacuous).
    """
    vm = _vm_with_leaders([_leader_row()])           # 🏃 RUNR
    vm["top_setups"] = {"buy": [_setup_row()]}       # ⚡ ZORB (not carded -> residual)
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")

    for ticker in ("RUNR", "ZORB"):
        assert _ts_row(ticker) in html, f"{ticker} row missing — assertions below are vacuous"
        assert _ts_tkr_anchor(ticker) in html, f"{ticker} ticker is not an anchor"

    # The defect itself: no ts-row may navigate via an inline location.href.
    assert "onclick=\"location.href='stock.html#" not in html

    # The delegated handler that covers clicks on the REST of the row.
    assert "tr.ts-row[data-tkr]" in html
    assert "window.MDXTerminal" in html


def test_risk_radar_link_targets_the_dialog():
    """The stocks-page market-state strip links to the risk radar POPUP.

    #sx-risk-v2 is the card wrapper, whose face is display:none on macro.html
    (the band is its face) and whose tray only opens through mx5OpenDlg — so the
    old anchor scrolled to an invisible element and nothing popped. macro.html's
    alert-hash resolver opens any .mx5-dlg named by the hash, and dlg-risk is
    that dialog.
    """
    vm = _vm_with_leaders([_leader_row()])
    # The strip is gated on market_state; the base VM pins it None, which would
    # make both assertions below vacuous.
    vm["market_state"] = {"color": "yellow", "label_en": "mixed", "label_zh": "混合"}
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert 'class="stk-ctx-strip' in html   # strip rendered — absence is not vacuous
    assert 'class="scx-more" href="macro.html#dlg-risk"' in html
    assert 'href="macro.html#sx-risk-v2"' not in html


def test_macro_alert_hash_waits_for_the_access_tier():
    """macro.html must not resolve a #dlg-* deep link before tier_preview.js boots.

    This block is inline in the body; tier_preview.js is `defer`, so at parse
    time window.MMXAccessPreview is undefined — and mx5OpenDlg reads an absent
    controller as anon, falling through to a hard location.href='/?signin=1…'
    when MMOnboard is also not up yet. Every cold #dlg-* arrival therefore
    bounced the visitor to the landing sign-in, signed in or not (measured
    2026-08-03 against the rendered site). The fix waits for the tier event.
    """
    html = _env().get_template("dashboard.html.j2").render(**_vm_with_leaders(None),
                                                           mode="macro")
    assert "mmx-access-tier" in html
    assert "_resolveAlertHashOnce" in html
    # The unguarded parse-time call is the defect — it must be gone.
    assert "\n    _resolveAlertHash();\n" not in html


def test_leaders_strip_absent_when_key_missing():
    """Pre-migration artifact (no `leaders` key): no strip, no exception, page
    otherwise unchanged."""
    vm = _vm_with_leaders(None)
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert len(html) > 50_000
    assert "ACME" in html            # board still rendered — absence is not vacuous
    assert _LEADERS_WRAPPER not in html
    assert _WAIT_CHIP not in html


def test_leaders_strip_absent_when_empty_list():
    """`leaders: []` (gate admitted nobody tonight) is the same honest no-op."""
    vm = _vm_with_leaders([])
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert "ACME" in html
    assert _LEADERS_WRAPPER not in html


def test_leaders_strip_buy_zone_dict_access():
    """buy_zone arrives as a PLAIN DICT in the artifact; the strip uses the same
    `_bz.low` attribute-access idiom as the card body above it (Jinja falls back
    to __getitem__). This pins that the zone renders rather than silently
    degrading to the wait state."""
    vm = _vm_with_leaders([_leader_row(
        entry_signal={"buy_zone": {"low": 98.5, "high": 104.25}})])
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert _ZONE_CHIP in html and ">回调买区<" in html
    assert "$98.50–$104.25" in html
    assert _WAIT_CHIP not in html


def test_leaders_strip_partial_buy_zone_falls_back_to_wait():
    """A half-populated zone (high=None) is not a zone — fall back to the honest
    wait stance rather than printing '$98.50–None'."""
    vm = _vm_with_leaders([_leader_row(
        entry_signal={"buy_zone": {"low": 98.5, "high": None}})])
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert _WAIT_CHIP in html
    assert _ZONE_CHIP not in html


def test_leaders_strip_extended_chip_over_threshold():
    """ext_z > 2.0 adds the chase-risk 'extended' chip; at/below it stays off."""
    env = _env()
    hot = env.get_template("dashboard.html.j2").render(
        **_vm_with_leaders([_leader_row(ext_z=2.6)]), mode="stocks")
    assert "Price is unusually far above its trend — chasing here is risky." in hot
    cool = env.get_template("dashboard.html.j2").render(
        **_vm_with_leaders([_leader_row(ext_z=1.1)]), mode="stocks")
    assert "Price is unusually far above its trend" not in cool


def test_leaders_strip_display_cap_is_fifteen():
    """The strip renders at most 15 rows even if the artifact carries more."""
    rows = [_leader_row(ticker=f"L{i:02d}", name=f"Leader {i}") for i in range(20)]
    html = _env().get_template("dashboard.html.j2").render(
        **_vm_with_leaders(rows), mode="stocks")
    assert "stock.html#L14" in html
    assert "stock.html#L15" not in html


def test_leaders_strip_renders_without_top_setups():
    """The strip is a sibling of the trigger sub-board, not nested inside it:
    top_setups absent must NOT suppress it."""
    vm = _vm_with_leaders([_leader_row()])
    vm["top_setups"] = None
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert _LEADERS_WRAPPER in html
    assert '<div class="topsetups">' not in html   # the trigger sub-board is gone


# --------------------------------------------------------------------------- #
# M12 — the leaders strip names its real rank key.
#
# The strip has ranked by trailing 3-month TOTAL return plus a theme boost since the
# v2 rebuild (_select_leaders, scripts/build_stock_library.py), with residual alpha
# only as the tiebreak.  The headline still said "Strongest runners by edge" and sat
# directly above a column headed "edge (α)", so the two together claimed an ordering
# the engine does not perform.  The column stays — it is a real read — but neither
# the headline nor the header may claim it sorts the table.
#
# Every assertion below is SCOPED TO THE STRIP: "strength" heads the unrelated
# top-setups table on the same page, so a document-wide assertion would be vacuous
# in one direction and wrong in the other.
# --------------------------------------------------------------------------- #

def _leaders_strip(html: str) -> str:
    start = html.find(_LEADERS_WRAPPER)
    assert start != -1, "the leaders strip did not render"
    end = html.find("</table>", start)
    assert end != -1
    return html[start:end]


def test_leaders_strip_slicer_excludes_the_top_setups_table():
    """Render both tables at once and prove the slice holds one and not the other."""
    vm = _vm_with_leaders([_leader_row()])
    vm["top_setups"] = {"buy": [_setup_row()], "eligible": 1}
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    strip = _leaders_strip(html)
    assert '<span class="l-en">strength</span>' in html
    assert "ZORB" in html and "ZORB" not in strip     # its rows are outside the slice
    assert "RUNR" in strip
    assert len(strip) < len(html) / 4


def test_leaders_headline_names_momentum_not_edge():
    vm = _vm_with_leaders([_leader_row()])
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    strip = _leaders_strip(html)
    assert ('<span class="l-en">The strongest runners over the past three months. '
            'No fresh entry yet — watch, don’t chase.</span>') in strip
    assert ("过去三个月最强的领跑股。暂无新入场信号——观察，勿追高。") in strip
    # the retired overclaim, in both languages
    assert "Strongest runners by edge" not in html
    assert "按优势排名的最强领跑股" not in html
    # the stance survives the rewrite (DESIGN_DOCTRINE Law 1)
    assert "watch, don’t chase" in strip and "观察，勿追高" in strip


def test_leaders_headline_tip_explains_the_user_decision_without_engine_prose():
    vm = _vm_with_leaders([_leader_row()])
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    strip = _leaders_strip(html)
    assert "have led the market over the past three months and remain near their highs" in strip
    assert "They are not buy calls" in strip
    assert "Wait for a pullback toward the shown zone" in strip
    assert "过去三个月领跑市场，且仍接近高位" in strip
    assert "它们不是买入建议" in strip
    assert "entry-gated" not in strip and "rank key" not in strip


def test_leaders_alpha_header_stops_claiming_it_orders_the_table():
    """The tiebreak stays, but the reader sees plain language rather than engine notation."""
    vm = _vm_with_leaders([_leader_row()])
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    strip = _leaders_strip(html)
    assert '<span class="l-en">relative strength</span><span class="l-zh">相对强度</span>' in strip
    assert "Used only to break ties here" in strip
    assert "这里只用于打破并列" in strip
    # the retired header, scoped to the strip (the top-setups table still uses it)
    assert "edge (α)" not in strip and "优势 (α)" not in strip
    # the column is KEPT: the value still renders under the new header
    assert "+2.31" in strip


def test_leaders_theme_header_does_not_contradict_the_theme_boost():
    """The header used to say theme membership "does not rank this table" while the
    rank key adds +0.5 for it — the two halves of the same surface disagreeing."""
    vm = _vm_with_leaders([_leader_row(theme={"id": "ai_software", "name": "AI software",
                                              "name_zh": "AI软件", "rank": 3})])
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    strip = _leaders_strip(html)
    assert "Membership adds a small boost to where a name sits in this table" in strip
    assert "归属会为该股在本表的名次带来小幅加成" in strip
    assert "theme membership does not rank this table" not in html
    assert "主题归属不影响本表排序" not in html


# --------------------------------------------------------------------------- #
# m6 (leaders half) — bull_days == 0 is "turned today", not a missing age.
# The same truthiness bug lived in three conditionals; this is the third.
# --------------------------------------------------------------------------- #

def _themed_leader(bull_days):
    theme = {"id": "ai_software", "name": "AI software", "name_zh": "AI软件", "rank": 3}
    if bull_days is not None:
        theme["bull_days"] = bull_days
    return _leader_row(theme=theme, theme_confirmed=True)


def test_leaders_theme_tip_reads_today_at_zero_bull_days():
    html = _env().get_template("dashboard.html.j2").render(
        **_vm_with_leaders([_themed_leader(0)]), mode="stocks")
    strip = _leaders_strip(html)
    assert "The theme itself only just turned up (today) —" in strip
    assert "主题本身刚刚转强（今日） —" in strip
    assert "(0 days in)" not in html and "（已进入第0天）" not in html


def test_leaders_theme_tip_keeps_a_real_age_and_stays_silent_on_none():
    """Both other directions of the same conditional: a real age still prints, and a
    genuinely unknown one must not be reported as 'today'."""
    env = _env()
    real = env.get_template("dashboard.html.j2").render(
        **_vm_with_leaders([_themed_leader(4)]), mode="stocks")
    assert "The theme itself only just turned up (4 days in) —" in _leaders_strip(real)
    assert "（已进入第4天）" in _leaders_strip(real)
    unknown = env.get_template("dashboard.html.j2").render(
        **_vm_with_leaders([_themed_leader(None)]), mode="stocks")
    strip = _leaders_strip(unknown)
    assert "The theme itself only just turned up —" in strip
    assert "(today)" not in strip and "（今日）" not in strip


# --------------------------------------------------------------------------- #
# §17 mobile (2026-08-02) — the prophet-panel strip tables must fit a 390px
# panel without x-scroll: at ≤680px the tertiary columns are hidden, keyed by
# per-column c-* classes.  The contract has two halves:
#   1. every <th> in BOTH strip tables carries a c-* class — a classless column
#      would silently sit outside the mobile budget and re-widen the table;
#   2. each class is either in the mobile KEEP set (identity, edge, stance) or
#      named in the 680px hide rule.
# Adding a column therefore forces an explicit mobile decision here.
# The G0.5a theme column only renders when a row stamps a theme, so the fixture
# stamps one to bring it under contract; its decision: context, not stance → hidden.
# --------------------------------------------------------------------------- #

_MOBILE_KEEP = {"c-stock", "c-edge", "c-buy", "c-entry"}


def _strip_thead_class_sets(html: str) -> list[set[str]]:
    """Per strip table (document order), the union of c-* classes on its header
    cells — failing if any <th> carries none."""
    sets = []
    for thead in re.findall(r'<table class="ts-tbl">\s*<thead>(.*?)</thead>', html, re.S):
        classes: set[str] = set()
        for attrs in re.findall(r"<th\b([^>]*)>", thead):
            m = re.search(r'class="([^"]*)"', attrs)
            c_marks = {c for c in (m.group(1).split() if m else []) if c.startswith("c-")}
            assert c_marks, f"strip <th{attrs}> has no c-* mobile class"
            classes |= c_marks
        sets.append(classes)
    return sets


def test_strip_tables_mobile_column_contract():
    vm = _vm_with_leaders([_leader_row(theme={"id": "ai_software", "name": "AI software",
                                              "name_zh": "AI软件", "rank": 3})])
    vm["top_setups"] = {"buy": [_setup_row()]}   # ZORB — residual, so the trigger table renders
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")

    per_table = _strip_thead_class_sets(html)
    assert len(per_table) == 2, "expected exactly the trigger + leaders strip tables"
    trigger, leaders = per_table
    assert trigger == {"c-stock", "c-sector", "c-edge", "c-rank", "c-buy",
                       "c-cycle", "c-trend", "c-factor", "c-setup"}
    assert leaders == {"c-stock", "c-sector", "c-theme", "c-edge", "c-offhigh",
                       "c-state", "c-entry"}

    # Half 2: the ≤680px rule hides exactly every non-keep column of both
    # tables.  `.topsetups .ts-tbl .c-*` selectors exist ONLY in that rule, so
    # scraping them from the page IS reading the hide list.
    hidden = set(re.findall(r"\.topsetups \.ts-tbl \.(c-[a-z]+)", html))
    assert hidden == (trigger | leaders) - _MOBILE_KEEP


# --------------------------------------------------------------------------- #
# MO-PAID-001_FIX_R1 — the two-axis "Regime — now & where it's headed" panel
# is the labeled regime read served on us_stocks.html (F00C F01 ruling D15).
# The OLD include lived INSIDE the macro-only `{% if mode == 'macro' %}` block
# (~line 2622 → ~line 16081, no else) behind `mode != 'macro'`, so the guard
# could never be true and the panel rendered on NO page. The new include sits
# in the stocks block, immediately after `{% endif %}{# /market_state B4 #}`
# and BEFORE `{% if action_board %}`. These four tests pin:
#   T1 — stocks + base_effect fixture: panel renders with both axis labels.
#   T2 — macro + SAME fixture: panel absent (the control — macro never hosts it).
#   T3 — stocks with base_effect absent/partial: degrades silently, no crash.
#   T4 — structural: exactly one include statement, on a line past the
#   `{# /mode != 'stocks' #}` close (so a future move back into the dead
#   macro-only section fails CI at detection).
# --------------------------------------------------------------------------- #


def _be_axis(q1: float, current_yoy: float, yoy_path: list[float] | None = None) -> dict:
    """One base_effect axis (growth or inflation). Field census from
    templates/_base_effect_strip.html.j2: q1/q2/q3 used in arithmetic + _iq
    branches; yoy_path used by `_axnote` when current_yoy is set."""
    return {
        "q1": q1,
        "q2": q1,            # shape-only; the template iterates ['q1','q2','q3']
        "q3": q1,
        "current_yoy": current_yoy,
        "yoy_path": yoy_path if yoy_path is not None else [current_yoy, current_yoy, current_yoy],
    }


def _vm_with_base_effect(**overrides) -> dict:
    """Base vm with both base_effect axes populated so the panel renders.
    Pass growth_only=True / inflation_only=True to exercise the partial case."""
    growth = overrides.pop("growth", _be_axis(0.5, 2.4))
    inflation = overrides.pop("inflation", _be_axis(-0.3, 1.9))
    if overrides.pop("growth_only", False):
        inflation = None
    if overrides.pop("inflation_only", False):
        growth = None
    base_effect = overrides.pop("base_effect", None)
    vm = _base_vm()
    if base_effect is not None:
        vm["latest"]["base_effect"] = base_effect
    else:
        vm["latest"]["base_effect"] = {"growth": growth, "inflation": inflation}
    vm.update(overrides)
    return vm


def _regime_read_section(html: str) -> str:
    """The #regime-read panel slice (id="regime-read" ... </div> closing that
    panel).  Pinning to the panel preserves bilingual parity: if the same
    label appears elsewhere on the page, the assertions are still scoped."""
    match = re.search(
        r'<div class="panel span12 bfwd rr-combined" id="regime-read">.*?</div>\s*</div>',
        html,
        re.S,
    )
    assert match, "#regime-read panel missing — T1 / T2 / T3 assertions would be vacuous"
    return match.group(0)


def test_t1_stocks_renders_regime_read_panel_with_both_axes():
    """T1: stocks mode + a populated base_effect (growth + inflation) renders
    the #regime-read panel EXACTLY ONCE, with both EN and ZH axis labels."""
    vm = _vm_with_base_effect()
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert html.count('id="regime-read"') == 1
    section = _regime_read_section(html)
    # Axis labels (EN + ZH), scoped to the panel — neither token appears
    # anywhere else on us_stocks, so an unscoped grep is also safe.
    assert "Growth" in section and "增长" in section
    assert "Inflation" in section and "通胀" in section


def test_t2_macro_does_not_host_the_regime_read_panel():
    """T2: macro mode + the SAME fixture — the panel is stocks-only, so macro
    must NEVER carry #regime-read. This is the control test: stocks renders,
    macro does not, on identical input."""
    vm = _vm_with_base_effect()
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="macro")
    assert 'id="regime-read"' not in html


def test_t3_stocks_degrades_silently_when_base_effect_missing_or_partial():
    """T3: stocks mode + an absent or partial base_effect must render without
    exception and WITHOUT emitting #regime-read. Two shapes exercised:
    latest.base_effect entirely missing, and one axis present / the other None
    (the partial case the include's `_has_be` guard was built for)."""
    env = _env()
    # Case A: base_effect key absent on latest.
    vm_absent = _base_vm()
    html_absent = env.get_template("dashboard.html.j2").render(**vm_absent, mode="stocks")
    assert 'id="regime-read"' not in html_absent
    # Case B: only growth (inflation None) — the include's `_has_be` guard
    # checks BOTH axes, so the panel stays absent.
    vm_growth_only = _vm_with_base_effect(inflation_only=False, inflation=None)
    html_growth_only = env.get_template("dashboard.html.j2").render(**vm_growth_only, mode="stocks")
    assert 'id="regime-read"' not in html_growth_only


def test_t4_structural_exactly_one_include_past_macro_block_close():
    """T4: the template source carries exactly one INCLUDE statement of
    _regime_read_panel.html.j2, and that include's line number is strictly
    past the closing `{# /mode != 'stocks' #}` of the nested stocks-only
    block (which sits inside the macro-only block at ~line 2622 → ~16081).
    A future move back into the dead section would push the include's line
    number back below that close and fail CI loudly."""
    src_path = ROOT / "templates" / "dashboard.html.j2"
    src = src_path.read_text(encoding="utf-8")
    lines = src.splitlines()

    # Exactly one include statement (NOT one literal occurrence — the spec'd
    # comment also names the file, so a raw string grep would over-fire; this
    # pattern matches only the actual Jinja include).
    include_hits = [i + 1 for i, line in enumerate(lines)
                    if re.search(r'\{%\s*include\s+["\']_regime_read_panel\.html\.j2["\']\s*%\}', line)]
    assert len(include_hits) == 1, (
        f"expected exactly one include of _regime_read_panel.html.j2, found {len(include_hits)} "
        f"on lines {include_hits}"
    )
    include_line = include_hits[0]

    # Find the closing `{# /mode != 'stocks' #}` (the nested stocks-only
    # block that the macro-only section used to enclose). The new include
    # must sit past it — the dead-block site (~15538) sat well before it.
    close_lines = [i + 1 for i, line in enumerate(lines)
                   if re.search(r"\{#\s*/mode\s*!=\s*['\"]stocks['\"]\s*#\}", line)]
    assert close_lines, "the nested `{# /mode != 'stocks' #}` close marker is missing — the test assumes the macro block still has this structure"
    assert include_line > close_lines[0], (
        f"include at line {include_line} sits BEFORE the {{# /mode != 'stocks' #}} close "
        f"at line {close_lines[0]} — the include is back inside the macro-only block"
    )


# --------------------------------------------------------------------------- #
# E0-G (2026-10-04, #8317): the Fed dialog's Inflation Read keys its state
# word on the transmission owner's inflation LEVEL token and its second clause
# on the owner's EXPECTATIONS token — both carried verbatim, both null-safe.
# The tests drive the owner's real producer through the Rates Command row into
# the real template block (the serialized route), so a vocabulary move on
# either side trips them.
# --------------------------------------------------------------------------- #

_INF_READ_START = "      {# ── d. Inflation Read"
_INF_READ_END = "      {# ── e. Risk Indicators"


def _inflation_read_block() -> str:
    src = (ROOT / "templates/dashboard.html.j2").read_text()
    start = src.index(_INF_READ_START)
    end = src.index(_INF_READ_END, start)
    return src[start:end]


def _render_inflation_read(row: dict) -> str:
    return jinja2.Environment(autoescape=True).from_string(_inflation_read_block()).render(_dlgrc_inf=row)


def _inflation_read_via_owner(core_pce_yoy, wedge):
    """Owner state (real producer) -> Rates Command row (real builder) -> real template block."""
    import pandas as pd  # noqa: PLC0415
    from engine import rate_inflation_transmission as rit  # noqa: PLC0415
    from engine import rates_inflation_command as rc  # noqa: PLC0415

    frame = pd.DataFrame({
        "core_pce_yoy": [core_pce_yoy],
        "infl_exp_5y": [2.5],
        "breakeven_5y5y": [2.5 + wedge] if wedge is not None else [None],
    })
    state = rit.current_state(frame)
    row = rc._build_inflation_row({"state": state}, [])
    return row, _render_inflation_read(row)


def _pill(en: str, zh: str) -> str:
    return f'<span class="l-en">{en}</span><span class="l-zh">{zh}</span>'


def test_inflation_read_at_target_with_zero_wedge_reads_at_target():
    row, html = _inflation_read_via_owner(2.0, 0.0)
    assert row["regime"] == "at target" and row["anchoring"] == "anchored"
    assert _pill("At target", "接近目标") in html
    assert "Core prices are close to the Fed’s 2% target; longer-run expectations look steady." in html
    assert "核心物价接近美联储2%目标；长期预期看起来稳定。" in html
    assert "Above target" not in html and "points above" not in html
    assert "(expectations: anchored)" in html and "（预期：锚定）" in html
    assert "color:var(--up,#22d97a)" in html


def test_inflation_read_above_target_drifting_up_is_the_wrong_way():
    row, html = _inflation_read_via_owner(2.8, 0.31)
    assert row["regime"] == "above target" and row["anchoring"] == "drifting up"
    assert _pill("Above target", "高于目标") in html
    assert "Core prices are still 0.8 points above the Fed’s 2% target; longer-run expectations are drifting up." in html
    assert "核心物价仍高于美联储2%目标 0.8 个百分点；长期预期上行脱锚。" in html
    assert "(expectations: drifting up)" in html and "（预期：上行脱锚）" in html
    assert "color:var(--down,#ef4444)" in html


def test_inflation_read_below_target_drifting_down_is_the_wrong_way():
    row, html = _inflation_read_via_owner(1.5, -0.31)
    assert row["regime"] == "below target" and row["anchoring"] == "drifting down"
    assert _pill("Below target", "低于目标") in html
    assert "Core prices are 0.5 points below the Fed’s 2% target; longer-run expectations are drifting down." in html
    assert "核心物价低于美联储2%目标 0.5 个百分点；长期预期下行。" in html
    assert "(expectations: drifting down)" in html and "（预期：下行）" in html
    assert "color:var(--down,#ef4444)" in html


def test_inflation_read_above_target_anchored_is_amber():
    row, html = _inflation_read_via_owner(2.8, 0.0)
    assert row["regime"] == "above target" and row["anchoring"] == "anchored"
    assert _pill("Above target", "高于目标") in html
    assert "still 0.8 points above the Fed’s 2% target; longer-run expectations look steady." in html
    assert "color:var(--warn,#f59e0b)" in html


def test_inflation_read_missing_expectations_model_discloses_plainly():
    row, html = _inflation_read_via_owner(2.8, None)
    assert row["regime"] == "above target" and row["anchoring"] is None
    assert _pill("Above target", "高于目标") in html
    assert "still 0.8 points above the Fed’s 2% target; the longer-run expectations read is being updated." in html
    assert "长期预期读数更新中。" in html
    assert "None" not in html
    assert "expectations:" not in html and "预期：" not in html
    assert "color:var(--warn,#f59e0b)" in html


def test_inflation_read_unknown_tokens_are_never_rendered_as_words():
    """A vocabulary move on the owner's side must read as 'being updated', never as a default word or the raw token."""
    row = {
        "core_pce_yoy": 2.8, "core_cpi_yoy": None, "core_pce_3m_ann": None, "vs_target_pp": 0.8,
        "regime": "hot", "direction": None, "breakeven_10y": None, "breakeven_5y5y": None,
        "anchoring": "unanchored", "nearest_cpi": None,
    }
    html = _render_inflation_read(row)
    assert _pill("Being updated", "更新中") in html
    assert "Core prices are being re-read against the Fed’s 2% target; the longer-run expectations read is being updated." in html
    assert "hot" not in html and "unanchored" not in html
    assert "Above target" not in html and "expectations:" not in html


def test_inflation_read_block_carries_no_retired_vocabulary():
    block = _inflation_read_block()
    for word in ("'drifting'", "unanchored", "a touch loose", "unmoored", "向上漂移", "略松动", "不稳", "_inf_above_"):
        assert word not in block, word
    for token in ("'above target'", "'at target'", "'below target'", "'anchored'", "'drifting up'", "'drifting down'"):
        assert token in block, token
