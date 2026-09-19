"""tests/test_build_options_hub_nightly.py — scripts/build_options_hub_nightly.py.

OEU bug-wave finding: the published options_hub/gex/{ROOT}.json carries a
headline `asof` and a self-consistent `coverage` block (both computed live from
the greeks/OI read for that session), but its `history` tail comes from a
SEPARATELY-CADENCED store (data/polygon_gex/summary_{ROOT}.parquet) that can lag
behind by one or more sessions with nothing in the payload disclosing the gap —
a reader sees one "asof" and a stale history tail contradicting it.

_attach_gex_history is the one place `history` is joined onto the live gex
payload (scripts/build_options_hub_nightly.build_root, CONTRACT v2). This
suite pins:
  - history is still OMITTED (not set to null) when the store is absent —
    CONTRACT v2's own frontend-checks-key-presence rule, unchanged.
  - when history IS attached, coverage now carries `history_asof` — the tail's
    own last date — so asof vs coverage.asof vs coverage.history_asof can be
    reconciled by a reader instead of silently disagreeing.
"""
from __future__ import annotations

import json

import pandas as pd

import scripts.build_options_hub_nightly as hub_builder

from scripts.build_options_hub_nightly import (
    _attach_gex_history,
    _nulled_nonfinite,
    _write_json,
)


def test_history_omitted_key_stays_omitted_when_store_absent():
    """CONTRACT v2: absent polygon_gex parquet -> 'history' key ABSENT, never
    null — the frontend checks key presence. Must not regress."""
    payload = {"schema": "options_hub.gex/v1", "asof": "2026-07-23",
               "coverage": {"asof": "2026-07-23", "n_contracts": 100}}
    out = _attach_gex_history(payload, None)
    assert "history" not in out
    assert "history_asof" not in out["coverage"]
    assert out == payload


def test_history_attached_discloses_its_own_last_date():
    payload = {"schema": "options_hub.gex/v1", "asof": "2026-07-23",
               "coverage": {"asof": "2026-07-23", "oi_date": "t-1", "n_contracts": 9959}}
    hist = [{"date": "2026-07-18"}, {"date": "2026-07-19"}, {"date": "2026-07-20"}]
    out = _attach_gex_history(payload, hist)
    assert out["history"] == hist
    assert out["coverage"]["history_asof"] == "2026-07-20"
    # The live-computed fields must be untouched — this only ADDS a fact.
    assert out["coverage"]["asof"] == "2026-07-23"
    assert out["asof"] == "2026-07-23"


def test_history_asof_reveals_the_lag_against_the_live_asof():
    """The exact defect: asof=2026-07-23 while history[-1].date=2026-07-20 —
    three real sessions absent from the series the headline claims to
    summarise.  Reconciling that gap now only needs coverage.history_asof."""
    payload = {"schema": "options_hub.gex/v1", "asof": "2026-07-23",
               "coverage": {"asof": "2026-07-23", "since": "2026-07-23"}}
    hist = [{"date": "2026-07-18"}, {"date": "2026-07-19"}, {"date": "2026-07-20"}]
    out = _attach_gex_history(payload, hist)
    assert out["asof"] != out["coverage"]["history_asof"]
    assert out["coverage"]["history_asof"] == "2026-07-20"


def test_empty_history_list_discloses_a_null_history_asof():
    """hist == [] (not None) — the store IS reachable but empty.  history_asof
    must be null, not crash on an index into an empty list."""
    payload = {"coverage": {"asof": "2026-07-23"}}
    out = _attach_gex_history(payload, [])
    assert out["history"] == []
    assert out["coverage"]["history_asof"] is None


def test_original_payload_dict_is_not_mutated():
    """build_root's own callers may hold a reference to the pre-attach payload
    (the fail-soft path re-uses it on exception) — _attach_gex_history must
    return a NEW dict, never mutate the caller's in place."""
    payload = {"coverage": {"asof": "2026-07-23"}}
    out = _attach_gex_history(payload, [{"date": "2026-07-20"}])
    assert "history" not in payload
    assert "history_asof" not in payload["coverage"]
    assert out is not payload


