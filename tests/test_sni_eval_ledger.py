"""Executable invariants for the SNI evaluation registration ledger draft."""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/evaluation"),
)

from sni_eval_ledger import (  # noqa: E402
    ABSTAIN,
    AUTHORITY_KEYS,
    BUDGET,
    CENSORED,
    MATURED,
    NOGO,
    PENDING,
    PUBLISH,
    REFUSAL_CODES,
    REGISTER,
    RESOLVE,
    SCORE,
    UNPRICEABLE,
    EvalLedger,
    LedgerRefused,
    brier,
    replay,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "research/single_name_intelligence/evaluation/REGISTRATION_LEDGER_DRAFT.md"
MOD = ROOT / "research/single_name_intelligence/evaluation/sni_eval_ledger.py"

DIGEST = "a" * 64
DIGEST_B = "b" * 64
PUBLISHED_AT = "2020-01-01T00:00:00Z"
HORIZON_END = "2020-02-01T00:00:00Z"
AFTER_HORIZON = "2020-02-02T00:00:00Z"
BEFORE_HORIZON = "2020-01-15T00:00:00Z"

BRIDGE_SENTENCE = (
    "Hit/return grading is not probabilistic forecast support until an accepted bridge exists."
)


def _led(tmp_path, name="eval.jsonl"):
    return EvalLedger(tmp_path / name)


def _reg(led, family_id="fam-a", protocol="sni.v0", version="1", split="test", h=21,
         digest=DIGEST):
    return led.append(REGISTER, {
        "family_id": family_id,
        "protocol": protocol,
        "version": version,
        "split": split,
        "h": h,
        "prereg_digest": digest,
    })


def _budget(led, family_id="fam-a", n=8):
    return led.append(BUDGET, {"family_id": family_id, "declared_trials": n})


def _publish(led, forecast_id, family_id="fam-a", p=0.25, **extra):
    payload = {
        "forecast_id": forecast_id,
        "family_id": family_id,
        "p": p,
        "inputs_digest": DIGEST,
        "published_at_utc": PUBLISHED_AT,
        "horizon_end_utc": HORIZON_END,
    }
    payload.update(extra)
    return led.append(PUBLISH, payload)


def _abstain(led, forecast_id, family_id="fam-a", reason="unestimable-coverage"):
    return led.append(ABSTAIN, {
        "forecast_id": forecast_id,
        "family_id": family_id,
        "reason": reason,
    })


def _resolve(led, forecast_id, state, outcome, observed_at_utc=AFTER_HORIZON):
    return led.append(RESOLVE, {
        "forecast_id": forecast_id,
        "state": state,
        "observed_at_utc": observed_at_utc,
        "outcome": outcome,
    })


def _prep(led, n=8, family_id="fam-a"):
    _reg(led, family_id=family_id)
    _budget(led, family_id=family_id, n=n)


def test_a26_duplicate_register_refused_count_stays_1(tmp_path):
    led = _led(tmp_path)
    _reg(led)
    assert led.registered_count() == 1
    with pytest.raises(LedgerRefused) as ei:
        _reg(led)
    assert ei.value.code == "ALREADY_REGISTERED"
    assert led.registered_count() == 1
    assert len(led.rows()) == 1


def test_a26_two_different_keys_count_2(tmp_path):
    led = _led(tmp_path)
    _reg(led, h=21)
    _reg(led, h=63)
    assert led.registered_count() == 2
    assert len(led.rows()) == 2


def test_budget_required(tmp_path):
    led = _led(tmp_path)
    _reg(led)
    with pytest.raises(LedgerRefused) as ei:
        _publish(led, "f1")
    assert ei.value.code == "BUDGET_REQUIRED"
    with pytest.raises(LedgerRefused) as ei:
        _abstain(led, "f2")
    assert ei.value.code == "BUDGET_REQUIRED"
    assert len(led.rows()) == 1


def test_budget_exceeded_on_nth_plus_1_trial(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=2)
    _publish(led, "f1", p=0.2)
    _abstain(led, "f2")
    with pytest.raises(LedgerRefused) as ei:
        _publish(led, "f3", p=0.3)
    assert ei.value.code == "BUDGET_EXCEEDED"
    assert led.state()["counts"]["published"] == 1
    assert led.state()["counts"]["abstained"] == 1


def test_a27_second_publish_same_id_same_p_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=4)
    _publish(led, "f1", p=0.2)
    with pytest.raises(LedgerRefused) as ei:
        _publish(led, "f1", p=0.2)
    assert ei.value.code == "IMMUTABLE_PUBLICATION"
    assert len(led.state()["published"]) == 1


