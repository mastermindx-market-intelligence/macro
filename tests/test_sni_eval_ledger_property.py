"""Model-based seeded property tests for the SNI evaluation ledger draft.

Evidence only (commission 8659, A26-A30). The ledger is an R1-gated
unregistered DRAFT. This file does not register anything, does not write
a ledger outside pytest tmp_path, and does not claim forecast support.

The reference model below is independent: it does not import any private
helper (_fold, _validate_*, _reg_key, _row_hash, ...) from
sni_eval_ledger. Expected refusal codes are taken from
REGISTRATION_LEDGER_DRAFT.md. Family/forecast/baseline ids are opaque
caller-supplied strings; none are canonical issuer or security ids.

Authority flags stay false on every accepted payload. A payload that
carries an authority-like key set other than literal False is a
refusal case (AUTHORITY_FLAG_REFUSED).
"""
from __future__ import annotations

import datetime
import json
import math
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/evaluation"),
)

from sni_eval_ledger import (  # noqa: E402
    EvalLedger,
    LedgerRefused,
    brier,
    replay,
)

SEEDS = range(300)

REGISTER = "REGISTER"
BUDGET = "BUDGET"
PUBLISH = "PUBLISH"
ABSTAIN = "ABSTAIN"
RESOLVE = "RESOLVE"
SCORE = "SCORE"
NOGO = "NOGO"

PENDING = "PENDING"
UNPRICEABLE = "UNPRICEABLE"
CENSORED = "CENSORED"
MATURED = "MATURED"

ROW_KINDS = (REGISTER, BUDGET, PUBLISH, ABSTAIN, RESOLVE, SCORE, NOGO)
TERMINAL_STATES = (UNPRICEABLE, CENSORED, MATURED)
FOUR_STATES = (PENDING, UNPRICEABLE, CENSORED, MATURED)

AUTHORITY_KEYS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)
_AUTHORITY_FOLDED = frozenset(k.casefold() for k in AUTHORITY_KEYS)

_HEX = "0123456789abcdef"
DIGEST = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64

FAMILIES = ("fam-a", "fam-b", "fam-c")
PROTOCOLS = ("sni.v0", "sni.v1")
VERSIONS = ("1", "2")
SPLITS = ("test", "holdout")
HS = (21, 63, 5)
FIDS = tuple("f%d" % i for i in range(12))

# Perturbation used by lgp_08: larger than the SCORE gate (1e-12) and
# larger than 1e-9, smaller than a 1e-3 mutant tolerance.
BRIER_PERTURB = 1e-8


# ---------------------------------------------------------------------------
# Independent reference model (spec/doc, not private module helpers)
# ---------------------------------------------------------------------------

def _is_hex64(value):
    return isinstance(value, str) and len(value) == 64 and all(c in _HEX for c in value)


