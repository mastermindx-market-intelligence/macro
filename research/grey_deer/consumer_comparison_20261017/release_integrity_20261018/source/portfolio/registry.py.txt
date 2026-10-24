"""Portfolio registry — the single source of truth for the books Mastermind manages.

Mastermind began as ONE paper book (the engine-gated *flagship*). It now harnesses
MULTIPLE independent portfolios, each with its own NAV / equity curve / blotter,
surfaced behind a tab switcher in the dashboard. A new portfolio TYPE is added by
appending an entry to ``PORTFOLIOS`` here and pointing a builder at it.

Path convention (chosen to preserve back-compat):
  * ``flagship`` (the original gated book) keeps its legacy home: ``data/portfolio/``.
  * every other portfolio lives under ``data/portfolios/<id>/``.

The per-portfolio store modules (``paper_account``, ``position_log``, ``trade_history``)
and the write-back ``bridge`` resolve their state files through ``data_dir(portfolio_id)``:
``None`` or the default id → the legacy dir (so the existing test fixtures that patch the
module-global path constants keep redirecting it); any other id → ``data/portfolios/<id>``.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# The original, engine-gated book. Its id resolves to the legacy data/portfolio/ dir.
#
# ``DEFAULT_ID`` is a STORAGE compatibility default, not the product/dashboard default.  It must
# remain ``flagship`` because a large amount of legacy code intentionally uses ``data_dir(None)``
# for the original ``data/portfolio`` tree.  New callers that need the product default should use
# ``DASHBOARD_DEFAULT_ID`` instead.
DEFAULT_ID = "flagship"
DASHBOARD_DEFAULT_ID = "autonomous"

# Ordered — this drives the dashboard tab order.
PORTFOLIOS: list[dict] = [
    {
        "id": "flagship",
        "name": "Flagship",
        "tagline": "Engine-gated · doctrine-disciplined",
        "kind": "gated",          # the deterministic, research-gated, sleeve-structured book
        "manager": "engine",
        "starting_nav": 1_000_000.0,
        "benchmark": "SPY",       # equity-curve comparison line
        "legacy": True,           # state lives in data/portfolio/ (not data/portfolios/flagship)
        "active": False,
        "status": "archived",
        "superseded_by": "autonomous",
        "archived_reason": "retired after the US-board design audit; history remains read-only",
    },
    {
        "id": "heavyweight",
        "name": "Heavyweight",
        "tagline": "Concentrated · presses Flagship's best",
        "kind": "heavyweight",    # an Opus Brain concentrating the firm's best ideas: universe =
                                  # union of published books (flagship, autonomous, etf; self_directed
                                  # excluded per ruling R1), one-per-cluster, 5–50% rails (bot/heavyweight.py)
        "manager": "brain",
        "starting_nav": 1_000_000.0,
        "benchmark": "SPY",
        "legacy": False,
        "active": False,
        "status": "archived",
        "superseded_by": "autonomous",
        "archived_reason": "redundant Flagship analogue; history remains read-only",
    },
    {
        "id": "autonomous",
        "name": "US Brain",
        "tagline": "Single-name US stocks · Codex-first AI · daily",
        "kind": "autonomous",     # shared-provider AI trades freely; no gate, no research paper
        "manager": "brain",
        "asset_policy": "single_name_equity_only",
        "starting_nav": 1_000_000.0,
        "benchmark": "SPY",
        "legacy": False,
        "active": True,
        "status": "active",
    },
    {
        "id": "etf",
        "name": "ETF Brain",
        "tagline": "US-listed ETFs only · Codex-first AI · daily · doctrine + guardrails",
        "kind": "etf_brain",      # shared-provider AI rotates across US ETFs (index/sector/factor/duration/
                                  # cash) under an ETF-adapted doctrine + hard risk guardrails (bot/etf.py).
                                  # The ETF-only allowlist is enforced in the trusted layer via
                                  # portfolio.etf_universe (not registry.venues — that gates market venue).
        "manager": "brain",
        "starting_nav": 1_000_000.0,
        "benchmark": "SPY",
        "legacy": False,
        "active": False,
        "status": "archived",
        "superseded_by": "autonomous",
        "archived_reason": "standalone ETF allocation mandate retired; history remains read-only",
    },
    {
        "id": "china",
        "name": "CN Brain",
        "tagline": "Mainland single-name A-shares · Codex-first AI · daily",
        "kind": "china_brain",    # shared-provider AI over the macro China A-share desks; holds
                                  # ONLY mainland A-shares (*.SS / *.SZ), marked natively in CNY (bot/china.py).
        "manager": "brain",
        "asset_policy": "single_name_equity_only",
        "starting_nav": 1_000_000.0,
        "benchmark": "000300.SS", # CSI 300 — broad Shanghai/Shenzhen A-share benchmark
        "benchmark_name": "CSI 300",
        "benchmark_name_zh": "沪深300",
        "currency": "CNY",        # base currency — A-shares quote CNY
        "venues": ["A-share"],    # tradeable universe: mainland A-shares (Shanghai / Shenzhen) only
        "legacy": False,
        "active": True,
        "status": "active",
    },
    {
        "id": "hk",
        "name": "HK Brain",
        "tagline": "Hong Kong single-name equities · Codex-first AI · daily",
        "kind": "hk_brain",       # shared-provider AI over the HK buy board; holds ONLY Hong-Kong
                                  # listed names (*.HK), marked natively in HKD (no cross-FX — bot/hk.py).
        "manager": "brain",
        "asset_policy": "single_name_equity_only",
        "starting_nav": 1_000_000.0,
        "benchmark": "^HSI",      # Hang Seng Index — native Hong Kong market benchmark
        "benchmark_name": "Hang Seng",
        "benchmark_name_zh": "恒生指数",
        "currency": "HKD",        # base currency — HK names quote HKD, so no cross-currency conversion
        "venues": ["HK"],         # tradeable universe: Hong Kong listings only
        "legacy": False,
        "active": True,
        "status": "active",
    },
    {
        "id": "self_directed",
        "name": "Self-Directed",
        "tagline": "Your book · you place the trades",
        "kind": "self_directed",  # YOU trade it by hand; served by portfolio.self_directed (its own
                                  # engine + state under data/portfolio/self_directed/, not paper_account)
        "manager": "you",
        "starting_nav": 1_000_000.0,
        "benchmark": "SPY",
        "legacy": False,
        "active": True,
        "status": "active",
    },
]

# Benchmark fallback for any portfolio missing an explicit one (back-compat: the US books).
_DEFAULT_BENCHMARK = "SPY"

_BY_ID = {p["id"]: p for p in PORTFOLIOS}

def canonical_id(portfolio_id: str | None = None) -> str:
    """Return the canonical id for a known book, or reject it before any filesystem use.

    ``None`` retains the legacy storage default.  All other values must be an exact registry id;
    aliases, whitespace, path-like values, and unknown ids fail closed.
    """
    candidate = DEFAULT_ID if portfolio_id is None else portfolio_id
    if type(candidate) is not str:
        raise ValueError(f"unknown portfolio id: {portfolio_id!r}")
    # Return literals rather than the caller's value.  Besides being fail-closed, this makes the
    # taint boundary obvious to static analysis and prevents a future path-normalisation shortcut.
    if candidate == "flagship":
        return "flagship"
    if candidate == "heavyweight":
        return "heavyweight"
    if candidate == "autonomous":
        return "autonomous"
    if candidate == "etf":
        return "etf"
    if candidate == "china":
        return "china"
    if candidate == "hk":
        return "hk"
    if candidate == "self_directed":
        return "self_directed"
    raise ValueError(f"unknown portfolio id: {portfolio_id!r}")


def _canonical_storage_id(portfolio_id: str | None = None) -> str:
    """Return a literal allowlisted storage id, including explicitly retained shadow storage."""
    if type(portfolio_id) is str and portfolio_id == "flagship_judgment":
        # Retired Flagship judgment submissions remain readable at their historical isolated path.
        # This is storage compatibility only; it is absent from PORTFOLIOS and never operational.
        return "flagship_judgment"
    return canonical_id(portfolio_id)


def ids() -> list[str]:
    return [p["id"] for p in PORTFOLIOS]


def all_portfolios() -> list[dict]:
    """A copy of the registry — safe to mutate by callers."""
    return [dict(p) for p in PORTFOLIOS]


def active_portfolios(*, include_self_directed: bool = True) -> list[dict]:
    """Active books only.

    Archived books deliberately stay in :func:`all_portfolios` so their historical NAV, trades,
    and decisions remain browseable. Operational code (schedulers, marking, settlement, exposure
    clamps) must opt into this active-only view instead.
    """
    return [
        dict(p) for p in PORTFOLIOS
        if bool(p.get("active", True))
        and (include_self_directed or p.get("id") != "self_directed")
    ]


def active_ids(*, include_self_directed: bool = True) -> list[str]:
    """Portfolio ids currently allowed to participate in operational work."""
    return [p["id"] for p in active_portfolios(include_self_directed=include_self_directed)]


def get(portfolio_id: str | None) -> dict:
    """Metadata for a portfolio (falls back to the default if unknown/None)."""
    return dict(_BY_ID.get(portfolio_id or DEFAULT_ID, _BY_ID[DEFAULT_ID]))


def is_known(portfolio_id: str | None) -> bool:
    return (portfolio_id or DEFAULT_ID) in _BY_ID


def is_active(portfolio_id: str | None) -> bool:
    """Whether a known portfolio may run, settle, mark, or enter current firm-risk math."""
    meta = _BY_ID.get(portfolio_id or DEFAULT_ID)
    return bool(meta and meta.get("active", True))


def is_archived(portfolio_id: str | None) -> bool:
    """Whether a known portfolio is retained for history but operationally disabled."""
    meta = _BY_ID.get(portfolio_id or DEFAULT_ID)
    return bool(meta and not meta.get("active", True))


def archived_run_result(portfolio_id: str, asof: str | None = None) -> dict:
    """Stable no-op payload for defense-in-depth runner guards.

    This helper performs no I/O. It lets direct Python/CLI entrypoints fail closed before clearing a
    submission, reading live feeds, acquiring model capacity, or mutating portfolio state.
    """
    meta = get(portfolio_id)
    return {
        "portfolio_id": meta["id"],
        "asof": asof,
        "active": False,
        "status": "archived",
        "archived": True,
        "skipped": "portfolio_archived",
        "superseded_by": meta.get("superseded_by"),
        "reason": meta.get("archived_reason") or "portfolio archived",
    }


def data_dir(portfolio_id: str | None = None) -> Path:
    """The per-portfolio state directory.

    ``flagship``/``None`` → the legacy ``data/portfolio/``; every other known book → its
    allowlisted directory under ``data/portfolios/``.  Unknown ids fail closed before a path is
    constructed.
    """
    pid = _canonical_storage_id(portfolio_id)
    # Every path component below is a source literal.  The caller-provided value never reaches a
    # filesystem expression, even after passing the exact-id allowlist above.
    if pid == "flagship":
        return _ROOT / "data" / "portfolio"
    if pid == "heavyweight":
        return _ROOT / "data" / "portfolios" / "heavyweight"
    if pid == "autonomous":
        return _ROOT / "data" / "portfolios" / "autonomous"
    if pid == "etf":
        return _ROOT / "data" / "portfolios" / "etf"
    if pid == "china":
        return _ROOT / "data" / "portfolios" / "china"
    if pid == "hk":
        return _ROOT / "data" / "portfolios" / "hk"
    if pid == "self_directed":
        return _ROOT / "data" / "portfolios" / "self_directed"
    if pid == "flagship_judgment":
        return _ROOT / "data" / "portfolios" / "flagship_judgment"
    raise AssertionError("canonical portfolio storage id has no path")  # pragma: no cover


def starting_nav(portfolio_id: str | None = None) -> float:
    return float(get(portfolio_id).get("starting_nav", 1_000_000.0))


def benchmark(portfolio_id: str | None = None) -> str:
    """The equity-curve comparison symbol for a book (default 'SPY' for the US books)."""
    return str(get(portfolio_id).get("benchmark") or _DEFAULT_BENCHMARK)


def benchmark_name(portfolio_id: str | None = None) -> str:
    """Human-readable benchmark label, falling back to the configured symbol."""
    meta = get(portfolio_id)
    return str(meta.get("benchmark_name") or meta.get("benchmark") or _DEFAULT_BENCHMARK)


def benchmark_name_zh(portfolio_id: str | None = None) -> str:
    """Chinese benchmark label, falling back to the English display name."""
    meta = get(portfolio_id)
    return str(meta.get("benchmark_name_zh") or benchmark_name(portfolio_id))


def currency(portfolio_id: str | None = None) -> str:
    """The book's base/display currency ('USD' default; 'HKD' for hk, 'CNY' for china)."""
    return str(get(portfolio_id).get("currency") or "USD")


def venues(portfolio_id: str | None = None) -> list[str]:
    """The venues a book may trade — e.g. ['HK'] or ['A-share']. Empty = unrestricted (US books)."""
    return list(get(portfolio_id).get("venues") or [])


def asset_policy(portfolio_id: str | None = None) -> str | None:
    """Return the exact registry-owned executable asset policy for a known book.

    Unlike :func:`get`, this authority lookup never falls back from an unknown id to Flagship.
    Callers at execution boundaries must not be able to opt an active AI book out of its mandate.
    """
    pid = canonical_id(portfolio_id)
    value = _BY_ID[pid].get("asset_policy")
    return str(value) if value else None


def requires_single_name_equity(portfolio_id: str | None = None) -> bool:
    """Whether positive single-name-equity identity is required before any BUY."""
    return asset_policy(portfolio_id) == "single_name_equity_only"
