#!/usr/bin/env python3
"""Render the Systematic Strategies research workspace from a compiled artifact.

This builder is deliberately *pure*. It reads one compiled JSON artifact that
matches the ``systematic_research.v1`` contract, projects it through an
allowlist, and renders ``templates/systematic_strategies.html.j2``. It imports
no engine module, performs no network call, reads no account or credential, and
has no production default output path.

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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_ROOT = Path(__file__).resolve().parent.parent
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

UNAVAILABLE = "Not available"

# A compiled artifact stamped in the future means the producer's clock (or the
# artifact) is wrong, and an untrustworthy as-of is exactly what must never be
# displayed as a fact. Tolerance absorbs ordinary skew without hiding a real
# clock fault.
FUTURE_TOLERANCE = timedelta(hours=24)

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
    "timestamp_future": "The research record is stamped in the future, so its as-of time cannot be trusted.",
    "summary_invalid": "The research record's summary counts are missing or malformed.",
    "capital_flag_nonzero": "The research record reports a strategy approved for capital. This workspace is research-only and will not show that result.",
    "strategies_invalid": "The research record's candidate list is missing or malformed.",
    "strategy_capital_flag": "A candidate in the research record claims capital eligibility, so the record was not displayed.",
    "strategy_unsupported": "The research record contains a candidate this page does not recognise.",
    "data_health_invalid": "The research record's data health block is missing or malformed.",
    "limitations_invalid": "The research record's limitation list is malformed.",
    "shape_invalid": "The research record is missing required fields.",
}

# The unit travels with the label. A bare "3.20" under "Net return per year" is
# an unlabelled number, and an unlabelled number on a research page is a reader
# guessing — the one thing Law 3 (numbers carry meaning) exists to prevent.
METRIC_LABELS = (
    ("net_sharpe", "Net Sharpe ratio", 2),
    ("net_cagr", "Net return per year (%)", 2),
    ("max_drawdown", "Worst peak-to-trough fall (%)", 2),
    ("turnover", "Annual turnover (times per year)", 2),
    ("cost_bps", "Assumed cost (basis points per trade)", 1),
    ("benchmark_sharpe", "Benchmark Sharpe ratio", 2),
)


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


def _number(value: Any, places: int, meter: _Meter, label: str) -> tuple[str, bool]:
    """Return ``(display_text, is_available)`` for one metric.

    ``None``, a missing key, a bool, a non-numeric type, ``NaN`` and ``±Inf``
    all render as unavailable — never as ``0`` and never as a number the page
    cannot vouch for.
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
    return f"{number:.{places}f}", True


def _parse_stamp(value: Any, code: str, *, now: datetime) -> datetime:
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
    if parsed > now + FUTURE_TOLERANCE:
        raise _Invalid("timestamp_future")
    return parsed


def _parse_day(value: Any, meter: _Meter, label: str) -> str | None:
    """Sample boundaries are display-only. A junk value degrades to ``None``."""
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
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
# view projection — an explicit allowlist; nothing else reaches the template
# --------------------------------------------------------------------------- #


def _metric_rows(historical: Mapping[str, Any], meter: _Meter) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, label, places in METRIC_LABELS:
        display, available = _number(historical.get(key), places, meter, label)
        rows.append({"label": label, "value": display, "available": available})
    return rows


def _build_strategy(raw: Any, meter: _Meter) -> dict[str, Any] | None:
    """Project one candidate, or return ``None`` for an id this page cannot label."""
    if not isinstance(raw, Mapping):
        raise _Invalid("strategies_invalid")
    strategy_id = _require(raw, "id", "strategies_invalid")
    if strategy_id not in CANDIDATE_LABELS:
        # An unknown id cannot be given a truthful candidate label, so it is not
        # shown. It is counted, not silently dropped.
        return None
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
    observations = _int(
        historical_raw.get("observations", 0), "strategies_invalid", minimum=0
    )

    instruments = _string_list(raw.get("instruments"), "strategies_invalid")
    invalidation = _string_list(raw.get("invalidation"), "strategies_invalid")
    limitations = _string_list(historical_raw.get("limitations"), "strategies_invalid")

    metrics_available = historical_state == "available"
    if not metrics_available:
        meter.note(
            f"{CANDIDATE_LABELS[strategy_id]} has no historical record, so its "
            "measured results are shown as unavailable."
        )
    metric_rows = _metric_rows(historical_raw, meter) if metrics_available else [
        {"label": label, "value": UNAVAILABLE, "available": False}
        for _key, label, _places in METRIC_LABELS
    ]

    return {
        "id": strategy_id,
        "label": CANDIDATE_LABELS[strategy_id],
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
        "stance": stance,
        "reason": reason,
        "blockers": blockers,
        "observations": observations,
        "instruments": instruments,
        "invalidation": invalidation,
        "historical": {
            "state": historical_state,
            "state_label": HISTORICAL_LABELS[historical_state],
            "available": metrics_available,
            "sample_start": _parse_day(
                historical_raw.get("sample_start"), meter, "Sample start date"
            ),
            "sample_end": _parse_day(
                historical_raw.get("sample_end"), meter, "Sample end date"
            ),
            "metrics": metric_rows,
            "limitations": limitations,
        },
        "prospective": {
            "state": prospective_state,
            "state_label": PROSPECTIVE_LABELS[prospective_state],
            "registered": _int(prospective_raw.get("registered", 0), "strategies_invalid"),
            "graded": _int(prospective_raw.get("graded", 0), "strategies_invalid"),
        },
        "paper": {"state": paper_state, "state_label": PAPER_LABELS[paper_state]},
        "next_prerequisite": _next_prerequisite(state, blockers, historical_state, meter),
    }


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


