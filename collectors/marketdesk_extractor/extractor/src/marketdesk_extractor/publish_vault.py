"""Research Vault publisher — a downstream hand-off target (additive).

Each COMPLETE MarketDesk paper is written to a PRIVATE Cloudflare R2 bucket under a
``research_inbox/`` prefix as a *pair*:

* ``{prefix}/{id}.pdf``  — the raw research PDF (from the local file, or copied from
  the paper's existing object in the *main* R2 bucket when the local copy is gone).
* ``{prefix}/{id}.json`` — a ``research_vault.sidecar.v1`` sidecar (see ``sidecar_for``).

A downstream dashboard runs an hourly ingest over that prefix and consumes the pairs.
This module ONLY wires the pipe: it makes no redistribution-rights decision and never
bypasses auth — it republishes artifacts the pipeline already fetched under the
authenticated session.

``VaultPublisher`` mirrors ``R2Uploader`` (lazy boto3 import so this module imports with
only stdlib + pydantic; S3-compatible client against the same Cloudflare account) but
targets a DIFFERENT bucket. ``sidecar_for`` is a pure, unit-testable mapping and is kept
free of any I/O.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .config import Config
from .utils import get_logger, normalize_ws

SIDECAR_SCHEMA = "research_vault.sidecar.v1"

# ---------------------------------------------------------------------------
# institution code -> display name
# ---------------------------------------------------------------------------
# Covers the IMPORTANT_INSTITUTIONS keys (config.py) plus the broker codes that
# show up in a paper's breadcrumb. Matching is case-insensitive on the raw string;
# unmapped values fall back to the raw string unchanged (see display_institution).
INSTITUTION_DISPLAY: dict[str, str] = {
    "GS": "Goldman Sachs",
    "GOLDMAN": "Goldman Sachs",
    "GOLDMAN SACHS": "Goldman Sachs",
    "JPM": "J.P. Morgan",
    "JP MORGAN": "J.P. Morgan",
    "J.P. MORGAN": "J.P. Morgan",
    "JPMORGAN": "J.P. Morgan",
    "MS": "Morgan Stanley",
    "MORGAN STANLEY": "Morgan Stanley",
    "BOFA": "Bank of America",
    "BAML": "Bank of America",
    "MERRILL": "Bank of America",
    "BANK OF AMERICA": "Bank of America",
    "DB": "Deutsche Bank",
    "DEUTSCHE": "Deutsche Bank",
    "DEUTSCHE BANK": "Deutsche Bank",
    "UBS": "UBS",
    "CITI": "Citi",
    "CITIGROUP": "Citi",
    "RBC": "RBC",
    "RBC CAPITAL MARKETS": "RBC",
    "BNY": "BNY",
    "BNY MELLON": "BNY",
    "BERNSTEIN": "Bernstein",
    "EVERCORE": "Evercore",
    "JEFFERIES": "Jefferies",
    "BARCLAYS": "Barclays",
    "BARC": "Barclays",
    "WELLS FARGO": "Wells Fargo",
    "WFC": "Wells Fargo",
    "CREDIT SUISSE": "Credit Suisse",
    "CS": "Credit Suisse",
    "HSBC": "HSBC",
    "NOMURA": "Nomura",
    "MIZUHO": "Mizuho",
    "TD": "TD Securities",
    "TD SECURITIES": "TD Securities",
    "BMO": "BMO Capital Markets",
    "COWEN": "TD Cowen",
    "TD COWEN": "TD Cowen",
    "WOLFE": "Wolfe Research",
    "PIPER": "Piper Sandler",
    "PIPER SANDLER": "Piper Sandler",
    "RAYMOND JAMES": "Raymond James",
    "STIFEL": "Stifel",
    "GUGGENHEIM": "Guggenheim",
    "MACQUARIE": "Macquarie",
    "SOCGEN": "Societe Generale",
    "SOCIETE GENERALE": "Societe Generale",
    "BNP": "BNP Paribas",
    "BNP PARIBAS": "BNP Paribas",
    "CITIC": "CITIC",
    "CLSA": "CLSA",
}

# Institutions that are buy-side (PE/asset managers) or independent research —
# everything else defaults to "sell" (MarketDesk is predominantly sell-side).
# Matched on the DISPLAY name, case-insensitively.
_BUY_SIDE = {
    "kkr", "apollo", "blackstone", "carlyle", "ares", "brookfield", "pimco",
    "bridgewater",
}
_INDEPENDENT = {
    "zero hedge", "the market ear", "ts lombard", "bca research",
    "capital economics", "alpine macro", "rosenberg research", "hedgeye",
    "gavekal", "other",
}


def side_for(institution_display: str | None) -> str:
    """Classify an institution's research side: buy | sell | independent."""
    if not institution_display:
        return "sell"
    key = institution_display.strip().lower()
    if key in _BUY_SIDE:
        return "buy"
    if key in _INDEPENDENT:
        return "independent"
    return "sell"

