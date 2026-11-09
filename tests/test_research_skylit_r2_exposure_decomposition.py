"""Research-only R2 construction contracts with synthetic source inputs."""


# --------------------------------------------------------------------------- Skylit R2 daily Stage 0

from datetime import date, timedelta
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from scripts import research_skylit_r2_exposure_decomposition as r2


def fake_greeks(spot, strike, time_years, vol, is_call):
    spot = np.asarray(spot, dtype=float)
    strike = np.asarray(strike, dtype=float)
    time_years = np.asarray(time_years, dtype=float)
    vol = np.asarray(vol, dtype=float)
    gamma = (0.01 + vol) * np.sqrt(time_years) / np.maximum(spot, 1.0)
    zero = np.zeros_like(gamma)
    return zero, gamma, zero, zero


class Calendar:
    @staticmethod
    def is_session(d):
        return d.weekday() < 5

    @staticmethod
    def session_n_forward(d, n):
        cur = d
        for _ in range(n):
            cur += timedelta(days=1)
            while cur.weekday() >= 5:
                cur += timedelta(days=1)
        return cur


def _chain(prior=(100, 200)):
    return pd.DataFrame([
        {
            "root": "SPY",
            "expiration": "2026-10-16",
            "strike": 100.0,
            "right": "C",
            "implied_vol": 0.20,
            "underlying_price": 100.0,
            "open_interest": prior[0],
        },
        {
            "root": "SPY",
            "expiration": "2026-10-16",
            "strike": 100.0,
            "right": "P",
            "implied_vol": 0.22,
            "underlying_price": 100.0,
            "open_interest": prior[1],
        },
    ])


def _oi(pub_session, values=(110, 190)):
    return pd.DataFrame([
        {
            "root": "SPY",
            "expiration": "2026-10-16",
            "strike": 100.0,
            "right": "C",
            "date": pub_session,
            "open_interest": values[0],
        },
        {
            "root": "SPY",
            "expiration": "2026-10-16",
            "strike": 100.0,
            "right": "P",
            "date": pub_session,
            "open_interest": values[1],
        },
    ])


def test_settled_state_uses_next_session_oi_not_same_day_oi():
    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=lambda s, root, store=None: _chain(prior=(100, 200)),
        oi_for_date=lambda s, root, store=None: _oi(s, values=(110, 190)),
    )
    state = r2.build_settled_state(
        "2026-09-14",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert state["position_publication_session"] == "2026-09-15"
    assert state["frame"]["position"].tolist() == [110.0, 190.0]
    assert state["target_gate_pass"] is True
    assert state["settled_oi_contract_rate"] == 1.0


def test_missing_next_session_oi_fails_coverage_without_zero_imputation():
    next_oi = _oi("2026-09-15").iloc[:1].copy()
    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=lambda s, root, store=None: _chain(),
        oi_for_date=lambda s, root, store=None: next_oi,
    )
    state = r2.build_settled_state(
        "2026-09-14",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert state["settled_oi_contract_rate"] == 0.5
    assert state["target_gate_pass"] is False
    assert len(state["frame"]) == 1


def test_malformed_source_identity_refuses_instead_of_shrinking_board():
    broken = _chain()
    broken.loc[1, "right"] = "UNKNOWN"
    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=lambda s, root, store=None: broken,
        oi_for_date=lambda s, root, store=None: _oi(s),
    )
    with pytest.raises(r2.R2Refusal, match="malformed contract identity rows"):
        r2.build_settled_state(
            "2026-09-14",
            "SPY",
            store_api=api,
            calendar_api=Calendar,
            greeks_fn=fake_greeks,
        )


