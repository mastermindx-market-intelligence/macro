"""Fail-closed development renderer guard for the public Prophet source pair."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.render_macro_fast import (
    _TODAY_BINDING_ATTRS,
    _today_source_binding,
    _tracked_today_binding,
)


def _html(**changed: str) -> str:
    data = {
        "data-today-total": "12",
        "data-today-visible": "0",
        "data-today-source-sha256": "sha256:" + "a" * 64,
        "data-today-pair-id": "pair-a",
        "data-today-selection-receipt": "sha256:" + "b" * 64,
        "data-today-served": "",
    }
    data.update(changed)
    attrs = " ".join(f'{k}="{v}"' for k, v in data.items())
    return "<html><section class=\"mx-sec\" id=\"us-today\" " + attrs + "></section></html>"


def test_all_six_binding_fields_are_required():
    original = _today_source_binding(_html())
    assert original is not None and len(original) == len(_TODAY_BINDING_ATTRS) == 6
    for key in _TODAY_BINDING_ATTRS:
        modified = _html().replace(f' {key}="', f' data-removed-{key}="')
        assert _today_source_binding(modified) is None, key
    assert _today_source_binding("<section id='us-today'></section>") is None


@pytest.mark.parametrize("key,new_value", [
    ("data-today-total", "13"),
    ("data-today-visible", "3"),
    ("data-today-source-sha256", "sha256:" + "c" * 64),
    ("data-today-pair-id", "pair-b"),
    ("data-today-selection-receipt", "sha256:" + "d" * 64),
    ("data-today-served", "3~sha256:" + "e" * 64),
])
def test_any_partition_drift_refuses_equivalence(key: str, new_value: str):
    assert _today_source_binding(_html()) != _today_source_binding(
        _html(**{key: new_value})
    )


def test_git_committed_public_source_is_authority():
    root = Path(__file__).resolve().parents[1]
    binding = _tracked_today_binding(root)
    assert binding is not None
    assert dict(binding).keys() == set(_TODAY_BINDING_ATTRS)
