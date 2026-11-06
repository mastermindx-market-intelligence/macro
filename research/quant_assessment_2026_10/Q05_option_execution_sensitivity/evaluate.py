from __future__ import annotations

__doc__ = """Q05 evaluator — RESEARCH ONLY.

Refuses to run unless sha256(PREREG.md) AND sha256(PREREG_AMENDMENT.md) match
their FREEZE.log lines. Every invocation (including a refusal or a crash)
appends one JSON line to RUNS.log with the command, exit code, input sha256s
and output sha256s.

Steps (PREREG §4, §7, §13; amendment A2/A6):
  1. eligibility census over the read-only data vintage (.json/.jsonl/.ndjson/
     .csv/.txt, their .gz forms decompressed and streamed, parquet schemas);
     every skipped extension is counted;
  2. req1 cross-check: module ruler == engine.options_nbbo_cohort.net_return_pct
     bit-for-bit on a fixed price grid;
  3. live selection parity: module select_quote vs the incumbent
     parse_quote_response on synthetic Theta-shaped rows (session date and
     contract expiry derived from the data vintage; no market value is read);
  4. if any eligible candidate input exists the verdict is NOT_IMPLEMENTED
     (manual review; the episode ingest adapter is not built); otherwise the
     stop rule applies: below 20 session blocks / 60 episodes no comparison is
     computed and the verdict is INSUFFICIENT_DATA.

Run:
  PYTHONPATH=<Q05 root> python3.12 evaluate.py
"""

import gzip
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
Q05_ROOT = HERE.parents[2]
DATA = Path("/Users/chriswong/Documents/Cluade/macro-main/data")
PREREG = HERE / "PREREG.md"
AMENDMENT = HERE / "PREREG_AMENDMENT.md"
FREEZE = HERE / "FREEZE.log"
RUNS = HERE / "RUNS.log"
RESULTS = HERE / "results"

OUTCOME_LEDGERS = (
    DATA / "options_signal_episode" / "outcomes_h60.jsonl",
    DATA / "options_signal_episode" / "outcomes_session.jsonl",
    DATA / "options_signal_campaign" / "outcomes.jsonl",
)
FLOW_LEDGER = DATA / "flow_signals" / "ledger.parquet"
POLICY_NEEDLE = b"oa3.long_single_leg_h60_nbbo/v1"
QUOTE_ENDPOINT_NEEDLE = b"/v3/option/history/quote"
TEXT_NEEDLES = (
    POLICY_NEEDLE,
    b"oa3_exact_option_outcome",
    QUOTE_ENDPOINT_NEEDLE,
    b"nbboobs_",
    b"bid_size",
    b"ask_size",
)
TEXT_EXT = (".json", ".jsonl", ".ndjson", ".csv", ".txt")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_hash(name: str) -> str | None:
    if not FREEZE.exists():
        return None
    m = re.search(rf"file={re.escape(name)} sha256=([0-9a-f]{{64}})", FREEZE.read_text())
    return m.group(1) if m else None


