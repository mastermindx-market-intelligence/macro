"""Per-use capture verdict for selection-cohort internal capture (W-C).

Derives every verdict from fresh registry bytes via :func:`registry_snapshot`.
Shape mirrors the ``load_registry_snapshot`` contract planned on the rights kernel
carrier (#7870) so the body can later delegate without a second parser.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import logging
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

from engine.theme_graph import rights

log = logging.getLogger(__name__)

PURPOSE = "selection_cohort_internal_capture"
PHASES = frozenset({"capture_write", "pre_read", "read_use"})
_MARKETS = frozenset({"us_today", "cn_featured"})
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_GENERATION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}")

class UseRefusal(RuntimeError):
    """Registry snapshot could not be read; carries ``code`` for the refusal reason."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


def registry_snapshot(path: str | Path | None = None) -> tuple[str, dict[str, dict]]:
    """Read registry bytes fresh; return ``(revision, families)``.

    ``revision`` is ``rights_`` + the first 32 hex digits of SHA-256 over the raw bytes.
    Mirrors the ``load_registry_snapshot`` shape on the incumbent rights kernel (#7870).
    """
    p = Path(path) if path is not None else rights.registry_path()
    if not p.exists():
        raise UseRefusal("REGISTRY_MISSING", f"registry file absent: {p}")
    raw = p.read_bytes()
    revision = "rights_" + hashlib.sha256(raw).hexdigest()[:32]
    try:
        doc = yaml.safe_load(raw.decode("utf-8"))
    except Exception as exc:
        raise UseRefusal("REGISTRY_MALFORMED", "YAML parse failed") from exc
    if not isinstance(doc, Mapping):
        raise UseRefusal("REGISTRY_MALFORMED", "document is not a mapping")
    families_raw = doc.get("families")
    if families_raw is None or not isinstance(families_raw, Mapping):
        raise UseRefusal("REGISTRY_MALFORMED", "families missing or not a mapping")
    out: dict[str, dict] = {}
    for name, row in families_raw.items():
        if not isinstance(row, Mapping):
            raise UseRefusal("REGISTRY_MALFORMED", f"family row {name!r} is not a mapping")
        out[str(name)] = dict(row)
    return revision, out


def _evaluated_at(now: dt.datetime | None) -> str:
    if now is None:
        now = dt.datetime.now(dt.timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    else:
        now = now.astimezone(dt.timezone.utc)
    return now.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _base_verdict(
    request: Mapping[str, Any],
    *,
    registry_path_str: str,
    evaluated: str,
) -> dict[str, Any]:
    return {
        "verdict": "REFUSED",
        "reason_codes": [],
        "purpose": request.get("purpose"),
        "phase": request.get("phase"),
        "market": request.get("market"),
        "source_ref": request.get("source_ref"),
        "source_sha256": request.get("source_sha256"),
        "generation_id": request.get("generation_id"),
        "source_family": None,
        "rights_class": None,
        "auth_class": None,
        "registry_revision": None,
        "registry_path": registry_path_str,
        "evaluated_at": evaluated,
    }


def _invalid_request(request: object) -> bool:
    if not isinstance(request, Mapping):
        return True
    phase = request.get("phase")
    if phase not in PHASES:
        return True
    if request.get("market") not in _MARKETS:
        return True
    sha = request.get("source_sha256")
    if not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha):
        return True
    source_ref = request.get("source_ref")
    if not isinstance(source_ref, str) or not source_ref:
        return True
    if request.get("purpose") != PURPOSE:
        return True
    gen = request.get("generation_id")
    if not isinstance(gen, str) or not gen or not _GENERATION_RE.fullmatch(gen):
        return True
    return False


def _refused(
    request: Mapping[str, Any],
    codes: list[str],
    *,
    registry_path_str: str,
    evaluated: str,
    source_family: str | None = None,
    rights_class: str | None = None,
    auth_class: str | None = None,
    registry_revision: str | None = None,
) -> dict[str, Any]:
    out = _base_verdict(request, registry_path_str=registry_path_str, evaluated=evaluated)
    out["reason_codes"] = codes
    out["source_family"] = source_family
    out["rights_class"] = rights_class
    out["auth_class"] = auth_class
    out["registry_revision"] = registry_revision
    return out


