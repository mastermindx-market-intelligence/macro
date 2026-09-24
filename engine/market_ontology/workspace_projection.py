"""``workspace_projection`` — bridge production ``event_workspace.v1`` payloads
into the composer row shape ``_build_economics`` consumes.

Operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001 (carrier
PR #7870), T08b. The composer's :func:`semiconductor_theme_research._build_economics`
keys on rows shaped like the synthetic witness fixture
(``tests/fixtures/semiconductor_theme_research/witness_hbm_packaging.json`` —
``event_id``, ``cik``/``company_node_id``, ``fiscal_period{year,quarter}``,
``guidance`` of ``guidance_item.v1`` items, ``reported`` rows with a closed
``fiscal_period`` ``"YYYYQn"`` token). Production intake
(:mod:`scripts.refresh_event_workspaces` +
:mod:`engine.company_intelligence.event_workspace_build`) emits a different
shape: ``facts`` of ``event_fact.v1`` with an ISO ``period`` end and an
optional ``typed_absence`` envelope, ``guidance`` of the same v1 items, an
``issuer`` block (``company_id`` carries the canonical ``cik:0000000000``),
a ``fiscal_period`` block that ALSO carries ``calendar_end``, ``sources``,
etc. Without this bridge, the composer silently emits
``economics.unavailable / management_sequence_missing`` even when a perfectly
admitted real workspace reaches the bundle.

This module is PURE — no I/O, no network, no imports beyond typing/re/collections
and the two engine modules named above. It is also NON-AUTHORING: every emitted
value is either an echo of an input the caller passed in or a fiat
classification over those inputs (CIK substring extraction, integer coercion of
``quarter``, numeric coercion of ``value``, ``(metric, basis)`` collision
detection). No arithmetic, no unit conversion, no derived midpoint, no
ranking, no sizing, no authority assertion.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Mapping

# Only the two engine modules explicitly named by the lane law.  ``re`` is a
# stdlib regex helper, ``Counter`` is a dict-derivative tally helper, and the
# rest are typing constructs.  No third-party imports; no I/O; no clock.
__all__ = ["project_event_workspace"]

# A 10-digit CIK string. ``cik:0001046179`` and ``cik0001046179`` both reduce
# to ``0001046179``; a bare ``1046179`` is zero-padded on output but the
# pattern itself accepts any 1..10-digit run that is not preceded by another
# digit (so "cik0001046179" matches the trailing ten, not a partial digit).
_CIK_DIGITS_RE = re.compile(r"(?<!\d)(\d{1,10})(?!\d)")

# Closed metric-bases the composer keys on.  Anything else is passed through
# verbatim and the composer decides what to do with it.
_REPORTED_OPTIONAL_KEYS = ("basis", "currency", "perimeter", "definition")

# Lifecycle keys the composer copies verbatim when present.  Each is copied
# independently — a missing key is dropped, never coerced to ``None``.
_LIFECYCLE_KEYS = ("source_available_at", "observed_at", "recorded_at")


def _parse_cik(raw: Any) -> str | None:
    """Extract the first 10-digit-padded CIK from a payload's ``issuer.company_id``.

    Accepts:
      * ``"cik:0001046179"``     → ``"0001046179"``
      * ``"cik0001046179"``      → ``"0001046179"``
      * ``"0001046179"``         → ``"0001046179"``
      * ``"1046179"``            → ``"0001046179"`` (zero-padded)
      * ``"0001046179  abcd"``   → ``"0001046179"`` (first run wins)

    Anything else (``None``, a non-string, a string with no digits) returns
    ``None`` — the composer keys on ``cik`` when ``company_node_id`` is absent.
    """
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    if text.lower().startswith("cik:"):
        text = text[4:]
    match = _CIK_DIGITS_RE.search(text)
    if match is None:
        return None
    digits = match.group(1)
    if not (1 <= len(digits) <= 10):
        return None
    return digits.zfill(10)


def _coerce_year(value: Any) -> int | None:
    """Accept an int year or a numeric string.  ``None``/anything else → ``None``."""
    if isinstance(value, bool):
        return None  # bool is an int subclass; refuse the promotion
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _coerce_quarter(value: Any) -> int | None:
    """Accept an int 1..4 or a numeric string.  Anything else → ``None``."""
    coerced = _coerce_year(value)
    if coerced is None:
        return None
    if coerced < 1 or coerced > 4:
        return None
    return coerced


def _coerce_numeric(value: Any) -> Any:
    """Accept a real numeric (``int``, ``float``, or numeric string).  Else pass through."""
    if isinstance(value, bool):
        # bool subclasses int; refuse the silent promotion to "0" / "1"
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            if any(ch in text for ch in ".eE"):
                return float(text)
            return int(text)
        except ValueError:
            return None
    return None


def _is_present_fact(fact: Mapping[str, Any]) -> bool:
    """A fact counts as ``present`` only when it has a numeric ``value`` and no
    ``typed_absence`` envelope.  ``typed_absence`` rows contribute nothing to
    the projection — their absence is already typed on the workspace."""
    if not isinstance(fact, Mapping):
        return False
    if "typed_absence" in fact:
        return False
    return _coerce_numeric(fact.get("value")) is not None


def _fiscal_period_token(year: Any, quarter: Any) -> str | None:
    """The closed ``"YYYYQn"`` token the composer's ``_fiscal_key`` parses.

    Never synthesized from a fact's ISO ``period`` — only from the WORKSPACE
    block's ``fiscal_period`` (year, quarter)."""
    coerced_year = _coerce_year(year)
    coerced_quarter = _coerce_quarter(quarter)
    if coerced_year is None or coerced_quarter is None:
        return None
    return f"{coerced_year}Q{coerced_quarter}"


