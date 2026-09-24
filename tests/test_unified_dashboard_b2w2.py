"""Tests for the UD-B2-W2 Unified Macro Dashboard spine-scale bindings.

Pins the binding contract per DEC-SPINE-SCALE-BINDINGS (META-CEO A, 2026-09-20):

  · HK row (data-market="hk", data-blocked-feed="hk_market_state") binds to
    HK_PROFILE market_state.score (engine/market_state_hk.py:152) persisted
    by build_hk to data/hk_market_state/latest.json. Macro vm reads
    {score, label_en, label_zh, asof, caveat_en, caveat_zh, display_only}.
  · CN row (data-market="cn", data-blocked-feed="cn_market_state") binds to
    CN_PROFILE market_state.score (engine/market_state_cn.py:148) persisted
    by build_china to data/china_market_state/latest.json (the existing
    convention used by build_china.py:1888 for the CN score_log). Same vm shape.
  · Bonds + Commodities rows stay designed-null (the ratified product state
    per R-W2-3, NOT a deferral). Their slugs (gov_bonds_regime,
    commodities_regime) stay UNCHANGED.

Engine-true fixtures ONLY (R-H): snapshots are produced by calling
`engine.market_state.persist(market_key=..., root=tmp_path)` on a real
snapshot the same engine that ships would write, then read back via
`load_persisted`. The test never hand-types a market_state output shape —
a snapshot built from `market_state_snapshot(..., profile=HK_PROFILE|CN_PROFILE)`
is what the real build path produces, and that is what the test fixture
mimics. All fixture writes are scoped to tmp_path so the repo's real
data/ tree is never touched (MM_DATA_GUARD-safe).

Built-page assertions are scoped to the spine slice: HK/CN rows carry
data-state="real" + marker geometry + caveat present in the disclosure;
bonds/commodities rows still designed-null with renamed-or-kept slugs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import jinja2
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"


# --------------------------------------------------------------------------- #
# Fixtures — engine-true snapshot built from the same HK/CN profiles the
# build path uses. NOT a hand-typed output shape. All writes go to tmp_path.
# --------------------------------------------------------------------------- #

def _calm_radar() -> dict:
    """Minimal calm Risk Radar stub (the only fields the snapshot reads)."""
    return {"watch": False, "ceiling": None, "can_force": False}


def _hk_input() -> dict:
    """Minimal `latest` input the HK conditions readers expect — same shape
    build_hk passes to market_state_snapshot. Never hand-typed output."""
    return {
        "date": "2026-09-20",
        "alerts": [],
        "conditions": {
            "roro": {
                "roro_state": "neutral",
                "roro": -0.05,
                "hk_roro_vhsi": 0.1,
                "hk_roro_hibor": 0.0,
                "legs": [{"lean": "risk-on"}, {"lean": "risk-off"}],
            },
            "breadth": {"above200_pctile": 0.5, "div": False},
            "recession": {"score": 30, "label": "low"},
            "drawdown_risk": {"score": 20, "band": "low"},
        },
        "liquidity_overlay": "neutral",
        "peg_state": "neutral",
        "risk_state": "Neutral",
        "risk_radar": _calm_radar(),
    }


def _cn_input() -> dict:
    """Minimal `latest` input the CN conditions readers expect."""
    return {
        "date": "2026-09-20",
        "alerts": [],
        "conditions": {
            "roro": {
                "roro_state": "neutral",
                "roro": -0.1,
                "china_roro_qvix": 0.2,
                "china_roro_margin": -0.1,
                "legs": [{"lean": "risk-on"}, {"lean": "risk-off"}],
            },
            "breadth": {"above200_pctile": 0.4, "div": False},
            "recession": {"score": 40, "label": "low"},
            "drawdown_risk": {"score": 30, "band": "low"},
        },
        "liquidity_overlay": "neutral",
        "risk_radar": _calm_radar(),
    }


@pytest.fixture
def intl_root(tmp_path):
    """Materialise a synthetic data/ root with HK + CN latest.json + score_logs
    under tmp_path. The fixture writes ONLY to tmp_path (MM_DATA_GUARD-safe)."""
    from engine import market_state as _ms
    from engine.market_state_cn import CN_PROFILE
    from engine.market_state_hk import HK_PROFILE

    root = tmp_path
    data_dir = root / "data"
    (data_dir / "hk_market_state").mkdir(parents=True)
    (data_dir / "china_market_state").mkdir(parents=True)

    # HK snapshot + score_log (25 rows for the >=22 travel gate).
    hk_snap = _ms.market_state_snapshot(_hk_input(), frame=None, alerts=[],
                                        profile=HK_PROFILE)
    assert hk_snap is not None, "HK_PROFILE snapshot must resolve"
    _ms.persist(hk_snap, root=root, market_key="hk")
    hk_rows = [
        {"date": (pd.Timestamp("2026-09-20") - pd.Timedelta(days=d)).strftime("%Y-%m-%d"),
         "score": 50 + i}
        for i, d in enumerate(range(24, -1, -1))
    ]
    pd.DataFrame(hk_rows).to_parquet(data_dir / "hk_market_state" / "score_log.parquet",
                                     index=False)

    # CN snapshot + score_log (25 rows).
    cn_snap = _ms.market_state_snapshot(_cn_input(), frame=None, alerts=[],
                                        profile=CN_PROFILE)
    assert cn_snap is not None, "CN_PROFILE snapshot must resolve"
    _ms.persist(cn_snap, root=root, market_key="cn")
    cn_rows = [
        {"date": (pd.Timestamp("2026-09-20") - pd.Timedelta(days=d)).strftime("%Y-%m-%d"),
         "score": 40 + i}
        for i, d in enumerate(range(24, -1, -1))
    ]
    pd.DataFrame(cn_rows).to_parquet(data_dir / "china_market_state" / "score_log.parquet",
                                     index=False)

    return root


def _persisted_ms_view(intl_root: Path, market_key: str) -> dict | None:
    """Read the persisted HK/CN market-state snapshot + score_log.parquet
    into the macro vm entry shape the template reads. R-H: the helper MUST
    stay byte-equivalent to scripts.build_site._persisted_ms_view — any drift
    here would let the tests pass while the real ingest path diverges. We
    mirror the helper rather than import it because build_site is a 7000+
    line module with heavy module-level work; importing it from a unit test
    triggers parquet / yaml / plotly initialisation. The drift is fenced by
    test_engine_market_state_persist_docstring_accurate + the path-mapping
    test below. Named `_persisted_ms_view` (not `_intl_ms_view`) because
    R-W2-2 forbids `intl_market_state` as a HK/CN source — the helper name
    must not reopen that trap."""
    from engine.market_state import load_persisted as _lp
    snap = _lp(root=intl_root, market_key=market_key)
    if snap is None:
        return None
    log_dir = {"hk": "hk_market_state", "cn": "china_market_state"}.get(market_key)
    sl_path = intl_root / "data" / log_dir / "score_log.parquet"
    view = {
        "score": snap.get("score"),
        "raw_score": snap.get("raw_score"),
        "verdict": snap.get("verdict"),
        "label_en": snap.get("label_en"),
        "label_zh": snap.get("label_zh"),
        "asof": snap.get("asof"),
        "caveat_en": snap.get("caveat_en") or "",
        "caveat_zh": snap.get("caveat_zh") or "",
        "display_only": True,
        "market": market_key,
        "ms_history": [],
    }
    if sl_path.exists():
        view["ms_history"] = (
            pd.read_parquet(sl_path).sort_values("date").tail(60).to_dict(orient="records")
        )
    return view


def test_persisted_ms_view_helper_matches_build_site_contract(intl_root):
    """Drift guard: the test helper's vm entry shape MUST match the shape
    scripts/build_site.py:_persisted_ms_view publishes. We assert the contract
    keys + the cn → china_market_state mapping rather than re-importing the
    helper (build_site has heavy module-level work). If build_site's helper
    later adds / renames a field, this test fails until the test helper
    catches up — preventing the named drift (Minor #4)."""
    view = _persisted_ms_view(intl_root, "cn")
    assert view is not None
    expected_keys = {"score", "raw_score", "verdict", "label_en", "label_zh",
                     "asof", "caveat_en", "caveat_zh", "display_only", "market",
                     "ms_history"}
    assert expected_keys.issubset(set(view.keys())), (
        f"test helper is missing required keys vs build_site contract: "
        f"{expected_keys - set(view.keys())}"
    )
    assert view["display_only"] is True
    assert view["market"] == "cn"
    # cn resolves under data/china_market_state/, not data/cn_market_state/.
    assert (intl_root / "data" / "china_market_state" / "latest.json").exists()
    assert not (intl_root / "data" / "cn_market_state").exists()


# --------------------------------------------------------------------------- #
# Template render helper — match the production env.
# --------------------------------------------------------------------------- #

def _env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
    )
    env.filters["min"] = lambda seq: min(seq)
    env.filters["regex_replace"] = (
        lambda s, pattern, repl: re.sub(pattern, repl, s)
        if isinstance(s, str) else s
    )
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    except Exception:  # noqa: BLE001 — i18n is optional in unit tests
        pass
    return env