def current_use_verdict(
    request: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Pure verdict from ``request`` and current registry bytes; never raises."""
    p = Path(path) if path is not None else rights.registry_path()
    registry_path_str = str(p)
    evaluated = _evaluated_at(now)

    if not isinstance(request, Mapping):
        return _refused(
            {},
            ["INVALID_USE_REQUEST"],
            registry_path_str=registry_path_str,
            evaluated=evaluated,
        )

    if _invalid_request(request):
        return _refused(
            request,
            ["INVALID_USE_REQUEST"],
            registry_path_str=registry_path_str,
            evaluated=evaluated,
        )

    source_ref = request["source_ref"]
    source_family = rights.family_for_source_ref(source_ref)
    if source_family is None:
        return _refused(
            request,
            ["SOURCE_FAMILY_UNRESOLVED"],
            registry_path_str=registry_path_str,
            evaluated=evaluated,
        )

    try:
        revision, families = registry_snapshot(p)
    except UseRefusal as exc:
        return _refused(
            request,
            [exc.code],
            registry_path_str=registry_path_str,
            evaluated=evaluated,
            source_family=source_family,
        )

    row = families.get(source_family)
    if row is None:
        return _refused(
            request,
            ["FAMILY_NOT_ENROLLED"],
            registry_path_str=registry_path_str,
            evaluated=evaluated,
            source_family=source_family,
            registry_revision=revision,
        )

    cls = str(row.get("rights_class", "")).strip()
    if cls not in rights.RIGHTS_CLASSES:
        return _refused(
            request,
            ["RIGHTS_CLASS_UNREADABLE"],
            registry_path_str=registry_path_str,
            evaluated=evaluated,
            source_family=source_family,
            registry_revision=revision,
        )

    if cls == "unresolved":
        return _refused(
            request,
            ["RIGHTS_UNRESOLVED"],
            registry_path_str=registry_path_str,
            evaluated=evaluated,
            source_family=source_family,
            rights_class=cls,
            registry_revision=revision,
        )

    auth = str(row.get("auth_class", "")).strip() or None

    return {
        "verdict": "ALLOWED",
        "reason_codes": [],
        "purpose": PURPOSE,
        "phase": request["phase"],
        "market": request["market"],
        "source_ref": source_ref,
        "source_sha256": request["source_sha256"],
        "generation_id": request["generation_id"],
        "source_family": source_family,
        "rights_class": cls,
        "auth_class": auth,
        "registry_revision": revision,
        "registry_path": registry_path_str,
        "evaluated_at": evaluated,
    }


class CaptureCapability:
    """Callable incumbent capture gate; stores the last verdict and never raises."""

    def __init__(self, *, path: str | Path | None = None) -> None:
        self._path = path
        self.last_verdict: dict[str, Any] | None = None

    def __call__(self, request: object) -> bool:
        try:
            verdict = current_use_verdict(
                request if isinstance(request, Mapping) else {},
                path=self._path,
            )
            self.last_verdict = verdict
            if verdict["verdict"] == "REFUSED":
                log.info(
                    "theme_graph.rights_use: capture refused (%s)",
                    ",".join(verdict["reason_codes"]),
                )
            return verdict["verdict"] == "ALLOWED"
        except Exception:
            self.last_verdict = {
                "verdict": "REFUSED",
                "reason_codes": ["CAPABILITY_ERROR"],
                "purpose": None,
                "phase": None,
                "market": None,
                "source_ref": None,
                "source_sha256": None,
                "generation_id": None,
                "source_family": None,
                "rights_class": None,
                "auth_class": None,
                "registry_revision": None,
                "registry_path": str(
                    Path(self._path) if self._path is not None else rights.registry_path()
                ),
                "evaluated_at": _evaluated_at(None),
            }
            log.info(
                "theme_graph.rights_use: capture refused (CAPABILITY_ERROR)",
            )
            return False


def capture_capability(*, path: str | Path | None = None) -> CaptureCapability:
    return CaptureCapability(path=path)
