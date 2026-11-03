"""Deterministic root-cause forensics for US Buy-Board episodes (Prophet Learning Loop §2).

WHAT THIS MODULE IS
-------------------
A pure classifier + aggregator. Given (a) an episode's outcome, (b) the board's OWN
state at the entry date, (c) the price path over the holding window, and (d) the
ticker's prior episode, it emits a multi-label failure taxonomy where every label
carries the trigger values that fired it. `scripts/prophet_postmortem.py` owns all the
I/O (parquet, jsonl, git archaeology, closes caches, artifact write); this file owns the
rules, so the rules are testable on synthetic rows with no fixtures.

FOUR THINGS THIS MODULE DELIBERATELY DOES NOT DO
------------------------------------------------
1. **No LLM anywhere** (constitution A7 — LLMs never originate signals). Every label is
   a feature-threshold rule with its threshold as a module constant and its trigger
   values written onto the row. A reader can re-derive any label by hand.
2. **No authority.** Nothing here ranks, sizes, gates or vetoes. A cohort that looks
   damning (say: every loser was bought under an `avoid` theme) is a CANDIDATE for a
   pre-registered study, not a live rule. That is why `veto_cost` below is symmetric —
   see WINNERS ARE FIRST-CLASS.
3. **No re-definition of the track record.** The scoring core is
   `engine.track_scoring` used unchanged: next-bar-close fill, forced verdict at
   `horizon`, symmetric maturity gate. This study runs the PURE fixed-horizon leg (no
   stop, no oscillator target) so the postmortem measures the SIGNAL, while the public
   ledger keeps its own exit rule. The two therefore differ by exactly the exit rule's
   effect (e.g. IPGP 2026-07-15: -17.9% fixed-horizon here vs -18.7% in the ledger,
   which stopped out on day 8). Neither is wrong; they answer different questions.
4. **No pooling of matured and in-flight rows into a rate.** An in-flight row is marked
   to the latest close, and a mark is outcome-conditioned in the exact way
   track_scoring rule 2 exists to prevent: today's biggest losers are over-represented
   among names that have not yet resolved. In-flight episodes are CLASSIFIED (that is
   the forensic value — a worst-rows list is largely made of names that have not yet
   finished) and are then held in a separate, labelled block that enters NO rate and NO
   expectancy. The corollary is that a cohort label read off such a row is a MARK with a
   shelf life: five of the operator's eleven worst names on 2026-07-31 were still open,
   and one of them (FN 07-21) closed +1.66%. See `path_tails`.
   `aggregate()` enforces this structurally: every rate is computed over
   `maturity == "matured"` only.

WINNERS ARE FIRST-CLASS (the symmetric cost column)
---------------------------------------------------
The failure taxonomy is only half an answer. "Every loser had a sector headwind at
entry" is worthless on its own, because the winners may have had one too — a headwind
veto that removes six losers and eight winners is a losing trade. So the same labels
are computed for winners (>= +8%), and `veto_cost` reports, for every costable claim
(one row per label-and-leg, `VETO_COST_SPECS`), BOTH sides of the counterfactual: losses
avoided AND winners forfeited, with the net. The winners-forfeited column is a column,
never a footnote.

SYSTEMIC VS ANOMALOUS
---------------------
A label that fires on nine episodes across one board night is one bad night; the same
label across seven nights is a process fault. `aggregate()` therefore counts label share
over DISTINCT ENTRY DATES as well as over rows, and prints the largest single-date
share, because episodes surfaced on the same night are one bet (track_scoring rule 3).

THE LABELS (§2 of research/PROPHET_LEARNING_LOOP_MASTERPLAN_BY_FABLE.md)
------------------------------------------------------------------------
  sector_headwind   theme/sector basket reco in {avoid, trim} at entry, or the board's
                    own spotlight read was `out_of_play` / stage `lagging`.
                    VISIBLE AT ENTRY. `weakening` (the RRG leading-but-rolling
                    quadrant) is recorded in the context and deliberately does NOT
                    fire — it is not yet a headwind, and folding it in would push the
                    label's base rate past half the board and make it uninformative.
  bought_extended   extension evidence at entry: the alignment read said overextended /
                    "Extended — wait", the entry-status was `extended`, the conviction
                    risk carried an `ext` component, or the fill price sat above the
                    board's own `chase_above` level. VISIBLE AT ENTRY.
  thesis_break      the setup itself failed: a later board night stamped
                    `hold.state == "broken"`, else a close crossed below the entry
                    row's published stop. NOT visible at entry.
  gap_event         a single-session close-to-close move <= -8% against the position.
                    Earnings/news class. NOT visible at entry. Close-to-close is the
                    honest available measure — the caches carry no opens, so a true
                    overnight gap is UNDER-counted, never over-counted.
  market_beta       the tape, not the pick: |excess| < 40% of |absolute| loss.
                    NOT visible at entry.
  re_admission      the same ticker was re-admitted <= 10 sessions after a prior
                    episode, on either of two legs that are NOT the same claim:
                      * `open_drawdown_at_readmit` — the prior position was ALREADY
                        >= 8% under water on the night of the re-admission. BUILDABLE.
                      * `prior_episode_loss` — the prior episode RESOLVED to a >= 8%
                        loss. HINDSIGHT (the operator's IPGP case was +3.04% GREEN on
                        the night the board bought it back).
                    NOT visible at entry as a label — see BUILDABLE VS HINDSIGHT.
  idiosyncratic     none of the above fired. Not a residual bucket to be proud of —
                    a large idiosyncratic share means the taxonomy is not yet
                    explaining the losses.

BUILDABLE VS HINDSIGHT (why `re_admission` is not a visible-at-entry label)
---------------------------------------------------------------------------
`VISIBLE_AT_ENTRY_LABELS` is a promise: every label in it could have been read off the
board's own state on the night of the pick, so costing a veto out of it answers a
question somebody could act on. `re_admission` fails that promise. Its headline
counterfactual (+79.08pp avoided over 7 flagged episodes, 2026-07-31 artifact) is
carried ENTIRELY by the `prior_episode_loss` leg, which needs the prior episode's
RESOLVED outcome — a number that does not exist on the night the board re-admits the
name. Leaving the label in the visible-at-entry list published a hindsight figure under
a buildable badge, which is the exact error the promotion gauntlet exists to prevent.
So:

  * the label sits OUTSIDE `VISIBLE_AT_ENTRY_LABELS`;
  * `veto_cost` carries ONE ROW PER LEG (`VETO_COST_SPECS`), each stamped
    `variant: buildable | hindsight_upper_bound`;
  * the buildable row is PRINTED EVEN WHEN IT FIRES ZERO TIMES. On today's data it
    fires zero times, and that zero is the finding — suppressing an empty row would
    leave only the hindsight number on the page, which is how a hindsight number gets
    read as a rule.

The per-ROW `visible_at_entry` flag stays leg-specific: an episode that fired on the
open-drawdown leg really was visible at entry and says so on the row. The label-level
list is the weaker, safer claim, and it is the one the aggregations, the report and the
admin panel read.

NULLS ARE PRINTED, NEVER DROPPED
--------------------------------
A ticker with no close path cannot be asked about gaps or stop crosses. Those labels
come back as an explicit null entry in `labels_null` with a reason, the episode still
appears in the artifact, and `aggregate()` reports the null counts per label so a
reader can see the denominator each label was actually evaluated on. The same holds one
level down for `re_admission`: a prior episode that could not be priced, or an
in-window prior with no mark, nulls the LEG it starves (`re_admission:<leg>`) so each
veto variant is costed only over the rows its own input reached.
"""
from __future__ import annotations

import datetime
import math
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

# --------------------------------------------------------------------------- #
# thresholds — every one of these is a knob a reader may re-derive a label from
# --------------------------------------------------------------------------- #

#: An episode is a LOSER at <= -8% absolute or <= -5% benchmark-excess. Two legs
#: because a -9% name in a -8% tape is a different failure from a -9% name in a flat
#: tape, and the taxonomy needs both in the cohort so `market_beta` has something to
#: separate.
LOSER_ABS_PCT = -8.0
LOSER_EXCESS_PCT = -5.0

#: An episode is a WINNER at >= +8% absolute — the mirror of the absolute loser gate,
#: so the two tails are cut at the same distance from zero.
WINNER_ABS_PCT = 8.0

#: Basket recommendations that count as a headwind at entry.
HEADWIND_RECOS = ("avoid", "trim")
#: Spotlight sector RRG stages that count as a headwind. `weakening` is excluded on
#: purpose (see module docstring).
HEADWIND_STAGES = ("lagging",)
#: Spotlight direction values that count as a headwind.
HEADWIND_DIRS = ("out_of_play",)

#: Conviction risk `ext` component at or above this counts as extension evidence.
EXT_RISK_MIN = 0.10

#: A single-session close-to-close move at or below this is a gap event.
GAP_PCT = -8.0

#: `market_beta` fires when the excess loss is smaller than this share of the absolute
#: loss — i.e. most of the damage was the tape.
BETA_SHARE_MAX = 0.40

#: Re-admission window, in sessions, and the loss that makes a re-admission notable.
READMIT_MAX_SESSIONS = 10
READMIT_LOSS_PCT = -8.0

#: The two `re_admission` legs, named once so the classifier, the veto specs, the null
#: keys and the tests all spell them the same way.
READMIT_LEG_OPEN_DRAWDOWN = "open_drawdown_at_readmit"   # buildable at entry
READMIT_LEG_PRIOR_LOSS = "prior_episode_loss"            # hindsight only

#: Leg-scoped null keys. `evaluated()` keys off the string in `labels_null[].label`, so
#: a leg that had no input leaves ITS universe without dragging the other leg out too.
READMIT_NULL_OPEN_DRAWDOWN = f"re_admission:{READMIT_LEG_OPEN_DRAWDOWN}"
READMIT_NULL_PRIOR_LOSS = f"re_admission:{READMIT_LEG_PRIOR_LOSS}"

#: The taxonomy, in the order aggregations print it. `idiosyncratic` sorts last on
#: purpose: it is the residual, and a reader should read it after the explanations.
TAXONOMY = (
    "sector_headwind",
    "bought_extended",
    "thesis_break",
    "gap_event",
    "market_beta",
    "re_admission",
    "idiosyncratic",
)

#: Bilingual plain-word copy for every label. Any surface that shows a label shows
#: these, never the raw slug (glance-tier law: no untranslated stats, no raw slugs).
TAXONOMY_COPY: dict[str, dict[str, str]] = {
    "sector_headwind": {
        "en": "Bought into a sector the desk was avoiding",
        "zh": "买在本已建议回避的板块",
    },
    "bought_extended": {
        "en": "Bought after the move had already run",
        "zh": "涨势已走完才买入",
    },
    "thesis_break": {
        "en": "The setup itself broke",
        "zh": "形态本身被破坏",
    },
    "gap_event": {
        "en": "A one-day drop of 8% or more",
        "zh": "单日下跌 8% 以上",
    },
    "market_beta": {
        "en": "The whole tape fell, not this pick",
        "zh": "整体行情下跌，非个股问题",
    },
    "re_admission": {
        "en": "Re-bought a name that had just lost money",
        "zh": "刚亏损的股票被再次买入",
    },
    "idiosyncratic": {
        "en": "No pattern found yet",
        "zh": "暂未发现规律",
    },
}

#: Labels the engine could in principle have acted on at entry, WHOLE — every episode
#: they fire on had the trigger readable on the night of the pick.
#:
#: `re_admission` is deliberately NOT here (see BUILDABLE VS HINDSIGHT in the module
#: docstring). It fires on two legs with opposite epistemic status, and on today's data
#: 100% of its fires are the hindsight leg, so a single "visible at entry: yes" badge on
#: the label would put a hindsight counterfactual in front of a reader as a buildable
#: one. It is costed instead through `VETO_COST_SPECS`, one row per leg.
VISIBLE_AT_ENTRY_LABELS = ("sector_headwind", "bought_extended")

