"""VPS premarket owner for the AM Edition overlay.

Lane B of MO-A3 A-MOR-2b
(DEC:MARKET-ONTOLOGY-MOR2B-PREMARKET-OWNER-AND-PLACEMENT-2026-09-24,
research/market_intelligence_productization/MARKET_ONTOLOGY_F01_MOR2B_BUILD_PACKET_2026-09-24.md
§3 B1–B6). Run by ``app/deploy/macro-am-edition.timer`` inside the ET premarket
window; its sole writers are ``public_dir/am_edition.json`` (registered asset,
NOT a ``/live/*`` file) and ``public_dir/am_edition.html`` (anonymous-readable,
served with ``Cache-Control: no-store`` and ``X-Robots-Tag: noindex, noarchive``).
Receipt: ``state_dir/last_run.json`` (NOT web-addressable).

Decision (in order; never raises):

(a) overlay exists AND bake is newer than the overlay  -> ``expire``: remove
    BOTH overlay files (json + html). The freshly-baked copy under
    ``site/am_edition.json`` is the source of truth from now on.

(b) phase == ``preopen`` on a NYSE session date         -> ``build``: render
    ``build_payload(..., live_dir=live_dir)`` into ``public_dir/am_edition.json``
    + ``public_dir/am_edition.html``. The json bytes go through
    ``lib.pages.write_page`` so they carry the same ``data-dbase`` shim the
    nightly ``site/am_edition.json`` does. Atomic write: temp file in the live
    store + ``os.replace`` (the live plane's idiom — see
    ``scripts/vps_live_orchestrator.atomic_publish`` and every sibling served-
    artifact writer). The two served files are chmod ``0o644`` so Caddy (user
    ``caddy``) can read them under the live plane's invariant
    (``scripts/vps_live_orchestrator.run``: ``mode = 0o644`` for everything
    under ``public_dir``); the receipt is chmod ``0o600`` because it lives
    under ``state_dir`` and is not web-addressable.

(c) otherwise                                          -> ``skip``: nothing to
    do — the nightly ``daily.yml`` / ``render.yml`` owns ``site/am_edition.*``
    outside the premarket window, and weekends / NYSE holidays never enter
    ``preopen`` regardless of the wall clock.

The lane reads only files already on the box (``site/``, ``data/``, the live
``quotes.json`` snapshot, the existing ``market_packet`` ladder) and writes
only under the live store. It does NOT touch ``data/``, does NOT spawn a
workflow, and does NOT run git. Any exception degrades to a receipt with
``decision=error``; ``main()`` returns 1 ONLY when ``public_dir`` itself is
un-writable (the one exit-1 case B1 names — every other failure stays exit 0
so the timer never surfaces a hard fail to the operator's mailbox).
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

# Served-artifact mode lives at 0o644 (live plane's invariant — see
# scripts/vps_live_orchestrator.run, `mode = 0o644` when the target is under
# public_dir). The receipt lives under state_dir and is NOT web-addressable,
# so it gets the same 0o600 default a sibling lane uses for non-served bytes
# (scripts/close_pass_publish.py, scripts/entry_radar_live.py).
_SERVED_MODE = 0o644
_RECEIPT_MODE = 0o600


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


def _atomic_write_bytes(target: Path, payload: bytes, *, mode: int = _SERVED_MODE) -> None:
    """Live-plane idiom: temp file in the same directory + os.replace.

    ``mode`` defaults to 0o644 so a served artifact under ``public_dir`` is
    readable by Caddy (user ``caddy``) without a chown dance — the explicit
    invariant scripts/vps_live_orchestrator.run enforces. Pass ``mode=0o600``
    for non-served artifacts (the receipt under ``state_dir``).

    Same-directory + replace is atomic on POSIX (rename(2) is atomic within a
    filesystem); cross-directory moves are NOT. Keeping the temp file in the
    live store guarantees the swap never produces a partial file Caddy could
    serve.
    """
    parent = target.parent
    if not parent.exists():
        # `/var/lib/macro-live/public` absent on a host without the live plane.
        # Match the sibling lane's "no live store -> no served copy" pattern
        # (scripts/entry_radar_live.py:266-270): never silently create the root.
        if parent == PUBLIC_DIR:
            log.warning(
                "am_edition_live: %s is absent — no VPS live plane on this host",
                parent,
            )
            raise FileNotFoundError(f"public_dir_missing: {parent}")
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.warning(
                "am_edition_live: cannot create %s (%s)", parent, exc
            )
            raise
    fd, tmp_path = tempfile.mkstemp(prefix=target.name + ".", dir=str(parent))
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
            # fchmod AFTER write+fsync so an external umask cannot strip the
            # read bit the live plane's invariant demands for served artifacts
            # (scripts/vps_live_orchestrator.run:246-252 and the sibling lanes'
            # scripts/{entry_radar,prophet,cn}_live_evaluator.py/close_pass_publish.py).
            os.fchmod(fh.fileno(), mode)
        os.replace(tmp_path, target)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:  # noqa: BLE001
                pass


def _atomic_write_text(target: Path, text: str, *, mode: int = _SERVED_MODE) -> None:
    _atomic_write_bytes(target, text.encode("utf-8"), mode=mode)


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


def _norm_iso_clock(value: str) -> str:
    """Normalize an ISO8601 stamp to a comparable string. Accepts naive and
    ``Z``-suffixed UTC strings and stamps a UTC ``+00:00`` suffix so the
    string compare is total-ordered and DST/Z-naive inputs cannot mis-order.
    The producer's own ``_norm_clock`` is the author-equivalent; this fallback
    exists only so the live lane never crashes on an unfamiliar stamp."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


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
    ``decision=error`` and an ``error`` key carrying the message string.

    The receipt carries exactly the six spec keys on every success path
    (``decision``, ``generated_at``, ``phase``, ``bake_generated_at``,
    ``overlay_generated_at``, ``block_states``). Error paths keep the SAME
    shape — they add an ``error`` key whose value is the message — so a
    downstream consumer that pins the shape never trips on a degraded run.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if root is None:
        root = Path(os.getcwd())

    site = root / "site"
    data_dir = root / "data"
    live_dir = _live_dir(root)

    receipt: dict = {
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
        receipt["decision"] = "error"
        receipt["error"] = f"public_dir_unwritable: {exc}"
        return receipt

    # State-dir is the non-fatal sibling: a degraded path means we cannot
    # write the receipt, but the lane's job (publishing the overlay) still
    # succeeds. `_write_receipt` does its own best-effort mkdir so we are not
    # required to create the parent here; the early ensure keeps the path
    # visible at the right lineage in `journalctl`.
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "am_edition_live: state_dir %s unavailable (%s) — receipt will be skipped",
            STATE_DIR,
            exc,
        )

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
        receipt["decision"] = "error"
        receipt["error"] = f"import_failed: {exc}"
        return receipt

    phase = _session_phase(now)
    receipt["phase"] = phase

    bake_path = site / BAKE_REL
    overlay_json_path = PUBLIC_DIR / OVERLAY_JSON
    overlay_html_path = PUBLIC_DIR / OVERLAY_HTML

    bake_iso = _read_iso_generated(bake_path) if bake_path.exists() else None
    overlay_iso = (
        _read_iso_generated(overlay_json_path) if overlay_json_path.exists() else None
    )
    receipt["bake_generated_at"] = bake_iso
    receipt["overlay_generated_at"] = overlay_iso

    # Decision (a): overlay present AND bake newer — freshest-wins expiry.
    # The bake is the canonical site copy; the overlay is the optional VPS
    # supersession. A newer bake means the overlay is stale and must come
    # down so the visitor stops reading bytes the nightly has superseded.
    if overlay_iso is not None and bake_iso is not None:
        bake_n = _norm_iso_clock(bake_iso)
        overlay_n = _norm_iso_clock(overlay_iso)
        if bake_n > overlay_n:
            for p in (overlay_json_path, overlay_html_path):
                try:
                    if p.exists():
                        p.unlink()
                except Exception as exc:  # noqa: BLE001
                    log.warning("am_edition_live: could not remove %s (%s)", p, exc)
            receipt["decision"] = "expire"
            return receipt

    # Decision (b): preopen on a NYSE session date — build the overlay.
    # `_session_phase` returns `weekend`/`holiday` BEFORE `preopen` (see
    # scripts/build_am_edition._session_phase), so the redundant
    # `nyse_calendar.is_session` check it was guarding against is no longer
    # needed here.
    if phase == "preopen":
        try:
            payload = build_payload(site, data_dir, now=now, live_dir=live_dir)
        except Exception as exc:  # noqa: BLE001
            log.error("am_edition_live: build_payload raised (%s)", exc)
            receipt["decision"] = "error"
            receipt["error"] = f"build_payload_failed: {exc}"
            return receipt

        # Receipt: derive the block-state summary BEFORE writing — if the JSON
        # write below partially fails the receipt still records what was
        # attempted, so the next tick can decide build vs skip honestly.
        receipt["block_states"] = _block_states_from_payload(payload)

        try:
            json_bytes = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n").encode("utf-8")
            _atomic_write_bytes(overlay_json_path, json_bytes, mode=_SERVED_MODE)
        except Exception as exc:  # noqa: BLE001
            log.error("am_edition_live: json write failed (%s)", exc)
            receipt["decision"] = "error"
            receipt["error"] = f"json_write_failed: {exc}"
            return receipt

        try:
            html = render_html(payload)
            if not html:
                # render_html returns "" both for jinja2-missing and template-
                # missing. The page-builder already warns on each cause; here
                # we record the json-only build and continue.
                log.warning("am_edition_live: render_html returned empty; json overlay only")
            else:
                _atomic_write_text(overlay_html_path, html, mode=_SERVED_MODE)
        except Exception as exc:  # noqa: BLE001
            log.error("am_edition_live: html render/write failed (%s)", exc)
            receipt["decision"] = "error"
            receipt["error"] = f"html_write_failed: {exc}"
            return receipt

        receipt["decision"] = "build"
        receipt["overlay_generated_at"] = receipt["generated_at"]
        return receipt

    # Decision (c): skip — phase is weekend / holiday / closed / preopen-off-session,
    # OR the overlay is already current.
    receipt["decision"] = "skip"
    return receipt