# Sentence splitter for turning a free-text summary into short bullets.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
# Leading markdown list/heading markers to strip from a bullet.
_MD_LEAD = re.compile(r"^\s*(?:[-*#>]+|\d+[.)])\s*")

_MIN_SUMMARY_POINTS = 2
_MAX_SUMMARY_POINTS = 5


# ---------------------------------------------------------------------------
# display-name helper
# ---------------------------------------------------------------------------
def display_institution(raw: Any) -> str | None:
    """Map a broker code/name to its display name; fall back to the raw string.

    Returns None only when *raw* is falsy (None/empty). Matching is case- and
    surrounding-whitespace-insensitive; an unmapped value is returned unchanged
    (trimmed) so we never drop information.
    """
    if not raw:
        return None
    key = str(raw).strip()
    if not key:
        return None
    return INSTITUTION_DISPLAY.get(key.upper(), key)


# ---------------------------------------------------------------------------
# field access — tolerate dict / sqlite3.Row / pydantic model / plain object
# ---------------------------------------------------------------------------
def _get(paper: Any, name: str, default: Any = None) -> Any:
    """Best-effort read of *name* from a paper mapping or object.

    Handles a plain dict, a ``sqlite3.Row`` (raises IndexError on a missing
    column — treated as absent), a pydantic model, or any attribute-bearing
    object. Missing -> *default*.
    """
    # mapping-like (dict, sqlite3.Row) — Row.keys() lists its columns
    keys = getattr(paper, "keys", None)
    if callable(keys):
        try:
            if name in set(keys()):
                val = paper[name]
                return default if val is None else val
            return default
        except Exception:  # noqa: BLE001 — fall through to attribute access
            pass
    # attribute-bearing object (pydantic model, dataclass, namespace)
    if hasattr(paper, name):
        val = getattr(paper, name)
        return default if val is None else val
    return default


def _to_bool(val: Any) -> bool:
    """Coerce a DB/JSON truthy value (0/1, '0'/'1', 'true'/'false') to bool."""
    if isinstance(val, str):
        return val.strip().lower() in {"1", "true", "yes", "on"}
    return bool(val)


def _summary_points(summary: Any) -> list[str]:
    """Split a free-text summary into 2-5 short, marker-free bullets.

    Splits on newlines / bullet markers first, then on sentence boundaries;
    strips leading markdown ``-``/``*``/``#``/``1.`` markers and collapses
    whitespace. Returns ``[]`` when *summary* is absent/blank.
    """
    if not summary:
        return []
    text = str(summary).strip()
    if not text:
        return []

    # 1) prefer explicit line / bullet boundaries
    raw_parts = [p for p in re.split(r"[\r\n]+|(?:^|\s)[•·]\s+", text) if p and p.strip()]
    # 2) if it was one blob, fall back to sentence splitting
    if len(raw_parts) < _MIN_SUMMARY_POINTS:
        raw_parts = _SENT_SPLIT.split(text)

    points: list[str] = []
    for part in raw_parts:
        cleaned = _MD_LEAD.sub("", part).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if cleaned:
            points.append(cleaned)
        if len(points) >= _MAX_SUMMARY_POINTS:
            break

    # a single un-splittable sentence is still one valid bullet
    if not points and text:
        points = [re.sub(r"\s+", " ", text)]
    return points


