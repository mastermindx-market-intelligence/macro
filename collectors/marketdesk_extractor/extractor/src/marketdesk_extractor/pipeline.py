"""End-to-end orchestration + the offline parse/upload/manifest stages.

State machine:  DISCOVERED -> DOWNLOADED -> PARSED -> COMPLETE
(with SKIPPED_SEEN / SKIPPED_OLD / FAILED as terminal side states).

`discover` + `download` need the authenticated browser; `parse` / `upload` / `manifest`
are fully offline and can run independently (that's why they're separate CLI commands).
Parsing failures are non-fatal: the PDF is still uploaded + manifested.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import db
from .auth import BrowserSession
from .config import Config
from .discover import DiscoverResult, discover
from .download import DownloadResult, download_pending
from .marketdesk import MarketDeskClient
from .schemas import ManifestEntry, ParseResult, Status
from .utils import date_str_from_unix, get_logger, utc_now

log = get_logger("pipeline")


# ---------------------------------------------------------------------------
# path helpers
# ---------------------------------------------------------------------------
def _row_date(row) -> str:
    # prefer publish date; fall back to a STABLE per-row value (discovery date),
    # never "now" — keeps a paper's artifacts/keys on one date across stages.
    for col in ("published_at", "discovered_at"):
        v = row[col]
        if v and len(v) >= 10:
            return v[:10]
    return date_str_from_unix(None)


def _artifact_paths(cfg: Config, row) -> dict:
    """Local + logical filenames for a downloaded paper's artifacts."""
    date_str = _row_date(row)
    pdf_name = row["pdf_filename"]
    base = Path(pdf_name).stem if pdf_name else row["blob_id"]
    md_name = f"{base}.md"
    meta_name = f"{base}.json"
    return {
        "date_str": date_str,
        "base": base,
        "pdf_name": pdf_name,
        "pdf_local": Path(cfg.raw_pdf_dir) / pdf_name if pdf_name else None,
        "md_name": md_name,
        "md_local": Path(cfg.markdown_dir) / date_str / md_name,
        "meta_name": meta_name,
        "meta_local": Path(cfg.metadata_dir) / date_str / meta_name,
    }


# ---------------------------------------------------------------------------
# PARSE
# ---------------------------------------------------------------------------
@dataclass
class ParseSummary:
    parsed: int = 0
    failed: int = 0

    def summary(self) -> str:
        return f"parsed={self.parsed} failed={self.failed}"


def parse_pending(cfg: Config, conn, *, limit: int | None = None) -> ParseSummary:
    from .parse_pdf import parse_pdf  # local import: heavy deps are optional

    rows = db.get_by_status(conn, [Status.DOWNLOADED])
    if limit:
        rows = rows[:limit]
    res = ParseSummary()

    for row in rows:
        p = _artifact_paths(cfg, row)
        if not p["pdf_local"] or not p["pdf_local"].exists():
            db.set_status(conn, row["blob_id"], Status.FAILED,
                          error_message="PDF file missing before parse")
            res.failed += 1
            continue
        base_metadata = _base_metadata(cfg, row)
        p["md_local"].parent.mkdir(parents=True, exist_ok=True)
        p["meta_local"].parent.mkdir(parents=True, exist_ok=True)
        result: ParseResult = parse_pdf(
            p["pdf_local"], p["md_local"], p["meta_local"],
            backend=cfg.parser_backend, base_metadata=base_metadata,
        )
        fields = {
            "metadata_filename": p["meta_name"],
            "parsed_at": utc_now().isoformat(),
            "parser": result.parser,
            "page_count": result.page_count,
        }
        if result.status == Status.PARSED and result.markdown_path:
            fields["markdown_filename"] = p["md_name"]
        if result.status == Status.FAILED:
            fields["error_message"] = (result.error or "parse failed")[:500]
            res.failed += 1
        else:
            res.parsed += 1
        # advance to PARSED regardless (PDF + metadata exist); md optional
        fields["status"] = Status.PARSED.value
        db.update_fields(conn, row["blob_id"], **fields)

    log.info("parse pass done: %s", res.summary())
    return res