def test_a27_second_publish_same_id_different_p_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=4)
    _publish(led, "f1", p=0.2)
    with pytest.raises(LedgerRefused) as ei:
        _publish(led, "f1", p=0.8)
    assert ei.value.code == "IMMUTABLE_PUBLICATION"
    stored_p = led.state()["published"]["f1"]["payload"]["p"]
    assert stored_p == 0.2


def test_a27_replay_from_file_equals_incremental_state(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=4)
    _publish(led, "f1", p=0.2)
    _publish(led, "f2", p=0.8)
    _resolve(led, "f1", MATURED, 0)
    led.assert_replay_equal()
    from_file = replay(led.path)
    assert from_file == led.state()
    assert from_file["published"]["f1"]["payload"]["p"] == 0.2


def test_a27_chain_verifies(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=3)
    _publish(led, "f1", p=0.3)
    assert led.verify_chain() == []
    rows = led.rows()
    assert rows[0]["prev_hash"] is None
    for i in range(1, len(rows)):
        assert rows[i]["prev_hash"] == rows[i - 1]["row_hash"]


def test_a27_tamper_middle_line_violation(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=3)
    _publish(led, "f1", p=0.3)
    _publish(led, "f2", p=0.4)
    path = led.path
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 3
    mid = json.loads(lines[1])
    mid["payload"]["family_id"] = "tampered-family"
    lines[1] = json.dumps(mid, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    violations = EvalLedger(path).verify_chain()
    assert violations
    assert any("HASH" in v or "PREV" in v for v in violations)


def test_a25_p_half_without_declared_reason_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=2)
    with pytest.raises(LedgerRefused) as ei:
        _publish(led, "f1", p=0.5)
    assert ei.value.code == "DEFAULT_PROBABILITY_REFUSED"
    assert led.state()["published"] == {}


def test_a25_p_half_with_declared_reason_accepted(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=2)
    row = _publish(led, "f1", p=0.5, declared_reason="named-uninformative-prior")
    assert row["payload"]["p"] == 0.5
    assert "f1" in led.state()["published"]


def test_a28_matured_needs_outcome(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=2)
    _publish(led, "f1", p=0.2)
    with pytest.raises(LedgerRefused) as ei:
        _resolve(led, "f1", MATURED, None)
    assert ei.value.code == "MATURED_OUTCOME_REQUIRED"
    assert led.state()["resolved"] == {}


def test_a28_censored_forbids_outcome(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=2)
    _publish(led, "f1", p=0.2)
    with pytest.raises(LedgerRefused) as ei:
        _resolve(led, "f1", CENSORED, 1)
    assert ei.value.code == "OUTCOME_FORBIDDEN"


def test_a28_early_matured_before_horizon_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=2)
    _publish(led, "f1", p=0.2)
    with pytest.raises(LedgerRefused) as ei:
        _resolve(led, "f1", MATURED, 1, observed_at_utc=BEFORE_HORIZON)
    assert ei.value.code == "HORIZON_NOT_REACHED"


