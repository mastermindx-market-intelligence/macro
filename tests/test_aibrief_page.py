"""Consolidated AI Daily Brief page (aibrief.html) render + nav-cleanup regression.

The old deterministic daily brief (scripts/daily_brief.py -> brief.html, plus the
china/hk variants) was retired and replaced by ONE static page that surfaces the
three EXISTING AI briefs written by engine/master_brain.py
(master_brief.json / china_brief.json / btc_brief.json) as toggle tabs.

ABX v2 (2026-07-19): the three lens brief BODIES are now SERVER-rendered by the
shared macro templates/_aibrief_body.html.j2 (build_aibrief.py loads the JSONs into
master_brief / china_brief / btc_brief). templates/aibrief.js was slimmed to the
overnight-cortex panel only. These tests render the REAL template (same Jinja env
as scripts/build_aibrief) and guard, at the source level, that no template ever
re-links the deleted brief pages.
"""
from __future__ import annotations

import json

import jinja2

from engine import i18n
from lib import config


def _env() -> jinja2.Environment:
    """Mirror scripts/build_aibrief.main()'s template environment."""
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(config.ROOT / "templates"))
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    return env


def _render(**briefs) -> str:
    """Render aibrief.html.j2 with the server-side panels absent (fail-open) and any
    passed lens briefs. Absent briefs render the honest 'not generated yet' note."""
    panels = {
        "ctx_strip": {"absent": True},
        "fwd_panel": {"absent": True, "events": [], "rebal_note_en": None, "rebal_note_zh": None},
        "record_panel": {"absent": True},
    }
    return _env().get_template("aibrief.html.j2").render(
        as_of="2026-06-14 12:00 UTC", **panels, **briefs
    )


def _committed_brief(name: str) -> dict:
    return json.loads((config.ROOT / "site" / name).read_text())


def test_three_lens_panels_present():
    """One .ai-brief panel per lens (server-rendered — no client fetch stubs)."""
    html = _render()
    assert html.count("ai-brief") >= 3
    # the client-fetch attributes are GONE (bodies are server-rendered now)
    assert "data-brief-src" not in html
    assert "data-brief-body" not in html


def test_committed_briefs_render_server_side():
    """The committed (v1-shaped) briefs render into the page via the shared macro —
    the v2 body must fail open on v1 payloads (no tldr → summary lead, no crash)."""
    html = _render(
        master_brief=_committed_brief("master_brief.json"),
        china_brief=_committed_brief("china_brief.json"),
        btc_brief=_committed_brief("btc_brief.json"),
    )
    # server-rendered macro body present (namespace .aib2-*), badge is house law
    assert '"aib2"' in html or 'class="aib2"' in html
    assert "not a signal source" in html
    # v1 payloads have no tldr → the summary lead-card fallback renders, no stance pill
    assert "aib2-lead" in html


def test_absent_brief_shows_honest_note():
    """No brief for a lens → an honest 'not generated yet' note, never a stray body."""
    html = _render()  # all briefs absent
    assert "has not generated yet" in html
    assert '"aib2"' not in html  # no empty body frame when all absent


def test_toggle_tabs_present():
    """Three market toggle buttons, one per lens."""
    html = _render()
    assert 'data-lens="macro"' in html
    assert 'data-lens="china"' in html
    assert 'data-lens="btc"' in html
    assert "Macro" in html and "China" in html and "Bitcoin" in html
    # exactly one panel is active by default (class-driven visibility)
    assert html.count("brief-tab active") == 1


def test_required_assets_loaded():
    """The page needs theme.css/.js + aibrief.js (cortex panel is still client-side)."""
    html = _render()
    assert 'href="theme.css"' in html
    assert 'src="theme.js"' in html
    assert 'src="aibrief.js"' in html


def test_per_lens_cadence_copy_no_blanket_daily_claim():
    """SPEC §7: the page no longer claims a blanket 'each day' refresh — BTC is every
    three days. The intro must state the split cadence honestly."""
    html = _render()
    assert "every three days" in html  # BTC honesty
    # the retired blanket claim must be gone
    assert "Regenerated automatically each day after the close" not in html


def test_static_nav_button_present():
    """The renamed 'AI Daily Brief' entry lives in the nav-ctrls cluster."""
    html = _render()
    assert "AI Daily Brief" in html
    assert 'class="ai-brief-link' in html
    assert 'class="nav-ctrls"' in html