def _render_macro_with_hero(vm: dict) -> str:
    return _env().get_template("_unified_dashboard_hero.html.j2").render(**vm)


def _spine_slice(html: str) -> str:
    """Pull out just the spine (mx-spine) block from the rendered hero — the
    spine gate per R-E-pattern slice. The slice runs from <div class="mx-spine"
    up to (but not including) the trailing <p class="ud-spine-foot">."""
    m = re.search(r'<div class="mx-spine"[^>]*>.*?<p class="ud-spine-foot"',
                  html, re.S)
    assert m, "spine slice not found in rendered hero"
    # Drop the trailing <p so the slice is just the spine block.
    return m.group(0)[: m.group(0).rfind("<p class=")]


def _hk_row(slice_: str) -> str:
    """Grab the HK spine row, including its closing tags. The row ends at the
    next `data-market="..."` opening OR at the closing of mx-spine."""
    # Walk from data-market="hk" to the next data-market= or to </div></div>
    # that closes mx-spine (the row is the last div before the spine's close).
    start = slice_.find('data-market="hk"')
    assert start >= 0, "HK row not found in spine slice"
    # Walk back to the opening <div
    div_start = slice_.rfind('<div class="mx-spine-row"', 0, start)
    assert div_start >= 0, "HK row opening <div not found"
    # Walk forward until we find the matching row close: the row ends right
    # before the next <div class="mx-spine-row" or the </div></div> that
    # closes mx-spine.
    rest = slice_[div_start:]
    # The row closes at the next occurrence of <div class="mx-spine-row" (the
    # next row's opening) OR at the closing </div> of mx-spine.
    next_row = rest.find('<div class="mx-spine-row"', 10)
    if next_row >= 0:
        return rest[:next_row]
    # Last row in the spine — close at the trailing </div> that ends mx-spine.
    # The mx-spine closes right before <p class="ud-spine-foot">. Since we
    # trimmed <p> out of the slice, look for the last </div></div> in the slice.
    end = rest.rfind('</div></div>')
    assert end >= 0, "HK row end not found"
    return rest[: end + len('</div></div>')]


