"""Financial snapshots: qualified source identity, private data and replay authority."""
from __future__ import annotations
import copy
import json
import pytest
from engine.neuralweb import brain_financial_views as fv, brain_financial_reader as fr
from engine.neuralweb import brain_gateway as gw


def fund(symbol="AAPL"):
    periods = [f"Q{q} {year}" for year in (2024, 2025) for q in range(1, 5)]
    income = {key: [None] * 8 for key in fv._BLOCKS["income"]}
    income.update(revenue=[10, 30, 60, 100, 15, 45, 90, 150],
                  net_income=[1, 3, 6, 10, 2, 4, 8, 12])
    return {"schema": "mastermind.fund/v1", "ticker": symbol, "asof": "2026-10-21",
            "stmt_currency": "USD", "quote_currency": "USD", "src": {"statements": "fixture"},
            "profile": {"sector": "Technology"}, "statements": {
                "annual": None,
                "quarterly": {"periods": periods, "income": income, "balance": {}, "cashflow": {}}}}


def wire(symbol="AAPL", **view):
    return fv.compile_financial_widget(
        {"template": "financial_statement", "symbol": symbol, "view": view},
        {"reader": "read_financial_statements", "result": {"fund": fund(symbol)}, "call_id": "read-1"},
        "turn:read-1",
    )


def price(**changes):
    result = {"symbol": "AAPL", "price": 123.45, "prev_close": 120,
              "change_pct": 2.875, "as_of": "2026-10-21", "source": "fixture"}
    result.update(changes)
    return fv.compile_financial_widget({"template": "price", "symbol": "AAPL"},
        {"reader": "get_quote", "result": result, "call_id": "quote-1"}, "turn:quote-1")


def test_statement_preserves_full_bases_before_display_slicing():
    w = wire("600519.SS", basis="interim", period_count=2)
    assert fv.validate_financial_view(w)
    f = w["visual"]["data"]["fund"]
    assert f["statements"]["annual"] is None
    assert len(f["statements"]["quarterly"]["periods"]) == 8
    assert f["statements"]["quarterly"]["income"]["revenue"] == [10, 30, 60, 100, 15, 45, 90, 150]
    receipt = fv.model_visible_financial_result(w)
    assert receipt["periods_available"] == {"annual": 0, "quarterly": 8}
    assert "data" not in receipt and "income" not in json.dumps(receipt)
    assert len(json.dumps(receipt)) < 1000


@pytest.mark.parametrize("bad", [None, "", True, False, float("nan"), float("inf"), "123"])
def test_price_rejects_missing_and_coerced_numbers(bad):
    assert price(price=bad).get("error") == "financial_widget_unavailable"


def test_price_can_be_truthful_quote_only_and_never_exports_synthetic_wicks():
    w = price()
    assert fv.validate_financial_view(w)
    assert w["visual"]["source"]["status"] == "partial"
    result = {"quote": {"symbol":"AAPL","price":123,"source":"fixture"},
              "bars":[{"date":"2026-10-20","close":121,"open":100,"high":150,"low":90}],
              "symbol":"AAPL"}
    w = fv.compile_financial_widget({"template":"price","symbol":"AAPL"},
        {"reader":"get_quote","result":result,"call_id":"quote"},"quote")
    assert w["visual"]["data"]["bars"] == [{"date":"2026-10-20","close":121}]
    assert fv.validate_financial_view(w)


@pytest.mark.parametrize("mutation", [
    lambda w: w["visual"]["data"]["fund"]["statements"]["quarterly"]["income"]["revenue"].__setitem__(0, 999),
    lambda w: w["visual"].__setitem__("normalizer_version", "latest"),
    lambda w: w["visual"]["source"].__setitem__("entity_id", "MSFT"),
    lambda w: w["visual"].__setitem__("html", "<script>alert(1)</script>"),
    lambda w: w["visual"]["view"].__setitem__("width", 999),
])
def test_tampered_history_fails_closed(mutation):
    w = wire()
    mutation(w)
    assert not fv.validate_financial_view(w)
    assert fv.public_financial_visuals({"visuals":[w]}) == []


