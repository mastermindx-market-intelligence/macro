"""Pure point-in-time XNYS breadth semantics; no I/O or trading authority."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

UNIVERSE_OPERATING = "nyse_operating"
UNIVERSE_ALL_ISSUES = "nyse_all_issues"
OPERATING_TYPES = frozenset({"CS", "ADRC"})
SOURCE_RULES_VERSION = "exchange_breadth.xnys.v1"
AUTHORITY = "display_research_context_only"

OBSERVATION_COLUMNS = [
    "session", "universe_key", "entity_key", "security_id",
    "share_class_figi", "composite_figi", "ticker", "name",
    "ticker_type", "primary_exchange", "currency", "identity_source",
    "identity_resolved",
]
INTERVAL_COLUMNS = [
    "universe_key", "entity_key", "security_id", "share_class_figi",
    "composite_figi", "ticker", "name", "ticker_type",
    "primary_exchange", "currency", "valid_from_session",
    "valid_to_session", "source", "source_rules_version",
]

_MATCH_COLUMNS = [
    "universe_key", "entity_key", "security_id", "share_class_figi",
    "composite_figi", "ticker", "ticker_type", "primary_exchange", "currency",
]


@dataclass(frozen=True, slots=True)
class IdentityResolution:
    entity_key: str | None
    security_id: str | None
    source: str

    @property
    def resolved(self) -> bool:
        return self.entity_key is not None


@dataclass(frozen=True)
class EntityPanelResult:
    closes: pd.DataFrame
    excluded_entities: dict[str, dict[str, Any]]


def assess_universe_coverage(
    universe_key: str,
    *,
    listed_n: int,
    resolved_identity_n: int,
    priced_n: int | None,
    min_identity_coverage: float,
    min_price_coverage: float,
) -> dict[str, Any]:
    """Return transparent primary/comparator coverage status.

    ``nyse_operating`` is the required headline universe.  ``nyse_all_issues``
    is a comparator: it carries the same floors as disclosure thresholds, but
    falling below them marks that comparator partial rather than invalidating a
    healthy primary generation.
    """
    if universe_key not in {UNIVERSE_OPERATING, UNIVERSE_ALL_ISSUES}:
        raise ValueError(f"unsupported exchange-breadth universe: {universe_key}")
    listed = int(listed_n)
    resolved = int(resolved_identity_n)
    priced = None if priced_n is None else int(priced_n)
    identity_floor = float(min_identity_coverage)
    price_floor = float(min_price_coverage)
    if listed < 0 or resolved < 0 or (priced is not None and priced < 0):
        raise ValueError("coverage counts must be non-negative")
    if resolved > listed or (priced is not None and priced > resolved):
        raise ValueError("coverage numerators cannot exceed their denominators")
    if not 0.0 <= identity_floor <= 1.0 or not 0.0 <= price_floor <= 1.0:
        raise ValueError("coverage floors must be between zero and one")

    identity_ratio = resolved / listed if listed else 0.0
    price_ratio = priced / listed if priced is not None and listed else None
    reasons: list[str] = []
    if listed == 0:
        reasons.append("empty_universe")
    elif identity_ratio < identity_floor:
        reasons.append("identity_coverage_below_floor")
    if (
        priced is not None
        and listed
        and price_ratio is not None
        and price_ratio < price_floor
    ):
        reasons.append("price_coverage_below_floor")

    price_complete = priced is not None
    usable = price_complete and not reasons
    status = "accepted" if usable else ("partial" if reasons else "pending_price")
    return {
        "required": universe_key == UNIVERSE_OPERATING,
        "status": status,
        "usable": usable,
        "confirmation_eligible": usable,
        "identity_coverage_pct": round(identity_ratio * 100.0, 4),
        "price_coverage_pct": (
            round(price_ratio * 100.0, 4) if price_ratio is not None else None
        ),
        "identity_floor_pct": round(identity_floor * 100.0, 4),
        "price_floor_pct": round(price_floor * 100.0, 4),
        "meets_identity_floor": listed > 0 and identity_ratio >= identity_floor,
        "meets_price_floor": (
            None
            if priced is None
            else listed > 0 and price_ratio is not None and price_ratio >= price_floor
        ),
        "coverage_reasons": reasons,
    }


def _session(value: object) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts.normalize()


def _text(value: object, *, upper: bool = False) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.upper() if upper else text


def _active(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "active"}
    return bool(value)


def resolve_entity_identity(
    row: Mapping[str, Any], session: object, *, alias_table: Any | None = None,
) -> IdentityResolution:
    ticker = _text(row.get("ticker"))
    on: date = _session(session).date()
    if ticker and alias_table is not None:
        for vendor in ("massive", "membership"):
            security_id = alias_table.resolve(vendor, ticker, on)
            if security_id:
                sid = str(security_id)
                return IdentityResolution(sid, sid, "security_id")
    share_figi = _text(row.get("share_class_figi"), upper=True)
    if share_figi:
        return IdentityResolution(f"FIGI:{share_figi}", None, "share_class_figi")
    composite_figi = _text(row.get("composite_figi"), upper=True)
    if composite_figi:
        return IdentityResolution(f"CFIGI:{composite_figi}", None, "composite_figi")
    return IdentityResolution(None, None, "unresolved")


def normalize_roster(
    rows: Sequence[Mapping[str, Any]] | None,
    session: object,
    *,
    alias_table: Any | None = None,
) -> pd.DataFrame:
    """Return explicit operating and all-issues XNYS observations."""
    asof = _session(session)
    normalized: list[dict[str, Any]] = []
    for raw in rows or ():
        ticker = _text(raw.get("ticker"))
        exchange = _text(raw.get("primary_exchange"), upper=True)
        market = (_text(raw.get("market")) or "").lower()
        ticker_type = _text(raw.get("type"), upper=True) or "UNKNOWN"
        if not ticker or exchange != "XNYS" or market != "stocks":
            continue
        if not _active(raw.get("active")):
            continue
        ident = resolve_entity_identity(raw, asof, alias_table=alias_table)
        base = {
            "session": asof, "entity_key": ident.entity_key,
            "security_id": ident.security_id,
            "share_class_figi": _text(raw.get("share_class_figi"), upper=True),
            "composite_figi": _text(raw.get("composite_figi"), upper=True),
            "ticker": ticker, "name": _text(raw.get("name")) or ticker,
            "ticker_type": ticker_type, "primary_exchange": exchange,
            "currency": (
                _text(raw.get("currency_name"))
                or _text(raw.get("currency")) or "unknown"
            ).lower(),
            "identity_source": ident.source,
            "identity_resolved": ident.resolved,
        }
        all_row = dict(base, universe_key=UNIVERSE_ALL_ISSUES)
        normalized.append(all_row)
        if ticker_type in OPERATING_TYPES:
            normalized.append(dict(base, universe_key=UNIVERSE_OPERATING))
    if not normalized:
        return pd.DataFrame(columns=OBSERVATION_COLUMNS)
    out = pd.DataFrame(normalized).reindex(columns=OBSERVATION_COLUMNS)
    return out.sort_values(
        ["universe_key", "ticker"], kind="stable"
    ).reset_index(drop=True)


def _same(left: object, right: object) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    return left == right


def update_membership_intervals(
    existing: pd.DataFrame | None,
    observed: pd.DataFrame | None,
    session: object,
    *,
    previous_session: object | None,
    last_observed_session: object | None,
    source: str = "massive_reference_tickers",
    source_rules_version: str = SOURCE_RULES_VERSION,
) -> pd.DataFrame:
    """Extend only when the canonical prior session was fully observed."""
    asof = _session(session)
    previous = _session(previous_session) if previous_session is not None else None
    last_seen = (
        _session(last_observed_session)
        if last_observed_session is not None else None
    )
    contiguous = previous is not None and previous == last_seen
    if existing is None or existing.empty:
        ledger = pd.DataFrame(columns=INTERVAL_COLUMNS)
    else:
        ledger = existing.copy().reindex(columns=INTERVAL_COLUMNS)
        for col in ("valid_from_session", "valid_to_session"):
            ledger[col] = pd.to_datetime(
                ledger[col], errors="coerce"
            ).dt.tz_localize(None).dt.normalize()
    if observed is None or observed.empty:
        return ledger.reset_index(drop=True)
    current = observed[
        observed["entity_key"].notna()
        & observed["identity_resolved"].fillna(False)
    ].copy()
    if current.empty:
        return ledger.reset_index(drop=True)
    current["session"] = pd.to_datetime(
        current["session"], errors="coerce"
    ).dt.tz_localize(None).dt.normalize()
    if not (current["session"] == asof).all():
        raise ValueError("observed roster session does not match update session")
    current = current.drop_duplicates(
        ["universe_key", "entity_key", "ticker"], keep="last"
    )
    additions: list[dict[str, Any]] = []
    for rec in current.to_dict("records"):
        extended = False
        if contiguous and not ledger.empty:
            candidate = ledger[ledger["valid_to_session"] == previous]
            for col in _MATCH_COLUMNS:
                expected = rec.get(col)
                candidate = candidate[
                    candidate[col].map(lambda value, target=expected: _same(value, target))
                ]
                if candidate.empty:
                    break
            if len(candidate) > 1:
                raise ValueError("ambiguous open membership interval")
            if len(candidate) == 1:
                idx = candidate.index[0]
                ledger.loc[idx, "valid_to_session"] = asof
                ledger.loc[idx, "name"] = rec.get("name") or ledger.loc[idx, "name"]
                extended = True
        if not extended:
            additions.append({
                "universe_key": rec.get("universe_key"),
                "entity_key": rec.get("entity_key"),
                "security_id": rec.get("security_id"),
                "share_class_figi": rec.get("share_class_figi"),
                "composite_figi": rec.get("composite_figi"),
                "ticker": rec.get("ticker"), "name": rec.get("name"),
                "ticker_type": rec.get("ticker_type"),
                "primary_exchange": rec.get("primary_exchange"),
                "currency": rec.get("currency"),
                "valid_from_session": asof, "valid_to_session": asof,
                "source": source,
                "source_rules_version": source_rules_version,
            })
    if additions:
        ledger = pd.concat([
            ledger, pd.DataFrame(additions, columns=INTERVAL_COLUMNS)
        ], ignore_index=True)
    return ledger.sort_values([
        "universe_key", "entity_key", "valid_from_session", "ticker"
    ], kind="stable").reset_index(drop=True)


def _series(raw: pd.Series) -> pd.Series:
    out = pd.to_numeric(raw.copy(), errors="coerce")
    idx = pd.to_datetime(out.index, errors="raise")
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    out.index = idx.normalize()
    if out.index.has_duplicates:
        raise ValueError("close series contains duplicate sessions")
    return out.sort_index()


def _split_events(events: pd.DataFrame | None, observation: object) -> pd.DataFrame:
    columns = ["execution_date", "split_from", "split_to"]
    if events is None or events.empty:
        return pd.DataFrame(columns=columns)
    missing = set(columns) - set(events.columns)
    if missing:
        raise ValueError(f"split events missing columns: {sorted(missing)}")
    out = events.copy()
    out["execution_date"] = pd.to_datetime(out["execution_date"], errors="raise")
    if out["execution_date"].dt.tz is not None:
        out["execution_date"] = (
            out["execution_date"].dt.tz_convert("UTC").dt.tz_localize(None)
        )
    out["execution_date"] = out["execution_date"].dt.normalize()
    out["split_from"] = pd.to_numeric(out["split_from"], errors="coerce")
    out["split_to"] = pd.to_numeric(out["split_to"], errors="coerce")
    valid = (
        np.isfinite(out["split_from"]) & np.isfinite(out["split_to"])
        & (out["split_from"] > 0) & (out["split_to"] > 0)
    )
    if not bool(valid.all()):
        raise ValueError("split ratios must be finite and strictly positive")
    out = out[out["execution_date"] <= _session(observation)].copy()
    if out["execution_date"].duplicated().any():
        raise ValueError("duplicate split execution date")
    return out.sort_values("execution_date", kind="stable").reset_index(drop=True)


def adjust_raw_close_series(
    raw: pd.Series,
    split_events: pd.DataFrame | None,
    observation_session: object,
) -> pd.Series:
    """Restate only pre-execution bars onto the observation share basis."""
    adjusted = _series(raw)
    for event in _split_events(split_events, observation_session).itertuples(
        index=False
    ):
        ratio = float(event.split_from) / float(event.split_to)
        adjusted.loc[adjusted.index < event.execution_date] *= ratio
    adjusted.name = raw.name
    return adjusted


def find_split_like_seams(
    series: pd.Series, *, lower_ratio: float = 0.60, upper_ratio: float = 1.65,
) -> list[pd.Timestamp]:
    if lower_ratio <= 0 or lower_ratio >= 1 or upper_ratio <= 1:
        raise ValueError("seam ratio bounds must straddle 1")
    clean = _series(series).dropna()
    if len(clean) < 2:
        return []
    ratio = clean / clean.shift(1)
    mask = ((ratio < lower_ratio) | (ratio > upper_ratio)).fillna(False)
    return [pd.Timestamp(ts) for ts in ratio.index[mask]]


def assemble_entity_close_panel(
    price_by_ticker: Mapping[str, pd.Series],
    intervals: pd.DataFrame,
    *,
    split_events: pd.DataFrame | None,
    observation_session: object,
    universe_key: str,
    detect_seams: bool = True,
) -> EntityPanelResult:
    """Join ticker histories through identity intervals; never splice reuse."""
    asof = _session(observation_session)
    if intervals is None or intervals.empty:
        return EntityPanelResult(pd.DataFrame(), {})
    work = intervals[
        (intervals["universe_key"] == universe_key)
        & intervals["entity_key"].notna()
    ].copy()
    if work.empty:
        return EntityPanelResult(pd.DataFrame(), {})
    for col in ("valid_from_session", "valid_to_session"):
        work[col] = pd.to_datetime(work[col], errors="raise").dt.tz_localize(None)
        work[col] = work[col].dt.normalize()
    work = work[work["valid_from_session"] <= asof]
    work["valid_to_session"] = work["valid_to_session"].clip(upper=asof)
    prices: dict[str, pd.Series] = {
        str(ticker).strip().upper(): _series(series)
        for ticker, series in price_by_ticker.items()
    }
    indexes = [s.index[s.index <= asof] for s in prices.values()]
    if not indexes:
        return EntityPanelResult(pd.DataFrame(), {})
    all_index = indexes[0]
    for idx in indexes[1:]:
        all_index = all_index.union(idx)
    all_index = all_index.sort_values()
    accepted: dict[str, pd.Series] = {}
    excluded: dict[str, dict[str, Any]] = {}
    for entity, group in work.groupby("entity_key", sort=True):
        combined = pd.Series(np.nan, index=all_index, dtype=float, name=str(entity))
        conflicts: list[str] = []
        for row in group.sort_values(
            ["valid_from_session", "ticker"]
        ).itertuples(index=False):
            source = prices.get(str(row.ticker).strip().upper())
            if source is None:
                continue
            end = min(pd.Timestamp(row.valid_to_session), asof)
            segment = source[
                (source.index >= row.valid_from_session) & (source.index <= end)
            ].dropna()
            overlap = combined.loc[segment.index].notna()
            if overlap.any():
                old = combined.loc[segment.index[overlap]].astype(float)
                new = segment.loc[overlap].astype(float)
                bad = ~np.isclose(old.values, new.values, rtol=1e-9, atol=1e-12)
                conflicts.extend(ts.strftime("%Y-%m-%d") for ts in old.index[bad])
            combined.loc[segment.index] = segment.values
        if conflicts:
            excluded[str(entity)] = {
                "reason": "conflicting_interval_prices",
                "dates": sorted(set(conflicts)),
            }
            continue
        events = split_events
        if (
            split_events is not None and not split_events.empty
            and "entity_key" in split_events.columns
        ):
            events = split_events[
                split_events["entity_key"].astype(str) == str(entity)
            ]
        adjusted = adjust_raw_close_series(combined, events, asof)
        seams = find_split_like_seams(adjusted) if detect_seams else []
        if seams:
            excluded[str(entity)] = {
                "reason": "unmatched_split_like_seam",
                "dates": [ts.strftime("%Y-%m-%d") for ts in seams],
            }
            continue
        if adjusted.notna().any():
            accepted[str(entity)] = adjusted
    return EntityPanelResult(
        pd.DataFrame(accepted, index=all_index).sort_index(), excluded
    )


def _membership(closes: pd.DataFrame, membership: pd.DataFrame | None) -> pd.DataFrame:
    if membership is None:
        return closes.notna()
    return membership.reindex(
        index=closes.index, columns=closes.columns
    ).fillna(False).astype(bool)


def _percent(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    den = pd.to_numeric(denominator, errors="coerce")
    num = pd.to_numeric(numerator, errors="coerce")
    return (100.0 * num / den.where(den > 0)).astype(float)


def compute_breadth_history(
    closes: pd.DataFrame,
    *,
    membership: pd.DataFrame | None = None,
    listed_counts: pd.Series | None = None,
    ma_windows: Sequence[int] = (20, 50, 200),
    nhnl_window: int = 252,
) -> pd.DataFrame:
    """Compute prior-window NH/NL and participation from adjusted closes."""
    if closes is None or closes.empty:
        return pd.DataFrame()
    if nhnl_window < 1:
        raise ValueError("nhnl_window must be positive")
    windows = tuple(dict.fromkeys(int(window) for window in ma_windows))
    if any(window < 1 for window in windows):
        raise ValueError("moving-average windows must be positive")
    frame = closes.copy().sort_index().apply(pd.to_numeric, errors="coerce")
    frame.index = pd.to_datetime(frame.index)
    if frame.index.tz is not None:
        frame.index = frame.index.tz_convert("UTC").tz_localize(None)
    frame.index = frame.index.normalize()
    eligible_mask = _membership(frame, membership)
    eligible = frame.where(eligible_mask)
    resolved = eligible_mask.sum(axis=1).astype(int)
    listed = resolved if listed_counts is None else pd.to_numeric(
        listed_counts.reindex(frame.index), errors="coerce"
    )
    priced = eligible.notna().sum(axis=1).astype(int)
    out = pd.DataFrame(index=frame.index)
    out["listed_n"] = listed
    out["resolved_identity_n"] = resolved
    out["priced_n"] = priced
    changes = eligible.diff()
    comparable = eligible.notna() & eligible.shift(1).notna() & eligible_mask
    adv = ((changes > 0) & comparable).sum(axis=1).astype(int)
    dec = ((changes < 0) & comparable).sum(axis=1).astype(int)
    unch = ((changes == 0) & comparable).sum(axis=1).astype(int)
    out["adv"], out["dec"], out["unch"] = adv, dec, unch
    out["adv_pct"] = _percent(adv, adv + dec)
    for window in windows:
        average = eligible.rolling(window, min_periods=window).mean()
        denominator_mask = eligible_mask & eligible.notna() & average.notna()
        denominator = denominator_mask.sum(axis=1)
        above = ((eligible > average) & denominator_mask).sum(axis=1)
        out[f"pct_above_{window}"] = _percent(above, denominator)
    prior = eligible.shift(1)
    prior_count = prior.rolling(
        nhnl_window, min_periods=nhnl_window
    ).count()
    prior_high = prior.rolling(
        nhnl_window, min_periods=nhnl_window
    ).max()
    prior_low = prior.rolling(
        nhnl_window, min_periods=nhnl_window
    ).min()
    seasoned_mask = (
        eligible_mask & eligible.notna() & (prior_count >= nhnl_window)
    )
    new_high = seasoned_mask & (eligible >= prior_high)
    new_low = seasoned_mask & (eligible <= prior_low)
    seasoned = seasoned_mask.sum(axis=1).astype(int)
    nh = new_high.sum(axis=1).astype(int)
    nl = new_low.sum(axis=1).astype(int)
    both = (new_high & new_low).sum(axis=1).astype(int)
    net = nh - nl
    out["seasoned_n"] = seasoned
    out["nh"], out["nl"], out["both_extremes"] = nh, nl, both
    out["nh_pct"] = _percent(nh, seasoned)
    out["nl_pct"] = _percent(nl, seasoned)
    out["net_nh"] = net
    out["net_nh_pct"] = _percent(net, seasoned)
    out["high_low_index"] = _percent(nh, nh + nl)
    out["ad_line"] = (adv - dec).cumsum()
    out["high_low_line"] = net.cumsum()
    out["coverage_pct"] = _percent(priced, listed)
    out["seasoned_pct"] = _percent(seasoned, listed)
    return out


def classify_breadth_state(
    frame: pd.DataFrame,
    *,
    price: pd.Series | None = None,
    asof: object | None = None,
    lookback: int = 20,
) -> dict[str, Any]:
    """Return one transparent, causal descriptive state."""
    unavailable = {
        "state": "unavailable", "tone": "muted",
        "reasons": ["breadth history unavailable"],
        "asof": None, "authority": AUTHORITY,
    }
    if frame is None or frame.empty:
        return unavailable
    if lookback < 1:
        raise ValueError("lookback must be positive")
    hist = frame.sort_index().copy()
    hist.index = pd.to_datetime(hist.index)
    if asof is not None:
        hist = hist[hist.index <= _session(asof)]
    if hist.empty:
        return dict(unavailable)
    required = {
        "adv_pct", "pct_above_50", "net_nh_pct", "nh_pct", "nl_pct"
    }
    missing = sorted(required - set(hist.columns))
    if missing:
        raise ValueError(f"breadth state frame missing columns: {missing}")
    latest = hist.iloc[-1]
    anchor = hist.iloc[-(lookback + 1)] if len(hist) > lookback else hist.iloc[0]
    pa50 = float(latest["pct_above_50"])
    adv_pct = float(latest["adv_pct"])
    net = float(latest["net_nh_pct"])
    nh_pct = float(latest["nh_pct"])
    nl_pct = float(latest["nl_pct"])
    pa50_change = pa50 - float(anchor["pct_above_50"])
    price_at_high = False
    if price is not None:
        px = pd.to_numeric(price.sort_index(), errors="coerce")
        px.index = pd.to_datetime(px.index)
        px = px[px.index <= hist.index[-1]].dropna()
        if not px.empty:
            tail = px.tail(lookback + 1)
            price_at_high = bool(tail.iloc[-1] >= tail.max())
    reasons: list[str] = []
    if nh_pct >= 4.0 and nl_pct >= 4.0:
        state, tone = "fragmentation", "warn"
        reasons.append("new-high and new-low intensity are both elevated")
    elif nl_pct >= 8.0 and net <= -5.0 and pa50 <= 35.0:
        state, tone = "washout", "neg"
        reasons.extend([
            "new-low intensity is extreme",
            "participation is deeply compressed",
        ])
    else:
        prior = hist.iloc[:-1].tail(lookback)
        prior_washout = bool(
            not prior.empty
            and (
                (pd.to_numeric(prior["nl_pct"], errors="coerce") >= 8.0)
                & (pd.to_numeric(
                    prior["net_nh_pct"], errors="coerce"
                ) <= -5.0)
            ).any()
        )
        if (
            prior_washout and adv_pct >= 60.0
            and net >= 3.0 and pa50_change >= 8.0
        ):
            state, tone = "recovery_thrust", "pos"
            reasons.extend([
                "breadth rebounded after a recent washout",
                "participation expanded sharply",
            ])
        elif price_at_high and (
            net < 0.0 or pa50_change <= -5.0 or pa50 < 50.0
        ):
            state, tone = "narrowing", "neg"
            reasons.append(
                "price is at a recent high without breadth confirmation"
            )
            if net < 0:
                reasons.append("new lows exceed new highs")
            if pa50_change <= -5:
                reasons.append("50-day participation deteriorated")
        elif (
            adv_pct >= 55.0 and net > 0.0 and pa50 >= 60.0
            and nh_pct > nl_pct
        ):
            state, tone = "broad_confirmation", "pos"
            reasons.extend([
                "advancers hold the majority",
                "new highs exceed new lows",
                "50-day participation is broad",
            ])
        elif pa50_change >= 5.0 and net > 0.0 and adv_pct >= 52.0:
            state, tone = "broadening", "pos"
            reasons.extend([
                "participation improved", "new highs exceed new lows"
            ])
        else:
            state, tone = "mixed", "muted"
            reasons.append("breadth components do not agree strongly")
    return {
        "state": state,
        "tone": tone,
        "reasons": reasons,
        "asof": pd.Timestamp(hist.index[-1]).strftime("%Y-%m-%d"),
        "authority": AUTHORITY,
        "components": {
            "adv_pct": round(adv_pct, 2),
            "pct_above_50": round(pa50, 2),
            "pct_above_50_change": round(pa50_change, 2),
            "net_nh_pct": round(net, 2),
            "nh_pct": round(nh_pct, 2),
            "nl_pct": round(nl_pct, 2),
            "price_at_recent_high": price_at_high,
        },
    }
