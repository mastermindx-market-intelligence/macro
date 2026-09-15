"""Central configuration + tunable selectors.

All runtime configuration is loaded from environment variables (via a ``.env`` file
using ``python-dotenv``). Nothing secret is ever hard-coded. Relative paths are
resolved against the current working directory (the cron/systemd job ``cd``s into the
project root before running).

The DOM ``SELECTORS`` block exists only for the resilience fallback in ``discover.py``;
the primary discovery path uses the MarketDesk JSON API (see ``docs/MARKETDESK_API.md``)
and needs no selectors.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _path(name: str, default: str) -> Path:
    return Path(os.getenv(name, default)).expanduser().resolve()


def _optional_path(name: str) -> Path | None:
    raw = (os.getenv(name, "") or "").strip()
    return Path(raw).expanduser().resolve() if raw else None


def _default_exclude_institutions() -> set[str]:
    """The embedded default blog/newsletter exclude set (from ``filters.py``).

    Imported lazily so ``config`` stays free of a hard import of the DB/schema
    layer at module load; ``filters`` never imports ``config``, so this is
    cycle-safe either way.
    """
    from .filters import DEFAULT_EXCLUDE_INSTITUTIONS
    return set(DEFAULT_EXCLUDE_INSTITUTIONS)


def _csv(name: str) -> list[str]:
    raw = os.getenv(name, "") or ""
    return [x.strip() for x in raw.split(",") if x.strip()]


def _csv_default(name: str, default: set[str]) -> set[str]:
    """CSV env var -> lower-cased set; falls back to ``default`` if unset or blank.

    Unlike ``_csv`` (which returns ``[]`` when the var is absent), this preserves an
    embedded default so a knob whose sensible "off" value is a non-empty set behaves
    correctly. An absent, empty, or all-whitespace value yields ``default`` — an
    accidentally-cleared line should not silently disable the filter. To turn the
    set OFF, use the feature's dedicated enable flag rather than emptying this list.
    """
    raw = os.getenv(name)
    if raw is None:
        return set(default)
    items = {x.strip().lower() for x in raw.split(",") if x.strip()}
    return items if items else set(default)


@dataclass(frozen=True)
class Profile:
    """One MarketDesk account = one persistent Playwright profile directory.

    ``name`` is a short stable label used in logs and the per-account rolling
    ledger (the ``papers.account`` column); ``path`` is the on-disk profile dir.
    """

    name: str
    path: Path


def _parse_profiles(raw: str, *, default_dir: Path) -> list[Profile]:
    """Parse ``MARKETDESK_PROFILES`` into an ordered, de-duplicated list.

    Each comma-separated entry is either ``name:path`` or just ``path`` (the name
    is then derived from the directory's basename). Blank/absent → a single
    profile pointing at ``default_dir`` (the existing single-account setup), whose
    name is derived the same way. Names are made unique by suffixing ``-2``, ``-3``
    on collision so the ledger key never silently merges two accounts.
    """
    entries = [e.strip() for e in (raw or "").split(",") if e.strip()]
    if not entries:
        entries = [str(default_dir)]

    out: list[Profile] = []
    used: dict[str, int] = {}
    for entry in entries:
        if ":" in entry and not _looks_like_windows_path(entry):
            name_part, _, path_part = entry.partition(":")
            name = name_part.strip()
            path_raw = path_part.strip()
        else:
            name = ""
            path_raw = entry
        path = Path(path_raw).expanduser().resolve()
        if not name:
            name = path.name or "account"
        # ensure uniqueness of the ledger key
        if name in used:
            used[name] += 1
            name = f"{name}-{used[name]}"
        else:
            used[name] = 1
        out.append(Profile(name=name, path=path))
    return out


def _looks_like_windows_path(entry: str) -> bool:
    # e.g. "C:\\Users\\..." — a drive-letter colon, not a name:path separator.
    return len(entry) >= 2 and entry[1] == ":" and entry[0].isalpha()


# ---------------------------------------------------------------------------
# Priority scoring config (rule-based, cheap, pre-download). See score.py.
# ---------------------------------------------------------------------------
IMPORTANT_INSTITUTIONS: dict[str, int] = {
    # canonical name/abbrev -> points. Matching is case-insensitive substring.
    "JPM": 25, "J.P. Morgan": 25, "JP Morgan": 25,
    "Morgan Stanley": 22, "MS": 22,
    "Goldman": 25, "Goldman Sachs": 25, "GS": 25,
    "BofA": 20, "Bank of America": 20, "BAML": 20, "Merrill": 20,
    "Citi": 18, "Citigroup": 18,
    "UBS": 18,
    "Bernstein": 18,
    "Evercore": 16,
    "Jefferies": 16,
}

# keyword -> points (case-insensitive, matched against title + AI summary).
KEYWORD_POINTS: dict[str, int] = {
    "catalyst": 10, "upgrade": 9, "downgrade": 9, "positive catalyst": 12,
    "earnings preview": 9, "earnings": 5, "margin": 6, "estimates": 6,
    "revisions": 8, "revision": 8, "positioning": 8, "flows": 7, "flow": 5,
    "macro": 5, "fed": 7, "cpi": 8, "rates": 6, "oil": 5, "ai": 6,
    "semis": 8, "semiconductor": 8, "datacenter": 8, "data center": 8,
    "credit": 6, "ipo": 8, "guidance": 7, "initiation": 9, "initiate": 9,
}

# points for tickers/watchlist symbols found in title/summary (per hit, capped).
WATCHLIST_POINTS_PER_HIT = 8
WATCHLIST_POINTS_CAP = 24

# penalty for low-actionability, calendar-only content.
LOW_ACTION_KEYWORDS: dict[str, int] = {
    "calendar": -6, "week ahead": -4, "daily wrap": -3, "morning note": -2,
    "recap": -3, "at a glance": -3,
}

# ---------------------------------------------------------------------------
# DOM fallback selectors (only used if the API path is unavailable).
# Centralized + easy to tune. Each entry is a list of candidate selectors tried
# in order; discovery also falls back to scraping all <a> anchors.
# ---------------------------------------------------------------------------
SELECTORS: dict[str, list[str]] = {
    "article_card": [
        "[data-testid=report-card]",
        ".report-card",
        ".latest-item",
        "li.report",
        "article",
    ],
    "card_title": [".report-title", ".title", "h3", "h4", "[data-field=title]"],
    "card_institution": [".institution", ".broker", "[data-field=institution]"],
    "card_age": [".age", ".timestamp", "time", "[data-field=age]"],
    "card_summary": [".summary", ".ai-summary", ".preview", "[data-field=summary]"],
    "card_link": ["a[href]"],
    "popout_button": [
        "[data-testid=popout]",
        "button[title*=pop i]",
        "a[target=_blank]",
        ".popout",
    ],
}


@dataclass
class Config:
    # MarketDesk / browser
    base_url: str
    profile_dir: Path
    headless: bool

    # storage / paths
    database_url: Path
    output_dir: Path
    raw_pdf_dir: Path
    markdown_dir: Path
    metadata_dir: Path
    manifest_dir: Path
    log_dir: Path

    # R2
    r2_enabled: bool
    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket: str
    r2_prefix: str

    # Dropbox
    dropbox_enabled: bool
    dropbox_access_token: str
    dropbox_prefix: str

    # Research Vault (downstream dashboard hand-off; PRIVATE R2 bucket). The vault
    # bucket may live in its OWN Cloudflare account: VAULT_R2_ACCOUNT_ID /
    # VAULT_R2_ACCESS_KEY_ID / VAULT_R2_SECRET_ACCESS_KEY each fall back to the
    # main R2_* value when blank (same-account case).
    vault_enabled: bool
    vault_r2_account_id: str
    vault_r2_access_key_id: str
    vault_r2_secret_access_key: str
    vault_r2_bucket: str
    vault_r2_prefix: str
    vault_top_pick_min_score: int

    # limits / politeness
    max_articles_per_run: int
    max_concurrent_pages: int
    max_concurrent_downloads: int
    max_concurrent_parse_workers: int
    default_since_hours: int

    # scoring
    download_only_above_priority: bool
    priority_threshold: int

    # exclusion filter (filters.py) — drop genuine noise before the download queue
    exclude_institutions: set[str]
    exclude_title_patterns_enabled: bool

    # multi-account "trickle" allocator (see allocator.py + trickle.py)
    download_cap_per_account_24h: int
    new_window_hours: int
    trickle_interval_sec: int
    discover_every_sec: int
    backfill_reserve_hours: int
    trickle_burst: int
    # periodic WIDE discovery pass (late-arriving AI summaries + truncated titles
    # only heal inside the discovery window, so the narrow 72h refresh can never
    # repair anything older — this is the daily deep pass that can)
    trickle_wide_discover_every_sec: int
    trickle_wide_discover_hours: int
    trickle_wide_heal_limit: int
    trickle_wide_discover_limit: int

    watchlist: list[str] = field(default_factory=list)
    # one persistent Playwright profile per account. Defaults to a single profile
    # at ``profile_dir`` so the pipeline works with one account today.
    profiles: list[Profile] = field(default_factory=list)

    # Optional fail-closed external-storage boundary. When configured, EVERY
    # mutable extractor path must live under storage_root, on the exact mounted
    # external volume. The free-space floor is checked at startup and before each
    # trickle tick/download so storage pressure never becomes a paper failure.
    storage_volume: Path | None = None
    storage_root: Path | None = None
    storage_volume_uuid: str = ""
    storage_min_free_gib: int = 0
    log_console: bool = True

    # parsing
    parser_backend: str = "marker"

    @classmethod
    def from_env(cls, dotenv_path: str | os.PathLike | None = None) -> "Config":
        load_dotenv(dotenv_path)  # loads ./.env by default; no-op if absent
        cfg = cls(
            base_url=os.getenv("MARKETDESK_BASE_URL", "https://marketdesk.ai").rstrip("/"),
            profile_dir=_path("MARKETDESK_PROFILE_DIR", "./browser_profile"),
            headless=_bool("MARKETDESK_HEADLESS", True),
            database_url=_path("DATABASE_URL", "./db/marketdesk.sqlite"),
            output_dir=_path("OUTPUT_DIR", "./data"),
            raw_pdf_dir=_path("RAW_PDF_DIR", "./data/raw_pdfs"),
            markdown_dir=_path("MARKDOWN_DIR", "./data/markdown"),
            metadata_dir=_path("METADATA_DIR", "./data/metadata"),
            manifest_dir=_path("MANIFEST_DIR", "./data/manifests"),
            log_dir=_path("LOG_DIR", "./logs"),
            r2_enabled=_bool("R2_ENABLED", False),
            r2_account_id=os.getenv("R2_ACCOUNT_ID", ""),
            r2_access_key_id=os.getenv("R2_ACCESS_KEY_ID", ""),
            r2_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY", ""),
            r2_bucket=os.getenv("R2_BUCKET", ""),
            r2_prefix=os.getenv("R2_PREFIX", "marketdesk").strip("/"),
            dropbox_enabled=_bool("DROPBOX_ENABLED", False),
            dropbox_access_token=os.getenv("DROPBOX_ACCESS_TOKEN", ""),
            dropbox_prefix=os.getenv("DROPBOX_PREFIX", "/marketdesk").rstrip("/"),
            vault_enabled=_bool("VAULT_ENABLED", False),
            vault_r2_account_id=os.getenv("VAULT_R2_ACCOUNT_ID", ""),
            vault_r2_access_key_id=os.getenv("VAULT_R2_ACCESS_KEY_ID", ""),
            vault_r2_secret_access_key=os.getenv("VAULT_R2_SECRET_ACCESS_KEY", ""),
            vault_r2_bucket=os.getenv("VAULT_R2_BUCKET", ""),
            vault_r2_prefix=os.getenv("VAULT_R2_PREFIX", "research_inbox").strip("/"),
            vault_top_pick_min_score=_int("VAULT_TOP_PICK_MIN_SCORE", 85),
            max_articles_per_run=_int("MAX_ARTICLES_PER_RUN", 300),
            max_concurrent_pages=_int("MAX_CONCURRENT_PAGES", 5),
            max_concurrent_downloads=_int("MAX_CONCURRENT_DOWNLOADS", 5),
            max_concurrent_parse_workers=_int("MAX_CONCURRENT_PARSE_WORKERS", 2),
            default_since_hours=_int("DEFAULT_SINCE_HOURS", 24),
            download_only_above_priority=_bool("DOWNLOAD_ONLY_ABOVE_PRIORITY", False),
            priority_threshold=_int("PRIORITY_THRESHOLD", 60),
            exclude_institutions=_csv_default(
                "EXCLUDE_INSTITUTIONS", _default_exclude_institutions()
            ),
            exclude_title_patterns_enabled=_bool("EXCLUDE_TITLE_PATTERNS_ENABLED", True),
            download_cap_per_account_24h=_int("DOWNLOAD_CAP_PER_ACCOUNT_24H", 70),
            new_window_hours=_int("NEW_WINDOW_HOURS", 48),
            trickle_interval_sec=_int("TRICKLE_INTERVAL_SEC", 60),
            discover_every_sec=_int("DISCOVER_EVERY_SEC", 900),
            backfill_reserve_hours=_int("BACKFILL_RESERVE_HOURS", 4),
            trickle_burst=_int("TRICKLE_BURST", 10),
            trickle_wide_discover_every_sec=_int(
                "TRICKLE_WIDE_DISCOVER_EVERY_SEC", 86400
            ),
            # 336h = 14 days, matching the dashboard ingest side's refresh window.
            trickle_wide_discover_hours=_int("TRICKLE_WIDE_DISCOVER_HOURS", 336),
            trickle_wide_heal_limit=_int("TRICKLE_WIDE_HEAL_LIMIT", 300),
            # walk_papers' limit caps SCANNED items, and MAX_ARTICLES_PER_RUN (300)
            # covers ~1.5 days at ~210 posts/day — a 14-day wide pass needs ~3000,
            # so it gets its own, much higher scan budget (discovery is uncapped).
            trickle_wide_discover_limit=_int("TRICKLE_WIDE_DISCOVER_LIMIT", 5000),
            watchlist=_csv("WATCHLIST"),
            storage_volume=_optional_path("MARKETDESK_STORAGE_VOLUME"),
            storage_root=_optional_path("MARKETDESK_STORAGE_ROOT"),
            storage_volume_uuid=os.getenv(
                "MARKETDESK_STORAGE_VOLUME_UUID", ""
            ).strip(),
            storage_min_free_gib=_int("MARKETDESK_STORAGE_MIN_FREE_GIB", 0),
            log_console=_bool("MARKETDESK_LOG_CONSOLE", True),
            parser_backend=os.getenv("PARSER_BACKEND", "marker").strip().lower(),
        )
        # Multi-account profiles: default to the single existing profile_dir so
        # the pipeline works unchanged with one account today.
        cfg.profiles = _parse_profiles(
            os.getenv("MARKETDESK_PROFILES", "") or "", default_dir=cfg.profile_dir
        )
        return cfg

    def mutable_paths(self) -> tuple[Path, ...]:
        """All extractor-owned paths that must share the guarded storage root."""
        return (
            self.output_dir,
            self.raw_pdf_dir,
            self.markdown_dir,
            self.metadata_dir,
            self.manifest_dir,
            self.log_dir,
            self.database_url,
            self.profile_dir,
            *(profile.path for profile in self.profiles),
        )

    def assert_storage_ready(self, *, extra_required_bytes: int = 0):
        """Return storage status, or raise before mutable work can touch disk."""
        if self.storage_volume is None and self.storage_root is None:
            return None
        if self.storage_volume is None or self.storage_root is None:
            from .storage import StorageGuardError
            raise StorageGuardError(
                "MARKETDESK_STORAGE_VOLUME and MARKETDESK_STORAGE_ROOT must be set together"
            )
        from .storage import check_storage
        return check_storage(
            volume=self.storage_volume,
            root=self.storage_root,
            managed_paths=self.mutable_paths(),
            required_volume_uuid=self.storage_volume_uuid,
            min_free_gib=self.storage_min_free_gib,
            extra_required_bytes=extra_required_bytes,
        )

    def ensure_dirs(self) -> None:
        """Validate durable storage first, then create child directories."""
        # Crucially, validation happens before mkdir. If /Volumes/STORAGE is not
        # mounted, no internal-disk directory can be created in its place.
        self.assert_storage_ready()
        for p in (
            self.output_dir, self.raw_pdf_dir, self.markdown_dir,
            self.metadata_dir, self.manifest_dir, self.log_dir,
            self.database_url.parent, self.profile_dir,
            *(profile.path for profile in self.profiles),
        ):
            Path(p).mkdir(parents=True, exist_ok=True)
        self.assert_storage_ready()

    # --- URL helpers (single source of truth for MarketDesk URL shapes) ---
    def blob_url(self, blob_id: str) -> str:
        return f"{self.base_url}/files/{blob_id}/blob"

    def article_url(self, item_id: str) -> str:
        return f"{self.base_url}/library/browse?item={item_id}"

    def api(self, path: str) -> str:
        return f"{self.base_url}/api/mobile/{path.lstrip('/')}"
