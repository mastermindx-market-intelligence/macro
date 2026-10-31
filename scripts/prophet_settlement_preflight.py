"""V4-A2 issuer-side source qualification preflight (deterministic, read-only).

Binds the exact SOURCE evidence a ``prophet.settlement_manifest/v1`` (masterplan
§18.2) would later cite, and refuses with explicit typed ``NOT_SETTLED`` reason
codes when any leg is unqualified:

* the FULL build-owned population inventory (path + raw bytes for every file in
  the nightly step's closed allowlist — never the changed-only delta TSV);
* the frozen origination source board (snapshot/bundle/live triple equality and
  durable gzip recovery, same semantics as the nightly receipt step);
* the final producer index bytes including the genuine ``computed_at`` clock
  stamped by ``scripts/build_prophet.py`` at the index-write boundary;
* a separately qualified incumbent GMI ThemeState immutable current-generation
  receipt: the accepted generation family is proven immutable and current
  through the incumbent owner (``engine/neuralweb/theme_state_generation*`` /
  ``engine/theme_graph/theme_state_production``), and any owner-issued read
  receipt supplied via ``--gmi-receipt`` is verified detached against that
  exact family plan witness. The descriptive
  ``data/neuralweb/theme_state.json`` shadow is never read, and this module
  never carries a rights verifier or mints a receipt of its own.

This preflight is an instrument, not an authority. It never issues a
``bundle_id``, never marks anything accepted or settled, never writes under
``site/`` or ``data/``, and carries no private payload (paths, hashes and
counts only). Its receipt is written to the caller-supplied runner-local path
(typically ``$RUNNER_TEMP``). No wall clock is invented: the only timestamps
bound here are bytes that already exist in the evidence. In the nightly step it
runs as an alarm, never a gate: a refusal never flips the checkpoint contract.

Refusal classes (closed vocabulary): inventory missing/population changed, path
not normalized/missing, symlink, bytes changed after freeze, index clock
missing/unqualified, split checkpoint (delta TSV vs inventory vs live
disagreement), and GMI accepted-reference missing/pending/unqualified, with
incumbent owner refusal reasons passed through under a ``GMI_`` prefix.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from scripts.prophet_output_inventory import (
    CANDIDATE_STORE_DIR,
    BOARD_REL,
    INDEX_REL,
    canonical_json,
    candidate_store_entries,
    digest,
    snapshot,
    store_sha256,
)

SCHEMA = "prophet.accepted_source_preflight/v1"
COMPUTED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Production qualification markers the incumbent GMI owner still stamps onto
# every available read (WS-GMI-THEME-GRAPH W3B in progress). A receipt carrying
# either is, by the owner's own validator, not a production qualification.
GMI_UNQUALIFIED_CODES = ("D2E_NOT_QUALIFIED", "CONTROLLED_TEST_ONLY")

STATUS_REFUSED = "NOT_SETTLED"
STATUS_QUALIFIED = "QUALIFIED_SOURCE_PREFLIGHT"

AUTHORITY_CAPS = {
    "ranking": False,
    "gating": False,
    "sizing": False,
    "insertion": False,
    "origination": False,
    "escalation": False,
    "trade": False,
    "predictive": False,
    "may_publish": False,
}


class InfrastructureError(Exception):
    """The preflight could not produce its typed receipt at all."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _normalized_rel(path: str) -> bool:
    """Incumbent checkpoint rule: normalized repository-relative paths only."""
    fenced = f"/{path}/"
    return (
        not path.startswith("/")
        and "\\" not in path
        and "/../" not in fenced
        and "/./" not in fenced
        and "//" not in fenced
    )