def test_page_does_not_link_old_brief_pages():
    """The new page must not reference the retired brief HTML files. NOTE: the exact
    href= form matters — 'aibrief.html' contains the substring 'brief.html'."""
    html = _render()
    assert 'href="brief.html"' not in html
    assert 'href="china_brief.html"' not in html
    assert 'href="hk_brief.html"' not in html
    # The header's external entry is Terminal. The old "Mastermind" nav pill was
    # removed 2026-08-01 — theme.js injects mm_brain.js sitewide, which mounts its
    # own bottom-right launcher, so the pill was a duplicate entry point.
    #
    # Scoped to `.nav-ctrls` since 2026-08-07: the guard was written when NO Bot
    # link existed anywhere, so a whole-page substring read as "the header has no
    # Bot pill". The Bot now has a legitimate Research mega-menu card, and the
    # header contract is what this line always meant. theme.js:1492 strips any
    # `.nav-ctrls a[href*="bot.mastermind-x.com"]` at runtime; the SOURCE must not
    # lean on that, so the control cluster ships without one.
    ctrls = html[html.find('<div class="nav-ctrls">'):]
    ctrls = ctrls[:ctrls.find("</nav>")]
    assert ctrls, "the shared header lost its .nav-ctrls control cluster"
    assert 'href="https://app.mastermind-x.com"' in ctrls
    assert "bot.mastermind-x.com" not in ctrls


def test_no_template_links_deleted_brief_pages():
    """Source-level guard across EVERY template: the deterministic brief pages are
    gone, so nothing may link brief.html / china_brief.html / hk_brief.html (in any
    relative form). Locks in the nav cleanup against future drift."""
    bad = ('href="brief.html"', 'href="../brief.html"',
           'href="china_brief.html"', 'href="../china_brief.html"',
           'href="hk_brief.html"', 'href="../hk_brief.html"')
    offenders = []
    for path in sorted((config.ROOT / "templates").glob("*.html.j2")):
        src = path.read_text()
        for needle in bad:
            if needle in src:
                offenders.append(f"{path.name}: {needle}")
    assert not offenders, "templates still link retired brief pages: " + "; ".join(offenders)


# ── 2026-10-19→11-09 AI-brief freeze: freshest-copy pick, stale chip, receipt ──
from datetime import datetime, timezone  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from scripts import build_aibrief as bab  # noqa: E402

_NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)


def _brief(gen: str, asof: str, **kw) -> dict:
    return {"generated_at": gen, "state_asof": asof, "summary": "s", **kw}


def _w(path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc))


def test_fresher_data_regime_copy_wins_over_stale_site_copy(tmp_path):
    site, data = tmp_path / "site", tmp_path / "data"
    _w(site / "master_brief.json", _brief("2026-10-18T22:00:00+00:00", "2026-10-16"))
    _w(data / "regime" / "master_brief.json", _brief("2026-11-09T01:00:00+00:00", "2026-11-06"))
    brief, src = bab._load_briefs_with_source(site, data)["master_brief"]
    assert src == "data_regime" and brief["state_asof"] == "2026-11-06"
    assert bab._load_briefs(site, data)["master_brief"]["state_asof"] == "2026-11-06"


def test_tie_and_unparseable_prefer_site_or_the_other_copy(tmp_path):
    site, data = tmp_path / "site", tmp_path / "data"
    ts = "2026-11-09T01:00:00+00:00"
    _w(site / "china_brief.json", _brief(ts, "a"))
    _w(data / "regime" / "china_brief.json", _brief(ts, "b"))
    assert bab._load_briefs_with_source(site, data)["china_brief"][1] == "site"
    # unparseable site timestamp -> the parseable data/regime copy wins
    _w(site / "btc_brief.json", _brief("garbage", "a"))
    _w(data / "regime" / "btc_brief.json", _brief(ts, "b"))
    assert bab._load_briefs_with_source(site, data)["btc_brief"][1] == "data_regime"


def test_missing_paths_do_not_crash_the_loader(tmp_path):
    loaded = bab._load_briefs_with_source(tmp_path / "nope", tmp_path / "nada")
    assert all(v == (None, None) for v in loaded.values())
    only_data = tmp_path / "d"
    _w(only_data / "regime" / "btc_brief.json", _brief("2026-11-08T00:00:00+00:00", "x"))
    assert bab._load_briefs_with_source(tmp_path / "nope", only_data)["btc_brief"][1] == "data_regime"


