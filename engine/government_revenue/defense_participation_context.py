"""Read the incumbent GroupPulse snapshot; never publish or advance its ledger.

Participation is basket market breadth, not a procurement relationship. The
existing algorithm must reproduce the displayed owner fields from the exact
current member tapes and SPY basis. This confers no historical/PIT, scientific,
ranking or capital-flow authority on those current descriptive observations.
"""
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re

from engine.company_intelligence.defense_profiles import defense_issuer
from lib import nyse_calendar

OWNER_PATHS = (
    'data/baskets/membership.json',
    'site/basketdata/pulse.json',
    'site/basketdata/baskets.json',
    'data/yahoo/SPY.parquet',
)


def _instant(value):
    value = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('participation_clock_timezone_required')
    return value


def _checked_path(root, relative):
    path = root / relative
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError('participation_input_symlink_refused')
    if path.exists() and not path.is_file():
        raise ValueError('participation_input_not_regular_file')
    return path


def participation_input_paths(root):
    """Exact owner dependency inventory, including explicit absent inputs."""
    root = Path(root)
    paths = set(OWNER_PATHS)
    marker = _checked_path(root, OWNER_PATHS[0])
    if marker.is_file():
        membership = json.loads(marker.read_bytes())
        members = membership['baskets']['defense']['members']
        for member in members:
            ticker = member['ticker']
            if not isinstance(ticker, str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,15}', ticker):
                raise ValueError('participation_member_path_invalid')
            # Retained/removed members are inexpensive explicit dependencies too;
            # a membership revision must invalidate the same receipt.
            paths.add(f'data/baskets/ohlcv/{ticker}.parquet')
    for relative in paths:
        _checked_path(root, relative)
    return tuple(sorted(paths))


def _hashes(root, paths):
    return {p: sha256((root / p).read_bytes()).hexdigest() if (root / p).is_file() else 'absent' for p in paths}


