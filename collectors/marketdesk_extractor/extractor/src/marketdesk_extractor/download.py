"""Download authenticated blob PDFs, hash, dedup by SHA-256, name + persist."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import db
from .config import Config
from .marketdesk import MarketDeskClient
from .schemas import Status
from .storage import StorageGuardError
from .utils import (
    build_pdf_filename, date_str_from_unix, get_logger,
    jitter_sleep, sha256_bytes, utc_now,
)

log = get_logger("download")


@dataclass
class DownloadResult:
    downloaded: int = 0
    skipped_dup: int = 0
    skipped_low_priority: int = 0
    failed: int = 0
    blob_ids: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"downloaded={self.downloaded} dup={self.skipped_dup} "
            f"low_priority={self.skipped_low_priority} failed={self.failed}"
        )


def _date_str(row) -> str:
    # prefer publish date; fall back to a STABLE per-row value (discovery date),
    # never "now" — so an item's artifacts/keys never drift across run days.
    for col in ("published_at", "discovered_at"):
        v = row[col]
        if v and len(v) >= 10:
            return v[:10]
    return date_str_from_unix(None)


def download_one(
    cfg: Config, conn, client: MarketDeskClient, row, *, account: str | None = None
) -> Status:
    blob_id = row["blob_id"]
    # Check BEFORE the provider request so a missing/full volume never spends a
    # download attempt. Check again with the payload size before the atomic write.
    cfg.assert_storage_ready()
    data = client.download_blob(blob_id)  # raises on non-PDF / http error
    cfg.assert_storage_ready(extra_required_bytes=len(data))
    digest = sha256_bytes(data)

    owner = db.find_sha256_owner(conn, digest, exclude_blob_id=blob_id)
    if owner is not None:
        db.set_status(
            conn, blob_id, Status.SKIPPED_SEEN,
            error_message=f"duplicate sha256 of {owner['blob_id']}",
        )
        log.info("skip %s: duplicate PDF of %s", blob_id, owner["blob_id"])
        return Status.SKIPPED_SEEN

    filename = build_pdf_filename(
        date_str=_date_str(row), institution=row["institution"],
        title=row["title"] or "untitled", blob_id=blob_id,
    )
    dest = Path(cfg.raw_pdf_dir) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(f".{dest.name}.part")
    try:
        partial.write_bytes(data)
        partial.replace(dest)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        raise StorageGuardError(
            f"durable PDF write failed on guarded storage {dest.parent}: {exc}"
        ) from exc

    fields = dict(
        sha256=digest, pdf_filename=filename,
        downloaded_at=utc_now().isoformat(), status=Status.DOWNLOADED.value,
    )
    if account is not None:  # trickle path records which account pulled it
        fields["account"] = account
    db.update_fields(conn, blob_id, **fields)
    log.info("downloaded %s -> %s (%d bytes)%s", blob_id, filename, len(data),
             f" [{account}]" if account else "")
    return Status.DOWNLOADED


def download_pending(
    cfg: Config, conn, client: MarketDeskClient, *, limit: int | None = None,
    force: bool = False,
) -> DownloadResult:
    statuses = [Status.DISCOVERED, Status.BLOB_FOUND]
    if force:
        statuses += [Status.FAILED]
    rows = db.get_by_status(conn, statuses)
    if limit:
        rows = rows[:limit]
    res = DownloadResult()

    for row in rows:
        blob_id = row["blob_id"]
        score = row["local_priority_score"] or 0
        if (cfg.download_only_above_priority and not force
                and score < cfg.priority_threshold):
            res.skipped_low_priority += 1
            continue
        try:
            status = download_one(cfg, conn, client, row)
            if status == Status.DOWNLOADED:
                res.downloaded += 1
                res.blob_ids.append(blob_id)
            elif status == Status.SKIPPED_SEEN:
                res.skipped_dup += 1
        except StorageGuardError:
            # Infrastructure failure, not a bad paper. Leave it DISCOVERED and
            # fail the command so launchd can retry after the volume recovers.
            raise
        except Exception as e:  # noqa: BLE001 - continue past a bad paper
            res.failed += 1
            db.set_status(conn, blob_id, Status.FAILED, error_message=str(e)[:500])
            log.error("download failed for %s: %s", blob_id, e)
        jitter_sleep()

    log.info("download pass done: %s", res.summary())
    return res
