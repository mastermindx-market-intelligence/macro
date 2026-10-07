#!/usr/bin/env python3
"""Reproduce frozen archive metadata; does NOT infer materiality or independence.

python audit_archived_sources.py --input-dir ./inputs --output SOURCE_AUDIT.json
All source files must match PB_D_PINNED_SOURCES.json. No network or live writes.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from fetch_inputs import validate


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError("Output exists; preserve old output and choose a new path")
    manifest = json.loads(Path(__file__).with_name("PB_D_PINNED_SOURCES.json").read_text())
    data, sources = {}, {}
    for source in manifest["sources"]:
        if source["id"] == "retro_grades":
            continue
        raw = (args.input_dir / source["filename"]).read_bytes()
        sources[source["id"]] = dict(source, **validate(raw, source))
        data[source["id"]] = json.loads(raw)

    compact = data["nvda_compact"]["tickers"]["NVDA"]
    full = data["nvda_news"]
    items = full["by_ticker"]["NVDA"]
    out = {"schema": "pb_d.archive_metadata_audit.v1", "status": "DISCOVERY_ONLY_ZERO_SIGNAL_AUTHORITY",
           "sources": sources, "nvda": {
        "compact_asof": data["nvda_compact"]["asof"],
        "full_asof": full["asof"], "full_fetched_at": full["fetched_at"],
        "n_recent": compact["n_recent"], "n_pos": compact["n_pos"], "n_neg": compact["n_neg"],
        "sentiment_lean": compact["sentiment_lean"], "sentiment_strength": compact["sentiment_strength"],
        "underlying_n": len(items), "null_sentiment_n": sum(x.get("sentiment") is None for x in items),
        "empty_summary_n": sum(not x.get("summary") for x in items),
        "null_event_n": sum(x.get("event") is None for x in items),
        "incidental_n": sum(x.get("centrality") == "incidental" for x in items),
        "source_counts": dict(Counter(x.get("source") for x in items)),
        "locator": "$.tickers.NVDA and $.by_ticker.NVDA",
        "interpretation": "Six retained items, zero classified positive/negative; all underlying sentiment fields are null. This is not six confidently neutral articles. Sep25 NVDA is outside the grade sample."},
        "sep10_attention_probes": {}, "holdings_revision_probe": {},
        "historical_quality_labels": {"verified_material_event": "UNKNOWN", "independent_evidence_2plus": "UNKNOWN",
            "reason": "Snapshot metadata and incomplete source lineage cannot certify issuer economic novelty or independent originating evidence at each decision cut."}}
    sep = data["sep10_news"]
    topics = {
        "INTC": ["Market-size promotion with incidental Intel tag", "Recommendation centered on Super Micro", "Nvidia-focused commentary with backdating flag"],
        "PRIM": ["Primoris lawsuit deadline notice", "Bloom Energy-focused multi-company lawsuit notice", "Argan earnings discussion", "Argan valuation discussion", "Primoris lawsuit deadline notice with backdating flag"]}
    for ticker in ("INTC", "PRIM"):
        rows = []
        for i, item in enumerate(sep["by_ticker"][ticker]):
            rows.append({"locator": f"$.by_ticker.{ticker}[{i}]", "url": item.get("url"),
                "archive_seendate": item.get("seendate"), "source": item.get("source"),
                "sentiment": item.get("sentiment"), "issuer_sentiment": item.get("per_ticker_sentiment", {}).get(ticker),
                "centrality": item.get("centrality"), "suspect_backdated": item.get("suspect_backdated", False),
                "topic_reading": topics[ticker][i], "topic_reading_status": "HUMAN_RESEARCH_METADATA_READING_NOT_VERIFIED_CORPORATE_FACT"})
        out["sep10_attention_probes"][ticker] = {"asof": sep["asof"], "fetched_at": sep["fetched_at"],
            "refresh_skipped_reason": sep.get("refresh_skipped_reason"), "n": len(rows), "items": rows,
            "scope_limit": "One Sep10 archive probe; cannot label all earlier issuer rows or verify the article's underlying corporate claims."}
    hs = data["sep10_holdings"]
    ho = data["oct_holdings"]
    revised = []
    for fund in ("D1CAPITAL", "POLEN"):
        before = next(x for x in hs["by_ticker"]["TSLA"]["holders"] if x["fund"] == fund)
        after = next(x for x in ho["by_ticker"]["TSLA"]["holders"] if x["fund"] == fund)
        keys = ("fund", "action", "shares", "value_usd", "period_end", "filing_date", "available_date", "fund_grade")
        revised.append({"before": {k: before.get(k) for k in keys}, "after": {k: after.get(k) for k in keys},
            "same_position": all(before.get(k) == after.get(k) for k in ("shares", "value_usd", "period_end")),
            "quality_eligibility_before": before.get("fund_grade") in ("A", "B"),
            "quality_eligibility_after": after.get("fund_grade") in ("A", "B")})
    out["holdings_revision_probe"] = {"ticker": "TSLA", "before_built": hs["built"], "after_built": ho["built"],
        "locator": "$.by_ticker.TSLA.holders[fund=D1CAPITAL|POLEN]", "revisions": revised,
        "interpretation": "Same disclosed positions receive later grades. POLEN crosses A/B eligibility; D1 remains qualifying. This does not establish a flip of the overall TSLA smartmoney boolean and does not backdate Sep10 classifications to Aug21."}
    out["claim_checks"] = [{"id": "NVDA_6_0_0", "equal": [compact["n_recent"], compact["n_pos"], compact["n_neg"]] == [6, 0, 0]},
        {"id": "NVDA_six_null_sentiments", "equal": len(items) == 6 and all(x.get("sentiment") is None for x in items)}]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "claims_equal": sum(x["equal"] for x in out["claim_checks"]),
                      "claims_checked": len(out["claim_checks"])}))


if __name__ == "__main__":
    main()