def append_run(record: dict) -> None:
    with open(RUNS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def scan_stream(fh) -> list[str]:
    found: set[bytes] = set()
    tail = b""
    keep = max(len(n) for n in TEXT_NEEDLES)
    for chunk in iter(lambda: fh.read(8 << 20), b""):
        buf = tail + chunk
        for n in TEXT_NEEDLES:
            if n not in found and n in buf:
                found.add(n)
        tail = buf[-keep:]
    return sorted(n.decode() for n in found)


def _ext(name: str) -> str:
    low = name.lower()
    if low.endswith(".gz"):
        return os.path.splitext(low[:-3])[1] + ".gz"
    return os.path.splitext(low)[1] or "<none>"


def census() -> dict:
    import pyarrow.parquet as pq

    text_hits, parquet_hits, unreadable = [], [], []
    skipped: Counter = Counter()
    n_files = n_bytes = n_gz = n_gz_bytes_decompressed = 0
    for dp, dn, fn in os.walk(DATA):
        dn[:] = sorted(d for d in dn if not d.startswith("."))
        for f in sorted(fn):
            p = Path(dp) / f
            ext = _ext(f)
            try:
                if ext == ".parquet":
                    n_files += 1
                    cols = pq.read_schema(p).names
                    low = [c.lower() for c in cols]
                    size_cols = [c for c, lc in zip(cols, low)
                                 if "size" in lc and ("bid" in lc or "ask" in lc)]
                    if size_cols:
                        parquet_hits.append({
                            "path": str(p.relative_to(DATA)),
                            "size_columns": size_cols,
                            "has_exchange_column": any("exchange" in lc for lc in low),
                            "has_condition_column": any("condition" in lc for lc in low),
                            "rows": pq.ParquetFile(p).metadata.num_rows,
                            "sha256": sha256_file(p),
                        })
                elif ext in TEXT_EXT:
                    n_files += 1
                    n_bytes += p.stat().st_size
                    with open(p, "rb") as fh:
                        hits = scan_stream(fh)
                    if hits:
                        text_hits.append({"path": str(p.relative_to(DATA)), "needles": hits,
                                          "bytes": p.stat().st_size, "sha256": sha256_file(p)})
                elif ext.endswith(".gz") and ext[:-3] in TEXT_EXT:
                    n_files += 1
                    n_gz += 1
                    n_bytes += p.stat().st_size
                    with gzip.open(p, "rb") as fh:
                        hits = scan_stream(fh)
                    with gzip.open(p, "rb") as fh:
                        n_gz_bytes_decompressed += sum(len(c) for c in iter(lambda: fh.read(8 << 20), b""))
                    if hits:
                        text_hits.append({"path": str(p.relative_to(DATA)), "needles": hits,
                                          "bytes": p.stat().st_size, "sha256": sha256_file(p),
                                          "gzip": True})
                else:
                    skipped[ext] += 1
            except Exception as exc:  # noqa: BLE001
                unreadable.append({"path": str(p.relative_to(DATA)), "error": type(exc).__name__})

    ledgers = []
    for p in OUTCOME_LEDGERS:
        counts: dict[str, int] = {}
        rows = complete_with_quotes = 0
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                rows += 1
                try:
                    rec = json.loads(line)
                except Exception:  # noqa: BLE001
                    counts["unparseable"] = counts.get("unparseable", 0) + 1
                    continue
                opt = rec.get("option") or {}
                key = f"{opt.get('status')}/{opt.get('reason')}"
                counts[key] = counts.get(key, 0) + 1
                if opt.get("status") == "complete" and opt.get("quote_basis"):
                    complete_with_quotes += 1
        ledgers.append({"path": str(p.relative_to(DATA)), "sha256": sha256_file(p), "rows": rows,
                        "option_status_reason": dict(sorted(counts.items())),
                        "option_complete_with_quote_basis": complete_with_quotes})

    t = pq.read_table(FLOW_LEDGER, columns=["session_date", "root", "exp", "strike", "right",
                                            "bid_size_median", "ask_size_median",
                                            "microstructure_schema"]).to_pandas()
    nn = t["bid_size_median"].notna()
    flow = {
        "path": str(FLOW_LEDGER.relative_to(DATA)),
        "sha256": sha256_file(FLOW_LEDGER),
        "rows": int(len(t)),
        "rows_with_nbbo_size_medians": int(nn.sum()),
        "sessions_with_nbbo_size_medians": int(t.loc[nn, "session_date"].nunique()),
        "latest_session_date": str(t["session_date"].max())[:10],
        "microstructure_schemas": sorted(t["microstructure_schema"].dropna().unique().tolist()),
        "eligible": False,
        "ineligible_reason": ("print-level aggregate NBBO medians per flow event; no per-contract "
                              "tick quote path, no entry/exit-window quotes, no OA-3 expression receipt"),
    }
    oa3_policy_files = [h["path"] for h in text_hits if POLICY_NEEDLE.decode() in h["needles"]]
    quote_endpoint_files = [h["path"] for h in text_hits
                            if QUOTE_ENDPOINT_NEEDLE.decode() in h["needles"]]
    return {
        "data_root": str(DATA),
        "files_scanned": n_files,
        "text_bytes_scanned": n_bytes,
        "gz_text_files_scanned": n_gz,
        "gz_text_bytes_decompressed": n_gz_bytes_decompressed,
        "text_extensions_scanned": list(TEXT_EXT) + [e + ".gz" for e in TEXT_EXT],
        "skipped_extension_counts": dict(sorted(skipped.items())),
        "text_needle_hits": text_hits,
        "parquet_bid_ask_size_hits": parquet_hits,
        "unreadable": unreadable,
        "outcome_ledgers": ledgers,
        "flow_ledger": flow,
        "oa3_policy_files": oa3_policy_files,
        "quote_endpoint_files": quote_endpoint_files,
    }


def ruler_crosscheck() -> dict:
    sys.path.insert(0, str(Q05_ROOT))
    from engine import options_execution_sensitivity as oes

    out = {"module_research_only": oes.RESEARCH_ONLY}
    try:
        from engine import options_nbbo_cohort as cohort
    except Exception as exc:  # noqa: BLE001
        out.update({"cohort_import": f"failed:{type(exc).__name__}", "pairs": 0, "mismatches": None})
        return out
    asks = [Decimal(c) / 100 for c in (1, 2, 5, 10, 25, 37, 50, 99, 100, 155, 415, 1280, 4999)]
    bids = [Decimal(0)] + asks
    pairs = mism = 0
    for a in asks:
        for b in bids:
            pairs += 1
            if oes.ruler_net_return_pct(a, b) != cohort.net_return_pct(a, b):
                mism += 1
    out.update({"cohort_import": "ok", "cohort_fee_per_side": str(cohort.FEE_PER_SIDE_USD),
                "pairs": pairs, "mismatches": mism})
    return out


def _parity_cases(oes, close_s: float) -> list[tuple[str, str, float, float, tuple]]:
    D = Decimal

    def q(t, bid, ask, bs=10, asz=10, **kw):
        return oes.Quote(t=t, bid=D(bid), ask=D(ask), bid_size=bs, ask_size=asz, **kw)

    a, e = 600, 660  # entry window [a, e]
    return [
        ("plain_entry", "ask", a, e, (q(600, "1.9", "2.0"),)),
        ("crossed_then_valid", "ask", a, e, (q(600, "2.1", "2.0"), q(605, "1.9", "2.05"))),
        ("ask_zero_exit_valid", "bid", a, e, (q(600, "2.5", "0", asz=0),)),
        ("bid_zero_entry_valid", "ask", a, e, (q(600, "0", "2.0", bs=0),)),
        ("bid_zero_exit_invalid", "bid", a, e, (q(600, "0", "2.6", bs=0),)),
        ("exchange_74_traded", "ask", a, e, (q(600, "1.9", "2.0", ask_exchange=74), q(603, "1.9", "2.1"))),
        ("exchange_74_other", "ask", a, e, (q(600, "1.9", "2.0", bid_exchange=74),)),
        ("condition_2_traded", "bid", a, e, (q(600, "2.5", "2.6", bid_condition=2), q(610, "2.4", "2.6"))),
        ("condition_2_other", "bid", a, e, (q(600, "2.5", "2.6", ask_condition=2),)),
        ("conflicting_duplicate", "ask", a, e, (q(600, "1.9", "2.0"), q(600, "1.9", "2.1"))),
        ("identical_duplicate", "ask", a, e, (q(600, "1.9", "2.0"), q(600, "1.9", "2.0"))),
        ("malformed_size", "ask", a, e, (q(600, "1.9", "2.0", asz=-1),)),
        ("malformed_condition_on_crossed_row", "ask", a, e,
         (q(600, "2.1", "2.0", ask_condition=-3), q(601, "1.9", "2.0"))),
        ("quote_before_arrival", "ask", a, e, (q(590, "0.1", "0.2"), q(620, "1.9", "2.0"))),
        ("insufficient_then_later_size", "ask", a, e, (q(600, "1.9", "2.0", asz=0), q(601, "1.9", "2.0"))),
        ("no_quote", "ask", a, e, ()),
        ("near_close_valid", "bid", close_s - 30, close_s + 30,
         (q(close_s - 10, "2.5", "2.6"), q(close_s + 5, "2.7", "2.8"))),
        ("after_close_only", "bid", close_s - 30, close_s + 30, (q(close_s + 5, "2.7", "2.8"),)),
    ]


def live_parity(c: dict) -> dict:
    from engine import options_execution_sensitivity as oes
    try:
        from engine import options_nbbo_cohort as cohort
    except Exception as exc:  # noqa: BLE001
        return {"cohort_import": f"failed:{type(exc).__name__}", "cases": 0, "mismatches": None}
    session = date.fromisoformat(c["flow_ledger"]["latest_session_date"])
    opened, closed = cohort._session_window(session)
    close_s = (closed - opened).total_seconds()
    expiry = (session + timedelta(days=30)).isoformat()
    contract = {"root": "SPY", "expiration": expiry, "right": "call", "strike": "100",
                "strike_millis": 100000,
                "occ_symbol": cohort.canonical_occ_symbol(root="SPY", expiration=expiry,
                                                          right="call", strike_millis=100000)}
    results, mism = [], 0
    for name, side, arrival, end, quotes in _parity_cases(oes, close_s):
        rows = [{
            "symbol": "SPY", "expiration": expiry, "strike": "100", "right": "call",
            "timestamp": (opened + timedelta(seconds=qq.t)).isoformat(),
            "bid_size": qq.bid_size, "ask_size": qq.ask_size,
            "bid_exchange": qq.bid_exchange, "ask_exchange": qq.ask_exchange,
            "bid_condition": qq.bid_condition, "ask_condition": qq.ask_condition,
            "bid": str(qq.bid), "ask": str(qq.ask),
        } for qq in quotes if qq.t <= end]
        try:
            got = cohort.parse_quote_response(
                rows, role="entry" if side == "ask" else "exit", contract=contract,
                boundary_at=opened + timedelta(seconds=arrival),
                query_end_at=opened + timedelta(seconds=end))
            incumbent = None if got is None else (got.event_at - opened).total_seconds()
        except cohort.NbboSourceError:
            incumbent = "invalid"
        chosen, why = oes.select_quote(quotes, side=side, arrival_t=arrival, window_end_t=end,
                                       min_displayed_contracts=1, session_open_t=0,
                                       session_close_t=close_s)
        module = (float(chosen.t) if chosen is not None
                  else "invalid" if why == oes.REASON_INVALID else None)
        ok = module == incumbent
        mism += 0 if ok else 1
        results.append({"case": name, "incumbent": incumbent, "module": module, "match": ok})
    return {"cohort_import": "ok", "session_basis": "latest flow-ledger session_date (vintage)",
            "cases": len(results), "mismatches": mism, "results": results}


def evaluate(c: dict) -> dict:
    from engine import options_execution_sensitivity as oes

    complete_with_quotes = sum(l["option_complete_with_quote_basis"] for l in c["outcome_ledgers"])
    eligible_candidates = {
        "oa3_policy_files": c["oa3_policy_files"],
        "quote_endpoint_files": c["quote_endpoint_files"],
        "ledger_rows_complete_with_quote_basis": complete_with_quotes,
    }
    any_eligible = bool(c["oa3_policy_files"] or c["quote_endpoint_files"] or complete_with_quotes)
    res = oes.evaluate_episodes([])
    base = res[oes.BASELINE_SCENARIO.key()]
    dec = res[oes.DECISION_SCENARIO.key()]
    loss = oes.population_loss(base, dec)
    empty_ci = oes.cluster_bootstrap_mean([], [])
    out = {
        "eligible_candidate_inputs": eligible_candidates,
        "eligible_oa3_episodes": 0,
        "eligible_session_blocks": 0,
        "scenarios_frozen": len(res),
        "decision_scenario": oes.DECISION_SCENARIO.key(),
        "population_loss_decision": loss,
        "comparison_computed": False,
        "missing_input": ("retained exact-contract OPRA NBBO tick quotes (Theta /v3/option/history/quote: "
                          "bid, ask, bid_size, ask_size, condition, exchange, acquisition clocks) over the "
                          "OA-3 entry and +60 min exit windows, bound to complete "
                          "oa3.long_single_leg_h60_nbbo/v1 expression receipts; the OA-3 policy is "
                          "preregistered_inactive and no such receipt or quote path is retained locally"),
    }
    if any_eligible:
        out.update({"classification": None, "verdict": "NOT_IMPLEMENTED",
                    "manual_review_required": True,
                    "note": "eligible candidate input found; episode ingest adapter not built"})
        return out
    status = oes.classify(empty_ci, empty_ci, n_holdout_episodes=0,
                          paired_delta_ci=empty_ci, decision_loss=loss)
    out.update({"classification": status,
                "verdict": "INSUFFICIENT_DATA" if status == "insufficient_data" else status,
                "manual_review_required": False})
    return out


def main() -> int:
    cmd = " ".join([sys.executable] + sys.argv)
    record: dict = {"command": cmd, "prereg_sha256": None, "frozen_sha256": None}
    exit_code = 1
    try:
        actual = sha256_file(PREREG)
        frozen = frozen_hash("PREREG.md")
        amend = sha256_file(AMENDMENT) if AMENDMENT.exists() else None
        amend_frozen = frozen_hash("PREREG_AMENDMENT.md")
        record.update({"prereg_sha256": actual, "frozen_sha256": frozen,
                       "amendment_sha256": amend, "amendment_frozen_sha256": amend_frozen})
        if frozen is None or actual != frozen:
            record["refused"] = "PREREG.md sha256 differs from FREEZE.log"
            exit_code = 3
            return exit_code
        if amend_frozen is None or amend != amend_frozen:
            record["refused"] = "PREREG_AMENDMENT.md sha256 differs from FREEZE.log"
            exit_code = 3
            return exit_code
        RESULTS.mkdir(exist_ok=True)
        c = census()
        x = ruler_crosscheck()
        lp = live_parity(c)
        e = evaluate(c)
        e["req1_ruler_crosscheck"] = x
        e["live_selection_parity"] = lp
        if x.get("mismatches") not in (0,):
            e["verdict"] = "BLOCKED_REQ1"
        elif lp.get("mismatches") not in (0,):
            e["verdict"] = "BLOCKED_PARITY"
        outputs = {"census.json": c, "evaluation.json": e}
        out_hashes = {}
        for name, obj in outputs.items():
            path = RESULTS / name
            path.write_text(json.dumps(obj, indent=1, sort_keys=True, default=str) + "\n")
            out_hashes[f"results/{name}"] = sha256_file(path)
        record["inputs"] = {l["path"]: l["sha256"] for l in c["outcome_ledgers"]}
        record["inputs"][c["flow_ledger"]["path"]] = c["flow_ledger"]["sha256"]
        record["inputs"]["census_hit_files"] = {h["path"]: h["sha256"] for h in
                                                c["text_needle_hits"] + c["parquet_bid_ask_size_hits"]}
        record["outputs"] = out_hashes
        record["verdict"] = e["verdict"]
        print(json.dumps({"verdict": e["verdict"], "req1_mismatches": x.get("mismatches"),
                          "parity_cases": lp.get("cases"), "parity_mismatches": lp.get("mismatches"),
                          "eligible": e["eligible_candidate_inputs"], "outputs": out_hashes},
                         sort_keys=True))
        exit_code = 0
        return exit_code
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 1
        raise
    finally:
        record["exit_code"] = exit_code
        append_run(record)


if __name__ == "__main__":
    sys.exit(main())
