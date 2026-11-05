"""GLT T09 component forecast study -- measurement-only engine (cohort 1).

Preregistered rolling-origin forecast study of three Fed balance-sheet
components (reserves WRESBAL, TGA, ON RRP) over fixed weekly origins with a
frozen baseline ladder, five residual candidates, purged training sets,
training-only transforms and training-only conformal intervals.  The module is
a pure engine: no network, no filesystem reads of the data or rendered-site
trees, no wall-clock access, and no writes; the runner owns all I/O.  Every
cell that does not earn its preregistered margin
over the best baseline with a calibrated interval is WITHHEOLD.  Vintage
cohort 1: latest-vintage canonical history, revision risk undocumented and
stated, not modelled.  See FROZEN_SPEC_T09 (ORCH-I, 2026-10-19).
"""

from __future__ import annotations

import calendar as _cal
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

from engine import global_liquidity_knowledge_time as _kt
from engine import global_liquidity_outlook as _outlook

SCHEMA = "glt_t09_component_forecast_result_v1"
TASK_ID = "GLT-T09"
AUTHORITY = "measurement_only"
VALIDATED = False
DEFAULT_DECISION_TZ = "America/New_York"
TARGETS = ("reserves_wresbal_bn", "tga_bn", "rrp_bn")
BASELINE_LADDER = ("persistence", "announced_only", "seasonal_calendar", "training_only_ar")
CALENDAR_INDICATORS = (
    "tax_jan15", "tax_apr15", "tax_jun15", "tax_sep15", "tax_dec15",
    "quarter_end", "month_end_non_quarter",
)
CLOCK_RULES = ("h41_thursday_1630", "dts_next_business_day_1600", "same_day_1315")
DISPOSITIONS = ("issued", "withheld_no_gain", "withheld_insufficient_sample",
                "withheld_miscalibrated", "unavailable")
FORBIDDEN_KEY_RE = re.compile(r"(^|_)(score|confidence|rank|size)(_|$)|probability_of")
TARGET_COMPONENT = {"tga_bn": "treasury_general_account", "rrp_bn": "reverse_repo_others"}

_FEDERAL_CBD = CustomBusinessDay(calendar=USFederalHolidayCalendar())
_CAL_FEATURES = tuple(f"cal_{name}" for name in CALENDAR_INDICATORS)
_RIDGE_FEATURES = tuple([f"r_lag{k}" for k in (1, 2, 3, 4)] + list(_CAL_FEATURES) + ["ann_change"])


class MissingPublicationClock(ValueError):
    """A source frame lacks a usable publication clock column."""


class LeakedValidationResidual(ValueError):
    """A fit or calibration saw rows that matured at or after its origin."""


class ReservedWindowTouched(ValueError):
    """An origin or outcome reached into the reserved evaluation window."""


class FamilyDeclarationError(ValueError):
    """The frozen family declaration failed a preregistration check."""


@dataclass(frozen=True)
class CandidateConfig:
    id: str
    kind: str
    p: int | None = None
    alpha: float | None = None

    def as_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "p": self.p, "alpha": self.alpha}


def _as_date(value, field: str) -> date:
    if isinstance(value, datetime):
        raise FamilyDeclarationError(f"{field}: a datetime is refused; use a date")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise FamilyDeclarationError(f"{field}: unparsable ISO date {value!r}") from exc
    raise FamilyDeclarationError(f"{field}: expected an ISO date string or date")


def _require(container, key: str, where: str):
    if not isinstance(container, dict) or key not in container:
        raise FamilyDeclarationError(f"{where}.{key}: required field missing")
    value = container[key]
    if value is None:
        raise FamilyDeclarationError(f"{where}.{key}: required field is None")
    if isinstance(value, str) and not value.strip():
        raise FamilyDeclarationError(f"{where}.{key}: required field is blank")
    if isinstance(value, (list, tuple, dict)) and len(value) == 0:
        raise FamilyDeclarationError(f"{where}.{key}: required field is empty")
    return value


@dataclass(frozen=True)
class Windows:
    calendar: str
    train_start: date
    train_end: date
    dev_start: date
    dev_end: date
    reserved_start: date
    reserved_end: date
    purge_sessions: int
    purge_rule: str
    purge_weeks: int

    def as_dict(self) -> dict:
        return {
            "calendar": self.calendar,
            "train_start": self.train_start.isoformat(),
            "train_end": self.train_end.isoformat(),
            "dev_start": self.dev_start.isoformat(),
            "dev_end": self.dev_end.isoformat(),
            "reserved_start": self.reserved_start.isoformat(),
            "reserved_end": self.reserved_end.isoformat(),
            "purge_sessions": self.purge_sessions,
            "purge_rule": self.purge_rule,
            "purge_weeks": self.purge_weeks,
        }


@dataclass(frozen=True)
class Origins:
    weekday: str
    decision_time: str
    decision_tz: str
    step_weeks: int
    min_train_weeks: int
    min_train_examples: int
    lag_buffer_days: int
    max_anchor_age_days: dict


@dataclass(frozen=True)
class Margins:
    primary_error: str
    secondary_error: str
    min_relative_gain: float
    ci_level: float
    block_weeks: int
    n_resamples: int
    seed: int
    min_scored_origins: int
    coverage_tolerance_points: float


@dataclass(frozen=True)
class Intervals:
    nominal_levels: tuple
    method: str
    calibration_scope: str
    interval_semantics: str
    min_calibration_residuals: int


@dataclass(frozen=True)
class FamilyDeclaration:
    name: str
    primary_target: str
    targets: tuple
    horizons_weeks: tuple
    baselines: tuple
    candidates: tuple
    n_trials_total: int
    training_only_ar_max_p: int
    windows: Windows
    origins: Origins
    margins: Margins
    intervals: Intervals
    clocks: dict
    sources: dict
    calendar_indicators: tuple
    card_ref: dict
    vintage_cohort: int
    revision_risk: str
    authority: str
    validated: bool
    estimate_type_for_issued: str
    information_set_rule: str

    def cells(self) -> list:
        return [(t, h, c) for t in self.targets for h in self.horizons_weeks for c in self.candidates]

    def trial_config(self, target, horizon_weeks, candidate) -> dict:
        return {
            "family": self.name,
            "target": target,
            "horizon_weeks": horizon_weeks,
            "candidate": candidate.as_dict(),
            "windows": self.windows.as_dict(),
            "card_hash": self.card_ref["card_hash"],
        }


def _parse_candidate(raw, where: str) -> CandidateConfig:
    cid = _require(raw, "id", where)
    kind = _require(raw, "kind", where)
    p = raw.get("p")
    alpha = raw.get("alpha")
    if kind == "residual_ar":
        if not isinstance(p, int) or isinstance(p, bool) or p not in (1, 2, 3, 4):
            raise FamilyDeclarationError(f"{where}.p: residual_ar needs p in 1..4, got {p!r}")
    elif kind == "ridge_residual":
        if not isinstance(alpha, (int, float)) or isinstance(alpha, bool) or not alpha > 0:
            raise FamilyDeclarationError(f"{where}.alpha: ridge_residual needs alpha > 0, got {alpha!r}")
    else:
        raise FamilyDeclarationError(f"{where}.kind: unknown candidate kind {kind!r}")
    return CandidateConfig(id=cid, kind=kind, p=p,
                             alpha=float(alpha) if (kind == "ridge_residual" and alpha is not None) else alpha)