# ── WP-GEX-DATES (Options Superintelligence R0.10) ───────────────────────────
# The dated gex_history snapshots gained a sessions index (dates.json) + a
# bounded self-heal. These pin the pure pieces: the index shape law (newest
# first, latest == dates[0], junk dropped), the validator (reject, never
# coerce), the calendar-driven miss computation (weekends are NOT holes — the
# long-lived "2026-07-18 hole" note was a Saturday; the real hole is 07-20),
# and the point-in-time trim on healed payloads (a late-published snapshot
# must not carry history rows after the date it claims to describe).

from scripts.build_options_hub_nightly import (  # noqa: E402
    build_gex_dates_index,
    is_gex_dates,
    gex_history_missed_sessions,
    _trim_history_to,
)


def test_gex_dates_index_sorts_newest_first_and_drops_junk():
    idx = build_gex_dates_index(
        ["2026-07-17", "2026-07-21", "2026-07-21", "not-a-date", None, ""],
        root="SPY", asof="2026-07-31T02:00:00+00:00",
    )
    assert idx["schema"] == "options_hub.gex_dates/v1"
    assert idx["dates"] == ["2026-07-21", "2026-07-17"]
    assert idx["latest"] == "2026-07-21"
    assert idx["count"] == 2
    assert idx["root"] == "SPY"
    assert is_gex_dates(idx)


def test_gex_dates_index_empty_is_valid_with_null_latest():
    idx = build_gex_dates_index([], root="NOPE", asof="")
    assert idx["dates"] == []
    assert idx["latest"] is None
    assert idx["count"] == 0
    assert is_gex_dates(idx)


def test_is_gex_dates_rejects_rather_than_coerces():
    good = {"root": "SPY", "dates": ["2026-07-21", "2026-07-17"], "latest": "2026-07-21"}
    assert is_gex_dates(good)
    assert not is_gex_dates({**good, "dates": ["2026-07-17", "2026-07-21"]})  # wrong order
    assert not is_gex_dates({**good, "latest": "2026-07-17"})                  # latest != dates[0]
    assert not is_gex_dates({**good, "dates": ["2026-07-21", "junk"]})         # non-date entry
    assert not is_gex_dates({"dates": ["2026-07-21"], "latest": "2026-07-21"})  # no root
    assert not is_gex_dates({"root": "SPY", "dates": [], "latest": "2026-07-21"})
    assert not is_gex_dates(None)


def test_missed_sessions_finds_the_real_hole_and_ignores_weekends():
    # Live plane as verified 2026-07-31: snapshots exist for every session in
    # the epoch→asof window EXCEPT Monday 2026-07-20. 07-18/19 and 07-25/26 are
    # weekends — the calendar must not report them as holes.
    existing = ["2026-07-30", "2026-07-29", "2026-07-28", "2026-07-27",
                "2026-07-24", "2026-07-23", "2026-07-22", "2026-07-21",
                "2026-07-17"]
    missed = gex_history_missed_sessions(existing, "2026-07-30")
    assert missed == ["2026-07-20"]


def test_missed_sessions_includes_a_suppressed_tonight_and_orders_newest_first():
    missed = gex_history_missed_sessions(["2026-07-17"], "2026-07-21")
    assert missed == ["2026-07-21", "2026-07-20"]


def test_missed_sessions_empty_plane_expects_every_session_since_epoch():
    missed = gex_history_missed_sessions([], "2026-07-20")
    assert missed == ["2026-07-20", "2026-07-17"]


