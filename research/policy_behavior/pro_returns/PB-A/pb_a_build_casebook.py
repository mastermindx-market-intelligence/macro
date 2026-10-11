#!/usr/bin/env python3
"""Normalize reviewed official-source annotations; no outcome source is read by build.

build: write decision-only casebook and strict forecast inputs.
assemble: add already frozen forecasts and separately scored outcomes to the casebook.
Source annotations are retrospective documentary reconstruction, not archived bytes.
"""
import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
NY = ZoneInfo('America/New_York')
PROTOCOL_COMMIT = '99253212652ba7d1248a587c249da44ec6e3b9b6'
PACKETS = ['early_fed_sources', 'recent_fed_sources', 'treasury_sources']
WEAK = {'initial_b1_2020-03-23', 'initial_b2_2020-03-23',
        'initial_b3_2020-03-23', 'strategy_pdf_2020-08-27', 'terms20230312'}
EARLY_RATES = {
 'FED_20181219_FOMC': (2.25, 2.50, 'UP', '2018-12-20'),
 'FED_20190130_FOMC': (2.25, 2.50, 'HOLD', '2019-01-31'),
 'FED_20190731_FOMC': (2.00, 2.25, 'DOWN', '2019-08-01'),
 'FED_20200303_EMERGENCY_CUT': (1.00, 1.25, 'DOWN', None),
 'FED_20200315_EMERGENCY_EASING': (0.00, 0.25, 'DOWN', '2020-03-16'),
}
TENSION_NOTES = {
 'FED_20190130_FOMC': 'Patient rate guidance coexists with continued runoff, while balance-sheet flexibility is announced; instrument and horizon tension, not contradictory current rate directions.',
 'FED_20191011_RESERVE_MANAGEMENT': 'Balance-sheet expansion serves reserve control while officials describe the monetary stance as unchanged; quantities and stance are distinct.',
 'FED_20200303_EMERGENCY_CUT': 'Statement retains a strong-fundamentals assessment while making an emergency 50bp cut in response to new risks; forecast/insurance tension, not proof of dishonesty.',
 'FED_20200323_FACILITIES_AND_PURCHASES': 'Broad support objective is implemented through particular credit channels, while Main Street is only a prospective program; targeted access is not universal relief.',
}

def read(name):
    return json.loads((ROOT / name).read_text())

def write(name, obj):
    (ROOT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dt(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))

def iso(d):
    return d.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

def date_bounds(d):
    a = datetime.fromisoformat(d).replace(tzinfo=NY)
    return {'earliest_utc': iso(a), 'latest_exclusive_utc': iso(a + timedelta(days=1))}

def ids_in(value):
    found = set()
    if isinstance(value, dict):
        for k, v in value.items():
            if k in ('source_ids', 'prior_public_sources') and isinstance(v, list):
                found.update(x for x in v if isinstance(x, str))
            else:
                found.update(ids_in(v))
    elif isinstance(value, list):
        for item in value:
            found.update(ids_in(item))
    return found

def remove_source_ids(value, excluded):
    if isinstance(value, dict):
        for k, v in value.items():
            if k == 'source_ids' and isinstance(v, list):
                value[k] = [x for x in v if x not in excluded]
            else:
                remove_source_ids(v, excluded)
    elif isinstance(value, list):
        for item in value:
            remove_source_ids(item, excluded)