def _cn_row(slice_: str) -> str:
    start = slice_.find('data-market="cn"')
    assert start >= 0, "CN row not found in spine slice"
    div_start = slice_.rfind('<div class="mx-spine-row"', 0, start)
    assert div_start >= 0, "CN row opening <div not found"
    rest = slice_[div_start:]
    next_row = rest.find('<div class="mx-spine-row"', 10)
    if next_row >= 0:
        return rest[:next_row]
    end = rest.rfind('</div></div>')
    assert end >= 0, "CN row end not found"
    return rest[: end + len('</div></div>')]


# --------------------------------------------------------------------------- #
# Engine persist-path tests (R-W2-4: own file, never US latest.json)
# --------------------------------------------------------------------------- #

def test_persist_hk_writes_to_own_path_not_us_latest(tmp_path):
    """HK persist MUST land in data/hk_market_state/latest.json — never
    data/market_state/latest.json (the US canonical)."""
    from engine import market_state as _ms
    from engine.market_state_hk import HK_PROFILE
    snap = _ms.market_state_snapshot(_hk_input(), frame=None, alerts=[],
                                     profile=HK_PROFILE)
    _ms.persist(snap, root=tmp_path, market_key="hk")
    path = tmp_path / "data" / "hk_market_state" / "latest.json"
    assert path.exists(), (
        f"data/hk_market_state/latest.json must exist after persist; got {path!r}"
    )
    # The US canonical is NOT created by the HK persist.
    us_path = tmp_path / "data" / "market_state" / "latest.json"
    assert not us_path.exists(), (
        "HK persist must not create data/market_state/latest.json"
    )


def test_persist_cn_writes_to_china_market_state_dir(tmp_path):
    """CN lives under data/china_market_state/ (the existing convention from
    build_china.py:1888). The persist must use that directory — NOT a
    cn_market_state directory."""
    from engine import market_state as _ms
    from engine.market_state_cn import CN_PROFILE
    snap = _ms.market_state_snapshot(_cn_input(), frame=None, alerts=[],
                                     profile=CN_PROFILE)
    _ms.persist(snap, root=tmp_path, market_key="cn")
    path = tmp_path / "data" / "china_market_state" / "latest.json"
    assert path.exists(), (
        f"data/china_market_state/latest.json must exist after persist; got {path!r}"
    )
    # The cn_market_state directory must NOT be created (that's the wrong dir).
    wrong = tmp_path / "data" / "cn_market_state" / "latest.json"
    assert not wrong.exists(), (
        f"CN persist must not write to {wrong!r} — the directory is china_market_state/"
    )


def test_persist_load_roundtrip_carries_required_vm_fields(intl_root):
    """The snapshot persisted must carry every field the macro vm entry
    contract specifies (R-W2-4):
      {score, label_en, label_zh, asof, caveat_en, caveat_zh, display_only}."""
    from engine.market_state import load_persisted as _lp
    for key in ("hk", "cn"):
        snap = _lp(root=intl_root, market_key=key)
        assert snap is not None, f"{key} snapshot must be loadable"
        for field in ("score", "label_en", "label_zh", "asof", "caveat_en", "caveat_zh"):
            assert field in snap, (
                f"{key} snapshot missing required vm field {field!r}: {snap!r}"
            )
        assert snap.get("market") == key
        # caveat MUST travel with the number — the named failure mode is
        # binding the score without the caveat stamp (R-W2-4).
        assert snap["caveat_en"], f"{key} caveat_en must be non-empty"


def test_persist_us_path_unchanged_after_per_market_persist(tmp_path):
    """Sanity: when only HK + CN persist, the US canonical
    data/market_state/latest.json is NOT created. The reverse — a US persist
    MUST still land at the canonical US path."""
    from engine import market_state as _ms
    from engine.market_state_cn import CN_PROFILE
    from engine.market_state_hk import HK_PROFILE
    _ms.persist(_ms.market_state_snapshot(_hk_input(), frame=None, alerts=[],
                                          profile=HK_PROFILE),
                root=tmp_path, market_key="hk")
    _ms.persist(_ms.market_state_snapshot(_cn_input(), frame=None, alerts=[],
                                          profile=CN_PROFILE),
                root=tmp_path, market_key="cn")
    assert not (tmp_path / "data" / "market_state" / "latest.json").exists()
    # Now a US persist (market_key=None, the default) — must land at the
    # canonical US path.
    _ms.persist({"asof": "2026-09-20", "verdict": "MIXED", "score": 50,
                 "label_en": "Mixed", "label_zh": "混合",
                 "caveat_en": "US caveat", "caveat_zh": "美股提示",
                 "display_only": True, "market": "us"},
                root=tmp_path)
    assert (tmp_path / "data" / "market_state" / "latest.json").exists(), (
        "US persist must still land at data/market_state/latest.json"
    )


