"""Pure research diagnostics over explicitly supplied, outcome-blind inputs.

No network, credential access, store discovery, outcome labelling, or production
writes. PASS means a bounded source assertion survived checks, not scientific
admission. Owner evidence must independently establish its scope and truth.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timezone
import hashlib
import json
import math
import re
from typing import Any, Literal

from lib.dataos.identity import VendorAliasTable, parse_id
from engine.prophet_live.interval import ADJUSTED

SPEC_REF = ('macro@1f21fb74735d826a37d5e1925b1d06af6feb6fda:'
            'SLR_P0_DEVELOPMENT_PREREG_2026-10-07.md+PREOUTCOME_V1_1')
FAMILIES = ('gics', 'identity', 'instrument_type', 'aliases', 'total_returns',
            'corporate_actions', 'membership', 'market_cap', 'events', 'earnings_schedule')
Status = Literal['PASS', 'FAIL', 'UNKNOWN']


class NotQualified(ValueError):
    """An input cannot support this bounded historical assertion."""


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def _utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise NotQualified('CLOCK_WITHOUT_TIMEZONE')
    return result.astimezone(timezone.utc)


@dataclass(frozen=True)
class SourceQualificationResult:
    field_family: str
    source_sha: str | None = None
    study_spec_ref: str = SPEC_REF
    source_owner_interface: str | None = None
    source_object_sha256: str | None = None
    dataset_designation: str | None = None
    license_or_permission_receipt_ref: str | None = None
    economic_valid_from: str | None = None
    economic_valid_to: str | None = None
    vendor_asof_date: str | None = None
    report_period_end: str | None = None
    first_publication_or_filing_accepted_at: str | None = None
    observed_ingested_at: str | None = None
    revision_generation: int | None = None
    knowledge_basis: str = 'UNKNOWN'
    historical_identity_basis: str = 'UNKNOWN'
    coverage_by_era: dict[str, int] | None = None
    exclusion_codes: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    status: Status = 'UNKNOWN'


def qualify(result: SourceQualificationResult, source_object: Any,
            decision_at: str) -> SourceQualificationResult:
    """Check a caller-supplied field receipt, never promote a refused/unknown feed.

    A permission reference is evidence for the reviewer to inspect; it is not a
    permission grant. Final-vintage mode preserves observed time honestly.
    Filing acceptance alone is not sufficient: the supplied publication bound
    must include actual dissemination or conservative next-session availability.
    """
    failures: list[str] = list(result.exclusion_codes)
    unknown: list[str] = []
    if result.status not in ('PASS', 'FAIL', 'UNKNOWN') or result.field_family not in FAMILIES:
        failures.append('INVALID_SOURCE_CONTRACT')
    if result.study_spec_ref != SPEC_REF:
        failures.append('STUDY_SPEC_REF_MISMATCH')
    if result.status == 'FAIL':
        failures.append('SOURCE_REFUSED_OR_FAILED')
    if result.status == 'UNKNOWN':
        unknown.append('SOURCE_UNAVAILABLE_OR_UNQUALIFIED')
    required = ('source_owner_interface', 'source_sha', 'source_object_sha256',
                'dataset_designation', 'license_or_permission_receipt_ref',
                'economic_valid_from', 'first_publication_or_filing_accepted_at',
                'observed_ingested_at', 'revision_generation', 'coverage_by_era',
                'evidence_refs')
    for field in required:
        value = getattr(result, field)
        if value is None or value == '' or value == () or value == {}:
            unknown.append('MISSING_' + field.upper())
    if result.source_sha and not re.fullmatch('[0-9a-f]{40}', result.source_sha):
        failures.append('INVALID_SOURCE_REF')
    if result.coverage_by_era is not None:
        if any(type(n) is not int or n < 0 for n in result.coverage_by_era.values()):
            failures.append('INVALID_COVERAGE_COUNTS')
        elif not any(n > 0 for n in result.coverage_by_era.values()):
            unknown.append('NO_OBSERVED_COVERAGE')
    if source_object is None:
        unknown.append('SOURCE_OBJECT_NOT_DELIVERED')
    elif not result.source_object_sha256 or digest(source_object) != result.source_object_sha256:
        failures.append('SOURCE_DIGEST_MISMATCH')
    if result.historical_identity_basis != 'OWNER_VALID_TIME':
        unknown.append('HISTORICAL_IDENTITY_NOT_PROVEN')
    if result.knowledge_basis not in ('ACTUALLY_FIRST_SEEN', 'FINAL_VINTAGE_VALID_TIME_ONLY'):
        unknown.append('KNOWLEDGE_BASIS_UNKNOWN')
    try:
        cutoff = _utc(decision_at)
        if result.economic_valid_from:
            start = date.fromisoformat(result.economic_valid_from)
            if start > cutoff.date():
                failures.append('NOT_YET_ECONOMICALLY_VALID')
            if result.economic_valid_to:
                end = date.fromisoformat(result.economic_valid_to)
                if end <= start:
                    failures.append('INVALID_VALID_TIME_INTERVAL')
                if cutoff.date() >= end:
                    failures.append('NO_LONGER_ECONOMICALLY_VALID')
        if result.first_publication_or_filing_accepted_at and result.observed_ingested_at:
            published = _utc(result.first_publication_or_filing_accepted_at)
            observed = _utc(result.observed_ingested_at)
            if published > cutoff:
                failures.append('NOT_PUBLIC_BY_CUTOFF')
            if observed < published:
                failures.append('OBSERVED_BEFORE_PUBLICATION')
            if result.knowledge_basis == 'ACTUALLY_FIRST_SEEN' and observed > cutoff:
                failures.append('FUTURE_RESTATED_NOT_FIRST_SEEN')
        if result.revision_generation is not None:
            if (type(result.revision_generation) is not int or result.revision_generation < 0):
                failures.append('INVALID_REVISION')
    except (ValueError, TypeError):
        failures.append('INVALID_SOURCE_CLOCK')
    status = 'FAIL' if failures else ('UNKNOWN' if unknown else 'PASS')
    return replace(result, status=status,
                   exclusion_codes=tuple(sorted(set(failures + unknown))))


def qualification_report(results: list[SourceQualificationResult]) -> dict:
    families = Counter(r.field_family for r in results)
    complete = (set(families) == set(FAMILIES) and all(n == 1 for n in families.values())
                and all(r.status == 'PASS' for r in results))
    blockers = sorted(set([c for r in results for c in r.exclusion_codes] +
                          ['MISSING_FAMILY_' + f.upper() for f in FAMILIES if families[f] != 1]))
    return dict(MISSION='SLR-P0-SOURCE-QUALIFICATION',
                PARENT_PR='https://github.com/mastermindx-market-intelligence/macro/pull/8645',
                FROZEN_SPEC='v1.0.1 plus pre-outcome v1.1 amendment',
                RESULT='SOURCE_QUALIFIED_FOR_INDEPENDENT_REVIEW' if complete else 'NOT_ADMITTED',
                REAL_DATA_READ=False, OUTCOMES_READ=False,
                DATA_SOURCE_RIGHTS='UNKNOWN', PARENT_PARITY='UNKNOWN',
                INDEPENDENT_REVIEW='OWED', PRODUCTION_CHANGED=False,
                CODE_PR=None, COMMIT_SHA=None, CI=[], BLOCKERS=blockers,
                NEXT_ACTION='Independent field-evidence review; no outcome access.',
                qualified_event_count=None, admission_granted=False,
                primary_estimate=None, source_results=[asdict(r) for r in results])


def validate_input_graph(value: Any) -> None:
    """Reject protected paths, unprojected parent tables and outcome feature keys.

    Used before any caller-supplied manifest is consumed. No file paths are opened
    by this module. Parent metadata must arrive as a separate whitelisted projection.
    """
    denied = ('cr1', 'af1', 'rh1', 'forward', 'outcome', 'durable_winner',
              'clean_hold', 'blow_off', 'failed_label', 'winner_episodes.parquet',
              'personality_timing', 'winner_autopsy_panel')
    if isinstance(value, dict):
        for key, child in value.items():
            text = str(key).lower()
            if any(d in text for d in denied) or re.fullmatch(r'y\d+|mae\d+|mfe\d+', text):
                raise NotQualified('INPUT_GRAPH_FORBIDDEN_COLUMN')
            validate_input_graph(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            validate_input_graph(child)
    elif isinstance(value, str):
        path = value.lower().replace('\\', '/')
        if any(d in path for d in ('cr1/', 'af1/', 'rh1/', 'personality_timing',
                                  'winner_episodes.parquet', 'winner_autopsy_panel')):
            raise NotQualified('INPUT_GRAPH_FORBIDDEN_PATH_OR_VALUE')


def resolve_alias(records: list[dict], vendor: str, symbol: str, on: str,
                  decision_at: str | None = None) -> str | None:
    if vendor in ('yahoo_fetch', 'store'):
        raise NotQualified('CURRENT_CATALOG_NOT_HISTORICAL_ALIAS')
    relevant = [r for r in records if r['vendor'] == vendor]
    if any(r.get('valid_from') is None for r in relevant):
        raise NotQualified('UNDATED_ALIAS')
    # Delegates naming/ambiguity and native polygon seals to the incumbent reader.
    return VendorAliasTable.from_records(relevant).resolve(
        vendor, symbol, date.fromisoformat(on), decision_at=decision_at)


def historical_sector(records: list[dict], on: str) -> str:
    selected = [r for r in records if r.get('valid_from') and r['valid_from'] <= on
                and (r.get('valid_to') is None or on < r['valid_to'])]
    if len(selected) != 1 or selected[0].get('taxonomy') != 'GICS':
        raise NotQualified('GICS_NOT_ADMITTED')
    sector = selected[0].get('sector')
    if not sector:
        raise NotQualified('GICS_NOT_ADMITTED')
    return sector


def check_benchmark_inception(on: str, first_session: str) -> None:
    if on < first_session:
        raise NotQualified('BENCHMARK_NOT_LISTED')


def freeze_peers(rows: list[dict], subject_issuer: str, sector: str,
                 lagged_session: str) -> tuple[list[dict], dict[str, int]]:
    """Consumes historical owner assertions; never derives issuer IDs from CIK."""
    parse_id(subject_issuer)
    excluded: Counter = Counter()
    selected: dict[str, dict] = {}
    for row in rows:
        reason = None
        issuer = row.get('issuer_id')
        security = row.get('security_id')
        try:
            if not issuer or not security or not issuer.startswith('ISS:') or not security.startswith('SEC:'):
                raise ValueError('missing identity')
            parse_id(issuer)
            parse_id(security)
        except ValueError:
            reason = 'IDENTITY_UNKNOWN'
        if reason is None:
            if issuer == subject_issuer:
                reason = 'SAME_ISSUER'
            elif row.get('instrument_type') not in ('CS', 'ADRC'):
                reason = 'TYPE_NOT_ORDINARY'
            elif (row.get('historical_identity_basis') != 'OWNER_VALID_TIME'
                  or not row.get('evidence_ref') or not row.get('known_at')):
                reason = 'HISTORICAL_IDENTITY_UNKNOWN'
            elif (not row.get('valid_from') or row['valid_from'] > lagged_session
                  or (row.get('valid_to') and lagged_session >= row['valid_to'])):
                reason = 'IDENTITY_NOT_VALID'
            elif _utc(row['known_at']).date().isoformat() > lagged_session:
                reason = 'IDENTITY_NOT_KNOWN'
            elif row.get('sector') != sector:
                reason = 'OTHER_SECTOR'
            elif row.get('controls_at') != lagged_session:
                reason = 'CONTROLS_NOT_LAGGED'
            elif (not _finite(row.get('lagged_adv')) or not _finite(row.get('lagged_close'))
                  or row['lagged_adv'] < 25_000_000 or row['lagged_close'] < 5):
                reason = 'LIQUIDITY_OR_PRICE'
            elif row.get('terminal_resolved') is not True:
                reason = 'TERMINAL_UNRESOLVED'
        if reason:
            excluded[reason] += 1
            continue
        prior = selected.get(issuer)
        if prior is None:
            selected[issuer] = row
        else:
            excluded['DUPLICATE_ISSUER'] += 1
            if (-row['lagged_adv'], security) < (-prior['lagged_adv'], prior['security_id']):
                selected[issuer] = row
    return [selected[i] for i in sorted(selected)], dict(excluded)


def _finite(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def validate_price_segment(bases: list[str], identities: list[str]) -> None:
    if not bases or len(bases) != len(identities) or set(bases) != {ADJUSTED}:
        raise NotQualified('BASIS_CONFLICT')
    if len(set(identities)) != 1 or not identities[0]:
        raise NotQualified('IDENTITY_SPLICE')


def economic_return(previous: float, close: float | None, *, cash: float = 0,
                    basis: str = ADJUSTED, terminal_proceeds: float | None = None) -> float:
    """Cash must be in the same split-adjusted per-share units as both prices."""
    if not _finite(previous) or previous <= 0 or not _finite(cash):
        raise NotQualified('INVALID_PRICE')
    if basis not in (ADJUSTED, 'split_adjusted'):
        raise NotQualified('BASIS_CONFLICT')
    if basis == ADJUSTED and cash != 0:
        raise NotQualified('DOUBLE_ADJUSTMENT')
    if close is None:
        if not _finite(terminal_proceeds) or terminal_proceeds < 0:
            raise NotQualified('TERMINAL_UNRESOLVED')
        wealth = terminal_proceeds
    elif _finite(close) and close > 0:
        wealth = close + cash
    else:
        raise NotQualified('INVALID_PRICE')
    return wealth / previous - 1


def action_receipt(pages: list[dict], required_ids: set[str]) -> list[str]:
    if not pages:
        raise NotQualified('ACTION_RECEIPT_MISSING')
    events: list[str] = []
    for i, page in enumerate(pages, 1):
        if page.get('page') != i or page.get('next_page') != (i+1 if i < len(pages) else None):
            raise NotQualified('ACTION_PAGE_INCOMPLETE')
        events.extend(page['events'])
    if len(events) != len(set(events)) or set(events) != required_ids:
        raise NotQualified('ACTION_DUPLICATE_OR_MISSING_EVENT')
    return events


def session_window(prices: dict, sessions: list, anchor: int, horizon: int) -> tuple:
    if anchor < horizon or anchor >= len(sessions) or horizon < 1:
        raise NotQualified('LOOKBACK_UNAVAILABLE')
    selected = tuple(sessions[anchor-horizon:anchor+1])
    if len(set(sessions)) != len(sessions) or any(s not in prices or not _finite(prices[s])
                                                or prices[s] <= 0 for s in selected):
        raise NotQualified('MISSING_SESSION')
    return selected


def measurement_window(anchor: int, horizon: int, session_count: int) -> tuple[int, ...]:
    """Synthetic measurement clock only; no labels or market outcomes computed."""
    if anchor < 0 or horizon < 1 or anchor + horizon >= session_count:
        raise NotQualified('LABEL_WINDOW_UNOBSERVABLE')
    return tuple(range(anchor+1, anchor+horizon+1))


def validate_feature_clock(cutoff: int, features: dict[str, tuple[int, Any]]) -> None:
    if any(known > cutoff for known, _ in features.values()):
        raise NotQualified('FUTURE_FEATURE')


def scheduled_earnings(cutoff: int, release_session: int | None,
                      announced_session: int | None) -> bool | None:
    if announced_session is None or announced_session > cutoff or release_session is None:
        return None
    return cutoff < release_session <= cutoff + 5


def h7_risk_set(rows: list[dict]) -> list:
    # Consumes only the D+20 eligibility projection, not any later shock/outcome.
    return [r['id'] for r in rows if r.get('baseline_eligible') is True]


def first_challenge(days: list[dict], onset: Any, watch: dict | None = None) -> dict:
    by_offset = {d['offset']: d for d in days}
    if len(by_offset) != len(days):
        return {'status': 'FIRST_CHALLENGE_UNOBSERVABLE', 'C': None}
    for offset in range(21, 64):
        status = by_offset.get(offset, {}).get('status', 'UNKNOWN')
        if status == 'SHOCK':
            if watch is None:
                return {'status': 'CONTINUATION_UNOBSERVABLE', 'C': offset}
            if watch.get('onset') != onset:
                return {'status': 'ONSET_MISMATCH', 'C': offset}
            return {'status': 'ELIGIBLE' if watch.get('state') == 'continuation'
                    else 'NOT_CONTINUATION', 'C': offset}
        if status != 'NONSHOCK':
            return {'status': 'FIRST_CHALLENGE_UNOBSERVABLE', 'C': None}
    return {'status': 'NO_CHALLENGE', 'C': None}


def common_shock(history, today, market) -> dict:
    import numpy as np
    h = np.asarray(history, dtype=float)
    t = np.asarray(today, dtype=float)
    m = np.asarray(market, dtype=float)
    if (h.ndim != 2 or h.shape[0] != 252 or h.shape[1] < 20 or t.shape != (h.shape[1],)
            or m.shape != (252,) or not np.isfinite(t).all()):
        return {'status': 'UNKNOWN', 'complete_sessions': None}
    complete = np.isfinite(h).all(axis=1) & np.isfinite(m)
    n = int(complete.sum())
    if n < 200:
        return {'status': 'UNKNOWN', 'complete_sessions': n}
    prior = h[complete].mean(axis=1)
    sigma = float(prior.std(ddof=1))
    if sigma <= 0:
        return {'status': 'UNKNOWN', 'complete_sessions': n}
    p = float(t.mean())
    z = (p-float(prior.mean()))/sigma
    breadth = float((t < 0).mean())
    return dict(status='SHOCK' if p < 0 and z <= -1 and breadth >= .6 else 'NONSHOCK',
                complete_sessions=n, peer_return=p, peer_z=z, breadth=breadth)


def expected_move(subject, peers, market, *, subject_C: float, peer_C: float,
                  market_C: float) -> dict:
    """Frozen two-stage, same-window OLS; caller supplies only C-252..C-1."""
    import numpy as np
    r, p, m = [np.asarray(a, dtype=float) for a in (subject, peers, market)]
    if r.shape != (252,) or p.shape != r.shape or m.shape != r.shape:
        raise NotQualified('FACTOR_COVERAGE')
    if not all(_finite(a) for a in (subject_C, peer_C, market_C)):
        raise NotQualified('FACTOR_COVERAGE')
    complete = np.isfinite(r) & np.isfinite(p) & np.isfinite(m)
    n = int(complete.sum())
    if n < 200:
        raise NotQualified('FACTOR_COVERAGE')
    r, p, m = [a[complete] for a in (r,p,m)]
    stage1 = np.column_stack((np.ones(n),m))
    if np.linalg.matrix_rank(stage1) != 2:
        raise NotQualified('FACTOR_RANK')
    a_s,b_sm = np.linalg.lstsq(stage1,p,rcond=None)[0]
    orthogonal = p-stage1@np.array([a_s,b_sm])
    stage2 = np.column_stack((np.ones(n),m,orthogonal))
    if np.linalg.matrix_rank(stage2) != 3:
        raise NotQualified('FACTOR_RANK')
    a_i,b_m,b_s = np.linalg.lstsq(stage2,r,rcond=None)[0]
    residual = r-stage2@np.array([a_i,b_m,b_s])
    rmse = float(np.sqrt((residual@residual)/(n-3)))
    if not math.isfinite(rmse) or rmse <= 0:
        raise NotQualified('FACTOR_RMSE')
    expected = float(a_i+b_m*market_C+b_s*(peer_C-a_s-b_sm*market_C))
    return dict(training_n=n,intercept=float(a_i),market_beta=float(b_m),
                sector_beta=float(b_s),peer_intercept=float(a_s),peer_market_beta=float(b_sm),
                rmse=rmse,expected=expected,epsilon=subject_C-expected,
                z=(subject_C-expected)/rmse)


def onset_cutoff(sessions: list, archive_end) -> Any:
    eligible = [s for s in sessions if s <= archive_end]
    if len(eligible) < 127 or len(set(sessions)) != len(sessions) or sessions != sorted(sessions):
        raise NotQualified('MASTER_SESSION_CUTOFF_UNAVAILABLE')
    return eligible[-127]


def information_census(rows: list[dict]) -> dict:
    cells: dict[tuple, list] = defaultdict(list)
    for row in rows:
        if not _finite(row['z']) or type(row['date_index']) is not int or row['date_index'] < 0:
            raise NotQualified('INVALID_CENSUS_INPUT')
        cells[(row['date_index'], row['sector'])].append(row)
    singletons = zero = identifying = 0
    for cell in cells.values():
        issuers = [r['issuer'] for r in cell]
        if len(issuers) != len(set(issuers)):
            raise NotQualified('DUPLICATE_ISSUER_IN_CELL')
        if len(cell) < 2:
            singletons += 1
        elif len(set(r['z'] for r in cell)) == 1:
            zero += 1
        else:
            identifying += len(cell)
    dates = Counter(r['date_index'] for r in rows)
    sectors = Counter(r['sector'] for r in rows)
    return dict(rows=len(rows), issuers=len(set(r['issuer'] for r in rows)), dates=len(dates),
                cells=len(cells), singleton_cells=singletons, zero_within_cell_z_cells=zero,
                identifying_rows=identifying,
                occupied_63_session_blocks=len(set(r['date_index']//63 for r in rows)),
                date_counts=dict(sorted(dates.items())), sector_counts=dict(sorted(sectors.items())),
                information_scope='Input-only descriptive counts; not empirical power.')


def replay_detector(bars, benchmark_closes: dict, sectors, *, master_sessions=None) -> dict:
    """Full-prefix candidate replay using the incumbent Detector-D math/constants.

    sectors is an already source-qualified date-indexed GICS projection. Each
    date's benchmark is used for that date's entire trailing return comparison.
    Missing prior benchmark observations abort, rather than compress or use SPY.
    The retained master-session index must be independently calendar-qualified.
    """
    import numpy as np
    import pandas as pd
    from engine import winner_autopsy as w
    c = bars['close']
    if master_sessions is not None and not c.index.equals(master_sessions):
        raise NotQualified('MASTER_SESSION_MISMATCH')
    if (not c.index.is_unique or not c.index.is_monotonic_increasing or len(c) < 68
            or not np.isfinite(c).all() or (c <= 0).any()
            or 'volume' not in bars or not np.isfinite(bars['volume']).all()
            or (bars['volume'] < 0).any() or not sectors.index.equals(c.index)):
        raise NotQualified('UNOBSERVABLE_HISTORY')
    dv = w._dollar_volume_series(c, bars['volume'])
    high = c >= c.shift(1).rolling(w.NEW_HIGH_LOOKBACK).max()
    liquid = w._median_dv(dv, 20) >= w.LIQUIDITY_FLOOR_USD
    vol = (w._dv_zscore(dv, 21) >= w.DV_Z_FLOOR) | (w._dv_ratio(dv, 5, 60) >= w.DV_5_60_RATIO)
    candidates = pd.Series(False, index=c.index)
    for sector in sectors.unique():
        benchmark = w._GICS_ETF.get(sector)
        if benchmark is None or benchmark not in benchmark_closes:
            raise NotQualified('BENCHMARK_HISTORY')
        b = benchmark_closes[benchmark].reindex(c.index)
        exc21 = w.compute_excess(c,b,21)
        exc42 = w.compute_excess(c,b,42)
        for i in np.flatnonzero((sectors == sector).to_numpy()):
            if i < 63:
                continue
            # Both legs must have original scheduled observations, even when one
            # of the two excess gates suffices. No synthetic pre-inception index.
            leg = b.iloc[i-42:i+1]
            if not np.isfinite(leg).all() or (leg <= 0).any():
                raise NotQualified('BENCHMARK_HISTORY')
            candidates.iloc[i] = bool(liquid.iloc[i] and high.iloc[i] and vol.iloc[i]
                                      and (exc21.iloc[i] >= w.EXCESS_21D_PP
                                           or exc42.iloc[i] >= w.EXCESS_42D_PP))
    onsets = _onsets(candidates)
    return dict(onsets=onsets, candidates=candidates,
                sector_by_session=sectors, benchmark_scope='DATED_GICS_NO_FALLBACK')


def _onsets(candidates) -> list:
    from engine import winner_autopsy as w
    last = -w.EPISODE_COOLDOWN-1
    result = []
    for i, (dt, candidate) in enumerate(candidates.items()):
        if not candidate or i-last <= w.EPISODE_COOLDOWN:
            continue
        if i >= 21 and (dt-candidates.index[i-21]).days > 45:
            continue
        if i >= 42 and (dt-candidates.index[i-42]).days > 75:
            continue
        result.append(dt)
        last = i
    return result


def parent_parity(replay: dict, original_onsets: list) -> dict:
    actual = replay['onsets']
    return dict(status='REPRODUCED_EXACTLY' if actual == original_onsets else 'DIFFERENT_ONSET',
                original_count=len(original_onsets), reproduced_count=len(set(actual)&set(original_onsets)),
                different_count=len(set(original_onsets)-set(actual)))


def continuation(replay: dict, prefix_bars, original_D) -> dict:
    """C-1 watch, with 150-row detection boundary and last-five override.

    Reject a different trimmed-window onset. Do not infer this D's continuation
    from the full-prefix latest onset or from an unrelated latest watch row.
    """
    from engine import winner_autopsy as w
    candidates = replay['candidates']
    if not candidates.index.equals(prefix_bars.index):
        raise NotQualified('WATCH_PREFIX_MISMATCH')
    start = max(0, len(candidates)-w.WATCH_WINDOW_TD)
    # Canonical watch recomputes detection after trimming: first 63 rows lack
    # new-high history even if the complete earlier prefix had a candidate.
    trimmed = candidates.iloc[start:].copy()
    trimmed.iloc[:63] = False
    onsets = _onsets(trimmed)
    latest = onsets[-1] if onsets else None
    if latest != original_D or original_D not in replay['onsets']:
        return dict(status='ONSET_MISMATCH', state=None, onset=latest)
    c = prefix_bars['close']
    age = int((c.index > latest).sum())
    if age > w.EPISODE_COOLDOWN:
        return dict(status='NOT_CONTINUATION', state=None, onset=latest)
    state = ('failed' if c.iloc[-1] < c.loc[latest]
             else 'continuation' if c.iloc[-1] >= .95*c.iloc[-63:].max() else 'digestion')
    if candidates.iloc[-5:].any():
        state = 'breakaway'
    return dict(status='PASS' if state == 'continuation' else 'NOT_CONTINUATION',
                state=state, onset=latest)


def main() -> int:
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stdin', action='store_true', help='Bounded source-receipt JSON packet; no source paths opened.')
    args = parser.parse_args()
    # No arbitrary source paths, provider activation, or empirical execution
    # switch. Missing receipts produce a reproducible negative result.
    try:
        if args.stdin:
            text = sys.stdin.read(1_048_577)
            if len(text) > 1_048_576:
                raise NotQualified('INPUT_PACKET_TOO_LARGE')
            packet = json.loads(text)
            validate_input_graph(packet)
            if set(packet)-{'decision_at','sources','synthetic'}:
                raise NotQualified('INPUT_PACKET_UNKNOWN_FIELDS')
            results = [qualify(SourceQualificationResult(**r['receipt']), r['source_object'],
                               packet['decision_at']) for r in packet['sources']]
            report = qualification_report(results)
            report['REAL_DATA_READ'] = packet.get('synthetic') is not True
            report['input_packet_sha256'] = digest(packet)
        else:
            report = qualification_report([SourceQualificationResult(
                field_family=f, exclusion_codes=('SOURCE_NOT_DELIVERED',)) for f in FAMILIES])
    except (ValueError, TypeError, KeyError):
        report = qualification_report([])
        # Error messages describe schema/gates only, never raw input contents.
        report['BLOCKERS'] = ['INPUT_GRAPH_OR_PACKET_INVALID']
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0 if report['RESULT'] == 'SOURCE_QUALIFIED_FOR_INDEPENDENT_REVIEW' else 2


if __name__ == '__main__':
    raise SystemExit(main())
