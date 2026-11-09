"""Theme price-coverage rows the HK / Canada basket pages print (W28B SPEC 2-3, no I/O).

engine.theme_scoring.compute_theme_intel records one population observation per theme
(lib.closes_panel.population_observation). A theme that meets the gate while missing some
configured names is scored with status "partial" and stays in ``themes``; a theme below the
gate is left out of ``themes`` and kept only in ``observation_refusals``. These helpers read
both lists and never raise on a missing or malformed theme_intel.
"""
from __future__ import annotations


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _text(value):
    return value if isinstance(value, str) and value else None


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _row(obs: dict, bid: str, name, name_zh, theme: dict | None) -> dict:
    theme = theme or {}
    return {
        "id": bid,
        "name": _text(name) or bid,
        "name_zh": _text(name_zh) or _text(name) or bid,
        "scored": bool(theme),
        "score": _num(theme.get("score")),
        "reco_en": _text(theme.get("reco_en")),
        "reco_zh": _text(theme.get("reco_zh")),
        "status": _text(obs.get("status")),
        "configured_n": _num(obs.get("configured_n")),
        "observed_n": _num(obs.get("observed_n")),
        "coverage": _num(obs.get("coverage")),
        "min_members": _num(obs.get("min_members")),
        "min_coverage": _num(obs.get("min_coverage")),
        "missing_columns": [m for m in _list(obs.get("missing_columns")) if _text(m)],
        "missing_at_asof": [m for m in _list(obs.get("missing_at_asof")) if _text(m)],
        "effective_as_of": _text(obs.get("effective_as_of")),
    }


def themeobs_rows(theme_intel, baskets=None) -> list[dict]:
    """Scored partial themes, then refused themes; [] when every theme read is complete.

    `baskets` is the page's basket list ({id, name, name_zh}); a refused theme takes its
    names from it because refusals carry only the basket id.
    """
    if not isinstance(theme_intel, dict):
        return []
    rows = []
    for theme in _list(theme_intel.get("themes")):
        obs = theme.get("observation") if isinstance(theme, dict) else None
        bid = _text(theme.get("id")) if isinstance(theme, dict) else None
        if bid and isinstance(obs, dict) and obs.get("status") == "partial":
            rows.append(_row(obs, bid, theme.get("name"), theme.get("name_zh"), theme))
    names = {b["id"]: b for b in _list(baskets) if isinstance(b, dict) and _text(b.get("id"))}
    for ref in _list(theme_intel.get("observation_refusals")):
        obs = ref.get("observation") if isinstance(ref, dict) else None
        bid = _text(ref.get("basket_id")) if isinstance(ref, dict) else None
        if bid and isinstance(obs, dict):
            b = names.get(bid, {})
            rows.append(_row(obs, bid, b.get("name"), b.get("name_zh"), None))
    return rows


def observation_line(theme_intel) -> dict:
    """The desk-level price receipt {effective_as_of, status}; {} when either is absent."""
    obs = theme_intel.get("observation") if isinstance(theme_intel, dict) else None
    if not isinstance(obs, dict):
        return {}
    when, status = _text(obs.get("effective_as_of")), _text(obs.get("status"))
    return {"effective_as_of": when, "status": status} if when and status else {}