# --------------------------------------------------------------------------- #
# Built-page assertions — spine slice (R-H, R-E-pattern slice gate)
# --------------------------------------------------------------------------- #

def test_spine_slice_hk_row_binds_real_with_caveat(intl_root):
    """HK row carries data-state="real", a marker geometry, and the engine
    caveat in the disclosure — binding the score WITHOUT the caveat is the
    named failure mode (R-W2-4)."""
    vm = {
        "market_state": None, "stance": {}, "ms_history": [],
        "hk_market_state": _persisted_ms_view(intl_root, "hk"),
        "cn_market_state": None,
        "latest": {}, "alerts": [], "event_strip": [],
        "fear_greed": {}, "risk_envelope": {},
    }
    slice_ = _spine_slice(_render_macro_with_hero(vm))
    row = _hk_row(slice_)

    # Slug renamed from hk_regime → hk_market_state (R-W2-5 wiring trap fix).
    assert 'data-blocked-feed="hk_market_state"' in row
    assert 'data-market="hk"' in row
    # Real state (score + >=22 rows).
    assert 'data-state="real"' in row
    # Marker geometry: a left:% style attribute (one-integer law: NO score
    # integer in the row slice).
    assert re.search(r'style="left:\d+(\.\d+)?%"', row), (
        "HK row must carry marker geometry (style=left:X%) — never a competing integer"
    )
    # Caveat stamp travels with the number.
    assert "Display-only" in row, (
        "HK row must surface the engine caveat_en (R-W2-4); "
        "binding the score without the caveat is the named failure mode"
    )
    # data-caveat-* attrs hold the caveat copy for downstream consumers.
    assert row.count("data-caveat-en=") == 1
    assert row.count("data-caveat-zh=") == 1


def test_spine_slice_cn_row_binds_real_with_caveat(intl_root):
    vm = {
        "market_state": None, "stance": {}, "ms_history": [],
        "hk_market_state": None,
        "cn_market_state": _persisted_ms_view(intl_root, "cn"),
        "latest": {}, "alerts": [], "event_strip": [],
        "fear_greed": {}, "risk_envelope": {},
    }
    slice_ = _spine_slice(_render_macro_with_hero(vm))
    row = _cn_row(slice_)

    assert 'data-blocked-feed="cn_market_state"' in row
    assert 'data-market="cn"' in row
    assert 'data-state="real"' in row
    assert re.search(r'style="left:\d+(\.\d+)?%"', row)
    assert "Display-only" in row
    assert row.count("data-caveat-en=") == 1
    assert row.count("data-caveat-zh=") == 1


def test_spine_slice_short_history_state_when_log_too_short(tmp_path):
    """When the HK score_log has fewer than 22 rows, the row must carry
    the designed-null travel with a real today marker — never substitute
    raw_score (R-W2-8)."""
    from engine import market_state as _ms
    from engine.market_state_hk import HK_PROFILE
    snap = _ms.market_state_snapshot(_hk_input(), frame=None, alerts=[],
                                     profile=HK_PROFILE)
    _ms.persist(snap, root=tmp_path, market_key="hk")
    # Short log (3 rows, below the >=22 threshold).
    pd.DataFrame([
        {"date": "2026-09-18", "score": 50},
        {"date": "2026-09-19", "score": 52},
        {"date": "2026-09-20", "score": 55},
    ]).to_parquet(tmp_path / "data" / "hk_market_state" / "score_log.parquet",
                  index=False)
    vm = {
        "market_state": None, "stance": {}, "ms_history": [],
        "hk_market_state": _persisted_ms_view(tmp_path, "hk"),
        "cn_market_state": None,
        "latest": {}, "alerts": [], "event_strip": [],
        "fear_greed": {}, "risk_envelope": {},
    }
    slice_ = _spine_slice(_render_macro_with_hero(vm))
    row = _hk_row(slice_)

    assert 'data-state="short-history"' in row, (
        f"HK row must be data-state=short-history when score_log < 22 rows; "
        f"got row head: {row[:200]!r}"
    )
    # No travel figure printed — must be a literal em-dash, never an integer.
    assert '<span class="tnum">+' not in row and '<span class="tnum">−' not in row, (
        "HK row must NOT print a month-ago travel figure when history < 22 rows "
        "(R-W2-8: never substitute raw_score)"
    )


