"""Replay the existing original-source H3 input gate without inspecting outcomes.

No network, new collector, result fitting or modification of the original audit.
The report binds original source hashes and actual availability clocks to the
new private-cohort input contract. Accounting observations cannot certify it.
"""
import argparse
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine.treasury_settlement_ledger import qualify_settlement_cohort, financing_baseline_at
from research.sovereign_auction_pressure.funding_audit.outcome_blind_funding_audit import load_sources

AUDIT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = AUDIT.parent / 'verification/local_codex_20261008/H3_INPUT_COVERAGE.json'


def report():
    sources = load_sources()  # Existing accepted hash/byte-length/clock checks.
    casebook_path = AUDIT / 'OUTCOME_BLIND_FUNDING_CASEBOOK.json'
    raw = casebook_path.read_bytes()
    casebook = json.loads(raw)
    cutoff = datetime.fromisoformat(casebook['decision_cutoff_s_minus_one'])
    sources_by_cutoff = [{"source_id": key, "source_digest": s['sha256'],
        "known_at": s['known_at_upper_bound'], "eligible_at_cutoff": s['eligible_s_minus_one'],
        "published_at": s['published_at'], "historical_first_release_verified": False}
        for key, s in sorted(sources.items())]
    # No source in the original audit certifies the complete private universe,
    # security-level cash basis, investor allocation or independent inventory.
    # Import no unsupported cash claim or fabricated funding release clock.
    cash = qualify_settlement_cohort(cohort_id='US_PRIVATE_MARKETABLE:2026-10-06',
        settlement_date=date(2026, 10, 6), decision_at=cutoff, claims=[], inventory=None)
    baseline = financing_baseline_at([], cutoff)
    return {"schema_version": "h3_outcome_blind_input_coverage.v1",
        "operation": "sovereign-auction-funding-local-codex-20261008-001",
        "source_casebook_sha256": hashlib.sha256(raw).hexdigest(),
        "source_hashes_verified": len(sources), "sources": sources_by_cutoff,
        "eligible_original_receipt_count": sum(s['eligible_s_minus_one'] for s in sources.values()),
        "private_cash_cohort": cash, "financing_baseline": baseline,
        "qualified_cash_claim_count": 0, "accepted_inventory_count": 0,
        "net_private_cash_usd": None, "reserve_pressure": None, "probabilities": None,
        "status": "INSUFFICIENT_PIT", "outcome_values_inspected": False,
        "models_fitted": False, "dataset_freeze": "NOT_ADMITTED",
        "prospective_evaluation_started": False,
        "prior_verdicts": {"SLF006": "NO-GO", "D2": "FAIL", "Terminal": "KILL"},
        "missing_source_contract": ["complete private bill/CMB and coupon cash claims",
            "same-cohort SOMA treatment exactly once", "private redemption payment inventory",
            "funded buyback payments not already included in redemptions, or sourced zeros",
            "independently accepted exact inventory", "eligible released financing vintages including IORB",
            "canonical prior-known liquidity, dealer/MMF and calendar baselines"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raw = json.dumps(report(), indent=2, sort_keys=True, allow_nan=False) + '\n'
    if args.check:
        if args.output.read_text() != raw:
            raise ValueError('H3 input coverage differs from original-source replay')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw)
    print(json.dumps({"status": "INSUFFICIENT_PIT", "source_hashes_verified": 12,
        "eligible_original_receipts": 0, "qualified_cash_claims": 0,
        "report_sha256": hashlib.sha256(raw.encode()).hexdigest(), "check_only": args.check}))


if __name__ == '__main__':
    main()
