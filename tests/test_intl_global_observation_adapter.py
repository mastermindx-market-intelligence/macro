"""IM12 adapter checks: incumbent receipts keep or withhold, never upgrade."""
from __future__ import annotations

import json
from copy import deepcopy

import pandas as pd
import pytest

from engine import intl_inputs
from engine.intl_performance_records import build_return_records
from lib.intl_eod_publication import build_eod_inputs
from lib.intl_global_observation_adapter import observations_from_qualification

EVALUATED = "2026-10-09T20:30:00+00:00"
GRANT = {
    "status": "confirmed",
    "scope": "intl-index-fx-eod-user-facing-v1",
    "decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
}


def _setup(tmp_path, *, omit=None):
    # Synthetic frame + stored witnesses shaped exactly like the incumbent
    # EOD publication suite: the last completed bar is 2026-10-07 and the
    # collector receipt is 2026-10-09T15:00Z, two full days later.
    dates = pd.bdate_range(end="2026-10-07", periods=280)
    series = []
    for cc, market in intl_inputs.countries().items():
        for symbol in (market["index"], market["fx"]):
            if symbol not in series:
                series.append(symbol)
    cols = {}
    for slot, symbol in enumerate(series):
        if symbol == omit:
            continue
        value = [float(100 + slot * 4 + 0.125 * i) for i in range(len(dates))]
        cols[symbol] = pd.Series(value, index=dates)
        path = tmp_path / "intl" / (
            symbol.replace("^", "_").replace("=", "_").replace("/", "_") + ".parquet")
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"close": value}, index=dates).to_parquet(path)
    frame = pd.DataFrame(cols).sort_index()
    status = {"sources": {"intl_prices": {
        "source": "intl_prices", "status": "ok",
        "checked_at": "2026-10-09T15:00:00+00:00",
        "last_date": "2026-10-07",
    }}}
    (tmp_path / "run_status.json").write_text(json.dumps(status), encoding="utf-8")
    return frame, series


def _chain(tmp_path, *, omit=None):
    """build_eod_inputs then the exact workspace-overview owner assembly."""
    frame, series = _setup(tmp_path, omit=omit)
    result = build_eod_inputs(frame, data_root=tmp_path, evaluated_at=EVALUATED, rights=GRANT)
    assert result is not None
    selected, inputs = result
    pending = intl_inputs.source_snapshot(
        selected, source_reference="intl-supplied-close:pending",
        adjustment_bases=inputs["adjustment_bases"])
    source_reference = "intl-supplied-close:sha256:" + pending["content_sha256"]
    snapshot = intl_inputs.source_snapshot(
        selected, source_reference=source_reference,
        adjustment_bases=inputs["adjustment_bases"])
    records = build_return_records(
        selected, market_ids=list(intl_inputs.countries()),
        source_reference=source_reference)
    qualifications = {}
    for basis in ("local", "usd_unhedged"):
        qualifications[basis] = intl_inputs.qualify_return_records(
            records, snapshot=snapshot,
            source_evidence=inputs["source_evidence"],
            disclosure_decisions=inputs["disclosure_decisions"],
            policy_id=inputs["policy_id"], currency_basis=basis)
    run_status = json.loads((tmp_path / "run_status.json").read_text(encoding="utf-8"))
    return {
        "series": series, "selected": selected, "inputs": inputs,
        "records": records, "qualifications": qualifications,
        "run_status_source": run_status["sources"]["intl_prices"],
    }


def _observations(chain, basis):
    return observations_from_qualification(
        chain["records"], chain["qualifications"][basis], closes=chain["selected"],
        source_evidence=chain["inputs"]["source_evidence"],
        run_status_source=chain["run_status_source"], evaluated_at=EVALUATED,
        rights=GRANT, currency_basis=basis)


