#!/usr/bin/env python3
"""Check the R4 dry-run receipt V2 (pre-EVAL-1 N-floor admission census). Standard library only.

Fails closed on: any of financial_influence / k3e_admissible / promotion_eligible not false
anywhere in the document, a non-null score or rank anywhere, a clock on or after the EVAL-1
boundary 2026-10-07T13:30Z, a known security_master version committed later than its
cutoff minus 24 hours, a missing or altered label on the header or on any row, a verdict
outside the enum, an effect field on a below-floor or sensitivity cell, and count arithmetic
that does not add up.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "itp.r4_dryrun_receipt.v2"
RECEIPT_ID = "R4_DRYRUN_RECEIPT_V2_2026-10-07"
BOUNDARY = dt.datetime(2026, 10, 7, 13, 30, tzinfo=dt.timezone.utc)
LAST_SESSION = dt.date(2026, 10, 6)
GUARD = dt.timedelta(hours=24)
CLOSE_UTC_HOUR = 20
BT = chr(96)
HEX40 = re.compile(r"^[0-9a-f]{40}\Z")
HEX64 = re.compile(r"^[0-9a-f]{64}\Z")
BLOCKED = re.compile(r"^R4_BLOCKED_[A-Z0-9_]+\Z")
VERDICTS = (
    "R4_ADMISSIBLE_DESCRIPTIVE",
    "R4_INSUFFICIENT_N_PRE_BOUNDARY",
    "R4_BLOCKED_NO_OWNER_RESIDUAL_FRAME",
    "R4_BLOCKED_NO_ISSUER_EPISODES",
    "R4_BLOCKED_CALENDAR_MISMATCH",
)
HORIZONS = (5, 21, 63)
SCOPES = ("overall", "metric=EPS", "metric=revenue", "period=0q", "period=+1q", "period=0y", "period=+1y")
FLOORS = dict(overall=100, subgroup=25)
ROLES = dict(S="PRIMARY", L="SENSITIVITY_VIOLATES_20_QUIET_SESSION_LAW")
STATUSES = ("ESTIMATED_DESCRIPTIVE", "NOT_ESTIMATED_BELOW_FLOOR", "NOT_ESTIMATED_SENSITIVITY_COUNTS_ONLY")
LABELS = dict(
    era="INTER_ERA_GAP",
    era_note="between the EVAL-0 holdout end 2026-08-21 and the EVAL-1 boundary 2026-10-07T13:30Z",
    promotion_bearing=False,
    cohort_filter="COHORT_FILTER_UNAVAILABLE",
    coupling_ceiling="COMPONENTS_ONLY",
    rights="UNKNOWN",
    financial_influence=False,
    k3e_admissible=False,
    promotion_eligible=False,
    score=None,
    rank=None,
    issuer_clock="REPO_HISTORY_AVAILABILITY",
)
FALSE_KEYS = ("financial_influence", "k3e_admissible", "promotion_eligible", "promotion_bearing")
NULL_KEYS = ("score", "rank")
ROOT_KEYS = (
    "schema", "receipt_id", "question", "verdict", "verdict_reason", "verdict_enum", "verdict_rule",
    "labels", "not_promotion_bearing", "boundary", "source", "corpus", "identity", "episode_law",
    "calendar", "mkt1", "shortfall", "cells", "v1_untouched", "trial_consumption",
)
CORPUS_CLOCKS = (
    "max_system_observed_at", "max_provider_observed_at", "max_decision_cutoff",
    "max_attempt_attempted_at", "max_attempt_completed_at",
)


def _when(value: object):
    if not isinstance(value, str) or not value:
        return None
    try:
        out = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return out if out.tzinfo is not None else None


def _day(value: object):
    if not isinstance(value, str):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def _int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _hex(pattern, value: object) -> bool:
    return isinstance(value, str) and bool(pattern.match(value))


def _walk(node: object, path: str, found: list) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            here = path + "." + str(key)
            if key in FALSE_KEYS and value is not False:
                found.append(here + " must be false")
            if key in NULL_KEYS and value is not None:
                found.append(here + " must be null (no score, no rank)")
            _walk(value, here, found)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk(value, path + "[" + str(index) + "]", found)


def _header(doc: dict, need) -> None:
    for key in ROOT_KEYS:
        need(key in doc, "missing key " + key)
    need(doc.get("schema") == SCHEMA, "schema must be " + SCHEMA)
    need(doc.get("receipt_id") == RECEIPT_ID, "receipt_id must be " + RECEIPT_ID)
    need(doc.get("not_promotion_bearing") is True, "not_promotion_bearing must be true")
    need(doc.get("trial_consumption") == "NONE", "trial_consumption must be NONE")
    verdict = doc.get("verdict")
    need(isinstance(verdict, str) and (verdict in VERDICTS or bool(BLOCKED.match(verdict))),
         "verdict must be in the enum or be an R4_BLOCKED_ reason")
    need(doc.get("verdict_enum") == list(VERDICTS), "verdict_enum must list the frozen verdicts")
    need(isinstance(doc.get("verdict_reason"), str) and bool(str(doc.get("verdict_reason")).strip()),
         "verdict_reason must be a non-empty string")
    need(doc.get("labels") == LABELS, "header labels must equal the frozen label set")

    boundary = doc.get("boundary")
    need(isinstance(boundary, dict), "boundary must be an object")
    if isinstance(boundary, dict):
        need(_when(boundary.get("eval1_boundary")) == BOUNDARY, "boundary.eval1_boundary must be 2026-10-07T13:30Z")
        need(_day(boundary.get("last_pre_boundary_session")) == LAST_SESSION,
             "boundary.last_pre_boundary_session must be 2026-10-06")

    source = doc.get("source")
    need(isinstance(source, dict), "source must be an object")
    if isinstance(source, dict):
        need(_hex(HEX40, source.get("revision")), "source.revision must be 40 hex characters")
        blobs = source.get("blobs")
        need(isinstance(blobs, dict) and bool(blobs), "source.blobs must be a non-empty object")
        if isinstance(blobs, dict):
            for name, blob in blobs.items():
                need(_hex(HEX40, blob), "source.blobs." + str(name) + " must be 40 hex")

    calendar = doc.get("calendar")
    need(isinstance(calendar, dict) and _day(calendar.get("end")) == LAST_SESSION,
         "calendar.end must be the last pre-boundary session")


def _clocks(doc: dict, need) -> None:
    corpus = doc.get("corpus")
    need(isinstance(corpus, dict), "corpus must be an object")
    if isinstance(corpus, dict):
        for key in CORPUS_CLOCKS:
            when = _when(corpus.get(key))
            need(when is not None and when < BOUNDARY, "corpus." + key + " must be a clock strictly before the boundary")
        sessions = corpus.get("cutoff_sessions")
        need(isinstance(sessions, dict) and bool(sessions), "corpus.cutoff_sessions must be a non-empty object")
        if isinstance(sessions, dict):
            for day in sessions:
                session = _day(day)
                need(session is not None and session <= LAST_SESSION,
                     "corpus.cutoff_sessions " + repr(day) + " is on or after the boundary session")
        need(isinstance(corpus.get("rows_dropped_by_boundary_rule"), dict),
             "corpus.rows_dropped_by_boundary_rule must be an object")

    identity = doc.get("identity")
    need(isinstance(identity, dict), "identity must be an object")
    if not isinstance(identity, dict):
        return
    need(identity.get("issuer_clock") == "REPO_HISTORY_AVAILABILITY",
         "identity.issuer_clock must be REPO_HISTORY_AVAILABILITY")
    need(identity.get("known_version_guard_hours") == 24, "identity.known_version_guard_hours must be 24")
    known = identity.get("known_version_by_cutoff_session")
    need(isinstance(known, dict) and bool(known), "identity.known_version_by_cutoff_session must be non-empty")
    if not isinstance(known, dict):
        return
    for day, version in known.items():
        session = _day(day)
        ok = isinstance(version, dict) and session is not None
        need(ok, "known version for " + repr(day) + " must be an object keyed by a session date")
        if not ok:
            continue
        cutoff = dt.datetime(session.year, session.month, session.day, CLOSE_UTC_HOUR, tzinfo=dt.timezone.utc)
        committed = _when(version.get("committer_time"))
        need(session <= LAST_SESSION, "known version session " + day + " is on or after the boundary")
        need(committed is not None and committed <= cutoff - GUARD,
             "known version for " + day + " committed later than its cutoff minus 24h")
        for key in ("blob", "commit"):
            need(_hex(HEX40, version.get(key)), "known version for " + day + ": " + key + " must be 40 hex")


def _mkt1(doc: dict, need):
    mkt = doc.get("mkt1")
    need(isinstance(mkt, dict), "mkt1 must be an object")
    if not isinstance(mkt, dict):
        return None
    path_used = mkt.get("path_used")
    need(path_used in ("a", "b", "none"), "mkt1.path_used must be a, b or none")
    path_a = mkt.get("path_a")
    need(isinstance(path_a, dict), "mkt1.path_a must be an object")
    if isinstance(path_a, dict):
        when = _when(path_a.get("generated_at"))
        need(when is not None and when < BOUNDARY, "mkt1.path_a.generated_at must be before the boundary")
        last = _day(path_a.get("last_session"))
        need(last is not None and last <= LAST_SESSION, "mkt1.path_a.last_session must be on or before 2026-10-06")
    path_b = mkt.get("path_b")
    if path_used != "b":
        need(path_b is None, "mkt1.path_b must be null unless path b is used")
        return path_used
    need(isinstance(path_b, dict), "mkt1.path_b must be an object when path b is used")
    if not isinstance(path_b, dict):
        return path_used
    last = _day(path_b.get("frame_last_session"))
    need(last is not None and last <= LAST_SESSION, "mkt1.path_b.frame_last_session must be on or before 2026-10-06")
    need(_day(path_b.get("sliced_to")) == LAST_SESSION, "mkt1.path_b.sliced_to must be 2026-10-06")
    cross = path_b.get("calendar_cross_check")
    need(isinstance(cross, dict) and isinstance(cross.get("equal"), bool),
         "mkt1.path_b.calendar_cross_check.equal must be a boolean")
    snap = path_b.get("snapshot")
    need(isinstance(snap, dict), "mkt1.path_b.snapshot must be an object")
    if isinstance(snap, dict):
        rec = snap.get("recomputed")
        need(isinstance(rec, dict) and _hex(HEX64, rec.get("manifest_sha256")),
             "mkt1.path_b.snapshot.recomputed.manifest_sha256 must be 64 hex")
        need(isinstance(rec, dict) and snap.get("manifest_sha256") == rec.get("manifest_sha256"),
             "mkt1.path_b.snapshot manifest_sha256 must equal the recomputed manifest")
        for key in ("copy_started_at", "copy_finished_at"):
            when = _when(snap.get(key))
            need(when is not None and when < BOUNDARY, "mkt1.path_b.snapshot." + key + " must be before the boundary")
    return path_used


COUNTS = ("effective_n", "complete", "right_censored_at_boundary", "complete_residual_available",
          "shortfall_vs_floor", "episode_identities")
ROW_KEYS = frozenset(COUNTS + (
    "variant", "role", "h", "scope", "floor", "anchor_sessions", "residual_unavailable_by_reason",
    "complete_meets_floor", "meets_floor", "effect_status", "labels",
))


def _row(prefix: str, row: dict, need) -> bool:
    variant, h, scope = row.get("variant"), row.get("h"), row.get("scope")
    need(row.get("role") == ROLES.get(variant), prefix + ".role must match its variant")
    need(row.get("labels") == LABELS, prefix + ".labels must equal the frozen label set")
    floor = FLOORS["overall"] if scope == "overall" else FLOORS["subgroup"]
    need(row.get("floor") == floor, prefix + ".floor must be " + str(floor))
    for name in COUNTS:
        need(_int(row.get(name)), prefix + "." + name + " must be a non-negative integer")
    if not all(_int(row.get(name)) for name in COUNTS):
        return False
    eff, comp, cens = row["effective_n"], row["complete"], row["right_censored_at_boundary"]
    avail = row["complete_residual_available"]
    need(comp + cens == eff, prefix + ": complete + right_censored must equal effective_n")
    need(avail <= comp, prefix + ": residual-available cannot exceed complete")
    need(eff <= row["episode_identities"], prefix + ": effective_n cannot exceed episode identities")
    need(row["shortfall_vs_floor"] == max(0, floor - avail), prefix + ".shortfall_vs_floor arithmetic")
    need(row.get("complete_meets_floor") is (comp >= floor), prefix + ".complete_meets_floor arithmetic")
    meets = variant == "S" and avail >= floor
    need(row.get("meets_floor") is meets, prefix + ".meets_floor arithmetic")
    unavailable = row.get("residual_unavailable_by_reason")
    need(isinstance(unavailable, dict) and all(_int(v) for v in unavailable.values())
         and sum(unavailable.values()) == comp - avail,
         prefix + ".residual_unavailable_by_reason must account for complete minus available")
    anchors = row.get("anchor_sessions")
    good = isinstance(anchors, dict) and all(
        _day(k) is not None and _day(k) <= LAST_SESSION and _int(v) for k, v in anchors.items())
    need(good and sum(anchors.values()) == eff,
         prefix + ".anchor_sessions must be pre-boundary sessions summing to effective_n")
    status = row.get("effect_status")
    need(status in STATUSES, prefix + ".effect_status unknown")
    if variant != "S":
        want = "NOT_ESTIMATED_SENSITIVITY_COUNTS_ONLY"
    elif meets:
        want = "ESTIMATED_DESCRIPTIVE"
    else:
        want = "NOT_ESTIMATED_BELOW_FLOOR"
    need(status == want, prefix + ".effect_status must be " + want)
    extra = sorted(k for k in row if k not in ROW_KEYS)
    if want == "ESTIMATED_DESCRIPTIVE":
        need(isinstance(row.get("effect"), dict) and row["effect"].get("n") == avail,
             prefix + ".effect must summarise exactly the available residuals")
        need(extra == ["effect"], prefix + " carries unexpected fields " + repr(extra))
    else:
        need(not extra, prefix + " carries effect or other fields on a cell that is not at the floor: " + repr(extra))
    return meets


def _cells(doc: dict, need, path_used) -> None:
    cells = doc.get("cells")
    need(isinstance(cells, list) and len(cells) == 2 * len(HORIZONS) * len(SCOPES),
         "cells must hold one row per (variant, h, scope)")
    if not isinstance(cells, list):
        return
    seen = set()
    s_rows = dict()
    for index, row in enumerate(cells):
        prefix = "cells[" + str(index) + "]"
        need(isinstance(row, dict), prefix + " must be an object")
        if not isinstance(row, dict):
            continue
        variant, h, scope = row.get("variant"), row.get("h"), row.get("scope")
        need(variant in ROLES and h in HORIZONS and scope in SCOPES, prefix + " has an unknown variant/h/scope")
        key = (variant, h, scope)
        need(key not in seen, prefix + " duplicates " + repr(key))
        seen.add(key)
        meets = _row(prefix, row, need)
        if variant == "S":
            s_rows.setdefault(h, []).append(meets)

    shortfall = doc.get("shortfall")
    fields = ("h", "scope", "floor", "effective_n", "complete", "complete_residual_available",
              "shortfall_vs_floor", "meets_floor")
    mine = [dict((f, r.get(f)) for f in fields) for r in cells if isinstance(r, dict) and r.get("variant") == "S"]
    need(shortfall == mine, "shortfall table must mirror the S cells")

    verdict = doc.get("verdict")
    admissible = [h for h, flags in s_rows.items() if len(flags) == len(SCOPES) and all(flags)]
    if verdict == "R4_ADMISSIBLE_DESCRIPTIVE":
        need(bool(admissible), "verdict ADMISSIBLE needs an h with every S cell at its floor")
        need(path_used in ("a", "b"), "verdict ADMISSIBLE needs an owner residual frame")
    elif verdict == "R4_INSUFFICIENT_N_PRE_BOUNDARY":
        need(not admissible, "verdict INSUFFICIENT contradicts an h with every S cell at its floor")


def _violations(doc: object) -> list:
    found = []

    def need(ok: bool, message: str) -> None:
        if not ok:
            found.append(message)

    need(isinstance(doc, dict), "root is not an object")
    if not isinstance(doc, dict):
        return found
    _walk(doc, "root", found)
    _header(doc, need)
    _clocks(doc, need)
    path_used = _mkt1(doc, need)
    _cells(doc, need, path_used)
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", required=True, help="path to R4_DRYRUN_RECEIPT_V2_2026-10-07.json")
    parser.add_argument("--md", default=None, help="optional rendered Markdown; must cite the JSON sha256")
    args = parser.parse_args(argv)
    path = Path(args.check)
    try:
        raw = path.read_bytes()
        doc = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print("unreadable receipt: " + str(exc))
        return 1
    found = _violations(doc)
    digest = hashlib.sha256(raw).hexdigest()
    if args.md:
        try:
            text = Path(args.md).read_text(encoding="utf-8")
        except OSError as exc:
            found.append("unreadable markdown: " + str(exc))
        else:
            if ("sha256 " + BT + digest + BT) not in text:
                found.append("markdown does not cite the JSON sha256")
            if (BT + str(doc.get("verdict")) + BT) not in text:
                found.append("markdown does not state the verdict")
    if found:
        for item in found:
            print(item)
        return 1
    s_cells = [r for r in doc["cells"] if r["variant"] == "S"]
    print("ok %s: verdict=%s sha256=%s s_cells=%d at_floor=%d mkt1_path=%s "
          "financial_influence=false k3e_admissible=false promotion_eligible=false" % (
              path.name, doc["verdict"], digest, len(s_cells),
              sum(1 for r in s_cells if r["meets_floor"]), doc["mkt1"]["path_used"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
