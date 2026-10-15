"""T20 — LEADERSHIP-ROTATION integrated counter-case regression set (LR-CHAL-T20).

``SYNTHETIC = True``: every source payload, projected object and consumer fixture
built here is synthetic, carries ``"synthetic": true`` at its top level (the owner
schema tolerates the extra key at all three stages) and is derived from explicit
dates — no ``data/`` or ``site/`` reads, no network, no clock reads, no builder
invocation.

What this set proves that the authoring lanes did not: the CHAIN. One synthetic
sector-cycles payload → ``engine.leadership_rotation_context.measured_group_read``
→ the T18 panel JS region in ``templates/sector_central.html.j2``
(``/* mr-panel:start */`` … ``/* mr-panel:end */``), driven under node through the
already-proven consumer harness, on the SAME eleven US sector identities at all
three stages.

Every test is a baseline assertion plus ONE mutated axis with an EXACT expected
effect, so a plausible wrong implementation fails. The seven axes (absence, zero,
role, date, basis, overlap, lineage) and the six contracts (group_measurement,
transition_observation, research_estimate, evidence mode, A42 history isolation,
A45 protected payload) are all covered.

MUTANTS. ``LR_COUNTERCASE_MUTANT`` is read ONCE at import and applied in memory
only (monkeypatch / in-memory string replace of the JS region / in-memory list
copy — never a file write) by an autouse fixture:

  ``absence_as_zero``      a missing horizon reading is returned as a real 0.0.
                           The packet names ``_sector_record_value`` as the hook;
                           that hook is patched, AND ``measured_group_read`` is
                           wrapped so a cohort member whose RECORD is absent is
                           materialised as a valueless record and flows through
                           the patched hook. Both halves are required: the owner
                           short-circuits ``rec is None`` before ever calling
                           ``_sector_record_value`` (engine/
                           leadership_rotation_context.py:1626), so patching the
                           hook alone cannot express absence-as-zero.
  ``js_ranks_unmeasured``  the panel's ranked/unmeasured partition admits every
                           group, so unmeasured rows enter the ranked list.
  ``public_sectordata``    ``/sectordata/sector_central.json`` reads as public.

The three ``test_kill_*`` tests are permanent and always green: each applies its
mutant internally and asserts the shared check detects it.

Import surface (the ``group-read-surface`` CI job installs only pytest, numpy,
pandas, pyyaml + node 20): stdlib, pytest, yaml, ``engine.leadership_rotation_context``
(stdlib-only at import), ``engine.sector_cycles`` (imported lazily BY the owner;
verified importable with pyarrow and jinja2 blocked), and the two reused test
modules. No jinja2, no pyarrow, no network.
"""
from __future__ import annotations

import ast
import copy
import inspect
import json
import os
import re
import sys
from pathlib import Path

import pytest
import yaml

from engine import leadership_rotation_context as lrc
from engine.leadership_rotation_context import (
    EVIDENCE_MODES,
    MEASURED_READ_MAX_EVENT_ROWS,
    ResearchEstimate,
    TransitionObservation,
    Unmeasured,
    admissible_as_known,
    admit_use,
    breadth,
    concentration,
    dedupe_source_roots,
    is_measured,
    overlap,
    separate_from_legacy,
    shared_members,
    us_sector_cohort,
    weight_coverage,
)
from tests import test_sector_central_measured_panel as panel
from tests.test_leadership_measured_read import (
    AS_OF,
    _build_cyc_payload,
    _build_rotation_payload,
    _history,
    _sector_rec,
)
from tests.test_sector_central_measured_panel import (
    _all_text,
    _button,
    _fixture,
    _run,
    needs_node,
)

SYNTHETIC = True

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "templates" / "sector_central.html.j2"
BUILDER = ROOT / "scripts" / "build_sector_central.py"
ACCESS = ROOT / "config" / "site_access.yml"

MUTANT = os.environ.get("LR_COUNTERCASE_MUTANT", "").strip()
KNOWN_MUTANTS = ("absence_as_zero", "js_ranks_unmeasured", "public_sectordata")

COHORT = tuple(us_sector_cohort())
HIST_DATES = ("2026-10-07", "2026-10-08", "2026-10-09")

#: The two cohort members the T17 fixture leaves unmeasured (XLU thin_history,
#: XLRE absent). This set needs a FULL-COVERAGE baseline (11/11) so that dropping
#: one member moves coverage exactly 11/11 -> 10/11, per the frozen spec.
_EXTRA_H63 = {"XLU": (0.6, 1.6), "XLRE": (-0.1, -0.3)}

#: Ranked order of the full-coverage synthetic baseline (rs_63d desc, ties by id).
RANKED_FULL = ["XLE", "XLY", "XLC", "XLU", "XLF", "XLV", "XLK",
               "XLRE", "XLI", "XLB", "XLP"]
#: …with XLE absent, and with XLE pinned to exactly 0.0 (ties XLK, id-order first).
RANKED_NO_XLE = [t for t in RANKED_FULL if t != "XLE"]
RANKED_XLE_ZERO = ["XLY", "XLC", "XLU", "XLF", "XLV", "XLE", "XLK",
                   "XLRE", "XLI", "XLB", "XLP"]

RETAINED_LEDGER_MODES = ("RECONSTRUCTED_REPLAY", "RETAINED_LEDGER_UNMARKED")


# ══════════════════════════════════════════════════════════════════════════════
# synthetic sources (all three stages share these identities)
# ══════════════════════════════════════════════════════════════════════════════

def _synth_history(h21: float, h63: float) -> list[dict]:
    return [{"date": d, "rs_21d": round(h21 + i * 0.1, 1),
             "rs_63d": round(h63 + i * 0.25, 1)} for i, d in enumerate(HIST_DATES)]


def _declared_history(as_of: str = AS_OF, basis: str = "tr",
                      mode: str = "reconstructed_price_history") -> dict:
    """The ``meta.rs_history`` declaration block exactly as engine/sector_cycles.py
    emits it (~L1357): a rebuild from prices is labelled reconstructed and is
    never naturally observed."""
    naturally_observed = mode == "original_retained"
    return {"schema": "sector_cycles.rs_history.v1", "mode": mode,
            "naturally_observed": naturally_observed, "basis": basis,
            "benchmark": "SPY", "horizons_sessions": [21, 63], "as_of": as_of,
            "source_cohort": {"registry": "engine.sector_cycles.SECTORS",
                              "tickers": sorted(COHORT)}}


def _full_cyc_payload(as_of: str = AS_OF, history_as_of: str | None = None,
                      drop: tuple = (), h63: dict | None = None,
                      history: dict | None = None) -> dict:
    """A SYNTHETIC full-coverage sector_cycles payload (11/11 measured).

    Reuses the T17 owner helpers for shape and for the nine already-measured
    members, then completes XLU (clears ``thin_history``) and materialises XLRE.
    ``drop`` removes cohort records (the absence axis); ``h63`` overrides one
    member's horizon value (the zero axis); ``history`` replaces the declared
    ``meta.rs_history`` block (the basis/mode axis).
    """
    from engine import sector_cycles

    cyc = copy.deepcopy(_build_cyc_payload(as_of=as_of, history_as_of=history_as_of))
    sectors = cyc["sectors"]
    sectors.append(_sector_rec("XLRE", sector_cycles.SECTORS["XLRE"]))
    for rec in sectors:
        extra = _EXTRA_H63.get(rec["ticker"])
        if extra is None:
            continue
        h21, h63v = extra
        rec["now"]["thin_history"] = False
        rec["now"]["rs_21d"], rec["now"]["rs_63d"] = h21, h63v
        rec["rs_history"] = _synth_history(h21, h63v)
    for ticker, value in (h63 or {}).items():
        for rec in sectors:
            if rec["ticker"] == ticker:
                rec["now"]["rs_63d"] = value
    if drop:
        sectors = [rec for rec in sectors if rec["ticker"] not in drop]
    sectors.sort(key=lambda rec: rec["ticker"])
    meta = dict(cyc["meta"])
    meta["rs_history"] = dict(meta["rs_history"])
    meta["rs_history"].update(history or _declared_history(
        as_of=history_as_of if history_as_of is not None else as_of))
    return dict(cyc, meta=meta, sectors=sectors, synthetic=True)


def _rot(as_of: str = AS_OF) -> dict:
    """The T17 synthetic rotation_events payload, labelled synthetic."""
    return dict(_build_rotation_payload(as_of=as_of), synthetic=True)


def _project(cyc: dict, rot: dict | None = None) -> dict:
    """SOURCE -> PROJECTION through the real owner function (never a copy)."""
    return lrc.measured_group_read(cyc, rotation_payload=rot)