def test_sparse_underlying_price_cannot_anchor_an_entire_qualified_board():
    chain = _chain()
    chain.loc[1, "underlying_price"] = np.nan
    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=lambda s, root, store=None: chain,
        oi_for_date=lambda s, root, store=None: _oi(s),
    )
    state = r2.build_settled_state(
        "2026-09-14",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert state["spot_input_contract_rate"] == pytest.approx(0.5)
    assert state["model_input_contract_rate"] == pytest.approx(1.0)
    assert state["settled_oi_contract_rate"] == pytest.approx(1.0)
    assert state["target_gate_pass"] is False


def test_zero_iv_source_saturation_is_classified_without_inventing_a_vol():
    chain = _chain()
    chain["delta"] = [0.50, -1.0]
    chain["vega"] = [0.10, 0.0]
    chain["theta"] = [-0.02, 0.0]
    chain.loc[1, "implied_vol"] = 0.0
    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=lambda s, root, store=None: chain,
        oi_for_date=lambda s, root, store=None: _oi(s),
    )
    state = r2.build_settled_state(
        "2026-09-14",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert state["iv_contract_rate"] == pytest.approx(0.5)
    assert state["model_state_classified_rate"] == pytest.approx(1.0)
    assert state["model_input_contract_rate"] == pytest.approx(1.0)
    assert state["saturated_zero_curvature_contract_rate"] == pytest.approx(0.5)
    assert state["unresolved_model_input_contract_rate"] == pytest.approx(0.0)
    assert state["target_gate_pass"] is True

    # The saturated contract is classified for coverage but is NOT given a fake
    # volatility or admitted to the continuous-IV Shapley frame.
    assert len(state["frame"]) == 1
    assert state["frame"]["right"].tolist() == ["C"]
    states = dict(
        zip(
            state["model_state_frame"]["right"],
            state["model_state_frame"]["model_state"],
        )
    )
    assert states == {
        "C": r2.MODEL_STATE_IV,
        "P": r2.MODEL_STATE_SATURATED,
    }


def test_zero_or_missing_iv_without_saturation_evidence_remains_unresolved():
    for bad_iv, bad_delta, bad_vega in [
        (0.0, -0.70, 0.0),
        (0.0, -1.0, 0.01),
        (np.nan, -1.0, 0.0),
    ]:
        chain = _chain()
        chain["delta"] = [0.50, bad_delta]
        chain["vega"] = [0.10, bad_vega]
        chain["theta"] = [-0.02, 0.0]
        chain.loc[1, "implied_vol"] = bad_iv
        api = SimpleNamespace(
            resolve_thetadata_store=lambda **kwargs: "/store",
            chain=lambda s, root, store=None, frame=chain: frame,
            oi_for_date=lambda s, root, store=None: _oi(s),
        )
        state = r2.build_settled_state(
            "2026-09-14",
            "SPY",
            store_api=api,
            calendar_api=Calendar,
            greeks_fn=fake_greeks,
        )
        assert state["model_state_classified_rate"] == pytest.approx(0.5)
        assert state["saturated_zero_curvature_contracts"] == 0
        assert state["unresolved_model_input_contract_rate"] == pytest.approx(0.5)
        assert state["target_gate_pass"] is False


def test_saturation_transition_is_composition_not_position_shapley():
    def chain_for(session, root, store=None):
        frame = _chain(prior=(100, 200))
        frame["delta"] = [0.50, -0.50]
        frame["vega"] = [0.10, 0.10]
        frame["theta"] = [-0.02, -0.02]
        if session == "2026-09-14":
            frame.loc[1, "implied_vol"] = 0.0
            frame.loc[1, "delta"] = -1.0
            frame.loc[1, "vega"] = 0.0
            frame.loc[1, "theta"] = 0.0
        return frame

    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=chain_for,
        oi_for_date=lambda session, root, store=None: (
            _oi(session, values=(110, 190))
            if session == "2026-09-15"
            else _oi(session, values=(120, 180))
        ),
    )
    got = r2.analyze_pair(
        "2026-09-14",
        "2026-09-15",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert got["status"] == "SURVIVOR_DECOMPOSITION_COMPLETE"
    assert got["decomposition"]["survivor_contracts"] == 1
    assert got["composition"]["model_state_from_saturated"] == 1
    assert got["composition"]["model_state_from_saturated_abs_mass"] > 0
    assert got["composition"]["model_state_to_saturated"] == 0
    assert got["composition"]["model_state_to_saturated_abs_mass"] == pytest.approx(0.0)
    assert got["composition"]["unresolved_entries"] == 0
    assert got["composition"]["known_composition_abs_mass"] > 0
    assert got["composition"]["observed_map_change_abs_mass"] > 0
    assert got["composition"]["construction_accounted_abs_mass"] > 0
    assert 0 < got["composition"]["construction_accounted_share"] <= 1
    assert got["composition"]["full_map_composition_resolved"] is False


def test_missing_iv_cannot_disappear_from_the_coverage_denominator():
    broken = _chain()
    broken.loc[1, "implied_vol"] = np.nan
    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=lambda s, root, store=None: broken,
        oi_for_date=lambda s, root, store=None: _oi(s),
    )
    state = r2.build_settled_state(
        "2026-09-14",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert state["unexpired_identity_contracts"] == 2
    assert state["iv_contract_rate"] == 0.5
    assert state["target_gate_pass"] is False


def test_oi_match_rate_uses_full_unexpired_board_even_when_iv_is_missing():
    rows = []
    oi_rows = []
    publication = "2026-09-15"
    for i in range(100):
        right = "C" if i % 2 == 0 else "P"
        strike = 90.0 + i * 0.25
        rows.append({
            "root": "SPY",
            "expiration": "2026-10-16",
            "strike": strike,
            "right": right,
            "implied_vol": (np.nan if i < 10 else 0.20),
            "underlying_price": 100.0,
            "open_interest": 100 + i,
        })
        # The ten IV-missing contracts plus one IV-valid contract are absent
        # from settled OI.  A post-IV denominator would incorrectly see 89/90
        # and pass; the full unexpired board must report 89/100 and fail.
        if i >= 10 and i != 10:
            oi_rows.append({
                "root": "SPY",
                "expiration": "2026-10-16",
                "strike": strike,
                "right": right,
                "date": publication,
                "open_interest": 100 + i,
            })

    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=lambda s, root, store=None: pd.DataFrame(rows),
        oi_for_date=lambda s, root, store=None: pd.DataFrame(oi_rows),
    )
    state = r2.build_settled_state(
        "2026-09-14",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert state["unexpired_identity_contracts"] == 100
    assert state["model_input_contract_rate"] == pytest.approx(0.90)
    assert state["settled_oi_contract_rate"] == pytest.approx(0.89)
    assert state["target_gate_pass"] is False


def _state(position, spot=100.0, vol=0.2, time_years=30 / 365):
    exposure = r2._exposure_gex(
        np.array([position]),
        np.array([spot]),
        np.array([vol]),
        np.array([time_years]),
        np.array([100.0]),
        np.array(["C"]),
        greeks_fn=fake_greeks,
    )[0]
    return pd.DataFrame([
        {
            "root": "SPY",
            "expiration": "2026-10-16",
            "strike": 100.0,
            "right": "C",
            "position": position,
            "spot": spot,
            "vol": vol,
            "time_years": time_years,
            "exposure_gex": exposure,
        },
    ])


def test_position_only_change_is_attributed_to_position():
    got = r2.decompose_survivors(
        _state(100),
        _state(120),
        greeks_fn=fake_greeks,
    )
    assert abs(got["component_net"]["position"]) > 0
    assert abs(got["component_net"]["spot"]) < 1e-12
    assert abs(got["component_net"]["vol"]) < 1e-12
    assert abs(got["component_net"]["time"]) < 1e-12
    assert got["max_contract_closure_error_abs"] < 1e-10


def test_raw_absolute_map_change_survives_cross_contract_net_cancellation():
    def two_sided_state(call_position, put_position):
        return pd.DataFrame([
            {
                "root": "SPY",
                "expiration": "2026-10-16",
                "strike": 100.0,
                "right": "C",
                "position": float(call_position),
                "spot": 100.0,
                "vol": 0.20,
                "time_years": 30 / 365,
                "exposure_gex": 0.0,
            },
            {
                "root": "SPY",
                "expiration": "2026-10-16",
                "strike": 100.0,
                "right": "P",
                "position": float(put_position),
                "spot": 100.0,
                "vol": 0.20,
                "time_years": 30 / 365,
                "exposure_gex": 0.0,
            },
        ])

    got = r2.decompose_survivors(
        two_sided_state(100, 100),
        two_sided_state(120, 120),
        greeks_fn=fake_greeks,
    )
    assert got["raw_survivor_change_net"] == pytest.approx(0.0, abs=1e-12)
    assert got["raw_survivor_change_abs_mass"] > 0
    assert got["component_abs_share"]["position"] == pytest.approx(1.0)
    assert got["max_contract_closure_error_abs"] < 1e-10


def test_mixed_change_shapley_closes_exactly():
    got = r2.decompose_survivors(
        _state(100, spot=100, vol=0.20, time_years=40 / 365),
        _state(130, spot=104, vol=0.27, time_years=39 / 365),
        greeks_fn=fake_greeks,
    )
    assert got["survivor_contracts"] == 1
    assert got["max_contract_closure_error_abs"] < 1e-9
    assert sum(
        value
        for value in got["component_abs_share"].values()
        if value is not None
    ) == pytest.approx(1.0)


def test_analyze_pair_never_opens_outcome_labels_and_requires_consecutive_sessions():
    prior = {
        "2026-09-14": (100, 200),
        "2026-09-15": (110, 190),
    }

    def chain(session, root, store=None):
        return _chain(prior=prior[session])

    def oi_for_date(session, root, store=None):
        values = (110, 190) if session == "2026-09-15" else (120, 180)
        return _oi(session, values=values)

    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=chain,
        oi_for_date=oi_for_date,
    )
    got = r2.analyze_pair(
        "2026-09-14",
        "2026-09-15",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert got["status"] == "SURVIVOR_DECOMPOSITION_COMPLETE"
    assert got["decomposition_scope"] == "survivor_contracts_only"
    assert got["pair_decision_eligible_not_before_session"] == "2026-09-16"
    assert got["exposure_unit"] == "USD dealer-delta change per +1% spot move"
    assert got["method"]["vol_counterfactual"] == "sticky_strike"
    assert got["method"]["kernel"].endswith(".fake_greeks")
    assert "component_net_per_calendar_day" not in got["decomposition"]
    assert got["outcome_labels_opened"] is False
    assert got["decomposition"]["max_contract_closure_error_abs"] < 1e-9

    with pytest.raises(r2.R2Refusal):
        r2.analyze_pair(
            "2026-09-14",
            "2026-09-16",
            "SPY",
            store_api=api,
            calendar_api=Calendar,
            greeks_fn=fake_greeks,
        )


# Real default dependencies, with every byte read supplied by this isolated fixture.
@pytest.fixture()
def default_r2_inputs(tmp_path, monkeypatch):
    from pathlib import Path
    from engine import thetadata_store as theta

    store = tmp_path / "synthetic_store"
    paths = {}
    for tier in ("eod", "oi", "greeks"):
        path = store / tier / "SPY" / "2026.parquet"
        path.parent.mkdir(parents=True)
        path.touch()  # only an existence witness; the parquet reader never opens it.
        paths[tier] = path

    identity = {
        "root": "SPY", "expiration": pd.Timestamp("2026-10-16"), "strike": 100.0}
    eod, greeks, oi = [], [], []
    for session, spot, call_iv, put_iv in (
            ("2026-09-04", 100.0, 0.20, 0.22),
            ("2026-09-08", 101.0, 0.21, 0.23)):
        for right, iv in (("C", call_iv), ("P", put_iv)):
            row = {**identity, "right": right, "date": pd.Timestamp(session)}
            eod.append(dict(row))
            greeks.append({
                **row, "implied_vol": iv, "underlying_price": spot,
                "timestamp": pd.Timestamp(session + "T20:00:00"),
                "underlying_timestamp": pd.Timestamp(session + "T19:59:00")})
    for session, call_oi, put_oi in (
            ("2026-09-04", 100, 200),
            ("2026-09-08", 110, 190),
            ("2026-09-09", 120, 180)):
        for right, value in (("C", call_oi), ("P", put_oi)):
            oi.append({
                **identity, "right": right, "date": pd.Timestamp(session),
                "open_interest": value})
    oi.append({
        **identity, "root": "QQQ", "right": "C",
        "date": pd.Timestamp("2026-09-08"), "open_interest": 999999})
    tables = {"eod": pd.DataFrame(eod), "oi": pd.DataFrame(oi),
              "greeks": pd.DataFrame(greeks)}
    calls = {"reads": [], "candidates": [], "classifications": []}

    def candidates():
        calls["candidates"].append("resolve")
        return [("synthetic", store)]

    def classify(path):
        assert path == store
        calls["classifications"].append(path)
        return theta._HAS_ROOT

    def read_parquet(path, columns=None, filters=None):
        path = Path(path)
        assert path in paths.values(), "a non-fixture store path was requested"
        tier = next(name for name, candidate in paths.items() if candidate == path)
        calls["reads"].append((tier, columns, filters))
        frame = tables[tier].copy(deep=True)
        if columns is not None:
            assert tier == "oi"
            assert columns == list(theta._OI_COLUMNS)
            assert filters is not None and filters[1] == ("root", "==", "SPY")
            assert filters[0][0:2] == ("date", "==")
            assert filters[0][2] in (
                pd.Timestamp("2026-09-08"), pd.Timestamp("2026-09-09"))
            # Return wrong-date/root witnesses too: the real reader must re-prove them.
            frame = frame.loc[:, columns]
        else:
            assert filters is None
        return frame

    monkeypatch.setattr(theta, "_store_candidates", candidates)
    monkeypatch.setattr(theta, "_classify_store", classify)
    monkeypatch.setattr(theta, "_PARQUET_CACHE", {})
    monkeypatch.setattr(theta.pd, "read_parquet", read_parquet)
    return SimpleNamespace(api=theta, store=store, paths=paths,
                           tables=tables, calls=calls)


def _default_r2_pair():
    return r2.analyze_pair("2026-09-04", "2026-09-08", "spy")


def _r2_cli_args():
    return ["--root", "SPY", "--session0", "2026-09-04",
            "--session1", "2026-09-08"]


def test_default_readers_kernel_and_real_holiday_calendar(default_r2_inputs):
    from engine import intraday_greeks

    fixture = default_r2_inputs
    got = _default_r2_pair()
    assert got["status"] == "SURVIVOR_DECOMPOSITION_COMPLETE"
    assert got["research_authority"] == "research_only"
    assert got["outcome_labels_opened"] is False
    assert got["elapsed_calendar_days"] == 4
    assert got["state0"]["position_publication_session"] == "2026-09-08"
    assert got["state1"]["position_publication_session"] == "2026-09-09"
    assert got["pair_decision_eligible_not_before_session"] == "2026-09-09"
    for state in (got["state0"], got["state1"]):
        assert state["eligible_contracts"] == 2
        assert state["settled_oi_matched_contracts"] == 2
        assert state["target_gate_pass"] is True
        for key in ("model_input_contract_rate", "spot_input_contract_rate",
                    "settled_oi_contract_rate", "prior_oi_contract_rate"):
            assert state[key] == 1.0
    assert got["method"]["kernel"] == "engine.intraday_greeks.bs_greeks_vec"
    assert got["method"]["rate"] == intraday_greeks.DEFAULT_R
    assert got["method"]["dividend_yield"] == intraday_greeks.DEFAULT_Q
    decomposition = got["decomposition"]
    assert decomposition["survivor_contracts"] == 2
    assert set(decomposition["component_net"]) == set(r2.FACTORS)
    assert all(np.isfinite(value) for value in decomposition["component_net"].values())
    assert decomposition["max_contract_closure_error_abs"] < 1e-6
    assert len(fixture.calls["candidates"]) == 2
    reads = fixture.calls["reads"]
    assert len(reads) == 5
    assert [tier for tier, columns, _ in reads if columns is None] == ["eod", "oi", "greeks"]
    narrow = [filters for _, columns, filters in reads if columns is not None]
    assert narrow == [
        [("date", "==", pd.Timestamp("2026-09-08")), ("root", "==", "SPY")],
        [("date", "==", pd.Timestamp("2026-09-09")), ("root", "==", "SPY")],
    ]


def test_default_reader_clock_only_duplicates_preserve_report(default_r2_inputs):
    fixture = default_r2_inputs
    baseline = _default_r2_pair()
    duplicate = fixture.tables["greeks"].iloc[[0]].copy()
    duplicate["timestamp"] += pd.Timedelta(minutes=1)
    duplicate["underlying_timestamp"] += pd.Timedelta(minutes=1)
    fixture.tables["greeks"] = pd.concat(
        [fixture.tables["greeks"], duplicate], ignore_index=True)
    fixture.api._PARQUET_CACHE.clear()  # this fixture owns the rebound cache.
    assert _default_r2_pair() == baseline
    cached = fixture.api._PARQUET_CACHE[str(fixture.paths["greeks"].resolve())]
    assert len(cached) == 5 and "timestamp" in cached.columns


def test_default_reader_conflicting_economics_refuse(default_r2_inputs):
    fixture = default_r2_inputs
    duplicate = fixture.tables["greeks"].iloc[[0]].copy()
    duplicate["implied_vol"] = 0.30
    fixture.tables["greeks"] = pd.concat(
        [fixture.tables["greeks"], duplicate], ignore_index=True)
    with pytest.raises(r2.R2Refusal, match="conflicting duplicate contract identities"):
        _default_r2_pair()


def test_cli_resolver_warning_stays_on_stderr(default_r2_inputs, monkeypatch, capsys):
    import json

    fixture = default_r2_inputs
    monkeypatch.setattr(fixture.api, "_classify_store", lambda path: fixture.api._UNKNOWN)
    assert r2.main(_r2_cli_args()) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)  # decode the entire stream, without removing warnings.
    assert payload["status"] == "SURVIVOR_DECOMPOSITION_COMPLETE"
    assert "::warning title=thetadata-store-unverified::" in captured.err
    assert "::warning" not in captured.out
    assert len(fixture.calls["candidates"]) == 2