def test_trim_history_cuts_future_rows_and_restates_history_asof():
    payload = {
        "asof": "2026-07-20",
        "coverage": {"asof": "2026-07-20", "history_asof": "2026-07-30"},
        "history": [{"date": "2026-07-17"}, {"date": "2026-07-20"},
                    {"date": "2026-07-21"}, {"date": "2026-07-30"}],
    }
    out = _trim_history_to(payload, "2026-07-20")
    assert [h["date"] for h in out["history"]] == ["2026-07-17", "2026-07-20"]
    assert out["coverage"]["history_asof"] == "2026-07-20"
    # PIT law: the original dict is not mutated (fail-soft callers may reuse it).
    assert [h["date"] for h in payload["history"]][-1] == "2026-07-30"
    assert payload["coverage"]["history_asof"] == "2026-07-30"


def test_trim_history_all_future_leaves_empty_history_and_null_asof():
    payload = {"history": [{"date": "2026-07-21"}], "coverage": {}}
    out = _trim_history_to(payload, "2026-07-20")
    assert out["history"] == []
    assert out["coverage"]["history_asof"] is None


def test_trim_history_without_history_key_is_a_no_op():
    payload = {"asof": "2026-07-20", "coverage": {"asof": "2026-07-20"}}
    out = _trim_history_to(payload, "2026-07-20")
    assert "history" not in out
    assert out == payload


# ── non-finite scrubbing on publish ───────────────────────────────────────────
# On 2026-08-07 a single NaN inside the cross-root aggregate raised out of
# json.dumps(allow_nan=False) and took the whole 380-root board with it. The
# desks kept serving the previous incremental checkpoint (372 names) and reported
# "Partial" for two days. These pin the blast radius at one cell, and pin that a
# non-finite value still never reaches a reader as a number.

def test_nonfinite_values_become_null_and_are_counted():
    counter = [0]
    out = _nulled_nonfinite(
        {"good": 1.5, "nan": float("nan"), "inf": float("inf"),
         "ninf": float("-inf")},
        counter,
    )
    assert out == {"good": 1.5, "nan": None, "inf": None, "ninf": None}
    assert counter[0] == 3


def test_nested_lists_and_dicts_are_scrubbed_in_place_of_the_payload():
    counter = [0]
    out = _nulled_nonfinite(
        {"rows": [{"root": "SPY", "gex": float("nan")},
                  {"root": "QQQ", "gex": 2.0}]},
        counter,
    )
    assert out["rows"][0]["gex"] is None
    assert out["rows"][1]["gex"] == 2.0
    assert out["rows"][0]["root"] == "SPY"   # non-floats pass through untouched
    assert counter[0] == 1


def test_clean_payload_is_untouched_and_counts_nothing():
    counter = [0]
    payload = {"asof": "2026-08-06", "rows": [{"gex": 1.0}], "n": 3}
    assert _nulled_nonfinite(payload, counter) == payload
    assert counter[0] == 0


def test_write_json_publishes_a_payload_containing_a_nan(tmp_path):
    """THE regression: one bad cell used to abort the entire publish."""
    path = tmp_path / "oi_movers.json"
    _write_json(path, {"asof": "2026-08-06",
                       "rows": [{"root": "SPY", "d_oi_pct": float("nan")}]})
    written = json.loads(path.read_text())
    assert written["rows"][0]["d_oi_pct"] is None
    assert written["asof"] == "2026-08-06"
    assert "NaN" not in path.read_text()   # never the invalid JSON literal

# ── MOVES current-source fallback / stale-object clearing ─────────────────────
from scripts.build_options_hub_nightly import (  # noqa: E402
    resolve_moves_inputs,
    _moves_publishable,
    _build_moves_payload,
    _moves_only_coverage_roots,
    _publish_moves_only_coverage,
)
from engine.moves_engine import moves_payload  # noqa: E402