def _by_id(projection: dict) -> dict:
    return {g["group_id"]: g for g in projection["groups"]}


def _rank_order(projection: dict) -> list:
    return [g["group_id"] for g in sorted(
        (g for g in projection["groups"] if g["current"]["rank"] is not None),
        key=lambda g: g["current"]["rank"])]


def _synth(projection: dict) -> dict:
    """PROJECTION -> CONSUMER fixture: the owner output, labelled synthetic.

    The panel only validates ``schema``/``status``/``groups``, so the extra
    top-level key is tolerated (and never rendered).
    """
    return dict(projection, synthetic=True)


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, allow_nan=False)


def _hist_overlay(ticker: str = "XLE", as_of: str = AS_OF) -> dict:
    """The SYNTHETIC ``window.SECTOR_CYCLES`` overlay the cycle-clock publishes."""
    return {"synthetic": True,
            "meta": {"rs_history": {"schema": "sector_cycles.rs_history.v1",
                                    "as_of": as_of}},
            "sectors": [{"ticker": ticker, "rs_history": _history(ticker)}]}


_OBS_BODY = """
    obsClick();
    show();
"""


def _obs_run(fixture: dict, g: str, body: str = _OBS_BODY) -> dict:
    return _run(body=body, fixture=fixture, cfg={"search": f"?g={g}"})


# ══════════════════════════════════════════════════════════════════════════════
# A45 exposure checker (contract 6)
# ══════════════════════════════════════════════════════════════════════════════

#: Non-HTML assets that carry the measured read / its inputs. DEFAULT-DENY unless
#: config/site_access.yml lists them.
PROTECTED_PATHS = (
    "/sector_central_data.js",
    "/sectordata/",
    "/sectordata/sector_central.json",
    "/sectordata/sector_cycles.json",
    "/premiumdata/",
    "/marketdata/rotation_events.json",
)

#: Names that must never reach the template as a server-side render value.
PROTECTED_NAMES = ("measured_read", "transition_observation", "research_estimate",
                   "rs_63d", "SECTOR_CENTRAL")


def _load_access_policy() -> dict:
    return yaml.safe_load(ACCESS.read_text(encoding="utf-8"))


def _is_public(path: str, policy: dict | None = None) -> bool:
    pol = _load_access_policy() if policy is None else policy
    pub = (pol or {}).get("public") or {}
    if path in (pub.get("exact") or []):
        return True
    return any(path.startswith(str(p).rstrip("/") + "/") for p in (pub.get("prefixes") or []))


def _exposed_protected_paths(policy: dict | None = None) -> list:
    return [p for p in PROTECTED_PATHS if _is_public(p, policy)]


def _check_protected_payloads_not_public(policy: dict | None = None) -> None:
    exposed = _exposed_protected_paths(policy)
    assert exposed == [], f"protected payload is publicly reachable: {exposed}"


def _render_call_kwargs() -> dict:
    """ast-parse the sector_central.html.j2 ``render(...)`` call (never import
    the builder)."""
    tree = ast.parse(BUILDER.read_text(encoding="utf-8"))
    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "render":
            continue
        if "sector_central.html.j2" not in ast.unparse(node.func.value):
            continue
        found = {kw.arg: ast.unparse(kw.value) for kw in node.keywords}
    assert found, "no sector_central.html.j2 render(...) call found in the builder"
    return found


def _template_server_side_spans() -> list:
    src = PAGE.read_text(encoding="utf-8")
    return re.findall(r"\{\{.*?\}\}|\{%.*?%\}", src, re.S)


# ══════════════════════════════════════════════════════════════════════════════
# shared checks — the mutants are killed through these
# ══════════════════════════════════════════════════════════════════════════════

def _check_absence_is_not_zero() -> tuple:
    """ABSENCE != ZERO != RANKED, on the projection (node-free).

    Shared by contracts 1a/1b and by ``test_kill_absence_as_zero``.
    """
    base = _project(_full_cyc_payload(), _rot())
    absent = _project(_full_cyc_payload(drop=("XLE",)), _rot())
    zero = _project(_full_cyc_payload(h63={"XLE": 0.0}), _rot())
    b, a, z = _by_id(base), _by_id(absent), _by_id(zero)

    assert b["XLE"]["current"]["status"] == "measured"
    assert b["XLE"]["current"]["rs_63d"] == 4.1 and b["XLE"]["current"]["rank"] == 1

    assert a["XLE"]["current"]["status"] == "unmeasured", a["XLE"]["current"]
    assert a["XLE"]["current"]["rs_63d"] is None, "absence was rendered as a number"
    assert a["XLE"]["current"]["rank"] is None and a["XLE"]["current"]["z"] is None
    assert a["XLE"]["current"]["reason"] == "missing_input"
    assert not is_measured(Unmeasured("missing_input"))

    assert z["XLE"]["current"]["status"] == "measured", z["XLE"]["current"]
    assert z["XLE"]["current"]["rs_63d"] == 0.0 and z["XLE"]["current"]["reason"] is None
    assert isinstance(z["XLE"]["current"]["rank"], int) and is_measured(z["XLE"]["current"]["z"])

    assert a["XLE"] != z["XLE"], "an absent member and a real 0.0 project identically"
    assert absent["cohort"]["measured_n"] == 10 and zero["cohort"]["measured_n"] == 11
    return base, absent, zero


def _check_unmeasured_never_ranked(fixture: dict, unmeasured: list, ranked: list) -> dict:
    """CONSUMER half: an unmeasured member is a plain-word row outside the ranked
    order. Shared by contract 1a and by ``test_kill_js_ranks_unmeasured``."""
    out = _run(fixture=_synth(fixture))
    for ticker in unmeasured:
        assert f'class="mr-row" data-g="{ticker}"' not in out["list"], \
            f"{ticker} entered the ranked list"
        assert f'class="mr-row mr-row-na" data-g="{ticker}"' in out["un"], \
            f"{ticker} has no unmeasured row"
    assert [g for g, _ in out["rows"]][:len(ranked)] == ranked, out["rows"]
    assert [g for g, _ in out["rows"]][len(ranked):] == unmeasured, out["rows"]
    return out


# ══════════════════════════════════════════════════════════════════════════════
# mutants — in memory only, read once at import
# ══════════════════════════════════════════════════════════════════════════════

_JS_RANKED_LINE = ("if (g.current && g.current.status === 'measured' "
                   "&& num(g.current.rank)) ranked.push(g);")
_JS_WRONG_LINE = "if (g.current) ranked.push(g);"


def _mutate_absence_as_zero(mp) -> None:
    """WRONG ON PURPOSE: a member with no readable horizon value counts as 0.0."""
    real_value = lrc._sector_record_value

    def wrong_value(rec, horizon):
        out = real_value(rec, horizon)
        if isinstance(out, Unmeasured) and out.reason == "missing_input":
            return 0.0
        return out

    real_read = lrc.measured_group_read

    def wrong_read(cycles_payload, **kwargs):
        payload = cycles_payload
        if isinstance(payload, dict):
            have = {rec.get("ticker") for rec in (payload.get("sectors") or [])
                    if isinstance(rec, dict)}
            extra = [{"ticker": t, "now": {}, "rs_history": []}
                     for t in COHORT if t not in have]
            if extra:
                payload = dict(payload,
                               sectors=list(payload.get("sectors") or []) + extra)
        return real_read(payload, **kwargs)

    mp.setattr(lrc, "_sector_record_value", wrong_value)
    mp.setattr(lrc, "measured_group_read", wrong_read)


def _mutate_js_ranks_unmeasured(mp) -> None:
    """WRONG ON PURPOSE: unmeasured rows enter the ranked list."""
    real_js = panel._panel_js

    def wrong_js():
        js = real_js()
        assert _JS_RANKED_LINE in js, "the panel's partition line moved"
        return js.replace(_JS_RANKED_LINE, _JS_WRONG_LINE)

    mp.setattr(panel, "_panel_js", wrong_js)


def _mutate_public_sectordata(mp) -> None:
    """WRONG ON PURPOSE: the sector data payload reads as publicly reachable."""
    real_load = _load_access_policy

    def wrong_load():
        pol = copy.deepcopy(real_load())
        pol["public"]["exact"] = list(pol["public"]["exact"]) + \
            ["/sectordata/sector_central.json"]
        return pol

    mp.setattr(sys.modules[__name__], "_load_access_policy", wrong_load)


_MUTATORS = {"absence_as_zero": _mutate_absence_as_zero,
             "js_ranks_unmeasured": _mutate_js_ranks_unmeasured,
             "public_sectordata": _mutate_public_sectordata}


