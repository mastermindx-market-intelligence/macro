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
    columns ``REVISED_COLUMNS`` plus ``liquidity`` (the overlay slot the
    liquidity_quality layer expects on the row).
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
    """The default producer map (F6). Tests inject their own."""
    if os.environ.get("REGIME_OUTLOOK_REPLAY_FAKE_FRAME") == "1":
        return _fake_producers()
    from engine.rate_inflation_transmission import (
        current_state, breakeven_decomposition,
    )
    from engine.yield_curve import regime as yield_curve_regime
    from engine.yield_momentum import build_yield_momentum
    from engine.conditions import conditions_snapshot
    from engine.regime import liquidity_quality
    from engine.market_state import _comp_breadth
    return {
        "current_state": current_state,
        "breakeven_decomposition": breakeven_decomposition,
        "yield_curve_regime": yield_curve_regime,
        "build_yield_momentum": build_yield_momentum,
        "conditions_snapshot": conditions_snapshot,
        "liquidity_quality": liquidity_quality,
        "comp_breadth": _comp_breadth,
    }


def _fake_producers() -> dict[str, Callable]:
    """Synthetic producers used by the CLI under the FAKE_FRAME env var."""
    def _state(f, **_):
        return {
            "inflation_direction": "cooling",
            "inflation_regime": "disinflating",
            "expectations_anchoring": "anchored",
            "rates_direction": "falling",
            "rates_regime": "easing",
        }
    def _bd(f, **_):
        return {"direction": "compressing", "trend": "compressing"}
    def _yc(f, **_):
        return {"regime": {"term_premium_dir": "rising"}}
    def _ym(f, **_):
        return {"series": {
            "2y": {"turn_watch": "off"},
            "5y": {"turn_watch": "off"},
            "10y": {"turn_watch": "off"},
            "20y": {"turn_watch": "off"},
            "30y": {"turn_watch": "off"},
        }}
    def _cs(f, **_):
        return {
            "labor_nowcast": {"read": "mixed"},
            "financial_conditions": {"state": "loose"},
            "complacency": {"breadth_div": False},
        }
    def _lq(f, **_):
        return {"label": "neutral", "stress_overlay": {"confirming_stress": False}}
    def _cb(payload, **_):
        return {"tone": "broadening"}
    return {
        "current_state": _state,
        "breakeven_decomposition": _bd,
        "yield_curve_regime": _yc,
        "build_yield_momentum": _ym,
        "conditions_snapshot": _cs,
        "liquidity_quality": _lq,
        "comp_breadth": _cb,
    }


_UNAVAILABLE_REASONS: dict[str, str] = {
    "L": "no_point_in_time_membership_and_no_as_of_seam",
    "B": "rate_futures_history_starts_2026_03_16",
    "D": "producer_not_pinned",
    "C": "producer_not_pinned",
}

_LABOR_SINGLE_VOTE_DATES = {"2018-10-31", "2019-08-30"}


def _set_path(doc: dict, path: list[str], value: Any) -> None:
    """Set a nested path in a synthetic artifact doc, creating dicts as needed."""
    cursor = doc
    for part in path[:-1]:
        nxt = cursor.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[part] = nxt
        cursor = nxt
    cursor[path[-1]] = value


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


