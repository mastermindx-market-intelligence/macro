"""Component-scope receipts never lend the aggregate clock to other markets.

An optional component scope in the ``intl_prices`` status block names the
markets one component run covered and binds each of them to its own
collection clock, its own retained per-country result receipt and its own
stored-file digests. These cases pin that the aggregate ``checked_at`` is a
batch end, not a source observation: a scoped series is published only on its
own component clock, an unscoped market is never published even when its
stored bars are current and match, and an invalid scope fails closed instead
of falling back to the legacy full-run receipt.
"""
from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

from engine import intl_inputs
from lib.intl_eod_publication import _path, build_eod_inputs
from tests.test_intl_eod_publication import (
    EVALUATED, GENERATION, GRANT, _overview, _panel, _setup,
)

JP = "JP"
KR = "KR"
UNRELATED = ("IN", "AU", "GB", "EZ", "TW")
AGGREGATE_CLOCK = "2026-10-09T15:00:00+00:00"
LAST_DATE = "2026-10-07"
ROWS = 280


def _component(root, market, *, checked_at=AGGREGATE_CLOCK, last_date=LAST_DATE,
               rows=ROWS, last=LAST_DATE, mutate=None):
    """Retain one canonical per-country result receipt and its component."""
    row = intl_inputs.countries()[market]
    store = {}
    post_store = {}
    for series_id in (row["index"], row["fx"]):
        path = _path(root, series_id)
        store[series_id] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rows": rows,
            "last": last,
        }
        post_store[path.name] = store[series_id]
    result = {
        "fetch_result": {"source": "intl_prices", "status": "ok", "last_date": last_date},
        "checked_at": checked_at,
        "post_store": post_store,
    }
    if mutate is not None:
        mutate(result)
    payload = json.dumps(result, indent=2, sort_keys=True).encode("utf-8")
    relative = f"intl/{market}/result.json"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "market": market,
        "result": relative,
        "result_sha256": hashlib.sha256(payload).hexdigest(),
        "checked_at": checked_at,
        "store": store,
    }


def _rewrite_receipt(root, component, *, last_date=LAST_DATE):
    """Rewrite the retained receipt to agree with the component, then rehash it."""
    row = intl_inputs.countries()[component["market"]]
    post_store = {}
    for series_id in (row["index"], row["fx"]):
        post_store[_path(root, series_id).name] = component["store"][series_id]
    result = {
        "fetch_result": {"source": "intl_prices", "status": "ok", "last_date": last_date},
        "checked_at": component["checked_at"],
        "post_store": post_store,
    }
    payload = json.dumps(result, indent=2, sort_keys=True).encode("utf-8")
    (root / component["result"]).write_bytes(payload)
    component["result_sha256"] = hashlib.sha256(payload).hexdigest()


def _install(root, components, scope=None):
    """Write the optional scope keys into the intl_prices status block."""
    path = root / "run_status.json"
    status = json.loads(path.read_text(encoding="utf-8"))
    source = status["sources"]["intl_prices"]
    source["collection_scope"] = list(
        scope if scope is not None else [item["market"] for item in components])
    source["collection_components"] = components
    path.write_text(json.dumps(status), encoding="utf-8")


def _call(root, frame, *, evaluated_at=EVALUATED):
    return build_eod_inputs(
        frame, data_root=root, evaluated_at=evaluated_at, rights=GRANT)


def _series(inputs):
    return {row["series_id"] for row in inputs["source_evidence"]}


def _row(panel, market_id):
    return next(row for row in panel["rows"] if row.get("market_id") == market_id)


def test_scoped_component_receipt_publishes_only_its_own_markets(tmp_path):
    """JP and KR are scoped; the other five markets stay unpublished."""
    frame, series = _setup(tmp_path)
    _install(tmp_path, [_component(tmp_path, JP), _component(tmp_path, KR)])
    result = _call(tmp_path, frame)
    assert result is not None
    delayed, inputs = result
    assert len(series) == 14
    assert _series(inputs) == {"^N225", "USDJPY=X", "^KS11", "USDKRW=X"}
    assert len(inputs["source_evidence"]) == 4
    # The unrelated markets' stored files are current and match the frame.
    for market in UNRELATED:
        row = intl_inputs.countries()[market]
        stored = pd.read_parquet(_path(tmp_path, row["index"]))
        assert stored.index[-1] == pd.Timestamp("2026-10-07")
    panel = _panel(_overview(delayed, inputs))
    local = _panel(_overview(delayed, inputs), basis="local")
    assert panel["eligible_count"] == local["eligible_count"] == 2
    assert {row["market_id"] for row in panel["rows"]
            if row["metric"]["quality"] == "qualified"} == {JP, KR}
    for market in UNRELATED:
        row = _row(panel, market)
        assert row["metric"]["quality"] != "qualified"
        assert row["metric"]["value"] is None


