"""CCW issuer credit/equity comparison, v1; descriptive, never a risk forecast.

Consumes the existing matched-change series. It neither prices a second bond
universe nor invents CDS. Missing sessions, peers and timestamps stay visible.
No network or writes occur in compile_snapshot().
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from io import BytesIO
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from lib.nyse_calendar import is_session, session_n_back, sessions_between
from engine.corp_credit import (
    INSTRUMENT_HISTORY_BASIS, INSTRUMENT_HISTORY_POPULATION,
    INSTRUMENT_HISTORY_SCHEMA, parse_instrument_history,
)

SCHEMA = "corp_credit.dislocation.v1"
METHOD = "matched-change-coarse-peer/1.0"
AUTHORITY = {"rank": False, "size": False, "gate": False, "escalate": False}
MIN_PEERS = 3
MAX_AGE_SESSIONS = 3
WIDENING_BP = 15.0  # descriptive 5-session candidate, NOT empirically calibrated
EQUITY_WEAK_PCT = -2.0
LIMITATIONS = [
    "Fund-held bonds are a sample, not total issuer debt.",
    "G-spread estimates are not CDS, OAS or executable prices.",
    "Registry issuer is an economic-parent proxy; legal obligor not yet resolved.",
    "Peers match fund grade and maturity bucket, not full rating/liquidity/seniority.",
    "Five-session windows require every common equity session; bond holidays may abstain.",
    "Source publication vintages are unqualified unless separately established.",
    "Descriptive comparison only; no default or equity-loss probability.",
]


def _number(value: Any) -> float | None:
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def identifier(value: Any) -> dict:
    """Type and checksum the native identifier; never manufacture an ISIN."""
    text = value.strip().upper() if isinstance(value, str) and value.isascii() else ""
    valid = False
    kind = "unknown"
    if len(text) == 9 and text[-1:].isdigit():
        kind = "cusip"
        try:
            values = [int(c) if c.isdigit() else ord(c) - 55 if c.isalpha()
                      else {"*": 36, "@": 37, "#": 38}[c] for c in text[:8]]
            total = sum(sum(map(int, str(v * (1 + i % 2)))) for i, v in enumerate(values))
            valid = (10 - total % 10) % 10 == int(text[-1])
        except (KeyError, ValueError):
            pass
    elif len(text) == 12 and text[:2].isalpha() and text[2:].isalnum() and text[-1].isdigit():
        kind = "isin"
        digits = "".join(c if c.isdigit() else str(ord(c) - 55) for c in text)
        total = 0
        for i, c in enumerate(reversed(digits)):
            n = int(c) * (2 if i % 2 else 1)
            total += n // 10 + n % 10
        valid = total % 10 == 0
    return {"value": text, "kind": kind, "checksum_valid": valid,
            "key": f"{kind}:{text}" if valid else None}


def _frame(frame: pd.DataFrame, required: set[str], label: str, cutoff: date) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    absent = required - set(frame)
    if absent:
        raise ValueError(f"{label}: missing columns {','.join(sorted(absent))}")
    out = frame.copy()
    parsed = pd.to_datetime(out["as_of"], errors="coerce", utc=True)
    out["as_of"] = parsed.dt.date
    out = out[out["as_of"].notna() & (out["as_of"] <= cutoff)]
    # An observed system/publication clock may narrow a view; never backdate it.
    if "available_at" in out:
        available = pd.to_datetime(out["available_at"], errors="coerce", utc=True)
        out = out[available.notna() & (available.dt.date <= cutoff)]
    return out


def _unique(frame: pd.DataFrame, keys: list[str], label: str) -> pd.DataFrame:
    """Exact duplicates can collapse; conflicting same-key records cannot win by order."""
    out = frame.drop_duplicates()
    if out.duplicated(keys).any():
        raise ValueError(f"{label}: conflicting duplicate observation")
    return out


def _window(frame: pd.DataFrame, end: date, horizon: int) -> dict:
    start = session_n_back(end, horizon)
    if start is None or frame.empty:
        return {"value_bp": None, "reason": "insufficient_history"}
    expected = sessions_between(start, end)
    expected = [d for d in expected if d > start]
    if len(expected) != horizon:
        return {"value_bp": None, "reason": "calendar_unavailable"}
    observed = set(frame["as_of"])
    missing = [d.isoformat() for d in [start, *expected] if d not in observed]
    if missing:
        return {"value_bp": None, "reason": "missing_session_or_matched_change",
                "start": start.isoformat(), "end": end.isoformat(),
                "missing_sessions": missing, "expected_sessions": horizon}
    window = frame.set_index("as_of").reindex(expected)
    delta = pd.to_numeric(window["d1_g_spread_bp_matched"], errors="coerce")
    matched = pd.to_numeric(window["matched_n"], errors="coerce")
    if delta.isna().any() or not all(math.isfinite(float(v)) for v in delta):
        return {"value_bp": None, "reason": "missing_session_or_matched_change"}
    if (matched.isna() | (matched < 1)).any():
        return {"value_bp": None, "reason": "no_matched_instruments"}
    return {"value_bp": round(float(delta.sum()), 6), "reason": None,
            "start": start.isoformat(), "end": end.isoformat(),
            "sessions": horizon, "min_matched_bonds": int(matched.min())}


def _equity_return(series: pd.Series | None, end: date, horizon: int) -> dict:
    start = session_n_back(end, horizon)
    result = {"value_pct": None, "reason": "equity_unavailable",
              "basis": "source_close_return_not_certified_total_return"}
    if series is None or series.empty or start is None:
        return result
    s = series.copy()
    parsed = pd.to_datetime(s.index, errors="coerce", utc=True)
    s.index = parsed.date
    s = s[[isinstance(d, date) and start <= d <= end for d in s.index]]
    if s.index.duplicated().any():
        result["reason"] = "conflicting_equity_dates"
        return result
    expected = sessions_between(start, end)
    s = pd.to_numeric(s.reindex(expected), errors="coerce")
    if len(expected) != horizon + 1 or s.isna().any() or (s <= 0).any():
        result.update(reason="missing_equity_sessions", start=start.isoformat(), end=end.isoformat(),
                      missing_sessions=[d.isoformat() for d in expected if pd.isna(s.loc[d])],
                      expected_sessions=horizon + 1)
        return result
    if not all(math.isfinite(float(v)) for v in s):
        result["reason"] = "invalid_equity_values"
        return result
    if (s.pct_change().abs().dropna() > 0.30).any():
        result["reason"] = "corporate_action_or_extreme_move_needs_review"
        return result
    result.update(value_pct=round(float((s.iloc[-1] / s.iloc[0] - 1) * 100), 6), reason=None)
    return result


def _registry(registry: dict) -> dict:
    mapping = {}
    for theme, values in registry.get("themes", {}).items():
        for issuer, meta in values.get("issuers", {}).items():
            if issuer in mapping:
                raise ValueError("registry: issuer appears in multiple theme definitions")
            mapping[issuer] = {"theme": theme, "equity_ticker": meta.get("equity_ticker"),
                               "tier": meta.get("tier")}
    return mapping


def _maturity_bucket(value: Any) -> str | None:
    value = _number(value)
    if value is None or value <= 0:
        return None
    return "short" if value <= 3 else "intermediate" if value <= 10 else "long"


def _state(change: float | None, equity: float | None, *, stale: bool,
           absolute_change: float | None) -> str:
    if stale:
        return "historical_only"
    if change is None or equity is None or absolute_change is None:
        return "insufficient_evidence"
    # Underperforming peers while one's own spread narrows is not widening.
    # The inverse is equally important: relative resilience is not recovery.
    if change >= WIDENING_BP and absolute_change >= WIDENING_BP:
        return "credit_widening_equity_steadier" if equity > EQUITY_WEAK_PCT else "joint_deterioration"
    if change <= -WIDENING_BP and absolute_change <= -WIDENING_BP:
        return "credit_improving_equity_weaker" if equity <= EQUITY_WEAK_PCT else "joint_improvement"
    if abs(change) >= WIDENING_BP:
        return "relative_gap_only"
    return "no_large_relative_change"



def _instrument_window(records: list[dict], end: date, horizon: int) -> dict:
    if not records:
        return {"value_bp": None, "reason": "insufficient_history"}
    frame = pd.DataFrame(records)
    frame["as_of"] = frame["as_of"].map(date.fromisoformat)
    result = _window(frame, end, horizon)
    if result["value_bp"] is None:
        return result
    start = date.fromisoformat(result["start"])
    selected = [row for row in records if start <= date.fromisoformat(row["as_of"]) <= end]
    latest = selected[-1]
    reason = None
    if any(not row["terms_consistent"] for row in selected):
        reason = "history_terms_conflict"
    elif any(row["currency_status"] == "conflict" for row in selected):
        reason = "history_currency_conflict"
    elif any(row["currency_status"] != "observed" for row in selected):
        reason = "history_currency_unknown"
    elif any(row["currency"] != "USD" for row in selected):
        reason = "history_currency_unsupported"
    elif any(row["coupon"] is None or row["maturity"] is None for row in selected):
        reason = "history_terms_missing"
    elif any((row["coupon"], row["maturity"]) != (latest["coupon"], latest["maturity"])
             for row in selected):
        reason = "history_terms_changed"
    return {"value_bp": None, "reason": reason} if reason else result


def _instrument_history(bond: pd.Series, end: date) -> tuple[dict, bool]:
    summary = {
        "schema": INSTRUMENT_HISTORY_SCHEMA,
        "population": INSTRUMENT_HISTORY_POPULATION,
        "valuation_basis": INSTRUMENT_HISTORY_BASIS,
        "status": "unavailable", "reason": "history_unavailable",
        "observations": 0, "first_seen": None, "observed_from": None,
        "observed_through": None, "currency": None, "cmt_as_of": None,
        "calculation_convention": None,
        "historical_publication_qualified": False,
        "independent_historical_pricing_qualified": False,
        "change_5": {"value_bp": None, "reason": "history_unavailable"},
        "change_21": {"value_bp": None, "reason": "history_unavailable"},
    }
    try:
        history = parse_instrument_history(
            bond.get("instrument_history_json"), isin=str(bond["isin"]),
            as_of=end.isoformat(), issuer=str(bond["issuer"]),
        )
    except (ValueError, TypeError, KeyError, OverflowError):
        summary.update(status="invalid", reason="history_invalid")
        summary["change_5"] = {"value_bp": None, "reason": "history_invalid"}
        summary["change_21"] = {"value_bp": None, "reason": "history_invalid"}
        return summary, False
    if history is None:
        return summary, False
    records = history["observations"]
    summary.update(
        observations=len(records), first_seen=history["first_seen"],
        calculation_convention=history["calculation_convention"],
        observed_from=records[0]["as_of"] if records else None,
        observed_through=records[-1]["as_of"] if records else None,
        currency=records[-1]["currency"] if records else None,
        cmt_as_of=records[-1]["cmt_as_of"] if records else None,
    )
    if not identifier(bond["isin"])["checksum_valid"]:
        short = long = {"value_bp": None, "reason": "history_identifier_unresolved"}
    else:
        short, long = _instrument_window(records, end, 5), _instrument_window(records, end, 21)
    summary.update(
        change_5=short, change_21=long,
        status="available" if short["value_bp"] is not None and long["value_bp"] is not None
               else "partial" if records else "unavailable",
        reason=short.get("reason") or long.get("reason"),
    )
    return summary, True


def _withhold_instrument_history(summary: dict, reason: str) -> dict:
    if summary.get("status") == "invalid" or summary.get("reason") == "history_unavailable":
        return summary
    result = dict(summary, reason=reason)
    result["change_5"] = {"value_bp": None, "reason": reason}
    result["change_21"] = {"value_bp": None, "reason": reason}
    result["status"] = "partial" if result.get("observations") else "unavailable"
    return result


def compile_snapshot(issuer_daily: pd.DataFrame, bonds: pd.DataFrame, registry: dict,
                     equities: dict[str, pd.Series], *, as_of: date,
                     provenance: dict | None = None) -> dict:
    """Compile a date-bounded descriptive view, with no effects or current-clock reads."""
    history = _frame(issuer_daily, {"as_of", "issuer", "d1_g_spread_bp_matched", "matched_n"}, "issuer", as_of)
    panel = _frame(bonds, {"as_of", "isin", "issuer"}, "bonds", as_of)
    history = _unique(history, ["as_of", "issuer"], "issuer") if not history.empty else history
    panel = _unique(panel, ["as_of", "isin"], "bonds") if not panel.empty else panel
    mapping = _registry(registry)
    result = {"schema": SCHEMA, "method": METHOD, "as_of": as_of.isoformat(),
              "authority": dict(AUTHORITY), "display_only": True,
              "point_in_time_qualified": False, "limitations": list(LIMITATIONS),
              "provenance": provenance or {}, "status": "unavailable", "issuers": [],
              "cds": {"status": "unavailable", "reason": "no_verified_CDS_observation_source"},
              "parameters": {"min_peers": MIN_PEERS, "window_sessions": 5,
                             "descriptive_widening_bp": WIDENING_BP,
                             "equity_weak_pct": EQUITY_WEAK_PCT,
                             "thresholds_validated": False},
              "coverage": {"bond_rows": len(panel), "issuers": 0},
              "instrument_history_coverage": {
                  "population": INSTRUMENT_HISTORY_POPULATION,
                  "instrument_rows": 0, "observation_rows": 0, "invalid_instrument_rows": 0,
              }}
    if history.empty:
        return result
    history = history[history["as_of"].map(is_session)].sort_values(["issuer", "as_of"])
    if history.empty:
        return result
    end = max(history["as_of"])
    age = len([d for d in sessions_between(end, as_of) if d > end])
    stale = age > MAX_AGE_SESSIONS
    result.update(status="stale" if stale else "partial", source_as_of=end.isoformat(), age_sessions=age)
    rows = []
    for issuer in sorted(mapping):
        sub = history[history["issuer"] == issuer]
        meta = mapping[issuer]
        if sub.empty or max(sub["as_of"]) != end:
            rows.append({"issuer": issuer, **meta, "state": "insufficient_evidence",
                         "reason": "issuer_not_observed_at_common_cutoff", "bonds": []})
            continue
        latest = sub.iloc[-1]
        short, long = _window(sub, end, 5), _window(sub, end, 21)
        previous = session_n_back(end, 5)
        prior = _window(sub, previous, 5) if previous else {"value_bp": None}
        accel = None
        if short["value_bp"] is not None and prior["value_bp"] is not None:
            accel = round((short["value_bp"] - prior["value_bp"]) / 5, 6)
        stock = _equity_return(equities.get(meta["equity_ticker"]), end, 5)
        securities = []
        issuer_panel = panel[panel["issuer"] == issuer] if not panel.empty else panel
        if not issuer_panel.empty:
            issuer_panel = issuer_panel[issuer_panel["as_of"] == end]
        for _, b in issuer_panel.iterrows():
            ident = identifier(b["isin"])
            instrument_history, parsed_history = _instrument_history(b, end)
            result["instrument_history_coverage"]["instrument_rows"] += int(parsed_history)
            result["instrument_history_coverage"]["observation_rows"] += instrument_history["observations"]
            result["instrument_history_coverage"]["invalid_instrument_rows"] += int(instrument_history["status"] == "invalid")
            securities.append({"identifier": ident, "name": str(b.get("name", "")),
                "as_of": end.isoformat(), "maturity": str(b.get("maturity", "")),
                "coupon_pct": _number(b.get("coupon")), "price_clean": _number(b.get("price_clean")),
                "g_spread_bp": _number(b.get("g_spread_bp")), "fund_held_par": _number(b.get("par")),
                "near_par_call_flag": (None if pd.isna(b.get("near_par_call_flag"))
                                      else bool(b.get("near_par_call_flag"))),
                "terms_status": "legal_currency_seniority_options_not_resolved",
                "spread_history": ("bounded_retained_history" if parsed_history
                                   else "invalid_history" if instrument_history["status"] == "invalid"
                                   else "not_available_in_latest_panel"),
                "instrument_history": instrument_history})
        securities.sort(key=lambda b: (b["maturity"], b["identifier"]["value"]))
        rows.append({"issuer": issuer, **meta, "source_as_of": end.isoformat(),
            "identity_status": "registry_economic_parent_proxy", "n_bonds": len(securities),
            "level_bp": _number(latest.get("g_spread_bp_pw")),
            "maturity_bucket": _maturity_bucket(latest.get("wam_yrs")),
            "change_5": short, "change_21": long, "acceleration_bp_per_session": accel,
            "equity_5": stock, "bonds": securities, "peer_issuers": [],
            "peer_change_5_bp": None, "relative_change_5_bp": None,
            "state": "historical_only" if stale else "insufficient_evidence"})
    for row in rows:
        if "change_5" not in row:
            continue
        peers = [p for p in rows if p["issuer"] != row["issuer"]
                 and p.get("tier") == row.get("tier") and p.get("tier") in {"IG", "HY"}
                 and row["maturity_bucket"] is not None
                 and p.get("maturity_bucket") == row["maturity_bucket"]
                 and p.get("change_5", {}).get("value_bp") is not None]
        row["peer_issuers"] = [p["issuer"] for p in peers]
        if len(peers) >= MIN_PEERS and row["change_5"]["value_bp"] is not None:
            median = float(pd.Series([p["change_5"]["value_bp"] for p in peers]).median())
            row["peer_change_5_bp"] = round(median, 6)
            row["relative_change_5_bp"] = round(row["change_5"]["value_bp"] - median, 6)
        else:
            row["peer_reason"] = "insufficient_coarse_peers_or_issuer_history"
        row["state"] = _state(row["relative_change_5_bp"], row["equity_5"]["value_pct"],
                              stale=stale, absolute_change=row["change_5"]["value_bp"])
    result["issuers"] = rows
    result["coverage"].update(issuers=len(rows),
        issuers_with_5_sessions=sum(r.get("change_5", {}).get("value_bp") is not None for r in rows),
        paired_comparisons=sum(r.get("relative_change_5_bp") is not None and r.get("equity_5", {}).get("value_pct") is not None for r in rows),
        identified_bond_rows=sum(len(r["bonds"]) for r in rows),
        invalid_identifiers=sum(not b["identifier"]["checksum_valid"] for r in rows for b in r["bonds"]))
    # Hash includes the resulting date-bounded evidence, not future input rows.
    body = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    result["observation_id"] = "cdi:" + hashlib.sha256(body.encode()).hexdigest()[:24]
    return result


def _digest(path: Path, payload: bytes | None = None) -> dict:
    return {"path": str(path.name), "sha256": hashlib.sha256(path.read_bytes() if payload is None else payload).hexdigest(),
            "availability": "current_snapshot_historical_publication_unqualified"}


def _pricing_qualification(cc: Path, provenance: dict, *, source_as_of: str | None,
                           as_of: date, history_coverage: dict | None = None) -> dict:
    """Read the existing CCW verdict; never manufacture a pass from a new clock."""
    result = {"status": "unqualified", "reason": "validation_unavailable",
              "source_binding_verified": False, "observation_as_of": source_as_of,
              "instrument_history_verified": False}
    path = cc / "validation.json"
    try:
        payload = path.read_bytes()
        val = json.loads(payload)
        provenance["pricing_validation"] = _digest(path, payload)
        result.update(price_convention=val.get("price_convention"),
                      validation_overall=val.get("overall"))
        binding = val.get("input_binding") or {}
        if val.get("overall") != "PASS":
            result["reason"] = "pricing_checks_not_passed"
        elif date.fromisoformat(val["as_of"]) > as_of:
            result["reason"] = "validation_after_cutoff"
        elif (binding.get("schema") != "corp_credit.validation_binding.v1"
              or binding.get("observation_as_of") != source_as_of):
            result["reason"] = "validation_observation_binding_missing_or_mismatched"
        elif (binding.get("calculation_convention") not in {"clean", "dirty"}
              or binding.get("calculation_convention") != val.get("price_convention")):
            result["reason"] = "calculation_convention_mismatch"
        elif any(binding.get("artifacts", {}).get(name) != provenance[key]["sha256"]
                 for name, key in [("bond_panel_latest", "bonds"), ("issuer_daily", "issuers")]):
            result["reason"] = "validation_artifact_hash_mismatch"
        elif val.get("sample_metadata", {}).get("LQD", {}).get("as_of") != source_as_of:
            result["reason"] = "independent_sample_not_same_observation_date"
        else:
            result.update(status="passed", reason=None, source_binding_verified=True,
                          sample_as_of=source_as_of,
                          lqd_median_error_bp=val.get("criteria", {}).get("b", {}).get("LQD", {}).get("median_bp"))
            history = binding.get("instrument_history")
            coverage = history_coverage or {}
            result["instrument_history_verified"] = bool(
                isinstance(history, dict)
                and history.get("schema") == INSTRUMENT_HISTORY_SCHEMA
                and history.get("population") == INSTRUMENT_HISTORY_POPULATION
                and history.get("valuation_basis") == INSTRUMENT_HISTORY_BASIS
                and history.get("historical_publication_qualified") is False
                and history.get("independent_historical_pricing_qualified") is False
                and coverage.get("invalid_instrument_rows") == 0
                and type(history.get("instrument_rows")) is int
                and type(history.get("observation_rows")) is int
                and history["instrument_rows"] == coverage.get("instrument_rows")
                and history["observation_rows"] == coverage.get("observation_rows")
                and type(history.get("convention_verified_rows")) is int
                and 0 <= history["convention_verified_rows"] <= history["observation_rows"]
            )
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        result["reason"] = "validation_unreadable_or_incomplete"
    return result


def _seal_snapshot(snapshot: dict) -> dict:
    """Include source qualification in the observation identity."""
    snapshot.pop("observation_id", None)
    body = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), allow_nan=False)
    snapshot["observation_id"] = "cdi:" + hashlib.sha256(body.encode()).hexdigest()[:24]
    return snapshot


def load_snapshot(root: Path, *, as_of: date) -> dict:
    """Existing CCW/stock-store adapter; no live collection and no source writes."""
    cc = root / "corp_bonds"
    files = {"issuers": cc / "series/issuer_daily.parquet", "bonds": cc / "series/bond_panel_latest.parquet",
             "registry": cc / "issuer_themes.json"}
    missing = [name for name, path in files.items() if not path.is_file()]
    if missing:
        empty = compile_snapshot(pd.DataFrame(), pd.DataFrame(), {}, {}, as_of=as_of)
        empty["reason"] = "missing_inputs:" + ",".join(missing)
        return empty
    payloads = {name: path.read_bytes() for name, path in files.items()}
    registry = json.loads(payloads["registry"])
    issuer_frame = pd.read_parquet(BytesIO(payloads["issuers"]))
    bond_frame = pd.read_parquet(BytesIO(payloads["bonds"]))
    dated = _frame(issuer_frame, {"as_of", "issuer", "d1_g_spread_bp_matched", "matched_n"}, "issuer", as_of)
    source_day = max(dated["as_of"]) if not dated.empty else as_of
    equities: dict[str, pd.Series] = {}
    provenance = {name: _digest(path, payloads[name]) for name, path in files.items()}
    for issuer, meta in _registry(registry).items():
        ticker = meta["equity_ticker"]
        if not isinstance(ticker, str) or not ticker.replace(".", "").replace("-", "").isalnum():
            continue
        candidates = []
        for priority, prefix in enumerate(["baskets/ohlcv", "yahoo"]):
            path = root / prefix / f"{ticker}.parquet"
            if not path.is_file():
                continue
            payload = path.read_bytes()
            df = pd.read_parquet(BytesIO(payload))
            column = next((c for c in ["close", "close_price"] if c in df), None)
            if column:
                series = df[column]
                check = _equity_return(series, source_day, 5)
                dates = pd.to_datetime(series.index, errors="coerce", utc=True)
                eligible = [d.date() for d in dates if not pd.isna(d) and d.date() <= source_day]
                latest = max(eligible) if eligible else date.min
                # Prefer an eligible complete window, then the freshest whole source.
                # Do not stitch stores or let a stale preferred store hide a newer one.
                score = (check.get("value_pct") is not None, latest, -priority)
                meta = _digest(path, payload)
                meta.update(store=prefix, observed_through=latest.isoformat())
                candidates.append((score, series, meta))
        if candidates:
            _, equities[ticker], provenance[f"equity:{issuer}"] = max(candidates, key=lambda item: item[0])
    snapshot = compile_snapshot(issuer_frame, bond_frame, registry, equities,
                                as_of=as_of, provenance=provenance)
    pricing = _pricing_qualification(
        cc, provenance, source_as_of=snapshot.get("source_as_of"), as_of=as_of,
        history_coverage=snapshot.get("instrument_history_coverage"),
    )
    snapshot["pricing_validation"] = pricing
    if pricing["status"] != "passed":
        for row in snapshot["issuers"]:
            row["state"] = "insufficient_evidence"
            row["reason"] = "pricing_unqualified"
            for field in ("change_5", "change_21"):
                row[field] = {"value_bp": None, "reason": "pricing_unqualified"}
            for field in ("relative_change_5_bp", "peer_change_5_bp", "acceleration_bp_per_session"):
                row[field] = None
            for bond in row.get("bonds", []):
                bond["price_clean"] = None
                bond["g_spread_bp"] = None
        snapshot["coverage"].update(issuers_with_5_sessions=0, paired_comparisons=0)
    if not pricing["instrument_history_verified"]:
        reason = "pricing_unqualified" if pricing["status"] != "passed" else "history_binding_unqualified"
        for row in snapshot["issuers"]:
            for bond in row.get("bonds", []):
                bond["instrument_history"] = _withhold_instrument_history(bond["instrument_history"], reason)
    return _seal_snapshot(snapshot)


def write_snapshot(snapshot: dict, destination: Path) -> None:
    """Atomically replace one derived projection, not a new raw-data/episode store."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    fd, temporary = tempfile.mkstemp(prefix=".credit-dislocation-", dir=destination.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(raw + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.root is None:
        from lib.config import data_dir
        args.root = data_dir()
    result = load_snapshot(args.root, as_of=args.as_of)
    destination = args.output or args.root / "corp_bonds/credit_dislocation.json"
    write_snapshot(result, destination)
    print(json.dumps({"output": str(destination), "status": result["status"],
                      "source_as_of": result.get("source_as_of"), "coverage": result["coverage"]}))


if __name__ == "__main__":
    main()