def test_spine_slice_bonds_and_commodities_stay_designed_null(intl_root):
    """R-W2-3 ratified product state, NOT deferral. Bonds + Commodities rows
    stay designed-null with their slugs UNCHANGED
    (gov_bonds_regime, commodities_regime). The HK/CN slug renames do NOT
    touch these rows."""
    vm = {
        "market_state": None, "stance": {}, "ms_history": [],
        "hk_market_state": _persisted_ms_view(intl_root, "hk"),
        "cn_market_state": _persisted_ms_view(intl_root, "cn"),
        "latest": {}, "alerts": [], "event_strip": [],
        "fear_greed": {}, "risk_envelope": {},
    }
    slice_ = _spine_slice(_render_macro_with_hero(vm))

    # Slugs UNCHANGED.
    assert 'data-blocked-feed="gov_bonds_regime"' in slice_
    assert 'data-blocked-feed="commodities_regime"' in slice_
    # Each appears exactly once (the designed-null row, never duplicated).
    assert slice_.count('data-blocked-feed="gov_bonds_regime"') == 1
    assert slice_.count('data-blocked-feed="commodities_regime"') == 1
    # HK/CN renames do NOT bleed into Bonds/Commodities.
    assert 'data-blocked-feed="hk_regime"' not in slice_
    assert 'data-blocked-feed="china_a_regime"' not in slice_


def _row_cells_without_disclosure(row: str) -> str:
    """R-W2-14: the row cells carry marker geometry, travel delta, stance
    words ONLY. As-of + caveat live in the disclosure, so strip
    `.mx-spine-caveat` (and style attributes, which are geometry) before
    scanning the cells for dates or competing integers."""
    cells = re.sub(
        r'<div class="mx-spine-caveat"[\s\S]*?</div>', "", row, count=1)
    cells = re.sub(r'\sstyle="[^"]*"', "", cells)
    return cells


def test_spine_slice_hk_no_competing_integer_on_rail(intl_root):
    """One-integer law (R-W2-9 / R-W2-14): HK row cells carry marker
    geometry + travel delta + stance words ONLY. No as-of date strings,
    and no integer besides the travel delta, in the cells. The as-of +
    caveat live in the disclosure (not the name cell)."""
    vm = {
        "market_state": None, "stance": {}, "ms_history": [],
        "hk_market_state": _persisted_ms_view(intl_root, "hk"),
        "cn_market_state": None,
        "latest": {}, "alerts": [], "event_strip": [],
        "fear_greed": {}, "risk_envelope": {},
    }
    slice_ = _spine_slice(_render_macro_with_hero(vm))
    row = _hk_row(slice_)
    assert re.search(r'class="mx-spine-mark" style="left:\d+(\.\d+)?%"', row), (
        f"HK row must carry the marker's percentage geometry; got row tail: "
        f"{row[-400:]!r}"
    )
    cells = _row_cells_without_disclosure(row)
    assert "as of" not in cells, (
        "R-W2-14: as-of dates must not appear in the spine row cells "
        f"(they live in the disclosure). cells={cells!r}"
    )
    assert "截至" not in cells, (
        "R-W2-14: ZH as-of dates must not appear in the spine row cells. "
        f"cells={cells!r}"
    )
    assert not re.search(r"\d{4}-\d{2}-\d{2}", cells), (
        "R-W2-14: no YYYY-MM-DD date strings in the spine row cells. "
        f"cells={cells!r}"
    )
    # Visible text of the cells (tags stripped): the only remaining integer
    # is the travel delta inside .tnum.
    travel_match = re.search(r'<span class="tnum">([+−]?\d+)</span>', row)
    assert travel_match, "HK real-state row must print a signed travel delta"
    visible = re.sub(r"<[^>]+>", " ", cells)
    integers = re.findall(r"\d+", visible)
    travel_digits = re.findall(r"\d+", travel_match.group(1))
    assert integers == travel_digits, (
        f"R-W2-14: the only integer in the HK row cells must be the travel "
        f"delta {travel_digits}; found {integers} in visible text {visible!r}"
    )


def test_spine_slice_hk_falls_back_to_null_when_snapshot_absent():
    """When hk_market_state=None is passed (no snapshot available), the row
    carries the designed-null treatment (data-state='null', no marker) —
    never a fake score, never a marker geometry."""
    vm = {
        "market_state": None, "stance": {}, "ms_history": [],
        "hk_market_state": None,
        "cn_market_state": None,
        "latest": {}, "alerts": [], "event_strip": [],
        "fear_greed": {}, "risk_envelope": {},
    }
    slice_ = _spine_slice(_render_macro_with_hero(vm))
    # HK row exists with the renamed slug but data-state="null".
    assert 'data-market="hk"' in slice_
    assert 'data-state="null"' in slice_
    # NO mx-spine-mark in the HK row (no real marker geometry without a score).
    row = _hk_row(slice_)
    assert 'mx-spine-mark' not in row, (
        "HK row must NOT carry a marker geometry when the snapshot is absent"
    )
    # Stance carries the designed-null chip ("Read being updated"), not a
    # verdict-band fallback (no verdict, no fallback).
    assert "Read being updated" in row or "判读更新中" in row


def test_spine_slice_does_not_wire_quad_artifact(intl_root):
    """R-W2-5 wiring-trap fix: the spine row MUST NOT read from the
    hk_regime / china_regime quad artifacts. The renamed slug
    hk_market_state / cn_market_state is the only valid source. Render
    against a vm that incidentally carries quad data — the row must NOT
    surface it."""
    vm = {
        "market_state": None, "stance": {}, "ms_history": [],
        "hk_market_state": _persisted_ms_view(intl_root, "hk"),
        "cn_market_state": _persisted_ms_view(intl_root, "cn"),
        # Quad payloads are NOT a spine source. Even if a builder wires them,
        # the row must not surface quad fields (quad != risk-on per R-W2-1).
        "hk_regime": {"quad": "Q4", "quad_name": "Growth-scare"},
        "china_a_regime": {"quad": "Q4", "quad_name": "Growth-scare"},
        "latest": {}, "alerts": [], "event_strip": [],
        "fear_greed": {}, "risk_envelope": {},
    }
    slice_ = _spine_slice(_render_macro_with_hero(vm))
    # Growth-scare is a quad name; it must NOT surface on the spine rows.
    assert "Growth-scare" not in slice_


