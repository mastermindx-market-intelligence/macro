"""Bounded read-only presentation of the existing annual USGS producer contract."""
from __future__ import annotations

import json
import math
import re
from datetime import date, datetime
from pathlib import Path

_MAX_BYTES = 256 * 1024
_MINERALS = (("cobalt", "Cobalt", "钴"), ("lithium", "Lithium", "锂"),
             ("gallium", "Gallium", "镓"), ("rare_earths", "Rare earths", "稀土"))
_FALSE_FLAGS = ("may_rank", "may_gate", "may_size", "may_escalate", "rotation_calls", "short_calls")
_COUNTRY_ZH = {"Argentina": "阿根廷", "Canada": "加拿大", "Chile": "智利", "China": "中国",
               "Estonia": "爱沙尼亚", "Finland": "芬兰", "Germany": "德国", "Japan": "日本",
               "Malaysia": "马来西亚", "Norway": "挪威", "Other": "其他"}
_UNIT_ZH = {"metric tons": "公吨"}


def _unavailable() -> dict:
    return {"state": "UNAVAILABLE", "rows": []}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _finite_float(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("non-finite JSON number")
    return parsed


def _reject_constant(value):
    raise ValueError("non-finite JSON value")


def _text(value, limit=1200):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        return None
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        return None
    return value  # The producer owns the sentence, including its qualifiers.


def _amount(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        return None
    if value % 1 == 0:
        return f"{int(value):,}"
    return str(value)  # Other values keep their recorded digits; never round.


def _import_sources(source):
    entries = source.get("import_sources_2021_24")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 12:
        return None
    total, rows = 0, []
    for entry in entries:
        if not isinstance(entry, dict):
            return None
        country, pct = _text(entry.get("country"), 60), entry.get("pct")
        if (not country or type(pct) not in (int, float) or not math.isfinite(pct)
                or not 0 <= pct <= 100):
            return None
        total += pct
        rows.append({"country_en": country, "country_zh": _COUNTRY_ZH.get(country, country),
                     "pct": _amount(pct)})
    return None if total > 101 else rows


def _world_output(producer):
    if not isinstance(producer, dict) or producer.get("unit") not in _UNIT_ZH:
        return None
    total = producer.get("world_total")
    if _amount(total) is None or total <= 0:
        return None
    unit = producer.get("unit")
    return {"amount": _amount(total), "unit_en": unit, "unit_zh": _UNIT_ZH[unit]}


def load_critical_minerals_context(path: Path) -> dict:
    """Read at most 256 KiB; absence, invalid metadata or promotion fails closed.

    Annual observation, publication and generation clocks stay separate. Partial
    coverage preserves only the producer's available sentences; no scoring, network,
    writes, imputation or conversion of source quantities happens here.
    """
    try:
        with Path(path).open("rb") as source:
            raw = source.read(_MAX_BYTES + 1)
        if len(raw) > _MAX_BYTES:
            return _unavailable()
        value = json.loads(raw, object_pairs_hook=_object, parse_constant=_reject_constant,
                           parse_float=_finite_float)
        if not isinstance(value, dict) or value.get("schema") != "critical_minerals_supply.v1":
            return _unavailable()
        authority = value.get("authority")
        if (not isinstance(authority, dict) or authority.get("is_context_only") is not True
                or authority.get("framing") != "critical_minerals_supply_context"
                or any(authority.get(k) is not False for k in _FALSE_FLAGS)):
            return _unavailable()
        edition = value.get("edition")
        if not isinstance(edition, dict):
            return _unavailable()
        year, published, item = edition.get("year"), edition.get("published"), edition.get("item_id")
        generated = value.get("generated_at")
        if type(year) is not int or not 1900 <= year <= 2200:
            return _unavailable()
        if not isinstance(published, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published):
            return _unavailable()
        date.fromisoformat(published)
        if not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{24}", item):
            return _unavailable()
        if not _text(generated, 40):
            return _unavailable()
        stamp = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            return _unavailable()
        minerals = value.get("commodities")
        if not isinstance(minerals, dict):
            return _unavailable()
        rows = []
        for key, en, zh in _MINERALS:
            source = minerals.get(key)
            source = source if isinstance(source, dict) else {}
            nulls = source.get("nulls")
            producer = source.get("leading_producer")
            period = producer.get("period") if isinstance(producer, dict) else None
            # Source periods are strings; an integer year may be represented
            # without changing its meaning, but booleans and fabricated dates may not.
            period = str(period) if type(period) is int else period
            read_en, read_zh = _text(source.get("read_en")), _text(source.get("read_zh"))
            available = bool(read_en and read_zh and _text(period, 80)
                             and isinstance(nulls, list)
                             and all(isinstance(n, str) for n in nulls)
                             and "no_edition_ingested" not in nulls)
            rows.append({"key": key, "label_en": _text(source.get("label_en"), 100) or en,
                         "label_zh": _text(source.get("label_zh"), 100) or zh,
                         "available": available, "read_en": read_en if available else None,
                         "read_zh": read_zh if available else None,
                         "observation_period": period if available else None,
                         "import_sources": _import_sources(source) if available else None,
                         "world_output": _world_output(producer) if available else None})
        count = sum(row["available"] for row in rows)
        if not count:
            return _unavailable()
        return {"state": "AVAILABLE" if count == len(rows) else "PARTIAL",
                "edition_year": year, "published": published, "generated_at": generated,
                "source_url": "https://www.sciencebase.gov/catalog/item/" + item,
                "has_import_sources": any(r["import_sources"] for r in rows),
                "rows": rows}
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        return _unavailable()
