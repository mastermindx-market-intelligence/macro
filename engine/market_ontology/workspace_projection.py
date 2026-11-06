"""``workspace_projection`` — bridge production ``event_workspace.v1`` payloads
into the composer row shape ``_build_economics`` consumes.

Operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001 (carrier
PR #7870), T08b + T08b-fix. The composer's
:func:`semiconductor_theme_research._build_economics` keys on rows shaped like
the synthetic witness fixture
(``tests/fixtures/semiconductor_theme_research/witness_hbm_packaging.json`` —
``event_id``, ``cik``/``company_node_id``, ``fiscal_period{year,quarter}``,
``guidance`` of ``guidance_item.v1`` items, ``reported`` rows with a closed
``fiscal_period`` ``"YYYYQn"`` token, and a lifecycle whose ``recorded_at``
the ``system_replay`` gate reads). Production intake
(``scripts/refresh_event_workspaces.py`` +
``engine/company_intelligence/event_workspace.py``) emits a different shape:
``facts`` of ``event_fact.v1`` with an ISO ``period`` end and an optional
``typed_absence`` envelope, ``guidance`` of the same v1 items, an ``issuer``
block (``company_id`` carries the canonical ``cik:0000000000``), a
``fiscal_period`` block that ALSO carries ``calendar_end``, and a lifecycle
``{state, observed_at, source_available_at}`` with NO ``recorded_at``.
Without this bridge the composer silently emits
``economics.unavailable / management_sequence_missing`` even when a perfectly
admitted real workspace reaches the bundle, and drops every real workspace in
``system_replay``.

Laws (each pinned in ``tests/test_workspace_projection.py``)
------------------------------------------------------------
* PURE and CLOSED: imports are ``copy``, ``datetime`` (parsers only — the
  clock is never read; no ``now``/``today``), ``math`` and ``typing`` — no
  engine import, no I/O, no network, no regular expressions.
* NEVER RAISES: every malformed input degrades to ``None`` (whole payload) or
  to a dropped field plus a typed omission token; no exception escapes for
  any input.
* VERBATIM, NEVER PARSED: a fact ``value`` is numeric iff
  ``isinstance(v, (int, float)) and not isinstance(v, bool)`` and, for a
  float, ``math.isfinite(v)``. A string is NOT a number (``"40.2"``,
  ``"2026"``, ``"2"`` are refused). ``fiscal_period.year`` / ``.quarter`` are
  accepted iff they are non-bool ``int`` with year in 1000..9999 (so the
  token is a genuine four-digit ``YYYY``) and quarter in 1..4. Nothing is
  coerced, normalised, defaulted or invented; the closed ``"YYYYQn"`` token
  is formed ONLY from the workspace block's int year and quarter — never
  from a fact's ISO ``period`` or any date.
* NON-FINITE: a numeric ``value`` that is NaN or ±inf is treated as not
  present — the fact is dropped and ``"reported_non_finite:<metric>"`` is
  recorded once per metric.
* CLOSED TOKENS: ``basis`` / ``currency`` / ``perimeter`` / ``definition`` /
  ``unit`` are tokens; when present they must be ``str`` (or ``None``), else
  the fact is malformed and dropped with ``"reported_malformed:<metric>"``
  (an unhashable ``basis`` such as a dict or list therefore never reaches a
  collision key).
* COLLISION: two present facts sharing ``(metric, basis)`` are ambiguous —
  NEITHER is emitted and ``"reported_ambiguous:<metric>"`` is recorded.
* UNKEYED PERIOD: when present facts exist but the workspace's ``year`` is
  not an int in 1000..9999 (so no ``"YYYYQn"`` token can be formed), the
  facts are dropped, ``fiscal_period.year`` is emitted as ``None`` and
  ``"reported_unkeyed:fiscal_period"`` is recorded once. A quarter that is
  not an int in 1..4 refuses the WHOLE payload (``None``) because the
  composer refuses a non-int quarter.
* CLOSED CIK GRAMMAR: ``issuer.company_id`` is accepted ONLY as
  ``cik:<digits>`` or ``cik<digits>`` (case-insensitive prefix) or a bare
  ASCII all-digit string of 1..10 digits, not all zeros; the digits are
  emitted zero-padded to ten (the identifier namespace ``_company_key``
  compares as ``cik:0000000000``). Anything else (LEI, ticker, prose,
  unicode digits, surrounding whitespace, an all-zero run) yields no CIK — and a payload whose CIK cannot be parsed is
  refused as a WHOLE (``None``), never emitted with ``cik: None``: the
  composer's ``_company_key`` would collapse every unknown-CIK workspace into
  the shared ``"cik:"`` bucket and pair one issuer's guidance with another's
  actual.
* FRESH COPIES: guidance items are deep-copied (token values are immutable
  ``str``/``None`` and need no copy); a downstream mutation never writes into
  the producer's payload. A guidance item that is not a mapping, or that
  cannot be deep-copied (an unpicklable member, pathological nesting), is
  dropped with ``"guidance_malformed_item"`` recorded once (the composer
  calls ``.get`` on each item).
* CLOCK STRINGS: ``lifecycle.source_available_at`` / ``.observed_at`` are
  copied only when they are strings in the grammar the composer's replay
  gate parses (``YYYY-MM-DD`` or an ISO-8601 instant, ``Z`` accepted) — the
  literal ``"unknown"`` is also copied for ``source_available_at`` because
  the composer types it. An explicit ``None`` under either key is production's
  typed absence (``_lifecycle_payload`` emits ``None`` for an unknown clock) and
  is dropped silently; anything else present under those keys is dropped
  with ``"lifecycle_malformed:<key>"``, so the composer's ``_le`` never sees a
  string it cannot parse.
* TWO CLOCKS (N11): production's system-recording clock is
  ``lifecycle.observed_at`` — real wall-clock ``now`` at first observation,
  carried forward unchanged by
  ``scripts/refresh_event_workspaces.py::prior_observed_at``. This bridge
  emits ``lifecycle.recorded_at = lifecycle.observed_at`` WHEN AND ONLY WHEN
  ``observed_at`` is present as a non-empty clock string (grammar above),
  keeping ``observed_at`` alongside. ``recorded_at`` is NEVER derived from ``generated_at`` or from a
  manifest — those are the SOURCE clock
  (``refresh_event_workspaces.py``: ``source_clock = acceptance_datetime``,
  which becomes ``source_available_at``; the two-clock violation
  ``observed_at=source_clock`` was removed everywhere else). A
  payload-supplied ``recorded_at`` is not a production field and is not
  copied.

Consumer fact (documented, not changed here): the composer reads only
``OwnerBundle.omissions`` (``_Selection`` lifts them into ``limitations`` as
``omitted:<name>``), so the BINDER that assembles the bundle must lift this
row's ``omissions`` into the bundle's ``omissions``; the row-level list is
the binder's input, not a composer input.

NON-AUTHORING: every emitted value is an echo of an input the caller passed
in or a closed classification over those inputs. No arithmetic, no unit
conversion, no derived midpoint, no ranking, no sizing, no authority flag.
"""
from __future__ import annotations

