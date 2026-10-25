"""Deterministic display annotation for served ticker-news text.

Pure functions. The only I/O is the rights-receipt read inside
``derivative_permitted``. Annotation is computed from the served headline and,
when that teaser was actually served, the served teaser. There is no body
parameter, no model call, and no stance or score field.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.news_events import classify_event, extract_numbers

SCHEMA = "ticker_news.annotation.v1"
ANNOTATOR_VERSION = "qbus_news_annotate.v1"
_DERIVATION = "deterministic_pattern"
_FIGURE_KEYS = ("usd", "percentages", "eps", "guidance_range", "count")


def _served_text(value: str | None) -> str | None:
    if isinstance(value, str) and value != "":
        return value
    return None


def _figures(numbers: dict) -> dict[str, Any]:
    return {key: numbers.get(key) for key in _FIGURE_KEYS}


def annotate_row(title: str | None, teaser: str | None) -> dict[str, Any] | None:
    """Classify one served headline, optionally confirmed by its served teaser.

    A missing or empty title returns None. An unmatched headline still returns
    the annotation object, with ``event_type`` null and figures taken from the
    same text the classifier saw.
    """
    headline = _served_text(title)
    if headline is None:
        return None
    extra = _served_text(teaser)
    if extra is None:
        classified = classify_event(headline)
        basis = "headline"
        text_basis = headline
    else:
        classified = classify_event(headline, extra)
        basis = "headline+teaser"
        text_basis = f"{headline} {extra}"

    if classified is None:
        event_type = None
        matched = None
        numbers = extract_numbers(text_basis)
    else:
        event_type = classified.get("event_type")
        matched = classified.get("matched")
        raw_numbers = classified.get("numbers")
        numbers = raw_numbers if isinstance(raw_numbers, dict) else {}

    return {
        "schema": SCHEMA,
        "event_type": event_type,
        "figures": _figures(numbers),
        "evidence": {"matched_pattern": matched},
        "basis": basis,
        "annotator_version": ANNOTATOR_VERSION,
        "derivation": _DERIVATION,
    }


def derivative_permitted(receipt_path) -> bool:
    """True only when the receipt file has boolean ``derivative_processing``.

    Qualification (audience, window, approval) is not repeated here. Any read,
    parse, or type fault returns False.
    """
    try:
        payload = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False
    if not isinstance(payload, dict):
        return False
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, dict):
        return False
    return capabilities.get("derivative_processing") is True