#: What each veto row is worth as evidence. `buildable` = the trigger exists on the
#: night of the pick, so the row is a candidate a pre-registration could be written
#: against. `hindsight_upper_bound` = the trigger needs a number that did not exist yet;
#: read the row as a CEILING on what the pattern could be worth if a buildable proxy is
#: ever found, never as the value of a rule.
VETO_VARIANT_COPY: dict[str, dict[str, str]] = {
    "buildable": {
        "en": ("Buildable — the trigger was readable on the night of the pick, so this "
               "counterfactual is about a rule someone could pre-register."),
        "zh": ("可落地 —— 触发条件在选股当晚即可读到，因此该反事实对应的是一条可以先行"
               "预注册再检验的规则。"),
    },
    "hindsight_upper_bound": {
        "en": ("Hindsight upper bound — the trigger needs a number that did not exist "
               "yet at entry. It is a ceiling on what the pattern could be worth if a "
               "buildable trigger is ever found, NOT the value of a rule."),
        "zh": ("事后上限 —— 触发条件依赖入场当时尚不存在的数字。它只是「若日后找到可落地"
               "触发条件，该规律最多值多少」的上限，并非某条规则的实际价值。"),
    },
}

#: Per-leg plain-word copy, for rows whose label is split by leg.
VETO_LEG_COPY: dict[str, dict[str, str]] = {
    READMIT_LEG_OPEN_DRAWDOWN: {
        "en": "Re-bought while the earlier position was already 8% under water",
        "zh": "前一笔仍浮亏 8% 以上时又被买入",
    },
    READMIT_LEG_PRIOR_LOSS: {
        "en": "Re-bought a name whose earlier position ended up losing 8% or more",
        "zh": "前一笔最终亏损 8% 以上的股票被再次买入",
    },
}

#: One veto row per COSTABLE claim, in print order. A row is (label, leg) rather than
#: just a label because `re_admission` is two different claims sharing one name, and
#: costing them on one line publishes the hindsight number under a buildable badge.
#: A spec with `leg=None` costs the whole label.
VETO_COST_SPECS: tuple[dict[str, Any], ...] = (
    {"label": "sector_headwind", "leg": None, "variant": "buildable"},
    {"label": "bought_extended", "leg": None, "variant": "buildable"},
    {"label": "re_admission", "leg": READMIT_LEG_OPEN_DRAWDOWN, "variant": "buildable"},
    {"label": "re_admission", "leg": READMIT_LEG_PRIOR_LOSS,
     "variant": "hindsight_upper_bound"},
)

#: GICS sector name (both the retro-ledger spelling and the board's spotlight
#: spelling) -> the equal-weight sector basket id in data/baskets/latest.json.
SECTOR_BASKET_ID: dict[str, str] = {
    "Communication Services": "us_sector_comm",
    "Communications": "us_sector_comm",
    "Consumer Discretionary": "us_sector_discretionary",
    "Consumer Staples": "us_sector_staples",
    "Energy": "us_sector_energy",
    "Financials": "us_sector_financials",
    "Health Care": "us_sector_health",
    "Industrials": "us_sector_industrials",
    "Information Technology": "us_sector_tech",
    "Technology": "us_sector_tech",
    "Materials": "us_sector_materials",
    "Real Estate": "us_sector_realestate",
    "Utilities": "us_sector_utilities",
}


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _f(v: Any) -> float | None:
    """Coerce to a finite float, else None. pandas NaN, None and '' all collapse."""
    if v is None or isinstance(v, bool):
        return None
    try:
        out = float(v)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _s(v: Any) -> str | None:
    """Coerce to a non-empty stripped string, else None."""
    if v is None or isinstance(v, bool):
        return None
    try:
        if pd.isna(v):  # type: ignore[arg-type]
            return None
    except (TypeError, ValueError):
        pass
    out = str(v).strip()
    return out or None


def _dig(obj: Any, *path: str) -> Any:
    """Walk nested mappings, returning None the moment the path leaves a mapping."""
    cur = obj
    for key in path:
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(key)
    return cur


# --------------------------------------------------------------------------- #
# strict calendar dates — the only representation that may enter a comparison
# --------------------------------------------------------------------------- #
def iso_calendar_date(value: Any, *, field: str = "date") -> str:
    """Validate ``value`` as a strict ISO calendar date (YYYY-MM-DD) and return it.

    The single accepted representation: a ``str`` that ``datetime.date.fromisoformat``
    parses AND that round-trips back to itself exactly. Non-strings, timestamp
    spellings ("2026-07-01T00:00:00"), non-canonical spellings ("2026-7-1",
    "20260731") and impossible calendar dates ("2026-02-30") all raise
    ``ValueError`` — nothing is extracted, coerced, repaired or read lexically.
    Every date this module compares has passed through here, so lexical order IS
    chronological order by construction.
    """
    if not isinstance(value, str):
        raise ValueError(
            f"{field}: expected an ISO calendar-date string, got "
            f"{type(value).__name__}: {value!r}")
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{field}: not a valid ISO calendar date (YYYY-MM-DD): {value!r} ({exc})"
        ) from exc
    if parsed.isoformat() != value:
        raise ValueError(
            f"{field}: not a canonical ISO calendar date (YYYY-MM-DD): {value!r}")
    return value


# --------------------------------------------------------------------------- #
# entry-time context
# --------------------------------------------------------------------------- #
def entry_context(
    snap_row: Mapping[str, Any] | None,
    retro_row: Mapping[str, Any] | None,
    themes_at_entry: Mapping[str, Mapping[str, Any]] | None,
    theme_ids: Sequence[str] | None,
    basket_asof: str | None,
) -> dict:
    """Assemble everything the board KNEW about a name on the night it surfaced.

    ``snap_row``        the board's own JSON row for (entry_date, ticker), if the
                        snapshot archive covers that date. Richest source.
    ``retro_row``       the retro-grade ledger row for the same key. Covers dates
                        older than the snapshot archive, with fewer fields.
    ``themes_at_entry`` {theme_id: theme dict} reconstructed from the state of
                        data/baskets/latest.json AS OF the entry date (git archaeology).
    ``theme_ids``       basket ids the ticker belonged to (membership.json). Current
                        membership — see the drift caveat the CLI prints.
    ``basket_asof``     the `as_of` stamped inside the reconstructed baskets blob, so
                        every theme reading in the row is auditable back to one commit.

    Every field is nullable. A null here is a real "the board did not record this",
    never a zero.
    """
    themes_at_entry = themes_at_entry or {}
    conv = _dig(snap_row, "conviction") or {}
    spot = _dig(conv, "spotlight") or {}
    align = _dig(conv, "alignment") or {}
    risk = _dig(conv, "risk") or {}
    esig = _dig(snap_row, "entry_signal") or {}
    hold = _dig(snap_row, "hold") or {}

    sector = (
        _s(_dig(spot, "sector", "name"))
        or _s(_dig(snap_row, "sector"))
        or _s(_dig(retro_row, "sector"))
    )

    # --- theme leg: the name's OWN baskets, state read at the entry date -----------
    own: list[dict] = []
    for tid in sorted({str(t) for t in (theme_ids or []) if t}):
        th = themes_at_entry.get(tid)
        if not isinstance(th, Mapping):
            continue
        own.append({
            "id": tid,
            "reco": _s(th.get("reco")),
            "label": _s(th.get("label")),
            "score": _f(th.get("score")),
            "bull_days": _f(th.get("bull_days")),
            "rank": _f(th.get("rank")),
        })
    # The board's own spotlight theme, when it resolved one (PIT-exact mapping).
    spot_theme_id = _s(_dig(spot, "theme", "slug"))

    # --- sector-basket leg: always available once the sector is known --------------
    sector_basket = None
    sb_id = SECTOR_BASKET_ID.get(sector or "")
    if sb_id:
        th = themes_at_entry.get(sb_id)
        sector_basket = {
            "id": sb_id,
            "reco": _s(_dig(th, "reco")),
            "label": _s(_dig(th, "label")),
            "score": _f(_dig(th, "score")),
            "bull_days": _f(_dig(th, "bull_days")),
            "rank": _f(_dig(th, "rank")),
        }

    price = _f(_dig(snap_row, "price")) or _f(esig.get("spot"))
    chase = _f(esig.get("chase_above"))

    return {
        "sector": sector,
        "basket_asof": _s(basket_asof),
        "themes": own,
        "spotlight_theme_id": spot_theme_id,
        "sector_basket": sector_basket,
        "spotlight": {
            "dir": _s(spot.get("dir")),
            "z": _f(spot.get("z")),
            "sector_stage": _s(_dig(spot, "sector", "stage")),
            "sector_extended": _dig(spot, "sector", "extended"),
            "sector_pctile_252d": _f(_dig(spot, "sector", "pctile_252d")),
        },
        "extension": {
            "overextended": _dig(align, "overextended"),
            "entry_tier": _s(align.get("entry_tier")),
            "ext_risk": _f(_dig(risk, "components", "ext")),
            "ext_z": _f(_dig(snap_row, "ext_z")),
            "price": price,
            "chase_above": chase,
            "above_chase": (price is not None and chase is not None and price > chase),
            "off_high_pct": _f(_dig(snap_row, "off_high")) or _f(_dig(retro_row, "off_high")),
        },
        "conviction": {
            "band": _s(conv.get("band")) or _s(_dig(retro_row, "band")),
            "score": _f(conv.get("score")) or _f(_dig(retro_row, "score")),
            "composite_z": _f(conv.get("composite_z")) or _f(_dig(retro_row, "composite_z")),
            "alpha": _f(_dig(snap_row, "alpha")) or _f(_dig(retro_row, "alpha")),
            "tier": _s(_dig(retro_row, "align_tier")) or _s(_dig(snap_row, "align_tier")),
            "tier_cascade": _s(_dig(retro_row, "tier_cascade")),
            "urgency": _s(_dig(snap_row, "urgency")) or _s(_dig(retro_row, "urgency")),
            "state": _s(_dig(snap_row, "state")) or _s(_dig(retro_row, "state")),
        },
        "entry_plan": {
            "status": _s(esig.get("status")) or _s(_dig(retro_row, "entry_status")),
            "stop": _f(esig.get("stop")),
            "atr_pct": _f(esig.get("atr_pct")),
            "invalidation": _f(hold.get("invalidation")),
            "hold_state": _s(hold.get("state")) or _s(_dig(retro_row, "hold_state")),
        },
        "days_since_signal": _f(_dig(snap_row, "signal", "fresh_bars")),
        "board_tenure_days": _f(_dig(retro_row, "board_tenure_days")),
    }


# --------------------------------------------------------------------------- #
# price-path features
# --------------------------------------------------------------------------- #
def path_features(
    close: "pd.Series | None",
    fill_date: Any,
    n_bars: int | None,
    stop_level: float | None,
) -> dict | None:
    """Path facts over the holding window, or None when there is no usable path.

    ``close``      the name's close series (DatetimeIndex ascending), or None.
    ``fill_date``  the bar the position opened on.
    ``n_bars``     how many forward bars the window covers (the episode's `held`, or
                   the bars available for an in-flight row). None -> to the end.
    ``stop_level`` the entry row's published stop, if the board recorded one.

    Returning None (rather than a dict of nulls) is deliberate: the caller must be
    forced to record WHY the path labels are missing instead of silently reading
    "no gap found".
    """
    if close is None or not hasattr(close, "dropna"):
        return None
    s = close.dropna()
    if s.empty:
        return None
    try:
        fill_ts = pd.Timestamp(fill_date)
    except (TypeError, ValueError):
        return None
    i = s.index.searchsorted(fill_ts, side="left")
    if i >= len(s):
        return None
    window = s.iloc[i:] if n_bars is None else s.iloc[i:i + int(n_bars) + 1]
    if len(window) < 2:
        return None

    rets = window.pct_change().dropna() * 100.0
    worst_pct = float(rets.min()) if len(rets) else None
    worst_date = str(rets.idxmin().date()) if len(rets) else None

    stop_cross_date = None
    stop_cross_px = None
    if stop_level is not None and math.isfinite(stop_level) and stop_level > 0:
        below = window.iloc[1:][window.iloc[1:] < stop_level]
        if len(below):
            stop_cross_date = str(below.index[0].date())
            stop_cross_px = float(below.iloc[0])

    return {
        "n_bars": int(len(window) - 1),
        "worst_session_pct": worst_pct,
        "worst_session_date": worst_date,
        "stop_level": stop_level,
        "stop_cross_date": stop_cross_date,
        "stop_cross_px": stop_cross_px,
    }