def test_snapshot_stays_identical_when_source_changes():
    source = fund()
    w = fv.compile_financial_widget({"template":"financial_statement","symbol":"AAPL"},
        {"reader":"read_financial_statements","result":{"fund":source},"call_id":"read"},"turn")
    before = json.dumps(w, sort_keys=True)
    source["statements"]["quarterly"]["income"]["revenue"][0] = 999
    assert json.dumps(w, sort_keys=True) == before
    assert fv.public_financial_visuals({"visuals":[w]}) == [w]


@pytest.mark.parametrize("params", [
    {"template":"price","symbol":"AAPL","view":{"statement":"income"}},
    {"template":"company","symbol":"AAPL","view":{"range":"1Y"}},
    {"template":"financial_statement","symbol":"AAPL","view":{"period_count":True}},
    {"template":"financial_statement","symbol":"AAPL","view":{"period_count":9}},
    {"template":"financial_statement","symbol":"AAPL","url":"https://evil.example"},
    {"template":"price","source_ref":"fin_untrusted"},
])
def test_closed_request_schema(params):
    with pytest.raises((ValueError, TypeError)):
        fv.normalize_request(params)


def test_source_reader_and_symbol_must_match_template():
    assert fv.compile_financial_widget({"template":"financial_statement","symbol":"MSFT"},
        {"reader":"read_financial_statements","result":{"fund":fund()},"call_id":"x"},"x").get("error")
    assert fv.compile_financial_widget({"template":"financial_statement","symbol":"AAPL"},
        {"reader":"get_earnings","result":{"fund":fund()},"call_id":"x"},"x").get("error")


def test_bulk_and_source_text_limits_fail_without_partial_normalization():
    oversized = fund()
    oversized["statements"]["quarterly"]["periods"] = ["x"] * 161
    assert fv.compile_financial_widget({"template":"financial_statement","symbol":"AAPL"},
        {"reader":"read_financial_statements","result":{"fund":oversized},"call_id":"x"},"x").get("error")
    assert fv.compile_financial_widget({"template":"financial_statement","symbol":"AAPL"},
        {"reader":"read_financial_statements","result":{"fund":fund()},"call_id":"x"},"x",
        screen=lambda _: False).get("error")


def test_admitted_wrapper_cannot_grant_withheld_data(tmp_path):
    calls = []
    result = fr.prepare_widget_read({"template":"financial_statement","symbol":"AAPL"},
        lambda name,args: calls.append((name,args)), {"render_financial_widget"}, tmp_path)
    assert result["error"] == "financial_source_not_admitted" and calls == []
    result = fr.prepare_widget_read({"template":"company","symbol":"AAPL"},
        lambda name,args: calls.append((name,args)), {"get_fundamentals"}, tmp_path)
    assert result["error"] == "financial_view_not_admitted" and calls == []


def test_one_authorized_read_and_no_second_model_roundtrip(tmp_path):
    calls=[]
    def dispatch(name,args):
        calls.append((name,args))
        return {"available":True,"fund":fund()}
    result=fr.prepare_widget_read({"template":"financial_statement","symbol":"AAPL"},
        dispatch,{"render_financial_widget","get_fundamentals"},tmp_path)
    assert calls == [("read_financial_statements",{"symbol":"AAPL"})]
    retained, charts={},[]
    receipt=gw._prepare_financial_widget(result,{},retained,"tool-1",charts,"",tmp_path,
        {"render_financial_widget","get_fundamentals"})
    assert receipt["ok"] and len(charts)==1
    assert "financial_observation" not in receipt and "statements" not in receipt
    assert retained[receipt["source_ref"]] == charts[0]


def test_references_reuse_completed_same_turn_snapshot_and_recheck_admission(tmp_path):
    original=wire()
    ref=fv.model_visible_financial_result(original)["source_ref"]
    args={"financial_request":{"template":"financial_statement","source_ref":ref,"view":{"basis":"interim"}}}
    charts,retained=[],{}
    bad=gw._prepare_financial_widget(args,{},retained,"r2",charts,"",tmp_path,{"get_fundamentals"})
    assert bad["error"]=="financial_source_ref_unavailable" and not charts
    denied=gw._prepare_financial_widget(args,{ref:original},retained,"r2",charts,"",tmp_path,set())
    assert denied["error"]=="financial_source_not_admitted" and not charts
    good=gw._prepare_financial_widget(args,{ref:original},retained,"r2",charts,"",tmp_path,{"get_fundamentals"})
    assert good["ok"]
    assert charts[0]["visual"]["data"]==original["visual"]["data"]
    assert charts[0]["visual"]["view"]["basis"]=="interim"
    assert original["visual"]["view"]["basis"]=="annual"


