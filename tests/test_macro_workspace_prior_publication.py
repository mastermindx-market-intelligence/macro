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

import importlib  # noqa: E402

from jinja2 import Environment, FileSystemLoader, StrictUndefined  # noqa: E402

from engine.market_os.macro_workspaces import consumer_payments as cp  # noqa: E402
from engine.market_os.macro_workspaces import contract  # noqa: E402
from engine.market_os.macro_workspaces.publication_prior import (  # noqa: E402
    apply_headline_publication_fields,
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


def test_producer_seal_substitutes_resolved_earlier_publication() -> None:
    body = {
        "headline": {
            "effective_date": "2026-07-01",
            "quadrant": {"x": 70.0, "y": 80.0, "x_status": "PRESENT", "y_status": "PRESENT"},
            "prior_state": {"state_id": "B", "effective_date": "2026-07-01",
                            "method_version": "v1"},
            "one_month_vector": {"dx": 0.0, "dy": 0.0, "status": "PRESENT",
                                 "null_reason": None},
            "transition_distance": 0.0,
        },
        "changes": {
            "comparability": "COMPARABLE",
            "prior_effective_date": "2026-07-01",
            "prior_generation_id": "july",
            "prior_method_version": "v1",
            "deltas": [{"metric_id": "retail_sales_level", "prior_value": 700000.0,
                        "current_value": 702500.0, "delta": 0.0, "note": "x"}],
            "status": "PRESENT",
            "null_reason": None,
        },
    }
    stored = {
        "headline": {"effective_date": "2026-07-01", "method_version": "v1",
                     "quadrant": {"x": 70.0, "y": 80.0}},
        "generation": {"generation_id": "july"},
        "changes": {
            "prior_effective_date": "2026-06-01",
            "prior_generation_id": "june",
            "prior_method_version": "v1",
            "deltas": [
                {"metric_id": "retail_sales_level", "prior_value": 680000.0,
                 "current_value": 700000.0, "delta": 20000.0},
                {"metric_id": "growth_momentum", "prior_value": 10.0,
                 "current_value": 70.0, "delta": 60.0},
                {"metric_id": "growth_level_breadth", "prior_value": 20.0,
                 "current_value": 80.0, "delta": 60.0},
            ],
        },
    }
    sealed = apply_producer_prior_seal(body, stored)
    assert sealed["changes"]["comparability"] == "COMPARABLE"
    assert sealed["changes"]["prior_effective_date"] == "2026-06-01"
    row = sealed["changes"]["deltas"][0]
    assert row["prior_value"] == pytest.approx(680000.0)
    assert row["current_value"] == pytest.approx(702500.0)
    assert row["delta"] == pytest.approx(22500.0)
    assert sealed["headline"]["one_month_vector"]["dx"] == pytest.approx(60.0)
    assert sealed["headline"]["prior_state"]["effective_date"] == "2026-06-01"


_COMPOSER_MODULES = (
    "business_activity",
    "capital_structure",
    "consumer_payments",
    "financial_conditions",
    "growth",
    "housing",
    "inflation",
    "labor",
    "liquidity_central_banks",
    "liquidity_regime",
    "monetary_policy",
    "national_debt",
    "rates_curves",
    "trade_flows",
)
_QUADRANT_COMPOSERS = frozenset({
    "growth", "inflation", "labor", "liquidity_regime",
    "financial_conditions", "consumer_payments",
})
_CONTRADICTION = {"present": False, "kind": None, "components": []}
_ASOF = "2026-07-01"
_PRIOR_ASOF = "2026-06-01"


def _stored(mod, eff: str, x: float = 10.0, y: float = 20.0) -> dict:
    return {
        "headline": {
            "effective_date": eff,
            "method_version": mod.METHOD_VERSION,
            "state_id": "B",
            "quadrant": {"x": x, "y": y, "x_status": "PRESENT", "y_status": "PRESENT"},
        },
        "generation": {"generation_id": f"{eff}-gen"},
        "changes": {"prior_effective_date": None, "deltas": []},
        "metrics": {"items": []},
    }


def _call_headline(mod, resolved):
    name = mod.__name__.rsplit(".", 1)[-1]
    if name == "growth":
        return mod._headline(40.0, "PRESENT", None, 60.0, "PRESENT", None, _ASOF, resolved)
    if name in {"inflation", "labor", "liquidity_regime", "financial_conditions"}:
        return mod._headline(40.0, "PRESENT", None, 60.0, "PRESENT", None,
                             _ASOF, resolved, _CONTRADICTION)
    if name == "consumer_payments":
        return mod._headline(40.0, "PRESENT", None, 60.0, "PRESENT", None, _ASOF, resolved)
    return mod._headline(_ASOF, resolved)


@pytest.mark.parametrize("wid", _COMPOSER_MODULES)
def test_headline_vector_uses_publication_prior(wid) -> None:
    mod = importlib.import_module(f"engine.market_os.macro_workspaces.{wid}")
    same = _stored(mod, _ASOF, x=40.0, y=60.0)
    resolved_same = resolve_publication_prior(same, _ASOF)
    assert resolved_same is None
    rebuilt = apply_headline_publication_fields(
        _call_headline(mod, resolved_same), resolved_same, raw_prior=same)
    assert rebuilt["one_month_vector"] is None
    assert rebuilt["transition_distance"] is None
    assert rebuilt["movement_state"] == "NO_EARLIER_PUBLICATION"

    earlier = _stored(mod, _PRIOR_ASOF, x=10.0, y=20.0)
    resolved_earlier = resolve_publication_prior(earlier, _ASOF)
    assert resolved_earlier is earlier
    later = apply_headline_publication_fields(
        _call_headline(mod, resolved_earlier), resolved_earlier, raw_prior=earlier)
    assert later["movement_state"] is None
    if wid in _QUADRANT_COMPOSERS:
        vec = later["one_month_vector"]
        assert vec["status"] == "PRESENT"
        assert vec["dx"] == pytest.approx(30.0)
        assert vec["dy"] == pytest.approx(40.0)
        assert later["transition_distance"] == pytest.approx(50.0)
    else:
        vec = later["one_month_vector"]
        assert vec is not None
        assert vec.get("status") != "PRESENT" or vec.get("dx") is None


def test_shell_null_vector_slot_prints_no_earlier_reading_both_locales() -> None:
    fx = _frames()
    first = _compose(fx["july"], fx["built_at"])
    second = _compose(fx["july"], fx["built_at"], prior=first)
    assert second["headline"]["one_month_vector"] is None
    assert second["headline"]["movement_state"] == "NO_EARLIER_PUBLICATION"
    view = V.build_view(
        second, page_built_at="2026-09-04T00:00:00Z",
        artifact={"path": "x", "manifest_path": "y", "sha256": "z", "bytes": 1,
                  "min_client_contract": "mastermind.macro_workspace_snapshot.v1@1.0.0"},
    )
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=True, undefined=StrictUndefined)
    html = env.from_string(
        '{% import "_macro_suite_shell.html.j2" as shell %}'
        "{{ shell.headline_band(view) }}"
    ).render(view=view)
    assert "No earlier reading yet" in html
    assert "暂无更早读数" in html
    assert "Δx 0.0" not in html and "Δx +0" not in html
    assert "None" not in html
    assert "Movement since the prior accepted print" in html


