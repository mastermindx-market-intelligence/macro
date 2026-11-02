#!/usr/bin/env python3
"""Build the W-LIQ.1 state-only contract, history, and frozen comparison receipt."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
ROOT = _ROOT

from engine.global_liquidity_transmission import (  # noqa: E402
    build_contract,
    load_producer_config,
    walk_forward_factor_comparison,
)
from lib import store  # noqa: E402


CONTRACT_PATH = ROOT / "site/liquiditydata/global_liquidity_transmission.json"
HISTORY_PATH = ROOT / "data/global_liquidity_transmission/state_history.parquet"
HISTORY_META_PATH = ROOT / "data/global_liquidity_transmission/state_history_meta.json"
COMPARISON_PATH = ROOT / "data/global_liquidity_transmission/factor_comparison_btc_4w.json"

_ASOF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _tmp_sibling(path: Path) -> Path:
    """Hidden same-directory tmp name, so os.replace is atomic on one filesystem."""
    return path.parent / f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}"


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """tmp + fsync + os.replace; a consumer never observes a partial artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_sibling(path)
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _write_json(path: Path, payload: dict) -> None:
    _atomic_write_bytes(
        path,
        (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"),
    )


def _write_parquet_atomic(history, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_sibling(path)
    try:
        history.to_parquet(tmp)
        with open(tmp, "rb") as fh:
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def preserve_first_known(payload: dict, previous: dict | None) -> dict:
    """Keep the earliest first-known clock for an exact immutable source retry."""
    if not previous:
        return payload
    if previous.get("meta", {}).get("source_snapshot_hash") != payload["meta"]["source_snapshot_hash"]:
        return payload
    old_clock = (
        previous.get("state", {})
        .get("event_reference", {})
        .get("clocks", {})
        .get("first_known_at")
    )
    if not old_clock:
        return payload
    payload["state"]["event_reference"]["clocks"]["first_known_at"] = old_clock
    payload["freshness"]["clocks"]["first_known_at"] = old_clock
    return payload


def _parse_iso(value) -> datetime | None:
    """Parses or None — an unparsable clock never wins a comparison."""
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _parse_day(value) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _first_known(payload: dict):
    clocks = payload.get("state", {}).get("event_reference", {}).get("clocks") or {}
    return clocks.get("first_known_at")


def _evidence_clock(payload: dict):
    clocks = payload.get("freshness", {}).get("clocks") or {}
    return clocks.get("evidence_available_at")


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _backdated_receipt_regression(payload: dict, previous: dict):
    """First leg receipt (reference_date/available_date) that moved backwards."""
    prev_components = (previous.get("freshness") or {}).get("components") or {}
    new_components = (payload.get("freshness") or {}).get("components") or {}
    if not isinstance(prev_components, dict) or not isinstance(new_components, dict):
        return None
    for group, legs in new_components.items():
        if not isinstance(legs, dict):
            continue
        prev_legs = prev_components.get(group)
        if not isinstance(prev_legs, dict):
            continue
        for leg, receipt in legs.items():
            prev_receipt = prev_legs.get(leg)
            if not isinstance(receipt, dict) or not isinstance(prev_receipt, dict):
                continue
            for field in ("reference_date", "available_date"):
                prev_day = _parse_day(prev_receipt.get(field))
                new_day = _parse_day(receipt.get(field))
                if prev_day is not None and new_day is not None and new_day < prev_day:
                    return (f"{group}.{leg}.{field}", prev_receipt.get(field), receipt.get(field))
    return None


def build(asof: str | None = None, *, out: str | None = None, print_notice: bool = True) -> dict:
    wall_start = time.monotonic()
    producer_cfg = load_producer_config()
    generated_at = datetime.now(timezone.utc)
    payload, history = build_contract(
        producer_cfg=producer_cfg,
        root=ROOT,
        asof=asof,
        generated_at=generated_at,
    )

    if out is not None:
        # (e) bounded replay: write ONLY --out; the stored history can never be
        # rewritten, so preserve_first_known is never applied against it.
        _atomic_write_bytes(
            Path(out),
            (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"),
        )
        return _finish(payload, "replayed", wall_start, contract=Path(out), print_notice=print_notice)

    previous = None
    if CONTRACT_PATH.exists():
        try:
            previous = json.loads(CONTRACT_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            previous = None

    # --- B2 outcome decision, computed before any write ---------------------
    trusted = previous is not None
    if previous is not None:
        for field, value in (
            ("state.event_reference.clocks.first_known_at", _first_known(previous)),
            ("freshness.clocks.first_known_at",
             (previous.get("freshness") or {}).get("clocks", {}).get("first_known_at")),
            ("meta.generated_at", previous.get("meta", {}).get("generated_at")),
        ):
            parsed = _parse_iso(value)
            if parsed is not None and parsed > generated_at:
                print(
                    f"::warning title=glt-future-clock-refused::previous {field}={value} "
                    f"is later than now={generated_at.isoformat()}; not inherited",
                    flush=True,
                )
                trusted = False
                break

    outcome = "written"
    if previous is not None:
        prev_asof = (previous.get("state") or {}).get("asof")
        new_asof = (payload.get("state") or {}).get("asof")
        prev_hash = (previous.get("meta") or {}).get("source_snapshot_hash")
        new_hash = (payload.get("meta") or {}).get("source_snapshot_hash")

        if trusted and prev_asof == new_asof and prev_hash == new_hash:
            # (b) write NOTHING. An untrusted (future-clocked) artifact is never kept
            # as-is: it falls through and is rewritten with fresh clocks (C11).
            outcome = "unchanged"
        else:
            stale = None
            prev_evidence = _parse_iso(_evidence_clock(previous))
            new_evidence = _parse_iso(_evidence_clock(payload))
            if prev_evidence is not None and new_evidence is not None and new_evidence < prev_evidence:
                stale = ("freshness.clocks.evidence_available_at", _evidence_clock(previous), _evidence_clock(payload))
            else:
                prev_day = _parse_day(prev_asof)
                new_day = _parse_day(new_asof)
                if prev_day is not None and new_day is not None and new_day < prev_day:
                    stale = ("state.asof", prev_asof, new_asof)
            if stale is not None:
                print(
                    f"::warning title=glt-stale-source-refused::{stale[0]} regressed "
                    f"from {stale[1]} to {stale[2]}; previous artifact kept",
                    flush=True,
                )
                outcome = "refused"  # (c2)
            else:
                backdated = _backdated_receipt_regression(payload, previous)
                if backdated is None and trusted:
                    prev_gen = _parse_iso(previous.get("meta", {}).get("generated_at"))
                    new_gen = _parse_iso(payload.get("meta", {}).get("generated_at"))
                    if prev_gen is not None and new_gen is not None and new_gen < prev_gen:
                        backdated = ("meta.generated_at",
                                     previous.get("meta", {}).get("generated_at"),
                                     payload.get("meta", {}).get("generated_at"))
                if backdated is not None:
                    print(
                        f"::warning title=glt-backdated-receipt-refused::{backdated[0]} "
                        f"{backdated[1]} -> {backdated[2]}; previous artifact kept",
                        flush=True,
                    )
                    outcome = "refused"  # (d)

    if outcome == "written" and previous is not None and trusted:
        prev_hash = previous.get("meta", {}).get("source_snapshot_hash")
        if prev_hash == payload["meta"]["source_snapshot_hash"]:
            payload = preserve_first_known(payload, previous)  # same hash, asof moved
        elif _parse_iso(_evidence_clock(previous)) is not None \
                and _parse_iso(_evidence_clock(previous)) == _parse_iso(_evidence_clock(payload)):
            old_clock = _first_known(previous)  # (c1) new hash, same evidence
            if old_clock:
                payload["state"]["event_reference"]["clocks"]["first_known_at"] = old_clock
                payload["freshness"]["clocks"]["first_known_at"] = old_clock

    if outcome == "written":
        # Write order: history parquet, comparison, history meta, CONTRACT LAST
        # (the contract is the consumer-visible commit point).
        _write_parquet_atomic(history, HISTORY_PATH)

        btc = store.read("yahoo", "BTC-USD")
        if btc is None or "close" not in btc:
            comparison = {
                "schema": "global_liquidity_transmission.factor_comparison.v1",
                "authority": "research_only_no_promotion",
                "status": "unavailable",
                "reason": "canonical yahoo/BTC-USD:close store missing",
            }
        else:
            comparison = walk_forward_factor_comparison(history, btc["close"])
            comparison["generated_at"] = generated_at.isoformat()
            comparison["history_cutoff"] = payload["state"]["asof"]
            comparison["source_snapshot_hash"] = payload["meta"]["source_snapshot_hash"]
            comparison["model_version"] = payload["meta"]["model_version"]
            comparison["data_version"] = payload["meta"]["data_version"]
        _write_json(COMPARISON_PATH, comparison)

        metadata = {
            "schema": "global_liquidity_transmission.history_meta.v1",
            "contract_schema": payload["meta"]["schema"],
            "producer_version": payload["meta"]["producer_version"],
            "model_version": payload["meta"]["model_version"],
            "data_version": payload["meta"]["data_version"],
            "source_snapshot_hash": payload["meta"]["source_snapshot_hash"],
            "config_hash": payload["meta"]["config_hash"],
            "generated_at": generated_at.isoformat(),
            "artifact": _display(HISTORY_PATH),
            "rows": len(history),
            "first_asof": str(history.index.min().date()),
            "last_asof": str(history.index.max().date()),
            "first_complete_state": (
                str(history.dropna(subset=["monetary_stance"]).index.min().date())
                if history["monetary_stance"].notna().any()
                else None
            ),
            "columns": list(history.columns),
            "pit_policy": payload["meta"]["pit_policy"],
            "historical_clock_law": {
                "observation_and_release": "reconstructed conservatively from economic reference dates and configured date-only lags",
                "first_known": "not reconstructable before the W-LIQ.1 producer existed; historical rows are not episode timestamps",
                "2023_2026_exact_episode_chronology": [],
                "chronology_status": "unavailable_do_not_infer_from_backfill",
            },
            "revision_law": payload["meta"]["revision_law"],
            "current_first_known_at": payload["state"]["event_reference"]["clocks"]["first_known_at"],
            "comparison_receipt": _display(COMPARISON_PATH),
        }
        _write_json(HISTORY_META_PATH, metadata)
        _write_json(CONTRACT_PATH, payload)

    # The notice and the result describe the artifact of record after this run. An
    # unchanged or refused run wrote nothing, so they report the kept artifact, never
    # the unwritten candidate (whose first_known_at is this run's own wall clock).
    record = payload if outcome == "written" else previous
    return _finish(record, outcome, wall_start, print_notice=print_notice)


def _notice_line(asof, source_snapshot_hash, first_known_at, wall_s: float, outcome: str) -> str:
    return (
        f"::notice title=glt-nightly::asof={asof} "
        f"source_snapshot_hash={source_snapshot_hash} "
        f"first_known_at={first_known_at} wall_s={wall_s:.2f} outcome={outcome}"
    )


def _finish(payload: dict, outcome: str, wall_start: float, *,
            contract: Path | None = None, print_notice: bool = True) -> dict:
    result = {
        "contract": _display(contract if contract is not None else CONTRACT_PATH),
        "history": _display(HISTORY_PATH),
        "history_meta": _display(HISTORY_META_PATH),
        "comparison": _display(COMPARISON_PATH),
        "asof": (payload.get("state") or {}).get("asof"),
        "quality_status": (payload.get("quality") or {}).get("status"),
        "outcome": outcome,
        "source_snapshot_hash": (payload.get("meta") or {}).get("source_snapshot_hash"),
        "first_known_at": _first_known(payload),
        "wall_s": round(time.monotonic() - wall_start, 2),
    }
    if print_notice:
        print(_notice_line(result["asof"], result["source_snapshot_hash"],
                           result["first_known_at"], result["wall_s"], outcome), flush=True)
    return result


def _replay_error(asof: str | None, out: str | None) -> str | None:
    if asof is None and out is None:
        return None
    if asof is None:
        return "--out requires --asof"
    if not _ASOF_RE.match(asof):
        return f"--asof must match YYYY-MM-DD (got {asof!r})"
    if out is None:
        return "--asof replay requires --out PATH"
    meta = None
    if HISTORY_META_PATH.exists():
        try:
            meta = json.loads(HISTORY_META_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            meta = None
    first = _parse_day((meta or {}).get("first_asof"))
    if meta is None or first is None:
        return ("replay window unknown: data/global_liquidity_transmission/"
                "state_history_meta.json missing or has no first_asof")
    wanted = _parse_day(asof)
    today = datetime.now(timezone.utc).date()
    if wanted is None or wanted < first or wanted > today:
        return f"--asof {asof} outside replay window [{first.isoformat()}, {today.isoformat()}]"
    resolved = Path(out).resolve()
    for forbidden in (ROOT / "site", ROOT / "data"):
        if resolved == forbidden or forbidden in resolved.parents:
            return f"--out must not be under the repo {forbidden.name}/ directory ({resolved})"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", help="Optional YYYY-MM-DD causal cutoff (bounded replay; requires --out)")
    parser.add_argument("--out", help="Replay output PATH (never under the repo's site/ or data/)")
    args = parser.parse_args()
    error = _replay_error(args.asof, args.out)
    if error is not None:
        print(error, file=sys.stderr)
        return 2
    result = build(args.asof, out=args.out, print_notice=False)
    print(json.dumps(result, indent=2, sort_keys=True))
    print(_notice_line(result["asof"], result["source_snapshot_hash"],
                       result["first_known_at"], result["wall_s"], result["outcome"]), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