# --------------------------------------------------------------------------- #
# cohort assignment
# --------------------------------------------------------------------------- #
def cohort_of(outcome_pct: float | None, excess_pct: float | None) -> str:
    """`loser` / `winner` / `neutral` / `unscored`, from the two-leg gates above.

    PRECEDENCE — THE ABSOLUTE RETURN DECIDES FIRST. The masterplan (§2) defines the
    winner gate as ">= +8%", absolute, with no excess leg; only the LOSER gate carries
    one. The excess leg exists to catch a name that LOST while the tape rose — not to
    demote a name that made money into a tape that rose faster.

    Testing the loser legs first made a +9% pick with -5.5% excess come back `loser`,
    which is wrong in both directions at once: it books a profitable pick as a loss, and
    it deletes a real winner from the winners-forfeited column, making every veto in
    `veto_cost` look cheaper than it is. Winner first, then the two loser legs, then
    neutral.
    """
    o = _f(outcome_pct)
    x = _f(excess_pct)
    if o is None and x is None:
        return "unscored"
    if o is not None and o >= WINNER_ABS_PCT:
        return "winner"
    if (o is not None and o <= LOSER_ABS_PCT) or (x is not None and x <= LOSER_EXCESS_PCT):
        return "loser"
    return "neutral"


def path_tails(cohort: str, mae_pct: float | None, mfe_pct: float | None) -> list[str]:
    """The gates an episode's PATH crossed that its VERDICT does not show.

    A forced-horizon verdict is a single number read off one bar, and `cohort_of` is
    right to trust it — but it is not the whole episode. FN 2026-07-21 fell 19.3% and
    closed +1.66%: `neutral`, correctly, and yet nothing like a name that drifted
    sideways for ten sessions. The difference IS the exit-policy question (masterplan
    G3): a stop would have booked that drawdown and forfeited the recovery, and the
    winner that ran +12% before handing it back is the same question from the other
    side. Both are invisible in a table keyed on the verdict alone.

    Recorded per row so the round trip is a FACT ON THE EPISODE rather than something a
    reader has to re-derive from MAE/MFE by eye — and so the serializer can tell a
    genuinely uneventful episode (safe to compact) from one whose context is the
    evidence. Empty when the path never left the band the verdict sits in.

    Takes the ROUNDED mae/mfe the row publishes, never the raw floats: a reader checking
    the flag against the printed number must never find them disagreeing at the gate.
    """
    out: list[str] = []
    mae, mfe = _f(mae_pct), _f(mfe_pct)
    if cohort != "loser" and mae is not None and mae <= LOSER_ABS_PCT:
        out.append("loser")
    if cohort != "winner" and mfe is not None and mfe >= WINNER_ABS_PCT:
        out.append("winner")
    return out


# --------------------------------------------------------------------------- #
# the classifier
# --------------------------------------------------------------------------- #
def _label(name: str, visible: bool, **trigger: Any) -> dict:
    return {
        "label": name,
        "en": TAXONOMY_COPY[name]["en"],
        "zh": TAXONOMY_COPY[name]["zh"],
        "visible_at_entry": bool(visible),
        "trigger": {k: trigger[k] for k in sorted(trigger)},
    }


def _null_readmit(nulls: list[dict], reason: str) -> None:
    """Null `re_admission` at the label level AND on both legs, with one reason.

    The leg-scoped keys are the denominators `veto_cost` costs each variant over, so a
    row the label could not be decided on has to leave BOTH leg universes as well —
    otherwise the buildable variant's "0 of N" would quietly count rows it never got to
    look at, which is the coverage lie this module exists to refuse.
    """
    for key in ("re_admission", READMIT_NULL_OPEN_DRAWDOWN, READMIT_NULL_PRIOR_LOSS):
        nulls.append({"label": key, "reason": reason})


def classify(
    *,
    outcome_pct: float | None,
    excess_pct: float | None,
    ctx: Mapping[str, Any],
    path: Mapping[str, Any] | None,
    hold_broken: Mapping[str, Any] | None = None,
    prior: Mapping[str, Any] | None = None,
    path_missing_reason: str = "no_price_path",
) -> tuple[list[dict], list[dict]]:
    """Return ``(labels, labels_null)`` for one episode.

    ``hold_broken``  {"date": .., "source": "hold_state_history"} when a later board
                     night stamped this run's hold state `broken`; None otherwise.
    ``prior``        the prior-episode comparison the caller's scan selected:
                     {"entry_date", "outcome_pct", "prior_matured",
                      "sessions_since_prior_exit", "mark_at_readmit_pct",
                      "n_priors_in_window", "selected_by"}.
                     None means the scan found NO prior episode in the window — a
                     DECIDED NEGATIVE that stays in every denominator, not a null.
                     {"undecidable": <reason>} means a prior existed and could not be
                     measured, which nulls the label and both legs.
    ``path_missing_reason``
                     why ``path`` is None, written onto the nulled path labels. The
                     caller must distinguish these: a delisted name with no series at
                     all and a name whose fill bar has not printed yet are BOTH
                     unevaluable, but only the first is a coverage hole. Defaulting
                     everything to "no_price_path" once made the artifact report 67
                     unpriceable episodes when 12 were unpriceable and 55 were simply
                     too young.

    Multi-label by construction. `idiosyncratic` is appended only when nothing else
    fired AND no path label had to be nulled — an episode whose gap/stop legs could not
    be evaluated is NOT "no pattern found", it is "not fully checked", and the null
    list says so.
    """
    labels: list[dict] = []
    nulls: list[dict] = []

    # ── sector_headwind — VISIBLE AT ENTRY ────────────────────────────────────
    # EVIDENCE FIRST, verdict second. The board's theme artifact only grew sector
    # baskets on 2026-06-26, and the snapshot archive only starts 2026-06-30, so a
    # third of the matured sample has NO entry-state to read at all. Emitting "no
    # headwind" for those rows would put them in the clean bucket and quietly halve
    # every headwind rate — a coverage lie of exactly the vacuous-green kind. When no
    # leg has an input, the label is NULLED and `aggregate` drops the row from that
    # label's denominator.
    hw_legs: list[dict] = []
    themes = ctx.get("themes") or []
    sb = ctx.get("sector_basket") or {}
    spot = ctx.get("spotlight") or {}
    hw_evidence = (
        any(th.get("reco") for th in themes)
        or sb.get("reco") is not None
        or spot.get("sector_stage") is not None
        or spot.get("dir") is not None
    )
    for th in themes:
        if (th.get("reco") or "") in HEADWIND_RECOS:
            hw_legs.append({"leg": "theme_reco", "theme_id": th.get("id"),
                            "reco": th.get("reco"), "label": th.get("label")})
    if (sb.get("reco") or "") in HEADWIND_RECOS:
        hw_legs.append({"leg": "sector_basket_reco", "theme_id": sb.get("id"),
                        "reco": sb.get("reco"), "label": sb.get("label")})
    if (spot.get("sector_stage") or "") in HEADWIND_STAGES:
        hw_legs.append({"leg": "sector_stage", "stage": spot.get("sector_stage"),
                        "pctile_252d": spot.get("sector_pctile_252d")})
    if (spot.get("dir") or "") in HEADWIND_DIRS:
        hw_legs.append({"leg": "spotlight_dir", "dir": spot.get("dir"),
                        "z": spot.get("z")})
    if hw_legs:
        labels.append(_label("sector_headwind", True, legs=hw_legs,
                             sector=ctx.get("sector"),
                             basket_asof=ctx.get("basket_asof")))
    elif not hw_evidence:
        nulls.append({"label": "sector_headwind",
                      "reason": "no_theme_state_or_spotlight_at_entry"})

    # ── bought_extended — VISIBLE AT ENTRY ────────────────────────────────────
    ext = ctx.get("extension") or {}
    status = (ctx.get("entry_plan") or {}).get("status") or ""
    ext_risk = _f(ext.get("ext_risk"))
    # Same evidence-first discipline. `above_chase` is a computed bool that is False
    # both when the fill was below the chase level AND when either price was missing,
    # so it can never stand in for evidence — the pair must be present.
    ex_evidence = (
        ext.get("overextended") is not None
        or ext.get("entry_tier") is not None
        or bool(status)
        or ext_risk is not None
        or (ext.get("price") is not None and ext.get("chase_above") is not None)
    )
    ex_legs: list[dict] = []
    if ext.get("overextended") is True:
        ex_legs.append({"leg": "alignment_overextended", "value": True})
    tier = ext.get("entry_tier") or ""
    if tier.lower().startswith("extended"):
        ex_legs.append({"leg": "entry_tier", "value": tier})
    if status == "extended":
        ex_legs.append({"leg": "entry_status", "value": status})
    if ext_risk is not None and ext_risk >= EXT_RISK_MIN:
        ex_legs.append({"leg": "risk_ext_component", "value": ext_risk,
                        "threshold": EXT_RISK_MIN})
    if ext.get("above_chase") is True:
        ex_legs.append({"leg": "above_chase_level", "price": ext.get("price"),
                        "chase_above": ext.get("chase_above")})
    if ex_legs:
        labels.append(_label("bought_extended", True, legs=ex_legs))
    elif not ex_evidence:
        nulls.append({"label": "bought_extended",
                      "reason": "no_entry_state_recorded"})

    # ── thesis_break — path-dependent, NOT visible at entry ───────────────────
    if hold_broken:
        labels.append(_label("thesis_break", False, source="hold_state_history",
                             date=hold_broken.get("date"),
                             board_date=hold_broken.get("board_date")))
    elif path is None:
        nulls.append({"label": "thesis_break", "reason": path_missing_reason})
    elif path.get("stop_cross_date"):
        labels.append(_label("thesis_break", False, source="stop_cross",
                             date=path.get("stop_cross_date"),
                             stop_level=path.get("stop_level"),
                             close=path.get("stop_cross_px")))
    elif path.get("stop_level") is None:
        nulls.append({"label": "thesis_break", "reason": "no_stop_level_recorded"})

    # ── gap_event — path-dependent, NOT visible at entry ──────────────────────
    if path is None:
        nulls.append({"label": "gap_event", "reason": path_missing_reason})
    else:
        worst = _f(path.get("worst_session_pct"))
        if worst is not None and worst <= GAP_PCT:
            labels.append(_label("gap_event", False, pct=round(worst, 2),
                                 date=path.get("worst_session_date"),
                                 threshold=GAP_PCT, basis="close_to_close"))

    # ── market_beta — NOT visible at entry ────────────────────────────────────
    o, x = _f(outcome_pct), _f(excess_pct)
    if o is not None and o < 0:
        if x is None:
            nulls.append({"label": "market_beta", "reason": "no_benchmark_excess"})
        else:
            share = abs(x) / abs(o) if abs(o) > 1e-9 else None
            if share is not None and share < BETA_SHARE_MAX:
                labels.append(_label("market_beta", False,
                                     excess_share_of_loss=round(share, 3),
                                     threshold=BETA_SHARE_MAX,
                                     abs_pct=round(o, 2), excess_pct=round(x, 2)))

    # ── re_admission ──────────────────────────────────────────────────────────
    # Two legs that differ in WHAT THE ENGINE COULD HAVE KNOWN, and the difference is
    # the finding, not a detail: a name re-bought while ALREADY 8% under water is a rule
    # the board could apply tonight; a name re-bought two days before the first position
    # rolled over is visible only in hindsight. Both are recorded, the row's
    # `visible_at_entry` is leg-specific, and `veto_cost` costs them on separate lines.
    #
    # NULL DISCIPLINE. `prior=None` means the caller's scan found NO prior episode inside
    # the window — a DECIDED NEGATIVE, and the row belongs in the denominator. Anything
    # the caller could not resolve arrives as a dict instead:
    #   {"undecidable": <reason>}  the in-window prior could not be priced or scored, so
    #                              this row is nulled on the label AND on both legs. A
    #                              name whose previous run cannot be measured is not
    #                              evidence that it came back clean.
    # An in-window prior missing ONE leg's input (no mark, or no prior outcome) nulls
    # only that leg, so the buildable variant's "0 of N" never counts rows whose
    # open-drawdown input never existed.
    if prior is not None:
        undecidable = _s(prior.get("undecidable"))
        gap = _f(prior.get("sessions_since_prior_exit"))
        prior_out = _f(prior.get("outcome_pct"))
        mark = _f(prior.get("mark_at_readmit_pct"))
        if undecidable:
            _null_readmit(nulls, undecidable)
        elif gap is None:
            _null_readmit(nulls, "prior_gap_not_measurable")
        else:
            in_window = gap <= READMIT_MAX_SESSIONS
            open_loss = mark is not None and mark <= READMIT_LOSS_PCT
            resolved_loss = prior_out is not None and prior_out <= READMIT_LOSS_PCT
            if in_window and mark is None:
                nulls.append({"label": READMIT_NULL_OPEN_DRAWDOWN,
                              "reason": "no_mark_at_readmit"})
            if in_window and prior_out is None:
                nulls.append({"label": READMIT_NULL_PRIOR_LOSS,
                              "reason": "no_prior_episode_outcome"})
            if in_window and mark is None and prior_out is None:
                nulls.append({"label": "re_admission",
                              "reason": "no_mark_and_no_prior_episode_outcome"})
            if in_window and (open_loss or resolved_loss):
                labels.append(_label(
                    "re_admission", open_loss,
                    prior_entry_date=prior.get("entry_date"),
                    prior_outcome_pct=None if prior_out is None else round(prior_out, 2),
                    # None when the caller did not say. A missing maturity flag is a
                    # null, never a False: an UNMATURED prior's "outcome" is a mark, and
                    # a reader comparing legs has to be able to see which is which.
                    prior_matured=prior.get("prior_matured"),
                    mark_at_readmit_pct=None if mark is None else round(mark, 2),
                    sessions_since_prior_exit=None if gap is None else int(gap),
                    leg=(READMIT_LEG_OPEN_DRAWDOWN if open_loss
                         else READMIT_LEG_PRIOR_LOSS),
                    n_priors_in_window=prior.get("n_priors_in_window"),
                    selected_by=prior.get("selected_by"),
                    threshold_pct=READMIT_LOSS_PCT,
                    max_sessions=READMIT_MAX_SESSIONS,
                ))

    # ── idiosyncratic — the residual ──────────────────────────────────────────
    # Fires whenever nothing else did. It deliberately does NOT suppress itself when a
    # leg had to be nulled: an episode with no label at all reads as a classifier bug,
    # and hiding the residual would hide exactly the rows the taxonomy fails to explain.
    # Instead the trigger names which legs were actually checked and which were not, and
    # `aggregate` splits the residual into fully-checked and partially-checked counts so
    # "no pattern found" is never confused with "not looked at".
    if not labels:
        # Intersected with the taxonomy on purpose: `labels_null` also carries
        # LEG-scoped keys (`re_admission:<leg>`), which are denominator bookkeeping for
        # one variant of one label, not a taxonomy leg a reader can be told went
        # unchecked. The label-level key is appended alongside them whenever the whole
        # label is undecidable, so nothing is lost by filtering here.
        unchecked = sorted({str(n.get("label")) for n in nulls} & set(TAXONOMY))
        labels.append(_label(
            "idiosyncratic", False,
            checked=[t for t in TAXONOMY[:-1] if t not in unchecked],
            unchecked=unchecked,
            fully_checked=not unchecked,
        ))

    labels.sort(key=lambda d: TAXONOMY.index(d["label"]))
    nulls.sort(key=lambda d: (d["label"], d["reason"]))
    return labels, nulls