import copy
import math
from datetime import datetime
from typing import Any, Mapping

__all__ = ["project_event_workspace"]

# Closed token keys copied verbatim from a present fact into the composer's
# ``reported`` row WHEN PRESENT (never invented, never defaulted).
_REPORTED_OPTIONAL_KEYS = ("basis", "currency", "perimeter", "definition")

# Production lifecycle keys copied verbatim WHEN PRESENT. ``recorded_at`` is
# NOT in this tuple: it is derived from ``observed_at`` (two-clock law above)
# and a payload-supplied value is never copied.
_LIFECYCLE_COPY_KEYS = ("source_available_at", "observed_at")

_ASCII_DIGITS = frozenset("0123456789")
_CIK_MAX_DIGITS = 10
_YEAR_MIN, _YEAR_MAX = 1000, 9999
_SOURCE_AVAILABILITY_TYPED_UNKNOWN = "unknown"  # the composer types this literal


# ---------------------------------------------------------------------------
# Closed predicates — no coercion anywhere
# ---------------------------------------------------------------------------

def _is_int(value: Any) -> bool:
    """A real ``int`` (``bool`` is refused; a numeric string is refused)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    """``int`` or ``float`` (not ``bool``); finiteness is judged separately."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_numeric(value: Any) -> bool:
    """A value is numeric iff it is a non-bool ``int``/``float`` AND finite.

    An ``int`` is always finite (``math.isfinite`` is only consulted for a
    ``float`` — calling it on an arbitrarily large int would raise)."""
    if not _is_number(value):
        return False
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def _is_token(value: Any) -> bool:
    """A closed token slot holds a ``str`` or an explicit ``None``."""
    return value is None or isinstance(value, str)