# ---------------------------------------------------------------------------
# truncated-title detection + /extra recovery
# ---------------------------------------------------------------------------
# MarketDesk ships some titles truncated: its ``name`` field drops a Reuters
# ``.EX)`` exchange suffix, so ``Alcon Inc. (ALCC.US)`` arrives as
# ``Alcon Inc. (ALCC`` (the tell is an unbalanced '('). We faithfully store what
# arrives; ``looks_truncated`` flags the symptom and ``extra_title`` recovers a
# fuller title from the item's ``/extra`` payload when one is present.
_EXTRA_TITLE_KEYS = ("title", "name", "displayName", "fullTitle", "originalName", "fileName")


def looks_truncated(title: Any) -> bool:
    """True when a title has more '(' than ')' — the fingerprint of a dropped
    ``.EX)`` exchange suffix (``Carrefour (CARR``, ``SAP (SAPG``, ``Alcon Inc. (ALCC``)."""
    if not title:
        return False
    t = str(title)
    return t.count("(") > t.count(")")


def _strip_pdf_ext(s: str) -> str:
    """Strip ONLY a trailing ``.pdf`` — never ``os.path.splitext``, which is the
    very operation that truncated ``(CARR.PA)`` to ``(CARR`` at the source."""
    return re.sub(r"\.pdf$", "", (s or "").strip(), flags=re.IGNORECASE)


def extra_title(extra: Any, current_title: Any) -> str | None:
    """A fuller replacement title from an item's ``/extra`` payload, or None.

    Returns a value ONLY when *current_title* looks truncated AND the payload
    carries a candidate that is balanced (no dangling '(') and at least as long —
    so a good title is never regressed, and a candidate that is itself truncated
    (MarketDesk's own ``name`` often is) is rejected. Which ``/extra`` key (if any)
    holds the full title is confirmed on the next live run; the multi-key probe +
    reject-if-not-better guard make an absent/unhelpful key a safe no-op.
    """
    cur = normalize_ws(current_title or "")
    if not looks_truncated(cur) or not isinstance(extra, dict):
        return None
    for k in _EXTRA_TITLE_KEYS:
        v = extra.get(k)
        if not isinstance(v, str):
            continue
        cand = normalize_ws(_strip_pdf_ext(v))
        if not cand or looks_truncated(cand):
            continue
        if len(cand) >= len(cur):
            return cand
    return None


def _breadcrumb(paper: Any) -> list[str]:
    """Return the paper's breadcrumb as a list of trimmed strings ([] if absent).

    Tolerates a real list, a JSON-encoded string (as it may arrive from a DB
    column), or a missing value.
    """
    raw = _get(paper, "breadcrumb", None)
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            raw = parsed if isinstance(parsed, list) else [raw]
        except Exception:  # noqa: BLE001 — not JSON; treat as a single crumb
            raw = [raw]
    try:
        return [str(x).strip() for x in raw if str(x).strip()]
    except TypeError:
        return []


def _desk_from_breadcrumb(crumbs: list[str], institution_raw: Any) -> str | None:
    """Last breadcrumb segment that is not the institution (e.g. 'S&T', 'Equity').

    Breadcrumbs look like ``[2026, July, Jul 7, Goldman, S&T]`` — the desk is the
    trailing non-institution crumb. Returns None when nothing qualifies.
    """
    if not crumbs:
        return None
    inst = str(institution_raw).strip().lower() if institution_raw else ""
    inst_display = (display_institution(institution_raw) or "").lower()

    def _is_inst(text: str) -> bool:
        tl = text.strip().lower()
        td = (display_institution(text) or "").lower()
        return tl == inst or tl == inst_display or (
            bool(inst_display) and td == inst_display
        )

    for crumb in reversed(crumbs):
        c = crumb.strip()
        if not c:
            continue
        # "Bernstein (Data Centers)" as a crumb: the base IS the institution and
        # the parenthetical is the desk.
        m = re.match(r"^\s*(.+?)\s*\(([^)]+)\)\s*$", c)
        if m and _is_inst(m.group(1)):
            return m.group(2).strip()
        # Skip any crumb that IS the institution under any of its variants:
        # the raw code ("GS"), the display name ("Goldman Sachs"), or a mapped
        # alias ("Goldman" -> "Goldman Sachs" == display).
        if _is_inst(c):
            continue
        return c
    return None


