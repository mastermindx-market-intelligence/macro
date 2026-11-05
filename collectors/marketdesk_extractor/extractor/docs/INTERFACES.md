# Module interface contract (for delegated modules)

`pipeline.py` imports the three modules below by these EXACT signatures. Implement to match;
do not change names/args. All live in `src/marketdesk_extractor/`. Python 3.11, type-hinted,
match the house style of the existing modules (module docstring, `from __future__ import
annotations`, `get_logger`, small focused functions).

Shared imports available:
- `from .config import Config`  — has `.r2_*`, `.dropbox_*`, `.r2_prefix`, `.dropbox_prefix`,
  `.raw_pdf_dir`, `.markdown_dir`, `.metadata_dir`, `.manifest_dir`, `.parser_backend`.
- `from .schemas import ParseResult, Status`
- `from .utils import get_logger`

---

## `parse_pdf.py`  — PDF → Markdown abstraction (Marker or MinerU)

```python
class BaseParser:
    name: str
    def to_markdown(self, pdf_path: Path) -> tuple[str, dict]:
        """Return (markdown_text, extra) where extra may include {'page_count': int}."""

def get_parser(backend: str) -> BaseParser:
    """backend in {'marker','mineru','none'}. Lazy-import the heavy dep INSIDE the parser's
    to_markdown/__init__ so importing this module never requires marker/mineru installed.
    Unknown/'none' -> a NoopParser that returns ("", {'page_count': <cheap count or None>}).
    The cheap page count may be obtained by counting b'/Type' b'/Page' occurrences in the
    raw PDF bytes (best-effort; None if unsure)."""

def parse_pdf(pdf_path: Path, markdown_path: Path, metadata_path: Path, *,
              backend: str, base_metadata: dict) -> ParseResult:
    """1) parser = get_parser(backend); md, extra = parser.to_markdown(pdf_path).
    2) write md to markdown_path (mkdir parents) — only if md non-empty.
    3) build metadata dict = {**base_metadata, 'page_count': extra.get('page_count'),
       'parser': parser.name, 'parsing_status': 'PARSED', 'markdown_path': str(markdown_path)
       (or None if md empty), 'parsed_at': <utc iso>}; write JSON (indent=2) to metadata_path.
    4) return ParseResult(markdown_path=..., metadata_path=str(metadata_path),
       page_count=extra.get('page_count'), parser=parser.name, status=Status.PARSED).
    On ANY exception: still write a metadata JSON with parsing_status='FAILED' and the error,
    and return ParseResult(status=Status.FAILED, error=str(e), metadata_path=...).
    Never raise."""
```
Notes: heavy ML deps are optional extras (`pip install .[marker]` / `.[mineru]`). If the
backend's import fails, degrade to NoopParser behavior for that call (log a clear warning)
rather than crashing the run.

---

## `upload_r2.py`  — Cloudflare R2 (primary), S3-compatible via boto3

```python
class R2Uploader:
    def __init__(self, cfg: Config): ...
    @property
    def enabled(self) -> bool:
        """cfg.r2_enabled AND account_id/access_key/secret/bucket all non-empty."""
    def key(self, kind: str, date_str: str, filename: str) -> str:
        """kind in {'raw_pdfs','markdown','metadata'} -> f'{cfg.r2_prefix}/{kind}/{date_str}/{filename}'.
        kind == 'manifests' -> f'{cfg.r2_prefix}/manifests/{filename}' (filename already 'YYYY-MM-DD.jsonl')."""
    def exists(self, key: str) -> bool:
        """head_object; True if present, False on 404. Best-effort (False on error)."""
    def upload_file(self, local_path: Path, key: str, *, content_type: str | None = None,
                    force: bool = False) -> str:
        """Idempotent: if not force and exists(key): return key without re-upload.
        Else put_object/upload_file with ContentType (guess from suffix if None:
        .pdf->application/pdf, .md->text/markdown, .json->application/json,
        .jsonl->application/x-ndjson). Return the key. Raise on hard failure."""
```
boto3 client: `boto3.client('s3', endpoint_url=f'https://{cfg.r2_account_id}.r2.cloudflarestorage.com',
aws_access_key_id=cfg.r2_access_key_id, aws_secret_access_key=cfg.r2_secret_access_key,
region_name='auto')`. Lazy-import boto3 inside `__init__`.

---

## `upload_dropbox.py`  — Dropbox (optional secondary; FAIL-SOFT)

```python
class DropboxUploader:
    def __init__(self, cfg: Config): ...
    @property
    def enabled(self) -> bool:
        """cfg.dropbox_enabled AND cfg.dropbox_access_token non-empty."""
    def path(self, kind: str, date_str: str, filename: str) -> str:
        """kind in {'raw_pdfs','markdown','metadata'} -> f'{cfg.dropbox_prefix}/{kind}/{date_str}/{filename}'.
        kind == 'manifests' -> f'{cfg.dropbox_prefix}/manifests/{filename}'."""
    def upload_file(self, local_path: Path, dropbox_path: str, *, force: bool = False) -> str | None:
        """Fail-soft: on ANY error, log a warning and return None (R2 is primary, must not
        break the run). Use dropbox SDK files_upload with mode=overwrite when force else add.
        Lazy-import `dropbox` inside __init__. Return the dropbox_path on success, else None."""
```

---

## Tests (`tests/test_db.py`, `tests/test_dedupe.py`, `tests/test_manifest.py`, + more)

Use pytest + tmp_path. No network, no Playwright, no boto3 calls (monkeypatch/stub as needed).
Cover at least: DB init + `upsert_discovered` idempotency + status transitions; SHA-256 dedup
(`find_sha256_owner`), including that re-download of a duplicate marks `SKIPPED_SEEN`; manifest
JSONL generation shape; R2 key generation (`R2Uploader.key`) for all kinds; filename builder /
slugify; priority scoring for a couple of representative papers; `humanize_age`.
Import from `marketdesk_extractor.*`. Keep them fast and deterministic.
