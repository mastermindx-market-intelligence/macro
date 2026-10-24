#!/usr/bin/env python3
"""Render the Systematic Strategies research workspace from a compiled artifact.

This builder is deliberately *pure*. It reads one compiled JSON artifact that
matches the ``systematic_research.v1`` contract, projects it through an
allowlist, and renders ``templates/systematic_strategies.html.j2``. It imports
no engine module — only the published ``lib.us_cash_calendar`` session slate,
which is a pure calendar — performs no network call, reads no account or
credential, and has no production default output path.

The reference clock is explicit. ``--now`` (or the ``now=`` keyword) fixes the
instant every freshness and ordering decision is made against, so the same
inputs plus the same clock render byte-identical HTML. Nothing is stamped from
an ambient wall clock on a page that cannot be trusted.

Contract honesty rules this file enforces (each is load-bearing, not stylistic):

* **Structural violations fail closed.** A wrong ``schema``, a missing or true
  ``live_orders_enabled``, a missing ``RESEARCH_ONLY`` mode, an unknown
  ``status``, a non-zero ``capital_eligible_count``, a strategy that claims
  ``capital_eligible``, or a missing required key all collapse the page to
  ``inputs_blocked`` with metrics unavailable. A corrupt artifact must never
  render as a healthy research result.
* **Metric-level junk degrades, it does not fabricate.** A non-finite or
  wrong-typed metric, an unparseable sample date, and a missing key all render
  that ONE value as "Not available" and raise a visible data-quality note. An
  absent value is never shown as ``0``; a real ``0`` is shown as ``0``.
* **Only allowlisted fields reach the template.** The view is rebuilt field by
  field, so unknown keys (account numbers, fills, credentials, paths) cannot
  leak into public HTML even though the artifact carries them.
* **Artifact values are text, never locators.** Revisions, names, reasons and
  instrument lists are rendered as escaped text only. No href, src, filename or
  output path is ever derived from artifact content, so a revision string such
  as ``../../etc/passwd`` cannot escape the page it appears on.

Usage::

    python -m scripts.render_systematic_strategies --input artifact.json \\
        --output site/systematic_strategies.html --copy-assets

``--output`` is optional; without it the HTML goes to stdout. ``--copy-assets``
copies ``templates/systematic_strategies.css`` next to the output file so the
page's scoped stylesheet is served from the same directory as the page (the
repo's plain-copy template->site asset convention, see
``scripts/check_template_site_sync.py``). It is opt-in: this module never
writes into a site tree on its own.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# The published US cash-equity session slate. Sample boundaries and the record's
# information cutoff are EXCHANGE-SESSION DATE LABELS; only ``generated_at`` and
# ``as_of`` are receipt instants. A weekday arithmetic rule would call holidays,
# one-off closures and half days sessions they are not, so both come from the
# same published calendar the rest of the repo reads. It is a pure calendar: no
# network, no account, no engine module.
from lib import us_cash_calendar  # noqa: E402  (needs _ROOT on sys.path)

ET = us_cash_calendar.ET

DEFAULT_TEMPLATE_DIR = _ROOT / "templates"
TEMPLATE_NAME = "systematic_strategies.html.j2"
SCOPED_CSS_NAME = "systematic_strategies.css"

SCHEMA_ID = "systematic_research.v1"
RESEARCH_MODE = "RESEARCH_ONLY"
KNOWN_STATUSES = frozenset({"research_available", "inputs_blocked"})
KNOWN_STRATEGY_IDS = ("tsmom_200", "rsi2_oversold")
KNOWN_STRATEGY_STATES = frozenset({"research_only", "blocked"})
KNOWN_STANCES = frozenset({"Observe only", "Stand aside"})
KNOWN_HISTORICAL_STATES = frozenset({"available", "unavailable"})
KNOWN_DATA_HEALTH_STATES = frozenset({"ready", "blocked"})

# The two candidate labels are page copy, fixed by the design direction. The
# strategy's real input name from the artifact is shown in the methodology
# section instead — never promoted into the glance tier as an invented label.
CANDIDATE_LABELS = {
    "tsmom_200": "Trend baseline",
    "rsi2_oversold": "Pullback timing",
}

STATE_LABELS = {
    "research_only": "Research only",
    "blocked": "Blocked",
}
HISTORICAL_LABELS = {
    "available": "Historical record available",
    "unavailable": "Historical record unavailable",
}
PROSPECTIVE_LABELS = {"not_started": "Not started"}
PAPER_LABELS = {"not_connected": "Not connected"}
DATA_HEALTH_LABELS = {"ready": "Ready", "blocked": "Blocked"}

# Chinese copy for the page's own fixed strings. The shared header ships a
# language toggle, so a page that leaves its chrome English-only while the
# toggle is on screen is making a claim it does not keep. Artifact-authored
# content — reasons, limitations, instruments, blockers — is DATA in whatever
# language the producer wrote, and is shown verbatim rather than invented into
# Chinese it never carried.
CANDIDATE_LABELS_ZH = {
    "tsmom_200": "趋势基准",
    "rsi2_oversold": "回调择时",
}
STATE_LABELS_ZH = {"research_only": "仅研究", "blocked": "受阻"}
HISTORICAL_LABELS_ZH = {"available": "历史记录可用", "unavailable": "历史记录不可用"}
PROSPECTIVE_LABELS_ZH = {"not_started": "尚未开始"}
PAPER_LABELS_ZH = {"not_connected": "未连接"}
DATA_HEALTH_LABELS_ZH = {"ready": "就绪", "blocked": "受阻"}
TURNOVER_CONVENTION_ZH = (
    "样本合计，非年度值：样本区间内组合成交名义金额除以权益的累加。"
    "样本长度不同的两个候选在此指标上不可直接比较。"
)

UNAVAILABLE = "Not available"

# No future information is allowed. A record stamped after the reference clock
# carries knowledge the reference clock does not have, so its as-of cannot be
# displayed as fact. There is deliberately NO tolerance window: an earlier
# tolerance of 24h accepted a record stamped 15 hours ahead, which is precisely
# the record that must never be shown as healthy. Skew is a producer bug to fix
# at the producer, not something a reader should absorb silently.
MAX_TEXT = 400
MAX_REVISION = 64
MAX_LIST_ITEMS = 40

# Every fail-closed reason is a fixed string from this table. Artifact text is
# never echoed into a reason, so a hostile artifact cannot talk its way into the
# page shell or leak internals through an error string.
BLOCK_REASONS: dict[str, str] = {
    "artifact_missing": "No compiled research record was supplied to this page.",
    "artifact_unreadable": "The compiled research record could not be read.",
    "artifact_not_json": "The compiled research record is not valid JSON.",
    "schema_unsupported": "The research record uses a format this page does not read.",
    "mode_unexpected": "The research record does not declare research-only mode.",
    "live_flag_missing": "The research record does not explicitly confirm that live orders are disabled.",
    "live_flag_enabled": "The research record reports live orders enabled. This workspace never presents trading controls.",
    "status_unknown": "The research record does not declare a state this page can read.",
    "timestamp_invalid": "The research record carries a timestamp this page cannot read.",
    "timestamp_future": "The research record is stamped after the reference clock, so it carries information this page cannot verify.",
    "timestamp_order": "The research record was generated before its own information cutoff, so its two timestamps cannot both be true.",
    "summary_count_mismatch": "The research record's summary counts do not match the candidates it actually carries.",
    "summary_invalid": "The research record's summary counts are missing or malformed.",
    "capital_flag_nonzero": "The research record reports a strategy approved for capital. This workspace is research-only and will not show that result.",
    "strategies_invalid": "The research record's candidate list is missing or malformed.",
    "strategy_duplicate": "The research record lists the same candidate more than once, so its cards and its counts could not agree.",
    "strategy_capital_flag": "A candidate in the research record claims capital eligibility, so the record was not displayed.",
    "strategy_unsupported": "The research record contains a candidate this page does not recognise.",
    "data_health_invalid": "The research record's data health block is missing or malformed.",
    "limitations_invalid": "The research record's limitation list is malformed.",
    "shape_invalid": "The research record is missing required fields.",
}

BLOCK_REASONS_ZH = {
    "artifact_missing": "未向本页提供任何已编译的研究记录。",
    "artifact_unreadable": "无法读取已编译的研究记录。",
    "artifact_not_json": "已编译的研究记录不是有效的 JSON。",
    "schema_unsupported": "该研究记录使用了本页无法读取的格式。",
    "mode_unexpected": "该研究记录未声明仅研究模式。",
    "live_flag_missing": "该研究记录未明确确认实盘下单已禁用。",
    "live_flag_enabled": "该研究记录显示实盘下单已启用。本工作区从不展示交易控件。",
    "status_unknown": "该研究记录未声明本页可读取的状态。",
    "timestamp_invalid": "该研究记录带有本页无法读取的时间戳。",
    "timestamp_future": "该研究记录的时间戳晚于参考时钟，因此含有本页无法核实的信息。",
    "timestamp_order": "该研究记录的生成时间早于其自身的信息截止时间，两个时间戳不可能同时成立。",
    "summary_invalid": "该研究记录的汇总计数缺失或格式错误。",
    "summary_count_mismatch": "该研究记录的汇总计数与其实际携带的候选不一致。",
    "capital_flag_nonzero": "该研究记录显示某策略已获资金批准。本工作区仅供研究，不会展示该结果。",
    "strategies_invalid": "该研究记录的候选列表缺失或格式错误。",
    "strategy_duplicate": "该研究记录重复列出同一候选，其卡片与计数将无法一致。",
    "strategy_capital_flag": "候选中有一项声明具备资金资格，因此该记录未被展示。",
    "strategy_unsupported": "该研究记录包含本页无法识别的候选。",
    "data_health_invalid": "该研究记录的数据健康区块缺失或格式错误。",
    "limitations_invalid": "该研究记录的局限列表格式错误。",
    "shape_invalid": "该研究记录缺少必填字段。",
}

# The unit travels with the label. A bare "3.20" under "Net return per year" is
# an unlabelled number, and an unlabelled number on a research page is a reader
# guessing — the one thing Law 3 (numbers carry meaning) exists to prevent.
#
# The fourth field is the DISPLAY SCALE. Rates and returns are DECIMAL FRACTIONS
# in this contract: ``0.0991`` is 9.91%, ``-0.241`` is -24.10%. Printing the raw
# fraction under a "%" label renders 0.10% for a 9.91% result — a number that is
# not wrong so much as unreadable, and a page that cannot be misread is the
# whole point of carrying the unit. Sharpe ratios and basis points are already in
# their display unit and scale by 1.
METRIC_LABELS = (
    ("net_sharpe", "Net Sharpe ratio", 2, 1),
    ("net_cagr", "Net return per year (%)", 2, 100),
    ("max_drawdown", "Worst peak-to-trough fall (%)", 2, 100),
    ("turnover", "Traded notional in sample (times)", 2, 1),
    ("cost_bps", "Assumed cost per trade, one way (basis points)", 1, 1),
    ("benchmark_sharpe", "Benchmark Sharpe ratio", 2, 1),
)

# Turnover is a SAMPLE TOTAL, not an annual rate: the sum of the portfolio's
# traded-notional/equity fractions across the sample window. Reading it as a
# per-year figure invites comparing a sixteen-year total against a one-year one.
# The convention travels with the number because the figure alone cannot carry it.
TURNOVER_CONVENTION = (
    "Sample total, not annual: the sum of portfolio traded-notional divided by "
    "equity across the sample window. Two candidates with different sample "
    "lengths are not comparable on this measure."
)

METRIC_LABELS_ZH = {
    "net_sharpe": "净夏普比率",
    "net_cagr": "年化净收益率 (%)",
    "max_drawdown": "最大峰谷回撤 (%)",
    "turnover": "样本内成交名义金额 (次)",
    "cost_bps": "单边假想成本 (基点)",
    "benchmark_sharpe": "基准夏普比率",
}


class _Invalid(Exception):
    """A structural contract violation — the page must fail closed."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