def test_quote_denial_falls_back_only_to_separately_admitted_labelled_summary(tmp_path):
    calls=[]
    def dispatch(name,args):
        calls.append(name)
        if name=="read_earnings_evidence":return {"available":False,"error":"insider_required"}
        return {"symbol":"AAPL","latest_earnings_call":{"summary":"Revenue increased.","fiscal_period":"Q1 2026"}}
    result=fr.prepare_widget_read({"template":"transcript","symbol":"AAPL"},dispatch,
        {"render_financial_widget","read_earnings_evidence","get_earnings"},tmp_path)
    assert calls==["read_earnings_evidence","get_earnings"]
    w=fv.compile_financial_widget(result["financial_request"],
        {**result["financial_observation"],"call_id":"t1"},"t1")
    assert w["visual"]["data"]["kind"]=="summary"
    assert w["visual"]["data"]["facts"]==[] and fv.validate_financial_view(w)


def test_statement_local_read_validates_identity_and_keeps_public_fixed_origin(tmp_path):
    (tmp_path/"AAPL.fund.json").write_text(json.dumps(fund()))
    assert fr.read_statement_snapshot({"symbol":"AAPL"},tmp_path)["available"]
    (tmp_path/"AAPL.fund.json").write_text(json.dumps(fund("MSFT")))
    assert not fr.read_statement_snapshot({"symbol":"AAPL"},tmp_path)["available"]
    assert fr._PUBLIC_FUND_BASE=="https://app.mastermind-x.com/data/"


@pytest.mark.parametrize("streaming",[False,True])
def test_financial_widget_reaches_real_loop_without_bulk_model_context(tmp_path,monkeypatch,streaming):
    from tests.test_brain_gateway import _MockClient,_MockResponse,_MockBlock,_sse
    monkeypatch.setattr(gw,"_grounding_digest",lambda *a,**k:"")
    monkeypatch.setattr(gw,"_symbol_grounding_digest",lambda *a,**k:"")
    monkeypatch.setattr("lib.ai_costs._write_ledger_path",lambda root=None:tmp_path/"usage.jsonl")
    (tmp_path/"AAPL.fund.json").write_text(json.dumps(fund()))
    client=_MockClient([
        _MockResponse([_MockBlock("tool_use",name="render_financial_widget",
            input_={"template":"financial_statement","symbol":"AAPL"},id_="financial-1")],"tool_use"),
        _MockResponse([_MockBlock("text","The statement is shown with local controls.")]),
    ])
    args=("Show AAPL financial statements","fast",[],{},tmp_path,tmp_path,"",client,"test-model",1000,3)
    if streaming:
        events=_sse(list(gw._run_brain_loop_stream(*args,meta_event={"type":"meta"})))
        charts=[e for e in events if e.get("visual")]
    else: charts=gw._run_brain_loop(*args)[-1]
    assert len(charts)==1 and fv.validate_financial_view(charts[0])
    assert "render_financial_widget" in {t["name"] for t in client.calls[0]["tools"]}
    results=json.dumps(client.calls[1]["messages"], default=str)
    assert "fin_" in results
    assert '"normalizer_version"' not in results and '"income"' not in results


def test_internal_statement_reader_cannot_be_forged_as_model_tool(tmp_path):
    (tmp_path/"AAPL.fund.json").write_text(json.dumps(fund()))
    for offered in (set(),{"get_fundamentals"},{"get_fundamentals","render_financial_widget"}):
        result=gw._dispatch_brain_tool("read_financial_statements",{"symbol":"AAPL"},
            tmp_path,tmp_path,"",allowed_tool_names=offered)
        assert result=={"error":"financial_source_not_admitted"}
    result=gw._dispatch_brain_tool("render_financial_widget",
        {"template":"financial_statement","symbol":"AAPL"},tmp_path,tmp_path,"",
        allowed_tool_names={"get_fundamentals","render_financial_widget"})
    assert result["financial_observation"]["result"]["available"]


def test_custom_metric_is_closed_and_statement_compatible():
    assert fv.normalize_request({"template":"financial_statement","symbol":"AAPL",
        "view":{"statement":"cashflow","metric":"fcf"}})["view"]["metric"]=="fcf"
    with pytest.raises(ValueError):
        fv.normalize_request({"template":"financial_statement","symbol":"AAPL",
            "view":{"statement":"income","metric":"fcf"}})


