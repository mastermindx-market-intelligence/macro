"""Structural native-plan contracts only; no real-source or publication acceptance.

All evidence and commentary below are fictional. No provider/generation is used.
"""
import copy

import pytest

from engine.press import validators as V, writer as W
from engine.press.native_plan_scope import scope_fragments
from tests import press_fixtures as F


def native_slot():
    ref = "chronicle:TEST-BULL-20260701"
    scope = dict(source_ref=ref, asset="TEST", recorded_at="2026-07-02",
                 price_basis_date="2026-07-01", close_date="2026-07-24",
                 authority_tier="display", entry_status="bounce_wait", confirmed_date=None,
                 quantities=dict(entry_reference=51.8, invalidation_threshold=46.22,
                                 target_1=60.17, target_2=68.54,
                                 stock_result_pct=-13.9223, days_held=23))
    lead = dict(id="lead", ref=ref, tier="first_party", values=[],
                text="Historical TEST simulated plan: stock -13.92% (plan result); held 23d.")
    plan = dict(id="plan", ref="prophet_plan:TEST-BULL-20260701", tier="first_party",
                values=[51.8, 46.22, 60.17, 68.54], dated="2026-07-02",
                text="Historical TEST plan recorded 2026-07-02, price basis 2026-07-01: "
                     "entry reference $51.8; invalidation threshold $46.22; "
                     "hypothetical target levels $60.17, $68.54.",
                native_plan_scope=copy.deepcopy(scope))
    context = dict(id="context", ref="artifact:context", tier="first_party", values=[51.8],
                   text="The unrelated market-state composite reads 51.8 today.")
    return F.slot(id="structural-native-plan", as_of="2026-07-26", min_words=300,
                  max_words=600, min_anchored_receipts=5,
                  story=dict(kind="signal_close", tickers=["TEST"], event_date="2026-07-24"),
                  primary_source=dict(kind="first_party", name="Mastermind Prophet ledger", ref=ref),
                  sources=[ref], facts=[lead, plan, context], raw_documents=[],
                  native_plan_scope=scope,
                  allowed_links=["https://www.mastermind-x.com/stocks/TEST.html"])


def positive_draft(slot):
    # Exact quantitative clauses earn receipts. The related explanatory
    # sentences exercise the unchanged sentence-level anchoring contract.
    paragraphs = [
        "Entry reference $51.8; this historical parameter establishes the starting reference "
        "used by the fictional paper scenario and is distinct from evidence that an investor "
        "actually entered a position at the recorded amount in a brokerage account.",
        "Invalidation threshold $46.22; this boundary describes how the recorded hypothetical "
        "scenario would be evaluated and must be distinguished from an observed transaction, "
        "a current instruction, or a claim that an actual stop order was submitted or executed.",
        "Hypothetical target levels $60.17, $68.54; these planned references describe the "
        "original scenario and do not establish that either target was achieved, that a "
        "position existed, or that any investor received the returns implied by those levels.",
        "Stock -13.92% (plan result); held 23d; the result belongs to the simulated scenario "
        "and its stated interval, so it provides an account of the fictional model record "
        "while leaving actual fills, transaction costs, and investor performance unestablished.",
        "The record separates its original setup from the subsequent outcome. The point of "
        "the comparison is accountability for the historical scenario rather than an effort "
        "to explain an issuer event or to turn a closed record into another actionable signal. "
        "Nothing here identifies a company-specific cause or tests the predictive quality "
        "of a population of signals. That would require separate evidence and a separate "
        "assessment with an appropriate comparison group.",
        "The recording date describes when the plan entered the model record, whereas the "
        "price basis identifies the vintage used to state its parameters. The later closure "
        "date belongs to the outcome record. Keeping those clocks separate prevents an "
        "old setup from appearing to be a fresh signal and prevents a recent outcome from "
        "changing what was known when the plan was first recorded.",
        "; ".join(scope_fragments(slot)) + ". "
        '<a href="https://www.mastermind-x.com/stocks/TEST.html">Company dossier</a>.',
    ]
    return F.draft(*paragraphs, title="A fictional historical plan closes",
                   description="A fictional historical paper plan illustrates the boundary between recorded parameters and simulated outcomes, with no executed-trade claim.",
                   slug="fictional-historical-plan-closes", fold=False)


def test_structural_positive_keeps_all_relevant_thresholds(tmp_path):
    slot = native_slot()
    draft = positive_draft(slot)
    cfg = F.config()
    report = V.validate(draft, slot, cfg, root=tmp_path)
    assert report["ok"], [(r["name"], r["detail"]) for r in report["checks"] if not r["ok"]]
    assert report["receipts"] == 6
    assert report["our_value_share"] >= .4
    assert 300 <= report["words"] <= 600
    assert cfg["validators"]["our_value_min"] == .4


def test_known_context_number_collision_earns_no_credit():
    slot = native_slot()
    draft = F.draft(slot["facts"][-1]["text"], fold=False, byline=False, footer=False)
    assert V.check_receipts(draft, slot, F.config())["metrics"]["receipts"] == 0
    assert V.check_our_value(draft, slot, F.config())["metrics"]["our_value_share"] == 0