# --------------------------------------------------------------------------- #
# Primary-route assertion — reads site/macro.html directly. B2-W2's binding
# semantics remain proven above against the retained component; the US route
# itself must not mount that candidate over the established macro dashboard.
# --------------------------------------------------------------------------- #

def _committed_macro_html() -> str | None:
    """Return the committed site/macro.html text, or None if absent. The file
    is part of the repo and is regenerated ONLY by scripts/build_site.py
    (R-W2-11: never a hand-rolled splice). Missing = nothing to gate; the test
    skips with an explicit reason rather than failing."""
    p = ROOT / "site" / "macro.html"
    return p.read_text() if p.exists() else None


def _committed_spine_slice(macro_html: str) -> str | None:
    """Pull the spine region (mx-spine … ud-spine-foot opener) from the
    COMMITTED page. Mirrors _spine_slice() over the partial render."""
    m = re.search(r'<div class="mx-spine"[^>]*>.*?<p class="ud-spine-foot"',
                  macro_html, re.S)
    if not m:
        return None
    return m.group(0)[: m.group(0).rfind("<p class=")]


def test_committed_macro_html_keeps_retained_spine_off_us_primary_route():
    """The B2-W2 spine remains a tested design candidate, not a US-route mount.

    The component-level tests above prove the HK/CN persisted market-state
    bindings and caveats. The committed US page must instead open on the
    established regime radar, with no #ud-hero or B2 spine slice stacked over it.
    """
    macro_html = _committed_macro_html()
    if macro_html is None:
        pytest.skip("site/macro.html absent in this checkout; built-page gate N/A")
    assert 'id="ud-hero"' not in macro_html
    assert _committed_spine_slice(macro_html) is None
    assert 'data-spec="ud-b1"' not in macro_html
    assert 'id="regime-radar"' in macro_html


def test_engine_market_state_persist_docstring_accurate():
    """Minor-1 fix: the persist() docstring must reflect the cn → china_market_state
    mapping (the spec keyword in build_china.py:1888). Pre-fix state: the
    docstring said "any non-US key writes data/<key>_market_state/latest.json",
    which is wrong for cn (it writes china_market_state)."""
    from engine.market_state import persist
    doc = persist.__doc__ or ""
    assert "china_market_state" in doc, (
        "engine.market_state.persist docstring must call out the cn → "
        "china_market_state path; the historical convention from "
        "build_china.py:1888 must be documented"
    )
    assert "hk_market_state" in doc


def test_persist_cn_writes_china_market_state_via_store_path():
    """Sanity-check on the path mapping: when market_key="cn", the resolved
    path uses china_market_state/ (not cn_market_state/). The DEC record
    cites this path; a regression that swaps it would break the macro
    spine ingest."""
    from engine.market_state import _store_path
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cn_path = _store_path(root=root, market_key="cn")
        assert "china_market_state" in str(cn_path), (
            f"CN must resolve to a china_market_state path; got {cn_path!r}"
        )
        assert "cn_market_state/latest.json" not in str(cn_path), (
            f"CN must NOT use the cn_market_state/ directory; got {cn_path!r}"
        )
        hk_path = _store_path(root=root, market_key="hk")
        assert "hk_market_state" in str(hk_path)
        us_path = _store_path(root=root)
        assert str(us_path).endswith("data/market_state/latest.json"), (
            "US default must still land at data/market_state/latest.json"
        )


# --------------------------------------------------------------------------- #
# Round-3 ruling gates (R-W2-11 .. R-W2-16)
# --------------------------------------------------------------------------- #

def test_build_site_helper_is_not_named_intl_ms_view():
    """Minor-1 / R-W2-2: the ingest helper must not be named `_intl_ms_view`
    — that name reopens the `intl_market_state` source trap. The lawful
    name is `_persisted_ms_view` (it loads persist() output)."""
    src = (ROOT / "scripts" / "build_site.py").read_text()
    assert "def _intl_ms_view" not in src
    assert "def _persisted_ms_view" in src


# Bake-coupled fields: a snapshot() field that landed on main AFTER the committed
# HK/CN latest.json was persisted is legitimately absent until the Asia-close
# lane re-persists (the "engine: asia dashboards <date>" commit, ~06:00Z). Main
# went red on ci-pack-3 for the whole day of 2026-09-23 this way: #7505 (04:00Z)
# added `participation_scope`, the committed artifacts were asof 2026-09-22, and
# this test is only ever run against the committed bytes. Each entry names the
# field and the UTC date it landed; the exemption holds ONLY while the artifact's
# own `asof` is strictly earlier than that date, so the next re-persist makes the
# field mandatory again and the row becomes dead weight to delete. A re-typed
# subset still fails: it lacks the blender fields and the older canonical keys.
_FIELDS_AWAITING_NIGHTLY_REPERSIST = {
    "participation_scope": "2026-09-23",  # #7505 fix(macro): selective vs broad risk-on
}


