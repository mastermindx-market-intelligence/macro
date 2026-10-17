"""Executable invariants for the SNI evaluation registration ledger draft."""
import datetime
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/evaluation"),
)

import sni_eval_ledger  # noqa: E402
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
    REGISTERED,
    RESOLVE,
    SCORE,
    UNPRICEABLE,
    EvalLedger,
    LedgerRefused,
    _row_hash,
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


def _reg_at(led, family_id="fam-a"):
    for row in led.rows():
        if row["kind"] == REGISTER and row["payload"]["family_id"] == family_id:
            return row["written_at_utc"]
    raise AssertionError("no REGISTER row for %s" % family_id)


def _shift(ts, days):
    raw = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
    dt = datetime.datetime.fromisoformat(raw) + datetime.timedelta(days=days)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _publish(led, forecast_id, family_id="fam-a", p=0.25, **extra):
    reg_at = _reg_at(led, family_id)
    payload = {
        "forecast_id": forecast_id,
        "family_id": family_id,
        "p": p,
        "inputs_digest": DIGEST,
        "published_at_utc": extra.pop("published_at_utc", _shift(reg_at, 1)),
        "horizon_end_utc": extra.pop("horizon_end_utc", _shift(reg_at, 32)),
    }
    payload.update(extra)
    return led.append(PUBLISH, payload)


def _abstain(led, forecast_id, family_id="fam-a", reason="unestimable-coverage"):
    return led.append(ABSTAIN, {
        "forecast_id": forecast_id,
        "family_id": family_id,
        "reason": reason,
    })


def _resolve(led, forecast_id, state, outcome, observed_at_utc=None):
    if observed_at_utc is None:
        observed_at_utc = AFTER_HORIZON
        for row in led.rows():
            if row["kind"] == PUBLISH and row["payload"]["forecast_id"] == forecast_id:
                observed_at_utc = _shift(row["payload"]["horizon_end_utc"], 1)
                break
    return led.append(RESOLVE, {
        "forecast_id": forecast_id,
        "state": state,
        "observed_at_utc": observed_at_utc,
        "outcome": outcome,
    })


def _prep(led, n=8, family_id="fam-a"):
    _reg(led, family_id=family_id)
    _budget(led, family_id=family_id, n=n)


def _score_payload(led, family_id="fam-a", **overrides):
    st = led.state()
    matured = []
    n_censored = n_unpriceable = n_pending = 0
    for fid, pub in st["published"].items():
        if pub["payload"].get("family_id") != family_id:
            continue
        res = st["resolved"].get(fid)
        if res == MATURED:
            matured.append(fid)
        elif res == CENSORED:
            n_censored += 1
        elif res == UNPRICEABLE:
            n_unpriceable += 1
        elif res is None:
            n_pending += 1
    matured.sort()
    payload = {
        "family_id": family_id,
        "baseline_id": "caller-frozen-baseline",
        "baseline_digest": DIGEST_B,
        "scored_forecast_ids": list(matured),
        "brier": brier(led, family_id) if matured else 0.0,
        "baseline_brier": 0.25,
        "n": len(matured),
        "n_censored": n_censored,
        "n_unpriceable": n_unpriceable,
        "n_pending": n_pending,
        "descriptive_only": True,
    }
    payload.update(overrides)
    return payload


def _hand_row(kind, payload, written_at_utc="2020-01-01T00:00:00Z"):
    row = {
        "seq": 1,
        "kind": kind,
        "written_at_utc": written_at_utc,
        "payload": payload,
        "prev_hash": None,
    }
    row["row_hash"] = _row_hash(row)
    return row


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
    before = _shift(_reg_at(led), 15)
    with pytest.raises(LedgerRefused) as ei:
        _resolve(led, "f1", MATURED, 1, observed_at_utc=before)
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
    row = led.append(SCORE, _score_payload(led, brier=expected))
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
        led.append(SCORE, _score_payload(led, brier=0.0))
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
        led.append(SCORE, _score_payload(
            led,
            scored_forecast_ids=["f1", "f2", "f3"],
            brier=0.0625,
            n=3,
        ))
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
    times = {
        "published_at_utc": _shift(_reg_at(led), 1),
        "horizon_end_utc": _shift(_reg_at(led), 32),
    }
    for key in AUTHORITY_KEYS:
        payload = {
            "forecast_id": "f-auth",
            "family_id": "fam-a",
            "p": 0.2,
            "inputs_digest": DIGEST,
            key: True,
        }
        payload.update(times)
        with pytest.raises(LedgerRefused) as ei:
            led.append(PUBLISH, payload)
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


