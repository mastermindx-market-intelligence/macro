"""Observed QQQ becomes an explicit-root ETF binding through the existing owner; SPY stays SPY.

Synthetic evidence only: this leaf never contacts a provider and never mints a
root alias. Root QQQ must bind its own reference initial underlying ticker,
every OCC series key, the raw observed row root, the acquisition parameter
symbol and the exact normalized Nasdaq ETF listing under a validator-compatible
synthetic listing receipt with no future listing date; QQQ canonical evidence
effective Oct 20 cannot authorize an Oct 19 session. An omitted/unknown member
keeps its place in the observed denominator and zero OI never promotes it into
the bound scope, while the existing SPY observed path and its v2 fields stay
unchanged through the retained wrapper.
"""
from decimal import Decimal
import json

import pandas as pd
import pytest

from engine.intelligence_workspace.entity import IdentityResolutionError
from engine.intelligence_workspace.options_contract_identity import (
    _sha,
    resolve_observed_spy_contract_identity,
    validate_dated_contract_identity,
)
from engine.options_exposure_projection import exposure_input_digest
from lib import symbol_directory_receipts as R
from lib.options_source_receipts import ACQUISITION_COLUMN, THETA_ENDPOINTS, theta_acquisition
from tests.test_options_contract_identity import (
    DAY as SPY_DAY,
    captured as _captured,
    listing,
    master as spy_master,
    observed_setup,
    parquet,
)
from tests.test_options_dated_projection import dated_book

from engine.intelligence_workspace.options_contract_identity import resolve_observed_etf_contract_identity

# QQQ's actual admitted profile is prospective from Oct20; these clocks remain
# synthetic test evidence and do not alter the imported SPY fixture's globals.
DAY = "2026-10-20"
NOW = "2026-10-20T12:00:00Z"
READ = "2026-10-20T11:30:00Z"
def captured(body, at=READ):
    return _captured(body, at=at)

V2_FIELDS = frozenset(
    "schema scope root source_session effective_from effective_to known_at security_id listing_key "
    "input_sha256 contract_keys observed_contract_keys reference_observation_sha256 reference_pages "
    "security_master_sha256 listing_sha256 listing_receipt_sha256 source_evidence_representation "
    "source_evidence_basis source_input_artifacts historical_first_availability_established "
    "root_alias_created binding_sha256".split()
)
QQQ_SECURITY = ("SEC:US-XNAS-QQQ", "US-XNAS-QQQ")
EXPS = ["2026-10-23", "2026-10-30", "2026-11-06"]


def qqq_master(**changes):
    row = dict(security_id="SEC:US-XNAS-QQQ", listing_key="US-XNAS-QQQ", country="US", mic="XNAS",
               inception_code="QQQ", effective_at=pd.Timestamp("2026-10-20"),
               ingested_at=pd.Timestamp("2026-10-20T11:13:21"), security_state=None, superseded_by=None)
    row.update(changes)
    return captured(parquet(pd.DataFrame([row])))


