"""X0 — descriptive release-reaction runner (E0 section 2.H3).

Measures, DESCRIPTIVELY, whether the CPI-core and payrolls release surprise
(first print minus a no-change benchmark) co-moves with the same-day daily
change in four rates (2y nominal, 10y nominal, 10y real, 10y breakeven).
Writes one JSON receipt and one Markdown receipt under ``out_dir`` and nothing
else anywhere. The only tested window is h0 (prior trading-day close to
release-day close); h1, terciles and sign agreement are descriptive.

This is never a prediction, never a sizing input, and never an explanation of
why rates moved. A labelled co-movement is ``DESCRIPTIVE_ONLY``; when the
evidence does not identify one the receipt reports ``NOT_IDENTIFIED`` and the
surface carries the raw window with no slope.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy import stats as sps

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from collectors.fred import load_vintages  # noqa: E402
from engine.challenger_spa_comparison import newey_west_lrvar  # noqa: E402
from engine.desk_placebo import holm_adjust  # noqa: E402
from engine.event_window import _fomc_announcement_dates  # noqa: E402
from engine.grading_stats import wilson_ci  # noqa: E402
from engine.release_target_truth import (  # noqa: E402
    default_vintage_path,
    load_full_vintage_parquets,
    reconstruct_release_target,
)
from engine.trial_ledger import TrialLedger  # noqa: E402
import lib.store  # noqa: E402

# ---------------------------------------------------------------------------
# 2.1 Constants (frozen)
# ---------------------------------------------------------------------------

SCHEMA = "ric_x0_reaction.v1"
TRIAL_FAMILY = "ric_x0_release_reaction_v1"
TRIAL_BUDGET = 8
PROTOCOL_PATH = "research/rates_inflation_command/seat_20261014/E0_RESEARCH_PROTOCOL.md"
PROTOCOL_SHA256 = "87b51dcad66c6f84989675e9cce91eb5b46b3888d60b2e599a8736d87e2309df"
RELEASES = ("CPI", "NFP")                       # tested families, in this order
TESTED_SERIES = {"CPI": "CPILFESL", "NFP": "PAYEMS"}
DESCRIPTIVE_SERIES = {"CPI_HEADLINE": "CPIAUCSL"}
RESPONSES = ("DGS2", "DGS10", "DFII10", "T10YIE")  # FRED store names, percent units
ERAS = {"2010s": ("2010-01-01", "2019-12-31"), "2021+": ("2021-01-01", None)}  # by release day D
SCALE_WINDOW = 24
MIN_EPISODES_PER_ERA = 40
ALPHA = 0.05
PRIOR_CLOSE_MAX_GAP_DAYS = 7
FIRST_PERIOD = "2007-02"
BENCHMARK_LABEL = "change vs a no-change benchmark"
TEST_IDS = tuple(f"{r}:{s}" for r in RELEASES for s in RESPONSES)  # 8 ids, e.g. "CPI:DGS2"

UNITS = {
    "CPI": "pp m/m (first print, 0.1 pp)",
    "NFP": "thousands of jobs m/m (first print)",
}
SCOPE_NOTE = (
    "Descriptive co-movement in daily closes only. Not a prediction, not a "
    "sizing input, and not an explanation of why rates moved."
)
DEFAULT_PPI_RECEIPT = (
    "research/rates_inflation_command/seat_20261014/x0_inputs/"
    "ppi_release_dates_receipt.json"
)
DEFAULT_GDP_RECEIPT = (
    "research/rates_inflation_command/seat_20261014/x0_inputs/"
    "gdp_advance_dates_receipt.json"
)
TIER1_KEYS = ("CPI", "NFP", "PCE", "PPI", "GDP_ADVANCE", "FOMC")
_ERA_KEYS = ("2010s", "2021+")
_ISO_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Episode statuses, in the exclusive precedence order of section 2.4.
STATUS_MISSING_SOURCE = "MISSING_SOURCE"
STATUS_NO_BENCHMARK = "NO_BENCHMARK"
STATUS_MULTI_PERIOD = "MULTI_PERIOD_RELEASE_DAY"
STATUS_AFTER_ASOF = "AFTER_ASOF"
STATUS_INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
STATUS_OUT_OF_ERA = "OUT_OF_ERA"
STATUS_TIER1 = "TIER1_COLLISION"
STATUS_OK = "OK"
STATUS_MISSING_RESPONSE = "MISSING_RESPONSE"
_NO_SURPRISE_STATUSES = (
    STATUS_MISSING_SOURCE,
    STATUS_NO_BENCHMARK,
    STATUS_MULTI_PERIOD,
)


class MissingInput(RuntimeError):
    """A required input store, receipt or response series is absent."""


# ---------------------------------------------------------------------------
# 2.2 Loaders (defaults; every key is injectable through run(loaders=...))
# ---------------------------------------------------------------------------

def default_release_target_loader(root: Path) -> Callable[[str, str], dict]:
    """Per series, load the full-vintage parquet ONCE, then reconstruct."""
    root = Path(root)
    cache: dict[str, pd.DataFrame] = {}

    def load(series_id: str, period: str) -> dict:
        if series_id not in cache:
            vin = load_full_vintage_parquets(default_vintage_path(root, series_id))
            cache[series_id] = vin
        return reconstruct_release_target(
            cache[series_id], series_id=series_id, period=period
        )

    return load


def default_periods_loader() -> Callable[[str], list[str]]:
    """Periods of ``series_id`` in the vintage store, >= FIRST_PERIOD, ascending."""

    def load(series_id: str) -> list[str]:
        v = load_vintages()
        if v is None:
            raise MissingInput(
                f"vintage store missing: cannot enumerate periods for {series_id}"
            )
        sub = v[v["series"] == series_id]
        periods = sorted({pd.Timestamp(p).strftime("%Y-%m") for p in sub["period"]})
        floor = pd.Timestamp(FIRST_PERIOD + "-01")
        return [p for p in periods if pd.Timestamp(p + "-01") >= floor]

    return load


def default_tier1_dates_loader(
    ppi_receipt: dict, gdp_receipt: dict
) -> Callable[[], dict[str, set[str]]]:
    """The frozen tier-1 list: CPI, NFP, PCE, PPI, GDP advance, FOMC."""

    def load() -> dict[str, set[str]]:
        v = load_vintages()
        if v is None:
            raise MissingInput("vintage store missing: cannot build tier-1 date sets")

        def rt_dates(series_id: str) -> set[str]:
            sub = v[v["series"] == series_id]
            return {pd.Timestamp(d).strftime("%Y-%m-%d") for d in sub["realtime_start"]}

        ppi: set[str] = rt_dates("PPIFIS")
        for row in ppi_receipt.get("rows", []):
            for key in ("ppiaco_first_realtime_start", "wpsfd49207_first_realtime_start"):
                val = row.get(key)
                if isinstance(val, str) and _ISO_DAY_RE.match(val):
                    ppi.add(val)
        gdp: set[str] = set()
        for row in gdp_receipt.get("rows", []):
            for key in ("gdp_first_realtime_start", "gdpc1_first_realtime_start"):
                val = row.get(key)
                if isinstance(val, str) and _ISO_DAY_RE.match(val):
                    gdp.add(val)
        return {
            "CPI": rt_dates("CPILFESL"),
            "NFP": rt_dates("PAYEMS"),
            "PCE": rt_dates("PCEPI"),
            "PPI": ppi,
            "GDP_ADVANCE": gdp,
            "FOMC": set(_fomc_announcement_dates()),
        }

    return load


def default_response_loader() -> Callable[[str], pd.Series]:
    """Daily close series from the ``fred`` group of lib.store (NaN dropped)."""

    def load(name: str) -> pd.Series:
        df = lib.store.read("fred", name)
        if df is None:
            raise MissingInput(f"fred response series missing: {name}")
        return df.iloc[:, 0].dropna()

    return load


def default_trial_ledger(root=None) -> TrialLedger:
    if root is None:
        return TrialLedger()
    return TrialLedger(Path(root) / "data" / "trial_ledger.jsonl")


def _hash_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _set_digest(values) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def _rel(path: Path, root: Path) -> str:
    """Path relative to ``root`` so a committed receipt carries no host path."""
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def default_input_files(root: Path) -> list[Path]:
    """Every file the default loaders open (E0 section 8 input provenance)."""
    from collectors.fred import _vintage_path
    from lib.store import _path as _store_path

    cands = [Path(_vintage_path())]
    cands += [
        Path(default_vintage_path(root, s)) for s in ("CPILFESL", "CPIAUCSL", "PAYEMS")
    ]
    cands += [Path(_store_path("fred", n)) for n in RESPONSES]
    return cands


def _read_receipt(path: Path) -> tuple[dict, str]:
    if not path.is_file():
        raise MissingInput(f"receipt file missing: {path}")
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    return json.loads(raw.decode("utf-8")), sha


# ---------------------------------------------------------------------------
# 2.3/2.4 Episodes, surprise, scale, exclusions, windows, eras
# ---------------------------------------------------------------------------

def _month_before(period: str) -> str:
    t = pd.Timestamp(period + "-01") - pd.offsets.MonthBegin(1)
    return t.strftime("%Y-%m")


def _value_of(release: str, rec: dict) -> float | None:
    val = rec.get("published_proxy_1dp") if release == "CPI" else rec.get("payroll_change_thousands")
    if val is None:
        return None
    return float(val)


def _era_of(day: pd.Timestamp) -> str | None:
    lo, hi = ERAS["2010s"]
    if pd.Timestamp(lo) <= day <= pd.Timestamp(hi):
        return "2010s"
    lo2, _ = ERAS["2021+"]
    if day >= pd.Timestamp(lo2):
        return "2021+"
    return None


def _build_release_episodes(
    release: str,
    periods: list[str],
    release_target: Callable[[str, str], dict],
) -> list[dict]:
    series = TESTED_SERIES[release]
    episodes: list[dict] = []
    for idx, period in enumerate(periods):
        if idx == 0:
            continue  # the first period has no prior
        prev_period = _month_before(period)
        cur = release_target(series, period)
        prev = release_target(series, prev_period)
        ep: dict[str, Any] = {
            "release": release,
            "series": series,
            "period": period,
            "release_day": None,
            "first_print": None,
            "naive_prior": None,
            "surprise_raw": None,
            "units": UNITS[release],
            "scale": None,
            "x": None,
            "era": None,
            "status": None,
            "collided_with": [],
            "h0_bp": {y: None for y in RESPONSES},
            "h1_bp": {y: None for y in RESPONSES},
            "missing_response": [],
            "_eligible_for_scale": False,
        }
        if cur.get("status") != "ok" or _value_of(release, cur) is None:
            ep["status"] = STATUS_MISSING_SOURCE
            episodes.append(ep)
            continue
        first_print = _value_of(release, cur)
        day = pd.Timestamp(cur["release_date"])
        ep["release_day"] = day.strftime("%Y-%m-%d")
        if prev.get("status") != "ok" or _value_of(release, prev) is None:
            ep["status"] = STATUS_NO_BENCHMARK
            ep["first_print"] = first_print
            episodes.append(ep)
            continue
        naive_prior = _value_of(release, prev)
        if pd.Timestamp(prev["release_date"]) >= day:
            ep["status"] = STATUS_NO_BENCHMARK
            ep["first_print"] = first_print
            episodes.append(ep)
            continue
        ep["first_print"] = first_print
        ep["naive_prior"] = naive_prior
        ep["surprise_raw"] = first_print - naive_prior
        ep["_day_ts"] = day
        ep["_eligible_for_scale"] = True
        episodes.append(ep)

    # Release-day uniqueness: two or more periods sharing one D poison every
    # episode on that day (one episode per release day cannot pick one).
    by_day: dict[str, int] = {}
    for ep in episodes:
        if ep["release_day"] is not None and ep["surprise_raw"] is not None:
            by_day[ep["release_day"]] = by_day.get(ep["release_day"], 0) + 1
    for ep in episodes:
        if (
            ep["status"] is None
            and ep["release_day"] is not None
            and by_day.get(ep["release_day"], 0) >= 2
        ):
            ep["status"] = STATUS_MULTI_PERIOD
            ep["_eligible_for_scale"] = False

    # Scale: strictly prior, leak-free, the LAST SCALE_WINDOW surprises of this
    # release that have a surprise at all.
    eligible = [
        ep
        for ep in episodes
        if ep["_eligible_for_scale"] and ep["surprise_raw"] is not None
    ]
    eligible.sort(key=lambda e: e["_day_ts"])
    for ep in episodes:
        if ep["status"] is not None or ep["surprise_raw"] is None:
            continue
        day = ep["_day_ts"]
        prior = [e["surprise_raw"] for e in eligible if e["_day_ts"] < day]
        if len(prior) < SCALE_WINDOW:
            ep["status"] = STATUS_INSUFFICIENT_HISTORY
            continue
        window = np.array(prior[-SCALE_WINDOW:], dtype=float)
        scale = float(np.std(window, ddof=1))
        if scale == 0.0 or not math.isfinite(scale):
            ep["status"] = STATUS_INSUFFICIENT_HISTORY
            continue
        ep["scale"] = scale
        ep["x"] = ep["surprise_raw"] / scale
    return episodes


def _apply_exclusions_and_eras(
    episodes: list[dict],
    tier1: dict[str, set[str]],
    asof_ts: pd.Timestamp,
) -> None:
    for ep in episodes:
        day = ep.get("_day_ts")
        if day is not None:
            ep["era"] = _era_of(day)
        if ep["status"] is not None:
            continue
        if day > asof_ts:
            ep["status"] = STATUS_AFTER_ASOF
            continue
        if ep["era"] is None:
            ep["status"] = STATUS_OUT_OF_ERA
            continue
        others = [k for k in TIER1_KEYS if k != ep["release"]]
        day_str = ep["release_day"]
        hit = sorted(k for k in others if day_str in tier1.get(k, set()))
        if hit:
            ep["status"] = STATUS_TIER1
            ep["collided_with"] = hit
            continue
        ep["status"] = STATUS_OK


def _attach_responses(episodes: list[dict], responses: dict[str, pd.Series]) -> None:
    for ep in episodes:
        day = ep.get("_day_ts")
        if day is None:
            continue
        for name, s in responses.items():
            idx = s.index
            pos = idx.searchsorted(day)
            if pos >= len(idx) or idx[pos] != day:
                ep["missing_response"].append(name)
                continue
            if pos == 0:
                ep["missing_response"].append(name)
                continue
            t_prev = idx[pos - 1]
            if (day - t_prev).days > PRIOR_CLOSE_MAX_GAP_DAYS:
                ep["missing_response"].append(name)
                continue
            ep["h0_bp"][name] = 100.0 * float(s.iloc[pos] - s.iloc[pos - 1])
            if pos + 1 < len(idx):
                ep["h1_bp"][name] = 100.0 * float(s.iloc[pos + 1] - s.iloc[pos])
        ep["missing_response"] = sorted(ep["missing_response"])


def _attach_headline(
    episodes: list[dict],
    release_target: Callable[[str, str], dict],
) -> None:
    """Descriptive CPI-headline surprise with its own leak-free scale."""
    for ep in episodes:
        ep["_headline_surprise"] = None
        ep["_headline_scale"] = None
        ep["_headline_x"] = None
        if ep["release"] != "CPI" or ep.get("_day_ts") is None:
            continue
        day = ep["_day_ts"]
        hcur = release_target(DESCRIPTIVE_SERIES["CPI_HEADLINE"], ep["period"])
        hprev = release_target(DESCRIPTIVE_SERIES["CPI_HEADLINE"], _month_before(ep["period"]))
        if hcur.get("status") != "ok" or hcur.get("published_proxy_1dp") is None:
            continue
        if hcur.get("release_date") != ep["release_day"]:
            continue  # headline must share the release day
        if hprev.get("status") != "ok" or hprev.get("published_proxy_1dp") is None:
            continue
        if pd.Timestamp(hprev["release_date"]) >= day:
            continue
        ep["_headline_surprise"] = float(hcur["published_proxy_1dp"]) - float(
            hprev["published_proxy_1dp"]
        )
    cands = [
        e for e in episodes if e.get("_headline_surprise") is not None
    ]
    cands.sort(key=lambda e: e["_day_ts"])
    for ep in episodes:
        if ep.get("_headline_surprise") is None:
            continue
        day = ep["_day_ts"]
        prior = [e["_headline_surprise"] for e in cands if e["_day_ts"] < day]
        if len(prior) < SCALE_WINDOW:
            continue
        window = np.array(prior[-SCALE_WINDOW:], dtype=float)
        scale = float(np.std(window, ddof=1))
        if scale == 0.0 or not math.isfinite(scale):
            continue
        ep["_headline_scale"] = scale
        ep["_headline_x"] = ep["_headline_surprise"] / scale


# ---------------------------------------------------------------------------
# 2.5 Statistic / 2.6 Label
# ---------------------------------------------------------------------------

def _slope_stat(pairs: list[tuple[float, float]]) -> dict:
    """OLS slope of y on x with the owner's HAC long-run variance SE."""
    n = len(pairs)

    def _deg(reason: str) -> dict:
        return {
            "n": n,
            "distinct_years": None,
            "beta_bp_per_sd": None,
            "se": None,
            "z": None,
            "p_normal": None,
            "p_t": None,
            "degenerate_reason": reason,
        }

    if n < 3:
        return _deg("n_below_3")
    x = np.array([p[0] for p in pairs], dtype=float)
    y = np.array([p[1] for p in pairs], dtype=float)
    xt = x - x.mean()
    sxx = float(xt @ xt)
    if sxx == 0.0:
        return _deg("zero_slope_variance")
    beta = float(xt @ y) / sxx
    u = y - y.mean() - beta * xt
    try:
        lrvar = newey_west_lrvar(xt * u)  # owner default lag: no lag argument
    except ValueError:
        return _deg("hac_lrvar_unavailable")
    var = n * lrvar
    if var <= 0.0 or not math.isfinite(var):
        return _deg("se_not_finite")
    se = math.sqrt(var) / sxx
    if se <= 0.0 or not math.isfinite(se):
        return _deg("se_not_finite")
    z = beta / se
    p_normal = 2.0 * float(sps.norm.sf(abs(z)))
    p_t = 2.0 * float(sps.t.sf(abs(z), df=n - 2))
    return {
        "n": n,
        "distinct_years": None,
        "beta_bp_per_sd": beta,
        "se": se,
        "z": z,
        "p_normal": p_normal,
        "p_t": p_t,
        "degenerate_reason": None,
    }


