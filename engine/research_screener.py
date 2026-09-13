"""Pure research-screener view-model compiler (F06 / B-F06-4).

Zero IO, no clock, no network. Input is already-loaded security_state.v1
objects plus valuation_scenario.v1 posture rows. Output is a
research_priority_only list: alphabetical by name by default, never a
ranker, never a score.

Theme has no owner on main (GMI theme owners unbuilt) and is always null.
Exposure has no per-user server path; the compiler always emits null and
names the lens in ``nulls``. Signed-in overlay is a client-side read of
the existing WatchStore.portfolio.list mechanism, not this module.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Mapping

SCHEMA = "research_screener.v1"
TIER = "research_priority_only"
CATALYST_WINDOW_TRADING_DAYS = 30
DEFAULT_ORDER = "name"
ALLOWED_ORDERS = ("name", "next_catalyst_date")

_FORBIDDEN_KEY_FRAGMENTS = ("score", "rank", "top", "best", "conviction")

THEME_NULL_EN = "Theme lens isn't available yet"
THEME_NULL_ZH = "主题视角尚未提供。"
EXPOSURE_NULL_EN = "Sign in to see which of these you hold"
EXPOSURE_NULL_ZH = "登录后即可看到你持有其中哪些。"

CATALYST_EVENT_EN = "Next earnings window"
CATALYST_EVENT_ZH = "下一份财报窗口"
CATALYST_OWNER_EN = "this company's security state catalyst record"
CATALYST_OWNER_ZH = "该公司证券状态中的催化事项记录"

VAL_OWNER_EN = "Valuation under different assumptions"
VAL_OWNER_ZH = "不同假设下的估值面板"
VAL_INEXPENSIVE_EN = "Looks inexpensive against reported earnings."
VAL_INEXPENSIVE_ZH = "对照已披露盈利显得便宜。"
VAL_EXPENSIVE_EN = "Looks expensive against reported earnings."
VAL_EXPENSIVE_ZH = "对照已披露盈利显得偏贵。"
VAL_INLINE_EN = "Looks in line with reported earnings."
VAL_INLINE_ZH = "对照已披露盈利大致相当。"

WHY_IDENTITY_EN = "This name is on the research list because it has a security state record."
WHY_IDENTITY_ZH = "该公司出现在研究名单上，是因为它有证券状态记录。"
_EN_SENTENCE_END = ".!?"
_ZH_SENTENCE_END = "。！？"


def _iso_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return date(value.year, value.month, value.day)
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def trading_days_between(start: date, end: date) -> int:
    """Weekday count from ``start`` to ``end``, excluding ``start``, including ``end``.

    Holidays are not a calendar this compiler owns. A weekday count is the
    checkable stand-in for "trading days" with zero IO.
    """
    if end <= start:
        return 0
    days = 0
    cursor = start
    one = timedelta(days=1)
    while cursor < end:
        cursor += one
        if cursor.weekday() < 5:
            days += 1
    return days


def _bilingual(en: str, zh: str) -> dict[str, str]:
    return {"en": en, "zh": zh}


def _en_sentence(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    if text[-1] not in _EN_SENTENCE_END:
        return text + "."
    return text


def _zh_sentence(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    if text[-1] not in _ZH_SENTENCE_END:
        return text + "。"
    return text


def _assert_no_forbidden_keys(obj: Any, path: str = "") -> None:
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            lowered = str(key).lower()
            for fragment in _FORBIDDEN_KEY_FRAGMENTS:
                if fragment == lowered or fragment in lowered.split("_"):
                    raise ValueError(
                        f"research_screener view-model forbids key {key!r} at {path or '/'}"
                    )
            _assert_no_forbidden_keys(value, f"{path}/{key}")
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            _assert_no_forbidden_keys(item, f"{path}[{i}]")


def _name_of(state: Mapping[str, Any], names: Mapping[str, str] | None) -> str:
    listing_key = str(state.get("listing_key") or "")
    ticker = str(state.get("ticker_display") or "")
    if names:
        if listing_key and names.get(listing_key):
            return str(names[listing_key])
        if ticker and names.get(ticker):
            return str(names[ticker])
    return str(state.get("name") or ticker or listing_key or "Unnamed")


def _catalyst_for(state: Mapping[str, Any], as_of: date | None) -> dict[str, Any] | None:
    legs = state.get("legs") if isinstance(state.get("legs"), Mapping) else {}
    catalyst = legs.get("catalyst") if isinstance(legs, Mapping) else None
    if not isinstance(catalyst, Mapping):
        return None
    observables = catalyst.get("next_observables") or []
    if not isinstance(observables, list):
        return None
    dated: list[tuple[date, Mapping[str, Any]]] = []
    for item in observables:
        if not isinstance(item, Mapping):
            continue
        start = _iso_date(item.get("window_start") or item.get("date"))
        if start is None:
            continue
        dated.append((start, item))
    if not dated:
        return None
    dated.sort(key=lambda pair: pair[0])
    event_date, _item = dated[0]
    if as_of is None:
        return None
    if event_date < as_of:
        return None
    if trading_days_between(as_of, event_date) > CATALYST_WINDOW_TRADING_DAYS:
        return None
    return {
        "next_event_name": _bilingual(CATALYST_EVENT_EN, CATALYST_EVENT_ZH),
        "date": event_date.isoformat(),
        "owner": _bilingual(CATALYST_OWNER_EN, CATALYST_OWNER_ZH),
    }


def _assumptions_text(assumptions: Mapping[str, Any] | None) -> dict[str, str]:
    assumptions = assumptions or {}
    growth = assumptions.get("sales_growth_pct")
    margin = assumptions.get("margin_delta_pp")
    multiple = assumptions.get("earnings_multiple")
    try:
        growth_n = float(growth)
    except (TypeError, ValueError):
        growth_n = 0.0
    try:
        margin_n = float(margin)
    except (TypeError, ValueError):
        margin_n = 0.0
    try:
        multiple_n = float(multiple)
    except (TypeError, ValueError):
        multiple_n = 0.0
    if abs(growth_n) < 1e-9:
        growth_en = "Sales unchanged"
        growth_zh = "销售收入不变"
    elif growth_n > 0:
        growth_en = f"Sales up {growth_n:g} percent"
        growth_zh = f"销售收入增长 {growth_n:g}%"
    else:
        growth_en = f"Sales down {abs(growth_n):g} percent"
        growth_zh = f"销售收入下降 {abs(growth_n):g}%"
    if abs(margin_n) < 1e-9:
        margin_en = "margins unchanged"
        margin_zh = "利润率不变"
    elif margin_n > 0:
        margin_en = f"margins up {margin_n:g} points"
        margin_zh = f"利润率上升 {margin_n:g} 个百分点"
    else:
        margin_en = f"margins down {abs(margin_n):g} points"
        margin_zh = f"利润率下降 {abs(margin_n):g} 个百分点"
    en = (
        f"{growth_en}, {margin_en}, valued at {multiple_n:g} times reported earnings."
    )
    zh = f"{growth_zh}，{margin_zh}，按已披露盈利的 {multiple_n:g} 倍估值。"
    return _bilingual(en, zh)


def _valuation_for(
    state: Mapping[str, Any],
    postures_by_ticker: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    ticker = str(state.get("ticker_display") or "")
    listing_key = str(state.get("listing_key") or "")
    blob = postures_by_ticker.get(ticker) or postures_by_ticker.get(listing_key)
    if not isinstance(blob, Mapping):
        return None
    schema = blob.get("schema")
    if schema not in (None, "valuation_scenario.v1"):
        return None
    scenarios = blob.get("scenarios") or []
    base = None
    for item in scenarios:
        if isinstance(item, Mapping) and item.get("key") == "base":
            base = item
            break
    if not isinstance(base, Mapping) or not base.get("computable"):
        return None
    per_share = base.get("per_share")
    try:
        per_share_n = float(per_share) if per_share is not None else None
    except (TypeError, ValueError):
        per_share_n = None
    price_block = blob.get("price") if isinstance(blob.get("price"), Mapping) else None
    price = price_block.get("value") if price_block else None
    try:
        price_n = float(price) if price is not None else None
    except (TypeError, ValueError):
        price_n = None
    if per_share_n is None or price_n is None:
        return None
    if price_n < per_share_n:
        label = _bilingual(VAL_INEXPENSIVE_EN, VAL_INEXPENSIVE_ZH)
    elif price_n > per_share_n:
        label = _bilingual(VAL_EXPENSIVE_EN, VAL_EXPENSIVE_ZH)
    else:
        label = _bilingual(VAL_INLINE_EN, VAL_INLINE_ZH)
    assumptions = base.get("assumptions") if isinstance(base.get("assumptions"), Mapping) else {}
    return {
        "label": label,
        "assumptions_text": _assumptions_text(assumptions),
        "owner": _bilingual(VAL_OWNER_EN, VAL_OWNER_ZH),
    }


def _why(
    catalyst: Mapping[str, Any] | None,
    valuation: Mapping[str, Any] | None,
) -> dict[str, str]:
    parts_en: list[str] = []
    parts_zh: list[str] = []
    if catalyst:
        event = catalyst["next_event_name"]
        owner = catalyst["owner"]
        parts_en.append(
            _en_sentence(f"{event['en']} on {catalyst['date']}, from {owner['en']}")
        )
        parts_zh.append(
            _zh_sentence(f"{event['zh']}在 {catalyst['date']}，来源：{owner['zh']}")
        )
    if valuation:
        label = valuation["label"]
        assumptions = valuation["assumptions_text"]
        owner = valuation["owner"]
        parts_en.append(
            " ".join(
                [
                    _en_sentence(label["en"]),
                    _en_sentence(assumptions["en"]),
                    _en_sentence(f"From {owner['en']}"),
                ]
            )
        )
        parts_zh.append(
            "".join(
                [
                    _zh_sentence(label["zh"]),
                    _zh_sentence(assumptions["zh"]),
                    _zh_sentence(f"来源：{owner['zh']}"),
                ]
            )
        )
    if not parts_en:
        return _bilingual(WHY_IDENTITY_EN, WHY_IDENTITY_ZH)
    return _bilingual(" ".join(parts_en), "".join(parts_zh))


def _index_postures(rows: list[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    if rows is None:
        return out
    if isinstance(rows, Mapping):
        for key, blob in rows.items():
            if isinstance(blob, Mapping):
                out[str(key)] = blob
        return out
    for blob in rows:
        if not isinstance(blob, Mapping):
            continue
        ticker = str(blob.get("ticker") or "")
        listing_key = str(blob.get("listing_key") or "")
        if ticker:
            out[ticker] = blob
        if listing_key:
            out[listing_key] = blob
    return out


def sort_rows(rows: list[dict[str, Any]], order: str = DEFAULT_ORDER) -> list[dict[str, Any]]:
    """Order by checkable facts only: name, or next catalyst date."""
    if order not in ALLOWED_ORDERS:
        order = DEFAULT_ORDER
    if order == "next_catalyst_date":
        def key(row: Mapping[str, Any]) -> tuple:
            catalyst = row.get("catalyst") if isinstance(row.get("catalyst"), Mapping) else None
            date_s = catalyst.get("date") if catalyst else None
            # Rows with no dated catalyst sort after dated ones, then by name.
            return (date_s is None, date_s or "", (row.get("name") or "").casefold(), row.get("listing_key") or "")
        return sorted(rows, key=key)
    return sorted(
        rows,
        key=lambda row: ((row.get("name") or "").casefold(), row.get("listing_key") or ""),
    )


def compile_research_screener(
    security_states: list[Mapping[str, Any]] | None,
    valuation_postures: list[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None = None,
    *,
    as_of: date | str | None = None,
    names: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Compile the research-priority-only screener view model.

    Parameters
    ----------
    security_states:
        Already-loaded ``security_state.v1`` objects (or wrappers that carry
        one under ``security_state``).
    valuation_postures:
        Already-computed ``valuation_scenario.v1`` blobs, either a list or a
        mapping keyed by ticker / listing_key.
    as_of:
        Anchor date for the 30-trading-day catalyst window. Required for a
        dated catalyst; omitted means every catalyst is null.
    names:
        Optional listing_key-or-ticker → display name map.
    """
    as_of_date = _iso_date(as_of)
    postures = _index_postures(valuation_postures)
    rows: list[dict[str, Any]] = []
    for raw in security_states or []:
        if not isinstance(raw, Mapping):
            continue
        state = raw.get("security_state") if isinstance(raw.get("security_state"), Mapping) else raw
        if not isinstance(state, Mapping):
            continue
        schema = state.get("schema")
        if schema not in (None, "security_state.v1"):
            continue
        listing_key = str(state.get("listing_key") or "")
        if not listing_key:
            continue
        ticker = str(state.get("ticker_display") or "")
        catalyst = _catalyst_for(state, as_of_date)
        valuation = _valuation_for(state, postures)
        rows.append({
            "listing_key": listing_key,
            "name": _name_of(state, names),
            "ticker": ticker,
            "catalyst": catalyst,
            "valuation_posture": valuation,
            "exposure": None,
            "theme": None,
            "why": _why(catalyst, valuation),
        })
    rows = sort_rows(rows, DEFAULT_ORDER)
    payload = {
        "schema": SCHEMA,
        "tier": TIER,
        "as_of": as_of_date.isoformat() if as_of_date else None,
        "order": DEFAULT_ORDER,
        "orderings": list(ALLOWED_ORDERS),
        "nulls": [
            {"lens": "theme", "en": THEME_NULL_EN, "zh": THEME_NULL_ZH},
            {"lens": "exposure", "en": EXPOSURE_NULL_EN, "zh": EXPOSURE_NULL_ZH},
        ],
        "rows": rows,
    }
    _assert_no_forbidden_keys(payload)
    return payload
