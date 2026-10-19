"""Small shared utilities: logging, hashing, slugify, filenames, time helpers."""
from __future__ import annotations

import hashlib
import logging
import re
import time
import unicodedata
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterable, Iterator, Sequence, TypeVar

T = TypeVar("T")

_LOG_CONFIGURED = False


def setup_logging(
    log_dir: str | Path, level: int = logging.INFO, *, console: bool = True
) -> logging.Logger:
    """Configure root logging with a rotating file handler + console. Idempotent."""
    global _LOG_CONFIGURED
    logger = logging.getLogger("marketdesk")
    if _LOG_CONFIGURED:
        return logger
    logger.setLevel(level)
    logger.propagate = False
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(
        Path(log_dir) / "marketdesk.log", maxBytes=5_000_000, backupCount=7,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    if console:
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(ch)
    _LOG_CONFIGURED = True
    return logger


def get_logger(name: str = "marketdesk") -> logging.Logger:
    return logging.getLogger("marketdesk" if name == "marketdesk" else f"marketdesk.{name}")


# --- hashing ---------------------------------------------------------------
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


# --- text / filenames ------------------------------------------------------
def slugify(text: str, max_len: int = 80) -> str:
    """Filesystem-safe, lowercased, hyphenated slug."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "untitled"


def normalize_ws(text: str | None) -> str:
    """Collapse repeated whitespace (MarketDesk titles have doubled spaces)."""
    return re.sub(r"\s+", " ", (text or "")).strip()


def build_pdf_filename(
    *, date_str: str, institution: str | None, title: str, blob_id: str
) -> str:
    """``{date}_{institution}_{slug(title)}_{blob_id}.pdf`` — clean + collision-safe."""
    inst = slugify(institution or "unknown", max_len=24)
    return f"{date_str}_{inst}_{slugify(title)}_{blob_id}.pdf"


# --- time ------------------------------------------------------------------
def iso_from_unix(t: int | None) -> str | None:
    if t is None:
        return None
    return datetime.fromtimestamp(int(t), tz=timezone.utc).isoformat()


def date_str_from_unix(t: int | None) -> str:
    """YYYY-MM-DD (UTC) used for filenames + R2/data folders. Falls back to today."""
    dt = datetime.fromtimestamp(int(t), tz=timezone.utc) if t else datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d")


def humanize_age(t: int | None, *, now: int | None = None) -> str | None:
    """MarketDesk-style age text from a unix timestamp: '5 min', '2 hr', 'Jul 6'."""
    if t is None:
        return None
    now = now if now is not None else int(time.time())
    delta = max(0, now - int(t))
    if delta < 3600:
        m = max(1, delta // 60)
        return f"{m} min"
    if delta < 86400:
        return f"{delta // 3600} hr"
    dt = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return dt.strftime("%b %-d") if hasattr(dt, "strftime") else dt.isoformat()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# --- misc ------------------------------------------------------------------
def chunked(seq: Sequence[T], size: int) -> Iterator[list[T]]:
    for i in range(0, len(seq), size):
        yield list(seq[i : i + size])


def jitter_sleep(base: float = 0.3, spread: float = 0.4) -> None:
    """Small politeness delay with deterministic-ish jitter (no randomness import needed)."""
    time.sleep(base + spread * (time.monotonic() % 1.0))
