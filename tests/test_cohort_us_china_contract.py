"""US/China cohort delivery contract (GMI recovery §9 step 6).

These are controlled witnesses over the REAL incumbent W3C path. A POSITIVE wrapper is
only ever produced by the incumbent publish+read path, under an injected controlled
OWNER capability. No receipt is hand-forged. A tampered wrapper always starts from a
genuine one, and it is an explicit structural counterexample, never natural evidence.

The qualified-read joins reuse the incumbent owning fixtures, unchanged, from
tests/test_theme_graph_selection_cohort.py. They are loaded the same way the incumbent
publication test loads them, so the owner's qualification rules are not copied or
forked here.
"""
import ast
import copy
import importlib.util
import inspect
import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from engine.market_ontology import cohort_us_china as m
from engine.theme_graph import rights_use
from engine.theme_graph import selection_cohort_projection as _proj
from engine.theme_graph import selection_cohort_publication as _pub
from engine.theme_graph.selection_cohort import FLAGS

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts/theme_graph/cohort_us_china_delivery.v1.schema.json"
PROJECTION_SCHEMA_PATH = ROOT / "contracts/theme_graph/selection_cohort_projection.v1.schema.json"
MODULE_PATH = ROOT / "engine/market_ontology/cohort_us_china.py"
T = "2026-10-04T09:00:00.123456Z"
OLD = "2026-10-04T08:00:00Z"
GENERATIONS = {"us": "native-process-1", "cn": "native-cn-library-1"}
GRANTED = {"purpose": m.DISCLOSURE_PURPOSE, "audience": m.DISCLOSURE_AUDIENCE, "granted": True}
NOT_GRANTED = {"purpose": m.DISCLOSURE_PURPOSE, "audience": m.DISCLOSURE_AUDIENCE, "granted": False}
MAGNITUDE_KEYS = {"score", "weight", "magnitude", "rank", "size", "confidence"}
VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
PROJECTION_VALIDATOR = Draft202012Validator(json.loads(PROJECTION_SCHEMA_PATH.read_text()))


# ------------------------------------------------------------------ local fixtures
# A minimal copy of the incumbent publication-test pattern (raw / controlled authority / ancestry).

def raw(generation=GENERATIONS["us"]):
    rows = [dict(ticker="ROK", featured=True, conviction={"verdict": "owner-late"},
                 entry_signal={"label": "blocked"}, risk_sizing={"units": None}),
            dict(ticker="OTHER", featured=False),
            dict(ticker="LRCX", featured=True, issuer_id="same-issuer",
                 conviction={"verdict": "owner-second"})]
    return json.dumps(dict(buy=rows, as_of="2026-10-03", emit={"pair_id": generation, "at_utc": OLD},
                           w3c_source={"schema": "mastermind.selection_cohort_library_source.v1",
                                       "generation_id": generation, "availability": "VALID",
                                       "available_at": OLD}),
                      separators=(",", ":"), allow_nan=False).encode()


def controlled_authority(request):
    # An injected controlled OWNER capability; never an actual rights assertion.
    assert request["purpose"] == "selection_cohort_internal_capture"
    assert request["source_sha256"] and request["generation_id"]
    assert request["phase"] in {"capture_write", "pre_read", "read_use"}
    if request["phase"] != "pre_read":
        assert request["ancestry"]
    return True


def ancestry():
    return dict(owner="fixture-owner", source_family="fixture-controlled-house", source_ref="fixture://owner",
                sha256="a" * 64, generation_id="fixture-owner-native-gen", available_at=OLD)


def cn_documents():
    handoff = _pub.source_handoff(generation_id=GENERATIONS["cn"], availability="VALID", available_at=OLD)
    library = dict(buy=[dict(ticker="000001.SZ", conviction={"verdict": "library"}), dict(ticker="000002.SZ")],
                   as_of="2026-10-03", w3c_source=handoff)
    served = copy.deepcopy(library)
    served["buy"][0]["conviction"] = {"verdict": "served-per-stock"}
    served["buy"][0]["board_since"] = "2026-10-03"
    return json.dumps(library).encode(), json.dumps(served).encode()