def _theta_snapshot(*, root="INTC", asof="2026-09-17", spot=107.02, iv=0.6252):
    # One exact-30-DTE expiry is enough to pin the canonical compute_vol ATM-IV path.
    return pd.DataFrame([
        {
            "root": root,
            "expiration": pd.Timestamp("2026-10-17"),
            "strike": 107.0,
            "right": "C",
            "snapshot_ts": pd.Timestamp(f"{asof} 16:00:00"),
            "implied_vol": iv,
            "underlying_price": spot,
        },
        {
            "root": root,
            "expiration": pd.Timestamp("2026-10-17"),
            "strike": 108.0,
            "right": "P",
            "snapshot_ts": pd.Timestamp(f"{asof} 15:59:59"),
            "implied_vol": iv,
            "underlying_price": spot,
        },
    ])


def test_moves_inputs_prefer_same_session_thetadata_eod_pair():
    got = resolve_moves_inputs(
        "INTC", "2026-09-17",
        {"spot_ref": 108.0}, {"atm_iv": 55.0},
        snapshot_loader=lambda _root: _theta_snapshot(),
    )
    assert got == {
        "spot": 108.0, "atm_iv_pct": 55.0,
        "input_source": "thetadata_eod", "asof": "2026-09-17",
    }


def test_moves_inputs_fall_back_to_same_session_thetadata_snapshot():
    got = resolve_moves_inputs(
        "INTC", "2026-09-17",
        {"spot_ref": None}, {"atm_iv": None},
        snapshot_loader=lambda _root: _theta_snapshot(),
    )
    assert got == {
        "spot": 107.02, "atm_iv_pct": 62.52,
        "input_source": "thetadata_snapshot", "asof": "2026-09-17",
    }


def test_moves_inputs_accept_newer_vendor_stamped_snapshot_than_settled_eod():
    got = resolve_moves_inputs(
        "INTC", "2026-09-17",
        {"spot_ref": None}, {"atm_iv": None},
        snapshot_loader=lambda _root: _theta_snapshot(
            asof="2026-09-18", spot=108.92, iv=0.638986,
        ),
    )
    assert got == {
        "spot": 108.92, "atm_iv_pct": 63.8986,
        "input_source": "thetadata_snapshot", "asof": "2026-09-18",
    }


def test_moves_inputs_refuse_snapshot_older_than_settled_eod():
    got = resolve_moves_inputs(
        "INTC", "2026-09-17",
        {"spot_ref": None}, {"atm_iv": None},
        snapshot_loader=lambda _root: _theta_snapshot(asof="2026-09-16"),
        snapshot_asof_ceiling="2026-09-18",
    )
    assert got == {"spot": None, "atm_iv_pct": None, "input_source": None, "asof": None}


def test_moves_inputs_refuse_snapshot_beyond_latest_settled_session():
    got = resolve_moves_inputs(
        "INTC", "2026-09-17",
        {"spot_ref": None}, {"atm_iv": None},
        snapshot_loader=lambda _root: _theta_snapshot(asof="2026-09-19"),
        snapshot_asof_ceiling="2026-09-18",
    )
    assert got == {"spot": None, "atm_iv_pct": None, "input_source": None, "asof": None}


def test_moves_inputs_refuse_cross_root_snapshot():
    got = resolve_moves_inputs(
        "INTC", "2026-09-17",
        {"spot_ref": None}, {"atm_iv": None},
        snapshot_loader=lambda _root: _theta_snapshot(root="AAPL"),
    )
    assert got == {"spot": None, "atm_iv_pct": None, "input_source": None, "asof": None}


def test_moves_inputs_malformed_snapshot_degrades_to_current_null_instead_of_raising():
    malformed = _theta_snapshot()
    malformed["strike"] = "not-a-number"
    got = resolve_moves_inputs(
        "INTC", "2026-09-17",
        {"spot_ref": None}, {"atm_iv": None},
        snapshot_loader=lambda _root: malformed,
        snapshot_asof_ceiling="2026-09-18",
    )
    assert got == {"spot": None, "atm_iv_pct": None, "input_source": None, "asof": None}