def test_legacy_full_run_receipt_is_unchanged_without_scope_keys(tmp_path):
    """Neither scope key present: the ordinary full-run receipt is untouched."""
    frame, series = _setup(tmp_path)
    status = json.loads((tmp_path / "run_status.json").read_text(encoding="utf-8"))
    source = status["sources"]["intl_prices"]
    assert "collection_scope" not in source
    assert "collection_components" not in source
    result = _call(tmp_path, frame)
    assert result is not None
    delayed, inputs = result
    assert len(inputs["source_evidence"]) == len(series) == 14
    assert _panel(_overview(delayed, inputs))["eligible_count"] == 7
    digest = hashlib.sha256(_path(tmp_path, "^N225").read_bytes()).hexdigest()
    row = next(item for item in inputs["source_evidence"]
               if item["series_id"] == "^N225")
    assert row["decision_ref"] == "saved-parquet:sha256:" + digest


def test_a_scope_over_every_configured_market_reproduces_the_full_run(tmp_path):
    """A complete scope is the full run under the component receipt."""
    frame, series = _setup(tmp_path)
    markets = list(intl_inputs.countries())
    _install(tmp_path, [_component(tmp_path, market) for market in markets])
    result = _call(tmp_path, frame)
    assert result is not None
    delayed, inputs = result
    assert len(inputs["source_evidence"]) == len(series) == 14
    assert _panel(_overview(delayed, inputs))["eligible_count"] == 7


def test_a_stale_component_does_not_borrow_the_aggregate_clock(tmp_path):
    """One expired component is withheld; the fresh component still publishes."""
    frame, _ = _setup(tmp_path)
    _install(tmp_path, [
        _component(tmp_path, JP, checked_at="2026-10-06T15:00:00+00:00"),
        _component(tmp_path, KR),
    ])
    result = _call(tmp_path, frame)
    assert result is not None
    delayed, inputs = result
    assert _series(inputs) == {"^KS11", "USDKRW=X"}
    panel = _panel(_overview(delayed, inputs))
    assert panel["eligible_count"] == 1
    assert _row(panel, JP)["metric"]["value"] is None
    assert _row(panel, KR)["metric"]["value"] is not None


def test_an_older_component_clock_keeps_the_older_common_cutoff(tmp_path):
    """The common cutoff follows the earliest eligible component, not the batch."""
    frame, _ = _setup(tmp_path)
    _install(tmp_path, [
        _component(tmp_path, JP, checked_at="2026-10-08T15:00:00+00:00"),
        _component(tmp_path, KR),
    ])
    result = _call(tmp_path, frame)
    assert result is not None
    delayed, inputs = result
    # 2026-10-08T15:00Z has not cleared 48 hours after the 2026-10-07 bar.
    assert delayed.index[-1] == pd.Timestamp("2026-10-06")
    assert {row["latest_completed_observation"]
            for row in inputs["source_evidence"]} == {"2026-10-06T00:00:00"}


def test_component_receipt_digest_is_traceable_beside_the_saved_digest(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    _install(tmp_path, [component])
    result = _call(tmp_path, frame)
    assert result is not None
    _, inputs = result
    row = next(item for item in inputs["source_evidence"]
               if item["series_id"] == "^N225")
    saved = hashlib.sha256(_path(tmp_path, "^N225").read_bytes()).hexdigest()
    assert row["decision_ref"].startswith("saved-parquet:sha256:" + saved)
    assert component["result_sha256"] in row["decision_ref"]


def test_a_receipt_cannot_grant_admission_by_asserting_it(tmp_path):
    """Retained receipt fields are never a permission grant."""
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP, mutate=lambda result: result.update({
        "eod_inputs_admitted": True,
        "source_evidence": [{"series_id": "^NSEI"}, {"series_id": "^AXJO"}],
    }))
    _install(tmp_path, [component])
    result = _call(tmp_path, frame)
    assert result is not None
    delayed, inputs = result
    assert _series(inputs) == {"^N225", "USDJPY=X"}
    panel = _panel(_overview(delayed, inputs))
    assert panel["eligible_count"] == 1
    assert _row(panel, "IN")["metric"]["value"] is None
    assert _row(panel, "AU")["metric"]["value"] is None


def test_a_scope_with_no_eligible_component_keeps_the_actual_zero_behavior(tmp_path):
    """No admitted component publishes no value; the publisher stays unavailable."""
    from scripts import build_intl as publisher
    frame, _ = _setup(tmp_path)
    _install(tmp_path, [_component(tmp_path, JP, checked_at="2026-10-05T15:00:00+00:00")])
    assert _call(tmp_path, frame) is None
    workspace = publisher._publication_workspace(
        frame, data_root=tmp_path, evaluated_at=EVALUATED)
    assert workspace is not None
    panel = _panel(workspace)
    assert panel["eligible_count"] == 0
    assert panel["ranking_reason"] == "no_qualified_returns"