def load_participation_inputs(root):
    """Capture and replay before the consuming generation clock is minted.

    Absent offline inputs stay absent. Present but contradictory inputs refuse
    publication. No source file, owner snapshot or episode ledger is modified.
    """
    from engine import group_pulse as gp
    import pandas as pd

    root = Path(root).resolve()
    paths = participation_input_paths(root)
    before = _hashes(root, paths)
    if any(before[p] == 'absent' for p in OWNER_PATHS):
        return None
    raw = {p: (root / p).read_bytes() for p in OWNER_PATHS[:3]}
    membership, pulses, baskets = (json.loads(raw[p]) for p in OWNER_PATHS[:3])
    pulse = pulses.get('defense')
    if gp.validate_pulse(pulse):
        raise ValueError('participation_pulse_invalid')
    market_date = pd.Timestamp(pulse['as_of'])
    if pulse['basket_id'] != 'defense' or market_date.tzinfo is not None:
        raise ValueError('participation_basket_identity_invalid')
    basket = membership['baskets']['defense']
    members = gp.live_members(basket, market_date)
    selected = [b for b in baskets['baskets'] if b['id'] == 'defense']
    if len(selected) != 1:
        raise ValueError('participation_basket_missing_or_ambiguous')
    owner = selected[0]
    observation = owner['observation']
    if (baskets['as_of'] != pulse['as_of'] or observation['effective_as_of'] != pulse['as_of']
            or owner['n_members'] != len(members) or pulse['n_members'] != len(members)
            or sorted(observation['configured_members']) != members
            or sorted(m['symbol'] for m in owner['members']) != members
            or observation['basis'] != 'exact_close_at_effective_as_of'
            or owner['weighting'] != 'equal'):
        raise ValueError('participation_membership_or_cutoff_mismatch')
    closes, volumes, missing = gp.load_member_tape(members, root / 'data')
    if missing or market_date not in closes.index:
        return None
    # gp.load_benchmark first consults a process-global store. Read its exact
    # documented parquet fallback here so another checkout cannot supply SPY.
    benchmark_frame = pd.read_parquet(root / OWNER_PATHS[3])
    benchmark_frame.index = pd.DatetimeIndex(pd.to_datetime(benchmark_frame.index))
    benchmark = benchmark_frame['close'].astype('float64').dropna().sort_index()
    if benchmark.empty or benchmark.index.has_duplicates or market_date not in benchmark.index:
        raise ValueError('participation_benchmark_unavailable')
    panel = gp.build_member_panel(closes, volumes, benchmark)
    participation, sets = gp._participation(panel, market_date, members)
    direction = gp._direction(sets, panel, market_date)
    selected_direction = ('agreement_pct', 'n_active', 'sign', 'leader')
    if (participation != pulse['participation'] or len(sets['covered']) != pulse['n_covered']
            or any(direction[k] != pulse['direction'][k] for k in selected_direction)):
        raise ValueError('participation_owner_replay_mismatch')
    observed_members = sorted(t for t in members if pd.notna(closes.at[market_date, t]))
    if (sorted(observation['observed_members']) != observed_members
            or observation['observed_n'] != len(observed_members)
            or observation['configured_n'] != len(members)
            or observation['coverage'] != len(observed_members) / len(members)):
        raise ValueError('participation_observation_denominator_mismatch')
    if paths != participation_input_paths(root) or before != _hashes(root, paths):
        raise ValueError('participation_inputs_changed_during_read')
    observed_at = datetime.now(timezone.utc).isoformat()
    if _instant(pulse['generated_at']) > _instant(observed_at) or market_date.date() > _instant(pulse['generated_at']).date():
        raise ValueError('participation_owner_future_clock')
    provenance_dates = [membership['version'], membership.get('curated'), basket['curated']]
    provenance_dates.extend(m.get('curated_added') for m in basket['members'])
    if any(date.fromisoformat(value) > _instant(observed_at).date() for value in provenance_dates if value is not None):
        raise ValueError('participation_membership_future_curation')
    return {'raw_bytes': raw, 'source_sha256': before, 'observed_at': observed_at,
            'covered_members': sets['covered'], 'active_members': sets['active']}


