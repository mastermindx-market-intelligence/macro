"""Cloudflare R2 uploader (S3-compatible via boto3).

Primary remote storage layer. boto3 is lazy-imported inside ``__init__`` so
importing this module succeeds with only stdlib + pydantic installed.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .config import Config
from .utils import get_logger

if TYPE_CHECKING:
    import boto3 as _boto3  # noqa: F401 — type-checking only

_CONTENT_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
}


class R2Uploader:
    """Upload local files to Cloudflare R2 using the S3-compatible API."""

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._log = get_logger("upload_r2")
        self._client: object | None = None

        if cfg.r2_enabled and self.enabled:
            import boto3  # lazy import — optional dep

            self._client = boto3.client(
                "s3",
                endpoint_url=f"https://{cfg.r2_account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=cfg.r2_access_key_id,
                aws_secret_access_key=cfg.r2_secret_access_key,
                region_name="auto",
            )

    @property
    def enabled(self) -> bool:
        """True only when all four R2 credentials are configured."""
        cfg = self._cfg
        return bool(
            cfg.r2_enabled
            and cfg.r2_account_id
            and cfg.r2_access_key_id
            and cfg.r2_secret_access_key
            and cfg.r2_bucket
        )

    def key(self, kind: str, date_str: str, filename: str) -> str:
        """Build the R2 object key for *kind* + *date_str* + *filename*.

        Special case: ``kind == 'manifests'`` omits the date segment because
        the filename already encodes the date (``YYYY-MM-DD.jsonl``).
        """
        prefix = self._cfg.r2_prefix
        if kind == "manifests":
            return f"{prefix}/manifests/{filename}"
        return f"{prefix}/{kind}/{date_str}/{filename}"

    def exists(self, key: str) -> bool:
        """Return True if *key* already exists in the bucket, False otherwise.

        Uses ``head_object``; treats 404 and any error as False (best-effort).
        """
        if not self.enabled or self._client is None:
            return False
        try:
            import botocore.exceptions  # bundled with boto3

            self._client.head_object(Bucket=self._cfg.r2_bucket, Key=key)  # type: ignore[attr-defined]
            return True
        except Exception as exc:
            # botocore raises ClientError with code '404' for missing keys
            try:
                code = exc.response["Error"]["Code"]  # type: ignore[attr-defined]
                if code in ("404", "NoSuchKey"):
                    return False
            except Exception:
                pass
            self._log.debug("exists(%s) check failed: %s", key, exc)
            return False

    def upload_file(
        self,
        local_path: Path,
        key: str,
        *,
        content_type: str | None = None,
        force: bool = False,
    ) -> str:
        """Upload *local_path* to R2 at *key*.

        Idempotent: if the key already exists and *force* is False, skips the
        upload and returns *key* immediately. Guesses ``ContentType`` from the
        file suffix when *content_type* is not provided. Raises on hard failure.
        """
        if not self.enabled or self._client is None:
            raise RuntimeError("R2Uploader is not enabled / client not initialised")

        if not force and self.exists(key):
            self._log.debug("skip upload (already exists): %s", key)
            return key

        ct = content_type or _CONTENT_TYPES.get(Path(local_path).suffix.lower(), "application/octet-stream")

        self._log.info("uploading %s -> r2://%s/%s", local_path, self._cfg.r2_bucket, key)
        with open(local_path, "rb") as fh:
            self._client.put_object(  # type: ignore[attr-defined]
                Bucket=self._cfg.r2_bucket,
                Key=key,
                Body=fh,
                ContentType=ct,
            )
        self._log.debug("uploaded OK: %s", key)
        return key
