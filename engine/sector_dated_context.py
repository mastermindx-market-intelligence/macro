"""Deterministic projection of configured-theme dated context and market-global risk.

This module is a pure, stateless, additive, DISPLAY-ONLY projection over three
already-decoded owner documents:

* ``regime_document``      -- the published regime snapshot (``data/regime/latest.json``)
* ``config_document``      -- the decoded site configuration (``config.yml``)
* ``public_risk_document`` -- the published public risk envelope
  (``site/riskdata/risk_envelope.json``)

It is NOT a source, evaluator, event owner, store, publisher or schedule. It
holds no state, it never mutates an input argument, and it performs no file,
network, environment, provider, builder, ledger or publication work. There is
no clock read anywhere in this module (never ``datetime.now``); the
``datetime`` use is parsing a caller-supplied *decision cutoff* for awareness
and validating a supplied owner clock, and no parsed value is ever compared
against any snapshot clock.

Owner builders are never imported and never invoked. The existing regime
document already carries ``theme_revisions`` and ``bottleneck``; this module
reads the selected branches and never recalculates a metric, never re-stamps a
date and never re-derives a composite.

What this projection is for
---------------------------
It explains how four things can coexist in the supplied evidence: positive
revision breadth, weakening broadening, an *older* neutral bottleneck, and
degraded market-global risk. It does that with dated, owner-attributed
observations and with a controlled set of four conditional alternatives, each
carrying a falsifier that is never marked met.

Independent clocks
------------------
Every clock stays with its own owner and is never merged:

* ``regime_document``  -- ``asof`` and ``freshness.built_at`` describe the
  owner build only.
* ``theme_revisions``  -- its own ``asof``.
* ``bottleneck``       -- its own ``asof`` (which may be materially older).
* public risk          -- ``source_session`` / ``as_of`` / ``observed_at`` /
  ``produced_at`` plus one ``as_of`` per freshness source.

Owner freshness does not mean fresh *now*; a git commit time cannot restamp a
component; and a fiscal year (``latest_fy``) is not a publication clock. The
declared native unit strings are preserved verbatim -- including one whose
prose contains "PIT" -- and that prose is never converted into an availability
qualification.

Historical mode
---------------
Supplying ``decision_cutoff`` switches the projection into historical mode.
The cutoff must be an aware ISO datetime; an invalid cutoff produces a typed
unavailable result. In historical mode every contextual value is WITHHELD with
the reason ``historical_availability_unqualified``: this module cannot
establish that a current snapshot was originally available at the cutoff, so it
never filters current snapshots or compares dates to simulate point-in-time.
No positive context survives under a historical claim.

Authority
---------
The projection is descriptive evidence only. ``may_rank``, ``may_gate``,
``may_size``, ``may_trade`` and ``may_escalate`` are literal ``False`` in every
result, and the fixed limitations always state that the output is not currently
sector-usable and not historically admissible.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime

__all__ = [
    "SCHEMA",
    "SCOPE",
    "STATUSES",
    "SECTION_STATUSES",
    "ENTRY_STATUSES",
    "COMPARISON_IDS",
    "AUTHORITY_FLAGS",
    "LIMITS",
    "REASONS",
    "ATTRIBUTION_KEYS",
    "project_dated_context",
]

# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

SCHEMA = "sector_dated_context/v1"
SCOPE = "configured_theme_example_with_market_global_risk"

#: Top-level status vocabulary. It reports which evidence sections were
#: projected -- never the freshness or the quality of the underlying owners.
STATUSES = ("dated_context", "partial", "unavailable")

#: Per-section status vocabulary.
SECTION_STATUSES = ("available", "partial", "unavailable", "withheld")

#: Per-alternative status vocabulary inside the comparison section.
ENTRY_STATUSES = ("supported", "unresolved")

#: The four fixed comparison identifiers. Exactly these, always.
COMPARISON_IDS = (
    "earnings_expectations",
    "narrow_or_fading_revisions",
    "physical_supply_constraint",
    "market_or_other_causes",
)

#: Authority flags; every one of them is a literal ``False`` in every result.
AUTHORITY_FLAGS = ("may_rank", "may_gate", "may_size", "may_trade", "may_escalate")

#: The three documents the caller may attribute.
ATTRIBUTION_KEYS = ("regime_document", "config_document", "public_risk_document")

#: Named, bounded limits.
LIMITS = {
    "max_configured_tickers": 64,
    "max_contributors": 64,
    "max_ticker_chars": 16,
    "max_theme_key_chars": 64,
    "max_theme_name_chars": 120,
    "max_source_ref_chars": 512,
    "max_selected_depth": 10,
    "max_selected_nodes": 2048,
    "max_comparison_entries": 4,
    "max_statement_chars": 320,
    "max_check_chars": 320,
    "max_output_bytes": 16384,
    "max_state_chars": 64,
}

#: Stable typed reasons. No raw exception prose is ever returned.
REASONS = (
    "invalid_decision_cutoff",
    "historical_availability_unqualified",
    "output_bound_exceeded",
    "output_not_serialisable",
    "input_bound_exceeded",
    "input_cycle_detected",
    "input_type_violation",
    "invalid_theme_key",
    "theme_identity_unqualified",
    "invalid_regime_document",
    "invalid_config_document",
    "invalid_public_risk_document",
    "invalid_source_attribution",
    "source_ref_invalid",
    "raw_sha256_invalid",
    "config_themes_unavailable",
    "theme_not_in_config",
    "theme_name_invalid",
    "roster_unavailable",
    "roster_ticker_invalid",
    "roster_duplicate_ticker",
    "roster_too_large",
    "contributors_too_large",
    "roster_count_mismatch",
    "revision_state_unavailable",
    "revision_field_invalid",
    "revision_field_unavailable",
    "revision_asof_unavailable",
    "revision_asof_invalid",
    "revision_breadth_unavailable",
    "revision_breadth_not_positive",
    "revision_counts_invalid",
    "revision_coverage_inconsistent",
    "contributors_unavailable",
    "contributors_duplicate",
    "contributors_outside_roster",
    "contributors_count_mismatch",
    "contributor_field_invalid",
    "contributor_field_unavailable",
    "non_finite_value",
    "boolean_not_numeric",
    "bottleneck_unavailable",
    "bottleneck_field_invalid",
    "market_risk_schema_missing",
    "market_risk_schema_unexpected",
    "market_risk_field_invalid",
    "market_risk_unavailable",
    "comparison_statement_too_long",
    "comparison_check_too_long",
    "comparison_entry_invalid",
    "evidence_reference_unresolved",
    "revision_level_state_unavailable",
    "revision_level_state_not_positive",
    "coverage_unavailable",
    "coverage_not_partial",
    "broadening_state_unavailable",
    "broadening_state_not_rolling",
    "level_state_unavailable",
    "bottleneck_band_unavailable",
    "bottleneck_asof_unavailable",
    "bottleneck_asof_invalid",
    "alternatives_not_resolved_by_supplied_evidence",
)

#: The one reason used when the projection withholds context for a cutoff.
HISTORICAL_REASON = "historical_availability_unqualified"

#: Integrity violations of the revision reading. A projected part that carries
#: one of these is dropped entirely, so no positive value survives it.
_REVISION_INTEGRITY_REASONS = (
    "revision_field_invalid",
    "revision_counts_invalid",
    "revision_coverage_inconsistent",
    "contributors_duplicate",
    "contributors_outside_roster",
    "contributors_count_mismatch",
    "contributor_field_invalid",
    "boolean_not_numeric",
    "non_finite_value",
    "roster_count_mismatch",
)

#: Integrity violations of the bottleneck reading.
_BOTTLENECK_INTEGRITY_REASONS = (
    "bottleneck_field_invalid",
    "boolean_not_numeric",
    "non_finite_value",
)

#: Reasons that mean a controlled reading could not be made from the supplied
#: evidence. Their presence makes the comparison section ``partial``: the
#: section projected, but the supplied evidence did not support the reading.
#: ``alternatives_not_resolved_by_supplied_evidence`` is deliberately absent --
#: the alternatives bucket is unresolved by design, not by missing evidence.
_READING_BLOCKED_REASONS = (
    "revision_level_state_unavailable",
    "revision_level_state_not_positive",
    "revision_breadth_unavailable",
    "revision_breadth_not_positive",
    "revision_counts_invalid",
    "coverage_unavailable",
    "coverage_not_partial",
    "contributors_unavailable",
    "contributors_count_mismatch",
    "broadening_state_unavailable",
    "broadening_state_not_rolling",
    "level_state_unavailable",
    "bottleneck_band_unavailable",
    "bottleneck_asof_unavailable",
    "bottleneck_asof_invalid",
    "theme_identity_unqualified",
    "evidence_reference_unresolved",
)

#: Maximum length of a short controlled state token (band, level state, ...).
_STATE_MAX = LIMITS["max_state_chars"]

_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")

#: An owner clock is either a calendar date or an aware timestamp.
_OWNER_DATE_RE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")

#: The private bound on a supplied owner clock string.
_CLOCK_MAX_CHARS = 64

#: The public risk envelope schema this projection reads.
_RISK_SCHEMA = "mastermind.risk_envelope/v1"


# ---------------------------------------------------------------------------
# 2. Small typed helpers
# ---------------------------------------------------------------------------

def _section(status, reasons, **fields):
    """Build a section: status first, then the typed reasons, then the data."""
    section = {"status": status, "reasons": list(reasons)}
    section.update(fields)
    return section


def _is_number(value):
    """True for a real number. ``bool`` is explicitly NOT a number here."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite_number(value):
    """True for a finite, non-boolean number. Huge ints stay finite."""
    if not _is_number(value):
        return False
    if isinstance(value, int):
        return True
    return math.isfinite(value)