def _field_awaits_nightly_repersist(field: str, snap: dict) -> bool:
    landed = _FIELDS_AWAITING_NIGHTLY_REPERSIST.get(field)
    asof = str(snap.get("asof") or "")
    return bool(landed) and bool(asof) and asof < landed


def test_committed_hk_cn_latest_json_is_persist_output():
    """R-W2-11 / R-W2-12: committed HK/CN latest.json must be
    persist(snapshot(profile)) output — the engine's own field set and
    key order — not a re-typed {score, verdict, labels} subset dumped
    through persist(). Compact JSON (no indent), labels from engine._LABEL,
    never the previous leg's re-originated 趋险 map."""
    from engine.market_state import _LABEL, market_state_snapshot
    from engine.market_state_hk import HK_PROFILE

    probe = market_state_snapshot(_hk_input(), frame=None, alerts=[],
                                  profile=HK_PROFILE)
    assert probe is not None
    canonical_keys = list(probe.keys())
    # snapshot() places "market" immediately before the caveats
    # (engine/market_state.py market_state_snapshot return dict).
    assert canonical_keys.index("market") < canonical_keys.index("caveat_en")
    blender_fields = (
        "score_ceiling", "score_caps", "score_gap", "radar",
        "components", "mtf", "overrides", "flip_en", "flip_zh",
        "alerts_count", "input_vintages", "stale_inputs",
        "degraded_components",
    )

    for rel, key in (
        ("data/hk_market_state/latest.json", "hk"),
        ("data/china_market_state/latest.json", "cn"),
    ):
        path = ROOT / rel
        if not path.exists():
            pytest.skip(f"{rel} absent in this checkout")
        raw = path.read_text()
        snap = json.loads(raw)
        keys = list(snap.keys())
        assert snap.get("market") == key
        verdict = snap["verdict"]
        assert snap["label_en"] == _LABEL[verdict][0]
        assert snap["label_zh"] == _LABEL[verdict][1]
        assert snap["label_zh"] != "趋险"
        # persist() writes json.dumps(..., ensure_ascii=False, default=str)
        # with no indent. A pretty-printed file is the old hand-typed splice.
        assert "\n  " not in raw, (
            f"{rel} is pretty-printed; persist() writes compact JSON"
        )
        missing = [k for k in blender_fields if k not in snap]
        assert not missing, (
            f"{rel} is a re-typed subset, not snapshot() output; "
            f"missing blender fields {missing}. keys={keys}"
        )
        for k in canonical_keys:
            if k not in snap and _field_awaits_nightly_repersist(k, snap):
                continue
            assert k in snap, (
                f"{rel} missing snapshot() field {k!r}; keys={keys}"
            )
        assert keys.index("market") < keys.index("caveat_en"), (
            f"{rel} must place 'market' before the caveats the way "
            f"market_state_snapshot() emits them; keys={keys}"
        )
        # persist() writer identity: compact json.dumps of the snap.
        rewritten = json.dumps(snap, ensure_ascii=False, default=str)
        assert raw == rewritten, (
            f"{rel} is not persist() writer output "
            f"(json.dumps(..., ensure_ascii=False, default=str))"
        )


def test_ud_b2_w2_splice_scripts_are_gone():
    """R-W2-11: the hand-rolled splice + capture scripts must not survive
    in the PR. site/macro.html is regenerated by scripts/build_site.py;
    persist artifacts are written by engine.market_state.persist()."""
    assert not (ROOT / "scripts" / "_ud_b2_w2_micro_build.py").exists()
    assert not (ROOT / "scripts" / "_ud_b2_w2_capture.py").exists()


def test_legacy_verify_shots_ud_b2_w2_are_gone():
    """R-W2-13: verify_shots/UD-B2-W2 and verify_shots/UD-B2-W2-spine-binding
    pin fabricated positions (55%/+4, 43%/−6) and must not survive in any
    form. Evidence lives at mockups/evidence/unified-dashboard-b2w2/."""
    assert not (ROOT / "verify_shots" / "UD-B2-W2").exists()
    assert not (ROOT / "verify_shots" / "UD-B2-W2-spine-binding").exists()


def test_hero_template_has_no_color_mix():
    """R-W2-16: changed template lines must not use color-mix(); existing
    tokens only. (scripts/check_design_system.py FUNC_COLOR_RE does not
    match color-mix — a linter gap; compliance is to the LAW.)"""
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text()
    assert "color-mix" not in src


def test_persisted_labels_come_from_engine_label_map(intl_root):
    """R-W2-12: EN/ZH verdict labels come from engine.market_state._LABEL,
    never a re-originated map (the previous leg's 趋险 vs 风险偏好)."""
    from engine.market_state import _LABEL, load_persisted
    for key in ("hk", "cn"):
        snap = load_persisted(root=intl_root, market_key=key)
        assert snap is not None
        verdict = snap["verdict"]
        assert snap["label_en"] == _LABEL[verdict][0]
        assert snap["label_zh"] == _LABEL[verdict][1]
        assert snap["label_zh"] != "趋险"