def qualify_participation_context(inputs, financial_inputs, *, generated_at):
    """Bind already-replayed current basket context to qualified member issuers."""
    empty = {'axes_by_ticker': {}, 'source_bindings': {}, 'local_proof': {'state': 'owner_absent'}}
    if inputs is None:
        return empty
    cutoff = _instant(generated_at)
    if _instant(inputs['observed_at']) > cutoff:
        # A current read must never become a historical observation.
        return {**empty, 'local_proof': {'state': 'observation_after_cutoff'}}
    raw = inputs['raw_bytes']
    if set(raw) != set(OWNER_PATHS[:3]) or any(sha256(raw[p]).hexdigest() != inputs['source_sha256'][p] for p in raw):
        raise ValueError('participation_owner_bytes_mismatch')
    membership, pulses, baskets = (json.loads(raw[p]) for p in OWNER_PATHS[:3])
    pulse = pulses['defense']
    market_date = pulse['as_of']
    if _instant(pulse['generated_at']) > cutoff:
        raise ValueError('participation_owner_after_cutoff')
    from engine import group_pulse as gp
    import pandas as pd
    members = gp.live_members(membership['baskets']['defense'], pd.Timestamp(market_date))
    part, direction = pulse['participation'], pulse['direction']
    if (len(inputs['covered_members']) != pulse['n_covered'] or len(inputs['active_members']) != part['activity_n']
            or not set(inputs['active_members']) <= set(inputs['covered_members']) <= set(members)):
        raise ValueError('participation_replay_sets_invalid')
    leader = direction['leader']['ticker'] if direction['leader'] else None
    n, covered, active = len(members), pulse['n_covered'], part['activity_n']
    def share(value):
        return 'unavailable' if value is None else f'{value * 100:.1f}%'
    vintage = membership['version']
    curated = membership['baskets']['defense']['curated']
    text_en = (f'Defense basket at {market_date}: {active}/{covered} covered members active ({share(part["activity_share"])}); '
               f'{covered}/{n} configured members covered. Above 50-day / 200-day average: '
               f'{share(part["trend_share_50d"])} of {part["trend_n_50d"]} / {share(part["trend_share_200d"])} of {part["trend_n_200d"]}. '
               f'Activity leader: {leader or "unavailable"}, not an alpha leader. Equal-weight, monthly rebalance; '
               f'current membership version {vintage}, defense curation {curated}, not historical first-seen membership. '
               f'Owner assembled {pulse["generated_at"]}. Coverage requires 63 return sessions; activity means unusually large '
               'SPY-adjusted absolute return OR elevated volume (when available); '
               'this is not capital flow or a market-cap concentration estimate.')
    text_zh = (f'国防篮子截至{market_date}：已覆盖成员中{active}/{covered}活跃（{share(part["activity_share"])}）；'
               f'已覆盖{covered}/{n}个配置成员。高于50日／200日均线：{part["trend_n_50d"]}个中的{share(part["trend_share_50d"])}／'
               f'{part["trend_n_200d"]}个中的{share(part["trend_share_200d"])}。活跃度领先者：{leader or "暂无"}，并非超额收益领先者。'
               f'等权、每月再平衡；当前成员版本{vintage}，国防篮子整理日期{curated}，并非历史首次获知成员。'
               f'原来源生成时间{pulse["generated_at"]}。覆盖要求63个回报交易日；活跃指经SPY调整的绝对回报异常增大，'
               '或成交量异常增加（有数据时）；不表示资金流或市值集中度。')
    bindings, axes = {}, {}
    for ticker, financial in financial_inputs.items():
        if ticker not in members:
            continue
        identity = financial['identity']
        issuer, security = identity['issuer_binding']['issuer_id'], identity['security_id']
        expected = defense_issuer(ticker)
        if issuer != expected.company_id or security not in expected.security_ids_at(cutoff.date()):
            raise ValueError('participation_financial_subject_mismatch')
        refs = []
        for label, path in zip(('membership', 'pulse', 'baskets'), OWNER_PATHS[:3]):
            digest = inputs['source_sha256'][path]
            ref = f'group_pulse:defense:{label}:{digest}:{ticker}'
            refs.append(ref)
            bindings[ref] = {'sha256': digest, 'content_id': f'defense:{label}:{digest}',
                             'contract': 'group_pulse.v1' if label == 'pulse' else 'basket_current_snapshot',
                             'owner_family': 'group_reads', 'issuer_id': issuer, 'security_id': security,
                             'periods': [market_date], 'observed_at': inputs['observed_at'], 'owner_admission_ref': path}
        axes[ticker] = {'participation': {
            'display_scope': 'government_revenue_entitled',
            'state': 'stale' if nyse_calendar.sessions_behind(date.fromisoformat(market_date), now=cutoff) else 'partial',
            'summary_en': text_en, 'summary_zh': text_zh, 'owner_ref': refs[1], 'evidence_refs': refs,
            'observed_at': inputs['observed_at'], 'fiscal_period': None, 'facts': [],
            'reason_code': 'current_basket_market_participation',
            'limitations': ['basket_context_not_issuer_alpha', 'current_membership_not_historical_first_seen',
                            'activity_not_capital_flow', 'capital_concentration_not_measured',
                            'spy_adjusted_activity_basis', 'volume_usable_not_volume_trigger',
                            'no_scientific_or_rights_reclassification']}}
    return {'axes_by_ticker': axes, 'source_bindings': bindings,
            'local_proof': {'state': 'replayed_current_group_context', 'market_as_of': market_date,
                            'observed_at': inputs['observed_at'], 'source_sha256': inputs['source_sha256']}}