def _artifact() -> dict:
    return {"path": "x", "manifest_path": "y", "sha256": "z", "bytes": 1,
            "min_client_contract": "mastermind.macro_workspace_snapshot.v1@1.0.0"}


def test_view_absence_labels_three_cases_both_locales() -> None:
    fx = _frames()
    first = _compose(fx["july"], fx["built_at"])
    second = _compose(fx["july"], fx["built_at"], prior=first)
    view_none = V.build_view(second, page_built_at="2026-09-04T00:00:00Z",
                             artifact=_artifact())
    assert view_none["changes"]["absence"]["label"]["en"] == "No earlier reading yet"
    assert view_none["changes"]["absence"]["label"]["zh"] == "暂无更早读数"
    assert view_none["glance"]["change"]["absence"]["label"]["en"] == "No earlier reading yet"
    assert view_none["glance"]["change"]["absence"]["label"]["zh"] == "暂无更早读数"

    snap = json.loads(json.dumps(second))
    snap["changes"] = {
        "comparability": "COMPARABLE",
        "prior_effective_date": "2026-06-01",
        "prior_generation_id": "june",
        "prior_method_version": "v1",
        "deltas": [{
            "metric_id": "retail_sales_level",
            "prior_value": 680000.0,
            "current_value": None,
            "delta": None,
            "note": "x",
        }],
        "status": "PRESENT",
        "null_reason": None,
    }
    view_cur = V.build_view(snap, page_built_at="2026-09-04T00:00:00Z",
                            artifact=_artifact())
    row = view_cur["changes"]["deltas"][0]
    assert row["prior_present"] is True
    assert row["current_present"] is False
    assert row["absence"]["label"]["en"] == "Current reading not available"
    assert row["absence"]["label"]["zh"] == "当前读数不可用"
    assert view_cur["glance"]["change"]["absence"]["label"]["en"] == (
        "Current reading not available")
    assert view_cur["glance"]["change"]["absence"]["label"]["zh"] == "当前读数不可用"

    snap2 = json.loads(json.dumps(snap))
    snap2["changes"]["deltas"][0]["current_value"] = 702500.0
    snap2["changes"]["deltas"][0]["delta"] = None
    view_delta = V.build_view(snap2, page_built_at="2026-09-04T00:00:00Z",
                              artifact=_artifact())
    computed = view_delta["changes"]["deltas"][0]
    assert computed["comparable"] is True
    assert computed["absence"] is None
    assert computed["delta_raw"] == pytest.approx(22500.0)
    assert computed["sign"] == "up"

