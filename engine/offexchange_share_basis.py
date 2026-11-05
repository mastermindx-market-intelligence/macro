from __future__ import annotations

__doc__ = """RESEARCH REFERENCE — NOT WIRED.

Off-exchange participation share-basis adapter (Q03, quant assessment 2026-10).

VERDICT (see research/quant_assessment_2026_10/Q03_offexchange_share_basis/VERDICT.md):
the verdict is recorded there and is not restated as a promotion here. Nothing in
the repository imports this module; it registers nothing, schedules nothing, gates
nothing and writes nothing. ``RESEARCH_ONLY`` is True by construction.

WHAT IT IS FOR
--------------
Off-exchange participation is FINRA off-exchange shares divided by consolidated
shares for the same session. FINRA reports shares exactly as traded on the day
(``RAW_AS_REPORTED``). A price vendor typically re-bases its volume history after
a split (``ADJUSTED_AS_OF`` some vintage position). Mixing the two makes every
pre-split session read participation divided by the split ratio, which the
incumbent ``engine.darkpool_signals.share_break_index`` detects and truncates.
This adapter instead converts BOTH sides to one share basis, but only with an
explicitly supplied, vintage-stamped factor record. It never estimates a factor
from the observed participation jump: an unknown or ambiguous action produces an
explicit noncomparability boundary, not a repaired number.

WHAT IT IS NOT
--------------
* Not a corporate-action owner. Factors come from a caller-supplied vintage.
* Not a direction signal. FINRA short volume is not short interest or net buying;
  ATS/non-ATS is a venue category, not owner intent; a corrected ratio is never
  institutional buying (DNR:HOLD-PSS-AF1-FINRA, DNR:HOLD-PSS-CD1-CROWDING).
* It never touches the frozen PSS-AF1 construction (short_vol / total_vol is a
  within-FINRA ratio and therefore basis-invariant; this module does not compute,
  accept or emit it).
* No in-place rewrite of any ledger: corrected reads are versioned, append-only
  values whose identity includes the factor vintage.

Positions are any totally ordered keys (integers in tests, timestamps in research
scripts). An action's ``effective`` key is the first session that trades on the
new share basis (the ex-date). ``ratio`` is new shares per old share: a 2:1 split
is 2.0, a 1:10 reverse split is 0.1.
"""

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

RESEARCH_ONLY = True
SCHEMA = "offexchange_share_basis.v1"
MAX_ROWS = 50_000          # bounded input: one name's daily history, generously
MAX_ACTIONS = 200          # bounded factor record per name

# ── action kinds ───────────────────────────────────────────────────────────────
FORWARD_SPLIT = "FORWARD_SPLIT"
REVERSE_SPLIT = "REVERSE_SPLIT"
NO_OP = "NO_OP"
AMBIGUOUS = "AMBIGUOUS"            # e.g. a spin-off adjustment recorded as a split
ACTION_KINDS = (FORWARD_SPLIT, REVERSE_SPLIT, NO_OP, AMBIGUOUS)

# ── volume conventions ─────────────────────────────────────────────────────────
RAW_AS_REPORTED = "RAW_AS_REPORTED"    # each row in the share units of its own session
ADJUSTED_AS_OF = "ADJUSTED_AS_OF"      # rows at/before as_of re-based to as_of units
UNKNOWN_CONVENTION = "UNKNOWN_CONVENTION"
CONVENTIONS = (RAW_AS_REPORTED, ADJUSTED_AS_OF, UNKNOWN_CONVENTION)

# ── row classes (denominator first, then basis) ────────────────────────────────
VALID = "VALID"
DENOM_MISSING = "DENOM_MISSING"
DENOM_NONFINITE = "DENOM_NONFINITE"
DENOM_NEGATIVE = "DENOM_NEGATIVE"
DENOM_ZERO = "DENOM_ZERO"
NUMERATOR_INVALID = "NUMERATOR_INVALID"
BASIS_INCOMPATIBLE = "BASIS_INCOMPATIBLE"
ROW_CLASSES = (VALID, DENOM_MISSING, DENOM_NONFINITE, DENOM_NEGATIVE, DENOM_ZERO,
               NUMERATOR_INVALID, BASIS_INCOMPATIBLE)

