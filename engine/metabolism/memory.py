"""engine.metabolism.memory — Append-only memory artifacts + anti-rot (V2-D §2).

Three append-only git artifacts:
  data/metabolism/fitness_history.jsonl   — SENSE/organism_state appends per run
  data/metabolism/lessons.jsonl           — VERIFY appends {cycle_id, verdict,
                                             what_worked, what_failed, construction}
  data/metabolism/agenda_archive/<cycle>.json — agenda archive-on-verify step

Anti-rot: when lessons.jsonl exceeds LESSONS_BYTE_CAP, a re-summarize helper
compresses old entries into a summary block; the raw tail feeds the next prompt.
The summary is display-tier only — never gate-altering.

All functions are NEVER-RAISE and return safe fallbacks on any error.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

SCHEMA_FITNESS_HISTORY = "metabolism.fitness_history.v1"
SCHEMA_LESSONS = "metabolism.lessons.v1"

# Per-lobe directory form (matches organism_state._load_fitness_history reader).
# Rows lacking a lobe_id go to the quarantine file.
FITNESS_HISTORY_DIR = ("data", "metabolism", "fitness_history")
FITNESS_HISTORY_QUARANTINE = "data/metabolism/fitness_history/_unattributed.jsonl"
LESSONS_PATH = ("data", "metabolism", "lessons.jsonl")
AGENDA_ARCHIVE_DIR = ("data", "metabolism", "agenda_archive")

# Anti-rot byte cap: when lessons.jsonl exceeds this, trigger re-summarization
LESSONS_BYTE_CAP = 60_000
# Number of bytes to keep as the "raw tail" after compression
LESSONS_TAIL_BYTES = 8_000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_root(root: Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parent.parent.parent


# ── fitness_history.jsonl ─────────────────────────────────────────────────────

def append_fitness_history(
    run_id: str,
    lobe: str | None,
    sensors: dict[str, Any],
    root: Path | None = None,
) -> bool:
    """Append a fitness snapshot to the per-lobe fitness history file.

    Writes to data/metabolism/fitness_history/<lobe_id>.jsonl (per-lobe
    directory form, matching organism_state._load_fitness_history reader).

    If lobe is None or empty the row goes to the quarantine file
    data/metabolism/fitness_history/_unattributed.jsonl so the B5 fork is
    always fail-closed: a missing lobe_id never silently discards data.

    Called by SENSE / organism_state stage per run.
    Returns True on success, False on any error.  NEVER raises.
    """
    try:
        repo = _repo_root(root)
        hist_dir = repo.joinpath(*FITNESS_HISTORY_DIR)
        hist_dir.mkdir(parents=True, exist_ok=True)

        row = {
            "schema": SCHEMA_FITNESS_HISTORY,
            "ts": _now_iso(),
            "run_id": run_id,
            "lobe": lobe,
            "sensors": sensors or {},
        }

        # Choose target file: per-lobe or quarantine
        lobe_slug = (lobe or "").strip()
        if lobe_slug:
            target = hist_dir / f"{lobe_slug}.jsonl"
        else:
            target = repo / FITNESS_HISTORY_QUARANTINE
            target.parent.mkdir(parents=True, exist_ok=True)
            log.warning(
                "memory.append_fitness_history: lobe_id missing — routing to quarantine %s",
                target,
            )

        with target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, separators=(",", ":"), default=str) + "\n")
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("memory.append_fitness_history: %s", exc)
        return False


def load_fitness_history(
    root: Path | None = None,
    lobe: str | None = None,
    tail_n: int | None = None,
) -> list[dict[str, Any]]:
    """Load per-lobe fitness history rows.

    Reads data/metabolism/fitness_history/<lobe_id>.jsonl when a lobe is
    specified (the canonical per-lobe form matched by the reader in
    organism_state._load_fitness_history).

    When lobe is None, iterates all *.jsonl files in the directory (excluding
    the quarantine file) and returns all rows, sorted by 'ts' ascending.

    Returns a list of rows (may be empty).  NEVER raises.
    """
    try:
        repo = _repo_root(root)
        hist_dir = repo.joinpath(*FITNESS_HISTORY_DIR)
        if not hist_dir.exists():
            return []

        rows: list[dict[str, Any]] = []

        if lobe is not None:
            # Per-lobe read: single file
            lobe_slug = lobe.strip()
            p = hist_dir / f"{lobe_slug}.jsonl"
            if not p.exists():
                return []
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:  # noqa: BLE001
                    continue
        else:
            # Whole-dir scan (skip quarantine file)
            quarantine_name = "_unattributed.jsonl"
            for fpath in sorted(hist_dir.glob("*.jsonl")):
                if fpath.name == quarantine_name:
                    continue
                try:
                    for line in fpath.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rows.append(json.loads(line))
                        except Exception:  # noqa: BLE001
                            continue
                except Exception as exc:  # noqa: BLE001
                    log.warning("memory.load_fitness_history: cannot read %s — %s", fpath, exc)

            # Sort by ts ascending for cross-lobe callers
            rows.sort(key=lambda r: str(r.get("ts") or ""))

        if tail_n is not None:
            rows = rows[-tail_n:]
        return rows
    except Exception as exc:  # noqa: BLE001
        log.warning("memory.load_fitness_history: %s", exc)
        return []


# ── lessons.jsonl ─────────────────────────────────────────────────────────────

def append_lesson(
    cycle_id: str,
    verdict: str,
    what_worked: str,
    what_failed: str,
    construction: str,
    proposal_id: str | None = None,
    lobe: str = "",
    root: Path | None = None,
) -> bool:
    """Append a lesson to data/metabolism/lessons.jsonl.

    Called by VERIFY after each proposal outcome so PROPOSE stops repeating
    dead constructions.  The optional lobe field enables lobe-exact recall
    scoring in engine.metabolism.recall (BUG 3 fix).  Old rows without the
    field parse fine — recall falls back to text-bag matching.

    Returns True on success, False on error.  NEVER raises.
    """
    try:
        repo = _repo_root(root)
        p = repo.joinpath(*LESSONS_PATH)
        row = {
            "schema": SCHEMA_LESSONS,
            "ts": _now_iso(),
            "cycle_id": cycle_id,
            "proposal_id": proposal_id,
            "lobe": lobe or "",
            "verdict": verdict,
            "what_worked": what_worked or "",
            "what_failed": what_failed or "",
            "construction": construction or "",
        }
        from scripts.metabolism_journal import owned_bytes
        with owned_bytes(repo, "lessons", "lessons") as owner:
            before = owner.read()
            raw = before["raw"] or b""
            if raw and not raw.endswith(b"\n"):
                raise ValueError("lessons_partial_tail")
            owner.replace(before, raw + (json.dumps(row, separators=(",", ":"), default=str) + "\n").encode())
        log.info("memory.append_lesson: cycle=%s verdict=%s lobe=%s", cycle_id, verdict, lobe or "")
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("memory.append_lesson: %s", exc)
        return False


def load_recent_lessons(
    root: Path | None = None,
    byte_cap: int = LESSONS_TAIL_BYTES,
) -> str:
    """Return the tail of lessons.jsonl as a text string, byte-capped.

    Returns '(lessons.jsonl not yet present — accruing)' if absent.
    NEVER raises.
    """
    try:
        repo = _repo_root(root)
        p = repo.joinpath(*LESSONS_PATH)
        if not p.exists():
            return "(lessons.jsonl not yet present — accruing)"
        text = p.read_text(encoding="utf-8")
        encoded = text.encode()
        if len(encoded) <= byte_cap:
            return text
        tail = encoded[-byte_cap:].decode(errors="replace")
        return "(tail)\n" + tail
    except Exception as exc:  # noqa: BLE001
        log.warning("memory.load_recent_lessons: %s", exc)
        return "(lessons unavailable)"


def _needs_resummary(root: Path | None = None) -> bool:
    """Return True if lessons.jsonl exceeds the anti-rot byte cap."""
    try:
        repo = _repo_root(root)
        p = repo.joinpath(*LESSONS_PATH)
        if not p.exists():
            return False
        size = p.stat().st_size
        return size > LESSONS_BYTE_CAP
    except Exception:  # noqa: BLE001
        return False


def _lesson_parts(raw: bytes) -> tuple[bytes, bytes]:
    if len(raw) <= LESSONS_TAIL_BYTES:
        return b"", raw
    boundary = raw.find(b"\n", len(raw) - LESSONS_TAIL_BYTES)
    boundary = len(raw) if boundary < 0 else boundary + 1
    return raw[:boundary], raw[boundary:]


def _lesson_source(snapshot: dict) -> dict:
    import hashlib
    raw = snapshot["raw"]
    if raw is None:
        raise ValueError("lessons_source_missing")
    prefix, tail = _lesson_parts(raw)
    return {
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        "file_identity": list(snapshot["identity"]),
        "prefix_sha256": hashlib.sha256(prefix).hexdigest(), "prefix_bytes": len(prefix),
        "tail_sha256": hashlib.sha256(tail).hexdigest(), "tail_bytes": len(tail),
    }


def capture_lessons_for_resummary(root: Path, *, max_prefix_bytes: int = 128 * 1024) -> tuple[dict, str]:
    """Capture the exact discarded prefix; a partial summary never discards unseen rows."""
    from scripts.metabolism_journal import owned_bytes, strict_json
    repo = _repo_root(root)
    with owned_bytes(repo, "lessons", "lessons") as owner:
        before = owner.read()
        source = _lesson_source(before)
        raw = before["raw"]
        if raw and not raw.endswith(b"\n"):
            raise ValueError("lessons_partial_tail")
        for line in raw.splitlines():
            if line.strip() and type(strict_json(line)) is not dict:
                raise ValueError("lessons_row_invalid")
        prefix, _ = _lesson_parts(raw)
        if not prefix or len(prefix) > max_prefix_bytes:
            raise ValueError("lessons_summary_input_bound")
        return source, prefix.decode("utf-8")


def resummary_lessons(
    summary_text: str,
    root: Path | None = None,
    *,
    expected_source: dict | None = None,
    receipt: dict | None = None,
) -> bool:
    """Replace under the append owner's lock; selected callers compare the captured source.

    Legacy callers retain the boolean interface. The optional receipt is returned
    directly to the incumbent journal caller; it is not another state file.
    """
    try:
        import hashlib
        from scripts.metabolism_journal import owned_bytes
        repo = _repo_root(root)
        if not isinstance(summary_text, str) or not summary_text.strip():
            return False
        if receipt is not None and (type(receipt) is not dict or receipt):
            return False
        with owned_bytes(repo, "lessons", "lessons") as owner:
            before = owner.read()
            if before["raw"] is None:
                return False
            source = _lesson_source(before)
            if expected_source is not None and source != expected_source:
                return False
            raw = before["raw"]
            _, tail = _lesson_parts(raw)
            # Decode strictly: a byte boundary is always immediately after a newline.
            tail_text = tail.decode("utf-8")
            summary_row = {
                "schema": SCHEMA_LESSONS, "ts": _now_iso(), "is_summary": True,
                "summary": summary_text,
                "note": (
                    "Anti-rot compression: this row summarizes lessons prior to the tail. "
                    "Display-only — never gate-altering. The raw tail follows."
                ),
            }
            if expected_source is not None:
                summary_row["source_coverage"] = {k: v for k, v in source.items() if k != "file_identity"}
            new_content = (json.dumps(summary_row, separators=(",", ":"), default=str) + "\n" + tail_text).encode()
            after = owner.replace(before, new_content)
            if receipt is not None:
                receipt.update({"source": source,
                    "summary_sha256": hashlib.sha256(summary_text.encode()).hexdigest(),
                    "result_sha256": hashlib.sha256(after["raw"]).hexdigest(),
                    "result_bytes": len(after["raw"]), "result_identity": list(after["identity"])})
        log.info("memory.resummary_lessons: compressed to %d bytes", len(new_content))
        return True
    except Exception as exc:
        log.warning("memory.resummary_lessons held (%s)", type(exc).__name__)
        return False


# ── agenda_archive/ ───────────────────────────────────────────────────────────

def archive_agenda(
    cycle_id: str,
    agenda_data: dict[str, Any],
    verify_outcome: dict[str, Any] | None = None,
    root: Path | None = None,
) -> bool:
    """Archive a completed agenda + graded outcome to data/metabolism/agenda_archive/.

    Called by the VERIFY stage after grading.  The archived file carries both
    the original agenda and the realized outcome so the dream cycle can compare
    what was proposed vs what materialized.

    Returns True on success.  NEVER raises.
    """
    try:
        repo = _repo_root(root)
        archive_dir = repo.joinpath(*AGENDA_ARCHIVE_DIR)
        archive_dir.mkdir(parents=True, exist_ok=True)

        payload: dict[str, Any] = {
            "schema": "metabolism.agenda_archive.v1",
            "cycle_id": cycle_id,
            "archived_at": _now_iso(),
            "agenda": agenda_data,
            "verify_outcome": verify_outcome or {},
        }

        out_path = archive_dir / f"{cycle_id}.json"
        tmp = out_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        tmp.replace(out_path)
        log.info("memory.archive_agenda: wrote %s", out_path)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("memory.archive_agenda: %s", exc)
        return False


def load_agenda_archive(
    root: Path | None = None,
    tail_n: int = 20,
) -> list[dict[str, Any]]:
    """Load the most recent agenda_archive entries (up to tail_n).

    Returns a list sorted oldest-first.  NEVER raises.
    """
    try:
        repo = _repo_root(root)
        archive_dir = repo.joinpath(*AGENDA_ARCHIVE_DIR)
        if not archive_dir.exists():
            return []
        files = sorted(archive_dir.glob("*.json"))
        if tail_n:
            files = files[-tail_n:]
        results: list[dict[str, Any]] = []
        for f in files:
            try:
                results.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                continue
        return results
    except Exception as exc:  # noqa: BLE001
        log.warning("memory.load_agenda_archive: %s", exc)
        return []