def _write_receipt(state_dir: Path, receipt: dict) -> None:
    """Receipt write is best-effort and tolerant of a degraded state dir. The
    receipt lives under state_dir (NOT web-addressable) so it is chmod 0o600 —
    the same mode every sibling lane uses for non-served bytes
    (scripts/close_pass_publish.py, scripts/entry_radar_live.py)."""
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_bytes(
            state_dir / "last_run.json",
            (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=False) + "\n").encode("utf-8"),
            mode=_RECEIPT_MODE,
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
        receipt = {
            "decision": "error",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "phase": None,
            "bake_generated_at": None,
            "overlay_generated_at": None,
            "block_states": {},
            "error": f"uncaught: {exc}",
        }

    _write_receipt(STATE_DIR, receipt)
    log.info(
        "am_edition_live: decision=%s phase=%s bake=%s overlay=%s",
        receipt.get("decision"),
        receipt.get("phase"),
        receipt.get("bake_generated_at"),
        receipt.get("overlay_generated_at"),
    )

    # B1: exit 0 unless the box is misconfigured. The spec's single exit-1
    # trigger is `public_dir_unwritable` — every other failure (state_dir
    # read-only, missing template, build_payload raised, json write partial)
    # degrades to `decision=error` but exits 0 so the timer never pages the
    # operator over a recoverable degradation.
    err = receipt.get("error") if isinstance(receipt.get("error"), str) else ""
    if (
        receipt.get("decision") == "error"
        and err.startswith("public_dir_unwritable:")
    ):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
