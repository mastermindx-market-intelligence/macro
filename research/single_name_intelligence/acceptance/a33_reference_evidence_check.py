"""SNI A33 reference-evidence checker (commission 8659).

SNI-local DRAFT contract over committed coverage reports. It consumes
owner-supplied cell statuses, owner path strings, evidence_rows, and
A33 class summaries from Data OS identity, Company Event/Earnings, FIF,
Capital Structure, Stock Identity, Options, Research Vault, and
qledger/Evaluation. It does not re-implement those owners. Identity ids
are caller-supplied opaque strings; this module never mints, derives, or
guesses a canonical HK/US issuer or security id.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade
path. Every authority flag stays literal False. A caller that tries to
set any of them true is refused (raise). Residual and stress statistics
are out of scope; this checker is descriptive of the committed reports
only. The reports' as_of is 2026-10-11; this module does not treat later
facts as then-known.

The frozen 2026-08 behavioral pilot (keys under behavioral_pilot.) is
historical prior art only and never counts as real current evidence.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

A33_CLASSES: tuple[str, ...] = (
    "identity_listing",
    "filings_announcements",
    "financials",
    "company_events_earnings_calendar",
    "corporate_actions_adjustment",
    "market_data_daily",
)
LIVE_STATUSES: tuple[str, ...] = ("OWNER_NATIVE", "PARTIAL")
PILOT_PREFIX = "behavioral_pilot."
SCHEMA = "sni_evidence_coverage.v0"
AUTHORITY_FLAGS: tuple[str, ...] = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)
COUNT_STATUSES: tuple[str, ...] = (
    "OWNER_NATIVE",
    "PARTIAL",
    "REFUSED",
    "ABSENT",
    "NO_OWNER",
)
BANNED_OWNER_TOKENS: tuple[str, ...] = ("fixture", "synthetic", "mock", "fake")
EXISTENCE_PREFIXES: tuple[str, ...] = (
    "engine/",
    "scripts/",
    "config/",
    "lib/",
    "research/",
    "collectors/",
)
DATA_PREFIX = "data/"
_SYMBOL_SUFFIX = re.compile(r"::[^\s]+$")
_PAREN_SUFFIX = re.compile(r"\s*\([^)]*\)\s*$")


def refuse_authority_grant(authority: Mapping[str, Any] | None) -> None:
    """Refuse (raise) if a caller tries to set any authority flag true."""
    if not isinstance(authority, Mapping):
        return
    for name in AUTHORITY_FLAGS:
        if authority.get(name) is True:
            raise ValueError(
                f"{name} must stay false; SNI A33 checker refuses authority"
            )


def strip_owner_suffix(raw: str) -> str:
    """Strip a trailing ::symbol or (...) suffix from an owner path string."""
    path = raw.strip()
    path = _SYMBOL_SUFFIX.sub("", path)
    path = _PAREN_SUFFIX.sub("", path)
    return path.strip()


def recount_statuses(metrics: Mapping[str, Any]) -> dict[str, int]:
    """Recount metrics statuses, including total."""
    tallies: Counter[str] = Counter()
    for cell in metrics.values():
        if isinstance(cell, Mapping):
            status = cell.get("status")
            if isinstance(status, str):
                tallies[status] += 1
    counted = {name: int(tallies.get(name, 0)) for name in COUNT_STATUSES}
    for name, n in tallies.items():
        if name not in counted:
            counted[name] = int(n)
    counted["total"] = len(metrics)
    return counted


def structural_errors(report: Mapping[str, Any]) -> list[str]:
    """Return structural errors on a loaded coverage report.

    Each of the following is an error:
    - wrong schema;
    - any authority flag not literal False (`is False`, not falsy);
    - a missing authority flag;
    - `counts` disagreeing with a recount of `metrics` statuses, total included;
    - any A33 class missing;
    - an A33 `best_cell` that is non-null but absent from `metrics`;
    - an A33 `best_status` disagreeing with `metrics[best_cell]["status"]`;
    - an `owner_native_cell` that is non-null while its cell's status is not OWNER_NATIVE.
    """
    errors: list[str] = []
    if report.get("schema") != SCHEMA:
        errors.append(
            f"schema {report.get('schema')!r} is not {SCHEMA!r}"
        )
    authority = report.get("authority")
    if not isinstance(authority, Mapping):
        errors.append("authority mapping missing")
        for name in AUTHORITY_FLAGS:
            errors.append(f"missing authority flag {name}")
    else:
        for name in AUTHORITY_FLAGS:
            if name not in authority:
                errors.append(f"missing authority flag {name}")
            elif authority[name] is not False:
                errors.append(
                    f"authority flag {name} is not literal False"
                )
    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping):
        errors.append("metrics mapping missing")
        metrics = {}
    counts = report.get("counts")
    expected = recount_statuses(metrics)
    if counts != expected:
        errors.append(f"counts disagree: report={counts!r} recount={expected!r}")
    a33 = report.get("a33_required_source_classes")
    if not isinstance(a33, Mapping):
        a33 = {}
        errors.append("a33_required_source_classes mapping missing")
    for cls in A33_CLASSES:
        if cls not in a33:
            errors.append(f"missing A33 class {cls}")
            continue
        info = a33[cls]
        if not isinstance(info, Mapping):
            errors.append(f"A33 class {cls} is not a mapping")
            continue
        best_cell = info.get("best_cell")
        best_status = info.get("best_status")
        if best_cell is not None:
            if best_cell not in metrics:
                errors.append(
                    f"A33 {cls} best_cell {best_cell!r} absent from metrics"
                )
            else:
                cell = metrics[best_cell]
                cell_status = (
                    cell.get("status") if isinstance(cell, Mapping) else None
                )
                if best_status != cell_status:
                    errors.append(
                        f"A33 {cls} best_status {best_status!r} disagrees with "
                        f"metrics[{best_cell!r}] status {cell_status!r}"
                    )
        native = info.get("owner_native_cell")
        if native is not None:
            if native not in metrics:
                errors.append(
                    f"A33 {cls} owner_native_cell {native!r} absent from metrics"
                )
            else:
                cell = metrics[native]
                cell_status = (
                    cell.get("status") if isinstance(cell, Mapping) else None
                )
                if cell_status != "OWNER_NATIVE":
                    errors.append(
                        f"A33 {cls} owner_native_cell {native!r} status is "
                        f"{cell_status!r} not OWNER_NATIVE"
                    )
    return errors


def owner_path_error(raw: Any, repo_root: Path) -> str | None:
    """Return a rejection reason for one owner path, or None if it qualifies.

    Every owner path, after stripping the suffix:
    - must not sit under `tests/`;
    - must not contain `fixture`, `synthetic`, `mock` or `fake` (case-insensitive);
    - if it starts with `engine/`, `scripts/`, `config/`, `lib/` or `research/`
      (and `collectors/`, the remaining in-repo owner tree cited by E1/E2),
      must exist under repo_root;
    - if it starts with `data/`, is NOT checked for existence (data/ is absent
      from sparse and CI checkouts), but its prefix is still checked;
    - any other prefix is an error. Keep this rule; surface the error instead
      of guessing.
    """
    if not isinstance(raw, str):
        return f"owner path is not a string: {raw!r}"
    path = strip_owner_suffix(raw)
    if not path:
        return f"owner path empty after suffix strip: {raw!r}"
    posix = path.replace("\\", "/")
    if posix == "tests" or posix.startswith("tests/"):
        return f"owner sits under tests/: {posix}"
    folded = posix.casefold()
    for token in BANNED_OWNER_TOKENS:
        if token in folded:
            return f"owner contains {token!r}: {posix}"
    if posix.startswith(EXISTENCE_PREFIXES):
        if not (repo_root / posix).exists():
            return f"owner path missing under repo_root: {posix}"
        return None
    if posix.startswith(DATA_PREFIX):
        return None
    return f"owner prefix not allowed (not guessed): {posix}"


def real_cells(report: Mapping[str, Any], repo_root: Path | str) -> list[str]:
    """Return the cells that count as real current evidence.

    A real cell has status in LIVE_STATUSES, evidence_rows > 0, a key that
    does not start with PILOT_PREFIX, and a non-empty owner list. Every
    owner path, after stripping the suffix, must qualify under
    owner_path_error (no tests/, no fixture/synthetic/mock/fake, known
    prefix, in-repo code path exists). An unknown prefix is an error and
    drops the cell; it is not guessed to exist.
    """
    root = Path(repo_root)
    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping):
        return []
    qualified: list[str] = []
    for key, cell in metrics.items():
        if not isinstance(key, str) or not isinstance(cell, Mapping):
            continue
        if cell.get("status") not in LIVE_STATUSES:
            continue
        rows = cell.get("evidence_rows")
        if not isinstance(rows, int) or rows <= 0:
            continue
        if key.startswith(PILOT_PREFIX):
            continue
        owners = cell.get("owner")
        if not isinstance(owners, list) or len(owners) == 0:
            continue
        if any(owner_path_error(item, root) is not None for item in owners):
            continue
        qualified.append(key)
    qualified.sort()
    return qualified


def real_evidence_present(
    report: Mapping[str, Any], repo_root: Path | str
) -> tuple[bool, list[str]]:
    """True iff structural_errors is empty AND real_cells is non-empty."""
    reasons: list[str] = []
    errors = structural_errors(report)
    if errors:
        reasons.extend(errors)
    cells = real_cells(report, repo_root)
    if not cells:
        reasons.append("no real current evidence cells")
    return (not errors and bool(cells), reasons)


def _class_gap_reason(cls: str, info: Mapping[str, Any]) -> str:
    status = info.get("best_status")
    blocking = info.get("blocking_missing_descriptors") or []
    if isinstance(blocking, list):
        names = [item for item in blocking if isinstance(item, str)]
    else:
        names = []
    if names:
        return f"{cls}: {status} ({', '.join(names)})"
    return f"{cls}: {status}"


def reference_floor(
    report: Mapping[str, Any], repo_root: Path | str
) -> tuple[bool, list[str]]:
    """True iff real_evidence_present holds AND every A33 class clears the floor.

    Every A33 class must have best_status in LIVE_STATUSES with its
    best_cell inside real_cells. reasons names each failing class with
    its best_status and blocking_missing_descriptors, e.g.
    `identity_listing: REFUSED (issuer_subject)`.
    """
    present, _present_reasons = real_evidence_present(report, repo_root)
    cells = set(real_cells(report, repo_root))
    a33 = report.get("a33_required_source_classes")
    if not isinstance(a33, Mapping):
        a33 = {}
    reasons: list[str] = []
    for cls in A33_CLASSES:
        info = a33.get(cls)
        if not isinstance(info, Mapping):
            reasons.append(f"{cls}: missing")
            continue
        best_status = info.get("best_status")
        best_cell = info.get("best_cell")
        live_ok = best_status in LIVE_STATUSES
        in_real = isinstance(best_cell, str) and best_cell in cells
        if not (live_ok and in_real):
            reasons.append(_class_gap_reason(cls, info))
    ok = bool(present) and not reasons
    return ok, reasons


def a33_class_table(
    report: Mapping[str, Any], repo_root: Path | str
) -> list[dict[str, Any]]:
    """Per-company A33 class rows for the review table and for tests.

    Columns: class, best_cell, best_status, in_real_cells,
    blocking_missing_descriptors, would_be_owner.
    """
    cells = set(real_cells(report, repo_root))
    a33 = report.get("a33_required_source_classes")
    if not isinstance(a33, Mapping):
        a33 = {}
    rows: list[dict[str, Any]] = []
    for cls in A33_CLASSES:
        info = a33.get(cls) if isinstance(a33.get(cls), Mapping) else {}
        best_cell = info.get("best_cell")
        blocking = info.get("blocking_missing_descriptors") or []
        if not isinstance(blocking, list):
            blocking = []
        rows.append(
            {
                "class": cls,
                "best_cell": best_cell,
                "best_status": info.get("best_status"),
                "in_real_cells": bool(
                    isinstance(best_cell, str) and best_cell in cells
                ),
                "blocking_missing_descriptors": list(blocking),
                "would_be_owner": info.get("would_be_owner"),
            }
        )
    return rows