def listing_snapshot(tmp, *, observation_date="2026-10-20", qqq_exchange="NASDAQ", qqq_etf=True):
    """Validator-compatible synthetic listing snapshot: SPY incumbent row kept, one normalized Nasdaq ETF QQQ row added.

    The operational receipt diagnostic still tracks exactly the one SPY row, so
    the receipt validates while QQQ itself is only admitted through the exact
    normalized Nasdaq ETF listing row the dated target reads.
    """
    n, o = 5000, 6500
    frame = pd.DataFrame(dict(
        date=[observation_date] * (n + o),
        symbol=[f"N{i}" for i in range(n - 1)] + ["QQQ"] + [f"O{i}" for i in range(o - 1)] + ["SPY"],
        security_name=["Synthetic"] * (n + o),
        exchange=["NASDAQ"] * (n - 1) + [qqq_exchange] + ["N"] * (o - 1) + ["P"],
        etf=[False] * (n - 1) + [qqq_etf] + [False] * (o - 1) + [True],
        test_issue=[False] * (n + o), is_preferred=[False] * (n + o),
        source=["nasdaqlisted"] * n + ["otherlisted"] * o))
    path = tmp / "snapshots" / f"{observation_date}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    sources = []
    for sid, url in ((R.NASDAQ_LISTED_SOURCE_ID, "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"),
                     (R.OTHER_LISTED_SOURCE_ID, "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt")):
        sources.append((sid, R.SourceFetch(value="synthetic", content=b"synthetic", requested_url=url,
                                           started_at=f"{observation_date}T01:00:00.000000Z",
                                           completed_at=f"{observation_date}T01:00:01.000000Z")))
    stamp = pd.Timestamp(observation_date).strftime("%m/%d/%Y")
    receipt = R.build_symbol_directory_completion_receipt(
        kind="listing_snapshot", observation_date=observation_date, artifact_path=path, source_fetches=sources,
        collector_started_at=f"{observation_date}T00:59:59.000000Z",
        collector_completed_at=f"{observation_date}T01:00:02.000000Z",
        pre_dedupe_rows=n + o, duplicate_occurrences=0, duplicate_key_count=0,
        source_row_counts=((R.NASDAQ_LISTED_SOURCE_ID, n), (R.OTHER_LISTED_SOURCE_ID, o)),
        pre_dedupe_spy_occurrences=({"source_id": R.OTHER_LISTED_SOURCE_ID, "symbol": "SPY",
                                     "security_name": "Synthetic", "exchange": "P", "etf": True,
                                     "test_issue": False, "is_preferred": False},),
        non_authoritative_footers=tuple(R.footer_diagnostic(source_id=sid, text=f"File Creation Time: {stamp} 01:00:00")
                                        for sid, _ in sources))
    body = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode() + b"\n"
    return captured(path.read_bytes()), captured(body)


@pytest.fixture(scope="module")
def qqq_listing(tmp_path_factory):
    return listing_snapshot(tmp_path_factory.mktemp("observed-qqq"))


def qqq_setup(listing):
    g, oi, ctx = dated_book()
    for frame, kind in ((g, "greeks"), (oi, "oi")):
        frame["date"] = pd.Timestamp(DAY)
        frame["root"] = "QQQ"
        params = dict(symbol="QQQ", expiration="20261023", start_date=20261020, end_date=20261020,
                      right="both", strike_range=5, format="csv")
        if kind == "greeks":
            params["version"] = "1"
        frame[ACQUISITION_COLUMN] = theta_acquisition(THETA_ENDPOINTS[kind], params, b"synthetic",
                                                      origin="http://theta-test:25503", received_at="2026-10-20T08:00:00Z")
    contracts = [dict(ticker=f"O:QQQ261023{s}00100000", underlying_ticker="QQQ",
                      contract_type="call" if s == "C" else "put", expiration_date="2026-10-23",
                      strike_price=100, exercise_style="american", shares_per_contract=100) for s in ("C", "P")]
    obs = dict(schema="options_reference_capability_observation/v1", state="response_observed",
               origin="https://api.polygon.io", path="/v3/reference/options/contracts",
               params=dict(as_of=DAY, underlying_ticker="QQQ", expiration_date="2026-10-23"),
               capability=dict(http_status=200, verdict="entitled"), contracts=contracts,
               payload_sha256="a" * 64, completed_at="2026-10-20T08:05:00Z",
               historical_first_availability_established=False)
    args = dict(source_session=DAY, input_sha256=exposure_input_digest(g, oi, DAY, "QQQ"),
                reference=captured(json.dumps(obs).encode()), security_master=qqq_master(),
                listing=listing[0], listing_receipt=listing[1], decision_at=NOW)
    return g, oi, ctx, obs, args