def cn_ancestry(served):
    row = json.loads(served)["buy"][0]
    return [{**ancestry(), "row_index": 0,
             "reason_projection_sha256": _pub.content_sha256({k: row.get(k) for k in _pub.REASONS})}]


@pytest.fixture(scope="module")
def owner():
    spec = importlib.util.spec_from_file_location(
        "w3c_incumbent_fixture_owner", ROOT / "tests/test_theme_graph_selection_cohort.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def joins(owner):
    receipt, member = owner.receipt, owner.member

    def qualified_reads(selection):
        ids, members = {}, {}
        for i, row in enumerate(selection["rows"]):
            sid = row["selection_id"]
            base = receipt()
            base.update(effective_at=T, known_at=T, available_at=OLD)
            binding = dict(selection_id=sid,
                           original_identity_sha256=_pub.content_sha256(row["original_identity"]),
                           selection_sha256=_pub.content_sha256(selection))
            ids[sid] = dict(**base, **binding, security_id=f"SEC:controlled:{i}",
                            graph_node_ids=[f"co:fixture:{i}"], historical_identity_claim=True)
            memberships = [member(i)] if i == 0 else []
            members[sid] = dict(**base, **binding, security_id=ids[sid]["security_id"], complete=True,
                                memberships=memberships, identity_receipt_ref=ids[sid]["receipt_ref"],
                                identity_receipt_sha256=ids[sid]["receipt_sha256"])
        return dict(identity_reads=ids, membership_reads=members, state_reads={})
    return qualified_reads


def publish(market, data_dir):
    """Finalize one generation through the incumbent owner seam; return (raw bytes, generation)."""
    if market == "us":
        data = raw()
        result = _pub.publish_us_source(data, data_dir=data_dir, finalized_at=T,
                                        authorize_capture=controlled_authority)
    else:
        library, data = cn_documents()
        result = _pub.publish_cn_source(data, library_bytes=library, data_dir=data_dir, finalized_at=T,
                                        reason_ancestry=cn_ancestry(data), authorize_capture=controlled_authority)
    assert result["status"] == "AVAILABLE", result["reason_codes"]
    return data, GENERATIONS[market]


def incumbent_wrapper(market, data, data_dir, **kwargs):
    return _pub.read_finalized_cohort(data, market=m.MARKETS[market]["incumbent_market"],
                                      generation_id=GENERATIONS[market], data_dir=data_dir, **kwargs)


def deliver(market, data, data_dir, **kwargs):
    return checked(m.read_cohort_delivery(market, data, generation_id=GENERATIONS[market],
                                          data_dir=data_dir, **kwargs))


def checked(doc):
    """Every produced document is schema-valid and carries the standing invariants."""
    VALIDATOR.validate(doc)
    if doc["projection"] is not None:
        PROJECTION_VALIDATOR.validate(doc["projection"])
    assert doc["public_display_allowed"] is False
    assert all(doc[flag] is False for flag in FLAGS)
    assert doc["viewer_disclosure_grant"]["confers_enrollment"] is False
    assert doc["prophet_board_graph_source_enrollment"]["derived_from_disclosure_grant"] is False
    if doc["delivery"] != "POSITIVE":
        assert doc["n_selected"] == 0 and doc["reason_codes"]
        assert doc["capture"]["authorized"] is False and doc["capture"]["receipt_sha256"] is None
        assert doc["prophet_board_graph_source_enrollment"]["state"] == "NOT_ENROLLED"
    if doc["delivery"] == "REFUSED":
        assert doc["projection"] is None
    return doc


@pytest.fixture
def positive(tmp_path, joins):
    """A genuine POSITIVE incumbent wrapper per market, plus the read inputs."""
    def make(market):
        data_dir = tmp_path / market
        data_dir.mkdir()
        data, _ = publish(market, data_dir)
        kwargs = dict(authorize_capture=controlled_authority, qualified_reads=joins)
        wrapper = incumbent_wrapper(market, data, data_dir, **kwargs)
        assert wrapper["status"] == "AVAILABLE" and wrapper["explanation"] is not None
        return data, data_dir, kwargs, wrapper
    return make


def classify(market, wrapper, **kwargs):
    return checked(m.classify_cohort_wrapper(market, wrapper, **kwargs))


def record_incumbent_reads(monkeypatch):
    calls = []
    monkeypatch.setattr(_pub, "read_finalized_cohort", lambda *a, **k: calls.append((a, k)))
    return calls


# ------------------------------------------------------------------ 1 identity

def test_markets_purpose_and_schema_are_the_incumbent_ones():
    assert {s["incumbent_market"]: s["cohort_scope"] for s in m.MARKETS.values()} == _pub.MARKETS
    assert m.CAPTURE_PURPOSE == rights_use.PURPOSE == "selection_cohort_internal_capture"
    assert m.DISCLOSURE_PURPOSE != m.CAPTURE_PURPOSE
    schema = json.loads(SCHEMA_PATH.read_text())
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == m.SCHEMA and schema["additionalProperties"] is False
    assert set(m.DELIVERIES) == set(schema["properties"]["delivery"]["enum"])
    keys = set(m.classify_cohort_wrapper("us", None))
    assert keys == set(schema["required"]) == set(schema["properties"])


# ------------------------------------------------------------------ 2/3 positive

@pytest.mark.parametrize("market", ["us", "cn"])
def test_authorized_capture_through_the_incumbent_path_is_positive(positive, market):
    data, data_dir, kwargs, wrapper = positive(market)
    doc = deliver(market, data, data_dir, **kwargs)
    spec = m.MARKETS[market]
    assert doc["delivery"] == "POSITIVE" and doc["reason_codes"] == []
    assert doc["market"] == market and doc["incumbent_market"] == spec["incumbent_market"]
    assert wrapper["receipt"]["market"] == spec["incumbent_market"]
    assert wrapper["receipt"]["reason_projection"] == spec["reason_projection"]
    assert wrapper["receipt"]["source_selection"]["cohort_scope"] == spec["cohort_scope"]
    assert wrapper["receipt"]["ancestry"][0]["owner"] == {"us": "build_stock_library",
                                                         "cn": "build_china_library"}[market]
    assert re.fullmatch(r"[0-9a-f]{64}", doc["capture"]["receipt_sha256"])
    assert doc["capture"] == dict(purpose=m.CAPTURE_PURPOSE, authorized=True,
                                  receipt_sha256=wrapper["receipt"]["receipt_sha256"],
                                  generation_id=GENERATIONS[market])
    assert doc["prophet_board_graph_source_enrollment"] == dict(
        state="ENROLLED_FOR_THIS_READ", basis=m.ENROLLMENT_BASIS, derived_from_disclosure_grant=False)
    assert doc["projection"] == _proj.project_selection_cohort_for_product(wrapper)
    assert doc["n_selected"] == doc["projection"]["n_selected"] == 2
    assert doc["viewer_disclosure_grant"]["state"] == "NOT_EVALUATED"


# ------------------------------------------------------------------ 4/5 degraded

@pytest.mark.parametrize("market", ["us", "cn"])
def test_natural_binding_none_is_an_honest_degraded_refusal(tmp_path, market):
    data, _ = publish(market, tmp_path)
    direct = incumbent_wrapper(market, data, tmp_path, authorize_capture=None)
    doc = deliver(market, data, tmp_path, authorize_capture=None)
    assert doc["delivery"] == "DEGRADED_REFUSAL" != "REFUSED"
    assert doc["reason_codes"] == direct["reason_codes"] == ["CAPTURE_RIGHTS_UNAVAILABLE"]
    assert doc["projection"] == _proj.project_selection_cohort_for_product(direct)
    assert doc["projection"]["availability"]["status"] == "UNAVAILABLE"
    assert doc["projection"]["unavailable_reason"] == "SOURCE_UNAVAILABLE:CAPTURE_RIGHTS_UNAVAILABLE"
    assert doc["n_selected"] == 0
    assert doc["prophet_board_graph_source_enrollment"]["state"] == "NOT_ENROLLED"


def test_refusing_capabilities_degrade_and_a_real_unenrolled_registry_refuses(tmp_path):
    """Both a refusing lambda and a REAL rights_use.CaptureCapability pointed at an
    absent registry file (verdict REFUSED REGISTRY_MISSING) degrade honestly."""
    data, _ = publish("us", tmp_path)
    capability = rights_use.CaptureCapability(path=tmp_path / "absent_rights_registry.yml")
    for authority in (lambda request: False, capability):
        direct = incumbent_wrapper("us", data, tmp_path, authorize_capture=authority)
        doc = deliver("us", data, tmp_path, authorize_capture=authority)
        assert doc["delivery"] == "DEGRADED_REFUSAL"
        assert doc["reason_codes"] == direct["reason_codes"] == ["CAPTURE_RIGHTS_UNAVAILABLE"]
    assert capability.last_verdict["verdict"] == "REFUSED"


def test_authorized_capture_without_qualified_reads_is_degraded_not_positive(tmp_path):
    data, _ = publish("us", tmp_path)
    doc = deliver("us", data, tmp_path, authorize_capture=controlled_authority)
    assert doc["delivery"] == "DEGRADED_REFUSAL"
    assert doc["reason_codes"] == ["EXPLANATION_UNAVAILABLE"]
    assert doc["projection"]["unavailable_reason"] == "EXPLANATION_UNAVAILABLE"


def test_missing_generation_and_incumbent_runtime_fault_degrade(tmp_path, monkeypatch):
    doc = deliver("us", raw(), tmp_path, authorize_capture=controlled_authority)
    assert doc["delivery"] == "DEGRADED_REFUSAL"
    assert classify("us", None)["reason_codes"] == ["WRAPPER_MISSING"]

    def outage(*args, **kwargs):
        raise OSError("controlled incumbent runtime outage")
    monkeypatch.setattr(_pub, "read_finalized_cohort", outage)
    doc = deliver("us", raw(), tmp_path, authorize_capture=controlled_authority)
    assert doc["delivery"] == "DEGRADED_REFUSAL"
    assert doc["reason_codes"] == ["SOURCE_RUNTIME_UNAVAILABLE"] and doc["projection"] is None


# ------------------------------------------------------------------ 6 unauthorized capture

def _tamper(case, wrapper):
    w = copy.deepcopy(wrapper)
    if case == "receipt_removed":
        w.pop("receipt")
    elif case == "capture_use_changed":
        w["receipt"]["capture_use"] = m.DISCLOSURE_PURPOSE
    elif case == "public_display_allowed":
        w["receipt"]["public_display_allowed"] = True
    elif case == "receipt_sha_altered":
        w["receipt"]["receipt_sha256"] = "0" * 64
    elif case == "available_with_reason_codes":
        w["reason_codes"] = ["CAPTURE_RIGHTS_UNAVAILABLE"]
    elif case == "unavailable_with_receipt":
        w["status"] = "UNAVAILABLE"
        w["reason_codes"] = ["CAPTURE_RIGHTS_UNAVAILABLE"]
        w["explanation"] = None
    elif case == "explanation_spliced":
        w["explanation"]["source_selection"]["n_selected"] += 1
    elif case == "selection_n_altered":
        w["receipt"]["source_selection"]["n_selected"] += 1
    elif case == "wrong_wrapper_schema":
        w["schema"] = "fixture.other_owner/v1"
    return w


@pytest.mark.parametrize("case", ["receipt_removed", "capture_use_changed", "public_display_allowed",
                                  "receipt_sha_altered", "available_with_reason_codes",
                                  "unavailable_with_receipt", "explanation_spliced",
                                  "selection_n_altered", "wrong_wrapper_schema"])
@pytest.mark.parametrize("market", ["us", "cn"])
def test_unauthorized_capture_is_refused_never_degraded(positive, market, case):
    _, _, _, wrapper = positive(market)
    assert classify(market, wrapper)["delivery"] == "POSITIVE"
    doc = classify(market, _tamper(case, wrapper))
    assert doc["delivery"] == "REFUSED" and doc["delivery"] != "DEGRADED_REFUSAL"
    assert len(doc["reason_codes"]) == 1 and doc["reason_codes"][0].startswith("UNAUTHORIZED_CAPTURE:")
    assert doc["projection"] is None and doc["n_selected"] == 0


# ------------------------------------------------------------------ 7 / 12 never reach the incumbent

class _CallableDict(dict):
    def __call__(self, request):
        return True


class _CallableStr(str):
    def __call__(self, request):
        return True


@pytest.mark.parametrize("authority", ["ALLOWED", b"ALLOWED", True, 200, {"verdict": "ALLOWED"},
                                       _CallableDict(verdict="ALLOWED"), _CallableStr("ALLOWED")])
def test_a_non_capability_authority_is_refused_before_the_incumbent(tmp_path, monkeypatch, authority):
    calls = record_incumbent_reads(monkeypatch)
    doc = deliver("us", raw(), tmp_path, authorize_capture=authority)
    assert doc["delivery"] == "REFUSED"
    assert doc["reason_codes"] == ["CAPTURE_AUTHORITY_NOT_A_CAPABILITY"]
    assert calls == []


def test_unsupported_market_is_refused_and_never_read(tmp_path, monkeypatch, positive):
    _, _, _, wrapper = positive("us")
    calls = record_incumbent_reads(monkeypatch)
    for market in ("hk", "us_today", "", None, 7):
        doc = checked(m.read_cohort_delivery(market, raw(), generation_id="x", data_dir=tmp_path,
                                             authorize_capture=controlled_authority))
        assert doc["delivery"] == "REFUSED" and doc["reason_codes"] == ["UNSUPPORTED_MARKET"]
        assert doc["incumbent_market"] is None and doc["cohort_scope"] is None
        assert classify(market, wrapper)["reason_codes"] == ["UNSUPPORTED_MARKET"]
    assert calls == []


# ------------------------------------------------------------------ 8 grant != enrollment

def test_a_granted_disclosure_never_enrolls_a_degraded_read(tmp_path):
    data, _ = publish("us", tmp_path)
    doc = deliver("us", data, tmp_path, authorize_capture=None, viewer_disclosure_grant=GRANTED)
    assert doc["delivery"] == "DEGRADED_REFUSAL"
    assert doc["viewer_disclosure_grant"]["state"] == "GRANTED"
    assert doc["prophet_board_graph_source_enrollment"]["state"] == "NOT_ENROLLED"
    assert doc["capture"]["authorized"] is False


def test_a_grant_shaped_authorizer_does_not_satisfy_the_capture_purpose(tmp_path, joins):
    data, _ = publish("us", tmp_path)
    seen = []

    def grant_shaped(request):
        seen.append(request.get("purpose"))
        return request.get("purpose") == m.DISCLOSURE_PURPOSE
    doc = deliver("us", data, tmp_path, authorize_capture=grant_shaped, qualified_reads=joins,
                  viewer_disclosure_grant=GRANTED)
    assert doc["delivery"] == "DEGRADED_REFUSAL"
    assert doc["reason_codes"] == ["CAPTURE_RIGHTS_UNAVAILABLE"]
    assert seen and set(seen) == {m.CAPTURE_PURPOSE}


def test_the_grant_is_recorded_only_and_never_changes_the_delivery(positive):
    data, data_dir, kwargs, _ = positive("us")
    grants = (None, GRANTED, NOT_GRANTED,
              {"purpose": m.CAPTURE_PURPOSE, "audience": m.DISCLOSURE_AUDIENCE, "granted": True})
    docs = [deliver("us", data, data_dir, viewer_disclosure_grant=g, **kwargs) for g in grants]
    states = [(d["viewer_disclosure_grant"]["state"], d["viewer_disclosure_grant"]["reason"]) for d in docs]
    assert states == [("NOT_EVALUATED", None), ("GRANTED", None), ("NOT_GRANTED", "NOT_GRANTED"),
                      ("NOT_GRANTED", "PURPOSE_MISMATCH")]
    stripped = [{k: v for k, v in d.items() if k != "viewer_disclosure_grant"} for d in docs]
    assert all(s == stripped[0] for s in stripped)
    assert stripped[0]["delivery"] == "POSITIVE"
    assert all(d["prophet_board_graph_source_enrollment"]["state"] == "ENROLLED_FOR_THIS_READ" for d in docs)


@pytest.mark.parametrize("grant, reason", [
    ([GRANTED], "MALFORMED"),
    ({"purpose": m.DISCLOSURE_PURPOSE, "audience": m.DISCLOSURE_AUDIENCE, "granted": "yes"}, "MALFORMED"),
    ({"purpose": m.DISCLOSURE_PURPOSE, "audience": "public", "granted": True}, "AUDIENCE_MISMATCH"),
])
def test_malformed_or_mismatched_grants_are_not_granted(grant, reason):
    doc = classify("us", None, viewer_disclosure_grant=grant)
    assert doc["viewer_disclosure_grant"]["state"] == "NOT_GRANTED"
    assert doc["viewer_disclosure_grant"]["reason"] == reason


def test_the_decision_function_never_receives_the_grant():
    assert list(inspect.signature(m._decide).parameters) == ["market", "wrapper", "rights_path"]


# ------------------------------------------------------------------ 9/10/11/13 unlawful sources

@pytest.mark.parametrize("market", ["us", "cn"])
def test_ths_basket_laundering_is_refused_in_available_and_unavailable_wrappers(tmp_path, positive, market):
    _, _, _, wrapper = positive(market)
    laundered = copy.deepcopy(wrapper)
    concepts = laundered["explanation"]["concepts"]
    if concepts:
        concepts[0]["node_id"] = "basket:baskets_china_ths:fixture"
    else:
        concepts.append({"node_id": "basket:baskets_china_ths:fixture"})
    assert classify(market, laundered)["reason_codes"] == ["LAUNDERING_REFUSED"]

    data, _ = publish(market, tmp_path / "unavailable")
    unavailable = incumbent_wrapper(market, data, tmp_path / "unavailable", authorize_capture=None)
    unavailable["reason_codes"] = list(unavailable["reason_codes"]) + ["basket:baskets_china_ths:fixture"]
    doc = classify(market, unavailable)
    assert doc["delivery"] == "REFUSED" and doc["reason_codes"] == ["LAUNDERING_REFUSED"]


@pytest.mark.parametrize("where", ["ancestry", "source_origin_ref"])
@pytest.mark.parametrize("market", ["us", "cn"])
def test_an_hkex_source_is_prohibited(positive, market, where):
    _, _, _, wrapper = positive(market)
    scraped = copy.deepcopy(wrapper)
    if where == "ancestry":
        assert scraped["receipt"]["ancestry"]
        scraped["receipt"]["ancestry"][0]["source_ref"] = "https://www1.hkexnews.hk/fixture"
    else:
        scraped["receipt"]["source_origin_ref"] = "https://www1.hkexnews.hk/fixture"
    doc = classify(market, scraped)
    assert doc["delivery"] == "REFUSED" and doc["reason_codes"] == ["PROHIBITED_SOURCE"]


def test_a_receipt_read_as_the_other_market_is_mixed_market(positive):
    for market, other in (("us", "cn"), ("cn", "us")):
        _, _, _, wrapper = positive(market)
        doc = classify(other, wrapper)
        assert doc["delivery"] == "REFUSED" and doc["reason_codes"] == ["MIXED_MARKET_REFUSED"]


@pytest.mark.parametrize("container", ["wrapper", "receipt", "explanation"])
@pytest.mark.parametrize("flag", FLAGS)
def test_any_escalated_authority_flag_is_refused(positive, flag, container):
    _, _, _, wrapper = positive("us")
    escalated = copy.deepcopy(wrapper)
    target = escalated if container == "wrapper" else escalated[container]
    assert target[flag] is False
    target[flag] = True
    doc = classify("us", escalated)
    assert doc["delivery"] == "REFUSED" and doc["reason_codes"] == ["AUTHORITY_ESCALATION_REFUSED"]


# ------------------------------------------------------------------ 14 no magnitude

def _keys(value):
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            yield from current.keys()
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


@pytest.mark.parametrize("market", ["us", "cn"])
def test_no_delivery_document_carries_a_magnitude(tmp_path, positive, market):
    data, data_dir, kwargs, wrapper = positive(market)
    docs = [deliver(market, data, data_dir, **kwargs),
            deliver(market, data, data_dir, authorize_capture=None, viewer_disclosure_grant=GRANTED),
            classify(market, _tamper("receipt_sha_altered", wrapper)),
            classify(market, None), classify("hk", wrapper)]
    assert [d["delivery"] for d in docs] == ["POSITIVE", "DEGRADED_REFUSAL", "REFUSED",
                                             "DEGRADED_REFUSAL", "REFUSED"]
    for doc in docs:
        assert not MAGNITUDE_KEYS & set(_keys(doc)), doc["delivery"]


# ------------------------------------------------------------------ 15 import boundary

def test_the_module_is_a_pure_reader_over_the_four_incumbent_imports():
    tree = ast.parse(MODULE_PATH.read_text())
    engine_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("engine"):
            engine_imports |= {f"{node.module}.{alias.name}" for alias in node.names}
        elif isinstance(node, ast.Import):
            assert not any(alias.name.startswith("engine") for alias in node.names)
    assert engine_imports == {"engine.theme_graph.selection_cohort_publication",
                              "engine.theme_graph.selection_cohort_projection",
                              "engine.theme_graph.selection_cohort.FLAGS",
                              "engine.theme_graph.rights_use.PURPOSE"}
    forbidden = {"write_product_projection", "publish_finalized_cohort", "publish_us_source",
                 "publish_cn_source", "write_text", "write_bytes", "open", "mkdir", "unlink"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
            assert name not in forbidden, name


# ------------------------------------------------------------------ 16 never raises

class _Hostile(dict):
    def get(self, *args, **kwargs):
        raise RuntimeError("controlled hostile mapping")


@pytest.mark.parametrize("market", ["us", "cn", None, 7])
@pytest.mark.parametrize("wrapper", [None, [], "x", {"status": object()}, {"schema": _pub.SCHEMA},
                                     {"schema": _pub.SCHEMA, "status": "AVAILABLE", "reason_codes": [],
                                      "receipt": "not-a-receipt"}])
def test_garbage_never_raises_and_is_schema_valid(market, wrapper):
    doc = classify(market, wrapper, viewer_disclosure_grant=object())
    assert doc["delivery"] in ("DEGRADED_REFUSAL", "REFUSED")


def test_a_classifier_fault_fails_closed():
    doc = classify("us", _Hostile(schema=_pub.SCHEMA), viewer_disclosure_grant=GRANTED)
    assert doc["delivery"] == "REFUSED" and doc["reason_codes"] == ["CLASSIFICATION_FAULT"]
    assert doc["viewer_disclosure_grant"]["state"] == "GRANTED"