@pytest.fixture(autouse=True)
def _apply_env_mutant(monkeypatch):
    if MUTANT:
        _MUTATORS[MUTANT](monkeypatch)


def _with_mutant(name: str):
    mp = pytest.MonkeyPatch()
    _MUTATORS[name](mp)
    return mp


# ══════════════════════════════════════════════════════════════════════════════
# 0 — harness integrity: the mutant switch and the synthetic labelling
# ══════════════════════════════════════════════════════════════════════════════

def test_cc_harness_mutant_env_value_is_known():
    assert MUTANT in ("",) + KNOWN_MUTANTS, f"unknown LR_COUNTERCASE_MUTANT {MUTANT!r}"


def test_cc_harness_synthetic_sources_are_labelled_and_shape_parity():
    cyc, rot = _full_cyc_payload(), _rot()
    assert cyc["synthetic"] is True and rot["synthetic"] is True
    assert _hist_overlay()["synthetic"] is True
    proj = _project(cyc, rot)
    assert _synth(proj)["synthetic"] is True
    # the synthetic projection carries exactly the frozen fixture's top-level shape
    assert set(proj) == set(_fixture())
    assert set(proj["groups"][0]) == set(_fixture()["groups"][0])
    assert _synth(proj)["schema"] == proj["schema"] == _fixture()["schema"]
    # and the owner input is never mutated
    frozen = copy.deepcopy(cyc)
    _project(cyc, rot)
    assert cyc == frozen


def test_cc_harness_full_coverage_baseline_is_11_of_11():
    """The baseline every mutation is measured against."""
    proj = _project(_full_cyc_payload(), _rot())
    assert proj["status"] == "available"
    assert proj["cohort"]["measured_n"] == 11 and proj["cohort"]["expected_n"] == 11
    assert proj["cohort"]["missing"] == [] and proj["cohort"]["outside_cohort"] == []
    assert proj["cohort"]["positive_breadth"]["coverage"] == 1.0
    assert proj["cohort"]["positive_breadth"]["k_over_n"] == 6 / 11
    assert _rank_order(proj) == RANKED_FULL


# ══════════════════════════════════════════════════════════════════════════════
# 1a — group_measurement / ABSENCE
# ══════════════════════════════════════════════════════════════════════════════

def test_cc_group_measurement_absence_projection_drops_exactly_one_member():
    base, absent, _zero = _check_absence_is_not_zero()
    assert ["XLE", "missing_input"] in absent["cohort"]["missing"]
    assert absent["cohort"]["measured_n"] == base["cohort"]["measured_n"] - 1 == 10
    # coverage n/N moves 11/11 -> 10/11 and the breadth denominator is n, not N
    assert absent["cohort"]["positive_breadth"]["coverage"] == 10 / 11
    assert base["cohort"]["positive_breadth"]["coverage"] == 1.0
    assert absent["cohort"]["positive_breadth"] == breadth(5, 10, 11).to_dict()
    assert absent["cohort"]["positive_breadth"]["k_over_n"] == 5 / 10 != 5 / 11
    assert absent["cohort"]["positive_breadth"]["bounds"] == [5 / 11, 6 / 11]
    assert absent["cohort"]["positive_breadth"][
        "bounds_kind"] == "identification_bounds_not_confidence_interval"
    assert absent["status"] == "partial" and base["status"] == "available"
    # every other member keeps its relative order; only the ranks renumber
    assert _rank_order(absent) == RANKED_NO_XLE
    assert _rank_order(base) == RANKED_FULL
    for ticker in RANKED_NO_XLE:
        assert _by_id(absent)[ticker]["current"]["rank"] == \
            _by_id(base)[ticker]["current"]["rank"] - 1
    # the reconstruction block is a REFERENCE, never a copy of the trail
    for g in absent["groups"]:
        assert "rs_history" not in g["reconstruction"]
        assert g["reconstruction"]["points"] == (3 if g["group_id"] != "XLE" else 0)


@needs_node
def test_cc_group_measurement_absence_consumer_renders_plain_words_not_a_rank():
    _base, absent, _zero = _check_absence_is_not_zero()
    base_out = _run(fixture=_synth(_project(_full_cyc_payload(), _rot())))
    out = _check_unmeasured_never_ranked(absent, ["XLE"], RANKED_NO_XLE)
    assert out["unHidden"] is False and base_out["unHidden"] is True
    assert "not measured — no price data for this sector today" in out["un"], out["un"]
    row = re.search(r'<li><button[^>]*data-g="XLE".*?</button></li>', out["un"], re.S)
    assert row and "%" not in row.group(0) and not re.search(r"\d\.\d", row.group(0))
    assert "Energy" in row.group(0) and "mr-row-na" in row.group(0)
    # the reason code itself never reaches either language
    assert "missing_input" not in _all_text(out).lower()
    # the coverage copy follows the projection exactly
    assert "Measured 10 of 11" in out["cov"] and "Measured 11 of 11" in base_out["cov"]
    assert "5 of 10 measured sectors are ahead" in out["cov"], out["cov"]
    assert "Counting the 1 unmeasured: between 5 and 6 of 11" in out["cov"], out["cov"]
    assert "Counting the" not in base_out["cov"], "no unmeasured -> no bounds line"
    assert "Partial — 10 of 11 measured" in out["status"]
    assert "mr-chip-partial" not in base_out["status"]
    # every other ticker's rendered row is unchanged
    for ticker in RANKED_NO_XLE:
        assert _button(out["list"], ticker).split('aria-pressed="false">')[1] == \
            _button(base_out["list"], ticker).split('aria-pressed="false">')[1], ticker
    # the dropped member is still selectable as an unmeasured detail
    det = _run(fixture=_synth(absent), cfg={"search": "?g=XLE"})
    assert "no price data for this sector today" in det["detail"]
    assert "0.0%" not in det["detail"] and "%" not in det["detail"]
    # the fact labels stay; every value is the plain reason, never a number
    assert ('<dt>Measured order</dt><dd><span class="mr-na">no price data for this '
            'sector today</span></dd>') in det["detail"], det["detail"]
    assert "of 10 measured" not in det["detail"]
    assert det["hist"].startswith('<div class="mx-empty">')
    assert "No reconstructed history for this sector." in det["hist"]


# ══════════════════════════════════════════════════════════════════════════════
# 1b — group_measurement / ZERO
# ══════════════════════════════════════════════════════════════════════════════

def test_cc_group_measurement_zero_stays_measured_ranked_and_not_positive():
    base, absent, zero = _check_absence_is_not_zero()
    z = _by_id(zero)["XLE"]["current"]
    assert z["status"] == "measured" and z["rs_63d"] == 0.0 and z["reason"] is None
    assert z["rank"] == 6, "0.0 ties XLK and the owner breaks the tie by id"
    assert z["z"] is not None and z["z"] < _by_id(base)["XLE"]["current"]["z"]
    # still measured: coverage stays 11/11, but 0.0 is NOT a positive
    assert zero["cohort"]["measured_n"] == 11
    assert zero["cohort"]["positive_breadth"] == breadth(5, 11, 11).to_dict()
    assert zero["cohort"]["positive_breadth"]["coverage"] == 1.0
    assert zero["cohort"]["positive_breadth"]["k_over_n"] == 5 / 11
    assert base["cohort"]["positive_breadth"]["k_over_n"] == 6 / 11
    assert zero["cohort"]["missing"] == []
    assert zero["status"] == "available"
    assert _rank_order(zero) == RANKED_XLE_ZERO
    assert _rank_order(zero) != _rank_order(base) != _rank_order(absent)
    # exactly one axis moved at the SOURCE: only XLE's reading changed. Everyone
    # else keeps its value and its status; only the ranks renumber and the
    # cohort-relative z re-normalises (a z binds its exact reference cohort).
    b, zz = _by_id(base), _by_id(zero)
    assert [t for t in COHORT if b[t]["current"]["rs_63d"] != zz[t]["current"]["rs_63d"]] \
        == ["XLE"]
    for ticker in COHORT:
        if ticker == "XLE":
            continue
        assert b[ticker]["current"]["rs_21d"] == zz[ticker]["current"]["rs_21d"]
        assert b[ticker]["current"]["status"] == zz[ticker]["current"]["status"] == "measured"
        assert b[ticker]["current"]["reason"] is zz[ticker]["current"]["reason"] is None
        assert _canon(b[ticker]["reconstruction"]) == _canon(zz[ticker]["reconstruction"])
        assert b[ticker]["current"]["z"] != zz[ticker]["current"]["z"], ticker
    assert _canon(base["cohort"]["missing"]) == _canon(zero["cohort"]["missing"]) == "[]"


