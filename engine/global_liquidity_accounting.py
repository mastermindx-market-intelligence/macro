"""Pure monetary accounting decomposition for the global-liquidity programme.

TIER AND CLAIM LEVEL
--------------------
This module is research/display-tier only: ``VALIDATED = False`` and
``CLAIM_LEVEL = "synthetic_arithmetic_identity"``. The identities implemented
here are exact algebra, verified on synthetic cases by
``tests/test_global_liquidity_accounting.py`` against the package oracle
``glt_fable_20261013/SYNTHETIC_ARITHMETIC.json``
(``evidence_type: SYNTHETIC_ARITHMETIC_ONLY_NOT_MARKET_RESULTS``). Nothing in
this module is a market measurement, an estimate of any real balance sheet, or
a validated economic result.

GOVERNED NAMES
--------------
* C05 -- liquidity-concept guard: amounts of different liquidity concepts are
  never pooled together (``sum_same_concept``).
* C07 -- constant-local-assets guard: when a local-currency stock is constant,
  a pure fx revaluation has exactly zero domestic term and zero interaction
  term; the entire USD change is fx translation (``FxDecomposition`` /
  ``decompose_fx_change``).
* C08 -- magnitude-type guard: ``RawMagnitude`` and ``StandardizedMagnitude``
  are distinct, non-substitutable types; a raw first difference and its
  prior-only expanding z-score may never be mixed or silently coerced
  (``MagnitudePair``, ``raw_magnitudes``, ``standardized_magnitudes``).

RELATIONSHIP TO THE INCUMBENT ENGINE
------------------------------------
The incumbent research engine ``engine/global_liquidity_transmission.py``
(v1) is untouched by this module and is NOT imported here. This module is
pure: standard library only, no I/O, no clock, no network, no third-party
numerics. It exists so display surfaces can show exact, reconcilable
arithmetic identities.

NUMBER CONTRACT
---------------
Accepted numbers: ``int``, ``float``, ``fractions.Fraction``,
``decimal.Decimal``. ``bool`` is refused with ``TypeError`` (a bool is not a
number here). "Null" means ``None``, or a ``float``/``Decimal`` that is NaN or
infinite. Null is NEVER converted to zero: it propagates and is reported by
name. ``Decimal`` and ``float`` must not be mixed inside one call; doing so
raises ``TypeError("mixed Decimal and float")``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Optional, Sequence, Tuple

__all__ = [
    "VALIDATED",
    "CLAIM_LEVEL",
    "DEFAULT_ABS_TOL",
    "DEFAULT_REL_TOL",
    "LIQUIDITY_CONCEPTS",
    "AccountingReconciliationError",
    "FxDecomposition",
    "RawMagnitude",
    "StandardizedMagnitude",
    "MagnitudePair",
    "ReserveIdentity",
    "IncompleteProxy",
    "ConceptAmount",
    "fx_rate_to_usd",
    "decompose_fx_change",
    "assert_reconciles",
    "raw_magnitudes",
    "standardized_magnitudes",
    "reserves_from_balance_sheet",
    "assert_reserve_identity",
    "reserve_change",
    "incomplete_net_liquidity_proxy",
    "sum_same_concept",
]

VALIDATED = False
CLAIM_LEVEL = "synthetic_arithmetic_identity"
DEFAULT_ABS_TOL = 1e-9
DEFAULT_REL_TOL = 1e-12

LIQUIDITY_CONCEPTS = (
    "central_bank_assets",
    "reserves",
    "broad_money",
    "private_credit",
    "funding_price",
    "market_liquidity",
)

_NUMBER_TYPES = (int, float, Fraction, Decimal)


class AccountingReconciliationError(AssertionError):
    """Raised when a stated identity does not hold under the tolerance law."""


# ---------------------------------------------------------------------------
# number helpers
# ---------------------------------------------------------------------------


def _is_null(value: object) -> bool:
    """True for None, NaN, or +/-infinity on float/Decimal inputs."""
    if value is None:
        return True
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, Decimal):
        return not value.is_finite()
    return False


def _reject_bool(name: str, value: object) -> None:
    if isinstance(value, bool):
        raise TypeError(f"{name} is a bool; bool is not a number here")


def _reject_mixed_decimal_float(**named: object) -> None:
    """Refuse a call that receives both Decimal and float inputs."""
    has_decimal = False
    has_float = False
    for value in named.values():
        if isinstance(value, bool):
            continue  # bool refusal is handled by _reject_bool
        if isinstance(value, Decimal):
            has_decimal = True
        elif isinstance(value, float):
            has_float = True
    if has_decimal and has_float:
        raise TypeError("mixed Decimal and float")


# ---------------------------------------------------------------------------
# 1) fx quote conversion
# ---------------------------------------------------------------------------


def fx_rate_to_usd(quote: Optional[object], *, invert: bool) -> Optional[object]:
    """Return USD per 1 unit of local currency from an fx quote.

    ``invert=False`` for quotes already quoted as USD per local unit (pass the
    quote through). ``invert=True`` for quotes like USDJPY (local units per
    USD): the result is ``1 / quote``.

    A null quote (``None``, NaN, infinite) or a non-positive quote yields
    ``None`` — a broken quote is never coerced to a usable number. Division is
    performed in the input's own type: ``int`` -> ``Fraction(1, quote)``,
    ``Fraction`` -> exact rational reciprocal, ``Decimal`` -> decimal
    division, ``float`` -> float reciprocal.
    """
    _reject_bool("quote", quote)
    if _is_null(quote):
        return None
    if quote <= 0:
        return None
    if not invert:
        return quote
    if isinstance(quote, int):
        return Fraction(1, quote)
    return 1 / quote


# ---------------------------------------------------------------------------
# 2) fx decomposition  V = q * L
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FxDecomposition:
    """Exact additive decomposition of a USD-value change ``d(q*L)``.

    ``usd_change = domestic_at_prior_fx + fx_translation + interaction`` where
    ``domestic_at_prior_fx = q_prev * dL``, ``fx_translation = L_prev * dq``
    and ``interaction = dL * dq`` (C07: with ``dL == 0`` both the domestic
    term and the interaction term are exactly zero).
    """

    local_prev: Optional[object]
    local_curr: Optional[object]
    usd_per_local_prev: Optional[object]
    usd_per_local_curr: Optional[object]
    usd_prev: Optional[object]
    usd_curr: Optional[object]
    usd_change: Optional[object]
    domestic_at_prior_fx: Optional[object]
    fx_translation: Optional[object]
    interaction: Optional[object]
    null_reason: Optional[str]
    concept: str = "central_bank_assets"

    def __post_init__(self) -> None:
        if self.concept not in LIQUIDITY_CONCEPTS:
            raise ValueError(
                f"unknown liquidity concept {self.concept!r}; expected one of {LIQUIDITY_CONCEPTS}"
            )

    def parts_sum(self) -> Optional[object]:
        """domestic + fx + interaction; ``None`` when any part is null."""
        if (
            self.domestic_at_prior_fx is None
            or self.fx_translation is None
            or self.interaction is None
        ):
            return None
        return (
            self.domestic_at_prior_fx + self.fx_translation + self.interaction
        )

    @property
    def is_null(self) -> bool:
        return self.null_reason is not None


def _null_decomposition(
    local_prev: object,
    local_curr: object,
    usd_per_local_prev: object,
    usd_per_local_curr: object,
    null_reason: str,
    concept: str,
) -> FxDecomposition:
    return FxDecomposition(
        local_prev=local_prev,
        local_curr=local_curr,
        usd_per_local_prev=usd_per_local_prev,
        usd_per_local_curr=usd_per_local_curr,
        usd_prev=None,
        usd_curr=None,
        usd_change=None,
        domestic_at_prior_fx=None,
        fx_translation=None,
        interaction=None,
        null_reason=null_reason,
        concept=concept,
    )


def decompose_fx_change(
    local_prev: object,
    local_curr: object,
    usd_per_local_prev: object,
    usd_per_local_curr: object,
    *,
    concept: str = "central_bank_assets",
) -> FxDecomposition:
    """Decompose the change in USD value ``V = q * L`` into three exact parts.

    If any input is null, every computed field is ``None`` and
    ``null_reason`` names every null input (nulls are never zeroed). If an fx
    input is non-positive the decomposition is null with reason
    ``"non-positive fx: <name>"``. Otherwise the three parts are computed
    exactly in the input's own numeric type (``Fraction``/``Decimal`` inputs
    stay exact; C07 holds identically: constant local assets give exactly zero
    domestic and interaction terms).
    """
    _reject_bool("local_prev", local_prev)
    _reject_bool("local_curr", local_curr)
    _reject_bool("usd_per_local_prev", usd_per_local_prev)
    _reject_bool("usd_per_local_curr", usd_per_local_curr)
    _reject_mixed_decimal_float(
        local_prev=local_prev,
        local_curr=local_curr,
        usd_per_local_prev=usd_per_local_prev,
        usd_per_local_curr=usd_per_local_curr,
    )

    nulls = [
        name
        for name, value in (
            ("local_prev", local_prev),
            ("local_curr", local_curr),
            ("usd_per_local_prev", usd_per_local_prev),
            ("usd_per_local_curr", usd_per_local_curr),
        )
        if _is_null(value)
    ]
    if nulls:
        return _null_decomposition(
            local_prev,
            local_curr,
            usd_per_local_prev,
            usd_per_local_curr,
            "null input: " + ", ".join(nulls),
            concept,
        )

    non_positive_fx = [
        name
        for name, value in (
            ("usd_per_local_prev", usd_per_local_prev),
            ("usd_per_local_curr", usd_per_local_curr),
        )
        if value <= 0
    ]
    if non_positive_fx:
        return _null_decomposition(
            local_prev,
            local_curr,
            usd_per_local_prev,
            usd_per_local_curr,
            "non-positive fx: " + ", ".join(non_positive_fx),
            concept,
        )

    usd_prev = usd_per_local_prev * local_prev
    usd_curr = usd_per_local_curr * local_curr
    d_local = local_curr - local_prev
    d_quote = usd_per_local_curr - usd_per_local_prev
    domestic = usd_per_local_prev * d_local
    fx_translation = local_prev * d_quote
    interaction = d_local * d_quote
    usd_change = usd_curr - usd_prev
    non_finite = [
        name
        for name, value in (
            ("usd_prev", usd_prev),
            ("usd_curr", usd_curr),
            ("usd_change", usd_change),
            ("domestic_at_prior_fx", domestic),
            ("fx_translation", fx_translation),
            ("interaction", interaction),
        )
        if _is_null(value)
    ]
    if non_finite:
        # Finite inputs can still overflow a float product to inf (and inf - inf
        # to NaN). That is not a decomposition: null with a reason, never a
        # garbage value that a NaN comparison would let "reconcile".
        return _null_decomposition(
            local_prev,
            local_curr,
            usd_per_local_prev,
            usd_per_local_curr,
            "non-finite result (overflow): " + ", ".join(non_finite),
            concept,
        )
    return FxDecomposition(
        local_prev=local_prev,
        local_curr=local_curr,
        usd_per_local_prev=usd_per_local_prev,
        usd_per_local_curr=usd_per_local_curr,
        usd_prev=usd_prev,
        usd_curr=usd_curr,
        usd_change=usd_change,
        domestic_at_prior_fx=domestic,
        fx_translation=fx_translation,
        interaction=interaction,
        null_reason=None,
        concept=concept,
    )


# ---------------------------------------------------------------------------
# 3) tolerance law
# ---------------------------------------------------------------------------


def assert_reconciles(
    decomp: FxDecomposition,
    *,
    abs_tol: float = DEFAULT_ABS_TOL,
    rel_tol: float = DEFAULT_REL_TOL,
) -> None:
    """Assert the stated fx decomposition tolerance law.

    Stated tolerance law: fail iff ``float(abs(residual)) > abs_tol +
    rel_tol * float(scale)`` where ``residual = parts_sum - usd_change`` AND
    separately ``residual2 = usd_change - (usd_curr - usd_prev)``,
    ``scale = max(abs(usd_prev), abs(usd_curr), abs(domestic),
    abs(fx), abs(interaction), 1)``.

    A null decomposition raises ``ValueError``: absence of data is never
    treated as "reconciled".

    Fail-closed clauses (B4 review): when both residuals are exactly zero in
    the input type the law holds without any float conversion (so an exact
    ``int``/``Fraction`` decomposition too large for a float still
    reconciles); otherwise a residual or scale that is not a finite float
    (overflow, NaN, or not representable) raises
    ``AccountingReconciliationError`` -- a NaN comparison is never allowed to
    read as "within tolerance".
    """
    if decomp.is_null:
        raise ValueError(
            f"cannot reconcile a null decomposition: {decomp.null_reason}"
        )
    parts_sum = decomp.parts_sum()
    computed_fields = (
        decomp.usd_prev,
        decomp.usd_curr,
        decomp.usd_change,
        decomp.domestic_at_prior_fx,
        decomp.fx_translation,
        decomp.interaction,
    )
    if parts_sum is None or any(field is None for field in computed_fields):
        raise ValueError(
            "cannot reconcile: computed fields are missing but null_reason is None"
        )
    residual_exact = parts_sum - decomp.usd_change
    residual2_exact = decomp.usd_change - (decomp.usd_curr - decomp.usd_prev)
    if residual_exact == 0 and residual2_exact == 0:
        return
    try:
        scale = max(
            abs(float(decomp.usd_prev)),
            abs(float(decomp.usd_curr)),
            abs(float(decomp.domestic_at_prior_fx)),
            abs(float(decomp.fx_translation)),
            abs(float(decomp.interaction)),
            1.0,
        )
        residual = float(residual_exact)
        residual2 = float(residual2_exact)
    except OverflowError as exc:
        raise AccountingReconciliationError(
            f"fx decomposition for concept {decomp.concept!r} is not representable "
            f"as a finite float and does not reconcile exactly: {exc}"
        ) from None
    limit = abs_tol + rel_tol * scale
    if not (
        math.isfinite(scale)
        and math.isfinite(limit)
        and math.isfinite(residual)
        and math.isfinite(residual2)
    ):
        raise AccountingReconciliationError(
            f"fx decomposition for concept {decomp.concept!r} has a non-finite "
            f"residual or scale (residual={residual!r}, residual2={residual2!r}, "
            f"scale={scale!r}); fail closed"
        )
    if abs(residual) > limit:
        raise AccountingReconciliationError(
            f"fx decomposition does not reconcile for concept {decomp.concept!r}: "
            f"residual parts_sum - usd_change = {residual!r} exceeds tolerance {limit!r}"
        )
    if abs(residual2) > limit:
        raise AccountingReconciliationError(
            f"fx decomposition does not reconcile for concept {decomp.concept!r}: "
            f"residual2 usd_change - (usd_curr - usd_prev) = {residual2!r} "
            f"exceeds tolerance {limit!r}"
        )


# ---------------------------------------------------------------------------
# 4) C08 magnitudes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RawMagnitude:
    """Raw first difference in source units (C08). No arithmetic operators."""

    value: Optional[object]
    unit: str

    def __post_init__(self) -> None:
        _reject_bool("value", self.value)


@dataclass(frozen=True)
class StandardizedMagnitude:
    """Prior-only expanding z-score of a raw magnitude (C08).

    ``value`` is a float or None; ``unit`` records the standardization;
    ``method`` names the estimator; ``min_periods`` is the minimum number of
    strictly-prior observations required. No arithmetic operators.
    """

    value: Optional[float]
    unit: str
    min_periods: int
    method: str = "prior_only_expanding_z"


@dataclass(frozen=True)
class MagnitudePair:
    """A raw magnitude together with its standardized counterpart (C08).

    The two types are not substitutable: ``__post_init__`` refuses anything
    that is not exactly a ``RawMagnitude`` paired with exactly a
    ``StandardizedMagnitude``.
    """

    magnitude: RawMagnitude
    magnitude_z: StandardizedMagnitude

    def __post_init__(self) -> None:
        if (
            type(self.magnitude) is not RawMagnitude
            or type(self.magnitude_z) is not StandardizedMagnitude
        ):
            raise TypeError(
                "magnitude and magnitude_z are not substitutable (C08)"
            )


def raw_magnitudes(
    levels: Sequence[object], *, unit: str
) -> Tuple[RawMagnitude, ...]:
    """First differences of ``levels`` in source units.

    Element 0 is ``RawMagnitude(None, unit)``; any null on either side of a
    difference yields ``None`` (never zero). Magnitude objects in ``levels``
    are refused with ``TypeError`` — this function consumes raw level numbers,
    not magnitudes.
    """
    _reject_mixed_decimal_float(**{f"level_{i}": lv for i, lv in enumerate(levels)})
    for position, level in enumerate(levels):
        if isinstance(level, (RawMagnitude, StandardizedMagnitude)):
            raise TypeError(
                f"levels[{position}] is a {type(level).__name__}, not a raw level "
                "number; raw_magnitudes consumes level numbers only (C08)"
            )
        _reject_bool(f"levels[{position}]", level)
    result = []
    previous = None
    for position, level in enumerate(levels):
        if position == 0:
            result.append(RawMagnitude(None, unit))
        elif _is_null(level) or _is_null(previous):
            result.append(RawMagnitude(None, unit))
        else:
            result.append(RawMagnitude(level - previous, unit))
        previous = level
    return tuple(result)


def standardized_magnitudes(
    raws: Sequence[object], *, min_periods: int
) -> Tuple[StandardizedMagnitude, ...]:
    """Prior-only expanding z-scores of raw magnitudes (prefix-causal).

    For position ``t`` only the non-null raw values at positions strictly
    before ``t`` are used. If the raw at ``t`` is null, or fewer than
    ``min_periods`` prior non-null values exist, or the prior sample standard
    deviation (ddof=1) is zero, the value is ``None``. Otherwise
    ``value = float((x_t - mean) / std)``. A raw whose float conversion is
    not finite (or overflows) is treated as null and never enters the prior
    sample, and a non-finite z is ``None``, never NaN. The result is
    prefix-causal by
    construction: the result over ``raws[:k]`` equals the first ``k`` results
    over the full sequence.

    Every element of ``raws`` must be exactly a ``RawMagnitude`` (a
    ``StandardizedMagnitude`` or a plain number is refused with
    ``TypeError``); all raws must share one unit (``ValueError`` otherwise).
    """
    if min_periods < 1:
        raise ValueError(f"min_periods must be >= 1, got {min_periods}")
    units = set()
    for position, raw in enumerate(raws):
        if type(raw) is not RawMagnitude:
            raise TypeError(
                f"raws[{position}] is a {type(raw).__name__}; every element must be "
                "exactly a RawMagnitude (C08)"
            )
        units.add(raw.unit)
    if len(units) > 1:
        raise ValueError(
            f"raw magnitudes must share one unit, got {sorted(units)}"
        )
    unit = "prior_only_expanding_z_of_" + (units.pop() if units else "")

    prior_values = []
    result = []
    for raw in raws:
        value: Optional[float] = None
        x: Optional[float] = None
        if not _is_null(raw.value):
            try:
                x = float(raw.value)
            except OverflowError:
                x = None
            if x is not None and not math.isfinite(x):
                x = None
        if x is not None:
            if len(prior_values) >= min_periods and len(prior_values) >= 2:
                count = len(prior_values)
                mean = sum(prior_values) / count
                try:
                    variance = sum(
                        (candidate - mean) ** 2 for candidate in prior_values
                    ) / (count - 1)
                    std = math.sqrt(variance)
                except OverflowError:
                    # Finite priors whose squared deviations exceed float range
                    # (float ``**`` raises where ``+`` overflows to inf): the
                    # z is not computable, so it is null -- never a crash.
                    std = math.inf
                if std != 0.0 and math.isfinite(std):
                    z = float((x - mean) / std)
                    value = z if math.isfinite(z) else None
            prior_values.append(x)
        result.append(
            StandardizedMagnitude(value, unit, min_periods=min_periods)
        )
    return tuple(result)


# ---------------------------------------------------------------------------
# 5) US reserves identity  R = A - N
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReserveIdentity:
    """The US reserves identity ``R = A - N`` on synthetic/display inputs."""

    assets: Optional[object]
    treasury_cash: Optional[object]
    reverse_repo: Optional[object]
    other_nonreserve_liabilities_and_capital: Optional[object]
    reserves: Optional[object]
    missing: Tuple[str, ...]
    null_reason: Optional[str]


def reserves_from_balance_sheet(
    *,
    assets: object,
    treasury_cash: object,
    reverse_repo: object,
    other_nonreserve_liabilities_and_capital: object,
) -> ReserveIdentity:
    """Compute reserves ``R = A - (TGA + RRP + other N)`` from the components.

    Any null component leaves ``reserves`` ``None`` and lists EVERY null
    component name, in signature order, in ``missing`` and ``null_reason`` —
    a missing component is never treated as zero.
    """
    names = (
        ("assets", assets),
        ("treasury_cash", treasury_cash),
        ("reverse_repo", reverse_repo),
        (
            "other_nonreserve_liabilities_and_capital",
            other_nonreserve_liabilities_and_capital,
        ),
    )
    _reject_bool("assets", assets)
    _reject_bool("treasury_cash", treasury_cash)
    _reject_bool("reverse_repo", reverse_repo)
    _reject_bool(
        "other_nonreserve_liabilities_and_capital",
        other_nonreserve_liabilities_and_capital,
    )
    _reject_mixed_decimal_float(**dict(names))

    missing = tuple(name for name, value in names if _is_null(value))
    if missing:
        return ReserveIdentity(
            assets=assets,
            treasury_cash=treasury_cash,
            reverse_repo=reverse_repo,
            other_nonreserve_liabilities_and_capital=(
                other_nonreserve_liabilities_and_capital
            ),
            reserves=None,
            missing=missing,
            null_reason="missing component(s): " + ", ".join(missing),
        )
    reserves = (
        assets
        - treasury_cash
        - reverse_repo
        - other_nonreserve_liabilities_and_capital
    )
    return ReserveIdentity(
        assets=assets,
        treasury_cash=treasury_cash,
        reverse_repo=reverse_repo,
        other_nonreserve_liabilities_and_capital=(
            other_nonreserve_liabilities_and_capital
        ),
        reserves=reserves,
        missing=(),
        null_reason=None,
    )


def assert_reserve_identity(
    ri: ReserveIdentity,
    *,
    abs_tol: float = DEFAULT_ABS_TOL,
    rel_tol: float = DEFAULT_REL_TOL,
) -> None:
    """Assert ``reserves + treasury_cash + reverse_repo + other == assets``.

    Same tolerance law as :func:`assert_reconciles` with
    ``scale = max(abs of all five quantities, 1)``. A null identity raises
    ``ValueError`` — absence is never "reconciled".
    """
    quantities = (
        ri.reserves,
        ri.treasury_cash,
        ri.reverse_repo,
        ri.other_nonreserve_liabilities_and_capital,
        ri.assets,
    )
    if any(_is_null(quantity) for quantity in quantities):
        missing = tuple(
            name
            for name, value in (
                ("reserves", ri.reserves),
                ("treasury_cash", ri.treasury_cash),
                ("reverse_repo", ri.reverse_repo),
                (
                    "other_nonreserve_liabilities_and_capital",
                    ri.other_nonreserve_liabilities_and_capital,
                ),
                ("assets", ri.assets),
            )
            if _is_null(value)
        )
        raise ValueError(
            "cannot reconcile a null reserve identity: missing component(s): "
            + ", ".join(missing)
        )
    scale = max(
        max(abs(float(quantity)) for quantity in quantities),
        1.0,
    )
    limit = abs_tol + rel_tol * scale
    residual = float(
        (ri.reserves + ri.treasury_cash + ri.reverse_repo + ri.other_nonreserve_liabilities_and_capital)
        - ri.assets
    )
    if abs(residual) > limit:
        raise AccountingReconciliationError(
            f"reserve identity does not reconcile: residual = {residual!r} "
            f"exceeds tolerance {limit!r}"
        )


def reserve_change(prev: ReserveIdentity, curr: ReserveIdentity) -> Optional[object]:
    """``curr.reserves - prev.reserves``; ``None`` when either side is null.

    Null means ``None``, NaN or infinite (``_is_null``), and a non-finite
    difference is ``None`` too -- never NaN.
    """
    if _is_null(prev.reserves) or _is_null(curr.reserves):
        return None
    change = curr.reserves - prev.reserves
    return None if _is_null(change) else change


@dataclass(frozen=True)
class IncompleteProxy:
    """An incomplete net-liquidity proxy ``A - TGA - RRP``.

    This is NOT reserves: it omits other non-reserve liabilities and capital,
    so its sign can disagree with the true reserves change. Display-tier only.
    """

    value: Optional[object]
    concept: str = "assets_minus_tga_minus_rrp_incomplete_proxy"
    null_reason: Optional[str] = None


def incomplete_net_liquidity_proxy(
    *, assets: object, treasury_cash: object, reverse_repo: object
) -> IncompleteProxy:
    """Compute ``A - TGA - RRP``; null components propagate, never zeroed.

    The result is NOT reserves — it omits other non-reserve liabilities and
    capital, and its sign can disagree with reserves (see the oracle case
    where reserves fall while this proxy rises).
    """
    _reject_bool("assets", assets)
    _reject_bool("treasury_cash", treasury_cash)
    _reject_bool("reverse_repo", reverse_repo)
    _reject_mixed_decimal_float(
        assets=assets, treasury_cash=treasury_cash, reverse_repo=reverse_repo
    )
    missing = [
        name
        for name, value in (
            ("assets", assets),
            ("treasury_cash", treasury_cash),
            ("reverse_repo", reverse_repo),
        )
        if _is_null(value)
    ]
    if missing:
        return IncompleteProxy(
            value=None,
            null_reason="missing component(s): " + ", ".join(missing),
        )
    return IncompleteProxy(value=assets - treasury_cash - reverse_repo)


# ---------------------------------------------------------------------------
# 6) C05 concept guard
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConceptAmount:
    """An amount tied to one liquidity concept and unit (C05)."""

    concept: str
    value: Optional[object]
    unit: str

    def __post_init__(self) -> None:
        if self.concept not in LIQUIDITY_CONCEPTS:
            raise ValueError(
                f"unknown liquidity concept {self.concept!r}; expected one of {LIQUIDITY_CONCEPTS}"
            )
        _reject_bool("value", self.value)


def sum_same_concept(amounts: Sequence[ConceptAmount]) -> ConceptAmount:
    """Sum amounts of ONE liquidity concept in ONE unit (C05).

    Empty input, mixed concepts, or mixed units raise ``ValueError``. Any null
    value makes the result value ``None`` — nulls are never treated as zero.
    """
    if not amounts:
        raise ValueError("sum_same_concept requires at least one ConceptAmount")
    concept = amounts[0].concept
    unit = amounts[0].unit
    for amount in amounts:
        if amount.concept != concept:
            raise ValueError(
                "refusing to pool different liquidity concepts (C05): "
                f"{concept!r} vs {amount.concept!r}"
            )
        if amount.unit != unit:
            raise ValueError(
                f"refusing to sum mixed units for concept {concept!r}: "
                f"{unit!r} vs {amount.unit!r}"
            )
    _reject_mixed_decimal_float(
        **{f"value_{i}": amount.value for i, amount in enumerate(amounts)}
    )
    if any(_is_null(amount.value) for amount in amounts):
        return ConceptAmount(concept=concept, value=None, unit=unit)
    total = amounts[0].value
    for amount in amounts[1:]:
        total = total + amount.value
    return ConceptAmount(concept=concept, value=total, unit=unit)