def _is_integral(value):
    """True for a non-negative integral count (a float of integral value is ok)."""
    if not _is_finite_number(value):
        return False
    if isinstance(value, int):
        return value >= 0
    return value >= 0 and float(value).is_integer()


def _is_count(value):
    """True for a non-negative integral count."""
    return _is_integral(value)


def _is_state_token(value):
    """True for a short, non-empty string usable as a controlled state token."""
    return isinstance(value, str) and 0 < len(value) <= _STATE_MAX


def _safe_theme_key(theme_key):
    """Return the selector only when it is a valid, bounded theme key.

    An invalid or oversized selector is never echoed into a result: a refusal
    carries a stable reason code, not the rejected value.
    """
    if (isinstance(theme_key, str) and theme_key
            and len(theme_key) <= LIMITS["max_theme_key_chars"]):
        return theme_key
    return None


def _detach(value):
    """Return a detached copy of a supplied mutable value.

    Lists and mappings are rebuilt so that the projection shares no mutable
    state with the caller's document, in either direction. The copy is built
    with an explicit stack, so no recursion depth is spent on it.
    """
    if not isinstance(value, (dict, list, tuple)):
        return value
    root = [] if isinstance(value, (list, tuple)) else {}
    stack = [(value, root)]
    while stack:
        source, target = stack.pop()
        if isinstance(source, dict):
            for key, item in source.items():
                if isinstance(item, (dict, list, tuple)):
                    child = [] if isinstance(item, (list, tuple)) else {}
                    target[key] = child
                    stack.append((item, child))
                else:
                    target[key] = item
        else:
            for item in source:
                if isinstance(item, (dict, list, tuple)):
                    child = [] if isinstance(item, (list, tuple)) else {}
                    target.append(child)
                    stack.append((item, child))
                else:
                    target.append(item)
    return root


