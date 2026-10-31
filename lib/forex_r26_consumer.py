"""Project the existing data/forex/latest.json into R26 display-only consumer views.

Deterministic, typed projection of the canonical forex publication for the R26
web consumer contract (recovery after read-only audit
forex-r26-recovery-source-audit-20261019-001). This module computes nothing,
scores nothing, forecasts nothing, and persists nothing: every displayed fact
is either reported by the canonical payload or is the quote-correct arithmetic
reading of a reported change against the displayed pair letters.

Contract:

- Three destinations: ``today``, ``explore`` and ``my_watches``. ``my_watches``
  is NOT_ACTIVE by contract: a constant view with unavailable account status and
  no module state; :func:`add_watch` refuses identically on every call.
- Four pair-tab availability statuses, and no others: ``available`` (reported
  change and price are finite numbers and the source marks the row reliable),
  ``degraded`` (row present but some evidence is missing, malformed, non-finite
  or source-marked unreliable; every gap is named in ``gaps``), ``missing``
  (requested pair has no row in the payload; nothing is invented), and
  ``withheld`` (payload gate failed; every tab fails closed together).
- Quote-correct pair direction, from the displayed pair letters only. A pair
  key like ``USDJPY`` reads base ``USD`` / quote ``JPY``; the reported ``chg``
  is the change of the quote-per-base rate. ``USDJPY`` at -0.42% means the
  quoted rate fell, so JPY is stronger and USD weaker; ``EURUSD`` at
  +0.28% means EUR is stronger. The source's assessed/favored currency list
  (``favored``) and any meta direction fields are never used for direction;
  they pass through for display only. A separate model_direction uses the
  decision owner's explicit, internally consistent quote convention and a
  current reliable model lean. It never replaces the observed direction.
  Keys without six displayed letters
  (the ``DXY`` index) claim no currency-vs-currency direction.
- Source as-of fails closed: a payload whose ``asof`` is unknown (missing,
  null, blank), malformed (not an ISO ``YYYY-MM-DD`` calendar date), or in the
  future relative to the reference date withholds every destination. The
  reference date is injectable; it defaults to the current UTC date.
  A prior date is historical, not current; a new assembly time cannot refresh it.
  A present decision_context is authoritative and malformed owners never fall
  back to legacy risk/regime fields.
  A declared ``source`` must be a non-empty string; an explicit null or a
  non-string value is malformed evidence and fails closed. The canonical
  publication does not currently declare a source; absence is shown as the
  explicit status ``unknown`` rather than invented provenance.
- Null is not zero. A missing, null, malformed or non-finite change produces
  no direction and no ``0.00%`` display; a literal finite ``0`` is the only
  input that displays ``0.00%`` / flat states.
- Source-reported status strings (``action``, ``headline``, ``sub``,
  ``stance``, ``regime``, ``risk``) pass through verbatim and are never
  used as observed price movement; the separately qualified model translation
  adds no score, probability, conviction or rating of its own.
- Out of scope and never produced here: forecast probabilities, ranking or
  ordering beyond payload order, entry/size/sizing suggestions, alerts, any
  queue/store/state/event engine, and any completed 4H close inferred from
  this daily snapshot. The ``kinematics`` member is deliberately not consumed
  by this projection.
- Keyboard and localization behavior are out of scope until a rendered
  consumer exists; raw source EN/ZH strings pass through untouched.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import date, datetime, timezone
import json
import math
from numbers import Real
import re

CONTRACT_VERSION = 1
PRODUCER = 'lib.forex_r26_consumer'

DESTINATIONS = ('today', 'explore', 'my_watches')
TAB_STATUSES = ('available', 'degraded', 'missing', 'withheld')
DIRECTION_STATES = ('stronger', 'weaker', 'flat')

_PAIR_KEY_RE = re.compile(r'[A-Z]{6}\Z')
_DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}\Z')


def _calendar_date(value: object) -> str | None:
    """Return the normalized ISO date for a well-formed calendar date, else None."""
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _finite_number(raw: object) -> tuple[float | None, str]:
    """Classify a reported number: ('available'|'missing'|'invalid', value).

    Booleans, non-numeric types and non-finite floats are invalid, never zero.
    """
    if raw is None:
        return None, 'missing'
    if isinstance(raw, bool) or not isinstance(raw, Real):
        return None, 'invalid'
    try:
        number = float(raw)
    except (OverflowError, ValueError, TypeError):
        return None, 'invalid'
    if not math.isfinite(number):
        return None, 'invalid'
    return number, 'available'


def _string_field(row: Mapping, key: str) -> str | None:
    value = row.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _project_gate(payload: object, reference_date: date) -> dict:
    """Gate the whole payload; fail closed on unknown/malformed/future as-of.

    A declared ``source`` must be a non-empty string; absence is the explicit
    status ``unknown`` (the canonical publication declares none today).
    Gate reasons are evaluated in a fixed precedence order.
    """
    if not isinstance(payload, Mapping):
        return {'status': 'withheld', 'reason': 'payload_malformed', 'asof': None,
                'reference_date': reference_date.isoformat(),
                'source_status': 'unavailable', 'source_label': None}
    raw_asof = payload.get('asof')
    asof = _calendar_date(raw_asof)
    if raw_asof is None or (isinstance(raw_asof, str) and not raw_asof.strip()):
        reason = 'asof_unknown'
    elif asof is None:
        reason = 'asof_malformed'
    elif asof > reference_date.isoformat():
        reason = 'asof_future'
    else:
        reason = None
    if 'source' not in payload:
        source_status, source_label = 'unknown', None
    else:
        source = payload.get('source')
        if isinstance(source, str) and source.strip():
            source_status, source_label = 'declared', source
        else:
            source_status, source_label = 'malformed', None
            reason = reason or 'source_malformed'
    if not isinstance(payload.get('pairs'), Mapping):
        reason = reason or 'pairs_section_unavailable'
    age = (reference_date - date.fromisoformat(asof)).days if asof else None
    gate = {'status': 'ok' if reason is None else 'withheld', 'reason': reason,
            'asof': asof, 'reference_date': reference_date.isoformat(),
            'source_status': source_status, 'source_label': source_label,
            'asof_age_days': age,
            'freshness_status': ('current_date_only' if age == 0 else
                                 'historical' if age is not None and age > 0 else 'unknown'),
            'freshness_basis': 'reference_date_comparison_only_not_source_freshness'}
    return gate


def _project_pair_tab(pair: object, row: object) -> dict:
    """Project one pair tab from evidence only; never invent row content."""
    tab = {'pair': pair, 'label': None, 'status': 'degraded', 'pair_scope': 'non_pair',
           'base_ccy': None, 'quote_ccy': None, 'price': None, 'price_status': 'missing',
           'chg': None, 'chg_status': 'missing', 'chg_display': None,
           'direction': None, 'direction_reason': 'chg_unavailable',
           'reliability': 'unstated', 'source_action': None, 'source_score': None,
           'source_headline': None, 'source_headline_zh': None,
           'source_sub': None, 'source_sub_zh': None, 'gaps': []}
    if row is None:
        tab['status'] = 'missing'
        tab['direction_reason'] = 'row_missing'
        tab['gaps'] = ['row_missing']
        return tab
    if not isinstance(row, Mapping):
        tab['direction_reason'] = 'row_malformed'
        tab['gaps'] = ['row_malformed']
        return tab
    gaps = []
    if isinstance(pair, str) and _PAIR_KEY_RE.fullmatch(pair):
        tab['pair_scope'] = 'fx_pair'
        tab['base_ccy'] = pair[:3]
        tab['quote_ccy'] = pair[3:]
    else:
        tab['direction_reason'] = 'no_displayed_pair_letters'
    label = _string_field(row, 'label')
    if label is None:
        gaps.append('label_missing')
    tab['label'] = label
    price, price_status = _finite_number(row.get('quote'))
    tab['price'], tab['price_status'] = price, price_status
    if price_status != 'available':
        gaps.append('price_' + price_status)
    chg, chg_status = _finite_number(row.get('chg'))
    tab['chg'], tab['chg_status'] = chg, chg_status
    if chg_status != 'available':
        gaps.append('chg_' + chg_status)
        tab['direction_reason'] = 'chg_unavailable'
    reliable = row.get('reliable')
    if reliable is True:
        tab['reliability'] = 'reliable'
    elif reliable is False:
        tab['reliability'] = 'unreliable'
        gaps.append('source_marks_unreliable')
    elif reliable is None:
        tab['reliability'] = 'unstated'
        gaps.append('reliability_unstated')
    else:
        tab['reliability'] = 'invalid'
        gaps.append('reliability_invalid')
    action = _string_field(row, 'action')
    if action is None:
        gaps.append('source_action_missing')
    tab['source_action'] = action
    score, _score_status = _finite_number(row.get('score'))
    tab['source_score'] = score
    tab['source_headline'] = _string_field(row, 'headline')
    tab['source_headline_zh'] = (_string_field(row, 'headline_zh') or
                                 _string_field(row, 'head_zh'))
    tab['source_sub'] = _string_field(row, 'sub')
    tab['source_sub_zh'] = _string_field(row, 'sub_zh')
    if chg_status == 'available':
        tab['chg_display'] = '0.00%' if chg == 0 else f'{chg:+.2f}%'
        if tab['pair_scope'] == 'fx_pair':
            if chg == 0:
                base_state, quote_state = 'flat', 'flat'
            elif chg > 0:
                base_state, quote_state = 'stronger', 'weaker'
            else:
                base_state, quote_state = 'weaker', 'stronger'
            tab['direction'] = {'basis': 'displayed_pair_letters_and_reported_chg',
                                'base_ccy_state': base_state,
                                'quote_ccy_state': quote_state}
            tab['direction_reason'] = None
    if tab['pair_scope'] != 'fx_pair':
        gaps.append('not_currency_pair')
    usable = (chg_status == 'available' and price_status == 'available'
              and tab['reliability'] == 'reliable' and tab['pair_scope'] == 'fx_pair')
    tab['status'] = 'available' if usable else 'degraded'
    tab['gaps'] = gaps
    return tab


def watches_view() -> dict:
    """My-watches destination: NOT_ACTIVE by contract, constant, no persistence."""
    return {'status': 'not_active', 'active': False, 'persistence': 'none',
            'watches': [], 'reason': 'watches_not_active_in_r26',
            'account_state': 'unavailable', 'activation_available': False}


def add_watch(_pair: object = None, **_kwargs: object) -> dict:
    """Refuse watch persistence by contract; the same result on every call."""
    return {'status': 'not_active', 'stored': False,
            'reason': 'watches_not_active_in_r26'}


def _model_direction(pair: str, row: object, instrument: object, *, current: bool) -> dict:
    """Translate the owner's qualified currency lean into the displayed pair."""
    result = {'available': False, 'pair_direction': None, 'assessed_currency': None,
              'basis': 'assessed_currency_model_lean_to_literal_pair',
              'reason': 'quote_convention_unavailable'}
    if not isinstance(instrument, Mapping) or not isinstance(row, Mapping):
        return result
    assessed = instrument.get('assessed_currency')
    mapping = instrument.get('assessed_to_pair_direction')
    convention = instrument.get('quote_convention')
    if (not _PAIR_KEY_RE.fullmatch(pair)
            or instrument.get('display_base') != pair[:3]
            or instrument.get('display_quote') != pair[3:]
            or assessed not in (pair[:3], pair[3:])
            or not isinstance(convention, Mapping)
            or convention.get('status') != 'qualified'
            or type(convention.get('inverted_from_assessed')) is not bool
            or convention['inverted_from_assessed'] != (assessed == pair[3:])
            or mapping != ('same' if assessed == pair[:3] else 'opposite')):
        return result
    result['assessed_currency'] = assessed
    if not current:
        result['reason'] = 'current_decision_unavailable'
        return result
    if row.get('reliable') is not True:
        result['reason'] = 'source_lean_not_reliable'
        return result
    action = _string_field(row, 'action')
    direction = {'LONG': 1, 'STRONG LONG': 1, 'SHORT': -1,
                 'STRONG SHORT': -1, 'FLAT': 0}.get(action)
    if direction is None:
        result['reason'] = 'source_lean_unavailable'
        return result
    if mapping == 'opposite':
        direction *= -1
    result.update(available=True, pair_direction='higher' if direction > 0 else
                  'lower' if direction < 0 else 'flat', reason=None)
    return result


