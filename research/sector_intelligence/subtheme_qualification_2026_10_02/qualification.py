"""Offline acceptance adapter for the incumbent subtheme evaluation owner.

No collection, production import, ranking policy, persistence service or trade authority.
Input receipts are required but their truth must be established by their source owners.
H sessions means NEXT session open through the Hth session close, inclusive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

CAPS = {k: False for k in ("may_rank", "may_gate", "may_size", "may_escalate", "may_trade")}
SCHEMA = "subtheme_replay_qualification.research.v1"


class QualificationError(ValueError):
    """An input cannot support the requested scientific comparison."""


def identifier(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise QualificationError("CANONICAL_IDENTIFIER_REQUIRED")
    return value


def canonical_date(value: Any) -> str:
    try:
        if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
            raise ValueError("noncanonical date")
    except (TypeError, ValueError) as exc:
        raise QualificationError("INVALID_EFFECTIVE_DATE") from exc
    return value


def content_digest(value: Any) -> str:
    """Canonical content identity, not merely a set of row labels."""
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def instant(value: str) -> datetime:
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, AttributeError, ValueError) as exc:
        raise QualificationError("INVALID_TIMESTAMP") from exc
    if d.tzinfo is None or d.utcoffset() is None:
        raise QualificationError("TIMEZONE_REQUIRED")
    return d.astimezone(timezone.utc)


def number(value: Any, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise QualificationError("NUMERIC_VALUE_REQUIRED")
    try:
        x = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise QualificationError("NUMERIC_RANGE_INVALID") from exc
    if not math.isfinite(x) or (positive and x <= 0):
        raise QualificationError("FINITE_POSITIVE_REQUIRED" if positive else "FINITE_REQUIRED")
    return x


def session_axis(rows: Sequence[Mapping[str, Any]]) -> tuple[list[str], dict[str, Mapping[str, Any]]]:
    dates = [r["session"] for r in rows]
    if not dates or dates != sorted(set(dates)):
        raise QualificationError("SESSION_AXIS_NOT_UNIQUE_SORTED")
    for d in dates:
        try:
            if date.fromisoformat(d).isoformat() != d:
                raise ValueError("noncanonical date")
        except (TypeError, ValueError) as exc:
            raise QualificationError("INVALID_SESSION_DATE") from exc
    prev_close = None
    for row in rows:
        op, cl = instant(row["open_at"]), instant(row["close_at"])
        if not op < cl or (prev_close is not None and op <= prev_close):
            raise QualificationError("SESSION_AXIS_OVERLAP")
        prev_close = cl
    return dates, dict(zip(dates, rows))


def frozen_members(signal: Mapping[str, Any]) -> list[dict[str, Any]]:
    decision = instant(signal["decision_at"])
    if signal.get("membership_basis") != "POINT_IN_TIME":
        raise QualificationError("MEMBERSHIP_NOT_PIT")
    rows = signal.get("members") or []
    if not rows:
        raise QualificationError("EMPTY_MEMBERSHIP")
    tickers, issuers, out = set(), set(), []
    for m in rows:
        ticker, issuer = identifier(m["ticker"]), identifier(m["issuer_id"])
        if not ticker or not issuer or ticker in tickers or issuer in issuers:
            raise QualificationError("DUPLICATE_OR_EMPTY_SECURITY_ISSUER")
        tickers.add(ticker)
        issuers.add(issuer)
        if instant(m["known_at"]) > decision:
            raise QualificationError("MEMBERSHIP_KNOWN_AFTER_DECISION")
        if instant(m["weight_known_at"]) > decision:
            raise QualificationError("WEIGHT_KNOWN_AFTER_DECISION")
        canonical_date(m["valid_from"])
        if m.get("valid_to") is not None:
            canonical_date(m["valid_to"])
            if m["valid_to"] <= m["valid_from"]:
                raise QualificationError("INVALID_EFFECTIVE_INTERVAL")
        if m["valid_from"] > signal["session"] or (
            m.get("valid_to") is not None and signal["session"] >= m["valid_to"]
        ):
            raise QualificationError("MEMBERSHIP_NOT_EFFECTIVE")
        out.append({**m, "weight": number(m["weight"], positive=True)})
    total = number(sum(m["weight"] for m in out), positive=True)
    return [{**m, "weight": m["weight"] / total} for m in out]


def peer_ex_issuer(members: Sequence[Mapping[str, Any]], issuer_id: str) -> list[dict[str, Any]]:
    """Remove ALL listings of the candidate issuer; empty peers stay empty."""
    kept = [{**m, "weight": number(m["weight"], positive=True)}
            for m in members if m["issuer_id"] != issuer_id]
    if not kept:
        return []
    total = number(sum(m["weight"] for m in kept), positive=True)
    return [{**m, "weight": m["weight"] / total} for m in kept]


def evidence_at(records: Sequence[Mapping[str, Any]], cutoff: str) -> dict[str, Any]:
    """Latest known version per claim, then independent source-cluster count.

    Source clustering is provided by its incumbent owner, never invented here.
    A revision does not become a second independent observation.
    """
    t = instant(cutoff)
    claims: dict[str, Mapping[str, Any]] = {}
    seen = set()
    for r in records:
        known = instant(r["known_at"])
        if known > t:
            continue
        published = instant(r["published_at"])
        if published > known:
            raise QualificationError("PUBLICATION_AFTER_KNOWLEDGE")
        identifier(r["claim_id"])
        if r.get("status", "ACTIVE") not in ("ACTIVE", "RETRACTED"):
            raise QualificationError("UNKNOWN_EVIDENCE_STATUS")
        key = (r["claim_id"], known)
        if key in seen:
            raise QualificationError("AMBIGUOUS_CLAIM_VERSION")
        seen.add(key)
        if not r.get("source_cluster_id"):
            raise QualificationError("SOURCE_CLUSTER_REQUIRED")
        old = claims.get(r["claim_id"])
        if old is None or instant(old["known_at"]) < known:
            claims[r["claim_id"]] = dict(r)
    rows = [claims[k] for k in sorted(claims)]
    active = [r for r in rows if r.get("status", "ACTIVE") == "ACTIVE"]
    return {"claims": active,
            "retracted_claims": [r for r in rows if r.get("status") == "RETRACTED"],
            "independent_source_clusters": len({r["source_cluster_id"] for r in active})}


def label_group(signal: Mapping[str, Any], horizon: int, sessions: Sequence[Mapping[str, Any]],
                prices: Mapping[tuple[str, str], Mapping[str, Any]], evaluation_at: str) -> dict[str, Any]:
    """Strict frozen-weight target; partial coverage is disclosed and NOT reweighted."""
    base: dict[str, Any] = {"snapshot_id": signal.get("snapshot_id"), "group_id": signal.get("group_id"),
                           "horizon_sessions": horizon, "status": "INELIGIBLE", "authority": CAPS.copy()}
    try:
        identifier(signal.get("snapshot_id"))
        identifier(signal.get("group_id"))
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
            raise QualificationError("INVALID_HORIZON")
        dates, axis = session_axis(sessions)
        if signal["session"] not in axis:
            raise QualificationError("SIGNAL_NOT_ON_SESSION_AXIS")
        decision, evaluation = instant(signal["decision_at"]), instant(evaluation_at)
        if instant(signal["feature_known_at"]) > decision:
            raise QualificationError("FEATURE_KNOWN_AFTER_DECISION")
        if decision < instant(axis[signal["session"]]["close_at"]):
            raise QualificationError("FINAL_SESSION_NOT_CLOSED")
        members = frozen_members(signal)
        base.update(expected_members=len(members), measured_members=0, covered_weight=0.0,
                    decision_at=signal["decision_at"], signal_session=signal["session"],
                    scores=dict(signal.get("scores", {})), benchmark=signal.get("benchmark"),
                    population_digest=content_digest(sorted(members, key=lambda m: m["ticker"])))
        start_index = dates.index(signal["session"]) + 1
        end_index = start_index + horizon - 1
        if end_index >= len(dates):
            raise QualificationError("CALENDAR_HORIZON_UNAVAILABLE")
        start, end = dates[start_index], dates[end_index]
        entry_at, exit_at = axis[start]["open_at"], axis[end]["close_at"]
        if decision >= instant(entry_at):
            raise QualificationError("DECISION_NOT_BEFORE_NEXT_OPEN")
        base.update(entry_session=start, exit_session=end, entry_at=entry_at, exit_at=exit_at,
                    target_basis="next_session_open_to_hth_session_close_frozen_weights")
        if evaluation < instant(exit_at):
            base.update(status="IMMATURE", reason="HORIZON_NOT_ELAPSED")
            return base

        def member_return(ticker: str) -> tuple[float | None, str | None]:
            a, b = prices.get((ticker, start)), prices.get((ticker, end))
            if a is None or b is None:
                return None, "EXACT_ENDPOINT_MISSING"
            if (a.get("ticker") != ticker or b.get("ticker") != ticker
                    or a.get("session") != start or b.get("session") != end):
                return None, "PRICE_ROW_IDENTITY_MISMATCH"
            if not a.get("basis_id") or a["basis_id"] != b.get("basis_id"):
                return None, "PRICE_BASIS_MISMATCH"
            if instant(a["known_at"]) > evaluation or instant(b["known_at"]) > evaluation:
                return None, "PRICE_KNOWN_AFTER_EVALUATION"
            if instant(a["known_at"]) < instant(axis[start]["close_at"]) or instant(b["known_at"]) < instant(axis[end]["close_at"]):
                return None, "FINAL_BAR_KNOWN_BEFORE_CLOSE"
            try:
                return number(number(b.get("close"), positive=True) / number(a.get("open"), positive=True) - 1), None
            except QualificationError as exc:
                return None, str(exc)

        returns, missing = {}, {}
        for m in members:
            r, err = member_return(m["ticker"])
            if err:
                missing[m["ticker"]] = err
            else:
                returns[m["ticker"]] = r
        covered = sum(m["weight"] for m in members if m["ticker"] in returns)
        base.update(measured_members=len(returns), covered_weight=covered, missing_members=missing)
        if missing:
            base.update(status="UNAVAILABLE", reason="FROZEN_POPULATION_INCOMPLETE")
            return base
        bench = signal.get("benchmark")
        if not bench:
            raise QualificationError("BENCHMARK_REQUIRED")
        reference, err = member_return(bench)
        if err:
            base.update(status="UNAVAILABLE", reason="BENCHMARK_" + err)
            return base
        raw = number(sum(m["weight"] * returns[m["ticker"]] for m in members))
        outcome_known = max(instant(prices[(ticker, day)]["known_at"])
                            for ticker in [m["ticker"] for m in members] + [bench]
                            for day in (start, end))
        base.update(status="MEASURED", outcome_known_at=outcome_known.isoformat(),
                    absolute_return=raw, benchmark_return=reference,
                    forward_excess=raw-reference, member_returns=returns,
                    effective_weight_n=1 / sum(m["weight"] ** 2 for m in members))
        return base
    except (QualificationError, KeyError) as exc:
        base.update(reason=str(exc))
        return base


def ranks(values: Sequence[float]) -> list[float]:
    pairs = sorted(enumerate(values), key=lambda p: p[1])
    result = [0.0] * len(values)
    i = 0
    while i < len(pairs):
        j = i + 1
        while j < len(pairs) and pairs[j][1] == pairs[i][1]:
            j += 1
        avg = (i + 1 + j) / 2
        for k in range(i, j):
            result[pairs[k][0]] = avg
        i = j
    return result


def rank_ic(a: Sequence[float], b: Sequence[float]) -> float | None:
    if len(a) != len(b) or len(a) < 3:
        return None
    try:
        x, y = ranks([number(v) for v in a]), ranks([number(v) for v in b])
    except QualificationError:
        return None
    mx, my = statistics.mean(x), statistics.mean(y)
    den = math.sqrt(sum((v-mx)**2 for v in x) * sum((v-my)**2 for v in y))
    return sum((u-mx)*(v-my) for u, v in zip(x, y)) / den if den else None


def paired_comparison(rows: Sequence[Mapping[str, Any]], baseline: str, challenger: str) -> dict[str, Any]:
    """Both scores evaluated on the exact same retained labels. No global winner."""
    identifier(baseline)
    identifier(challenger)
    if baseline == challenger:
        raise QualificationError("DISTINCT_MODELS_REQUIRED")
    seen, groups, excluded = set(), {}, {}
    for r in rows:
        key = (r["snapshot_id"], r["horizon_sessions"])
        if key in seen:
            raise QualificationError("DUPLICATE_LABEL_ID")
        seen.add(key)
        reason = None
        if r["status"] != "MEASURED":
            reason = r["status"]
        else:
            try:
                for field in [baseline, challenger]:
                    number(r.get("scores", {}).get(field))
                number(r["forward_excess"])
            except QualificationError:
                reason = "PAIR_SCORE_OR_TARGET_UNAVAILABLE"
        if reason:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        g = (r["horizon_sessions"], r["signal_session"])
        groups.setdefault(g, []).append(r)
    per_date = []
    for (h, day), cohort in sorted(groups.items()):
        if len({r.get("target_basis") for r in cohort}) != 1:
            raise QualificationError("MIXED_TARGET_BASIS")
        paired_content = [{"snapshot_id": r["snapshot_id"], "group_id": r["group_id"],
                           "horizon_sessions": h, "signal_session": day,
                           "population_digest": r.get("population_digest"),
                           "target_basis": r.get("target_basis"), "benchmark": r.get("benchmark"),
                           "entry_at": r.get("entry_at"), "exit_at": r.get("exit_at"),
                           "outcome_known_at": r.get("outcome_known_at"),
                           "forward_excess": r["forward_excess"],
                           "baseline": baseline, "baseline_score": r["scores"][baseline],
                           "challenger": challenger, "challenger_score": r["scores"][challenger]}
                          for r in sorted(cohort, key=lambda x: x["snapshot_id"])]
        if len({r["group_id"] for r in cohort}) != len(cohort):
            raise QualificationError("DUPLICATE_GROUP_IN_COMPARISON")
        a = rank_ic([r["scores"][baseline] for r in cohort], [r["forward_excess"] for r in cohort])
        b = rank_ic([r["scores"][challenger] for r in cohort], [r["forward_excess"] for r in cohort])
        per_date.append({"horizon_sessions": h, "session": day, "matched_rows": len(cohort),
                         "pair_digest": content_digest(paired_content),
                         "pair_digest_schema": "matched_label_and_score_content.v2",
                         "baseline_ic": a, "challenger_ic": b,
                         "ic_delta": b-a if a is not None and b is not None else None})
    summary = {}
    for h in sorted({r["horizon_sessions"] for r in per_date}):
        usable = [r for r in per_date if r["horizon_sessions"] == h and r["ic_delta"] is not None]
        summary[str(h)] = {"matched_ic_dates": len(usable),
                           "mean_paired_ic_delta": statistics.mean(r["ic_delta"] for r in usable) if usable else None,
                           "inferential_status": "UNQUALIFIED_REQUIRES_BLOCK_AND_REGIME_EVALUATION"}
    return {"per_date": per_date, "by_horizon": summary, "excluded": excluded,
            "winner": None, "authority": CAPS.copy()}


def purged_training_ids(training: Sequence[Mapping[str, Any]], validation: Sequence[Mapping[str, Any]]) -> list[str]:
    """Chronological split: train outcomes must finish BEFORE first validation decision."""
    if not validation:
        raise QualificationError("EMPTY_VALIDATION")
    boundary = min(instant(v["decision_at"]) for v in validation)
    selected = []
    for r in training:
        if not r.get("outcome_known_at"):
            raise QualificationError("OUTCOME_KNOWLEDGE_CLOCK_REQUIRED")
        if (instant(r["decision_at"]) < boundary and instant(r["exit_at"]) < boundary
                and instant(r["outcome_known_at"]) < boundary):
            selected.append(r["snapshot_id"])
    return selected


def nonoverlapping_time_windows(rows: Sequence[Mapping[str, Any]]) -> int:
    """Greedy count of disjoint label intervals, NOT a claim of independent episodes."""
    intervals = sorted({(instant(r["entry_at"]), instant(r["exit_at"])) for r in rows}, key=lambda p:p[1])
    last, count = None, 0
    for start, end in intervals:
        if end < start:
            raise QualificationError("INVALID_LABEL_INTERVAL")
        if last is None or start > last:
            count += 1
            last = end
    return count


def run_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    manifest = packet["manifest"]
    if manifest.get("membership_basis") != "POINT_IN_TIME":
        raise QualificationError("MANIFEST_MEMBERSHIP_NOT_PIT")
    for field in ("calendar_receipt", "price_receipt", "signal_receipt"):
        if not manifest.get(field):
            raise QualificationError("SOURCE_RECEIPT_REQUIRED:" + field)
    if manifest.get("price_basis") != "OWNER_QUALIFIED_ADJUSTED_OHLC":
        raise QualificationError("PRICE_BASIS_NOT_QUALIFIED")
    session_axis(packet["sessions"])
    price_map = {}
    for row in packet["prices"]:
        key = (row["ticker"], row["session"])
        if key in price_map:
            raise QualificationError("DUPLICATE_PRICE_ROW")
        price_map[key] = row
    ids = [r["snapshot_id"] for r in packet["signals"]]
    if len(ids) != len(set(ids)):
        raise QualificationError("DUPLICATE_SNAPSHOT_ID")
    labels = [label_group(s, h, packet["sessions"], price_map, packet["evaluation_at"])
              for s in packet["signals"] for h in packet["horizons"]]
    measured = [r for r in labels if r["status"] == "MEASURED"]
    return {"schema": SCHEMA, "manifest": manifest, "labels": labels,
            "label_status_counts": {k: sum(r["status"] == k for r in labels) for k in sorted({r["status"] for r in labels})},
            "comparison": paired_comparison(labels, packet["baseline"], packet["challenger"]),
            "max_disjoint_time_windows": nonoverlapping_time_windows(measured),
            "disjoint_time_windows_by_horizon": {
                str(h): nonoverlapping_time_windows([r for r in measured if r["horizon_sessions"] == h])
                for h in sorted(set(packet["horizons"]))},
            "independent_episodes": None, "authority": CAPS.copy(),
            "limitations": ["Input attestations require external source-owner verification.",
                            "Frozen adjusted-open/close targets are not a transaction-cost or capacity backtest.",
                            "No alpha, probability calibration, deployment or strategy promotion established."]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    try:
        raw = args.input.read_bytes()
        packet = json.loads(raw)
        result = run_packet(packet)
        result["input_sha256"] = hashlib.sha256(raw).hexdigest()
        text = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "REFUSED", "reason": str(exc), "authority": CAPS}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