def _stat_pairs(episodes: list[dict], release: str, response: str, era: str | None,
                x_key: str = "x") -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for ep in episodes:
        if ep["release"] != release or ep["status"] != STATUS_OK:
            continue
        if era is not None and ep["era"] != era:
            continue
        xval = ep.get(x_key)
        yval = ep["h0_bp"].get(response)
        if xval is None or yval is None:
            continue
        pairs.append((float(xval), float(yval)))
    return pairs


def _compute_tests(all_episodes: list[dict]) -> dict:
    tests: dict[str, dict] = {}
    for test_id in TEST_IDS:
        release, response = test_id.split(":", 1)
        block = {"eras": {}, "label": None, "reasons": None, "surface": None}
        for era in _ERA_KEYS:
            episodes = [
                ep
                for ep in all_episodes
                if ep["release"] == release
                and ep["status"] == STATUS_OK
                and ep["era"] == era
                and ep["h0_bp"].get(response) is not None
            ]
            years = {int(ep["_day_ts"].year) for ep in episodes}
            stat = _slope_stat(
                [(float(ep["x"]), float(ep["h0_bp"][response])) for ep in episodes]
            )
            stat["distinct_years"] = len(years) if episodes else None
            block["eras"][era] = stat
        tests[test_id] = block
    # Holm needs every test's p first; fill in a second pass.
    # E0 fixes m=8 per era: a degenerate test (p=None) enters Holm as p=1.0 so
    # it can never shrink m and ease the other seven; its own label stays
    # NOT_IDENTIFIED through its degenerate reason.
    for era in _ERA_KEYS:
        pnorm = {
            tid: (
                tests[tid]["eras"][era]["p_normal"]
                if tests[tid]["eras"][era]["p_normal"] is not None
                else 1.0
            )
            for tid in TEST_IDS
        }
        pt = {
            tid: (
                tests[tid]["eras"][era]["p_t"]
                if tests[tid]["eras"][era]["p_t"] is not None
                else 1.0
            )
            for tid in TEST_IDS
        }
        holm_n = holm_adjust(pnorm)
        holm_t = holm_adjust(pt)
        for tid in TEST_IDS:
            blk = tests[tid]["eras"][era]
            # the 1.0 stand-in only protects m; a test with no p reports none
            blk["p_holm_normal"] = holm_n[tid] if blk["p_normal"] is not None else None
            blk["p_holm_t"] = holm_t[tid] if blk["p_t"] is not None else None
            ok_n = blk["p_holm_normal"] is not None and blk["p_holm_normal"] < ALPHA
            ok_t = blk["p_holm_t"] is not None and blk["p_holm_t"] < ALPHA
            blk["clears"] = bool(ok_n and ok_t)
            blk["borderline"] = bool(ok_n != ok_t)
    for tid in TEST_IDS:
        block = tests[tid]
        reasons: list[str] = []
        for era in _ERA_KEYS:
            blk = block["eras"][era]
            if blk["n"] < MIN_EPISODES_PER_ERA:
                reasons.append(f"n_below_40:{era}")
            if not blk["clears"]:
                reasons.append(f"not_significant:{era}")
            if blk["degenerate_reason"] is not None:
                reasons.append(f"degenerate:{era}")
        b1 = block["eras"]["2010s"]["beta_bp_per_sd"]
        b2 = block["eras"]["2021+"]["beta_bp_per_sd"]
        same_sign = (
            b1 is not None
            and b2 is not None
            and b1 != 0.0
            and b2 != 0.0
            and math.copysign(1.0, b1) == math.copysign(1.0, b2)
        )
        if not same_sign:
            reasons.append("sign_flip")
        if reasons:
            block["label"] = "NOT_IDENTIFIED"
            block["reasons"] = reasons
        else:
            block["label"] = "DESCRIPTIVE_ONLY"
            block["reasons"] = []
        block["surface"] = _surface_of(block, all_episodes, tid)
    return tests