def test_staleness_uses_refresh_days_with_grace_and_lens_fallback():
    def fr(lens, gen, **kw):
        return bab._lens_freshness(lens, _brief(gen, "x", **kw), "site", _NOW)["stale"]

    # macro/china fall back to 1d cadence: stale only past 1d + 1d6h grace = 2.25d
    assert fr("macro", "2026-11-07T07:00:00+00:00") is False   # 2.21d
    assert fr("macro", "2026-11-07T05:00:00+00:00") is True    # 2.29d
    # btc falls back to 3d: stale only past 3d + 1.25d = 4.25d (interval-gated lens
    # regenerates at ~3d + nightly jitter; 6h slack beyond the 1d grace absorbs it)
    assert fr("btc", "2026-11-05T07:00:00+00:00") is False     # 4.21d
    assert fr("btc", "2026-11-05T05:00:00+00:00") is True
    # explicit refresh_days wins over the lens fallback
    assert fr("macro", "2026-11-05T13:00:00+00:00", refresh_days=3) is False
    # no usable timestamp -> unknown, never stale
    assert bab._lens_freshness("macro", None, None, _NOW)["stale"] is None


def test_corrupt_refresh_days_falls_back_to_lens_default_without_crashing():
    # json.loads accepts NaN/Infinity; timedelta(days=nan) raises — one bad lens
    # value must degrade to the default cadence, never kill the page/receipt.
    for bad in (float("nan"), float("inf"), 0, -2, 1e9, True):
        info = bab._lens_freshness("btc", _brief("2026-11-08T00:00:00+00:00", "x",
                                                 **{"refresh_days": bad}), "site", _NOW)
        assert info["refresh_days"] == 3, bad
        assert info["stale"] is False  # 1.5d old, 3d cadence -> fresh


def test_oversized_json_int_refresh_days_degrades_not_aborts():
    # C2 2026-11-10: a legal JSON integer like 10**309 is a Python int too large
    # for float conversion — math.isfinite(int) raises OverflowError. One bad
    # lens value must degrade to the default, never abort the whole dict before
    # the receipt exists (main's call order: freshness precedes every write).
    for bad in (10**309, -(10**309)):
        info = bab._lens_freshness(
            "btc", _brief("2026-11-08T00:00:00+00:00", "x", **{"refresh_days": bad}),
            "site", _NOW)
        assert info["refresh_days"] == 3, bad
        assert info["stale"] is False
    # and through the dict builder: a bad BTC lens cannot abort Macro/China facts
    loaded = {"master_brief": (_brief("2026-11-09T01:00:00+00:00", "x"), "site"),
              "china_brief": (None, None),
              "btc_brief": (_brief("2026-11-09T01:00:00+00:00", "x",
                                   **{"refresh_days": 10**309}), "site")}
    receipt = bab._build_freshness(loaded, _NOW)
    assert receipt["lenses"]["btc"]["refresh_days"] == 3
    assert receipt["lenses"]["macro"]["stale"] is False


def test_visible_cadence_consumes_the_normalized_value():
    # C2 2026-11-10: the receipt normalizes corrupt cadence, so the VISIBLE chip
    # must consume the annotation's normalized value — NaN/inf/-2/1e9/True/
    # "not-a-number" may never reach the caption ("Updated every nan days"),
    # and a bool True must not read as "Updated daily" on a 3-day lens.
    for bad in (float("nan"), float("inf"), -2, 1e9, True, "not-a-number"):
        loaded = {"btc_brief": (_brief("2026-11-09T01:00:00+00:00", "2026-11-06",
                                       **{"refresh_days": bad}), "site")}
        receipt = bab._build_freshness(loaded, _NOW)
        assert receipt["lenses"]["btc"]["refresh_days"] == 3, bad
        html = _render(**bab._annotate_freshness(loaded, receipt))
        assert "every nan" not in html and "every inf" not in html, bad
        assert "not-a-number" not in html, bad
        assert "Updated every 3 days" in html, bad  # normalized caption
        assert "Updated daily" not in html, bad     # True must not read as 1
    # a clean annotated 1-day cadence still says daily
    loaded = {"btc_brief": (_brief("2026-11-09T01:00:00+00:00", "x", refresh_days=1), "site")}
    html = _render(**bab._annotate_freshness(loaded, bab._build_freshness(loaded, _NOW)))
    assert "Updated daily" in html


def test_stale_brief_without_refresh_days_still_gets_the_stale_chip():
    # fallback cadence (macro -> 1d) applies; the chip must not depend on the
    # brief carrying its own refresh_days
    html = _stale_html("2026-10-18T22:00:00+00:00")
    assert "Stale — last generated 2026-10-18" in html
    assert "Updated daily" not in html


