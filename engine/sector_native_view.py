"""Pure Sector core/history/Brief/action-board projection for a selected runtime generation.

The caller supplies one verified, coherent input set and performs authorization.
This module never loads data, reads configuration, takes the current time, grades
calls, or changes a publication pointer. It does not infer freshness from a poll.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import math
import re
from typing import Any, Literal
from urllib.parse import urlsplit

from lib.sector_action_preview import _ACTNOW_LANES, partition_actnow
from lib.sector_history_contract import (
    RS_HISTORY_HORIZONS, RS_HISTORY_MAX_POINTS, RS_HISTORY_MODE, RS_HISTORY_SCHEMA,
)

MAX_VIEW_BYTES = 4 * 1024 * 1024
# These are explicit bounds of the native representation, not a new source cohort.
MAX_CORE_SECTORS = 100
MAX_HISTORY_TURNS = 256
_SECTOR_ID = re.compile(r"[a-z][a-z0-9_-]{0,79}\Z")
_SECTOR_TICKER = re.compile(r"[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)?\Z")
_MEASURED_READ_SCHEMA = "leadership_rotation_context.measured_group_read/v1"
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_GROUP_FIELDS = (
    "id", "name", "name_zh", "category", "health", "desk_score", "breadth",
    "r10", "alloc_rank", "val_state", "label", "reco",
)
_ROW_FIELDS = (
    "kind", "ticker", "slug", "name", "name_zh", "reco", "label", "label_zh",
    "score", "alloc_rank", "above_trend", "eligible", "durability", "book_wt",
    "validated", "signal_grade", "clean_entry", "clean_quality", "perf_20d_rel",
    "breadth_pct50", "top_members", "rollover_band", "rollover_band_zh",
    "reco_why_en", "reco_why_zh", "rs_pctile", "flip_distance",
)
_FACTOR_FIELDS = ("chip_en", "chip_zh", "tip_en", "tip_zh", "tone")


class SectorViewUnavailable(ValueError):
    """A safe, closed reason code; never attach input or private manifest data."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class SectorViewReceipt:
    """Already-qualified public identity, supplied by the publication adapter."""

    generation_id: str
    source_session: str
    published_at: str
    qualification: Literal["accepted", "stale", "degraded"]
    input_version: str
    # Explicit migration baseline, never inferred from an older secondary file.
    baseline_session: str | None = None


@dataclass(frozen=True)
class SectorViewInputs:
    central: dict[str, Any]
    cycles: dict[str, Any]
    baskets: dict[str, Any]
    handoff: dict[str, Any]
    action_board: dict[str, Any]


def _session(value: Any) -> str:
    if not isinstance(value, str):
        raise SectorViewUnavailable("invalid_source_session")
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError:
        raise SectorViewUnavailable("invalid_source_session") from None
    return value


def _pick(doc: dict, keys: tuple[str, ...]) -> dict:
    result = {}
    for key in keys:
        if key not in doc:
            continue
        value = doc[key]
        # Native fields are scalar, except the existing top-members string list.
        # An unexpected nested object must not smuggle source/private metadata.
        if key == "top_members":
            if value is not None and (not isinstance(value, list)
                                      or any(not isinstance(v, str) for v in value)):
                raise SectorViewUnavailable("invalid_projection_value")
        elif value is not None and not isinstance(value, (str, int, float, bool)):
            raise SectorViewUnavailable("invalid_projection_value")
        result[key] = deepcopy(value)
    return result