def exact_wire(tmp_path):
    from tests.test_earnings_public_wire import _article
    from engine.earnings_narrative.context_packets import build_context_packet
    article,*_ = _article(tmp_path)
    packet=build_context_packet(article)
    result={"available":True,"ticker":"AAPL","event":packet["event"],
            "receipts":packet["source"],"facts":packet["facts"]}
    return fv.compile_financial_widget({"template":"transcript","symbol":"AAPL"},
        {"reader":"read_earnings_evidence","result":result,"call_id":"exact-1"},"exact-1")


def test_exact_quote_replay_rechecks_current_membership_and_owner(tmp_path,monkeypatch):
    from unittest.mock import patch
    from tests.test_brain_visuals_integration import TID
    from tests.test_brain_visuals_browser import sample
    exact=exact_wire(tmp_path)
    assert fv.validate_financial_view(exact)
    generic=sample()
    statement=wire()
    saved=[statement,exact,generic]
    assert fv.public_financial_visuals({"visuals":saved})==[statement]
    assert fv.public_financial_visuals({"visuals":saved},allow_transcript_quotes=True)==[statement,exact]
    for entitled,expected in [(False,[statement,generic]),(True,saved)]:
        monkeypatch.setattr(gw,"_earnings_evidence_allowed",lambda *a,**k:entitled)
        with patch.object(gw,"_thread_read_rows",side_effect=[[{"id":TID}],
            [{"role":"assistant","content":"Retained evidence.","visuals":saved}]]) as read:
            response=gw.get_thread(TID,"owner")
        assert response["messages"][0]["visuals"]==expected
        assert response["messages"][0].get("visual_notices",[]) == ([] if entitled else [{"type":"membership_required","template":"transcript"}])
        if not entitled:
            assert exact["visual"]["data"]["source_sha256"] not in json.dumps(response)
        assert "user_id=eq.owner" in read.call_args_list[0].args[0]
    with patch.object(gw,"_thread_read_rows",return_value=[]) as read:
        assert gw.get_thread(TID,"intruder") is None
        assert read.call_count==1


def test_changed_transcript_focus_cannot_relabel_an_old_reference(tmp_path,monkeypatch):
    exact=exact_wire(tmp_path)
    reference=fv.model_visible_financial_result(exact)["source_ref"]
    monkeypatch.setattr(gw,"_earnings_evidence_allowed",lambda *a,**k:True)
    request={"financial_request":{"template":"transcript","source_ref":reference,
        "view":{"transcript_id":"another-call"}}}
    assert gw._prepare_financial_widget(request,{reference:exact},{},"r2",[],"member",tmp_path,
        {"read_earnings_evidence"})["error"]=="financial_source_ref_view_unavailable"


def test_forged_quote_receipt_is_not_saved_or_displayed(tmp_path):
    exact=exact_wire(tmp_path)
    altered=copy.deepcopy(exact)
    altered["visual"]["data"]["facts"][0]["quote"]["text"] += " Invented words."
    altered["visual"]["source"]["snapshot_id"]=fv._sha(altered["visual"]["data"])
    assert not fv.validate_financial_view(altered)
    assert fv.public_financial_visuals({"visuals":[altered]},allow_transcript_quotes=True)==[]


def test_fresh_and_reused_views_share_the_identity_derivation(tmp_path):
    original=wire()
    reference=fv.model_visible_financial_result(original)["source_ref"]
    charts=[]
    result=gw._prepare_financial_widget(
        {"financial_request":{"template":"financial_statement","source_ref":reference}},
        {reference:original},{},"turn:read-1",charts,"owner",tmp_path,{"get_fundamentals"})
    assert result["ok"] is True
    assert charts==[original]


def test_withheld_notice_is_static_and_never_exposes_invalid_evidence(tmp_path):
    exact=exact_wire(tmp_path)
    notices=fv.financial_replay_notices({"visuals":[exact]})
    assert notices==[{"type":"membership_required","template":"transcript"}]
    assert fv.financial_replay_notices({"visuals":[exact]},allow_transcript_quotes=True)==[]
    exact["visual"]["data"]["facts"][0]["quote"]["text"] += " forged"
    assert fv.financial_replay_notices({"visuals":[exact]})==[]
