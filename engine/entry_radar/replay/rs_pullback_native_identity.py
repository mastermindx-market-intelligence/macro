"""RS Pullback research inputs from the existing Terminal and identity readers.

This explicit entry point owns only the consumer join. R27 owns retained minute
decoding; R12 owns identity validity, selection and refusal. Native read objects
describe parser custody, not authentication. No file is read or written here,
no clock is supplied to an owner reader, and no source or product is admitted.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Mapping

from engine.entry_radar.replay import rs_pullback_launch_data as panel
from engine.entry_radar.replay import terminal_minute_observations as terminal
from engine.entry_radar.replay.identity_observation_snapshot import IdentitySnapshotRead
from lib.dataos.identity import IdentityError

INPUT_SCHEMA = "mastermind.rs_pullback_launch.phase1_owner_input.v1"
PANEL_SCHEMA = "mastermind.rs_pullback_launch.phase1_owner_panel.v1"
BINDING_SCHEMA = "mastermind.rs_pullback_launch.native_identity_binding.v1"


@dataclass(frozen=True, slots=True)
class NativeRoleReads:
    """One candidate/role's explicitly retained owner reads.

    The current Terminal snapshot is not implicitly enrolled. Earlier actual
    Terminal read objects may enroll its retained prefix. The identity read is
    chosen explicitly for this candidate/role; this adapter creates no second
    revision selector. None represents an honestly missing owner read.
    """

    terminal_read: terminal.TerminalMinuteSnapshot | None
    enrolled_terminal_reads: tuple[terminal.TerminalMinuteSnapshot, ...]
    identity_read: IdentitySnapshotRead | None


def _configuration(bundle: Mapping[str, Any],
                   owner_reads: Mapping[str, Mapping[str, NativeRoleReads]],
                   reader_identity: str) -> None:
    if not isinstance(bundle, Mapping) or bundle.get("schema") != INPUT_SCHEMA:
        raise panel.InputContractError("unsupported owner-read input schema")
    if bundle.get("window_policy_schema") not in (panel.INPUT_SCHEMA, panel.INPUT_V2_SCHEMA):
        raise panel.InputContractError("explicit v1 or v2 window policy required")
    if any(key in bundle for key in ("minutes", "terminal_minute_read_receipts")):
        raise panel.InputContractError("owner-read input cannot contain caller JSON observations")
    if not isinstance(reader_identity, str) or not reader_identity.strip():
        raise panel.InputContractError("configured owner reader identity required")
    symbols = bundle.get("required_symbols")
    if not isinstance(symbols, Mapping) or set(symbols) != set(panel.ROLES) or any(
        not isinstance(symbol, str) or not symbol or symbol.strip() != symbol
        for symbol in symbols.values()
    ):
        raise panel.InputContractError("freeze one exact symbol for each of the four roles")
    streams = bundle.get("streams", {})
    if not isinstance(streams, Mapping):
        raise panel.InputContractError("stream metadata must be an object")
    for meta in streams.values():
        if not isinstance(meta, Mapping):
            raise panel.InputContractError("stream metadata must be an object")
        if "identity" in meta or "security_id" in meta:
            raise panel.InputContractError("legacy identity metadata cannot enter owner-read input")
    candidates = bundle.get("candidates", [])
    if not isinstance(candidates, list) or any(not isinstance(item, Mapping) for item in candidates):
        raise panel.InputContractError("candidate population must be a list of objects")
    ids = [item.get("candidate_id") for item in candidates]
    if any(not isinstance(value, str) or not value for value in ids):
        raise panel.InputContractError("candidate identities must be nonempty strings")
    if not isinstance(owner_reads, Mapping) or not set(owner_reads) <= set(ids):
        raise panel.InputContractError("owner reads must name predeclared candidates")
    for roles in owner_reads.values():
        if not isinstance(roles, Mapping) or not set(roles) <= set(panel.ROLES):
            raise panel.InputContractError("owner reads must name the four input roles")
        for reads in roles.values():
            if not isinstance(reads, NativeRoleReads):
                raise panel.InputContractError("native evidence requires NativeRoleReads")
            if reads.terminal_read is not None and not isinstance(
                reads.terminal_read, terminal.TerminalMinuteSnapshot
            ):
                raise panel.InputContractError("native evidence requires a Terminal owner read")
            if type(reads.enrolled_terminal_reads) is not tuple or any(
                not isinstance(read, terminal.TerminalMinuteSnapshot)
                for read in reads.enrolled_terminal_reads
            ):
                raise panel.InputContractError("enrollment requires actual Terminal owner reads")
            if reads.identity_read is not None and not isinstance(reads.identity_read, IdentitySnapshotRead):
                raise panel.InputContractError("native evidence requires an identity owner read")


def _finish(report: dict[str, Any], rows: list[dict[str, Any]],
            security_id: str | None = None) -> panel._NativeRoleInput:
    report["binding_sha256"] = panel.digest(report)
    errors = (() if report["status"] == "BOUND" else
              ("IDENTITY_NOT_BOUND_AT_DECISION", "NATIVE_IDENTITY_" + report["status"]))
    # Canonical strings make the private role result immutable; materializing
    # them later copies original rows without changing or resealing any row.
    return panel._NativeRoleInput(
        panel.canonical(rows), panel.canonical(report), security_id, errors)


def _role_input(candidate: Mapping[str, Any], role: str, stream: str,
                opening: datetime, closing: datetime, cutoff: datetime, *,
                reads: NativeRoleReads | None, symbol: str,
                reader_identity: str) -> panel._NativeRoleInput:
    decision_at = panel._iso(cutoff)
    report: dict[str, Any] = {
        "schema": BINDING_SCHEMA, "candidate_id": candidate["candidate_id"],
        "role": role, "stream": stream, "event_session_date": candidate["session"],
        "decision_at": decision_at, "query": None,
        "terminal_observations": [], "terminal_read_receipts": [],
        "terminal_rows_sha256": panel.digest([]), "identity_resolution": None,
        "status": "UNAVAILABLE", "reason": "TERMINAL_MINUTES_UNAVAILABLE",
    }
    if reads is None or reads.terminal_read is None:
        return _finish(report, [])
    try:
        receipts = [read.receipt for read in reads.enrolled_terminal_reads]
        decoded = terminal.decode_terminal_minute_observations(
            reads.terminal_read, receipts, reader_identity=reader_identity,
            symbol=symbol, stream=stream, stream_metadata=None,
            cutoff=decision_at, output_schema=terminal.DECODE_SCHEMA_V2,
        )
        # A query must come from a visible row in the candidate's owner session.
        # Other sessions, display bars and empty capture headers cannot supply it.
        rows = [row for row in decoded["minutes"]
                if opening <= panel._clock(row["start"]) < closing]
    except panel.InputContractError:
        report.update(status="REFUSED", reason="TERMINAL_INPUT_INVALID")
        return _finish(report, [])
    if not rows:
        return _finish(report, [])
    queries = {(row["source_observation"]["source_vendor"],
                row["source_observation"]["source_symbol"]) for row in rows}
    report["terminal_rows_sha256"] = panel.digest(rows)
    report["terminal_observations"] = [
        {"receipt_sha256": row["receipt_sha256"], "revision_id": row["revision_id"],
         "owner_read_receipt_sha256": row["source_observation"]["owner_read_receipt_sha256"]}
        for row in rows
    ]
    selected_receipts = {row["source_observation"]["owner_read_receipt_sha256"] for row in rows}
    receipts_by_sha = {receipt["receipt_sha256"]: receipt for receipt in receipts
                       if receipt["receipt_sha256"] in selected_receipts}
    if set(receipts_by_sha) != selected_receipts:
        raise RuntimeError("Terminal decoder selected an unenrolled read receipt")
    report["terminal_read_receipts"] = [receipts_by_sha[key] for key in sorted(receipts_by_sha)]
    if len(queries) != 1:
        report.update(status="REFUSED", reason="CONFLICTING_SOURCE_QUERY")
        return _finish(report, rows)
    vendor, vendor_symbol = next(iter(queries))
    event_date = date.fromisoformat(candidate["session"])
    report["query"] = {"vendor": vendor, "vendor_symbol": vendor_symbol,
                       "event_session_date": event_date.isoformat()}
    if reads.identity_read is None:
        report["reason"] = "IDENTITY_READ_UNAVAILABLE"
        return _finish(report, rows)
    identity = reads.identity_read
    try:
        # Withhold a future input before alias_table() inspects its payload.
        # This only excludes evidence; R12 still validates/selects eligible reads.
        completed = identity.receipt.read_completed_at_utc_ns
        if type(completed) is not str or re.fullmatch(r"[1-9][0-9]{0,18}", completed) is None \
                or int(completed) > 2**63 - 1:
            raise IdentityError("identity read completion clock is invalid")
        if int(completed) > panel._epoch_ns(cutoff):
            report["reason"] = "IDENTITY_NOT_KNOWN_AT_DECISION"
            return _finish(report, rows)
        resolution = identity.alias_table().resolve_binding(
            vendor, vendor_symbol, event_date, decision_at=decision_at,
            snapshot_receipts=(identity.receipt,),
        )
        if resolution.status not in {"BOUND", "REFUSED", "UNAVAILABLE"}:
            raise RuntimeError("identity owner returned an unsupported disposition")
        if resolution.receipt_sha256 is not None:
            if resolution.receipt_sha256 != identity.receipt.receipt_sha256:
                raise RuntimeError("identity owner selected an unprovided snapshot")
            report["identity_read_receipt"] = identity.receipt.as_record()
    except (IdentityError, json.JSONDecodeError, UnicodeDecodeError):
        report.update(status="REFUSED", reason="IDENTITY_INPUT_INVALID")
        return _finish(report, rows)
    # Preserve the complete native value, including deliberate null fields.
    # A null receipt does not expose the supplied read's otherwise future facts.
    report.update(status=resolution.status, reason=resolution.reason,
                  identity_resolution=asdict(resolution))
    if resolution.status == "BOUND" and not resolution.security_id:
        raise RuntimeError("bound identity owner result omitted its security identity")
    return _finish(report, rows, resolution.security_id if resolution.status == "BOUND" else None)


def _inventory(owner_reads: Mapping[str, Mapping[str, NativeRoleReads]]) -> dict[str, Any]:
    """Hash opaque supplied inputs only for panel-level replay diagnostics.

    Do not semantically validate a future identity receipt via as_record() here.
    Its raw dataclass fields and opaque byte hashes cannot affect candidate seals.
    These diagnostics are consistency information, not read authentication.
    """
    def sha(raw: bytes) -> str:
        return hashlib.sha256(raw).hexdigest()

    def terminal_record(read: terminal.TerminalMinuteSnapshot | None) -> dict[str, Any] | None:
        if read is None:
            return None
        return {"snapshot_bytes_sha256": sha(read.raw_bytes),
                "receipt_bytes_sha256": sha(read.receipt_json.encode("utf-8", errors="surrogatepass"))}

    result = {}
    for candidate_id, roles in owner_reads.items():
        result[candidate_id] = {}
        for role, reads in roles.items():
            identity = reads.identity_read
            identity_record = None if identity is None else {
                "snapshot_receipt_bytes_sha256": sha(identity.snapshot.receipt_bytes),
                "artifact_bytes_sha256": [[name, sha(raw)] for name, raw in identity.snapshot.artifact_bytes],
                "alias_bytes_sha256": sha(identity.snapshot.alias_json),
                "master_bytes_sha256": sha(identity.snapshot.master_json),
                "consumer_receipt_fields": asdict(identity.receipt),
            }
            result[candidate_id][role] = {
                "terminal_read": terminal_record(reads.terminal_read),
                "enrolled_terminal_reads": [terminal_record(read) for read in reads.enrolled_terminal_reads],
                "identity_read": identity_record,
            }
    return result


def build_input_panel_from_owner_reads(
    bundle: Mapping[str, Any], *,
    owner_reads: Mapping[str, Mapping[str, NativeRoleReads]], reader_identity: str,
) -> dict[str, Any]:
    """Join actual owner reads without changing legacy JSON v1/v2 behavior.

    Use actual objects returned by read_terminal_minute_snapshot and
    read_identity_snapshot. Supply reads separately for every predeclared
    candidate/role; absent reads remain unavailable. The frozen required_symbols
    constrain source decoding but never substitute for a visible source query.

    Calendar/window guards run first. All evidence uses the panel's actual,
    conservatively microsecond-representable decision cutoff, never its feature
    anchor. Exact source row bytes/seals and native refusal values survive the
    join. Basis, first-seen, revision, context and admission guards still apply.
    """
    _configuration(bundle, owner_reads, reader_identity)

    def provide(candidate, role, stream, opening, closing, cutoff):
        return _role_input(
            candidate, role, stream, opening, closing, cutoff,
            reads=owner_reads.get(candidate["candidate_id"], {}).get(role),
            symbol=bundle["required_symbols"][role], reader_identity=reader_identity,
        )

    prepared = {**bundle, "schema": bundle["window_policy_schema"]}
    result = panel._build_input_panel(prepared, native_role_provider=provide)
    inventory = _inventory(owner_reads)
    result.update(
        schema=PANEL_SCHEMA, window_policy_schema=bundle["window_policy_schema"],
        owner_read_inputs=inventory,
        input_bundle_sha256=panel.digest(
            {"bundle": bundle, "owner_reads": inventory, "reader_identity": reader_identity}),
    )
    return result