def normalize_source(s, packet):
    x = copy.deepcopy(s)
    sid = s['source_id']
    url = s['url']
    x['annotation_packet'] = packet + '.json'
    x['canonical_document_id'] = 'DOC_' + hashlib.sha256(url.encode()).hexdigest()[:16]
    # Distinct documents of the same policy institution are not independent testimony.
    if 'treasury' in url:
        family = 'US_TREASURY'
    elif 'newyorkfed.org' in url:
        family = 'FEDERAL_RESERVE_SYSTEM'
    else:
        family = 'FEDERAL_RESERVE_SYSTEM'
    x['originator_family'] = family
    x['originator_families'] = [family]
    if sid == 'joint20230312':
        x['originator_family'] = 'JOINT_FED_TREASURY_FDIC'
        x['originator_families'] = ['FEDERAL_RESERVE_SYSTEM', 'US_TREASURY', 'FDIC']
    x['independence_note'] = 'Official issuer document; repeated URLs/attachments and statements of the same institution are correlated evidence, not independent corroboration.'
    c = s.get('publication_clock', s.get('clock', {}))
    timestamp = s.get('publication_timestamp_utc') or c.get('utc') or c.get('publication_utc')
    role = s.get('role', '')
    clock_kind = c.get('clock_kind', '')
    archaeology = ('archaeology' in role or 'ARCHAEOLOGY' in clock_kind
                   or sid.startswith('clock') or sid == 'TREASURY_BUYBACK_INDEX_CURRENT')
    precision = c.get('precision', s.get('time_precision', 'UNKNOWN')).upper()
    evidence = c.get('evidence', c.get('clock_evidence', s.get('clock_basis', 'Dated official source header.')))
    if sid in ('jh20220826', 'jhclock20220826'):
        clock_kind = 'OFFICIAL_RELEASE_ON_DELIVERY_TIME'
        evidence += ' Documentary prepared-text release time; not proof that each passage had been spoken by the cut.'
    if sid == 'TREASURY_TENTATIVE_BUYBACK_Q22024':
        evidence = 'PDF explicitly states For Publication May 1st, 2024; no public release minute is established.'
    if sid == 'TREASURY_BBR_20240529174000':
        evidence = 'PDF immediate-release header explicitly dates publication May 29, 2024. Filename 174000 identifies operation-start association, not posting time.'
    interval = c.get('public_time_interval_utc', {})
    lower = c.get('interval_start_utc') or interval.get('earliest')
    upper = c.get('interval_end_exclusive_utc') or interval.get('latest_exclusive')
    pub_date = c.get('publication_date', c.get('local_date', s.get('publication_date')))
    if not timestamp and not upper and pub_date and re.fullmatch(r'\d{4}-\d{2}-\d{2}', pub_date):
        bounds = date_bounds(pub_date)
        lower, upper = bounds['earliest_utc'], bounds['latest_exclusive_utc']
    if sid in WEAK:
        grade = 'PARENT_LINK_ASSOCIATION_QUARANTINED'
        role_canonical = 'CLOCK_OR_VERSION_CONTEXT_ONLY'
        clock_kind = 'PARENT_LINK_ASSOCIATION_NOT_INDEPENDENT_PUBLICATION_CLOCK'
        # Remove falsely precise inherited timestamps from the canonical clock.
        timestamp = None
        evidence += ' Parent-link association is retained as uncertainty; attachment-only facts are excluded from the certified decision block.'
        bound = None
    elif archaeology:
        grade = 'ARCHAEOLOGY_ONLY'
        role_canonical = 'CLOCK_OR_VERSION_CONTEXT_ONLY'
        bound = None
    elif timestamp:
        grade = 'DOCUMENTARY_MINUTE'
        role_canonical = 'ELIGIBLE_IF_BEFORE_EPISODE_CUT'
        bound = iso(dt(timestamp) + timedelta(minutes=1))
    elif upper:
        grade = 'DOCUMENTARY_DATE'
        role_canonical = 'ELIGIBLE_IF_BEFORE_EPISODE_CUT'
        bound = upper
    else:
        grade = 'UNRESOLVED_CLOCK'
        role_canonical = 'CLOCK_OR_VERSION_CONTEXT_ONLY'
        bound = None
    x['canonical_clock'] = {
        'precision': precision if sid not in WEAK else 'PARENT_ASSOCIATION_ONLY',
        'grade': grade, 'kind': clock_kind or 'OFFICIAL_DOCUMENTARY_HEADER',
        'nominal_publication_utc': timestamp,
        'interval_start_utc': lower,
        'interval_end_exclusive_utc': upper,
        'public_time_upper_bound_utc': bound,
        'bound_rule': 'Minute-only evidence is conservatively bounded by the end of its displayed minute; date-only evidence by next local midnight. These are documentary bounds, not server telemetry.',
        'evidence': evidence,
    }
    x['canonical_role'] = role_canonical
    return x