def _base_metadata(cfg: Config, row) -> dict:
    """The parse metadata JSON base (spec item 43)."""
    p = _artifact_paths(cfg, row)
    return {
        "blob_id": row["blob_id"],
        "title": row["title"],
        "institution": row["institution"],
        "article_url": row["article_url"],
        "blob_url": row["blob_url"],
        "published_at": row["published_at"],
        "marketdesk_age_text": row["marketdesk_age_text"],
        "marketdesk_summary": row["marketdesk_summary"],
        "local_priority_score": row["local_priority_score"],
        "sha256": row["sha256"],
        "original_pdf_path": str(p["pdf_local"]) if p["pdf_local"] else None,
        "discovered_at": row["discovered_at"],
        "downloaded_at": row["downloaded_at"],
    }


# ---------------------------------------------------------------------------
# UPLOAD
# ---------------------------------------------------------------------------
@dataclass
class UploadSummary:
    uploaded: int = 0
    completed_local: int = 0
    failed: int = 0

    def summary(self) -> str:
        return (f"uploaded={self.uploaded} local_only={self.completed_local} "
                f"failed={self.failed}")


def upload_pending(cfg: Config, conn, *, limit: int | None = None,
                   force: bool = False) -> UploadSummary:
    from .upload_r2 import R2Uploader
    from .upload_dropbox import DropboxUploader

    r2 = R2Uploader(cfg)
    dbx = DropboxUploader(cfg)
    res = UploadSummary()

    rows = db.get_by_status(conn, [Status.PARSED, Status.DOWNLOADED])
    if limit:
        rows = rows[:limit]

    for row in rows:
        blob_id = row["blob_id"]
        p = _artifact_paths(cfg, row)
        try:
            if not r2.enabled and not dbx.enabled:
                db.set_status(conn, blob_id, Status.COMPLETE)
                res.completed_local += 1
                continue

            fields: dict = {}
            # (local_path, r2_kind, name, db_col)
            artifacts = [(p["pdf_local"], "raw_pdfs", p["pdf_name"], "r2_pdf_key")]
            if row["markdown_filename"]:
                artifacts.append((p["md_local"], "markdown", p["md_name"], "r2_markdown_key"))
            if row["metadata_filename"]:
                artifacts.append((p["meta_local"], "metadata", p["meta_name"], "r2_metadata_key"))

            if r2.enabled:
                for local, kind, name, col in artifacts:
                    if local and Path(local).exists():
                        key = r2.key(kind, p["date_str"], name)
                        r2.upload_file(Path(local), key, force=force)
                        fields[col] = key
            if dbx.enabled and p["pdf_local"] and Path(p["pdf_local"]).exists():
                dpath = dbx.path("raw_pdfs", p["date_str"], p["pdf_name"])
                got = dbx.upload_file(Path(p["pdf_local"]), dpath, force=force)
                if got:
                    fields["dropbox_pdf_path"] = got
                if dbx.enabled:  # also mirror md/metadata (fail-soft)
                    for local, kind, name, _col in artifacts[1:]:
                        if local and Path(local).exists():
                            dbx.upload_file(Path(local), dbx.path(kind, p["date_str"], name),
                                            force=force)

            fields["uploaded_at"] = utc_now().isoformat()
            fields["status"] = Status.COMPLETE.value
            db.update_fields(conn, blob_id, **fields)
            res.uploaded += 1
        except Exception as e:  # noqa: BLE001
            res.failed += 1
            db.set_status(conn, blob_id, Status.FAILED, error_message=str(e)[:500])
            log.error("upload failed for %s: %s", blob_id, e)

    log.info("upload pass done: %s", res.summary())
    return res