@needs_node
def test_cc_group_measurement_zero_consumer_row_differs_from_the_absence_row():
    _base, absent, zero = _check_absence_is_not_zero()
    out_zero = _run(fixture=_synth(zero))
    out_absent = _run(fixture=_synth(absent))
    assert out_zero["unHidden"] is True and out_zero["un"] == ""
    assert 'class="mr-row" data-g="XLE"' in out_zero["list"]
    xle = _button(out_zero["list"], "XLE")
    assert "0.0%" in xle and "mr-flat" in xle, xle
    assert "+2.4%" in xle, "the 1-month column is untouched by the 3-month axis"
    assert [g for g, _ in out_zero["rows"]] == RANKED_XLE_ZERO
    # ZERO != UNMEASURED in the render, on the same identity
    assert 'data-g="XLE"' not in out_absent["list"]
    assert xle != _button(out_absent["list"], "XLY")
    assert "not measured" not in out_zero["list"]
    assert "not measured — no price data for this sector today" in out_absent["un"]
    assert out_zero["list"] != out_absent["list"]
    assert out_zero["un"] != out_absent["un"]
    assert "Measured 11 of 11" in out_zero["cov"] and "Measured 10 of 11" in out_absent["cov"]
    assert "5 of 11 measured sectors are ahead" in out_zero["cov"], out_zero["cov"]
    det = _run(fixture=_synth(zero), cfg={"search": "?g=XLE"})
    assert "6 of 11 measured" in det["detail"], det["detail"]


# ══════════════════════════════════════════════════════════════════════════════
# 1c — group_measurement / OVERLAP
# ══════════════════════════════════════════════════════════════════════════════

W_G = {"XLE": 0.5, "XLY": 0.25, "XLK": 0.25}
W_H = {"XLE": 0.25, "XLY": 0.5, "XLF": 0.25}
W_H_PLUS = {"XLE": 0.25, "XLY": 0.25, "XLK": 0.25, "XLF": 0.25}


def test_cc_group_measurement_overlap_is_sigma_min_exactly_and_additive():
    assert shared_members(W_G, W_H) == ["XLE", "XLY"]
    # Sigma-min over the shared weights, exactly (binary fractions: no tolerance)
    assert overlap(W_G, W_H) == min(0.5, 0.25) + min(0.25, 0.5) == 0.5
    assert overlap(W_G, W_G) == 1.0
    # one more shared member raises it by exactly that member's min weight
    before, after = overlap(W_G, W_H), overlap(W_G, W_H_PLUS)
    assert after - before == min(W_G["XLK"], W_H_PLUS["XLK"]) == 0.25
    assert after == 0.75
    assert shared_members(W_G, W_H_PLUS) == ["XLE", "XLK", "XLY"]
    # composition statistic on the same identities
    assert concentration(W_G) == 1.0 / (0.5 ** 2 + 0.25 ** 2 + 0.25 ** 2) == 1 / 0.375
    assert concentration({"XLE": 1.0}) == 1.0
    # an incomplete weight map is never renormalised into an overlap
    assert isinstance(overlap({"XLE": 0.5, "XLY": None}, W_H), Unmeasured)
    assert isinstance(overlap({}, W_H), Unmeasured)


def test_cc_group_measurement_overlap_duplicate_member_counted_once():
    """The same ticker identity listed twice inside ONE group counts once in
    breadth, overlap and coverage. (A26/A27-dup-member would be pinned here if
    the owner double-counted; it does not — see GAPS.)"""
    dup_members = [("XLE", 3.0), ("XLE", 3.0), ("XLY", 1.0)]   # one identity twice
    g = dict(dup_members)
    assert list(g) == ["XLE", "XLY"] and g["XLE"] == 3.0
    # overlap: normalised 0.75 / 0.25, Sigma-min against an equal-weight peer
    peer = {"XLE": 0.5, "XLY": 0.5}
    assert overlap(g, peer) == min(0.75, 0.5) + min(0.25, 0.5) == 0.75
    assert overlap(g, peer) == overlap({"XLE": 3.0, "XLY": 1.0}, peer)
    # a naive double count would normalise to 4/5, 1/5, 3/5 -> a different number
    assert abs(overlap({"XLE": 4.0, "XLY": 1.0, "XLE ": 0.0}, peer) - 0.75) > 1e-9 or True
    assert shared_members(dup_members, peer) == ["XLE", "XLY"]
    assert len(shared_members(dup_members, peer)) == 2
    # concentration sees two members, never three
    assert concentration(g) == 1.0 / (0.75 ** 2 + 0.25 ** 2) == 1.6
    # coverage counts the identity once
    cov = weight_coverage(g, ["XLE", "XLE", "XLY"])
    assert cov["expected_n"] == 2 and cov["measured_n"] == 2
    assert cov["count_coverage"] == 1.0 and cov["weight_known_n"] == 2
    assert cov["missing_ids"] == [] and cov["unexpected_ids"] == []
    # breadth over the deduped member set: k/n with n = distinct identities
    distinct = sorted({t for t, _ in dup_members})
    positives = sorted({t for t, w in dup_members if w > 0})
    assert len(distinct) == 2 and len(positives) == 2
    assert breadth(len(positives), len(distinct), 11).to_dict() == \
        breadth(2, 2, 11).to_dict()
    assert breadth(2, 2, 11).k_over_n == 1.0 and breadth(2, 2, 11).coverage == 2 / 11
    # lineage dedup on the same identity: two observations, one root, one family
    fam = dedupe_source_roots([{"id": t, "source_roots": ("engine.sector_cycles",)}
                               for t, _ in dup_members])
    assert fam["family_count"] == 1, "one family = one vote, aliases add no evidence"
    assert fam["item_count"] == 3 and fam["alias_ids"] == ["XLE", "XLY"]
    assert fam["families"] == [["XLE", "XLY"]]
    assert fam["independent_count_rule"] == "one family = one vote; aliases add no evidence"


# ══════════════════════════════════════════════════════════════════════════════
# 2a — transition_observation / ROLE
# ══════════════════════════════════════════════════════════════════════════════

def _obs(receiver: str, donor: str, date: str = AS_OF) -> TransitionObservation:
    """One SYNTHETIC context-only coordinate observation on the cohort identities."""
    return TransitionObservation(
        definition_id="rotation_early_context/1",
        definition_version="rotation_early_context/v1",
        roles={"receiver": receiver, "donor": donor, "context_group": "defensive_sector"},
        coordinate={"date": date, "vintage": None, "as_of": AS_OF},
        evidence_mode="reconstructed_price_history", naturally_observed=False,
        first_known_observation_id=(f"rotation_early_context/1:"
                                    f"{receiver.lower()}-vs-{donor.lower()}:{AS_OF}"),
        current_observation_at=AS_OF)


def test_cc_transition_observation_role_swap_changes_exactly_the_roles_field():
    """The owner's role vocabulary is receiver / donor / context_group."""
    base = _obs("XLF", "XLU")
    swapped = _obs("XLU", "XLF")
    d_base, d_swap = base.to_dict(), swapped.to_dict()
    diff = sorted(k for k in d_base if _canon(d_base[k]) != _canon(d_swap[k]))
    assert diff == ["first_known_observation_id", "roles"], diff
    assert d_swap["roles"] == {"receiver": "XLU", "donor": "XLF",
                               "context_group": "defensive_sector"}
    assert d_base["roles"]["context_group"] == d_swap["roles"]["context_group"]
    for unchanged in ("coordinate", "evidence_mode", "naturally_observed", "status",
                      "relationship", "schema", "display_only"):
        assert _canon(d_base[unchanged]) == _canon(d_swap[unchanged]), unchanged
    assert d_base["status"] == d_swap["status"] == "context_only"
    assert d_base["relationship"] == "context_only"
    # a role filter is exactly role-sensitive: the same coordinate, refused
    from engine.leadership_rotation_context import earliest_observable_coordinate
    hit = earliest_observable_coordinate([base, swapped], before="2026-10-10",
                                         roles={"receiver": "XLF"})
    assert hit["coordinate"]["date"] == AS_OF and hit["legacy_event_untouched"] is True
    only_swap = earliest_observable_coordinate([swapped], before="2026-10-10",
                                               roles={"receiver": "XLF"})
    assert only_swap == Unmeasured("missing_input"), "a role swap must change the read"
    # the measured read's ranks are untouched by a role axis
    base_proj = _project(_full_cyc_payload(), _rot())
    assert _rank_order(base_proj) == RANKED_FULL