def _is_nonempty_str(value):
    return isinstance(value, str) and value != ""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_finite_number(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _parse_utc(value, field):
    if not isinstance(value, str) or value == "":
        return "INVALID_PAYLOAD"
    raw = value
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(raw)
    except ValueError:
        return "INVALID_PAYLOAD"
    if dt.tzinfo is None:
        return "INVALID_PAYLOAD"
    return dt


def _shift(ts, days):
    raw = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
    dt = datetime.datetime.fromisoformat(raw) + datetime.timedelta(days=days)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _check_authority(obj):
    """Spec: nested dicts, list elements, case/whitespace variants."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and key.strip().casefold() in _AUTHORITY_FOLDED:
                if value is not False:
                    return "AUTHORITY_FLAG_REFUSED"
            code = _check_authority(value)
            if code:
                return code
    elif isinstance(obj, list):
        for item in obj:
            code = _check_authority(item)
            if code:
                return code
    return None


def _reg_key_from_payload(payload):
    return (
        payload.get("family_id"),
        payload.get("protocol"),
        payload.get("version"),
        payload.get("split"),
        payload.get("h"),
    )


class ReferenceModel:
    """Plain-dict reference for the evaluation ledger draft.

    Tracks registered keys, family budgets, publications (id -> p),
    resolutions (id -> state/outcome), and nogo families. Refusal codes
    come from REGISTRATION_LEDGER_DRAFT.md, applied in the documented
    gate order (authority, then kind-specific required fields / named
    codes).
    """

    def __init__(self):
        self.registered = {}
        self.registered_at = {}
        self.budgets = {}
        self.published = {}
        self.abstained = {}
        self.resolved = {}
        self.nogo = set()
        self.scores = []

    def registered_count(self):
        return len(self.registered)

    def _family_registered(self, family_id):
        for key in self.registered:
            if key[0] == family_id:
                return True
        return False

    def matured_ids(self, family_id):
        ids = []
        for fid, pub in self.published.items():
            if pub["family_id"] != family_id:
                continue
            res = self.resolved.get(fid)
            if res is not None and res["state"] == MATURED:
                ids.append(fid)
        ids.sort()
        return ids

    def exclusion_counts(self, family_id):
        n_censored = n_unpriceable = n_pending = 0
        for fid, pub in self.published.items():
            if pub["family_id"] != family_id:
                continue
            res = self.resolved.get(fid)
            if res is None:
                n_pending += 1
            elif res["state"] == CENSORED:
                n_censored += 1
            elif res["state"] == UNPRICEABLE:
                n_unpriceable += 1
        return n_censored, n_unpriceable, n_pending

    def model_brier(self, family_id):
        pairs = []
        for fid in sorted(self.published):
            pub = self.published[fid]
            if pub["family_id"] != family_id:
                continue
            res = self.resolved.get(fid)
            if res is None or res["state"] != MATURED:
                continue
            pairs.append((float(pub["p"]), float(res["outcome"])))
        if not pairs:
            return None
        squares = [(p - o) ** 2 for p, o in pairs]
        return math.fsum(squares) / len(squares)

    def predict(self, op):
        kind = op["kind"]
        payload = op["payload"]
        if kind not in ROW_KINDS:
            return ("refuse", "UNKNOWN_KIND")
        if not isinstance(payload, dict):
            return ("refuse", "INVALID_PAYLOAD")
        auth = _check_authority(payload)
        if auth:
            return ("refuse", auth)
        if kind == REGISTER:
            return self._predict_register(payload)
        if kind == BUDGET:
            return self._predict_budget(payload)
        if kind == PUBLISH:
            return self._predict_publish(payload)
        if kind == ABSTAIN:
            return self._predict_abstain(payload)
        if kind == RESOLVE:
            return self._predict_resolve(payload)
        if kind == SCORE:
            return self._predict_score(payload)
        if kind == NOGO:
            return self._predict_nogo(payload)
        return ("refuse", "UNKNOWN_KIND")

    def _require(self, payload, keys):
        for key in keys:
            if key not in payload:
                return "INVALID_PAYLOAD"
        return None

    def _predict_register(self, payload):
        miss = self._require(
            payload, ("family_id", "protocol", "version", "split", "h", "prereg_digest")
        )
        if miss:
            return ("refuse", miss)
        for field in ("family_id", "protocol", "version", "split"):
            if not _is_nonempty_str(payload[field]):
                return ("refuse", "INVALID_PAYLOAD")
        if not _is_int(payload["h"]):
            return ("refuse", "INVALID_PAYLOAD")
        if not _is_hex64(payload["prereg_digest"]):
            return ("refuse", "INVALID_PREREG_DIGEST")
        key = _reg_key_from_payload(payload)
        if key in self.registered:
            return ("refuse", "ALREADY_REGISTERED")
        return ("ok", None)

    def _predict_budget(self, payload):
        miss = self._require(payload, ("family_id", "declared_trials"))
        if miss:
            return ("refuse", miss)
        family_id = payload["family_id"]
        if not _is_nonempty_str(family_id):
            return ("refuse", "INVALID_PAYLOAD")
        if not self._family_registered(family_id):
            return ("refuse", "FAMILY_NOT_REGISTERED")
        if family_id in self.budgets:
            return ("refuse", "DUPLICATE_BUDGET")
        n = payload["declared_trials"]
        if not _is_int(n) or n <= 0:
            return ("refuse", "INVALID_DECLARED_TRIALS")
        return ("ok", None)

    def _predict_publish(self, payload):
        miss = self._require(
            payload,
            (
                "forecast_id",
                "family_id",
                "p",
                "inputs_digest",
                "published_at_utc",
                "horizon_end_utc",
            ),
        )
        if miss:
            return ("refuse", miss)
        forecast_id = payload["forecast_id"]
        family_id = payload["family_id"]
        if not _is_nonempty_str(forecast_id):
            return ("refuse", "INVALID_PAYLOAD")
        if not _is_nonempty_str(family_id):
            return ("refuse", "INVALID_PAYLOAD")
        if not self._family_registered(family_id):
            return ("refuse", "FAMILY_NOT_REGISTERED")
        if family_id in self.nogo:
            return ("refuse", "FAMILY_NOGO")
        if forecast_id in self.published:
            return ("refuse", "IMMUTABLE_PUBLICATION")
        if forecast_id in self.abstained:
            return ("refuse", "ALREADY_ABSTAINED")
        if family_id not in self.budgets:
            return ("refuse", "BUDGET_REQUIRED")
        budget = self.budgets[family_id]
        if budget["used_trials"] + 1 > budget["declared_trials"]:
            return ("refuse", "BUDGET_EXCEEDED")
        if not _is_hex64(payload["inputs_digest"]):
            return ("refuse", "INVALID_INPUTS_DIGEST")
        published_at = _parse_utc(payload["published_at_utc"], "published_at_utc")
        if published_at == "INVALID_PAYLOAD":
            return ("refuse", "INVALID_PAYLOAD")
        horizon_end = _parse_utc(payload["horizon_end_utc"], "horizon_end_utc")
        if horizon_end == "INVALID_PAYLOAD":
            return ("refuse", "INVALID_PAYLOAD")
        reg_at = _parse_utc(self.registered_at[family_id], "written_at_utc")
        if reg_at == "INVALID_PAYLOAD":
            return ("refuse", "INVALID_PAYLOAD")
        if published_at < reg_at:
            return ("refuse", "PUBLISH_BEFORE_REGISTER")
        if horizon_end < published_at:
            return ("refuse", "HORIZON_BEFORE_PUBLISH")
        p = payload["p"]
        if isinstance(p, bool) or not isinstance(p, (int, float)):
            return ("refuse", "INVALID_P")
        p = float(p)
        if math.isnan(p) or math.isinf(p) or not (0.0 < p < 1.0):
            return ("refuse", "INVALID_P")
        reason = payload.get("declared_reason")
        if p == 0.5:
            if not _is_nonempty_str(reason):
                return ("refuse", "DEFAULT_PROBABILITY_REFUSED")
        return ("ok", None)

    def _predict_abstain(self, payload):
        miss = self._require(payload, ("forecast_id", "family_id", "reason"))
        if miss:
            return ("refuse", miss)
        forecast_id = payload["forecast_id"]
        family_id = payload["family_id"]
        if not _is_nonempty_str(forecast_id):
            return ("refuse", "INVALID_PAYLOAD")
        if not _is_nonempty_str(family_id):
            return ("refuse", "INVALID_PAYLOAD")
        if not _is_nonempty_str(payload["reason"]):
            return ("refuse", "EMPTY_REASON")
        if not self._family_registered(family_id):
            return ("refuse", "FAMILY_NOT_REGISTERED")
        if family_id in self.nogo:
            return ("refuse", "FAMILY_NOGO")
        if forecast_id in self.published:
            return ("refuse", "ALREADY_PUBLISHED")
        if forecast_id in self.abstained:
            return ("refuse", "ALREADY_ABSTAINED")
        if family_id not in self.budgets:
            return ("refuse", "BUDGET_REQUIRED")
        budget = self.budgets[family_id]
        if budget["used_trials"] + 1 > budget["declared_trials"]:
            return ("refuse", "BUDGET_EXCEEDED")
        return ("ok", None)

    def _predict_resolve(self, payload):
        miss = self._require(payload, ("forecast_id", "state", "observed_at_utc", "outcome"))
        if miss:
            return ("refuse", miss)
        forecast_id = payload["forecast_id"]
        if not _is_nonempty_str(forecast_id):
            return ("refuse", "INVALID_PAYLOAD")
        if forecast_id in self.resolved:
            return ("refuse", "ALREADY_RESOLVED")
        if forecast_id not in self.published:
            return ("refuse", "UNKNOWN_FORECAST")
        if forecast_id in self.abstained:
            return ("refuse", "NOT_PENDING")
        resolve_state = payload["state"]
        if resolve_state not in TERMINAL_STATES:
            return ("refuse", "INVALID_RESOLVE_STATE")
        outcome = payload["outcome"]
        observed = _parse_utc(payload["observed_at_utc"], "observed_at_utc")
        if observed == "INVALID_PAYLOAD":
            return ("refuse", "INVALID_PAYLOAD")
        pub = self.published[forecast_id]
        horizon_end = _parse_utc(pub["horizon_end_utc"], "horizon_end_utc")
        published_at = _parse_utc(pub["published_at_utc"], "published_at_utc")
        if horizon_end == "INVALID_PAYLOAD" or published_at == "INVALID_PAYLOAD":
            return ("refuse", "INVALID_PAYLOAD")
        family_id = pub["family_id"]
        reg_at = _parse_utc(self.registered_at[family_id], "written_at_utc")
        if reg_at == "INVALID_PAYLOAD":
            return ("refuse", "INVALID_PAYLOAD")
        if resolve_state == MATURED:
            if (
                outcome is True
                or outcome is False
                or not _is_int(outcome)
                or outcome not in (0, 1)
            ):
                return ("refuse", "MATURED_OUTCOME_REQUIRED")
            if observed < published_at or observed < reg_at:
                return ("refuse", "OUTCOME_BEFORE_REGISTER")
            if observed < horizon_end:
                return ("refuse", "HORIZON_NOT_REACHED")
        else:
            if outcome is not None:
                return ("refuse", "OUTCOME_FORBIDDEN")
        return ("ok", None)

    def _predict_score(self, payload):
        miss = self._require(
            payload,
            (
                "family_id",
                "baseline_id",
                "baseline_digest",
                "scored_forecast_ids",
                "brier",
                "baseline_brier",
                "n",
                "n_censored",
                "n_unpriceable",
                "n_pending",
                "descriptive_only",
            ),
        )
        if miss:
            return ("refuse", miss)
        family_id = payload["family_id"]
        if not _is_nonempty_str(family_id):
            return ("refuse", "INVALID_PAYLOAD")
        if not self._family_registered(family_id):
            return ("refuse", "FAMILY_NOT_REGISTERED")
        if not _is_nonempty_str(payload["baseline_id"]):
            return ("refuse", "INVALID_PAYLOAD")
        if not _is_hex64(payload["baseline_digest"]):
            return ("refuse", "INVALID_BASELINE_DIGEST")
        if payload.get("descriptive_only") is not True:
            return ("refuse", "DESCRIPTIVE_ONLY_REQUIRED")
        ids = payload["scored_forecast_ids"]
        if not isinstance(ids, list) or any(not _is_nonempty_str(i) for i in ids):
            return ("refuse", "INVALID_PAYLOAD")
        if ids != sorted(ids):
            return ("refuse", "SCORED_IDS_UNSORTED")
        if len(ids) != len(set(ids)):
            return ("refuse", "INVALID_PAYLOAD")
        n = payload["n"]
        if not _is_int(n):
            return ("refuse", "INVALID_PAYLOAD")
        for key in ("n_censored", "n_unpriceable", "n_pending"):
            if not _is_int(payload[key]):
                return ("refuse", "INVALID_PAYLOAD")
        n_censored, n_unpriceable, n_pending = self.exclusion_counts(family_id)
        if (
            payload["n_censored"] != n_censored
            or payload["n_unpriceable"] != n_unpriceable
            or payload["n_pending"] != n_pending
        ):
            return ("refuse", "INVALID_PAYLOAD")
        matured = self.matured_ids(family_id)
        if not matured:
            return ("refuse", "NO_MATURED_FORECASTS")
        for fid in ids:
            pub = self.published.get(fid)
            if pub is None or pub["family_id"] != family_id:
                return ("refuse", "NOT_MATURED")
            res = self.resolved.get(fid)
            if res is None or res["state"] != MATURED:
                return ("refuse", "NOT_MATURED")
        if n != len(ids) or n != len(matured) or ids != matured:
            return ("refuse", "N_MISMATCH")
        reported = payload["brier"]
        if not _is_finite_number(reported):
            return ("refuse", "INVALID_PAYLOAD")
        baseline_brier = payload["baseline_brier"]
        if not _is_finite_number(baseline_brier):
            return ("refuse", "INVALID_PAYLOAD")
        recomputed = self.model_brier(family_id)
        if recomputed is None:
            return ("refuse", "NO_MATURED_FORECASTS")
        if abs(float(reported) - recomputed) > 1e-12:
            return ("refuse", "BRIER_MISMATCH")
        return ("ok", None)

    def _predict_nogo(self, payload):
        miss = self._require(payload, ("family_id", "reason"))
        if miss:
            return ("refuse", miss)
        family_id = payload["family_id"]
        if not _is_nonempty_str(family_id):
            return ("refuse", "INVALID_PAYLOAD")
        if not _is_nonempty_str(payload["reason"]):
            return ("refuse", "EMPTY_REASON")
        if not self._family_registered(family_id):
            return ("refuse", "FAMILY_NOT_REGISTERED")
        if family_id in self.nogo:
            return ("refuse", "ALREADY_NOGO")
        return ("ok", None)

    def apply(self, op, written_at_utc):
        kind = op["kind"]
        payload = op["payload"]
        if kind == REGISTER:
            key = _reg_key_from_payload(payload)
            self.registered[key] = payload["prereg_digest"]
            family_id = payload["family_id"]
            if family_id not in self.registered_at:
                self.registered_at[family_id] = written_at_utc
        elif kind == BUDGET:
            self.budgets[payload["family_id"]] = {
                "declared_trials": payload["declared_trials"],
                "used_trials": 0,
            }
        elif kind == PUBLISH:
            fid = payload["forecast_id"]
            self.published[fid] = {
                "p": payload["p"],
                "family_id": payload["family_id"],
                "published_at_utc": payload["published_at_utc"],
                "horizon_end_utc": payload["horizon_end_utc"],
                "inputs_digest": payload["inputs_digest"],
            }
            family_id = payload["family_id"]
            if family_id in self.budgets:
                self.budgets[family_id]["used_trials"] += 1
        elif kind == ABSTAIN:
            fid = payload["forecast_id"]
            self.abstained[fid] = {"family_id": payload["family_id"]}
            family_id = payload["family_id"]
            if family_id in self.budgets:
                self.budgets[family_id]["used_trials"] += 1
        elif kind == RESOLVE:
            self.resolved[payload["forecast_id"]] = {
                "state": payload["state"],
                "outcome": payload["outcome"],
            }
        elif kind == SCORE:
            self.scores.append(dict(payload))
        elif kind == NOGO:
            self.nogo.add(payload["family_id"])


# ---------------------------------------------------------------------------
# Operation generator
# ---------------------------------------------------------------------------

SCENARIOS = (
    "register_new",
    "register_dup",
    "register_changed_key",
    "register_bad_digest",
    "budget_ok",
    "budget_dup",
    "budget_before_reg",
    "budget_bad_n",
    "publish_ok",
    "publish_dup_same_p",
    "publish_dup_diff_p",
    "publish_p_half",
    "publish_p_half_reason",
    "publish_invalid_p",
    "publish_before_budget",
    "publish_early_ts",
    "publish_horizon_before",
    "publish_abstained_id",
    "abstain_ok",
    "abstain_empty",
    "abstain_published",
    "abstain_dup",
    "resolve_matured",
    "resolve_matured_no_outcome",
    "resolve_censored",
    "resolve_censored_outcome",
    "resolve_unpriceable",
    "resolve_unpriceable_outcome",
    "resolve_early",
    "resolve_unknown",
    "resolve_dup",
    "resolve_bad_state",
    "resolve_outcome_before_reg",
    "score_ok",
    "score_bad_brier",
    "score_non_matured",
    "score_unsorted",
    "score_not_descriptive",
    "score_no_matured",
    "nogo_ok",
    "nogo_dup",
    "nogo_empty",
    "authority",
    "unknown_kind",
    "missing_keys",
)


def _free_fid(model, rng):
    unused = [fid for fid in FIDS if fid not in model.published and fid not in model.abstained]
    if unused:
        return rng.choice(unused)
    return "f%d" % rng.randint(100, 999)


def _pending_ids(model):
    return [fid for fid in model.published if fid not in model.resolved]


def _family_with_budget_room(model):
    out = []
    for fam, bud in model.budgets.items():
        if fam in model.nogo:
            continue
        if bud["used_trials"] < bud["declared_trials"] and model._family_registered(fam):
            out.append(fam)
    return out


def _publish_times(model, family_id, rng, mode="ok"):
    reg_at = model.registered_at.get(family_id, "2026-01-01T00:00:00Z")
    if mode == "early":
        published_at = _shift(reg_at, -rng.randint(1, 5))
        horizon_end = _shift(published_at, rng.randint(1, 10))
    elif mode == "horizon_before":
        published_at = _shift(reg_at, rng.randint(1, 5))
        horizon_end = _shift(published_at, -rng.randint(1, 5))
    else:
        published_at = _shift(reg_at, rng.randint(0, 3))
        horizon_end = _shift(published_at, rng.randint(0, 40))
    return published_at, horizon_end


def _register_payload(rng, family_id=None, **overrides):
    payload = {
        "family_id": family_id if family_id is not None else rng.choice(FAMILIES),
        "protocol": rng.choice(PROTOCOLS),
        "version": rng.choice(VERSIONS),
        "split": rng.choice(SPLITS),
        "h": rng.choice(HS),
        "prereg_digest": rng.choice((DIGEST, DIGEST_B, DIGEST_C)),
    }
    payload.update(overrides)
    return payload


def _valid_score_payload(model, family_id):
    matured = model.matured_ids(family_id)
    n_censored, n_unpriceable, n_pending = model.exclusion_counts(family_id)
    computed = model.model_brier(family_id)
    return {
        "family_id": family_id,
        "baseline_id": "caller-frozen-baseline",
        "baseline_digest": DIGEST_B,
        "scored_forecast_ids": list(matured),
        "brier": 0.0 if computed is None else computed,
        "baseline_brier": 0.25,
        "n": len(matured),
        "n_censored": n_censored,
        "n_unpriceable": n_unpriceable,
        "n_pending": n_pending,
        "descriptive_only": True,
    }


def _inject_authority(payload, rng):
    key = rng.choice(AUTHORITY_KEYS)
    style = rng.choice(("top", "nested", "list", "case", "space", "upper"))
    value = rng.choice((True, 1, "true"))
    if style == "top":
        payload[key] = value
    elif style == "nested":
        payload["nested"] = {key: value}
    elif style == "list":
        payload["x"] = [{key: value}]
    elif style == "case":
        payload[key.title()] = value
    elif style == "space":
        payload[" " + key + " "] = value
    else:
        payload[key.upper()] = value
    return payload


def emit_op(rng, model, step, n_steps):
    """Emit one random op, biased toward a valid family lifecycle."""
    if step == 0:
        return {"kind": REGISTER, "payload": _register_payload(rng, family_id="fam-a",
                                                              protocol="sni.v0", version="1",
                                                              split="test", h=21,
                                                              prereg_digest=DIGEST)}
    if step == 1:
        return {"kind": BUDGET, "payload": {"family_id": "fam-a", "declared_trials": 12}}
    if step == 2 and rng.random() < 0.7:
        return {"kind": REGISTER, "payload": _register_payload(rng, family_id="fam-b",
                                                              protocol="sni.v0", version="1",
                                                              split="test", h=21,
                                                              prereg_digest=DIGEST_B)}
    if step == 3 and "fam-b" in model.registered_at and rng.random() < 0.8:
        return {"kind": BUDGET, "payload": {"family_id": "fam-b", "declared_trials": 8}}

    # Near the end of a sequence, bias toward resolve/score/nogo so
    # A28-A30 properties actually see terminal states.
    if step > n_steps * 0.55 and _pending_ids(model) and rng.random() < 0.35:
        scenario = rng.choice(
            ("resolve_matured", "resolve_censored", "resolve_unpriceable",
             "resolve_censored_outcome", "score_ok", "score_bad_brier", "nogo_ok")
        )
    else:
        scenario = rng.choice(SCENARIOS)
    return _emit_scenario(rng, model, scenario)


def _emit_scenario(rng, model, scenario):
    registered_fams = [k[0] for k in model.registered]
    fam = rng.choice(registered_fams) if registered_fams else rng.choice(FAMILIES)

    if scenario == "register_new":
        payload = _register_payload(rng)
        return {"kind": REGISTER, "payload": payload}
    if scenario == "register_dup":
        if model.registered:
            key = rng.choice(list(model.registered.keys()))
            payload = {
                "family_id": key[0],
                "protocol": key[1],
                "version": key[2],
                "split": key[3],
                "h": key[4],
                "prereg_digest": model.registered[key],
            }
            return {"kind": REGISTER, "payload": payload}
        return {"kind": REGISTER, "payload": _register_payload(rng)}
    if scenario == "register_changed_key":
        if model.registered:
            key = rng.choice(list(model.registered.keys()))
            field = rng.choice(("protocol", "version", "split", "h"))
            payload = {
                "family_id": key[0],
                "protocol": key[1],
                "version": key[2],
                "split": key[3],
                "h": key[4],
                "prereg_digest": DIGEST_C,
            }
            if field == "protocol":
                payload["protocol"] = "sni.changed"
            elif field == "version":
                payload["version"] = "changed"
            elif field == "split":
                payload["split"] = "changed"
            else:
                payload["h"] = key[4] + 1
            return {"kind": REGISTER, "payload": payload}
        return {"kind": REGISTER, "payload": _register_payload(rng, h=99)}
    if scenario == "register_bad_digest":
        payload = _register_payload(rng, prereg_digest=rng.choice(
            ("ZZ" + "a" * 62, "a" * 63, "a" * 65, "", "A" * 64)
        ))
        return {"kind": REGISTER, "payload": payload}

    if scenario == "budget_ok":
        candidates = [f for f in set(registered_fams) if f not in model.budgets]
        if candidates:
            return {"kind": BUDGET, "payload": {
                "family_id": rng.choice(candidates),
                "declared_trials": rng.choice((1, 2, 4, 8, 12)),
            }}
        return {"kind": BUDGET, "payload": {
            "family_id": fam, "declared_trials": rng.choice((4, 8)),
        }}
    if scenario == "budget_dup":
        if model.budgets:
            fam = rng.choice(list(model.budgets))
        return {"kind": BUDGET, "payload": {"family_id": fam, "declared_trials": 4}}
    if scenario == "budget_before_reg":
        return {"kind": BUDGET, "payload": {
            "family_id": "fam-unregistered", "declared_trials": 4,
        }}
    if scenario == "budget_bad_n":
        n = rng.choice((0, -1, 1.5, True, "8"))
        return {"kind": BUDGET, "payload": {"family_id": fam, "declared_trials": n}}

    if scenario.startswith("publish") or scenario.startswith("abstain") or scenario.startswith("resolve") or scenario.startswith("score") or scenario.startswith("nogo"):
        pass

    if scenario == "publish_ok":
        room = _family_with_budget_room(model)
        family_id = rng.choice(room) if room else fam
        published_at, horizon_end = _publish_times(model, family_id, rng, "ok")
        p = rng.choice((0.1, 0.2, 0.25, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9))
        return {"kind": PUBLISH, "payload": {
            "forecast_id": _free_fid(model, rng),
            "family_id": family_id,
            "p": p,
            "inputs_digest": DIGEST,
            "published_at_utc": published_at,
            "horizon_end_utc": horizon_end,
        }}
    if scenario in ("publish_dup_same_p", "publish_dup_diff_p"):
        if model.published:
            fid = rng.choice(list(model.published))
            pub = model.published[fid]
            p = pub["p"] if scenario == "publish_dup_same_p" else (0.11 if pub["p"] != 0.11 else 0.22)
            return {"kind": PUBLISH, "payload": {
                "forecast_id": fid,
                "family_id": pub["family_id"],
                "p": p,
                "inputs_digest": DIGEST,
                "published_at_utc": pub["published_at_utc"],
                "horizon_end_utc": pub["horizon_end_utc"],
            }}
        return _emit_scenario(rng, model, "publish_ok")
    if scenario == "publish_p_half":
        room = _family_with_budget_room(model)
        family_id = rng.choice(room) if room else fam
        published_at, horizon_end = _publish_times(model, family_id, rng, "ok")
        return {"kind": PUBLISH, "payload": {
            "forecast_id": _free_fid(model, rng),
            "family_id": family_id,
            "p": 0.5,
            "inputs_digest": DIGEST,
            "published_at_utc": published_at,
            "horizon_end_utc": horizon_end,
        }}
    if scenario == "publish_p_half_reason":
        room = _family_with_budget_room(model)
        family_id = rng.choice(room) if room else fam
        published_at, horizon_end = _publish_times(model, family_id, rng, "ok")
        return {"kind": PUBLISH, "payload": {
            "forecast_id": _free_fid(model, rng),
            "family_id": family_id,
            "p": 0.5,
            "inputs_digest": DIGEST,
            "published_at_utc": published_at,
            "horizon_end_utc": horizon_end,
            "declared_reason": "named-uninformative-prior",
        }}
    if scenario == "publish_invalid_p":
        room = _family_with_budget_room(model)
        family_id = rng.choice(room) if room else fam
        published_at, horizon_end = _publish_times(model, family_id, rng, "ok")
        p = rng.choice((
            float("nan"), float("inf"), float("-inf"),
            -0.1, 0.0, 1.0, 1.5, True, False, "0.2", None,
        ))
        return {"kind": PUBLISH, "payload": {
            "forecast_id": _free_fid(model, rng),
            "family_id": family_id,
            "p": p,
            "inputs_digest": DIGEST,
            "published_at_utc": published_at,
            "horizon_end_utc": horizon_end,
        }}
    if scenario == "publish_before_budget":
        unbudgeted = [f for f in set(registered_fams) if f not in model.budgets]
        family_id = rng.choice(unbudgeted) if unbudgeted else "fam-a"
        published_at, horizon_end = _publish_times(model, family_id, rng, "ok")
        return {"kind": PUBLISH, "payload": {
            "forecast_id": _free_fid(model, rng),
            "family_id": family_id,
            "p": 0.3,
            "inputs_digest": DIGEST,
            "published_at_utc": published_at,
            "horizon_end_utc": horizon_end,
        }}
    if scenario == "publish_early_ts":
        family_id = fam
        published_at, horizon_end = _publish_times(model, family_id, rng, "early")
        return {"kind": PUBLISH, "payload": {
            "forecast_id": _free_fid(model, rng),
            "family_id": family_id,
            "p": 0.3,
            "inputs_digest": DIGEST,
            "published_at_utc": published_at,
            "horizon_end_utc": horizon_end,
        }}
    if scenario == "publish_horizon_before":
        family_id = fam
        published_at, horizon_end = _publish_times(model, family_id, rng, "horizon_before")
        return {"kind": PUBLISH, "payload": {
            "forecast_id": _free_fid(model, rng),
            "family_id": family_id,
            "p": 0.3,
            "inputs_digest": DIGEST,
            "published_at_utc": published_at,
            "horizon_end_utc": horizon_end,
        }}
    if scenario == "publish_abstained_id":
        if model.abstained:
            fid = rng.choice(list(model.abstained))
            family_id = model.abstained[fid]["family_id"]
            published_at, horizon_end = _publish_times(model, family_id, rng, "ok")
            return {"kind": PUBLISH, "payload": {
                "forecast_id": fid,
                "family_id": family_id,
                "p": 0.3,
                "inputs_digest": DIGEST,
                "published_at_utc": published_at,
                "horizon_end_utc": horizon_end,
            }}
        return _emit_scenario(rng, model, "abstain_ok")

    if scenario == "abstain_ok":
        room = _family_with_budget_room(model)
        family_id = rng.choice(room) if room else fam
        return {"kind": ABSTAIN, "payload": {
            "forecast_id": _free_fid(model, rng),
            "family_id": family_id,
            "reason": "unestimable-coverage",
        }}
    if scenario == "abstain_empty":
        return {"kind": ABSTAIN, "payload": {
            "forecast_id": _free_fid(model, rng),
            "family_id": fam,
            "reason": "",
        }}
    if scenario == "abstain_published":
        if model.published:
            fid = rng.choice(list(model.published))
            return {"kind": ABSTAIN, "payload": {
                "forecast_id": fid,
                "family_id": model.published[fid]["family_id"],
                "reason": "after-publish",
            }}
        return _emit_scenario(rng, model, "abstain_ok")
    if scenario == "abstain_dup":
        if model.abstained:
            fid = rng.choice(list(model.abstained))
            return {"kind": ABSTAIN, "payload": {
                "forecast_id": fid,
                "family_id": model.abstained[fid]["family_id"],
                "reason": "again",
            }}
        return _emit_scenario(rng, model, "abstain_ok")

    if scenario.startswith("resolve"):
        pending = _pending_ids(model)
        if scenario == "resolve_unknown":
            return {"kind": RESOLVE, "payload": {
                "forecast_id": "f-unknown",
                "state": MATURED,
                "observed_at_utc": "2026-12-01T00:00:00Z",
                "outcome": 1,
            }}
        if scenario == "resolve_dup" and model.resolved:
            fid = rng.choice(list(model.resolved))
            return {"kind": RESOLVE, "payload": {
                "forecast_id": fid,
                "state": MATURED,
                "observed_at_utc": "2026-12-01T00:00:00Z",
                "outcome": 1,
            }}
        if scenario == "resolve_bad_state":
            fid = pending[0] if pending else "f-none"
            return {"kind": RESOLVE, "payload": {
                "forecast_id": fid,
                "state": rng.choice((PENDING, "FOO", "matured", "")),
                "observed_at_utc": "2026-12-01T00:00:00Z",
                "outcome": None,
            }}
        if not pending:
            return _emit_scenario(rng, model, "publish_ok")
        fid = rng.choice(pending)
        pub = model.published[fid]
        if scenario == "resolve_matured":
            return {"kind": RESOLVE, "payload": {
                "forecast_id": fid,
                "state": MATURED,
                "observed_at_utc": _shift(pub["horizon_end_utc"], rng.randint(0, 3)),
                "outcome": rng.choice((0, 1)),
            }}
        if scenario == "resolve_matured_no_outcome":
            return {"kind": RESOLVE, "payload": {
                "forecast_id": fid,
                "state": MATURED,
                "observed_at_utc": _shift(pub["horizon_end_utc"], 1),
                "outcome": None,
            }}
        if scenario == "resolve_censored":
            return {"kind": RESOLVE, "payload": {
                "forecast_id": fid,
                "state": CENSORED,
                "observed_at_utc": _shift(pub["horizon_end_utc"], 1),
                "outcome": None,
            }}
        if scenario == "resolve_censored_outcome":
            return {"kind": RESOLVE, "payload": {
                "forecast_id": fid,
                "state": CENSORED,
                "observed_at_utc": _shift(pub["horizon_end_utc"], 1),
                "outcome": rng.choice((0, 1)),
            }}
        if scenario == "resolve_unpriceable":
            return {"kind": RESOLVE, "payload": {
                "forecast_id": fid,
                "state": UNPRICEABLE,
                "observed_at_utc": _shift(pub["horizon_end_utc"], 1),
                "outcome": None,
            }}
        if scenario == "resolve_unpriceable_outcome":
            return {"kind": RESOLVE, "payload": {
                "forecast_id": fid,
                "state": UNPRICEABLE,
                "observed_at_utc": _shift(pub["horizon_end_utc"], 1),
                "outcome": 1,
            }}
        if scenario == "resolve_early":
            hor = pub["horizon_end_utc"]
            pub_at = pub["published_at_utc"]
            early = _shift(hor, -1)
            return {"kind": RESOLVE, "payload": {
                "forecast_id": fid,
                "state": MATURED,
                "observed_at_utc": early,
                "outcome": 1,
            }}
        if scenario == "resolve_outcome_before_reg":
            return {"kind": RESOLVE, "payload": {
                "forecast_id": fid,
                "state": MATURED,
                "observed_at_utc": "2019-01-01T00:00:00Z",
                "outcome": 1,
            }}
        return {"kind": RESOLVE, "payload": {
            "forecast_id": fid,
            "state": MATURED,
            "observed_at_utc": _shift(pub["horizon_end_utc"], 1),
            "outcome": 0,
        }}

    if scenario.startswith("score"):
        family_id = fam
        payload = _valid_score_payload(model, family_id)
        if scenario == "score_ok":
            return {"kind": SCORE, "payload": payload}
        if scenario == "score_bad_brier":
            payload["brier"] = float(payload["brier"]) + BRIER_PERTURB
            return {"kind": SCORE, "payload": payload}
        if scenario == "score_non_matured":
            extra = _pending_ids(model)
            censored = [fid for fid, res in model.resolved.items() if res["state"] != MATURED]
            pick = extra + censored
            if pick:
                payload["scored_forecast_ids"] = sorted(set(payload["scored_forecast_ids"] + [pick[0]]))
                payload["n"] = len(payload["scored_forecast_ids"])
            else:
                payload["scored_forecast_ids"] = ["f-not-matured"]
                payload["n"] = 1
            return {"kind": SCORE, "payload": payload}
        if scenario == "score_unsorted":
            if len(payload["scored_forecast_ids"]) >= 2:
                payload["scored_forecast_ids"] = list(reversed(payload["scored_forecast_ids"]))
            else:
                payload["scored_forecast_ids"] = ["z-id", "a-id"]
                payload["n"] = 2
            return {"kind": SCORE, "payload": payload}
        if scenario == "score_not_descriptive":
            payload["descriptive_only"] = False
            return {"kind": SCORE, "payload": payload}
        if scenario == "score_no_matured":
            empty_fam = [f for f in set(registered_fams) if not model.matured_ids(f)]
            family_id = rng.choice(empty_fam) if empty_fam else fam
            payload = _valid_score_payload(model, family_id)
            return {"kind": SCORE, "payload": payload}

    if scenario == "nogo_ok":
        return {"kind": NOGO, "payload": {"family_id": fam, "reason": "failed-prereg-check"}}
    if scenario == "nogo_dup":
        if model.nogo:
            fam = rng.choice(list(model.nogo))
        return {"kind": NOGO, "payload": {"family_id": fam, "reason": "again"}}
    if scenario == "nogo_empty":
        return {"kind": NOGO, "payload": {"family_id": fam, "reason": ""}}

    if scenario == "authority":
        room = _family_with_budget_room(model)
        family_id = rng.choice(room) if room else fam
        published_at, horizon_end = _publish_times(model, family_id, rng, "ok")
        payload = {
            "forecast_id": _free_fid(model, rng),
            "family_id": family_id,
            "p": 0.2,
            "inputs_digest": DIGEST,
            "published_at_utc": published_at,
            "horizon_end_utc": horizon_end,
        }
        return {"kind": rng.choice(ROW_KINDS), "payload": _inject_authority(payload, rng)}

    if scenario == "unknown_kind":
        return {"kind": rng.choice(("FOO", "PUBLISH ", "register", "GRADE")), "payload": {
            "family_id": fam,
        }}

    if scenario == "missing_keys":
        kind = rng.choice(ROW_KINDS)
        return {"kind": kind, "payload": {"family_id": fam}}

    return {"kind": REGISTER, "payload": _register_payload(rng)}


def _op_brief(op):
    payload = op.get("payload") or {}
    keep = (
        "family_id", "forecast_id", "p", "state", "outcome", "reason",
        "declared_reason", "declared_trials", "protocol", "version", "split",
        "h", "descriptive_only", "brier", "n", "scored_forecast_ids",
        "published_at_utc", "horizon_end_utc", "observed_at_utc",
    )
    brief = {"kind": op.get("kind")}
    for key in keep:
        if key in payload:
            val = payload[key]
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                brief[key] = repr(val)
            else:
                brief[key] = val
    for key in payload:
        if isinstance(key, str) and key.strip().casefold() in _AUTHORITY_FOLDED:
            brief[key] = payload[key]
        if key in ("nested", "x"):
            brief[key] = payload[key]
    return brief


def _fail(seed, step, op, expected, got, extra=""):
    msg = "(seed=%r, step=%r, op=%r, expected=%r, got=%r)" % (
        seed, step, _op_brief(op), expected, got,
    )
    if extra:
        msg += " " + extra
    pytest.fail(msg)


def _ledger_apply(led, op):
    try:
        row = led.append(op["kind"], op["payload"])
        return ("ok", None, row)
    except LedgerRefused as exc:
        return ("refuse", exc.code, None)


def _drive(tmp_path, seed, suffix="drv"):
    rng = random.Random(seed)
    n_steps = rng.randint(5, 60)
    led = EvalLedger(tmp_path / ("sni-lgp-%s-%s.jsonl" % (suffix, seed)))
    model = ReferenceModel()
    log = []
    for step in range(n_steps):
        op = emit_op(rng, model, step, n_steps)
        expected = model.predict(op)
        got_status, got_code, row = _ledger_apply(led, op)
        got = (got_status, got_code)
        log.append((step, op, expected, got, row))
        if got_status == "ok" and expected[0] == "ok":
            model.apply(op, row["written_at_utc"])
        # On disagreement the caller decides whether to fail; model is
        # only folded on joint accept so later predictions stay honest.
    return led, model, log, rng, n_steps


def _id_state_from_ledger(led):
    """Map each published forecast_id to one of the four A28 states."""
    st = led.state()
    published = st["published"]
    resolved = st["resolved"]
    out = {}
    for fid in published:
        if fid not in resolved:
            out[fid] = PENDING
        else:
            out[fid] = resolved[fid]
    return out, st


def _resolve_outcomes_from_rows(led):
    out = {}
    for row in led.rows():
        if row["kind"] == RESOLVE:
            payload = row["payload"]
            out[payload["forecast_id"]] = (payload.get("state"), payload.get("outcome"))
    return out


def _assert_four_states(seed, step, op, led):
    id_states, st = _id_state_from_ledger(led)
    for fid, label in id_states.items():
        if label not in FOUR_STATES:
            _fail(seed, step, op, FOUR_STATES, label, extra="id=%r" % fid)
    outcomes = _resolve_outcomes_from_rows(led)
    for fid, (res_state, outcome) in outcomes.items():
        if res_state in (CENSORED, UNPRICEABLE) and outcome is not None:
            _fail(
                seed, step, op,
                "outcome=null for %s" % res_state,
                outcome,
                extra="id=%r" % fid,
            )
        if res_state == MATURED and outcome not in (0, 1):
            _fail(
                seed, step, op,
                "outcome in {0,1} for MATURED",
                outcome,
                extra="id=%r" % fid,
            )
        if fid in id_states and id_states[fid] != res_state:
            _fail(seed, step, op, id_states[fid], res_state, extra="resolved/state mismatch id=%r" % fid)
    for fid, label in id_states.items():
        if label == PENDING:
            if fid in outcomes:
                _fail(seed, step, op, "pending has no resolve row", outcomes[fid], extra="id=%r" % fid)
        elif label == MATURED:
            if fid not in outcomes or outcomes[fid][1] not in (0, 1):
                _fail(seed, step, op, "matured carries outcome", outcomes.get(fid), extra="id=%r" % fid)
        elif label in (CENSORED, UNPRICEABLE):
            if fid not in outcomes or outcomes[fid][1] is not None:
                _fail(seed, step, op, "%s outcome=null" % label, outcomes.get(fid), extra="id=%r" % fid)
    return st


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

def test_lgp_01_model_agrees(tmp_path):
    for seed in SEEDS:
        led, model, log, rng, n_steps = _drive(tmp_path, seed, suffix="p01")
        for step, op, expected, got, row in log:
            if expected != got:
                _fail(seed, step, op, expected, got)
            if got[0] == "ok":
                assert row is not None


def test_lgp_02_count_once(tmp_path):
    for seed in SEEDS:
        rng = random.Random(seed)
        led = EvalLedger(tmp_path / ("sni-lgp-p02-%s.jsonl" % seed))
        model = ReferenceModel()
        n_steps = rng.randint(5, 60)

        # Forced A26 probes: identical spec does not increment; any
        # changed key field is a new belief.
        forced = [
            {"kind": REGISTER, "payload": _register_payload(
                rng, family_id="fam-a", protocol="sni.v0", version="1",
                split="test", h=21, prereg_digest=DIGEST,
            )},
            {"kind": REGISTER, "payload": _register_payload(
                rng, family_id="fam-a", protocol="sni.v0", version="1",
                split="test", h=21, prereg_digest=DIGEST,
            )},
            {"kind": REGISTER, "payload": _register_payload(
                rng, family_id="fam-a", protocol="sni.v0", version="1",
                split="test", h=63, prereg_digest=DIGEST_B,
            )},
            {"kind": BUDGET, "payload": {"family_id": "fam-a", "declared_trials": 8}},
        ]
        for step, op in enumerate(forced):
            expected = model.predict(op)
            got_status, got_code, row = _ledger_apply(led, op)
            got = (got_status, got_code)
            if expected != got:
                _fail(seed, step, op, expected, got)
            if got_status == "ok":
                model.apply(op, row["written_at_utc"])
            count = led.registered_count()
            if count != model.registered_count():
                _fail(
                    seed, step, op,
                    model.registered_count(), count,
                    extra="registered_count drifted",
                )

        assert led.registered_count() == 2
        assert model.registered_count() == 2

        for step in range(len(forced), n_steps):
            op = emit_op(rng, model, step, n_steps)
            expected = model.predict(op)
            got_status, got_code, row = _ledger_apply(led, op)
            got = (got_status, got_code)
            if expected[0] == "ok" and got_status == "ok":
                model.apply(op, row["written_at_utc"])
            count = led.registered_count()
            if count != model.registered_count():
                _fail(
                    seed, step, op,
                    model.registered_count(), count,
                    extra="registered_count drifted",
                )


def test_lgp_03_publication_immutable(tmp_path):
    for seed in SEEDS:
        rng = random.Random(seed)
        led = EvalLedger(tmp_path / ("sni-lgp-p03-%s.jsonl" % seed))
        model = ReferenceModel()
        n_steps = rng.randint(5, 60)
        first_p = {}
        for step in range(n_steps):
            if step == 4 and model.published:
                fid = rng.choice(list(model.published))
                pub = model.published[fid]
                op = {"kind": PUBLISH, "payload": {
                    "forecast_id": fid,
                    "family_id": pub["family_id"],
                    "p": pub["p"],
                    "inputs_digest": DIGEST,
                    "published_at_utc": pub["published_at_utc"],
                    "horizon_end_utc": pub["horizon_end_utc"],
                }}
            else:
                op = emit_op(rng, model, step, n_steps)
            expected = model.predict(op)
            got_status, got_code, row = _ledger_apply(led, op)
            got = (got_status, got_code)
            if got_status == "ok" and op["kind"] == PUBLISH:
                fid = op["payload"]["forecast_id"]
                p = row["payload"]["p"]
                if fid in first_p:
                    _fail(
                        seed, step, op,
                        ("refuse", "IMMUTABLE_PUBLICATION"),
                        got,
                        extra="republish of %r accepted" % fid,
                    )
                first_p[fid] = p
            if expected[0] == "ok" and got_status == "ok":
                model.apply(op, row["written_at_utc"])
            if got_status == "ok":
                st = led.state()
                for fid, p in first_p.items():
                    stored = st["published"][fid]["payload"]["p"]
                    if stored != p:
                        _fail(
                            seed, step, op, p, stored,
                            extra="published p mutated for %r" % fid,
                        )
            elif op["kind"] == PUBLISH:
                fid = op["payload"].get("forecast_id")
                if fid in first_p:
                    st = led.state()
                    stored = st["published"][fid]["payload"]["p"]
                    if stored != first_p[fid]:
                        _fail(
                            seed, step, op, first_p[fid], stored,
                            extra="refused publish mutated p for %r" % fid,
                        )


def test_lgp_04_four_states_distinct(tmp_path):
    for seed in SEEDS:
        rng = random.Random(seed)
        led = EvalLedger(tmp_path / ("sni-lgp-p04-%s.jsonl" % seed))
        model = ReferenceModel()
        n_steps = rng.randint(5, 60)
        for step in range(n_steps):
            # Guarantee a censored-with-outcome probe so m2 is visible.
            if step == n_steps - 1 and _pending_ids(model):
                fid = _pending_ids(model)[0]
                pub = model.published[fid]
                op = {"kind": RESOLVE, "payload": {
                    "forecast_id": fid,
                    "state": CENSORED,
                    "observed_at_utc": _shift(pub["horizon_end_utc"], 1),
                    "outcome": 1,
                }}
            else:
                op = emit_op(rng, model, step, n_steps)
            expected = model.predict(op)
            got_status, got_code, row = _ledger_apply(led, op)
            if expected[0] == "ok" and got_status == "ok":
                model.apply(op, row["written_at_utc"])
            if got_status == "ok" or True:
                try:
                    _assert_four_states(seed, step, op, led)
                except LedgerRefused as exc:
                    _fail(seed, step, op, "state readable", ("refuse", exc.code))


def test_lgp_05_replay_equals_incremental(tmp_path):
    for seed in SEEDS:
        led, model, log, rng, n_steps = _drive(tmp_path, seed, suffix="p05")
        accepted = [(step, op, got) for step, op, expected, got, row in log if got[0] == "ok"]
        try:
            led.assert_replay_equal()
        except LedgerRefused as exc:
            last = accepted[-1] if accepted else (None, {"kind": None, "payload": {}}, None)
            _fail(seed, last[0], last[1], "replay equal", ("refuse", exc.code))
        from_file = replay(led.path)
        incremental = led.state()
        if from_file != incremental:
            last = accepted[-1] if accepted else (None, {"kind": None, "payload": {}}, None)
            _fail(seed, last[0], last[1], "replay==state", "mismatch")
        violations = led.verify_chain()
        if violations:
            last = accepted[-1] if accepted else (None, {"kind": None, "payload": {}}, None)
            _fail(seed, last[0], last[1], [], violations, extra="verify_chain")


def _tamper_one_byte(path, rng):
    """Flip one byte of a seed-chosen line/field. Returns (line_i, field)."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    line_i = rng.randrange(len(lines))
    row = json.loads(lines[line_i])
    field_names = [k for k in row.keys() if k != "payload"]
    payload = row.get("payload")
    if isinstance(payload, dict) and payload:
        field_names.append("payload." + rng.choice(list(payload.keys())))
    field = rng.choice(field_names)
    if field.startswith("payload."):
        key = field.split(".", 1)[1]
        value = payload[key]
        target = "payload"
    else:
        value = row[field]
        key = field
        target = "row"
    if isinstance(value, str) and value:
        pos = rng.randrange(len(value))
        alphabet = "0123456789abcdefxyzXYZ"
        new_c = rng.choice([c for c in alphabet if c != value[pos]])
        new_value = value[:pos] + new_c + value[pos + 1:]
    elif isinstance(value, bool):
        new_value = not value
    elif isinstance(value, int) and not isinstance(value, bool):
        new_value = value + rng.choice((-1, 1, 7))
    elif isinstance(value, float):
        new_value = value + 0.01 if math.isfinite(value) else 0.3
    elif value is None:
        new_value = "tampered"
    else:
        new_value = "tampered"
    if target == "payload":
        row["payload"][key] = new_value
    else:
        row[field] = new_value
    lines[line_i] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return line_i, field


def test_lgp_06_tamper_detected(tmp_path):
    observed_codes = []
    for seed in SEEDS:
        rng = random.Random(seed)
        led, model, log, _rng, n_steps = _drive(tmp_path, seed, suffix="p06")
        if not led.rows():
            op = {"kind": REGISTER, "payload": _register_payload(
                rng, family_id="fam-a", protocol="sni.v0", version="1",
                split="test", h=21, prereg_digest=DIGEST,
            )}
            row_status, code, row = _ledger_apply(led, op)
            if row_status != "ok":
                _fail(seed, 0, op, ("ok", None), (row_status, code), extra="forced register")
        path = led.path
        line_i, field = _tamper_one_byte(path, rng)

        replay_refused = False
        replay_code = None
        try:
            replay(path)
        except LedgerRefused as exc:
            replay_refused = True
            replay_code = exc.code
        except Exception as exc:
            replay_refused = True
            replay_code = type(exc).__name__

        chain_codes = []
        try:
            chain_codes = EvalLedger(path).verify_chain()
        except Exception as exc:
            chain_codes = [type(exc).__name__]

        if not chain_codes and not replay_refused:
            _fail(
                seed, line_i, {"kind": "TAMPER", "payload": {"field": field, "line": line_i}},
                "replay/verify_chain refuse",
                ("ok", None),
            )
        observed_codes.append((replay_code, tuple(chain_codes[:3])))
    assert len(observed_codes) == 300


def test_lgp_07_row_permutation(tmp_path):
    for seed in SEEDS:
        rng = random.Random(seed)
        led, model, log, _rng, n_steps = _drive(tmp_path, seed, suffix="p07")
        if len(led.rows()) < 2:
            for extra_step, extra in enumerate((
                {"kind": REGISTER, "payload": _register_payload(
                    rng, family_id="fam-z", protocol="sni.v0", version="1",
                    split="test", h=21, prereg_digest=DIGEST,
                )},
                {"kind": REGISTER, "payload": _register_payload(
                    rng, family_id="fam-y", protocol="sni.v0", version="1",
                    split="test", h=21, prereg_digest=DIGEST_B,
                )},
            ), start=100):
                status, code, row = _ledger_apply(led, extra)
                if status != "ok" and len(led.rows()) < 2:
                    continue
        rows_before = led.rows()
        if len(rows_before) < 2:
            continue
        orig_state = led.state()
        orig_text = led.path.read_text(encoding="utf-8")
        lines = orig_text.splitlines()
        if len(lines) < 2:
            continue
        # Prefer two independent PUBLISH rows; else any two lines.
        pub_idx = [i for i, line in enumerate(lines)
                   if json.loads(line).get("kind") == PUBLISH]
        if len(pub_idx) >= 2:
            i, j = pub_idx[0], pub_idx[1]
        else:
            i, j = 0, 1
            if len(lines) > 2:
                i = rng.randrange(len(lines))
                j = rng.randrange(len(lines))
                while j == i:
                    j = rng.randrange(len(lines))
        lines[i], lines[j] = lines[j], lines[i]
        led.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tampered = EvalLedger(led.path)
        violations = []
        try:
            violations = tampered.verify_chain()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            violations = [type(exc).__name__]
        state_ok = False
        new_state = None
        try:
            new_state = tampered.state()
            state_ok = True
        except (LedgerRefused, json.JSONDecodeError, UnicodeDecodeError, ValueError):
            state_ok = False
        if not violations:
            if not state_ok:
                continue
            if new_state != orig_state:
                _fail(
                    seed, (i, j),
                    {"kind": "PERMUTE", "payload": {"i": i, "j": j}},
                    orig_state.get("counts"),
                    new_state.get("counts") if new_state else None,
                    extra="permutation yielded a different accepted state",
                )


def test_lgp_08_brier_reference(tmp_path):
    for seed in SEEDS:
        rng = random.Random(seed)
        led = EvalLedger(tmp_path / ("sni-lgp-p08-%s.jsonl" % seed))
        model = ReferenceModel()
        n_steps = rng.randint(5, 60)

        def _step(step, op):
            expected = model.predict(op)
            got_status, got_code, row = _ledger_apply(led, op)
            got = (got_status, got_code)
            if expected[0] == "ok" and got_status == "ok":
                model.apply(op, row["written_at_utc"])
            return expected, got, row

        setup = [
            {"kind": REGISTER, "payload": _register_payload(
                rng, family_id="fam-a", protocol="sni.v0", version="1",
                split="test", h=21, prereg_digest=DIGEST,
            )},
            {"kind": BUDGET, "payload": {"family_id": "fam-a", "declared_trials": 12}},
        ]
        for step, op in enumerate(setup):
            expected, got, row = _step(step, op)
            if expected != got:
                _fail(seed, step, op, expected, got)

        n_pub = rng.randint(1, 4)
        for k in range(n_pub):
            op = emit_op(rng, model, 2 + k, n_steps)
            # Force a valid publish into fam-a when possible.
            published_at, horizon_end = _publish_times(model, "fam-a", rng, "ok")
            p = rng.choice((0.1, 0.25, 0.3, 0.75, 0.9))
            op = {"kind": PUBLISH, "payload": {
                "forecast_id": "f-mat-%d" % k,
                "family_id": "fam-a",
                "p": p,
                "inputs_digest": DIGEST,
                "published_at_utc": published_at,
                "horizon_end_utc": horizon_end,
            }}
            expected, got, row = _step(10 + k, op)
            if expected != got:
                _fail(seed, 10 + k, op, expected, got)
            if got[0] == "ok":
                res_op = {"kind": RESOLVE, "payload": {
                    "forecast_id": "f-mat-%d" % k,
                    "state": MATURED,
                    "observed_at_utc": _shift(horizon_end, 1),
                    "outcome": rng.choice((0, 1)),
                }}
                expected, got, row = _step(20 + k, res_op)
                if expected != got:
                    _fail(seed, 20 + k, res_op, expected, got)

        for family_id in set(k[0] for k in model.registered):
            matured = model.matured_ids(family_id)
            if not matured:
                continue
            computed = model.model_brier(family_id)
            got_brier = brier(led, family_id)
            if abs(got_brier - computed) > 1e-12:
                _fail(
                    seed, "brier", {"kind": SCORE, "payload": {"family_id": family_id}},
                    computed, got_brier,
                )

        if model.matured_ids("fam-a"):
            payload = _valid_score_payload(model, "fam-a")
            payload["brier"] = float(payload["brier"]) + BRIER_PERTURB
            op = {"kind": SCORE, "payload": payload}
            expected, got, row = _step(80, op)
            if got != ("refuse", "BRIER_MISMATCH"):
                _fail(seed, 80, op, ("refuse", "BRIER_MISMATCH"), got)

        for step in range(n_steps):
            op = emit_op(rng, model, step, n_steps)
            expected, got, row = _step(100 + step, op)
            for family_id in set(k[0] for k in model.registered):
                if not model.matured_ids(family_id):
                    continue
                computed = model.model_brier(family_id)
                try:
                    got_brier = brier(led, family_id)
                except LedgerRefused as exc:
                    _fail(seed, 100 + step, op, computed, ("refuse", exc.code))
                    continue
                if abs(got_brier - computed) > 1e-12:
                    _fail(seed, 100 + step, op, computed, got_brier)


def test_lgp_09_nogo_blocks_family_only(tmp_path):
    for seed in SEEDS:
        rng = random.Random(seed)
        led = EvalLedger(tmp_path / ("sni-lgp-p09-%s.jsonl" % seed))
        model = ReferenceModel()
        n_steps = rng.randint(5, 60)

        def _step(step, op):
            expected = model.predict(op)
            got_status, got_code, row = _ledger_apply(led, op)
            got = (got_status, got_code)
            if expected[0] == "ok" and got_status == "ok":
                model.apply(op, row["written_at_utc"])
            return expected, got, row

        setup = [
            {"kind": REGISTER, "payload": _register_payload(
                rng, family_id="fam-a", protocol="sni.v0", version="1",
                split="test", h=21, prereg_digest=DIGEST,
            )},
            {"kind": BUDGET, "payload": {"family_id": "fam-a", "declared_trials": 8}},
            {"kind": REGISTER, "payload": _register_payload(
                rng, family_id="fam-b", protocol="sni.v0", version="1",
                split="test", h=21, prereg_digest=DIGEST_B,
            )},
            {"kind": BUDGET, "payload": {"family_id": "fam-b", "declared_trials": 8}},
        ]
        for step, op in enumerate(setup):
            expected, got, row = _step(step, op)
            if expected != got:
                _fail(seed, step, op, expected, got)

        for step in range(n_steps):
            op = emit_op(rng, model, step + 4, n_steps + 4)
            _step(step + 4, op)

        nogo_op = {"kind": NOGO, "payload": {"family_id": "fam-a", "reason": "failed-prereg-check"}}
        expected, got, row = _step(90, nogo_op)
        if got[0] == "ok" or (got == ("refuse", "ALREADY_NOGO")):
            pass
        elif expected != got:
            _fail(seed, 90, nogo_op, expected, got)
        if "fam-a" not in model.nogo and got[0] == "ok":
            pass
        # After NOGO of fam-a (accepted now or earlier), publish in fam-a
        # is FAMILY_NOGO; fam-b still publishes if budget remains.
        if "fam-a" in led.state()["nogo"]:
            published_at, horizon_end = _publish_times(model, "fam-a", rng, "ok")
            blocked = {"kind": PUBLISH, "payload": {
                "forecast_id": "f-nogo-a-%s" % seed,
                "family_id": "fam-a",
                "p": 0.3,
                "inputs_digest": DIGEST,
                "published_at_utc": published_at,
                "horizon_end_utc": horizon_end,
            }}
            expected, got, row = _step(91, blocked)
            if got != ("refuse", "FAMILY_NOGO"):
                _fail(seed, 91, blocked, ("refuse", "FAMILY_NOGO"), got)
            if "fam-b" in model.budgets and "fam-b" not in model.nogo:
                room = model.budgets["fam-b"]
                if room["used_trials"] < room["declared_trials"]:
                    published_at, horizon_end = _publish_times(model, "fam-b", rng, "ok")
                    other = {"kind": PUBLISH, "payload": {
                        "forecast_id": "f-nogo-b-%s" % seed,
                        "family_id": "fam-b",
                        "p": 0.4,
                        "inputs_digest": DIGEST,
                        "published_at_utc": published_at,
                        "horizon_end_utc": horizon_end,
                    }}
                    expected, got, row = _step(92, other)
                    if got[0] != "ok":
                        _fail(seed, 92, other, ("ok", None), got)


def test_lgp_10_authority_never_true(tmp_path):
    for seed in SEEDS:
        rng = random.Random(seed)
        led = EvalLedger(tmp_path / ("sni-lgp-p10-%s.jsonl" % seed))
        model = ReferenceModel()
        n_steps = rng.randint(5, 60)
        for step in range(n_steps):
            op = emit_op(rng, model, step, n_steps)
            expected = model.predict(op)
            got_status, got_code, row = _ledger_apply(led, op)
            if expected[0] == "ok" and got_status == "ok":
                model.apply(op, row["written_at_utc"])

        kind = rng.choice(ROW_KINDS)
        payload = {"family_id": "fam-a", "reason": "x", "declared_trials": 4,
                   "forecast_id": "f-auth", "p": 0.2, "inputs_digest": DIGEST,
                   "published_at_utc": "2099-01-01T00:00:00Z",
                   "horizon_end_utc": "2099-02-01T00:00:00Z",
                   "protocol": "sni.v0", "version": "1", "split": "test",
                   "h": 21, "prereg_digest": DIGEST,
                   "state": MATURED, "observed_at_utc": "2099-03-01T00:00:00Z",
                   "outcome": 1, "baseline_id": "b", "baseline_digest": DIGEST_B,
                   "scored_forecast_ids": ["f-auth"], "brier": 0.0,
                   "baseline_brier": 0.25, "n": 1, "n_censored": 0,
                   "n_unpriceable": 0, "n_pending": 0, "descriptive_only": True}
        payload = _inject_authority(dict(payload), rng)
        op = {"kind": kind, "payload": payload}
        expected = model.predict(op)
        got_status, got_code, row = _ledger_apply(led, op)
        got = (got_status, got_code)
        if got != ("refuse", "AUTHORITY_FLAG_REFUSED"):
            _fail(seed, n_steps, op, ("refuse", "AUTHORITY_FLAG_REFUSED"), got)
        if expected != ("refuse", "AUTHORITY_FLAG_REFUSED"):
            _fail(seed, n_steps, op, ("refuse", "AUTHORITY_FLAG_REFUSED"), expected,
                  extra="model missed authority")