def load_family(path) -> FamilyDeclaration:
    """Parse and validate the frozen family declaration (YAML)."""
    import yaml

    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise FamilyDeclarationError("config: root must be a mapping")

    fam = _require(raw, "family", "config")
    name = _require(fam, "name", "family")
    primary_target = _require(fam, "primary_target", "family")
    targets_raw = _require(fam, "targets", "family")
    horizons_raw = _require(fam, "horizons_weeks", "family")
    baselines_raw = _require(fam, "baselines", "family")
    candidates_raw = _require(fam, "candidates", "family")
    n_trials_total = _require(fam, "n_trials_total", "family")
    max_p = _require(fam, "training_only_ar_max_p", "family")

    targets = tuple(targets_raw)
    horizons = tuple(horizons_raw)
    for h in horizons:
        if not isinstance(h, int) or isinstance(h, bool) or h <= 0:
            raise FamilyDeclarationError(f"family.horizons_weeks: horizon {h!r} is not a positive int")
    if list(baselines_raw) != list(BASELINE_LADDER):
        raise FamilyDeclarationError("family.baselines: must equal the frozen baseline ladder")
    if primary_target not in targets:
        raise FamilyDeclarationError("family.primary_target: not among targets")
    for t in targets:
        if t not in TARGETS:
            raise FamilyDeclarationError(f"family.targets: {t!r} is not a declared TARGET")
    if len(candidates_raw) > 5:
        raise FamilyDeclarationError("family.candidates: more than 5 candidates")
    candidates = tuple(_parse_candidate(c, f"family.candidates[{i}]") for i, c in enumerate(candidates_raw))
    ids = [c.id for c in candidates]
    if len(set(ids)) != len(ids):
        raise FamilyDeclarationError("family.candidates: duplicate candidate ids")
    expected_trials = len(targets) * len(horizons) * len(candidates)
    if n_trials_total != expected_trials:
        raise FamilyDeclarationError(
            f"family.n_trials_total: {n_trials_total} != {len(targets)}*{len(horizons)}*{len(candidates)}")

    win = _require(raw, "windows", "config")
    wd = {k: _as_date(_require(win, k, "windows"), f"windows.{k}")
          for k in ("train_start", "train_end", "dev_start", "dev_end", "reserved_start", "reserved_end")}
    purge_sessions = _require(win, "purge_sessions", "windows")
    purge_rule = _require(win, "purge_rule", "windows")
    purge_weeks = _require(win, "purge_weeks", "windows")
    if purge_rule != "ceil(purge_sessions/5)":
        raise FamilyDeclarationError(f"windows.purge_rule: {purge_rule!r} != 'ceil(purge_sessions/5)'")
    if purge_weeks != math.ceil(purge_sessions / 5):
        raise FamilyDeclarationError(
            f"windows.purge_weeks: {purge_weeks} != ceil(purge_sessions/5) = {math.ceil(purge_sessions / 5)}")
    if not (wd["train_start"] < wd["train_end"] < wd["dev_start"] <= wd["dev_end"]
            < wd["reserved_start"] <= wd["reserved_end"]):
        raise FamilyDeclarationError(
            "windows: order must be train_start < train_end < dev_start <= dev_end "
            f"< reserved_start <= reserved_end, got {wd}")
    windows = Windows(calendar=_require(win, "calendar", "windows"), purge_sessions=purge_sessions,
                      purge_rule=purge_rule, purge_weeks=purge_weeks, **wd)

    org = _require(raw, "origins", "config")
    origins = Origins(
        weekday=_require(org, "weekday", "origins"),
        decision_time=_require(org, "decision_time", "origins"),
        decision_tz=_require(org, "decision_tz", "origins"),
        step_weeks=_require(org, "step_weeks", "origins"),
        min_train_weeks=_require(org, "min_train_weeks", "origins"),
        min_train_examples=_require(org, "min_train_examples", "origins"),
        lag_buffer_days=_require(org, "lag_buffer_days", "origins"),
        max_anchor_age_days=dict(_require(org, "max_anchor_age_days", "origins")),
    )

    mar = _require(raw, "margins", "config")
    margins = Margins(
        primary_error=_require(mar, "primary_error", "margins"),
        secondary_error=_require(mar, "secondary_error", "margins"),
        min_relative_gain=float(_require(mar, "min_relative_gain", "margins")),
        ci_level=float(_require(mar, "ci_level", "margins")),
        block_weeks=_require(mar, "block_weeks", "margins"),
        n_resamples=_require(mar, "n_resamples", "margins"),
        seed=_require(mar, "seed", "margins"),
        min_scored_origins=_require(mar, "min_scored_origins", "margins"),
        coverage_tolerance_points=float(_require(mar, "coverage_tolerance_points", "margins")),
    )

    itr = _require(raw, "intervals", "config")
    intervals = Intervals(
        nominal_levels=tuple(_require(itr, "nominal_levels", "intervals")),
        method=_require(itr, "method", "intervals"),
        calibration_scope=_require(itr, "calibration_scope", "intervals"),
        interval_semantics=_require(itr, "interval_semantics", "intervals"),
        min_calibration_residuals=_require(itr, "min_calibration_residuals", "intervals"),
    )

    cal_ind = tuple(_require(raw, "calendar_indicators", "config"))
    if list(cal_ind) != list(CALENDAR_INDICATORS):
        raise FamilyDeclarationError("calendar_indicators: must equal the frozen indicator list")

    clocks = dict(_require(raw, "clocks", "config"))
    for t, clock in clocks.items():
        rule = _require(clock, "rule", f"clocks.{t}")
        if rule not in CLOCK_RULES:
            raise FamilyDeclarationError(f"clocks.{t}.rule: {rule!r} is not a declared CLOCK_RULE")

    card_ref = dict(_require(raw, "preregistration_card_ref", "config"))
    _require(card_ref, "card_hash", "preregistration_card_ref")

    authority = _require(raw, "authority", "config")
    validated = _require(raw, "validated", "config")
    if authority != AUTHORITY:
        raise FamilyDeclarationError(f"authority: {authority!r} != {AUTHORITY!r}")
    if validated is not False:
        raise FamilyDeclarationError("validated: must be false for a measurement-only family")

    return FamilyDeclaration(
        name=name, primary_target=primary_target, targets=targets, horizons_weeks=horizons,
        baselines=tuple(baselines_raw), candidates=candidates, n_trials_total=n_trials_total,
        training_only_ar_max_p=max_p, windows=windows, origins=origins, margins=margins,
        intervals=intervals, clocks=clocks, sources=dict(_require(raw, "sources", "config")),
        calendar_indicators=cal_ind, card_ref=card_ref,
        vintage_cohort=_require(raw, "vintage_cohort", "config"),
        revision_risk=_require(raw, "revision_risk", "config"),
        authority=authority, validated=validated,
        estimate_type_for_issued=_require(raw, "estimate_type_for_issued", "config"),
        information_set_rule=_require(raw, "information_set_rule", "config"),
    )


