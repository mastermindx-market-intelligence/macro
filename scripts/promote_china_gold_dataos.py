"""Safely promote the two China-gold source datasets after proven live acceptance.

This is an explicit source-writer utility, not a scheduler or lifecycle plane. It is
DRY-RUN by default. The --apply flag only changes the two canonical Data OS
registry statuses from PROPOSED to PRODUCED after the production quality receipt
proves artifact-bound close-proxy readiness. It never commits or pushes Git state.

Usage:
    python -m scripts.promote_china_gold_dataos
    python -m scripts.promote_china_gold_dataos --apply
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml

from lib import config


SCHEMA = "commodity.china_gold_premium_quality.v1"
TARGET_DATASET_IDS = (
    "commodity.gold.sge_au9999.close",
    "commodity.gold.xaucny.close_ref",
)


def _load_receipt(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError(f"quality receipt unreadable at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("quality receipt must be a JSON object")
    return value


def _load_registry(path: Path) -> tuple[str, dict]:
    try:
        text = path.read_text()
        payload = yaml.safe_load(text) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"dataset registry unreadable at {path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("datasets"), list):
        raise ValueError("dataset registry must contain a datasets list")
    return text, payload


def _registry_statuses(payload: dict) -> tuple[dict[str, str], list[str]]:
    statuses: dict[str, str] = {}
    duplicates: list[str] = []
    for row in payload.get("datasets") or []:
        if not isinstance(row, dict):
            continue
        dataset_id = str(row.get("dataset_id") or "")
        if not dataset_id:
            continue
        if dataset_id in statuses:
            duplicates.append(dataset_id)
            continue
        statuses[dataset_id] = str(row.get("status") or "")
    return statuses, duplicates


def assess(
    receipt: dict,
    registry_payload: dict,
    *,
    repo_root: Path | None = None,
) -> dict:
    """Return the exact promotion plan without mutating source."""
    blockers: list[str] = []
    if receipt.get("schema") != SCHEMA:
        blockers.append(
            f"receipt schema is {receipt.get('schema')!r}, required {SCHEMA!r}"
        )
    if receipt.get("close_proxy_dataos_promotion_ready") is not True:
        blockers.append("quality receipt is not close-proxy Data OS promotion-ready")
    receipt_blockers = receipt.get("close_proxy_dataos_promotion_blockers")
    if receipt_blockers not in ([], None):
        blockers.append("quality receipt still carries promotion blockers")

    artifacts = receipt.get("source_artifacts")
    by_id = {
        str(item.get("dataset_id")): item
        for item in artifacts or []
        if isinstance(item, dict) and item.get("dataset_id")
    }
    for dataset_id in TARGET_DATASET_IDS:
        item = by_id.get(dataset_id)
        if not isinstance(item, dict):
            blockers.append(f"receipt is missing artifact {dataset_id}")
            continue
        if item.get("exists") is not True:
            blockers.append(f"artifact {dataset_id} does not exist")
        try:
            rows = int(item.get("rows") or 0)
        except (TypeError, ValueError):
            rows = 0
        if rows < 1:
            blockers.append(f"artifact {dataset_id} has no rows")
        digest = str(item.get("sha256") or "")
        if len(digest) != 64 or any(
            ch not in "0123456789abcdef" for ch in digest.lower()
        ):
            blockers.append(f"artifact {dataset_id} has no bound sha256")
        if item.get("selected_asof_present") is not True:
            blockers.append(f"artifact {dataset_id} does not bind the selected row")

        if repo_root is not None:
            rel_raw = str(item.get("path") or "")
            rel = Path(rel_raw)
            if not rel_raw or rel.is_absolute() or ".." in rel.parts:
                blockers.append(
                    f"artifact {dataset_id} has invalid repo-relative path {rel_raw!r}"
                )
            else:
                current = repo_root / rel
                if not current.is_file():
                    blockers.append(
                        f"artifact {dataset_id} is missing from current source tree"
                    )
                else:
                    current_digest = hashlib.sha256(current.read_bytes()).hexdigest()
                    if current_digest != digest:
                        blockers.append(
                            f"artifact {dataset_id} current sha256 does not match receipt"
                        )

    statuses, duplicates = _registry_statuses(registry_payload)
    for dataset_id in duplicates:
        if dataset_id in TARGET_DATASET_IDS:
            blockers.append(f"dataset registry duplicates target {dataset_id}")

    pending: list[str] = []
    already: list[str] = []
    for dataset_id in TARGET_DATASET_IDS:
        status = statuses.get(dataset_id)
        if status == "PROPOSED":
            pending.append(dataset_id)
        elif status == "PRODUCED":
            already.append(dataset_id)
        elif status is None:
            blockers.append(f"dataset registry is missing {dataset_id}")
        else:
            blockers.append(
                f"dataset registry status for {dataset_id} is {status or 'unbound'}"
            )

    return {
        "eligible": not blockers,
        "pending": pending,
        "already_produced": already,
        "blockers": blockers,
    }


def _promote_text(text: str, dataset_ids: list[str]) -> str:
    out = text
    for dataset_id in dataset_ids:
        block_pattern = re.compile(
            rf"(?ms)^  - dataset_id: {re.escape(dataset_id)}\n"
            rf"(?P<body>.*?)(?=^  - dataset_id: |\Z)"
        )
        match = block_pattern.search(out)
        if match is None:
            raise ValueError(f"cannot find registry block for {dataset_id}")
        block = match.group(0)
        promoted, count = re.subn(
            r"(?m)^(    status: )PROPOSED$",
            r"\1PRODUCED",
            block,
            count=1,
        )
        if count != 1:
            raise ValueError(
                f"registry block for {dataset_id} is not exactly PROPOSED"
            )
        out = out[: match.start()] + promoted + out[match.end() :]
    return out


def promote(
    *,
    receipt_path: Path | str | None = None,
    registry_path: Path | str | None = None,
    apply: bool = False,
) -> dict:
    receipt_path = Path(receipt_path) if receipt_path is not None else (
        config.data_dir() / "quality" / "china_gold_premium.json"
    )
    registry_path = Path(registry_path) if registry_path is not None else (
        config.ROOT / "config" / "dataset_registry.yml"
    )

    receipt = _load_receipt(receipt_path)
    registry_text, registry_payload = _load_registry(registry_path)
    repo_root = (
        registry_path.parent.parent
        if registry_path.parent.name == "config"
        else registry_path.parent
    )
    result = assess(receipt, registry_payload, repo_root=repo_root)
    result.update(
        {
            "receipt_path": str(receipt_path),
            "registry_path": str(registry_path),
            "applied": [],
        }
    )
    if not apply or not result["eligible"] or not result["pending"]:
        return result

    updated = _promote_text(registry_text, result["pending"])
    registry_path.write_text(updated)

    _, verified_payload = _load_registry(registry_path)
    statuses, duplicates = _registry_statuses(verified_payload)
    if duplicates:
        raise RuntimeError(f"post-write registry has duplicate ids: {duplicates}")
    for dataset_id in TARGET_DATASET_IDS:
        if statuses.get(dataset_id) != "PRODUCED":
            raise RuntimeError(
                f"post-write verification failed for {dataset_id}: "
                f"{statuses.get(dataset_id)!r}"
            )
    result["applied"] = list(result["pending"])
    result["pending"] = []
    result["already_produced"] = list(TARGET_DATASET_IDS)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--receipt",
        type=Path,
        default=None,
        help="override the production quality receipt path",
    )
    ap.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="override config/dataset_registry.yml",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="write the two PROPOSED to PRODUCED status changes; never commits/pushes",
    )
    args = ap.parse_args(argv)

    try:
        result = promote(
            receipt_path=args.receipt,
            registry_path=args.registry,
            apply=args.apply,
        )
    except Exception as exc:
        print(f"China gold Data OS promotion error: {exc}")
        return 2

    print(json.dumps(result, indent=2))
    if not result["eligible"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