def test_a28_second_resolve_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=2)
    _publish(led, "f1", p=0.2)
    _resolve(led, "f1", CENSORED, None)
    with pytest.raises(LedgerRefused) as ei:
        _resolve(led, "f1", MATURED, 1)
    assert ei.value.code == "ALREADY_RESOLVED"
    assert led.state()["resolved"]["f1"] == CENSORED


def test_a28_four_states_distinct_pending_unresolved(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=4)
    _publish(led, "f-pending", p=0.2)
    _publish(led, "f-matured", p=0.3)
    _publish(led, "f-censored", p=0.4)
    _publish(led, "f-unpriceable", p=0.6)
    _resolve(led, "f-matured", MATURED, 1)
    _resolve(led, "f-censored", CENSORED, None)
    _resolve(led, "f-unpriceable", UNPRICEABLE, None)
    st = led.state()
    assert "f-pending" in st["published"]
    assert "f-pending" not in st["resolved"]
    assert st["resolved"]["f-matured"] == MATURED
    assert st["resolved"]["f-censored"] == CENSORED
    assert st["resolved"]["f-unpriceable"] == UNPRICEABLE
    assert st["counts"]["pending"] == 1
    seen = {
        PENDING,
        st["resolved"]["f-matured"],
        st["resolved"]["f-censored"],
        st["resolved"]["f-unpriceable"],
    }
    assert seen == {PENDING, MATURED, CENSORED, UNPRICEABLE}


def test_a29_brier_recompute_exact_three_matured(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=4)
    _publish(led, "f1", p=0.25)
    _publish(led, "f2", p=0.50, declared_reason="named-uninformative-prior")
    _publish(led, "f3", p=0.75)
    _resolve(led, "f1", MATURED, 0)
    _resolve(led, "f2", MATURED, 1)
    _resolve(led, "f3", MATURED, 1)
    expected = 0.125
    assert brier(led, "fam-a") == expected
    row = led.append(SCORE, {
        "family_id": "fam-a",
        "baseline_id": "caller-frozen-baseline",
        "baseline_digest": DIGEST_B,
        "scored_forecast_ids": ["f1", "f2", "f3"],
        "brier": expected,
        "baseline_brier": 0.25,
        "n": 3,
        "descriptive_only": True,
    })
    assert row["payload"]["brier"] == expected
    assert row["payload"]["descriptive_only"] is True
    assert len(led.state()["scores"]) == 1


def test_a29_score_wrong_brier_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=3)
    _publish(led, "f1", p=0.25)
    _publish(led, "f2", p=0.25)
    _publish(led, "f3", p=0.25)
    _resolve(led, "f1", MATURED, 0)
    _resolve(led, "f2", MATURED, 0)
    _resolve(led, "f3", MATURED, 1)
    with pytest.raises(LedgerRefused) as ei:
        led.append(SCORE, {
            "family_id": "fam-a",
            "baseline_id": "caller-frozen-baseline",
            "baseline_digest": DIGEST_B,
            "scored_forecast_ids": ["f1", "f2", "f3"],
            "brier": 0.0,
            "baseline_brier": 0.25,
            "n": 3,
            "descriptive_only": True,
        })
    assert ei.value.code == "BRIER_MISMATCH"
    assert led.state()["scores"] == []


def test_a29_score_non_matured_id_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=3)
    _publish(led, "f1", p=0.25)
    _publish(led, "f2", p=0.25)
    _publish(led, "f3", p=0.25)
    _resolve(led, "f1", MATURED, 0)
    _resolve(led, "f2", MATURED, 0)
    with pytest.raises(LedgerRefused) as ei:
        led.append(SCORE, {
            "family_id": "fam-a",
            "baseline_id": "caller-frozen-baseline",
            "baseline_digest": DIGEST_B,
            "scored_forecast_ids": ["f1", "f2", "f3"],
            "brier": 0.0625,
            "baseline_brier": 0.25,
            "n": 3,
            "descriptive_only": True,
        })
    assert ei.value.code == "NOT_MATURED"


