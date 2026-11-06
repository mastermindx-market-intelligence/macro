"""C19 WP31 evaluator — GATES: prereg gates, registration act, exposure ledger.

Part of the Commission-19 WP31 incremental-information evaluator (lane GATES).
Source of truth: ``research/C19_WP31_INCREMENTAL_INFORMATION_PREREG.md``
(pre-registration, §8 Admission and trial accounting), merged on main as commit
``8e1950932b29f89a89da94c50ccef4ef5f2d8d1c``.  Build contract: the seat-frozen
WP31_BUILD_SPEC.md, sha256
``5485384ad1f08a0211f634045d23d623d7e4d961924d5b9f5911ea6081149ef1``
(section "Gates and registration (prereg §8)").

What this module enforces (prereg §8.5):
  * G-1  the frozen-prefix sha256 of the prereg document matches the embedded
    constant (amendments append AFTER the §10 marker and never change it);
  * G-2  PREREG_COMMIT is 40-hex and an ancestor of HEAD — fail-closed on any
    probe error;
  * G-3  the trial ledger holds a ``declared_budget`` row for this family whose
    reason carries BOTH frozen identifiers, alongside pre-existing unrelated
    families (the anti-truncation assertion — a sparse-tree write that replaced
    the fleet ledger with a one-family file refuses);
  * REG  the registration act itself: one idempotent ``register_trials`` budget
    declaration, never from a sparse worktree, never on the default ledger;
  * EXPOSURE  the per-episode label-read ledger (append-only, first-read-wins).

Design: pure logic with injected environmental facts (doc bytes, ancestry
probe, ledger lines, ledger/exposure paths) — mirroring
``engine/entry_radar/replay/gates.py``, whose algorithms for
``frozen_prefix`` / ``check_doc_hash`` / ``check_merged_ancestry`` /
``check_budget_row`` are re-implemented here with THIS program's constants
(no import from ``engine/entry_radar``: its constants differ).  Refusal is an
exception (``WP31Refusal``), never a return code; passing gates return
``{"gate": ..., "detail": ...}`` receipt dicts.  No I/O at import time;
standard library only.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Callable, Iterable, Mapping

# --------------------------------------------------------------------------- #
# Frozen constants (prereg §8; WP31_BUILD_SPEC "Gates and registration")
# --------------------------------------------------------------------------- #
FAMILY = "c19_wp31_incremental_information"
BUDGET = 6
BASIS = "itemized"
BASIS_ITEMS = (
    "primary_delta",
    "hr_a1_minus_hr_a0",
    "a2_minus_s_vs_a2_minus_k",
    "economic_translation_a2",
    "split_aapl",
    "split_homebuilders",
)
PREREG_DOC = "research/C19_WP31_INCREMENTAL_INFORMATION_PREREG.md"
PREREG_COMMIT = "8e1950932b29f89a89da94c50ccef4ef5f2d8d1c"
PREREG_DOC_SHA256 = "44c9df659288c64987758f8408c2b7eced41488e57251c4390ddd466bf1f7a43"
PREREG_FROZEN_MARKER = "## \u00a710 Amendments (append-only"
EVALUATOR_READER = "c19_wp31_evaluator"


class WP31Refusal(RuntimeError):
    """A WP31 gate refused.  ``.gate`` names it: G-1 / G-2 / G-3 / REG / EXPOSURE."""

    def __init__(self, gate: str, msg: str) -> None:
        super().__init__(f"{gate}: {msg}")
        self.gate = gate


def _refuse(gate: str, msg: str) -> None:
    raise WP31Refusal(gate, msg)


def _receipt(gate: str, detail: str) -> dict:
    return {"gate": gate, "detail": detail}


# --------------------------------------------------------------------------- #
# G-1 — prereg frozen-prefix hash.
# Mirrors engine/entry_radar/replay/gates.py:45-59 (frozen_prefix) and
# :62-71 (check_doc_hash) with this program's constants.
# --------------------------------------------------------------------------- #
def frozen_prefix(doc_bytes: bytes) -> bytes:
    """The bytes G-1 hashes: everything up to and INCLUDING the §10 marker line.

    Refuses (fail-closed) when the marker is absent — a prereg without its
    amendment fence is not the frozen document.  Identical algorithm to
    ``engine/entry_radar/replay/gates.py`` ``frozen_prefix`` (lines 45-59),
    with this program's marker constant (prereg §8.5: the §10 heading, not the
    entry-radar §16 marker).
    """
    marker = PREREG_FROZEN_MARKER.encode("utf-8")
    idx = doc_bytes.find(marker)
    if idx < 0:
        _refuse("G-1", f"frozen marker {PREREG_FROZEN_MARKER!r} absent "
                       "from the prereg document")
    end = doc_bytes.find(b"\n", idx)
    if end < 0:
        end = len(doc_bytes)
    return doc_bytes[: end + 1]


def check_doc_hash(doc_bytes: bytes) -> dict:
    """G-1: sha256 of the prereg's FROZEN PREFIX equals the frozen constant.

    Mirrors ``engine/entry_radar/replay/gates.py`` ``check_doc_hash``
    (lines 62-71), including its UNSET sentinel discipline.
    """
    if PREREG_DOC_SHA256 == "UNSET":
        _refuse("G-1", "PREREG_DOC_SHA256 is UNSET — the prereg has not been "
                       "stamped into the evaluator")
    got = hashlib.sha256(frozen_prefix(doc_bytes)).hexdigest()
    if got != PREREG_DOC_SHA256:
        _refuse("G-1", f"prereg frozen-prefix sha256 {got} != frozen "
                       f"{PREREG_DOC_SHA256}")
    return _receipt("G-1", f"frozen-prefix sha256 {got}")


# --------------------------------------------------------------------------- #
# G-2 — merged ancestry.
# Mirrors engine/entry_radar/replay/gates.py:77-93 (check_merged_ancestry).
# --------------------------------------------------------------------------- #
def check_merged_ancestry(is_ancestor_of_head: Callable[[str], bool]) -> dict:
    """G-2: the recorded prereg commit is an ancestor of the evaluator's HEAD.

    ``is_ancestor_of_head`` is injected (the runner passes a closure over
    ``git merge-base --is-ancestor``); a False answer or a raised error refuses
    (fail-closed).  Mirrors ``engine/entry_radar/replay/gates.py``
    ``check_merged_ancestry`` (lines 77-93) with this program's constants.
    """
    if PREREG_COMMIT == "UNSET":
        _refuse("G-2", "PREREG_COMMIT is UNSET — no merged prereg commit recorded")
    if not re.fullmatch(r"[0-9a-f]{40}", PREREG_COMMIT):
        _refuse("G-2", f"PREREG_COMMIT {PREREG_COMMIT!r} is not a 40-hex sha")
    try:
        ok = bool(is_ancestor_of_head(PREREG_COMMIT))
    except Exception as exc:  # noqa: BLE001 — fail closed, name the failure
        _refuse("G-2", f"ancestry probe raised {exc!r} (fail-closed)")
    if not ok:
        _refuse("G-2", f"prereg commit {PREREG_COMMIT} is not an ancestor of HEAD")
    return _receipt("G-2", f"prereg commit {PREREG_COMMIT} is merged history")


# --------------------------------------------------------------------------- #
# G-3 — TrialLedger declared-budget admission.
# Mirrors engine/entry_radar/replay/gates.py:99-138 (check_budget_row),
# including the pre-existing-families anti-truncation block (lines 109-138).
# Difference by spec: this family's budget row admits n >= BUDGET (prereg §8.3
# "budgets only rise"), where entry_radar pins == its frozen 253.
# --------------------------------------------------------------------------- #
def check_budget_row(ledger_lines: Iterable[str]) -> dict:
    """G-3: data/trial_ledger.jsonl holds this family's declared_budget row
    whose reason carries exactly the G-1/G-2 identifiers and n >= BUDGET —
    AND the ledger already carries pre-existing unrelated families (the
    anti-truncation assertion mirrored from ``engine/entry_radar/replay/gates.py``
    lines 109-138: a sparse-tree write would have replaced the fleet ledger
    with a one-family file; that state refuses)."""
    want_reason_bits = (
        f"w5_prereg={PREREG_COMMIT}",
        f"doc_sha256={PREREG_DOC_SHA256}",
    )
    found = False
    other_families: set[str] = set()
    for line in ledger_lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001 — torn line tolerated, never counted
            continue
        fam = row.get("family")
        if fam and fam != FAMILY:
            other_families.add(str(fam))
        if (row.get("kind") == "declared_budget"
                and fam == FAMILY
                and int(row.get("n", -1)) >= BUDGET):
            reason = str(row.get("reason") or "")
            if all(bit in reason for bit in want_reason_bits):
                found = True
    if not found:
        _refuse("G-3", "no declared_budget row for family "
                       f"{FAMILY!r} with n>={BUDGET} "
                       "carrying the frozen prereg identifiers")
    if not other_families:
        _refuse("G-3", "trial ledger carries no pre-existing families — this is "
                       "the sparse-tree truncation signature; refuse rather than "
                       "bless a corrupt store")
    return _receipt("G-3", f"budget row n>={BUDGET} admitted beside "
                           f"{len(other_families)} pre-existing families")


# --------------------------------------------------------------------------- #
# REG — the registration act (prereg §8.3–§8.4)
# --------------------------------------------------------------------------- #
def registration_reason() -> str:
    """The frozen budget-row reason: prereg commit + doc hash + itemized basis."""
    return (f"w5_prereg={PREREG_COMMIT} doc_sha256={PREREG_DOC_SHA256} "
            f"basis=itemized:" + ",".join(BASIS_ITEMS))


def register(ledger: "object | None", *, allow_sparse_for_test: bool = False,
             repo_root: "str | Path | None" = None) -> dict:
    """Write this family's declared-budget row through ``register_trials``.

    Prereg §8.4: budget=6, basis itemized, reason = ``registration_reason()``
    (carrying PREREG_COMMIT and PREREG_DOC_SHA256), written before any label is
    read, on the lane that owns trial-ledger appends — NEVER from a sparse
    worktree.  ``register_trials`` is idempotent (dedup on family+n+reason), so
    a re-run does not add a second row.

    Refuses with gate ``REG`` when:
      * ``ledger`` is None — the default ``TrialLedger()`` would silently point
        at the production ``data/trial_ledger.jsonl``; the caller must pass the
        ledger it owns;
      * ``scripts.worktree_sparse.missing_dirs()`` reports a non-materialized
        top-level dir (sparse signature), unless the caller explicitly passes
        ``allow_sparse_for_test=True``.
    """
    if ledger is None:
        _refuse("REG", "register() requires an explicit ledger — refusing to fall "
                       "through to the default production trial ledger")
    from scripts import worktree_sparse  # lazy: keeps import side-effect free
    root = Path(repo_root) if repo_root is not None else None
    missing = (worktree_sparse.missing_dirs(root) if root is not None
               else worktree_sparse.missing_dirs())
    if missing and not allow_sparse_for_test:
        _refuse("REG", f"refusing registration from a sparse worktree; missing "
                       f"top-level dirs: {missing} "
                       "(materialize the tree, or pass allow_sparse_for_test=True "
                       "explicitly in a test)")
    from engine.trial_ledger import register_trials
    with register_trials(FAMILY, budget=BUDGET, reason=registration_reason(),
                         basis="itemized", ledger=ledger):
        pass
    return _receipt("REG", f"declared_budget family={FAMILY!r} n={BUDGET} "
                           f"basis={BASIS} written (idempotent)")


# --------------------------------------------------------------------------- #
# EXPOSURE — per-episode label-read ledger (prereg §6 "Exposure ledger")
# --------------------------------------------------------------------------- #
def _exposure_rows(path: "str | Path") -> list[dict]:
    """Read the exposure JSONL at ``path``; missing file → []; torn lines skipped
    exactly as the gates skip them (tolerated, never counted)."""
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    rows: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001 — torn line tolerated, never counted
            continue
        if type(row) is not dict:
            continue
        rows.append(row)
    return rows


def record_label_read(path: "str | Path", issuer: str, q: str, reader: str,
                      at_iso: str) -> dict:
    """Append the FIRST label-read row for (issuer, q); first-read-wins.

    Append-only JSONL at the caller-given ``path`` (created if absent): a row
    ``{"issuer", "q", "reader", "at"}`` is appended only when no row for
    ``(issuer, q)`` exists yet; an existing first row is returned unchanged and
    the file is never rewritten.
    """
    p = Path(path)
    for row in _exposure_rows(p):
        if row.get("issuer") == issuer and row.get("q") == q:
            return row
    row = {"issuer": issuer, "q": q, "reader": reader, "at": at_iso}
    if p.parent is not None and str(p.parent) not in ("", "."):
        p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def first_label_read(path: "str | Path", issuer: str, q: str) -> "dict | None":
    """The first exposure row for (issuer, q), or None (missing file counts as
    no reads)."""
    for row in _exposure_rows(path):
        if row.get("issuer") == issuer and row.get("q") == q:
            return row
    return None


def is_exposed(path: "str | Path", issuer: str, q: str) -> bool:
    """True iff the FIRST label read for (issuer, q) was NOT by the evaluator
    (prereg §6: a human or agent label read outside the evaluator marks the
    episode EXPOSED).  No recorded read → False."""
    row = first_label_read(path, issuer, q)
    if row is None:
        return False
    return row.get("reader") != EVALUATOR_READER


__all__ = [
    "FAMILY", "BUDGET", "BASIS", "BASIS_ITEMS", "PREREG_DOC", "PREREG_COMMIT",
    "PREREG_DOC_SHA256", "PREREG_FROZEN_MARKER", "EVALUATOR_READER",
    "WP31Refusal", "frozen_prefix", "check_doc_hash", "check_merged_ancestry",
    "check_budget_row", "registration_reason", "register", "record_label_read",
    "first_label_read", "is_exposed",
]
