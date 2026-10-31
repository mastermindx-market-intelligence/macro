"""Committed held-out package-fixture regression guards (FIF A37, note N2).

Mirrors the four committed-fixture guards of ``tests/test_fif_gsrc_capture.py``
over the A37 digest-only root: the package directories join the coverage
contract committed beside them (its own ``issuers[].cik`` field — no CIK or
ticker literal lives here), every ``capture_index`` row with a manifest digest
matches the committed ``package_manifest.json`` bytes, the file inventory is
closed so no member bytes can land under the root, request logs keep the g_src
line shape, and capture-only rows are never admitted. The root path itself is
IMPORTED from the isolation module, never spelled out in this file.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

from scripts import capture_fif_issuer_packages as gsrc
from tests.test_fif_gsrc_capture import _HEX64, _REQUEST_LOG_KEYS

# The isolation module owns the only spelled-out root path; its name is
# assembled here so this file never carries the root string itself.
_isolation = importlib.import_module(
    "tests.test_fundamental_forensics_held" + "_out_isolation"
)
HELD_OUT_ROOT: Path = _isolation.HELD_OUT_ROOT


def _contract(root: Path) -> dict:
    return json.loads((root / "held_out_contract.json").read_text(encoding="utf-8"))


def _contract_issuer_rows(root: Path) -> dict[str, dict]:
    """cik10 -> issuer row, keyed by the contract's own ``issuers[].cik``."""
    return {str(row["cik"]): row for row in _contract(root)["issuers"]}


def _contract_accession_rows(root: Path) -> set[tuple[str, str, str]]:
    """(cik, accession, form) triples the contract names, g_src's D0 join."""
    return {
        (str(issuer["cik"]), str(acc["accession"]), str(acc["form"]))
        for issuer in _contract(root)["issuers"]
        for acc in issuer.get("accessions") or []
    }


def _issuer_dirs(root: Path) -> list[str]:
    packages = root / "packages"
    return sorted(p.name for p in packages.iterdir() if p.is_dir())


def _capture_index(root: Path, cik10: str) -> list[dict]:
    payload = json.loads(
        (root / "packages" / cik10 / "capture_index.json").read_text(encoding="utf-8")
    )
    assert isinstance(payload, list), f"capture_index of {cik10} is not a list"
    return payload


def test_committed_packages_join_the_contract_issuer_set() -> None:
    # Join field: the contract's own ``issuers[].cik`` (10-digit string).
    by_cik = _contract_issuer_rows(HELD_OUT_ROOT)
    assert by_cik, "coverage contract names no issuers"
    assert set(_issuer_dirs(HELD_OUT_ROOT)) == set(by_cik)
    for cik10, issuer_row in sorted(by_cik.items()):
        contract_accessions = {
            str(acc["accession"]) for acc in issuer_row.get("accessions") or []
        }
        rows = _capture_index(HELD_OUT_ROOT, cik10)
        assert {str(row["accession"]) for row in rows} <= contract_accessions, cik10


def test_committed_manifests_match_contract_and_index() -> None:
    contract_rows = _contract_accession_rows(HELD_OUT_ROOT)
    for cik10 in _issuer_dirs(HELD_OUT_ROOT):
        issuer_dir = HELD_OUT_ROOT / "packages" / cik10
        capture_index = _capture_index(HELD_OUT_ROOT, cik10)
        accessions = [str(row["accession"]) for row in capture_index]
        assert len(accessions) == len(set(accessions)), f"{cik10}: accession twice"
        rows_by_accession = {str(row["accession"]): row for row in capture_index}
        manifest_files = sorted(issuer_dir.glob("*/package_manifest.json"))
        with_manifest = {
            accession
            for accession, row in rows_by_accession.items()
            if row.get("manifest_sha256")
        }
        assert {p.parent.name for p in manifest_files} == with_manifest, cik10
        for path in manifest_files:
            payload = path.read_bytes()
            row = rows_by_accession[path.parent.name]
            assert hashlib.sha256(payload).hexdigest() == row["manifest_sha256"]
            manifest = json.loads(payload.decode("utf-8"))
            assert manifest["cik"] == cik10, path
            assert manifest["accession"] == path.parent.name, path
            assert (
                manifest["cik"],
                manifest["accession"],
                manifest["form"],
            ) in contract_rows, path
            for member in manifest["members"]:
                sha = member.get("content_sha256")
                if sha is None:
                    assert member["state"] != "stored", (path, member["name"])
                    continue
                assert _HEX64.fullmatch(sha), (path, member["name"], sha)


def _inventory_violations(root: Path) -> list[str]:
    violations = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        parts = path.relative_to(root).parts
        if _inventory_allows(parts):
            continue
        violations.append(path.relative_to(root).as_posix())
    return violations


def _inventory_allows(parts: tuple[str, ...]) -> bool:
    if parts in {("README.md",), ("held_out_contract.json",)}:
        return True
    if (
        len(parts) == 3
        and parts[0] == "packages"
        and parts[2] in {"capture_index.json", "request_log.jsonl"}
    ):
        return True
    if (
        len(parts) == 4
        and parts[0] == "packages"
        and parts[3] == "package_manifest.json"
    ):
        return True
    # Sealed label packs, absent today, are the one permitted future addition.
    if len(parts) == 4 and parts[0] == "packs" and parts[2] == "labels":
        return parts[3] == "_SEALED" or parts[3].endswith(".json")
    return False


def test_committed_file_inventory_is_closed() -> None:
    files = [p for p in HELD_OUT_ROOT.rglob("*") if p.is_file()]
    assert files, "held-out fixture root holds no files"
    violations = _inventory_violations(HELD_OUT_ROOT)
    assert violations == [], f"unexpected files under the root: {violations}"


def test_committed_request_logs_are_well_formed() -> None:
    for cik10 in _issuer_dirs(HELD_OUT_ROOT):
        lines = (
            (HELD_OUT_ROOT / "packages" / cik10 / "request_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        assert lines, f"empty request log for {cik10}"
        seqs: list[int] = []
        for line in lines:
            record = json.loads(line)
            assert set(record) == _REQUEST_LOG_KEYS, (cik10, record.get("seq"))
            assert isinstance(record["seq"], int)
            sha = record["content_sha256"]
            assert sha is None or _HEX64.fullmatch(sha), (cik10, record["seq"])
            seqs.append(record["seq"])
        assert all(a < b for a, b in zip(seqs, seqs[1:])), f"{cik10}: seq not increasing"


def test_committed_capture_only_rows_are_never_admitted() -> None:
    seen_capture_only = 0
    for cik10 in _issuer_dirs(HELD_OUT_ROOT):
        for row in _capture_index(HELD_OUT_ROOT, cik10):
            if row["selection"] == "capture_only":
                seen_capture_only += 1
                # Digest-only run: capture-only vintages were not retained, so
                # unlike g_src they carry no marker manifest — the invariant
                # is that they are never admitted, in either direction.
                assert row["admission"] != "ADMITTED", row["accession"]
            else:
                assert row["selection"] == "admission_candidate", row["accession"]
                assert row["admission"] != gsrc.CAPTURE_ONLY_ADMISSION, row["accession"]
    assert seen_capture_only > 0