def _is_valid_owner_clock(value):
    """True for a usable owner clock: a calendar date or an aware timestamp.

    A non-empty string is not a clock. Only an ISO calendar date or an ISO
    timestamp that carries a real UTC offset qualifies; every other value is
    an unknown clock, and an unknown clock never supports a dated or
    contemporaneous claim.
    """
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text or len(text) > _CLOCK_MAX_CHARS:
        return False
    if _OWNER_DATE_RE.match(text):
        try:
            datetime.fromisoformat(text)
        except ValueError:
            return False
        return True
    candidate = text[:-1] + "+00:00" if text[-1] in ("Z", "z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _safe_ratio(numerator, denominator):
    """The covered share of two accepted counts, or None when it is unusable.

    A zero denominator has no ratio, and a pair of counts too large for a
    float division has none either. Both are refusals, never an exception and
    never a silent zero.
    """
    if denominator == 0:
        return None
    try:
        return numerator / denominator
    except (OverflowError, TypeError, ValueError, ZeroDivisionError):
        return None


def _mapping(node):
    """Return the node when it is a mapping, else ``None``."""
    return node if isinstance(node, dict) else None


def _bounded_scan(node, counter, max_depth=None, max_nodes=None):
    """Bounded, cycle-aware scan of one selected input branch.

    ``counter`` is a single-element list holding the running node count for the
    document this branch belongs to, so the budget applies per document.
    Returns a reason string on refusal, else ``None``.

    Only the *selected* branches are ever scanned: an unrelated million-byte
    regime section is never traversed.
    """
    if max_depth is None:
        max_depth = LIMITS["max_selected_depth"]
    if max_nodes is None:
        max_nodes = LIMITS["max_selected_nodes"]
    path = set()

    def walk(current, depth):
        if depth > max_depth:
            return "input_bound_exceeded"
        counter[0] += 1
        if counter[0] > max_nodes:
            return "input_bound_exceeded"
        if isinstance(current, (dict, list, tuple)):
            marker = id(current)
            if marker in path:
                return "input_cycle_detected"
            path.add(marker)
            try:
                if isinstance(current, dict):
                    for key, value in current.items():
                        if not isinstance(key, str):
                            return "input_type_violation"
                        problem = walk(value, depth + 1)
                        if problem:
                            return problem
                else:
                    for value in current:
                        problem = walk(value, depth + 1)
                        if problem:
                            return problem
            finally:
                path.discard(marker)
            return None
        if current is None or isinstance(current, (str, bool, int, float)):
            return None
        return "input_type_violation"

    return walk(node, 1)


def _resolve(context, path):
    """True when a dotted evidence reference resolves to a projected field."""
    node = context
    for part in path.split("."):
        if isinstance(node, dict):
            if part not in node:
                return False
            node = node[part]
        elif isinstance(node, list):
            if not part.isdigit() or int(part) >= len(node):
                return False
            node = node[int(part)]
        else:
            return False
    return True


def _parse_decision_cutoff(value):
    """Validate a decision cutoff.

    The cutoff must be an aware ISO datetime (a string or a ``datetime`` with a
    real UTC offset). It is validated for awareness only and is never compared
    against any snapshot clock -- this module does not simulate point-in-time.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return False
        return True
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return False
        candidate = text[:-1] + "+00:00" if text[-1] in ("Z", "z") else text
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return False
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return False
        return True
    return False


# ---------------------------------------------------------------------------
# 3. Fixed sections
# ---------------------------------------------------------------------------

def _limitations():
    """The fixed limitations; identical in every result, valid or not."""
    return {
        "current_sector_usable": False,
        "historically_admissible": False,
        "sector_mapping": {
            "status": "unavailable",
            "reason": "native_sector_mapping_not_supplied",
        },
        "original_available_at": None,
        "availability_reason": "native_availability_and_revision_selection_not_supplied",
        "attribution_verification": "not_established_by_projection",
    }


def _authority():
    """The fixed authority block; every flag is a literal ``False``."""
    return {flag: False for flag in AUTHORITY_FLAGS}


def _unavailable_result(theme_key, reasons, status="unavailable"):
    """A complete, well-formed result in which nothing was projected.

    The selector is echoed only when it is a valid, bounded theme key, so a
    refusal never carries an invalid or oversized value back to the caller.
    """
    reasons = list(reasons)
    return {
        "schema": SCHEMA,
        "status": status,
        "scope": SCOPE,
        "theme": _section(
            "unavailable", reasons, theme_key=_safe_theme_key(theme_key),
            name=None,
            roster=[], roster_size=0, membership_basis="configured_theme_roster",
        ),
        "observations": _section("unavailable", reasons),
        "comparison": _section(
            "unavailable", reasons, evaluation="prospective_unevaluated",
            entries=[],
        ),
        "market_risk": _section("unavailable", reasons, scope="market_global"),
        "provenance": _section("unavailable", reasons),
        "limitations": _limitations(),
        "authority": _authority(),
    }


def _bounded_result(result, theme_key):
    """Return the result when it fits the output bound, else a bounded refusal.

    Nothing is ever trimmed to fit: a result that does not fit is refused
    whole, with a stable reason code and no raw exception prose.
    """
    try:
        encoded = json.dumps(
            result, ensure_ascii=False, separators=(",", ":"),
            allow_nan=False, sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return _unavailable_result(theme_key, ["output_not_serialisable"])
    if len(encoded) > LIMITS["max_output_bytes"]:
        return _unavailable_result(theme_key, ["output_bound_exceeded"])
    return result


def _refuse(theme_key, reasons, status="unavailable"):
    """A bounded refusal: stable reason codes and no rejected value."""
    return _bounded_result(
        _unavailable_result(theme_key, reasons, status=status), theme_key)


# ---------------------------------------------------------------------------
# 4. Theme (configured roster identity)
# ---------------------------------------------------------------------------

def _build_theme(theme_key, config_document):
    """Project the configured theme roster.

    The roster is the *configured theme* roster. It is not ETF membership and
    not sector membership; no sector mapping is available here.
    """
    reasons = []
    themes = _mapping(config_document.get("themes"))
    if themes is None:
        return _section(
            "unavailable", ["config_themes_unavailable"], theme_key=theme_key,
            name=None, roster=[], roster_size=0,
            membership_basis="configured_theme_roster",
        )
    entry = _mapping(themes.get(theme_key))
    if entry is None:
        return _section(
            "unavailable", ["theme_not_in_config"], theme_key=theme_key,
            name=None, roster=[], roster_size=0,
            membership_basis="configured_theme_roster",
        )
    name = entry.get("name")
    if not isinstance(name, str) or not name or len(name) > LIMITS["max_theme_name_chars"]:
        return _section(
            "unavailable", ["theme_name_invalid"], theme_key=theme_key,
            name=None, roster=[], roster_size=0,
            membership_basis="configured_theme_roster",
        )
    raw_tickers = entry.get("tickers")
    if not isinstance(raw_tickers, (list, tuple)):
        return _section(
            "unavailable", ["roster_unavailable"], theme_key=theme_key, name=name,
            roster=[], roster_size=0, membership_basis="configured_theme_roster",
        )
    if len(raw_tickers) > LIMITS["max_configured_tickers"]:
        return _section(
            "unavailable", ["roster_too_large"], theme_key=theme_key, name=name,
            roster=[], roster_size=0, membership_basis="configured_theme_roster",
        )
    roster = []
    seen = set()
    for ticker in raw_tickers:
        if (not isinstance(ticker, str) or not ticker
                or len(ticker) > LIMITS["max_ticker_chars"]):
            reasons.append("roster_ticker_invalid")
            continue
        if ticker in seen:
            reasons.append("roster_duplicate_ticker")
            continue
        seen.add(ticker)
        roster.append(ticker)
    if reasons:
        return _section(
            "unavailable", reasons, theme_key=theme_key, name=name, roster=[],
            roster_size=0, membership_basis="configured_theme_roster",
        )
    return _section(
        "available", [], theme_key=theme_key, name=name, roster=roster,
        roster_size=len(roster), membership_basis="configured_theme_roster",
    )


# ---------------------------------------------------------------------------
# 5. Observations (dated theme state + the separately dated bottleneck)
# ---------------------------------------------------------------------------

def _project_number(value, reasons, invalid_reason):
    """Project a finite non-boolean number, or record a typed reason."""
    if not _is_number(value):
        reasons.append("boolean_not_numeric" if isinstance(value, bool) else invalid_reason)
        return None
    if not _is_finite_number(value):
        reasons.append("non_finite_value")
        return None
    return value


def _project_count(value, reasons, invalid_reason):
    """Project a non-negative integral count, or record a typed reason."""
    if not _is_number(value):
        reasons.append("boolean_not_numeric" if isinstance(value, bool) else invalid_reason)
        return None
    if not _is_finite_number(value):
        reasons.append("non_finite_value")
        return None
    if not _is_count(value):
        reasons.append(invalid_reason)
        return None
    return value


def _build_clocks(regime_document, revisions_asof, bottleneck_asof):
    """Keep every owner clock separate; never merge or restamp them."""
    freshness = _mapping(regime_document.get("freshness")) or {}
    clocks = {
        "regime_asof": regime_document.get("asof"),
        "regime_built_at": freshness.get("built_at"),
        "regime_freshness": {
            "asof": freshness.get("asof"),
            "built_at": freshness.get("built_at"),
            "age_days": freshness.get("age_days"),
            "age_sessions": freshness.get("age_sessions"),
            "max_age_sessions": freshness.get("max_age_sessions"),
            "stale": freshness.get("stale"),
        },
        "theme_revisions_asof": revisions_asof,
        "bottleneck_asof": bottleneck_asof,
    }
    return clocks


def _project_units(revisions):
    """Preserve the owner-declared native units verbatim.

    The declared ``breadth_accel`` unit string contains the word "PIT"; that
    prose is copied unchanged and is never treated as an availability
    qualification.
    """
    weights = _mapping(revisions.get("weights")) or {}
    units = {}
    for metric in ("breadth", "est_drift_90d", "breadth_accel", "breadth_cov"):
        text = weights.get(metric)
        if isinstance(text, str) and text:
            units[metric] = text
    units.update({
        "est_chg_90d": "member 90d consensus-EPS drift %",
        "net_up_total": "count of net-up revisions",
        "coverage": "covered members over configured members",
        "n_covered": "count of covered configured members",
        "n_members": "count of configured members",
        "n_analysts": "count of covering analysts",
        "n_covering": "count of covering estimates",
        "breadth_accel_basis_days": "days to the declared prior snapshot basis",
    })
    return units


def _build_revision_state(theme_state, revisions_asof, reasons):
    """Project the dated revision state of one configured theme.

    The revision clock is the ``theme_revisions`` owner clock; it is never
    taken from the theme entry, the regime clock or the bottleneck clock.
    """
    state = {}
    if revisions_asof is None or (
            isinstance(revisions_asof, str) and not revisions_asof.strip()):
        reasons.append("revision_asof_unavailable")
    elif not _is_valid_owner_clock(revisions_asof):
        reasons.append("revision_asof_invalid")
    else:
        state["asof"] = revisions_asof
    level_state = theme_state.get("level_state")
    if level_state is None:
        reasons.append("revision_level_state_unavailable")
    elif _is_state_token(level_state):
        state["level_state"] = level_state
    else:
        reasons.append("revision_field_invalid")
    for field in ("breadth", "est_drift_90d", "breadth_accel", "breadth_cov", "coverage"):
        value = theme_state.get(field)
        if value is None:
            reasons.append("revision_field_unavailable")
            continue
        projected = _project_number(value, reasons, "revision_field_invalid")
        if projected is not None:
            state[field] = projected
    net_up_total = theme_state.get("net_up_total")
    if net_up_total is None:
        reasons.append("revision_field_unavailable")
    else:
        projected = _project_count(net_up_total, reasons, "revision_counts_invalid")
        if projected is not None:
            state["net_up_total"] = projected
    for field in ("n_covered", "n_members"):
        value = theme_state.get(field)
        if value is None:
            reasons.append("revision_field_unavailable")
            continue
        projected = _project_count(value, reasons, "revision_counts_invalid")
        if projected is not None:
            state[field] = projected
    basis_days = theme_state.get("basis_days")
    if basis_days is None:
        reasons.append("revision_field_unavailable")
    else:
        projected = _project_count(basis_days, reasons, "revision_counts_invalid")
        if projected is not None:
            state["breadth_accel_basis_days"] = projected
    broadening_state = theme_state.get("broadening_state")
    if broadening_state is None:
        reasons.append("broadening_state_unavailable")
    elif _is_state_token(broadening_state):
        state["broadening_state"] = broadening_state
    else:
        reasons.append("revision_field_invalid")
    return state


def _build_contributors(theme_state, roster, reasons):
    """Project the covered contributor rows and check them against the roster."""
    raw = theme_state.get("members")
    if not isinstance(raw, (list, tuple)):
        reasons.append("contributors_unavailable")
        return []
    if len(raw) > LIMITS["max_contributors"]:
        reasons.append("contributors_too_large")
        return []
    contributors = []
    seen = set()
    for row in raw:
        row = _mapping(row)
        if row is None:
            reasons.append("contributor_field_invalid")
            continue
        ticker = row.get("ticker")
        if ticker is None:
            reasons.append("contributor_field_unavailable")
            continue
        if not isinstance(ticker, str) or not ticker or len(ticker) > LIMITS["max_ticker_chars"]:
            reasons.append("contributor_field_invalid")
            continue
        if ticker in seen:
            reasons.append("contributors_duplicate")
            continue
        seen.add(ticker)
        if roster and ticker not in roster:
            reasons.append("contributors_outside_roster")
            continue
        projected = {"ticker": ticker}
        for field in ("breadth", "est_chg_90d", "breadth_cov"):
            value = row.get(field)
            if value is None:
                reasons.append("contributor_field_unavailable")
                continue
            number = _project_number(value, reasons, "contributor_field_invalid")
            if number is not None:
                projected[field] = number
        for field in ("n_analysts", "n_covering"):
            value = row.get(field)
            if value is None:
                reasons.append("contributor_field_unavailable")
                continue
            count = _project_count(value, reasons, "contributor_field_invalid")
            if count is not None:
                projected[field] = count
        contributors.append(projected)
    return contributors


def _project_fingerprint(fingerprint, reasons):
    """Project the member fingerprint, preserving nulls, zero and provisionality."""
    fingerprint = _mapping(fingerprint)
    if fingerprint is None:
        reasons.append("bottleneck_field_invalid")
        return None
    projected = {}
    for field in ("theme", "basis"):
        value = fingerprint.get(field)
        if isinstance(value, str) and value:
            projected[field] = value
    for field in ("fingerprint_tightness", "leg7_member_inventory", "leg8_member_backlog"):
        if field not in fingerprint:
            continue
        value = fingerprint.get(field)
        if value is None:
            projected[field] = None          # a genuine owner null is preserved
            continue
        number = _project_number(value, reasons, "bottleneck_field_invalid")
        if number is not None:
            projected[field] = number
    n_legs_live = fingerprint.get("n_legs_live")
    count = _project_count(n_legs_live, reasons, "bottleneck_field_invalid")
    if count is not None:
        projected["n_legs_live"] = count
    provisional = fingerprint.get("provisional")
    if isinstance(provisional, bool):
        projected["provisional"] = provisional
    components = _mapping(fingerprint.get("components"))
    if components is not None:
        projected_components = {}
        for name, raw in components.items():
            raw = _mapping(raw)
            if raw is None:
                reasons.append("bottleneck_field_invalid")
                continue
            component = {}
            value = raw.get("value")
            if value is None:
                component["value"] = None
            else:
                number = _project_number(value, reasons, "bottleneck_field_invalid")
                if number is not None:
                    component["value"] = number
            for field in ("n_reporting", "latest_fy", "min_required"):
                if field not in raw:
                    continue
                count = _project_count(raw.get(field), reasons, "bottleneck_field_invalid")
                if count is not None:
                    component[field] = count
            for field in ("met_gate", "weight_provisional"):
                value = raw.get(field)
                if isinstance(value, bool):
                    component[field] = value
            description = raw.get("description")
            if isinstance(description, str) and description:
                component["description"] = description
            projected_components[name] = component
        projected["components"] = projected_components
    return projected


def _build_bottleneck(bottleneck_state, bottleneck_asof, reasons):
    """Project the separately dated bottleneck reading.

    The clock is the ``bottleneck`` owner clock; it is never taken from the
    theme entry, the regime clock or the revision clock, and it is never
    restamped. Nothing is recomputed: a numeric zero stays zero, a null backlog
    leg stays null, the annual cadence stays annual and the provisional flags
    stay provisional.
    """
    projected = {}
    if bottleneck_asof is None or (
            isinstance(bottleneck_asof, str) and not bottleneck_asof.strip()):
        reasons.append("bottleneck_asof_unavailable")
    elif not _is_valid_owner_clock(bottleneck_asof):
        reasons.append("bottleneck_asof_invalid")
    else:
        projected["asof"] = bottleneck_asof
    name = bottleneck_state.get("name")
    if isinstance(name, str) and name:
        projected["name"] = name
    naics = bottleneck_state.get("naics")
    if isinstance(naics, str) and naics:
        projected["naics"] = naics
    for field in ("band", "numeric_band"):
        value = bottleneck_state.get(field)
        if _is_state_token(value):
            projected[field] = value
    for field in ("tightness", "numeric_composite", "cap_u_latest", "ppi_yoy_latest",
                  "language_accel"):
        if field not in bottleneck_state:
            continue
        value = bottleneck_state.get(field)
        if value is None:
            projected[field] = None
            continue
        number = _project_number(value, reasons, "bottleneck_field_invalid")
        if number is not None:
            projected[field] = number
    for field in ("n_legs", "language_hits", "language_n_filers"):
        value = bottleneck_state.get(field)
        count = _project_count(value, reasons, "bottleneck_field_invalid")
        if count is not None:
            projected[field] = count
    for field in ("regime", "text_only"):
        value = bottleneck_state.get(field)
        if isinstance(value, bool):
            projected[field] = value
    leg6 = _mapping(bottleneck_state.get("leg6_detail"))
    if leg6 is not None:
        projected_leg6 = {}
        for field in ("value", "accel"):
            value = leg6.get(field)
            if value is None:
                projected_leg6[field] = None
                continue
            number = _project_number(value, reasons, "bottleneck_field_invalid")
            if number is not None:
                projected_leg6[field] = number
        for field in ("hits", "n_filers"):
            value = leg6.get(field)
            count = _project_count(value, reasons, "bottleneck_field_invalid")
            if count is not None:
                projected_leg6[field] = count
        provisional = leg6.get("provisional")
        if isinstance(provisional, bool):
            projected_leg6["provisional"] = provisional
        projected["leg6_detail"] = projected_leg6
    fingerprint = _project_fingerprint(bottleneck_state.get("fingerprint"), reasons)
    if fingerprint is not None:
        projected["fingerprint"] = fingerprint
    return projected


def _build_observations(regime_document, theme_key, roster, historical,
                        theme_qualified):
    """Project the dated observation sections.

    The revision reading and the bottleneck reading are independent parts. A
    failure in one part never erases the other: a part that fails an
    integrity check is dropped entirely, so no positive value survives it.

    Every assertion in this section depends on the configured theme identity,
    so an invalid or unavailable identity withholds the whole section instead
    of letting an empty roster stand in for a qualified one. The
    market-global risk reading is not part of this section and is not
    affected by it.

    Returns ``(section, revision_state, contributors, bottleneck,
    revision_reasons, bottleneck_reasons)``.
    """
    revisions = _mapping(regime_document.get("theme_revisions")) or {}
    bottleneck = _mapping(regime_document.get("bottleneck")) or {}
    revisions_themes = _mapping(revisions.get("themes")) or {}
    bottleneck_themes = _mapping(bottleneck.get("themes")) or {}
    revisions_state = _mapping(revisions_themes.get(theme_key)) or {}
    bottleneck_state = _mapping(bottleneck_themes.get(theme_key)) or {}
    clocks = _build_clocks(
        regime_document, revisions.get("asof"), bottleneck.get("asof"),
    )

    if historical:
        # Historical mode: every contextual value is withheld. The section
        # keeps only its status, the typed reason and the clocks that identify
        # which snapshot would have been projected; no measured value survives
        # a historical claim.
        return (_section("withheld", [HISTORICAL_REASON], clocks=clocks),
                {}, [], {}, [HISTORICAL_REASON], [HISTORICAL_REASON])

    if not theme_qualified:
        # The configured theme identity is invalid or unavailable. Every
        # reading below is keyed to that identity, so none of them is
        # projected and none of them is asserted.
        reasons = ["theme_identity_unqualified"]
        return (_section("unavailable", reasons, clocks=clocks),
                {}, [], {}, list(reasons), [])

    revision_reasons = []
    revision_state = {}
    contributors = []
    if not revisions_state:
        revision_reasons.append("revision_state_unavailable")
    else:
        revision_state = _build_revision_state(
            revisions_state, revisions.get("asof"), revision_reasons)
        contributors = _build_contributors(
            revisions_state, roster, revision_reasons)
        n_covered = revision_state.get("n_covered")
        n_members = revision_state.get("n_members")
        coverage = revision_state.get("coverage")
        # One accepted-count predicate governs every count check, so an
        # integral float count is checked exactly like an integer count.
        if _is_count(n_covered) and _is_count(n_members):
            if n_members == 0:
                # a zero-member roster has no coverage ratio at all
                if n_covered:
                    revision_reasons.append("revision_counts_invalid")
                if coverage is not None:
                    revision_reasons.append("revision_coverage_inconsistent")
            elif n_covered > n_members:
                revision_reasons.append("revision_counts_invalid")
            else:
                ratio = _safe_ratio(n_covered, n_members)
                if ratio is None:
                    revision_reasons.append("revision_counts_invalid")
                elif coverage is not None and abs(coverage - ratio) > 1e-9:
                    revision_reasons.append("revision_coverage_inconsistent")
        if _is_count(n_members) and n_members != len(roster):
            revision_reasons.append("roster_count_mismatch")
        if _is_count(n_covered) and n_covered != len(contributors):
            revision_reasons.append("contributors_count_mismatch")

    bottleneck_reasons = []
    bottleneck_projection = {}
    if not bottleneck_state:
        bottleneck_reasons.append("bottleneck_unavailable")
    else:
        bottleneck_projection = _build_bottleneck(
            bottleneck_state, bottleneck.get("asof"), bottleneck_reasons)

    revision_ok = bool(revisions_state) and not any(
        reason in _REVISION_INTEGRITY_REASONS for reason in revision_reasons)
    bottleneck_ok = bool(bottleneck_state) and not any(
        reason in _BOTTLENECK_INTEGRITY_REASONS for reason in bottleneck_reasons)

    reasons = list(revision_reasons) + list(bottleneck_reasons)
    if revision_ok and bottleneck_ok:
        status = "available"
    elif revision_ok or bottleneck_ok:
        status = "partial"
    else:
        status = "unavailable"

    section = _section(status, reasons, clocks=clocks)
    if revision_ok:
        section["units"] = _project_units(revisions)
        section["revision_state"] = revision_state
        section["contributors"] = contributors
    if bottleneck_ok:
        section["bottleneck"] = bottleneck_projection
    return (section,
            revision_state if revision_ok else {},
            contributors if revision_ok else [],
            bottleneck_projection if bottleneck_ok else {},
            revision_reasons,
            bottleneck_reasons)


# ---------------------------------------------------------------------------
# 6. Market-global risk (separate from the sector reading)
# ---------------------------------------------------------------------------

def _project_measured_state(raw, reasons):
    measured = _mapping(raw)
    if measured is None:
        reasons.append("market_risk_field_invalid")
        return None
    projected = {}
    verdict = measured.get("verdict")
    if isinstance(verdict, str) and verdict:
        projected["verdict"] = verdict
    else:
        reasons.append("market_risk_field_invalid")
    score = measured.get("score")
    number = _project_number(score, reasons, "market_risk_field_invalid")
    if number is not None:
        projected["score"] = number
    usable = measured.get("usable")
    if isinstance(usable, bool):
        projected["usable"] = usable
    else:
        reasons.append("market_risk_field_invalid")
    for field in ("as_of", "role", "source_artifact"):
        value = measured.get(field)
        if isinstance(value, str) and value:
            projected[field] = value
    return projected


def _project_hazard_summary(raw, reasons):
    hazard = _mapping(raw)
    if hazard is None:
        reasons.append("market_risk_field_invalid")
        return None
    projected = {}
    for field in ("stage", "stage_reason", "stage_since", "stage_since_basis"):
        value = hazard.get(field)
        if isinstance(value, str) and value:
            projected[field] = value
        elif value is None and field == "stage":
            projected[field] = None       # a genuine owner null is preserved
    for field in ("primary_episode_id",):
        value = hazard.get(field)
        if value is None or isinstance(value, str):
            projected[field] = value
    count = hazard.get("active_episode_count")
    projected_count = _project_count(count, reasons, "market_risk_field_invalid")
    if projected_count is not None:
        projected["active_episode_count"] = projected_count
    for field in ("contributing_sources", "unreadable_sources", "capped_sources",
                  "unmapped_required_sources"):
        value = hazard.get(field)
        if isinstance(value, list):
            projected[field] = [item for item in value if isinstance(item, str)]
    display_only = hazard.get("display_only")
    if isinstance(display_only, bool):
        projected["display_only"] = display_only
    return projected


def _project_risk_freshness(raw, reasons):
    freshness = _mapping(raw)
    if freshness is None:
        reasons.append("market_risk_field_invalid")
        return None
    projected = {}
    source_session = freshness.get("source_session")
    if isinstance(source_session, str) and source_session:
        projected["source_session"] = source_session
    all_on_session = freshness.get("all_on_session")
    if isinstance(all_on_session, bool):
        projected["all_on_session"] = all_on_session
    else:
        reasons.append("market_risk_field_invalid")
    off_session = freshness.get("off_session_sources")
    if isinstance(off_session, list):
        projected["off_session_sources"] = [
            item for item in off_session if isinstance(item, str)]
    per_source = _mapping(freshness.get("per_source"))
    if per_source is None:
        reasons.append("market_risk_field_invalid")
    else:
        projected_per_source = {}
        for name, entry in per_source.items():
            entry = _mapping(entry)
            if entry is None:
                reasons.append("market_risk_field_invalid")
                continue
            item = {}
            as_of = entry.get("as_of")
            if isinstance(as_of, str) and as_of:
                item["as_of"] = as_of
            matches = entry.get("matches_session")
            if isinstance(matches, bool):
                item["matches_session"] = matches
            state = entry.get("state")
            if isinstance(state, str) and state:
                item["state"] = state
            projected_per_source[name] = item
        projected["per_source"] = projected_per_source
    return projected


def _project_coherence(raw, reasons):
    coherence = _mapping(raw)
    if coherence is None:
        reasons.append("market_risk_field_invalid")
        return None
    projected = {}
    state = coherence.get("state")
    if isinstance(state, str) and state:
        projected["state"] = state
    else:
        reasons.append("market_risk_field_invalid")
    count = coherence.get("contradiction_count")
    projected_count = _project_count(count, reasons, "market_risk_field_invalid")
    if projected_count is not None:
        projected["contradiction_count"] = projected_count
    contradictions = coherence.get("contradictions")
    if isinstance(contradictions, list):
        # the projected list shares nothing with the supplied document
        projected["contradictions"] = _detach(contradictions)
    for field in ("compares", "excludes"):
        value = coherence.get(field)
        if isinstance(value, list):
            projected[field] = [item for item in value if isinstance(item, str)]
    scope = coherence.get("scope")
    if isinstance(scope, str) and scope:
        projected["scope"] = scope
    display_only = coherence.get("display_only")
    if isinstance(display_only, bool):
        projected["display_only"] = display_only
    return projected


def _project_policy_summary(raw, reasons):
    policy = _mapping(raw)
    if policy is None:
        reasons.append("market_risk_field_invalid")
        return None
    projected = {}
    for field in ("posture", "basis"):
        value = policy.get(field)
        if isinstance(value, str) and value:
            projected[field] = value
        else:
            reasons.append("market_risk_field_invalid")
    count = policy.get("policy_count")
    projected_count = _project_count(count, reasons, "market_risk_field_invalid")
    if projected_count is not None:
        projected["policy_count"] = projected_count
    active = policy.get("active_policy_ids")
    if isinstance(active, list):
        projected["active_policy_ids"] = [
            item for item in active if isinstance(item, str)]
    else:
        reasons.append("market_risk_field_invalid")
    display_only = policy.get("display_only")
    if isinstance(display_only, bool):
        projected["display_only"] = display_only
    return projected


def _project_source_authority(raw, reasons):
    authority = _mapping(raw)
    if authority is None:
        reasons.append("market_risk_field_invalid")
        return None
    projected = {}
    for field in ("envelope_may_execute", "envelope_may_gate", "envelope_may_rank",
                  "envelope_may_size", "policy_actions_require_individual_authority"):
        value = authority.get(field)
        if isinstance(value, bool):
            projected[field] = value
        else:
            reasons.append("market_risk_field_invalid")
    return projected


def _build_market_risk(public_risk_document, historical):
    """Project the market-global risk envelope.

    This is a separate, market-global descriptive reading. It never derives a
    sector hazard and it never fills a null hazard stage from an optional
    source.

    An incompatible owner input fails closed: no measured reading, no hazard,
    no policy and no reference survives it. With a compatible schema each
    subsection is qualified on its own: a failed subsection is withheld
    entirely, its independent siblings stay, and the returned admitted paths
    name only the readings that may be referenced.

    Returns ``(section, projected, admitted_paths)``.
    """
    reasons = []
    document = _mapping(public_risk_document)
    if document is None:
        return (_section("unavailable", ["invalid_public_risk_document"],
                         scope="market_global"), {}, frozenset())

    schema = document.get("schema")
    if not isinstance(schema, str) or not schema:
        # an owner document that does not declare the expected schema is an
        # incompatible owner input: nothing in it is admitted
        return (_section("unavailable", ["market_risk_schema_missing"],
                         scope="market_global"), {}, frozenset())
    if schema != _RISK_SCHEMA:
        return (_section("unavailable", ["market_risk_schema_unexpected"],
                         scope="market_global"), {}, frozenset())

    projected = {"scope": "market_global"}
    admitted_paths = set()

    for field in ("definition_id", "market", "bundle_id", "source_session", "as_of",
                  "observed_at", "produced_at", "revision", "data_state"):
        value = document.get(field)
        if isinstance(value, str) and value:
            projected[field] = value
            admitted_paths.add("market_risk." + field)
        else:
            reasons.append("market_risk_field_invalid")
    stale_after = document.get("stale_after")
    if stale_after is None or isinstance(stale_after, str):
        projected["stale_after"] = stale_after
        admitted_paths.add("market_risk.stale_after")

    def admit(name, value):
        """Keep one independently qualified subsection, or withhold it."""
        if value is None:
            return
        projected[name] = value
        for field, item in value.items():
            if item is not None:
                admitted_paths.add("market_risk." + name + "." + field)

    before = len(reasons)
    measured = _project_measured_state(document.get("measured_state"), reasons)
    if len(reasons) == before:
        admit("measured_state", measured)
    before = len(reasons)
    hazard = _project_hazard_summary(document.get("hazard_summary"), reasons)
    if len(reasons) == before:
        admit("hazard_summary", hazard)
    before = len(reasons)
    freshness = _project_risk_freshness(document.get("freshness"), reasons)
    if len(reasons) == before:
        admit("freshness", freshness)
    before = len(reasons)
    coherence = _project_coherence(document.get("coherence"), reasons)
    if len(reasons) == before:
        admit("coherence", coherence)
    before = len(reasons)
    policy = _project_policy_summary(document.get("policy_summary"), reasons)
    if len(reasons) == before:
        admit("policy_summary", policy)
    before = len(reasons)
    authority = _project_source_authority(document.get("authority"), reasons)
    if len(reasons) == before:
        admit("source_authority", authority)

    if historical:
        return (_section("withheld", [HISTORICAL_REASON], scope="market_global"),
                {}, frozenset())

    status = "available"
    if reasons:
        status = "partial" if admitted_paths else "unavailable"
    return _section(status, reasons, **projected), projected, admitted_paths


# ---------------------------------------------------------------------------
# 7. Comparison (four fixed, conditional alternatives)
# ---------------------------------------------------------------------------

def _entry(id_, status, statement, evidence_refs, check, reasons):
    return {
        "id": id_,
        "evaluation": "prospective_unevaluated",
        "status": status,
        "statement": statement,
        "evidence_refs": list(evidence_refs),
        "falsifier": {"check": check, "met": False},
        "reasons": list(reasons),
    }


def _withheld_statement(entry_id):
    """The statement used when context is withheld for a decision cutoff."""
    subjects = {
        "earnings_expectations":
            "the positive-revision-breadth reading",
        "narrow_or_fading_revisions":
            "the narrow-or-fading reading",
        "physical_supply_constraint":
            "the physical-supply reading",
        "market_or_other_causes":
            "the market-context reading",
    }
    return (
        "Withheld: the supplied snapshot is not qualified as available at the "
        "decision cutoff, so " + subjects[entry_id] + " is not asserted."
    )


def _unqualified_theme_statement(entry_id):
    """The statement used when the configured theme identity is not usable."""
    subjects = {
        "earnings_expectations":
            "the positive-revision-breadth reading",
        "narrow_or_fading_revisions":
            "the narrow-or-fading reading",
        "physical_supply_constraint":
            "the physical-supply reading",
    }
    return (
        "Withheld: the configured theme identity is unavailable or invalid, so "
        + subjects[entry_id] + " is not asserted."
    )


#: The controlled falsifier checks. They are fixed copy and never carry a
#: claim about the supplied evidence.
_EARNINGS_CHECK = (
    "A later qualified same-cohort snapshot that loses positive revision "
    "breadth would challenge this reading; check revision dates, coverage "
    "and revision counts."
)
_NARROW_CHECK = (
    "Later qualified broadening evidence with wider coverage would "
    "challenge this caution; no coverage threshold is asserted here."
)
_SUPPLY_CHECK = (
    "Qualified contemporaneous physical-supply owner evidence could "
    "change this assessment; provisional language-leg and fingerprint "
    "signals are insufficient alone."
)
_MARKET_CHECK = (
    "Owner evidence that establishes or contradicts a specified non-theme "
    "mechanism would be required to resolve this alternative."
)


def _build_comparison(context, revision_state, contributors, bottleneck,
                      historical, market_risk_status, market_risk_paths,
                      theme_qualified, revision_reasons, bottleneck_reasons):
    """Build the four fixed conditional alternatives.

    Every statement about positivity, coverage or neutrality is derived from
    the values actually supplied. A missing or changed value can never leave a
    stale positive claim behind: the entry becomes ``unresolved`` with a typed
    reason instead.

    The supplied owner level label and the numeric reading that would support
    it are kept apart. A stronger statement needs its own numeric support; a
    label on its own never carries it, and a conflicting observation makes the
    reading unresolved rather than positive.
    """
    entries = []
    revision_integrity = [reason for reason in revision_reasons
                           if reason in _REVISION_INTEGRITY_REASONS]
    bottleneck_integrity = [reason for reason in bottleneck_reasons
                            if reason in _BOTTLENECK_INTEGRITY_REASONS]

    def resolve(path):
        return _resolve(context, path)

    # -- 1. earnings_expectations -----------------------------------------
    if historical:
        entries.append(_entry(
            "earnings_expectations", "unresolved",
            _withheld_statement("earnings_expectations"), [],
            _EARNINGS_CHECK,
            [HISTORICAL_REASON],
        ))
    elif not theme_qualified:
        entries.append(_entry(
            "earnings_expectations", "unresolved",
            _unqualified_theme_statement("earnings_expectations"), [],
            _EARNINGS_CHECK,
            ["theme_identity_unqualified"],
        ))
    else:
        level_state = revision_state.get("level_state")
        if level_state is None:
            statement = (
                "The supplied revision level state is unavailable; the "
                "positive-revision-breadth reading is not established by this "
                "snapshot."
            )
            entries.append(_entry(
                "earnings_expectations", "unresolved", statement, [],
                _EARNINGS_CHECK,
                ["revision_level_state_unavailable"] + revision_integrity,
            ))
        elif level_state == "POSITIVE":
            # the supplied owner label is not the numeric support. The strong
            # statement is made only when the supplied observations support
            # it on their own.
            gap = None
            support_reason = None
            breadth = revision_state.get("breadth")
            n_covered = revision_state.get("n_covered")
            n_members = revision_state.get("n_members")
            if breadth is None:
                support_reason = "revision_breadth_unavailable"
                gap = "the supplied snapshot reports no revision breadth"
            elif breadth <= 0:
                support_reason = "revision_breadth_not_positive"
                gap = "the supplied revision breadth is not positive"
            elif not _is_count(n_covered) or not _is_count(n_members):
                support_reason = "coverage_unavailable"
                gap = "the supplied snapshot reports no covered-member counts"
            elif n_covered > n_members:
                support_reason = "revision_counts_invalid"
                gap = ("the covered-member count exceeds the "
                       "configured-member count")
            elif ("contributors_unavailable" in revision_reasons
                  or "contributors_too_large" in revision_reasons):
                support_reason = "contributors_unavailable"
                gap = "the supplied snapshot reports no covered-contributor rows"
            elif len(contributors) != n_covered:
                support_reason = "contributors_count_mismatch"
                gap = ("the covered-contributor rows do not match the "
                       "covered-member count")
            if support_reason is None:
                refs = [
                    "observations.revision_state.level_state",
                    "observations.revision_state.breadth",
                    "observations.revision_state.n_covered",
                    "observations.revision_state.n_members",
                ]
                refs = [ref for ref in refs if resolve(ref)]
                statement = (
                    "Positive revision breadth in the supplied snapshot is consistent "
                    "with improving covered-member expectations; price cause is not "
                    "established."
                )
                reasons = [] if refs else ["evidence_reference_unresolved"]
                entries.append(_entry(
                    "earnings_expectations",
                    "supported" if refs else "unresolved",
                    statement, refs,
                    _EARNINGS_CHECK,
                    reasons,
                ))
            else:
                refs = [
                    "observations.revision_state.level_state",
                    "observations.revision_state.breadth",
                ]
                refs = [ref for ref in refs if resolve(ref)]
                statement = (
                    "The supplied owner revision level state is " + level_state
                    + ", but " + gap + "; the positive-revision-breadth reading "
                    "is not established by this snapshot."
                )
                entries.append(_entry(
                    "earnings_expectations", "unresolved", statement, refs,
                    _EARNINGS_CHECK,
                    [support_reason] + revision_integrity,
                ))
        else:
            refs = [
                "observations.revision_state.level_state",
                "observations.revision_state.breadth",
            ]
            refs = [ref for ref in refs if resolve(ref)]
            statement = (
                "The supplied revision level state is " + level_state + "; the "
                "positive-revision-breadth reading is not established by this "
                "snapshot."
            )
            entries.append(_entry(
                "earnings_expectations", "unresolved", statement, refs,
                _EARNINGS_CHECK,
                ["revision_level_state_not_positive"],
            ))

    # -- 2. narrow_or_fading_revisions ------------------------------------
    if historical:
        entries.append(_entry(
            "narrow_or_fading_revisions", "unresolved",
            _withheld_statement("narrow_or_fading_revisions"), [],
            _NARROW_CHECK,
            [HISTORICAL_REASON],
        ))
    elif not theme_qualified:
        entries.append(_entry(
            "narrow_or_fading_revisions", "unresolved",
            _unqualified_theme_statement("narrow_or_fading_revisions"), [],
            _NARROW_CHECK,
            ["theme_identity_unqualified"],
        ))
    else:
        n_covered = revision_state.get("n_covered")
        n_members = revision_state.get("n_members")
        broadening_state = revision_state.get("broadening_state")
        level_state = revision_state.get("level_state")
        missing = []
        if not _is_count(n_covered) or not _is_count(n_members):
            missing.append("coverage_unavailable")
        if broadening_state is None:
            missing.append("broadening_state_unavailable")
        if level_state is None:
            missing.append("level_state_unavailable")
        if missing:
            coverage_phrase = (
                "coverage " + str(n_covered) + " of " + str(n_members)
                if "coverage_unavailable" not in missing
                else "coverage unavailable")
            broadening_phrase = (
                "broadening state " + broadening_state
                if "broadening_state_unavailable" not in missing
                else "broadening state unavailable")
            level_phrase = (
                "level state " + level_state
                if "level_state_unavailable" not in missing
                else "level state unavailable")
            statement = (
                "The supplied revision snapshot does not establish the "
                "narrow-or-fading reading: " + coverage_phrase + ", "
                + broadening_phrase + ", " + level_phrase + "."
            )
            entries.append(_entry(
                "narrow_or_fading_revisions", "unresolved", statement, [],
                _NARROW_CHECK,
                missing + revision_integrity,
            ))
        elif n_covered >= n_members:
            refs = [
                "observations.revision_state.coverage",
                "observations.revision_state.n_covered",
                "observations.revision_state.n_members",
                "observations.revision_state.broadening_state",
            ]
            refs = [ref for ref in refs if resolve(ref)]
            statement = (
                "The supplied snapshot covers " + str(n_covered) + " of "
                + str(n_members) + " configured members with broadening state "
                + broadening_state + " and level state " + level_state + "; the "
                "narrow-or-fading reading is not established."
            )
            entries.append(_entry(
                "narrow_or_fading_revisions", "unresolved", statement, refs,
                _NARROW_CHECK,
                ["coverage_not_partial"],
            ))
        elif broadening_state != "ROLLING":
            refs = [
                "observations.revision_state.coverage",
                "observations.revision_state.n_covered",
                "observations.revision_state.n_members",
                "observations.revision_state.broadening_state",
            ]
            refs = [ref for ref in refs if resolve(ref)]
            statement = (
                "The supplied snapshot covers " + str(n_covered) + " of "
                + str(n_members) + " configured members with broadening state "
                + broadening_state + "; the narrow-or-fading reading is not "
                "established by this snapshot."
            )
            entries.append(_entry(
                "narrow_or_fading_revisions", "unresolved", statement, refs,
                _NARROW_CHECK,
                ["broadening_state_not_rolling"],
            ))
        else:
            refs = [
                "observations.revision_state.coverage",
                "observations.revision_state.n_covered",
                "observations.revision_state.n_members",
                "observations.revision_state.broadening_state",
                "observations.revision_state.level_state",
            ]
            refs = [ref for ref in refs if resolve(ref)]
            statement = (
                "Coverage of " + str(n_covered) + " of " + str(n_members)
                + " configured members with source-native broadening state "
                + broadening_state + " warrants caution on breadth and momentum "
                "despite a " + level_state + " level state."
            )
            reasons = [] if refs else ["evidence_reference_unresolved"]
            entries.append(_entry(
                "narrow_or_fading_revisions",
                "supported" if refs else "unresolved",
                statement, refs,
                _NARROW_CHECK,
                reasons,
            ))

    # -- 3. physical_supply_constraint ------------------------------------
    if historical:
        entries.append(_entry(
            "physical_supply_constraint", "unresolved",
            _withheld_statement("physical_supply_constraint"), [],
            _SUPPLY_CHECK,
            [HISTORICAL_REASON],
        ))
    elif not theme_qualified:
        entries.append(_entry(
            "physical_supply_constraint", "unresolved",
            _unqualified_theme_statement("physical_supply_constraint"), [],
            _SUPPLY_CHECK,
            ["theme_identity_unqualified"],
        ))
    else:
        band = bottleneck.get("band")
        bottleneck_asof = bottleneck.get("asof")
        revision_asof = revision_state.get("asof")
        if band is None or bottleneck_asof is None:
            refs = []
            statement = (
                "The supplied bottleneck snapshot does not expose a band and a "
                "date; no contemporaneous physical-tightness assessment is "
                "asserted."
            )
            reasons = []
            if band is None:
                reasons.append("bottleneck_band_unavailable")
            if bottleneck_asof is None:
                reasons.append("bottleneck_asof_unavailable")
            entries.append(_entry(
                "physical_supply_constraint", "unresolved", statement, refs,
                _SUPPLY_CHECK,
                reasons + bottleneck_integrity,
            ))
        else:
            refs = [
                "observations.bottleneck.band",
                "observations.bottleneck.asof",
                "observations.bottleneck.numeric_composite",
                "observations.bottleneck.fingerprint",
            ]
            refs = [ref for ref in refs if resolve(ref)]
            # each provisional sentence is generated from its own owner flag
            leg6 = _mapping(bottleneck.get("leg6_detail")) or {}
            provisional_parts = []
            if leg6.get("provisional") is True:
                provisional_parts.append("language leg")
            fingerprint = _mapping(bottleneck.get("fingerprint")) or {}
            if fingerprint.get("provisional") is True:
                provisional_parts.append("member fingerprint")
            if revision_asof and revision_asof == bottleneck_asof:
                statement = (
                    "The bottleneck snapshot dated " + bottleneck_asof
                    + " with band " + band + " is contemporaneous with the "
                    "revision snapshot and does not by itself confirm physical "
                    "tightness."
                )
            elif revision_asof:
                statement = (
                    "The separately dated bottleneck snapshot (band " + band
                    + ", as of " + bottleneck_asof
                    + ") does not confirm contemporaneous physical tightness in "
                    "the revision snapshot dated " + revision_asof + "."
                )
            else:
                statement = (
                    "The separately dated bottleneck snapshot (band " + band
                    + ", as of " + bottleneck_asof
                    + ") does not confirm contemporaneous physical tightness."
                )
            if provisional_parts:
                verb = "is" if len(provisional_parts) == 1 else "are"
                statement += (" Its " + " and ".join(provisional_parts) + " "
                              + verb + " provisional.")
            entries.append(_entry(
                "physical_supply_constraint",
                "supported" if refs else "unresolved",
                statement, refs,
                _SUPPLY_CHECK,
                ([] if refs else ["evidence_reference_unresolved"])
                + bottleneck_integrity,
            ))

    # -- 4. market_or_other_causes ----------------------------------------
    # a reference must resolve to an admitted reading, not merely to a field
    # that happens to be present in a withheld subsection
    candidate_refs = [
        "market_risk.measured_state.verdict",
        "market_risk.data_state",
        "market_risk.hazard_summary.stage_reason",
        "market_risk.coherence.state",
    ]
    refs = [ref for ref in candidate_refs
            if ref in market_risk_paths and resolve(ref)]
    reasons = ["alternatives_not_resolved_by_supplied_evidence"]
    if historical:
        statement = _withheld_statement("market_or_other_causes")
        reasons = [HISTORICAL_REASON] + reasons
    else:
        statement = (
            "Market-global risk is descriptive context, not a causal explanation "
            "of the theme revision state; resolving this alternative needs owner "
            "evidence that establishes or contradicts a specified mechanism."
        )
        if market_risk_status == "unavailable":
            reasons.append("market_risk_unavailable")
        elif market_risk_status != "available":
            reasons.append("market_risk_field_invalid")
    entries.append(_entry(
        "market_or_other_causes", "unresolved", statement, refs,
        _MARKET_CHECK,
        reasons,
    ))

    reasons = []
    for item in entries:
        if len(item["statement"]) > LIMITS["max_statement_chars"]:
            reasons.append("comparison_statement_too_long")
        if len(item["falsifier"]["check"]) > LIMITS["max_check_chars"]:
            reasons.append("comparison_check_too_long")
    if reasons:
        return _section("unavailable", reasons,
                        evaluation="prospective_unevaluated", entries=[]), {}
    status = "available"
    section_reasons = []
    if historical:
        # the four controlled alternatives and their falsifiers are still
        # projected, but every reading they carry is withheld
        status = "withheld"
        section_reasons = [HISTORICAL_REASON]
    elif any(reason in _READING_BLOCKED_REASONS
             for item in entries for reason in item["reasons"]):
        status = "partial"
    return _section(status, section_reasons,
                    evaluation="prospective_unevaluated",
                    entries=entries), {item["id"]: item for item in entries}


# ---------------------------------------------------------------------------
# 8. Provenance
# ---------------------------------------------------------------------------

def _build_provenance(source_attribution):
    """Carry the caller-supplied attribution without claiming verification.

    The attribution is caller-supplied. A decoded dictionary cannot establish
    raw SHA equality, so the projection never claims custody, receipt or
    original availability for the attributed bytes.
    """
    reasons = []
    projected = {}
    attribution = _mapping(source_attribution)
    if attribution is None:
        reasons.append("invalid_source_attribution")
    else:
        for key in ATTRIBUTION_KEYS:
            entry = _mapping(attribution.get(key))
            if entry is None:
                reasons.append("invalid_source_attribution")
                projected[key] = {"source_ref": None, "raw_sha256": None}
                continue
            source_ref = entry.get("source_ref")
            raw_sha256 = entry.get("raw_sha256")
            if (not isinstance(source_ref, str) or not source_ref
                    or len(source_ref) > LIMITS["max_source_ref_chars"]):
                reasons.append("source_ref_invalid")
                source_ref = None
            if not isinstance(raw_sha256, str) or not _SHA256_RE.match(raw_sha256):
                reasons.append("raw_sha256_invalid")
                raw_sha256 = None
            projected[key] = {"source_ref": source_ref, "raw_sha256": raw_sha256}
    status = "available" if not reasons else ("partial" if projected else "unavailable")
    return _section(
        status, reasons,
        source_attribution=projected,
        attribution_verification="not_established_by_projection",
        projection={
            "schema": SCHEMA,
            "deterministic": True,
            "reads": list(ATTRIBUTION_KEYS) + ["source_attribution"],
            "writes": [],
        },
    )


# ---------------------------------------------------------------------------
# 9. The projection
# ---------------------------------------------------------------------------

def project_dated_context(*, theme_key, regime_document, config_document,
                          public_risk_document, source_attribution,
                          decision_cutoff=None):
    """Project a dated configured-theme context and market-global risk.

    Parameters
    ----------
    theme_key:
        The configured theme key, e.g. ``"memory_storage"``.
    regime_document, config_document, public_risk_document:
        Already-decoded owner documents. They are read, never mutated, and
        never re-fetched, rebuilt or recalculated.
    source_attribution:
        Caller-supplied ``{"regime_document": {...}, "config_document": {...},
        "public_risk_document": {...}}`` with a bounded ``source_ref`` and an
        exact 64-character lowercase-hex ``raw_sha256`` per document. This is
        attribution only: the projection never verifies custody or original
        availability from it.
    decision_cutoff:
        Optional aware ISO datetime. When supplied, the projection enters
        historical mode and withholds every contextual value with the reason
        ``historical_availability_unqualified``. An invalid cutoff produces a
        typed unavailable result.

    Returns
    -------
    dict
        A detached, deterministic projection with the fixed sections
        ``theme``, ``observations``, ``comparison``, ``market_risk``,
        ``provenance``, ``limitations`` and ``authority``, plus ``schema``,
        ``status`` and ``scope``.
    """
    # -- the cutoff is validated first and fails closed --------------------
    historical = decision_cutoff is not None
    if historical and not _parse_decision_cutoff(decision_cutoff):
        return _refuse(theme_key, ["invalid_decision_cutoff"])

    if (not isinstance(theme_key, str) or not theme_key
            or len(theme_key) > LIMITS["max_theme_key_chars"]):
        return _refuse(theme_key, ["invalid_theme_key"])

    regime = _mapping(regime_document)
    config = _mapping(config_document)
    risk = _mapping(public_risk_document)
    document_reasons = []
    if regime is None:
        document_reasons.append("invalid_regime_document")
    if config is None:
        document_reasons.append("invalid_config_document")
    if risk is None:
        document_reasons.append("invalid_public_risk_document")
    if document_reasons:
        return _refuse(theme_key, document_reasons)

    # -- bounded scan of the selected branches only ------------------------
    regime_counter = [0]
    config_counter = [0]
    risk_counter = [0]
    scan_reasons = []
    revisions = _mapping(regime.get("theme_revisions")) or {}
    bottleneck = _mapping(regime.get("bottleneck")) or {}
    revisions_themes = _mapping(revisions.get("themes")) or {}
    bottleneck_themes = _mapping(bottleneck.get("themes")) or {}
    config_themes = _mapping(config.get("themes")) or {}

    selections = (
        (regime_counter, regime.get("asof")),
        (regime_counter, regime.get("freshness")),
        (regime_counter, revisions.get("asof")),
        (regime_counter, revisions.get("weights")),
        (regime_counter, revisions_themes.get(theme_key)),
        (regime_counter, bottleneck.get("asof")),
        (regime_counter, bottleneck_themes.get(theme_key)),
        (config_counter, config_themes.get(theme_key)),
        (risk_counter, risk.get("measured_state")),
        (risk_counter, risk.get("hazard_summary")),
        (risk_counter, risk.get("freshness")),
        (risk_counter, risk.get("coherence")),
        (risk_counter, risk.get("policy_summary")),
        (risk_counter, risk.get("authority")),
    )
    for counter, node in selections:
        if node is None:
            continue
        problem = _bounded_scan(node, counter)
        if problem:
            scan_reasons.append(problem)
            break
    if scan_reasons:
        return _refuse(theme_key, scan_reasons)

    # -- sections ----------------------------------------------------------
    theme_section = _build_theme(theme_key, config)
    roster = theme_section.get("roster") or []
    theme_qualified = theme_section.get("status") == "available"
    (observations_section, revision_state, contributors, bottleneck_projection,
     revision_reasons, bottleneck_reasons) = _build_observations(
        regime, theme_key, roster, historical, theme_qualified)
    (market_risk_section, _market_risk_projection,
     market_risk_paths) = _build_market_risk(risk, historical)

    context = {
        "theme": theme_section,
        "observations": observations_section,
        "market_risk": market_risk_section,
    }
    comparison_section, _ = _build_comparison(
        context, revision_state, contributors, bottleneck_projection, historical,
        market_risk_section.get("status"), market_risk_paths, theme_qualified,
        revision_reasons, bottleneck_reasons)
    provenance_section = _build_provenance(source_attribution)

    # -- status ------------------------------------------------------------
    # The status reports which EVIDENCE sections were projected. It never
    # reports the freshness or the quality of an owner, and it never reports
    # the caller-supplied attribution, which is carried with its own status
    # inside the provenance section.
    if theme_section["status"] != "available":
        status = "unavailable"
    elif (observations_section["status"] == "available"
          and comparison_section["status"] == "available"
          and market_risk_section["status"] == "available"):
        status = "dated_context"
    else:
        status = "partial"

    result = {
        "schema": SCHEMA,
        "status": status,
        "scope": SCOPE,
        "theme": theme_section,
        "observations": observations_section,
        "comparison": comparison_section,
        "market_risk": market_risk_section,
        "provenance": provenance_section,
        "limitations": _limitations(),
        "authority": _authority(),
    }

    # -- output bound: never truncate silently -----------------------------
    return _bounded_result(result, theme_key)
