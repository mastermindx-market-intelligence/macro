"""Bilingual clause for configured FDA molecules that have no matched rows.

Display-only sibling of the foresight chip. Synthetic inputs only: this module
does not read the shortage store, does not call the network, and does not
import the scarcity engine or the theme graph.
"""
from __future__ import annotations


def _tokens(value) -> tuple[str, ...]:
    """Unique non-empty strings, in first-seen order. A bare string is not a list."""
    if value is None or isinstance(value, (str, bytes)):
        return ()
    try:
        items = iter(value)
    except TypeError:
        return ()
    tokens: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            continue
        token = item.strip()
        if not token or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tuple(tokens)


def molecule_gap_clause(molecules_checked, molecules_with_rows) -> dict | None:
    """Name checked molecules that have no rows, or None when every one does.

    English is ASCII, in checked order, and does not count. Chinese is a
    separate sentence. Drug tokens stay the Latin names already on the
    coverage dict. Both halves are absent (the clause is None) when there
    is no gap.
    """
    checked = _tokens(molecules_checked)
    present = set(_tokens(molecules_with_rows))
    missing = tuple(name for name in checked if name not in present)
    if not missing:
        return None
    listed = ", ".join(missing)
    return {
        "en": f"no records: {listed}",
        "zh": "无记录：" + "、".join(missing),
    }
