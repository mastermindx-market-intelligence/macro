"""Read-only production bindings for independently installed WTI evidence.

The two environment pins select immutable objects in the incumbent Yahoo store.
They are server configuration, never request inputs. Installing an admission pin
requires independently verified issuer/use evidence; a digest is NOT that proof.
No pin, missing object, stale subject or malformed input means no admission.
This module does not acquire, publish, sign or infer any facts or calendars.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

FACTS_PIN = "WTI_NATIVE_SESSION_FACTS_SHA256"
ADMISSION_PIN = "WTI_SCENARIO_ADMISSION_SHA256"
_DIGEST = re.compile(r"[0-9a-f]{64}")
_LIMIT = 500_000


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate evidence key")
        result[key] = value
    return result


def _finite(value):
    raise ValueError("nonfinite evidence value")


def _clock(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("invalid evidence clock")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("evidence clock requires timezone")
    return stamp.astimezone(timezone.utc)


def _read_selected(data_dir: Path, digest: str | None):
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        return None
    descriptors = []
    try:
        # Never follow a substituted store directory, symlink or special file.
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptors.append(os.open(data_dir, flags))
        for part in ("yahoo", ".availability_capture", "objects"):
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
        fd = os.open(digest + ".json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=descriptors[-1])
        descriptors.append(fd)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > _LIMIT:
            return None
        with os.fdopen(os.dup(fd), "rb") as stream:
            raw = stream.read(_LIMIT + 1)
        if len(raw) > _LIMIT or hashlib.sha256(raw).hexdigest() != digest:
            return None
        result = json.loads(raw, object_pairs_hook=_unique, parse_constant=_finite)
        return result if isinstance(result, dict) else None
    except (OSError, ValueError, TypeError, RecursionError):
        return None
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def _configuration(pin: str, data_dir, environ):
    from lib import config
    environment = os.environ if environ is None else environ
    # Freeze the explicit deployment selection; never scan for a "latest" object.
    return Path(config.data_dir() if data_dir is None else data_dir), environment.get(pin)


def native_session_reader(*, data_dir=None, environ=None):
    root, digest = _configuration(FACTS_PIN, data_dir, environ)

    def read(provider_sha, merged_sha, context_sha, observed):
        facts = _read_selected(root, digest)
        if facts is None:
            return None
        try:
            from lib.store import validate_wti_session_facts
            pairs = facts.get("historical_labels")
            if not isinstance(pairs, list) or any(not isinstance(p, list) or len(p) != 2 for p in pairs):
                return None
            # This supplier reads facts already known at this observation. The
            # capture owner separately validates against its actual frame/clock.
            return validate_wti_session_facts(facts, provider_sha=provider_sha,
                merged_sha=merged_sha, context_sha=context_sha,
                labels=[p[0] for p in pairs], observed=observed, captured=observed)
        except (ValueError, TypeError, KeyError, IndexError, OverflowError):
            return None
    return read


def session_selector(*, data_dir=None, environ=None):
    root, digest = _configuration(ADMISSION_PIN, data_dir, environ)

    def select(subject):
        from engine.ontology_scenario_runtime import WTISessionAdmission, WTISessionSubject
        if not isinstance(subject, WTISessionSubject):
            return None
        receipt = _read_selected(root, digest)
        if receipt is None:
            return None
        try:
            if (set(receipt) != {"schema", "subject", "native_facts_sha256", "known_by"}
                    or receipt["schema"] != "ontology.wti_session_admission.v1"
                    or receipt["subject"] != asdict(subject)
                    or not isinstance(receipt["native_facts_sha256"], str)
                    or not _DIGEST.fullmatch(receipt["native_facts_sha256"])
                    or _clock(receipt["known_by"]) > _clock(subject.knowledge_cutoff)):
                return None
            # Downstream binds facts digest, export/TXI completion and cutoff
            # before any price decoding. An exported capture cannot issue this.
            return WTISessionAdmission(subject, receipt["native_facts_sha256"], receipt["known_by"])
        except (ValueError, TypeError, KeyError, OverflowError):
            return None
    return select


def configure_wti_sessions(app):
    """Install only the reader callable; no evidence I/O or promotion at startup."""
    from app.ontology_explorer import _repo_root
    # Match the API's server-selected publication root (including MACRO_REPO),
    # rather than accidentally selecting admission from a source checkout.
    app.state.wti_session_selector = session_selector(data_dir=_repo_root() / "data")