# ---------------------------------------------------------------------------
# the pure mapping — MarketDesk paper -> research_vault.sidecar.v1
# ---------------------------------------------------------------------------
def vault_id(blob_id: Any) -> str:
    """Stable, idempotent, CASE-SAFE sidecar id for a paper.

    MarketDesk blob ids are case-sensitive base62 (``yRoSHLwPSzj``), but the
    downstream vault slugs ids to lowercase — so two blob ids differing only in
    case would collide after the fold. We lowercase up front and append a 6-hex
    sha256 of the ORIGINAL id, which survives any case-folding downstream:
    ``marketdesk-yroshlwpszj-a41f09``. Deterministic -> idempotent re-publish.
    """
    import hashlib
    raw = str(blob_id)
    h6 = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:6]
    safe = re.sub(r"[^a-z0-9-]+", "-", raw.lower()).strip("-") or "paper"
    return f"marketdesk-{safe}-{h6}"


def sidecar_for(paper: Any, *, top_pick_min_score: int = 85) -> dict:
    """Build the ``research_vault.sidecar.v1`` dict for a paper (pure; no I/O).

    *paper* may be a DB row (``sqlite3.Row``/dict), a ``ManifestEntry``/pydantic
    model, or any attribute-bearing object exposing the MarketDesk fields
    (``blob_id, title, institution, published_at, marketdesk_summary, breadcrumb,
    is_top_pick, is_saved, local_priority_score, page_count`` + optional
    ``pdf_filename``, ``tickers``, ``tags``, ``language``).
    """
    blob_id = _get(paper, "blob_id", "")
    institution_raw = _get(paper, "institution", None)

    # "Bernstein (Data Centers)" -> institution "Bernstein", desk "Data Centers".
    paren_desk = None
    if institution_raw:
        m = re.match(r"^\s*(.+?)\s*\(([^)]+)\)\s*$", str(institution_raw))
        if m:
            institution_raw, paren_desk = m.group(1), m.group(2).strip()

    crumbs = _breadcrumb(paper)
    desk = _desk_from_breadcrumb(crumbs, institution_raw) or paren_desk

    score = _get(paper, "local_priority_score", None)
    try:
        score_val = int(score) if score is not None else 0
    except (TypeError, ValueError):
        score_val = 0
    top_pick = _to_bool(_get(paper, "is_top_pick", False)) or (
        score_val >= int(top_pick_min_score)
    )

    published = _get(paper, "published_at", None)
    published_iso = _isoformat_z(published)

    # pages: page_count when present
    pages = _get(paper, "page_count", None)
    try:
        pages = int(pages) if pages is not None else None
    except (TypeError, ValueError):
        pages = None

    # source_filename: the pdf filename (DB col pdf_filename; ManifestEntry has a path)
    source_filename = _get(paper, "pdf_filename", None)
    if not source_filename:
        local_pdf = _get(paper, "local_pdf_path", None)
        if local_pdf:
            source_filename = str(local_pdf).rsplit("/", 1)[-1]

    # tags: breadcrumb desk + any cheap keyword tags already captured
    tags: list[str] = []
    if desk:
        tags.append(desk)
    extra_tags = _get(paper, "tags", None)
    if extra_tags:
        for t in extra_tags if isinstance(extra_tags, (list, tuple)) else [extra_tags]:
            ts = str(t).strip()
            if ts and ts not in tags:
                tags.append(ts)

    # tickers: watchlist matches if captured, else []
    tickers_raw = _get(paper, "tickers", None)
    tickers: list[str] = []
    if tickers_raw:
        for t in tickers_raw if isinstance(tickers_raw, (list, tuple)) else [tickers_raw]:
            ts = str(t).strip()
            if ts and ts not in tickers:
                tickers.append(ts)

    inst_display = display_institution(institution_raw)
    sidecar: dict[str, Any] = {
        "schema": SIDECAR_SCHEMA,
        "id": vault_id(blob_id),
        "title": _get(paper, "title", "") or "",
        "institution": inst_display,
        "desk": desk,
        "side": side_for(inst_display),
        "published_at": published_iso,
        "summary_points": _summary_points(_get(paper, "marketdesk_summary", None)),
        "tags": tags,
        "tickers": tickers,
        "top_pick": top_pick,
        "pages": pages,
        "language": str(_get(paper, "language", "en") or "en"),
        "source_filename": source_filename,
    }
    return sidecar


