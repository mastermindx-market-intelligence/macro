"""Historical issuer comparisons over the incumbent SEC cash/debt read models.

No collection, provider or publication effect. Reported values remain third
party, including arithmetic derived solely from those figures. Period clocks never become the
date of the new event or the date this consumer runs.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from engine.capital_need import assemble_capital_need
from engine.cash_runway import extract_cash_runway
from engine.debt_maturity import extract_maturity_ladder
from engine.press.external_candidate import _read_bound


def issuer_baseline_context(review: dict, *, root: Path, as_of: datetime,
                            reviewed_tickers: dict, reviewed_claims: list) -> tuple[list, dict]:
    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        raise ValueError('issuer-baseline evaluation requires an explicit instant')
    now = as_of.astimezone(timezone.utc)
    as_of = now.date()
    fields = {'ticker', 'cik', 'cache_sha256', 'identity_sha256',
              'event_quantity_literal', 'relevance'}
    if not isinstance(review, dict) or set(review) != fields:
        raise ValueError('explicit issuer-baseline review required')
    ticker, cik, literal = (review[k] for k in ('ticker', 'cik', 'event_quantity_literal'))
    if (not isinstance(ticker, str) or ticker not in reviewed_tickers
            or not isinstance(cik, str) or not re.fullmatch(r'\d{10}', cik) or int(cik) == 0
            or not isinstance(review['relevance'], str) or not 1 <= len(review['relevance'].strip()) <= 500
            or not isinstance(literal, str)
            or literal not in [c.get('quantity_literal') for c in reviewed_claims]):
        raise ValueError('issuer-baseline identity or event comparison is unqualified')
    amount = re.fullmatch(r'\$(\d+(?:\.\d+)?) (million|billion)', literal)
    if amount is None:
        raise ValueError('issuer baseline supports explicit positive USD event amounts only')
    event_usd = Decimal(amount[1]) * (10**6 if amount[2] == 'million' else 10**9)
    if not event_usd.is_finite() or event_usd <= 0:
        raise ValueError('issuer-baseline event amount must be positive')

    root = Path(root).resolve()
    cache_rel = f'data/debt_maturity/cache/CIK{cik}.json'
    identity_rel = 'data/edgar/ticker_cik_ledger.json'
    revisions = {}
    payloads = []
    for rel, digest in ((cache_rel, review['cache_sha256']),
                        (identity_rel, review['identity_sha256'])):
        path = root / rel
        if path.resolve() != path:
            raise ValueError('issuer-baseline evidence may not traverse symlinks')
        payloads.append(json.loads(_read_bound(path, digest, 8_000_000)))
        revisions['artifact:' + rel] = 'sha256:' + digest
    cache, ledger = payloads
    if not isinstance(cache, dict) or not isinstance(ledger, dict):
        raise ValueError('issuer-baseline evidence must be objects')
    entries = ledger.get('tickers', ledger)
    entry = entries.get(ticker) if isinstance(entries, dict) else None
    mapped = entry.get('cik') if isinstance(entry, dict) else entry
    if isinstance(mapped, bool) or not str(mapped).isdigit() or str(mapped).zfill(10) != cik:
        raise ValueError('issuer-baseline ticker and CIK mismatch')
    embedded = cache.get('cik')
    if isinstance(embedded, bool) or not str(embedded).isdigit() or str(embedded).zfill(10) != cik:
        raise ValueError('issuer-baseline embedded CIK mismatch')
    try:
        fetched = datetime.fromisoformat(cache['fetched_at'].replace('Z', '+00:00'))
        if fetched.tzinfo is None or fetched.astimezone(timezone.utc) > now:
            raise ValueError('invalid acquisition clock')
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise ValueError('issuer-baseline acquisition clock required') from exc

    debt = extract_maturity_ladder(cache, cik=cik, as_of=as_of)
    cash = extract_cash_runway(cache, cik=cik, as_of=as_of, ladder=debt)
    for block in (debt, cash):
        block['fetched_at'] = cache['fetched_at']
    view = assemble_capital_need(debt, cash, issuer_id='CIK' + cik,
                                 security_id=ticker, as_of=as_of)
    if view['status'] != 'complete' or view['coverage']['reasons']:
        raise ValueError('issuer-baseline read model is incomplete or stale')
    period = cash['period']
    if debt['period']['accn'] != period['accn'] or debt['period']['end'] != period['end']:
        raise ValueError('issuer-baseline requires one matched annual filing')
    reported = view['reported']
    cash_usd = Decimal(str(reported['cash']['value']))
    ocf = Decimal(str(reported['operating_cash_flow']['value']))
    capex = Decimal(str(reported['capex']['value']))
    fcf = Decimal(str(view['derived']['free_cash_flow']['value']))
    due = next((Decimal(str(b['value'])) for b in reported['debt_due']['buckets']
                if b['key'] == 'y1' and b['state'] == 'observed'), None)
    total = Decimal(str(reported['debt_due']['total_reported_usd']))
    if due is None or any(not x.is_finite() or x <= 0 for x in (cash_usd, fcf, due, total)):
        raise ValueError('issuer-baseline comparison denominators must be positive')

    ref = 'artifact:' + cache_rel
    receipt = revisions[ref]
    base = {'ref': ref, 'dated': period['end'], 'receipt': receipt,
            'source_name': 'Issuer SEC annual filing',
            'period': dict(period), 'evaluation_as_of': as_of.isoformat(),
            'context_relevance': review['relevance'].strip()}
    def number(x):
        return format(x, 'f')
    def pct(n, d):
        return (n / d * 100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    facts = []
    def add(fid, text, value, *, derived):
        facts.append({**base, 'id': f'issuer_{ticker}_{fid}', 'text': text,
                      'values': [number(value)], 'tier': 'third_party', 'derived_from_external': derived})
    stamp = f"{ticker}'s fiscal year ended {period['end']} (filed {period['filed']})"
    for fid, label, value in [('cash', 'year-end cash', cash_usd),
                              ('ocf', 'annual operating cash flow', ocf),
                              ('capex', 'annual capital expenditure', capex),
                              ('due', 'principal due in the first 12 months AFTER that fiscal year end', due),
                              ('total', 'total disclosed maturity principal', total)]:
        add(fid, f'For {stamp}, reported {label} was ${number(value)}.', value, derived=False)
    add('fcf', f'For {stamp}, our subtraction of capital expenditure from operating cash flow gives '
        f'${number(fcf)} of historical free cash flow.', fcf, derived=True)
    cover, share = pct(cash_usd, due), pct(due, total)
    add('cover', f'For {stamp}, our historical cash-to-first-bucket principal ratio is {cover}%. '
        'The maturity interval begins at fiscal year end, not today.', cover, derived=True)
    add('near_share', f'For {stamp}, our first-bucket share of total disclosed principal is {share}%.',
        share, derived=True)
    for fid, label, denominator in [('event_cash', 'year-end cash', cash_usd), ('event_fcf', 'annual free cash flow', fcf)]:
        value = pct(event_usd, denominator)
        add(fid, f'The reviewed event amount is {value}% of {stamp} {label}, by our arithmetic. '
            'This is a historical scale comparison, not current liquidity, a payment schedule or a price-effect estimate.',
            value, derived=True)
    for rel in ('engine/press/issuer_baseline.py', 'engine/debt_maturity.py',
                'engine/cash_runway.py', 'engine/capital_need.py'):
        module_root = Path(__file__).resolve().parents[2]
        revisions['implementation:' + rel] = 'sha256:' + hashlib.sha256((module_root / rel).read_bytes()).hexdigest()
    return facts, revisions
