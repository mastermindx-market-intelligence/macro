"""SNI-local DRAFT evaluation registration ledger.

This module is an SNI-local draft contract that CONSUMES the
qledger / Evaluation owner's vocabulary (registration, maturity,
censoring, proper scores, frozen baselines). It does not replace
qledger, does not implement Evaluation OS, and does not originate
any probability, identity, forecast, rank, gate, size, signal,
escalation, or trade.

Identity ids (family_id, forecast_id, baseline_id) are caller-supplied
opaque strings owned by Stock Identity / Data OS; this module never
mints, derives, or guesses canonical HK/US issuer or security
identifiers.

Authority flags stay false: a payload that carries any of
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority, trade_authority is refused. Nothing here feeds
a ranker, gate, sizer, signal, escalation, or trade path.

Scores are DESCRIPTIVE residual statistics against a caller-supplied
frozen baseline (A24/A29). They are never causal and never "news
impact". p = 0.5 with no declared_reason is refused (A25). An
unestimable family abstains with a named reason.

Row kinds: REGISTER, BUDGET, PUBLISH, ABSTAIN, RESOLVE, SCORE, NOGO.
The ledger is append-only JSONL with a sha256 hash chain. Replay of
the file must reproduce the same state as an incremental fold (A27).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

REGISTER = "REGISTER"
BUDGET = "BUDGET"
PUBLISH = "PUBLISH"
ABSTAIN = "ABSTAIN"
RESOLVE = "RESOLVE"
SCORE = "SCORE"
NOGO = "NOGO"

ROW_KINDS = (REGISTER, BUDGET, PUBLISH, ABSTAIN, RESOLVE, SCORE, NOGO)

PENDING = "PENDING"
UNPRICEABLE = "UNPRICEABLE"
CENSORED = "CENSORED"
MATURED = "MATURED"

RESOLVE_STATES = frozenset({UNPRICEABLE, CENSORED, MATURED})
OUTCOME_STATES = frozenset({PENDING, UNPRICEABLE, CENSORED, MATURED})

AUTHORITY_KEYS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

REFUSAL_CODES = frozenset({
    "ALREADY_REGISTERED",
    "BUDGET_REQUIRED",
    "BUDGET_EXCEEDED",
    "IMMUTABLE_PUBLICATION",
    "REPLAY_MISMATCH",
    "DEFAULT_PROBABILITY_REFUSED",
    "ALREADY_RESOLVED",
    "MATURED_OUTCOME_REQUIRED",
    "OUTCOME_FORBIDDEN",
    "HORIZON_NOT_REACHED",
    "NOT_PENDING",
    "BRIER_MISMATCH",
    "NOT_MATURED",
    "FAMILY_NOGO",
    "AUTHORITY_FLAG_REFUSED",
    "FAMILY_NOT_REGISTERED",
    "ALREADY_PUBLISHED",
    "ALREADY_ABSTAINED",
    "UNKNOWN_KIND",
    "INVALID_PAYLOAD",
    "INVALID_PREREG_DIGEST",
    "INVALID_INPUTS_DIGEST",
    "INVALID_BASELINE_DIGEST",
    "INVALID_P",
    "INVALID_DECLARED_TRIALS",
    "EMPTY_REASON",
    "DESCRIPTIVE_ONLY_REQUIRED",
    "SCORED_IDS_UNSORTED",
    "INVALID_RESOLVE_STATE",
    "N_MISMATCH",
    "UNKNOWN_FORECAST",
    "DUPLICATE_BUDGET",
    "ALREADY_NOGO",
    "NO_MATURED_FORECASTS",
})

_HEX = "0123456789abcdef"


class LedgerRefused(Exception):
    """Append or replay refused. ``code`` is a member of REFUSAL_CODES."""

    def __init__(self, code, detail=""):
        if code not in REFUSAL_CODES:
            raise ValueError("unknown refusal code: %r" % (code,))
        self.code = code
        self.detail = detail
        Exception.__init__(self, ("%s: %s" % (code, detail)) if detail else code)


@dataclass
class LedgerRow:
    seq: int
    kind: str
    written_at_utc: str
    payload: dict
    prev_hash: object
    row_hash: str

    def to_dict(self):
        return {
            "seq": self.seq,
            "kind": self.kind,
            "written_at_utc": self.written_at_utc,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "row_hash": self.row_hash,
        }


def _refuse(code, detail=""):
    raise LedgerRefused(code, detail)


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _row_hash(row):
    body = {k: v for k, v in row.items() if k != "row_hash"}
    return _sha256_text(_canonical(body))


def _is_hex64(value):
    return isinstance(value, str) and len(value) == 64 and all(c in _HEX for c in value)


def _is_nonempty_str(value):
    return isinstance(value, str) and value != ""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _now_utc():
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _parse_utc(value, field):
    if not isinstance(value, str) or value == "":
        _refuse("INVALID_PAYLOAD", "missing or empty %s" % field)
    raw = value
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(raw)
    except ValueError:
        _refuse("INVALID_PAYLOAD", "unparseable %s" % field)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _require_keys(payload, keys):
    for key in keys:
        if key not in payload:
            _refuse("INVALID_PAYLOAD", "missing %s" % key)


def _check_authority(payload):
    if not isinstance(payload, dict):
        _refuse("INVALID_PAYLOAD", "payload must be an object")
    for key in AUTHORITY_KEYS:
        if key in payload:
            _refuse("AUTHORITY_FLAG_REFUSED", key)
        if payload.get(key) is True:
            _refuse("AUTHORITY_FLAG_REFUSED", key)


def _reg_key(payload):
    return (
        payload["family_id"],
        payload["protocol"],
        payload["version"],
        payload["split"],
        payload["h"],
    )


def _empty_state():
    st = {
        "registered": {},
        "budgets": {},
        "published": {},
        "abstained": {},
        "resolved": {},
        "scores": [],
        "nogo": set(),
        "counts": {},
    }
    _refresh_counts(st, 0)
    return st


def _refresh_counts(st, n_rows):
    published = st["published"]
    resolved = st["resolved"]
    pending = sum(1 for fid in published if fid not in resolved)
    st["counts"] = {
        "rows": n_rows,
        "registered": len(st["registered"]),
        "published": len(published),
        "abstained": len(st["abstained"]),
        "resolved": len(resolved),
        "pending": pending,
        "scores": len(st["scores"]),
        "nogo": len(st["nogo"]),
    }


def _clone_state(st):
    return {
        "registered": dict(st["registered"]),
        "budgets": {k: dict(v) for k, v in st["budgets"].items()},
        "published": dict(st["published"]),
        "abstained": dict(st["abstained"]),
        "resolved": dict(st["resolved"]),
        "scores": list(st["scores"]),
        "nogo": set(st["nogo"]),
        "counts": dict(st["counts"]),
    }


def _states_equal(a, b):
    return _state_fingerprint(a) == _state_fingerprint(b)


def _state_fingerprint(st):
    registered = [
        {"key": list(k), "prereg_digest": v}
        for k, v in sorted(st["registered"].items(), key=lambda kv: _canonical(list(kv[0])))
    ]
    budgets = {k: dict(v) for k, v in sorted(st["budgets"].items())}
    published = {k: st["published"][k] for k in sorted(st["published"])}
    abstained = {k: st["abstained"][k] for k in sorted(st["abstained"])}
    resolved = {k: st["resolved"][k] for k in sorted(st["resolved"])}
    nogo = sorted(st["nogo"])
    blob = {
        "registered": registered,
        "budgets": budgets,
        "published": published,
        "abstained": abstained,
        "resolved": resolved,
        "scores": st["scores"],
        "nogo": nogo,
        "counts": st["counts"],
    }
    return _canonical(blob)


def _fold(st, row):
    kind = row["kind"]
    payload = row["payload"]
    if kind == REGISTER:
        st["registered"][_reg_key(payload)] = payload["prereg_digest"]
    elif kind == BUDGET:
        st["budgets"][payload["family_id"]] = {
            "declared_trials": payload["declared_trials"],
            "used_trials": 0,
        }
    elif kind == PUBLISH:
        fid = payload["forecast_id"]
        st["published"][fid] = row
        family_id = payload["family_id"]
        if family_id in st["budgets"]:
            st["budgets"][family_id]["used_trials"] += 1
    elif kind == ABSTAIN:
        fid = payload["forecast_id"]
        st["abstained"][fid] = row
        family_id = payload["family_id"]
        if family_id in st["budgets"]:
            st["budgets"][family_id]["used_trials"] += 1
    elif kind == RESOLVE:
        st["resolved"][payload["forecast_id"]] = payload["state"]
    elif kind == SCORE:
        st["scores"].append(row)
    elif kind == NOGO:
        st["nogo"].add(payload["family_id"])
    n_rows = st["counts"].get("rows", 0) + 1
    _refresh_counts(st, n_rows)


def _family_registered(st, family_id):
    for key in st["registered"]:
        if key[0] == family_id:
            return True
    return False


def _matured_ids(st, family_id):
    ids = []
    for fid, pub in st["published"].items():
        if pub["payload"].get("family_id") != family_id:
            continue
        if st["resolved"].get(fid) == MATURED:
            ids.append(fid)
    ids.sort()
    return ids


def _brier_pairs(ledger, family_id):
    """(p, outcome) for MATURED publications of family_id, in forecast_id order."""
    rows = ledger.rows()
    published = {}
    resolved = {}
    for row in rows:
        kind = row["kind"]
        payload = row["payload"]
        if kind == PUBLISH and payload.get("family_id") == family_id:
            published[payload["forecast_id"]] = payload
        elif kind == RESOLVE:
            fid = payload.get("forecast_id")
            if fid in published:
                resolved[fid] = payload
    pairs = []
    for fid in sorted(published):
        res = resolved.get(fid)
        if res is None or res.get("state") != MATURED:
            continue
        p = published[fid]["p"]
        outcome = res.get("outcome")
        pairs.append((fid, p, outcome))
    return pairs


def brier(ledger, family_id):
    """Mean (p - outcome)^2 over MATURED forecasts of family_id. Descriptive only."""
    pairs = _brier_pairs(ledger, family_id)
    if not pairs:
        _refuse("NO_MATURED_FORECASTS", family_id)
    squares = []
    for _fid, p, outcome in pairs:
        squares.append((float(p) - float(outcome)) ** 2)
    return math.fsum(squares) / len(squares)


def replay(path):
    """Fresh EvalLedger(path).state() rebuilt solely from the JSONL file."""
    return EvalLedger(path).state()


def _validate_register(st, payload):
    _require_keys(payload, ("family_id", "protocol", "version", "split", "h", "prereg_digest"))
    for field in ("family_id", "protocol", "version", "split"):
        if not _is_nonempty_str(payload[field]):
            _refuse("INVALID_PAYLOAD", field)
    if not _is_int(payload["h"]):
        _refuse("INVALID_PAYLOAD", "h")
    if not _is_hex64(payload["prereg_digest"]):
        _refuse("INVALID_PREREG_DIGEST")
    key = _reg_key(payload)
    if key in st["registered"]:
        _refuse("ALREADY_REGISTERED")


def _validate_budget(st, payload):
    _require_keys(payload, ("family_id", "declared_trials"))
    family_id = payload["family_id"]
    if not _is_nonempty_str(family_id):
        _refuse("INVALID_PAYLOAD", "family_id")
    if not _family_registered(st, family_id):
        _refuse("FAMILY_NOT_REGISTERED", family_id)
    if family_id in st["budgets"]:
        _refuse("DUPLICATE_BUDGET", family_id)
    n = payload["declared_trials"]
    if not _is_int(n) or n <= 0:
        _refuse("INVALID_DECLARED_TRIALS")


def _validate_publish(st, payload):
    _require_keys(
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
    forecast_id = payload["forecast_id"]
    family_id = payload["family_id"]
    if not _is_nonempty_str(forecast_id):
        _refuse("INVALID_PAYLOAD", "forecast_id")
    if not _is_nonempty_str(family_id):
        _refuse("INVALID_PAYLOAD", "family_id")
    if not _family_registered(st, family_id):
        _refuse("FAMILY_NOT_REGISTERED", family_id)
    if family_id in st["nogo"]:
        _refuse("FAMILY_NOGO", family_id)
    if forecast_id in st["published"]:
        _refuse("IMMUTABLE_PUBLICATION", forecast_id)
    if forecast_id in st["abstained"]:
        _refuse("ALREADY_ABSTAINED", forecast_id)
    if family_id not in st["budgets"]:
        _refuse("BUDGET_REQUIRED", family_id)
    budget = st["budgets"][family_id]
    if budget["used_trials"] + 1 > budget["declared_trials"]:
        _refuse("BUDGET_EXCEEDED", family_id)
    if not _is_hex64(payload["inputs_digest"]):
        _refuse("INVALID_INPUTS_DIGEST")
    _parse_utc(payload["published_at_utc"], "published_at_utc")
    _parse_utc(payload["horizon_end_utc"], "horizon_end_utc")
    p = payload["p"]
    if isinstance(p, bool) or not isinstance(p, (int, float)):
        _refuse("INVALID_P")
    p = float(p)
    if math.isnan(p) or math.isinf(p) or not (0.0 < p < 1.0):
        _refuse("INVALID_P")
    reason = payload.get("declared_reason")
    if p == 0.5:
        if not _is_nonempty_str(reason):
            _refuse("DEFAULT_PROBABILITY_REFUSED")


def _validate_abstain(st, payload):
    _require_keys(payload, ("forecast_id", "family_id", "reason"))
    forecast_id = payload["forecast_id"]
    family_id = payload["family_id"]
    if not _is_nonempty_str(forecast_id):
        _refuse("INVALID_PAYLOAD", "forecast_id")
    if not _is_nonempty_str(family_id):
        _refuse("INVALID_PAYLOAD", "family_id")
    if not _is_nonempty_str(payload["reason"]):
        _refuse("EMPTY_REASON")
    if not _family_registered(st, family_id):
        _refuse("FAMILY_NOT_REGISTERED", family_id)
    if family_id in st["nogo"]:
        _refuse("FAMILY_NOGO", family_id)
    if forecast_id in st["published"]:
        _refuse("ALREADY_PUBLISHED", forecast_id)
    if forecast_id in st["abstained"]:
        _refuse("ALREADY_ABSTAINED", forecast_id)
    if family_id not in st["budgets"]:
        _refuse("BUDGET_REQUIRED", family_id)
    budget = st["budgets"][family_id]
    if budget["used_trials"] + 1 > budget["declared_trials"]:
        _refuse("BUDGET_EXCEEDED", family_id)


def _validate_resolve(st, payload):
    _require_keys(payload, ("forecast_id", "state", "observed_at_utc", "outcome"))
    forecast_id = payload["forecast_id"]
    if not _is_nonempty_str(forecast_id):
        _refuse("INVALID_PAYLOAD", "forecast_id")
    if forecast_id in st["resolved"]:
        _refuse("ALREADY_RESOLVED", forecast_id)
    if forecast_id not in st["published"]:
        _refuse("UNKNOWN_FORECAST", forecast_id)
    if forecast_id in st["abstained"]:
        _refuse("NOT_PENDING", forecast_id)
    resolve_state = payload["state"]
    if resolve_state not in RESOLVE_STATES:
        _refuse("INVALID_RESOLVE_STATE", repr(resolve_state))
    outcome = payload["outcome"]
    observed = _parse_utc(payload["observed_at_utc"], "observed_at_utc")
    pub = st["published"][forecast_id]
    horizon_end = _parse_utc(pub["payload"]["horizon_end_utc"], "horizon_end_utc")
    if resolve_state == MATURED:
        if outcome is True or outcome is False or not _is_int(outcome) or outcome not in (0, 1):
            _refuse("MATURED_OUTCOME_REQUIRED")
        if observed < horizon_end:
            _refuse("HORIZON_NOT_REACHED")
    else:
        if outcome is not None:
            _refuse("OUTCOME_FORBIDDEN")


def _validate_score(ledger, st, payload):
    _require_keys(
        payload,
        (
            "family_id",
            "baseline_id",
            "baseline_digest",
            "scored_forecast_ids",
            "brier",
            "baseline_brier",
            "n",
            "descriptive_only",
        ),
    )
    family_id = payload["family_id"]
    if not _is_nonempty_str(family_id):
        _refuse("INVALID_PAYLOAD", "family_id")
    if not _family_registered(st, family_id):
        _refuse("FAMILY_NOT_REGISTERED", family_id)
    if not _is_nonempty_str(payload["baseline_id"]):
        _refuse("INVALID_PAYLOAD", "baseline_id")
    if not _is_hex64(payload["baseline_digest"]):
        _refuse("INVALID_BASELINE_DIGEST")
    if payload.get("descriptive_only") is not True:
        _refuse("DESCRIPTIVE_ONLY_REQUIRED")
    ids = payload["scored_forecast_ids"]
    if not isinstance(ids, list) or any(not _is_nonempty_str(i) for i in ids):
        _refuse("INVALID_PAYLOAD", "scored_forecast_ids")
    if ids != sorted(ids):
        _refuse("SCORED_IDS_UNSORTED")
    if len(ids) != len(set(ids)):
        _refuse("INVALID_PAYLOAD", "duplicate scored_forecast_ids")
    n = payload["n"]
    if not _is_int(n):
        _refuse("INVALID_PAYLOAD", "n")
    matured = _matured_ids(st, family_id)
    if not matured:
        _refuse("NO_MATURED_FORECASTS", family_id)
    for fid in ids:
        pub = st["published"].get(fid)
        if pub is None or pub["payload"].get("family_id") != family_id:
            _refuse("NOT_MATURED", fid)
        if st["resolved"].get(fid) != MATURED:
            _refuse("NOT_MATURED", fid)
    if n != len(ids) or n != len(matured) or ids != matured:
        _refuse("N_MISMATCH")
    reported = payload["brier"]
    if isinstance(reported, bool) or not isinstance(reported, (int, float)):
        _refuse("INVALID_PAYLOAD", "brier")
    baseline_brier = payload["baseline_brier"]
    if isinstance(baseline_brier, bool) or not isinstance(baseline_brier, (int, float)):
        _refuse("INVALID_PAYLOAD", "baseline_brier")
    recomputed = brier(ledger, family_id)
    if abs(float(reported) - recomputed) > 1e-12:
        _refuse("BRIER_MISMATCH")


def _validate_nogo(st, payload):
    _require_keys(payload, ("family_id", "reason"))
    family_id = payload["family_id"]
    if not _is_nonempty_str(family_id):
        _refuse("INVALID_PAYLOAD", "family_id")
    if not _is_nonempty_str(payload["reason"]):
        _refuse("EMPTY_REASON")
    if not _family_registered(st, family_id):
        _refuse("FAMILY_NOT_REGISTERED", family_id)
    if family_id in st["nogo"]:
        _refuse("ALREADY_NOGO", family_id)


class EvalLedger:
    """Append-only hash-chained JSONL evaluation registration ledger."""

    def __init__(self, path):
        self.path = Path(path)
        self._incremental = _clone_state(self._rebuild())

    def rows(self):
        if not self.path.exists() or self.path.stat().st_size == 0:
            return []
        out = []
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                out.append(json.loads(line))
        return out

    def _rebuild(self):
        st = _empty_state()
        rows = self.rows()
        for row in rows:
            _fold(st, row)
        _refresh_counts(st, len(rows))
        return st

    def state(self):
        """Rebuild ledger state purely from rows. No cache is consulted."""
        return self._rebuild()

    def registered_count(self):
        return len(self.state()["registered"])

    def verify_chain(self):
        """Return a list of violation strings; empty means the chain is intact."""
        violations = []
        try:
            rows = self.rows()
        except json.JSONDecodeError as exc:
            return ["JSON_DECODE:%s" % exc]
        prev = None
        for i, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                violations.append("ROW_NOT_OBJECT:%s" % i)
                continue
            if row.get("seq") != i:
                violations.append("SEQ_MISMATCH:%s" % i)
            if row.get("prev_hash") != prev:
                violations.append("PREV_HASH_MISMATCH:%s" % i)
            try:
                expected = _row_hash(row)
            except (TypeError, ValueError) as exc:
                violations.append("HASH_INPUT:%s:%s" % (i, exc))
                prev = row.get("row_hash")
                continue
            if row.get("row_hash") != expected:
                violations.append("ROW_HASH_MISMATCH:%s" % i)
            prev = row.get("row_hash")
        return violations

    def assert_replay_equal(self):
        """A27: incremental fold must equal a from-scratch rebuild from the file."""
        rebuilt = self.state()
        from_file = replay(self.path)
        if not _states_equal(rebuilt, from_file) or not _states_equal(
            rebuilt, self._incremental
        ):
            _refuse("REPLAY_MISMATCH")

    def append(self, kind, payload):
        if kind not in ROW_KINDS:
            _refuse("UNKNOWN_KIND", repr(kind))
        if not isinstance(payload, dict):
            _refuse("INVALID_PAYLOAD", "payload must be an object")
        payload = json.loads(_canonical(payload))
        _check_authority(payload)
        st = self.state()
        if kind == REGISTER:
            _validate_register(st, payload)
        elif kind == BUDGET:
            _validate_budget(st, payload)
        elif kind == PUBLISH:
            _validate_publish(st, payload)
        elif kind == ABSTAIN:
            _validate_abstain(st, payload)
        elif kind == RESOLVE:
            _validate_resolve(st, payload)
        elif kind == SCORE:
            _validate_score(self, st, payload)
        elif kind == NOGO:
            _validate_nogo(st, payload)
        existing = self.rows()
        prev_hash = existing[-1]["row_hash"] if existing else None
        row = {
            "seq": len(existing) + 1,
            "kind": kind,
            "written_at_utc": _now_utc(),
            "payload": payload,
            "prev_hash": prev_hash,
        }
        row["row_hash"] = _row_hash(row)
        self._write_line(row)
        _fold(self._incremental, row)
        _refresh_counts(self._incremental, row["seq"])
        return row

    def _write_line(self, row):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = _canonical(row) + "\n"
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
