"""Issuer SIC resolution from the shipped coverage contracts.

The SIC served here is the coverage contract's classification basis
(``issuer_class_basis: sic``) — the basis on which an issuer's class is
derived for metric applicability — not a point-in-time fact about the issuer.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Mapping

# Type alias for the per-site injection seam: maps a source entity id (the
# ledger's CIK spelling) to a normalized SIC digit-string or ``None``.
IssuerSicResolver = Callable[[str], "str | None"]

_COVERAGE_RELATIVE_PATH = ("config", "fundamental_forensics", "coverage")
_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
# Shipped documents that live beside the member contracts but carry no member
# records: the frozen C2 tier thresholds (``coverage_proof.THRESHOLDS_SCHEMA``).
# Only an exact declared schema is skipped; every other file in the directory
# is still held to the member-contract shape and fails closed.
_NON_MEMBER_SCHEMAS = frozenset({"fundamental_forensics.coverage_thresholds/v1"})


def _normalize_cik(value: Any) -> str | None:
    """Zero-pad a CIK spelling to the SEC's 10-digit form.

    Unparseable spellings return ``None`` (no possible match), keeping the
    lookup fail-closed rather than raising on hostile input.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        digits = str(value)
    elif isinstance(value, str):
        digits = value.strip()
    else:
        return None
    if not digits or not digits.isdigit():
        return None
    return digits.zfill(10)


def _normalize_sic(value: Any) -> str | None:
    """Normalize a SIC spelling to its digit string.

    Anything that is not a non-negative integer or a digit-only string
    returns ``None``.  ``issuer_class_for_sic`` maps unparseable text to the
    class ``unknown``, which no exclusion-only applicability policy excludes,
    so letting such text through would admit class-restricted metrics; a
    ``None`` SIC instead keeps them ``NOT_EVALUABLE`` (``issuer_class_unknown``).
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value) if value >= 0 else None
    if isinstance(value, str):
        text = value.strip()
        return text if text and text.isascii() and text.isdigit() else None
    return None


@lru_cache(maxsize=None)
def _shipped_sic_index(repo_root_text: str) -> dict[str, str]:
    """Load every shipped coverage contract's CIK -> SIC index.

    Two shipped contracts that disagree on the SIC for one CIK (including a
    present-versus-absent disagreement) raise at load: the classification
    basis is governance, so an ambiguous basis is never silently resolved.
    """
    root = Path(repo_root_text)
    index: dict[str, str | None] = {}
    provenance: dict[str, str] = {}
    coverage_dir = root.joinpath(*_COVERAGE_RELATIVE_PATH)
    for path in sorted(coverage_dir.glob("*.json")):
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"shipped coverage contract is unreadable: {path.name}: {exc}"
            ) from exc
        if not isinstance(parsed, Mapping):
            raise ValueError(
                f"shipped coverage contract is not a JSON object: {path.name}"
            )
        schema = parsed.get("schema")
        if isinstance(schema, str) and schema in _NON_MEMBER_SCHEMAS:
            continue
        issuers = parsed.get("issuers")
        if not isinstance(issuers, list):
            raise ValueError(
                f"shipped coverage contract carries no issuers list: {path.name}"
            )
        for member in issuers:
            if not isinstance(member, Mapping):
                raise ValueError(
                    f"shipped coverage contract member is not an object: {path.name}"
                )
            cik = _normalize_cik(member.get("cik"))
            if cik is None:
                continue
            sic = _normalize_sic(member.get("sic"))
            if cik in index and index[cik] != sic:
                raise ValueError(
                    "shipped coverage contracts disagree on the SIC for one CIK: "
                    f"{provenance[cik]} records {index[cik]!r} and {path.name} "
                    f"records {sic!r} for CIK {cik}"
                )
            index[cik] = sic
            provenance.setdefault(cik, path.name)
    return {cik: sic for cik, sic in index.items() if sic is not None}


def resolve_issuer_sic(
    cik: str | int | None,
    *,
    repo_root: Path | str | None = None,
) -> str | None:
    """Resolve one issuer's SIC from the shipped coverage contracts.

    The CIK is zero-pad normalized before an exact match against the member
    records of every shipped contract under
    ``config/fundamental_forensics/coverage/*.json``.  A CIK with no matching
    member record, or a matching record with no ``sic``, returns ``None`` —
    the fail-closed path that keeps a class-restricted metric
    ``NOT_EVALUABLE`` (``issuer_class_unknown``) rather than guessing.  No
    network, no environment, no object store: shipped bytes only.

    ``functools.partial(resolve_issuer_sic, repo_root=<root>)`` is the
    default resolver shape production sites bind when the caller injects
    none; hermetic tests inject their own callable instead.
    """
    normalized = _normalize_cik(cik)
    if normalized is None:
        return None
    root = Path(repo_root) if repo_root is not None else _DEFAULT_REPO_ROOT
    return _shipped_sic_index(str(root.resolve())).get(normalized)