def test_r1_01_score_only_file_refused(tmp_path):
    path = tmp_path / "score_only.jsonl"
    payload = {
        "family_id": "fam-a",
        "baseline_id": "caller-frozen-baseline",
        "baseline_digest": DIGEST_B,
        "scored_forecast_ids": ["f1"],
        "brier": 0.0625,
        "baseline_brier": 0.25,
        "n": 1,
        "n_censored": 0,
        "n_unpriceable": 0,
        "n_pending": 0,
        "descriptive_only": True,
    }
    row = _hand_row(SCORE, payload)
    path.write_text(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    led = EvalLedger(path)
    violations = led.verify_chain()
    assert violations
    assert any("FAMILY_NOT_REGISTERED" in v for v in violations)
    with pytest.raises(LedgerRefused) as ei:
        led.state()
    assert ei.value.code == "FAMILY_NOT_REGISTERED"


def test_r1_01_resolve_only_file_refused(tmp_path):
    path = tmp_path / "resolve_only.jsonl"
    payload = {
        "forecast_id": "f1",
        "state": MATURED,
        "observed_at_utc": "2020-02-02T00:00:00Z",
        "outcome": 1,
    }
    row = _hand_row(RESOLVE, payload)
    path.write_text(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    led = EvalLedger(path)
    violations = led.verify_chain()
    assert violations
    assert any("UNKNOWN_FORECAST" in v for v in violations)
    with pytest.raises(LedgerRefused) as ei:
        led.state()
    assert ei.value.code == "UNKNOWN_FORECAST"


def test_r1_01_valid_ledger_still_replays(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=4)
    _publish(led, "f1", p=0.25)
    _resolve(led, "f1", MATURED, 0)
    led.append(SCORE, _score_payload(led))
    assert led.verify_chain() == []
    led.assert_replay_equal()


def test_r1_02_publish_before_register_refused(tmp_path):
    led = _led(tmp_path)
    _reg(led)
    _budget(led)
    n = len(led.rows())
    with pytest.raises(LedgerRefused) as ei:
        _publish(led, "f1", p=0.25, published_at_utc="2020-01-01T00:00:00Z")
    assert ei.value.code == "PUBLISH_BEFORE_REGISTER"
    assert len(led.rows()) == n


def test_r1_02_horizon_before_publish_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=2)
    n = len(led.rows())
    reg_at = _reg_at(led)
    with pytest.raises(LedgerRefused) as ei:
        _publish(
            led, "f1", p=0.25,
            published_at_utc=_shift(reg_at, 10),
            horizon_end_utc=_shift(reg_at, 1),
        )
    assert ei.value.code == "HORIZON_BEFORE_PUBLISH"
    assert len(led.rows()) == n


def test_r1_02_outcome_before_register_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=2)
    _publish(led, "f1", p=0.25)
    n = len(led.rows())
    with pytest.raises(LedgerRefused) as ei:
        _resolve(led, "f1", MATURED, 1, observed_at_utc="2019-06-01T00:00:00Z")
    assert ei.value.code == "OUTCOME_BEFORE_REGISTER"
    assert len(led.rows()) == n


def test_r1_02_pre_registration_score_unreachable(tmp_path):
    led = _led(tmp_path)
    _reg(led)
    _budget(led)
    try:
        _publish(
            led, "f1", p=0.25,
            published_at_utc="2019-01-01T00:00:00Z",
            horizon_end_utc="2019-06-01T00:00:00Z",
        )
    except LedgerRefused:
        pass
    try:
        _resolve(led, "f1", MATURED, 1, observed_at_utc="2019-12-15T00:00:00Z")
    except LedgerRefused:
        pass
    try:
        led.append(SCORE, {
            "family_id": "fam-a",
            "baseline_id": "caller-frozen-baseline",
            "baseline_digest": DIGEST_B,
            "scored_forecast_ids": ["f1"],
            "brier": 0.5625,
            "baseline_brier": 0.25,
            "n": 1,
            "n_censored": 0,
            "n_unpriceable": 0,
            "n_pending": 0,
            "descriptive_only": True,
        })
    except LedgerRefused:
        pass
    assert all(r["kind"] != SCORE for r in led.rows())
    assert led.state()["scores"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("brier", float("nan")),
        ("brier", float("inf")),
        ("baseline_brier", float("nan")),
        ("baseline_brier", float("-inf")),
        ("brier", True),
    ],
)
def test_r1_07_nonfinite_brier_refused(tmp_path, field, value):
    led = _led(tmp_path)
    _prep(led, n=2)
    _publish(led, "f1", p=0.25)
    _resolve(led, "f1", MATURED, 0)
    n = len(led.rows())
    payload = _score_payload(led)
    payload[field] = value
    with pytest.raises(LedgerRefused) as ei:
        led.append(SCORE, payload)
    assert ei.value.code == "INVALID_PAYLOAD"
    assert len(led.rows()) == n


