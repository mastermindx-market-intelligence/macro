from __future__ import annotations

# A ``from __future__`` import must precede everything, so the module docstring
# is bound explicitly to ``__doc__``.
__doc__ = """RESEARCH REFERENCE — NOT WIRED.

Q05 — option outcome sensitivity to latency, available size and execution cost.

Verdict (research/quant_assessment_2026_10/Q05_option_execution_sensitivity/VERDICT.md):
INSUFFICIENT_DATA. No retained local record carries a complete OA-3
(``oa3.long_single_leg_h60_nbbo/v1``) exact-contract outcome together with the
raw OPRA NBBO tick path (bid/ask, bid/ask size, condition, exchange) over the
entry and exit windows, so no empirical sensitivity comparison was computed.
This module is the frozen, pure reference for how such a comparison must be
computed once that evidence exists. Nothing imports it; it registers nothing,
schedules nothing and performs no I/O.

Governing documents: PREREG.md (frozen) plus PREREG_AMENDMENT.md (amendment 1,
independent-audit fixes, hashed into FREEZE.log before any new outcome).

What it pins:

* ``ruler_net_return_pct`` reproduces the OA-3 frozen ruler exactly (ask entry,
  bid exit, 100 multiplier, USD 0.65 per side, quantized to 0.000001) before any
  sensitivity term is applied (req1).
* ``select_quote`` mirrors the incumbent ``engine.options_nbbo_cohort.
  parse_quote_response`` row rules (amendment A2): RTH filter, crossed only when
  ``bid > 0 and ask > 0 and ask < bid``, per-side firm-condition /
  known-exchange / positive price+size validity, malformed integer fields and
  conflicting same-timestamp quotes make the leg ``quote_response_invalid``. It
  never uses a quote stamped before the scenario arrival time (req2). The
  earliest valid candidate decides; if its displayed size on the traded side is
  below the scenario requirement the leg is ``unavailable`` — never filled from
  a later, neighbouring-contract, midpoint or best-of-window quote (req3).
* ``scenario_outcome`` applies the OA-3 Ruling D session-close rules (amendment
  A1): at latency 0 an entry boundary outside RTH, a boundary + 60 s at or after
  the close, an exit window end at or after the close, or an exit target outside
  RTH is ``excluded`` exactly as OA-3 excludes it; at latency > 0 a scenario
  whose delayed window reaches the close is ``unavailable`` (population loss).
  Latency shifts BOTH arrivals: entry at boundary + latency, exit target at the
  selected entry event + 3600 s + latency (PREREG §3/§14, amendment A5).
* ``FROZEN_GRID`` is one shared, immutable scenario grid applied identically to
  every name; ``evaluate_episodes`` accepts no per-name parameters (req4).
* Every outcome keeps four separate layers — ``gross`` (descriptive mid-to-mid,
  never a fill), ``ruler`` (OA-3 cost formula; labelled with the OA-3 policy id
  only at latency 0), ``scenario`` and ``actual_fill`` (always unavailable: no
  executable fill is ever claimed) (req5).
* ``population_loss``, ``cluster_bootstrap_mean``, ``materiality`` and
  ``classify`` report contracts that become untradable, session-block
  (dependence-aware) uncertainty with an honest block count, the PREREG §9
  practical-effect bar and the decision-scenario floor (req6, amendment A3).

Clocks are integer or float seconds on a caller-supplied relative axis; this
module never reads a wall clock and contains no calendar dates. Packages,
0DTE contracts and short options are excluded, not modelled.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

RESEARCH_ONLY = True

POLICY_ID = "oa3.long_single_leg_h60_nbbo/v1"
DELAYED_RULER_BASIS = "oa3_cost_formula_on_delayed_scenario_quotes"
MULTIPLIER = Decimal(100)
FEE_PER_SIDE_USD = Decimal("0.65")
RETURN_QUANTUM = Decimal("0.000001")
ENTRY_WINDOW_S = 60
EXIT_HORIZON_S = 3600
EXIT_WINDOW_S = 60
BASELINE_MIN_DISPLAYED_CONTRACTS = 1
MIN_HOLDOUT_BLOCKS = 20
MIN_HOLDOUT_EPISODES = 60
MATERIAL_PAIRED_DROP_PP = 1.0
MATERIAL_LOSS_FRACTION = 0.10
TRAIN_NUMERATOR = 3
TRAIN_DENOMINATOR = 5

# Transcribed verbatim from engine/options_nbbo_cohort.py (the OA-3 quote parser).
FIRM_OPRA_QUOTE_CONDITIONS = frozenset(
    {0, 1, 3, 4, 5, 7, 8, 12, 13, 14, 15, 16, 42, 48, 49, 50, 51, 52, 53, 54, 56}
)
KNOWN_THETA_EXCHANGES = frozenset(set(range(1, 78)) - {74, 76})

STATUS_COMPLETE = "complete"
STATUS_UNAVAILABLE = "unavailable"
STATUS_EXCLUDED = "excluded"
STATUS_PENDING = "pending"

REASON_NO_QUOTE = "no_eligible_quote_in_window"
REASON_SIZE = "insufficient_displayed_size"
REASON_INVALID = "quote_response_invalid"

ACTUAL_FILL_LAYER = {
    "status": STATUS_UNAVAILABLE,
    "reason": "no_executable_fill_claim",
    "net_return_pct": None,
}


class ExecutionSensitivityError(ValueError):
    """Raised for malformed inputs; never used to mask an unavailable leg."""


@dataclass(frozen=True)
class Quote:
    """One retained exact-contract NBBO tick on a relative clock (seconds).

    Field names follow the Theta ``/v3/option/history/quote`` row. ``acquired_t``
    is the optional acquisition clock of the retained row (amendment A4).
    """

    t: float
    bid: Decimal
    ask: Decimal
    bid_size: int
    ask_size: int
    bid_condition: int = 0
    ask_condition: int = 0
    bid_exchange: int = 1
    ask_exchange: int = 1
    in_session: bool = True
    acquired_t: float | None = None


@dataclass(frozen=True)
class Scenario:
    """One frozen execution scenario. Applied identically to every name."""

    latency_s: float
    min_displayed_contracts: int
    fee_per_side_usd: Decimal
    slippage_per_share_usd: Decimal

    def key(self) -> str:
        return (
            f"lat{self.latency_s:g}_size{self.min_displayed_contracts}"
            f"_fee{self.fee_per_side_usd}_slip{self.slippage_per_share_usd}"
        )


@dataclass(frozen=True)
class ScenarioGrid:
    latencies_s: tuple[float, ...]
    min_displayed_contracts: tuple[int, ...]
    fees_per_side_usd: tuple[Decimal, ...]
    slippages_per_share_usd: tuple[Decimal, ...]

    def scenarios(self) -> tuple[Scenario, ...]:
        out = []
        for lat in self.latencies_s:
            for size in self.min_displayed_contracts:
                for fee in self.fees_per_side_usd:
                    for slip in self.slippages_per_share_usd:
                        out.append(Scenario(lat, size, fee, slip))
        return tuple(out)


BASELINE_SCENARIO = Scenario(0, BASELINE_MIN_DISPLAYED_CONTRACTS, FEE_PER_SIDE_USD, Decimal("0"))
DECISION_SCENARIO = Scenario(5, 1, FEE_PER_SIDE_USD, Decimal("0.01"))
FROZEN_GRID = ScenarioGrid(
    latencies_s=(0, 1, 5, 15, 30),
    min_displayed_contracts=(1, 5, 10),
    fees_per_side_usd=(Decimal("0.65"), Decimal("1.30")),
    slippages_per_share_usd=(Decimal("0"), Decimal("0.01"), Decimal("0.05")),
)


@dataclass(frozen=True)
class Episode:
    """One OA-3-eligible long single-leg expression with its raw quote path.

    ``boundary_t`` is ``expression.available_at``; ``session_open_t`` /
    ``session_close_t`` bound the same NYSE RTH session. ``entry_retrieved_t`` /
    ``exit_retrieved_t`` are the per-leg retrieval clocks and ``vintage`` the
    data-vintage label (amendment A4); all optional.
    """

    episode_id: str
    name: str
    contract_id: str
    block_id: str
    boundary_t: float
    session_close_t: float
    entry_quotes: tuple[Quote, ...]
    exit_quotes: tuple[Quote, ...]
    is_package: bool = False
    is_zero_dte: bool = False
    is_short: bool = False
    meta: Mapping[str, Any] = field(default_factory=dict)
    session_open_t: float | None = None
    entry_retrieved_t: float | None = None
    exit_retrieved_t: float | None = None
    vintage: str | None = None


def _dec(value: Any, label: str) -> Decimal:
    if isinstance(value, float):
        value = repr(value)
    try:
        out = Decimal(value)
    except Exception as exc:  # noqa: BLE001
        raise ExecutionSensitivityError(f"{label} is not a decimal") from exc
    if not out.is_finite():
        raise ExecutionSensitivityError(f"{label} is not finite")
    return out


def ruler_net_return_pct(
    entry_ask: Any,
    exit_bid: Any,
    *,
    fee_per_side_usd: Any = FEE_PER_SIDE_USD,
    slippage_per_share_usd: Any = Decimal("0"),
) -> Decimal:
    """OA-3 ruler. With default arguments it equals the frozen OA-3 formula.

    entry cost  = 100 * (ask + slippage) + fee
    exit value  = 100 * max(bid - slippage, 0) - fee
    return pct  = (exit value - entry cost) / entry cost * 100, quantized 1e-6.
    Slippage only ever worsens both legs; it can never improve a fill.
    """

    entry = _dec(entry_ask, "entry ask")
    exit_value = _dec(exit_bid, "exit bid")
    fee = _dec(fee_per_side_usd, "fee")
    slip = _dec(slippage_per_share_usd, "slippage")
    if entry <= 0 or exit_value < 0:
        raise ExecutionSensitivityError("return prices are outside bounds")
    if fee < 0 or slip < 0:
        raise ExecutionSensitivityError("costs must be non-negative")
    entry_cost = MULTIPLIER * (entry + slip) + fee
    exit_px = exit_value - slip
    if exit_px < 0:
        exit_px = Decimal(0)
    exit_net = MULTIPLIER * exit_px - fee
    return ((exit_net - entry_cost) / entry_cost * Decimal(100)).quantize(RETURN_QUANTUM)


def gross_mid_return_pct(entry: Quote, exit_: Quote) -> Decimal:
    """Descriptive mid-to-mid move of the SAME selected quotes. Never a fill."""

    mid_in = (entry.bid + entry.ask) / 2
    mid_out = (exit_.bid + exit_.ask) / 2
    if mid_in <= 0:
        raise ExecutionSensitivityError("entry mid is not positive")
    return ((mid_out - mid_in) / mid_in * Decimal(100)).quantize(RETURN_QUANTUM)


class _InvalidResponse(Exception):
    """A row the incumbent parser would reject (it raises, OA-3 -> UNAVAILABLE)."""


def _source_int(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise _InvalidResponse
    return value


def _source_price(value: Any) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise _InvalidResponse
    return value


def _in_rth(q: Quote, session_open_t: float | None, session_close_t: float | None) -> bool:
    if not q.in_session:
        return False
    if session_open_t is not None and q.t < session_open_t:
        return False
    if session_close_t is not None and q.t >= session_close_t:
        return False
    return True


def _identity(q: Quote) -> tuple:
    return (q.bid, q.ask, q.bid_size, q.ask_size, q.bid_exchange, q.ask_exchange,
            q.bid_condition, q.ask_condition)


def select_quote(
    quotes: Sequence[Quote],
    *,
    side: str,
    arrival_t: float,
    window_end_t: float,
    min_displayed_contracts: int,
    session_open_t: float | None = None,
    session_close_t: float | None = None,
    retrieved_t: float | None = None,
) -> tuple[Quote | None, str | None]:
    """Earliest valid quote with ``arrival_t <= t <= window_end_t``.

    Mirrors ``options_nbbo_cohort.parse_quote_response`` row by row: rows before
    the arrival are skipped, rows outside RTH are skipped, malformed integer
    fields make the response invalid (sizes/exchanges are checked before the
    crossed test, conditions after it, as in the incumbent), negative or crossed
    (``bid > 0 and ask > 0 and ask < bid``) rows are skipped, and only the traded
    side must be firm, on a known exchange and positive in price and size. Two
    different valid quotes at one timestamp anywhere in the window make the
    response invalid. Returns ``(quote, None)`` or ``(None, reason)``.

    A quote stamped before the arrival is never eligible. If the earliest valid
    quote shows fewer than ``min_displayed_contracts`` on the traded side, the
    leg is unavailable — the selector does not search later quotes for size
    (that would be a best-of-window fill convention).
    """

    if side not in ("ask", "bid"):
        raise ExecutionSensitivityError("side must be 'ask' or 'bid'")
    if min_displayed_contracts < 1:
        raise ExecutionSensitivityError("size requirement must be >= 1")
    candidates: list[Quote] = []
    seen: dict[float, tuple] = {}
    try:
        for q in sorted(quotes, key=lambda x: x.t):
            if q.t < arrival_t:
                continue
            if q.t > window_end_t:
                break
            if not _in_rth(q, session_open_t, session_close_t):
                continue
            if q.acquired_t is not None and (
                q.acquired_t < q.t or (retrieved_t is not None and q.acquired_t > retrieved_t)
            ):
                raise _InvalidResponse
            bid = _source_price(q.bid)
            ask = _source_price(q.ask)
            bid_size = _source_int(q.bid_size)
            ask_size = _source_int(q.ask_size)
            bid_exchange = _source_int(q.bid_exchange)
            ask_exchange = _source_int(q.ask_exchange)
            if bid < 0 or ask < 0 or (bid > 0 and ask > 0 and ask < bid):
                continue
            bid_condition = _source_int(q.bid_condition)
            ask_condition = _source_int(q.ask_condition)
            if side == "ask":
                valid = (ask > 0 and ask_size > 0
                         and ask_condition in FIRM_OPRA_QUOTE_CONDITIONS
                         and ask_exchange in KNOWN_THETA_EXCHANGES)
            else:
                valid = (bid > 0 and bid_size > 0
                         and bid_condition in FIRM_OPRA_QUOTE_CONDITIONS
                         and bid_exchange in KNOWN_THETA_EXCHANGES)
            if not valid:
                continue
            ident = _identity(q)
            previous = seen.get(q.t)
            if previous is not None and previous != ident:
                raise _InvalidResponse
            if previous is None:
                seen[q.t] = ident
                candidates.append(q)
    except _InvalidResponse:
        return None, REASON_INVALID
    if not candidates:
        return None, REASON_NO_QUOTE
    chosen = min(candidates, key=lambda x: x.t)
    shown = chosen.ask_size if side == "ask" else chosen.bid_size
    if shown < min_displayed_contracts:
        return None, REASON_SIZE
    return chosen, None


def _empty(base: Mapping[str, Any], status: str, reason: str) -> dict[str, Any]:
    return {**base, "status": status, "reason": reason,
            "gross": None, "ruler": None, "scenario_layer": None}


def scenario_outcome(episode: Episode, scenario: Scenario) -> dict[str, Any]:
    """Evaluate one episode under one frozen scenario, layers kept separate.

    Session rules follow OA-3 Ruling D at latency 0 and amendment A1 at
    latency > 0; retrieval maturity follows amendment A4.
    """

    base = {
        "episode_id": episode.episode_id,
        "name": episode.name,
        "contract_id": episode.contract_id,
        "block_id": episode.block_id,
        "scenario": scenario.key(),
        "actual_fill": dict(ACTUAL_FILL_LAYER),
    }
    if episode.is_package or episode.is_zero_dte or episode.is_short:
        reason = (
            "package_excluded" if episode.is_package
            else "zero_dte_excluded" if episode.is_zero_dte
            else "short_option_excluded"
        )
        return _empty(base, STATUS_EXCLUDED, reason)
    close = episode.session_close_t
    opened = episode.session_open_t
    boundary = episode.boundary_t
    # OA-3 Ruling D, before any quote parsing: properties of the episode alone.
    if (opened is not None and boundary < opened) or boundary >= close:
        return _empty(base, STATUS_EXCLUDED, "entry_boundary_outside_rth")
    if boundary + ENTRY_WINDOW_S >= close:
        return _empty(base, STATUS_EXCLUDED, "horizon_crosses_session_close")
    delayed = scenario.latency_s > 0
    arrival = boundary + scenario.latency_s
    entry_end = arrival + ENTRY_WINDOW_S
    if entry_end >= close:
        return _empty(base, STATUS_UNAVAILABLE, "entry_outside_session")
    if episode.entry_retrieved_t is not None and episode.entry_retrieved_t < entry_end:
        return _empty(base, STATUS_PENDING, "entry_window_not_matured_at_retrieval")
    entry, why = select_quote(
        episode.entry_quotes, side="ask", arrival_t=arrival, window_end_t=entry_end,
        min_displayed_contracts=scenario.min_displayed_contracts,
        session_open_t=opened, session_close_t=close, retrieved_t=episode.entry_retrieved_t,
    )
    if entry is None:
        return _empty(base, STATUS_UNAVAILABLE, f"entry_{why}")
    exit_target = entry.t + EXIT_HORIZON_S + scenario.latency_s
    exit_end = exit_target + EXIT_WINDOW_S
    if exit_end >= close:
        if delayed:
            return _empty(base, STATUS_UNAVAILABLE, "exit_outside_session")
        return _empty(base, STATUS_EXCLUDED, "horizon_crosses_session_close")
    if opened is not None and not opened <= exit_target < close:
        if delayed:
            return _empty(base, STATUS_UNAVAILABLE, "exit_outside_session")
        return _empty(base, STATUS_EXCLUDED, "exit_boundary_outside_rth")
    if episode.exit_retrieved_t is not None and episode.exit_retrieved_t < exit_end:
        return _empty(base, STATUS_PENDING, "exit_window_not_matured_at_retrieval")
    exit_q, why = select_quote(
        episode.exit_quotes, side="bid", arrival_t=exit_target, window_end_t=exit_end,
        min_displayed_contracts=scenario.min_displayed_contracts,
        session_open_t=opened, session_close_t=close, retrieved_t=episode.exit_retrieved_t,
    )
    if exit_q is None:
        return _empty(base, STATUS_UNAVAILABLE, f"exit_{why}")
    entry_cost = MULTIPLIER * (entry.ask + scenario.slippage_per_share_usd) + scenario.fee_per_side_usd
    exit_px = max(exit_q.bid - scenario.slippage_per_share_usd, Decimal(0))
    pnl = MULTIPLIER * exit_px - scenario.fee_per_side_usd - entry_cost
    return {
        **base,
        "status": STATUS_COMPLETE,
        "reason": None,
        "entry_t": entry.t,
        "exit_t": exit_q.t,
        "gross": {"basis": "descriptive_mid_to_mid_not_a_fill",
                  "return_pct": gross_mid_return_pct(entry, exit_q)},
        "ruler": {"basis": DELAYED_RULER_BASIS if delayed else POLICY_ID,
                  "net_return_pct": ruler_net_return_pct(entry.ask, exit_q.bid)},
        "scenario_layer": {
            "basis": "frozen_scenario_quote_ruler",
            "net_return_pct": ruler_net_return_pct(
                entry.ask, exit_q.bid,
                fee_per_side_usd=scenario.fee_per_side_usd,
                slippage_per_share_usd=scenario.slippage_per_share_usd,
            ),
            "net_pnl_usd": pnl,
        },
    }


def evaluate_episodes(
    episodes: Iterable[Episode], grid: ScenarioGrid = FROZEN_GRID
) -> dict[str, list[dict[str, Any]]]:
    """Apply every scenario of one shared frozen grid to every episode.

    There is deliberately no per-name, per-contract or outcome-dependent
    parameter: the grid is fixed before outcomes are read.
    """

    if not isinstance(grid, ScenarioGrid):
        raise TypeError("grid must be a frozen ScenarioGrid shared by all names")
    eps = tuple(episodes)
    scenarios = (BASELINE_SCENARIO,) + tuple(s for s in grid.scenarios() if s != BASELINE_SCENARIO)
    return {s.key(): [scenario_outcome(e, s) for e in eps] for s in scenarios}


def population_loss(
    baseline: Sequence[Mapping[str, Any]], scenario: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Contracts complete under the baseline that become untradable under a scenario."""

    base_ok = {r["episode_id"] for r in baseline if r["status"] == STATUS_COMPLETE}
    by_id = {r["episode_id"]: r for r in scenario}
    lost = sorted(i for i in base_ok if by_id.get(i, {}).get("status") != STATUS_COMPLETE)
    reasons: dict[str, int] = {}
    for i in lost:
        rsn = str(by_id.get(i, {}).get("reason") or "missing")
        reasons[rsn] = reasons.get(rsn, 0) + 1
    n = len(base_ok)
    return {
        "baseline_complete": n,
        "scenario_complete": sum(1 for r in scenario if r["status"] == STATUS_COMPLETE),
        "became_untradable": len(lost),
        "untradable_episode_ids": lost,
        "loss_fraction": (len(lost) / n) if n else None,
        "reasons": dict(sorted(reasons.items())),
    }