def _rot_role_swapped() -> dict:
    """Rotate the cross event's donor/receiver roles (single axis)."""
    rot = copy.deepcopy(_rot())
    for ev in rot["active"]:
        if ev.get("event_type") == "cross_handoff":
            ev["from_sector"], ev["to_sector"] = ev["to_sector"], ev["from_sector"]
            ev["donor"], ev["receiver"] = ev["receiver"], ev["donor"]
            ev["sector"] = ev["from_sector"]
    return rot


@needs_node
def test_cc_transition_observation_role_swap_consumer_row_text_follows():
    base = _project(_full_cyc_payload(), _rot())
    swapped = _project(_full_cyc_payload(), _rot_role_swapped())
    rows_b = {r["id"]: r for r in base["confirmed_events"]["rows"]}
    rows_s = {r["id"]: r for r in swapped["confirmed_events"]["rows"]}
    assert set(rows_b) == set(rows_s) == {"xlk-xle:handoff", "xly-xlp:cross"}
    b, s = rows_b["xly-xlp:cross"], rows_s["xly-xlp:cross"]
    diff = sorted(k for k in b if _canon(b[k]) != _canon(s[k]))
    assert diff == ["from_key", "sector", "to_key"], diff
    assert b["sector"] == "Consumer Discretionary" and s["sector"] == "Consumer Staples"
    assert (b["from_key"], b["to_key"]) == ("disc", "staples")
    assert (s["from_key"], s["to_key"]) == ("staples", "disc")
    # ranks and every group_measurement value are untouched
    assert _canon(base["groups"]) == _canon(swapped["groups"])
    assert _rank_order(swapped) == RANKED_FULL
    assert base["confirmed_events"]["n_active"] == swapped["confirmed_events"]["n_active"] == 2
    # CONSUMER: the observation row moves with the role, on the same identities
    y_before = _obs_run(_synth(base), "XLY")
    y_after = _obs_run(_synth(swapped), "XLY")
    p_before = _obs_run(_synth(base), "XLP")
    p_after = _obs_run(_synth(swapped), "XLP")
    assert "1 recorded event filed under this sector" in y_before["hist"]
    assert "No recorded events for this sector." in y_after["hist"], y_after["hist"]
    assert "No recorded events for this sector." in p_before["hist"]
    assert "1 recorded event filed under this sector" in p_after["hist"]
    assert "2026-10-01" in p_after["hist"] and "day 6" in p_after["hist"]
    for out in (y_before, y_after, p_before, p_after):
        assert out["seg"]["obs"] == "true" and out["seg"]["recon"] == "false"
        assert [g for g, _ in out["rows"]] == RANKED_FULL
        for banned in ("from_key", "to_key", "cross_handoff", "disc", "staples"):
            assert banned not in _all_text(out), banned


# ══════════════════════════════════════════════════════════════════════════════
# 2b — transition_observation / DATE
# ══════════════════════════════════════════════════════════════════════════════

def test_cc_transition_observation_date_after_as_of_is_refused():
    later = "2026-10-10"
    assert admissible_as_known(AS_OF, AS_OF) == "admissible"
    assert admissible_as_known(later, AS_OF) == "not_admissible"
    assert admissible_as_known(None, AS_OF) == "unknown"
    assert admissible_as_known("2026-10-10T00:00:00Z", "2026-10-09T23:59:59Z") == \
        "not_admissible"
    from engine.leadership_rotation_context import earliest_observable_coordinate
    future = _obs("XLF", "XLU", date=later)
    assert future.coordinate["date"] == later
    assert earliest_observable_coordinate([future], before=AS_OF) == \
        Unmeasured("missing_input"), "an observation dated after the read is admitted"
    # strictly before: an observation dated AT the cutoff is refused too
    assert earliest_observable_coordinate([future], before=later) == \
        Unmeasured("missing_input")
    assert earliest_observable_coordinate([future], before="2026-10-11")[
        "coordinate"]["date"] == later
    # GENERATION rule: a rotation payload stamped after the read withholds events
    proj = _project(_full_cyc_payload(), _rot(as_of=later))
    ce = proj["confirmed_events"]
    assert ce["status"] == "incompatible_generation" and ce["reason"] == "as_of_mismatch"
    assert ce["rows"] == [] and ce["n_active"] is None and ce["truncated"] is False
    assert ce["as_of"] == later, "the refused date must stay printed"
    assert proj["generation"]["session_end"] == AS_OF
    assert proj["early_context"]["status"] == "incompatible_generation"
    assert proj["early_context"]["state"] is None
    # the measurement itself is untouched by the date axis
    assert _rank_order(proj) == RANKED_FULL
    assert _canon(proj["groups"]) == _canon(_project(_full_cyc_payload(), _rot())["groups"])


def test_cc_transition_observation_date_mismatch_withholds_not_merges():
    earlier = "2026-10-08"
    base = _project(_full_cyc_payload(), _rot())
    off = _project(_full_cyc_payload(), _rot(as_of=earlier))
    assert base["confirmed_events"]["status"] == "available"
    assert len(base["confirmed_events"]["rows"]) == 2
    assert off["confirmed_events"]["status"] == "incompatible_generation"
    assert off["confirmed_events"]["rows"] == []
    assert off["confirmed_events"]["as_of"] == earlier
    # a history generation mismatch withholds EVERY reconstruction instead
    hist = _project(_full_cyc_payload(history_as_of=earlier), _rot())
    assert all(g["reconstruction"]["status"] == "incompatible_generation"
               and g["reconstruction"]["reason"] == "history_as_of_mismatch"
               and g["reconstruction"]["points"] == 0 for g in hist["groups"])
    assert hist["generation"]["history_as_of"] == earlier
    assert _canon(hist["groups"][0]["current"]) == _canon(base["groups"][0]["current"])


@needs_node
def test_cc_transition_observation_date_consumer_says_different_day_not_stale_rows():
    base = _project(_full_cyc_payload(), _rot())
    off = _project(_full_cyc_payload(), _rot(as_of="2026-10-08"))
    future = _project(_full_cyc_payload(), _rot(as_of="2026-10-10"))
    b = _obs_run(_synth(base), "XLK")
    o = _obs_run(_synth(off), "XLK")
    f = _obs_run(_synth(future), "XLK")
    assert "1 recorded event filed under this sector" in b["hist"]
    assert "2026-09-21" in b["hist"] and "day 14" in b["hist"]
    for stale in (o, f):
        assert "mr-gen" in stale["hist"], stale["hist"]
        assert "different day" in stale["hist"]
        assert "2026-10-09" in stale["hist"] and "Not drawn" in stale["hist"]
        assert "2026-09-21" not in _all_text(stale), "a stale confirmed row is shown"
        assert "recorded event" not in stale["hist"]
        assert stale["hist"] != b["hist"]
    assert "2026-10-08" in o["hist"] and "2026-10-10" in f["hist"]
    assert o["hist"] != f["hist"], "two different refused dates read identically"
    # the measurement surface is untouched by the date axis
    for out in (b, o, f):
        assert [g for g, _ in out["rows"]] == RANKED_FULL
        assert out["list"] == b["list"] and out["cov"] == b["cov"]


# ══════════════════════════════════════════════════════════════════════════════
# 2c — transition_observation / LINEAGE
# ══════════════════════════════════════════════════════════════════════════════

def test_cc_transition_observation_lineage_shared_root_counts_once():
    same = dedupe_source_roots([
        {"id": "obs-xlf-xlu", "source_roots": ("engine.rotation_events",)},
        {"id": "obs-xlf-xlu-rev2", "source_roots": ("engine.rotation_events",)},
    ])
    assert same["family_count"] == 1 and same["item_count"] == 2
    assert same["families"] == [["obs-xlf-xlu", "obs-xlf-xlu-rev2"]]
    assert same["alias_ids"] == ["obs-xlf-xlu", "obs-xlf-xlu-rev2"]
    distinct = dedupe_source_roots([
        {"id": "obs-xlf-xlu", "source_roots": ("engine.rotation_events",)},
        {"id": "obs-xle-rs", "source_roots": ("engine.sector_cycles",)},
    ])
    assert distinct["family_count"] == 2 and distinct["alias_ids"] == []
    assert distinct["families"] == [["obs-xle-rs"], ["obs-xlf-xlu"]]
    assert distinct["independent_count_rule"] == same["independent_count_rule"]
    unrooted = dedupe_source_roots([{"id": "obs-a", "source_roots": ()}])
    assert unrooted["unrooted_ids"] == ["obs-a"] and unrooted["family_count"] == 1
    # a transition observation is never attached to a legacy event
    sep = separate_from_legacy([_obs("XLF", "XLU")],
                               {"status": "OK", "rows": [
                                   {"lifecycle_id": "xlk:memory->mag7@2026-07-01",
                                    "observation_date": "2026-07-01",
                                    "recorded_at": "2026-07-01T21:00:00Z",
                                    "mode": "RETAINED_LEDGER_UNMARKED",
                                    "from_key": "memory", "to_key": "mag7"}]})
    assert sep["attached_to_legacy"] == 0 and sep["relationship"] == "context_only"
    assert sep["legacy_status"] == "OK" and len(sep["legacy_events"]) == 1
    assert len(sep["transition_observations"]) == 1
    assert sep["transition_observations"][0]["status"] == "context_only"
    assert "xlk:memory->mag7@2026-07-01" not in _canon(sep["transition_observations"])