def qqq_observed_setup(listing, count=120):
    g, oi, ctx, _, args = qqq_setup(listing)
    g = pd.concat([g.iloc[[i % 2]] for i in range(count)], ignore_index=True)
    oi = pd.concat([oi.iloc[[i % 2]] for i in range(count)], ignore_index=True)
    for frame, kind in ((g, "greeks"), (oi, "oi")):
        frame["strike"] = [100 + i // 2 for i in range(count)]
        frame["expiration"] = [EXPS[(i // 2) % 3] for i in range(count)]
        params = dict(symbol="QQQ", expiration="*", start_date=20261020, end_date=20261020, right="both", format="csv")
        if kind == "greeks":
            params["version"] = "1"
        frame[ACQUISITION_COLUMN] = theta_acquisition(THETA_ENDPOINTS[kind], params, b"synthetic-full-book",
                                                      origin="http://theta-test:25503", received_at="2026-10-20T08:00:00Z")
    contracts = []
    for row in g.to_dict("records"):
        stamp = pd.Timestamp(row["expiration"]).strftime("%y%m%d")
        contracts.append(dict(ticker=f"O:QQQ{stamp}{row['right']}{int(row['strike'] * 1000):08d}",
                              underlying_ticker="QQQ", contract_type="call" if row["right"] == "C" else "put",
                              expiration_date=row["expiration"], strike_price=row["strike"],
                              exercise_style="american", shares_per_contract=100))
    scope = dict(underlying_ticker="QQQ", as_of=DAY, **{"expiration_date.gte": DAY},
                 expired="false", order="asc", sort="ticker", limit=1000)
    page = dict(schema="options_reference_page_observation/v1", state="response_observed",
                origin="https://api.polygon.io", path="/v3/reference/options/contracts", params=scope,
                capability=dict(http_status=200, verdict="entitled",
                                evidence=dict(response_sha256="a" * 64, response_bytes=123456,
                                              completed_at="2026-10-20T08:05:00Z")),
                payload_sha256="a" * 64, completed_at="2026-10-20T08:05:00Z", contracts=contracts, next_params=None)
    obs = dict(schema="options_reference_population_observation/v1", state="COMPLETE", root="QQQ",
               source_session=DAY, origin=page["origin"], path=page["path"], initial_params=scope,
               pages=[page], historical_first_availability_established=False)
    args.update(reference=captured(json.dumps(obs).encode()), input_sha256=exposure_input_digest(g, oi, DAY, "QQQ"))
    return g, oi, ctx, obs, args


def test_observed_qqq_binds_exact_root_tuple_and_own_coordinates(qqq_listing):
    g, oi, ctx, obs, args = qqq_observed_setup(qqq_listing)
    bound = resolve_observed_etf_contract_identity(g, oi, root="QQQ", **args).receipt
    assert set(bound) == V2_FIELDS  # existing v2 fields unchanged
    assert bound["schema"] == "options.dated_contract_identity/v2" and bound["scope"] == "observed_contracts"
    assert bound["root"] == "QQQ" and (bound["security_id"], bound["listing_key"]) == QQQ_SECURITY
    assert bound["source_session"] == DAY and bound["effective_from"] == DAY and bound["effective_to"] == "2026-10-21"
    assert bound["known_at"] == "2026-10-20T11:30:00+00:00" and bound["input_sha256"] == args["input_sha256"]
    assert not bound["root_alias_created"] and not bound["historical_first_availability_established"]
    assert len(bound["observed_contract_keys"]) == 120 and len(bound["contract_keys"]) == 120
    keys = validate_dated_contract_identity(bound, root="QQQ", source_session=DAY,
                                            input_sha256=args["input_sha256"], cutoff=NOW)
    assert len(keys) == 120 and {k[0] for k in keys} == set(EXPS) and {int(k[1]) for k in keys} == set(range(100, 160))
    with pytest.raises(IdentityResolutionError):  # the QQQ receipt never validates as another root
        validate_dated_contract_identity(bound, root="SPY", source_session=DAY,
                                         input_sha256=args["input_sha256"], cutoff=NOW)
    with pytest.raises(IdentityResolutionError):  # the SPY-only observed entry point stays SPY-only
        resolve_observed_spy_contract_identity(g, oi, **args)


def test_observed_spy_path_unchanged_through_explicit_root_entrypoint(listing):
    g, oi, ctx, obs, args = observed_setup(listing)
    wrapper = resolve_observed_spy_contract_identity(g, oi, **args).receipt
    assert set(wrapper) == V2_FIELDS
    general = resolve_observed_etf_contract_identity(g, oi, root="SPY", **args).receipt
    assert general == wrapper
    assert len(validate_dated_contract_identity(wrapper, root="SPY", source_session=SPY_DAY,
                                                input_sha256=args["input_sha256"], cutoff=args["decision_at"])) == 120


def test_observed_qqq_omitted_member_keeps_denominator_and_zero_oi_promotes_nothing(qqq_listing):
    g, oi, ctx, obs, args = qqq_observed_setup(qqq_listing)
    omitted = obs["pages"][0]["contracts"].pop()
    oi.loc[len(oi) - 1, "open_interest"] = 0  # same coordinate; zero OI is not a reference member
    args.update(reference=captured(json.dumps(obs).encode()),
                input_sha256=exposure_input_digest(g, oi, DAY, "QQQ"))
    bound = resolve_observed_etf_contract_identity(g, oi, root="QQQ", **args).receipt
    assert len(bound["observed_contract_keys"]) == 120 and len(bound["contract_keys"]) == 119
    missing = (omitted["expiration_date"], format(Decimal(str(omitted["strike_price"])).normalize(), "f"),
               "C" if omitted["contract_type"] == "call" else "P")
    assert [tuple(k) for k in bound["observed_contract_keys"]].count(missing) == 1
    assert missing not in [tuple(k) for k in bound["contract_keys"]]
    keys = validate_dated_contract_identity(bound, root="QQQ", source_session=DAY,
                                            input_sha256=args["input_sha256"], cutoff=NOW)
    assert len(keys) == 119 and missing not in keys


def test_observed_qqq_validation_refuses_aliased_or_foreign_tuples(qqq_listing):
    g, oi, ctx, obs, args = qqq_observed_setup(qqq_listing, count=24)
    bound = resolve_observed_etf_contract_identity(g, oi, root="QQQ", **args).receipt
    for field, value in (("root", "SPY"), ("security_id", "SEC:US-ARCX-SPY"), ("listing_key", "US-ARCX-SPY")):
        forged = dict(bound)
        forged[field] = value
        forged["binding_sha256"] = _sha({k: v for k, v in forged.items() if k != "binding_sha256"})
        with pytest.raises(IdentityResolutionError):
            validate_dated_contract_identity(forged, root="QQQ", source_session=DAY,
                                             input_sha256=args["input_sha256"], cutoff=NOW)


@pytest.mark.parametrize("mode", ["wrong_root", "reference_scope", "series_key", "row_root", "acquisition_symbol",
                                  "canonical_other_security", "canonical_effective_future",
                                  "canonical_ingested_after_decision", "listing_venue", "listing_etf_flag",
                                  "listing_future_date", "preknown_read"])
def test_observed_qqq_refuses_wrong_root_reference_series_canonical_or_listing(qqq_listing, tmp_path, mode):
    g, oi, ctx, obs, args = qqq_observed_setup(qqq_listing, count=24)
    if mode == "wrong_root":
        obs["root"] = "SPY"
    elif mode == "reference_scope":  # reference initial underlying ticker must be QQQ itself
        obs["initial_params"]["underlying_ticker"] = "SPY"
    elif mode == "series_key":  # OCC ticker/key must match the declared strike
        obs["pages"][0]["contracts"][0]["ticker"] = "O:QQQ261023C00101000"
    elif mode == "row_root":  # raw observed rows stay QQQ
        g.loc[0, "root"] = "SPY"
    elif mode == "acquisition_symbol":  # acquisition parameters symbol must be QQQ
        g[ACQUISITION_COLUMN] = theta_acquisition(
            THETA_ENDPOINTS["greeks"], dict(symbol="SPY", expiration="*", start_date=20261020,
                                            end_date=20261020, right="both", format="csv"),
            b"synthetic-full-book", origin="http://theta-test:25503", received_at="2026-10-20T08:00:00Z")
    elif mode == "canonical_other_security":  # SPY canonical metadata cannot carry QQQ
        args["security_master"] = spy_master()
    elif mode == "canonical_effective_future":  # future canonical evidence cannot authorize this session
        args["security_master"] = qqq_master(effective_at=pd.Timestamp("2026-10-21"))
    elif mode == "canonical_ingested_after_decision":  # actual ingestion must precede the decision
        args["security_master"] = qqq_master(ingested_at=pd.Timestamp("2026-10-20T12:01:00"))
    elif mode == "listing_venue":  # exact normalized Nasdaq listing, not another venue
        args["listing"], args["listing_receipt"] = listing_snapshot(tmp_path, qqq_exchange="P")
    elif mode == "listing_etf_flag":
        args["listing"], args["listing_receipt"] = listing_snapshot(tmp_path, qqq_etf=False)
    elif mode == "listing_future_date":  # no future listing date supports an earlier session
        args["listing"], args["listing_receipt"] = listing_snapshot(tmp_path, observation_date="2026-10-21")
    args["reference"] = captured(json.dumps(obs).encode(),
                                 at="2026-10-20T07:00:00Z" if mode == "preknown_read" else READ)
    args["input_sha256"] = exposure_input_digest(g, oi, DAY, "QQQ")
    with pytest.raises(IdentityResolutionError):
        resolve_observed_etf_contract_identity(g, oi, root="QQQ", **args)


def test_self_consistent_qqq_receipt_cannot_extend_before_native_admission(qqq_listing):
    g, oi, _, _, args = qqq_observed_setup(qqq_listing, count=24)
    bound = resolve_observed_etf_contract_identity(g, oi, root="QQQ", **args).receipt
    bound.update(source_session="2026-10-19", effective_from="2026-10-19", effective_to="2026-10-20")
    bound["binding_sha256"] = _sha({k:v for k,v in bound.items() if k!="binding_sha256"})
    with pytest.raises(IdentityResolutionError, match="predates native admission"):
        validate_dated_contract_identity(bound, root="QQQ", source_session="2026-10-19",
                                        input_sha256=args["input_sha256"], cutoff=NOW)


def test_qqq_resolver_cannot_mint_a_pre_admission_receipt_even_with_older_synthetic_evidence(tmp_path):
    old="2026-10-19"
    listing=listing_snapshot(tmp_path,observation_date=old)
    g,oi,_,obs,args=qqq_observed_setup(listing,count=24)
    for frame in (g,oi):
        frame["date"]=pd.Timestamp(old)
        rec=json.loads(frame[ACQUISITION_COLUMN].iloc[0])
        rec["parameters"].update(start_date=20261019,end_date=20261019)
        frame[ACQUISITION_COLUMN]=json.dumps(rec)
    scope=obs["initial_params"];scope.update(as_of=old,**{"expiration_date.gte":old})
    obs["source_session"]=old;obs["pages"][0]["params"]=scope
    args.update(source_session=old,input_sha256=exposure_input_digest(g,oi,old,"QQQ"),
        reference=captured(json.dumps(obs).encode()),
        security_master=qqq_master(effective_at=pd.Timestamp("2026-10-15"),ingested_at=pd.Timestamp("2026-10-15T11:13:21")))
    with pytest.raises(IdentityResolutionError,match="predates native admission"):
        resolve_observed_etf_contract_identity(g,oi,root="QQQ",**args)