# ---------------------------------------------------------------------------
# RESEARCH VAULT (downstream dashboard hand-off)
# ---------------------------------------------------------------------------
@dataclass
class VaultSummary:
    published: int = 0
    skipped: int = 0

    def summary(self) -> str:
        return f"published={self.published} skipped={self.skipped}"


def _vault_paper_view(cfg: Config, row) -> dict:
    """A publisher-friendly dict for a DB row: all row columns + the resolved
    local raw-PDF path (so VaultPublisher reads local bytes before falling back
    to the main-bucket copy). breadcrumb/tags/tickers are not persisted on the
    row, so they default empty — sidecar_for tolerates their absence.
    """
    p = _artifact_paths(cfg, row)
    view = {k: row[k] for k in row.keys()}
    view["local_pdf_path"] = (
        str(p["pdf_local"]) if p["pdf_local"] and Path(p["pdf_local"]).exists() else None
    )
    return view


def publish_vault_pending(
    cfg: Config, conn, *, limit: int | None = None, force: bool = False
) -> VaultSummary:
    """Publish COMPLETE-but-not-yet-vaulted papers to the Research Vault bucket.

    Resumable: each success is recorded (``vault_key`` + ``vaulted_at``) so a
    re-run only picks up the remainder. A disabled/misconfigured vault is a clean
    no-op. A single paper failing never aborts the batch (VaultPublisher swallows
    per-paper errors and returns None).
    """
    from .publish_vault import VaultPublisher

    res = VaultSummary()
    pub = VaultPublisher(cfg)
    if not pub.enabled:
        log.debug("vault publisher disabled; skipping publish_vault_pending")
        return res

    rows = db.get_vault_pending(conn, limit=limit)
    for row in rows:
        view = _vault_paper_view(cfg, row)
        # A pending paper that ALREADY carries a vault_key is a metadata re-heal
        # (a self-healed summary/title with vaulted_at nulled): rewrite the sidecar
        # JSON only — the PDF is already in the bucket and its bytes may be gone.
        if row["vault_key"]:
            vid = pub.republish_sidecar(view)
        else:
            vid = pub.publish(view, force=force)
        if vid:
            db.mark_vaulted(conn, row["blob_id"], vid, utc_now().isoformat())
            res.published += 1
        else:
            res.skipped += 1

    log.info("vault pass done: %s", res.summary())
    return res


# ---------------------------------------------------------------------------
# MANIFEST
# ---------------------------------------------------------------------------
def _manifest_entry(cfg: Config, row) -> ManifestEntry:
    p = _artifact_paths(cfg, row)
    return ManifestEntry(
        paper_id=row["id"],
        title=row["title"],
        institution=row["institution"],
        article_url=row["article_url"],
        blob_url=row["blob_url"],
        blob_id=row["blob_id"],
        published_at=row["published_at"],
        marketdesk_age_text=row["marketdesk_age_text"],
        marketdesk_summary=row["marketdesk_summary"],
        local_priority_score=row["local_priority_score"],
        sha256=row["sha256"],
        page_count=row["page_count"],
        parser=row["parser"],
        local_pdf_path=str(p["pdf_local"]) if p["pdf_local"] else None,
        local_markdown_path=str(p["md_local"]) if row["markdown_filename"] else None,
        r2_pdf_key=row["r2_pdf_key"],
        r2_markdown_key=row["r2_markdown_key"],
        r2_metadata_key=row["r2_metadata_key"],
        dropbox_pdf_path=row["dropbox_pdf_path"],
        status=row["status"],
    )


def write_manifest(cfg: Config, conn, date_str: str, *, upload: bool = True) -> Path:
    """Write data/manifests/YYYY-MM-DD.jsonl for all processed papers of that date."""
    rows = [
        r for r in db.get_for_manifest_date(conn, date_str)
        if r["status"] in {
            Status.COMPLETE.value, Status.UPLOADED.value,
            Status.PARSED.value, Status.DOWNLOADED.value,
        }
    ]
    out = Path(cfg.manifest_dir) / f"{date_str}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            entry = _manifest_entry(cfg, row)
            fh.write(json.dumps(entry.model_dump(), ensure_ascii=False) + "\n")
    log.info("manifest %s: %d papers -> %s", date_str, len(rows), out)

    if upload:
        _upload_manifest(cfg, out, date_str)
    return out