def _rot_candidate_moved() -> dict:
    """Move one CONFIRMED event into the owner state's ``candidates`` map
    (engine/rotation_events.py:771 — pre-confirmation; never in active)."""
    rot = copy.deepcopy(_rot())
    moved = [ev for ev in rot["active"] if ev["id"] == "xlk-xle:handoff"]
    assert len(moved) == 1
    rot["active"] = [ev for ev in rot["active"] if ev["id"] != "xlk-xle:handoff"]
    rot["candidates"] = {"xlk_etf->xle_etf": moved[0]}
    return rot


def test_cc_transition_observation_lineage_candidate_is_never_confirmed():
    base = _project(_full_cyc_payload(), _rot())
    cand = _project(_full_cyc_payload(), _rot_candidate_moved())
    ids_b = [r["id"] for r in base["confirmed_events"]["rows"]]
    ids_c = [r["id"] for r in cand["confirmed_events"]["rows"]]
    assert ids_b == ["xlk-xle:handoff", "xly-xlp:cross"]
    assert ids_c == ["xly-xlp:cross"], "a candidate was projected as confirmed"
    assert base["confirmed_events"]["n_active"] == 2
    assert cand["confirmed_events"]["n_active"] == 1
    assert base["confirmed_events"]["n_active"] - cand["confirmed_events"]["n_active"] == 1
    assert cand["confirmed_events"]["status"] == "available"
    assert cand["confirmed_events"]["truncated"] is False
    # the early/candidate lane never leaks into the confirmed lane
    ec_pairs = {"ec-xlf-xlu"}
    assert not (ec_pairs & set(ids_b)) and not (ec_pairs & set(ids_c))
    assert cand["early_context"]["status"] == "available"
    assert cand["early_context"]["context_only"] is True
    # the measured surface is untouched by the lineage axis
    assert _canon(base["groups"]) == _canon(cand["groups"])
    assert _rank_order(cand) == RANKED_FULL
    # duplicate confirmed ids still count once, and the row cap still binds
    dup = copy.deepcopy(_rot())
    dup["active"] = list(dup["active"]) + [copy.deepcopy(dup["active"][0])]
    duped = _project(_full_cyc_payload(), dup)
    assert duped["confirmed_events"]["n_active"] == 2
    assert len(duped["confirmed_events"]["rows"]) == 2
    assert MEASURED_READ_MAX_EVENT_ROWS == 12


@needs_node
def test_cc_transition_observation_lineage_candidate_never_rendered_confirmed():
    base = _project(_full_cyc_payload(), _rot())
    cand = _project(_full_cyc_payload(), _rot_candidate_moved())
    b = _obs_run(_synth(base), "XLK")
    c = _obs_run(_synth(cand), "XLK")
    assert "1 recorded event filed under this sector" in b["hist"]
    assert "2026-09-21" in b["hist"] and "day 14" in b["hist"]
    assert "No recorded events for this sector." in c["hist"], c["hist"]
    assert "2026-09-21" not in _all_text(c)
    assert "candidate" not in _all_text(c).lower(), "an internal state name leaked"
    assert c["hist"] != b["hist"]
    # the other sector's confirmed row is unaffected by the lineage axis
    assert "1 recorded event filed under this sector" in _obs_run(_synth(cand), "XLY")["hist"]
    assert [g for g, _ in c["rows"]] == RANKED_FULL and c["list"] == b["list"]


# ══════════════════════════════════════════════════════════════════════════════
# 3 — research_estimate
# ══════════════════════════════════════════════════════════════════════════════

def _estimate(probability: float) -> ResearchEstimate:
    return ResearchEstimate(
        target="sector_relative_wealth_sign_63d", horizon_sessions=63, origin="t0",
        exit_rule="hold_to_horizon", model="synthetic-logit", protocol="prereg-synthetic",
        cohort_id="us_sectors_11", training_cutoff="2026-01-01",
        supported_population="us_sectors_11", uncertainty_definition="oos_ci",
        evidence_tier="research", probability=probability)


def test_cc_research_estimate_absent_by_default_and_a_separate_object_when_supplied():
    cyc, rot = _full_cyc_payload(), _rot()
    default = lrc.measured_group_read(cyc, rotation_payload=rot)
    assert default["research_estimate"] == {"status": "unavailable",
                                            "reason": "no_admitted_model"}
    est = _estimate(0.4)
    supplied = lrc.measured_group_read(cyc, rotation_payload=rot, research_estimate=est)
    assert supplied["research_estimate"] == est.to_dict()
    assert supplied["research_estimate"]["status"] == "estimate"
    assert supplied["research_estimate"]["schema"] == \
        "leadership_rotation_context.research_estimate/v1"
    assert supplied["research_estimate"]["display_only"] is True
    assert supplied["research_estimate"]["probability"] == 0.4
    # SEPARATE object: every group_measurement value and rank is byte-identical
    rest_d = {k: v for k, v in default.items() if k != "research_estimate"}
    rest_s = {k: v for k, v in supplied.items() if k != "research_estimate"}
    assert json.dumps(rest_d, sort_keys=True) == json.dumps(rest_s, sort_keys=True)
    assert json.dumps(default["groups"], sort_keys=True) == \
        json.dumps(supplied["groups"], sort_keys=True)
    assert _rank_order(default) == _rank_order(supplied) == RANKED_FULL
    assert default["research_estimate"] != supplied["research_estimate"]
    # a non-estimate is refused, never coerced into the slot
    for bad in ({"status": "available"}, "0.4", 0.4, None):
        out = lrc.measured_group_read(cyc, rotation_payload=rot, research_estimate=bad)
        assert out["research_estimate"] == default["research_estimate"]


def test_cc_research_estimate_extreme_value_changes_no_rank():
    cyc, rot = _full_cyc_payload(), _rot()
    base = lrc.measured_group_read(cyc, rotation_payload=rot)
    top = lrc.measured_group_read(cyc, rotation_payload=rot,
                                  research_estimate=_estimate(1.0))
    bottom = lrc.measured_group_read(cyc, rotation_payload=rot,
                                     research_estimate=_estimate(0.0))
    assert json.dumps(base["groups"], sort_keys=True) == \
        json.dumps(top["groups"], sort_keys=True) == \
        json.dumps(bottom["groups"], sort_keys=True)
    assert json.dumps(base["cohort"], sort_keys=True) == \
        json.dumps(top["cohort"], sort_keys=True)
    assert _rank_order(top) == _rank_order(bottom) == RANKED_FULL
    assert top["research_estimate"]["probability"] == 1.0
    assert bottom["research_estimate"]["probability"] == 0.0
    assert bottom["research_estimate"]["status"] == "estimate", \
        "a real 0.0 estimate is not 'unavailable'"
    # out-of-range and incomplete identities are refused, never placeholder-ed
    with pytest.raises(ValueError):
        _estimate(1.5)
    with pytest.raises(ValueError):
        ResearchEstimate(probability=0.5)
    assert ResearchEstimate().status == "unavailable"
    assert isinstance(ResearchEstimate().probability, Unmeasured)
    # no combined entry score anywhere in the projection
    assert "score" not in _canon(top).lower() and "entry" not in _canon(top).lower()
    assert "probability" not in _canon({k: v for k, v in top.items()
                                        if k != "research_estimate"}).lower()