def _require_clock(frame, clock: str = "published_at_utc") -> None:
    if clock not in getattr(frame, "columns", ()):
        raise MissingPublicationClock(f"frame has no {clock!r} column")
    if frame[clock].isna().any():
        raise MissingPublicationClock(f"frame has NaT/None values in {clock!r}")


def attach_publication_clock(frame, *, rule, decision_tz=DEFAULT_DECISION_TZ):
    """Return a copy of ``frame`` with a tz-aware UTC ``published_at_utc``."""
    out = frame.copy()
    obs = pd.DatetimeIndex(pd.to_datetime(out["obs_date"])).normalize()
    if rule == "same_day_1315":
        day, hour, minute = obs, 13, 15
    elif rule == "h41_thursday_1630":
        day, hour, minute = pd.DatetimeIndex([_FEDERAL_CBD.rollforward(ts) for ts in obs + pd.Timedelta(days=1)]), 16, 30
    elif rule == "dts_next_business_day_1600":
        day, hour, minute = pd.DatetimeIndex([_FEDERAL_CBD.rollforward(ts) for ts in obs + pd.Timedelta(days=1)]), 16, 0
    else:
        raise ValueError(f"unknown publication rule: {rule!r}")
    local = day + pd.Timedelta(hours=hour, minutes=minute)
    out["published_at_utc"] = local.tz_localize(decision_tz).tz_convert("UTC")
    return out


def _cutoff_for(origin, decision_tz):
    if isinstance(origin, pd.Timestamp):
        origin = origin.to_pydatetime()
    if isinstance(origin, datetime):
        if origin.tzinfo is None or origin.utcoffset() is None:
            origin = origin.date()
    return _kt.cutoff_utc(origin, decision_tz)


def information_set(frame, *, origin, clock="published_at_utc", decision_tz=DEFAULT_DECISION_TZ):
    """Rows already published at the decision instant (copy, original order)."""
    _require_clock(frame, clock)
    cutoff = _cutoff_for(origin, decision_tz)
    mask = frame[clock] <= pd.Timestamp(cutoff)
    return frame.loc[mask].copy()


def panel_fridays(windows, origins) -> pd.DatetimeIndex:
    start = pd.Timestamp(windows.train_start) - pd.Timedelta(days=origins.lag_buffer_days)
    return pd.date_range(start=start, end=pd.Timestamp(windows.dev_end), freq="W-FRI")


def weekly_panel(frame, *, fridays, max_anchor_age_days, decision_tz=DEFAULT_DECISION_TZ):
    """Anchor level per decision Friday from the admitted information set."""
    _require_clock(frame)
    fr = pd.DatetimeIndex(fridays)
    srt = frame.assign(_sort=frame["published_at_utc"]).sort_values("_sort", kind="mergesort")
    clock_idx = pd.DatetimeIndex(srt["published_at_utc"])
    obs_vals = pd.DatetimeIndex(pd.to_datetime(srt["obs_date"])).to_numpy()
    vals = pd.to_numeric(srt["value"], errors="coerce").to_numpy(dtype=float)
    run_arg = np.full(len(obs_vals), -1, dtype=np.int64)
    best = np.datetime64("NaT")
    cur = -1
    for i in range(len(obs_vals)):
        ov = obs_vals[i]
        if not np.isnat(ov) and (np.isnat(best) or ov > best):
            best = ov
            cur = i
        run_arg[i] = cur
    cutoffs = fr.tz_localize(decision_tz).tz_convert("UTC")
    k = clock_idx.searchsorted(cutoffs, side="right")
    n = len(obs_vals)
    kr = np.clip(np.where(k > 0, run_arg[np.clip(k - 1, 0, max(n - 1, 0))], -1), -1, max(n - 1, 0))
    obs_chosen = np.where(kr >= 0, obs_vals[np.clip(kr, 0, max(n - 1, 0))], np.datetime64("NaT"))
    vals_chosen = np.where(kr >= 0, vals[np.clip(kr, 0, max(n - 1, 0))], np.nan)
    age_days = (fr.to_numpy() - obs_chosen) / np.timedelta64(1, "D")
    available = (kr >= 0) & np.isfinite(vals_chosen) & (age_days <= float(max_anchor_age_days))
    level = np.where(available, vals_chosen, np.nan)
    panel = pd.DataFrame(
        {"level": level.astype(float),
         "obs_date": obs_chosen.astype("datetime64[ns]"),
         "available": available.astype(bool)},
        index=fr)
    panel.index.name = "friday"
    return panel


def _as_day(value):
    if isinstance(value, pd.Timestamp):
        return value.date() if value.tzinfo is None else value.date()
    if isinstance(value, datetime):
        return value.date()
    return value


def announced_increment(announcements, *, target, start, end, as_of, anchor_level,
                        decision_tz=DEFAULT_DECISION_TZ, units_per_bn=1000.0):
    """Announced change in $bn over (start, end], from announcements admissible at ``as_of``."""
    if not announcements:
        return 0.0
    start, end = _as_day(start), _as_day(end)
    admitted = _outlook.admissible_announcements(announcements, as_of=_as_day(as_of), decision_tz=decision_tz)["admitted"]
    counted = []
    for ann in admitted:
        component = ann.get("component")
        for change in ann.get("changes", ()):
            eff = _as_day(change.get("effective"))
            if eff is None:
                continue
            if start < eff <= end:
                counted.append((eff, component, change))
    counted.sort(key=lambda item: item[0])
    if target in TARGET_COMPONENT:
        wanted = TARGET_COMPONENT[target]
        counted = [(e, c, ch) for (e, c, ch) in counted if c == wanted]
    else:
        counted = [(e, c, ch) for (e, c, ch) in counted if c in _outlook.COMPONENT_SIGN]
    if not counted:
        return 0.0
    u = float(units_per_bn)
    deltas = [float(ch["delta"]) for (e, c, ch) in counted if ch.get("delta") is not None]
    level_positions = [i for i, (e, c, ch) in enumerate(counted) if ch.get("level") is not None]
    if target in TARGET_COMPONENT:
        if not level_positions:
            return sum(deltas) / u
        li = level_positions[-1]
        lev_eff, _lev_component, lev_change = counted[li]
        after = sum(float(ch["delta"]) for (e, c, ch) in counted[li + 1:]
                    if ch.get("delta") is not None and e > lev_eff)
        if anchor_level is None or not math.isfinite(float(anchor_level)):
            return None
        return float(lev_change["level"]) / u + after / u - float(anchor_level)
    if level_positions:
        return None
    return sum(_outlook.COMPONENT_SIGN[c] * float(ch["delta"])
               for (e, c, ch) in counted if ch.get("delta") is not None) / u


_TAX_DAYS = {(1, 15): "tax_jan15", (4, 15): "tax_apr15", (6, 15): "tax_jun15",
             (9, 15): "tax_sep15", (12, 15): "tax_dec15"}