def test_r1_08_score_requires_exclusion_counts(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=4)
    _publish(led, "f-mat", p=0.25)
    _publish(led, "f-cen", p=0.40)
    _publish(led, "f-unp", p=0.60)
    _publish(led, "f-pen", p=0.20)
    _resolve(led, "f-mat", MATURED, 0)
    _resolve(led, "f-cen", CENSORED, None)
    _resolve(led, "f-unp", UNPRICEABLE, None)
    assert brier(led, "fam-a") == 0.0625
    n = len(led.rows())
    missing = {
        "family_id": "fam-a",
        "baseline_id": "caller-frozen-baseline",
        "baseline_digest": DIGEST_B,
        "scored_forecast_ids": ["f-mat"],
        "brier": 0.0625,
        "baseline_brier": 0.25,
        "n": 1,
        "descriptive_only": True,
    }
    with pytest.raises(LedgerRefused) as ei:
        led.append(SCORE, missing)
    assert ei.value.code == "INVALID_PAYLOAD"
    assert len(led.rows()) == n
    row = led.append(SCORE, _score_payload(
        led,
        n_censored=1,
        n_unpriceable=1,
        n_pending=1,
        brier=0.0625,
    ))
    assert row["payload"]["brier"] == 0.0625
    assert brier(led, "fam-a") == 0.0625
    assert row["payload"]["n_censored"] == 1
    assert row["payload"]["n_unpriceable"] == 1
    assert row["payload"]["n_pending"] == 1


def test_r1_08_wrong_count_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=4)
    _publish(led, "f-mat", p=0.25)
    _publish(led, "f-cen", p=0.40)
    _publish(led, "f-unp", p=0.60)
    _publish(led, "f-pen", p=0.20)
    _resolve(led, "f-mat", MATURED, 0)
    _resolve(led, "f-cen", CENSORED, None)
    _resolve(led, "f-unp", UNPRICEABLE, None)
    n = len(led.rows())
    with pytest.raises(LedgerRefused) as ei:
        led.append(SCORE, _score_payload(led, n_censored=0, brier=0.0625))
    assert ei.value.code == "INVALID_PAYLOAD"
    assert len(led.rows()) == n


@pytest.mark.parametrize(
    "extra",
    [
        {"authority": {"rank_authority": True}},
        {"nested": {"trade_authority": True}},
        {"Rank_Authority": True},
        {"SIGNAL_AUTHORITY": 1},
        {"x": [{"gate_authority": "true"}]},
        {" size_authority ": True},
    ],
)
def test_r1_09_nested_authority_refused(tmp_path, extra):
    led = _led(tmp_path)
    _prep(led, n=4)
    reg_at = _reg_at(led)
    payload = {
        "forecast_id": "f-auth",
        "family_id": "fam-a",
        "p": 0.2,
        "inputs_digest": DIGEST,
        "published_at_utc": _shift(reg_at, 1),
        "horizon_end_utc": _shift(reg_at, 32),
    }
    payload.update(extra)
    with pytest.raises(LedgerRefused) as ei:
        led.append(PUBLISH, payload)
    assert ei.value.code == "AUTHORITY_FLAG_REFUSED"
    all_false = {
        "forecast_id": "f-ok",
        "family_id": "fam-a",
        "p": 0.2,
        "inputs_digest": DIGEST,
        "published_at_utc": _shift(reg_at, 1),
        "horizon_end_utc": _shift(reg_at, 32),
    }
    for key in AUTHORITY_KEYS:
        all_false[key] = False
    row = led.append(PUBLISH, all_false)
    assert row["payload"]["forecast_id"] == "f-ok"
    assert "f-ok" in led.state()["published"]


def test_r1_10_docstring_names_owners():
    doc = sni_eval_ledger.__doc__
    assert doc is not None
    for name in (
        "_append_rows",
        "log_declared_budget",
        "register",
        "grade_claim",
        "brier_decomposition",
    ):
        assert name in doc, name


def test_r1_11_budget_before_register_refused(tmp_path):
    led = _led(tmp_path)
    with pytest.raises(LedgerRefused) as ei:
        led.append(BUDGET, {"family_id": "fam-a", "declared_trials": 8})
    assert ei.value.code == "FAMILY_NOT_REGISTERED"
    assert led.rows() == []


def test_r1_12_written_at_tamper_detected(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=3)
    _publish(led, "f1", p=0.3)
    assert len(led.rows()) == 3
    path = led.path
    lines = path.read_text(encoding="utf-8").splitlines()
    row1 = json.loads(lines[0])
    row1["written_at_utc"] = "1999-01-01T00:00:00Z"
    lines[0] = json.dumps(row1, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    violations = EvalLedger(path).verify_chain()
    assert any(v == "ROW_HASH_MISMATCH:1" or v.startswith("ROW_HASH_MISMATCH:1") for v in violations)


def test_r1_15_naive_timestamp_refused(tmp_path):
    led = _led(tmp_path)
    _prep(led, n=2)
    n = len(led.rows())
    with pytest.raises(LedgerRefused) as ei:
        _publish(led, "f1", p=0.25, published_at_utc="2020-01-01T00:00:00")
    assert ei.value.code == "INVALID_PAYLOAD"
    assert len(led.rows()) == n


def test_r1_15_draft_registered_false():
    doc = DOC.read_text(encoding="utf-8")
    assert "registered: false" in doc
    assert REGISTERED is False
    assert sni_eval_ledger.REGISTERED is False