def _isoformat_z(published: Any) -> str | None:
    """Normalize a published_at value to an ISO-8601 string with a Z suffix.

    Accepts a datetime, an ISO string (possibly with ``+00:00``), or None.
    """
    if published is None:
        return None
    # datetime -> isoformat
    iso = published.isoformat() if hasattr(published, "isoformat") else str(published)
    iso = iso.strip()
    if not iso:
        return None
    if iso.endswith("+00:00"):
        return iso[:-6] + "Z"
    return iso


# ---------------------------------------------------------------------------
# the publisher — mirrors R2Uploader, different bucket
# ---------------------------------------------------------------------------
class VaultPublisher:
    """Publish (PDF + sidecar) pairs to the PRIVATE Research Vault R2 bucket.

    Mirrors ``R2Uploader``: lazy boto3 import, S3-compatible client against the
    same Cloudflare account (``r2_account_id`` endpoint, reusing the R2 keys),
    idempotent writes. Targets ``cfg.vault_r2_bucket`` under ``cfg.vault_r2_prefix``.
    """

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._log = get_logger("publish_vault")
        self._client: object | None = None       # vault-account client
        self._main_client: object | None = None  # main-account client (fallback reads)

        if self.enabled:
            import boto3  # lazy import — optional dep

            self._client = boto3.client(
                "s3",
                endpoint_url=f"https://{self._vault_account_id()}.r2.cloudflarestorage.com",
                aws_access_key_id=self._vault_key(),
                aws_secret_access_key=self._vault_secret(),
                region_name="auto",
            )

    # --- cred resolution: VAULT_R2_* (own Cloudflare account) -> main R2_* ----
    def _vault_account_id(self) -> str:
        return self._cfg.vault_r2_account_id or self._cfg.r2_account_id

    def _vault_key(self) -> str:
        return self._cfg.vault_r2_access_key_id or self._cfg.r2_access_key_id

    def _vault_secret(self) -> str:
        return self._cfg.vault_r2_secret_access_key or self._cfg.r2_secret_access_key

    @property
    def enabled(self) -> bool:
        """True only when vault publishing is on AND creds + bucket resolve.

        The vault bucket may live in its OWN Cloudflare account (VAULT_R2_ACCOUNT_ID
        / VAULT_R2_ACCESS_KEY_ID / VAULT_R2_SECRET_ACCESS_KEY); each credential falls
        back to the main R2_* value for the same-account case.
        """
        cfg = self._cfg
        return bool(
            cfg.vault_enabled
            and self._vault_account_id()
            and self._vault_key()
            and self._vault_secret()
            and cfg.vault_r2_bucket
        )

    def pdf_key(self, vid: str) -> str:
        return f"{self._cfg.vault_r2_prefix}/{vid}.pdf"

    def json_key(self, vid: str) -> str:
        return f"{self._cfg.vault_r2_prefix}/{vid}.json"

    # --- low-level R2 helpers (vault bucket) -------------------------------
    def _exists(self, key: str) -> bool:
        if not self.enabled or self._client is None:
            return False
        try:
            self._client.head_object(Bucket=self._cfg.vault_r2_bucket, Key=key)  # type: ignore[attr-defined]
            return True
        except Exception as exc:  # noqa: BLE001
            try:
                code = exc.response["Error"]["Code"]  # type: ignore[attr-defined]
                if code in ("404", "NoSuchKey", "NotFound"):
                    return False
            except Exception:
                pass
            self._log.debug("vault exists(%s) check failed: %s", key, exc)
            return False

    def _read_main_object(self, key: str) -> bytes | None:
        """Read a PDF's bytes from the MAIN R2 bucket (fallback source).

        The main archive may be in a DIFFERENT Cloudflare account than the vault,
        so this uses its own client built from the main R2_* creds (lazy).
        """
        cfg = self._cfg
        if not (cfg.r2_account_id and cfg.r2_access_key_id
                and cfg.r2_secret_access_key and cfg.r2_bucket):
            return None
        try:
            if self._main_client is None:
                import boto3  # lazy import — optional dep
                self._main_client = boto3.client(
                    "s3",
                    endpoint_url=f"https://{cfg.r2_account_id}.r2.cloudflarestorage.com",
                    aws_access_key_id=cfg.r2_access_key_id,
                    aws_secret_access_key=cfg.r2_secret_access_key,
                    region_name="auto",
                )
            resp = self._main_client.get_object(Bucket=cfg.r2_bucket, Key=key)  # type: ignore[attr-defined]
            return resp["Body"].read()
        except Exception as exc:  # noqa: BLE001
            self._log.warning("vault: could not read main r2://%s/%s: %s",
                              cfg.r2_bucket, key, exc)
            return None

    def _put(self, key: str, body: bytes, content_type: str) -> None:
        self._client.put_object(  # type: ignore[attr-defined]
            Bucket=self._cfg.vault_r2_bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    # --- public API --------------------------------------------------------
    def publish(self, paper: Any, *, force: bool = False) -> str | None:
        """Publish one paper's (PDF + sidecar) pair to the vault bucket.

        Returns the sidecar id on success, or None when disabled / skipped /
        failed. NEVER raises on a single paper — a bad paper is logged and
        skipped so a batch keeps going.

        Idempotent: when *both* keys already exist and *force* is False, this is
        a no-op that still returns the id (so callers can mark the paper vaulted).
        """
        if not self.enabled or self._client is None:
            return None

        try:
            blob_id = _get(paper, "blob_id", None)
            if not blob_id:
                self._log.warning("vault: paper has no blob_id; skipping")
                return None
            vid = vault_id(blob_id)
            pkey = self.pdf_key(vid)
            jkey = self.json_key(vid)

            if not force and self._exists(pkey) and self._exists(jkey):
                self._log.debug("vault: skip (both keys exist): %s", vid)
                return vid

            # --- PDF bytes: local raw file first, else copy from main bucket ---
            pdf_bytes = self._pdf_bytes(paper)
            if pdf_bytes is None:
                self._log.warning("vault: no PDF bytes available for %s; skipping", vid)
                return None

            # --- write the pair (PDF then sidecar) ---
            if force or not self._exists(pkey):
                self._put(pkey, pdf_bytes, "application/pdf")
            sidecar = sidecar_for(
                paper, top_pick_min_score=self._cfg.vault_top_pick_min_score
            )
            body = json.dumps(sidecar, ensure_ascii=False).encode("utf-8")
            self._put(jkey, body, "application/json")

            self._log.info("vault: published %s -> r2://%s/%s{.pdf,.json}",
                          vid, self._cfg.vault_r2_bucket, pkey.rsplit(".", 1)[0])
            return vid
        except Exception as e:  # noqa: BLE001 — one bad paper never aborts a batch
            bid = _get(paper, "blob_id", "?")
            self._log.error("vault: publish failed for %s: %s", bid, e)
            return None

    def republish_sidecar(self, paper: Any) -> str | None:
        """Overwrite ONLY the sidecar ``.json`` for an already-vaulted paper — the
        PDF is left in place. Used to push corrected metadata (a late-generated
        MarketDesk summary, a recovered full title) without re-uploading the PDF
        (so it works even after the local raw file is pruned and R2 archive is off).
        Returns the id, or None (disabled / no blob_id / failed). Never raises."""
        if not self.enabled or self._client is None:
            return None
        try:
            blob_id = _get(paper, "blob_id", None)
            if not blob_id:
                self._log.warning("vault: sidecar re-publish skipped — no blob_id")
                return None
            vid = vault_id(blob_id)
            sidecar = sidecar_for(
                paper, top_pick_min_score=self._cfg.vault_top_pick_min_score
            )
            body = json.dumps(sidecar, ensure_ascii=False).encode("utf-8")
            self._put(self.json_key(vid), body, "application/json")
            self._log.info("vault: re-published sidecar %s", vid)
            return vid
        except Exception as e:  # noqa: BLE001 — one bad paper never aborts a batch
            self._log.error("vault: sidecar re-publish failed for %s: %s",
                            _get(paper, "blob_id", "?"), e)
            return None

    def _pdf_bytes(self, paper: Any) -> bytes | None:
        """PDF bytes for *paper*: local raw file if present, else main-bucket copy."""
        local_pdf = _get(paper, "local_pdf_path", None)
        if local_pdf:
            try:
                with open(local_pdf, "rb") as fh:
                    return fh.read()
            except OSError as exc:
                self._log.debug("vault: local pdf unreadable (%s): %s", local_pdf, exc)
        r2_pdf_key = _get(paper, "r2_pdf_key", None)
        if r2_pdf_key:
            return self._read_main_object(str(r2_pdf_key))
        return None