def _read_json(path: Path):
    """Read JSON evidence, refusing to invent content for missing bytes."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def _leg(refused_codes: list[str], detail: dict | None = None) -> dict:
    return {
        "status": "REFUSED" if refused_codes else "QUALIFIED",
        "reason_codes": list(refused_codes),
        "detail": detail or {},
    }


def _bind_inventory(root: Path, inventory_path: Path, persisted):
    """Full-population leg: persisted nightly inventory vs re-derived live bytes."""
    if persisted is None:
        code = "INVENTORY_MISSING" if not inventory_path.exists() else "INVENTORY_UNREADABLE"
        return _leg([code], {"sha256": None, "file_count": None})
    reasons: list[str] = []
    bad_paths = sorted(rel for rel in persisted if not isinstance(rel, str) or not _normalized_rel(rel))
    if bad_paths:
        reasons.append("PATH_NOT_NORMALIZED")
    try:
        live = snapshot(root)
    except RuntimeError as exc:
        return _leg(["SYMLINK_REFUSED"], {"sha256": None, "file_count": len(persisted),
                                          "detail_message": str(exc)})
    added = sorted(set(live) - set(persisted))
    removed = sorted(set(persisted) - set(live))
    changed = sorted(
        rel
        for rel, fingerprint in live.items()
        if rel in persisted and persisted[rel] != fingerprint
    )
    if added or removed or changed:
        reasons.append("INVENTORY_POPULATION_CHANGED")
    detail: dict = {"sha256": _sha256(canonical_json(persisted)),
                    "file_count": len(persisted), "live_file_count": len(live)}
    for name, rows in (("added", added), ("removed", removed), ("changed", changed)):
        if rows:
            detail[name] = rows[:8]
    return _leg(reasons, detail)


def _bind_candidate_store(root: Path, persisted):
    """Candidate store leg: FULL plans population digest and count."""
    if persisted is None:
        return dict(_leg(["INVENTORY_MISSING"]), sha256=None, file_count=None)
    store_dir = root / CANDIDATE_STORE_DIR
    if store_dir.is_symlink():
        return dict(_leg(["SYMLINK_REFUSED"]), sha256=None, file_count=None)
    if not store_dir.is_dir():
        return dict(_leg(["CANDIDATE_STORE_PATH_MISSING"]), sha256=None, file_count=None)
    entries = candidate_store_entries(persisted)
    return dict(
        _leg([]),
        sha256=store_sha256(entries),
        file_count=len(entries),
    )


def _bind_board(root: Path, source_snapshot_path: Path, source_blob_path: Path):
    """Frozen source leg: snapshot/bundle/live triple equality + durable recovery."""
    reasons: list[str] = []
    source_doc = _read_json(source_snapshot_path)
    source = source_doc.get("source") if isinstance(source_doc, dict) else None
    if not isinstance(source, dict) or not source.get("path") or not source.get("sha256"):
        raise InfrastructureError("source snapshot lacks its frozen source binding")
    expected_sha = str(source["sha256"])
    board_rel = str(source["path"])
    if board_rel != BOARD_REL:
        reasons.append("SOURCE_PATH_AMBIGUOUS")
    board_path = root / board_rel
    live_bytes = None
    if board_path.is_symlink():
        reasons.append("SYMLINK_REFUSED")
    elif board_path.is_file():
        live_bytes = board_path.read_bytes()
    blob_bytes = None
    if source_blob_path.is_file() and not source_blob_path.is_symlink():
        blob_bytes = source_blob_path.read_bytes()
    live_sha = _sha256(live_bytes) if live_bytes is not None else None
    blob_sha = _sha256(blob_bytes) if blob_bytes is not None else None
    # Exact incumbent triple equality: live bytes, frozen blob bytes and the
    # snapshot binding must all recover the same source, or nothing from an
    # ambiguous source snapshot may be treated as bound.
    if live_sha != expected_sha or blob_sha != expected_sha or live_bytes != blob_bytes:
        reasons.append("SOURCE_CHANGED_AFTER_FREEZE")
    durable_path = root / str(source.get("snapshot_path") or "")
    durable_raw = None
    if durable_path.is_file() and not durable_path.is_symlink():
        try:
            durable_raw = gzip.decompress(durable_path.read_bytes())
        except (OSError, EOFError):
            durable_raw = None
    if blob_bytes is None or durable_raw != blob_bytes:
        reasons.append("DURABLE_SOURCE_SNAPSHOT_MISSING")
    price_through = source.get("price_through")
    if not isinstance(price_through, str) or not DATE_RE.fullmatch(price_through):
        reasons.append("SOURCE_CLOCK_UNQUALIFIED")
    leg = _leg(reasons, {"path": board_rel, "snapshot_path": source.get("snapshot_path")})
    leg["sha256"] = expected_sha if not reasons else None
    return leg


def _parse_delta(delta_path: Path):
    """Incumbent delta TSV rows; None when unreadable or non-normalized."""
    try:
        text = delta_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    rows: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 3 or not _normalized_rel(parts[0]):
            return None
        rows[parts[0]] = (parts[1], parts[2])
    return rows


def _bind_index(root: Path, persisted, delta_rows, delta_path: Path,
                frozen_board_sha: str | None):
    """Final index leg: raw bytes, genuine computed_at, split-checkpoint binding."""
    reasons: list[str] = []
    detail: dict = {}
    index_path = root / INDEX_REL
    if index_path.is_symlink():
        reasons.append("SYMLINK_REFUSED")
    if not index_path.is_file():
        reasons.append("INDEX_MISSING")
        return dict(_leg(reasons, detail), sha256=None, computed_at=None)
    raw = index_path.read_bytes()
    raw_sha = _sha256(raw)
    live_fingerprint = digest(index_path)
    try:
        doc = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        doc = None
    computed_at = doc.get("computed_at") if isinstance(doc, dict) else None
    if not isinstance(computed_at, str) or not computed_at:
        reasons.append("INDEX_CLOCK_MISSING")
    elif not COMPUTED_AT_RE.fullmatch(computed_at) or _unparseable(computed_at):
        reasons.append("INDEX_CLOCK_UNQUALIFIED")
    if not isinstance(doc, dict) or doc.get("source_board_sha256") != frozen_board_sha:
        reasons.append("INDEX_BOARD_BINDING_MISMATCH")
    if persisted is not None and persisted.get(INDEX_REL) != live_fingerprint:
        reasons.append("INVENTORY_POPULATION_CHANGED")
    if not delta_path.exists():
        reasons.append("DELTA_MANIFEST_MISSING")
    elif delta_rows is None:
        reasons.append("PATH_NOT_NORMALIZED")
    else:
        row = delta_rows.get(INDEX_REL)
        if row is not None and row[1] != live_fingerprint:
            reasons.append("SPLIT_CHECKPOINT_INDEX_MISMATCH")
        for rel, (_before, after) in delta_rows.items():
            if rel == INDEX_REL:
                continue
            if not (root / rel).is_file():
                reasons.append("PATH_MISSING")
            elif persisted is not None and persisted.get(rel) != after:
                reasons.append("SPLIT_CHECKPOINT_TSV_STALE")
    detail["source_board_sha256"] = doc.get("source_board_sha256") if isinstance(doc, dict) else None
    leg = _leg(reasons, detail)
    leg["sha256"] = raw_sha if not reasons else None
    leg["computed_at"] = computed_at if not reasons else None
    return leg


def _unparseable(computed_at: str) -> bool:
    try:
        dt.datetime.strptime(computed_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return True
    return False


def _bind_gmi_theme_state(root: Path, gmi_receipt_path: Path | None):
    """GMI leg: incumbent accepted-generation family + production qualification.

    Everything here goes through the incumbent owner's own validators: the
    family is proven immutable/current via ``theme_state_generation``, and a
    separately issued owner read receipt is verified detached against that
    exact family plan witness via ``validate_read_receipt_at_use``. This module
    never reads the descriptive ``data/neuralweb/theme_state.json`` shadow,
    never carries a rights verifier, and never mints a generation, right,
    clock or receipt of its own.
    """
    from engine.neuralweb import theme_state_generation as g
    from engine.neuralweb import theme_state_generation_reader as reader

    reasons: list[str] = []
    detail: dict = {"source": "incumbent_generation_family", "receipt_status": None,
                    "receipt_reason_codes": None, "generation_id": None}
    bound_sha: str | None = None
    plan = None
    try:
        current_raw = g.read(root, g.CURRENT)
        if current_raw is None:
            reasons.append("GMI_ACCEPTED_REFERENCE_MISSING")
        elif g.read(root, g.PENDING) is not None:
            reasons.append("GMI_PENDING_GENERATION_OWNS_PREFIX")
        else:
            ancestry = g._accepted_ancestry(root, current_raw)
            ref = g.parse(current_raw)
            plan = ancestry[ref["generation_id"]]
            state = g.validate_generation(plan)
            if plan["root"] != str(Path(root).resolve()):
                reasons.append("GMI_ACCEPTED_PLAN_SCOPE_MISMATCH")
            detail["generation_id"] = ref["generation_id"]
            detail["state_raw_sha256"] = state["state_sha256"]
    except g.GenerationUnavailable as error:
        reasons.append("GMI_" + str(getattr(error, "reason", error)))
    except (ValueError, TypeError, KeyError, AttributeError, OSError):
        reasons.append("GMI_FAMILY_UNREADABLE")
    if plan is not None and not reasons:
        if gmi_receipt_path is None or not gmi_receipt_path.exists():
            # Production truth today: the incumbent GMI reader has issued no
            # production-qualified receipt the nightly lane could carry
            # (current-use rights owner unwired, W3B in progress). Absence is
            # typed, never guessed around.
            reasons.append("GMI_RECEIPT_NOT_SUPPLIED")
        else:
            receipt = _read_json(gmi_receipt_path)
            if not isinstance(receipt, dict):
                reasons.append("GMI_RECEIPT_UNREADABLE")
            else:
                try:
                    reader.validate_read_receipt_at_use(receipt, publication_plan=plan)
                except (ValueError, TypeError, KeyError, AttributeError, OSError):
                    reasons.append("GMI_RECEIPT_INVALID")
                detail["receipt_status"] = receipt.get("status")
                detail["receipt_reason_codes"] = receipt.get("reason_codes")
                if "GMI_RECEIPT_INVALID" not in reasons:
                    if receipt.get("status") not in ("DESCRIPTIVE", "VALID_EMPTY"):
                        reasons.append("GMI_RECEIPT_NOT_AVAILABLE")
                    elif any(
                        code in receipt.get("reason_codes") or []
                        for code in GMI_UNQUALIFIED_CODES
                    ):
                        reasons.append("GMI_THEME_STATE_NOT_QUALIFIED")
                    elif (receipt.get("publication") or {}).get("generation_id") != (
                        detail.get("generation_id")
                    ):
                        reasons.append("GMI_GENERATION_MISMATCH")
                    else:
                        raw_sha = (receipt.get("state_identity") or {}).get("raw_sha256")
                        if raw_sha is None or raw_sha != detail.get("state_raw_sha256"):
                            reasons.append("GMI_STATE_IDENTITY_MISMATCH")
                        else:
                            bound_sha = raw_sha
    leg = _leg(reasons, detail)
    leg["sha256"] = bound_sha
    return leg


def run_preflight(
    root: Path,
    *,
    inventory_path: Path,
    source_snapshot_path: Path,
    source_blob_path: Path,
    delta_path: Path,
    gmi_receipt_path: Path | None = None,
) -> dict:
    """Bind all issuer-side source legs and return the typed preflight receipt."""
    root = Path(root).resolve()
    persisted = _read_json(inventory_path)
    if persisted is not None and not isinstance(persisted, dict):
        persisted = None
    inventory_leg = _bind_inventory(root, inventory_path, persisted)
    source_doc = _read_json(source_snapshot_path)
    source = source_doc.get("source") if isinstance(source_doc, dict) else None
    if not isinstance(source, dict) or not source.get("sha256"):
        raise InfrastructureError("source snapshot lacks its frozen source binding")
    frozen_board_sha = str(source["sha256"])
    board_leg = _bind_board(root, source_snapshot_path, source_blob_path)
    index_leg = _bind_index(root, persisted, _parse_delta(delta_path), delta_path,
                            frozen_board_sha)
    store_leg = _bind_candidate_store(root, persisted)
    gmi_leg = _bind_gmi_theme_state(root, gmi_receipt_path)

    reason_codes = sorted(
        {
            *inventory_leg["reason_codes"],
            *board_leg["reason_codes"],
            *index_leg["reason_codes"],
            *store_leg["reason_codes"],
            *gmi_leg["reason_codes"],
        }
    )
    artifact_hashes = {
        "board": board_leg["sha256"],
        "candidate_store": store_leg["sha256"],
        "index": index_leg["sha256"],
        "theme_state": gmi_leg["sha256"],
    }
    qualified = (
        not reason_codes
        and all(leg["status"] == "QUALIFIED" for leg in
                (inventory_leg, board_leg, index_leg, store_leg, gmi_leg))
        and all(value for value in artifact_hashes.values())
    )
    receipt = {
        "schema": SCHEMA,
        # Settlement belongs to the A2 manifest issuer and its reader proof.
        # The preflight can only report that source evidence is bound; it is
        # never accepted, never settled and never carries a bundle identity.
        "status": STATUS_QUALIFIED if qualified else STATUS_REFUSED,
        "accepted": False,
        "reason_codes": reason_codes,
        "leg_detail": {
            "board": board_leg,
            "candidate_store": store_leg,
            "gmi_theme_state": gmi_leg,
            "index": index_leg,
            "inventory": inventory_leg,
        },
        "artifact_hashes": artifact_hashes,
        "artifact_inventory_sha256": inventory_leg["detail"].get("sha256"),
        "artifact_inventory_file_count": inventory_leg["detail"].get("file_count"),
        "candidate_count": store_leg["file_count"],
        # The canonical board family of the US settlement chain (masterplan
        # §18.2); the manifest issuer cites it, the preflight only restates it.
        "board_definition": "us_prophet_v4",
        # An accepted bundle identity is issued downstream, only after the A2
        # manifest and reader proof exist. The issuer preflight never mints one.
        "bundle_id": None,
        "reader_proof": None,
        "publish": None,
        "authority_caps": dict(AUTHORITY_CAPS),
    }
    _self_check(receipt)
    return receipt


def _self_check(receipt: dict) -> None:
    """Hard invariants: this instrument can never claim settlement or identity."""
    if receipt["bundle_id"] is not None or receipt["accepted"] is not False:
        raise InfrastructureError("preflight attempted to produce accepted identity")
    if receipt["status"] == STATUS_REFUSED and not receipt["reason_codes"]:
        raise InfrastructureError("refused preflight without typed reason codes")
    if receipt["status"] == STATUS_QUALIFIED and receipt["reason_codes"]:
        raise InfrastructureError("qualified preflight carrying refusal codes")
    if receipt["status"] == STATUS_QUALIFIED and any(
        value is None for value in receipt["artifact_hashes"].values()
    ):
        raise InfrastructureError("qualified preflight with an unbound artifact")
    if any(receipt["authority_caps"].values()):
        raise InfrastructureError("preflight authority caps must all stay False")


def write_receipt(receipt: dict, receipt_path: Path, root: Path | None = None) -> None:
    """Deterministic runner-local receipt bytes; never under site/ or data/."""
    encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    resolved = Path(receipt_path).resolve()
    if root is not None:
        repo = Path(root).resolve()
        if resolved.is_relative_to(repo / "site") or resolved.is_relative_to(repo / "data"):
            raise InfrastructureError(
                "preflight receipt must stay runner-local, not under site/ or data/"
            )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_bytes(encoded.encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=os.environ.get("GITHUB_WORKSPACE") or os.getcwd())
    parser.add_argument("--inventory", default=os.environ.get("PROPHET_INVENTORY"))
    parser.add_argument("--source-snapshot", default=os.environ.get("PROPHET_SOURCE_SNAPSHOT"))
    parser.add_argument("--source-blob", default=os.environ.get("PROPHET_SOURCE_BLOB"))
    parser.add_argument("--delta", default=os.environ.get("PROPHET_DELTA"))
    parser.add_argument("--receipt-out", default=os.environ.get("PROPHET_PREFLIGHT_RECEIPT"))
    parser.add_argument(
        "--gmi-receipt",
        default=os.environ.get("PROPHET_GMI_RECEIPT"),
        help="owner-issued ThemeState generation read receipt to verify (optional)",
    )
    args = parser.parse_args(argv)
    missing = [
        name
        for name, value in (
            ("--inventory", args.inventory),
            ("--source-snapshot", args.source_snapshot),
            ("--source-blob", args.source_blob),
            ("--delta", args.delta),
            ("--receipt-out", args.receipt_out),
        )
        if not value
    ]
    if missing:
        print(
            "::error title=prophet accepted-source preflight::missing required evidence paths: "
            + ", ".join(missing),
            flush=True,
        )
        return 2
    try:
        receipt = run_preflight(
            Path(args.root),
            inventory_path=Path(args.inventory),
            source_snapshot_path=Path(args.source_snapshot),
            source_blob_path=Path(args.source_blob),
            delta_path=Path(args.delta),
            gmi_receipt_path=Path(args.gmi_receipt) if args.gmi_receipt else None,
        )
        write_receipt(receipt, Path(args.receipt_out), Path(args.root))
    except InfrastructureError as exc:
        print(
            f"::warning title=prophet accepted-source preflight::settlement evidence "
            f"stays unbound ({exc})",
            flush=True,
        )
        return 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(
            f"::warning title=prophet accepted-source preflight::could not bind source "
            f"evidence ({type(exc).__name__}: {exc})",
            flush=True,
        )
        return 2
    summary = ",".join(receipt["reason_codes"]) or "none"
    print(
        f"::notice title=prophet accepted-source preflight::status={receipt['status']} "
        f"reasons={summary} bundle_id=null",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