def _project_reported(
    facts: Any, year: Any, quarter: Any, omissions: list[str],
) -> list[dict[str, Any]]:
    """Map ``event_fact.v1`` payloads → composer ``reported`` rows.

    Rules enforced here:
      * only PRESENT facts (numeric ``value``, no ``typed_absence``) survive;
      * the row's ``fiscal_period`` is the workspace's closed ``"YYYYQn"`` —
        never parsed from the fact's ISO ``period``;
      * ``basis``/``currency``/``perimeter``/``definition`` are copied verbatim
        WHEN PRESENT, never invented;
      * ``provenance``/``source_span`` are NEVER copied into ``reported``
        (the composer keys on closed tokens, not on the prose receipt);
      * two present facts sharing ``(metric, basis)`` is ambiguous: NEITHER
        row is emitted and the omission is recorded under
        ``"reported_ambiguous:<metric>"`` (collisions on different bases do
        NOT collide and both rows survive).
    """
    if not isinstance(facts, list) and not isinstance(facts, tuple):
        return []
    token = _fiscal_period_token(year, quarter)
    if token is None:
        # Workspace's own (year, quarter) failed validation; nothing to anchor
        # the rows to.  Absent facts stay absent; no provenance to leak.
        return []

    # Group present facts by (metric, basis) for collision detection.  A
    # fact without ``basis`` collides with itself and with every other
    # ``(metric, None)`` — the closed grammar states basis; an absent basis is
    # a distinct collision key by fiat.
    groups: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
    for fact in facts:
        if not _is_present_fact(fact):
            continue
        metric = fact.get("metric")
        if not isinstance(metric, str) or not metric:
            continue
        basis = fact.get("basis") if "basis" in fact else None
        groups.setdefault((metric, basis), []).append(fact)

    rows: list[dict[str, Any]] = []
    for (metric, basis), members in groups.items():
        if len(members) > 1:
            omissions.append(f"reported_ambiguous:{metric}")
            continue
        fact = members[0]
        row: dict[str, Any] = {
            "metric": metric,
            "value": _coerce_numeric(fact.get("value")),
            "unit": fact.get("unit"),
            "fiscal_period": token,
        }
        for optional in _REPORTED_OPTIONAL_KEYS:
            if optional in fact:
                row[optional] = fact[optional]
        rows.append(row)
    # Determinism: same input order, no ranking.
    rows.sort(key=lambda r: (str(r.get("metric") or ""), str(r.get("basis") or "")))
    return rows


def _project_guidance(raw: Any) -> list[Any]:
    """Copy ``guidance_item.v1`` items verbatim.  A non-list passes through empty."""
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, tuple):
        return list(raw)
    return []


def _project_lifecycle(raw: Any) -> dict[str, Any]:
    """Copy each lifecycle key verbatim WHEN PRESENT.  Missing keys are dropped,
    never coerced to ``None``.  An absent lifecycle yields ``{}``."""
    if not isinstance(raw, Mapping):
        return {}
    projected: dict[str, Any] = {}
    for key in _LIFECYCLE_KEYS:
        if key in raw:
            projected[key] = raw[key]
    return projected


def project_event_workspace(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Project a production ``event_workspace.v1`` payload into the composer row.

    The composer keys on the witness-fixture shape — ``event_id``,
    ``cik``/``company_node_id``, ``fiscal_period{year,quarter}``,
    ``guidance`` (``guidance_item.v1``), ``reported`` rows whose
    ``fiscal_period`` is a closed ``"YYYYQn"``, and a lifecycle triple.  This
    function is the pure bridge; it never raises, never invents tokens, and
    never parses a fiscal period out of a date.

    Returns the projected row (a fresh dict) on success.  Returns ``None`` when
    the payload cannot safely be projected — i.e. it is not a mapping, or it
    is missing the minimum scaffolding (``event_id``, ``fiscal_period`` with
    a coercible int quarter).  Malformed nested fields degrade the row but
    never raise: a fact with a non-numeric value contributes nothing; a CIK
    we cannot parse yields ``cik: None`` (the composer keys on ``cik`` when
    ``company_node_id`` is absent); a missing lifecycle key is dropped.
    """
    if not isinstance(payload, Mapping):
        return None

    event_id = payload.get("event_id")
    if not isinstance(event_id, str) or not event_id:
        return None

    fiscal_period = payload.get("fiscal_period")
    if not isinstance(fiscal_period, Mapping):
        return None
    year_value = fiscal_period.get("year")
    quarter_value = fiscal_period.get("quarter")
    coerced_year = _coerce_year(year_value)
    coerced_quarter = _coerce_quarter(quarter_value)
    if coerced_quarter is None:
        # The composer refuses a non-int quarter; the same gate applies here.
        return None

    issuer = payload.get("issuer")
    company_id = None
    if isinstance(issuer, Mapping):
        company_id = issuer.get("company_id")
    cik = _parse_cik(company_id)

    omissions: list[str] = []
    reported = _project_reported(
        payload.get("facts"), coerced_year, coerced_quarter, omissions,
    )
    guidance = _project_guidance(payload.get("guidance"))
    lifecycle = _project_lifecycle(payload.get("lifecycle"))

    row: dict[str, Any] = {
        "event_id": event_id,
        "cik": cik,
        "fiscal_period": {"year": coerced_year, "quarter": coerced_quarter},
        "guidance": guidance,
        "reported": reported,
        "lifecycle": lifecycle,
        "omissions": omissions,
    }
    # ``company_node_id`` is deliberately omitted — the composer keys on
    # ``cik`` when ``company_node_id`` is absent, and a payload's
    # ``issuer.company_id`` is a CIK-shaped string ("cik:0001046179"), not the
    # company_node_id the bundle's identity_results learn.
    return row