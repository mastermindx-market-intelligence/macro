"""Proof-only saved/display comparison. No collection or runtime authority.

Every saved value must survive exactly. Five known builder additions are allowed
only when independently supplied expected outputs match them. The breadth input
is analytical display context, not a chart decoration or part of the saved trio.
Unknown additions, overwritten values and missing data fail the proof.
"""
from __future__ import annotations

import math

DOMAINS = ("conditions", "fear_euphoria", "market_drivers")
ALLOWED_ADDITIONS = frozenset({
    "conditions.roro_html", "conditions.recession_html", "conditions.drawdown_html",
    "fear_euphoria.chart_html", "conditions.breadth",
})


def verify_projection(saved: dict, displayed: dict, *, expected_additions: dict) -> dict:
    """Check exact values and structure without mutating either input."""
    assert isinstance(saved, dict) and isinstance(displayed, dict), "invalid roots"
    assert isinstance(expected_additions, dict), "expected additions unavailable"
    assert set(expected_additions) <= ALLOWED_ADDITIONS, "unreviewed expected path"
    additions, leaf_count = [], 0

    def same(a, b, path, *, allow_additions=True):
        nonlocal leaf_count
        assert type(a) is type(b), f"type changed: {path}"
        if isinstance(a, dict):
            assert set(a) <= set(b), f"saved keys removed: {path}"
            for key in sorted(set(b) - set(a)):
                added_path = f"{path}.{key}"
                assert allow_additions and added_path in expected_additions, f"unexpected addition: {added_path}"
                same(expected_additions[added_path], b[key], added_path, allow_additions=False)
                additions.append(added_path)
            for key in a:
                same(a[key], b[key], f"{path}.{key}", allow_additions=allow_additions)
        elif isinstance(a, list):
            assert len(a) == len(b), f"list length changed: {path}"
            for i, (x, y) in enumerate(zip(a, b)):
                same(x, y, f"{path}[{i}]", allow_additions=allow_additions)
        else:
            both_nan = isinstance(a, float) and math.isnan(a) and math.isnan(b)
            assert both_nan or a == b, f"saved value changed: {path}"
            if allow_additions:
                leaf_count += 1

    for domain in DOMAINS:
        assert domain in saved and domain in displayed, f"domain missing: {domain}"
        same(saved[domain], displayed[domain], domain)
    assert set(additions) == set(expected_additions), "expected projection missing or overwrote a saved key"
    return {"saved_measurements_unchanged": True, "saved_leaf_count": leaf_count,
            "reviewed_additions": sorted(additions),
            "breadth_is_separate_derived_context": "conditions.breadth" in additions}