def repair_weak_annotations(e, decision):
    """Quarantine attachment-only detail, preserving reviewed headline evidence."""
    excluded = sorted(set(e['source_ids']) & WEAK)
    audit = []
    if excluded:
        audit.append({'source_ids': excluded, 'disposition': 'QUARANTINED_FROM_CERTIFIED_DECISION_BLOCK',
                      'reason': 'Original-parent association does not independently establish attachment publication before this cut.',
                      'original_annotation_locator': 'source_packets/' + e['_packet'] + '.json#/episodes; match episode_id',
                      'forecast_impact': 'NONE: neither attachment details nor motive text is accepted by the predictor.'})
    remove_source_ids(decision, WEAK)
    if e['episode_id'] == 'FED_20200323_FACILITIES_AND_PURCHASES':
        decision['constraints'] = [decision['constraints'][0],
            'Facilities cover named credit markets/instruments; fine credit-rating, maturity, issuer-limit and haircut details from parent-linked term sheets are quarantined from the intraday block.']
        decision['feasible_alternatives'][1] = {
            'alternative': 'Add immediate direct support for additional businesses beyond the announced credit channels.',
            'evidence': 'Main Street lending is expected in the future in the timed headline; exact legal/operational feasibility of broader immediate coverage is not established.',
            'consideration_status': 'FUTURE_PROGRAM_ANNOUNCED_NOT_A_REJECTED_EQUIVALENT',
            'source_ids': ['facilities_2020-03-23']}
        decision['strategic_distribution'] = {
            'direct_beneficiaries': ['Corporate financing and eligible ABS credit channels, specified money-market and municipal funding channels.'],
            'indirect_beneficiaries': ['Workers, suppliers and borrowers through intended credit transmission; an inference, not observed flows.'],
            'burden_bearers': ['Public institutions take contingent credit exposure; businesses outside initially operational channels lack equivalent immediate program access.'],
            'selective_relief_present': 'YES',
            'selectivity_rationale': 'Named instruments and channels; Main Street is prospective. Fine term-sheet eligibility and covenants are quarantined.',
            'changes': ['Authorized financing access/backstop, not demonstrated cash lending.']}
        decision['competing_hypotheses'][0]['evidence_for'] = ['Market functioning and credit transmission objectives; Section13(3), Treasury approval and equity support in the timed release.']
        decision['competing_hypotheses'][1]['evidence_for'] = ['Corporate/ABS credit facilities announced immediately; Main Street only expected.']
    if e['episode_id'] == 'FED_TREASURY_2023_03_12_BTFP':
        a = decision['actions'][0]
        a['magnitude']['loan_rate'] = None
        a['magnitude']['loan_rate_status'] = 'PARENT_LINKED_TERMS_QUARANTINED'
        a['effective_window'] = 'March12 announcement offers loans up to one year; exact new-advance deadline from attachment is quarantined.'
        a['target'] = 'Banks and other eligible depository institutions with qualifying Treasury, agency debt or mortgage-backed securities as described in the headline.'
        a['legal_authority_note'] = 'Headline documents Board action and Treasury approval of an ESF backstop. Detailed recourse/legal terms are not independently clock-certified here.'
        a['mechanical_transmission_channels'] = [
            'Par collateral valuation supports liquidity despite market-value losses, potentially reducing forced sales.',
            '$25bn is Treasury backstop availability, not loan volume or a proved cash transfer.']
        decision['constraints']['institutional'] = [{'fact': 'Distinct Treasury/Fed/FDIC roles, named-bank resolution protection and special assessment; headline describes eligible collateral and borrowers.', 'source_ids': ['joint20230312', 'btfp20230312']}]
        decision['strategic_distribution']['burden_bearers'][-1]['mechanism'] = 'Authorized credit exposure and backstop; realized losses unknown.'
        decision['competing_hypotheses'][0]['evidence_for'] = ['Collateralized liquidity, bank-loss assessment, explicit equity exclusion and no rate decision in the two timed headlines.']
    for a in decision['actions']:
        if a.get('executed_flow_receipt'):
            if a.get('status') != 'EXECUTED_ALLOCATION':
                raise ValueError('Unexpected executed flow claim')
            a['executed_flow_receipt'] = False
            a['accepted_allocation_receipt_present'] = True
            a['completed_settlement_receipt_present'] = False
            a['execution_scope'] = 'Accepted offers only; settlement scheduled for next day. No proved settled cash or reserve injection.'
    return audit

