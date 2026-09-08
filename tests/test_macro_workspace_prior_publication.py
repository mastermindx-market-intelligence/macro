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
    effective_date_of,
    is_strictly_earlier,
    no_earlier_publication,
    prior_publication_snapshot,
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
        "prior_publication": {
            "headline": {
                "effective_date": "2026-06-01",
                "method_version": "v1",
                "state_id": "B",
                "quadrant": {"x": 10.0, "y": 20.0, "x_status": "PRESENT",
                             "y_status": "PRESENT"},
            },
            "metrics": {"items": [
                {"metric_id": "retail_sales_level", "value": 680000.0},
            ]},
            "generation": {"generation_id": "june"},
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
    assert "No vector is drawn: there is no method-comparable prior print to move from." in html


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


def test_growth_same_dated_rebuild_keeps_hysteresis_held_prior() -> None:
    """Reviewer NB1: x=49, y=49 against a June B print must not flip B→C."""
    from engine.market_os.macro_workspaces import growth as g

    june = {
        "headline": {
            "state_id": "B",
            "method_version": g.METHOD_VERSION,
            "effective_date": "2026-06-01",
            "quadrant": {"x": 58.0, "y": 53.0, "x_status": "PRESENT",
                         "y_status": "PRESENT"},
        },
        "generation": {"generation_id": "june-gen"},
        "metrics": {"items": []},
    }
    build1 = g._headline(49.0, "PRESENT", None, 49.0, "PRESENT", None,
                         "2026-07-01", june)
    july = {
        "headline": {"effective_date": "2026-07-01",
                     "method_version": g.METHOD_VERSION,
                     "state_id": build1["state_id"],
                     "quadrant": {"x": 49.0, "y": 49.0}},
        "prior_publication": prior_publication_snapshot(june),
        "metrics": {"items": []},
        "generation": {"generation_id": "july-gen"},
    }
    resolved = resolve_publication_prior(july, "2026-07-01")
    build2 = g._headline(49.0, "PRESENT", None, 49.0, "PRESENT", None,
                         "2026-07-01", resolved)
    assert build1["state_id"] == "B"
    assert build2["state_id"] == "B"
    assert build1["hysteresis"]["held_prior"] is True
    assert build2["hysteresis"]["held_prior"] is True
    assert build1["one_month_vector"] == build2["one_month_vector"]
    assert build1["transition_distance"] == build2["transition_distance"]
    assert build1["hysteresis"]["note"] == build2["hysteresis"]["note"]
    assert build1["one_month_vector"]["dx"] == pytest.approx(-9.0)
    assert build1["one_month_vector"]["dy"] == pytest.approx(-4.0)


def test_consumer_payments_same_dated_rebuild_is_identical_publication() -> None:
    fx = _frames()
    june = _compose(fx["june"], fx["built_at"])
    july = _compose(fx["july"], fx["built_at"], prior=june)
    rebuilt = _compose(fx["july"], fx["built_at"], prior=july)
    assert july["headline"]["state_id"] == rebuilt["headline"]["state_id"]
    assert (july["headline"]["hysteresis"]["held_prior"]
            == rebuilt["headline"]["hysteresis"]["held_prior"])
    assert july["headline"]["one_month_vector"] == rebuilt["headline"]["one_month_vector"]
    assert (july["headline"]["transition_distance"]
            == rebuilt["headline"]["transition_distance"])
    assert july["headline"]["hysteresis"]["note"] == rebuilt["headline"]["hysteresis"]["note"]
    assert rebuilt["changes"] == july["changes"]
    assert rebuilt["prior_publication"] == july["prior_publication"]
    assert july["prior_publication"]["headline"]["effective_date"] == "2026-06-01"
    assert july["prior_publication"]["headline"]["state_id"] == june["headline"]["state_id"]
    contract.validate(july)
    contract.validate(rebuilt)


@pytest.mark.parametrize("wid", _COMPOSER_MODULES)
def test_same_dated_rebuild_matches_first_build_headline(wid) -> None:
    mod = importlib.import_module(f"engine.market_os.macro_workspaces.{wid}")
    earlier = _stored(mod, _PRIOR_ASOF, x=10.0, y=20.0)
    resolved1 = resolve_publication_prior(earlier, _ASOF)
    assert resolved1 is earlier
    build1 = apply_headline_publication_fields(
        _call_headline(mod, resolved1), resolved1, raw_prior=earlier)

    carried = {
        "headline": {
            "effective_date": _ASOF,
            "method_version": mod.METHOD_VERSION,
            "state_id": build1.get("state_id"),
            "quadrant": {"x": 40.0, "y": 60.0},
        },
        "prior_publication": prior_publication_snapshot(earlier),
        "metrics": {"items": []},
        "generation": {"generation_id": "july-gen"},
        "changes": {},
    }
    resolved2 = resolve_publication_prior(carried, _ASOF)
    assert resolved2 is not None
    assert effective_date_of(resolved2) == _PRIOR_ASOF
    assert resolved2["headline"]["state_id"] == "B"
    build2 = apply_headline_publication_fields(
        _call_headline(mod, resolved2), resolved2, raw_prior=carried)
    assert build1["state_id"] == build2["state_id"]
    assert build1["one_month_vector"] == build2["one_month_vector"]
    assert build1["transition_distance"] == build2["transition_distance"]
    h1 = build1.get("hysteresis") or {}
    h2 = build2.get("hysteresis") or {}
    assert h1.get("held_prior") == h2.get("held_prior")
    assert h1.get("note") == h2.get("note")


def test_later_publication_computes_against_stored_earlier_snapshot() -> None:
    fx = _frames()
    june = _compose(fx["june"], fx["built_at"])
    july = _compose(fx["july"], fx["built_at"], prior=june)
    assert july["prior_publication"]["headline"]["effective_date"] == (
        june["headline"]["effective_date"])
    assert _retail(july)["prior_value"] == pytest.approx(680000.0)
    resolved = resolve_publication_prior(july, "2026-08-01")
    assert resolved is july


def test_producer_seal_types_absent_vector_when_prior_quadrant_non_numeric() -> None:
    body = {
        "headline": {
            "effective_date": "2026-07-01",
            "quadrant": {"x": 70.0, "y": 80.0, "x_status": "PRESENT",
                         "y_status": "PRESENT"},
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
        "headline": {"effective_date": "2026-07-01", "method_version": "v1"},
        "prior_publication": {
            "headline": {
                "effective_date": "2026-06-01",
                "method_version": "v1",
                "state_id": "B",
                "quadrant": {"x": None, "y": None, "x_status": "ABSENT",
                             "y_status": "ABSENT"},
            },
            "metrics": {"items": []},
            "generation": {"generation_id": "june"},
        },
    }
    sealed = apply_producer_prior_seal(body, stored)
    vec = sealed["headline"]["one_month_vector"]
    assert vec["status"] == "ABSENT"
    assert vec["null_reason"] == "NO_EARLIER_PUBLICATION"
    assert vec["dx"] is None and vec["dy"] is None
    assert sealed["headline"]["transition_distance"] is None
    assert sealed["headline"]["prior_state"]["effective_date"] == "2026-07-01"


def test_glance_preserves_method_changed_absence_from_real_composer() -> None:
    fx = _frames()
    june = _compose(fx["june"], fx["built_at"])
    june["headline"]["method_version"] = "consumer_payments.compose.OLD"
    july = _compose(fx["july"], fx["built_at"], prior=june)
    assert july["changes"]["comparability"] == "METHOD_CHANGED"
    view = V.build_view(
        july, page_built_at="2026-09-04T00:00:00Z", artifact=_artifact())
    block = view["changes"]["absence"]
    glance = view["glance"]["change"]["absence"]
    assert glance == block
    assert glance["label"]["en"] == (
        "Method version changed — shown as a method change, not a delta")
    assert glance["label"]["zh"] == (
        "方法版本已变更 — 按方法变更呈现，而非数值变化")
    assert glance["label"]["en"] != "Current reading not available"


def test_newly_tracked_metric_without_stored_prior_is_typed_no_earlier() -> None:
    fx = _frames()
    june = _compose(fx["june"], fx["built_at"])
    july = _compose(fx["july"], fx["built_at"], prior=june)
    snap = json.loads(json.dumps(july))
    items = snap["prior_publication"]["metrics"]["items"]
    snap["prior_publication"]["metrics"]["items"] = [
        it for it in items if it.get("metric_id") != "retail_sales_level"
    ]
    rebuilt = _compose(fx["july"], fx["built_at"], prior=snap)
    row = _retail(rebuilt)
    assert row["prior_value"] is None
    view = V.build_view(
        rebuilt, page_built_at="2026-09-04T00:00:00Z", artifact=_artifact())
    retail_view = next(
        d for d in view["changes"]["deltas"] if d["metric_id"] == "retail_sales_level")
    assert retail_view["absence"]["label"]["en"] == "No earlier reading yet"
    assert retail_view["absence"]["label"]["zh"] == "暂无更早读数"


def test_resolve_returns_stored_prior_publication_on_same_dated_rebuild() -> None:
    stored = {
        "headline": {"effective_date": "2026-07-01", "state_id": "C"},
        "prior_publication": {
            "headline": {"effective_date": "2026-06-01", "state_id": "B",
                         "method_version": "v1",
                         "quadrant": {"x": 58.0, "y": 53.0}},
            "metrics": {"items": [{"metric_id": "growth_momentum", "value": 58.0}]},
        },
    }
    resolved = resolve_publication_prior(stored, "2026-07-01")
    assert resolved is stored["prior_publication"]
    assert resolved["headline"]["state_id"] == "B"
    assert resolve_publication_prior(
        {"headline": {"effective_date": "2026-07-01"}}, "2026-07-01"
    ) is None

