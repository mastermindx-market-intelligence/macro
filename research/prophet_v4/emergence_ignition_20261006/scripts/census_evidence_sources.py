#!/usr/bin/env python3
"""Read-only Prophet evidence-source census from immutable Git objects.

Run in an isolated research directory. This does not import or execute producers,
fetch vendors, edit a checkout, or qualify an exposure. Final-vintage source
counts are inventory; exact decision-time versions remain a separate gate.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import subprocess

import pandas as pd

DEFAULT_REF = "731a23fb64b9f6f1a321c77618f927f1a58d2d41"
DATA_PATHS = [
    "data/edgar/eps_quarterly.parquet",
    "data/edgar/eps_filing_dates.parquet",
    "data/edgar/earnings_8k_dates.parquet",
    "data/earnings/earnings.parquet",
    "data/revisions/history.parquet",
    "data/revisions/expectation_observations.parquet",
    "data/revisions/expectation_attempts.parquet",
    "data/polygon/news_sentiment.parquet",
    "data/news/event_log.parquet",
    "data/qbus/items.parquet",
    "data/smart_money/filing_receipts.parquet",
    "data/edgar/guidance_hits.parquet",
    "data/edgar/rpo.parquet",
    "data/edgar/material_8k_events.parquet",
    "data/theme_graph/edges.parquet",
    "data/theme_graph/evidence.parquet",
    "data/baskets/membership_history.parquet",
]
SOURCE_PATHS = [
    "collectors/edgar_eps.py", "engine/sue.py", "engine/us_prophet_fusion.py",
    "collectors/edgar_earnings_8k.py", "collectors/equity_earnings.py",
    "collectors/equity_revisions.py", "engine/analyst_revisions.py",
    "collectors/edgar_13f.py", "engine/smart_money.py", "engine/manager_quality.py",
    "engine/financial_news.py", "engine/news_event_ledger.py", "engine/qkernel.py", "engine/qbus.py",
    "collectors/polygon_news.py",
    "scripts/build_stock_library.py", "engine/prophet_lab/intelligence_vector.py",
    "engine/prophet_lab/earnings_dossier.py", "engine/earnings_release/receipts.py",
    "engine/earnings_release/binding.py", "engine/earnings_narrative/contracts.py",
    "engine/earnings_narrative/generation.py", "engine/earnings_narrative/extract.py",
    "engine/group_linked_outsiders.py", "engine/theme_graph/membership_evidence.py",
    "engine/gex_confirm.py", "engine/options_flow.py", "engine/theme_options_witness.py",
    "research/prophet_v4/r6_program/rulings/R6-B04-01_DOSSIER_CONTRACT_2026-09-24.md",
    "research/prophet_v4/r6_program/rulings/R6-D07-01_EVIDENCE_CLASS_REGISTER_ADOPTION_2026-09-27.md",
    "research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md",
    "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/RESULT.md",
    "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/result.json",
]
CASES = {"TSLA": "2026-08-21", "ADM": "2026-09-03", "PRIM": "2026-09-03",
         "INTC": "2026-09-10", "ISRG": "2026-09-14", "NVDA": "2026-09-25"}


def compact_values(series):
    return {str(k): int(v) for k, v in series.fillna("__NULL__").value_counts().items()}


def blank_count(series):
    return int(series.isna().sum() + series.dropna().astype(str).str.strip().eq("").sum())


class Reader:
    def __init__(self, repo, ref):
        self.repo, self.ref = str(repo), ref
        self.refs = {}

    def git(self, *args):
        return subprocess.run(["git", "-C", self.repo, *args], capture_output=True, check=False)

    def raw(self, path):
        result = self.git("show", f"{self.ref}:{path}")
        if result.returncode:
            self.refs[path] = {"state": "ABSENT_AT_PIN", "error": result.stderr.decode().strip()}
            return None
        data = result.stdout
        self.refs[path] = {
            "state": "PRESENT", "bytes": len(data), "sha256": sha256(data).hexdigest(),
            "git_blob": self.git("rev-parse", f"{self.ref}:{path}").stdout.decode().strip(),
            "url": f"https://github.com/mastermindx-market-intelligence/macro/blob/{self.ref}/{path}",
        }
        return data

    def frame(self, path):
        raw = self.raw(path)
        return None if raw is None else pd.read_parquet(io.BytesIO(raw))

    def paths(self, prefix):
        return self.git("ls-tree", "-r", "--name-only", self.ref, prefix).stdout.decode().splitlines()


def frame_summary(frame):
    result = {"rows": len(frame), "columns": list(frame), "nulls": {}, "blank_or_null": {}, "clock_ranges": {}}
    for name in frame.columns:
        series = frame[name]
        result["nulls"][name] = int(series.isna().sum())
        if series.dtype == "object" or str(series.dtype).startswith("str"):
            result["blank_or_null"][name] = blank_count(series)
        if any(token in name for token in ("date", "asof", "seen", "crawled", "observed_at", "fetched", "public_at", "published_at", "accepted_at", "belief_time", "evidence_time")):
            nonmissing = series.dropna().astype(str)
            nonmissing = nonmissing[nonmissing.str.strip().ne("")]
            if len(nonmissing):
                result["clock_ranges"][name] = [nonmissing.min(), nonmissing.max()]
    for name in ("ticker", "ticker_compat", "issuer_id", "security_id", "event_id", "event_key", "item_id", "accession", "slug", "source"):
        if name in frame:
            result[f"unique_{name}"] = int(frame[name].nunique())
    for name in ("rights_class", "missingness_reason", "correction_state", "status", "direction", "event_type", "edge_type", "relation", "type", "source", "form"):
        if name in frame and frame[name].nunique() <= 60:
            result[f"counts_{name}"] = compact_values(frame[name])
    return result


def json_records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def build(reader):
    out = {"schema": "research.prophet_evidence_source_census.v1", "macro_ref": reader.ref,
           "mode": "READ_ONLY_GIT_OBJECTS", "proof_class": "CURRENT_PIN_INVENTORY_NOT_EXPOSURE_QUALIFICATION",
           "sources": {}, "selected_cases": {}, "limitations": [
               "Counts inventory one committed source vintage; they do not establish observed-as-run historical exposure.",
               "A real public clock without value/revision linkage does not establish point-in-time value admissibility.",
               "Missing or unregistered family age thresholds are not silently filled.",
               "Case dates below are date-level inspection cuts, not reconstructed exact publication or execution cuts.",
               "Generic clock_ranges contain raw lexical endpoints; timezone parsing and clock-quality qualification remain explicit separate gates.",
           ]}
    frames = {}
    for path in DATA_PATHS:
        frame = reader.frame(path)
        if frame is not None:
            frames[path] = frame
            out["sources"][path] = frame_summary(frame)
        else:
            out["sources"][path] = {"state": "ABSENT_AT_PIN"}
    eps = frames["data/edgar/eps_quarterly.parquet"].copy()
    lag = (pd.to_datetime(eps.asof_date) - pd.to_datetime(eps.period_end)).dt.days
    out["eps_clock_inventory"] = {"rows": len(eps), "exactly_60_days": int(lag.eq(60).sum()),
        "other_lags": int(lag.ne(60).sum()), "lag_over_215_days": int(lag.gt(215).sum()),
        "clock_basis_column_present": any(c in eps for c in ("clock_basis", "asof_basis", "filed_date", "accession")),
        "lag_day_histogram": compact_values(lag),
        "warning": "60-day equality is consistent with fallback but not a proof that every such row is synthetic; real filing may also be day 60."}
    filings = frames["data/edgar/earnings_8k_dates.parquet"].copy()
    acceptance = pd.to_datetime(filings.acceptance_datetime, errors="coerce", utc=True)
    out["earnings_clock_inventory"] = {"invalid_or_missing_acceptance": int(acceptance.isna().sum()),
        "duplicate_cik_accession": int(filings.duplicated(["cik", "accession"]).sum()),
        "filing_clock_not_earnings_value_link": True, "no_row_capture_clock": True}
    for ticker, cut in CASES.items():
        e = eps[(eps.ticker == ticker) & (pd.to_datetime(eps.asof_date) <= pd.Timestamp(cut))].sort_values("period_end").tail(1)
        f = filings[(filings.ticker == ticker) & (filings.filing_date <= cut)].sort_values(["filing_date", "acceptance_datetime"]).tail(2)
        out["selected_cases"][ticker] = {"date_cut": cut, "latest_eps_eligible_by_legacy_gate": json_records(e),
            "latest_item_202_filings_before_date_cut_NOT_LINKED_TO_EPS": json_records(f),
            "strict_earnings_arrival_qualified": False}
    expectations = frames["data/revisions/expectation_observations.parquet"]
    period_present = expectations.period_end.notna() & expectations.period_end.astype(str).str.strip().ne("")
    out["expectation_inventory"] = {"rows_with_period_end": int(period_present.sum()),
        "rows_with_nonmissing_value": int(expectations.value.notna().sum()),
        "rows_with_period_and_value": int((period_present & expectations.value.notna()).sum()),
        "all_source_clocks_unknown": all(blank_count(expectations[c]) == len(expectations) for c in ("source_effective_at", "source_published_at")),
        "all_issuer_security_refs_unknown": all(blank_count(expectations[c]) == len(expectations) for c in ("issuer_ref", "security_ref")),
        "all_rights_unknown": bool(expectations.rights_class.eq("UNKNOWN").all()),
        "contributor_coverage": int(expectations.contributor_id.notna().sum())}
    expectation_seen = pd.to_datetime(expectations.system_observed_at, errors="coerce", utc=True, format="mixed")
    out["expectation_inventory"]["unparseable_or_missing_system_observed_at"] = int(expectation_seen.isna().sum())
    for ticker, cut in CASES.items():
        day_end = pd.Timestamp(cut, tz="UTC") + pd.Timedelta(days=1)
        e = expectations[(expectations.ticker_compat == ticker) & (expectation_seen < day_end)]
        out["selected_cases"][ticker]["expectation_rows_by_date_cut"] = len(e)
    news = frames["data/news/event_log.parquet"]
    pub = pd.to_datetime(news.seendate, errors="coerce", utc=True)
    seen = pd.to_datetime(news.first_seen_utc, errors="coerce", utc=True)
    out["news_event_clock_inventory"] = {"duplicate_event_ids": int(news.event_id.duplicated().sum()),
        "unparseable_seendate": int(pub.isna().sum()), "unparseable_first_seen": int(seen.isna().sum()),
        "source_clock_later_than_capture": int((pub > seen).sum()),
        "source_clock_not_uniform_publication_semantics": True}
    for ticker, cut in CASES.items():
        belongs = news.tickers.map(lambda s: ticker in json.loads(s) if isinstance(s, str) else False)
        day_end = pd.Timestamp(cut, tz="UTC") + pd.Timedelta(days=1)
        rows = news[belongs & (seen < day_end)]
        out["selected_cases"][ticker]["news_event_rows_captured_by_date_cut"] = len(rows)
    raw = reader.raw("site/news/by_ticker.json")
    news_index = json.loads(raw)
    rows = list(news_index.get("tickers", {}).values())
    out["news_index_inventory"] = {"asof": news_index.get("asof"), "tickers": len(rows),
        "n_recent_ge3": sum((x.get("n_recent") or 0) >= 3 for x in rows),
        "direction_counts": dict(Counter(x.get("sentiment_lean") for x in rows)),
        "article_ref_count": sum(len(x.get("top", [])) for x in rows),
        "family_source_clock_preserved_in_chip": False}
    smart_paths = [p for p in reader.paths("data/smart_money") if p.count("/") == 3
                   and re.fullmatch(r"\d{4}-\d{2}-\d{2}\.parquet", Path(p).name)]
    schema_counter, row_total, q2_complete, periods, funds = Counter(), 0, 0, set(), set()
    q2_summary = []
    for path in sorted(smart_paths):
        frame = reader.frame(path)
        if frame is None:
            continue
        row_total += len(frame)
        periods.add(Path(path).stem)
        funds.add(Path(path).parent.name)
        required = ["filing_date", "accepted_at", "accession", "source_sha256", "fetched_at"]
        complete = all(name in frame and blank_count(frame[name]) == 0 for name in required)
        schema_counter["complete_clock_hash_rows" if complete else "legacy_or_incomplete_rows"] += len(frame)
        if path.endswith("/2026-06-30.parquet"):
            q2_complete += int(complete)
            q2_summary.append({"path": path, "rows": len(frame), "clock_hash_complete": complete,
                **{name: (str(frame[name].iloc[0]) if name in frame and len(frame) else None) for name in required}})
    out["smart_money_inventory"] = {"original_snapshot_files": len(smart_paths), "funds": len(funds),
        "rows": row_total, "period_range": [min(periods), max(periods)],
        "schema_rows": dict(schema_counter), "q2_2026_files": len(q2_summary),
        "q2_2026_files_complete_clocks_hash": q2_complete, "q2_2026_snapshots": q2_summary,
        "complete_means_all_rows_have_required_columns": True,
        "requires_two_qualified_holdings_versions_and_PIT_grade": True}
    case_ownership = {
        "TSLA": ("d1capital", "88160R101"), "ADM": ("soros", "039483102"),
        "PRIM": ("soros", "74164F103"), "INTC": ("coatue", "458140100"),
        "ISRG": ("d1capital", "46120E602"), "NVDA": ("soros", "67066G104"),
    }
    for ticker, (fund, cusip) in case_ownership.items():
        positions = {}
        for period in ("2026-03-31", "2026-06-30"):
            path = f"data/smart_money/{fund}/{period}.parquet"
            frame = reader.frame(path)
            columns = [c for c in ("cusip", "issuer", "title_class", "sh_type", "shares", "period_end", "filing_date",
                                  "accepted_at", "available_date", "accession", "source_sha256", "fetched_at") if c in frame]
            positions[period] = {"path": path, "rows": json_records(frame[frame.cusip == cusip][columns])}
        out["selected_cases"][ticker]["selected_fund_position_versions"] = positions
        out["selected_cases"][ticker]["ownership_binding_basis"] = "BOARD_SELECTED_FUND_AND_VERIFIED_RAW_CUSIP; not a new canonical identity assertion"
    qbus = frames["data/qbus/items.parquet"]
    qseen = pd.to_datetime(qbus._crawled_at, errors="coerce", utc=True, format="mixed")
    out["qbus_clock_inventory"] = {"unparseable_or_missing_capture": int(qseen.isna().sum()),
        "blank_event_key": blank_count(qbus.event_key), "duplicate_item_id": int(qbus.item_id.duplicated().sum()),
        "clustering_is_not_earnings_origin_independence": True}
    counterparties = frames["data/edgar/material_8k_events.parquet"]
    out["relationship_inventory"] = {"material_8k_rows": len(counterparties),
        "counterparty_nonblank": len(counterparties) - blank_count(counterparties.counterparty),
        "current_graph_types": compact_values(frames["data/theme_graph/edges.parquet"]["type"])}
    json_paths = ["data/gex/latest.json", "data/gex/gate.json", "data/options_flow/signing_gate.json",
                  "data/neuralweb/theme_options_witness.json"]
    out["options_inventory"] = {}
    for path in json_paths:
        raw = reader.raw(path)
        if raw is None:
            out["options_inventory"][path] = {"state": "ABSENT_AT_PIN"}
            continue
        obj = json.loads(raw)
        out["options_inventory"][path] = {k: v for k, v in obj.items() if k in (
            "asof", "as_of", "generated_at", "generated", "status", "state", "scored", "direction_reliable",
            "magnitude_reliable", "store_present", "coverage_stats", "authority")}
    for path in SOURCE_PATHS:
        reader.raw(path)
    out["source_identities"] = reader.refs
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = build(Reader(args.repo, args.ref))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"out": str(args.out), "sha256": sha256(args.out.read_bytes()).hexdigest(),
                      "sources": len(result["source_identities"]), "case_count": len(result["selected_cases"])}))


if __name__ == "__main__":
    main()