# --------------------------------------------------------------------------- #
# aggregation
# --------------------------------------------------------------------------- #
def _rate(num: int, den: int) -> float | None:
    return round(100.0 * num / den, 1) if den else None


def _labels_of(row: Mapping[str, Any]) -> set[str]:
    return {str(lb.get("label")) for lb in (row.get("labels") or [])}


def _fired(row: Mapping[str, Any], label: str, leg: str | None) -> bool:
    """Did ``label`` fire on this row — and, when ``leg`` is given, on THAT leg?

    Leg filtering reads the label's own recorded trigger, so a veto variant is costed
    over exactly the episodes whose trigger it names. A row carrying the label with no
    recorded leg matches only the whole-label spec (``leg=None``); it is never credited
    to a specific leg on a guess.
    """
    for lb in (row.get("labels") or []):
        if str(lb.get("label")) != label:
            continue
        if leg is None or str((lb.get("trigger") or {}).get("leg")) == leg:
            return True
    return False


def _loss(rows: Iterable[Mapping[str, Any]]) -> float:
    """Summed ABSOLUTE loss over rows, in percentage points."""
    return sum(abs(_f(r.get("outcome_pct")) or 0.0) for r in rows)


def _nulled(row: Mapping[str, Any]) -> set[str]:
    return {str(nl.get("label")) for nl in (row.get("labels_null") or [])}


