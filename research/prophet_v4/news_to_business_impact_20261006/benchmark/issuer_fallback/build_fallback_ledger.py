"""Build the draw-time fallback ticker->CIK ledger from the SEC owner's cached company_tickers snapshot.

usage (from the repository tree root, Python 3.12):
  PYTHONPATH=. python3.12 research/prophet_v4/news_to_business_impact_20261006/benchmark/issuer_fallback/build_fallback_ledger.py \
      SEC_COMPANY_TICKERS OUT_LEDGER OUT_REPORT

SEC_COMPANY_TICKERS is the owner's cache data/edgar/company_tickers.json (collectors/edgar.py).
It is read, never fetched, and it is not tracked in git, so the ledger this tool writes is
committed beside it and pinned by sha256 in the report.

The ledger is the estate shape {"note", "tickers"} that engine.news_impact.issuer.load_ledger
reads. Keys are canonical tickers (canonical_ticker); a canonical ticker that two SEC rows give
to different CIKs becomes a list of CIKs, which the resolver refuses as ambiguous. Company
titles are dropped: the ledger carries tickers and CIKs only.

tape_draw consults this file only through --fallback-ledger, which fills rows the primary
ledger leaves unresolved and only for tickers the primary ledger does not carry
(DEC:NEWS-IMPACT-ISSUER-FALLBACK-LEDGER). The owner ledger data/edgar/ticker_cik_ledger.json
and collectors/edgar.py are not edited.
"""
import hashlib
import json
import sys
from pathlib import Path

from engine.news_impact.issuer import canonical_ticker


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    sec_path, out_ledger, out_report = (Path(a) for a in argv)
    rows = json.loads(sec_path.read_text(encoding="utf-8"))
    if not isinstance(rows, dict):
        raise SystemExit("company_tickers snapshot is not a JSON object")
    by_ticker: dict[str, set[int]] = {}
    blank = 0
    for row in rows.values():
        ticker = canonical_ticker(str(row["ticker"]))
        if not ticker:
            blank += 1
            continue
        by_ticker.setdefault(ticker, set()).add(int(row["cik_str"]))
    tickers = {
        t: (sorted(ciks) if len(ciks) > 1 else next(iter(ciks)))
        for t, ciks in sorted(by_ticker.items())
    }
    sec_sha = _sha256(sec_path)
    ledger = {
        "note": (
            "draw-time fallback ledger: SEC company_tickers.json snapshot sha256 "
            f"{sec_sha}; canonical tickers; undated; consulted only through "
            "tape_draw --fallback-ledger (DEC:NEWS-IMPACT-ISSUER-FALLBACK-LEDGER)"
        ),
        "tickers": tickers,
    }
    out_ledger.parent.mkdir(parents=True, exist_ok=True)
    out_ledger.write_text(json.dumps(ledger, sort_keys=True, separators=(",", ":")) + "\n")
    report = {
        "tool": "build_fallback_ledger.py",
        "sec_snapshot_sha256": sec_sha,
        "sec_rows": len(rows),
        "sec_blank_tickers": blank,
        "ledger_tickers": len(tickers),
        "ledger_ambiguous_tickers": sum(1 for v in tickers.values() if isinstance(v, list)),
        "ledger_sha256": _sha256(out_ledger),
    }
    out_report.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
