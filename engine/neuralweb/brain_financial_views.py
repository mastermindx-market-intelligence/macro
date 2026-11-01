"""Closed financial display snapshots for Brain's existing chart/history owners.

No authentication, retrieval, financial normalization or durable store lives here.
The gateway must dispatch the canonical reader under the current user's authority
before calling compile_financial_widget. A source_ref never grants read access.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import date
from typing import Any, Callable
from urllib.parse import urlsplit

from engine.quote_resolution import safe_symbol

VERSION = 2
NORMALIZER_VERSION = "terminal-statements-38723cef-v1"
MAX_BYTES = 131072
MAX_WIDGETS = 4
TEMPLATES = ("price", "financial_statement", "company", "transcript")
_READERS = {
    "price": {"get_quote"},
    "financial_statement": {"read_financial_statements"},
    "company": {"get_fundamentals"},
    "transcript": {"read_earnings_evidence", "get_earnings"},
}
_VIEWS = {
    "price": {"range"}, "financial_statement": {"statement", "basis", "period_count", "metric"},
    "company": set(), "transcript": {"transcript_id", "focus"},
}
_ENUMS = {
    "statement": ("income", "balance", "cashflow"), "basis": ("annual", "interim"),
    "range": ("1M", "3M", "6M", "YTD", "1Y", "MAX"),
}
_BLOCKS = {
    "income": ("revenue", "cogs", "gross_profit", "opex", "op_income", "nonop_income",
               "pretax_income", "taxes", "net_income", "eps_basic", "eps_diluted", "ebitda"),
    "balance": ("assets", "assets_st", "assets_lt", "liabilities", "liab_st", "liab_lt",
                "equity", "debt", "cash", "net_debt"),
    "cashflow": ("cfo", "cfi", "cff", "capex", "fcf"),
}
_ENUMS["metric"] = tuple(dict.fromkeys(key for keys in _BLOCKS.values() for key in keys))
_META_ARRAYS = {
    "periods", "period_start", "source_period_start", "period_end", "fiscal_year",
    "period_kind", "period_number", "source_period_label", "is_cumulative",
    "normalization_method", "source_family_by_period", "src_by_period",
    "filed_by_period", "restated_by_period",
}
_META_ENUMS = {
    "reporting_cadence": {"annual", "quarterly", "semiannual", "mixed"},
    "flow_basis": {"as_reported", "cumulative_ytd", "discrete_period", "mixed_period"},
    "source_market": {"us", "cn", "hk", "ca", "intl", "crypto"},
    "source_family": {"industrial", "bank", "insurer", "financial_services", "ambiguous", "other"},
    "source_family_basis": {"profile_sector_absent_industrial_structure"},
}
_ARRAY_ENUMS = {
    "period_kind": {"quarter", "half_year", "full_year", "year_to_date"},
    "normalization_method": {"as_reported", "as_reported_ytd", "difference_from_prior_ytd",
                             "unavailable_missing_base"},
    "source_family_by_period": _META_ENUMS["source_family"],
}
_TITLE = {"price": "Price and trend", "financial_statement": "Financial statements",
          "company": "Company brief", "transcript": "Earnings call evidence"}
_UNSAFE = re.compile(r"<\s*[/!a-z]|[\x00-\x08\x0b\x0c\x0e-\x1f\u202a-\u202e\u2066-\u2069]", re.I)


class FinancialViewError(ValueError):
    pass


def _need(condition: bool, reason: str) -> None:
    if not condition:
        raise FinancialViewError(reason)


def _text(value: Any, limit: int = 500, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    _need(isinstance(value, str) and len(value) <= limit and not _UNSAFE.search(value), "invalid_text")
    return value


def _num(value: Any, nullable: bool = True) -> int | float | None:
    if value is None and nullable:
        return None
    _need(type(value) in (int, float) and math.isfinite(value) and abs(value) <= 1e15, "invalid_number")
    return value


def _encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def _bounded(value: Any) -> None:
    _need(len(_encoded(value)) <= MAX_BYTES, "snapshot_too_large")


def _sha(value: Any) -> str:
    return hashlib.sha256(_encoded(value)).hexdigest()


def _closed(value: Any, fields: set[str]) -> None:
    _need(isinstance(value, dict) and set(value) == fields, "unknown_or_missing_fields")


def _url(value: Any) -> str | None:
    if value is None or value == "":
        return None
    value = _text(value, 2000)
    parsed = urlsplit(value)
    _need(parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username
          and not parsed.password, "invalid_source_url")
    return value


def normalize_request(params: Any) -> dict:
    _need(isinstance(params, dict) and not set(params) - {"template", "symbol", "source_ref", "view"}, "invalid_request")
    _need(len(_encoded(params)) <= 4096, "request_too_large")
    template = params.get("template")
    _need(template in TEMPLATES, "unknown_template")
    raw_symbol = params.get("symbol")
    symbol = safe_symbol(_text(raw_symbol, 40)) if raw_symbol else None
    ref = params.get("source_ref")
    _need(ref is None or (isinstance(ref, str) and bool(re.fullmatch(r"fin_[a-f0-9]{64}", ref))), "invalid_source_ref")
    _need(bool(symbol or ref), "symbol_or_ref_required")
    view = params.get("view") or {}
    _need(isinstance(view, dict) and not set(view) - set().union(*_VIEWS.values()), "invalid_view")
    view = {k: v for k, v in view.items() if v is not None}
    _need(not set(view) - _VIEWS[template], "incompatible_view")
    for key, value in view.items():
        if key in _ENUMS:
            _need(value in _ENUMS[key], "invalid_view_enum")
        elif key == "period_count":
            _need(type(value) is int and 1 <= value <= 8, "invalid_period_count")
        else:
            _text(value, 200)
    if template == "price":
        view = {"range": "1Y", **view}
    elif template == "financial_statement":
        view = {"statement": "income", "basis": "annual", "period_count": 4, **view}
        if "metric" in view:
            _need(view["metric"] in _BLOCKS[view["statement"]], "incompatible_metric")
    return {"template": template, "symbol": symbol, "source_ref": ref, "view": view}


def financial_widget_tool_schema() -> dict:
    properties = {key: {"type": ["string", "null"], "enum": [*values, None]}
                  for key, values in _ENUMS.items()}
    properties.update({
        "period_count": {"type": ["integer", "null"], "minimum": 1, "maximum": 8},
        "transcript_id": {"type": ["string", "null"], "maxLength": 200},
        "focus": {"type": ["string", "null"], "maxLength": 200},
    })
    return {"name": "render_financial_widget", "description":
        "Show a ready-made financial widget from authorized existing sources in one call. "
        "Choose price, company, financial_statement or transcript and a symbol. "
        "The host fetches data, labels sources and provides local controls; do not build rows or repeat bulk data. "
        "An optional source_ref reuses only a completed financial snapshot in this turn. "
        "Statements use canonical Terminal semantics; never describe raw YTD values as discrete quarters. "
        "Exact transcript evidence remains member-gated; public summaries are labelled.",
        "input_schema": {"type": "object", "additionalProperties": False,
            "properties": {
                "template": {"type": "string", "enum": list(TEMPLATES)},
                "symbol": {"type": ["string", "null"], "maxLength": 40},
                "source_ref": {"type": ["string", "null"], "maxLength": 68},
                "view": {"type": "object", "additionalProperties": False, "properties": properties},
            }, "required": ["template"]}}


def _period_set(raw: Any) -> dict | None:
    if raw is None:
        return None
    _need(isinstance(raw, dict), "invalid_statement_set")
    periods = raw.get("periods")
    _need(isinstance(periods, list) and len(periods) <= 160, "invalid_periods")
    n = len(periods)
    out: dict = {}
    for key in _META_ARRAYS:
        if key not in raw:
            continue
        values = raw[key]
        _need(isinstance(values, list) and len(values) <= n, "unaligned_metadata")
        for value in values:
            if key in ("is_cumulative", "restated_by_period"):
                _need(type(value) is bool, "invalid_boolean")
            elif key == "period_number":
                _need(value is None or (type(value) is int and 1 <= value <= 4), "invalid_period_number")
            elif key in _ARRAY_ENUMS:
                _need(value in _ARRAY_ENUMS[key], "invalid_period_metadata")
            else:
                _text(value, 160, nullable=key in {"period_start", "source_period_start", "filed_by_period"})
        out[key] = copy.deepcopy(values)
    for key, choices in _META_ENUMS.items():
        if key in raw:
            _need(raw[key] in choices, "invalid_statement_metadata")
            out[key] = raw[key]
    for block, fields in _BLOCKS.items():
        raw_block = raw.get(block) or {}
        _need(isinstance(raw_block, dict), "invalid_statement_block")
        out[block] = {}
        for field in fields:
            values = raw_block.get(field, [])
            _need(isinstance(values, list) and len(values) <= n, "unaligned_values")
            out[block][field] = [_num(v) for v in values]
    if "vendor_gaps" in raw:
        gaps = raw["vendor_gaps"]
        _need(isinstance(gaps, dict) and not set(gaps) - set(_BLOCKS), "invalid_vendor_gaps")
        out["vendor_gaps"] = {}
        for block, fields in gaps.items():
            _need(isinstance(fields, list) and len(fields) <= 20
                  and all(f in _BLOCKS[block] for f in fields), "invalid_vendor_gaps")
            out["vendor_gaps"][block] = list(fields)
    return out


def _statement_data(result: dict) -> dict:
    fund = result.get("fund", result)
    _need(isinstance(fund, dict) and fund.get("schema") == "mastermind.fund/v1", "invalid_fund_schema")
    statements = fund.get("statements") or {}
    _need(isinstance(statements, dict), "invalid_statements")
    out = {
        "schema": "mastermind.fund/v1", "ticker": safe_symbol(fund.get("ticker")),
        "asof": _text(fund.get("asof"), 80, True),
        "quote_currency": _text(fund.get("quote_currency"), 16, True),
        "stmt_currency": _text(fund.get("stmt_currency"), 16, True),
        "src": {k: _text((fund.get("src") or {}).get(k), 160, True)
                for k in ("statements", "statement_lineage")},
        "profile": {"sector": _text((fund.get("profile") or {}).get("sector"), 160, True)},
        "statements": {key: _period_set(statements.get(key)) for key in ("annual", "quarterly")},
    }
    _need(bool(out["ticker"]), "missing_identity")
    _need(any(s and s.get("periods") for s in out["statements"].values()), "statements_unavailable")
    return {"fund": out}


def _price_data(result: dict) -> dict:
    quote = result.get("quote", result)
    _need(isinstance(quote, dict), "invalid_quote")
    clean = {key: _num(quote.get(key)) for key in ("price", "prev_close", "change_pct")}
    _need(clean["price"] is not None and clean["price"] > 0, "quote_unavailable")
    clean.update({
        "as_of": _text(quote.get("as_of"), 80, True),
        "source": _text(quote.get("source"), 160, True),
        "live": quote.get("live") if type(quote.get("live")) is bool else None,
        "delayed_min": _num(quote.get("delayed_min")),
    })
    bars = result.get("bars") or []
    _need(isinstance(bars, list) and len(bars) <= 600, "invalid_bars")
    normalized = []
    previous = ""
    for bar in bars:
        _need(isinstance(bar, dict), "invalid_bar")
        day = _text(bar.get("date"), 10)
        _need(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", day)), "invalid_bar_date")
        date.fromisoformat(day)
        _need(day > previous, "unordered_bars")
        previous = day
        # The card is a daily-close trend. The existing chart owner may supply
        # synthetic OHLC for close-only markets; never export those as measured wicks.
        clean_bar = {"date": day, "close": _num(bar.get("close"), False)}
        _need(clean_bar["close"] > 0, "invalid_close")
        normalized.append(clean_bar)
    return {
        "symbol": safe_symbol(quote.get("symbol") or result.get("symbol")), "quote": clean,
        "bars": normalized, "bar_interval": "1d",
        "history_asof": _text(result.get("history_asof"), 80, True),
        "currency": _text(result.get("currency") or quote.get("currency"), 16, True),
    }


def _company_data(result: dict) -> dict:
    profile = result.get("profile") or {}
    _need(isinstance(profile, dict), "invalid_profile")
    fields = {k: _text(profile.get(k), 500, True) for k in ("name", "sector", "description")}
    asof = _text(result.get("asof"), 80, True)
    metrics = []
    def metric(key, label, value, unit):
        if value is not None:
            metrics.append({"key": key, "label": label, "value": _num(value),
                            "unit": unit, "asof": asof, "period": None, "source": "get_fundamentals"})
    metric("market_cap", "Market cap", profile.get("mktcap_bn"), "bn")
    values = result.get("valuation") or {}
    for key, label in (("trailing_pe", "Trailing P/E"), ("forward_pe", "Forward P/E"),
                       ("price_to_book", "Price / book"), ("price_to_sales", "Price / sales")):
        metric(key, label, values.get(key), "×")
    return {"symbol": safe_symbol(result.get("symbol")), "profile": fields, "metrics": metrics}


def _transcript_data(result: dict, reader: str, view: dict) -> dict:
    if reader == "read_earnings_evidence":
        from engine.earnings_narrative.public_wire import verify_public_wire_fact_projection
        event = result.get("event") or {}
        receipts = result.get("receipts") or {}
        source_sha = receipts.get("source_sha256")
        facts = result.get("facts")
        verify_public_wire_fact_projection(facts, source_sha256=source_sha, max_facts=6)
        if view.get("transcript_id"):
            _need(view["transcript_id"] == event.get("transcript_id"), "transcript_mismatch")
        # A focus chooses among already-authorized exact facts; it cannot synthesize quotations.
        if view.get("focus"):
            terms = view["focus"].lower().split()
            matches = [f for f in facts if any(t in f["quote"]["text"].lower() for t in terms)]
            _need(bool(matches), "transcript_focus_unavailable")
            facts = matches
        return {
            "symbol": safe_symbol(result.get("ticker")),
            "event": {k: _text(event.get(k), 200, True) for k in ("transcript_id", "period", "date")},
            "kind": "quotes", "facts": copy.deepcopy(facts), "summary": None,
            "source_sha256": source_sha, "known_at": _text(receipts.get("known_at"), 80, True),
            "correction_status": _text(receipts.get("correction_status"), 80, True),
            "source_url": None,
        }
    call = result.get("latest_earnings_call") or {}
    _need(isinstance(call, dict), "invalid_call_context")
    summary = _text(call.get("summary"), 2000)
    _need(bool(summary.strip()), "transcript_unavailable")
    if view.get("transcript_id"):
        _need(view["transcript_id"] in {call.get("event_id"), call.get("source_record_id")}, "transcript_mismatch")
    citation = call.get("citation") or {}
    return {
        "symbol": safe_symbol(result.get("symbol") or call.get("ticker")),
        "event": {"transcript_id": _text(call.get("event_id"), 200, True),
                  "period": _text(call.get("fiscal_period"), 200, True),
                  "date": _text(call.get("call_date"), 80, True)},
        "kind": "summary", "facts": [], "summary": summary, "source_sha256": None,
        "known_at": _text(citation.get("source_updated_at"), 80, True),
        "correction_status": None, "source_url": _url(citation.get("url")),
    }


def _all_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _all_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _all_strings(v)


def compile_financial_widget(params: Any, observation: Any, identity: str,
                             *, screen: Callable[[str], bool] | None = None) -> dict:
    try:
        request = normalize_request(params)
        _need(isinstance(observation, dict), "missing_observation")
        reader, result = observation.get("reader"), observation.get("result")
        template = request["template"]
        _need(reader in _READERS[template] and isinstance(result, dict), "incompatible_reader")
        _need(not result.get("error") and result.get("available") is not False
              and result.get("ok") is not False, "source_unavailable")
        call_id = _text(observation.get("call_id"), 128)
        _need(bool(call_id), "missing_call_identity")
        if template == "financial_statement":
            data = _statement_data(result)
            entity, asof = data["fund"]["ticker"], data["fund"]["asof"]
        elif template == "price":
            data = _price_data(result)
            entity, asof = data["symbol"], data["quote"]["as_of"]
        elif template == "company":
            data = _company_data(result)
            entity, asof = data["symbol"], _text(result.get("asof"), 80, True)
        else:
            data = _transcript_data(result, reader, request["view"])
            entity, asof = data["symbol"], data["known_at"]
        _need(bool(entity) and (not request["symbol"] or entity == request["symbol"]), "identity_mismatch")
        _need(isinstance(identity, str) and 0 < len(identity) <= 256, "invalid_identity")
        source = {"reader": reader, "call_id": call_id, "entity_id": entity,
                  "snapshot_id": _sha(data), "asof": asof,
                  "status": "partial" if template == "price" and not data["bars"] else "available"}
        visual = {"version": VERSION, "template": template, "title": entity + " · " + _TITLE[template],
                  "source": source, "data": data, "view": request["view"],
                  "normalizer_version": NORMALIZER_VERSION if template == "financial_statement" else None}
        # Existing output guards cover ALL source/model text, not just the title.
        if screen:
            _need(screen("\n".join(_all_strings(visual))), "financial_copy_rejected")
        wire = {"type": "chart", "visual_id": financial_visual_id(identity, visual), "visual": visual}
        _bounded(wire)
        _need(validate_financial_view(wire), "invalid_compiled_view")
        return wire
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return {"error": "financial_widget_unavailable",
                "note": "The requested financial view is unavailable from qualified source data. Explain the gap; do not invent values."}


def validate_financial_view(wire: Any) -> bool:
    """Validate retained display bytes only; caller still owns account and entitlement checks."""
    try:
        _closed(wire, {"type", "visual_id", "visual"})
        _bounded(wire)
        _need(wire["type"] == "chart" and isinstance(wire["visual_id"], str)
              and bool(re.fullmatch(r"[a-f0-9]{24}", wire["visual_id"])), "invalid_wire")
        v = wire["visual"]
        _closed(v, {"version", "template", "title", "source", "data", "view", "normalizer_version"})
        _need(type(v["version"]) is int and v["version"] == VERSION, "invalid_version")
        template, data, source = v["template"], v["data"], v["source"]
        _need(template in TEMPLATES and isinstance(data, dict), "invalid_template")
        _text(v["title"], 200)
        _closed(source, {"reader", "call_id", "entity_id", "snapshot_id", "asof", "status"})
        _need(source["reader"] in _READERS[template], "invalid_reader")
        _text(source["call_id"], 128)
        entity = _text(source["entity_id"], 24)
        _need(bool(entity) and safe_symbol(entity) == entity, "invalid_identity")
        _text(source["asof"], 80, True)
        _need(source["status"] in {"available", "partial"}, "invalid_status")
        _need(source["snapshot_id"] == _sha(data), "snapshot_changed")
        req = normalize_request({"template": template, "symbol": entity, "view": v["view"]})
        _need(req["view"] == v["view"], "noncanonical_view")
        expected_normalizer = NORMALIZER_VERSION if template == "financial_statement" else None
        _need(v["normalizer_version"] == expected_normalizer, "unsupported_normalizer")
        if template == "financial_statement":
            _closed(data, {"fund"})
            _need(_statement_data(data) == data and data["fund"]["ticker"] == entity, "invalid_statement")
        elif template == "price":
            _closed(data, {"symbol", "quote", "bars", "bar_interval", "history_asof", "currency"})
            _closed(data["quote"], {"price", "prev_close", "change_pct", "as_of", "source", "live", "delayed_min"})
            # The owner symbol is outside the quote projection in the retained form.
            _need(_price_data(data) == data and data["symbol"] == entity, "invalid_price")
            for bar in data["bars"]:
                _closed(bar, {"date", "close"})
        elif template == "company":
            _closed(data, {"symbol", "profile", "metrics"})
            _need(data["symbol"] == entity and isinstance(data["metrics"], list)
                  and len(data["metrics"]) <= 12, "invalid_company")
            _closed(data["profile"], {"name", "sector", "description"})
            for item in data["profile"].values():
                _text(item, 500, True)
            for metric in data["metrics"]:
                _closed(metric, {"key", "label", "value", "unit", "asof", "period", "source"})
                _num(metric["value"], False)
                for key in ("key", "label", "unit", "source"):
                    _text(metric[key], 160)
                for key in ("asof", "period"):
                    _text(metric[key], 80, True)
        else:
            _closed(data, {"symbol", "event", "kind", "facts", "summary", "source_sha256",
                           "known_at", "correction_status", "source_url"})
            _need(data["symbol"] == entity, "invalid_transcript_identity")
            _closed(data["event"], {"transcript_id", "period", "date"})
            for val in data["event"].values():
                _text(val, 200, True)
            for key in ("known_at", "correction_status"):
                _text(data[key], 80, True)
            _url(data["source_url"])
            if data["kind"] == "quotes":
                from engine.earnings_narrative.public_wire import verify_public_wire_fact_projection
                _need(source["reader"] == "read_earnings_evidence" and data["summary"] is None
                      and data["source_url"] is None, "quote_reader_mismatch")
                verify_public_wire_fact_projection(data["facts"], source_sha256=data["source_sha256"], max_facts=6)
            else:
                _need(data["kind"] == "summary" and source["reader"] == "get_earnings"
                      and data["facts"] == [] and data["source_sha256"] is None, "invalid_summary")
                _text(data["summary"], 2000)
        for text in _all_strings(data):
            _need(not _UNSAFE.search(text), "unsafe_source_text")
        return True
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return False


def public_financial_visuals(meta: Any, *, allow_transcript_quotes: bool = False) -> list[dict]:
    if not isinstance(meta, dict) or not isinstance(meta.get("visuals"), list):
        return []
    return [wire for wire in meta["visuals"][:MAX_WIDGETS] if validate_financial_view(wire)
            and (allow_transcript_quotes or wire["visual"]["source"]["reader"] != "read_earnings_evidence")]


def financial_replay_notices(meta: Any, *, allow_transcript_quotes: bool = False) -> list[dict]:
    """Explain withheld evidence without projecting its entity, facts or receipt."""
    if allow_transcript_quotes or not isinstance(meta, dict) or not isinstance(meta.get("visuals"), list):
        return []
    if any(validate_financial_view(wire)
           and wire["visual"]["source"]["reader"] == "read_earnings_evidence"
           for wire in meta["visuals"][:MAX_WIDGETS]):
        return [{"type": "membership_required", "template": "transcript"}]
    return []


def financial_visual_id(identity: str, visual: dict) -> str:
    """One stable identity derivation for fresh compilation and same-turn reuse."""
    _need(isinstance(identity, str) and 0 < len(identity) <= 256, "invalid_identity")
    return _sha([identity, visual])[:24]


def model_visible_financial_result(wire: dict) -> dict:
    if not validate_financial_view(wire):
        return {"error": "financial_widget_unavailable"}
    v = wire["visual"]
    out = {"ok": True, "visual_id": wire["visual_id"], "template": v["template"],
           "source_ref": "fin_" + v["source"]["snapshot_id"],
           "symbol": v["source"]["entity_id"], "asof": v["source"]["asof"],
           "status": v["source"]["status"],
           "note": "Prepared for the user; final response screening controls display. Controls need no model call."}
    if v["template"] == "price":
        out["quote"] = {k: v["data"]["quote"][k] for k in ("price", "change_pct", "as_of", "source")}
    elif v["template"] == "financial_statement":
        fund = v["data"]["fund"]
        out["statement_currency"] = fund["stmt_currency"]
        out["periods_available"] = {k: len((s or {}).get("periods", [])) for k, s in fund["statements"].items()}
        out["note"] += " The browser applies canonical statement normalization; do not infer discrete-quarter values from raw source arrays."
    elif v["template"] == "company":
        out["name"] = v["data"]["profile"]["name"]
        out["sector"] = v["data"]["profile"]["sector"]
    else:
        out["evidence_kind"] = v["data"]["kind"]
        out["period"] = v["data"]["event"]["period"]
    return out
