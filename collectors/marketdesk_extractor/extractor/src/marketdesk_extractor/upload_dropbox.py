"""Dropbox secondary upload — fail-soft, never breaks the run.

R2 is the primary store; this module mirrors files to Dropbox as an optional
secondary. Any failure is logged as a warning and returns None so the pipeline
can continue uninterrupted. The ``dropbox`` SDK is lazy-imported inside
``__init__`` so importing this module never requires the SDK to be installed.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .config import Config
from .utils import get_logger

if TYPE_CHECKING:
    pass


class DropboxUploader:
    """Upload files to Dropbox as a fail-soft secondary store."""

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._log: logging.Logger = get_logger("upload_dropbox")
        self._dbx: object | None = None  # lazy-initialised on first upload

        # Attempt to initialise the SDK client now so .enabled is accurate.
        if cfg.dropbox_enabled and cfg.dropbox_access_token:
            try:
                import dropbox  # noqa: PLC0415  (lazy import)
                self._dbx = dropbox.Dropbox(cfg.dropbox_access_token)
            except Exception as exc:  # ImportError or auth bootstrap failure
                self._log.warning(
                    "Dropbox SDK unavailable or token invalid; uploads will no-op. "
                    "Reason: %s",
                    exc,
                )
                self._dbx = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        """True only when Dropbox is configured AND the SDK client was created."""
        return (
            self._cfg.dropbox_enabled
            and bool(self._cfg.dropbox_access_token)
            and self._dbx is not None
        )

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def path(self, kind: str, date_str: str, filename: str) -> str:
        """Build the Dropbox destination path.

        Parameters
        ----------
        kind:
            One of ``'raw_pdfs'``, ``'markdown'``, ``'metadata'``, or
            ``'manifests'``.
        date_str:
            ISO date string (``'YYYY-MM-DD'``).  Ignored for ``'manifests'``.
        filename:
            The file's basename (e.g. ``'report.pdf'``).

        Returns
        -------
        str
            Absolute Dropbox path (starts with ``/``).
        """
        prefix = self._cfg.dropbox_prefix  # already rstripped of '/'
        if kind == "manifests":
            return f"{prefix}/manifests/{filename}"
        return f"{prefix}/{kind}/{date_str}/{filename}"

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload_file(
        self,
        local_path: Path,
        dropbox_path: str,
        *,
        force: bool = False,
    ) -> str | None:
        """Upload *local_path* to *dropbox_path* in Dropbox.

        Fail-soft: any error (SDK missing, auth failure, network, I/O …) is
        logged as a warning and ``None`` is returned so the pipeline is never
        interrupted.

        Parameters
        ----------
        local_path:
            Path to the file on disk.
        dropbox_path:
            Absolute destination path inside the user's Dropbox.
        force:
            If ``True``, use ``WriteMode.overwrite``; otherwise ``WriteMode.add``
            (Dropbox will auto-rename on conflict rather than overwrite).

        Returns
        -------
        str | None
            *dropbox_path* on success, ``None`` on any failure.
        """
        if not self.enabled:
            self._log.debug(
                "Dropbox upload skipped (disabled or SDK unavailable): %s",
                dropbox_path,
            )
            return None

        try:
            import dropbox  # noqa: PLC0415  (lazy import — already succeeded in __init__)
            import dropbox.files  # noqa: PLC0415

            mode = (
                dropbox.files.WriteMode.overwrite
                if force
                else dropbox.files.WriteMode.add
            )
            data = Path(local_path).read_bytes()
            self._dbx.files_upload(data, dropbox_path, mode=mode)  # type: ignore[union-attr]
            self._log.debug("Dropbox upload OK: %s -> %s", local_path, dropbox_path)
            return dropbox_path
        except Exception as exc:  # noqa: BLE001  (intentional broad catch)
            self._log.warning(
                "Dropbox upload FAILED (non-fatal) for %s -> %s: %s",
                local_path,
                dropbox_path,
                exc,
            )
            return None
