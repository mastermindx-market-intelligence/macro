"""VPS premarket owner for the AM Edition overlay.

Lane B of MO-A3 A-MOR-2b (DEC:MARKET-ONTOLOGY-MOR2B-PREMARKET-OWNER-AND-PLACEMENT-2026-09-24).
Run by ``app/deploy/macro-am-edition.timer`` inside the ET premarket window;
its sole writers are ``public_dir/am_edition.json`` (registered asset, NOT a
``/live/*`` file) and ``public_dir/am_edition.html`` (anonymous-readable, served
with ``Cache-Control: no-store`` and ``X-Robots-Tag: noindex, noarchive``).
Receipt: ``state_dir/last_run.json`` (NOT web-addressable).

Decision (in order; never raises; exits 0 unless the box is misconfigured):

(a) overlay exists AND bake is newer than the overlay  -> ``expire``: remove
    BOTH overlay files (json + html). The freshly-baked copy under
    ``site/am_edition.json`` is the source of truth from now on.

(b) phase == ``preopen`` on a NYSE session date         -> ``build``: render
    ``build_payload(..., live_dir=live_dir)`` into ``public_dir/am_edition.json``
    + ``public_dir/am_edition.html``. Atomic write: temp file in the live store
    + ``os.replace`` (the live plane's idiom — see scripts.watch_release_publications).

(c) otherwise                                          -> ``skip``: nothing to
    do — the nightly ``daily.yml`` / ``render.yml`` owns ``site/am_edition.*``
    outside the premarket window, and weekends / NYSE holidays never enter
    ``preopen`` regardless of the wall clock.

The lane reads only files already on the box (``site/``, ``data/``, the live
``quotes.json`` snapshot, the existing ``market_packet`` ladder) and writes
only under the live store. It does NOT touch ``data/``, does NOT spawn a
workflow, and does NOT run git. The body of the decision is structured so that
any exception degrades to a receipt with ``decision=error`` and the script
returns 0 — the timer never surfaces a hard fail to the operator's mailbox.
A misconfigured box (no public_dir writable) is the one exit-1 case the spec
calls out, and only that one.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Path setup: `python -m scripts.am_edition_live` is the entry point, and the
# script lives at <repo_root>/scripts/. Parent on sys.path so build_am_edition
# and lib.config import cleanly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("am_edition_live")

# Three-rung live-dir ladder — copied verbatim from
# engine/neuralweb/market_packet.py:86-101 (MACRO_LIVE_DIR env → VPS path →
# site/live). The brain gateway / notify_turn_events read the same ladder; the
# premarket owner must, too, so the overlay reads the exact bytes the rest of
# the live plane is currently serving.
_LIVE_DIR_ENV = "MACRO_LIVE_DIR"
_VPS_LIVE_DIR = Path("/var/lib/macro-live/public/live")

# On-disk destinations for THIS lane. /var/lib/macro-live/public is the live
# store (Caddy's `root * /var/lib/macro-live/public`); the AM edition overlay
# writes here so the file is freshest-wins vs site/am_edition.json.
PUBLIC_DIR = Path("/var/lib/macro-live/public")
STATE_DIR = Path("/var/lib/macro-live/state/am_edition")
BAKE_REL = "am_edition.json"          # nightly / render lane writes this under site/
OVERLAY_JSON = "am_edition.json"      # writes under PUBLIC_DIR
OVERLAY_HTML = "am_edition.html"      # writes under PUBLIC_DIR


def _live_dir(root: Path) -> Path:
    """Resolve the live-artifact directory (mirror of market_packet.py:90-106).

    (a) ``$MACRO_LIVE_DIR`` when set (operator override),
    (b) ``/var/lib/macro-live/public/live`` when that path exists,
    (c) ``<root>/site/live`` (dev / tests).
    """
    try:
        env = os.environ.get(_LIVE_DIR_ENV)
        if env and env.strip():
            return Path(env.strip())
        if _VPS_LIVE_DIR.is_dir():
            return _VPS_LIVE_DIR
    except Exception:  # noqa: BLE001
        pass
    return root / "site" / "live"


def _atomic_write_bytes(target: Path, payload: bytes) -> None:
    """Live-plane idiom: temp file in the same directory + os.replace.

    Same-directory + replace is atomic on POSIX (rename(2) is atomic within a
    filesystem); cross-directory moves are NOT. Keeping the temp file in the
    live store guarantees the swap never produces a partial file Caddy could
    serve."""
    target.parent.mkdir(parents=True, exist_ok=True)
    # delete=False + NamedTemporaryFile then close() so we can os.replace a
    # fully-flushed file; the .replace below is the atomic rename.
    fd, tmp_path = tempfile.mkstemp(prefix=target.name + ".", dir=str(target.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:  # noqa: BLE001
                # Some filesystems (e.g. tmpfs on certain kernels) reject
                # fsync; the os.replace below still publishes atomically.
                pass
        os.replace(tmp_path, target)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:  # noqa: BLE001
                pass


def _atomic_write_text(target: Path, text: str) -> None:
    _atomic_write_bytes(target, text.encode("utf-8"))


def _read_iso_generated(path: Path) -> str | None:
    """Best-effort read of `generated_at` from a baked AM Edition JSON. Returns
    the ISO string when present and parseable, else None."""
    try:
        d = json.loads(path.read_bytes())
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(d, dict):
        return None
    g = d.get("generated_at")
    return g if isinstance(g, str) else None


def _is_session_date(now_utc: datetime) -> bool:
    """NYSE session day? Weekends + full-day holidays both answer False
    (lib.nyse_calendar.is_session)."""
    try:
        from lib import nyse_calendar  # noqa: WPS433 — local import keeps the module's import-time cheap.
        from zoneinfo import ZoneInfo
        return nyse_calendar.is_session(now_utc.astimezone(ZoneInfo("America/New_York")).date())
    except Exception:  # noqa: BLE001
        return False


def _block_states_from_payload(payload: dict) -> dict:
    """Flatten the rendered payload's block keys → their typed states. The receipt
    only carries the LEGACY six-typed-state surface (the receipt is operator
    telemetry, not the rendered page) so a build error or stale state is visible
    at a glance."""
    out: dict = {}
    for b in payload.get("blocks") or []:
        if not isinstance(b, dict):
            continue
        key = b.get("key")
        state = b.get("state")
        if isinstance(key, str) and isinstance(state, str):
            out[key] = state
    return out


def run(now: datetime | None = None, root: Path | None = None) -> dict:
    """Run one premarket pass. Returns the receipt dict that gets written to
    ``state_dir/last_run.json``. NEVER raises (the timer must never surface a
    hard fail); on any internal error the receipt is shaped with
    ``decision=error`` and an ``error`` key carrying the message string."""
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if root is None:
        root = Path(os.getcwd())

    site = root / "site"
    data_dir = root / "data"
    live_dir = _live_dir(root)

    receipt_base: dict = {
        "decision": "skip",
        "generated_at": now.isoformat(),
        "phase": None,
        "bake_generated_at": None,
        "overlay_generated_at": None,
        "block_states": {},
    }

    # Public-dir misconfig is the ONE exit-1 condition the spec names; check it
    # first so a degraded box never silently writes the receipt into a path
    # nobody will read.
    try:
        PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        log.error("am_edition_live: cannot ensure %s (%s)", PUBLIC_DIR, exc)
        return {"decision": "error", "error": f"public_dir_unwritable: {exc}"}
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        log.error("am_edition_live: cannot ensure %s (%s)", STATE_DIR, exc)
        return {"decision": "error", "error": f"state_dir_unwritable: {exc}"}

    # Imports live AFTER the dir check so a missing lib.config / build_am_edition
    # surfaces as a structured error receipt instead of an exit-1.
    try:
        from scripts.build_am_edition import (  # noqa: WPS433
            _session_phase,
            build_payload,
            render_html,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("am_edition_live: cannot import build_am_edition (%s)", exc)
        return {"decision": "error", "error": f"import_failed: {exc}"}

    phase = _session_phase(now)
    receipt_base["phase"] = phase

    bake_path = site / BAKE_REL
    overlay_json_path = PUBLIC_DIR / OVERLAY_JSON
    overlay_html_path = PUBLIC_DIR / OVERLAY_HTML

    bake_iso = _read_iso_generated(bake_path) if bake_path.exists() else None
    overlay_iso = (
        _read_iso_generated(overlay_json_path) if overlay_json_path.exists() else None
    )
    receipt_base["bake_generated_at"] = bake_iso
    receipt_base["overlay_generated_at"] = overlay_iso

    # Decision (a): overlay present AND bake newer — freshest-wins expiry.
    # The bake is the canonical site copy; the overlay is the optional VPS
    # supersession. A newer bake means the overlay is stale and must come
    # down so the visitor stops reading bytes the nightly has superseded.
    if overlay_iso is not None and bake_iso is not None and bake_iso > overlay_iso:
        for p in (overlay_json_path, overlay_html_path):
            try:
                if p.exists():
                    p.unlink()
            except Exception as exc:  # noqa: BLE001
                log.warning("am_edition_live: could not remove %s (%s)", p, exc)
        receipt_base["decision"] = "expire"
        return receipt_base

    # Decision (b): preopen on an NYSE session date — build the overlay.
    if phase == "preopen" and _is_session_date(now):
        try:
            payload = build_payload(site, data_dir, now=now, live_dir=live_dir)
        except Exception as exc:  # noqa: BLE001
            log.error("am_edition_live: build_payload raised (%s)", exc)
            receipt_base["decision"] = "error"
            receipt_base["error"] = f"build_payload_failed: {exc}"
            return receipt_base

        # Receipt: derive the block-state summary BEFORE writing — if the JSON
        # write below partially fails the receipt still records what was
        # attempted, so the next tick can decide build vs skip honestly.
        receipt_base["block_states"] = _block_states_from_payload(payload)

        try:
            json_bytes = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n").encode("utf-8")
            _atomic_write_bytes(overlay_json_path, json_bytes)
        except Exception as exc:  # noqa: BLE001
            log.error("am_edition_live: json write failed (%s)", exc)
            receipt_base["decision"] = "error"
            receipt_base["error"] = f"json_write_failed: {exc}"
            return receipt_base

        try:
            html = render_html(payload)
            if not html:
                # render_html returns "" both for jinja2-missing and template-
                # missing. The page-builder already warns on each cause; here
                # we record the json-only build and continue.
                log.warning("am_edition_live: render_html returned empty; json overlay only")
            else:
                _atomic_write_text(overlay_html_path, html)
        except Exception as exc:  # noqa: BLE001
            log.error("am_edition_live: html render/write failed (%s)", exc)
            receipt_base["decision"] = "error"
            receipt_base["error"] = f"html_write_failed: {exc}"
            return receipt_base

        receipt_base["decision"] = "build"
        receipt_base["overlay_generated_at"] = receipt_base["generated_at"]
        return receipt_base

    # Decision (c): skip — phase is weekend / holiday / closed / preopen-off-session,
    # OR the overlay is already current.
    receipt_base["decision"] = "skip"
    return receipt_base


def _write_receipt(state_dir: Path, receipt: dict) -> None:
    """Receipt write is best-effort and tolerant of a degraded state dir."""
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_bytes(
            state_dir / "last_run.json",
            (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=False) + "\n").encode("utf-8"),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("am_edition_live: could not write receipt (%s)", exc)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else []
    # No CLI surface today; the timer invokes `python -m scripts.am_edition_live`
    # with no args. Future flags (--once, --now ISO) would land here.
    try:
        receipt = run()
    except Exception as exc:  # noqa: BLE001 — last-ditch: never raise out of the unit
        log.error("am_edition_live: uncaught (%s)", exc)
        receipt = {"decision": "error", "error": f"uncaught: {exc}"}

    _write_receipt(STATE_DIR, receipt)
    log.info(
        "am_edition_live: decision=%s phase=%s bake=%s overlay=%s",
        receipt.get("decision"),
        receipt.get("phase"),
        receipt.get("bake_generated_at"),
        receipt.get("overlay_generated_at"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