def _receipt(receipt: SectorViewReceipt) -> tuple[dict, str]:
    if not isinstance(receipt, SectorViewReceipt):
        raise SectorViewUnavailable("invalid_receipt")
    for token in (receipt.generation_id, receipt.input_version):
        if not isinstance(token, str) or not _TOKEN.fullmatch(token):
            raise SectorViewUnavailable("invalid_receipt")
    source = _session(receipt.source_session)
    baseline = _session(receipt.baseline_session) if receipt.baseline_session else source
    if baseline > source:
        raise SectorViewUnavailable("future_baseline")
    if receipt.qualification not in ("accepted", "stale", "degraded"):
        raise SectorViewUnavailable("invalid_qualification")
    try:
        published = datetime.fromisoformat(receipt.published_at.replace("Z", "+00:00"))
        if published.tzinfo is None or published.utcoffset() is None:
            raise ValueError
    except (AttributeError, TypeError, ValueError):
        raise SectorViewUnavailable("invalid_publication_clock") from None
    return {
        "schema": "sector_native_view.receipt.v1",
        "source": "macro.sector",
        "generation_id": receipt.generation_id,
        "source_session": source,
        "published_at": receipt.published_at,
        "qualification": receipt.qualification,
        "input_version": receipt.input_version,
        "baseline_session": baseline if baseline != source else None,
    }, baseline


def build_brief_series(subject_id: str | None, chart: Any) -> dict | None:
    """The existing Brief's 21 matched observations / 20-session relative wealth.

    Equivalent to templates/_sector_central_brief.js.j2::buildSectorBriefSeries;
    this is a presentation projection of accepted levels, not a new signal.
    """
    if not isinstance(subject_id, str) or not subject_id or not isinstance(chart, dict):
        return None
    dates, benchmark = chart.get("dates"), chart.get("bench")
    baskets = chart.get("baskets")
    values = baskets.get(subject_id) if isinstance(baskets, dict) else None
    if not all(isinstance(v, list) for v in (dates, benchmark, values)):
        return None
    if len(dates) < 21 or len(values) != len(dates) or len(benchmark) != len(dates):
        return None
    dates, values, benchmark = dates[-21:], values[-21:], benchmark[-21:]
    previous = None
    for observed, value, bench in zip(dates, values, benchmark):
        try:
            _session(observed)
        except SectorViewUnavailable:
            return None
        if previous is not None and observed <= previous:
            return None
        previous = observed
        for number in (value, bench):
            if (isinstance(number, bool) or not isinstance(number, (int, float))
                    or not math.isfinite(number) or number <= 0):
                return None
    points = [
        {"date": observed, "value": ((value / values[0]) / (bench / benchmark[0]) - 1) * 100}
        for observed, value, bench in zip(dates, values, benchmark)
    ]
    if any(not math.isfinite(point["value"]) for point in points):
        return None
    return {
        "points": points, "start": dates[0], "end": dates[-1],
        "sessions": 20, "value": points[-1]["value"],
    }


def _safe_href(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) > 1024:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if (parsed.scheme or parsed.netloc or value.startswith("//")
            or "\\" in value or any(part in (".", "..") for part in parsed.path.split("/"))
            or not parsed.path.endswith(".html")):
        return None
    return value


def _board(board: Any, *, audience: str, preview_rows: int) -> dict:
    if not isinstance(board, dict):
        raise SectorViewUnavailable("invalid_action_board")
    for lane, _, _ in _ACTNOW_LANES:
        rows = board.get(lane, [])
        if (not isinstance(rows, list) or len(rows) > 10000
                or any(not isinstance(row, dict) for row in rows)):
            raise SectorViewUnavailable("invalid_action_board")
    lanes, total, withheld_total = {}, 0, 0
    # All slicing comes from the builder's canonical partition, including the
    # shared hold/avoid budget. Unknown top-level fields never bypass the split.
    for key, _, _, preview, withheld in partition_actnow(board, preview_rows):
        total += len(preview) + len(withheld)
        rows = preview + withheld if audience == "entitled" else preview
        visible = []
        for row in rows:
            item = _pick(row, _ROW_FIELDS)
            href = _safe_href(row.get("href"))
            if href is not None:
                item["href"] = href
            visible.append(item)
        hidden = 0 if audience == "entitled" else len(withheld)
        withheld_total += hidden
        lanes[key] = {"rows": visible, "total": len(preview) + len(withheld), "locked": hidden}
    return {"lanes": lanes, "total": total, "locked": withheld_total}