def reconstruct_letters(
    frame: pd.DataFrame,
    d: str,
    *,
    producers: dict[str, Callable] | None = None,
) -> tuple[dict[str, bytes | None], dict[str, dict[str, Any]]]:
    """Reconstruct the seven owner artifacts at date ``d``.

    Returns ``(input_bytes, coverage)``.

    ``input_bytes[letter]`` is the JSON-encoded doc for T/R/M and ``None`` for
    L/B/D/C (the producers for those letters are not pinned).

    ``coverage[letter]`` lists every mapping field whose artifact is that letter
    with one of: ``produced``, ``not_produced:<reason>``,
    ``unavailable:single_vote``, ``partial:2_of_3_votes``. Per-letter status is
    ``reconstructed`` if the producer ran OR ``unavailable`` if it raised.
    """
    from engine.rates_command_outlook import load_mapping

    mapping = load_mapping()
    if producers is None:
        producers = _real_producers()

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

    # ---- T: current_state + breakeven_decomposition + yield_curve + yield_momentum ----
    t_doc: dict[str, Any] = {"asof": d}
    t_fields: dict[str, str] = {}
    try:
        cs = producers["current_state"](frame) or {}
        _set_path(t_doc, ["state", "inflation", "direction"], cs.get("inflation_direction"))
        _set_path(t_doc, ["state", "inflation", "regime"], cs.get("inflation_regime"))
        _set_path(t_doc, ["state", "expectations", "anchoring"], cs.get("expectations_anchoring"))
        _set_path(t_doc, ["state", "rates", "direction"], cs.get("rates_direction"))
        _set_path(t_doc, ["state", "rates", "regime"], cs.get("rates_regime"))
        for f in _fields_for_letter(mapping, "T"):
            if f["path"][0] == "state" and len(f["path"]) >= 2:
                t_fields[f["field_id"]] = "produced"

        bd = producers["breakeven_decomposition"](frame) or {}
        _set_path(t_doc, ["breakeven_decomp", "direction"], bd.get("direction"))
        _set_path(t_doc, ["breakeven_decomp", "trend"], bd.get("trend"))
        for f in _fields_for_letter(mapping, "T"):
            if f["path"][0] == "breakeven_decomp":
                t_fields[f["field_id"]] = "produced"

        yc = producers["yield_curve_regime"](frame) or {}
        _set_path(t_doc, ["yield_curve", "regime", "term_premium_dir"],
                  (yc.get("regime") or {}).get("term_premium_dir"))
        for f in _fields_for_letter(mapping, "T"):
            if f["path"][0] == "yield_curve":
                t_fields[f["field_id"]] = "produced"

        # Strip rate_observations origin evidence before computing (F6). It was
        # captured into frame.attrs from the FULL history at engine/inputs.py:175
        # and the docs only want the post-cut reading.
        if "rate_observations" in frame.attrs:
            del frame.attrs["rate_observations"]
        ym = producers["build_yield_momentum"](frame) or {}
        series = ym.get("series") or {}
        for tenor in ("2y", "5y", "10y", "20y", "30y"):
            s = series.get(tenor) or {}
            _set_path(t_doc, ["yield_momentum", "series", tenor, "turn_watch"],
                      s.get("turn_watch"))
        for f in _fields_for_letter(mapping, "T"):
            if f["path"][0] == "yield_momentum":
                t_fields[f["field_id"]] = "produced"

        for f in _fields_for_letter(mapping, "T"):
            t_fields.setdefault(f["field_id"], "not_produced:producer_not_pinned")
        input_bytes["T"] = json.dumps(t_doc, ensure_ascii=False).encode()
        coverage["T"] = {"status": "reconstructed", "reason": None, "fields": t_fields}
    except Exception as exc:  # noqa: BLE001
        reason = f"producer_error:{type(exc).__name__}"
        for f in _fields_for_letter(mapping, "T"):
            t_fields[f["field_id"]] = f"not_produced:{reason}"
        coverage["T"] = {
            "status": "unavailable", "reason": reason, "fields": t_fields,
        }

    # ---- R: liquidity_quality + conditions_snapshot ----
    r_doc: dict[str, Any] = {"asof": d}
    r_fields: dict[str, str] = {}
    try:
        # Mirror engine/run.py:316-328 exactly (F6): we row from a dict that
        # carries the overlay under the key "liquidity" (the latest.json shape
        # regime produces); the replay proxy operates at runtime, so we use the
        # LAST row of the cut frame as the overlay string-equivalent.
        last_row = frame.iloc[-1] if len(frame) else None
        overlay = None
        if last_row is not None and "liquidity" in frame.columns:
            overlay = last_row.get("liquidity")
        lq = producers["liquidity_quality"](
            frame, overlay=overlay, asof=pd.Timestamp(d),
        ) or {}
        _set_path(r_doc, ["liquidity_quality", "label"], lq.get("label"))
        # stress_overlay is best-effort; absence noted but not fatal
        so = lq.get("stress_overlay") or {}
        if "confirming_stress" in so:
            _set_path(
                r_doc,
                ["liquidity_quality", "stress_overlay", "confirming_stress"],
                so.get("confirming_stress"),
            )
            for f in _fields_for_letter(mapping, "R"):
                if (f["path"][0] == "liquidity_quality"
                        and len(f["path"]) >= 3
                        and f["path"][2] == "stress_overlay"):
                    r_fields[f["field_id"]] = "produced"
        else:
            for f in _fields_for_letter(mapping, "R"):
                if (f["path"][0] == "liquidity_quality"
                        and len(f["path"]) >= 3
                        and f["path"][2] == "stress_overlay"):
                    r_fields[f["field_id"]] = "not_produced:producer_not_pinned"

        for f in _fields_for_letter(mapping, "R"):
            if f["path"] == ["liquidity_quality", "label"]:
                r_fields[f["field_id"]] = "produced"

        cs = producers["conditions_snapshot"](frame) or {}
        _set_path(r_doc, ["conditions", "financial_conditions", "state"],
                  (cs.get("financial_conditions") or {}).get("state"))
        _set_path(r_doc, ["conditions", "complacency", "breadth_div"],
                  (cs.get("complacency") or {}).get("breadth_div"))
        labor_nowcast = (cs.get("labor_nowcast") or {}).get("read")
        _set_path(r_doc, ["conditions", "labor_nowcast", "read"], labor_nowcast)

        # F7: labour read at 2018/2019 is forced mixed -> mark unavailable; at
        # 2022 dates two votes exist -> mark partial:2_of_3_votes but keep value.
        for f in _fields_for_letter(mapping, "R"):
            if f["path"] == ["conditions", "labor_nowcast", "read"]:
                if d in _LABOR_SINGLE_VOTE_DATES:
                    _del_path(r_doc, ["conditions", "labor_nowcast", "read"])
                    r_fields[f["field_id"]] = "unavailable:single_vote"
                else:
                    r_fields[f["field_id"]] = "partial:2_of_3_votes"
            elif f["path"][:2] == ["conditions", "financial_conditions"]:
                r_fields[f["field_id"]] = "produced"
            elif f["path"][:2] == ["conditions", "complacency"]:
                r_fields[f["field_id"]] = "produced"

        for f in _fields_for_letter(mapping, "R"):
            r_fields.setdefault(f["field_id"], "not_produced:producer_not_pinned")
        input_bytes["R"] = json.dumps(r_doc, ensure_ascii=False).encode()
        coverage["R"] = {"status": "reconstructed", "reason": None, "fields": r_fields}
    except Exception as exc:  # noqa: BLE001
        reason = f"producer_error:{type(exc).__name__}"
        for f in _fields_for_letter(mapping, "R"):
            r_fields[f["field_id"]] = f"not_produced:{reason}"
        coverage["R"] = {
            "status": "unavailable", "reason": reason, "fields": r_fields,
        }

    # ---- M: market_state._comp_breadth keyed off R.conditions ----
    m_doc: dict[str, Any] = {"asof": d}
    m_fields: dict[str, str] = {}
    try:
        r_conditions = (r_doc.get("conditions") or {}) if r_doc else {}
        breadth = producers["comp_breadth"]({"conditions": r_conditions}) or {}
        _set_path(m_doc, ["components", "breadth", "tone"], breadth.get("tone"))
        for f in _fields_for_letter(mapping, "M"):
            m_fields[f["field_id"]] = "produced"
        for f in _fields_for_letter(mapping, "M"):
            m_fields.setdefault(f["field_id"], "not_produced:producer_not_pinned")
        input_bytes["M"] = json.dumps(m_doc, ensure_ascii=False).encode()
        coverage["M"] = {"status": "reconstructed", "reason": None, "fields": m_fields}
    except Exception as exc:  # noqa: BLE001
        reason = f"producer_error:{type(exc).__name__}"
        for f in _fields_for_letter(mapping, "M"):
            m_fields[f["field_id"]] = f"not_produced:{reason}"
        coverage["M"] = {
            "status": "unavailable", "reason": reason, "fields": m_fields,
        }

    return input_bytes, coverage


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
                        help="Path to write the labelled JSON. Required unless --dry-run.")
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
    forbidden_roots = ("data", "site", "config")
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