def _calendar_counts(t_date: date, m_date: date) -> dict:
    counts = {name: 0 for name in CALENDAR_INDICATORS}
    cur = t_date + timedelta(days=1)
    while cur <= m_date:
        tax = _TAX_DAYS.get((cur.month, cur.day))
        last_day = _cal.monthrange(cur.year, cur.month)[1]
        if tax is not None:
            counts[tax] += 1
        elif cur.day == last_day:
            if cur.month in (3, 6, 9, 12):
                counts["quarter_end"] += 1
            else:
                counts["month_end_non_quarter"] += 1
        cur += timedelta(days=1)
    return counts


def build_design(panel, *, horizon_weeks, target, announcements=(),
                 decision_tz=DEFAULT_DECISION_TZ, calendar_indicators=CALENDAR_INDICATORS):
    """One row per panel Friday: anchor, outcome, lags, announced changes, calendar counts."""
    levels = {}
    available = {}
    for ts, lvl, avail in zip(panel.index, panel["level"], panel["available"]):
        levels[pd.Timestamp(ts)] = float(lvl) if pd.notna(lvl) else float("nan")
        available[pd.Timestamp(ts)] = bool(avail)

    def w(ts):
        return levels.get(pd.Timestamp(ts), float("nan"))

    rows = []
    for t in panel.index:
        t = pd.Timestamp(t)
        maturity = t + pd.Timedelta(days=7 * horizon_weeks)
        w_t = w(t)
        w_m = w(maturity)
        y = w_m - w_t if (math.isfinite(w_m) and math.isfinite(w_t)) else float("nan")
        d_lags, r_lags, ann_weekly = {}, {}, {}
        for k in (1, 2, 3, 4):
            w_here, w_prev = w(t - pd.Timedelta(days=7 * (k - 1))), w(t - pd.Timedelta(days=7 * k))
            d_k = w_here - w_prev if (math.isfinite(w_here) and math.isfinite(w_prev)) else float("nan")
            d_lags[k] = d_k
            inc = announced_increment(announcements, target=target, start=t - pd.Timedelta(days=7 * k),
                                      end=t - pd.Timedelta(days=7 * (k - 1)), as_of=t.date(),
                                      anchor_level=w_prev, decision_tz=decision_tz)
            ann_weekly[k] = float("nan") if inc is None else float(inc)
            r_lags[k] = d_k - ann_weekly[k] if math.isfinite(d_k) else float("nan")
        ann_change = announced_increment(announcements, target=target, start=t, end=maturity,
                                         as_of=t.date(), anchor_level=w_t, decision_tz=decision_tz)
        ann_change = float("nan") if ann_change is None else float(ann_change)
        counts = _calendar_counts(t.date(), maturity.date())
        week = t.isocalendar().week
        row = {
            "anchor_level": w_t,
            "anchor_available": available[t],
            "maturity": maturity,
            "y": y,
            "outcome_available": math.isfinite(y),
        }
        for k in (1, 2, 3, 4):
            row[f"d_lag{k}"] = d_lags[k]
            row[f"ann_weekly_lag{k}"] = ann_weekly[k]
            row[f"r_lag{k}"] = r_lags[k]
        row["ann_change"] = ann_change
        row["y_res"] = y - ann_change if math.isfinite(y) else float("nan")
        for name in calendar_indicators:
            row[f"cal_{name}"] = counts[name]
        row["iso_week"] = 52 if week == 53 else week
        rows.append(row)
    design = pd.DataFrame(rows, index=pd.DatetimeIndex(panel.index))
    design["maturity"] = pd.to_datetime(design["maturity"])
    design["iso_week"] = design["iso_week"].astype(int)
    return design


def assert_outside_reserved(dates, *, horizon_weeks, dev_end, reserved_start):
    for d in dates:
        if pd.Timestamp(d) >= pd.Timestamp(reserved_start):
            raise ReservedWindowTouched(f"origin {pd.Timestamp(d).date()} >= reserved_start {reserved_start}")
        if pd.Timestamp(d) + pd.Timedelta(days=7 * horizon_weeks) > pd.Timestamp(dev_end):
            raise ReservedWindowTouched(
                f"origin {pd.Timestamp(d).date()} matures after dev_end {dev_end} at h={horizon_weeks}")


def rolling_origins(index, *, train_end, dev_end, reserved_start, min_train_weeks,
                    step_weeks, horizon_weeks, purge_weeks):
    """Eligible evaluation origins (ascending), stepped, never touching the reserved window."""
    idx = pd.DatetimeIndex(index)
    if pd.Timestamp(dev_end) >= pd.Timestamp(reserved_start):
        raise ReservedWindowTouched(f"dev_end {dev_end} >= reserved_start {reserved_start}")
    if len(idx) and bool((idx >= pd.Timestamp(reserved_start)).any()):
        bad = idx[idx >= pd.Timestamp(reserved_start)][0]
        raise ReservedWindowTouched(f"index element {bad.date()} >= reserved_start {reserved_start}")
    min_origin = idx[0] + pd.Timedelta(days=7 * (min_train_weeks + horizon_weeks + purge_weeks))
    mature_ok = idx + pd.Timedelta(days=7 * horizon_weeks) <= pd.Timestamp(dev_end)
    eligible = idx[(idx > pd.Timestamp(train_end)) & mature_ok & (idx >= min_origin)]
    out = eligible[::step_weeks]
    assert_outside_reserved(out, horizon_weeks=horizon_weeks, dev_end=dev_end, reserved_start=reserved_start)
    return out


def training_rows(design, *, origin, horizon_weeks, purge_weeks, train_start):
    """In-sample rows at ``origin``: matured at least ``purge_weeks`` before it."""
    cutoff = pd.Timestamp(origin) - pd.Timedelta(days=7 * purge_weeks)
    mask = (design.index >= pd.Timestamp(train_start)) & (design["maturity"] <= cutoff) \
        & design["outcome_available"].astype(bool)
    return design.loc[mask]