# ── factor attestation status for a name ───────────────────────────────────────
ATTESTED = "ATTESTED"          # the vintage covers this name (possibly: no actions)
UNATTESTED = "UNATTESTED"      # the vintage says nothing -> factor UNKNOWN, never inferred

_SIMPLE_INT_MAX = 1000
_SIMPLE_PQ_MAX = 20
_RATIO_REL_TOL = 1e-3


def classify_ratio(ratio: float) -> str:
    """Classify a share ratio WITHOUT reference to any participation data.

    A ratio counts as a clean split only when it (or its reciprocal) is an integer
    up to 1000, or a small fraction p/q with p, q <= 20. Anything else (1.253 from
    a spin-off adjustment, 0.602, 1.327, 1.04) is AMBIGUOUS: the vendor may or may
    not have re-based volume by it, so rows across it are not comparable.
    """
    r = float(ratio)
    if not math.isfinite(r) or r <= 0:
        return AMBIGUOUS
    if abs(r - 1.0) <= 1e-12:
        return NO_OP
    kind = FORWARD_SPLIT if r > 1 else REVERSE_SPLIT
    for x in (r, 1.0 / r):
        n = round(x)
        if 2 <= n <= _SIMPLE_INT_MAX and abs(x - n) / x <= _RATIO_REL_TOL:
            return kind
    for q in range(1, _SIMPLE_PQ_MAX + 1):
        p = round(r * q)
        if 1 <= p <= _SIMPLE_PQ_MAX and p != q and abs(r - p / q) / r <= _RATIO_REL_TOL:
            return kind
    return AMBIGUOUS


@dataclass(frozen=True)
class CorporateAction:
    effective: Any
    ratio: float
    note: str = ""

    @property
    def kind(self) -> str:
        return classify_ratio(self.ratio)


@dataclass(frozen=True)
class FactorVintage:
    """An immutable, identified factor record for ONE name.

    ``vintage_id`` names the source snapshot (e.g. a file sha256 plus fetch stamp).
    ``attested_through`` is the last position the snapshot can speak for: an action
    effective after it is unknown to this vintage. ``attested=False`` means the
    source has no entry for the name at all (factor UNKNOWN).
    """
    ticker: str
    vintage_id: str
    source: str
    actions: tuple[CorporateAction, ...] = ()
    attested: bool = True
    attested_through: Any = None

    def __post_init__(self) -> None:
        if len(self.actions) > MAX_ACTIONS:
            raise ValueError("too many actions for one name")
        keys = [a.effective for a in self.actions]
        if keys != sorted(keys):
            raise ValueError("actions must be sorted by effective position")
        if len(set(map(repr, keys))) != len(keys):
            raise ValueError("duplicate effective position in one vintage")

    def content_hash(self) -> str:
        payload = {
            "ticker": self.ticker,
            "vintage_id": self.vintage_id,
            "source": self.source,
            "attested": bool(self.attested),
            "attested_through": _key_repr(self.attested_through),
            "actions": [[_key_repr(a.effective), float(a.ratio)] for a in self.actions],
        }
        return _sha(payload)


@dataclass(frozen=True)
class BasisRead:
    """One versioned corrected read. Never mutated; superseded only by appending."""
    ticker: str
    schema: str
    result_id: str
    vintage_id: str
    vintage_hash: str
    numerator_convention: str
    denominator_convention: str
    denominator_as_of: Any
    attestation: str
    positions: tuple
    participation: tuple
    raw_participation: tuple
    row_class: tuple
    factor_applied: tuple
    segment: tuple
    level_status: str
    counts: dict = field(default_factory=dict)


# ── helpers ────────────────────────────────────────────────────────────────────

def _key_repr(k: Any) -> Any:
    if k is None:
        return None
    if isinstance(k, (int, float, str)):
        return k
    return str(k)