def _typed_fields(doc: Any, *, strings=(), numbers=(), booleans=(), code: str) -> dict:
    """Copy only the declared nullable fields; no coercion or zero substitution."""
    if not isinstance(doc, dict):
        raise SectorViewUnavailable(code)
    out = {}
    for keys, expected in ((strings, str), (numbers, (int, float)), (booleans, bool)):
        for key in keys:
            if key not in doc:
                continue
            value = doc[key]
            if value is not None:
                if not isinstance(value, expected):
                    raise SectorViewUnavailable(code)
                if expected == (int, float) and (isinstance(value, bool) or not math.isfinite(value)):
                    raise SectorViewUnavailable(code)
            out[key] = value
    return out


def _sector_identity(row: Any, code: str) -> tuple[str, str]:
    if (not isinstance(row, dict) or row.get("kind") != "sector"
            or not isinstance(row.get("id"), str) or not _SECTOR_ID.fullmatch(row["id"])
            or not isinstance(row.get("ticker"), str)
            or not _SECTOR_TICKER.fullmatch(row["ticker"])):
        raise SectorViewUnavailable(code)
    return row["id"], row["ticker"]


def _bounded_records(value: Any, limit: int, code: str) -> list:
    if (not isinstance(value, list) or len(value) > limit
            or any(not isinstance(row, dict) for row in value)):
        raise SectorViewUnavailable(code)
    return value


def _measured_read(value: Any, source: str) -> dict:
    code = "invalid_measured_read"
    if (not isinstance(value, dict) or value.get("schema") != _MEASURED_READ_SCHEMA
            or value.get("status") not in ("available", "partial", "unavailable")):
        raise SectorViewUnavailable(code)
    out = _typed_fields(value, strings=("schema", "status", "reason"), code=code)
    containers = ("generation", "cohort", "groups")
    if not any(key in value for key in containers):
        # This exact outage stub is emitted by the canonical central adapter.
        if value["status"] != "unavailable" or value.get("reason") != "projection_error":
            raise SectorViewUnavailable(code)
        return out
    if not all(key in value for key in containers):
        raise SectorViewUnavailable(code)
    out["generation"] = _typed_fields(value["generation"], strings=("session_end", "benchmark"), code=code)
    out["cohort"] = _typed_fields(value["cohort"], numbers=("expected_n", "measured_n"), code=code)
    if _session(out["generation"].get("session_end")) != source:
        raise SectorViewUnavailable("mixed_measured_session")
    if out["generation"].get("benchmark") != "SPY":
        raise SectorViewUnavailable(code)
    expected, measured = out["cohort"].get("expected_n"), out["cohort"].get("measured_n")
    horizon = value["cohort"].get("horizon")
    if (type(expected) is not int or type(measured) is not int
            or not 0 <= measured <= expected <= MAX_CORE_SECTORS or expected == 0
            or horizon not in ("rs_21d", "rs_63d")):
        raise SectorViewUnavailable(code)
    status = "available" if measured == expected else "partial" if measured else "unavailable"
    if value["status"] != status:
        raise SectorViewUnavailable(code)
    out["groups"], seen, ranks = [], set(), []
    for row in _bounded_records(value["groups"], MAX_CORE_SECTORS, code):
        ident = row.get("group_id")
        if not isinstance(ident, str) or not _SECTOR_TICKER.fullmatch(ident) or ident in seen:
            raise SectorViewUnavailable(code)
        seen.add(ident)
        group = _typed_fields(row, strings=("group_id", "name_en", "name_zh"), code=code)
        current = _typed_fields(row.get("current"), strings=("status", "reason"),
                                numbers=("rank", "rs_21d", "rs_63d"), code=code)
        if current.get("status") == "measured":
            if (type(current.get("rank")) is not int or current["rank"] < 1
                    or current.get(horizon) is None or current.get("reason") is not None):
                raise SectorViewUnavailable(code)
            ranks.append(current["rank"])
        elif current.get("status") == "unmeasured":
            if (current.get("rank") is not None or not current.get("reason")
                    or current.get(horizon) is not None):
                raise SectorViewUnavailable(code)
        else:
            raise SectorViewUnavailable(code)
        group["current"] = current
        out["groups"].append(group)
    if len(seen) != expected or sorted(ranks) != list(range(1, measured + 1)):
        raise SectorViewUnavailable(code)
    return out