def test_cli_unmounted_resolver_refuses_without_reader_or_fallback(
        default_r2_inputs, monkeypatch, capsys):
    import json

    fixture = default_r2_inputs
    alternate = fixture.store.parent / "must_not_be_considered"
    candidate_calls, classified = [], []

    def candidates():
        candidate_calls.append("resolve")
        return [("synthetic", fixture.store), ("sentinel", alternate)]

    def classify(path):
        assert path == fixture.store, "the refused resolver fell through to another store"
        classified.append(path)
        return fixture.api._UNMOUNTED

    def no_reader(*args, **kwargs):
        pytest.fail("a resolver refusal reached a store reader")

    monkeypatch.setattr(fixture.api, "_store_candidates", candidates)
    monkeypatch.setattr(fixture.api, "_classify_store", classify)
    monkeypatch.setattr(fixture.api, "_unmounted_volume", lambda path: fixture.store)
    for name in ("chain", "oi_for_date", "_load_parquets"):
        monkeypatch.setattr(fixture.api, name, no_reader)
    assert r2.main(_r2_cli_args()) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "REFUSED" and "UNMOUNTED" in payload["reason"]
    assert candidate_calls == ["resolve"] and classified == [fixture.store]
    assert fixture.calls["reads"] == []


def test_cli_does_not_relabel_unrelated_kernel_errors(
        default_r2_inputs, monkeypatch, capsys):
    def unexpected_kernel(*args, **kwargs):
        raise RuntimeError("unexpected kernel failure")

    monkeypatch.setattr(r2, "_default_greeks_fn", lambda: unexpected_kernel)
    with pytest.raises(RuntimeError, match="unexpected kernel failure"):
        r2.main(_r2_cli_args())
    assert capsys.readouterr().out == ""