def test_current_null_moves_payload_is_publishable_to_clear_stale_r2_object():
    payload = moves_payload("INTC", "2026-09-17", None, None, input_source=None)
    assert payload["expected_move"] is None
    assert _moves_publishable(payload, "INTC", "2026-09-17") is True


def test_build_moves_payload_turns_newer_intc_theta_snapshot_into_fresh_band():
    payload = _build_moves_payload(
        "INTC", "2026-09-17", {"spot_ref": None}, {"atm_iv": None},
        calibration=None, learned_band_mult={"sticky": 1.1, "all": 1.3}, regime="sticky",
        snapshot_loader=lambda _root: _theta_snapshot(
            asof="2026-09-18", spot=108.92, iv=0.638986,
        ),
        snapshot_asof_ceiling="2026-09-18",
    )
    assert payload["asof"] == "2026-09-18"
    assert payload["input_source"] == "thetadata_snapshot"
    assert payload["regime"] is None
    assert payload["learned_band_mult"]["value"] == 1.3
    assert payload["spot_ref"] == 108.92
    assert payload["atm_iv"] == 63.8986
    assert payload["expected_move"] == {
        "band_mult": 1.96, "horizon_days": 1.0, "pct": 7.8895,
        "lo": 100.3268, "hi": 117.5132,
    }
    assert "no_data_reason" not in payload
    assert _moves_publishable(payload, "INTC", "2026-09-17") is True


def test_historical_replay_ceiling_refuses_newer_snapshot_and_clears_stale_band():
    payload = _build_moves_payload(
        "INTC", "2026-09-17", {"spot_ref": None}, {"atm_iv": None},
        calibration=None, learned_band_mult=None, regime=None,
        snapshot_loader=lambda _root: _theta_snapshot(asof="2026-09-18"),
        snapshot_asof_ceiling="2026-09-17",
    )
    assert payload["asof"] == "2026-09-17"
    assert payload["input_source"] is None
    assert payload["expected_move"] is None
    assert payload["no_data_reason"] == "no_current_spot_iv_pair"


def test_build_moves_payload_publishes_current_null_when_every_current_input_is_absent():
    payload = _build_moves_payload(
        "WBS", "2026-09-17", {"spot_ref": None}, {"atm_iv": None},
        calibration=None, learned_band_mult=None, regime=None,
        snapshot_loader=lambda _root: None,
    )
    assert payload["asof"] == "2026-09-17"
    assert payload["input_source"] is None
    assert payload["expected_move"] is None
    assert payload["no_data_reason"] == "no_current_spot_iv_pair"
    assert _moves_publishable(payload, "WBS", "2026-09-17") is True


def test_moves_publishable_rejects_cross_root_or_regressing_session():
    p = moves_payload("INTC", "2026-09-17", 107.02, 62.52, input_source="thetadata_snapshot")
    assert not _moves_publishable(p, "AAPL", "2026-09-17")
    assert not _moves_publishable(p, "INTC", "2026-09-18")
    assert _moves_publishable(p, "INTC", "2026-09-16")
    malformed = {**p, "asof": "9999-99-99"}
    assert not _moves_publishable(malformed, "INTC", "2026-09-17")


# ── MOVES breadth post-pass selection ─────────────────────────────────────────

def test_moves_only_coverage_roots_add_uncapped_roster_without_repeating_primary_roots():
    got = _moves_only_coverage_roots(
        ["SPY", "INTC"],
        roots_override=None,
        date_override=None,
        universe_roots=["SPY", "AAPL", "INTC", "BABA", "AAPL", "UBER"],
    )
    assert got == ["AAPL", "BABA", "UBER"]


def test_moves_only_coverage_roots_skip_broadening_for_explicit_roots_or_historical_date():
    universe = ["SPY", "AAPL", "INTC"]
    assert _moves_only_coverage_roots(
        ["SPY"], roots_override=["SPY"], date_override=None, universe_roots=universe,
    ) == []
    assert _moves_only_coverage_roots(
        ["SPY"], roots_override=None, date_override="2026-09-17", universe_roots=universe,
    ) == []