def _core(central: dict, source: str) -> tuple[dict, dict[str, str]]:
    code = "invalid_sector_core"
    rows, identities, tickers = [], {}, set()
    source_rows = _bounded_records(central.get("sectors"), MAX_CORE_SECTORS, code)
    if not source_rows:
        raise SectorViewUnavailable(code)
    for row in source_rows:
        ident, ticker = _sector_identity(row, code)
        if ident in identities or ticker in tickers or not isinstance(row.get("name"), str) or not row["name"]:
            raise SectorViewUnavailable(code)
        identities[ident] = ticker
        tickers.add(ticker)
        item = _typed_fields(row, strings=("id", "ticker", "kind", "name", "name_zh", "accent"), code=code)
        for block, strings, numbers, booleans in (
            ("momentum", ("lead",), ("rs_21d", "rs_63d", "rs_21d_rank", "rs_rank"), ("above_200d",)),
            ("heat", (), ("heat_1M", "breadth_pct", "adv", "dec"), ()),
            ("rotation", ("state", "state_plain_en", "state_plain_zh"), (), ()),
            ("conviction", ("label_en",), (), ()),
            ("cycle", ("phaseLabel",), (), ()),
        ):
            if block in row:
                item[block] = None if row[block] is None else _typed_fields(
                    row[block], strings=strings, numbers=numbers, booleans=booleans, code=code)
        for block, fields, minimum in (("momentum", ("rs_21d_rank", "rs_rank"), 1),
                                        ("heat", ("adv", "dec"), 0)):
            for key in fields:
                value = (item.get(block) or {}).get(key)
                if value is not None and (value < minimum or value % 1 != 0):
                    raise SectorViewUnavailable(code)
        rows.append(item)
    out = {"as_of": source, "sectors": rows}
    if "measured_read" in central:
        out["measured_read"] = _measured_read(central["measured_read"], source)
    return out, identities