def _surface_of(block: dict, all_episodes: list[dict], test_id: str) -> dict:
    release, response = test_id.split(":", 1)
    raw_window: dict[str, dict] = {}
    for era in _ERA_KEYS:
        vals = [
            float(ep["h0_bp"][response])
            for ep in all_episodes
            if ep["release"] == release
            and ep["status"] == STATUS_OK
            and ep["era"] == era
            and ep["h0_bp"].get(response) is not None
        ]
        raw_window[era] = {
            "n": len(vals),
            "h0_mean_bp": float(np.mean(vals)) if vals else None,
            "h0_median_bp": float(np.median(vals)) if vals else None,
        }
    return {
        "label": block["label"],
        "show_slope": block["label"] == "DESCRIPTIVE_ONLY",
        "raw_window": raw_window,
    }


# ---------------------------------------------------------------------------
# 2.7 Descriptives (never tested, never Holm, never labelled)
# ---------------------------------------------------------------------------

def _compute_descriptives(all_episodes: list[dict]) -> dict:
    descriptive: dict[str, Any] = {}

    headline: dict[str, dict] = {}
    for response in RESPONSES:
        headline[response] = {}
        for era in _ERA_KEYS:
            pairs = _stat_pairs(all_episodes, "CPI", response, era, x_key="_headline_x")
            stat = _slope_stat(pairs)
            headline[response][era] = {
                "n": stat["n"],
                "beta_bp_per_sd": stat["beta_bp_per_sd"],
                "se": stat["se"],
                "p_normal": stat["p_normal"],
                "p_t": stat["p_t"],
                "degenerate_reason": stat["degenerate_reason"],
            }
    descriptive["cpi_headline_slope"] = headline

    h1: dict[str, dict] = {}
    for test_id in TEST_IDS:
        release, response = test_id.split(":", 1)
        h1[test_id] = {}
        for era in _ERA_KEYS:
            vals = [
                float(ep["h1_bp"][response])
                for ep in all_episodes
                if ep["release"] == release
                and ep["status"] == STATUS_OK
                and ep["era"] == era
                and ep["h1_bp"].get(response) is not None
            ]
            h1[test_id][era] = {
                "n": len(vals),
                "mean_bp": float(np.mean(vals)) if vals else None,
                "median_bp": float(np.median(vals)) if vals else None,
                "sd_bp": float(np.std(vals, ddof=1)) if len(vals) >= 2 else None,
            }
    descriptive["h1"] = h1

    terciles: dict[str, dict] = {}
    for test_id in TEST_IDS:
        release, response = test_id.split(":", 1)
        terciles[test_id] = {}
        for era in _ERA_KEYS:
            eps = [
                ep
                for ep in all_episodes
                if ep["release"] == release
                and ep["status"] == STATUS_OK
                and ep["era"] == era
                and ep["x"] is not None
                and ep["h0_bp"].get(response) is not None
            ]
            try:
                x = pd.Series([float(ep["x"]) for ep in eps])
                bins = pd.qcut(x, 3, labels=False)
            except ValueError:
                terciles[test_id][era] = {"status": "NOT_COMPUTABLE"}
                continue
            out = []
            for b in (0, 1, 2):
                sel = [eps[i] for i in range(len(eps)) if int(bins.iloc[i]) == b]
                xs = [float(e["x"]) for e in sel]
                ys = [float(e["h0_bp"][response]) for e in sel]
                out.append({
                    "n": len(sel),
                    "x_lo": min(xs) if xs else None,
                    "x_hi": max(xs) if xs else None,
                    "h0_mean_bp": float(np.mean(ys)) if ys else None,
                    "h0_median_bp": float(np.median(ys)) if ys else None,
                })
            terciles[test_id][era] = out
    descriptive["terciles"] = terciles

    sign: dict[str, dict] = {}
    for test_id in TEST_IDS:
        release, response = test_id.split(":", 1)
        sign[test_id] = {}
        for era in _ERA_KEYS:
            eps = [
                ep
                for ep in all_episodes
                if ep["release"] == release
                and ep["status"] == STATUS_OK
                and ep["era"] == era
                and ep["x"] is not None
                and ep["h0_bp"].get(response) is not None
            ]
            used = [
                ep for ep in eps if ep["x"] != 0.0 and ep["h0_bp"][response] != 0.0
            ]
            k = sum(
                1
                for ep in used
                if math.copysign(1.0, float(ep["x"]))
                == math.copysign(1.0, float(ep["h0_bp"][response]))
            )
            n = len(used)
            ci = wilson_ci(k, n) if n > 0 else None
            sign[test_id][era] = {
                "k": k,
                "n": n,
                "share": (k / n) if n else None,
                "wilson95": [ci[0], ci[1]] if ci is not None else None,
                "zero_excluded": len(eps) - n,
            }
    descriptive["sign_agreement"] = sign
    return descriptive