def build():
    protocol = read('PB_A_PROTOCOL_FREEZE.json')
    inputs_path = ROOT / 'PB_A_DECISION_INPUTS.json'
    frozen = (read('PB_A_DECISION_INPUTS.json')['meta']['coding_frozen_at_utc']
              if inputs_path.exists() else iso(datetime.now(timezone.utc).replace(microsecond=0)))
    all_sources, raw_episodes, packet_hashes = [], [], {}
    for name in PACKETS:
        data = read('source_packets/' + name + '.json')
        packet_hashes[name + '.json'] = sha(ROOT / 'source_packets' / (name + '.json'))
        all_sources.extend(normalize_source(s, name) for s in data['sources'])
        for e in data['episodes'] + data.get('optional_challenge_episodes', []):
            e['_packet'] = name
            raw_episodes.append(e)
    catalog = {s['source_id']: s for s in all_sources}
    assert len(catalog) == len(all_sources), 'Duplicate source IDs'
    canonical_aliases = {}
    for s in all_sources:
        canonical_aliases.setdefault(s['canonical_document_id'], []).append(s['source_id'])
    for s in all_sources:
        s['same_url_aliases'] = canonical_aliases[s['canonical_document_id']]
    episodes, model_inputs = [], []
    for raw in sorted(raw_episodes, key=lambda x: (x['decision_cut_utc'], x['episode_id'])):
        eid, cut = raw['episode_id'], raw['decision_cut_utc']
        event_date = raw.get('event_date', raw.get('episode_date')) or raw['first_public_evidence_utc'][:10]
        regime = next(r['id'] for r in protocol['regimes'] if r['start'] <= event_date <= r['end'])
        cohort = 'ADVERSARIAL_CHALLENGE' if eid.startswith('CHALLENGE_') else 'PRIMARY'
        split = 'DEVELOPMENT' if event_date < '2023-01-01' else 'CHRONOLOGICAL_REPORT'
        old = raw['decision_time']
        proposed = old.get('proposed_feature_codes', {})
        decision = {
            'rhetoric': copy.deepcopy(old['rhetoric']),
            'actions': copy.deepcopy(old['actions']),
            'constraints': copy.deepcopy(old['constraints']),
            'feasible_alternatives': copy.deepcopy(old.get('feasible_alternatives', old.get('alternatives'))),
            'strategic_distribution': copy.deepcopy(old.get('strategic_distribution', old.get('distribution'))),
            'competing_hypotheses': copy.deepcopy(old['competing_hypotheses']),
            'pre_cut_market_expectations': {'status': 'MISSING_NOT_RECONSTRUCTED', 'policy_surprise_scoring': 'BLOCKED', 'reason': 'No pre-cut futures/OIS or equivalent pricing snapshot. Official rhetoric/SEP is not market pricing.'},
            'private_intent_status': 'UNRESOLVED',
            'institutional_rationale_status': 'STRONG_COMPETING_EXPLANATION_NOT_PROVEN_EXCLUSIVE_MOTIVE',
            'institutional_rationale_basis': copy.deepcopy(old['competing_hypotheses'][0]),
        }
        audit = repair_weak_annotations(raw, decision)
        decision['institutional_rationale_basis'] = copy.deepcopy(decision['competing_hypotheses'][0])
        for r in decision['rhetoric']:
            r['source_ids'] = r.get('source_ids') or ([r['source_id']] if r.get('source_id') else [])
            r['faithful_paraphrase'] = r.get('faithful_paraphrase', r.get('paraphrase'))
            if eid == 'US_FED_TREASURY_20200409_FACILITIES' and r.get('source_id') == 'FED_MONETARY_20200409A':
                r['faithful_paraphrase'] = r['paraphrase'] = 'Fed framed the facilities as relief and financial stability support through the pandemic.'
            if eid == 'US_TREASURY_20240529_FIRST_LIQUIDITY_BUYBACK_RESULTS' and r.get('source_id') == 'TREASURY_JY2315':
                r['faithful_paraphrase'] = r['paraphrase'] = 'May1 operational guidance announced intended scheduled liquidity-support buybacks with a temporary security cap; May29 reports allocations, not a new macroeconomic forecast.'
            r['explicit_horizon'] = r.get('explicit_horizon', r.get('horizon', 'UNSPECIFIED'))
            r['ambiguity_conditionality'] = r.get('ambiguity_conditionality') or r.get('conditionality') or r.get('ambiguity') or 'See faithful paraphrase; no unconditional calendar guarantee inferred.'
            r['evidence_publication_clocks'] = [
                {'source_id': sid, 'clock': catalog[sid]['canonical_clock']}
                for sid in r.get('source_ids', [])]
        for a in decision['actions']:
            if 'target' not in a:
                a['target'] = {'instrument_target': a.get('instrument'), 'counterparty_detail': 'See direct beneficiaries and source; no unobserved individual counterparty inferred.'}
            if 'mechanical_transmission_channels' not in a:
                a['mechanical_transmission_channels'] = [a.get('mechanical_transmission', 'Instrument changes authorized policy, funding or credit conditions as described; magnitude of realized transmission is not certified by this announcement.')]
        for h in decision['competing_hypotheses']:
            if 'new_observation_to_rerank' not in h:
                h['new_observation_to_rerank'] = h.get('material_re_rank_observation', {'research_need': 'Observe evidence testing the following specified falsifiers; no such future evidence is used as an input.', 'observable_tests': h['falsifiers']})
        decision['market_controls'] = {'pre_event_expectations': 'MISSING', 'rate_regime': regime, 'volatility': 'NOT_RECONSTRUCTED', 'market_sector_state': 'Qualitative source context only; no synchronized panel', 'prior_issuer_sector_momentum': 'NOT_APPLICABLE_TO_FOCAL_US_POLICY_ISSUER; no sector-return inference'}
        decision['calendar_controls'] = copy.deepcopy(raw.get('calendar_controls', {'status': 'Documented policy/release dates only; exhaustive coincident-event control not reconstructed.'}))
        decision['action_persistence_after_cost_visible'] = 'UNKNOWN'
        decision['persistence_coding_limit'] = 'Sources may describe salient costs, but a comparable pre-cut adverse-cost and repeated-choice panel was not separately reconstructed. No predictive contribution from this field is claimed.'
        decision['alternative_lower_cost_path_visible'] = 'UNKNOWN'
        distribution = decision['strategic_distribution']
        selective = distribution.get('selective_relief_present', distribution.get('selective_relief', 'UNKNOWN'))
        decision['selective_relief_present'] = next((x for x in ['YES', 'NO'] if str(selective).startswith(x)), 'UNKNOWN')
        proposed_dir = proposed.get('rhetoric_direction', 'ABSTAIN')
        m0 = 'ABSTAIN' if eid == 'FED_20191011_RESERVE_MANAGEMENT' else proposed_dir
        if eid in EARLY_RATES:
            lo, hi, action_dir, effective = EARLY_RATES[eid]
            known = {'lower_pct': lo, 'upper_pct': hi, 'decision_utc': raw['first_public_evidence_utc'], 'effective_date': effective, 'status': 'KNOWN_DECIDED'}
        else:
            a = next((a for a in old['actions'] if a.get('instrument') == 'FED_FUNDS_TARGET_RANGE'), None)
            if a:
                mag = a['magnitude']
                lo, hi = mag['lower_percent'], mag['upper_percent']
                action_dir = 'UP' if mag['change_bp'] > 0 else 'DOWN' if mag['change_bp'] < 0 else 'HOLD'
                known = {'lower_pct': lo, 'upper_pct': hi, 'decision_utc': raw['first_public_evidence_utc'], 'effective_date': a.get('effective_date'), 'status': 'KNOWN_DECIDED'}
            else:
                known, action_dir, hi = None, 'NOT_RATE', None
        relation = old.get('rhetoric_action_direction_relation', old.get('rhetoric_action_relation', ''))
        descriptive = copy.deepcopy(old.get('descriptive_tension', {}))
        if eid in TENSION_NOTES:
            descriptive = {'classification': 'MIXED', 'tension_present': True, 'evidence': TENSION_NOTES[eid], 'scope': 'Descriptive tension across goals/instruments/horizons', 'deception_inference': False}
        if not descriptive:
            descriptive = {'classification': relation, 'tension_present': relation == 'MIXED', 'evidence': relation, 'deception_inference': False}
        current_aligned = (m0 in ('UP', 'DOWN') and m0 == action_dir) or relation.startswith('ALIGNED')
        if eid in ('FED_20190130_FOMC', 'FED_2021_11_03_TAPER', 'FED_2024_05_01_QT_TAPER'):
            current_aligned = True  # current policy-rate stance/guidance while other instruments differ.
        tags = {'rhetoric_action_alignment': bool(current_aligned), 'rhetoric_action_divergence_or_tension': bool(descriptive.get('tension_present')), 'intent_unresolved': True, 'strong_institutional_explanation': True}
        decision['rhetoric_action_assessment'] = descriptive
        decision['rhetoric_action_direction_relation'] = ('MIXED' if descriptive.get('tension_present') else 'ALIGNED' if current_aligned else 'NOT_COMPARABLE')
        decision['assessment_note'] = 'Alignment/tension labels may overlap across instruments and horizons; neither establishes honesty, deception, exclusive motive or causality.'
        # Admit only actual case sources plus explicitly referenced prior context, never every registered source.
        wanted = set(raw['source_ids']) | ids_in(decision) | set(old.get('prior_public_sources', []))
        admitted, excluded = [], []
        for sid in sorted(wanted):
            if sid not in catalog:
                raise ValueError(f'Unresolved source reference {eid}: {sid}')
            s = catalog[sid]
            bound = s['canonical_clock']['public_time_upper_bound_utc']
            if bound and dt(bound) <= dt(cut) and sid not in WEAK:
                admitted.append(sid)
            else:
                excluded.append({'source_id': sid, 'reason': s['canonical_clock']['grade'] if not bound else 'PUBLIC_TIME_BOUND_AFTER_CUT'})
        remove_source_ids(decision, set(catalog) - set(admitted))
        assert len(decision['competing_hypotheses']) >= 2
        assert all(h.get('falsifiers') for h in decision['competing_hypotheses'])
        features = {'rhetoric_forward_direction': m0,
                    'has_new_rate_decision': known is not None,
                    'rate_decision_direction': action_dir,
                    'decided_target_upper_pct': hi if known else None}
        feature_sources = [x for x in admitted if not x.startswith('clock')]
        bounds = [{'source_id': sid, 'public_time_upper_bound_utc': catalog[sid]['canonical_clock']['public_time_upper_bound_utc'], 'role': 'DECISION_TIME_FACT'} for sid in feature_sources]
        input_row = {'episode_id': eid, 'event_date': event_date, 'decision_cut_utc': cut,
                     'cohort': cohort, 'regime': regime, 'split': split,
                     'features': features, 'feature_source_ids': feature_sources,
                     'source_time_bounds': bounds, 'known_rate_decision': known}
        model_inputs.append(input_row)
        decision['frozen_baseline_features'] = copy.deepcopy(features)
        decision['feature_coding_rationale'] = {
            'rhetoric': ('Current-stance maintenance statement has no clean future-rate direction; C03 overrides helper HOLD proposal.' if eid == 'FED_20191011_RESERVE_MANAGEMENT' else proposed.get('rhetoric_rationale', proposed.get('justification', 'Treasury/liquidity instrument has no clean focal Fed policy-rate implication.'))),
            'horizon': proposed.get('rhetoric_horizon', proposed.get('horizon', 'No clean rate path')),
            'horizon_extrapolation_assumption': 'A coded clean focal path is applied mechanically to all three calendar horizons; official communication does not promise these endpoints.',
            'action': 'Persist only a new focal rate decision; a rate mentioned as existing operational context is not a new decision.',
            'floor': 'A newly cut 0–0.25% conventional target maps M2 to HOLD. Negative rates are not coded as legally impossible.',
            'qualitative_information_usage': 'All motives, beneficiaries, constraints prose and alternatives excluded from the four-key predictor. The only constraint in M2 is the explicit conventional-floor rule.',
        }
        headline = raw.get('first_public_evidence_utc')
        certificate = {
            'historical_documentary_source_time_certified': True,
            'certificate_scope': 'Reviewed original official documentary content before a declared historical cut at the recorded clock precision. Does not certify contemporaneous served bytes, server first-post time, market expectations, realized lending/settlement, private intent or causal effects.',
            'first_public_evidence_precision': 'MINUTE' if headline else 'DATE_ONLY',
            'first_public_evidence_utc': headline,
            'first_public_evidence_interval_utc': None if headline else date_bounds(event_date),
            'cut_policy': 'INTRADAY_DOCUMENTARY_BOUND' if dt(cut).astimezone(NY).date().isoformat() == event_date else 'NEXT_LOCAL_MIDNIGHT_DATE_BOUND',
            'admitted_source_ids': admitted, 'excluded_source_ids': excluded,
            'attachment_audit': audit,
            'historical_byte_snapshot_available': False,
            'publication_seconds_observed': False,
            'market_expectations_certified': False,
        }
        uncertainties = copy.deepcopy(raw.get('material_uncertainties', raw.get('limitations', old.get('uncertainties', []))))
        if eid == 'FED_TREASURY_2023_03_12_BTFP':
            uncertainties = [u for u in uncertainties if 'midnight cut permits' not in str(u)]
            uncertainties.append('March13 midnight cut is retained as the frozen conservative episode cut; parent-linked term-sheet details remain excluded from the certified decision block. Promised depositor access has not been certified executed.')
        e = {'episode_id': eid, 'event_date': event_date, 'event_label': raw.get('event_label', eid.replace('_', ' ')),
             'episode_family': raw['episode_family'], 'actor_ids': raw['actor_ids'], 'institution_ids': raw['institution_ids'],
             'cohort': cohort, 'regime': regime, 'split': split, 'decision_cut_utc': cut,
             'event_time_precision': certificate['first_public_evidence_precision'],
             'first_public_evidence_utc': headline,
             'pit_certified': True,
             'pit_certification_scope': certificate['certificate_scope'],
             'source_clock_certificate': certificate,
             'source_lineage': {'admitted_document_ids': sorted({catalog[s]['canonical_document_id'] for s in admitted}),
                                'originator_families': sorted({f for s in admitted for f in catalog[s]['originator_families']}),
                                'independence_warning': 'Multiple documents and joint agency announcements are not statistically independent sources.'},
             'selection_tags': tags,
             'decision_time': decision,
             'material_uncertainties': uncertainties,
             'excluded_later_context': copy.deepcopy(raw.get('later_outcomes', raw.get('outcomes', {}))),
             'outcomes': {'status': 'NOT_JOINED_FORECAST_FREEZE_REQUIRED'}}
        episodes.append(e)
    primary = [e for e in episodes if e['cohort'] == 'PRIMARY']
    assert len(primary) == 24 and len(episodes) == 25
    for tag in ('rhetoric_action_alignment', 'rhetoric_action_divergence_or_tension', 'intent_unresolved', 'strong_institutional_explanation'):
        assert sum(e['selection_tags'][tag] for e in primary) >= 5, tag
    summary = {'primary_episodes': len(primary), 'separate_adversarial_challenge_episodes': 1,
               'selection_tags_primary': {k: sum(e['selection_tags'][k] for e in primary) for k in primary[0]['selection_tags']},
               'first_public_clock_primary': dict(Counter(e['source_clock_certificate']['first_public_evidence_precision'] for e in primary)),
               'cut_policy_primary': dict(Counter(e['source_clock_certificate']['cut_policy'] for e in primary)),
               'registered_source_records': len(all_sources), 'unique_url_documents': len(canonical_aliases),
               'source_families': sorted({f for s in all_sources for f in s['originator_families']}),
               'admitted_source_records_primary': len(set(s for e in primary for s in e['source_clock_certificate']['admitted_source_ids']))}
    casebook = {'schema': 'mastermind.pb_a_casebook.v1', 'operation_key': protocol['operation_key'],
                'authority': 'RESEARCH_ONLY', 'protocol_freeze_commit': PROTOCOL_COMMIT,
                'coding_frozen_at_utc': frozen, 'source_packet_sha256': packet_hashes,
                'sample_design': protocol['sample_design'],
                'summary': summary,
                'interpretation_rules': ['Outcomes occur only after decision_time, and only frozen four-key features feed the predictor.', 'Clock certification is documentary and scoped; date-only and quarantined attachment evidence must not be promoted to intraday certainty.', 'Categories overlap; private intent is unresolved for every row.'],
                'sources': all_sources, 'episodes': episodes}
    inputs = {'meta': {'protocol_freeze_commit': PROTOCOL_COMMIT, 'coding_frozen_at_utc': frozen}, 'episodes': model_inputs}
    write('PB_A_DECISION_INPUTS.json', inputs)
    write('PB_A_CASEBOOK.json', casebook)
    print(json.dumps(summary, indent=2))