def test_incumbent_qualified_chain_qualifies_both_bases_with_exact_identities(tmp_path):
    chain = _chain(tmp_path)
    checked_at = chain["run_status_source"]["checked_at"]
    for basis, leg in (("usd_unhedged", "usd"), ("local", "local")):
        before = {
            "records": deepcopy(chain["records"]),
            "qualification": deepcopy(chain["qualifications"][basis]),
            "closes": chain["selected"].copy(),
            "source_evidence": deepcopy(chain["inputs"]["source_evidence"]),
            "run_status_source": deepcopy(chain["run_status_source"]),
            "rights": deepcopy(GRANT),
        }
        observations = _observations(chain, basis)
        assert len(observations) == 7 * 5
        assert len({obs["identity"]["market_id"] + obs["identity"]["horizon"]
                    for obs in observations}) == 7 * 5
        for observation in observations:
            incumbent = observation["incumbent"]
            assert incumbent is not None
            if incumbent["quality"] == "qualified":
                assert observation["state"] == "qualified"
                assert observation["abstain_reasons"] == []
            else:
                assert observation["state"] == "abstain"
            identity = observation["identity"]
            assert identity["currency_basis"] == basis
            assert identity["universe_id"] == identity["market_id"]
            record = next(row for row in chain["records"]["records"]
                          if row["market_id"] == identity["market_id"]
                          and row["horizon"] == identity["horizon"])
            assert observation["value"]["pct"] == pytest.approx(record[leg]["value"])
            clocks = observation["clocks"]
            assert clocks["observation"] == {
                "at": record[leg]["window"]["end"], "precision": "session_date"}
            assert clocks["source_publication"] == {
                "at": checked_at, "precision": "upper_bound"}
            assert clocks["ingestion"] == {"at": checked_at, "precision": "exact"}
            assert clocks["computation"] == {"at": EVALUATED, "precision": "exact"}
            if basis == "usd_unhedged" and observation["state"] == "qualified":
                assert observation["identity_residual"] <= 1e-9
                assert observation["decomposition"] is not None
        assert chain["records"] == before["records"]
        assert chain["qualifications"][basis] == before["qualification"]
        assert chain["selected"].equals(before["closes"])
        assert chain["inputs"]["source_evidence"] == before["source_evidence"]
        assert chain["run_status_source"] == before["run_status_source"]
        assert GRANT == before["rights"]


def test_usd_hedged_never_borrows_an_unhedged_incumbent(tmp_path):
    chain = _chain(tmp_path)
    observations = observations_from_qualification(
        chain["records"], chain["qualifications"]["usd_unhedged"],
        closes=chain["selected"], source_evidence=chain["inputs"]["source_evidence"],
        run_status_source=chain["run_status_source"], evaluated_at=EVALUATED,
        rights=GRANT, currency_basis="usd_hedged")
    assert len(observations) == 7 * 5
    for observation in observations:
        assert observation["state"] == "abstain"
        assert "basis_unsupported" in observation["abstain_reasons"]
        assert observation["value"] is None
        assert observation["decomposition"] is None
        assert observation["incumbent"] is None
    empty = observations_from_qualification(
        chain["records"], {"qualifications": []},
        closes=chain["selected"], source_evidence=chain["inputs"]["source_evidence"],
        run_status_source=chain["run_status_source"], evaluated_at=EVALUATED,
        rights=GRANT, currency_basis="usd_hedged")
    assert all("basis_unsupported" in obs["abstain_reasons"] for obs in empty)


def test_missing_fx_evidence_withholds_usd_without_poisoning_local(tmp_path):
    full = _chain(tmp_path)
    full_counts = {}
    for basis in ("local", "usd_unhedged"):
        full_counts[basis] = sum(obs["state"] == "qualified"
                                 for obs in _observations(full, basis))
    assert full_counts == {"local": 35, "usd_unhedged": 35}

    # The fx column absent from the source frame entirely.
    omitted = _chain(tmp_path, omit="USDJPY=X")
    for basis in ("local", "usd_unhedged"):
        observations = _observations(omitted, basis)
        qualified = [obs for obs in observations if obs["state"] == "qualified"]
        assert len(qualified) <= full_counts[basis]
        japan = [obs for obs in observations if obs["identity"]["market_id"] == "JP"]
        if basis == "usd_unhedged":
            assert all(obs["state"] == "abstain" for obs in japan)
            assert all("value_unavailable" in obs["abstain_reasons"]
                       or "source_evidence_missing" in obs["abstain_reasons"]
                       for obs in japan)
            assert all(obs["value"] is None for obs in japan)
        else:
            assert all(obs["state"] == "qualified" for obs in japan)

    # Dropping only the persisted fx witness must not promote any observation.
    trimmed = _chain(tmp_path)
    trimmed_evidence = [entry for entry in trimmed["inputs"]["source_evidence"]
                        if entry["series_id"] != "USDJPY=X"]
    observations = observations_from_qualification(
        trimmed["records"], trimmed["qualifications"]["usd_unhedged"],
        closes=trimmed["selected"], source_evidence=trimmed_evidence,
        run_status_source=trimmed["run_status_source"], evaluated_at=EVALUATED,
        rights=GRANT, currency_basis="usd_unhedged")
    japan = [obs for obs in observations if obs["identity"]["market_id"] == "JP"]
    assert all(obs["state"] == "abstain" for obs in japan)
    assert all("source_evidence_missing" in obs["abstain_reasons"] for obs in japan)
    assert sum(obs["state"] == "qualified" for obs in observations) < full_counts[
        "usd_unhedged"]