@dataclass(frozen=True)
class Fitted:
    kind: str
    coef: tuple
    intercept: float
    feature_names: tuple
    feature_mean: tuple | None = None
    feature_std: tuple | None = None
    p: int | None = None
    alpha: float | None = None
    n_train: int = 0
    origin: pd.Timestamp | None = None
    min_train_examples: int = 0
    week_means: tuple | None = None
    overall_mean: float | None = None

    def predict(self, row):
        get = row.__getitem__ if hasattr(row, "__getitem__") else (lambda k: row.get(k))

        def _num(name):
            try:
                v = get(name)
            except (KeyError, IndexError):
                return None
            if v is None:
                return None
            try:
                fv = float(v)
            except (TypeError, ValueError):
                return None
            return fv if math.isfinite(fv) else None

        if self.kind == "persistence":
            return 0.0
        if self.kind == "announced_only":
            return _num("ann_change")
        if self.kind in ("seasonal_calendar", "training_only_ar", "residual_ar", "ridge_residual"):
            if self.n_train < self.min_train_examples or self.n_train <= 0:
                return None
        if self.kind == "seasonal_calendar":
            if self.overall_mean is None:
                return None
            bucket = dict(self.week_means or ()).get(int(row["iso_week"]))
            base = bucket if bucket is not None else self.overall_mean
            total = 0.0
            for name, coef in zip(self.feature_names, self.coef):
                v = _num(name)
                if v is None:
                    return None
                total += float(coef) * v
            return float(base) + total
        if self.kind == "training_only_ar":
            total = float(self.intercept)
            for name, coef in zip(self.feature_names, self.coef):
                v = _num(name)
                if v is None:
                    return None
                total += float(coef) * v
            return total
        ann = _num("ann_change")
        if ann is None:
            return None
        if self.kind == "residual_ar":
            total = float(self.intercept)
            for name, coef in zip(self.feature_names, self.coef):
                v = _num(name)
                if v is None:
                    return None
                total += float(coef) * v
            return ann + total
        if self.kind == "ridge_residual":
            total = 0.0
            for name, mean, std, coef in zip(self.feature_names, self.feature_mean, self.feature_std, self.coef):
                v = _num(name)
                if v is None:
                    return None
                if std and std > 0.0:
                    total += float(coef) * ((v - float(mean)) / float(std))
            return ann + float(self.intercept) + total
        raise ValueError(f"unknown fitted kind: {self.kind!r}")


def _check_no_leak(train_frame, origin) -> None:
    if len(train_frame) and bool((train_frame["maturity"] >= pd.Timestamp(origin)).any()):
        raise LeakedValidationResidual(
            f"training row matures at/after origin {pd.Timestamp(origin)}")


def _finite_rows(train_frame, columns):
    mask = np.ones(len(train_frame), dtype=bool)
    for col in columns:
        mask &= np.isfinite(pd.to_numeric(train_frame[col], errors="coerce").to_numpy(dtype=float))
    return train_frame.loc[mask]


def fit_baseline(name, train_frame, *, origin, max_p=4, min_train_examples=104) -> Fitted:
    """Fit one baseline on training rows only (leakage refused)."""
    _check_no_leak(train_frame, origin)
    origin = pd.Timestamp(origin)
    n_all = len(train_frame)
    if name == "persistence":
        return Fitted(kind="persistence", coef=(), intercept=0.0, feature_names=(),
                      n_train=n_all, origin=origin, min_train_examples=min_train_examples)
    if name == "announced_only":
        return Fitted(kind="announced_only", coef=(), intercept=0.0, feature_names=("ann_change",),
                      n_train=n_all, origin=origin, min_train_examples=min_train_examples)
    if name == "seasonal_calendar":
        sub = _finite_rows(train_frame, ["y"])
        y = sub["y"].to_numpy(dtype=float)
        weeks = sub["iso_week"].to_numpy(dtype=int)
        buckets, overall = {}, (float(np.mean(y)) if len(y) else None)
        for wk in np.unique(weeks):
            sel = weeks == wk
            if int(sel.sum()) >= 2:
                buckets[int(wk)] = float(np.mean(y[sel]))
        if not len(sub):
            return Fitted(kind="seasonal_calendar", coef=(), intercept=0.0, feature_names=_CAL_FEATURES,
                          n_train=0, origin=origin, min_train_examples=min_train_examples,
                          week_means=None, overall_mean=None)
        resid = np.array([y[i] - buckets.get(int(weeks[i]), overall) for i in range(len(y))], dtype=float)
        X = np.column_stack([pd.to_numeric(sub[c], errors="coerce").to_numpy(dtype=float) for c in _CAL_FEATURES])
        beta = np.linalg.lstsq(X, resid, rcond=None)[0]
        return Fitted(kind="seasonal_calendar", coef=tuple(float(b) for b in beta), intercept=0.0,
                      feature_names=_CAL_FEATURES, n_train=len(sub), origin=origin,
                      min_train_examples=min_train_examples,
                      week_means=tuple(sorted(buckets.items())), overall_mean=overall)
    if name == "training_only_ar":
        sub = _finite_rows(train_frame, ["y"] + [f"d_lag{k}" for k in (1, 2, 3, 4)])
        y = sub["y"].to_numpy(dtype=float)
        if not len(sub):
            return Fitted(kind="training_only_ar", coef=(), intercept=0.0, feature_names=(),
                          p=None, n_train=0, origin=origin, min_train_examples=min_train_examples)
        best = None
        for p in range(1, max_p + 1):
            feats = [f"d_lag{k}" for k in range(1, p + 1)]
            X = np.column_stack([np.ones(len(sub))] +
                                [pd.to_numeric(sub[c], errors="coerce").to_numpy(dtype=float) for c in feats])
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            rss = float(np.sum((y - X @ beta) ** 2))
            aic = len(y) * math.log(max(rss / len(y), 5e-324)) + 2 * (p + 1)
            if best is None or aic < best[0]:
                best = (aic, p, beta)
        _, p, beta = best
        return Fitted(kind="training_only_ar", coef=tuple(float(b) for b in beta[1:]),
                      intercept=float(beta[0]), feature_names=tuple(f"d_lag{k}" for k in range(1, p + 1)),
                      p=p, n_train=len(sub), origin=origin, min_train_examples=min_train_examples)
    raise ValueError(f"unknown baseline name: {name!r}")


def fit_candidate(config, train_frame, *, origin, min_train_examples=104) -> Fitted:
    """Fit one residual candidate on training rows only (leakage refused)."""
    _check_no_leak(train_frame, origin)
    origin = pd.Timestamp(origin)
    if config.kind == "residual_ar":
        feats = [f"r_lag{k}" for k in range(1, config.p + 1)]
        sub = _finite_rows(train_frame, ["y_res"] + feats)
        if not len(sub):
            return Fitted(kind="residual_ar", coef=(), intercept=0.0, feature_names=tuple(feats),
                          p=config.p, n_train=0, origin=origin, min_train_examples=min_train_examples)
        y = sub["y_res"].to_numpy(dtype=float)
        X = np.column_stack([np.ones(len(sub))] +
                            [pd.to_numeric(sub[c], errors="coerce").to_numpy(dtype=float) for c in feats])
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        return Fitted(kind="residual_ar", coef=tuple(float(b) for b in beta[1:]), intercept=float(beta[0]),
                      feature_names=tuple(feats), p=config.p, n_train=len(sub), origin=origin,
                      min_train_examples=min_train_examples)
    if config.kind == "ridge_residual":
        sub = _finite_rows(train_frame, ["y_res"] + list(_RIDGE_FEATURES))
        if not len(sub):
            return Fitted(kind="ridge_residual", coef=(), intercept=0.0, feature_names=_RIDGE_FEATURES,
                          alpha=config.alpha, n_train=0, origin=origin, min_train_examples=min_train_examples)
        y = sub["y_res"].to_numpy(dtype=float)
        X = np.column_stack([pd.to_numeric(sub[c], errors="coerce").to_numpy(dtype=float)
                             for c in _RIDGE_FEATURES])
        mean = X.mean(axis=0)
        std = X.std(axis=0, ddof=0)
        std_safe = np.where(std > 0.0, std, 1.0)
        Z = (X - mean) / std_safe
        Z = np.where((std > 0.0)[None, :], Z, 0.0)
        y_center = y - float(np.mean(y))
        beta = np.linalg.solve(Z.T @ Z + float(config.alpha) * np.eye(Z.shape[1]), Z.T @ y_center)
        return Fitted(kind="ridge_residual", coef=tuple(float(b) for b in beta),
                      intercept=float(np.mean(y)), feature_names=_RIDGE_FEATURES,
                      feature_mean=tuple(float(m) for m in mean), feature_std=tuple(float(s) for s in std),
                      alpha=config.alpha, n_train=len(sub), origin=origin,
                      min_train_examples=min_train_examples)
    raise ValueError(f"unknown candidate kind: {config.kind!r}")