def _required_text_gap(row: Mapping, field: str) -> str | None:
    if field not in row or row[field] is None:
        return field + '_missing'
    if not isinstance(row[field], str):
        return field + '_invalid'
    if not row[field].strip():
        return field + '_blank'
    return None


def _current_read(payload: Mapping, gate: dict) -> dict:
    """Honor the existing decision owner; never fall back around a present owner.

    Date comparison describes the snapshot's age, not vendor availability.
    Historical quotes remain readable without becoming a current decision.
    """
    gaps = []
    result = {'available': False, 'basis': 'legacy_current_fields',
              'regime': None, 'risk': None, 'reason': None, 'gaps': gaps,
              'snapshot_id': None, 'assembled_at': None, 'source_revision': None,
              'asof': gate.get('asof'), 'asof_age_days': gate.get('asof_age_days'),
              'last_confirmed': None}
    if 'decision_context' in payload:
        result['basis'] = 'decision_context'
        owner = payload['decision_context']
        valid = (
            isinstance(owner, Mapping)
            and owner.get('schema') == 'mastermind.forex.decision-context.v1'
            and owner.get('authority') == 'display_only'
            and _string_field(owner, 'snapshot_id') is not None
            and isinstance(owner.get('current_read'), Mapping)
            and type(owner['current_read'].get('available')) is bool
        )
        if not valid:
            gaps.append('decision_context_malformed')
            result['reason'] = gaps[0]
            return result
        current = owner['current_read']
        current_asof = _calendar_date(current.get('calculated_asof'))
        current_age = ((date.fromisoformat(gate['reference_date']) -
                        date.fromisoformat(current_asof)).days if current_asof else None)
        result.update(asof=current_asof, asof_age_days=current_age)
        if current['available'] and current_age != 0:
            gaps.append('current_read_asof_unknown_or_malformed' if current_age is None else
                        'current_read_asof_future' if current_age < 0 else
                        'current_read_asof_before_reference_date')
        result.update(snapshot_id=owner['snapshot_id'],
                      assembled_at=deepcopy(owner.get('assembled_at')),
                      source_revision=deepcopy(owner.get('source_revision')),
                      last_confirmed=deepcopy(current.get('last_confirmed')))
        result['regime'] = _string_field(current, 'regime')
        result['risk'] = _string_field(current, 'risk')
        if current['available']:
            gaps.extend('decision_context_' + gap
                        for field in ('risk', 'regime')
                        if (gap := _required_text_gap(current, field)) is not None)
        else:
            gaps.append(_string_field(current, 'reason') or
                        'decision_context_current_read_unavailable')
    else:
        result['regime'] = _string_field(payload, 'regime')
        result['risk'] = _string_field(payload, 'risk')
        result['last_confirmed'] = deepcopy(payload.get('last_confirmed'))
        gaps.extend(gap for field in ('risk', 'regime')
                    if (gap := _required_text_gap(payload, field)) is not None)
    if gate.get('freshness_status') == 'historical':
        gaps.append('asof_before_reference_date')
    if gate['status'] != 'ok':
        gaps.append('gate_withheld:' + str(gate['reason']))
    result['available'] = not gaps and gate.get('asof_age_days') == 0
    result['reason'] = gaps[0] if gaps else None
    return result