def _blocked_view(code: str, *, now: datetime) -> dict[str, Any]:
    return {
        "contract_ok": False,
        "status": "inputs_blocked",
        "blocked": True,
        "blocked_reasons": [BLOCK_REASONS.get(code, BLOCK_REASONS["shape_invalid"])],
        "generated_at_iso": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at_text": "Not available",
        "as_of_text": "Not available",
        "as_of_iso": None,
        "mode_label": "Research only",
        "research_only": True,
        "live_orders_enabled": False,
        "candidate_count": 0,
        "evaluated_count": 0,
        "capital_eligible_count": 0,
        "strategies": [],
        "data_health": {"state": "blocked", "state_label": "Blocked", "reasons": [], "last_session": None},
        "versions": {"code_revision": None, "data_revision": None},
        "limitations": [],
        "not_shown": [],
        "data_notes": [],
        "stance": "Observe only",
        "stance_detail": "No strategy is approved for capital.",
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
        return _blocked_view(exc.code, now=now)


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
    strategies: list[dict[str, Any]] = []
    not_shown = 0
    for raw in list(raw_strategies)[:MAX_LIST_ITEMS]:
        projected = _build_strategy(raw, meter)
        if projected is None:
            not_shown += 1
        else:
            strategies.append(projected)
    if not_shown:
        meter.note(
            f"{not_shown} candidate(s) in the research record are not ones this "
            "page recognises and were not shown."
        )
    # One card per distinct candidate: a duplicated id cannot become a second
    # row that implies two studies exist.
    strategies.sort(key=lambda item: KNOWN_STRATEGY_IDS.index(item["id"]))
    strategies = strategies[: len(KNOWN_STRATEGY_IDS)]

    health = _mapping(_require(root, "data_health", "shape_invalid"), "data_health_invalid")
    health_state = _one_of(
        _require(health, "state", "data_health_invalid"),
        KNOWN_DATA_HEALTH_STATES,
        "data_health_invalid",
    )
    data_health = {
        "state": health_state,
        "state_label": DATA_HEALTH_LABELS[health_state],
        "reasons": _string_list(health.get("reasons"), "data_health_invalid"),
        "last_session": _parse_day(
            health.get("last_session"), meter, "Latest complete session"
        ),
    }

    limitations = _string_list(_require(root, "limitations", "limitations_invalid"), "limitations_invalid")

    if not strategies:
        status = "inputs_blocked"

    stance = "Observe only"
    if not strategies:
        stance_detail = "No strategy is approved for capital."
    else:
        count = len(strategies)
        stance_detail = (
            f"{count} candidate{'s' if count != 1 else ''} under study. "
            "No strategy is approved for capital."
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
        "mode_label": "Research only",
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


def load_artifact(path: Path | str) -> Any:
    """Read and parse one compiled artifact. Raises on unreadable/invalid input."""
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=_reject_constant)


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
        view = _blocked_view("artifact_unreadable", now=now)
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
                _safe_load(args.input_path), args.template_dir
            )
            write_page(output, html)
            print(f"wrote {output}")
            return 0
        path, contract_ok = render_file(
            args.input_path,
            output,
            template_dir=args.template_dir,
            copy_assets=args.copy_assets,
        )
        print(f"wrote {path} ({'contract ok' if contract_ok else 'inputs blocked'})")
        return 0

    sys.stdout.write(render_report(_safe_load(args.input_path), args.template_dir))
    return 0


def _safe_load(input_path: str) -> Any:
    """Load an artifact, or ``None`` when it cannot be read or parsed."""
    try:
        return load_artifact(input_path)
    except (OSError, ValueError):
        return None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())