def cluster_bootstrap_mean(
    values: Sequence[float],
    block_ids: Sequence[str],
    *,
    n_boot: int = 2000,
    seed: int = 5051,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Session-block (cluster) bootstrap of a mean. Honest N = number of blocks."""

    v = np.asarray(values, dtype=float)
    b = np.asarray(block_ids, dtype=object)
    if v.shape[0] != b.shape[0]:
        raise ExecutionSensitivityError("values and block ids differ in length")
    if not 1 <= n_boot <= 20000:
        raise ExecutionSensitivityError("n_boot out of bounds")
    uniq = sorted(set(b.tolist()))
    if not uniq:
        return {"mean": None, "lo": None, "hi": None, "n_blocks": 0, "n_rows": 0}
    groups = [v[b == u] for u in uniq]
    sums = np.array([g.sum() for g in groups])
    counts = np.array([g.size for g in groups])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(uniq), size=(n_boot, len(uniq)))
    boot = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    lo, hi = np.quantile(boot, [alpha / 2, 1 - alpha / 2])
    return {
        "mean": float(v.mean()),
        "lo": float(lo),
        "hi": float(hi),
        "n_blocks": len(uniq),
        "n_rows": int(v.size),
    }


def paired_scenario_delta(
    baseline: Sequence[Mapping[str, Any]], scenario: Sequence[Mapping[str, Any]]
) -> tuple[list[float], list[str]]:
    """Scenario minus baseline net return on episodes complete under both."""

    by_id = {r["episode_id"]: r for r in scenario if r["status"] == STATUS_COMPLETE}
    deltas, blocks = [], []
    for r in baseline:
        if r["status"] != STATUS_COMPLETE or r["episode_id"] not in by_id:
            continue
        s = by_id[r["episode_id"]]
        deltas.append(float(s["scenario_layer"]["net_return_pct"] - r["ruler"]["net_return_pct"]))
        blocks.append(str(r["block_id"]))
    return deltas, blocks


def break_even_extra_cost_usd(
    baseline: Sequence[Mapping[str, Any]], *, n_boot: int = 2000, seed: int = 5051
) -> dict[str, Any]:
    """Per-episode extra symmetric per-side cost (USD/contract) that zeroes P&L.

    Returns the per-episode distribution (``net_pnl_usd / 2``) and its
    session-cluster bootstrap mean CI (PREREG §12 settings; amendment A6).
    """

    rows = [r for r in baseline if r["status"] == STATUS_COMPLETE]
    per_episode = [
        {"episode_id": r["episode_id"], "block_id": str(r["block_id"]),
         "usd": float(r["scenario_layer"]["net_pnl_usd"]) / 2.0}
        for r in rows
    ]
    ci = cluster_bootstrap_mean([p["usd"] for p in per_episode],
                                [p["block_id"] for p in per_episode], n_boot=n_boot, seed=seed)
    return {"per_episode": per_episode, "mean": ci["mean"], "ci": ci}


def chronological_session_split(session_keys: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """PREREG §11: sorted whole sessions; first floor(3n/5) train, rest holdout."""

    keys = list(session_keys)
    if any(not isinstance(k, str) or not k for k in keys):
        raise ExecutionSensitivityError("session keys must be non-empty strings")
    uniq = sorted(set(keys))
    n_train = (TRAIN_NUMERATOR * len(uniq)) // TRAIN_DENOMINATOR
    return tuple(uniq[:n_train]), tuple(uniq[n_train:])


def materiality(
    paired_delta_ci: Mapping[str, Any], decision_loss: Mapping[str, Any]
) -> dict[str, Any]:
    """PREREG §9 practical-effect bar for the decision scenario."""

    mean = paired_delta_ci.get("mean")
    loss = decision_loss.get("loss_fraction")
    reasons = []
    if mean is not None and mean <= -MATERIAL_PAIRED_DROP_PP:
        reasons.append("paired_mean_drop_ge_1pp")
    if loss is not None and loss >= MATERIAL_LOSS_FRACTION:
        reasons.append("untradable_fraction_ge_10pct")
    return {"material": bool(reasons), "reasons": reasons,
            "paired_mean_delta_pp": mean, "loss_fraction": loss}


def classify(
    baseline_ci: Mapping[str, Any],
    decision_ci: Mapping[str, Any],
    *,
    n_holdout_episodes: int,
    paired_delta_ci: Mapping[str, Any],
    decision_loss: Mapping[str, Any],
) -> str:
    """Frozen verdict rule (PREREG §6/§9/§13, amendment A3).

    Never relaxes the quote ruler to rescue a benefit.
    """

    if (baseline_ci.get("n_blocks") or 0) < MIN_HOLDOUT_BLOCKS or n_holdout_episodes < MIN_HOLDOUT_EPISODES:
        return "insufficient_data"
    lo = baseline_ci.get("lo")
    if lo is None or lo <= 0:
        return "no_benefit_under_ruler"
    d_lo = decision_ci.get("lo")
    if d_lo is None or d_lo <= 0:
        return "execution_fragile"
    if materiality(paired_delta_ci, decision_loss)["material"]:
        return "execution_fragile"
    if (decision_ci.get("n_blocks") or 0) < MIN_HOLDOUT_BLOCKS or (decision_ci.get("n_rows") or 0) < MIN_HOLDOUT_EPISODES:
        return "execution_fragile"
    return "execution_robust"