def calibrate_interval(fitted, inner_residuals, *, nominal_levels, min_n=52):
    """Training-only conformal half-widths per nominal level (percentage points)."""
    origin = pd.Timestamp(fitted.origin)
    idx = pd.DatetimeIndex(inner_residuals.index) if len(inner_residuals.index) else pd.DatetimeIndex([])
    if len(idx) and bool((idx >= origin).any()):
        raise LeakedValidationResidual(
            f"inner residual matures at/after fitted origin {origin}")
    vals = pd.to_numeric(pd.Series(inner_residuals.values, index=idx), errors="coerce").to_numpy(dtype=float)
    absr = np.abs(vals[np.isfinite(vals)])
    n = int(absr.size)
    out = {}
    for level in nominal_levels:
        k = math.ceil((n + 1) * float(level) / 100.0)
        if n < min_n or k > n:
            out[int(level)] = None
            continue
        out[int(level)] = float(np.partition(absr, k - 1)[k - 1])
    return out


def _fmt(x) -> str:
    if x is None:
        return "None"
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    if isinstance(x, (float, np.floating)):
        if not math.isfinite(float(x)):
            return str(x)
        return f"{round(float(x), 6):g}"
    return str(x)


def dispose_with_reason(cell, margins):
    den, iv = cell["denominators"], cell["intervals"]
    gain, ci = cell["relative_gain"], cell["gain_ci"]
    if den["n_origins_scored"] == 0:
        return ("unavailable",
                f"no scored origins: n_origins_total={_fmt(den['n_origins_total'])}, "
                f"n_outage={_fmt(den['n_outage'])}, outage_share={_fmt(den['outage_share'])}, "
                f"source_status={den['source_status']}")
    if den["n_origins_scored"] < margins.min_scored_origins:
        return ("withheld_insufficient_sample",
                f"n_origins_scored={_fmt(den['n_origins_scored'])} < "
                f"min_scored_origins={margins.min_scored_origins}")
    no_gain = (gain is None or ci is None or ci.get("low") is None
               or float(gain) < float(margins.min_relative_gain) or float(ci["low"]) <= 0.0)
    if no_gain:
        return ("withheld_no_gain",
                f"best baseline {cell['best_baseline']}: relative_gain={_fmt(gain)} "
                f"(min_relative_gain={_fmt(margins.min_relative_gain)}), gain_ci="
                f"({_fmt(ci.get('low'))}, {_fmt(ci.get('high'))}) at level {_fmt(ci.get('level'))}")
    for key in iv:
        rec = iv[key]
        nominal = rec["nominal"]
        bad = (rec["n_missing"] > 0 or rec["observed_coverage"] is None or rec["mean_width"] is None
               or abs(float(rec["observed_coverage"]) - float(nominal)) > float(margins.coverage_tolerance_points))
        if bad:
            return ("withheld_miscalibrated",
                    f"level {nominal}: observed_coverage={_fmt(rec['observed_coverage'])} vs "
                    f"nominal={_fmt(nominal)} (tolerance {_fmt(margins.coverage_tolerance_points)}), "
                    f"mean_width={_fmt(rec['mean_width'])}, n_missing={rec['n_missing']}")
    detail = "; ".join(
        f"level {iv[k]['nominal']}: coverage={_fmt(iv[k]['observed_coverage'])}, width={_fmt(iv[k]['mean_width'])}"
        for k in iv)
    return ("issued",
            f"relative_gain={_fmt(gain)} vs best baseline {cell['best_baseline']}, "
            f"gain_ci=({_fmt(ci['low'])}, {_fmt(ci['high'])}) at level {_fmt(ci['level'])}; {detail}")


def dispose(cell, margins) -> str:
    return dispose_with_reason(cell, margins)[0]


