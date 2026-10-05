"""Regime-outlook coverage replay for the four closed SH-12 dates.

Slice E1r of the state-path-and-science contract (rule R-I, seen-history row
SH-12). Reconstructs the seven owner artifacts at four closed dates from today's
stored frames truncated to each date, runs the mapping's path readings on them,
and writes ONE labelled JSON.

The output is a hindsight reconstruction on revised data. It is NOT
point-in-time and NOT evidence of skill. It exists to surface wording / guard /
provenance holes before any change is proposed (R-I; the rule may never be used
to make a path fit an episode, to choose between paths, or as support for a
claim on the page).

Owned by E1r; the seat runs this on a host that holds ``data/``/``site/``. Tests
exercise the pure path with synthetic frames and injected producers.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

# Paths to the source files this tool mirrors. Quoted verbatim from the live
# call shape in `engine/run.py` (lib ~316-328) so reviewers can audit the line.
LIQUIDITY_QUALITY_CALL = (
    "from engine.regime import liquidity_quality; "
    "liquidity_quality(f, overlay=row['liquidity'], asof=asof)"
)

# Real column names verified in engine/inputs.py; cited lines are the exact
# source lines that introduce each column into the frame.
REVISED_COLUMNS: tuple[str, ...] = (
    "nfci",             # engine/inputs.py:320
    "anfci",            # engine/inputs.py:320
    "infl_exp_5y",      # engine/inputs.py:389
    "indeed_postings",  # engine/inputs.py:420 (FRED IHLIDXUS)
    "pct_above_200",    # engine/inputs.py:459
    "net_liquidity_bn", # engine/inputs.py:451
    "zq_front",         # engine/inputs.py:247
)

REPLAY_DATES: tuple[str, ...] = (
    "2018-10-31",
    "2019-08-30",
    "2022-06-30",
    "2022-10-31",
)
LABEL = (
    "hindsight reconstruction on revised data; not point-in-time; "
    "not evidence of skill"
)
TRUNCATION_RULE = (
    "frame = engine.inputs.build_features(pit_basis='release', "
    "pit_as_of=d).loc[:d]; last index must be <= d; producers read the last row"
)
RULE_ID = "R-I"
SEEN_HISTORY_ROW = "SH-12"
SCHEMA_VERSION = "regime_outlook_replay.v1"
# Contract §E1 row E1r: "its output is committed beside the mapping" — the
# mapping is config/regime_outlook_mapping_v2.json, so the replay lands here.
OUTPUT_PATH = "config/regime_outlook_replay_v2_sh12.json"
# R-I: "Fields with no stored history are reported `unknown: insufficient_history`,
# not approximated." Each per-field reading carries one of these classes beside
# the composer's own status so the committed file explains every non-available
# row on its face.
HISTORY_LEGEND: dict[str, str] = {
    "read": "owner produced a non-null leaf at the date; the composer read it",
    "owner_null": "owner produced its guarded null for the leaf at the date "
                  "(the composer reads it as missing/owner_default_on_missing)",
    "partial_history": "owner read from a reduced source set at the date "
                       "(labour: 2 of 3 votes; Indeed IHLIDXUS begins 2020-02)",
    "insufficient_history": "no stored history for the owner's sources at the "
                            "date (labour: <=1 of 3 votes); read withheld, "
                            "never approximated",
    "not_in_replay": "letter outside the R-I replay (L/B/D/C) or field not "
                     "assembled by the replay",
    "producer_error": "owner decision function raised at the date",
}


# ---------------------------------------------------------------------------
# Frame construction
# ---------------------------------------------------------------------------

def build_frame(d: str, *, build_features: Callable | None = None) -> pd.DataFrame:
    """Build a frame truncated to date ``d`` with the PIT router on.

    Raises ``ValueError`` if the resulting frame is empty or whose last row
    still sits past ``d``. Clears ``frame.attrs`` and stores what was cleared
    under key ``cleared_attrs`` so the audit trail survives a downstream
    consumer (yield_momentum strips ORIGIN_ATTR before computing, but the
    capture happens before any cut — see engine/inputs.py:175).
    """
    if build_features is None:
        if os.environ.get("REGIME_OUTLOOK_REPLAY_FAKE_FRAME") == "1":
            build_features = _fake_build_features
        else:
            from engine.inputs import build_features as _bf
            build_features = _bf

    frame = build_features(pit_basis="release", pit_as_of=d)
    if frame is None or len(frame) == 0:
        raise ValueError(f"build_features returned an empty frame for {d}")

    cleared_attrs = dict(frame.attrs) if frame.attrs else {}

    cut = frame.loc[:pd.Timestamp(d)]
    if len(cut) == 0:
        raise ValueError(f"frame is empty after cut to {d}")
    if cut.index[-1] > pd.Timestamp(d):
        raise ValueError(
            f"frame last index {cut.index[-1]} is past the cut date {d}"
        )

    # .loc slicing produces a fresh frame with attrs reset; rebind explicitly
    # so the audit trail survives downstream use (yield_momentum strips
    # ORIGIN_ATTR before computing, but the capture happened before any cut
    # — see engine/inputs.py:175).
    cut.attrs = {"cleared_attrs": cleared_attrs}
    return cut


def _fake_build_features(*, pit_basis=None, pit_as_of=None, **_) -> pd.DataFrame:
    """Synthetic stand-in for ``engine.inputs.build_features`` used only when
    the test harness sets ``REGIME_OUTLOOK_REPLAY_FAKE_FRAME=1``. Mirrors the
    columns ``REVISED_COLUMNS`` (plus a ``liquidity`` column kept only for
    frame-shape parity; the overlay is produced by the ``liquidity_overlay``
    producer, never read from the frame).
    """
    d = pd.Timestamp(pit_as_of)
    idx = pd.bdate_range(d - pd.tseries.offsets.BDay(30),
                         d + pd.tseries.offsets.BDay(60))
    f = pd.DataFrame(index=idx)
    f["nfci"] = 0.0
    f["anfci"] = 0.0
    f["infl_exp_5y"] = 2.0
    f["indeed_postings"] = 100.0
    f["pct_above_200"] = 0.5
    f["net_liquidity_bn"] = 100.0
    f["zq_front"] = 95.0
    f["liquidity"] = "expanding"
    return f


def frame_digest(frame: pd.DataFrame) -> dict[str, Any]:
    """Byte-deterministic digest of a frame for the audit trail."""
    h = pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    import hashlib
    sha = hashlib.sha256(h).hexdigest()
    return {
        "sha256": sha,
        "rows": int(len(frame)),
        "cols": int(frame.shape[1]),
        "first": frame.index[0].isoformat(),
        "last": frame.index[-1].isoformat(),
    }


# ---------------------------------------------------------------------------
# Letter reconstruction
# ---------------------------------------------------------------------------

def _real_producers() -> dict[str, Callable]:
    """The default producer map (F6). Tests inject their own.

    Each producer is the SAME decision function the nightly calls, and the
    letter docs below are assembled the way the nightly assembles them, with
    the producer's WHOLE dict in place (never a hand-picked leaf): the
    mapping's clocks (``T.asof``, ``breakeven_decomp.as_of``,
    ``yield_momentum.series.<t>.as_of``, ``conditions.vintages.*``) and guards
    (``default_token_needs``, ``turn_watch_null``, ``credit_stress_leg``,
    ``component_not_degraded``) read SIBLING fields of the verdict leaf, so a
    leaf-only reconstruction reads as ``unknown`` on every row even when the
    producer has a reading (measured 2026-10-04, first replay run: 4 dates x
    all paths ``unknown``).
    """
    if os.environ.get("REGIME_OUTLOOK_REPLAY_FAKE_FRAME") == "1":
        return _fake_producers()
    from engine.rate_inflation_transmission import (
        current_state, breakeven_decomposition,
    )
    from engine.yield_curve import regime as yield_curve_regime
    from engine.yield_momentum import build_yield_momentum
    from engine.conditions import conditions_snapshot
    from engine.regime import liquidity_quality, liquidity_overlay
    from engine.market_state import _comp_breadth

    def _overlay_last(frame: pd.DataFrame):
        # engine/run.py:316-318 passes overlay=row["liquidity"], where row is
        # the regime frame built by engine/regime.py classify() (:294 sets
        # out["liquidity"] = liquidity_overlay(f)). The overlay is NOT a
        # column of the features frame; reading it from there yields None and
        # liquidity_quality then labels "unknown" (the first-run defect).
        s = liquidity_overlay(frame)
        if s is None or len(s) == 0:
            return None
        v = s.iloc[-1]
        return None if (v is None or (isinstance(v, float) and pd.isna(v))) else v

    return {
        "current_state": current_state,
        "breakeven_decomposition": breakeven_decomposition,
        "yield_curve_regime": yield_curve_regime,
        "build_yield_momentum": build_yield_momentum,
        "conditions_snapshot": conditions_snapshot,
        "liquidity_overlay": _overlay_last,
        "liquidity_quality": liquidity_quality,
        "comp_breadth": _comp_breadth,
    }


_TENORS: tuple[str, ...] = ("2y", "5y", "10y", "20y", "30y")


def _fake_producers() -> dict[str, Callable]:
    """Synthetic producers used by the CLI under the FAKE_FRAME env var.

    Shapes mirror the real producers' return dicts (the owner artifacts the
    golden fixture ``tests/fixtures/regime_outlook/readings_golden_v2.json``
    pins), including the sibling fields the mapping's clocks and guards need.
    """
    def _asof(f) -> str:
        return f.index[-1].date().isoformat()

    def _state(f, **_):
        return {
            "inflation": {
                "direction": "cooling", "regime": "above target",
                "core_pce_3m_ann": 2.05, "core_pce_yoy": 3.01,
            },
            "expectations": {"anchoring": "anchored", "market_minus_model_bp": -23.0},
            "rates": {
                "direction": "rising", "regime": "restrictive",
                "real_10y_chg_63d_bp": 58.0, "real_10y_pctile": 1.0,
            },
        }

    def _bd(f, **_):
        return {
            "as_of": _asof(f), "direction": "flat", "trend": "uptrend",
            "velocity_bp": {"chg_20d_bp": 1.0},
        }

    def _yc(f, **_):
        # engine/yield_curve.py regime() returns a FLAT dict; the nightly nests
        # it under yield_curve.regime (engine/yield_curve.py snapshot()).
        return {"key": "bear_steepener", "term_premium_dir": "rising"}

    def _ym(f, **_):
        a = _asof(f)
        return {"series": {
            t: {
                "status": "available", "as_of": a, "path_qualified": True,
                "velocity_bp": {"22d": 39.0}, "turn_watch": None,
            }
            for t in _TENORS
        }}

    def _cs(f, **_):
        a = _asof(f)
        return {
            "vintages": {
                "nfci": {"asof": a, "stale": False},
                "pct_above_200": {"asof": a, "stale": False},
            },
            "labor_nowcast": {
                "read": "labor firm", "claims_yoy_pct": -11.0,
                "indeed_chg_3m_pct": 2.3, "withheld_tax_yoy_pct": 5.0,
            },
            "financial_conditions": {"state": "loose"},
            "complacency": {
                "breadth_div": False, "spy_high_prox": 0.01,
                "breadth_above200_pctile": 0.62,
            },
        }

    def _lo(f, **_):
        return "expanding"

    def _lq(f, overlay=None, asof=None, **_):
        return {
            "asof": _asof(f),
            # Tokens from the mapping's vocabulary (engine/regime.py labels).
            "label": "benign-expansion" if overlay == "expanding" else "unknown",
            "stress_overlay": {
                "confirming_stress": False, "hy_oas_z": 0.4, "nfci": -0.5,
            },
        }

    def _cb(payload, **_):
        # market_state._tone_from_score emits good / warn / bad.
        return {"key": "breadth", "tone": "good", "degraded": False}

    return {
        "current_state": _state,
        "breakeven_decomposition": _bd,
        "yield_curve_regime": _yc,
        "build_yield_momentum": _ym,
        "conditions_snapshot": _cs,
        "liquidity_overlay": _lo,
        "liquidity_quality": _lq,
        "comp_breadth": _cb,
    }


_UNAVAILABLE_REASONS: dict[str, str] = {
    "L": "no_point_in_time_membership_and_no_as_of_seam",
    "B": "rate_futures_history_starts_2026_03_16",
    "D": "producer_not_pinned",
    "C": "producer_not_pinned",
}

# F7: the labour read is a 3-vote composite (claims yoy / Indeed postings 3m /
# withheld tax yoy; engine/conditions.py labor_nowcast). Indeed's FRED series
# (IHLIDXUS) starts 2020-02, so the 2018/2019 dates are expected to carry a
# single vote and the 2022 dates two; the replay MEASURES the vote count from
# the producer's own dict rather than asserting it by date.
_LABOR_VOTE_KEYS: tuple[str, ...] = (
    "claims_yoy_pct", "indeed_chg_3m_pct", "withheld_tax_yoy_pct",
)
_LABOR_READ_PATH: list[str] = ["conditions", "labor_nowcast", "read"]


def _leaf(doc: Any, path: list[Any]) -> Any:
    """Resolve a mapping path against a doc the way the composer reads it.

    String segments index dicts; a dict segment ``{"key": "breadth"}`` selects
    the element of a LIST whose ``key`` equals ``"breadth"``. Returns ``None``
    when any step is absent (so a producer's explicit ``null`` and an absent
    container both resolve to ``None`` here; the coverage mark distinguishes
    them by whether the producer ran).
    """
    cursor = doc
    for seg in path:
        if isinstance(seg, dict):
            if not isinstance(cursor, list):
                return None
            k, v = next(iter(seg.items()))
            cursor = next(
                (e for e in cursor if isinstance(e, dict) and e.get(k) == v), None,
            )
        elif isinstance(cursor, dict):
            cursor = cursor.get(seg)
        else:
            return None
        if cursor is None:
            return None
    return cursor


def _del_path(doc: dict, path: list[str]) -> None:
    """Remove a nested path if present. Walks defensively."""
    cursor = doc
    for part in path[:-1]:
        if not isinstance(cursor, dict) or part not in cursor:
            return
        cursor = cursor[part]
    if isinstance(cursor, dict):
        cursor.pop(path[-1], None)


def _fields_for_letter(mapping: dict[str, Any], letter: str) -> list[dict[str, Any]]:
    return [f for f in mapping["fields"] if f["artifact"] == letter]


def _mark_leaves(
    doc: dict[str, Any],
    fields: list[dict[str, Any]],
    marks: dict[str, str],
) -> None:
    """Mark every field not already marked: ``produced`` when its leaf resolves
    to a non-null value at the mapping path, else ``produced_null`` (the
    producer ran; the mapping's guard decides what the null means)."""
    for f in fields:
        if f["field_id"] in marks:
            continue
        marks[f["field_id"]] = (
            "produced" if _leaf(doc, f["path"]) is not None else "produced_null"
        )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def reconstruct_letters(
    frame: pd.DataFrame,
    d: str,
    *,
    producers: dict[str, Callable] | None = None,
) -> tuple[dict[str, bytes | None], dict[str, dict[str, Any]]]:
    """Reconstruct the seven owner artifacts at date ``d``.

    Returns ``(input_bytes, coverage)``.

    ``input_bytes[letter]`` is the JSON-encoded doc for T/R/M and ``None`` for
    L/B/D/C (the producers for those letters are not pinned). T/R/M carry the
    producers' whole dicts under the keys the nightly uses
    (``engine/run.py`` ``latest[...]`` / ``market_state_snapshot``), so every
    sibling the mapping's clocks and guards name is present when the producer
    emits it. ``asof`` is the cut frame's last index date (the nightly's
    convention), which is ``<= d``.

    ``coverage[letter]`` lists every mapping field whose artifact is that letter
    with one of: ``produced`` (leaf non-null at the mapping path),
    ``produced_null`` (producer ran, leaf null — the guard rules),
    ``not_produced:<reason>``, ``unavailable:single_vote`` /
    ``unavailable:no_votes`` (labour read dropped), ``partial:2_of_3_votes``. Per-letter status is ``reconstructed`` if the
    producers ran OR ``unavailable`` if one raised.
    """
    from engine.rates_command_outlook import load_mapping

    mapping = load_mapping()
    if producers is None:
        producers = _real_producers()

    asof = frame.index[-1].date().isoformat() if len(frame) else d
    asof_ts = frame.index[-1] if len(frame) else pd.Timestamp(d)

    input_bytes: dict[str, bytes | None] = {L: None for L in "TRMLBDC"}
    coverage: dict[str, dict[str, Any]] = {}

    # ---- L, B, D, C: never reconstructed (F5). ----
    for letter in "LBDC":
        coverage[letter] = {
            "status": "unavailable",
            "reason": _UNAVAILABLE_REASONS[letter],
            "fields": {
                f["field_id"]: f"not_produced:{_UNAVAILABLE_REASONS[letter]}"
                for f in _fields_for_letter(mapping, letter)
            },
        }

    # ---- T: state + breakeven_decomp + yield_curve.regime + yield_momentum ----
    # Assembled as the transmission owner assembles its artifact: whole dicts
    # under the artifact's keys; yield_curve nests regime() under "regime"
    # exactly as engine/yield_curve.py snapshot() does.
    t_doc: dict[str, Any] = {"asof": asof}
    t_fields: dict[str, str] = {}
    try:
        t_doc["state"] = _as_dict(producers["current_state"](frame))
        t_doc["breakeven_decomp"] = _as_dict(producers["breakeven_decomposition"](frame))
        t_doc["yield_curve"] = {
            "asof": asof,
            "regime": _as_dict(producers["yield_curve_regime"](frame)),
        }
        # Strip rate_observations origin evidence before computing (F6). It was
        # captured into frame.attrs from the FULL history at engine/inputs.py:175
        # and the docs only want the post-cut reading.
        if "rate_observations" in frame.attrs:
            del frame.attrs["rate_observations"]
        t_doc["yield_momentum"] = _as_dict(producers["build_yield_momentum"](frame))
        _mark_leaves(t_doc, _fields_for_letter(mapping, "T"), t_fields)
        input_bytes["T"] = json.dumps(t_doc, ensure_ascii=False, default=str).encode()
        coverage["T"] = {"status": "reconstructed", "reason": None, "fields": t_fields}
    except Exception as exc:  # noqa: BLE001
        reason = f"producer_error:{type(exc).__name__}"
        t_fields = {
            f["field_id"]: f"not_produced:{reason}"
            for f in _fields_for_letter(mapping, "T")
        }
        coverage["T"] = {
            "status": "unavailable", "reason": reason, "fields": t_fields,
        }

    # ---- R: liquidity_quality + conditions_snapshot ----
    r_doc: dict[str, Any] = {"asof": asof}
    r_fields: dict[str, str] = {}
    labor_votes: int | None = None
    try:
        overlay = producers["liquidity_overlay"](frame)
        r_doc["liquidity_quality"] = _as_dict(producers["liquidity_quality"](
            frame, overlay=overlay, asof=asof_ts,
        ))
        r_doc["liquidity_overlay"] = overlay
        r_doc["conditions"] = _as_dict(producers["conditions_snapshot"](frame))

        # F7: the labour read is only as good as its votes. One vote -> the
        # read is dropped and marked unavailable; two -> kept, marked partial;
        # three -> produced.
        labor = _as_dict(r_doc["conditions"].get("labor_nowcast"))
        labor_votes = sum(1 for k in _LABOR_VOTE_KEYS if labor.get(k) is not None)
        for f in _fields_for_letter(mapping, "R"):
            if f["path"] == _LABOR_READ_PATH:
                if labor_votes <= 1:
                    _del_path(r_doc, _LABOR_READ_PATH)
                    r_fields[f["field_id"]] = (
                        "unavailable:single_vote" if labor_votes == 1
                        else "unavailable:no_votes"
                    )
                elif labor_votes == 2:
                    r_fields[f["field_id"]] = "partial:2_of_3_votes"
        _mark_leaves(r_doc, _fields_for_letter(mapping, "R"), r_fields)
        input_bytes["R"] = json.dumps(r_doc, ensure_ascii=False, default=str).encode()
        coverage["R"] = {
            "status": "reconstructed", "reason": None, "fields": r_fields,
            "labor_votes": labor_votes,
        }
    except Exception as exc:  # noqa: BLE001
        reason = f"producer_error:{type(exc).__name__}"
        r_fields = {
            f["field_id"]: f"not_produced:{reason}"
            for f in _fields_for_letter(mapping, "R")
        }
        coverage["R"] = {
            "status": "unavailable", "reason": reason, "fields": r_fields,
            "labor_votes": labor_votes,
        }

    # ---- M: market_state._comp_breadth keyed off R.conditions ----
    # market_state_snapshot emits components as a LIST of component dicts
    # (each with key/tone/degraded) and input_vintages from
    # latest["conditions"]["vintages"] (engine/market_state.py:1140,1185).
    m_doc: dict[str, Any] = {"asof": asof}
    m_fields: dict[str, str] = {}
    try:
        conditions = _as_dict(r_doc.get("conditions"))
        component = producers["comp_breadth"]({"conditions": conditions})
        m_doc["components"] = [component] if isinstance(component, dict) else []
        m_doc["input_vintages"] = conditions.get("vintages")
        if not isinstance(component, dict):
            for f in _fields_for_letter(mapping, "M"):
                m_fields[f["field_id"]] = "not_produced:owner_returned_none"
        _mark_leaves(m_doc, _fields_for_letter(mapping, "M"), m_fields)
        input_bytes["M"] = json.dumps(m_doc, ensure_ascii=False, default=str).encode()
        coverage["M"] = {"status": "reconstructed", "reason": None, "fields": m_fields}
    except Exception as exc:  # noqa: BLE001
        reason = f"producer_error:{type(exc).__name__}"
        m_fields = {
            f["field_id"]: f"not_produced:{reason}"
            for f in _fields_for_letter(mapping, "M")
        }
        coverage["M"] = {
            "status": "unavailable", "reason": reason, "fields": m_fields,
        }

    return input_bytes, coverage


def _history_class(mark: str | None) -> str:
    """Map a replay coverage mark onto the contract's history vocabulary."""
    if mark is None:
        return "not_in_replay"
    if mark == "produced":
        return "read"
    if mark == "produced_null":
        return "owner_null"
    if mark.startswith("partial:"):
        return "partial_history"
    if mark.startswith("unavailable:"):
        return "insufficient_history"
    if "producer_error" in mark:
        return "producer_error"
    if mark.startswith("not_produced:") and "history" in mark:
        # e.g. B: rate_futures_history_starts_2026_03_16 — no stored history
        return "insufficient_history"
    return "not_in_replay"


def _field_readings(
    mapping: dict[str, Any],
    coverage: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One row per mapping field: composer status beside the replay mark."""
    marks: dict[str, str] = {}
    for letter in coverage.values():
        if isinstance(letter, dict):
            marks.update(letter.get("fields") or {})
    by_id = {r.get("id"): r for r in evidence}
    rows: list[dict[str, Any]] = []
    for field in mapping.get("fields", []):
        fid = field.get("field_id")
        r = by_id.get(fid)
        mark = marks.get(fid)
        rows.append({
            "id": fid,
            "status": r.get("status") if r else None,
            "issues": list(r.get("issues") or []) if r else [],
            "values": r.get("values") if r else None,
            "replay_mark": mark,
            "history": _history_class(mark),
        })
    return rows


# ---------------------------------------------------------------------------
# Replay driver
# ---------------------------------------------------------------------------

def replay(
    mapping: dict[str, Any],
    *,
    mapping_sha256: str,
    dates: tuple[str, ...] = REPLAY_DATES,
    build_frame_fn: Callable | None = None,
    producers: dict[str, Callable] | None = None,
) -> dict[str, Any]:
    """Run the four-date coverage replay and return the labelled JSON dict."""
    from engine.rates_command_outlook import load_mapping
    from engine.rates_command_outlook_compose import (
        read_inputs, evidence_rows, outlook_paths, state_families,
    )

    if mapping is None:
        mapping = load_mapping()

    if build_frame_fn is None:
        build_frame_fn = build_frame

    per_date: list[dict[str, Any]] = []
    for d in dates:
        frame = build_frame_fn(d)
        digest = frame_digest(frame)
        input_bytes, coverage = reconstruct_letters(
            frame, d, producers=producers,
        )
        docs, record = read_inputs(mapping, input_bytes)
        cutoff = datetime(
            int(d[:4]), int(d[5:7]), int(d[8:10]), 23, 59,
            tzinfo=timezone.utc,
        )
        evidence = evidence_rows(
            mapping, docs, record,
            analysis_cutoff=cutoff, us_session=date(int(d[:4]), int(d[5:7]), int(d[8:10])),
        )
        sfs = state_families(mapping, evidence)
        cards = outlook_paths(mapping, docs, evidence)
        avail = miss = unk = 0
        for r in evidence:
            st = r.get("status")
            if st == "available":
                avail += 1
            elif st == "missing":
                miss += 1
            else:
                unk += 1
        per_date.append({
            "date": d,
            "frame": digest,
            "letters": coverage,
            "state_families": sfs,
            "paths": cards,
            "readings": _field_readings(mapping, coverage, evidence),
            "evidence_summary": {
                "available": avail, "missing": miss, "unknown": unk,
            },
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "label": LABEL,
        "rule": RULE_ID,
        "seen_history_row": SEEN_HISTORY_ROW,
        "mapping_version": mapping.get("mapping_version"),
        "mapping_sha256": mapping_sha256,
        "truncation_rule": TRUNCATION_RULE,
        "revised_columns_caveat": list(REVISED_COLUMNS),
        "output_path": OUTPUT_PATH,
        "history_legend": dict(HISTORY_LEGEND),
        "dates": list(dates),
        "per_date": per_date,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _atomic_write(path: Path, payload: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


def _print_coverage(out: dict[str, Any]) -> None:
    lines = ["date | T | R | M | L | B | D | C | paths | avail/miss/unknown"]
    for row in out["per_date"]:
        letters = row["letters"]
        st = {L: letters[L]["status"] for L in "TRMLBDC"}
        es = row["evidence_summary"]
        lines.append(
            f"{row['date']} | {st['T']} | {st['R']} | {st['M']} | "
            f"{st['L']} | {st['B']} | {st['D']} | {st['C']} | "
            f"{len(row['paths'])} | "
            f"{es['available']}/{es['missing']}/{es['unknown']}"
        )
    print("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="regime_outlook_replay",
        description=(
            "Regime-outlook coverage replay for the four closed SH-12 dates "
            "(contract rule R-I, slice E1r)."
        ),
    )
    parser.add_argument("--out", required=False, default=None,
                        help="Path to write the labelled JSON. Required unless "
                             f"--dry-run. The committed copy lives at {OUTPUT_PATH}.")
    parser.add_argument("--data-dir", default=None,
                        help="Override the data root; honored only if lib.config "
                             "reads MACRO_DATA_DIR (it does not — see notes).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the coverage table; write nothing.")
    args = parser.parse_args(argv)

    if args.data_dir:
        # lib/config.data_dir() resolves via config["storage"]["data_dir"]
        # (lib/config.py:35-36). The config file path is ROOT / "config/config.yml"
        # and is NOT keyed off MACRO_DATA_DIR, so we record the override and let
        # the operator know it is informational.
        print(
            "::notice title=regime-outlook-replay-data-dir-override::"
            f"--data-dir={args.data_dir} is informational; lib/config.data_dir() "
            "reads config['storage']['data_dir'] from config/config.yml and does "
            "not honor MACRO_DATA_DIR. Edit config.yml to override.",
            flush=True,
        )

    if args.dry_run:
        from engine.rates_command_outlook import load_mapping, mapping_sha256
        mapping = load_mapping()
        out = replay(mapping, mapping_sha256=mapping_sha256())
        _print_coverage(out)
        return 0

    if not args.out:
        print(
            "::error title=regime-outlook-replay-args::--out is required "
            "(or pass --dry-run).",
            flush=True,
        )
        return 2

    out_path = Path(args.out).resolve()
    # data/ and site/ are engine stores and never hold a hand-run artifact.
    # config/ is NOT refused: the contract (E1 row E1r) commits this output
    # beside the mapping, i.e. OUTPUT_PATH.
    forbidden_roots = ("data", "site")
    parts = out_path.parts
    for root in forbidden_roots:
        if root in parts and parts.index(root) >= len(parts) - 3:
            print(
                "::error title=regime-outlook-replay-out-forbidden::"
                f"--out {out_path} lives under {root}/ which is reserved "
                "for engine stores; refused per R-I output contract.",
                flush=True,
            )
            return 2

    try:
        from engine.rates_command_outlook import load_mapping, mapping_sha256
        mapping = load_mapping()
        out = replay(mapping, mapping_sha256=mapping_sha256())
        payload = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
        _atomic_write(out_path, payload)
    except Exception as exc:  # noqa: BLE001
        print(
            f"::error title=regime-outlook-replay-failed::"
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())