"""Field-order pin for the Robotics ImportError type mirror.

The composer imports ``ResearchQuery`` and ``OwnerBundle`` from the
semiconductor owner and keeps a frozen mirror on ``except ImportError``.
That arm never runs when the owner imports, so this test forces the
ImportError, re-imports the composer, and compares
``tuple(__dataclass_fields__)``. It skips when the owner module is absent.
A drift fails; it is not an xfail.
"""

from __future__ import annotations

import importlib
import sys

import pytest

_SEMI = "engine.market_ontology.semiconductor_theme_research"
_ROB = "engine.market_ontology.robotics_theme_research"


def test_mirror_field_order_matches_shared_owner():
    try:
        semi = importlib.import_module(_SEMI)
    except ImportError:
        pytest.skip("semiconductor_theme_research is not importable")
    owner_query = tuple(semi.ResearchQuery.__dataclass_fields__)
    owner_bundle = tuple(semi.OwnerBundle.__dataclass_fields__)

    saved_semi = sys.modules.get(_SEMI)
    saved_rob = sys.modules.get(_ROB)
    sys.modules[_SEMI] = None
    sys.modules.pop(_ROB, None)
    try:
        mirror = importlib.import_module(_ROB)
        assert mirror.SHARED_TYPES is False
        assert tuple(mirror.ResearchQuery.__dataclass_fields__) == owner_query
        assert tuple(mirror.OwnerBundle.__dataclass_fields__) == owner_bundle
    finally:
        if saved_semi is None:
            sys.modules.pop(_SEMI, None)
        else:
            sys.modules[_SEMI] = saved_semi
        sys.modules.pop(_ROB, None)
        if saved_rob is not None:
            sys.modules[_ROB] = saved_rob
        importlib.import_module(_ROB)
