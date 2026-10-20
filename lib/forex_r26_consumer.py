"""Project the existing data/forex/latest.json into R26 display-only consumer views.

Deterministic, typed projection of the canonical forex publication for the R26
web consumer contract (recovery after read-only audit
forex-r26-recovery-source-audit-20261019-001). This module computes nothing,
scores nothing, forecasts nothing, and persists nothing: every displayed fact
is either reported by the canonical payload or is the quote-correct arithmetic
reading of a reported change against the displayed pair letters.

Contract:

- Three destinations: ``today``, ``explore`` and ``my_watches``. ``my_watches``
  is NOT_ACTIVE by contract: an empty, constant view with no persistence and
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
  quote currency moved down, so JPY is stronger and USD weaker; ``EURUSD`` at
  +0.28% means EUR is stronger. The source's assessed/favored currency list
  (``favored``) and any meta direction fields are never used for direction;
  they pass through for display only. Keys without six displayed letters
  (the ``DXY`` index) claim no currency-vs-currency direction.
- Source as-of fails closed: a payload whose ``asof`` is unknown (missing,
  null, blank), malformed (not an ISO ``YYYY-MM-DD`` calendar date), or in the
  future relative to the reference date withholds every destination. The
  reference date is injectable; it defaults to the local current date.
  A declared ``source`` must be a non-empty string; an explicit null or a
  non-string value is malformed evidence and fails closed. The canonical
  publication does not currently declare a source; absence is shown as the
  explicit status ``unknown`` rather than invented provenance.
- Null is not zero. A missing, null, malformed or non-finite change produces
  no direction and no ``0.00%`` display; a literal finite ``0`` is the only
  input that displays ``0.00%`` / flat states.
- Source-reported status strings (``action``, ``headline``, ``sub``,
  ``stance``, ``regime``, ``risk``) pass through verbatim and are never
  reinterpreted as consumer bullishness or bearishness; the projection adds
  no sentiment, conviction or rating field of its own.
- Out of scope and never produced here: forecast probabilities, ranking or
  ordering beyond payload order, entry/size/sizing suggestions, alerts, any
  queue/store/state/event engine, and any completed 4H close inferred from
  this daily snapshot. The ``kinematics`` member is deliberately not consumed
  by this projection.
- Keyboard and localization behavior are out of scope until a rendered
  consumer exists; raw source EN/ZH strings pass through untouched.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
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
    gate = {'status': 'ok' if reason is None else 'withheld', 'reason': reason,
            'asof': asof, 'reference_date': reference_date.isoformat(),
            'source_status': source_status, 'source_label': source_label}
    return gate


def _project_pair_tab(pair: object, row: object) -> dict:
    """Project one pair tab from evidence only; never invent row content."""
    tab = {'pair': pair, 'label': None, 'status': 'degraded', 'pair_scope': 'non_pair',
           'base_ccy': None, 'quote_ccy': None, 'price': None, 'price_status': 'missing',
           'chg': None, 'chg_status': 'missing', 'chg_display': None,
           'direction': None, 'direction_reason': 'chg_unavailable',
           'reliability': 'unstated', 'source_action': None, 'source_score': None,
           'source_headline': None, 'source_sub': None, 'gaps': []}
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
    tab['source_sub'] = _string_field(row, 'sub')
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
    usable = (chg_status == 'available' and price_status == 'available'
              and tab['reliability'] == 'reliable')
    tab['status'] = 'available' if usable else 'degraded'
    tab['gaps'] = gaps
    return tab


def watches_view() -> dict:
    """My-watches destination: NOT_ACTIVE by contract, constant, no persistence."""
    return {'status': 'not_active', 'active': False, 'persistence': 'none',
            'watches': [], 'reason': 'watches_not_active_in_r26'}


def add_watch(_pair: object = None, **_kwargs: object) -> dict:
    """Refuse watch persistence by contract; the same result on every call."""
    return {'status': 'not_active', 'stored': False,
            'reason': 'watches_not_active_in_r26'}


def project_r26_consumer(payload: object, *, reference_date: date | None = None,
                         universe: object = None) -> dict:
    """Build the full three-destination R26 consumer view; pure and deterministic.

    ``reference_date`` defaults to the local current date; tests inject a fixed
    date. ``universe`` defaults to the payload's own pair order; universe keys
    without a payload row project as ``missing`` tabs, and payload pairs outside
    the universe are ignored.
    """
    if reference_date is None:
        reference_date = date.today()
    gate = _project_gate(payload, reference_date)
    pairs = payload.get('pairs') if isinstance(payload, Mapping) else None
    if universe is None:
        universe = list(pairs) if isinstance(pairs, Mapping) else []
    else:
        universe = list(universe)
    tabs = []
    for pair in universe:
        tab = _project_pair_tab(pair, pairs.get(pair) if isinstance(pairs, Mapping) else None)
        if gate['status'] != 'ok':
            tab['status'] = 'withheld'
            tab['direction'] = None
            tab['direction_reason'] = 'gate_withheld'
            tab['gaps'] = tab['gaps'] + ['gate_withheld:' + str(gate['reason'])]
        tabs.append(tab)
    if gate['status'] == 'ok':
        stance = payload.get('stance')
        today = {'status': 'ok', 'reason': None, 'asof': gate['asof'],
                 'source_status': gate['source_status'],
                 'source_label': gate['source_label'],
                 'regime': _string_field(payload, 'regime'),
                 'risk': _string_field(payload, 'risk'),
                 'stance': dict(stance) if isinstance(stance, Mapping) else None,
                 'favored': list(payload['favored'])
                 if isinstance(payload.get('favored'), list) else None,
                 'favored_basis': ('source_assessed_currencies_display_only'
                                   '_not_used_for_pair_direction'),
                 'pair_tabs': tabs, 'gaps': []}
        explore = {'status': 'ok', 'reason': None, 'asof': gate['asof'],
                   'ordering': 'payload_order_no_ranking', 'pairs': tabs, 'gaps': []}
    else:
        reason = 'gate_withheld:' + str(gate['reason'])
        today = {'status': 'withheld', 'reason': gate['reason'], 'asof': gate['asof'],
                 'source_status': gate['source_status'],
                 'source_label': gate['source_label'],
                 'regime': None, 'risk': None, 'stance': None, 'favored': None,
                 'favored_basis': ('source_assessed_currencies_display_only'
                                   '_not_used_for_pair_direction'),
                 'pair_tabs': tabs, 'gaps': [reason]}
        explore = {'status': 'withheld', 'reason': gate['reason'], 'asof': gate['asof'],
                   'ordering': 'payload_order_no_ranking', 'pairs': tabs,
                   'gaps': [reason]}
    return {'contract_version': CONTRACT_VERSION, 'producer': PRODUCER, 'gate': gate,
            'destinations': {'today': today, 'explore': explore,
                             'my_watches': watches_view()}}


def load_latest_payload(path: str) -> dict:
    """Load a canonical latest.json payload from disk.

    Raises FileNotFoundError / ValueError on a missing or malformed file; the
    caller decides whether to fail closed through :func:`project_r26_consumer`.
    """
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)
