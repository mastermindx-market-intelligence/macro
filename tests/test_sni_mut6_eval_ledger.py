"""Mutation-targeted tests for M6E survivors in sni_eval_ledger.py.

Each test in this file pins a specific mutation that survived the existing
sni_eval_ledger importer suite. The docstring names the file:line, the
original token, and the mutated token. The test re-applies the mutation in
place during verification (not committed here) and asserts the named refusal
code is raised on the unmutated module.

Authority flags stay false; identity ids remain caller-supplied opaque
strings. Fixtures are synthetic.
"""
from __future__ import annotations

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
    BUDGET,
    CENSORED,
    MATURED,
    NOGO,
    PUBLISH,
    REGISTER,
    RESOLVE,
    SCORE,
    UNPRICEABLE,
    EvalLedger,
    LedgerRefused,
    brier,
)

DIGEST = "a" * 64
DIGEST_B = "b" * 64


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
    import datetime as _dt
    dt = _dt.datetime.fromisoformat(raw) + _dt.timedelta(days=days)
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


def _resolve(led, forecast_id, state, outcome, observed_at_utc=None):
    if observed_at_utc is None:
        observed_at_utc = "2020-02-02T00:00:00Z"
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


# --------------------------------------------------------------------------
# M6E-OA_validate_score-009
# sni_eval_ledger.py:660, `or` -> `and` in
#   `if not isinstance(ids, list) or any(not _is_nonempty_str(i) for i in ids):`
# --------------------------------------------------------------------------
def test_m6e_validate_score_or_and_nonstring_item_refused(tmp_path):
    """sni_eval_ledger.py:660, `or` -> `and` (_validate_score element check).

    The mutation collapses the disjunction to a conjunction: the gate only
    refuses when `ids` is NOT a list AND any item in `ids` is not a non-empty
    string. With ``scored_forecast_ids = [123]`` the first clause is False
    and the second is True. The original `or` refuses with
    INVALID_PAYLOAD "scored_forecast_ids"; the `and` mutant passes through
    and is caught later at N_MISMATCH.
    """
    led = _led(tmp_path)
    _reg(led)
    _budget(led, n=2)
    _publish(led, "f1", p=0.25)
    _resolve(led, "f1", MATURED, 0)
    payload = _score_payload(led, scored_forecast_ids=[123])
    n_rows = len(led.rows())
    with pytest.raises(LedgerRefused) as ei:
        led.append(SCORE, payload)
    assert ei.value.code == "INVALID_PAYLOAD"
    assert ei.value.detail == "scored_forecast_ids"
    assert len(led.rows()) == n_rows
    assert led.state()["scores"] == []


# --------------------------------------------------------------------------
# Companion: a non-list payload with one non-empty-string item must still
# refuse with INVALID_PAYLOAD "scored_forecast_ids".  This pins the first
# clause of the disjunction and would have caught a deletion-of-not-typeof
# guard as well.
# --------------------------------------------------------------------------
def test_m6e_validate_score_non_list_scored_ids_refused(tmp_path):
    """Companion: covers the first clause of the line 660 disjunction.

    ``scored_forecast_ids`` is a string (not a list) so the first clause
    ``not isinstance(ids, list)`` is True. The original `or` refuses with
    INVALID_PAYLOAD "scored_forecast_ids". The `and` mutant would refuse
    only if iterating the string encountered a non-empty-string item —
    which it would (every char is a non-empty string); so the `and` mutant
    also refuses here. This test primarily pins the first clause so any
    future deletion of `not isinstance(ids, list)` is caught.
    """
    led = _led(tmp_path)
    _reg(led)
    _budget(led, n=2)
    _publish(led, "f1", p=0.25)
    _resolve(led, "f1", MATURED, 0)
    payload = _score_payload(led, scored_forecast_ids="not-a-list")
    n_rows = len(led.rows())
    with pytest.raises(LedgerRefused) as ei:
        led.append(SCORE, payload)
    assert ei.value.code == "INVALID_PAYLOAD"
    assert ei.value.detail == "scored_forecast_ids"
    assert len(led.rows()) == n_rows
    assert led.state()["scores"] == []