def score_cells(frame, *, target, horizon_weeks, family, cell_index_start):
    """Score the 5 candidate cells of one (target, horizon) on the eval-origin frame."""
    margins = family.margins
    baseline_cols = [f"f_{name}" for name in BASELINE_LADDER]
    cand_cols = [f"f_{c.id}" for c in family.candidates]
    model_cols = baseline_cols + cand_cols
    source_ok = frame["source_available"].astype(bool).to_numpy()
    outcome_ok = frame["outcome_available"].astype(bool).to_numpy()
    scored = source_ok & outcome_ok
    for col in model_cols:
        vals = pd.to_numeric(frame[col], errors="coerce").to_numpy(dtype=float)
        scored = scored & np.isfinite(vals)
    n_total = len(frame)
    n_outage = int((~source_ok).sum())
    n_outcome = int((source_ok & ~outcome_ok).sum())
    n_model = int((source_ok & outcome_ok & ~scored).sum())
    n_scored = int(scored.sum())
    denominators = {
        "n_origins_total": n_total,
        "n_outage": n_outage,
        "outage_share": (float(n_outage) / float(n_total)) if n_total and n_outage else None,
        "n_outcome_unavailable": n_outcome,
        "n_model_unavailable": n_model,
        "n_origins_scored": n_scored,
        "source_status": str(frame.attrs.get("source_status", "loaded")),
    }
    y = pd.to_numeric(frame["y"], errors="coerce").to_numpy(dtype=float)
    errors = {}
    model_vals = {}
    for col in model_cols:
        vals = pd.to_numeric(frame[col], errors="coerce").to_numpy(dtype=float)
        model_vals[col] = vals
        name = col[2:]
        if n_scored == 0:
            errors[name] = {"mae": None, "rmse": None}
            continue
        e = vals[scored] - y[scored]
        errors[name] = {"mae": float(np.mean(np.abs(e))), "rmse": float(np.sqrt(np.mean(e ** 2)))}
    best_name, best_mae = None, None
    for name in BASELINE_LADDER:
        mae = errors[name]["mae"]
        if mae is not None and (best_mae is None or mae < best_mae):
            best_name, best_mae = name, mae
    e_best = None if best_name is None else model_vals[f"f_{best_name}"][scored] - y[scored]
    first_origin = str(pd.Timestamp(frame.index[0]).date()) if n_total else None
    last_origin = str(pd.Timestamp(frame.index[-1]).date()) if n_total else None
    cells = []
    for k, config in enumerate(family.candidates):
        cell_index = cell_index_start + k
        col = f"f_{config.id}"
        mae_c = errors[config.id]["mae"]
        if n_scored == 0 or best_mae is None or best_mae == 0.0 or mae_c is None:
            relative_gain = None
        else:
            relative_gain = 1.0 - mae_c / best_mae
        gain_ci = None
        if n_scored >= margins.block_weeks and n_scored > 0 and e_best is not None and relative_gain is not None:
            rng = np.random.default_rng([margins.seed, cell_index])
            n_blocks = math.ceil(n_scored / margins.block_weeks)
            starts = rng.integers(0, n_scored - margins.block_weeks + 1,
                                  size=(margins.n_resamples, n_blocks))
            idx = (starts[..., None] + np.arange(margins.block_weeks)).reshape(margins.n_resamples, -1)[:, :n_scored]
            mean_best = np.abs(e_best[idx]).mean(axis=1)
            mean_c = np.abs((model_vals[col][scored] - y[scored])[idx]).mean(axis=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                gains = 1.0 - mean_c / mean_best
            if not bool(np.all(np.isnan(gains))):
                lo, hi = np.nanpercentile(gains, [100.0 * (1.0 - margins.ci_level) / 2.0,
                                                  100.0 * (1.0 + margins.ci_level) / 2.0])
                gain_ci = {"level": margins.ci_level, "low": float(lo), "high": float(hi)}
        intervals = {}
        e_c = None if n_scored == 0 else model_vals[col][scored] - y[scored]
        for level in family.intervals.nominal_levels:
            qvals = pd.to_numeric(frame[f"q{level}_{config.id}"], errors="coerce").to_numpy(dtype=float)[scored] \
                if n_scored else np.array([], dtype=float)
            have = np.isfinite(qvals)
            n_missing = int((~have).sum())
            if bool(have.any()):
                coverage = 100.0 * float(np.mean(np.abs(e_c[have]) <= qvals[have]))
                width = float(np.mean(2.0 * qvals[have]))
            else:
                coverage, width = None, None
            intervals[str(level)] = {"nominal": int(level), "observed_coverage": coverage,
                                     "mean_width": width, "n_missing": n_missing}
        cells.append({
            "target": target,
            "horizon_weeks": horizon_weeks,
            "candidate": config.id,
            "cell_index": cell_index,
            "best_baseline": best_name,
            "relative_gain": relative_gain,
            "gain_ci": gain_ci,
            "errors": dict(errors),
            "intervals": intervals,
            "denominators": dict(denominators),
            "first_origin": first_origin,
            "last_origin": last_origin,
        })
    return cells


def _model_columns(family):
    return ([f"f_{name}" for name in BASELINE_LADDER] + [f"f_{c.id}" for c in family.candidates])


def _null_origin_frame(O, family, status):
    per = pd.DataFrame(index=O)
    n = len(O)
    per["source_available"] = np.zeros(n, dtype=bool)
    per["outcome_available"] = np.zeros(n, dtype=bool)
    per["y"] = np.full(n, np.nan)
    for col in _model_columns(family):
        per[col] = np.full(n, np.nan)
    for cfg in family.candidates:
        for level in family.intervals.nominal_levels:
            per[f"q{level}_{cfg.id}"] = np.full(n, np.nan)
    per.attrs["source_status"] = status
    return per


def _eval_origin_frame(frame, status, *, fridays, O, family, target, horizon_weeks, announcements):
    W, Ocfg = family.windows, family.origins
    panel = weekly_panel(frame, fridays=fridays, max_anchor_age_days=Ocfg.max_anchor_age_days[target],
                         decision_tz=Ocfg.decision_tz)
    design = build_design(panel, horizon_weeks=horizon_weeks, target=target, announcements=announcements,
                          decision_tz=Ocfg.decision_tz, calendar_indicators=family.calendar_indicators)
    max_o = pd.Timestamp(O[-1])
    fit_ts = design.index[(design.index >= pd.Timestamp(W.train_start)) & (design.index <= max_o)]
    mat = design["maturity"].to_numpy().astype("datetime64[ns]")
    order = np.argsort(mat, kind="stable")
    mat_sorted = mat[order]
    avail_sorted = design["outcome_available"].to_numpy(dtype=bool)[order]
    geo_sorted = np.asarray(design.index >= pd.Timestamp(W.train_start))[order]
    purge_delta = np.timedelta64(7 * W.purge_weeks, "D")

    def _train_at(origin_ts):
        cut = np.datetime64(pd.Timestamp(origin_ts).to_datetime64()) - purge_delta
        pos = int(np.searchsorted(mat_sorted, cut, side="right"))
        sel = order[:pos][geo_sorted[:pos] & avail_sorted[:pos]]
        return design.iloc[np.sort(sel)]

    forecasts, fitted_at, resid = {}, {}, {c.id: ([], []) for c in family.candidates}
    for cfg in family.candidates:
        mats, vals = resid[cfg.id]
        for t in fit_ts:
            fitted = fit_candidate(cfg, _train_at(t), origin=t, min_train_examples=Ocfg.min_train_examples)
            fitted_at[(cfg.id, t)] = fitted
            fc = fitted.predict(design.loc[t])
            forecasts[(cfg.id, t)] = fc
            if fc is not None and math.isfinite(fc):
                yv = float(design.loc[t, "y"])
                if math.isfinite(yv):
                    mats.append(pd.Timestamp(design.loc[t, "maturity"]))
                    vals.append(yv - fc)
    for name in BASELINE_LADDER:
        for o in O:
            fitted = fit_baseline(name, _train_at(o), origin=o,
                                  max_p=family.training_only_ar_max_p,
                                  min_train_examples=Ocfg.min_train_examples)
            forecasts[(name, o)] = fitted.predict(design.loc[o])
    per = pd.DataFrame(index=O)
    per["source_available"] = [bool(panel.loc[o, "available"]) for o in O]
    per["outcome_available"] = [bool(design.loc[o, "outcome_available"]) for o in O]
    per["y"] = [float(design.loc[o, "y"]) for o in O]
    for col in _model_columns(family):
        key = col[2:]
        per[col] = [np.nan if forecasts.get((key, o)) is None else float(forecasts[(key, o)]) for o in O]
    for cfg in family.candidates:
        mats, vals = resid[cfg.id]
        res_idx = pd.DatetimeIndex(mats) if mats else pd.DatetimeIndex([])
        res_vals = np.asarray(vals, dtype=float)
        for level in family.intervals.nominal_levels:
            column = []
            for o in O:
                if len(res_idx):
                    sel = (res_idx <= (pd.Timestamp(o) - pd.Timedelta(days=7 * W.purge_weeks)))
                    inner = pd.Series(res_vals[np.asarray(sel)], index=res_idx[np.asarray(sel)])
                else:
                    inner = pd.Series(dtype=float)
                qs = calibrate_interval(fitted_at[(cfg.id, pd.Timestamp(o))], inner,
                                        nominal_levels=family.intervals.nominal_levels,
                                        min_n=family.intervals.min_calibration_residuals)
                q = qs.get(int(level))
                column.append(np.nan if q is None else float(q))
            per[f"q{level}_{cfg.id}"] = column
    per.attrs["source_status"] = status
    return per


def run_study(sources, *, family, announcements=()):
    """Run the preregistered study: 45 disposed cells, cell order, reserved window untouched."""
    W, Ocfg = family.windows, family.origins
    fridays = panel_fridays(W, Ocfg)
    eval_idx = fridays[(fridays >= pd.Timestamp(W.train_start)) & (fridays <= pd.Timestamp(W.dev_end))]
    n_h, n_c = len(family.horizons_weeks), len(family.candidates)
    results = []
    for ti, target in enumerate(family.targets):
        src = sources.get(target) or {"frame": None, "status": "source_missing:unknown"}
        frame, status = src.get("frame"), str(src.get("status", "loaded"))
        for hi, h in enumerate(family.horizons_weeks):
            O = rolling_origins(eval_idx, train_end=W.train_end, dev_end=W.dev_end,
                                reserved_start=W.reserved_start, min_train_weeks=Ocfg.min_train_weeks,
                                step_weeks=Ocfg.step_weeks, horizon_weeks=h, purge_weeks=W.purge_weeks)
            if frame is None or len(O) == 0:
                per = _null_origin_frame(O, family, status)
            else:
                per = _eval_origin_frame(frame, status, fridays=fridays, O=O, family=family,
                                         target=target, horizon_weeks=h, announcements=announcements)
            cells = score_cells(per, target=target, horizon_weeks=h, family=family,
                                cell_index_start=(ti * n_h + hi) * n_c)
            for cell in cells:
                disposition, reason = dispose_with_reason(cell, family.margins)
                cell["disposition"] = disposition
                cell["reason"] = reason
                cell["estimate_type"] = "statistical_forecast" if disposition == "issued" else "unavailable"
                cell["abstention_reason"] = None if disposition == "issued" else disposition
            results.extend(cells)
    return results


def register_family(ledger, family, *, info_cutoffs) -> int:
    """Declare the budget then register every cell; returns new trials (True returns)."""
    card_hash = family.card_ref["card_hash"]
    reason = (f"GLT T09 preregistered family (3 targets x 3 horizons x 5 candidates); "
              f"card {card_hash[:12]}")
    ledger.log_declared_budget(family.n_trials_total, family=family.name, reason=reason)
    new_trials = 0
    for (target, horizon_weeks, candidate) in family.cells():
        ok = ledger.log_trial(family.trial_config(target, horizon_weeks, candidate),
                              family=family.name, info_cutoff=info_cutoffs[(target, horizon_weeks)])
        if ok is True:
            new_trials += 1
    return new_trials


def reconcile_forecast_identity(paths, h41_anchor, *, nonreserve_lines=_outlook.H41_NONRESERVE_LIABILITY_LINES):
    """Project the H.4.1 anchor by forecast changes and re-run the T08 identity."""
    if h41_anchor is None:
        return {"available": False, "reason": "no_h41_table5_anchor_in_inputs", "residual": None}
    missing = [k for k in ("tga_bn", "rrp_bn", "reserves_wresbal_bn") if k not in paths]
    if missing:
        raise ValueError(f"forecast identity needs changes for tga_bn, rrp_bn, reserves_wresbal_bn; missing {missing}")
    d_tga = float(paths["tga_bn"])
    d_rrp = float(paths["rrp_bn"])
    d_res = float(paths["reserves_wresbal_bn"])
    projection = h41_anchor.copy()
    projection[_outlook.H41_TGA_LINE] = projection[_outlook.H41_TGA_LINE] + 1000.0 * d_tga
    projection[_outlook.H41_RRP_OTHERS_LINE] = projection[_outlook.H41_RRP_OTHERS_LINE] + 1000.0 * d_rrp
    projection[_outlook.H41_RESERVES_LINE] = projection[_outlook.H41_RESERVES_LINE] + 1000.0 * d_res
    t08 = _outlook.reconcile_reserve_identity(projection, nonreserve_lines=nonreserve_lines)
    return {
        "available": True,
        "residual": t08["residual"],
        "reconciles": t08["reconciles"],
        "projection": projection,
        "assumption": ("assets and every other H.4.1 line held at the anchor; TGA, RRP Others and "
                       "reserves moved by the forecast changes"),
        "t08": t08,
    }


def _sanitize(value):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            key = str(k)
            if FORBIDDEN_KEY_RE.search(key):
                raise ValueError(f"forbidden card key: {key!r}")
            out[key] = _sanitize(v)
        return out
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    if isinstance(value, pd.Series):
        return {str(k): _sanitize(v) for k, v in value.items()}
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        f = float(value)
        return None if not math.isfinite(f) else round(f, 6)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def result_card(*, family, cells, inputs, ledger_receipt, forecast_identity, as_of) -> dict:
    """Assemble the preregistered result card (floats rounded, NaN/inf dropped)."""
    counts = {d: 0 for d in DISPOSITIONS}
    for cell in cells:
        counts[cell["disposition"]] = counts.get(cell["disposition"], 0) + 1
    supplied = bool(inputs.get("announcements_supplied")) if isinstance(inputs, dict) else False
    receipt = ledger_receipt if isinstance(ledger_receipt, dict) else {}
    margins, intervals = family.margins, family.intervals
    card = {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "authority": AUTHORITY,
        "validated": False,
        "vintage_cohort": family.vintage_cohort,
        "revision_risk": family.revision_risk,
        "preregistration_card_ref": family.card_ref,
        "family": {
            "name": family.name,
            "primary_target": family.primary_target,
            "targets": list(family.targets),
            "horizons_weeks": list(family.horizons_weeks),
            "baselines": list(family.baselines),
            "baseline_labels": {"announced_only": "announced_only" if supplied else "announced_only(empty)"},
            "candidates": [c.as_dict() for c in family.candidates],
            "n_trials_total": family.n_trials_total,
        },
        "windows": family.windows.as_dict(),
        "clocks": family.clocks,
        "information_set_rule": family.information_set_rule,
        "margins": {
            "primary_error": margins.primary_error,
            "secondary_error": margins.secondary_error,
            "min_relative_gain": margins.min_relative_gain,
            "ci_level": margins.ci_level,
            "block_weeks": margins.block_weeks,
            "n_resamples": margins.n_resamples,
            "seed": margins.seed,
            "min_scored_origins": margins.min_scored_origins,
            "coverage_tolerance_points": margins.coverage_tolerance_points,
        },
        "intervals": {
            "nominal_levels": list(intervals.nominal_levels),
            "method": intervals.method,
            "calibration_scope": intervals.calibration_scope,
            "interval_semantics": intervals.interval_semantics,
            "min_calibration_residuals": intervals.min_calibration_residuals,
        },
        "calendar_indicators": list(family.calendar_indicators),
        "inputs": inputs,
        "trial_ledger": {
            "family": receipt.get("family", family.name),
            "literal_n": receipt.get("literal_n"),
            "declared_budget": receipt.get("declared_budget"),
        },
        "forecast_identity": forecast_identity,
        "cells": cells,
        "summary": {"n_cells": len(cells), "dispositions": counts},
        "run": {"as_of": as_of},
    }
    return _sanitize(card)


def write_card(card, path) -> None:
    """Write the card as sorted, indented JSON with a trailing newline."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(card, indent=2, sort_keys=True) + "\n")