def _history(cycles: dict, source: str, core_ids: dict[str, str]) -> dict:
    code = "invalid_sector_history"
    meta = cycles.get("meta")
    contract = meta.get("rs_history") if isinstance(meta, dict) else None
    expected = {
        "schema": RS_HISTORY_SCHEMA, "mode": RS_HISTORY_MODE,
        "naturally_observed": False, "basis": "tr", "benchmark": "SPY",
        "horizons_sessions": list(RS_HISTORY_HORIZONS),
        "max_points_per_sector": RS_HISTORY_MAX_POINTS,
    }
    if (not isinstance(contract, dict)
            or any(contract.get(key) != value for key, value in expected.items())
            or contract.get("naturally_observed") is not False
            or type(contract.get("max_points_per_sector")) is not int
            or type(contract.get("horizons_sessions")) is not list
            or any(type(v) is not int for v in contract["horizons_sessions"])
            or ("as_of" in contract and contract["as_of"] != source)
            or meta.get("benchmark", "SPY") != "SPY"):
        raise SectorViewUnavailable(code)
    rows, identities, tickers = [], set(), set()
    core_by_ticker = {ticker: ident for ident, ticker in core_ids.items()}
    source_rows = _bounded_records(cycles.get("sectors"), MAX_CORE_SECTORS, code)
    if not source_rows:
        raise SectorViewUnavailable(code)
    for row in source_rows:
        ident, ticker = _sector_identity(row, code)
        if ident in identities or ticker in tickers:
            raise SectorViewUnavailable(code)
        identities.add(ident)
        tickers.add(ticker)
        if ((ident in core_ids and core_ids[ident] != ticker)
                or (ticker in core_by_ticker and core_by_ticker[ticker] != ident)):
            raise SectorViewUnavailable("mixed_sector_identity")
        points, prior = [], ""
        for point in _bounded_records(row.get("rs_history"), RS_HISTORY_MAX_POINTS, code):
            day = _session(point.get("date"))
            if day > source or day <= prior:
                raise SectorViewUnavailable(code)
            prior = day
            projected = _typed_fields(point, strings=("date",), numbers=("rs_21d", "rs_63d"), code=code)
            if any(projected.get(key) is None for key in ("rs_21d", "rs_63d")):
                raise SectorViewUnavailable(code)
            points.append(projected)
        turns, prior = [], ""
        for turn in _bounded_records(row.get("turns"), MAX_HISTORY_TURNS, code):
            day = _session(turn.get("date"))
            if (day > source or day <= prior or turn.get("k") not in ("peak", "trough")
                    or type(turn.get("major")) is not bool or type(turn.get("provisional")) is not bool):
                raise SectorViewUnavailable(code)
            prior = day
            projected = _typed_fields(turn, strings=("date", "k"), numbers=("mag_pct",),
                                      booleans=("major", "provisional"), code=code)
            if projected.get("mag_pct") is not None and projected["mag_pct"] < 0:
                raise SectorViewUnavailable(code)
            turns.append(projected)
        rows.append({"id": ident, "ticker": ticker, "kind": "sector", "rs_history": points, "turns": turns})
    if identities != set(core_ids):
        raise SectorViewUnavailable("mixed_sector_identity")
    # Missing observations stay explicitly empty. Never complete them from
    # another generation, infer observations, or export raw price/cycle internals.
    return {"meta": {"asOf": source, "rs_history": deepcopy(expected)}, "sectors": rows}