def test_a_duplicate_scope_market_fails_closed(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    _install(tmp_path, [component], scope=[JP, JP])
    assert _call(tmp_path, frame) is None


def test_an_unknown_scope_market_fails_closed(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    _install(tmp_path, [component], scope=[JP, "ZZ"])
    assert _call(tmp_path, frame) is None


def test_the_scope_and_component_domains_must_match(tmp_path):
    frame, _ = _setup(tmp_path)
    components = [_component(tmp_path, JP), _component(tmp_path, KR)]
    _install(tmp_path, components, scope=[JP])
    assert _call(tmp_path, frame) is None
    _install(tmp_path, components[:1], scope=[JP, KR])
    assert _call(tmp_path, frame) is None


def test_a_single_scope_key_fails_closed(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    path = tmp_path / "run_status.json"
    status = json.loads(path.read_text(encoding="utf-8"))
    source = status["sources"]["intl_prices"]
    source["collection_scope"] = [JP]
    path.write_text(json.dumps(status), encoding="utf-8")
    assert _call(tmp_path, frame) is None
    status = json.loads(path.read_text(encoding="utf-8"))
    source = status["sources"]["intl_prices"]
    del source["collection_scope"]
    source["collection_components"] = [component]
    path.write_text(json.dumps(status), encoding="utf-8")
    assert _call(tmp_path, frame) is None


def test_a_component_must_bind_exactly_its_configured_index_and_fx(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    other = intl_inputs.countries()[KR]["index"]
    component["store"][other] = dict(component["store"]["^N225"])
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None
    component = _component(tmp_path, JP)
    del component["store"]["USDJPY=X"]
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None


def test_a_receipt_may_not_name_another_country_file(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP, mutate=lambda result: result["post_store"].update(
        {"_KS11.parquet": {"sha256": "0" * 64, "rows": 1, "last": LAST_DATE}}))
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None


def test_the_receipt_post_store_must_equal_the_component_store(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    _rewrite_receipt(tmp_path, component)
    component["store"]["^N225"]["rows"] = 999
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None


def test_an_unsafe_receipt_path_fails_closed(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    component["result"] = "../escaped/result.json"
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None
    component = _component(tmp_path, JP)
    component["result"] = str((tmp_path / component["result"]).resolve())
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None


def test_a_symlinked_receipt_fails_closed(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    frame, _ = _setup(root)
    component = _component(root, JP)
    escaped = tmp_path / "escaped-result.json"
    escaped.write_text("{}", encoding="utf-8")
    link = root / "intl" / JP / "linked.json"
    link.symlink_to(escaped)
    component["result"] = f"intl/{JP}/linked.json"
    component["result_sha256"] = hashlib.sha256(escaped.read_bytes()).hexdigest()
    _install(root, [component])
    assert _call(root, frame) is None


def test_a_missing_receipt_fails_closed(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    (tmp_path / component["result"]).unlink()
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None


def test_a_changed_receipt_fails_closed(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    path = tmp_path / component["result"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["retained_note"] = "rewritten after the receipt was bound"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None


def test_a_forged_component_clock_fails_closed(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    component["checked_at"] = "2026-10-09T16:00:00+00:00"
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None


def test_a_bound_store_digest_must_match_the_stored_bytes(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    forged = dict(component["store"]["^N225"])
    forged["sha256"] = "0" * 64
    component["store"]["^N225"] = forged
    _rewrite_receipt(tmp_path, component)
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None


def test_a_component_clock_after_the_batch_end_fails_closed(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP, checked_at="2026-10-09T18:00:00+00:00")
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None


def test_a_component_clock_after_the_evaluation_fails_closed(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP, checked_at="2026-10-09T21:00:00+00:00")
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None


@pytest.mark.parametrize("bad", ["", "  ", 42, None, [], {}])
def test_a_non_text_receipt_digest_fails_closed(tmp_path, bad):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    component["result_sha256"] = bad
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None


def test_a_missing_bound_store_blob_is_source_failure_not_legacy_fallback(tmp_path):
    frame, _ = _setup(tmp_path)
    _install(tmp_path, [_component(tmp_path, JP), _component(tmp_path, KR)])
    _path(tmp_path, '^N225').unlink()
    assert _call(tmp_path, frame) is None


def test_nonfinite_retained_json_is_not_a_scoped_receipt(tmp_path):
    frame, _ = _setup(tmp_path)
    component = _component(tmp_path, JP)
    path = tmp_path / component['result']
    raw = path.read_bytes().replace(b'"fetch_result":', b'"nonfinite_extra": NaN, "fetch_result":')
    path.write_bytes(raw); component['result_sha256'] = hashlib.sha256(raw).hexdigest()
    _install(tmp_path, [component])
    assert _call(tmp_path, frame) is None
