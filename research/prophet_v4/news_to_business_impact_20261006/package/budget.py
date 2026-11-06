#!/usr/bin/env python3
"""Offline scenario calculator. Assumptions, not measured Mastermind traffic.
No network, provider calls, credentials, trades, or production changes.
"""
from dataclasses import dataclass, asdict
from decimal import Decimal
import json

@dataclass(frozen=True)
class Stage:
    name: str
    decisions_per_day: int
    input_tokens_per_decision: int
    output_tokens_per_decision: int
    input_usd_per_million: str
    output_usd_per_million: str

    def cost(self, days: int = 30) -> Decimal:
        counts = (days, self.decisions_per_day, self.input_tokens_per_decision,
                  self.output_tokens_per_decision)
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in counts):
            raise ValueError('Counts and days must be nonnegative integers')
        pi, po = Decimal(self.input_usd_per_million), Decimal(self.output_usd_per_million)
        if not pi.is_finite() or not po.is_finite() or pi < 0 or po < 0:
            raise ValueError('Prices must be finite and nonnegative')
        return (Decimal(days * self.decisions_per_day) *
                (self.input_tokens_per_decision * pi + self.output_tokens_per_decision * po)
                / Decimal(1_000_000))

STAGES = [
    Stage('small-model extraction', 3000, 2200, 250, '0.10', '0.40'),
    Stage('selective stronger-model adjudication', 100, 4500, 700, '2', '10'),
    Stage('frontier thesis-change review', 5, 12000, 1500, '10', '50'),
]

def report() -> dict:
    base = sum((stage.cost() for stage in STAGES), Decimal(0))
    all_raw = Stage('all 20000 raw items at frontier extraction rates',
                    20000, 2200, 250, '10', '50').cost()
    return {
        'status': 'ILLUSTRATIVE_NOT_OBSERVED',
        'pricing_checked': '2026-10-06',
        'calendar_days': 30,
        'raw_items_per_day_assumption': 20000,
        'stages': [asdict(s) | {'usd_per_day': str(s.cost(1)),
                              'usd_per_30_days': str(s.cost())} for s in STAGES],
        'inference_base_usd': str(base),
        'inference_with_100_percent_overhead_usd': str(2 * base),
        'all_raw_frontier_extraction_usd': str(all_raw),
        'three_times_work_two_times_prices_usd': str(6 * base),
        'proposed_daily_cap_usd': '10',
        'proposed_monthly_cap_usd': '250',
        'proposed_initial_build_and_benchmark_cap_usd': '750',
        'exclusions': ['existing subscriptions', 'new data licenses', 'tax',
                       'paid search/tool charges', 'incremental hardware',
                       'storage and existing infrastructure'],
        'caveats': [
            'Token envelopes must count all attempts, retrieved context, and billable reasoning.',
            'Quality, traffic, dedup ratio, route eligibility and throughput are not measured.',
            'No cache or batch discount is assumed.',
            'Rates anchor a scenario, not a provider purchase or routing authorization.',
            'Caps require the existing metering/admission owner; this script does not enforce them.',
        ],
        'sources': {
            'small_model': 'https://ai.google.dev/gemini-api/docs/pricing.md',
            'strong_and_frontier': 'https://platform.claude.com/docs/en/about-claude/pricing',
        },
    }

if __name__ == '__main__':
    r = report()
    assert Decimal(r['inference_base_usd']) == Decimal('106.05')
    assert Decimal(r['inference_with_100_percent_overhead_usd']) == Decimal('212.10')
    assert Decimal(r['all_raw_frontier_extraction_usd']) == Decimal('20700')
    assert Decimal(r['three_times_work_two_times_prices_usd']) == Decimal('636.30')
    try:
        Stage('invalid', -1, 1, 1, '1', '1').cost()
        raise AssertionError('negative count was accepted')
    except ValueError:
        pass
    print(json.dumps(r, indent=2))