# --------------------------------------------------------------------------- #
# small typed readers — every one of these fails CLOSED on a structural fault
# --------------------------------------------------------------------------- #


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _Invalid(code)
    return value


def _require(mapping: Mapping[str, Any], key: str, code: str) -> Any:
    if key not in mapping:
        raise _Invalid(code)
    return mapping[key]


def _text(value: Any, code: str, *, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str):
        raise _Invalid(code)
    # Control characters (including newlines) are stripped so a value can never
    # forge a line break or an attribute boundary in the rendered shell.
    cleaned = "".join(ch for ch in value if ch == "\t" or ord(ch) >= 32)
    return cleaned.strip()[:limit]


def _int(value: Any, code: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _Invalid(code)
    if value < minimum:
        raise _Invalid(code)
    return value


def _exactly_false(value: Any, code: str) -> bool:
    """The live-orders flag must be present and exactly ``false``.

    A missing flag is a failure, not a default: this page refuses to imply a
    research-only state it was never told about.
    """
    if value is False:
        return False
    raise _Invalid(code)


def _string_list(value: Any, code: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise _Invalid(code)
    out: list[str] = []
    for item in list(value)[:MAX_LIST_ITEMS]:
        if not isinstance(item, str):
            raise _Invalid(code)
        cleaned = "".join(ch for ch in item if ch == "\t" or ord(ch) >= 32)
        cleaned = cleaned.strip()[:MAX_TEXT]
        if cleaned:
            out.append(cleaned)
    return out


def _one_of(value: Any, allowed: frozenset[str], code: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise _Invalid(code)
    return value


# --------------------------------------------------------------------------- #
# graceful (metric-level) readers — a bad value here degrades ONE field
# --------------------------------------------------------------------------- #


class _Meter:
    """Collects the data-quality notes raised while degrading single fields."""

    def __init__(self) -> None:
        self.notes: list[str] = []

    def note(self, message: str) -> None:
        if message not in self.notes:
            self.notes.append(message)


def _number(
    value: Any, places: int, scale: float, meter: _Meter, label: str
) -> tuple[str, bool]:
    """Return ``(display_text, is_available)`` for one metric.

    ``None``, a missing key, a bool, a non-numeric type, ``NaN`` and ``±Inf``
    all render as unavailable — never as ``0`` and never as a number the page
    cannot vouch for. ``scale`` converts the contract's decimal fraction into
    the unit the label names (100 for a percent, 1 otherwise); it is applied
    only after the value is known finite, so a non-finite input can never be
    multiplied into something that looks like a number.
    """
    if value is None:
        return UNAVAILABLE, False
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        meter.note(f"{label} was not a usable number and is shown as unavailable.")
        return UNAVAILABLE, False
    number = float(value)
    if not math.isfinite(number):
        meter.note(f"{label} was not a usable number and is shown as unavailable.")
        return UNAVAILABLE, False
    return f"{number * scale:.{places}f}", True


def _parse_stamp(value: Any, code: str, *, now: datetime) -> datetime:
    """Read one receipt INSTANT, normalised to UTC.

    A naive value is read as UTC; an offset value is normalised, so the same
    instant written two ways compares equal. Any instant later than the explicit
    reference clock is rejected outright — there is no tolerance window.
    """
    if not isinstance(value, str) or not value.strip():
        raise _Invalid(code)
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise _Invalid(code) from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    if parsed > now:
        raise _Invalid("timestamp_future")
    return parsed


def _session_day(value: Any, meter: _Meter, label: str) -> date | None:
    """Read one EXCHANGE-SESSION DATE LABEL into a calendar ``date``.

    A sample boundary is a session the exchange traded, not a receipt instant:
    ``2010-01-04`` is that session's own date and must not be shifted a day by a
    UTC conversion. A bare or naive value is therefore read as the calendar date
    it names; only an explicitly offset value is an instant, and it is projected
    into exchange-local time before the date is taken. A junk value degrades to
    ``None`` and raises a visible note — it never becomes today's date.
    """
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        meter.note(f"{label} was not a readable date and is shown as unavailable.")
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        meter.note(f"{label} was not a readable date and is shown as unavailable.")
        return None
    if parsed.tzinfo is None:
        return parsed.date()
    return parsed.astimezone(ET).date()


# --------------------------------------------------------------------------- #
# view projection — an explicit allowlist; nothing else reaches the template
# --------------------------------------------------------------------------- #


def _metric_rows(historical: Mapping[str, Any], meter: _Meter) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, label, places, scale in METRIC_LABELS:
        display, available = _number(historical.get(key), places, scale, meter, label)
        rows.append(
            {
                "label": label,
                "label_zh": METRIC_LABELS_ZH[key],
                "value": display,
                "available": available,
                "note": TURNOVER_CONVENTION if key == "turnover" else "",
                "note_zh": TURNOVER_CONVENTION_ZH if key == "turnover" else "",
            }
        )
    return rows


def _unavailable_rows() -> list[dict[str, Any]]:
    return [
        {
            "label": label,
            "label_zh": METRIC_LABELS_ZH[key],
            "value": UNAVAILABLE,
            "available": False,
            "note": "",
            "note_zh": "",
        }
        for key, label, _places, _scale in METRIC_LABELS
    ]


def _has_metric_schema(historical: Mapping[str, Any]) -> bool:
    """Does the historical block actually carry measurements at all?

    A record may claim ``state: available`` while carrying no metric key
    whatsoever. That is not a historical record with gaps; it is an empty shell
    that would otherwise render as a table of six "Not available" rows while the
    candidate still claimed to be under study.
    """
    return any(key in historical for key, _l, _p, _s in METRIC_LABELS)


def _build_strategy(
    raw: Any, meter: _Meter, *, cutoff_day: date
) -> dict[str, Any]:
    """Project one candidate.

    An id this page cannot label is a structural fault, not a row to hide: the
    candidate list and the summary counts are read together, so dropping an
    unrecognised id would silently make those counts describe a record that no
    longer exists. Duplicate ids are the same fault in a different shape — two
    cards sharing one DOM id, one of the two real candidates truncated away.
    """
    if not isinstance(raw, Mapping):
        raise _Invalid("strategies_invalid")
    strategy_id = _require(raw, "id", "strategies_invalid")
    if not isinstance(strategy_id, str) or strategy_id not in CANDIDATE_LABELS:
        raise _Invalid("strategy_unsupported")
    if _require(raw, "capital_eligible", "strategies_invalid") is not False:
        raise _Invalid("strategy_capital_flag")

    historical_raw = _mapping(
        _require(raw, "historical", "strategies_invalid"), "strategies_invalid"
    )
    historical_state = _one_of(
        _require(historical_raw, "state", "strategies_invalid"),
        KNOWN_HISTORICAL_STATES,
        "strategies_invalid",
    )
    prospective_raw = _mapping(
        _require(raw, "prospective", "strategies_invalid"), "strategies_invalid"
    )
    prospective_state = _one_of(
        _require(prospective_raw, "state", "strategies_invalid"),
        frozenset(PROSPECTIVE_LABELS),
        "strategies_invalid",
    )
    paper_raw = _mapping(
        _require(raw, "paper", "strategies_invalid"), "strategies_invalid"
    )
    paper_state = _one_of(
        _require(paper_raw, "state", "strategies_invalid"),
        frozenset(PAPER_LABELS),
        "strategies_invalid",
    )

    state = _one_of(
        _require(raw, "status", "strategies_invalid"),
        KNOWN_STRATEGY_STATES,
        "strategies_invalid",
    )
    stance = _one_of(
        _require(raw, "stance", "strategies_invalid"), KNOWN_STANCES, "strategies_invalid"
    )
    horizon = _int(
        _require(raw, "horizon_sessions", "strategies_invalid"),
        "strategies_invalid",
        minimum=0,
    )
    reason = _text(_require(raw, "reason", "strategies_invalid"), "strategies_invalid")
    blockers = _string_list(raw.get("blockers"), "strategies_invalid")
    # Required, not defaulted. A missing observation count is an absent
    # measurement; defaulting it to 0 would display "0 observations" beside
    # measured returns, which is the guessed zero this page must never print.
    observations = _int(
        _require(historical_raw, "observations", "strategies_invalid"),
        "strategies_invalid",
        minimum=0,
    )

    instruments = _string_list(raw.get("instruments"), "strategies_invalid")
    invalidation = _string_list(raw.get("invalidation"), "strategies_invalid")
    limitations = _string_list(historical_raw.get("limitations"), "strategies_invalid")

    # Forward counts are required too, and "not started" is a claim about them:
    # a not-started record that also reports registered/graded records is making
    # two contradictory statements, and no reader can tell which one is the truth.
    registered = _int(
        _require(prospective_raw, "registered", "strategies_invalid"),
        "strategies_invalid",
    )
    graded = _int(
        _require(prospective_raw, "graded", "strategies_invalid"), "strategies_invalid"
    )
    if prospective_state == "not_started" and (registered or graded):
        raise _Invalid("strategies_invalid")

    sample_start = _session_day(
        historical_raw.get("sample_start"), meter, "Sample start date"
    )
    sample_end = _session_day(
        historical_raw.get("sample_end"), meter, "Sample end date"
    )

    metrics_available, unavailable_why = _historical_is_measurable(
        historical_raw,
        historical_state=historical_state,
        sample_start=sample_start,
        sample_end=sample_end,
        observations=observations,
        cutoff_day=cutoff_day,
    )
    label = CANDIDATE_LABELS[strategy_id]
    if metrics_available:
        metric_rows = _metric_rows(historical_raw, meter)
    else:
        meter.note(
            f"{label} is recorded as having a historical result, but {unavailable_why} "
            "Its measured results are shown as unavailable."
            if historical_state == "available"
            else f"{label} has no historical record, so its measured results are "
            "shown as unavailable."
        )
        metric_rows = _unavailable_rows()

    return {
        "id": strategy_id,
        "label": label,
        "label_zh": CANDIDATE_LABELS_ZH[strategy_id],
        "name": _text(raw.get("name", ""), "strategies_invalid"),
        "family": _text(raw.get("family", ""), "strategies_invalid"),
        "horizon_sessions": horizon,
        "horizon_text": (
            f"{horizon} sessions"
            if horizon == 1
            else f"{horizon:,} sessions"
        ),
        "state": state,
        "state_label": STATE_LABELS[state],
        "state_label_zh": STATE_LABELS_ZH[state],
        "stance": stance,
        "reason": reason,
        "blockers": blockers,
        "observations": observations,
        "instruments": instruments,
        "invalidation": invalidation,
        "historical": {
            "state": historical_state,
            "state_label": HISTORICAL_LABELS[historical_state],
            "state_label_zh": HISTORICAL_LABELS_ZH[historical_state],
            "available": metrics_available,
            "sample_start": sample_start.isoformat() if sample_start else None,
            "sample_end": sample_end.isoformat() if sample_end else None,
            "metrics": metric_rows,
            "limitations": limitations,
        },
        "prospective": {
            "state": prospective_state,
            "state_label": PROSPECTIVE_LABELS[prospective_state],
            "state_label_zh": PROSPECTIVE_LABELS_ZH[prospective_state],
            "registered": registered,
            "graded": graded,
        },
        "paper": {
            "state": paper_state,
            "state_label": PAPER_LABELS[paper_state],
            "state_label_zh": PAPER_LABELS_ZH[paper_state],
        },
        "next_prerequisite": _next_prerequisite(state, blockers, historical_state, meter),
    }


def _historical_is_measurable(
    historical: Mapping[str, Any],
    *,
    historical_state: str,
    sample_start: date | None,
    sample_end: date | None,
    observations: int,
    cutoff_day: date,
) -> tuple[bool, str]:
    """May this candidate's measured performance actually be shown?

    Returns ``(measurable, reason_it_is_not)``. A record may assert
    ``state: available`` and still fail every one of these — and when it does,
    the honest display is "unavailable", because a return measured over no known
    window, or over a window that ends after the record's own declared cutoff,
    describes nothing this page can vouch for.
    """
    if historical_state != "available":
        return False, "it carries no historical record."
    if sample_start is None or sample_end is None:
        return False, "its sample window has no readable start or end date."
    if sample_start > sample_end:
        return False, "its sample window ends before it starts."
    if sample_end > cutoff_day:
        return False, (
            "its sample ends after the information cutoff the record itself "
            "declares, so it reports sessions the record says it has not seen."
        )
    if observations <= 0:
        return False, "its record carries no observations."
    if not _has_metric_schema(historical):
        return False, "its record carries no measurements."
    return True, ""


def _next_prerequisite(
    state: str,
    blockers: Sequence[str],
    historical_state: str,
    meter: _Meter,
) -> str:
    """The next thing this candidate is waiting on, in the artifact's own words.

    Derived only from real contract fields. When the record names no blocker,
    the honest prerequisite is that nothing is approved yet.
    """
    if blockers:
        return blockers[0]
    if state == "blocked":
        return "The research record marks this candidate blocked and names no specific blocker."
    if historical_state == "unavailable":
        return "A historical record to measure against."
    meter.note(
        "A candidate named no blocker; the outstanding prerequisite shown is that "
        "forward records have not started."
    )
    return "Forward records — forward testing has not started."


def _blocked_view(code: str) -> dict[str, Any]:
    """The fail-closed page.

    It stamps NO timestamp. The record was unreadable, so its generation time is
    unknown — and writing the renderer's own clock into a ``<time datetime=...>``
    would present "now" as the age of a research record that does not exist.
    """
    return {
        "contract_ok": False,
        "status": "inputs_blocked",
        "blocked": True,
        "blocked_reasons": [BLOCK_REASONS.get(code, BLOCK_REASONS["shape_invalid"])],
        "blocked_reasons_zh": [
            BLOCK_REASONS_ZH.get(code, BLOCK_REASONS_ZH["shape_invalid"])
        ],
        "generated_at_iso": None,
        "generated_at_text": "Not available",
        "as_of_text": "Not available",
        "as_of_iso": None,
        "as_of_day": None,
        "freshness": {
            "state": "unknown",
            "label": "Unknown",
            "label_zh": "未知",
            "detail": "",
            "detail_zh": "",
        },
        "mode_label": "Research only",
        "mode_label_zh": "仅研究",
        "turnover_convention": TURNOVER_CONVENTION,
        "turnover_convention_zh": TURNOVER_CONVENTION_ZH,
        "research_only": True,
        "live_orders_enabled": False,
        "candidate_count": 0,
        "evaluated_count": 0,
        "capital_eligible_count": 0,
        "strategies": [],
        "data_health": {"state": "blocked", "state_label": "Blocked", "state_label_zh": DATA_HEALTH_LABELS_ZH["blocked"], "reasons": [], "last_session": None},
        "versions": {"code_revision": None, "data_revision": None},
        "limitations": [],
        "not_shown": [],
        "data_notes": [],
        "stance": "Observe only",
        "stance_detail": "No strategy is approved for capital.",
        "stance_zh": "仅观察",
        "stance_detail_zh": "没有任何策略获得资金批准。",
    }


def build_view(
    report: Any, *, now: datetime | None = None
) -> dict[str, Any]:
    """Project a compiled artifact into the strict view the template consumes.

    Returns a fail-closed view instead of raising: a malformed artifact must
    still render an honest page, never a synthesized successful one.
    """
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    meter = _Meter()
    try:
        return _build_view_checked(report, meter=meter, now=now)
    except _Invalid as exc:
        return _blocked_view(exc.code)


def _freshness(*, as_of: datetime, now: datetime) -> dict[str, Any]:
    """Is this record's information current, judged against the reference clock?

    The test is the published US cash slate: the newest session whose daily bar
    is actually DUE at the reference clock. That is not a weekday rule — it knows
    holidays, one-off closures and half days, and before a full session's 17:00
    ET settle it correctly reports the PREVIOUS session as the newest available.

    A record may still be shown when it is stale; what it may not do is present
    itself as current. Stale means the measured history ends before the newest
    due session, so the page says so in words and never claims a current signal.
    """
    expected = us_cash_calendar.expected_last_session(now)
    record_day = as_of.astimezone(ET).date()
    if record_day < expected:
        return {
            "state": "stale",
            "label": "Stale",
            "label_zh": "已过期",
            "expected_session": expected.isoformat(),
            "record_session": record_day.isoformat(),
            "detail": (
                f"This record's information ends at the {record_day.isoformat()} "
                f"session, but the newest session due at the reference clock is "
                f"{expected.isoformat()}. Everything below is a historical "
                "reconstruction, not current data, and no current signal is claimed."
            ),
            "detail_zh": (
                f"该记录的信息截至 {record_day.isoformat()} 交易日，"
                f"而参考时钟下最新应到的交易日为 {expected.isoformat()}。"
                "以下全部内容均为历史重建，并非当前数据，也未主张任何当前信号。"
            ),
        }
    return {
        "state": "current",
        "label": "Current for the last complete session",
        "label_zh": "截至最近完整交易日",
        "expected_session": expected.isoformat(),
        "record_session": record_day.isoformat(),
        "detail": "",
        "detail_zh": "",
    }


def _build_view_checked(report: Any, *, meter: _Meter, now: datetime) -> dict[str, Any]:
    root = _mapping(report, "shape_invalid")
    if _require(root, "schema", "shape_invalid") != SCHEMA_ID:
        raise _Invalid("schema_unsupported")
    if _require(root, "mode", "shape_invalid") != RESEARCH_MODE:
        raise _Invalid("mode_unexpected")
    if "live_orders_enabled" not in root:
        raise _Invalid("live_flag_missing")
    _exactly_false(root["live_orders_enabled"], "live_flag_enabled")
    status = _one_of(
        _require(root, "status", "shape_invalid"), KNOWN_STATUSES, "status_unknown"
    )

    generated_at = _parse_stamp(
        _require(root, "generated_at", "shape_invalid"), "timestamp_invalid", now=now
    )
    as_of = _parse_stamp(
        _require(root, "as_of", "shape_invalid"), "timestamp_invalid", now=now
    )
    # A record cannot be generated before the information it reports. Both values
    # are normalised to UTC before they are compared, so the ordering holds for a
    # cutoff written as 2026-10-21T16:00:00-04:00 and a generation stamp written
    # as 2026-10-22T18:26:00Z exactly as it holds for two UTC stamps.
    if generated_at < as_of:
        raise _Invalid("timestamp_order")

    # Everything below compares against the record's own DECLARED information
    # cutoff, not against the renderer's wall clock. The cutoff day is the
    # exchange-local date of that instant, because the sample boundaries it is
    # compared with are exchange-session date labels.
    cutoff_day = as_of.astimezone(ET).date()

    source = _mapping(_require(root, "source", "shape_invalid"), "shape_invalid")
    code_revision = _text(
        _require(source, "code_revision", "shape_invalid"), "shape_invalid", limit=MAX_REVISION
    )
    data_revision = _text(
        _require(source, "data_revision", "shape_invalid"), "shape_invalid", limit=MAX_REVISION
    )

    summary = _mapping(_require(root, "summary", "shape_invalid"), "summary_invalid")
    candidate_count = _int(
        _require(summary, "candidate_count", "summary_invalid"), "summary_invalid"
    )
    evaluated_count = _int(
        _require(summary, "evaluated_count", "summary_invalid"), "summary_invalid"
    )
    capital_eligible_count = _int(
        _require(summary, "capital_eligible_count", "summary_invalid"), "summary_invalid"
    )
    if capital_eligible_count != 0:
        raise _Invalid("capital_flag_nonzero")

    raw_strategies = _require(root, "strategies", "strategies_invalid")
    if not isinstance(raw_strategies, Sequence) or isinstance(raw_strategies, (str, bytes)):
        raise _Invalid("strategies_invalid")
    entries = list(raw_strategies)
    if len(entries) > MAX_LIST_ITEMS:
        # A truncated candidate list is a record this page cannot describe: the
        # counts below are checked against the rows actually shown, so silently
        # keeping the first N would make the summary describe a different record.
        raise _Invalid("strategies_invalid")

    # Ids are read before anything is projected, so a duplicate is caught as a
    # duplicate rather than becoming two cards that share one DOM id.
    seen: set[str] = set()
    for raw in entries:
        entry_id = raw.get("id") if isinstance(raw, Mapping) else None
        if not isinstance(entry_id, str) or entry_id not in CANDIDATE_LABELS:
            raise _Invalid("strategy_unsupported")
        if entry_id in seen:
            raise _Invalid("strategy_duplicate")
        seen.add(entry_id)

    strategies = [
        _build_strategy(raw, meter, cutoff_day=cutoff_day) for raw in entries
    ]
    # Deterministic order without dropping anything: the canonical candidate
    # order is applied to exactly the rows that survived validation.
    strategies.sort(key=lambda item: KNOWN_STRATEGY_IDS.index(item["id"]))

    # The summary counts and the candidate rows are read as one claim. A record
    # reporting 17 candidates and 99 evaluations beside two cards is not a
    # record with two cards; it is a record whose counts describe something else,
    # and showing the cards would lend them a credibility they have not earned.
    evaluated_count_actual = sum(1 for item in strategies if item["historical"]["available"])
    if (
        candidate_count != len(strategies)
        or evaluated_count != evaluated_count_actual
    ):
        raise _Invalid("summary_count_mismatch")

    health = _mapping(_require(root, "data_health", "shape_invalid"), "data_health_invalid")
    health_state = _one_of(
        _require(health, "state", "data_health_invalid"),
        KNOWN_DATA_HEALTH_STATES,
        "data_health_invalid",
    )
    last_session_day = _session_day(
        health.get("last_session"), meter, "Latest complete session"
    )
    data_health = {
        "state": health_state,
        "state_label": DATA_HEALTH_LABELS[health_state],
        "state_label_zh": DATA_HEALTH_LABELS_ZH[health_state],
        "reasons": _string_list(health.get("reasons"), "data_health_invalid"),
        "last_session": last_session_day.isoformat() if last_session_day else None,
    }

    limitations = _string_list(_require(root, "limitations", "limitations_invalid"), "limitations_invalid")

    freshness = _freshness(as_of=as_of, now=now)

    if not strategies:
        status = "inputs_blocked"

    stance = "Observe only"
    if not strategies:
        stance_detail = "No strategy is approved for capital."
        stance_detail_zh = "没有任何策略获得资金批准。"
    else:
        count = len(strategies)
        stance_detail = (
            f"{count} candidate{'s' if count != 1 else ''} under study. "
            "No strategy is approved for capital."
        )
        stance_detail_zh = (
            f"正在研究 {count} 个候选。没有任何策略获得资金批准。"
        )

    return {
        "contract_ok": True,
        "status": status,
        "blocked": status != "research_available",
        "blocked_reasons": [],
        "generated_at_iso": generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at_text": generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        "as_of_text": as_of.strftime("%Y-%m-%d %H:%M UTC"),
        "as_of_iso": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of_day": cutoff_day.isoformat(),
        "freshness": freshness,
        "mode_label": "Research only",
        "mode_label_zh": "仅研究",
        "turnover_convention": TURNOVER_CONVENTION,
        "turnover_convention_zh": TURNOVER_CONVENTION_ZH,
        "research_only": True,
        "live_orders_enabled": False,
        "candidate_count": candidate_count,
        "evaluated_count": evaluated_count,
        "capital_eligible_count": 0,
        "strategies": strategies,
        "data_health": data_health,
        "versions": {"code_revision": code_revision, "data_revision": data_revision},
        "limitations": limitations,
        "not_shown": [],
        "data_notes": meter.notes,
        "stance": stance,
        "stance_detail": stance_detail,
        "stance_zh": "仅观察",
        "stance_detail_zh": stance_detail_zh,
    }


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #


def _environment(template_dir: Path | str | None = None) -> Environment:
    directory = Path(template_dir) if template_dir else DEFAULT_TEMPLATE_DIR
    return Environment(
        loader=FileSystemLoader(str(directory)),
        autoescape=True,
        undefined=StrictUndefined,
    )


def render_view(view: Mapping[str, Any], template_dir: Path | str | None = None) -> str:
    """Render an already-projected view. The single template invocation."""
    template = _environment(template_dir).get_template(TEMPLATE_NAME)
    return template.render(
        report=view,
        active_section="research",
        active_page="systematic_strategies",
        nav_prefix="",
        page_css=SCOPED_CSS_NAME,
        seo_title="Systematic Strategies — Research Workspace — MastermindX",
        seo_desc=(
            "A research-only workspace for systematic strategy candidates: what was "
            "measured, what is still missing, and why nothing here is approved for capital."
        ),
        seo_path="systematic_strategies.html",
    )


def render_report(
    report: Any, template_dir: Path | str | None = None, *, now: datetime | None = None
) -> str:
    """Render the workspace page. Pure: no I/O beyond reading templates."""
    return render_view(build_view(report, now=now), template_dir)


def _reject_constant(name: str) -> Any:
    # ``NaN``/``Infinity``/``-Infinity`` are accepted by json.loads by default.
    # They are not JSON, and this artifact's numbers must be finite.
    raise ValueError(f"non-finite JSON constant: {name}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Refuse a JSON object that names the same field twice.

    ``json.loads`` keeps the last occurrence, so a record carrying
    ``"capital_eligible_count": 0, ... "capital_eligible_count": 4`` reads here
    as a clean zero while the bytes on disk say otherwise. Which of the two
    claims the producer meant is not something this page can recover, so the
    artifact is refused instead of half-believed.
    """
    seen: set[str] = set()
    for key, _value in pairs:
        if key in seen:
            raise ValueError(f"duplicate JSON key: {key}")
        seen.add(key)
    return dict(pairs)


def load_artifact(path: Path | str) -> Any:
    """Read and parse one compiled artifact. Raises on unreadable/invalid input."""
    return json.loads(
        Path(path).read_text(encoding="utf-8"),
        parse_constant=_reject_constant,
        object_pairs_hook=_reject_duplicate_keys,
    )


def render_file(
    input_path: Path | str,
    output_path: Path | str,
    *,
    template_dir: Path | str | None = None,
    copy_assets: bool = False,
    now: datetime | None = None,
) -> tuple[Path, bool]:
    """Render ``input_path`` to ``output_path``. Returns ``(path, contract_ok)``.

    An unreadable or invalid artifact is not an error here: it renders the
    fail-closed page, because a broken build artifact must produce an honest
    page rather than a missing one.
    """
    output = Path(output_path)
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    try:
        report = load_artifact(input_path)
    except (OSError, ValueError):
        view = _blocked_view("artifact_unreadable")
    else:
        view = build_view(report, now=now)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_view(view, template_dir), encoding="utf-8")
    if copy_assets:
        source_dir = Path(template_dir) if template_dir else DEFAULT_TEMPLATE_DIR
        shutil.copyfile(source_dir / SCOPED_CSS_NAME, output.parent / SCOPED_CSS_NAME)
    return output, view["contract_ok"]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="render_systematic_strategies",
        description=(
            "Render the Systematic Strategies research workspace from one compiled "
            "systematic_research.v1 artifact. No network, no account lookup, and no "
            "output path is written unless --output is given."
        ),
    )
    parser.add_argument(
        "--input", dest="input_path", help="Path to the compiled research artifact (JSON)."
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        help="Where to write the rendered page. Omit to print to stdout.",
    )
    parser.add_argument(
        "--template-dir",
        default=None,
        help=f"Template directory (default: {DEFAULT_TEMPLATE_DIR}).",
    )
    parser.add_argument(
        "--copy-assets",
        action="store_true",
        help=(
            f"Also copy {SCOPED_CSS_NAME} next to the output file so the page's "
            "scoped stylesheet is served beside it. Off by default."
        ),
    )
    parser.add_argument(
        "--now",
        dest="now",
        default=None,
        help=(
            "Reference clock (ISO 8601, UTC assumed when no offset is given) for "
            "every freshness and ordering decision. Pin it to make a render "
            "reproducible; omitted, the wall clock is used."
        ),
    )
    parser.add_argument(
        "--site",
        action="store_true",
        help=(
            "Route the output through lib.pages.write_page so the shared-shell shim "
            "is injected. Requires --output; refuses to create a site directory."
        ),
    )
    args = parser.parse_args(argv)

    if not args.input_path:
        parser.error("--input is required")
    if args.site and not args.output_path:
        parser.error("--site requires --output")

    now: datetime | None = None
    if args.now:
        try:
            now = _parse_reference_clock(args.now)
        except ValueError:
            print(
                f"--now {args.now!r} is not an ISO 8601 timestamp",
                file=sys.stderr,
            )
            return 2

    if args.output_path:
        output = Path(args.output_path)
        if args.site:
            from lib.pages import write_page  # imported only for an explicit site write

            if not output.parent.is_dir():
                print(
                    f"refusing to create the site directory {output.parent}; "
                    "point --output at an existing site tree.",
                    file=sys.stderr,
                )
                return 2
            html = render_report(
                _safe_load(args.input_path), args.template_dir, now=now
            )
            write_page(output, html)
            print(f"wrote {output}")
            return 0
        path, contract_ok = render_file(
            args.input_path,
            output,
            template_dir=args.template_dir,
            copy_assets=args.copy_assets,
            now=now,
        )
        print(f"wrote {path} ({'contract ok' if contract_ok else 'inputs blocked'})")
        return 0

    sys.stdout.write(
        render_report(_safe_load(args.input_path), args.template_dir, now=now)
    )
    return 0


def _parse_reference_clock(text: str) -> datetime:
    """Read an operator-supplied reference clock. UTC assumed when naive."""
    value = text.strip()
    if value.endswith(("Z", "z")):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_load(input_path: str) -> Any:
    """Load an artifact, or ``None`` when it cannot be read or parsed."""
    try:
        return load_artifact(input_path)
    except (OSError, ValueError):
        return None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())