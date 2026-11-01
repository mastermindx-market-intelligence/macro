#!/usr/bin/env python3
"""Validator for EVAL-1 partition clock receipts (stdlib + nyse_calendar only)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date as date_cls
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[3]
_root_s = str(ROOT)
if _root_s not in sys.path:
    sys.path.insert(0, _root_s)

import lib.nyse_calendar as nyse_calendar

SCHEMA = "itp.eval1_partition_clock.v1"
REGISTRATION_ID = "K3E-EVAL-1-V1"
VERDICTS = (
    "EVAL1_NOT_ADMITTED",
    "F_DEV_OPEN",
    "PURGE_1",
    "F_VAL_OPEN",
    "PURGE_2",
    "F_HOLD_OPEN",
    "PROSPECTIVE_SHADOW",
)
LABELS = {
    "financial_influence": False,
    "k3e_admissible": False,
    "promotion_eligible": False,
    "promotion_bearing": False,
    "score": None,
    "rank": None,
    "issuer_clock": "REPO_HISTORY_AVAILABILITY",
}
REFUSAL_KEYS = frozenset(
    {
        "schema",
        "registration_id",
        "verdict",
        "verdict_enum",
        "rev",
        "rev_commit_time",
        "labels",
        "admission",
        "gaps",
    }
)
ADMITTED_TOP = frozenset(
    {
        "schema",
        "registration_id",
        "verdict",
        "verdict_enum",
        "rev",
        "rev_commit_time",
        "labels",
        "admission",
        "source",
        "calendar",
        "corpus",
        "identity",
        "episode_starts",
        "count_unit",
        "partitions",
        "prospective_shadow_after_session",
        "cross_check",
        "gaps",
    }
)
FORBIDDEN_KEY_RE = re.compile(r"direction|label|up|down|flat|loss|brier", re.I)
FORBIDDEN_TOKENS = frozenset(
    {"direction", "label", "labels", "up", "down", "flat", "mixed", "loss", "brier"}
)
NO_OUTCOME_SENTENCE = (
    "No outcome field is read or emitted; financial_influence, k3e_admissible and promotion_eligible are false."
)
FLOOR = 100


def _session_after(d: date_cls) -> date_cls:
    cur = d
    for _ in range(10):
        cur = cur.fromordinal(cur.toordinal() + 1)
        if nyse_calendar.is_session(cur):
            return cur
    raise ValueError("no session after " + d.isoformat())


def _walk_keys(node: object, path: str, out: list[str]) -> None:
    if isinstance(node, dict):
        for key, val in node.items():
            if path == "" and key == "labels":
                pass
            elif key == "labels" and path != "":
                out.append(path + ".labels nested labels key forbidden")
            elif FORBIDDEN_KEY_RE.search(str(key)) and not (path == "" and key == "labels"):
                out.append(f"forbidden key {path}.{key}")
            if key in ("financial_influence", "k3e_admissible", "promotion_eligible", "promotion_bearing"):
                if val is not False:
                    out.append(f"{path}.{key} must be False")
            if key in ("score", "rank") and val is not None:
                out.append(f"{path}.{key} must be None")
            _walk_keys(val, path + "." + str(key) if path else str(key), out)
    elif isinstance(node, list):
        for i, val in enumerate(node):
            _walk_keys(val, f"{path}[{i}]", out)


def _walk_string_values(node: object, out: list[str]) -> None:
    if isinstance(node, dict):
        for key, val in node.items():
            if key == "labels" and isinstance(val, dict):
                continue
            _walk_string_values(val, out)
    elif isinstance(node, list):
        for val in node:
            _walk_string_values(val, out)
    elif isinstance(node, str):
        for tok in re.split(r"[^A-Za-z0-9]+", node):
            if tok.lower() in FORBIDDEN_TOKENS:
                out.append(f"forbidden token in string: {tok}")


def _verdict_from_partitions(parts: dict) -> str:
    if parts["F_HOLD"]["state"] == "CLOSED":
        return "PROSPECTIVE_SHADOW"
    if parts["F_HOLD"]["state"] == "OPEN":
        return "F_HOLD_OPEN"
    if parts["PURGE_2"]["state"] == "OPEN":
        return "PURGE_2"
    if parts["F_VAL"]["state"] == "OPEN":
        return "F_VAL_OPEN"
    if parts["PURGE_1"]["state"] == "OPEN":
        return "PURGE_1"
    if parts["F_DEV"]["state"] == "OPEN":
        return "F_DEV_OPEN"
    return "PROSPECTIVE_SHADOW"


def violations(doc: dict, raw_bytes: bytes | None = None, md_text: str | None = None) -> list[str]:
    out: list[str] = []
    if raw_bytes is not None:
        expect = json.dumps(doc, sort_keys=True, indent=1, ensure_ascii=True).encode("utf-8") + b"\n"
        if raw_bytes != expect:
            out.append("raw_bytes do not match canonical json")
    if doc.get("schema") != SCHEMA:
        out.append("schema mismatch")
    if doc.get("registration_id") != REGISTRATION_ID:
        out.append("registration_id mismatch")
    if doc.get("verdict") not in VERDICTS:
        out.append("verdict not in enum")
    if doc.get("verdict_enum") != list(VERDICTS):
        out.append("verdict_enum mismatch")
    if set(doc.get("labels", {}).keys()) != set(LABELS.keys()):
        out.append("labels keys mismatch")
    else:
        for k, v in LABELS.items():
            got = doc["labels"][k]
            if v is None or isinstance(v, bool):
                if got is not v:
                    out.append(f"labels.{k} must use identity is check")
            elif got != v:
                out.append(f"labels.{k} mismatch")

    _walk_keys(doc, "", out)
    _walk_string_values(doc, out)

    verdict = doc.get("verdict")
    if verdict == "EVAL1_NOT_ADMITTED":
        if set(doc.keys()) != REFUSAL_KEYS:
            out.append("refusal top-level keys mismatch")
        adm = doc.get("admission")
        if set(adm.keys()) != {"admitted", "refusal_codes", "source_main_commit"}:
            out.append("refusal admission keys mismatch")
        if adm.get("admitted") is not False:
            out.append("refusal admitted must be False")
        codes = adm.get("refusal_codes")
        if not isinstance(codes, list) or not codes:
            out.append("refusal_codes must be non-empty list")
        else:
            for c in codes:
                if not isinstance(c, str) or not re.fullmatch(r"[A-Z0-9_]+", c):
                    out.append("invalid refusal code")
        return out

    if set(doc.keys()) != ADMITTED_TOP:
        out.append("admitted top-level keys mismatch")
    adm = doc.get("admission", {})
    if adm.get("admitted") is not True or adm.get("refusal_codes") != []:
        out.append("admission must be admitted with empty refusal_codes")
    boundary = adm.get("boundary_session")
    if not isinstance(boundary, str) or not nyse_calendar.is_session(date_cls.fromisoformat(boundary)):
        out.append("boundary_session must be a session")
    parts = doc.get("partitions", {})
    if set(parts.keys()) != {"F_DEV", "PURGE_1", "F_VAL", "PURGE_2", "F_HOLD"}:
        out.append("partitions keys mismatch")
    if parts.get("F_DEV", {}).get("start_session") != boundary:
        out.append("F_DEV start must equal boundary")

    counting_keys = {"state", "status", "floor", "start_session", "close_session", "primary_n", "primary_n_of_floor", "secondary_n"}
    purge_keys = {"state", "sessions", "start_session", "end_session"}
    for name in ("F_DEV", "F_VAL", "F_HOLD"):
        if set(parts[name].keys()) != counting_keys:
            out.append(f"{name} counting keys mismatch")
    for name in ("PURGE_1", "PURGE_2"):
        if set(parts[name].keys()) != purge_keys:
            out.append(f"{name} purge keys mismatch")

    for name in ("F_DEV", "F_VAL", "F_HOLD"):
        p = parts[name]
        st, status, pn = p["state"], p["status"], p["primary_n"]
        if p["primary_n_of_floor"] != f"{pn}/{FLOOR}":
            out.append(f"{name} primary_n_of_floor mismatch")
        if st == "CLOSED":
            if status != "FLOOR_MET" or pn < FLOOR:
                out.append(f"{name} CLOSED invariants")
        elif st == "OPEN":
            if status != "INSUFFICIENT_EPISODE_N" or pn >= FLOOR or p["close_session"] is not None:
                out.append(f"{name} OPEN invariants")
        elif st == "NOT_STARTED":
            if pn != 0 or p["secondary_n"] != 0 or p["close_session"] is not None:
                out.append(f"{name} NOT_STARTED invariants")

    if parts["F_DEV"]["secondary_n"] < parts["F_DEV"]["primary_n"]:
        out.append("F_DEV secondary_n < primary_n")

    if doc.get("cross_check") != "engine.k3e_eval1_forward.assign_partitions AGREES":
        out.append("cross_check string mismatch")

    if _verdict_from_partitions(parts) != doc.get("verdict"):
        out.append("verdict inconsistent with partition states")

    def purge_span_ok(prev_close: str | None, purge: dict, next_start: str | None) -> bool:
        if purge["state"] == "NOT_STARTED":
            return True
        if not prev_close or not purge.get("start_session") or not purge.get("end_session"):
            return False
        ps = date_cls.fromisoformat(purge["start_session"])
        pe = date_cls.fromisoformat(purge["end_session"])
        if ps != _session_after(date_cls.fromisoformat(prev_close)):
            return False
        if len(nyse_calendar.sessions_between(ps, pe)) != 63:
            return False
        if next_start is not None and next_start != _session_after(pe).isoformat():
            return False
        return True

    if not purge_span_ok(parts["F_DEV"]["close_session"], parts["PURGE_1"], parts["F_VAL"]["start_session"]):
        out.append("PURGE_1 span mismatch")
    if not purge_span_ok(parts["F_VAL"]["close_session"], parts["PURGE_2"], parts["F_HOLD"]["start_session"]):
        out.append("PURGE_2 span mismatch")

    if md_text is not None:
        if raw_bytes is not None and hashlib_sha256(raw_bytes) not in md_text:
            out.append("md missing sha256")
        if NO_OUTCOME_SENTENCE not in md_text:
            out.append("md missing no-outcome sentence")
        for tok in ("up", "down", "flat", "mixed", "direction", "brier", "loss"):
            if re.search(rf"\b{tok}\b", md_text, re.I):
                out.append(f"md forbidden word {tok}")

    return out


def hashlib_sha256(b: bytes) -> str:
    import hashlib

    return hashlib.sha256(b).hexdigest()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", required=False)
    p.add_argument("--md", default=None)
    args = p.parse_args(argv)
    if not args.check:
        p.print_help()
        return 0
    try:
        path = Path(args.check)
        raw = path.read_bytes()
        doc = json.loads(raw.decode("utf-8"))
        md_text = Path(args.md).read_text(encoding="utf-8") if args.md else None
    except (OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    errs = violations(doc, raw_bytes=raw, md_text=md_text)
    if errs:
        for e in errs:
            print(e)
        return 1
    print(f"OK {args.check}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