@pytest.mark.parametrize("change", ["missing", "stale", "different_fact"])
def test_bad_native_scope_refuses_before_model_lookup(monkeypatch, change):
    slot = native_slot()
    if change == "missing":
        slot.pop("native_plan_scope")
    elif change == "stale":
        slot["native_plan_scope"]["close_date"] = "2026-07-23"
    else:
        slot["facts"][1]["native_plan_scope"]["entry_status"] = "active"
    def forbidden(*_a, **_kw):
        pytest.fail("model lookup/provider work must not occur")
    monkeypatch.setattr(W, "_model_id", forbidden)
    state = W.RunState()
    result = W.write(slot, F.config(), state=state, single_provider_attempt=True)
    assert not result["ok"] and result["reason"] == "native_plan_scope_invalid"
    assert state.calls == state.tokens_used == state.failures == 0


def test_writer_exposes_only_bound_facts_and_requires_dossier_and_limits():
    slot = native_slot()
    _system, prompt = W.build_prompt(slot, F.config())
    assert slot["facts"][0]["text"] in prompt and slot["facts"][1]["text"] in prompt
    assert slot["facts"][-1]["text"] not in prompt
    assert "CONTINUATION" in prompt
    assert all(fragment in prompt for fragment in scope_fragments(slot))


def test_scope_check_requires_real_dossier_anchor():
    slot = native_slot()
    draft = positive_draft(slot)
    draft["body_html"] = draft["body_html"].replace(
        '<a href="https://www.mastermind-x.com/stocks/TEST.html">Company dossier</a>',
        "https://www.mastermind-x.com/stocks/TEST.html")
    assert not V.check_native_plan_scope(draft, slot, F.config())["ok"]


def test_legacy_nonplan_contract_is_unchanged():
    slot = F.slot()
    draft = F.draft("Our composite reads 56 today.", fold=False, byline=False, footer=False)
    assert V.native_plan_preflight(slot, F.config()) == {"ok": True, "active": False}
    assert V.check_native_plan_scope(draft, slot, F.config())["metrics"]["active"] is False
    assert V.check_our_value(draft, slot, F.config())["metrics"]["our_value_share"] == 1


def test_rounded_result_and_repeated_entry_do_not_create_extra_receipts():
    slot = native_slot()
    slot['facts'][0]['text'] += ' Stock -13.9% (plan result).'
    slot['facts'][1]['text'] += ' Activation trigger $51.8.'
    draft = positive_draft(slot)
    draft['body_html'] += '<p>Stock -13.9% (plan result); activation trigger $51.8.</p>'
    row = V.check_receipts(draft, slot, F.config())
    assert row['metrics']['receipts'] == 6


def test_missing_existing_dossier_refuses_before_model_lookup(monkeypatch):
    slot = native_slot()
    slot['allowed_links'] = []
    monkeypatch.setattr(W, '_model_id', lambda *_: pytest.fail('no provider preflight'))
    result = W.write(slot, F.config(), state=W.RunState())
    assert result['reason'] == 'native_plan_scope_invalid'


def test_unavailable_distinct_story_receipts_refuse_without_refill(monkeypatch):
    slot = native_slot()
    slot['min_anchored_receipts'] = 7
    before = copy.deepcopy(slot)
    monkeypatch.setattr(W, '_model_id', lambda *_: pytest.fail('no provider preflight'))
    result = W.write(slot, F.config(), state=W.RunState())
    assert result['reason'] == 'native_plan_receipts_insufficient'
    assert slot == before


@pytest.mark.parametrize("ref", ["invalid", "chronicle:", "chronicle: ", "prophet_plan:TEST"])
def test_malformed_primary_binding_refuses_before_model_lookup(monkeypatch, ref):
    slot = native_slot()
    slot["primary_source"]["ref"] = ref
    slot["sources"] = [ref]
    slot["native_plan_scope"]["source_ref"] = ref
    slot["facts"][0]["ref"] = ref
    slot["facts"][1]["native_plan_scope"]["source_ref"] = ref
    monkeypatch.setattr(W, "_model_id", lambda *_: pytest.fail("no model/provider work"))
    state = W.RunState()
    result = W.write(slot, F.config(), state=state, single_provider_attempt=True)
    assert not result["ok"] and result["reason"] == "native_plan_scope_invalid"
    assert state.calls == state.tokens_used == state.failures == 0


@pytest.mark.parametrize("anchor, usable", [
    ('<a href="/stocks/TEST.html"></a>', False),
    ('<a href="/stocks/TEST.html">  </a>', False),
    ('<a href="/stocks/TEST.html"><!--Company dossier--></a>', False),
    ('<a href="/stocks/TEST.html" hidden>Company dossier</a>', False),
    ('<div hidden><a href="/stocks/TEST.html">Company dossier</a></div>', False),
    ('<a href="/stocks/TEST.html"><span aria-hidden="true">Company dossier</span></a>', False),
    ('<a href="/stocks/TEST.html" style="display: none">Company dossier</a>', False),
    ('&lt;a href="/stocks/TEST.html"&gt;Company dossier&lt;/a&gt;', False),
    ('<a href="/stocks/TEST.html">Company dossier</a>', True),
    ('<a href="/stocks/TEST.html"><strong>Company dossier</strong></a>', True),
])
def test_dossier_continuation_requires_visible_anchor_label(anchor, usable):
    from engine.press.native_plan_scope import scope_problems
    slot = native_slot()
    body = positive_draft(slot)["body_html"]
    body = body.replace('<a href="https://www.mastermind-x.com/stocks/TEST.html">Company dossier</a>', anchor)
    problems = scope_problems(body, slot)
    assert (not any("continuation" in p for p in problems)) is usable