def assemble():
    book = read('PB_A_CASEBOOK.json')
    forecast = read('PB_A_FORECAST_FREEZE.json')
    outcomes = read('PB_A_OUTCOMES.json')
    # The scorer defines its row schema; preserve each full row in the joined casebook.
    frows = forecast.get('forecast_payload', forecast).get('episodes')
    orows = outcomes.get('episodes', outcomes.get('outcomes'))
    if not isinstance(frows, list) or not isinstance(orows, list):
        raise ValueError('Unexpected scorer output; inspect before changing assembly mapping')
    fmap = {r['episode_id']: r for r in frows}
    omap = {r['episode_id']: r for r in orows}
    for row in book['episodes']:
        eid = row['episode_id']
        decision = row['decision_time']
        decision['frozen_forecasts'] = fmap[eid]
        # Ensure outcomes remain the last substantive block.
        row['outcomes'] = omap[eid]
    book['forecast_artifact_sha256'] = sha(ROOT / 'PB_A_FORECAST_FREEZE.json')
    book['outcome_artifact_sha256'] = sha(ROOT / 'PB_A_OUTCOMES.json')
    write('PB_A_CASEBOOK.json', book)
    print('Joined frozen forecasts and separately scored outcomes for', len(book['episodes']), 'rows.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'assemble'])
    args = parser.parse_args()
    build() if args.command == 'build' else assemble()
