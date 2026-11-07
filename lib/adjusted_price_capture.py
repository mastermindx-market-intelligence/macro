"""Value-only fixed four-field and genuine five-field adjusted capture/merge.

This is shared validation for the incumbent breadth and basket acquisition
owners. It performs no provider, config, path, clock, publication or store I/O.
It does not establish a verified generation or authorize a legacy writer transfer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import numpy as np
import pandas as pd

FIELDS = ("close", "high", "low", "volume")
OHLCV_FIELDS = ("open", "high", "low", "close", "volume")
PRICES = FIELDS[:-1]
MAX_ROWS = 50_000
MAX_COLUMNS = 5_000
MAX_PANEL_CELLS = 5_000_000


class AdjustedCaptureError(ValueError):
    pass


@dataclass(frozen=True)
class AdjustedPriceCapture:
    panels: Mapping[str, pd.DataFrame]
    spans: Mapping[str, tuple[pd.Timestamp, pd.Timestamp]]
    requested: tuple[str, ...]


@dataclass(frozen=True)
class AdjustedMerge:
    panels: Mapping[str, pd.DataFrame]
    needs_repair: tuple[str, ...]
    repaired: tuple[str, ...]
    unresolved: tuple[str, ...]
    current: tuple[str, ...]
    reasons: Mapping[str, str]


def empty_panel() -> pd.DataFrame:
    return pd.DataFrame(index=pd.DatetimeIndex([], name="Date"))


def _capture_panel_values(frame: pd.DataFrame, *, field: str,
                          allow_price_placeholders: bool = False) -> np.ndarray:
    """One scalar validator, including before the incumbent placeholder scrub."""
    for name in frame.columns:
        column = frame[name]
        if (not pd.api.types.is_numeric_dtype(column) or pd.api.types.is_bool_dtype(column)
                or pd.api.types.is_complex_dtype(column)):
            raise AdjustedCaptureError("invalid_adjusted_value")
    try:
        values = frame.to_numpy(dtype=float, na_value=np.nan)
    except (TypeError, ValueError):
        raise AdjustedCaptureError("invalid_adjusted_value") from None
    present = ~np.isnan(values)
    if (not np.isfinite(values[present]).all()
            or (field == "volume" and (values[present] < 0).any())
            or (field != "volume" and not allow_price_placeholders
                and (values[present] <= 0).any())):
        raise AdjustedCaptureError("invalid_adjusted_value")
    return values


def validate_ohlcv_geometry(panels: Mapping[str, pd.DataFrame]) -> None:
    """Reject impossible observed OHLC pairs without aligning away archive axes."""
    for upper, lower in (("high", "open"), ("high", "close"), ("high", "low"),
                         ("open", "low"), ("close", "low")):
        high, low = panels[upper].align(panels[lower], join="inner")
        observed = high.notna() & low.notna()
        if ((high < low) & observed).to_numpy().any():
            raise AdjustedCaptureError("invalid_ohlcv_geometry")


def _capture_panels(panels: Mapping[str, Any], *, fields: tuple[str, ...], source_session: str,
                    allow_absent: bool = False) -> dict[str, pd.DataFrame]:
    """Validate/detach supplied matrices without sorting or repairing them."""
    from lib import market_session
    if not isinstance(panels, Mapping) or set(panels) != set(fields):
        raise AdjustedCaptureError("exact_adjusted_fields_required")
    try:
        if not isinstance(source_session, str) or date.fromisoformat(source_session).isoformat() != source_session:
            raise ValueError
        target = pd.Timestamp(source_session)
    except (TypeError, ValueError):
        raise AdjustedCaptureError("invalid_source_session") from None
    output = {}
    checked_indices = set()
    for field in fields:
        frame = panels[field]
        if frame is None and allow_absent:
            frame = empty_panel()
        if (not isinstance(frame, pd.DataFrame) or len(frame) > MAX_ROWS or frame.size > MAX_PANEL_CELLS
                or len(frame.columns) > MAX_COLUMNS or frame.columns.has_duplicates
                or not isinstance(frame.index, pd.DatetimeIndex) or frame.index.hasnans
                or frame.index.has_duplicates or not frame.index.is_monotonic_increasing
                or frame.index.tz is not None or not frame.index.equals(frame.index.normalize())
                or any(not isinstance(t, str) or not t or len(t) > 24 for t in frame.columns)):
            raise AdjustedCaptureError("invalid_adjusted_panel")
        if len(frame) and frame.index[-1] > target:
            raise AdjustedCaptureError("future_prior_or_capture")
        index_key = tuple(frame.index)
        if index_key not in checked_indices:
            if any(not market_session.is_session_date("US", stamp.date()) for stamp in frame.index):
                raise AdjustedCaptureError("non_session_observation")
            checked_indices.add(index_key)
        values = _capture_panel_values(frame, field=field)
        copied = pd.DataFrame(values, index=frame.index.copy(), columns=frame.columns.copy())
        copied.index = copied.index.as_unit("ns")
        output[field] = copied
    if fields == OHLCV_FIELDS:
        validate_ohlcv_geometry(output)
    return output


def capture_panels(panels: Mapping[str, Any], *, source_session: str,
                   allow_absent: bool = False) -> dict[str, pd.DataFrame]:
    return _capture_panels(panels, fields=FIELDS, source_session=source_session, allow_absent=allow_absent)


def capture_close_panel(panel: Any, *, source_session: str, allow_absent: bool = False) -> pd.DataFrame:
    """Apply the same scalar/date/bounds contract to an actual close-only owner."""
    return _capture_panels({"close": panel}, fields=("close",), source_session=source_session,
                           allow_absent=allow_absent)["close"]


def _capture_adjusted_response(frame: Any, *, requested: tuple[str, ...],
                              source_session: str, fields: tuple[str, ...]) -> AdjustedPriceCapture:
    """Extract one actual group_by=column, auto_adjust=True provider response."""
    if (not requested or len(set(requested)) != len(requested)
            or not isinstance(frame, pd.DataFrame) or frame.empty
            or not isinstance(frame.index, pd.DatetimeIndex) or frame.columns.has_duplicates
            or frame.index.has_duplicates or not frame.index.is_monotonic_increasing
            or frame.index.hasnans or frame.index.tz is not None
            or not frame.index.equals(frame.index.normalize()) or len(frame) > MAX_ROWS):
        raise AdjustedCaptureError("invalid_adjusted_response")
    target = pd.Timestamp(source_session)
    # The caller explicitly requests completed observations. An in-progress
    # provider tail is excluded here, before it contributes to spans/coverage.
    raw = frame.loc[frame.index <= target]
    if raw.empty:
        raise AdjustedCaptureError("no_completed_observations")
    columns = raw.columns
    multi = isinstance(columns, pd.MultiIndex)
    if (multi and columns.nlevels != 2) or (not multi and len(requested) != 1):
        raise AdjustedCaptureError("ambiguous_adjusted_symbols")
    if multi and (not set(columns.get_level_values(1)).issubset(requested)):
        raise AdjustedCaptureError("unexpected_adjusted_symbol")
    level0 = columns.get_level_values(0) if multi else columns
    if "Close" not in level0:
        raise AdjustedCaptureError("adjusted_close_missing")
    panels = {}
    for field in fields:
        vendor_field = field.title()
        if vendor_field not in level0:
            values = pd.DataFrame(np.nan, index=raw.index, columns=requested)
        else:
            values = raw[vendor_field]
            if isinstance(values, pd.Series):
                values = values.to_frame(requested[0])
            if (values.columns.has_duplicates or not set(values.columns).issubset(requested)):
                raise AdjustedCaptureError("ambiguous_adjusted_symbols")
            values = values.reindex(columns=requested)
        panels[field] = values
    panels = _capture_panels(panels, fields=fields, source_session=source_session)
    spans = {ticker: (panels["close"].index[0], panels["close"].index[-1])
             for ticker in requested if panels["close"][ticker].notna().any()}
    return AdjustedPriceCapture(MappingProxyType(panels), MappingProxyType(spans), requested)


def _combine_adjusted_captures(captures: list[AdjustedPriceCapture], *,
                              requested: tuple[str, ...], fields: tuple[str, ...]) -> AdjustedPriceCapture:
    spans = {}
    for capture in captures:
        if set(capture.spans) & set(spans):
            raise AdjustedCaptureError("duplicate_adjusted_batch_symbol")
        spans.update(capture.spans)
    panels = {}
    for field in fields:
        parts = [capture.panels[field] for capture in captures]
        panels[field] = pd.concat(parts, axis=1).sort_index() if parts else empty_panel()
        if panels[field].columns.has_duplicates:
            raise AdjustedCaptureError("duplicate_adjusted_batch_symbol")
    return AdjustedPriceCapture(MappingProxyType(panels), MappingProxyType(spans), requested)


def _remap_adjusted_capture(capture: AdjustedPriceCapture, *, canonical_to_vendor: Mapping[str, str], fields: tuple[str, ...]) -> AdjustedPriceCapture:
    if len(set(canonical_to_vendor.values())) != len(canonical_to_vendor):
        raise AdjustedCaptureError("vendor_alias_collision")
    inverse = {vendor: canonical for canonical, vendor in canonical_to_vendor.items()}
    if set(capture.requested) != set(inverse):
        raise AdjustedCaptureError("adjusted_request_identity_changed")
    return AdjustedPriceCapture(
        MappingProxyType({field: capture.panels[field].rename(columns=inverse).copy(deep=True) for field in fields}),
        MappingProxyType({inverse[ticker]: span for ticker, span in capture.spans.items()}),
        tuple(canonical_to_vendor))


def _validated_capture(value: AdjustedPriceCapture, *, source_session: str,
                       allowed: tuple[str, ...], fields: tuple[str, ...] = FIELDS) -> AdjustedPriceCapture:
    if (not isinstance(value, AdjustedPriceCapture) or not isinstance(value.spans, Mapping)
            or len(set(value.requested)) != len(value.requested)
            or not set(value.requested).issubset(allowed)
            or not set(value.spans).issubset(value.requested)):
        raise AdjustedCaptureError("invalid_adjusted_capture")
    panels = _capture_panels(value.panels, fields=fields, source_session=source_session)
    spans = {}
    for ticker, span in value.spans.items():
        if (not isinstance(span, tuple) or len(span) != 2
                or not all(isinstance(stamp, pd.Timestamp) for stamp in span)):
            raise AdjustedCaptureError("invalid_fresh_span")
        start, end = span
        if (start.tz is not None or end.tz is not None or start != start.normalize()
                or end != end.normalize() or start > end or end > pd.Timestamp(source_session)):
            raise AdjustedCaptureError("invalid_fresh_span")
        if any(ticker not in panel.columns or start not in panel.index or end not in panel.index
               for panel in panels.values()):
            raise AdjustedCaptureError("invalid_fresh_span")
        for panel in panels.values():
            observed = panel[ticker].dropna()
            if len(observed) and (observed.index[0] < start or observed.index[-1] > end):
                raise AdjustedCaptureError("observations_outside_fresh_span")
        spans[ticker] = (start, end)
    if any(not set(panel.columns).issubset(value.requested) for panel in panels.values()):
        raise AdjustedCaptureError("unexpected_adjusted_symbol")
    return AdjustedPriceCapture(MappingProxyType(panels), MappingProxyType(spans), tuple(value.requested))


def _merge_adjusted_capture(*, fields: tuple[str, ...], prior: Mapping[str, Any], fresh: AdjustedPriceCapture,
                          active: tuple[str, ...], source_session: str,
                          basis_tolerance: float, minimum_repair_sessions: int,
                          residual_suspects: tuple[str, ...] = (),
                          repair: AdjustedPriceCapture | None = None,
                          full_replacement: bool = False,
                          allow_historical_replacement: bool = False) -> AdjustedMerge:
    """A fresh span owns its nulls/gaps; a repair owns every required whole column.

    Unresolved repairs retain original prior columns, never a partly updated
    adjustment basis. Retained or departed observations do not count as current.
    """
    from lib import store
    if (type(allow_historical_replacement) is not bool
            or (allow_historical_replacement and not full_replacement)):
        raise AdjustedCaptureError("historical_replacement_requires_full_request")
    if (not active or len(set(active)) != len(active)
            or type(minimum_repair_sessions) is not int or minimum_repair_sessions < 1
            or type(basis_tolerance) not in (int, float) or not np.isfinite(basis_tolerance)
            or not 0 <= basis_tolerance < 1 or not set(residual_suspects).issubset(active)):
        raise AdjustedCaptureError("invalid_adjusted_merge_policy")
    previous = _capture_panels(prior, fields=fields, source_session=source_session, allow_absent=True)
    initial = _validated_capture(fresh, source_session=source_session, allowed=active, fields=fields)
    replacement = _validated_capture(repair, source_session=source_session, allowed=active, fields=fields) if repair is not None else None
    if full_replacement:
        replacement = initial
    index = pd.DatetimeIndex([])
    columns = set(active)
    for collection in (previous, initial.panels, replacement.panels if replacement is not None else {}):
        for panel in collection.values():
            index = index.union(panel.index)
            columns.update(panel.columns)
    index = index.sort_values().as_unit("ns")
    columns = sorted(columns)
    if len(index) > MAX_ROWS or len(columns) > MAX_COLUMNS or len(index) * len(columns) > MAX_PANEL_CELLS:
        raise AdjustedCaptureError("adjusted_union_bound")
    merged = {field: panel.reindex(index=index, columns=columns).copy(deep=True)
              for field, panel in previous.items()}
    reasons = {}
    target = pd.Timestamp(source_session)
    for ticker in active:
        if full_replacement:
            reasons[ticker] = "full_history_request"
        elif ticker not in initial.spans:
            reasons[ticker] = "not_returned"
        else:
            start, end = initial.spans[ticker]
            mask = (index >= start) & (index <= end)
            for field in fields:
                merged[field].loc[mask, ticker] = initial.panels[field][ticker].reindex(index[mask])
            for field in (field for field in fields if field != "volume"):
                old = previous[field][ticker].dropna() if ticker in previous[field] else pd.Series(dtype=float)
                new = initial.panels[field][ticker].dropna()
                comparison = store.compare_basis(old.to_frame("close"), new.to_frame("close"),
                    strict=True, tol=basis_tolerance)
                if comparison.status != store.BASIS_ALIGNED or comparison.overlap_dates < 3:
                    reasons[ticker] = "basis_unqualified"
                    break
            if end != target or any(target not in initial.panels[field].index
                    or pd.isna(initial.panels[field].at[target, ticker]) for field in fields):
                reasons.setdefault(ticker, "target_incomplete")
            jointly_observed = pd.concat([merged[field][ticker] for field in fields], axis=1).notna().all(axis=1)
            if int(jointly_observed.sum()) < minimum_repair_sessions:
                reasons.setdefault(ticker, "history_insufficient")
        if ticker in residual_suspects:
            reasons[ticker] = "residual_seam"
    needed = tuple(ticker for ticker in active if ticker in reasons)
    repaired = []
    unresolved = []
    for ticker in needed:
        qualified = replacement is not None and ticker in replacement.spans
        replacement_tip = None
        if qualified:
            common_dates = None
            for field in fields:
                values = replacement.panels[field][ticker].dropna()
                old = previous[field][ticker].dropna() if ticker in previous[field] else pd.Series(dtype=float)
                common_dates = values.index if common_dates is None else common_dates.intersection(values.index)
                if (len(values) < max(minimum_repair_sessions, len(old))
                        or (not allow_historical_replacement and values.index[-1] != target)
                        or (len(old) and (values.index[0] > old.index[0]
                                          or not old.index.isin(values.index).all()))):
                    qualified = False
                    break
                if replacement_tip is None:
                    replacement_tip = values.index[-1]
                elif allow_historical_replacement and values.index[-1] != replacement_tip:
                    qualified = False
                    break
            required_tip = replacement_tip if allow_historical_replacement else target
            if qualified and (len(common_dates) < minimum_repair_sessions
                    or required_tip not in common_dates or required_tip > target):
                qualified = False
        if qualified:
            if allow_historical_replacement and replacement_tip < target:
                reasons[ticker] = "historical_only"
            for field in fields:
                merged[field][ticker] = replacement.panels[field][ticker].reindex(index)
            repaired.append(ticker)
        else:
            for field in fields:
                merged[field][ticker] = (previous[field][ticker].reindex(index)
                    if ticker in previous[field] else np.nan)
            unresolved.append(ticker)
    observed = set(initial.spans) | set(repaired)
    current = tuple(ticker for ticker in active if ticker in observed and ticker not in unresolved
        and all(target in merged[field].index and pd.notna(merged[field].at[target, ticker]) for field in fields))
    return AdjustedMerge(MappingProxyType(merged), needed, tuple(repaired), tuple(unresolved),
                         current, MappingProxyType(reasons))


def capture_ohlcv_panels(panels: Mapping[str, Any], *, source_session: str,
                         allow_absent: bool = False) -> dict[str, pd.DataFrame]:
    """Capture genuine Open/High/Low/Close/Volume; no field substitution."""
    return _capture_panels(panels, fields=OHLCV_FIELDS, source_session=source_session,
                           allow_absent=allow_absent)


def capture_adjusted_response(frame: Any, *, requested: tuple[str, ...],
                              source_session: str) -> AdjustedPriceCapture:
    return _capture_adjusted_response(frame, requested=requested,
        source_session=source_session, fields=FIELDS)


def capture_adjusted_ohlcv_response(frame: Any, *, requested: tuple[str, ...],
                                    source_session: str) -> AdjustedPriceCapture:
    return _capture_adjusted_response(frame, requested=requested,
        source_session=source_session, fields=OHLCV_FIELDS)


def combine_adjusted_captures(captures: list[AdjustedPriceCapture], *,
                              requested: tuple[str, ...]) -> AdjustedPriceCapture:
    return _combine_adjusted_captures(captures, requested=requested, fields=FIELDS)


def combine_adjusted_ohlcv_captures(captures: list[AdjustedPriceCapture], *,
                                    requested: tuple[str, ...]) -> AdjustedPriceCapture:
    return _combine_adjusted_captures(captures, requested=requested, fields=OHLCV_FIELDS)


def remap_adjusted_capture(capture: AdjustedPriceCapture, *,
                           canonical_to_vendor: Mapping[str, str]) -> AdjustedPriceCapture:
    return _remap_adjusted_capture(capture, canonical_to_vendor=canonical_to_vendor,
                                   fields=FIELDS)


def remap_adjusted_ohlcv_capture(capture: AdjustedPriceCapture, *,
                                 canonical_to_vendor: Mapping[str, str]) -> AdjustedPriceCapture:
    return _remap_adjusted_capture(capture, canonical_to_vendor=canonical_to_vendor,
                                   fields=OHLCV_FIELDS)


def merge_adjusted_capture(*, prior: Mapping[str, Any], fresh: AdjustedPriceCapture,
                          active: tuple[str, ...], source_session: str,
                          basis_tolerance: float, minimum_repair_sessions: int,
                          residual_suspects: tuple[str, ...] = (),
                          repair: AdjustedPriceCapture | None = None,
                          full_replacement: bool = False) -> AdjustedMerge:
    return _merge_adjusted_capture(fields=FIELDS, prior=prior, fresh=fresh,
        active=active, source_session=source_session, basis_tolerance=basis_tolerance,
        minimum_repair_sessions=minimum_repair_sessions, residual_suspects=residual_suspects,
        repair=repair, full_replacement=full_replacement)


def merge_adjusted_ohlcv_capture(*, prior: Mapping[str, Any], fresh: AdjustedPriceCapture,
                                active: tuple[str, ...], source_session: str,
                                basis_tolerance: float, minimum_repair_sessions: int,
                                residual_suspects: tuple[str, ...] = (),
                                repair: AdjustedPriceCapture | None = None,
                                full_replacement: bool = False,
                                allow_historical_replacement: bool = False) -> AdjustedMerge:
    return _merge_adjusted_capture(fields=OHLCV_FIELDS, prior=prior, fresh=fresh,
        active=active, source_session=source_session, basis_tolerance=basis_tolerance,
        minimum_repair_sessions=minimum_repair_sessions, residual_suspects=residual_suspects,
        repair=repair, full_replacement=full_replacement,
        allow_historical_replacement=allow_historical_replacement)
