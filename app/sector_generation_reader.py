"""Read adapter for the incumbent verified Sector generation facade.

Only deployment supplies the absolute private root. Each request captures the selected
pointer and verified member bytes once; the adapter never reopens paths or falls back
to the static site. Authorization remains in app.sector_generation's existing gates.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from app.sector_generation import SectorGeneration, SectorGenerationRequest
from lib.sector_generation_contract import (
    SECTOR_GENERATION_DOMAIN, SECTOR_GENERATION_MEMBERS, project_sector_bundle,
)
from scripts.vps_live_orchestrator import read_selected_generation


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SectorGenerationReader:
    """Stateless request adapter; no cache, poller, selection or writer effect."""

    def __init__(self, *, generations_root: Path,
                 clock: Callable[[], datetime] = _utc_now,
                 preview_rows: int = 3,
                 snapshot_reader: Callable = read_selected_generation):
        root = Path(generations_root)
        if not root.is_absolute():
            raise ValueError("Sector generation root must be explicit and absolute")
        if (isinstance(preview_rows, bool) or not isinstance(preview_rows, int)
                or not 0 <= preview_rows <= 100):
            raise ValueError("Invalid server-owned preview count")
        self._root = root
        self._clock = clock
        self._preview_rows = preview_rows
        self._snapshot_reader = snapshot_reader

    def read_selected_generation(self, request: SectorGenerationRequest) -> SectorGeneration:
        if request.audience not in ("preview", "entitled"):
            raise ValueError("Invalid Sector audience")
        snapshot = self._snapshot_reader(
            generations_root=self._root, domain=SECTOR_GENERATION_DOMAIN,
            members=SECTOR_GENERATION_MEMBERS,
        )
        # Observe the clock after capture: a concurrent publication may have
        # completed between request entry and the one pointer read.
        now = self._clock()
        projection = project_sector_bundle(
            member_bytes=snapshot.members,
            input_identity=snapshot.manifest.get("input_identity"),
            generation_id=snapshot.generation_id, published_at=snapshot.published_at,
            now=now, audience=request.audience, preview_rows=self._preview_rows,
        )
        receipt = projection["receipt"]
        return SectorGeneration(
            payload=projection, source_session=receipt["source_session"],
            published_at=receipt["published_at"], qualification=receipt["qualification"],
        )


def configure_sector_generation_reader(app, *, generations_root: str | None) -> bool:
    """Bind the existing reader from deployment config, with no store acquisition.

    Unset configuration leaves the mounted route unavailable. Invalid config
    clears the capability and raises; it never selects the checkout/static tree.
    """
    app.state.sector_generation_reader = None
    if generations_root is None:
        return False
    if (type(generations_root) is not str or not generations_root
            or generations_root != generations_root.strip()
            or len(generations_root) > 4096 or "\x00" in generations_root):
        raise ValueError("invalid_sector_generation_root")
    root = Path(generations_root)
    if not root.is_absolute() or root == Path("/") or ".." in root.parts:
        raise ValueError("invalid_sector_generation_root")
    app.state.sector_generation_reader = SectorGenerationReader(generations_root=root)
    return True