def evaluated(rows: Sequence[Mapping[str, Any]], label: str) -> list[Mapping[str, Any]]:
    """Rows on which ``label`` could actually be decided.

    ``label`` is any key that appears in a row's ``labels_null`` — a taxonomy label, or
    a LEG key like ``re_admission:open_drawdown_at_readmit`` when one leg of a label had
    an input the other did not.

    The single most important filter in this module. A row whose entry state was never
    recorded is NOT evidence that the label did not apply, and letting it sit in the
    unflagged bucket would deflate every rate and every counterfactual by the size of
    the uncovered history (here: a third of the matured sample predates the snapshot
    archive). Nulls are printed, then excluded from their own denominator — never
    silently counted as negatives.
    """
    return [r for r in rows if label not in _nulled(r)]


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict:
    """Roll episode rows up into the summary artifact.

    EVERY rate below is computed over ``maturity == "matured"`` rows only. In-flight
    rows are counted, listed and classified, and are reported in their own block
    (`in_flight`) that carries no rate — see rule 4 in the module docstring.
    """
    rows = list(rows)
    matured = sorted([r for r in rows if r.get("maturity") == "matured"],
                     key=lambda r: (str(r.get("entry_date")), str(r.get("ticker"))))
    inflight = sorted([r for r in rows if r.get("maturity") == "in_flight"],
                      key=lambda r: (str(r.get("entry_date")), str(r.get("ticker"))))

    losers = [r for r in matured if r.get("cohort") == "loser"]
    winners = [r for r in matured if r.get("cohort") == "winner"]
    loss_total = _loss(losers)

    # ── label frequencies, both tails, on the denominator each label EARNED ───
    # Shares are over rows where the label could be decided (see `evaluated`), and the
    # raw counts sit beside them so the two are never confused.
    #
    # `loss_contribution_pct` is the ONE column that does not move with the label: its
    # denominator is ALWAYS the whole matured-loser book, so the column is comparable
    # down the table and across runs. Mixing it with the per-label decidable denominator
    # made a label evaluable on 34 of 109 losers look like it carried a share of a
    # 34-loser book while the row beside it was sharing a 109-loser one — two different
    # 100%s in the same column. The per-label reach is disclosed SEPARATELY, as coverage:
    # `loser_coverage_pct` (share of losers the label could be decided on) and
    # `decidable_loss_share_pct` (share of the loser BOOK those rows carry). Read
    # contribution against coverage: 18.8% of the book carried by a label that could only
    # be decided on 31% of it is a very different sentence from 18.8% out of full reach.
    label_freq: list[dict] = []
    for name in TAXONOMY:
        l_eval = evaluated(losers, name)
        w_eval = evaluated(winners, name)
        l_rows = [r for r in l_eval if name in _labels_of(r)]
        w_rows = [r for r in w_eval if name in _labels_of(r)]
        n_null = len(matured) - len(evaluated(matured, name))
        label_freq.append({
            "label": name,
            "en": TAXONOMY_COPY[name]["en"],
            "zh": TAXONOMY_COPY[name]["zh"],
            "visible_at_entry": name in VISIBLE_AT_ENTRY_LABELS,
            "n_losers": len(l_rows),
            "n_losers_evaluated": len(l_eval),
            "n_losers_total": len(losers),
            "loser_share_pct": _rate(len(l_rows), len(l_eval)),
            "n_winners": len(w_rows),
            "n_winners_evaluated": len(w_eval),
            "n_winners_total": len(winners),
            "winner_share_pct": _rate(len(w_rows), len(w_eval)),
            "loss_contribution_pct": (
                round(100.0 * _loss(l_rows) / loss_total, 1) if loss_total else None),
            "loss_contribution_basis": "all matured losers' summed absolute loss",
            "loss_contribution_denominator_pp": round(loss_total, 2),
            "loser_coverage_pct": _rate(len(l_eval), len(losers)),
            "decidable_loss_share_pct": (
                round(100.0 * _loss(l_eval) / loss_total, 1) if loss_total else None),
            "n_matured_with_label": len([r for r in matured if name in _labels_of(r)]),
            "n_evaluated": len(matured) - n_null,
            "n_null_disclosed": n_null,
        })

    # ── systemic vs anomalous: distinct DATES, not just rows ──────────────────
    loser_dates = sorted({str(r.get("entry_date")) for r in losers})
    systemic: list[dict] = []
    for name in TAXONOMY:
        l_rows = [r for r in losers if name in _labels_of(r)]
        dates = sorted({str(r.get("entry_date")) for r in l_rows})
        by_date = {d: len([r for r in l_rows if str(r.get("entry_date")) == d]) for d in dates}
        top_date = max(by_date, key=lambda d: (by_date[d], d)) if by_date else None
        systemic.append({
            "label": name,
            "n_dates": len(dates),
            "date_share_pct": _rate(len(dates), len(loser_dates)),
            "n_loser_dates_total": len(loser_dates),
            "max_single_date_share_pct": (
                _rate(by_date[top_date], len(l_rows)) if top_date else None
            ),
            "max_single_date": top_date,
            "read": (
                "unfired" if not dates
                else "anomalous" if len(dates) <= 2
                else "systemic" if (len(loser_dates) and len(dates) / len(loser_dates) >= 0.5)
                else "recurring"
            ),
        })

    # ── the SYMMETRIC counterfactual: what each would-be veto costs ───────────
    # Both sides of the ledger for every costable claim. `n_winners_forfeited` and
    # `winners_forfeited_pct` are the operator's "don't weed out real winners"
    # requirement expressed as first-class columns.
    #
    # ONE ROW PER (label, leg), not per label — `VETO_COST_SPECS`. `re_admission` is two
    # claims with opposite epistemic status, and a single line for it printed a hindsight
    # number (+79.08pp on the 2026-07-31 artifact, carried entirely by the resolved-loss
    # leg) under a visible-at-entry badge. Every row now says which it is, and a
    # buildable row that fires ZERO times is still printed — the zero is the finding.
    veto_cost: list[dict] = []
    for spec in VETO_COST_SPECS:
        name, leg, variant = spec["label"], spec["leg"], spec["variant"]
        key = name if leg is None else f"{name}:{leg}"
        universe = evaluated(matured, key)       # the veto's real reach, leg-aware
        flagged = [r for r in universe if _fired(r, name, leg)]
        f_losers = [r for r in flagged if r.get("cohort") == "loser"]
        f_winners = [r for r in flagged if r.get("cohort") == "winner"]
        loss_avoided = _loss(f_losers)
        wins_forfeited = sum(_f(r.get("outcome_pct")) or 0.0 for r in f_winners)
        pnl_flagged = [_f(r.get("outcome_pct")) for r in flagged]
        pnl_flagged = [v for v in pnl_flagged if v is not None]
        copy = VETO_LEG_COPY.get(leg or "") or TAXONOMY_COPY[name]
        veto_cost.append({
            "key": key,
            "label": name,
            "leg": leg,
            "variant": variant,
            # A row-level restatement of the label-level promise. `buildable` here means
            # the trigger existed at entry; it is NOT read off VISIBLE_AT_ENTRY_LABELS,
            # because a label can be excluded there precisely BECAUSE one of its legs is
            # hindsight while the other is not.
            "visible_at_entry": variant == "buildable",
            "en": copy["en"],
            "zh": copy["zh"],
            "variant_en": VETO_VARIANT_COPY[variant]["en"],
            "variant_zh": VETO_VARIANT_COPY[variant]["zh"],
            "basis": (
                "matured episodes on which this label could be decided" if leg is None
                else f"matured episodes on which the `{leg}` leg could be decided"
            ),
            "n_universe": len(universe),
            "n_matured_total": len(matured),
            "n_null_disclosed": len(matured) - len(universe),
            "n_flagged": len(flagged),
            "flagged_share_of_universe_pct": _rate(len(flagged), len(universe)),
            "n_losers_avoided": len(f_losers),
            "loss_avoided_pct": round(loss_avoided, 2),
            "n_winners_forfeited": len(f_winners),
            "winners_forfeited_pct": round(wins_forfeited, 2),
            "net_pct_if_vetoed": round(loss_avoided - wins_forfeited, 2),
            "mean_outcome_of_flagged_pct": (
                round(sum(pnl_flagged) / len(pnl_flagged), 2) if pnl_flagged else None
            ),
            "mean_outcome_of_unflagged_pct": _mean_outcome(
                [r for r in universe if not _fired(r, name, leg)]
            ),
            "n_dates_flagged": len({str(r.get("entry_date")) for r in flagged}),
        })

    # ── headwind-at-entry vs tailwind-at-entry ───────────────────────────────
    # Restricted to rows where the label was decidable, so an uncovered row can never
    # land in the "no headwind" bucket and flatter it.
    def _split(pred, label: str) -> dict:
        sel = [r for r in evaluated(matured, label) if pred(r)]
        outs = [_f(r.get("outcome_pct")) for r in sel]
        outs = [v for v in outs if v is not None]
        return {
            "n": len(sel),
            "n_losers": len([r for r in sel if r.get("cohort") == "loser"]),
            "loss_rate_pct": _rate(len([r for r in sel if r.get("cohort") == "loser"]), len(sel)),
            "n_winners": len([r for r in sel if r.get("cohort") == "winner"]),
            "win_rate_pct": _rate(len([r for r in sel if r.get("cohort") == "winner"]), len(sel)),
            "mean_outcome_pct": round(sum(outs) / len(outs), 2) if outs else None,
            "n_dates": len({str(r.get("entry_date")) for r in sel}),
        }

    cohort_splits = {
        "headwind_at_entry": _split(
            lambda r: "sector_headwind" in _labels_of(r), "sector_headwind"),
        "no_headwind_at_entry": _split(
            lambda r: "sector_headwind" not in _labels_of(r), "sector_headwind"),
        "extended_at_entry": _split(
            lambda r: "bought_extended" in _labels_of(r), "bought_extended"),
        "not_extended_at_entry": _split(
            lambda r: "bought_extended" not in _labels_of(r), "bought_extended"),
    }

    # ── repeat offenders ──────────────────────────────────────────────────────
    by_ticker: dict[str, list[Mapping[str, Any]]] = {}
    for r in losers:
        by_ticker.setdefault(str(r.get("ticker")), []).append(r)
    repeat = sorted(
        (
            {
                "ticker": tk,
                "n_loser_episodes": len(eps),
                "entry_dates": sorted(str(e.get("entry_date")) for e in eps),
                "total_loss_pct": round(
                    sum(abs(_f(e.get("outcome_pct")) or 0.0) for e in eps), 2),
                "labels": sorted({lb for e in eps for lb in _labels_of(e)}),
            }
            for tk, eps in by_ticker.items() if len(eps) > 1
        ),
        key=lambda d: (-d["total_loss_pct"], d["ticker"]),
    )

    # ── diagnostics: why a label did or did not fire ──────────────────────────
    # A label that never fires is a claim about the world, and a reader is entitled to
    # see the quantity it was thresholded on rather than a bare zero. `market_beta` in
    # particular reads as "the tape was never the cause" — that is only credible with
    # the excess-share distribution printed beside it.
    shares = sorted(
        abs(_f(r.get("excess_pct")) or 0.0) / abs(_f(r.get("outcome_pct")) or 1.0)
        for r in losers
        if _f(r.get("excess_pct")) is not None and _f(r.get("outcome_pct"))
    )
    idio = [r for r in matured if "idiosyncratic" in _labels_of(r)]
    idio_full = [
        r for r in idio
        if any(lb.get("label") == "idiosyncratic"
               and (lb.get("trigger") or {}).get("fully_checked") is True
               for lb in (r.get("labels") or []))
    ]
    diagnostics = {
        "market_beta_excess_share": {
            "n": len(shares),
            "threshold": BETA_SHARE_MAX,
            "min": round(shares[0], 3) if shares else None,
            "p10": round(shares[len(shares) // 10], 3) if shares else None,
            "median": round(shares[len(shares) // 2], 3) if shares else None,
            "max": round(shares[-1], 3) if shares else None,
            "note_en": ("|benchmark-excess| as a share of |absolute| loss, over matured "
                        "losers. The label fires below the threshold; a distribution "
                        "sitting entirely above it means the losses were the picks, not "
                        "the tape."),
            "note_zh": ("成熟亏损样本中「超额亏损」占「绝对亏损」的比例。低于阈值才触发该标签；"
                        "若分布整体高于阈值，说明亏损来自选股本身而非大盘。"),
        },
        "idiosyncratic_split": {
            "n_total": len(idio),
            "n_fully_checked": len(idio_full),
            "n_with_unchecked_legs": len(idio) - len(idio_full),
            "note_en": ("`idiosyncratic` fires when nothing else did. Rows with unchecked "
                        "legs are NOT 'no pattern found' — they are 'not fully looked at', "
                        "and the row's own labels_null names which leg."),
            "note_zh": ("当其他标签均未触发时才标记为「暂未发现规律」。若该行仍有未能判定的检查项，"
                        "其含义是「尚未查全」而非「确无规律」，具体缺哪一项见该行的 labels_null。"),
        },
    }

    return {
        "n_episodes": len(rows),
        "n_matured": len(matured),
        "n_in_flight": len(inflight),
        "n_unscored": len([r for r in rows if r.get("maturity") == "unscored"]),
        "n_board_dates": len({str(r.get("entry_date")) for r in matured}),
        "cohorts": {
            "n_losers": len(losers),
            "n_winners": len(winners),
            "n_neutral": len([r for r in matured if r.get("cohort") == "neutral"]),
            "loser_gate": {"abs_pct": LOSER_ABS_PCT, "excess_pct": LOSER_EXCESS_PCT},
            "winner_gate": {"abs_pct": WINNER_ABS_PCT},
            "total_loser_loss_pct": round(loss_total, 2),
        },
        "label_frequency": label_freq,
        "systemic_vs_anomalous": systemic,
        "veto_cost": veto_cost,
        "cohort_splits": cohort_splits,
        "repeat_offenders": repeat,
        "diagnostics": diagnostics,
        "in_flight": {
            "n": len(inflight),
            "note_en": ("Marked to the latest close and classified for forensics only. "
                        "These rows enter no rate and no expectancy — an unresolved "
                        "position's mark is outcome-conditioned."),
            "note_zh": ("按最新收盘价标记，仅用于复盘分类。此类记录不计入任何胜率或期望值 —— "
                        "未了结持仓的浮动盈亏会受结果选择影响。"),
            # The four marks add to `n`, so a reader can check that the two tails the
            # report prints are the whole in-flight block and not a chosen slice.
            "n_losers_marked": len([r for r in inflight if r.get("cohort") == "loser"]),
            "n_winners_marked": len([r for r in inflight if r.get("cohort") == "winner"]),
            "n_neutral_marked": len([r for r in inflight if r.get("cohort") == "neutral"]),
            "n_unscored_marked": len([r for r in inflight if r.get("cohort") == "unscored"]),
            "label_frequency": [
                {
                    "label": name,
                    "n": len([r for r in inflight if name in _labels_of(r)]),
                }
                for name in TAXONOMY
            ],
        },
        "taxonomy": [
            {"label": name, "en": TAXONOMY_COPY[name]["en"],
             "zh": TAXONOMY_COPY[name]["zh"],
             "visible_at_entry": name in VISIBLE_AT_ENTRY_LABELS,
             # Only `re_admission` needs this today: the label is not visible at entry,
             # but one of its two legs is, and a reader who sees a bare "no" is owed the
             # reason rather than left to infer that the pattern is unusable.
             "legs": [
                 {"leg": s["leg"], "variant": s["variant"],
                  "visible_at_entry": s["variant"] == "buildable",
                  "en": VETO_LEG_COPY[s["leg"]]["en"],
                  "zh": VETO_LEG_COPY[s["leg"]]["zh"]}
                 for s in VETO_COST_SPECS
                 if s["label"] == name and s["leg"] is not None
             ] or None}
            for name in TAXONOMY
        ],
        "thresholds": {
            "loser_abs_pct": LOSER_ABS_PCT,
            "loser_excess_pct": LOSER_EXCESS_PCT,
            "winner_abs_pct": WINNER_ABS_PCT,
            "headwind_recos": list(HEADWIND_RECOS),
            "headwind_stages": list(HEADWIND_STAGES),
            "headwind_dirs": list(HEADWIND_DIRS),
            "ext_risk_min": EXT_RISK_MIN,
            "gap_pct": GAP_PCT,
            "beta_share_max": BETA_SHARE_MAX,
            "readmit_max_sessions": READMIT_MAX_SESSIONS,
            "readmit_loss_pct": READMIT_LOSS_PCT,
            "readmit_legs": {
                READMIT_LEG_OPEN_DRAWDOWN: "buildable",
                READMIT_LEG_PRIOR_LOSS: "hindsight_upper_bound",
            },
            "visible_at_entry_labels": list(VISIBLE_AT_ENTRY_LABELS),
        },
    }


def _mean_outcome(rows: Iterable[Mapping[str, Any]]) -> float | None:
    vals = [_f(r.get("outcome_pct")) for r in rows]
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


# --------------------------------------------------------------------------- #
# cohort integrity — descriptive source-stamp receipt (Q02/B22)
# --------------------------------------------------------------------------- #
# A DESCRIPTIVE measurement of which board definition each existing episode was
# originally admitted under, read from the two ORIGINAL membership sources. Like the
# rest of this module it is measurement tier only: no grade moves, no verdict, no
# promotion read, and no pooled cross-era rate is ever produced here. The legacy
# `aggregate()` summary a caller already publishes is untouched — this block is strictly
# additive and exists so a reader can see where "the board's record" is actually two
# different board products.
#
# Division of labour (unchanged): the CALLER (scripts/prophet_postmortem.py) owns all
# I/O and hands in pre-extracted memberships; this file owns the rules; `aggregate()`
# itself owns every descriptive per-era calculation.
#
#   memberships = {
#     "<source>": {date: {ticker: [stamp_or_None, ...]}},   # ONE entry per source record
#   }
# The list keeps every record a source carries — the retro ledger stores one row per
# (as_of, ticker, horizon), so two horizons on one night are two records, and stamps
# that differ between them are a real same-key conflict, never silently deduped.

#: Version of the `cohort_integrity` block itself.
COHORT_INTEGRITY_SCHEMA = "prophet_cohort_integrity/v1"

#: The five descriptive partitions, in the FIXED precedence a block is resolved in.
#: An episode lands in the FIRST partition that matches, so a same-date disagreement is
#: a `conflict` even when other membership days carry mixed stamps too, and an episode
#: with mixed stamps plus a gap is `mixed` — the record-level disagreement always
#: outranks the quieter defects.
INTEGRITY_CONFLICT = "conflict"
INTEGRITY_MIXED = "mixed"
INTEGRITY_PARTIAL = "partial"
INTEGRITY_SINGLE = "single"
INTEGRITY_UNASSIGNED = "unassigned"
INTEGRITY_PARTITIONS = (
    INTEGRITY_CONFLICT,
    INTEGRITY_MIXED,
    INTEGRITY_PARTIAL,
    INTEGRITY_SINGLE,
    INTEGRITY_UNASSIGNED,
)
INTEGRITY_PARTITION_PRECEDENCE = "conflict > mixed > partial > single > unassigned"

#: Stamp spellings that ARE explicitly missing. Mirrors the nullish spellings the US
#: ledger folds to its legacy era — MINUS `legacy` itself: a receipt manufactures no era
#: name. Whatever a source literally recorded is kept exactly as recorded; only true
#: absence (None, non-string, empty, a null-like placeholder) lands here, and it stays
#: missing attribution. It is never date-inferred, never back-filled from the current
#: definition.
_INTEGRITY_NULLISH = frozenset({"", "none", "nan", "<na>", "null"})


def integrity_stamp(value: Any) -> str | None:
    """The ORIGINAL `rank_by` string a source recorded, or None when explicitly missing.

    Non-string values, empties and null-like placeholders are missing — not an era.
    Everything else comes back EXACTLY as recorded (including surrounding whitespace,
    case and spelling), so `us_prophet_v1`, `alpha` and `legacy` stay
    three different recorded stamps and none of them is invented.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    return None if text.lower() in _INTEGRITY_NULLISH else value


def integrity_source_receipt(
    memberships: Mapping[str, Mapping[str, Mapping[str, Sequence[Any]]]] | None,
) -> dict:
    """Where each source reaches, and where the sources' memberships differ.

    A date present in only one source is that source's DOCUMENTED REACH — the retro
    ledger reaches back before the snapshot archive and the archive runs past the last
    retro grade — and is never counted as a disagreement. With FEWER THAN TWO sources
    there is no overlap and no cross-source disagreement at all, and the receipt says
    so truthfully instead of intersecting a set with itself.

    Published per overlap date: the tickers only one source carried, and any ticker
    both sources carried with differing stamps. Published across ALL dates of each
    source, overlap or not: within-source same-date stamp disagreements (e.g. two
    horizons on one night recorded different `rank_by`). No winner/loser selection,
    no preferred source.

    Membership date and ticker keys are validated strictly (``iso_calendar_date``,
    non-empty strings); a malformed key raises instead of entering any comparison.
    """
    memberships = memberships or {}
    per_source: dict[str, dict] = {}
    date_sets: dict[str, set[str]] = {}
    ticker_sets: dict[str, dict[str, set[str]]] = {}
    stamp_sets: dict[str, dict[str, dict[str, set[str]]]] = {}
    for src in sorted(memberships):
        days = memberships.get(src) or {}
        if not isinstance(days, Mapping):
            raise ValueError(
                f"memberships[{src!r}]: expected a mapping of date -> ticker -> stamps, "
                f"got {type(days).__name__}")
        dates = sorted(iso_calendar_date(d, field=f"memberships[{src!r}] date key")
                       for d in days)
        n_records = 0
        by_date_tickers: dict[str, set[str]] = {}
        by_date_stamps: dict[str, dict[str, set[str]]] = {}
        for d in dates:
            day = days.get(d) or {}
            if not isinstance(day, Mapping):
                raise ValueError(
                    f"memberships[{src!r}][{d}]: expected a mapping of ticker -> stamps")
            tks = by_date_tickers.setdefault(d, set())
            stamps = by_date_stamps.setdefault(d, {})
            for tk in sorted(day):
                if not isinstance(tk, str) or not tk.strip():
                    raise ValueError(
                        f"memberships[{src!r}][{d}]: invalid ticker key {tk!r}")
                recorded = day.get(tk) or []
                n_records += len(recorded)
                tks.add(tk)
                for raw in recorded:
                    st = integrity_stamp(raw)
                    if st is not None:
                        stamps.setdefault(tk, set()).add(st)
        date_sets[src] = set(dates)
        ticker_sets[src] = by_date_tickers
        stamp_sets[src] = by_date_stamps
        per_source[src] = {
            "n_dates": len(dates),
            "dates": dates,
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
            "n_membership_records": n_records,
        }

    # Within-source same-date stamp disagreements, across ALL dates of each source —
    # disjoint dates included, so a horizon conflict on a date the other source never
    # reached is still visible on the receipt beside the cross-source differences.
    within: list[dict] = []
    for src in sorted(stamp_sets):
        for d in sorted(stamp_sets[src]):
            for tk in sorted(stamp_sets[src][d]):
                stamps = sorted(stamp_sets[src][d][tk])
                if len(stamps) > 1:
                    within.append({"source": src, "date": d, "ticker": tk,
                                   "stamps": stamps})
    within.sort(key=lambda r: (r["source"], r["date"], r["ticker"]))

    all_dates: set[str] = set()
    for s in date_sets.values():
        all_dates |= s
    # ONE SOURCE = NO OVERLAP, truthfully. Intersecting a single date set with itself
    # used to report every date as an "overlap" and every ticker as a disagreement.
    overlap: list[str] = []
    per_overlap: list[dict] = []
    n_diff = 0
    only_dates = {src: sorted(date_sets[src]) for src in sorted(date_sets)}
    if len(date_sets) >= 2:
        overlap = sorted(set.intersection(*date_sets.values()))
        only_dates = {
            src: sorted(date_sets[src] - set().union(
                *(s for name, s in date_sets.items() if name != src)))
            for src in sorted(date_sets)
        }
        for d in overlap:
            sets = {src: set(ticker_sets[src].get(d) or set())
                    for src in sorted(date_sets)}
            shared: set[str] | None = None
            for s in sets.values():
                shared = set(s) if shared is None else (shared & s)
            shared = shared or set()
            # "Only in this source" = present here, absent from EVERY other source — the
            # union of the others, never `union - this` (that would also drop tickers the
            # sources genuinely share).
            only_in = {
                src: sorted(sets[src] - set().union(
                    *(s for name, s in sets.items() if name != src)))
                for src in sorted(sets)
            }
            stamp_disagreements: list[dict] = []
            for tk in sorted(set().union(*sets.values())):
                carriers = [src for src in sorted(sets) if tk in sets[src]]
                if len(carriers) < 2:
                    continue
                by_src = {src: sorted(stamp_sets[src].get(d, {}).get(tk) or set())
                          for src in carriers}
                flat = {st for v in by_src.values() for st in v}
                if len(flat) > 1:
                    stamp_disagreements.append({"ticker": tk, "stamps_by_source": by_src})
            differs = any(only_in.values()) or bool(stamp_disagreements)
            n_diff += 1 if differs else 0
            per_overlap.append({
                "date": d,
                "n_shared_tickers": len(shared),
                "only_in": only_in,
                "stamp_disagreements": stamp_disagreements,
                "membership_difference": differs,
            })

    latest = max(all_dates) if all_dates else None
    return {
        "sources": per_source,
        "latest_board_date": latest,
        "n_dates_all_sources": len(all_dates),
        "overlap_dates": overlap,
        "n_overlap_dates": len(overlap),
        "dates_in_one_source_only": sorted(all_dates - set(overlap)),
        "per_source_only_dates": only_dates,
        "membership_on_overlap_dates": per_overlap,
        "n_overlap_dates_with_membership_difference": n_diff,
        "within_source_stamp_disagreements": within,
        "n_within_source_stamp_disagreements": len(within),
        "note_en": ("A board date present in only one source is that source's documented "
                    "reach, not a disagreement; with fewer than two sources there is no "
                    "overlap and no cross-source disagreement at all. Per-overlap-date "
                    "ticker-set and stamp differences, and within-source same-date stamp "
                    "disagreements across ALL dates, are published so real membership "
                    "disagreement is visible. No source is preferred and no cohort is "
                    "selected."),
        "note_zh": ("仅出现在单一来源的board日期属于该来源的既有覆盖范围，并非分歧；来源少于两个时，"
                    "不存在任何重叠或跨来源分歧。重叠日期上两来源的成分与盖章差异、以及单一来源内部"
                    "所有日期的同日盖章分歧均逐项公布，以便暴露真正的成员分歧。"
                    "不偏袒任何来源，也不据此挑选任何群体。"),
    }


def integrity_assignments(
    memberships: Mapping[str, Mapping[str, Mapping[str, Sequence[Any]]]] | None,
    episodes: Sequence[Mapping[str, Any]] | None,
    *,
    as_of: str,
) -> list[dict]:
    """One assignment record per existing episode, in fixed (entry_date, ticker) order.

    ``as_of`` is REQUIRED and must be a strict ISO calendar date: the FROZEN ORIGINAL
    CUT every membership observation is read through. The caller supplies it — the
    generation path's real board as_of, or a preserved artifact's validated as_of —
    never a clock, the current config, or the current sources' latest date. Membership
    observations are filtered to ``d <= as_of``; an open episode runs to that cut
    INCLUSIVE, a closed one to ``min(existing board_exit_date EXCLUSIVE, as_of
    INCLUSIVE)``. Anything a later source vintage recorded beyond the cut is excluded
    from attribution and disclosed on the block (``as_of_cut``); it can never assign,
    conflict or re-era an episode.

    Membership evidence must be CONTIGUOUS inside that interval, reading the union of
    buy memberships across the original sources on each recorded board date. The first
    recorded in-window board date where the ticker is absent from ALL sources is a
    genuine observed gap: stamps recorded after it belong to a later admission, so they
    are excluded from this episode's attribution, disclosed on the record
    (``observed_gap``), and the episode is downgraded from ``single`` to ``partial`` so
    it cannot enter the per-era summaries. A date absent from one source alone is
    disjoint documented coverage, not a gap; a calendar date no source recorded is
    never inferred. Legacy episode identity, board_exit and returns are read, never
    rewritten.

    Resolution (first match wins):
      * ``conflict``   — differing recorded stamps for the SAME (date, ticker), within
                         one source (e.g. across horizons) or between the two sources;
      * ``mixed``      — different recorded stamps on DIFFERENT membership days (an
                         episode crossing an era boundary);
      * ``partial``    — agreeing recorded stamps, plus at least one missing stamp,
                         missing original entry-day attribution, or an observed gap;
      * ``single``     — one recorded stamp, every membership record stamped, including
                         an explicitly stamped original entry-day record;
      * ``unassigned`` — no recorded stamp anywhere in the window.

    Episodes with no membership record at all are `unassigned` too — a membership gap
    is missing attribution, never a manufactured era. An episode whose identity cannot
    be validated (non-ISO or nullish entry/exit; NaN is NOT the open sentinel, None is)
    is ``unavailable``: an explicit error record that enters no partition, no window
    and no era, never a lexical comparison. Score fields on ``episodes`` rows are only
    read for identity (ticker/entry/exit/maturity) and are never written.
    """
    cut = iso_calendar_date(as_of, field="as_of")
    cut_d = datetime.date.fromisoformat(cut)
    memberships = memberships or {}

    normalized: dict[str, dict[str, dict[str, list[Any]]]] = {}
    recorded: set[str] = set()
    for src in sorted(memberships):
        days = memberships.get(src) or {}
        if not isinstance(days, Mapping):
            raise ValueError(
                f"memberships[{src!r}]: expected a mapping of date -> ticker -> stamps")
        norm_days: dict[str, dict[str, list[Any]]] = {}
        for raw_key in days:
            d = iso_calendar_date(raw_key, field=f"memberships[{src!r}] date key")
            day = days.get(d) or {}
            if not isinstance(day, Mapping):
                raise ValueError(
                    f"memberships[{src!r}][{d}]: expected a mapping of ticker -> stamps")
            norm_day: dict[str, list[Any]] = {}
            for tk in day:
                if not isinstance(tk, str) or not tk.strip():
                    raise ValueError(
                        f"memberships[{src!r}][{d}]: invalid ticker key {tk!r}")
                norm_day[tk] = list(day.get(tk) or [])
            norm_days[d] = norm_day
        normalized[src] = norm_days
        recorded |= set(norm_days)
    recorded_iso = sorted(recorded)          # validated ISO: lexical order IS chronology
    recorded_dates = [datetime.date.fromisoformat(d) for d in recorded_iso]

    def _present(d_iso: str, ticker: str) -> bool:
        return any((normalized[src].get(d_iso) or {}).get(ticker)
                   for src in normalized)

    # Preserve the artifact's row identity; ticker/entry is only a legacy key,
    # never a substitute for distinct native episode identity or a deduplication rule.
    episode_rows = list(episodes or [])
    key_counts: dict[tuple[str, str], int] = {}
    for row in episode_rows:
        if isinstance(row, Mapping):
            tk, entry = row.get("ticker"), row.get("entry_date")
            if isinstance(tk, str) and isinstance(entry, str):
                key_counts[(tk, entry)] = key_counts.get((tk, entry), 0) + 1
    intervals: dict[str, list[tuple[int, str, str]]] = {}
    for i, row in enumerate(episode_rows):
        if not isinstance(row, Mapping):
            continue
        try:
            tk = row.get("ticker")
            entry = iso_calendar_date(row.get("entry_date"), field="entry_date")
            exit_ = row.get("board_exit_date")
            end = iso_calendar_date(exit_, field="board_exit_date") if exit_ is not None else "9999-12-31"
            if isinstance(tk, str) and tk.strip() and entry <= cut and end > entry:
                intervals.setdefault(tk, []).append((i, entry, end))
        except ValueError:
            continue
    overlapping: set[int] = set()
    for spans in intervals.values():
        for left_pos, (i, start, end) in enumerate(spans):
            for j, other_start, other_end in spans[left_pos + 1:]:
                if start != other_start and start < other_end and other_start < end:
                    overlapping.update((i, j))
    indexed = sorted(enumerate(episode_rows), key=lambda item: (
        str(item[1].get("entry_date")), str(item[1].get("ticker")), item[0])
        if isinstance(item[1], Mapping) else ("", "", item[0]))
    out: list[dict] = []
    for row_index, ep in indexed:
        if not isinstance(ep, Mapping):
            out.append({
                "ticker": None, "entry_date": None, "board_exit_date": None,
                "maturity": None, "partition": None, "unavailable": True,
                "identity_error": f"episode row is {type(ep).__name__}, not an object",
                "unavailable_reason": "malformed_episode_identity",
            })
            continue
        raw_tk = ep.get("ticker")
        raw_entry = ep.get("entry_date")
        raw_exit = ep.get("board_exit_date")
        ticker = raw_tk if isinstance(raw_tk, str) and raw_tk.strip() else None
        error: str | None = None
        unavailable_reason = "malformed_episode_identity"
        if ticker is None:
            error = f"invalid ticker {raw_tk!r}"
        entry_d: datetime.date | None = None
        exit_d: datetime.date | None = None
        if error is None:
            try:
                entry_d = datetime.date.fromisoformat(
                    iso_calendar_date(raw_entry, field="entry_date"))
            except ValueError as exc:
                error = str(exc)
        if error is None and raw_exit is not None:
            if isinstance(raw_exit, float) and math.isnan(raw_exit):
                error = ("board_exit_date is NaN — NaN is not the open sentinel "
                         "(None is); refused instead of read as a lexical window bound")
            else:
                try:
                    exit_d = datetime.date.fromisoformat(
                        iso_calendar_date(raw_exit, field="board_exit_date"))
                except ValueError as exc:
                    error = str(exc)
        if error is None and entry_d > cut_d:
            error = "episode entry_date is after the frozen artifact as_of cut"
            unavailable_reason = "episode_entry_after_cut"
        if error is None and exit_d is not None and exit_d <= entry_d:
            error = "board_exit_date must be strictly after entry_date (exclusive exit)"
            unavailable_reason = "invalid_episode_interval"
        if error is None and key_counts.get((ticker, raw_entry), 0) > 1:
            error = "repeated legacy ticker/entry identity cannot distinguish native episodes"
            unavailable_reason = "ambiguous_episode_identity"
        if error is None and row_index in overlapping:
            error = "overlapping same-ticker episode intervals do not identify disjoint admissions"
            unavailable_reason = "overlapping_episode_intervals"
        if error is not None:
            out.append({
                "ticker": raw_tk if isinstance(raw_tk, str) else None,
                "entry_date": raw_entry if isinstance(raw_entry, str) else None,
                "board_exit_date": raw_exit if isinstance(raw_exit, str) else None,
                "maturity": ep.get("maturity"),
                "partition": None,
                "unavailable": True,
                "identity_error": error,
                "unavailable_reason": unavailable_reason,
            })
            continue
        open_episode = exit_d is None

        window: list[str] = []
        for d_iso, d_date in zip(recorded_iso, recorded_dates):
            if d_date < entry_d or d_date > cut_d:
                continue
            if exit_d is not None and d_date >= exit_d:
                continue
            window.append(d_iso)

        records: list[dict] = []
        for src in sorted(normalized):
            days = normalized[src]
            for d in window:
                for raw in (days.get(d) or {}).get(ticker) or []:
                    records.append({"source": src, "date": d,
                                    "stamp": integrity_stamp(raw)})

        # CONTIGUITY. The first recorded in-window board date with the ticker absent
        # from ALL sources is a genuine observed gap; stamps after it belong to a
        # later admission and are excluded from this episode's attribution.
        gap_iso = next((d for d in window if not _present(d, ticker)), None)
        excluded_after_gap: list[str] = []
        n_excluded_after_gap = 0
        if gap_iso is not None:
            excluded_after_gap = [d for d in window if d > gap_iso]
            records = [r for r in records if r["date"] <= gap_iso]
            n_excluded_after_gap = sum(
                len((normalized[src].get(d) or {}).get(ticker) or [])
                for src in sorted(normalized) for d in excluded_after_gap)

        distinct: set[str] = set()
        n_missing = 0
        by_date: dict[str, dict[str, set[str]]] = {}
        for rec in records:
            if rec["stamp"] is None:
                n_missing += 1
            else:
                distinct.add(rec["stamp"])
                by_date.setdefault(rec["date"], {}) \
                       .setdefault(rec["source"], set()).add(rec["stamp"])
        entry_records = [dict(rec) for rec in records if rec["date"] == str(entry_d)]
        entry_stamps = sorted({rec["stamp"] for rec in entry_records
                               if rec["stamp"] is not None})
        entry_missing = sum(rec["stamp"] is None for rec in entry_records)
        if len(entry_stamps) > 1:
            entry_state = INTEGRITY_CONFLICT
        elif not entry_stamps:
            entry_state = INTEGRITY_UNASSIGNED
        elif entry_missing:
            entry_state = INTEGRITY_PARTIAL
        else:
            entry_state = INTEGRITY_SINGLE
        conflicts: list[dict] = []
        for d in sorted(by_date):
            day = by_date[d]
            day_stamps: set[str] = set()
            for v in day.values():
                day_stamps |= v
            if len(day_stamps) > 1:
                conflicts.append({
                    "date": d,
                    "stamps_by_source": {src: sorted(day[src]) for src in sorted(day)},
                })

        if conflicts:
            partition = INTEGRITY_CONFLICT
        elif len(distinct) > 1:
            partition = INTEGRITY_MIXED
        elif distinct and (n_missing or entry_state != INTEGRITY_SINGLE):
            partition = INTEGRITY_PARTIAL
        elif distinct:
            partition = INTEGRITY_SINGLE
        else:
            partition = INTEGRITY_UNASSIGNED
        # An observed gap means the episode's evidence is not contiguous: however
        # clean the pre-gap stamps look, the attribution is partial at best and can
        # never enter the per-era (single-only) summaries.
        if gap_iso is not None and partition == INTEGRITY_SINGLE:
            partition = INTEGRITY_PARTIAL

        records_by_source: dict[str, int] = {}
        for rec in records:
            records_by_source[rec["source"]] = records_by_source.get(rec["source"], 0) + 1

        observed_gap = None
        if gap_iso is not None:
            observed_gap = {
                "date": gap_iso,
                "n_records_after_gap_excluded": n_excluded_after_gap,
                "dates_after_gap": excluded_after_gap,
            }

        out.append({
            "ticker": ticker,
            "entry_date": entry_d.isoformat(),
            "board_exit_date": None if exit_d is None else exit_d.isoformat(),
            "open_episode": open_episode,
            "maturity": ep.get("maturity"),
            "as_of": cut,
            "entry_attribution": {
                "state": entry_state,
                "records": entry_records,
                "stamps": entry_stamps,
                "n_missing_stamp_records": entry_missing,
            },
            "partition": partition,
            "stamp": next(iter(sorted(distinct))) if len(distinct) == 1 else None,
            "stamps": sorted(distinct),
            "window_dates": list(window),
            "n_membership_records": len(records),
            "n_stamped_records": len(records) - n_missing,
            "n_missing_stamp_records": n_missing,
            "records_by_source": {k: records_by_source[k] for k in sorted(records_by_source)},
            "conflicts": conflicts,
            "observed_gap": observed_gap,
        })
    for assignment, (row_index, _) in zip(out, indexed):
        assignment["episode_row_index"] = row_index
    return out


def cohort_integrity_block(
    memberships: Mapping[str, Mapping[str, Mapping[str, Sequence[Any]]]] | None,
    episodes: Sequence[Mapping[str, Any]] | None,
    *,
    as_of: str,
    include_era_rates: bool = True,
) -> dict:
    """Assemble the additive top-level `cohort_integrity` block.

    ``as_of`` is REQUIRED — the frozen original cut (strict ISO calendar date) every
    membership observation is read through; see `integrity_assignments`. Later source
    vintages are disclosed on the block and never assign, conflict or re-era anything.

    ``episodes`` are the artifact's own episode rows; only identity and maturity fields
    are read and nothing on them is written — the legacy summary and every episode field
    stay byte-equivalent. When ``include_era_rates`` is set, each era's descriptive
    summary is computed with the EXISTING `aggregate()` over that era's `single`
    episodes alone — and ONLY while the original sources' membership observations are
    conflict-free (no within-source same-date stamp disagreement, no cross-source stamp
    disagreement, no same-date ticker-set difference on an overlap date, and no read or
    schema defect reported by the caller). Each era block is a wrapper stamped
    ``descriptive_only`` with an explicit no-promotion authority around the unchanged
    legacy aggregate. Two eras never share a denominator, no pooled cross-era rate is
    produced here, and no promotion or readiness verdict either.
    """
    cut = iso_calendar_date(as_of, field="as_of")
    assignments = integrity_assignments(memberships, episodes, as_of=cut)
    # Validate and disclose the full source reach, but adjudicate membership
    # agreement only inside the artifact's cut. A later conflicting revision
    # cannot invalidate an earlier frozen description.
    full_receipt = integrity_source_receipt(memberships)
    cut_memberships = {
        src: {d: day for d, day in (days or {}).items() if d <= cut}
        for src, days in (memberships or {}).items()
    }
    receipt = integrity_source_receipt(cut_memberships)

    valid_assignments = [a for a in assignments if a.get("partition") is not None]
    n_unavailable = sum(a.get("unavailable") is True for a in assignments)

    partitions: dict[str, dict] = {}
    for name in INTEGRITY_PARTITIONS:
        sel = [a for a in assignments if a["partition"] == name]
        partitions[name] = {
            "n_episodes": len(sel),
            "n_entry_dates": len({a["entry_date"] for a in sel}),
            "maturity": {
                "matured": len([a for a in sel if a.get("maturity") == "matured"]),
                "in_flight": len([a for a in sel if a.get("maturity") == "in_flight"]),
                "unscored": len([a for a in sel
                                 if a.get("maturity") not in ("matured", "in_flight")]),
            },
        }

    # FUTURE VINTAGE REACH — disclosed, never allowed to assign. Everything the
    # sources recorded beyond the frozen cut is counted here so a reader can see
    # exactly what the cut excluded.
    n_after_cut = 0
    for src in sorted(memberships or {}):
        days = memberships.get(src) or {}
        for raw_key, day in days.items():
            if str(raw_key) > cut:      # validated ISO keys: lexical == chronological
                n_after_cut += sum(len(v or []) for v in (day or {}).values())
    dates_after_cut = sorted({d for src in full_receipt["sources"].values()
                              for d in src["dates"] if d > cut})

    membership_conflict_free = (
        not any(a.get("conflicts") for a in assignments)
        and receipt["n_overlap_dates_with_membership_difference"] == 0
        and not receipt["within_source_stamp_disagreements"]
    )

    block: dict = {
        "schema": COHORT_INTEGRITY_SCHEMA,
        "descriptive_only": True,
        "as_of_cut": {
            "as_of": cut,
            "n_membership_records_after_cut": n_after_cut,
            "dates_after_cut": dates_after_cut,
            "full_source_reach": full_receipt,
            "note_en": ("Frozen original cut: membership observations are read only up "
                        "to this explicit as_of. Later source vintages are disclosed "
                        "here and are never allowed to assign, conflict or re-era an "
                        "episode."),
            "note_zh": ("冻结的原始切点：成员观测仅读取到该显式 as_of 为止。更晚的来源版本仅在"
                        "此披露，绝不参与任何episode的归属、冲突判定或时代划分。"),
        },
        "membership_conflict_free": membership_conflict_free,
        "partition_precedence": INTEGRITY_PARTITION_PRECEDENCE,
        "counting_unit": "unambiguous_original_episode_row",
        "n_episode_rows": len(assignments),
        "n_episodes": len(valid_assignments),
        "n_episodes_unavailable": n_unavailable,
        "partitions": partitions,
        "sources": receipt,
        "episodes": assignments,
        "note_en": ("Descriptive receipt of each episode's ORIGINAL board-definition "
                    "stamps, from the original membership sources only, read up to the "
                    "explicit as_of cut. The legacy summary is retained unchanged for "
                    "compatibility and is NOT a cross-era comparison; missing stamps "
                    "are missing attribution, never a legacy era; disjoint source reach "
                    "is documented coverage, not disagreement; an observed membership "
                    "gap splits an episode from later readmission stamps."),
        "note_zh": ("仅描述性收据：按原始成员来源记录每个episode当时的board定义盖章，"
                    "且只读取到显式 as_of 切点为止。旧版汇总按原样保留以兼容下游，且不是任何"
                    "跨时代比较；缺失盖章属于缺失归属，而非某个「legacy 时代」；来源间不重叠的"
                    "覆盖范围是正常记录，并非分歧；观测到的成员缺口会把episode与后来的重新"
                    "纳入盖章分开。"),
    }

    if include_era_rates:
        if n_unavailable:
            block["per_era_unavailable_reason"] = "invalid_or_ambiguous_episode_identity_or_interval"
        elif not membership_conflict_free:
            block["per_era_unavailable_reason"] = "conflicting_original_membership"
        else:
            per_era: dict[str, dict] = {}
            era_stamps = sorted({a["stamp"] for a in assignments
                                 if a["partition"] == INTEGRITY_SINGLE and a["stamp"]})
            for stamp in era_stamps:
                era_rows = [
                    episodes[a["episode_row_index"]] for a in assignments
                    if a.get("stamp") == stamp and a["partition"] == INTEGRITY_SINGLE
                ]
                per_era[stamp] = {
                    "era_stamp": stamp,
                    "descriptive_only": True,
                    "promotion_authority": (
                        "none — descriptive receipt only: this era summary confers no "
                        "grade change, no verdict, no promotion or readiness read, and "
                        "its episodes are never pooled with or compared against any "
                        "other era"),
                    "aggregate": aggregate(era_rows),
                }
            block["per_era"] = per_era
            block["per_era_note_en"] = ("One fully independent descriptive summary per "
                                        "recorded era stamp, computed with the existing "
                                        "aggregate() on that era's single-assigned episodes "
                                        "alone. Every block is descriptive_only with an "
                                        "explicit no-promotion authority; eras are never "
                                        "pooled, never share a rate denominator, and are "
                                        "never cross-compared.")
            block["per_era_note_zh"] = ("每个记录在案的board定义各一份独立描述性汇总，仅用该时代"
                                        "明确单一归属的episode、按既有 aggregate() 口径计算。"
                                        "每份均为 descriptive_only 并显式声明不携带任何晋升权力；"
                                        "各时代绝不合并、不共用任何分母、不做跨时代比较。")
    return block


def classify_source_findings(view: Mapping[str, Any]) -> dict[str, Any]:
    """Project T4 source/data observations without evaluating any episode outcome.

    The caller owns the supplied snapshot's identity/freshness. Exact canonical parser
    diagnostics are an allowlist, not a prose heuristic: T4's generic parse-error code
    also covers size caps and unreadable content. Strong stale-input attribution needs
    the upstream's own content clock in this same snapshot. Neither counts nor classes
    confer causal, independent-trial, evaluation-tier or execution authority.
    """
    from copy import deepcopy

    if (not isinstance(view, Mapping)
            or view.get("schema") != "mastermind.output_health.v1"
            or not isinstance(view.get("outputs"), list)
            or not isinstance(view.get("generated"), Mapping)):
        raise ValueError("a canonical output-health snapshot is required")
    rows = view["outputs"]
    if any(not isinstance(row, Mapping) for row in rows):
        raise ValueError("output-health outputs must be records")
    observed_at = view["generated"].get("observed_at")
    def usable_clock(value, *, naive_allowed=False):
        if not isinstance(value, str) or not value.strip():
            return False
        try:
            parsed = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return False
        # Date-only clocks cannot earn T4's stale content verdict without a calendar.
        return (len(value.strip()) > 10
                and (parsed.utcoffset() is not None or naive_allowed))

    if not usable_clock(observed_at):
        raise ValueError("output-health observation time is required")

    fields = ("engine_id", "artifact_id", "path", "state", "assessment_status",
              "decided_by", "observed_at", "source_asof", "age_hours",
              "freshness_sla_hours", "dependency_bound", "required_inputs",
              "reason_codes", "evidence", "reader_observation")
    def retained(row):
        return deepcopy({key: row.get(key) for key in fields})

    by_id: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        aid = row.get("artifact_id")
        if isinstance(aid, str) and aid:
            by_id.setdefault(aid, []).append(row)

    def identified(row):
        return (all(isinstance(row.get(key), str) and row[key].strip()
                    for key in ("artifact_id", "engine_id", "path"))
                and len(by_id.get(row["artifact_id"], [])) == 1
                and row.get("observed_at") == observed_at)

    # These are exact diagnostics emitted by build_output_health._read_watermark.
    # No match on arbitrary error prose, caps, empty stores, or malformed timestamps.
    parser_defects = {
        f"{location} ({error})"
        for location in ("content does not parse", "last jsonl row does not parse",
                         "envelope sidecar does not parse")
        for error in ("JSONDecodeError", "ValueError")
    }
    def content_stale(row):
        age, sla = row.get("age_hours"), row.get("freshness_sla_hours")
        clock = row.get("source_asof")
        codes = row.get("reason_codes")
        valid_codes = isinstance(codes, list) and all(isinstance(c, str) and c for c in codes)
        numeric = lambda value: (type(value) in (int, float)
                                 and math.isfinite(value))
        return (identified(row) and row.get("state") == "stale"
                and row.get("assessment_status") in ("complete", "partial")
                and row.get("decided_by") == "content_watermark"
                and valid_codes and usable_clock(clock, naive_allowed=(
                    "naive_watermark_coerced_utc" in codes))
                and numeric(age) and numeric(sla) and sla > 0 and age > sla)

    observations, unaffected = [], []
    for index, row in enumerate(rows):
        valid_identity = identified(row)
        if (valid_identity and row.get("state") == "healthy"
                and row.get("assessment_status") == "complete"):
            unaffected.append({"classification": None,
                               "disposition": "no_failure_observed",
                               "output": retained(row)})
            continue
        raw_codes = row.get("reason_codes")
        codes = sorted(set(raw_codes)) if (isinstance(raw_codes, list)
                    and all(isinstance(code, str) and code for code in raw_codes)) else []
        for code in codes or ["no_supported_reason"]:
            classification, eligibility, source, source_id = (
                "unclassified", "unsupported_or_insufficient_evidence", None, None)
            if not valid_identity:
                eligibility = "missing_ambiguous_or_mismatched_snapshot_identity"
            elif code == "content_parse_error":
                evidence = row.get("evidence")
                if isinstance(evidence, list) and any(
                    isinstance(item, Mapping) and item.get("plane") == "producer"
                    and item.get("source") == "content"
                    and isinstance(item.get("detail"), str)
                    and item["detail"] in parser_defects for item in evidence
                ):
                    classification, eligibility = "data_issue", "observed_content_parser_defect"
                else:
                    eligibility = "parse_code_does_not_establish_content_defect"
            elif code.startswith("required_input_stale:"):
                source_id = code.split(":", 1)[1]
                candidates = by_id.get(source_id, [])
                source = candidates[0] if len(candidates) == 1 else None
                required = row.get("required_inputs")
                links = [link for link in required if isinstance(link, Mapping)
                         and link.get("artifact_id") == source_id] if isinstance(required, list) else []
                if (row.get("dependency_bound") == "exact"
                        and row.get("state") == "stale"
                        and row.get("decided_by") == "dependency"
                        and len(links) == 1 and links[0].get("state") == "stale"
                        and source is not None and content_stale(source)
                        and links[0].get("assessment_status") == source.get("assessment_status")):
                    classification, eligibility = "stale_feature", "observed_required_input_content_sla_exceeded"
                else:
                    eligibility = "exact_required_input_content_clock_not_established"
            observations.append({
                "observation_id": f"{index}:{code}",
                "engine_id": row.get("engine_id"), "artifact_id": row.get("artifact_id"),
                "classification": classification, "reason_code": code,
                "eligibility": eligibility, "source_artifact_id": source_id,
                "output": retained(row), "source": retained(source) if source is not None else None,
            })
    grouped: dict[tuple[str, str, str | None], list[str]] = {}
    for item in observations:
        key = (item["classification"], item["reason_code"], item["source_artifact_id"])
        grouped.setdefault(key, []).append(item["observation_id"])
    groups = [{"classification": key[0], "reason_code": key[1],
               "source_artifact_id": key[2], "observation_ids": members,
               "observation_count": len(members), "count_unit": "health_observations"}
              for key, members in sorted(grouped.items(), key=lambda pair: (
                  pair[0][0], pair[0][1], pair[0][2] or ""))]
    return {
        "schema": "postmortem.source_findings.v1", "scope": "source_data_observations",
        "evaluation_status": "not_assessed", "observed_at": observed_at,
        "count_unit": "health_observations", "observation_unit": "output_reason_pair_in_supplied_snapshot",
        "observation_identity_scope": "this_snapshot_only", "n_outputs": len(rows),
        "unavailable_output_count": sum(row.get("state") == "unavailable" for row in rows),
        "unclassified_observation_count": sum(item["classification"] == "unclassified" for item in observations),
        "observations": observations, "groups": groups, "unaffected_outputs": unaffected,
    }