def _is_quarter(value: Any) -> bool:
    return _is_int(value) and 1 <= value <= 4


def _is_year(value: Any) -> bool:
    """A four-digit int year — the only year that forms a closed ``YYYY``."""
    return _is_int(value) and _YEAR_MIN <= value <= _YEAR_MAX


def _is_clock_string(value: Any) -> bool:
    """True iff ``value`` is a non-empty string the composer's replay gate can
    parse: a ``YYYY-MM-DD`` day or an ISO-8601 instant (``Z`` accepted) —
    the same two parsers the composer applies. Pure: nothing is converted or
    emitted, the clock is never read."""
    if not isinstance(value, str) or not value:
        return False
    try:
        if "T" in value:
            text = value[:-1] + "+00:00" if value.endswith("Z") else value
            datetime.fromisoformat(text)   # tz-naive instants are accepted as UTC by the composer
        else:
            datetime.strptime(value, "%Y-%m-%d")
    except Exception:  # noqa: BLE001 — a str subclass with a hostile protocol is not a clock string
        return False
    return True


def _parse_cik(raw: Any) -> str | None:
    """Closed CIK grammar (N3): ``cik:<digits>``, ``cik<digits>``
    (case-insensitive prefix) or a bare ASCII all-digit string of 1..10
    digits, not all zeros. No stripping, no search, no regex; anything else
    → ``None``."""
    if not isinstance(raw, str) or not raw:
        return None
    lowered = raw.lower()
    if lowered.startswith("cik:"):
        digits = raw[4:]
    elif lowered.startswith("cik"):
        digits = raw[3:]
    else:
        digits = raw
    if not 1 <= len(digits) <= _CIK_MAX_DIGITS:
        return None
    if not all(char in _ASCII_DIGITS for char in digits):
        return None
    if set(digits) == {"0"}:
        return None  # an all-zero run is not an issuer; it would key the shared bucket
    return digits.zfill(_CIK_MAX_DIGITS)


def _record(omissions: list[str], token: str) -> None:
    """Append an omission token once (order-preserving)."""
    if token not in omissions:
        omissions.append(token)


# ---------------------------------------------------------------------------
# Projections
# ---------------------------------------------------------------------------

def _fiscal_period_token(year: Any, quarter: Any) -> str | None:
    """The closed ``"YYYYQn"`` token the composer's ``_fiscal_key`` parses —
    formed ONLY from a four-digit int year and an int quarter in 1..4."""
    if not _is_year(year) or not _is_quarter(quarter):
        return None
    return f"{year}Q{quarter}"


def _project_reported(
    facts: Any, token: str | None, omissions: list[str],
) -> list[dict[str, Any]]:
    """Map ``event_fact.v1`` payloads → composer ``reported`` rows under the
    laws in the module docstring (present-only, verbatim, closed tokens,
    collision → neither row, unkeyed period → typed omission)."""
    if not isinstance(facts, (list, tuple)):
        return []

    # First pass: classify every fact; nothing here can raise for any input.
    present: list[tuple[str, Any, Mapping[str, Any]]] = []
    for fact in facts:
        if not isinstance(fact, Mapping):
            continue
        if "typed_absence" in fact:
            continue
        metric = fact.get("metric")
        if not isinstance(metric, str) or not metric:
            continue
        value = fact.get("value")
        if not _is_numeric(value):
            if _is_number(value):
                _record(omissions, f"reported_non_finite:{metric}")
            continue
        if not _is_token(fact.get("unit")) or any(
            key in fact and not _is_token(fact[key]) for key in _REPORTED_OPTIONAL_KEYS
        ):
            _record(omissions, f"reported_malformed:{metric}")
            continue
        basis = fact.get("basis") if "basis" in fact else None
        present.append((metric, basis, fact))

    if not present:
        return []
    if token is None:
        _record(omissions, "reported_unkeyed:fiscal_period")
        return []

    groups: dict[tuple[str, str | None], list[Mapping[str, Any]]] = {}
    for metric, basis, fact in present:
        groups.setdefault((metric, basis), []).append(fact)

    rows: list[dict[str, Any]] = []
    for (metric, _basis), members in groups.items():
        if len(members) > 1:
            _record(omissions, f"reported_ambiguous:{metric}")
            continue
        fact = members[0]
        row: dict[str, Any] = {
            "metric": metric,
            "value": fact["value"],
            "unit": fact.get("unit"),          # str | None — immutable, verbatim
            "fiscal_period": token,
        }
        for optional in _REPORTED_OPTIONAL_KEYS:
            if optional in fact:
                row[optional] = fact[optional]  # str | None — immutable, verbatim
        rows.append(row)
    rows.sort(key=lambda r: (r["metric"], r.get("basis") or ""))
    return rows