def _universe_keys(universe: object, pairs: object) -> list[str]:
    keys = list(pairs) if universe is None and isinstance(pairs, Mapping) else universe
    if keys is None:
        keys = []
    if isinstance(keys, (str, bytes, bytearray)) or not isinstance(keys, Sequence):
        raise ValueError('universe_must_be_an_ordered_sequence')
    if any(not isinstance(key, str) or not key.strip() for key in keys):
        raise ValueError('universe_keys_must_be_nonempty_strings')
    if len(set(keys)) != len(keys):
        raise ValueError('universe_keys_must_be_unique')
    return list(keys)


def project_r26_consumer(payload: object, *, reference_date: date | None = None,
                         universe: object = None) -> dict:
    """Project one snapshot without input mutation or cross-destination aliases.

    Old valid observations stay dated and readable; Today/Explore degrade and
    current availability is false. A present decision-context owner is
    authoritative even when malformed or unavailable. Legacy payloads need
    nonempty risk/regime fields and the reference date for a current read.
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).date()
    if not isinstance(reference_date, date) or isinstance(reference_date, datetime):
        raise ValueError('reference_date_must_be_a_calendar_date')
    gate = _project_gate(payload, reference_date)
    source = payload if isinstance(payload, Mapping) else {}
    pairs = source.get('pairs')
    keys = _universe_keys(universe, pairs)
    current = _current_read(source, gate)
    owner = source.get('decision_context')
    instruments = {}
    if current['snapshot_id'] is not None and isinstance(owner, Mapping):
        rows = owner.get('pairs')
        if isinstance(rows, list):
            for item in rows:
                if isinstance(item, Mapping) and isinstance(item.get('pair'), str):
                    key = item['pair']
                    # Ambiguous duplicate conventions cannot establish a lean.
                    instruments[key] = None if key in instruments else item
    tabs = []
    for pair in keys:
        row = pairs.get(pair) if isinstance(pairs, Mapping) else None
        tab = _project_pair_tab(pair, row)
        raw_date = row.get('calculated_asof', gate['asof']) if isinstance(row, Mapping) else gate['asof']
        pair_asof = _calendar_date(raw_date)
        age = (reference_date - date.fromisoformat(pair_asof)).days if pair_asof else None
        tab.update(asof=pair_asof, asof_age_days=age,
                   date_status='current_date_only' if age == 0 else
                   'historical' if age is not None and age > 0 else 'unknown',
                   chg_horizon=_string_field(row, 'chg_horizon') if isinstance(row, Mapping) else None)
        if isinstance(row, Mapping) and 'calculated_asof' in row and (age is None or age < 0):
            tab['status'] = 'withheld'
            tab['direction'] = None
            tab['direction_reason'] = 'pair_asof_unavailable'
            tab['gaps'].append('pair_asof_unknown_malformed_or_future')
        tab['model_direction'] = _model_direction(
            pair, row, instruments.get(pair),
            current=current['available'] and age == 0 and tab['status'] != 'withheld')
        if gate['status'] != 'ok':
            tab['status'] = 'withheld'
            tab['direction'] = None
            tab['direction_reason'] = 'gate_withheld'
            tab['gaps'] = tab['gaps'] + ['gate_withheld:' + str(gate['reason'])]
        tabs.append(tab)
    withheld = gate['status'] != 'ok'
    gaps = list(current['gaps'])
    status = 'withheld' if withheld else 'ok' if current['available'] else 'degraded'
    reason = gate['reason'] if withheld else current['reason']
    stance = source.get('stance')
    today = {
        'status': status, 'reason': reason, 'asof': gate['asof'],
        'source_status': gate['source_status'], 'source_label': gate['source_label'],
        'current_available': current['available'],
        'asof_age_days': gate.get('asof_age_days'),
        'freshness_status': gate.get('freshness_status', 'unknown'),
        'freshness_basis': 'reference_date_comparison_only_not_source_freshness',
        'regime': None if withheld else current['regime'],
        'risk': None if withheld else current['risk'],
        'stance': deepcopy(stance) if not withheld and isinstance(stance, Mapping) else None,
        'favored': deepcopy(source['favored'])
        if not withheld and isinstance(source.get('favored'), list) else None,
        'favored_basis': 'source_assessed_currencies_display_only_not_used_for_pair_direction',
        'pair_tabs': tabs, 'gaps': gaps,
    }
    explore = {
        'status': status, 'reason': reason, 'asof': gate['asof'],
        'current_available': current['available'],
        'ordering': 'payload_order_no_ranking', 'pairs': deepcopy(tabs),
        'gaps': list(gaps),
    }
    return {
        'contract_version': CONTRACT_VERSION, 'producer': PRODUCER, 'gate': gate,
        'current_read': deepcopy(current),
        'destinations': {'today': today, 'explore': explore,
                         'my_watches': watches_view()},
    }


def load_latest_payload(path: str) -> dict:
    """Load a canonical latest.json payload from disk.

    Raises FileNotFoundError / ValueError on a missing or malformed file; the
    caller decides whether to fail closed through :func:`project_r26_consumer`.
    """
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)
