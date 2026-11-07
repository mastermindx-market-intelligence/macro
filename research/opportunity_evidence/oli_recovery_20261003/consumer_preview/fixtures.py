"""Synthetic engineering examples, not market observations or recommendations."""
from copy import deepcopy
from preview_contract import EXPECTED_OWNERS, PROFILE, STRATEGY_SCOPED_OWNERS

CUT = "2026-10-02T15:00:00Z"

def reference(name, generation="fixture-generation-1"):
    owner = EXPECTED_OWNERS.get(name, "portfolio.plan")
    result = {"owner": owner, "schema": f"fixture.{name}/v1",
              "native_id": f"fixture:{name}:demo", "generation": generation,
              "security_id": "fixture:security:demo", "identity_epoch": "fixture-identity-1"}
    if owner in STRATEGY_SCOPED_OWNERS:
        result.update(strategy_owner="prophet.strategy", strategy_id="fixture:strategy:pullback", strategy_version="fixture.v1")
    return result

def baseline():
    values = {
        "phase": {"native_state": "CONFIRMED", "reason": "The fixture's completed-bar confirmation remains recorded."},
        "entry": {"native_verdict": "WAIT_FOR_RESET", "reason": "The source fixture does not offer a fresh entry at this quote.",
                  "phase_ref": reference("phase"), "quote_ref": reference("quote"), "geometry_ref": reference("geometry")},
        "geometry": {"trigger": "128.00", "invalidation": "123.40", "currency": "USD", "price_basis": "fixture-unadjusted",
                     "basis_at": "2026-10-02T14:30:00Z", "opportunity_expires_at": "2026-10-09T20:00:00Z"},
        "quote": {"price": "132.10", "currency": "USD", "price_basis": "fixture-unadjusted"},
        "support": {"text": "The completed-bar confirmation remains intact.", "dependence_group": "price_structure"},
        "contradiction": {"text": "Peer participation is weak despite the subject's advance.", "dependence_group": "peer_breadth"},
        "next_condition": {"text": "Reassess only after the owner records a qualified reset and a new entry verdict.", "dependence_group": "strategy_rule"},
    }
    sources = {name: {"ref": reference(name), "status": "AVAILABLE", "observed_at": "2026-10-02T14:59:00Z",
                      "known_at": "2026-10-02T14:59:10Z", "valid_until": "2026-10-02T15:05:00Z", "value": value,
                      "correction_of": None} for name, value in values.items()}
    return {"profile": PROFILE, "synthetic": True, "scenario": "Confirmed, but no fresh entry", "decision_at": CUT,
            "subject": {"security_id": "fixture:security:demo", "identity_epoch": "fixture-identity-1", "ticker": "DEMO",
                        "name": "Demonstration Semiconductor"},
            "strategy": {"owner": "prophet.strategy", "id": "fixture:strategy:pullback", "version": "fixture.v1",
                         "label": "Pullback continuation", "holding_horizon": "10–30 trading sessions"},
            "sources": sources, "forecasts": None}

def plan(state="SAVED", has_position=None):
    return {"synthetic": True, "viewer_id": "fixture-viewer", "ref": reference("plan"), "native_state": state,
            "has_position": has_position, "known_at": "2026-10-02T14:58:00Z", "valid_until": "2026-10-02T16:00:00Z"}

def absent(bundle, source, status="UNAVAILABLE"):
    row = bundle["sources"][source]
    row.update(status=status, value=None, observed_at=None, known_at=None, valid_until=None)
    return bundle

def scenarios():
    out = []
    def add(key, label, change=lambda b: None, private=None):
        b=baseline(); b["scenario"]=label; change(b)
        out.append({"key":key,"bundle":b,"private_plan":private if private is not None else plan()})
    add("confirmed", "Confirmed, but no fresh entry")
    add("holding", "Existing position, no fresh entry", private=plan("ENTERED", True))
    add("expired_entry", "Fresh quote cannot refresh expired permission", lambda b: b["sources"]["entry"].update(valid_until=CUT))
    add("mixed_generation", "New quote generation, old permission", lambda b: b["sources"]["quote"]["ref"].update(generation="fixture-generation-2"))
    add("missing_optional", "Optional peer context unavailable", lambda b: absent(b,"contradiction","NOT_COVERED"))
    add("transport_failure", "Entry transport unavailable — not a quiet market", lambda b: absent(b,"entry","TRANSPORT_UNAVAILABLE"))
    add("future_knowledge", "Known-later confirmation stays undisplayed", lambda b: b["sources"]["phase"].update(known_at="2026-10-02T15:01:00Z"))
    def correct(b):
        row=b["sources"]["contradiction"];row["correction_of"]=deepcopy(row["ref"])
        row["ref"]["generation"]="fixture-generation-2";row["value"]["text"]="The owner corrected the earlier peer-coverage reading; the prior generation is retained."
    add("correction", "A source correction retains its prior reference", correct)
    add("rights", "Source rights blocked", lambda b: absent(b,"support","RIGHTS_BLOCKED"))
    add("native_extended", "Native EXTENDED is not a sell instruction", lambda b: b["sources"]["phase"]["value"].update(native_state="EXTENDED"), private=plan("ENTERED",True))
    return out