def _project_guidance(raw: Any, omissions: list[str]) -> list[Any]:
    """Deep-copy ``guidance_item.v1`` mappings verbatim. A non-list yields
    ``[]``; a non-mapping item, or one that cannot be deep-copied, is dropped
    with ``guidance_malformed_item``."""
    if not isinstance(raw, (list, tuple)):
        return []
    items: list[Any] = []
    for item in raw:
        if not isinstance(item, Mapping):
            _record(omissions, "guidance_malformed_item")
            continue
        try:
            items.append(copy.deepcopy(item))
        except Exception:  # noqa: BLE001 — unpicklable member / pathological nesting
            _record(omissions, "guidance_malformed_item")
    return items


def _project_lifecycle(raw: Any, omissions: list[str]) -> dict[str, Any]:
    """Copy ``source_available_at`` / ``observed_at`` verbatim WHEN PRESENT
    as clock strings the composer can parse, and derive ``recorded_at`` from
    ``observed_at`` under the two-clock law. Missing keys are dropped, never
    coerced to ``None``; a present value outside the clock grammar is dropped
    with ``lifecycle_malformed:<key>``."""
    if not isinstance(raw, Mapping):
        return {}
    projected: dict[str, Any] = {}
    for key in _LIFECYCLE_COPY_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if value is None:
            continue  # production's typed absence (_lifecycle_payload emits None): dropped, not malformed
        if _is_clock_string(value) or (
            key == "source_available_at" and value == _SOURCE_AVAILABILITY_TYPED_UNKNOWN
        ):
            projected[key] = value
        else:
            _record(omissions, f"lifecycle_malformed:{key}")
    observed = projected.get("observed_at")
    if isinstance(observed, str):
        projected["recorded_at"] = observed
    return projected


def project_event_workspace(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Project a production ``event_workspace.v1`` payload into the composer row.

    Returns a fresh dict with exactly the keys ``event_id``, ``cik``,
    ``fiscal_period``, ``guidance``, ``reported``, ``lifecycle``,
    ``omissions``; or ``None`` when the payload cannot be projected as a
    whole: not a mapping, no non-empty ``event_id`` string, no
    ``fiscal_period`` mapping, a quarter that is not an int in 1..4, or an
    ``issuer.company_id`` outside the closed CIK grammar. A year outside
    1000..9999 is emitted as ``None`` (its facts become ``reported_unkeyed``).
    Never raises.
    """
    if not isinstance(payload, Mapping):
        return None

    event_id = payload.get("event_id")
    if not isinstance(event_id, str) or not event_id:
        return None

    fiscal_period = payload.get("fiscal_period")
    if not isinstance(fiscal_period, Mapping):
        return None
    year = fiscal_period.get("year")
    quarter = fiscal_period.get("quarter")
    if not _is_quarter(quarter):
        return None

    issuer = payload.get("issuer")
    cik = _parse_cik(issuer.get("company_id")) if isinstance(issuer, Mapping) else None
    if cik is None:
        return None

    omissions: list[str] = []
    token = _fiscal_period_token(year, quarter)
    reported = _project_reported(payload.get("facts"), token, omissions)
    guidance = _project_guidance(payload.get("guidance"), omissions)
    lifecycle = _project_lifecycle(payload.get("lifecycle"), omissions)

    return {
        "event_id": event_id,
        "cik": cik,
        "fiscal_period": {"year": year if _is_year(year) else None, "quarter": quarter},
        "guidance": guidance,
        "reported": reported,
        "lifecycle": lifecycle,
        "omissions": omissions,
    }