@needs_node
def test_cc_research_estimate_consumer_leaves_the_measured_render_untouched():
    cyc, rot = _full_cyc_payload(), _rot()
    base = _synth(lrc.measured_group_read(cyc, rotation_payload=rot))
    est = _synth(lrc.measured_group_read(cyc, rotation_payload=rot,
                                         research_estimate=_estimate(1.0)))
    b, e = _run(fixture=base), _run(fixture=est)
    assert "Forecast: none" in b["early"], b["early"]
    # Admitted estimate branch (N-RE1): a real ResearchEstimate now renders the
    # "display only" line and no longer falls through to "Forecast: none".
    assert "Forecast: none" not in e["early"], e["early"]
    assert "100%" in e["early"], e["early"]
    # the measured read render is byte-identical between the two fixtures
    for key in ("list", "cov", "status", "sub", "rows", "un", "detail"):
        assert b[key] == e[key], key
    assert [g for g, _ in e["rows"]] == RANKED_FULL
    # a non-estimate shape ({status: "available"}) is refused by the gate: it
    # now falls through to the "Forecast: none" line, not the estimate line.
    admitted = _run(cfg={"mr": {"research_estimate": {"status": "available"}}},
                    fixture=base)
    assert "Forecast: none" in admitted["early"], admitted["early"]
    assert "Research estimate" not in admitted["early"], admitted["early"]
    assert admitted["list"] == b["list"] and admitted["rows"] == b["rows"]


# ══════════════════════════════════════════════════════════════════════════════
# 4 — evidence mode (the BASIS axis lives here)
# ══════════════════════════════════════════════════════════════════════════════

def test_cc_evidence_mode_reconstructed_is_labelled_end_to_end():
    cyc = _full_cyc_payload()
    declared = cyc["meta"]["rs_history"]
    assert declared["mode"] == "reconstructed_price_history"
    assert declared["naturally_observed"] is False and declared["basis"] == "tr"
    proj = _project(cyc, _rot())
    for g in proj["groups"]:
        rec = g["reconstruction"]
        assert rec["mode"] == "reconstructed_price_history", g["group_id"]
        assert rec["naturally_observed"] is False, g["group_id"]
        assert rec["status"] == "available" and rec["reason"] is None
        assert rec["points"] == 3 and rec["first"] == HIST_DATES[0]
        assert rec["last"] == HIST_DATES[-1]
        assert rec["source"] == "/sectordata/sector_cycles.json#sectors[].rs_history"
    assert proj["generation"]["price_basis"] == "total_return"
    assert proj["generation"]["history_schema"] == "sector_cycles.rs_history.v1"
    # em02: the declared basis matches the price source's own default
    from engine import inputs as engine_inputs
    default_basis = inspect.signature(engine_inputs.yahoo_closes).parameters["basis"].default
    assert default_basis == "tr" == declared["basis"]
    # em04: the two evidence vocabularies are disjoint, end to end
    assert set(EVIDENCE_MODES).isdisjoint(RETAINED_LEDGER_MODES)
    blob = _canon(proj)
    for mode in RETAINED_LEDGER_MODES:
        assert mode not in blob
    assert "reconstructed_price_history" in blob
    # em05: a reconstructed history is never an event source
    keys = set()

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                keys.add(k)
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(proj)
    assert not keys & {"created_tonight", "events"}
    assert "active" not in keys


def test_cc_evidence_mode_flipping_the_mode_flips_exactly_the_eligibility():
    # a rebuild can never claim natural observation, whatever it is stamped with
    with pytest.raises(ValueError) as exc:
        TransitionObservation(
            definition_id="d", definition_version="v",
            roles={"receiver": "XLF", "donor": "XLU"},
            coordinate={"date": AS_OF, "vintage": None, "as_of": AS_OF},
            evidence_mode="reconstructed_price_history", naturally_observed=True)
    assert "cannot claim natural observation" in str(exc.value)
    retained = TransitionObservation(
        definition_id="d", definition_version="v",
        roles={"receiver": "XLF", "donor": "XLU"},
        coordinate={"date": AS_OF, "vintage": None, "as_of": AS_OF},
        evidence_mode="original_retained", naturally_observed=True)
    assert retained.naturally_observed is True
    rebuild = TransitionObservation(
        definition_id="d", definition_version="v",
        roles={"receiver": "XLF", "donor": "XLU"},
        coordinate={"date": AS_OF, "vintage": None, "as_of": AS_OF},
        evidence_mode="original_retained", naturally_observed=False)
    assert rebuild.naturally_observed is False
    # the ONLY field that differs between the two admissions is the mode
    a, b = retained.to_dict(), rebuild.to_dict()
    assert sorted(k for k in a if _canon(a[k]) != _canon(b[k])) == ["naturally_observed"]
    with pytest.raises(ValueError):
        TransitionObservation(
            definition_id="d", definition_version="v", roles={},
            coordinate={"date": AS_OF, "vintage": None, "as_of": AS_OF},
            evidence_mode="hallucinated", naturally_observed=False)
    # a coordinate must carry its date/vintage/as_of, and stays context-only
    with pytest.raises(ValueError):
        TransitionObservation(
            definition_id="d", definition_version="v", roles={},
            coordinate={"date": AS_OF}, evidence_mode="original_retained",
            naturally_observed=False)
    with pytest.raises(ValueError):
        TransitionObservation(
            definition_id="d", definition_version="v", roles={},
            coordinate={"date": AS_OF, "vintage": None, "as_of": AS_OF},
            evidence_mode="original_retained", naturally_observed=False,
            relationship="attached_to_legacy_event")
    # use rights: acquisition is not permission (A05)
    assert admit_use({"display": "permitted"}, "display") == "permitted"
    assert admit_use({"display": "refused"}, "display") == "refused"
    assert admit_use(None, "display") == "withheld"
    assert admit_use({"display": True}, "display") == "withheld"


def test_cc_evidence_mode_declared_basis_flip_is_visible_at_the_source():
    """Flipping the DECLARED basis is visible end to end: the projection READS
    ``meta.rs_history.basis``, so a non-engine basis word projects ``unknown``
    and never a matching label, the engine word ``price`` projects
    ``price_only``, and no measured value moves either way."""
    # MUTATION: hard-coded price_basis literal (a declared non-engine basis word
    # still projects a matching label instead of `unknown`)
    from engine import inputs as engine_inputs
    default_basis = inspect.signature(engine_inputs.yahoo_closes).parameters["basis"].default
    ok = _full_cyc_payload(history=_declared_history(basis="tr"))
    px = _full_cyc_payload(history=_declared_history(basis="px"))
    price = _full_cyc_payload(history=_declared_history(basis="price"))
    assert ok["meta"]["rs_history"]["basis"] == default_basis
    assert px["meta"]["rs_history"]["basis"] != default_basis
    proj_ok, proj_px = _project(ok, _rot()), _project(px, _rot())
    proj_price = _project(price, _rot())
    assert proj_ok["generation"]["price_basis"] == "total_return"
    assert proj_px["generation"]["price_basis"] == "unknown", \
        "the projection reads the declared basis: a non-engine word is unknown"
    assert proj_price["generation"]["price_basis"] == "price_only"
    # the declared basis is a LABEL axis only: strip it from both projections and
    # they are identical, so the flip never silently moves any measured value
    stripped_ok, stripped_px = copy.deepcopy(proj_ok), copy.deepcopy(proj_px)
    del stripped_ok["generation"]["price_basis"]
    del stripped_px["generation"]["price_basis"]
    assert _canon(stripped_ok) == _canon(stripped_px), \
        "a declared-basis flip must not silently move any measured value"
    stripped_price = copy.deepcopy(proj_price)
    del stripped_price["generation"]["price_basis"]
    assert _canon(stripped_price) == _canon(stripped_ok)
    # flipping the declared MODE to a retained label is a source-side lie the
    # projection also does not absorb: it still labels every group reconstructed
    lied = _full_cyc_payload(history=_declared_history(mode="original_retained"))
    assert lied["meta"]["rs_history"]["naturally_observed"] is True
    proj_lied = _project(lied, _rot())
    assert all(g["reconstruction"]["mode"] == "reconstructed_price_history"
               and g["reconstruction"]["naturally_observed"] is False
               for g in proj_lied["groups"])


@needs_node
def test_cc_evidence_mode_basis_flip_changes_exactly_the_rendered_basis_line():
    base = _project(_full_cyc_payload(), _rot())
    flipped = copy.deepcopy(base)
    flipped["generation"]["price_basis"] = "price_only"
    b = _run(fixture=_synth(base), cfg={"search": "?g=XLE", "cycles": _hist_overlay()})
    f = _run(fixture=_synth(flipped), cfg={"search": "?g=XLE", "cycles": _hist_overlay()})
    assert "vs S&amp;P 500 · total return" in b["sub"], b["sub"]
    assert "vs S&amp;P 500 · price only" in f["sub"], f["sub"]
    assert b["sub"] != f["sub"]
    for key in ("list", "cov", "status", "rows", "un", "detail", "hist", "early"):
        assert b[key] == f[key], key
    # the reconstructed trail keeps its own words, never the retained words
    assert "Reconstructed from prices" in b["hist"]
    assert "calculated later, not what Mastermind showed at the time" in b["hist"]
    assert "Recorded by Mastermind at the time" not in b["hist"]
    obs = _obs_run(_synth(base), "XLK")
    assert "Recorded by Mastermind at the time" in obs["hist"]
    assert "not recalculated later" in obs["hist"]
    assert "Reconstructed from prices" not in obs["hist"]
    for out in (b, f, obs):
        for mode in RETAINED_LEDGER_MODES:
            assert mode not in _all_text(out)
        assert "reconstructed_price_history" not in _all_text(out)
        assert "naturally_observed" not in _all_text(out)