def test_missing_collector_receipt_clock_abstains_everywhere(tmp_path):
    chain = _chain(tmp_path)
    silent = dict(chain["run_status_source"])
    silent.pop("checked_at")
    for basis in ("local", "usd_unhedged"):
        observations = observations_from_qualification(
            chain["records"], chain["qualifications"][basis], closes=chain["selected"],
            source_evidence=chain["inputs"]["source_evidence"], run_status_source=silent,
            evaluated_at=EVALUATED, rights=GRANT, currency_basis=basis)
        assert observations
        for observation in observations:
            assert observation["state"] == "abstain"
            assert "clock_missing" in observation["abstain_reasons"]


def test_downgraded_incumbent_receipt_withholds_exactly_that_observation(tmp_path):
    chain = _chain(tmp_path)
    qualification = deepcopy(chain["qualifications"]["usd_unhedged"])
    target = next(receipt for receipt in qualification["qualifications"]
                  if receipt["binding"]["market_id"] == "JP"
                  and receipt["binding"]["horizon"] == "1m"
                  and receipt["binding"]["leg"] == "usd")
    assert target["binding"]["currency_basis"] == "usd_unhedged"
    assert target["quality"] == "qualified"
    target["quality"] = "stale"
    target["reason"] = "source_session_missed"
    observations = observations_from_qualification(
        chain["records"], qualification, closes=chain["selected"],
        source_evidence=chain["inputs"]["source_evidence"],
        run_status_source=chain["run_status_source"], evaluated_at=EVALUATED,
        rights=GRANT, currency_basis="usd_unhedged")
    assert len(observations) == 7 * 5
    japan_1m = [obs for obs in observations
                if obs["identity"]["market_id"] == "JP"
                and obs["identity"]["horizon"] == "1m"]
    assert len(japan_1m) == 1
    downgraded = japan_1m[0]
    assert downgraded["state"] == "abstain"
    assert "incumbent_qualification_withheld" in downgraded["abstain_reasons"]
    assert downgraded["value"] is None
    assert downgraded["incumbent"]["quality"] == "stale"
    assert downgraded["incumbent"]["reason"] == "source_session_missed"
    others = [obs for obs in observations if obs is not downgraded]
    assert all(obs["state"] == "qualified" for obs in others)
    assert len(others) == 7 * 5 - 1


def test_receipt_bound_to_a_foreign_fx_id_abstains_identity_mismatch(tmp_path):
    chain = _chain(tmp_path)
    qualification = deepcopy(chain["qualifications"]["usd_unhedged"])
    target = next(receipt for receipt in qualification["qualifications"]
                  if receipt["binding"]["market_id"] == "JP"
                  and receipt["binding"]["horizon"] == "1m"
                  and receipt["binding"]["leg"] == "usd")
    original_fx_id = target["binding"]["fx_id"]
    target["binding"]["fx_id"] = "EURUSD=X"
    observations = observations_from_qualification(
        chain["records"], qualification, closes=chain["selected"],
        source_evidence=chain["inputs"]["source_evidence"],
        run_status_source=chain["run_status_source"], evaluated_at=EVALUATED,
        rights=GRANT, currency_basis="usd_unhedged")
    japan_1m = [obs for obs in observations
                if obs["identity"]["market_id"] == "JP"
                and obs["identity"]["horizon"] == "1m"]
    assert len(japan_1m) == 1
    assert "identity_mismatch" in japan_1m[0]["abstain_reasons"]
    assert japan_1m[0]["state"] == "abstain"
    assert japan_1m[0]["identity"]["fx_id"] == original_fx_id
    others = [obs for obs in observations if obs is not japan_1m[0]]
    assert all("identity_mismatch" not in obs["abstain_reasons"] for obs in others)
    assert all(obs["state"] == "qualified" for obs in others)