def project_sector_view(
    inputs: SectorViewInputs,
    receipt: SectorViewReceipt,
    *,
    audience: Literal["preview", "entitled"],
    preview_rows: int = 3,
) -> dict[str, Any]:
    """Project accepted owner outputs without creating intelligence or authority.

    Audience is a trusted caller decision, not authorization. The API must enforce
    the existing canonical-resource policies even for a preview representation.
    Older basket/Brief inputs require an explicit common baseline in the receipt;
    a mixed or future session is never silently promoted to the current source.
    """
    public_receipt, baseline = _receipt(receipt)
    if audience not in ("preview", "entitled"):
        raise SectorViewUnavailable("invalid_audience")
    if (isinstance(preview_rows, bool) or not isinstance(preview_rows, int)
            or not 0 <= preview_rows <= 100):
        raise SectorViewUnavailable("invalid_preview")
    if not isinstance(inputs, SectorViewInputs) or not all(
        isinstance(doc, dict) for doc in (
            inputs.central, inputs.cycles, inputs.baskets, inputs.handoff, inputs.action_board
        )
    ):
        raise SectorViewUnavailable("invalid_inputs")
    try:
        core_sessions = (inputs.central.get("as_of"), inputs.cycles["meta"].get("asOf"))
        theme = inputs.baskets["theme_intel"]
        context = inputs.handoff["theme_context"]
        secondary_sessions = (
            inputs.baskets.get("as_of"), theme.get("as_of"), context.get("as_of"),
            inputs.action_board.get("as_of"),
        )
        if not all(_session(value) == receipt.source_session for value in core_sessions):
            raise SectorViewUnavailable("mixed_core_sessions")
        if not all(_session(value) == baseline for value in secondary_sessions):
            raise SectorViewUnavailable("mixed_brief_sessions")
    except (KeyError, TypeError, AttributeError):
        raise SectorViewUnavailable("missing_source_contract") from None
    if inputs.action_board.get("schema") != "sector_intelligence_action_board.v1":
        raise SectorViewUnavailable("invalid_action_board_contract")
    leadership = context.get("leadership")
    if not isinstance(leadership, dict):
        raise SectorViewUnavailable("missing_leadership")
    strength = leadership.get("strength")
    if (not isinstance(strength, list) or len(strength) > 1000
            or any(not isinstance(group, dict) for group in strength)):
        raise SectorViewUnavailable("invalid_leadership")
    groups = [_pick(group, _GROUP_FIELDS) for group in strength]
    subject = groups[0] if groups else None
    state = leadership.get("state")
    # Labels are copied from the accepted Macro Brief template, not reclassified.
    titles = {
        "rotating": ("Leadership is rotating.", "领涨正在轮动。"),
        "strain": ("Leadership under pressure.", "领涨开始承压。"),
        "steady": ("Leadership is holding.", "领涨格局延续。"),
    }
    headline = titles.get(state, ("Leadership not measured.", "领涨状态暂无实测。"))
    lead = _pick(leadership, ("state", "days_in_state", "stance_en", "stance_zh"))
    lead["strength"] = groups
    trailing = leadership.get("trailing_leader")
    lead["trailing_leader"] = _pick(trailing, _GROUP_FIELDS) if isinstance(trailing, dict) else None
    series = build_brief_series(subject.get("id") if subject else None, inputs.baskets.get("chart"))
    if series is not None and series["end"] != baseline:
        raise SectorViewUnavailable("comparison_session_mismatch")
    comparison = {
        "status": "available" if series else "unavailable",
        "reason": None if series else "matching_closes_unavailable",
        "subject": deepcopy(subject),
        "basket_kind": ("equal_weight_sector_basket"
                        if subject and str(subject.get("id", "")).startswith("us_sector_")
                        else "theme_basket") if subject else None,
        "benchmark": "SPY",
        "measure": "20_session_relative_wealth",
        # Carry the owner's construction/history disclosure. The chart payload
        # does not declare a uniform price/TR basis, so never infer one here.
        "source_notes": _pick(inputs.baskets, ("construction", "history_note", "note")),
        "price_basis": "not_declared_by_chart",
        "series": series,
    }
    core, core_ids = _core(inputs.central, receipt.source_session)
    history = _history(inputs.cycles, receipt.source_session, core_ids)
    factor = inputs.handoff.get("factor_season")
    data = {
        "schema": "sector_native_view.v1",
        "audience": audience,
        "core": core,
        "history": history,
        "brief": {
            "as_of": baseline,
            "status": "declared_older_baseline" if baseline != receipt.source_session else "available",
            "headline": {"en": headline[0], "zh": headline[1]},
            "leadership": lead,
            "comparison": comparison,
            "factor_season": _pick(factor, _FACTOR_FIELDS) if isinstance(factor, dict) else None,
        },
        "action_board": {
            "as_of": baseline,
            **_board(inputs.action_board.get("action_board"),
                     audience=audience, preview_rows=preview_rows),
        },
    }
    try:
        encoded_data = json.dumps(data, ensure_ascii=False, allow_nan=False,
                                  sort_keys=True, separators=(",", ":")).encode("utf-8")
        # Hash only the authorized representation. Hidden-row changes cannot
        # change a preview hash when visible content and approved counts agree.
        public_receipt["content_sha256"] = hashlib.sha256(encoded_data).hexdigest()
        output = {"data": data, "receipt": public_receipt}
        encoded = json.dumps(output, ensure_ascii=False, allow_nan=False,
                             sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        raise SectorViewUnavailable("invalid_projection_value") from None
    if len(encoded) > MAX_VIEW_BYTES:
        raise SectorViewUnavailable("projection_too_large")
    return output