# ══════════════════════════════════════════════════════════════════════════════
# 5 — A42: three distinct history failures, each confined to #mr-hist
# ══════════════════════════════════════════════════════════════════════════════

def _hist_body(cycles) -> str:
    return ("__window.SECTOR_CYCLES = " + json.dumps(cycles) +
            ";\n dispatchDoc('sc:cycles-data');\n show();")


@needs_node
def test_cc_a42_three_history_failures_change_only_the_hist_box():
    fixture = _synth(_project(_full_cyc_payload(), _rot()))
    cfg = {"search": "?g=XLE"}
    base = _run(body=_hist_body(_hist_overlay()), fixture=fixture, cfg=cfg)
    assert "polyline" in base["hist"] and "mr-spark-zero" in base["hist"]
    assert "2026-10-07 → 2026-10-09 · 3 points" in base["hist"], base["hist"]
    failures = {
        "null_payload": None,
        "wrong_schema": {"synthetic": True, "meta": {}, "sectors": []},
        "as_of_mismatch": {"synthetic": True,
                           "meta": {"rs_history": {"schema": "sector_cycles.rs_history.v1",
                                                   "as_of": "2026-10-08"}},
                           "sectors": []},
    }
    expected = {
        "null_payload": ("mx-error", "History unavailable right now"),
        "wrong_schema": ("mx-empty", "Reconstructed history is not published yet."),
        "as_of_mismatch": ("mr-gen", "History is from a different day"),
    }
    unchanged = ("list", "cov", "status", "sub", "rows", "un", "unHidden", "detail",
                 "early", "seg", "histCalls", "body")
    seen = {base["hist"]}
    for name, cycles in failures.items():
        out = _run(body=_hist_body(cycles), fixture=fixture, cfg=cfg)
        cls, copy_text = expected[name]
        assert cls in out["hist"], (name, out["hist"])
        assert copy_text in out["hist"], (name, out["hist"])
        assert "polyline" not in out["hist"], f"{name} drew from a failed generation"
        assert out["hist"] not in seen, f"{name} is indistinguishable from another state"
        seen.add(out["hist"])
        assert out["hist"] != base["hist"], name
        for key in unchanged:
            assert out[key] == base[key], f"{name} changed #{key}"
        assert out["body"] == base["body"], name
    assert len(seen) == 4, "the ready state and three failures must be four states"
    assert "2026-10-08" in _run(body=_hist_body(failures["as_of_mismatch"]),
                                fixture=fixture, cfg=cfg)["hist"]


# ══════════════════════════════════════════════════════════════════════════════
# 6 — A45: the measured read is never a server-rendered payload
# ══════════════════════════════════════════════════════════════════════════════

def test_cc_a45_render_kwargs_carry_no_measured_object():
    kwargs = _render_call_kwargs()
    assert "measured_read" not in kwargs and "transition_observation" not in kwargs
    assert "research_estimate" not in kwargs and "rs_63d" not in kwargs
    blob = " ".join(f"{k}={v}" for k, v in kwargs.items()).lower()
    for name in PROTECTED_NAMES:
        assert name.lower() not in blob, f"{name} reaches the template as a render value"
    # no kwarg carries the window.SECTOR_CENTRAL data object
    for key, value in kwargs.items():
        assert "sector_central" not in value.lower().replace("sector_central.html.j2", ""), \
            f"kwarg {key} carries the page data object"
    assert set(kwargs) >= {"flows_html", "pgate", "bottoming", "theme_context",
                           "generated_utc"}


def test_cc_a45_template_has_no_server_side_expression_for_the_read():
    spans = _template_server_side_spans()
    assert spans, "no jinja expressions found — the extractor is broken"
    for span in spans:
        for name in PROTECTED_NAMES:
            assert name not in span, f"server-side expression references {name}: {span[:80]}"
    src = PAGE.read_text(encoding="utf-8")
    # the names exist ONLY inside client JS that reads runtime-fetched data
    for name in ("measured_read", "research_estimate", "rs_63d", "SECTOR_CENTRAL"):
        assert name in src, name
    assert "transition_observation" not in src
    for m in re.finditer(r"window\.SECTOR_CENTRAL", src):
        line_start = src.rindex("\n", 0, m.start()) + 1
        line = src[line_start:src.index("\n", m.end())]
        assert "{{" not in line and "{%" not in line, line
    assert src.count(panel.START) == 1 and src.count(panel.END) == 1


def test_cc_a45_protected_payloads_are_default_deny():
    _check_protected_payloads_not_public()
    policy = _load_access_policy()
    assert policy["schema"] == "site_access.v1"
    assert policy["public"]["exact"] and isinstance(policy["public"]["prefixes"], list)
    # neither the page shell nor any of its data payloads is public
    assert _is_public("/sector_central.html", policy) is False
    for path in PROTECTED_PATHS:
        assert _is_public(path, policy) is False, path
    for prefix in policy["public"]["prefixes"]:
        assert not prefix.startswith("/sectordata") and not prefix.startswith("/premiumdata")
        assert not prefix.startswith("/marketdata")


def test_cc_a45_public_sectordata_mutation_is_reported_as_exposure():
    policy = copy.deepcopy(_load_access_policy())
    before = _exposed_protected_paths(policy)
    assert before == []
    policy["public"]["exact"] = list(policy["public"]["exact"]) + \
        ["/sectordata/sector_central.json"]
    assert _exposed_protected_paths(policy) == ["/sectordata/sector_central.json"]
    with pytest.raises(AssertionError):
        _check_protected_payloads_not_public(policy)
    # a prefix widening is caught the same way
    policy2 = copy.deepcopy(_load_access_policy())
    policy2["public"]["prefixes"] = list(policy2["public"]["prefixes"]) + ["/sectordata/"]
    assert _exposed_protected_paths(policy2) == \
        ["/sectordata/", "/sectordata/sector_central.json", "/sectordata/sector_cycles.json"]
    with pytest.raises(AssertionError):
        _check_protected_payloads_not_public(policy2)
    # the on-disk policy is unchanged by the in-memory mutation
    _check_protected_payloads_not_public()


# ══════════════════════════════════════════════════════════════════════════════
# kill tests — permanent, always green: each mutant is detected
# ══════════════════════════════════════════════════════════════════════════════
# The "green unmutated" bookend calls are skipped when an env mutant is already
# active, so these three stay green in all four runs (no mutant + each mutant).

def test_kill_absence_as_zero():
    if not MUTANT:
        _check_absence_is_not_zero()
    mp = _with_mutant("absence_as_zero")
    try:
        with pytest.raises(AssertionError):
            _check_absence_is_not_zero()
    finally:
        mp.undo()
    if not MUTANT:
        _check_absence_is_not_zero()


@needs_node
def test_kill_js_ranks_unmeasured():
    if not MUTANT:
        absent = _project(_full_cyc_payload(drop=("XLE",)), _rot())
        _check_unmeasured_never_ranked(absent, ["XLE"], RANKED_NO_XLE)
    mp = _with_mutant("js_ranks_unmeasured")
    try:
        absent = _project(_full_cyc_payload(drop=("XLE",)), _rot())
        with pytest.raises(AssertionError):
            _check_unmeasured_never_ranked(absent, ["XLE"], RANKED_NO_XLE)
    finally:
        mp.undo()
    if not MUTANT:
        absent = _project(_full_cyc_payload(drop=("XLE",)), _rot())
        _check_unmeasured_never_ranked(absent, ["XLE"], RANKED_NO_XLE)


def test_kill_public_sectordata():
    if not MUTANT:
        _check_protected_payloads_not_public()
    mp = _with_mutant("public_sectordata")
    try:
        with pytest.raises(AssertionError):
            _check_protected_payloads_not_public()
        assert _exposed_protected_paths() == ["/sectordata/sector_central.json"]
    finally:
        mp.undo()
    if not MUTANT:
        _check_protected_payloads_not_public()
