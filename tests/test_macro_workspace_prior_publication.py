"""Prior is the previous PUBLICATION, never the previous build of the same one.

Regression for the self-prior bug: ``build.py`` used to hand the previously
written ``latest.json`` to composers as ``prior_snapshot``, so a nightly
rebuild of an unchanged publication minted ``prior_value == current_value``,
``delta 0.0``, ``sign flat``, still stamped ``COMPARABLE``.

    python3 -m pytest tests/test_macro_workspace_prior_publication.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.market_os.macro_workspaces import consumer_payments as cp  # noqa: E402
from engine.market_os.macro_workspaces import contract  # noqa: E402
from engine.market_os.macro_workspaces.publication_prior import (  # noqa: E402
    apply_producer_prior_seal,
    is_strictly_earlier,
    no_earlier_publication,
    resolve_publication_prior,
)
from lib import macro_suite_view as V  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "macro_workspace_prior_publication" / (
    "consumer_payments_fred_frames.json"
)


def _frames() -> dict:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    built_at = raw["built_at"]

    def _rows(block: dict) -> dict:
        out = {}
        for sid, rows in block.items():
            if rows is None:
                out[sid] = None
            else:
                out[sid] = [tuple(r) for r in rows]
        return out

    return {
        "built_at": built_at,
        "june": _rows(raw["june"]),
        "july": _rows(raw["july"]),
    }


def _compose(frames: dict, built_at: str, prior=None) -> dict:
    return contract.finalize(cp.compose(frames, built_at=built_at, prior_snapshot=prior))


def _retail(snap: dict):
    return next(d for d in snap["changes"]["deltas"]
                if d["metric_id"] == "retail_sales_level")


def test_same_dated_rebuild_carries_the_earlier_publication_forward() -> None:
    fx = _frames()
    june = _compose(fx["june"], fx["built_at"])
    july = _compose(fx["july"], fx["built_at"], prior=june)
    rebuilt = _compose(fx["july"], fx["built_at"], prior=july)

    assert june["headline"]["effective_date"] == "2026-06-01"
    assert july["headline"]["effective_date"] == "2026-07-01"
    assert rebuilt["headline"]["effective_date"] == "2026-07-01"

    assert july["changes"]["comparability"] == "COMPARABLE"
    assert july["changes"]["prior_effective_date"] == "2026-06-01"
    assert _retail(july)["prior_value"] == pytest.approx(680000.0)
    assert _retail(july)["current_value"] == pytest.approx(700000.0)
    assert _retail(july)["delta"] == pytest.approx(20000.0)

    assert rebuilt["changes"] == july["changes"]
    assert rebuilt["changes"]["prior_effective_date"] == "2026-06-01"
    assert _retail(rebuilt)["prior_value"] == pytest.approx(680000.0)
    assert _retail(rebuilt)["current_value"] != _retail(rebuilt)["prior_value"]


def test_later_publication_uses_the_earlier_publication_values_as_prior() -> None:
    fx = _frames()
    june = _compose(fx["june"], fx["built_at"])
    july = _compose(fx["july"], fx["built_at"], prior=june)
    june_level = next(m["value"] for m in june["metrics"]["items"]
                      if m["metric_id"] == "retail_sales_level")
    assert july["changes"]["prior_effective_date"] == june["headline"]["effective_date"]
    assert _retail(july)["prior_value"] == pytest.approx(june_level)


def test_same_dated_rebuild_without_an_earlier_publication_is_typed_null() -> None:
    fx = _frames()
    first = _compose(fx["july"], fx["built_at"])
    second = _compose(fx["july"], fx["built_at"], prior=first)

    assert first["changes"]["comparability"] == "NO_PRIOR"
    assert second["changes"]["comparability"] == "NO_EARLIER_PUBLICATION"
    assert second["changes"]["prior_effective_date"] is None
    assert second["changes"]["deltas"] == []
    assert second["changes"]["null_reason"] == "INSUFFICIENT_HISTORY"
    typed = no_earlier_publication()
    assert typed["comparability"] == "NO_EARLIER_PUBLICATION"
    assert typed["prior_effective_date"] is None


def test_resolve_does_not_use_a_later_stored_date_as_prior() -> None:
    stored = {
        "headline": {"effective_date": "2026-08-01", "method_version": "v1"},
        "changes": {"prior_effective_date": "2026-07-01", "deltas": []},
    }
    assert resolve_publication_prior(stored, "2026-06-01") is None
    assert is_strictly_earlier("2026-07-01", "2026-07-01") is False
    assert is_strictly_earlier("2026-07-01T23:00:00Z", "2026-07-02") is True


def test_producer_seal_refuses_a_same_dated_comparable() -> None:
    body = {
        "headline": {"effective_date": "2026-07-01"},
        "changes": {
            "comparability": "COMPARABLE",
            "prior_effective_date": "2026-07-01",
            "prior_generation_id": "x",
            "prior_method_version": "v1",
            "deltas": [{"metric_id": "retail_sales_level", "prior_value": 700000.0,
                        "current_value": 700000.0, "delta": 0.0, "note": "x"}],
            "status": "PRESENT",
            "null_reason": None,
        },
    }
    sealed = apply_producer_prior_seal(body, {
        "headline": {"effective_date": "2026-07-01"},
        "changes": {"prior_effective_date": "2026-07-01", "deltas": []},
    })
    assert sealed["changes"]["comparability"] == "NO_EARLIER_PUBLICATION"
    assert sealed["changes"]["deltas"] == []


def test_view_prints_plain_words_for_null_deltas_never_none_or_nan() -> None:
    fx = _frames()
    first = _compose(fx["july"], fx["built_at"])
    second = _compose(fx["july"], fx["built_at"], prior=first)
    view = V.build_view(
        second, page_built_at="2026-09-04T00:00:00Z",
        artifact={"path": "x", "manifest_path": "y", "sha256": "z", "bytes": 1,
                  "min_client_contract": "mastermind.macro_workspace_snapshot.v1@1.0.0"},
    )
    changes = view["changes"]
    assert changes["comparable"] is False
    assert changes["comparability_label"]["en"] == "No earlier reading yet"
    assert changes["comparability_label"]["zh"] == "暂无更早读数"
    assert changes["absence"]["label"]["en"] == "No earlier reading yet"
    assert changes["absence"]["label"]["zh"] == "暂无更早读数"
    blob = json.dumps(changes, ensure_ascii=False)
    assert "None" not in blob
    assert "nan" not in blob.lower()
    glance = view["glance"]["change"]
    assert glance["present"] is False
    assert glance["absence"]["label"]["en"] == "No earlier reading yet"
    assert glance["absence"]["label"]["zh"] == "暂无更早读数"