def _stale_html(gen: str, **kw) -> str:
    loaded = {"master_brief": (_brief(gen, "2026-10-16", **kw), "site"),
              "china_brief": (None, None), "btc_brief": (None, None)}
    fresh = bab._build_freshness(loaded, _NOW)
    return _render(**bab._annotate_freshness(loaded, fresh))


def test_stale_chip_renders_with_last_generated_date_bilingual():
    html = _stale_html("2026-10-18T22:00:00+00:00", refresh_days=1)
    assert "Stale — last generated 2026-10-18" in html
    assert "已过期 — 上次生成 2026-10-18" in html
    assert "Updated daily" not in html  # the cadence claim is replaced, not appended


def test_fresh_brief_keeps_cadence_chip_and_no_stale_chip():
    html = _stale_html("2026-11-09T01:00:00+00:00", refresh_days=1)
    assert "Updated daily" in html
    assert "Stale — last generated" not in html


def test_unknown_age_brief_shows_no_chip_at_all():
    # unparseable generated_at → age unknown → the page must not claim "Updated daily"
    html = _stale_html("garbage", refresh_days=1)
    assert "Updated daily" not in html
    assert "Updated every" not in html
    assert "Stale — last generated" not in html


def test_raw_brief_without_freshness_annotation_keeps_v1_cadence_chip():
    # other pages pass briefs with no `_freshness` — v1 fail-open chip stands
    html = _render(master_brief=_brief("2026-11-09T01:00:00+00:00", "2026-11-06", refresh_days=1))
    assert "Updated daily" in html


def _fake_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "templates").symlink_to(config.ROOT / "templates")
    return root


def test_main_writes_freshness_receipt_and_stale_page(tmp_path, monkeypatch):
    root = _fake_root(tmp_path)
    site = tmp_path / "out" / "site"
    _w(site / "master_brief.json", _brief("2026-10-18T22:00:00+00:00", "2026-10-16", refresh_days=1))
    _w(root / "data" / "regime" / "master_brief.json",
       _brief("2026-11-09T01:00:00+00:00", "2026-11-06", refresh_days=1))
    _w(site / "btc_brief.json", _brief("2026-10-18T22:00:00+00:00", "2026-10-16"))
    # china present but with an UNPARSEABLE generated_at -> unknown age
    _w(site / "china_brief.json", _brief("garbage", "2026-10-16", refresh_days=1))
    monkeypatch.setattr(bab, "config", SimpleNamespace(
        load=lambda: {"storage": {"site_dir": str(site)}}, ROOT=root))
    assert bab.main() == 0
    receipt = json.loads((site / "aibrief_freshness.json").read_text())
    assert datetime.fromisoformat(receipt["built_at"]).tzinfo is not None
    assert set(receipt["lenses"]) == {"macro", "china", "btc"}
    macro = receipt["lenses"]["macro"]
    assert macro["generated_at"] == "2026-11-09T01:00:00+00:00"
    assert macro["state_asof"] == "2026-11-06"
    assert macro["refresh_days"] == 1 and macro["source"] == "data_regime"
    # btc (site copy, 2026-10-18) is long past 3d+grace
    assert receipt["lenses"]["btc"]["source"] == "site" and receipt["lenses"]["btc"]["stale"] is True
    # china PRESENT but unknown age -> receipt records None, and the page shows the
    # china lens NO chip at all (no unverifiable "Updated daily"; exactly one such
    # chip on the page, belonging to the fresh macro lens)
    assert receipt["lenses"]["china"]["generated_at"] is None
    assert receipt["lenses"]["china"]["stale"] is None
    html = (site / "aibrief.html").read_text()
    assert "Stale — last generated 2026-10-18" in html  # btc lens
    assert html.count("Updated daily") == 1             # macro only — china suppressed


def test_main_fail_open_still_writes_receipt_when_render_breaks(tmp_path, monkeypatch, capsys):
    root = _fake_root(tmp_path)
    site = tmp_path / "out" / "site"
    _w(site / "master_brief.json", _brief("2026-11-09T01:00:00+00:00", "2026-11-06"))
    monkeypatch.setattr(bab, "config", SimpleNamespace(
        load=lambda: {"storage": {"site_dir": str(site)}}, ROOT=root))

    def _boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(bab, "write_page", _boom)
    assert bab.main() == 0  # fail-open law: never breaks the site build
    assert "::warning title=aibrief-build::" in capsys.readouterr().out
    assert (site / "aibrief_freshness.json").exists()