def test_a30_nogo_then_publish_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=4)
    led.append(NOGO, {"family_id": "fam-a", "reason": "failed-prereg-check"})
    with pytest.raises(LedgerRefused) as ei:
        _publish(led, "f1", p=0.2)
    assert ei.value.code == "FAMILY_NOGO"
    assert "fam-a" in led.state()["nogo"]


def test_a30_different_family_still_publishes(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=4, family_id="fam-a")
    _prep(led, n=4, family_id="fam-b")
    led.append(NOGO, {"family_id": "fam-a", "reason": "failed-prereg-check"})
    row = _publish(led, "fb1", family_id="fam-b", p=0.3)
    assert row["payload"]["family_id"] == "fam-b"
    assert "fb1" in led.state()["published"]
    with pytest.raises(LedgerRefused) as ei:
        _publish(led, "fa1", family_id="fam-a", p=0.3)
    assert ei.value.code == "FAMILY_NOGO"


def test_authority_key_in_payload_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=2)
    for key in AUTHORITY_KEYS:
        payload = {
            "forecast_id": "f-auth",
            "family_id": "fam-a",
            "p": 0.2,
            "inputs_digest": DIGEST,
            "published_at_utc": PUBLISHED_AT,
            "horizon_end_utc": HORIZON_END,
            key: True,
        }
        with pytest.raises(LedgerRefused) as ei:
            led.append(PUBLISH, payload)
        assert ei.value.code == "AUTHORITY_FLAG_REFUSED"
    payload_false = {
        "forecast_id": "f-auth",
        "family_id": "fam-a",
        "p": 0.2,
        "inputs_digest": DIGEST,
        "published_at_utc": PUBLISHED_AT,
        "horizon_end_utc": HORIZON_END,
        "rank_authority": False,
    }
    with pytest.raises(LedgerRefused) as ei:
        led.append(PUBLISH, payload_false)
    assert ei.value.code == "AUTHORITY_FLAG_REFUSED"
    assert led.state()["published"] == {}


def test_doc_refusal_codes_exist_in_module():
    doc = DOC.read_text(encoding="utf-8")
    mod = MOD.read_text(encoding="utf-8")
    assert BRIDGE_SENTENCE in doc
    start = doc.index("## Refusal code table")
    section = doc[start:]
    end_markers = [m.start() for m in re.finditer(r"\n## ", section[3:])]
    table = section if not end_markers else section[: end_markers[0] + 3]
    codes = set(re.findall(r"`([A-Z][A-Z0-9_]+)`", table))
    codes.discard("REGISTER")
    codes.discard("BUDGET")
    codes.discard("PUBLISH")
    codes.discard("ABSTAIN")
    codes.discard("RESOLVE")
    codes.discard("SCORE")
    codes.discard("NOGO")
    codes.discard("PENDING")
    codes.discard("UNPRICEABLE")
    codes.discard("CENSORED")
    codes.discard("MATURED")
    assert codes
    for code in sorted(codes):
        assert code in mod, code
        assert code in REFUSAL_CODES, code
    for code in sorted(REFUSAL_CODES):
        assert code in doc, code
        assert code in mod, code


def test_unpriceable_forbids_outcome(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=2)
    _publish(led, "f1", p=0.2)
    with pytest.raises(LedgerRefused) as ei:
        _resolve(led, "f1", UNPRICEABLE, 0)
    assert ei.value.code == "OUTCOME_FORBIDDEN"


def test_abstain_and_publish_are_mutually_exclusive(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=4)
    _abstain(led, "f1")
    with pytest.raises(LedgerRefused) as ei:
        _publish(led, "f1", p=0.2)
    assert ei.value.code == "ALREADY_ABSTAINED"
    _publish(led, "f2", p=0.2)
    with pytest.raises(LedgerRefused) as ei:
        _abstain(led, "f2")
    assert ei.value.code == "ALREADY_PUBLISHED"