# ---------------------------------------------------------------------------
# 2.8 Receipt, Markdown and the runner surface
# ---------------------------------------------------------------------------

def _round6(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _round6(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round6(v) for v in obj]
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        if not math.isfinite(v):
            return None
        return round(v, 6)
    return obj


def _episode_public(ep: dict) -> dict:
    return {
        "release": ep["release"],
        "series": ep["series"],
        "period": ep["period"],
        "release_day": ep["release_day"],
        "first_print": ep["first_print"],
        "naive_prior": ep["naive_prior"],
        "surprise_raw": ep["surprise_raw"],
        "units": ep["units"],
        "scale": ep["scale"],
        "x": ep["x"],
        "era": ep["era"],
        "status": ep["status"],
        "collided_with": list(ep["collided_with"]),
        "h0_bp": dict(ep["h0_bp"]),
        "h1_bp": dict(ep["h1_bp"]),
        "missing_response": list(ep["missing_response"]),
    }


def _fmt(v: Any, spec: str = ".4f") -> str:
    if v is None:
        return "—"
    return format(float(v), spec)


def _fmt_p(v: Any) -> str:
    if v is None:
        return "—"
    return format(float(v), ".4g")


def _write_markdown(receipt: dict) -> str:
    lines: list[str] = []
    add = lines.append
    add("# X0 release reaction — descriptive receipt")
    add("")
    add(receipt["scope_note"])
    add("")
    add(f"Benchmark: {receipt['benchmark_label']}")
    add("")
    add(
        f"Protocol: {receipt['protocol']['path']} "
        f"(sha256 {receipt['protocol']['sha256']})"
    )
    add("")
    add(f"As-of: {receipt['asof']}")
    add("")
    inputs = receipt.get("inputs", {})
    add("## Inputs")
    add("")
    add("| input | sha256 | rights |")
    add("|---|---|---|")
    for key in ("ppi_dates", "gdp_dates"):
        blk = inputs.get(key) or {}
        rights = blk.get("rights") or {}
        licence = rights.get("licensing", "not recorded")
        add(f"| {blk.get('path', key)} | {blk.get('sha256', '—')} | {licence} |")
    for entry in inputs.get("files", []):
        add(f"| {entry['path']} | {entry['sha256']} | — |")
    add("")
    add("Windows: h0 = prior trading-day close to release-day close (the only "
        "tested window). h1 = release-day close to next trading-day close "
        "(descriptive only).")
    add("")
    for era in _ERA_KEYS:
        lo, hi = ERAS[era]
        add(f"## Tests — era {era} ({lo} .. {hi or 'open'})")
        add("")
        add("| test | n | beta (bp/sd) | se | p_holm_normal | p_holm_t | label |")
        add("|---|---|---|---|---|---|---|")
        for tid in TEST_IDS:
            blk = receipt["tests"][tid]["eras"][era]
            add(
                f"| {tid} | {blk['n']} | {_fmt(blk['beta_bp_per_sd'])} "
                f"| {_fmt(blk['se'])} | {_fmt_p(blk['p_holm_normal'])} "
                f"| {_fmt_p(blk['p_holm_t'])} | {receipt['tests'][tid]['label']} |"
            )
        add("")
    add("## Labels")
    add("")
    for tid in TEST_IDS:
        block = receipt["tests"][tid]
        reasons = ", ".join(block["reasons"]) if block["reasons"] else "—"
        add(f"- {tid}: {block['label']} ({reasons})")
    add("")
    add("## Exclusions and episode counts")
    add("")
    add("| release | status | n |")
    add("|---|---|---|")
    for release in RELEASES:
        for status, n in sorted(receipt["counts"][release].items()):
            add(f"| {release} | {status} | {n} |")
    add("")
    add("MISSING_RESPONSE counts (episode, response) pairs; the per-episode "
        "lists name the response series.")
    add("")
    desc = receipt["descriptive"]
    add("## Descriptive companions — CPI headline co-movement (never tested)")
    add("")
    add("| response | era | n | beta (bp/sd) | se | p_normal | p_t |")
    add("|---|---|---|---|---|---|---|")
    for response in RESPONSES:
        for era in _ERA_KEYS:
            blk = desc["cpi_headline_slope"][response][era]
            add(
                f"| {response} | {era} | {blk['n']} | {_fmt(blk['beta_bp_per_sd'])} "
                f"| {_fmt(blk['se'])} | {_fmt_p(blk['p_normal'])} | {_fmt_p(blk['p_t'])} |"
            )
    add("")
    add("## Descriptive companions — h1 windows (never tested)")
    add("")
    add("| test | era | n | mean (bp) | median (bp) | sd (bp) |")
    add("|---|---|---|---|---|---|")
    for tid in TEST_IDS:
        for era in _ERA_KEYS:
            blk = desc["h1"][tid][era]
            add(
                f"| {tid} | {era} | {blk['n']} | {_fmt(blk['mean_bp'])} "
                f"| {_fmt(blk['median_bp'])} | {_fmt(blk['sd_bp'])} |"
            )
    add("")
    add("## Descriptive companions — h0 by surprise tercile (never tested)")
    add("")
    add("| test | era | tercile | n | x range | h0 mean (bp) | h0 median (bp) |")
    add("|---|---|---|---|---|---|---|")
    for tid in TEST_IDS:
        for era in _ERA_KEYS:
            blocks = desc["terciles"][tid][era]
            if isinstance(blocks, dict):
                add(f"| {tid} | {era} | not computable | — | — | — | — |")
                continue
            for i, blk in enumerate(blocks, start=1):
                xr = (
                    f"[{_fmt(blk['x_lo'], '.3f')}, {_fmt(blk['x_hi'], '.3f')}]"
                    if blk["x_lo"] is not None else "—"
                )
                add(
                    f"| {tid} | {era} | {i} | {blk['n']} | {xr} "
                    f"| {_fmt(blk['h0_mean_bp'])} | {_fmt(blk['h0_median_bp'])} |"
                )
    add("")
    add("## Descriptive companions — sign agreement (never tested)")
    add("")
    add("| test | era | k | n | share | wilson 95% | zero excluded |")
    add("|---|---|---|---|---|---|---|")
    for tid in TEST_IDS:
        for era in _ERA_KEYS:
            blk = desc["sign_agreement"][tid][era]
            ci = (
                f"[{_fmt(blk['wilson95'][0], '.3f')}, {_fmt(blk['wilson95'][1], '.3f')}]"
                if blk["wilson95"] else "—"
            )
            add(
                f"| {tid} | {era} | {blk['k']} | {blk['n']} "
                f"| {_fmt(blk['share'], '.3f')} | {ci} | {blk['zero_excluded']} |"
            )
    add("")
    return "\n".join(lines) + "\n"


def run(
    root,
    out_dir,
    *,
    asof=None,
    declare_budget=False,
    loaders=None,
    ppi_dates_path=None,
    gdp_dates_path=None,
) -> dict:
    """Build the X0 descriptive receipt and write it under ``out_dir``."""
    root = Path(root)
    out_dir = Path(out_dir)
    loaders = dict(loaders or {})

    # A drifted protocol may never produce a receipt (or a ledger row) that
    # claims E0: fail closed before declaring or writing anything.
    protocol_file = root / PROTOCOL_PATH
    protocol_sha = (
        hashlib.sha256(protocol_file.read_bytes()).hexdigest()
        if protocol_file.is_file()
        else None
    )
    if protocol_sha is not None and protocol_sha != PROTOCOL_SHA256:
        raise MissingInput(
            f"protocol sha256 mismatch: expected {PROTOCOL_SHA256}, found {protocol_sha}"
        )

    # The declared budget is logged exactly once, before any computation,
    # only when the flag is set. The default ledger is bound to ``root`` so
    # the run never appends to a cwd-relative ledger.
    if declare_budget:
        ledger_factory = loaders.get("trial_ledger") or (
            lambda: default_trial_ledger(root)
        )
        ledger = ledger_factory() if callable(ledger_factory) else ledger_factory
        ledger.log_declared_budget(
            TRIAL_BUDGET,
            family=TRIAL_FAMILY,
            reason=f"E0 H3 {PROTOCOL_PATH} sha256={PROTOCOL_SHA256}",
        )

    ppi_path = Path(ppi_dates_path) if ppi_dates_path else root / DEFAULT_PPI_RECEIPT
    gdp_path = Path(gdp_dates_path) if gdp_dates_path else root / DEFAULT_GDP_RECEIPT
    ppi_receipt, ppi_sha = _read_receipt(ppi_path)
    gdp_receipt, gdp_sha = _read_receipt(gdp_path)

    release_target = loaders.get("release_target") or default_release_target_loader(root)
    periods_loader = loaders.get("periods") or default_periods_loader()
    tier1_loader = loaders.get("tier1_dates") or default_tier1_dates_loader(
        ppi_receipt, gdp_receipt
    )
    response_loader = loaders.get("response") or default_response_loader()

    responses = {name: response_loader(name) for name in RESPONSES}
    if asof is None:
        asof_ts = min(s.index.max() for s in responses.values())
    else:
        asof_ts = pd.Timestamp(asof)
    asof_str = pd.Timestamp(asof_ts).strftime("%Y-%m-%d")

    tier1 = tier1_loader()

    # Hash every file the default loaders open; an injected loader opens no
    # default file, so the list is only built when all four are defaults.
    files: list[dict[str, str]] = []
    file_lister = loaders.get("input_files")
    if file_lister is None and not any(
        k in loaders for k in ("release_target", "periods", "tier1_dates", "response")
    ):
        file_lister = default_input_files
    if file_lister is not None:
        for p in file_lister(root):
            if Path(p).is_file():
                files.append({"path": _rel(p, root), "sha256": _hash_file(p)})

    all_episodes: list[dict] = []
    for release in RELEASES:
        series = TESTED_SERIES[release]
        periods = periods_loader(series)
        eps = _build_release_episodes(release, periods, release_target)
        _apply_exclusions_and_eras(eps, tier1, asof_ts)
        _attach_responses(eps, responses)
        if release == "CPI":
            _attach_headline(eps, release_target)
        else:
            for ep in eps:
                ep["_headline_surprise"] = None
                ep["_headline_scale"] = None
                ep["_headline_x"] = None
        all_episodes.extend(eps)

    tests = _compute_tests(all_episodes)
    descriptive = _compute_descriptives(all_episodes)

    counts: dict[str, dict[str, int]] = {}
    for release in RELEASES:
        counts[release] = {}
    for ep in all_episodes:
        bucket = counts[ep["release"]]
        bucket[ep["status"]] = bucket.get(ep["status"], 0) + 1
        if ep["missing_response"]:
            bucket[STATUS_MISSING_RESPONSE] = (
                bucket.get(STATUS_MISSING_RESPONSE, 0) + len(ep["missing_response"])
            )

    family_summary = {
        label: sum(1 for t in tests.values() if t["label"] == label)
        for label in ("DESCRIPTIVE_ONLY", "NOT_IDENTIFIED")
    }

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "protocol": {"path": PROTOCOL_PATH, "sha256": protocol_sha},
        "asof": asof_str,
        "benchmark_label": BENCHMARK_LABEL,
        "scope_note": SCOPE_NOTE,
        "inputs": {
            "release_series": {
                "tested": dict(TESTED_SERIES),
                "descriptive": dict(DESCRIPTIVE_SERIES),
            },
            "responses": {
                name: {
                    "last_date": s.index.max().strftime("%Y-%m-%d"),
                    "n_obs": int(len(s)),
                }
                for name, s in responses.items()
            },
            "ppi_dates": {
                "path": _rel(ppi_path, root),
                "sha256": ppi_sha,
                "rows": len(ppi_receipt.get("rows", [])),
                "rights": ppi_receipt.get("rights"),
            },
            "gdp_dates": {
                "path": _rel(gdp_path, root),
                "sha256": gdp_sha,
                "rows": len(gdp_receipt.get("rows", [])),
                "rights": gdp_receipt.get("rights"),
            },
            "ppi_date_disagreements": [
                r.get("period")
                for r in ppi_receipt.get("rows", [])
                if r.get("agree") is False
            ],
            "tier1_counts": {key: len(tier1.get(key, set())) for key in TIER1_KEYS},
            "tier1_digests": {
                key: _set_digest(tier1.get(key, set())) for key in TIER1_KEYS
            },
            "files": files,
        },
        "deviations": [],
        "trial": {
            "family": TRIAL_FAMILY,
            "budget": TRIAL_BUDGET,
            "declared": bool(declare_budget),
        },
        "episodes": [_episode_public(ep) for ep in all_episodes],
        "counts": counts,
        "tests": tests,
        "family_summary": family_summary,
        "descriptive": descriptive,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    receipt = _round6(receipt)
    (out_dir / "x0_reaction.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=1, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "x0_reaction.md").write_text(_write_markdown(receipt), encoding="utf-8")
    return receipt


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="x0_reaction",
        description="X0 descriptive release-reaction runner (E0 section 2.H3)",
    )
    parser.add_argument("--root", default=".", help="repo root (default: cwd)")
    parser.add_argument("--out-dir", required=True, help="receipt output directory")
    parser.add_argument("--asof", default=None, help="information cutoff YYYY-MM-DD")
    parser.add_argument("--ppi-dates", default=None, help="PPI receipt JSON path")
    parser.add_argument("--gdp-dates", default=None, help="GDP advance receipt JSON path")
    parser.add_argument(
        "--declare-budget",
        action="store_true",
        help="declare the 8-test budget through TrialLedger before computing",
    )
    args = parser.parse_args(argv)
    run(
        Path(args.root),
        Path(args.out_dir),
        asof=args.asof,
        declare_budget=args.declare_budget,
        ppi_dates_path=args.ppi_dates,
        gdp_dates_path=args.gdp_dates,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