def _sha(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _num(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v):
        return None
    return v


def classify_denominator(x: Any) -> str:
    """Zero, missing, negative and non-finite denominators are distinct classes."""
    v = _num(x)
    if v is None:
        return DENOM_MISSING
    if not math.isfinite(v):
        return DENOM_NONFINITE
    if v < 0:
        return DENOM_NEGATIVE
    if v == 0:
        return DENOM_ZERO
    return VALID


def cumulative_factor(actions: Sequence[CorporateAction], start: Any, end: Any) -> float:
    """Shares on the ``end`` basis per share on the ``start`` basis.

    Product of ratios of actions with start < effective <= end. Raises if any
    action in that span is AMBIGUOUS — an ambiguous factor is never applied.
    """
    f = 1.0
    for a in actions:
        if start < a.effective <= end:
            if a.kind == AMBIGUOUS:
                raise ValueError("ambiguous action inside conversion span")
            f *= float(a.ratio)
    return f


def _segments(positions: Sequence[Any], actions: Sequence[CorporateAction],
              attested_through: Any) -> list[int]:
    """Comparability segment per row: a new segment starts at every AMBIGUOUS
    action and after the attestation horizon (unknown actions may follow it)."""
    cuts = sorted([a.effective for a in actions if a.kind == AMBIGUOUS],
                  key=lambda k: k)
    seg = []
    for p in positions:
        s = sum(1 for c in cuts if p >= c)
        if attested_through is not None and p > attested_through:
            s = len(cuts) + 1
        seg.append(s)
    return seg


def normalize_participation(
    ticker: str,
    positions: Sequence[Any],
    finra_total: Sequence[Any],
    vendor_volume: Sequence[Any],
    vintage: FactorVintage,
    *,
    denominator_convention: str,
    denominator_as_of: Any = None,
) -> BasisRead:
    """Put FINRA (RAW_AS_REPORTED) and vendor volume on ONE share basis.

    Under ADJUSTED_AS_OF(A) a vendor row at t <= A is in A's units, so FINRA row t
    is scaled by cumulative_factor(t, A). Under RAW_AS_REPORTED both sides are
    already in session-t units and no factor is applied. Under UNKNOWN_CONVENTION
    or an UNATTESTED vintage, any row separated from the last row by a known or
    possible action is BASIS_INCOMPATIBLE — no factor is guessed.

    Inputs are not mutated. Returns an immutable BasisRead whose ``result_id``
    binds the vintage hash, the conventions and the input digest.
    """
    n = len(positions)
    if n > MAX_ROWS:
        raise ValueError("input exceeds MAX_ROWS")
    if len(finra_total) != n or len(vendor_volume) != n:
        raise ValueError("positions, numerator and denominator lengths differ")
    if list(positions) != sorted(positions):
        raise ValueError("positions must be sorted")
    if denominator_convention not in CONVENTIONS:
        raise ValueError(f"unknown convention {denominator_convention!r}")
    if denominator_convention == ADJUSTED_AS_OF and denominator_as_of is None:
        raise ValueError("ADJUSTED_AS_OF requires denominator_as_of")
    if vintage.ticker != ticker:
        raise ValueError("vintage belongs to another ticker")

    actions = list(vintage.actions) if vintage.attested else []
    last = positions[-1] if n else None
    seg = _segments(positions, actions, vintage.attested_through) if n else []
    any_ambiguous = any(a.kind == AMBIGUOUS for a in actions)

    part: list[float | None] = []
    raw: list[float | None] = []
    cls: list[str] = []
    fac: list[float | None] = []
    for i in range(n):
        p = positions[i]
        num = _num(finra_total[i])
        dcls = classify_denominator(vendor_volume[i])
        den = _num(vendor_volume[i])
        raw_v = (num / den) if (dcls == VALID and num is not None
                                and math.isfinite(num) and num >= 0) else None
        raw.append(raw_v)
        if dcls != VALID:
            cls.append(dcls); part.append(None); fac.append(None); continue
        if num is None or not math.isfinite(num) or num < 0:
            cls.append(NUMERATOR_INVALID); part.append(None); fac.append(None); continue

        f: float | None
        if not vintage.attested:
            f = None                      # factor UNKNOWN: never inferred
        elif denominator_convention == RAW_AS_REPORTED:
            f = 1.0
        elif denominator_convention == ADJUSTED_AS_OF:
            end = denominator_as_of if p <= denominator_as_of else p
            try:
                f = cumulative_factor(actions, p, end)
            except ValueError:
                f = None
        else:  # UNKNOWN_CONVENTION: only rows with no known action ahead are safe
            ahead = [a for a in actions if p < a.effective <= last]
            f = 1.0 if not ahead else None

        if f is None:
            # unattested name, ambiguous span or unknown convention: the raw ratio
            # stays visible in raw_participation, but no same-basis value exists
            cls.append(BASIS_INCOMPATIBLE); part.append(None); fac.append(None)
            continue
        cls.append(VALID); fac.append(f); part.append(num * f / den)

    attestation = ATTESTED if vintage.attested else UNATTESTED
    beyond = (vintage.attested_through is not None and denominator_as_of is not None
              and denominator_as_of > vintage.attested_through)
    if attestation == UNATTESTED:
        level_status = "NONCOMPARABLE"
    elif any_ambiguous or beyond:
        level_status = "RELATIVE_WITHIN_SEGMENT"
    else:
        level_status = "ABSOLUTE"

    counts = {c: cls.count(c) for c in ROW_CLASSES}
    input_digest = _sha({
        "positions": [_key_repr(p) for p in positions],
        "num": [_num(x) for x in finra_total],
        "den": [_num(x) for x in vendor_volume],
    })
    vhash = vintage.content_hash()
    result_id = _sha({
        "schema": SCHEMA, "ticker": ticker, "vintage_hash": vhash,
        "num_conv": RAW_AS_REPORTED, "den_conv": denominator_convention,
        "den_as_of": _key_repr(denominator_as_of), "input": input_digest,
    })
    return BasisRead(
        ticker=ticker, schema=SCHEMA, result_id=result_id,
        vintage_id=vintage.vintage_id, vintage_hash=vhash,
        numerator_convention=RAW_AS_REPORTED,
        denominator_convention=denominator_convention,
        denominator_as_of=denominator_as_of, attestation=attestation,
        positions=tuple(positions), participation=tuple(part),
        raw_participation=tuple(raw), row_class=tuple(cls),
        factor_applied=tuple(fac), segment=tuple(seg),
        level_status=level_status, counts=counts,
    )


def append_read(ledger: tuple, read: BasisRead) -> tuple:
    """Append-only versioned ledger of corrected reads (a tuple, never mutated).

    A read with a new result_id is appended and every earlier vintage's read is
    preserved. Re-appending an identical read is idempotent; a different read under
    an existing result_id is refused (identity collision).
    """
    for r in ledger:
        if r.result_id == read.result_id:
            if r != read:
                raise ValueError("result_id collision with different content")
            return ledger
    return tuple(ledger) + (read,)


def reads_for(ledger: Iterable[BasisRead], ticker: str) -> list[BasisRead]:
    return [r for r in ledger if r.ticker == ticker]


def window_level_shift(values: Sequence[Any], split_at: int, *, pre: int, post: int,
                       min_valid: int) -> float | None:
    """median(log v, post window) - median(log v, pre window) around index split_at.

    Pre = the ``pre`` rows before split_at; post = ``post`` rows from split_at on.
    Returns None when either side has fewer than ``min_valid`` positive finite
    values. Pure descriptive helper: it never selects a factor.
    """
    if pre <= 0 or post <= 0 or min_valid <= 0:
        raise ValueError("windows must be positive")
    vals = list(values)
    if len(vals) > MAX_ROWS:
        raise ValueError("input exceeds MAX_ROWS")
    a = vals[max(0, split_at - pre):split_at]
    b = vals[split_at:split_at + post]

    def logs(xs):
        out = []
        for x in xs:
            v = _num(x)
            if v is not None and math.isfinite(v) and v > 0:
                out.append(math.log(v))
        return out

    la, lb = logs(a), logs(b)
    if len(la) < min_valid or len(lb) < min_valid:
        return None
    return _median(lb) - _median(la)


def _median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else 0.5 * (s[m - 1] + s[m])


def contract() -> dict:
    """The module's own activation contract, for the no-silent-activation test."""
    return {
        "research_only": RESEARCH_ONLY,
        "schema": SCHEMA,
        "registers": (),
        "writes": (),
        "emits_direction": False,
        "computes_short_ratio": False,
    }