def _upload_manifest(cfg: Config, path: Path, date_str: str) -> None:
    try:
        from .upload_r2 import R2Uploader
        r2 = R2Uploader(cfg)
        if r2.enabled:
            r2.upload_file(path, r2.key("manifests", date_str, path.name), force=True)
    except Exception as e:  # noqa: BLE001
        log.warning("manifest R2 upload failed: %s", e)
    try:
        from .upload_dropbox import DropboxUploader
        dbx = DropboxUploader(cfg)
        if dbx.enabled:
            dbx.upload_file(path, dbx.path("manifests", date_str, path.name), force=True)
    except Exception as e:  # noqa: BLE001
        log.warning("manifest Dropbox upload failed: %s", e)


# ---------------------------------------------------------------------------
# FULL RUN
# ---------------------------------------------------------------------------
@dataclass
class RunReport:
    discover: DiscoverResult | None = None
    download: DownloadResult | None = None
    parse: ParseSummary | None = None
    upload: UploadSummary | None = None
    vault: "VaultSummary | None" = None
    manifests: list[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = []
        if self.discover:
            parts.append(f"discover[{self.discover.summary()}]")
        if self.download:
            parts.append(f"download[{self.download.summary()}]")
        if self.parse:
            parts.append(f"parse[{self.parse.summary()}]")
        if self.upload:
            parts.append(f"upload[{self.upload.summary()}]")
        if self.vault:
            parts.append(f"vault[{self.vault.summary()}]")
        parts.append(f"manifests={len(self.manifests)}")
        return " ".join(parts)


def run(
    cfg: Config,
    *,
    limit: int | None = None,
    since_hours: int | None = None,
    backfill: bool = False,
    do_parse: bool = True,
    do_upload: bool = True,
    do_manifest: bool = True,
) -> RunReport:
    """discover -> download -> parse -> upload -> manifest, in one shot."""
    cfg.ensure_dirs()
    conn = db.connect(cfg.database_url)
    db.init_db(conn)
    report = RunReport()

    # online stages (need the browser)
    with BrowserSession(cfg) as sess:
        if not sess.is_authenticated():
            raise RuntimeError(
                "Not authenticated. Run `marketdesk auth` and log in first."
            )
        client = MarketDeskClient(sess.context, cfg)
        report.discover = discover(
            cfg, conn, client, limit=limit, since_hours=since_hours, backfill=backfill,
        )
        report.download = download_pending(cfg, conn, client, limit=limit)

    # offline stages
    if do_parse and cfg.parser_backend != "none":
        report.parse = parse_pending(cfg, conn)
    if do_upload:
        report.upload = upload_pending(cfg, conn)

    # research-vault hand-off (after upload; opt-in via VAULT_ENABLED)
    if cfg.vault_enabled:
        report.vault = publish_vault_pending(cfg, conn)

    if do_manifest:
        dates = _dates_touched(conn)
        for d in dates:
            report.manifests.append(str(write_manifest(cfg, conn, d)))

    db.set_meta(conn, "last_successful_run", utc_now().isoformat())
    conn.close()
    log.info("run complete: %s", report.summary())
    return report


def _dates_touched(conn) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT substr(published_at,1,10) d FROM papers "
        "WHERE status IN (?,?,?,?) AND published_at IS NOT NULL ORDER BY d DESC",
        (Status.COMPLETE.value, Status.UPLOADED.value, Status.PARSED.value,
         Status.DOWNLOADED.value),
    ).fetchall()
    return [r["d"] for r in rows if r["d"]]
