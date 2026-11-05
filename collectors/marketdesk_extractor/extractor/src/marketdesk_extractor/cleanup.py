"""Local artifact cleanup — reclaim disk by pruning PDFs already safe in R2.

Safety model:
- Only deletes **local** files. Never touches R2/Dropbox or the SQLite rows, so the
  dedup memory is preserved: a pruned paper is still "seen" and never re-downloaded.
- By default only prunes papers whose status is COMPLETE/UPLOADED **and** that carry an
  ``r2_pdf_key`` (i.e. the durable copy is confirmed in R2). Pass ``require_r2=False`` to
  override (not recommended).
- Age-gated (``older_than_days``) and supports ``dry_run`` to preview.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import db
from .config import Config
from .pipeline import _artifact_paths
from .schemas import Status
from .utils import get_logger

log = get_logger("cleanup")


@dataclass
class CleanupResult:
    considered: int = 0
    pruned_pdfs: int = 0
    pruned_markdown: int = 0
    pruned_metadata: int = 0
    bytes_freed: int = 0
    skipped_no_r2: int = 0
    skipped_no_vault: int = 0
    skipped_recent: int = 0
    dry_run: bool = False

    def summary(self) -> str:
        mb = self.bytes_freed / 1_048_576
        verb = "would free" if self.dry_run else "freed"
        return (
            f"considered={self.considered} pruned_pdfs={self.pruned_pdfs} "
            f"pruned_md={self.pruned_markdown} pruned_meta={self.pruned_metadata} "
            f"{verb}={mb:.1f}MB skipped_no_r2={self.skipped_no_r2} "
            f"skipped_no_vault={self.skipped_no_vault} "
            f"skipped_recent={self.skipped_recent}"
            + (" [DRY-RUN]" if self.dry_run else "")
        )


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def prune_local(
    cfg: Config,
    conn,
    *,
    older_than_days: int = 7,
    dry_run: bool = False,
    require_r2: bool = True,
    require_vault: bool = False,
    include_markdown: bool = False,
    include_metadata: bool = False,
) -> CleanupResult:
    """Delete local PDF (and optionally markdown/metadata) files already archived off-box.

    Durability gate — what proves it is safe to delete the local copy:
    - ``require_vault=True``  -> the paper carries a ``vault_key`` (its PDF is durable in
      the private Research Vault bucket). Use this when the vault bucket is the archive
      of record and the main-account R2 archive is off (``R2_ENABLED=false``), which is
      exactly when ``r2_pdf_key`` is always NULL and the r2 gate would skip everything.
    - ``require_r2=True`` (default) -> the paper carries an ``r2_pdf_key`` (main-account
      archive). ``require_vault`` takes precedence when set.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(0, older_than_days))
    rows = db.get_by_status(conn, [Status.COMPLETE, Status.UPLOADED])
    res = CleanupResult(dry_run=dry_run)

    def rm(path: Path | None) -> int:
        if not path or not Path(path).exists():
            return 0
        size = Path(path).stat().st_size
        if not dry_run:
            Path(path).unlink()
        return size

    for row in rows:
        res.considered += 1
        if require_vault:
            if not row["vault_key"]:
                res.skipped_no_vault += 1
                continue
        elif require_r2 and not row["r2_pdf_key"]:
            res.skipped_no_r2 += 1
            continue
        ts = _parse_iso(row["downloaded_at"] or row["uploaded_at"] or row["discovered_at"])
        if ts and ts > cutoff:
            res.skipped_recent += 1
            continue

        p = _artifact_paths(cfg, row)
        freed = rm(p["pdf_local"])
        if freed:
            res.pruned_pdfs += 1
            res.bytes_freed += freed
        if include_markdown and row["markdown_filename"]:
            f = rm(p["md_local"])
            if f:
                res.pruned_markdown += 1
                res.bytes_freed += f
        if include_metadata and row["metadata_filename"]:
            f = rm(p["meta_local"])
            if f:
                res.pruned_metadata += 1
                res.bytes_freed += f
        if freed:
            log.info("%s local artifacts for %s (%s)",
                     "would prune" if dry_run else "pruned", row["blob_id"],
                     p["pdf_name"])

    log.info("cleanup done: %s", res.summary())
    return res