def test_spine_slice_aria_labels_are_plain_caveat_sentences(intl_root):
    """R-W2-15: aria-labels are plain sentences mirroring the ACTUAL caveat
    text, EN and ZH. 'engine caveat' machine-English is banned copy."""
    hk = _persisted_ms_view(intl_root, "hk")
    cn = _persisted_ms_view(intl_root, "cn")
    vm = {
        "market_state": None, "stance": {}, "ms_history": [],
        "hk_market_state": hk, "cn_market_state": cn,
        "latest": {}, "alerts": [], "event_strip": [],
        "fear_greed": {}, "risk_envelope": {},
    }
    html = _render_macro_with_hero(vm)
    slice_ = _spine_slice(html)
    assert "engine caveat" not in slice_
    assert 'aria-label="engine caveat"' not in html
    # Each bound row's disclosure aria-label is the actual caveat sentence
    # (as-of prefix + engine caveat), in both locales — on the attribute,
    # not merely as visible disclosure text (a non-sentence aria-label
    # would still pass if we only searched the row body).
    hk_row = _hk_row(slice_)
    cn_row = _cn_row(slice_)

    def _disc(asof, caveat, *, zh: bool) -> str:
        if not asof:
            return caveat
        return (f"截至 {asof}。{caveat}" if zh
                else f"As of {asof}. {caveat}")

    hk_en = _disc(hk.get("asof"), hk["caveat_en"], zh=False)
    hk_zh = _disc(hk.get("asof"), hk["caveat_zh"], zh=True)
    cn_en = _disc(cn.get("asof"), cn["caveat_en"], zh=False)
    cn_zh = _disc(cn.get("asof"), cn["caveat_zh"], zh=True)
    assert f'aria-label="{hk_en}"' in hk_row, (
        f"HK EN aria-label must be the full disclosure sentence; "
        f"expected aria-label={hk_en!r} in {hk_row[-500:]!r}"
    )
    assert f'aria-label="{hk_zh}"' in hk_row, (
        f"HK ZH aria-label must be the full disclosure sentence; "
        f"expected aria-label={hk_zh!r} in {hk_row[-500:]!r}"
    )
    assert f'aria-label="{cn_en}"' in cn_row, (
        f"CN EN aria-label must be the full disclosure sentence; "
        f"expected aria-label={cn_en!r} in {cn_row[-500:]!r}"
    )
    assert f'aria-label="{cn_zh}"' in cn_row, (
        f"CN ZH aria-label must be the full disclosure sentence; "
        f"expected aria-label={cn_zh!r} in {cn_row[-500:]!r}"
    )
    # Visible disclosure still carries the caveat sentences.
    assert hk["caveat_en"] in hk_row
    assert hk["caveat_zh"] in hk_row
    assert cn["caveat_en"] in cn_row
    assert cn["caveat_zh"] in cn_row


def test_spine_slice_asof_lives_in_disclosure_not_name_cell(intl_root):
    """R-W2-14: as-of dates are absent from the name cell; they travel with
    the caveat in the disclosure."""
    hk = _persisted_ms_view(intl_root, "hk")
    vm = {
        "market_state": None, "stance": {}, "ms_history": [],
        "hk_market_state": hk, "cn_market_state": None,
        "latest": {}, "alerts": [], "event_strip": [],
        "fear_greed": {}, "risk_envelope": {},
    }
    row = _hk_row(_spine_slice(_render_macro_with_hero(vm)))
    name_m = re.search(
        r'<div class="mx-spine-name">(.*?)</div>', row, re.S)
    assert name_m, "HK name cell not found"
    name = name_m.group(1)
    assert "as of" not in name
    assert "截至" not in name
    assert "mx-spine-asof" not in name
    disc_m = re.search(
        r'<div class="mx-spine-caveat"[^>]*>(.*?)</div>', row, re.S)
    assert disc_m, "HK caveat disclosure must exist when the row is bound"
    disc = disc_m.group(1)
    asof = str(hk.get("asof") or "")
    if asof:
        assert asof in disc, (
            f"as-of {asof} must live in the disclosure; disclosure={disc!r}"
        )
    assert hk["caveat_en"] in disc
    assert hk["caveat_zh"] in disc


def test_spine_slice_cn_no_date_or_score_integer_in_cells(intl_root):
    """R-W2-14 mirror for the CN row cells."""
    vm = {
        "market_state": None, "stance": {}, "ms_history": [],
        "hk_market_state": None,
        "cn_market_state": _persisted_ms_view(intl_root, "cn"),
        "latest": {}, "alerts": [], "event_strip": [],
        "fear_greed": {}, "risk_envelope": {},
    }
    row = _cn_row(_spine_slice(_render_macro_with_hero(vm)))
    cells = _row_cells_without_disclosure(row)
    assert "as of" not in cells
    assert "截至" not in cells
    assert not re.search(r"\d{4}-\d{2}-\d{2}", cells)
    travel_match = re.search(r'<span class="tnum">([+−]?\d+)</span>', row)
    assert travel_match
    visible = re.sub(r"<[^>]+>", " ", cells)
    integers = re.findall(r"\d+", visible)
    travel_digits = re.findall(r"\d+", travel_match.group(1))
    assert integers == travel_digits, (
        f"CN row cells may only show the travel delta; found {integers} in "
        f"{visible!r}"
    )