def test_moves_only_coverage_roots_normalize_case_and_dedupe_roster():
    got = _moves_only_coverage_roots(
        ["spy"], roots_override=None, date_override=None,
        universe_roots=["SPY", "aapl", "AAPL", "intc"],
    )
    assert got == ["AAPL", "INTC"]


def test_moves_only_postpass_writes_and_uploads_only_moves_plane(monkeypatch, tmp_path):
    builds = []
    writes = []
    uploads = []

    def fake_build(root, asof, gex_payload, vol_payload, **kwargs):
        builds.append((root, asof, gex_payload, vol_payload, kwargs.get("regime")))
        return moves_payload(
            root, asof, 100.0, 20.0, input_source="thetadata_snapshot",
        )

    def fake_write(path, payload):
        writes.append((path.relative_to(tmp_path).as_posix(), payload["root"]))

    def fake_upload(_s3, _bucket, path, key):
        uploads.append((path.relative_to(tmp_path).as_posix(), key))
        return True

    monkeypatch.setattr(hub_builder, "_build_moves_payload", fake_build)
    monkeypatch.setattr(hub_builder, "_write_json", fake_write)
    monkeypatch.setattr(hub_builder, "_upload_r2", fake_upload)

    result = _publish_moves_only_coverage(
        ["AAPL", "BABA"],
        asof="2026-09-17",
        out_dir=tmp_path,
        s3=object(),
        bucket="bucket",
        moves_grades_by_root={},
        moves_learned_mult=None,
        snapshot_asof_ceiling="2026-09-18",
        max_workers=1,
    )

    assert builds == [
        ("AAPL", "2026-09-17", {}, {}, None),
        ("BABA", "2026-09-17", {}, {}, None),
    ]
    assert writes == [("moves/AAPL.json", "AAPL"), ("moves/BABA.json", "BABA")]
    assert uploads == [
        ("moves/AAPL.json", "options_hub/moves/AAPL.json"),
        ("moves/BABA.json", "options_hub/moves/BABA.json"),
    ]
    assert result == {"requested": 2, "written": 2, "uploaded": 2, "failed": []}


def test_moves_only_postpass_keeps_failed_builds_inert(monkeypatch, tmp_path):
    def fake_build(root, *_args, **_kwargs):
        if root == "BAD":
            raise RuntimeError("boom")
        return moves_payload(root, "2026-09-17", 100.0, 20.0, input_source="thetadata_snapshot")

    monkeypatch.setattr(hub_builder, "_build_moves_payload", fake_build)
    monkeypatch.setattr(hub_builder, "_write_json", lambda *_args, **_kwargs: None)

    result = _publish_moves_only_coverage(
        ["GOOD", "BAD"], asof="2026-09-17", out_dir=tmp_path,
        s3=None, bucket="", moves_grades_by_root={}, moves_learned_mult=None,
        max_workers=1,
    )
    assert result["requested"] == 2
    assert result["written"] == 1
    assert result["uploaded"] == 0
    assert result["failed"] == ["BAD"]


def test_moves_only_default_roster_includes_existing_gex_state_index_roots(monkeypatch, tmp_path):
    from engine import options_universe

    monkeypatch.setattr(options_universe, "gex_symbols_uncapped", lambda: ["SPY", "AAA"])
    index_dir = tmp_path / "site" / "options_structure" / "gex_state"
    index_dir.mkdir(parents=True)
    (index_dir / "_index.json").write_text(json.dumps({
        "schema": "options_structure.gex_state_index/v1",
        "rows": {"NDX": {"asof": "2026-09-17"}, "GLD": {"asof": "2026-09-17"}},
    }))
    monkeypatch.setattr(hub_builder, "_REPO", tmp_path)
    assert _moves_only_coverage_roots(
        ["SPY"], roots_override=None, date_override=None,
    ) == ["AAA", "NDX", "GLD"]
