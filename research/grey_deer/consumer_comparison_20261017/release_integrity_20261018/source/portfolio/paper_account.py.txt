"""$1,000,000 paper-trading account — persistent NAV, fills, equity curve.

PAPER ONLY — never executes real trades, never touches a broker.

State files (all in data/portfolio/):
  account.json      — inception_date, starting_nav, cash, positions, spy_shares
  fills.jsonl       — one JSON line per simulated fill
  nav_history.jsonl — one JSON line per mark() call (daily NAV snapshot)

Price sources:
  - Leadership sleeve ETFs + SPY: lib.store.read("yahoo", ticker)["close"]
  - Conviction single-name tickers: breadth/_closes_cache.parquet
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import fcntl
import threading
from copy import deepcopy
from contextlib import contextmanager
from datetime import UTC, date, datetime, timezone
from numbers import Real
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

import bot  # noqa: F401  -> vendor/macro onto sys.path

if TYPE_CHECKING:
    import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
_DATA = _ROOT / "data" / "portfolio"
_ACCOUNT_PATH = _DATA / "account.json"
_FILLS_PATH = _DATA / "fills.jsonl"
_NAV_PATH = _DATA / "nav_history.jsonl"
_PAPER_LOCK_STATE = threading.local()


def _pending_path() -> Path:
    """Pending-orders file, derived from `_DATA` at call time so tests that patch
    `_DATA` (without patching every path constant) still redirect it."""
    return _DATA / "pending_orders.json"

_STARTING_NAV = 1_000_000.0
_INCEPTION_DATE = date.today().isoformat()  # forward-realized track begins today


# ---------------------------------------------------------------------------
# No-trade band (rebalancing tolerance)
# ---------------------------------------------------------------------------
# A Brain book restates its FULL target book every run. When it re-states the same weight
# for a name it intends to HOLD, that weight — measured against a NAV/price that has drifted
# since the last mark — almost never equals the position's current value to the dollar, so a
# naive snap-to-target generates a tiny "rebalancing" trim/add the Brain never asked for
# (e.g. a 19.8-share sell out of 1007, ~2% of the line). Those de-minimis fills clutter the
# trade dashboard with confusing noise.
#
# The band fixes that: an incremental adjustment to a CONTINUING position (held before AND
# still in the target) is only executed when its notional clears this fraction of NAV; below
# it, the position is left untouched (drift accumulates against the live target each run, so a
# genuinely meaningful move still trades once it crosses the band — no unbounded drift). A
# brand-new entry and a full exit (name dropped from the target) ALWAYS execute — they are
# deliberate decisions, never de-minimis noise. Override via env for tuning.
def _no_trade_band_frac() -> float:
    try:
        return max(0.0, float(os.environ.get("MASTERMIND_NO_TRADE_BAND_FRAC", "0.01")))
    except (TypeError, ValueError):
        return 0.01


# ---------------------------------------------------------------------------
# Minimum trade size (dust filter)
# ---------------------------------------------------------------------------
# Sizing is purely `weight * NAV / price`, so a Brain that hands a name a sliver of a weight
# (a few bps) buys a sliver of a share — e.g. 0.4 shares of IWM (~$118) or 0.1 of HUBB. Those
# dust lines are pointless: they can't move the book, they clutter the blotter, and a fractional
# share count reads as broken. Two rules kill them, applied to every BUY in every book:
#   1. Whole shares — a buy is floored to an integer share count (no fractional dust). A-share
#      board lots (buy in 100s) are intentionally NOT enforced here: a high-priced name (a ¥1800
#      stock would need a >2% line to clear one lot) would be silently dropped, so whole-share +
#      the notional floor is the safe, currency-agnostic rule. (Revisit per-venue lots later.)
#   2. Notional floor — after flooring, a buy worth less than this fraction of NAV is skipped
#      entirely (the position is simply not opened / not topped up). Default 0.1% of NAV (~$1k on
#      a $1M book) — well under the 0.5% "small starter" the no-trade-band tests protect, so a
#      deliberate small open still goes through.
# Sells/exits are NEVER blocked — a dust line you already hold must always stay fully exitable.
# Both knobs override via env; set MASTERMIND_ALLOW_FRACTIONAL=1 to restore fractional sizing.
def _min_trade_frac() -> float:
    try:
        return max(0.0, float(os.environ.get("MASTERMIND_MIN_TRADE_FRAC", "0.001")))
    except (TypeError, ValueError):
        return 0.001


def _allow_fractional() -> bool:
    return os.environ.get("MASTERMIND_ALLOW_FRACTIONAL", "").strip().lower() in {"1", "true", "yes", "on"}


def _min_position_frac() -> float:
    """Smallest weight at which a BRAND-NEW position may be OPENED — a target below this isn't worth
    a book slot, so the name simply isn't opened. Names already HELD are exempt: this floor never
    force-closes a position (the Brain trims/exits those deliberately, and a name dropped from the
    target still fully exits). Stricter than the per-trade dust floor (_min_trade_frac): that one
    governs every trade incl. top-ups; this one governs new entries. Default 0.5% of NAV — the same
    threshold the no-trade-band treats as the smallest deliberate starter. Override via env."""
    try:
        return max(0.0, float(os.environ.get("MASTERMIND_MIN_POSITION_FRAC", "0.005")))
    except (TypeError, ValueError):
        return 0.005


def _quantize_buy_shares(shares: float) -> float:
    """Floor a desired BUY to whole shares (kill fractional dust) unless fractional sizing is
    explicitly re-enabled. Sells are not quantized — a held line must stay fully exitable."""
    import math
    if _allow_fractional() or shares <= 0:
        return max(0.0, float(shares))
    return float(math.floor(shares))


def _buyable_shares(shares: float, px: float, nav_now: float) -> float:
    """Tradable size for a BUY: whole-share quantized, then dust-filtered against the min
    notional (a fraction of NAV). Returns 0.0 when the trade is too small to bother with."""
    q = _quantize_buy_shares(shares)
    if q <= 0.0 or px <= 0.0:
        return 0.0
    if q * px < _min_trade_frac() * max(nav_now, 0.0):
        return 0.0
    return q


def _persisted_positive_number(value: float, digits: int) -> float:
    """Round ordinary fill facts compactly without collapsing a real dust exit to zero."""
    raw = float(value)
    rounded = round(raw, digits)
    if rounded > 0.0:
        return rounded
    precise = round(raw, 12)
    return precise if precise > 0.0 else raw


def _persisted_fill_facts(shares: float, price: float, value: float) -> dict[str, float]:
    """Canonical display precision with positive sub-cent/sub-quantum exits preserved exactly."""
    return {
        "shares": _persisted_positive_number(shares, 6),
        "price": _persisted_positive_number(price, 4),
        "value": _persisted_positive_number(value, 2),
    }


# ---------------------------------------------------------------------------
# multi-portfolio path resolution
# ---------------------------------------------------------------------------
# Mastermind now harnesses several independent books. Every public operation takes an
# optional `portfolio_id`: None or the default ('flagship') resolves to the legacy
# module-global path constants (kept patchable so the existing test fixtures that
# monkeypatch _DATA/_ACCOUNT_PATH/_FILLS_PATH/_NAV_PATH still redirect the store);
# any other id resolves to a per-id subdir under data/portfolios/<id>/ via the registry.

def _paths(portfolio_id: str | None = None) -> dict[str, Path]:
    from portfolio import registry
    if not portfolio_id or portfolio_id == registry.DEFAULT_ID:
        return {"data": _DATA, "account": _ACCOUNT_PATH, "fills": _FILLS_PATH,
                "nav": _NAV_PATH, "pending": _pending_path()}
    base = registry.data_dir(portfolio_id)
    return {"data": base, "account": base / "account.json", "fills": base / "fills.jsonl",
            "nav": base / "nav_history.jsonl", "pending": base / "pending_orders.json"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ensure_dir(portfolio_id: str | None = None) -> None:
    _paths(portfolio_id)["data"].mkdir(parents=True, exist_ok=True)


def _load_account(portfolio_id: str | None = None) -> dict[str, Any]:
    """Load account state, first completing any recoverable paper transaction.

    A write-ahead transaction is deliberately not ignored: returning an account while its fill
    ledger is known to be incomplete would make an execution failure look like an ordinary settled
    book.  Recovery is idempotent; a genuine conflict raises and leaves the artifact for inspection.
    """
    with _paper_transaction_lock(portfolio_id):
        if _transaction_path(portfolio_id).exists():
            _recover_paper_transaction_unlocked(portfolio_id)
        return _load_account_file(portfolio_id)


def _fresh_account() -> dict[str, Any]:
    return {
        "inception_date": _INCEPTION_DATE,
        "starting_nav": _STARTING_NAV,
        "cash": _STARTING_NAV,
        "positions": {},          # TICKER -> {shares, avg_cost}
        "spy_shares": None,       # set on first mark()
        "spy_inception_price": None,
    }


def _load_account_file(portfolio_id: str | None = None, *, strict: bool = False) -> dict[str, Any]:
    """Read account.json without invoking transaction recovery.

    ``strict`` is used by replay: a corrupt on-disk account must never be mistaken for a fresh book
    and overwritten by a prepared transaction.
    """
    _account_path = _paths(portfolio_id)["account"]
    try:
        if _account_path.exists():
            raw = json.loads(_account_path.read_text())
            # basic schema validation
            if (
                isinstance(raw.get("cash"), (int, float))
                and isinstance(raw.get("positions"), dict)
                and raw.get("starting_nav")
            ):
                return raw
            if strict:
                raise PaperTransactionConflict("account schema is invalid during transaction recovery")
    except PaperTransactionConflict:
        raise
    except Exception as exc:
        if strict:
            raise PaperTransactionConflict(
                f"account cannot be read during transaction recovery: {exc!r}"
            ) from exc
    return _fresh_account()


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Durably replace one runtime-state file without exposing a partial JSON document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with tmp.open("wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            # Some filesystems do not permit directory fsync.  The atomic replace still holds.
            pass
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _durable_unlink(path: Path) -> None:
    """Remove one runtime-state file and durably publish the directory change."""
    try:
        path.unlink()
    except FileNotFoundError:
        return
    try:
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        # Match atomic replacement: unlink is complete even where directory fsync is unsupported.
        pass


def _save_account(state: dict[str, Any], portfolio_id: str | None = None) -> None:
    _ensure_dir(portfolio_id)
    _atomic_write_bytes(
        _paths(portfolio_id)["account"],
        json.dumps(state, indent=2, default=str).encode("utf-8"),
    )


# --------------------------------------------------------------------------- #
# cash sweep — idle cash earns a money-market yield, so a Brain that holds cash
# for lack of conviction is REWARDED (~4%/yr), not penalized vs a fully-invested
# benchmark. Incentivizes discipline over forced marginal buys.
# --------------------------------------------------------------------------- #
_CASH_YIELD_DEFAULT = 0.04            # 4% annualized money-market sweep
_TRADING_DAYS = 252


def _cash_yield_rate() -> float:
    """Annual cash-sweep rate; tunable via env CASH_YIELD_ANNUAL (default 4%)."""
    try:
        return float(os.environ.get("CASH_YIELD_ANNUAL", _CASH_YIELD_DEFAULT))
    except (TypeError, ValueError):
        return _CASH_YIELD_DEFAULT


def accrue_cash_yield(asof: str, portfolio_id: str | None = None,
                      annual_rate: float | None = None) -> float:
    """Accrue ONE trading-day of money-market yield to the cash balance, IDEMPOTENT per
    (book, calendar date): a re-run on the same ``asof`` is a no-op (no double-accrual). Best-effort;
    never raises. Returns the (possibly grown) cash balance. Call once per trading day, before
    ``mark()`` — the daily mark job (Mon-Fri) supplies the ~252 accruals/yr the rate/252 step
    assumes. Only the cash value changes; ``mark()``'s idempotent nav_history write is untouched."""
    rate = _cash_yield_rate() if annual_rate is None else float(annual_rate)
    try:
        with _paper_transaction_lock(portfolio_id):
            state = _load_account(portfolio_id)
            cash = float(state.get("cash") or 0.0)
            # A committed settlement receipt owns the exact post-transaction cash until all
            # projections are durable. Accrual waits rather than changing the dated NAV preimage.
            if pending_settlement_receipts(portfolio_id):
                return round(cash, 2)
            if state.get("cash_yield_through") == asof or cash <= 0 or rate <= 0:
                return round(cash, 2)
            cash = round(cash * (1.0 + rate / _TRADING_DAYS), 2)
            state["cash"] = cash
            state["cash_yield_through"] = asof
            _save_account(state, portfolio_id)
            return cash
    except Exception:  # noqa: BLE001 — the sweep is additive; never break a build/mark
        try:
            return round(float(_load_account(portfolio_id).get("cash") or 0.0), 2)
        except Exception:  # noqa: BLE001
            return 0.0


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    created = not path.exists()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    if created:
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            # The appended row is durable even where the filesystem rejects directory fsync.
            pass


def _load_jsonl(path: Path) -> list[dict]:
    """Load all lines from a JSONL file; skip corrupt lines."""
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


# ---------------------------------------------------------------------------
# recoverable paper transaction boundary
# ---------------------------------------------------------------------------
# account.json and fills.jsonl cannot be replaced in one filesystem operation.  A durable
# write-ahead artifact therefore describes the complete transition before either file changes.
# The account carries the transaction id and every fill carries a deterministic fill id.  Replay
# can then distinguish "not started", "account applied", and "some/all fills appended" without
# guessing or booking a duplicate fill.  The artifact is removed only after account, fills, and the
# exact pending target (when settlement supplied one) have all reached their committed state.
PAPER_TRANSACTION_SCHEMA = "paper_transaction.v1"
PAPER_SETTLEMENT_RECEIPT_SCHEMA = "paper_settlement_receipt.v2"
# Fill shares are persisted to six decimal places while the authoritative account snapshot keeps
# the engine's full-precision float.  Each persisted fill can therefore explain at most half one
# share quantum of representation drift; receipt validation must never use an unbounded relative
# tolerance that grows with position size.
_PERSISTED_FILL_SHARE_QUANTUM = 0.000001


class PaperTransactionConflict(RuntimeError):
    """Prepared paper state cannot be replayed without overwriting unrelated runtime state."""


def _transaction_path(portfolio_id: str | None = None) -> Path:
    return _paths(portfolio_id)["data"] / "paper_transaction.json"


def _settlement_receipt_dir(portfolio_id: str | None = None) -> Path:
    return _paths(portfolio_id)["data"] / "settlement_receipts"


def _settlement_receipt_path(
    transaction_id: str,
    portfolio_id: str | None = None,
) -> Path:
    return _settlement_receipt_dir(portfolio_id) / f"{transaction_id}.json"


@contextmanager
def _paper_transaction_lock(portfolio_id: str | None = None):
    """Serialize one book across processes, while allowing same-thread nested boundaries."""
    path = _paths(portfolio_id)["data"] / ".paper_transaction.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    key = str(path.resolve())
    depths = getattr(_PAPER_LOCK_STATE, "depths", None)
    if depths is None:
        depths = {}
        _PAPER_LOCK_STATE.depths = depths
    if depths.get(key, 0):
        depths[key] += 1
        try:
            yield
        finally:
            depths[key] -= 1
        return
    with path.open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        depths[key] = 1
        try:
            yield
        finally:
            depths.pop(key, None)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def _content_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def _write_transaction(payload: dict[str, Any], portfolio_id: str | None = None) -> None:
    _atomic_write_bytes(
        _transaction_path(portfolio_id),
        json.dumps(payload, indent=2, default=str).encode("utf-8"),
    )


def _load_transaction(portfolio_id: str | None = None) -> dict[str, Any] | None:
    path = _transaction_path(portfolio_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PaperTransactionConflict(f"paper transaction artifact is unreadable: {exc!r}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != PAPER_TRANSACTION_SCHEMA:
        raise PaperTransactionConflict("paper transaction artifact has an unknown schema")
    return payload


def _repair_partial_jsonl_tail(path: Path) -> None:
    """Remove only a provably incomplete final JSONL fragment left by an interrupted append.

    Complete legacy rows (including a valid last row without a newline) are preserved.  A malformed
    tail is copied to a recovery artifact before the ledger is atomically repaired.
    """
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return
    if not raw or raw.endswith(b"\n"):
        return
    split_at = raw.rfind(b"\n") + 1
    tail = raw[split_at:]
    try:
        json.loads(tail.decode("utf-8"))
    except Exception:
        recovery = path.with_name(
            f"{path.name}.partial.{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
        )
        _atomic_write_bytes(recovery, tail)
        _atomic_write_bytes(path, raw[:split_at])
        return
    _atomic_write_bytes(path, raw + b"\n")


def _pending_clear_transition(
    portfolio_id: str | None = None,
    *,
    prices: dict[str, float] | None = None,
    price_sources: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Capture the exact queued target that a successful settlement is allowed to remove."""
    path = _pending_target_path(portfolio_id)
    pending_payload = _read_pending_target_payload(portfolio_id)
    settlement_prices = {
        str(ticker).upper().strip(): float(price)
        for ticker, price in (prices or {}).items()
        if (
            isinstance(ticker, str)
            and ticker.strip()
            and isinstance(price, Real)
            and not isinstance(price, bool)
            and math.isfinite(float(price))
            and float(price) > 0.0
        )
    }
    transition = {
        "kind": "clear_pending_target",
        "filename": path.name,
        "before_sha256": _file_sha256(path),
        # This is the accepted executable instruction, including its hash-bound structured PM
        # decision.  It becomes the recovery outbox if account/fill commit outlives the caller.
        "pending_payload": deepcopy(pending_payload),
        "settlement_prices": settlement_prices,
    }
    if price_sources:
        transition["settlement_price_sources"] = {
            ticker: str(price_sources.get(ticker) or "settlement_snapshot")
            for ticker in settlement_prices
        }
    return transition


def _write_settlement_receipt(
    transaction: dict[str, Any],
    portfolio_id: str | None = None,
) -> dict[str, Any] | None:
    """Durably publish one committed target settlement before its WAL can disappear."""
    transition = transaction.get("followup")
    if not isinstance(transition, dict) or transition.get("kind") != "clear_pending_target":
        return None
    pending = transition.get("pending_payload")
    if not isinstance(pending, dict) or not isinstance(pending.get("target"), dict):
        raise PaperTransactionConflict("settlement transaction lacks its queued target provenance")
    target = validate_target_weights(
        pending.get("target"),
        require_canonical_tickers=True,
        portfolio_id=portfolio_id,
    )
    constraints = _validated_execution_constraints(
        pending.get("execution_constraints")
        if "execution_constraints" in pending
        else None,
        target=target,
        decision_snapshot=pending.get("decision_snapshot"),
        portfolio_id=portfolio_id,
    )
    transaction_id = str(transaction.get("transaction_id") or "")
    if len(transaction_id) != 64 or any(ch not in "0123456789abcdef" for ch in transaction_id):
        raise PaperTransactionConflict("settlement transaction id is invalid")
    fills = [
        deepcopy(entry.get("record"))
        for entry in (transaction.get("fills") or [])
        if isinstance(entry, dict) and isinstance(entry.get("record"), dict)
    ]
    identity = transaction.get("identity")
    if not isinstance(identity, dict) or _content_sha256(identity) != transaction_id:
        raise PaperTransactionConflict("settlement transaction identity preimage is invalid")
    account_before = transaction.get("account_before")
    if (
        not isinstance(account_before, dict)
        or identity.get("account_before_sha256") != _content_sha256(account_before)
    ):
        raise PaperTransactionConflict("settlement transaction before-state preimage is invalid")
    receipt = {
        "schema": PAPER_SETTLEMENT_RECEIPT_SCHEMA,
        "transaction_id": transaction_id,
        "portfolio_id": str(portfolio_id or "flagship"),
        "settlement_asof": transaction.get("asof"),
        # Stable across replay attempts; wall-clock freshness belongs to the caller's finalization
        # event, while the receipt itself must be byte-comparable for idempotent recovery.
        "committed_at": transaction.get("prepared_at") or transaction.get("asof"),
        "pending_target_sha256": transition.get("before_sha256"),
        "target_sha256": _target_sha256(target),
        "target": target,
        "decision_snapshot": deepcopy(pending.get("decision_snapshot")),
        "queued_asof": pending.get("asof"),
        "fills": fills,
        # The transaction id is the external anchor: account.json retains it even for zero-fill
        # target settlements.  Keeping the exact preimage here lets recovery detect any change to
        # captured prices, cash, positions, target, or fills rather than trusting a self-rehash.
        "transaction_identity": deepcopy(identity),
        "account_before": deepcopy(account_before),
        "account_before_positions": deepcopy(
            (transaction.get("account_before") or {}).get("positions") or {}
        ),
        "account_after_positions": deepcopy(
            (transaction.get("account_after") or {}).get("positions") or {}
        ),
        "settlement_prices": deepcopy(transition.get("settlement_prices") or {}),
        "settlement_price_sources": deepcopy(
            transition.get("settlement_price_sources") or {}
        ),
    }
    if constraints is not None:
        receipt["execution_constraints"] = deepcopy(constraints)
    path = _settlement_receipt_path(transaction_id, portfolio_id)
    encoded = json.dumps(receipt, indent=2, default=str).encode("utf-8")
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PaperTransactionConflict(
                f"settlement receipt is unreadable: {exc!r}"
            ) from exc
        if _content_sha256(existing) != _content_sha256(receipt):
            raise PaperTransactionConflict("settlement receipt conflicts with recovered WAL")
        return existing
    _atomic_write_bytes(path, encoded)
    return receipt


def validated_settlement_receipt_fills(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    """Return fills only when IDs, date, and the committed account transition all agree.

    A deterministic fill id proves only that a row is internally self-consistent; it is not a
    signature.  Bind the complete signed share flow back to the receipt's immutable before/after
    account snapshots so a changed-and-re-ID'd row, omitted fill, or unexplained position mutation
    cannot become settlement authority.
    """
    transaction_id = str(receipt.get("transaction_id") or "")
    fills = receipt.get("fills")
    settlement_asof = receipt.get("settlement_asof")
    if (
        len(transaction_id) != 64
        or any(ch not in "0123456789abcdef" for ch in transaction_id)
        or not isinstance(fills, list)
        or not isinstance(settlement_asof, str)
    ):
        raise PaperTransactionConflict("settlement receipt fill lineage is invalid")
    identity = receipt.get("transaction_identity")
    account_before = receipt.get("account_before")
    if (
        not isinstance(identity, dict)
        or _content_sha256(identity) != transaction_id
        or identity.get("schema") != PAPER_TRANSACTION_SCHEMA
        or identity.get("portfolio_id") != receipt.get("portfolio_id")
        or identity.get("asof") != settlement_asof
        or not isinstance(account_before, dict)
        or identity.get("account_before_sha256") != _content_sha256(account_before)
    ):
        raise PaperTransactionConflict("settlement receipt transaction preimage is invalid")
    identity_after = identity.get("account_after")
    identity_fills = identity.get("fills")
    identity_followup = identity.get("followup")
    if (
        not isinstance(identity_after, dict)
        or not isinstance(identity_fills, list)
        or not isinstance(identity_followup, dict)
        or identity_followup.get("kind") != "clear_pending_target"
    ):
        raise PaperTransactionConflict("settlement receipt transaction preimage is invalid")
    pending_payload = identity_followup.get("pending_payload")
    if not isinstance(pending_payload, dict):
        raise PaperTransactionConflict("settlement receipt transaction preimage is invalid")
    if (
        receipt.get("pending_target_sha256") != identity_followup.get("before_sha256")
        or receipt.get("target") != pending_payload.get("target")
        or receipt.get("decision_snapshot") != pending_payload.get("decision_snapshot")
        or receipt.get("queued_asof") != pending_payload.get("asof")
        or receipt.get("settlement_prices") != identity_followup.get("settlement_prices")
        or receipt.get("settlement_price_sources")
        != (identity_followup.get("settlement_price_sources") or {})
        or receipt.get("account_before_positions") != (account_before.get("positions") or {})
        or receipt.get("account_after_positions") != (identity_after.get("positions") or {})
    ):
        raise PaperTransactionConflict("settlement receipt bound preimage fields disagree")
    unsigned_fills = [
        {
            key: value
            for key, value in fill.items()
            if key not in {"fill_id", "transaction_id"}
        }
        for fill in fills
        if isinstance(fill, dict)
    ]
    if unsigned_fills != identity_fills:
        raise PaperTransactionConflict("settlement receipt fill preimage disagrees")
    try:
        canonical_settlement_asof = date.fromisoformat(settlement_asof).isoformat()
    except ValueError as exc:
        raise PaperTransactionConflict(
            "settlement receipt fill date lineage is invalid"
        ) from exc
    if settlement_asof != canonical_settlement_asof:
        raise PaperTransactionConflict("settlement receipt fill date lineage is invalid")

    def _snapshot_shares(field: str) -> dict[str, float]:
        snapshot = receipt.get(field)
        if not isinstance(snapshot, dict):
            raise PaperTransactionConflict(
                "settlement receipt position lineage is invalid"
            )
        shares_by_ticker: dict[str, float] = {}
        for raw_ticker, raw_position in snapshot.items():
            ticker = _canonical_target_ticker(raw_ticker)
            if (
                not ticker
                or raw_ticker != ticker
                or not isinstance(raw_position, dict)
            ):
                raise PaperTransactionConflict(
                    "settlement receipt position lineage is invalid"
                )
            raw_shares = raw_position.get("shares")
            if not isinstance(raw_shares, Real) or isinstance(raw_shares, bool):
                raise PaperTransactionConflict(
                    "settlement receipt position lineage is invalid"
                )
            shares = float(raw_shares)
            if not math.isfinite(shares) or shares < 0.0:
                raise PaperTransactionConflict(
                    "settlement receipt position lineage is invalid"
                )
            shares_by_ticker[ticker] = shares
        return shares_by_ticker

    before_shares = _snapshot_shares("account_before_positions")
    after_shares = _snapshot_shares("account_after_positions")
    raw_before_cash = account_before.get("cash")
    raw_after_cash = identity_after.get("cash")
    if (
        not isinstance(raw_before_cash, Real)
        or isinstance(raw_before_cash, bool)
        or not isinstance(raw_after_cash, Real)
        or isinstance(raw_after_cash, bool)
        or not math.isfinite(float(raw_before_cash))
        or not math.isfinite(float(raw_after_cash))
        or float(raw_before_cash) < 0.0
        or float(raw_after_cash) < 0.0
    ):
        raise PaperTransactionConflict("settlement receipt cash lineage is invalid")
    validated: list[dict[str, Any]] = []
    seen: set[str] = set()
    signed_fill_shares: dict[str, float] = {}
    fill_counts: dict[str, int] = {}
    signed_fill_cash = 0.0
    for index, record in enumerate(fills):
        if not isinstance(record, dict):
            raise PaperTransactionConflict("settlement receipt contains a malformed fill")
        ticker = _canonical_target_ticker(record.get("ticker"))
        side = str(record.get("side") or "").lower().strip()
        if not ticker or record.get("ticker") != ticker or side not in {"buy", "sell"}:
            raise PaperTransactionConflict("settlement receipt fill instrument is invalid")
        if record.get("date") != canonical_settlement_asof:
            raise PaperTransactionConflict(
                "settlement receipt fill date does not match settlement"
            )
        numeric: dict[str, float] = {}
        for key in ("shares", "price", "value"):
            raw = record.get(key)
            if not isinstance(raw, Real) or isinstance(raw, bool):
                raise PaperTransactionConflict("settlement receipt fill facts are invalid")
            value = float(raw)
            if not math.isfinite(value) or value <= 0.0:
                raise PaperTransactionConflict("settlement receipt fill facts are invalid")
            numeric[key] = value
        # The engine persists shares to 6dp, price to 4dp, and value to cents.  Independent
        # rounding can move their displayed product by roughly shares*0.00005 plus
        # price*0.0000005; tolerate only that mathematically bounded representation error.
        rounding_bound = (
            numeric["shares"] * 0.00005
            + numeric["price"] * 0.0000005
            + 0.005
        )
        if abs(numeric["shares"] * numeric["price"] - numeric["value"]) > (
            rounding_bound + 1e-9
        ):
            raise PaperTransactionConflict("settlement receipt fill value is inconsistent")
        if record.get("transaction_id") != transaction_id:
            raise PaperTransactionConflict("settlement receipt fill transaction is invalid")
        fill_id = str(record.get("fill_id") or "")
        expected_id = hashlib.sha256(
            _canonical_json_bytes({
                "transaction_id": transaction_id,
                "index": index,
                "fill": {
                    key: value
                    for key, value in record.items()
                    if key not in {"fill_id", "transaction_id"}
                },
            })
        ).hexdigest()
        if fill_id != expected_id or fill_id in seen:
            raise PaperTransactionConflict("settlement receipt deterministic fill id is invalid")
        seen.add(fill_id)
        signed_fill_shares[ticker] = signed_fill_shares.get(ticker, 0.0) + (
            numeric["shares"] if side == "buy" else -numeric["shares"]
        )
        signed_fill_cash += numeric["value"] if side == "sell" else -numeric["value"]
        fill_counts[ticker] = fill_counts.get(ticker, 0) + 1
        validated.append(deepcopy(record))

    for ticker in sorted(
        set(before_shares) | set(after_shares) | set(signed_fill_shares)
    ):
        account_delta = after_shares.get(ticker, 0.0) - before_shares.get(ticker, 0.0)
        persisted_fill_delta = signed_fill_shares.get(ticker, 0.0)
        # Summing N independently rounded 6dp fills permits at most N half-quanta of absolute
        # drift.  The fixed epsilon covers binary-float arithmetic; it never scales with shares.
        tolerance = (
            fill_counts.get(ticker, 0) * _PERSISTED_FILL_SHARE_QUANTUM / 2.0
            + 1e-9
        )
        if abs(account_delta - persisted_fill_delta) > tolerance:
            raise PaperTransactionConflict(
                f"settlement receipt fills do not explain account share delta: {ticker}"
            )
    # Each fill value is persisted to cents, so aggregate cash can differ from the engine's
    # unrounded internal values by at most half a cent per fill.
    cash_delta = float(raw_after_cash) - float(raw_before_cash)
    cash_tolerance = len(validated) * 0.005 + 1e-8
    if abs(cash_delta - signed_fill_cash) > cash_tolerance:
        raise PaperTransactionConflict(
            "settlement receipt fills do not explain account cash delta"
        )
    return validated


def _canonical_settlement_price_symbol(value: Any) -> str:
    """Canonical executable/benchmark symbol accepted in settlement price evidence."""
    if not isinstance(value, str):
        return ""
    symbol = value.upper().strip()
    if symbol.startswith("^"):
        tail = symbol[1:]
        if tail and len(symbol) <= 16 and all(
            char.isalnum() or char in ".-" for char in tail
        ):
            return symbol
        return ""
    return _canonical_target_ticker(value)


def validated_settlement_receipt_prices(
    receipt: dict[str, Any],
) -> dict[str, float]:
    """Return exact settlement marks only when coverage and immutable fill prices agree."""
    raw_prices = receipt.get("settlement_prices")
    if not isinstance(raw_prices, dict):
        raise PaperTransactionConflict(
            "settlement receipt price evidence is invalid"
        )
    prices: dict[str, float] = {}
    for raw_symbol, raw_price in raw_prices.items():
        symbol = _canonical_settlement_price_symbol(raw_symbol)
        if not symbol or raw_symbol != symbol:
            raise PaperTransactionConflict(
                "settlement receipt price symbol is noncanonical"
            )
        if not isinstance(raw_price, Real) or isinstance(raw_price, bool):
            raise PaperTransactionConflict(
                "settlement receipt price evidence is invalid"
            )
        price = float(raw_price)
        if not math.isfinite(price) or price <= 0.0:
            raise PaperTransactionConflict(
                "settlement receipt price evidence is invalid"
            )
        prices[symbol] = price

    target = validate_target_weights(
        receipt.get("target"),
        require_canonical_tickers=True,
        portfolio_id=str(receipt.get("portfolio_id") or "flagship"),
    )
    required = set(target)
    for field in ("account_before_positions", "account_after_positions"):
        snapshot = receipt.get(field)
        if not isinstance(snapshot, dict):
            raise PaperTransactionConflict(
                "settlement receipt position lineage is invalid"
            )
        required.update(snapshot)
    from portfolio import registry
    required.add(registry.benchmark(str(receipt.get("portfolio_id") or "flagship")))
    missing = sorted(required - set(prices))
    if missing:
        raise PaperTransactionConflict(
            "settlement receipt price coverage is incomplete: " + ",".join(missing)
        )

    fills = validated_settlement_receipt_fills(receipt)
    for fill in fills:
        ticker = str(fill["ticker"])
        fill_price = float(fill["price"])
        # Fills persist the session price at 4dp while the captured mark may retain more digits.
        if abs(prices[ticker] - fill_price) > 0.00005 + 1e-12:
            raise PaperTransactionConflict(
                f"settlement receipt price contradicts fill: {ticker}"
            )
    return prices


def settlement_receipt_fills_are_durable(
    receipt: dict[str, Any],
    portfolio_id: str | None = None,
) -> bool:
    """Prove every receipt fill is present byte-for-value in the durable trade blotter.

    The account transition, public positions, and decision log must never advance past a receipt
    whose fill rows are absent or changed in ``fills.jsonl``.  Legacy rows without deterministic
    IDs remain readable, but malformed JSON and duplicate/conflicting receipt IDs fail closed.
    """
    expected = validated_settlement_receipt_fills(receipt)
    if not expected:
        return True
    path = _paths(portfolio_id)["fills"]
    if not path.exists():
        raise PaperTransactionConflict("settlement receipt fills are absent from trade history")
    observed: dict[str, dict[str, Any]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        raise PaperTransactionConflict("settlement trade history is unreadable") from exc
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception as exc:
            raise PaperTransactionConflict("settlement trade history is malformed") from exc
        if not isinstance(row, dict):
            raise PaperTransactionConflict("settlement trade history contains a non-object row")
        fill_id = row.get("fill_id")
        if fill_id is None:
            continue
        if not isinstance(fill_id, str) or fill_id in observed:
            raise PaperTransactionConflict("settlement trade history fill identity is invalid")
        observed[fill_id] = row
    for fill in expected:
        durable = observed.get(fill["fill_id"])
        if durable != fill:
            raise PaperTransactionConflict(
                "settlement receipt fill is absent or differs in trade history"
            )
    return True


def pending_settlement_receipts(portfolio_id: str | None = None) -> list[dict[str, Any]]:
    """Validated, oldest-first committed-settlement outbox rows awaiting finalization."""
    root = _settlement_receipt_dir(portfolio_id)
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PaperTransactionConflict(
                f"settlement receipt {path.name} is unreadable: {exc!r}"
            ) from exc
        transaction_id = str(row.get("transaction_id") or "")
        if (
            row.get("schema") != PAPER_SETTLEMENT_RECEIPT_SCHEMA
            or row.get("portfolio_id") != str(portfolio_id or "flagship")
            or path.name != f"{transaction_id}.json"
        ):
            raise PaperTransactionConflict("settlement receipt identity is invalid")
        target = validate_target_weights(
            row.get("target"),
            require_canonical_tickers=True,
            portfolio_id=portfolio_id,
        )
        _validated_execution_constraints(
            row.get("execution_constraints")
            if "execution_constraints" in row
            else None,
            target=target,
            decision_snapshot=row.get("decision_snapshot"),
            portfolio_id=portfolio_id,
        )
        if row.get("target_sha256") != _target_sha256(target):
            raise PaperTransactionConflict("settlement receipt target digest mismatch")
        validated_settlement_receipt_fills(row)
        validated_settlement_receipt_prices(row)
        rows.append(row)
    rows.sort(key=lambda row: (str(row.get("committed_at") or ""), row["transaction_id"]))
    return rows


def acknowledge_settlement_receipt(
    transaction_id: str,
    portfolio_id: str | None = None,
) -> bool:
    """Acknowledge only the exact committed receipt after mark/publish finalization."""
    value = str(transaction_id or "")
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError("invalid settlement receipt transaction id")
    path = _settlement_receipt_path(value, portfolio_id)
    if not path.exists():
        return False
    _durable_unlink(path)
    return True


def _pending_orders_transition(
    orders_after: list[dict[str, Any]],
    portfolio_id: str | None = None,
) -> dict[str, Any]:
    path = _paths(portfolio_id)["pending"]
    return {
        "kind": "replace_pending_orders",
        "filename": path.name,
        "before_sha256": _file_sha256(path),
        "after_orders": deepcopy(orders_after),
        "after_sha256": hashlib.sha256(
            json.dumps(orders_after, indent=2, default=str).encode("utf-8")
        ).hexdigest(),
    }


def _apply_transaction_followup(
    transaction: dict[str, Any],
    portfolio_id: str | None = None,
) -> None:
    transition = transaction.get("followup")
    if not isinstance(transition, dict):
        return
    kind = transition.get("kind")
    if kind not in {"clear_pending_target", "replace_pending_orders"}:
        raise PaperTransactionConflict("paper transaction contains an unknown follow-up")
    path = (
        _pending_target_path(portfolio_id)
        if kind == "clear_pending_target"
        else _paths(portfolio_id)["pending"]
    )
    if transition.get("filename") != path.name:
        raise PaperTransactionConflict("paper transaction follow-up path is invalid")
    expected = transition.get("before_sha256")
    observed = _file_sha256(path)
    if kind == "replace_pending_orders":
        orders_after = transition.get("after_orders")
        if not isinstance(orders_after, list):
            raise PaperTransactionConflict("paper transaction pending-order payload is invalid")
        if observed == transition.get("after_sha256"):
            return
        if observed != expected:
            # A newer queue has already superseded the orders this transaction consumed.
            return
        _save_pending(orders_after, portfolio_id)
        return

    if observed is None:
        return
    if observed != expected:
        # A newer complete target superseded the one this transaction settled.  It must remain
        # executable; completion of the older transaction is not authority to delete it.
        return
    clear_pending_target(portfolio_id)


def _position_shares_for_mandate(state: dict[str, Any], ticker: str) -> float:
    lot = (state.get("positions") or {}).get(ticker)
    if not isinstance(lot, dict):
        return 0.0
    try:
        shares = float(lot.get("shares") or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return shares if math.isfinite(shares) and shares > 0.0 else 0.0


def _validate_stock_only_transaction_mandate(
    transaction: dict[str, Any],
    *,
    portfolio_id: str,
    before: dict[str, Any],
    after: dict[str, Any],
    fills: list[Any],
) -> None:
    """Reject a legacy/malformed AI-book WAL before it can mutate paper state.

    A WAL is executable authority.  After the common-stock-only cutover, replay must enforce the
    same mandate as a fresh rebalance instead of applying a pre-upgrade ETF buy and discovering the
    violation only while writing its receipt.  Existing ETF lots may remain unchanged or decrease;
    any increase and every recorded BUY require positive common-stock identity.
    """
    from portfolio import instrument_policy

    transition = transaction.get("followup")
    preserved: frozenset[str] = frozenset()
    constrained_positions_sha256: str | None = None
    if isinstance(transition, dict) and transition.get("kind") == "clear_pending_target":
        pending = transition.get("pending_payload")
        incompatibility = pending_target_contract_error(pending, portfolio_id)
        if incompatibility:
            raise PaperTransactionConflict(
                f"{portfolio_id} WAL pending target violates mandate: {incompatibility}"
            )
        constraints = (
            pending.get("execution_constraints")
            if isinstance(pending, dict) and "execution_constraints" in pending
            else None
        )
        if isinstance(constraints, dict):
            preserved = frozenset(constraints.get("tickers") or [])
            constrained_positions_sha256 = constraints.get("positions_sha256")

    if constrained_positions_sha256 is not None:
        try:
            before_positions_sha256 = positions_sha256(before.get("positions"))
        except InvalidExecutionConstraints as exc:
            raise PaperTransactionConflict(
                f"{portfolio_id} WAL positions snapshot is invalid: {exc.reason}"
            ) from exc
        if before_positions_sha256 != constrained_positions_sha256:
            raise PaperTransactionConflict(
                f"{portfolio_id} WAL positions snapshot violates migration authority"
            )

    for entry in fills:
        if not isinstance(entry, dict) or not isinstance(entry.get("record"), dict):
            raise PaperTransactionConflict("autonomous WAL contains a malformed fill entry")
        record = entry["record"]
        ticker = _canonical_target_ticker(record.get("ticker"))
        if not ticker or record.get("ticker") != ticker:
            raise PaperTransactionConflict("autonomous WAL contains a noncanonical fill ticker")
        side = str(record.get("side") or "").lower().strip()
        if side not in {"buy", "sell"}:
            raise PaperTransactionConflict("autonomous WAL contains an invalid fill side")
        if side == "buy":
            identity_error = instrument_policy.executable_equity_error(
                portfolio_id, ticker
            )
            if identity_error:
                raise PaperTransactionConflict(
                    f"{portfolio_id} WAL BUY violates mandate: {identity_error}"
                )
        if ticker in preserved:
            raise PaperTransactionConflict(
                f"autonomous WAL trades preserved position: {ticker}"
            )
    before_positions = before.get("positions") or {}
    after_positions = after.get("positions") or {}
    if not isinstance(before_positions, dict) or not isinstance(after_positions, dict):
        raise PaperTransactionConflict("autonomous WAL position state is invalid")
    for raw_ticker in set(before_positions) | set(after_positions):
        ticker = _canonical_target_ticker(raw_ticker)
        if not ticker or raw_ticker != ticker:
            raise PaperTransactionConflict("autonomous WAL contains a noncanonical position")
        before_shares = _position_shares_for_mandate(before, ticker)
        after_shares = _position_shares_for_mandate(after, ticker)
        if after_shares > before_shares + 1e-9:
            identity_error = instrument_policy.executable_equity_error(
                portfolio_id, ticker
            )
            if identity_error:
                raise PaperTransactionConflict(
                    f"{portfolio_id} WAL position increase violates mandate: {identity_error}"
                )

    for ticker in preserved:
        if before_positions.get(ticker) != after_positions.get(ticker):
            raise PaperTransactionConflict(
                f"autonomous WAL changed preserved position: {ticker}"
            )


def _recover_paper_transaction_unlocked(
    portfolio_id: str | None = None,
) -> dict[str, Any] | None:
    """Idempotently finish a prepared account/fill transition and return its audit summary.

    Recovery never guesses.  The current account must equal either the recorded before state or
    the exact after state; otherwise replay stops with the artifact intact.  Deterministic fill ids
    make an exception raised before *or after* an append safe to retry.
    """
    transaction = _load_transaction(portfolio_id)
    if transaction is None:
        return None
    if transaction.get("portfolio_id") != str(portfolio_id or "flagship"):
        raise PaperTransactionConflict("paper transaction portfolio identity mismatch")

    before = transaction.get("account_before")
    after = transaction.get("account_after")
    fills = transaction.get("fills")
    if not isinstance(before, dict) or not isinstance(after, dict) or not isinstance(fills, list):
        raise PaperTransactionConflict("paper transaction payload is incomplete")
    if transaction.get("account_before_sha256") != _content_sha256(before):
        raise PaperTransactionConflict("paper transaction before-state digest mismatch")
    if transaction.get("account_after_sha256") != _content_sha256(after):
        raise PaperTransactionConflict("paper transaction after-state digest mismatch")

    from portfolio import registry

    if registry.requires_single_name_equity(portfolio_id):
        _validate_stock_only_transaction_mandate(
            transaction,
            portfolio_id=portfolio_id,
            before=before,
            after=after,
            fills=fills,
        )

    current = _load_account_file(portfolio_id, strict=True)
    current_hash = _content_sha256(current)
    before_hash = transaction["account_before_sha256"]
    after_hash = transaction["account_after_sha256"]
    if current_hash == before_hash:
        _save_account(after, portfolio_id)
    elif current_hash != after_hash:
        raise PaperTransactionConflict(
            "account changed outside the prepared paper transaction; replay stopped"
        )

    fills_path = _paths(portfolio_id)["fills"]
    _repair_partial_jsonl_tail(fills_path)
    existing_ids = {
        str(row.get("fill_id"))
        for row in _load_jsonl(fills_path)
        if isinstance(row, dict) and row.get("fill_id")
    }
    for entry in fills:
        if not isinstance(entry, dict):
            raise PaperTransactionConflict("paper transaction fill entry is malformed")
        fill_id = entry.get("fill_id")
        record = entry.get("record")
        if not isinstance(fill_id, str) or not isinstance(record, dict):
            raise PaperTransactionConflict("paper transaction fill entry is incomplete")
        if record.get("fill_id") != fill_id:
            raise PaperTransactionConflict("paper transaction fill id mismatch")
        expected_id = hashlib.sha256(
            _canonical_json_bytes({
                "transaction_id": transaction.get("transaction_id"),
                "index": entry.get("index"),
                "fill": {k: v for k, v in record.items() if k not in {"fill_id", "transaction_id"}},
            })
        ).hexdigest()
        if fill_id != expected_id:
            raise PaperTransactionConflict("paper transaction deterministic fill id is invalid")
        if fill_id in existing_ids:
            continue
        _append_jsonl(fills_path, record)
        existing_ids.add(fill_id)

    receipt = _write_settlement_receipt(transaction, portfolio_id)
    _apply_transaction_followup(transaction, portfolio_id)
    _durable_unlink(_transaction_path(portfolio_id))
    result = {
        "transaction_id": transaction.get("transaction_id"),
        "portfolio_id": transaction.get("portfolio_id"),
        "fill_count": len(fills),
        "status": "committed",
    }
    if receipt is not None:
        result["settlement_receipt_id"] = receipt["transaction_id"]
    return result


def recover_paper_transaction(portfolio_id: str | None = None) -> dict[str, Any] | None:
    """Serialize and idempotently finish one book's prepared paper transaction."""
    with _paper_transaction_lock(portfolio_id):
        return _recover_paper_transaction_unlocked(portfolio_id)


def _commit_account_and_fills(
    before: dict[str, Any],
    after: dict[str, Any],
    fills: list[dict[str, Any]],
    *,
    asof: str,
    portfolio_id: str | None = None,
    followup: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Prepare and commit one replay-safe paper mutation."""
    try:
        canonical_asof = date.fromisoformat(asof).isoformat()
    except (TypeError, ValueError) as exc:
        raise PaperTransactionConflict("paper transaction asof is not a canonical ISO date") from exc
    if asof != canonical_asof:
        raise PaperTransactionConflict("paper transaction asof is not a canonical ISO date")
    with _paper_transaction_lock(portfolio_id):
        if _transaction_path(portfolio_id).exists():
            _recover_paper_transaction_unlocked(portfolio_id)
        if pending_settlement_receipts(portfolio_id):
            raise PaperTransactionConflict(
                "paper mutation blocked by an unfinalized settlement receipt"
            )

        before_snapshot = deepcopy(before)
        after_snapshot = deepcopy(after)
        raw_fills = [deepcopy(fill) for fill in fills]
        if before_snapshot == after_snapshot and not raw_fills and followup is None:
            return None

        seed = {
            "schema": PAPER_TRANSACTION_SCHEMA,
            "portfolio_id": str(portfolio_id or "flagship"),
            "asof": str(asof),
            "account_before_sha256": _content_sha256(before_snapshot),
            "account_after": deepcopy(after_snapshot),
            "fills": deepcopy(raw_fills),
            "followup": deepcopy(followup),
        }
        transaction_id = hashlib.sha256(_canonical_json_bytes(seed)).hexdigest()
        is_target_settlement = (
            isinstance(followup, dict)
            and followup.get("kind") == "clear_pending_target"
        )
        if before_snapshot != after_snapshot or raw_fills or is_target_settlement:
            after_snapshot["last_paper_transaction_id"] = transaction_id

        fill_entries: list[dict[str, Any]] = []
        for index, fill in enumerate(raw_fills):
            fill_id = hashlib.sha256(
                _canonical_json_bytes({
                    "transaction_id": transaction_id,
                    "index": index,
                    "fill": fill,
                })
            ).hexdigest()
            record = {**fill, "transaction_id": transaction_id, "fill_id": fill_id}
            fill_entries.append({"index": index, "fill_id": fill_id, "record": record})

        transaction = {
            "schema": PAPER_TRANSACTION_SCHEMA,
            "transaction_id": transaction_id,
            "portfolio_id": str(portfolio_id or "flagship"),
            "asof": str(asof),
            "prepared_at": datetime.now(UTC).isoformat(),
            "account_before": before_snapshot,
            "account_before_sha256": _content_sha256(before_snapshot),
            "account_after": after_snapshot,
            "account_after_sha256": _content_sha256(after_snapshot),
            "fills": fill_entries,
            "followup": followup,
            "identity": seed,
        }
        _write_transaction(transaction, portfolio_id)
        return _recover_paper_transaction_unlocked(portfolio_id)


# ---------------------------------------------------------------------------
# price loaders (engine price store)
# ---------------------------------------------------------------------------

def _fetch_price_series(ticker: str) -> "pd.Series | None":
    """Return a date-indexed close Series from the macro engine price stores.

    Priority:
      1. lib.store.read("yahoo", ticker) — has sector ETFs + SPY
      2. breadth/_closes_cache.parquet   — has the S&P large-cap single names
    """
    try:
        import pandas as pd
        from lib import store  # vendored macro lib
        df = store.read("yahoo", ticker)
        if df is not None and "close" in df.columns and len(df) > 0:
            s = df["close"].astype(float).dropna()
            s.index = pd.to_datetime(s.index)
            return s
    except Exception:
        pass

    try:
        import pandas as pd
        from lib import config  # vendored macro lib
        closes_path = config.data_dir() / "breadth" / "_closes_cache.parquet"
        if closes_path.exists():
            cache = None
            try:
                import pandas as _pd
                cache = _pd.read_parquet(closes_path)
            except Exception:
                pass
            if cache is not None and ticker in cache.columns:
                s = cache[ticker].astype(float).dropna()
                s.index = _pd.to_datetime(s.index)
                return s
    except Exception:
        pass

    # The vendored Macro store does not yet include these native regional indexes. Keep the live
    # fallback deliberately narrow so ordinary single-name reads remain offline/deterministic while
    # every benchmark consumer (performance, calibration, risk views) can resolve the same indexes.
    if (ticker or "").upper().strip() in {"000300.SS", "^HSI"}:
        try:
            from data_layer import yahoo_feed
            s = yahoo_feed.history_local(ticker)
            if s is not None and len(s) > 0:
                return s
        except Exception:
            pass

    return None


def _live_price(ticker: str) -> float | None:
    """Best live mark for a ticker, in USD.

    Dispatches by venue suffix:
      * ``*.SS`` / ``*.SZ`` → the LIVE Tushare A-share close (CNY) when available, else the vendored
                              ``chinastockdata/`` snapshot → USD
      * ``*.HK`` / ``^HSI`` → the LIVE Yahoo close (HKD) when available, else the vendored
                              ``hkstockdata/`` snapshot → USD
      * else                → ``stockdata/``     (USD, incl. US-listed China ADRs)
    The China/HK legs convert their LOCAL quote to USD via ``portfolio.fx`` so the paper account's
    single-currency NAV stays honest (it holds all three venues at once). Live marks come from
    Tushare for A-shares (``daily``) and Yahoo for Hong Kong; both degrade to the snapshot on any
    miss (Tushare's ``hk_daily`` is too rate-limited to mark a multi-name HK book)."""
    t = (ticker or "").upper().strip()
    if t.endswith(".SS") or t.endswith(".SZ"):
        sub, convert = "chinastockdata", True
    elif t.endswith(".HK") or t == "^HSI":
        sub, convert = "hkstockdata", True
    else:
        sub, convert = "stockdata", False

    local: float | None = None
    # A-shares: prefer Yahoo's native-CNY Shanghai/Shenzhen quote, which remains reachable from
    # non-China VPS hosts; retain Tushare as the second live source. Hong Kong: Yahoo HKD close
    # (Tushare's ``hk_daily`` is throttled to ~1 call/hr — see data_layer.yahoo_feed).
    # Both lag-correct the vendored snapshot.
    if t.endswith((".SS", ".SZ")):
        try:
            from data_layer import yahoo_feed
            local = yahoo_feed.price_local(t)
        except Exception:
            local = None
        if local is None:
            try:
                from data_layer import tushare_feed
                local = tushare_feed.price_local(t)
            except Exception:
                local = None
    elif t.endswith(".HK") or t == "^HSI":
        try:
            from data_layer import yahoo_feed
            local = yahoo_feed.price_local(t)
        except Exception:
            local = None
    else:
        # US (bare tickers + ETFs): the LIVE Yahoo quote (USD) via yfinance — reflects TODAY's tape.
        # The vendored stockdata snapshot is CI/EOD-lagging, so on a fast day (e.g. SMH -7%) it marks a
        # stale price and the book NAV is wrong; the live leg fixes that. Degrades to the snapshot below.
        try:
            from data_layer import yahoo_feed
            local = yahoo_feed.price_local(t)
        except Exception:
            local = None
    # Fallback (and the only path when the live leg misses): the vendored per-name snapshot.
    if local is None:
        try:
            p = _ROOT / "vendor" / "macro" / "site" / sub / f"{t}.json"
            if p.exists():
                v = (json.loads(p.read_text()).get("tech") or {}).get("price")
                if v is not None:
                    local = float(v)
        except Exception:
            local = None
    if local is None:
        return None
    if convert:
        from portfolio import fx
        return fx.to_usd(local, t)
    return local


def _current_price(ticker: str) -> float | None:
    """Best available current/last-close price for a ticker: the stockdata live mark first,
    else the last point of the engine price series (covers the leadership-sleeve ETFs)."""
    px = _live_price(ticker)
    if px and px > 0:
        return px
    s = _fetch_price_series(ticker)
    try:
        if s is not None and len(s) > 0:
            v = float(s.iloc[-1])
            # The series stores (yahoo / breadth cache) quote in LOCAL currency; convert a China/HK
            # name to USD so the fallback can't leak a raw CNY/HKD mark into NAV (bare US tickers pass
            # through unchanged). Mirrors the conversion _live_price already does for the live mark.
            from portfolio import fx
            return fx.to_usd(v, ticker)
    except Exception:
        pass
    return None


def _benchmark_for(portfolio_id: str | None) -> str:
    """The registry-resolved equity-curve comparison symbol (SPY / CSI 300 / Hang Seng)."""
    try:
        from portfolio import registry
        return registry.benchmark(portfolio_id)
    except Exception:
        return "SPY"


def reset_cost_basis_to_market(prices: dict[str, float] | None = None,
                               portfolio_id: str | None = None) -> dict[str, float]:
    """Reset every holding's avg_cost to its CURRENT market price → wipes unrealized P&L.

    Used when the book is marked flat with no trading (e.g. the market has been closed all day):
    nothing actually traded, so carrying a stale unrealized gain/loss is wrong. Only the cost
    basis — and therefore unrealized P&L — is reset to zero as of now.

    NAV-safe: a holding is reset ONLY to a real current mark. `prices` (the same marks nav()/
    positions_pnl() use) is preferred; the stockdata live price is the per-name fallback. A name
    with NO available mark is SKIPPED (never reset to a stale series value) so the avg_cost — which
    nav() falls back to when a live quote is missing — can't silently shift the portfolio total.
    Returns {ticker: new_cost_basis}. Paper-only."""
    state = _load_account(portfolio_id)
    prices = prices or {}
    updated: dict[str, float] = {}
    for ticker, pos in state.get("positions", {}).items():
        px = prices.get(ticker)
        if px is None:
            px = _live_price(ticker)          # the stockdata mark (consistent with the marks elsewhere)
        if px and px > 0 and pos.get("shares"):
            pos["avg_cost"] = round(float(px), 4)
            updated[ticker] = pos["avg_cost"]
    _save_account(state, portfolio_id)
    return updated


# ---------------------------------------------------------------------------
# core account operations
# ---------------------------------------------------------------------------

def nav(prices: dict[str, float], portfolio_id: str | None = None) -> float:
    """Current NAV = cash + market value of all positions."""
    state = _load_account(portfolio_id)
    mktval = sum(
        pos["shares"] * prices.get(ticker, pos["avg_cost"])
        for ticker, pos in state["positions"].items()
    )
    return state["cash"] + mktval


def positions_pnl(prices: dict[str, float], portfolio_id: str | None = None) -> dict[str, dict]:
    """Per-ticker live P&L from the account's average-cost lots, marked to `prices`.

    Returns {TICKER: {shares, avg_cost, current_price, market_value,
                      unrealized_pnl, unrealized_pct}}. Values are None when a
    live price is missing (offline) so callers can render an honest dash."""
    state = _load_account(portfolio_id)
    out: dict[str, dict] = {}
    for ticker, pos in state.get("positions", {}).items():
        shares = float(pos.get("shares") or 0.0)
        avg = float(pos.get("avg_cost") or 0.0)
        px = prices.get(ticker)
        rec = {
            "shares": shares,
            "avg_cost": round(avg, 4) if avg else None,
            "current_price": round(px, 4) if px else None,
            "market_value": None,
            "unrealized_pnl": None,
            "unrealized_pct": None,
        }
        if px and avg and shares:
            rec["market_value"] = round(shares * px, 2)
            rec["unrealized_pnl"] = round((px - avg) * shares, 2)
            rec["unrealized_pct"] = round((px / avg - 1) * 100, 2)
        out[ticker] = rec
    return out


def _trusted_execution_price(value: Any) -> bool:
    """Whether ``value`` is a usable paper-fill mark.

    Average cost remains an acceptable *valuation* fallback elsewhere in this module, but it is
    never evidence of a price at which an exit could have occurred.  Keep the execution predicate
    deliberately narrow so ``None``, zero, negative, NaN, and infinities all fail closed.
    """
    try:
        price = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(price) and price > 0.0


def unpriceable_exit_tickers(
    target_weights: dict[str, float],
    prices: dict[str, float],
    portfolio_id: str | None = None,
    *,
    state: dict[str, Any] | None = None,
) -> list[str]:
    """Return held names the target intends to fully exit without a trusted fill price.

    A missing target row and an explicit non-positive target weight both mean a full exit.  A held
    name with a positive target is not blocked here: ``rebalance`` can safely carry it unchanged
    until it is priceable.  ``state`` is injectable so higher-level execution paths can validate a
    single account snapshot before performing any write.
    """
    account = state if state is not None else _load_account(portfolio_id)
    targets: dict[str, float] = {}
    for raw_ticker, raw_weight in (target_weights or {}).items():
        ticker = str(raw_ticker).upper().strip()
        if not ticker:
            continue
        try:
            targets[ticker] = float(raw_weight)
        except (TypeError, ValueError):
            targets[ticker] = 0.0

    blocked: list[str] = []
    for raw_ticker, position in (account.get("positions") or {}).items():
        ticker = str(raw_ticker).upper().strip()
        try:
            shares = float((position or {}).get("shares") or 0.0)
        except (TypeError, ValueError):
            shares = 0.0
        if shares <= 1e-9 or targets.get(ticker, 0.0) > 1e-9:
            continue
        if not _trusted_execution_price(prices.get(ticker)):
            blocked.append(ticker)
    return sorted(set(blocked))


def unpriceable_target_requirements(
    target_weights: dict[str, float],
    prices: dict[str, float],
    portfolio_id: str | None = None,
    *,
    state: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    """Return every missing mark that prevents an atomic complete-target rebalance.

    A complete target is one instruction, not a best-effort collection of independent
    orders.  It requires a trusted mark for every positive target row (new or held) and
    for every held row omitted/zeroed by the target.  Otherwise a partial rebalance can
    consume cash for the priceable names, silently skip another accepted name, and then
    clear the queue.  ``state`` lets callers bind the check to the same account snapshot
    they use for execution.
    """
    account = state if state is not None else _load_account(portfolio_id)
    targets = validate_target_weights(target_weights, portfolio_id=portfolio_id)
    held = {
        str(raw_ticker).upper().strip()
        for raw_ticker, position in (account.get("positions") or {}).items()
        if isinstance(position, dict)
        and isinstance(position.get("shares"), Real)
        and float(position.get("shares") or 0.0) > 1e-9
    }
    positive_targets = set(targets)
    exits = held - positive_targets
    required = positive_targets | exits
    blocked = sorted(
        ticker for ticker in required
        if not _trusted_execution_price(prices.get(ticker))
    )
    return {
        "tickers": blocked,
        "exit_tickers": sorted(set(blocked) & exits),
        "positive_target_tickers": sorted(set(blocked) & positive_targets),
    }


class InvalidTargetWeights(ValueError):
    """A complete executable target failed the deterministic sizing contract."""

    def __init__(self, reason: str):
        self.reason = str(reason)
        super().__init__(f"invalid target weights: {self.reason}")


def _canonical_target_ticker(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    ticker = value.upper().strip()
    if not ticker or len(ticker) > 16:
        return ""
    if any(not (char.isalnum() or char in ".-") for char in ticker):
        return ""
    return ticker


def canonical_positive_positions(positions: Any) -> dict[str, dict[str, float]]:
    """Canonical executable held-lot snapshot used by operator-migration constraints.

    Only positive lots participate.  Cash, marks, and other account metadata are deliberately
    excluded, while ticker set, exact share count, and average cost are authority-bearing.  Invalid
    lot data fails closed instead of being omitted from the digest.
    """
    if not isinstance(positions, dict):
        raise InvalidExecutionConstraints("positions_snapshot_not_object")
    canonical: dict[str, dict[str, float]] = {}
    for raw_ticker in sorted(positions):
        ticker = _canonical_target_ticker(raw_ticker)
        if not ticker or raw_ticker != ticker:
            raise InvalidExecutionConstraints("positions_snapshot_ticker_noncanonical")
        raw_lot = positions.get(raw_ticker)
        if not isinstance(raw_lot, dict):
            raise InvalidExecutionConstraints(f"positions_snapshot_lot_invalid:{ticker}")
        raw_shares = raw_lot.get("shares")
        if isinstance(raw_shares, bool) or not isinstance(raw_shares, Real):
            raise InvalidExecutionConstraints(f"positions_snapshot_lot_invalid:{ticker}")
        shares = float(raw_shares)
        if not math.isfinite(shares) or shares < 0.0:
            raise InvalidExecutionConstraints(f"positions_snapshot_shares_invalid:{ticker}")
        if shares <= 1e-9:
            continue
        raw_avg_cost = raw_lot.get("avg_cost")
        if isinstance(raw_avg_cost, bool) or not isinstance(raw_avg_cost, Real):
            raise InvalidExecutionConstraints(f"positions_snapshot_lot_invalid:{ticker}")
        avg_cost = float(raw_avg_cost)
        if not math.isfinite(avg_cost) or avg_cost <= 0.0:
            raise InvalidExecutionConstraints(f"positions_snapshot_cost_invalid:{ticker}")
        canonical[ticker] = {"shares": shares, "avg_cost": avg_cost}
    return canonical


def positions_sha256(positions: Any) -> str:
    """Digest the exact positive held-lot snapshot (ticker, shares, and average cost)."""
    return _content_sha256(canonical_positive_positions(positions))


def validate_target_weights(
    target_weights: Any,
    *,
    require_canonical_tickers: bool = False,
    portfolio_id: str | None = None,
) -> dict[str, float]:
    """Validate and canonicalize one complete executable target book.

    This is an authority boundary, not a convenience coercer: booleans, numeric strings, NaN,
    infinities, negative weights, individual weights above 100%, canonical ticker collisions, and
    gross exposure above 100% are rejected.  Zero rows carry no executable intent and are removed.
    Registry-declared AI books have an additional positive-identity requirement: every retained
    row must resolve to a trusted single-name-equity contract for that market.  The archived ETF
    book and the user's self-directed book remain outside this mandate.
    """
    if not isinstance(target_weights, dict):
        raise InvalidTargetWeights("target_not_object")

    canonical: dict[str, float] = {}
    observed: set[str] = set()
    for raw_ticker, raw_weight in target_weights.items():
        ticker = _canonical_target_ticker(raw_ticker)
        if not ticker:
            raise InvalidTargetWeights("invalid_ticker")
        if require_canonical_tickers and raw_ticker != ticker:
            raise InvalidTargetWeights("noncanonical_ticker")
        if ticker in observed:
            raise InvalidTargetWeights("canonical_ticker_collision")
        observed.add(ticker)

        if isinstance(raw_weight, bool) or not isinstance(raw_weight, Real):
            raise InvalidTargetWeights(f"non_numeric_weight:{ticker}")
        weight = float(raw_weight)
        if not math.isfinite(weight):
            raise InvalidTargetWeights(f"non_finite_weight:{ticker}")
        if weight < 0.0:
            raise InvalidTargetWeights(f"negative_weight:{ticker}")
        if weight > 1.0:
            raise InvalidTargetWeights(f"weight_above_one:{ticker}")
        if weight > 0.0:
            from portfolio import registry

            if registry.requires_single_name_equity(portfolio_id):
                from portfolio import instrument_policy

                identity_error = instrument_policy.executable_equity_error(
                    portfolio_id, ticker
                )
                if identity_error:
                    raise InvalidTargetWeights(identity_error)
            canonical[ticker] = weight

    gross = math.fsum(canonical.values())
    if gross > 1.0:
        raise InvalidTargetWeights("gross_above_one")
    return canonical


def rebalance(
    target_weights: dict[str, float],
    prices: dict[str, float],
    asof: str,
    portfolio_id: str | None = None,
    *,
    _followup: dict[str, Any] | None = None,
    _preserve_existing_shares: frozenset[str] | set[str] | None = None,
    _preserve_positions_sha256: str | None = None,
) -> None:
    """Simulate fills to reach target_weights * current_nav.

    Rules:
    - No leverage: malformed or over-gross targets fail closed before account mutation.
    - Cash floored at 0.
    - Fills recorded to fills.jsonl.
    - account.json updated atomically.

    GuardrailResult contract: if the no-leverage or cash-floor check raises unexpectedly, a
    FREEZE event is logged to run_events and the exception re-raised so the caller can decide
    whether to abort the run (callers already wrap with try/except for best-effort runs).
    """
    # Validate before loading/recovering mutable account state.  An invalid current instruction is
    # never allowed to trigger a write, nor is it silently normalized into a different portfolio.
    target_weights = validate_target_weights(
        target_weights,
        portfolio_id=portfolio_id,
    )
    preserve_existing_shares = frozenset(_preserve_existing_shares or ())
    preserve_mode = _preserve_positions_sha256 is not None
    if preserve_mode:
        if portfolio_id != "autonomous":
            raise InvalidExecutionConstraints("preserve_mode_wrong_portfolio")
        if preserve_existing_shares != frozenset(target_weights):
            raise InvalidExecutionConstraints("preserve_tickers_target_set_mismatch")
        if (
            not isinstance(_preserve_positions_sha256, str)
            or len(_preserve_positions_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in _preserve_positions_sha256)
        ):
            raise InvalidExecutionConstraints("preserve_positions_sha256_invalid")
    elif preserve_existing_shares:
        raise InvalidExecutionConstraints("preserve_positions_sha256_missing")
    state = _load_account(portfolio_id)
    before_state = deepcopy(state)
    if preserve_mode:
        observed_positions_sha256 = positions_sha256(state.get("positions"))
        if observed_positions_sha256 != _preserve_positions_sha256:
            raise InvalidExecutionConstraints("positions_snapshot_mismatch")
    preserved_lots: dict[str, dict[str, Any]] = {}
    for ticker in sorted(preserve_existing_shares):
        lot = (state.get("positions") or {}).get(ticker)
        if not isinstance(lot, dict):
            raise InvalidExecutionConstraints(f"preserved_position_missing:{ticker}")
        try:
            held_shares = float(lot.get("shares") or 0.0)
        except (TypeError, ValueError) as exc:
            raise InvalidExecutionConstraints(
                f"preserved_position_invalid:{ticker}"
            ) from exc
        if not math.isfinite(held_shares) or held_shares <= 1e-9:
            raise InvalidExecutionConstraints(f"preserved_position_missing:{ticker}")
        preserved_lots[ticker] = deepcopy(lot)

    current_nav = (
        state["cash"]
        + sum(
            pos["shares"] * prices.get(ticker, pos["avg_cost"])
            for ticker, pos in state["positions"].items()
        )
    )

    # No-trade band, in dollars, for this run's NAV. Incremental adjustments to a continuing
    # position below this notional are suppressed (see _no_trade_band_frac for the rationale).
    band = _no_trade_band_frac() * current_nav

    fills: list[dict] = []

    # ---- determine target shares for each ticker we can PRICE this run ----
    targeted = set(target_weights)                 # everything we INTEND to hold (priced or not)
    target_shares: dict[str, float] = {}
    for ticker, weight in target_weights.items():
        if ticker in preserve_existing_shares:
            # The operator migration has no authority to resize continuing common stocks.  Target
            # weights remain in the complete book for identity/provenance, but share count is the
            # executable invariant even if the price doubles between queue and settlement.
            continue
        px = prices.get(ticker)
        if px is None or px <= 0:
            continue                               # targeted but unpriceable this run -> carry, don't trade
        held = state["positions"].get(ticker, {}).get("shares", 0.0)
        if held <= 1e-9 and weight < _min_position_frac() - 1e-9:
            continue                               # don't OPEN a sub-floor sliver position (held names exempt)
        target_dollar = weight * current_nav
        target_shares[ticker] = target_dollar / px

    # ---- process sells first (free up cash before buys) ----
    # ONLY adjust a held position we can price AND that is in the target. A held name that is
    # targeted but has no price THIS run is NOT touched (the old code defaulted its target to 0 and
    # liquidated the whole position on a transient missing quote — a spurious exit).
    for ticker, pos in list(state["positions"].items()):
        if ticker not in target_shares:
            continue
        tgt = target_shares[ticker]
        cur = pos["shares"]
        diff = tgt - cur
        if diff < -1e-9:
            sell_shares = -diff
            px = prices.get(ticker, pos["avg_cost"])
            value = sell_shares * px
            # No-trade band: a sub-band trim of a name we're still holding (tgt > 0, so never a
            # full exit) is left alone — don't manufacture a tiny sell the Brain never intended.
            if value < band:
                continue
            state["cash"] += value
            pos["shares"] = tgt
            if pos["shares"] < 1e-9:
                del state["positions"][ticker]
            fills.append({
                "date": asof,
                "ticker": ticker,
                "side": "sell",
                **_persisted_fill_facts(sell_shares, px, value),
            })

    # Close out only tickers GENUINELY dropped from the target *and* carrying a trusted price this
    # run.  ``avg_cost`` may value inventory when a quote is missing, but booking an exit at cost
    # fabricates a fill and realized return.  Higher-level settle paths reject the whole target on
    # this condition; direct low-level callers conservatively carry only the unpriceable line.
    for ticker in list(state["positions"].keys()):
        if ticker not in targeted:
            pos = state["positions"][ticker]
            px = prices.get(ticker)
            if not _trusted_execution_price(px):
                continue
            px = float(px)
            sell_shares = pos["shares"]
            value = sell_shares * px
            state["cash"] += value
            del state["positions"][ticker]
            fills.append({
                "date": asof,
                "ticker": ticker,
                "side": "sell",
                **_persisted_fill_facts(sell_shares, px, value),
            })

    # ---- process buys ----
    for ticker, tgt in target_shares.items():
        cur = state["positions"].get(ticker, {}).get("shares", 0.0)
        diff = tgt - cur
        if diff > 1e-9:
            px = prices.get(ticker)
            if px is None or px <= 0:
                continue
            # No-trade band: skip a sub-band ADD to a CONTINUING position (held before this run).
            # A brand-new entry (cur ~ 0) is a deliberate open and always executes.
            if cur > 1e-9 and diff * px < band:
                continue
            # clamp so we don't spend more than available cash
            buy_shares = min(diff, state["cash"] / px)
            # dust filter: whole shares + min-notional floor (skip sliver buys like 0.4 IWM)
            buy_shares = _buyable_shares(buy_shares, px, current_nav)
            if buy_shares < 1e-9:
                continue
            value = buy_shares * px
            state["cash"] = max(0.0, state["cash"] - value)
            if ticker in state["positions"]:
                old = state["positions"][ticker]
                total_shares = old["shares"] + buy_shares
                old["avg_cost"] = (
                    (old["shares"] * old["avg_cost"] + value) / total_shares
                )
                old["shares"] = total_shares
            else:
                state["positions"][ticker] = {
                    "shares": buy_shares,
                    "avg_cost": px,
                }
            fills.append({
                "date": asof,
                "ticker": ticker,
                "side": "buy",
                **_persisted_fill_facts(buy_shares, px, value),
            })

    for ticker, original_lot in preserved_lots.items():
        if (state.get("positions") or {}).get(ticker) != original_lot:
            raise InvalidExecutionConstraints(f"preserved_position_changed:{ticker}")

    try:
        _commit_account_and_fills(
            before_state,
            state,
            fills,
            asof=asof,
            portfolio_id=portfolio_id,
            followup=_followup,
        )
    except Exception as _exc:
        # Log FREEZE: account write failure — do not silently lose fills or corrupt the ledger.
        # Conservative action: we attempted the write; it failed. Re-raise so callers can handle.
        try:
            from control_plane.guardrail import GuardrailResult, Severity
            GuardrailResult.failed(
                "rebalance_account_write",
                Severity.FREEZE,
                detail=f"rebalance account save raised: {_exc!r}"[:200],
                action_taken="recoverable transaction retained; execution stopped",
            ).log(job="paper_account_rebalance", book=str(portfolio_id or "flagship"))
        except Exception:  # noqa: BLE001 — guardrail logging must never mask the original error
            pass
        raise  # re-raise so callers' existing try/except can decide next steps


def execute_fill(ticker: str, side: str, *, weight: float | None = None,
                 shares: float | None = None, price: float | None = None,
                 prices: dict[str, float] | None = None,
                 asof: str | None = None, portfolio_id: str | None = None) -> dict:
    """A SINGLE-NAME paper fill, funded from / credited to cash.

    Unlike rebalance() — which takes a FULL target book and SELLS anything not in it —
    this adds, trims, or exits EXACTLY one ticker and never touches any other position.
    It is how the advisor chat conducts an ad-hoc paper trade.

    side  : "buy" | "sell"
    sizing: buy  -> `weight` (fraction of NAV) or explicit `shares`
            sell -> explicit `shares`, or omit both to EXIT the whole position
    Returns {ok, ticker, side, shares, price, value, cash_after}; ok=False on no price /
    insufficient cash / nothing to sell. Paper-only; reversible.
    """
    ticker = ticker.upper()
    side = (side or "").lower()
    asof = asof or date.today().isoformat()
    # The advisor/single-fill path bypasses complete-target normalization.  Apply the same positive
    # identity policy before even loading recoverable account state so it cannot become a side door
    # for an ETF or an unverified symbol.  Sells deliberately remain unrestricted: legacy ETF
    # inventory must always be exitable from the common-stock-only successor book.
    from portfolio import registry

    if side == "buy" and registry.requires_single_name_equity(portfolio_id):
        validate_target_weights(
            {ticker: 1.0},
            require_canonical_tickers=True,
            portfolio_id=portfolio_id,
        )
    state = _load_account(portfolio_id)
    before_state = deepcopy(state)
    px = price if (price and price > 0) else _current_price(ticker)
    if not px or px <= 0:
        return {"ok": False, "ticker": ticker, "error": "no price available"}
    pos = state["positions"].get(ticker)

    if side == "buy":
        if shares is None:
            pmap = dict(prices or {})
            pmap.setdefault(ticker, px)
            dollars = max(0.0, float(weight or 0.0)) * nav(pmap, portfolio_id)
            shares = dollars / px
        shares = min(float(shares), state["cash"] / px)          # cash-bounded, no leverage
        # dust filter: whole shares + min-notional floor (same rule as the Brain rebalance)
        shares = _buyable_shares(shares, px, nav({**(prices or {}), ticker: px}, portfolio_id))
        if shares <= 1e-9:
            return {"ok": False, "ticker": ticker, "error": "below minimum trade size"}
        value = shares * px
        state["cash"] = max(0.0, state["cash"] - value)
        if pos:
            total = pos["shares"] + shares
            pos["avg_cost"] = (pos["shares"] * pos["avg_cost"] + value) / total
            pos["shares"] = total
        else:
            state["positions"][ticker] = {"shares": shares, "avg_cost": px}
        fill = {"date": asof, "ticker": ticker, "side": "buy",
                **_persisted_fill_facts(shares, px, value)}
    else:                                                        # sell / trim / exit
        if not pos or pos["shares"] <= 1e-9:
            return {"ok": False, "ticker": ticker, "error": "no position to sell"}
        sell = pos["shares"] if shares is None else min(float(shares), pos["shares"])
        if sell <= 1e-9:
            return {"ok": False, "ticker": ticker, "error": "zero size"}
        value = sell * px
        state["cash"] += value
        pos["shares"] -= sell
        if pos["shares"] < 1e-9:
            del state["positions"][ticker]
        fill = {"date": asof, "ticker": ticker, "side": "sell",
                **_persisted_fill_facts(sell, px, value)}

    _commit_account_and_fills(
        before_state,
        state,
        [fill],
        asof=asof,
        portfolio_id=portfolio_id,
    )
    return {"ok": True, **fill, "cash_after": round(state["cash"], 2)}


# ---------------------------------------------------------------------------
# pending orders — overnight / market-closed buy queue
# ---------------------------------------------------------------------------
# When the desk decides to buy while the market is CLOSED, nothing trades: we
# record a PENDING order with an estimated price (the previous close) and let it
# fill at the NEXT open, at the real market price. Pending orders never touch
# cash or positions until they fill — NAV stays honest while they sit in queue.

def load_pending(portfolio_id: str | None = None) -> list[dict]:
    """All currently-queued (unfilled) orders. [] on missing/corrupt file."""
    try:
        p = _paths(portfolio_id)["pending"]
        if p.exists():
            data = json.loads(p.read_text())
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _save_pending(orders: list[dict], portfolio_id: str | None = None) -> None:
    _ensure_dir(portfolio_id)
    _atomic_write_bytes(
        _paths(portfolio_id)["pending"],
        json.dumps(orders, indent=2, default=str).encode("utf-8"),
    )


def queue_orders(
    target_weights: dict[str, float],
    est_prices: dict[str, float],
    asof: str,
    *,
    nav_base: float | None = None,
    fill_after: str | None = None,
    portfolio_id: str | None = None,
) -> list[dict]:
    """Queue PENDING orders to move the book toward the FULL `target_weights`, sized at
    `est_prices` (the previous close). Used when the market is CLOSED — no fill, no
    cash/position change. The whole pending list is REPLACED so the latest decision wins
    (idempotent per build). Returns the pending list. Paper-only.

    Both SIDES are queued (this is the fix for the flagship book that structurally never
    sold): the market-closed cron fired every day at 22:40 UTC when NYSE was shut, so the
    only sell-capable path — rebalance(), gated on market-open — never ran, and this queue
    (formerly buy-only) could not represent an exit. The book therefore accreted buys with
    no offsetting sells until cash hit ~$0 and every subsequent queued buy was dead on
    arrival. Now, mirroring the FULL target book the Brain books settle via settle_target():
      * SELL — every held name whose target weight is REDUCED, or that is ABSENT from the
        target book entirely, is queued as a side='sell'. A full exit (dropped name) always
        queues; a partial trim of a CONTINUING position must clear the no-trade band (below).
      * BUY  — every name whose target share count exceeds what is held (new entry or top-up),
        subject to the same whole-share + min-notional dust filter used at market-open.
    fill_pending() then executes the SELLS FIRST at the open (freeing cash) so the buys are
    funded — see that function. Nothing here touches cash/positions; NAV stays honest while
    orders sit queued.

    No-trade band / dust: an incremental adjustment (trim of a name still in the target, or a
    top-up of a continuing position) is only queued when its notional clears the ~1%-of-NAV
    band — the same rule rebalance() uses — so a de-minimis drift is not churned. A full exit
    and a brand-new entry are deliberate decisions and are never banded. Sells are share-
    quantified (exact held-minus-target share delta, never fractional-quantized — a held line
    must stay fully exitable); buys reuse _buyable_shares (whole-share + dust floor), matching
    how buys were always queued.

    nav_base : the NAV the weights are fractions of. When None (the recommended call), it is
               the CURRENT marked NAV (cash + positions at est_prices) — NOT the $1M starting
               NAV. A stale hardcoded $1M base is the historical sizing bug: on a book that has
               drifted far from $1M it sizes every target against the wrong denominator. $1M
               survives only as the ultimate fallback when the live NAV can't be computed
               (empty/zero) so a first-ever build on a fresh account still sizes sanely.
    fill_after : the next-open date string for display.
    """
    target_weights = validate_target_weights(
        target_weights,
        portfolio_id=portfolio_id,
    )
    state = _load_account(portfolio_id)
    if nav_base is None or float(nav_base) <= 0.0:
        nav_base = state["cash"] + sum(
            pos["shares"] * est_prices.get(tk, pos["avg_cost"])
            for tk, pos in state["positions"].items()
        )
    # last-resort only: a genuinely empty/zero-NAV account (no cash, no marks) still needs a
    # non-zero denominator to size a first build — fall back to the $1M inception NAV.
    if not nav_base or float(nav_base) <= 0.0:
        nav_base = _STARTING_NAV
    if fill_after is None:
        try:
            from portfolio import market_calendar
            fill_after = market_calendar.next_open_day().isoformat()
        except Exception:
            fill_after = None

    # No-trade band, in dollars, for this run's NAV — the same band rebalance() applies. It
    # suppresses de-minimis trims/top-ups of a CONTINUING position (full exits/new entries are
    # never banded, below), so a queued rebalance can't churn micro-positions any more than a
    # live one can.
    band = _no_trade_band_frac() * nav_base

    # normalise the target book to upper-case tickers once (weights collapse on collision)
    targets: dict[str, float] = {}
    for tk, w in (target_weights or {}).items():
        targets[str(tk).upper()] = targets.get(str(tk).upper(), 0.0) + float(w or 0.0)
    targeted = set(targets)

    orders: list[dict] = []

    # ---- SELLS first: held names reduced vs target, or dropped from the book entirely ----
    # (queued first purely for a readable blotter; fill_pending is what enforces sells-before-
    # buys at the open so freed cash funds the buys.)
    for ticker, pos in state.get("positions", {}).items():
        ticker = str(ticker).upper()
        held = float(pos.get("shares") or 0.0)
        if held <= 1e-9:
            continue
        px = est_prices.get(ticker)
        if px is None or px <= 0:
            px = float(pos.get("avg_cost") or 0.0)          # exit sizing can lean on cost when unpriced
        if px is None or px <= 0:
            continue                                        # truly no price — can't size a pending sell
        weight = targets.get(ticker)
        if weight is None:
            # DROPPED from the target book → full exit. Always queues (never banded).
            sell_shares = held
        else:
            target_shares = (weight * nav_base) / px
            reduce_by = held - target_shares
            if reduce_by <= 1e-9:
                continue                                    # at/above target — no sell (buy leg handles adds)
            # trim of a name still in the book: only if it clears the no-trade band
            if reduce_by * px < band:
                continue
            sell_shares = reduce_by
        value = round(sell_shares * px, 2)
        if sell_shares <= 1e-9 or value <= 0.0:
            continue
        orders.append({
            "id": f"{asof}-{ticker}-sell",
            "ticker": ticker,
            "side": "sell",
            "shares": round(float(sell_shares), 6),
            "est_price": round(float(px), 4),
            "est_value": value,
            "weight": round(float(weight or 0.0), 4),
            "placed_asof": asof,
            "fill_after": fill_after,
            "status": "pending",
        })

    # ---- BUYS: new entries + top-ups toward target (unchanged sizing conventions) ----
    for ticker, weight in targets.items():
        px = est_prices.get(ticker)
        if px is None or px <= 0:
            continue                                   # can't estimate without a prior close
        held = float(state["positions"].get(ticker, {}).get("shares", 0.0))
        if held <= 1e-9 and weight < _min_position_frac() - 1e-9:
            continue                                   # don't OPEN a sub-floor sliver position (held names exempt)
        target_shares = (weight * nav_base) / px
        raw_add = target_shares - held
        # No-trade band: skip a sub-band top-up of a CONTINUING position (a brand-new entry,
        # held ~ 0, is a deliberate open and is never banded). Mirrors rebalance()'s buy leg.
        if held > 1e-9 and raw_add * px < band:
            continue
        # dust filter: whole shares + min-notional floor (don't queue sliver buys)
        shares = _buyable_shares(raw_add, px, nav_base)
        value = round(shares * px, 2)
        if shares <= 0.0 or value <= 0.0:
            continue                                   # already at/above target, or below the dust floor
        orders.append({
            "id": f"{asof}-{ticker}-buy",
            "ticker": ticker,
            "side": "buy",
            "shares": shares,
            "est_price": round(px, 4),
            "est_value": value,
            "weight": round(float(weight), 4),
            "placed_asof": asof,
            "fill_after": fill_after,
            "status": "pending",
        })
    _save_pending(orders, portfolio_id)
    return orders


def fill_pending(prices: dict[str, float], asof: str, portfolio_id: str | None = None) -> list[dict]:
    """Fill every queued order at the live `prices` (the market price at the open).

    SELLS FILL FIRST, then buys. This ordering is load-bearing: a market-closed build now
    queues a FULL rebalance (sells + buys — see queue_orders), and the sells must settle
    before the buys so the freed cash actually funds them. Within each phase every order
    trades its queued SHARE COUNT at the real fill price:
      * sell — credits cash, reduces (or closes) the position; a queued sell for a name no
        longer held, or for more shares than remain, is clamped to what is actually held.
      * buy  — cash-bounded (no leverage); the whole queued count fills only if cash allows,
        otherwise it fills as many whole shares as the (post-sell) cash covers and the
        remainder stays queued (existing graceful-partial behavior, unchanged).
    A real fill is appended to fills.jsonl and the position updated. An order with no
    available market price stays pending. Returns the executed fills. Call this FIRST on any
    build that runs while the market is open.

    Backward-compatible: a legacy pending_orders.json holding only buys (no 'side' field)
    still fills — a missing/blank side defaults to 'buy', so the buy-only phase runs exactly
    as before and the sell phase is simply empty."""
    pending = load_pending(portfolio_id)
    if not pending:
        return []
    from portfolio import registry

    if registry.requires_single_name_equity(portfolio_id):
        # A pre-policy/manual pending-order artifact must not bypass the complete-target boundary.
        # Validate every BUY before account recovery/mutation; SELL rows stay unrestricted so
        # inherited ETFs remain removable.
        buy_targets = {
            str(order.get("ticker") or "").upper().strip(): 1.0
            for order in pending
            if str(order.get("side") or "buy").lower() != "sell"
        }
        validate_target_weights(buy_targets, portfolio_id=portfolio_id)
    state = _load_account(portfolio_id)
    before_state = deepcopy(state)
    fills: list[dict] = []
    still_pending: list[dict] = []

    def _px_for(ticker: str, o: dict) -> float | None:
        px = prices.get(ticker)
        if px is None or px <= 0:
            px = _current_price(ticker)
        return px if (px and px > 0) else None

    # split the queue by side; a missing/blank side is a legacy buy (back-compat read path).
    sells = [o for o in pending if str(o.get("side") or "buy").lower() == "sell"]
    buys = [o for o in pending if str(o.get("side") or "buy").lower() != "sell"]

    # ---- PHASE 1: sells (free up cash before the buys are funded) ----
    for o in sells:
        ticker = (o.get("ticker") or "").upper()
        want = float(o.get("shares") or 0.0)
        px = _px_for(ticker, o)
        pos = state["positions"].get(ticker)
        held = float(pos.get("shares") or 0.0) if pos else 0.0
        if px is None or want <= 1e-9 or held <= 1e-9:
            # no price → keep queued; nothing (or nothing left) to sell → drop the stale order.
            if px is None and want > 1e-9 and held > 1e-9:
                still_pending.append(o)
            continue
        sell = min(want, held)                         # clamp to what is actually held
        value = sell * px
        state["cash"] += value
        pos["shares"] = held - sell
        if pos["shares"] < 1e-9:
            del state["positions"][ticker]
        fills.append({
            "date": asof, "ticker": ticker, "side": "sell",
            **_persisted_fill_facts(sell, px, value),
            "from_pending": True,
        })

    # ---- PHASE 2: buys (bounded by the cash left after the sells settled) ----
    for o in buys:
        ticker = (o.get("ticker") or "").upper()
        want = float(o.get("shares") or 0.0)
        px = _px_for(ticker, o)
        if px is None or want <= 1e-9:
            still_pending.append(o)                    # can't fill without a price — keep queued
            continue
        buy = min(want, state["cash"] / px) if px else 0.0
        buy = _quantize_buy_shares(buy)                # whole shares (queued count already dust-filtered)
        if buy <= 1e-9:
            still_pending.append(o)                    # out of cash / sub-lot — keep queued
            continue
        value = buy * px
        state["cash"] = max(0.0, state["cash"] - value)
        pos = state["positions"].get(ticker)
        if pos:
            total = pos["shares"] + buy
            pos["avg_cost"] = (pos["shares"] * pos["avg_cost"] + value) / total
            pos["shares"] = total
        else:
            state["positions"][ticker] = {"shares": buy, "avg_cost": px}
        fills.append({
            "date": asof, "ticker": ticker, "side": "buy",
            **_persisted_fill_facts(buy, px, value),
            "from_pending": True,
        })
    _commit_account_and_fills(
        before_state,
        state,
        fills,
        asof=asof,
        portfolio_id=portfolio_id,
        followup=_pending_orders_transition(still_pending, portfolio_id),
    )
    return fills


# ---------------------------------------------------------------------------
# pending TARGET — the market-closed branch for the free-form Brain books
# ---------------------------------------------------------------------------
# The flagship queues BUY orders when shut (queue_orders, above). The Brain books submit a COMPLETE
# target book (sells + trims + buys), so a buy-only queue can't represent "rebalance to this at the
# open." Instead we persist the whole decided target and settle it with one rebalance() at the next
# open. Idempotent: re-running a closed session REPLACES the queued target (latest decision wins), so
# repeatedly building after the close can never churn the book — nothing is filled until the open.

# The successor US book changed both its selection policy and its investable universe.  A queued
# target is executable state, not merely a cache: an unversioned v1 target left on disk can otherwise
# survive a deployment and rebalance the v2 book into the retired ETF-heavy policy at the next open.
# Regional books did not make that breaking transition, so their existing unversioned queue contract
# remains valid.  The compatibility fence below is deliberately scoped to ``autonomous`` only.
PENDING_TARGET_SCHEMA_V2 = "pending_target.v2"
US_BRAIN_ENGINE_V2 = "us_brain_v2"
PENDING_DECISION_SCHEMA_V1 = "pending_decision.v1"
EXECUTION_CONSTRAINTS_SCHEMA_V1 = "execution_constraints.v1"
PRESERVE_EXISTING_SHARES_MODE = "preserve_existing_shares"
AUTONOMOUS_LEGACY_ETF_MIGRATION_SCHEMA_V1 = "autonomous_legacy_etf_migration.v1"
_MAX_PENDING_DECISION_BYTES = 1_000_000


class PendingTargetQuarantined(RuntimeError):
    """Raised after an incompatible queued target has been isolated without executing it."""

    def __init__(self, result: dict[str, Any]):
        self.result = result
        super().__init__(
            f"pending target quarantined for {result.get('portfolio_id')}: "
            f"{result.get('reason')}"
        )


class InvalidExecutionConstraints(ValueError):
    """A privileged executable constraint failed its narrow authorization contract."""

    def __init__(self, reason: str):
        self.reason = str(reason)
        super().__init__(f"invalid execution constraints: {self.reason}")


class PendingTargetCASConflict(RuntimeError):
    """A require-absent queue write lost its compare-and-swap precondition."""

    def __init__(self, portfolio_id: str | None = None):
        self.portfolio_id = portfolio_id or "flagship"
        super().__init__(
            f"pending target already exists for {self.portfolio_id}; require-absent save refused"
        )


class UnpriceableExitPrices(RuntimeError):
    """Legacy-named stop for any incomplete complete-target price set.

    The queued target remains on disk.  Callers can retry at a later market-open price rather than
    clearing an only-partly-applied instruction or inventing a paper fill from average cost.
    """

    def __init__(
        self,
        tickers: list[str],
        portfolio_id: str | None = None,
        *,
        exit_tickers: list[str] | None = None,
        positive_target_tickers: list[str] | None = None,
    ):
        self.tickers = sorted(set(str(t).upper() for t in tickers))
        self.exit_tickers = sorted(
            set(str(t).upper() for t in (exit_tickers or []))
        )
        self.positive_target_tickers = sorted(
            set(str(t).upper() for t in (positive_target_tickers or []))
        )
        self.portfolio_id = portfolio_id or "flagship"
        super().__init__(
            f"unpriceable complete-target names for {self.portfolio_id}: "
            f"{', '.join(self.tickers)}"
        )


def _pending_target_path(portfolio_id: str | None = None) -> Path:
    return _paths(portfolio_id)["data"] / "pending_target.json"


def pending_target_file_exists(portfolio_id: str | None = None) -> bool:
    """Whether executable queue state exists, including malformed JSON that cannot be loaded."""
    return _pending_target_path(portfolio_id).exists()


def _target_sha256(target: dict[str, float]) -> str:
    """Stable identity for the executable portion of a queued instruction."""
    encoded = json.dumps(
        target,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _pending_decision_record(
    decision_snapshot: dict[str, Any] | None,
    *,
    target: dict[str, float],
    asof: str,
    portfolio_id: str | None,
) -> dict[str, Any] | None:
    """Bind an accepted structured PM decision to the exact executable target.

    The submission scratch files are intentionally cleared before every Brain turn, so they cannot
    be settlement provenance.  This compact record travels atomically inside ``pending_target``.
    A deterministic risk rewrite may pass an existing record; its original structured submission
    is preserved while the lineage records the target hash transition.
    """
    if decision_snapshot is None:
        return None
    if not isinstance(decision_snapshot, dict):
        raise TypeError("decision_snapshot must be a mapping")

    # JSON round-tripping rejects non-serializable executable metadata and gives us an isolated,
    # immutable copy.  The typed MCP boundary already bounds the structured submission; this final
    # cap prevents an audit attachment from turning executable state into an unbounded artifact.
    raw = json.dumps(decision_snapshot, default=str, ensure_ascii=False)
    if len(raw.encode("utf-8")) > _MAX_PENDING_DECISION_BYTES:
        raise ValueError("decision_snapshot exceeds bounded pending-target budget")
    supplied = json.loads(raw)

    pid = portfolio_id or "flagship"
    digest = _target_sha256(target)
    if supplied.get("schema_version") == PENDING_DECISION_SCHEMA_V1:
        record = supplied
        if record.get("portfolio_id") not in {None, pid}:
            raise ValueError("decision_snapshot portfolio identity mismatch")
        previous = record.get("target_sha256")
        if previous and previous != digest:
            lineage = list(record.get("target_lineage") or [])
            lineage.append({
                "from_target_sha256": previous,
                "to_target_sha256": digest,
                "rebound_asof": asof,
                "reason": "deterministic_risk_rewrite",
            })
            if len(lineage) > 20:
                tail = lineage[-19:]
                root = str(record.get("accepted_target_sha256") or lineage[0].get(
                    "from_target_sha256"
                ) or "")
                bridge_to = str(tail[0].get("from_target_sha256") or "")
                lineage = [{
                    "from_target_sha256": root,
                    "to_target_sha256": bridge_to,
                    "rebound_asof": asof,
                    "reason": "deterministic_risk_rewrite_compacted",
                    "compacted_transitions": len(record.get("target_lineage") or []) - 18,
                }] + tail
            record["target_lineage"] = lineage
        record.setdefault("accepted_target_sha256", previous or digest)
        record["target_sha256"] = digest
        record["portfolio_id"] = pid
        record["last_bound_asof"] = asof
        return record

    return {
        "schema_version": PENDING_DECISION_SCHEMA_V1,
        "portfolio_id": pid,
        "accepted_asof": asof,
        "target_sha256": digest,
        "accepted_target_sha256": digest,
        "submission": supplied,
    }


def _validated_execution_constraints(
    execution_constraints: Any,
    *,
    target: dict[str, float],
    decision_snapshot: dict[str, Any] | None,
    portfolio_id: str | None,
) -> dict[str, Any] | None:
    """Authorize the one narrow share-preservation mode used by the ETF migration.

    Generic PM targets carry no constraints and retain ordinary weight-based semantics.  A
    preservation constraint is accepted only when it is hash-bound to this exact autonomous target
    and its accepted decision snapshot proves the deterministic operator-migration schema.  Exact
    set equality prevents the privilege from hiding a resize/add beside the preserved positions.
    """
    if execution_constraints is None:
        return None
    if portfolio_id != "autonomous":
        raise InvalidExecutionConstraints("unauthorized_portfolio")
    if not isinstance(execution_constraints, dict):
        raise InvalidExecutionConstraints("constraint_not_object")
    expected_fields = {
        "schema",
        "mode",
        "tickers",
        "target_sha256",
        "positions_sha256",
    }
    if set(execution_constraints) != expected_fields:
        raise InvalidExecutionConstraints("unexpected_constraint_fields")
    if execution_constraints.get("schema") != EXECUTION_CONSTRAINTS_SCHEMA_V1:
        raise InvalidExecutionConstraints("unsupported_constraint_schema")
    if execution_constraints.get("mode") != PRESERVE_EXISTING_SHARES_MODE:
        raise InvalidExecutionConstraints("unsupported_constraint_mode")

    digest = _target_sha256(target)
    if execution_constraints.get("target_sha256") != digest:
        raise InvalidExecutionConstraints("constraint_target_sha256_mismatch")
    positions_digest = execution_constraints.get("positions_sha256")
    if (
        not isinstance(positions_digest, str)
        or len(positions_digest) != 64
        or any(ch not in "0123456789abcdef" for ch in positions_digest)
    ):
        raise InvalidExecutionConstraints("constraint_positions_sha256_invalid")
    raw_tickers = execution_constraints.get("tickers")
    if not isinstance(raw_tickers, list):
        raise InvalidExecutionConstraints("constraint_tickers_not_list")
    tickers: list[str] = []
    for raw_ticker in raw_tickers:
        ticker = _canonical_target_ticker(raw_ticker)
        if not ticker or raw_ticker != ticker:
            raise InvalidExecutionConstraints("constraint_ticker_noncanonical")
        tickers.append(ticker)
    if tickers != sorted(set(tickers)):
        raise InvalidExecutionConstraints("constraint_tickers_not_sorted_unique")
    if tickers != sorted(target):
        raise InvalidExecutionConstraints("constraint_tickers_target_set_mismatch")

    decision = decision_snapshot
    if (
        not isinstance(decision, dict)
        or decision.get("schema_version") != PENDING_DECISION_SCHEMA_V1
        or decision.get("portfolio_id") != "autonomous"
        or decision.get("target_sha256") != digest
        or not isinstance(decision.get("submission"), dict)
    ):
        raise InvalidExecutionConstraints("unauthorized_decision_snapshot")
    migration = decision["submission"].get("operator_migration")
    if (
        not isinstance(migration, dict)
        or migration.get("schema") != AUTONOMOUS_LEGACY_ETF_MIGRATION_SCHEMA_V1
        or migration.get("paper_only") is not True
    ):
        raise InvalidExecutionConstraints("unauthorized_operator_migration")
    preserved = migration.get("preserved_common_stocks")
    if not isinstance(preserved, list):
        raise InvalidExecutionConstraints("migration_preserved_tickers_not_list")
    normalized_preserved: list[str] = []
    for raw_ticker in preserved:
        ticker = _canonical_target_ticker(raw_ticker)
        if not ticker or raw_ticker != ticker:
            raise InvalidExecutionConstraints("migration_preserved_ticker_noncanonical")
        normalized_preserved.append(ticker)
    if normalized_preserved != sorted(set(normalized_preserved)):
        raise InvalidExecutionConstraints("migration_preserved_tickers_not_sorted_unique")
    if normalized_preserved != tickers:
        raise InvalidExecutionConstraints("migration_preserved_tickers_mismatch")
    if migration.get("positions_sha256") != positions_digest:
        raise InvalidExecutionConstraints("migration_positions_sha256_mismatch")

    return {
        "schema": EXECUTION_CONSTRAINTS_SCHEMA_V1,
        "mode": PRESERVE_EXISTING_SHARES_MODE,
        "tickers": tickers,
        "target_sha256": digest,
        "positions_sha256": positions_digest,
    }


def pending_target_contract_error(payload: dict[str, Any] | None,
                                  portfolio_id: str | None = None) -> str | None:
    """Return an incompatibility reason for an executable pending target, else ``None``.

    Only the successor US book has a breaking *version* contract.  Every book shares the same
    executable-target validation contract; malformed regional legacy payloads fail closed too.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("target"), dict):
        return "malformed_payload"
    if portfolio_id == "autonomous":
        if payload.get("schema_version") != PENDING_TARGET_SCHEMA_V2:
            return "missing_or_incompatible_schema_version"
        if payload.get("engine_version") != US_BRAIN_ENGINE_V2:
            return "missing_or_incompatible_engine_version"
        if payload.get("portfolio_id") != "autonomous":
            return "portfolio_identity_mismatch"
    elif portfolio_id in {"china", "hk"} and any(
        key in payload
        for key in ("asset_policy", "instrument_policy_version", "portfolio_id")
    ):
        # Pre-policy regional queues remain readable, but any queue that claims
        # the new authority contract must match it exactly.
        from portfolio import instrument_policy

        if payload.get("portfolio_id") != portfolio_id:
            return "portfolio_identity_mismatch"
        if payload.get("asset_policy") != instrument_policy.POLICY_NAME:
            return "missing_or_incompatible_asset_policy"
        if payload.get("instrument_policy_version") != instrument_policy.POLICY_VERSION:
            return "missing_or_incompatible_instrument_policy_version"
    try:
        target = validate_target_weights(
            payload.get("target"),
            require_canonical_tickers=True,
            portfolio_id=portfolio_id,
        )
    except InvalidTargetWeights as exc:
        return f"invalid_target:{exc.reason}"
    decision = payload.get("decision_snapshot")
    if decision is not None:
        if not isinstance(decision, dict):
            return "malformed_decision_snapshot"
        if decision.get("schema_version") != PENDING_DECISION_SCHEMA_V1:
            return "incompatible_decision_snapshot_schema"
        if decision.get("portfolio_id") != (portfolio_id or "flagship"):
            return "decision_snapshot_portfolio_mismatch"
        if not isinstance(decision.get("submission"), dict):
            return "malformed_decision_submission"
        if decision.get("target_sha256") != _target_sha256(target):
            return "decision_snapshot_target_mismatch"
    try:
        if "execution_constraints" in payload:
            if payload.get("execution_constraints") is None:
                raise InvalidExecutionConstraints("constraint_not_object")
            _validated_execution_constraints(
                payload.get("execution_constraints"),
                target=target,
                decision_snapshot=decision,
                portfolio_id=portfolio_id,
            )
    except InvalidExecutionConstraints as exc:
        return f"invalid_execution_constraints:{exc.reason}"
    return None


def quarantine_pending_target(portfolio_id: str | None, reason: str,
                              payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Recoverably isolate an incompatible target and write bounded audit metadata.

    The source is atomically renamed within its existing runtime-book directory.  It is never
    deleted and its contents are not rewritten, so an operator can inspect or restore it.  A compact
    JSONL side ledger lives beside the quarantined file; the shared governance event is best-effort.
    If the move itself fails, callers still receive/raise a fail-closed result and MUST NOT rebalance.
    """
    source = _pending_target_path(portfolio_id)
    data_dir = source.parent
    data_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    suffix = f"{now.strftime('%Y%m%dT%H%M%S%fZ')}.{uuid4().hex[:8]}"
    destination = data_dir / f"pending_target.quarantine.{suffix}.json"
    raw = b""
    try:
        raw = source.read_bytes()
    except OSError:
        pass

    observed = payload if isinstance(payload, dict) else {}
    target = observed.get("target") if isinstance(observed.get("target"), dict) else {}
    record: dict[str, Any] = {
        "event": "pending_target_quarantined",
        "portfolio_id": portfolio_id or "flagship",
        "reason": str(reason),
        "quarantined_at": now.isoformat(),
        "source_file": source.name,
        "quarantine_file": destination.name,
        "recoverable": True,
        "expected_contract": ({
            "schema_version": PENDING_TARGET_SCHEMA_V2,
            "engine_version": US_BRAIN_ENGINE_V2,
            "portfolio_id": "autonomous",
            "instrument_policy_version": "single_name_equity.v1",
            "target_weights": (
                "canonical_positively_verified_us_common_stock_only_"
                "finite_long_only_gross_lte_one"
            ),
        } if portfolio_id == "autonomous" else {
            "portfolio_id": portfolio_id or "flagship",
            "instrument_policy_version": (
                "single_name_equity.v1"
                if portfolio_id in {"china", "hk"}
                else None
            ),
            "target_weights": (
                "canonical_positively_verified_single_name_equity_only_"
                "finite_long_only_gross_lte_one"
                if portfolio_id in {"china", "hk"}
                else "canonical_finite_long_only_gross_lte_one"
            ),
        }),
        "observed_contract": {
            "schema_version": observed.get("schema_version"),
            "engine_version": observed.get("engine_version"),
            "portfolio_id": observed.get("portfolio_id"),
        },
        "queued_asof": observed.get("asof"),
        "target_count": len(target),
        "target_symbols": sorted(str(t).upper() for t in target)[:50],
        "source_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
    }
    try:
        source.replace(destination)
        try:
            dir_fd = os.open(data_dir, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            # The atomic rename remains fail-closed where directory fsync is unavailable.
            pass
        record["status"] = "quarantined"
    except Exception as exc:  # noqa: BLE001 - failure remains a hard, non-executing stop
        record["status"] = "quarantine_failed"
        record["recoverable"] = source.exists()
        record["error"] = repr(exc)[:300]

    try:
        _append_jsonl(data_dir / "pending_target_quarantine.jsonl", record)
    except Exception as exc:  # noqa: BLE001 - the shared event below is a second audit sink
        record["audit_ledger_error"] = repr(exc)[:300]
    try:
        from control_plane import run_events
        run_events.append({
            "kind": "pending_target_quarantined",
            "job": "pending_target_contract_guard",
            "book": portfolio_id or "flagship",
            "step": "pre_rebalance_validation",
            "status": "skip",
            "severity": "HARD_STOP",
            "actor": "deterministic_engine",
            "extra": {
                "reason": record["reason"],
                "quarantine_file": record["quarantine_file"],
                "quarantine_status": record["status"],
                "recoverable": record["recoverable"],
                "expected_contract": record["expected_contract"],
                "observed_contract": record["observed_contract"],
                "target_count": record["target_count"],
                "source_sha256": record["source_sha256"],
            },
        })
    except Exception as exc:  # noqa: BLE001 - event logging never re-enables a quarantined target
        record["event_log_error"] = repr(exc)[:300]
    return record


def preflight_pending_target(
    portfolio_id: str | None = None,
    *,
    _locked: bool = False,
) -> dict[str, Any]:
    """Validate queued executable state before any consumer may inspect or rewrite its target.

    This is the single cutover boundary used by settlement, deterministic de-risk, and overnight
    refinement.  Returning ``ok=False`` means the caller must stop immediately: the incompatible
    file has been recoverably quarantined (or its quarantine move failed closed).  Missing queues
    and valid regional legacy queues remain ordinary ``ok=True`` outcomes.
    """
    # Validation and a possible quarantine are one compare-and-act boundary.  Otherwise a valid
    # PM queue written after our read could be renamed based on the stale artifact we inspected.
    if not _locked:
        with _paper_transaction_lock(portfolio_id):
            return preflight_pending_target(portfolio_id, _locked=True)

    # Finish any already-prepared settlement first.  In particular, a crash/failure after account
    # and fills committed but before queue deletion must clear that exact old queue before it can be
    # mistaken for a fresh instruction.
    recover_paper_transaction(portfolio_id)
    raw_pending = _read_pending_target_payload(portfolio_id)
    pending = load_pending_target(portfolio_id)
    if pending is None:
        if pending_target_file_exists(portfolio_id):
            reason = pending_target_contract_error(raw_pending, portfolio_id) or "malformed_payload"
            quarantined = quarantine_pending_target(portfolio_id, reason, raw_pending)
            return {
                "ok": False,
                "skipped": "pending_target_quarantined",
                "quarantined": True,
                "quarantine": quarantined,
                "pending": None,
            }
        return {"ok": True, "pending": None}

    incompatibility = pending_target_contract_error(pending, portfolio_id)
    if incompatibility:
        quarantined = quarantine_pending_target(portfolio_id, incompatibility, pending)
        return {
            "ok": False,
            "skipped": "pending_target_quarantined",
            "quarantined": True,
            "quarantine": quarantined,
            "pending": None,
        }
    return {"ok": True, "pending": pending}


def save_pending_target(
    target_weights: dict[str, float],
    asof: str,
    portfolio_id: str | None = None,
    *,
    decision_snapshot: dict[str, Any] | None = None,
    execution_constraints: dict[str, Any] | None = None,
    require_pending_absent: bool = False,
    _after_save_locked: Callable[[], None] | None = None,
) -> None:
    """Atomically persist the latest decided target and its accepted PM provenance.

    ``decision_snapshot`` is optional for backward-compatible/operator queues.  All active Brain
    loops provide it.  When present, it is embedded in the same atomic file and hash-bound to the
    numeric target, so a later failed refinement cannot erase or misattribute the eventual fill.
    ``execution_constraints`` is privileged and normally absent; only the hash-bound autonomous
    legacy-ETF operator migration may request exact-share preservation.  Every writer serializes on
    the paper-transaction lock.  ``require_pending_absent`` upgrades the operator migration's
    pre-save observation into an atomic compare-and-swap; generic PM writers retain latest-wins.
    """
    target = validate_target_weights(
        target_weights,
        portfolio_id=portfolio_id,
    )
    decision = _pending_decision_record(
        decision_snapshot,
        target=target,
        asof=asof,
        portfolio_id=portfolio_id,
    )
    if decision is not None:
        # Once an accepted queue was atomically paired with a decision-ledger claim, deterministic
        # risk rewrites must retain that reconciliation requirement.  A later rewrite has no new
        # callback because it inherits the original decision; clearing the flag would let a
        # missing/mismatched row masquerade as a pre-ledger legacy queue at settlement.
        decision["decision_log_required"] = bool(
            decision.get("decision_log_required") is True
            or _after_save_locked is not None
        )
    constraints = _validated_execution_constraints(
        execution_constraints,
        target=target,
        decision_snapshot=decision,
        portfolio_id=portfolio_id,
    )
    payload = {
        "target": target,
        "asof": asof,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }
    if decision is not None:
        payload["decision_snapshot"] = decision
    if constraints is not None:
        payload["execution_constraints"] = constraints
    if portfolio_id == "autonomous":
        payload.update({
            "schema_version": PENDING_TARGET_SCHEMA_V2,
            "engine_version": US_BRAIN_ENGINE_V2,
            "portfolio_id": "autonomous",
        })
    if portfolio_id in {"autonomous", "china", "hk"}:
        from portfolio import instrument_policy

        payload["asset_policy"] = instrument_policy.POLICY_NAME
        payload["instrument_policy_version"] = instrument_policy.POLICY_VERSION
        payload["portfolio_id"] = portfolio_id
    if not isinstance(require_pending_absent, bool):
        raise TypeError("require_pending_absent must be boolean")
    if _after_save_locked is not None and not callable(_after_save_locked):
        raise TypeError("_after_save_locked must be callable")
    with _paper_transaction_lock(portfolio_id):
        path = _pending_target_path(portfolio_id)
        if constraints is not None:
            if _transaction_path(portfolio_id).exists():
                raise PaperTransactionConflict(
                    "cannot queue operator migration with an unresolved paper transaction"
                )
            current_account = _load_account_file(portfolio_id, strict=True)
            if positions_sha256(current_account.get("positions")) != constraints.get(
                "positions_sha256"
            ):
                raise InvalidExecutionConstraints(
                    "positions_snapshot_changed_before_queue"
                )
        if require_pending_absent and path.exists():
            raise PendingTargetCASConflict(portfolio_id)
        prior_payload = path.read_bytes() if path.exists() else None
        _atomic_write_bytes(
            path,
            json.dumps(payload, indent=2, default=str).encode("utf-8"),
        )
        if _after_save_locked is not None:
            try:
                _after_save_locked()
            except Exception:
                # The queue and its user-facing decision claim are one logical publication.
                # Restore the prior executable intent when that projection cannot be written.
                if prior_payload is None:
                    _durable_unlink(path)
                else:
                    _atomic_write_bytes(path, prior_payload)
                raise


def _read_pending_target_payload(portfolio_id: str | None = None) -> dict | None:
    """Parse the queued target without validating or mutating it (preflight owns quarantine)."""
    try:
        p = _pending_target_path(portfolio_id)
        if p.exists():
            d = json.loads(p.read_text())
            if isinstance(d, dict) and isinstance(d.get("target"), dict):
                return d
    except Exception:
        pass
    return None


def load_pending_target(portfolio_id: str | None = None) -> dict | None:
    """Return a valid queued target, or ``None`` for missing/corrupt/incompatible state.

    Settlement consumers must use ``preflight_pending_target`` so an invalid executable artifact is
    quarantined with an audit record.  This read helper still applies the identical shared validator
    and never hands malformed weights to a caller.
    """
    payload = _read_pending_target_payload(portfolio_id)
    if pending_target_contract_error(payload, portfolio_id):
        return None
    return payload


def clear_pending_target(portfolio_id: str | None = None) -> None:
    _durable_unlink(_pending_target_path(portfolio_id))


def settle_target(prices: dict[str, float], asof: str,
                  portfolio_id: str | None = None, *,
                  _price_sources: dict[str, str] | None = None,
                  _locked: bool = False) -> dict | None:
    """If a target was queued while the market was closed, rebalance to it now (at the open marks)
    and clear it. Returns the settled target dict, or None if nothing was queued. Paper-only.

    The autonomous-book contract is validated before ``rebalance``.  A legacy/unversioned target is
    quarantined in place and raises ``PendingTargetQuarantined``; current holdings remain untouched.
    If any positive target or intended full exit lacks a trusted price,
    ``UnpriceableExitPrices`` is raised before an account write and the pending target is retained
    for a later retry.
    """
    try:
        canonical_asof = date.fromisoformat(asof).isoformat()
    except (TypeError, ValueError) as exc:
        raise PaperTransactionConflict("settlement asof is not a canonical ISO date") from exc
    if asof != canonical_asof:
        raise PaperTransactionConflict("settlement asof is not a canonical ISO date")
    if not _locked:
        with _paper_transaction_lock(portfolio_id):
            return settle_target(
                prices,
                asof,
                portfolio_id=portfolio_id,
                _price_sources=_price_sources,
                _locked=True,
            )
    preflight = preflight_pending_target(portfolio_id)
    if not preflight["ok"]:
        raise PendingTargetQuarantined(preflight["quarantine"])
    pt = preflight["pending"]
    if not pt:
        return None
    # A modern Brain queue and its user-facing ledger row are one logical publication.  A crash
    # between the two durable file writes must fail before account/fill mutation, not after it.
    decision_snapshot = pt.get("decision_snapshot")
    if isinstance(decision_snapshot, dict) and (
        decision_snapshot.get("decision_log_required") is True
    ):
        try:
            from bot import decision_rows
            decision_rows.validate_queued_decision_snapshot(
                str(portfolio_id or "flagship"), decision_snapshot
            )
        except Exception as exc:
            raise PaperTransactionConflict(
                f"required queued decision projection is unavailable: {exc}"
            ) from exc
    # Preflight already applied this validator in strict-persisted mode.  Re-validate here to close
    # a future refactor/TOCTOU seam and to pass canonical weights into the rebalance engine.
    target = validate_target_weights(
        pt.get("target") or {},
        require_canonical_tickers=True,
        portfolio_id=portfolio_id,
    )
    constraints = _validated_execution_constraints(
        pt.get("execution_constraints") if "execution_constraints" in pt else None,
        target=target,
        decision_snapshot=pt.get("decision_snapshot"),
        portfolio_id=portfolio_id,
    )
    preserve_existing_shares = (
        frozenset(constraints["tickers"]) if constraints is not None else None
    )
    preserve_positions_sha256 = (
        constraints["positions_sha256"] if constraints is not None else None
    )
    missing_prices = unpriceable_target_requirements(
        target,
        prices,
        portfolio_id=portfolio_id,
    )
    # A target settlement also writes the dated benchmark-relative NAV projection.  Capture that
    # benchmark mark in the same immutable transaction preimage as the execution prices.  Reject a
    # low-level caller before account/fill mutation when it omits the benchmark; otherwise the
    # commit would manufacture an outbox receipt that can never pass finalization.
    from portfolio import registry
    benchmark = registry.benchmark(portfolio_id)
    if not _trusted_execution_price(prices.get(benchmark)):
        missing_prices["tickers"] = sorted(
            set(missing_prices["tickers"]) | {benchmark}
        )
    if missing_prices["tickers"]:
        raise UnpriceableExitPrices(
            missing_prices["tickers"],
            portfolio_id,
            exit_tickers=missing_prices["exit_tickers"],
            positive_target_tickers=missing_prices["positive_target_tickers"],
        )
    followup = _pending_clear_transition(
        portfolio_id, prices=prices, price_sources=_price_sources
    )
    rebalance(
        target,
        prices,
        asof,
        portfolio_id=portfolio_id,
        _followup=followup,
        _preserve_existing_shares=preserve_existing_shares,
        _preserve_positions_sha256=preserve_positions_sha256,
    )
    # Test doubles and older embedders may replace ``rebalance`` with a compatible callable that
    # ignores the private transaction follow-up.  Clear only if the exact original target still
    # remains and no WAL is outstanding; a newer target is never removed here.
    if (
        not _transaction_path(portfolio_id).exists()
        and _file_sha256(_pending_target_path(portfolio_id)) == followup.get("before_sha256")
    ):
        clear_pending_target(portfolio_id)
    return target


def mark(prices: dict[str, float], asof: str, portfolio_id: str | None = None,
         benchmark: str | None = None, *,
         mark_source: str = "paper_account_mark",
         _settlement_receipt_id: str | None = None,
         _locked: bool = False) -> None:
    """Snapshot NAV to nav_history.jsonl. Also initialises the benchmark shares on first call.

    The benchmark symbol is registry-resolved per book. Its normalized shares remain in the
    back-compat ``spy_shares`` slot, while ``benchmark_symbol`` records which index those shares
    belong to so a benchmark change can never reuse the old instrument's scale."""
    if not _locked:
        with _paper_transaction_lock(portfolio_id):
            return mark(
                prices,
                asof,
                portfolio_id=portfolio_id,
                benchmark=benchmark,
                mark_source=mark_source,
                _settlement_receipt_id=_settlement_receipt_id,
                _locked=True,
            )
    receipts = pending_settlement_receipts(portfolio_id)
    if receipts:
        if (
            len(receipts) != 1
            or _settlement_receipt_id != receipts[0].get("transaction_id")
            or mark_source != "settlement_receipt"
        ):
            raise PaperTransactionConflict(
                "NAV mark blocked by an unfinalized settlement receipt"
            )
    elif _settlement_receipt_id is not None:
        raise PaperTransactionConflict("NAV mark settlement receipt is unavailable")
    state = _load_account(portfolio_id)
    bench = benchmark or _benchmark_for(portfolio_id)

    nav_path = _paths(portfolio_id)["nav"]

    # Initialise the benchmark on first mark. Regional books historically used FXI without storing
    # the symbol; infer that legacy state once, then reset the normalized benchmark at $1M when the
    # configured instrument changes to CSI 300 / Hang Seng. Portfolio NAV and holdings are untouched.
    spy_px = prices.get(bench)
    stored_benchmark = state.get("benchmark_symbol")
    if stored_benchmark is None and state.get("spy_shares") is not None:
        stored_benchmark = "FXI" if portfolio_id in {"china", "hk"} else "SPY"
    if spy_px and spy_px > 0 and (
            state.get("spy_shares") is None or stored_benchmark != bench):
        state["spy_shares"] = _STARTING_NAV / spy_px
        state["spy_inception_price"] = spy_px
        state["benchmark_symbol"] = bench
        _save_account(state, portfolio_id)
    elif spy_px and spy_px > 0 and state.get("benchmark_symbol") is None:
        state["benchmark_symbol"] = bench
        _save_account(state, portfolio_id)

    # Persist each held position's latest *observed* mark so closed-market readers can value the
    # account at its last completed mark.  A missing quote MUST NOT overwrite that evidence with
    # avg_cost: doing so turns an absent feed into a fabricated zero P&L and destroys the only EOD
    # price the dashboard can carry overnight.  The mark's date/source travel with the value, and a
    # backfill for an older date cannot roll a newer stored mark backward.  This metadata is display
    # provenance only; execution continues to require the explicit ``prices`` argument elsewhere.
    _marked_any = False
    _mark_asof = str(asof)[:10]
    _mark_source = str(mark_source or "paper_account_mark").strip() or "paper_account_mark"
    for ticker, pos in state["positions"].items():
        px = prices.get(ticker)
        try:
            px = float(px) if px is not None else None
        except (TypeError, ValueError):
            px = None
        if px is None or not math.isfinite(px) or px <= 0:
            continue
        previous_asof = str(pos.get("current_price_asof") or "")[:10]
        try:
            if previous_asof and date.fromisoformat(previous_asof) > date.fromisoformat(_mark_asof):
                continue
        except (TypeError, ValueError):
            pass
        pos["current_price"] = round(px, 4)
        pos["current_price_asof"] = _mark_asof
        pos["current_price_source"] = _mark_source
        pos["current_price_time_kind"] = "portfolio_mark_date"
        _marked_any = True
    if _marked_any:
        _save_account(state, portfolio_id)

    current_nav = state["cash"] + sum(
        pos["shares"] * prices.get(ticker, pos["avg_cost"])
        for ticker, pos in state["positions"].items()
    )
    invested = current_nav - state["cash"]

    spy_nav: float | None = None
    if state.get("spy_shares") and spy_px:
        spy_nav = state["spy_shares"] * spy_px

    record = {
        "date": asof,
        "nav": round(current_nav, 2),
        "cash": round(state["cash"], 2),
        "invested": round(invested, 2),
        "spy_nav": round(spy_nav, 2) if spy_nav is not None else None,
        "benchmark": bench,
    }
    # idempotent per date: keep exactly one NAV row per calendar date (replace, don't
    # append) so repeated book builds on the same day don't pile up duplicate points.
    rows: list[dict] = []
    if nav_path.exists():
        for line in nav_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("date") != asof:
                rows.append(r)
    rows.append(record)
    # A delayed receipt retry may repair an older settlement date after newer daily marks exist.
    # Preserve chronological ledger order so readers that consume the final/previous rows never
    # mistake the repaired older mark for the current session.
    rows.sort(key=lambda row: str(row.get("date") or ""))
    _ensure_dir(portfolio_id)
    _atomic_write_bytes(
        nav_path,
        ("\n".join(json.dumps(r, default=str) for r in rows) + "\n").encode("utf-8"),
    )


# ---------------------------------------------------------------------------
# benchmark history loader (used by performance() for the comparison line only)
# ---------------------------------------------------------------------------

def _load_spy_history(window: int = 91, symbol: str = "SPY") -> "list[tuple[str, float]] | list":
    """Return [(date_str, close), ...] for the benchmark `symbol` over the last `window` sessions.

    Uses the same store loader as _fetch_price_series so it works offline as
    long as the engine price cache is populated.  Returns [] if unavailable.
    """
    s = _fetch_price_series(symbol)
    if s is None or len(s) == 0:
        return []
    try:
        s = s.sort_index().tail(window)
        return [(idx.date().isoformat(), float(v)) for idx, v in s.items()]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# /api/performance payload
# ---------------------------------------------------------------------------

def performance(portfolio_id: str | None = None,
                prices: dict[str, float] | None = None) -> dict:
    """Assemble the /api/performance contract.

    Series is HONEST:
      - spy_nav = the configured benchmark's real history normalised to $1,000,000 at the first
        date of the window (legacy field name retained for existing chart/API consumers).
      - nav (our portfolio) = $1,000,000 FLAT for every date before
        inception_date; from inception onward it uses the real marked NAV from
        nav_history.jsonl.  No hypothetical repricing of our allocation ever.
      - kind = "pre_inception" for the flat prefix, "realized" from inception.

    `prices` (TICKER → price in the book's BASE currency, e.g. live delayed quotes for the US
    books, snapshot/FX marks for HK/China) makes `current_nav` LIVE: the CURRENT account holdings
    are valued now (cash + live market value — realized P&L is already booked into cash) instead of
    freezing on the last once-daily nav_history snapshot. Without it the function degrades to the
    last realized row (back-compat). This is what makes the dashboard NAV move intraday.

    Returns a safe minimal payload on error.
    """
    bench = _benchmark_for(portfolio_id)
    try:
        from portfolio import registry
        bench_name = registry.benchmark_name(portfolio_id)
        bench_name_zh = registry.benchmark_name_zh(portfolio_id)
    except Exception:
        bench_name = bench
        bench_name_zh = bench

    _base: dict[str, Any] = {
        "inception_date": _INCEPTION_DATE,
        "starting_nav": _STARTING_NAV,
        "current_nav": _STARTING_NAV,
        "cash": _STARTING_NAV,
        "invested": 0.0,
        "total_return_pct": 0.0,
        "vs_benchmark_pct": None,
        "vs_spy_pct": None,  # backward-compatible key; value is always versus ``benchmark``
        "benchmark": bench,
        "benchmark_name": bench_name,
        "benchmark_name_zh": bench_name_zh,
        "benchmark_as_of": None,
        "day_change_pct": 0.0,
        "max_drawdown_pct": 0.0,
        "realized_since": _INCEPTION_DATE,
        "series": [],
        "note": "No data yet — run the book build to initialise.",
    }

    try:
        state = _load_account(portfolio_id)
        realized_rows = _load_jsonl(_paths(portfolio_id)["nav"])

        inception_date = state.get("inception_date", _INCEPTION_DATE)

        try:
            today_iso = date.today().isoformat()
        except Exception:
            today_iso = ""

        # LIVE current values: when the caller passes today's marks (base ccy), value the CURRENT
        # account holdings now (cash + live market value) instead of freezing on the last daily
        # nav_history snapshot — this is what moves the NAV intraday. Fall back to the last realized
        # row, then to starting NAV.
        live_nav: float | None = None
        if prices:
            try:
                live_nav = nav(prices, portfolio_id)
            except Exception:
                live_nav = None

        if live_nav is not None:
            current_nav = live_nav
            cash = float(state.get("cash", _STARTING_NAV))
            invested = current_nav - cash
            spy_nav_latest = realized_rows[-1].get("spy_nav") if realized_rows else None
        elif realized_rows:
            latest = realized_rows[-1]
            current_nav = float(latest["nav"])
            cash = float(latest["cash"])
            invested = float(latest.get("invested", 0.0))
            spy_nav_latest = latest.get("spy_nav")
        else:
            current_nav = _STARTING_NAV
            cash = state.get("cash", _STARTING_NAV)
            invested = 0.0
            spy_nav_latest = None

        total_return_pct = (current_nav - _STARTING_NAV) / _STARTING_NAV * 100

        # Compare like-for-like SINCE INCEPTION using the currently configured benchmark's own
        # history. This avoids relabeling persisted FXI rows as CSI 300 / Hang Seng during the
        # migration. The legacy spy_nav path is retained only when it is provably the same symbol.
        benchmark_history = _load_spy_history(504, bench)
        benchmark_since = [
            (d, px) for d, px in benchmark_history
            if d >= inception_date and (not today_iso or d <= today_iso) and px > 0
        ]
        vs_benchmark_pct: float | None = None
        if benchmark_since:
            benchmark_return = (
                float(benchmark_since[-1][1]) / float(benchmark_since[0][1]) - 1.0
            ) * 100
            vs_benchmark_pct = round(total_return_pct - benchmark_return, 4)
        elif spy_nav_latest:
            latest_benchmark = realized_rows[-1].get("benchmark") if realized_rows else None
            persisted_matches = (
                latest_benchmark == bench or (latest_benchmark is None and bench == "SPY")
            )
            if persisted_matches:
                benchmark_return = (
                    float(spy_nav_latest) - _STARTING_NAV
                ) / _STARTING_NAV * 100
                vs_benchmark_pct = round(total_return_pct - benchmark_return, 4)

        # day-over-day change. With a live mark, compare to the last daily close STRICTLY before
        # today (so we don't divide by today's own frozen snapshot); otherwise the prior row.
        day_change_pct: float = 0.0
        if live_nav is not None:
            prior = [r for r in realized_rows if (r.get("date") or "") < today_iso]
            if prior:
                prev_nav = float(prior[-1]["nav"])
                if prev_nav > 0:
                    day_change_pct = round((current_nav - prev_nav) / prev_nav * 100, 4)
        elif len(realized_rows) >= 2:
            prev_nav = float(realized_rows[-2]["nav"])
            if prev_nav > 0:
                day_change_pct = round((current_nav - prev_nav) / prev_nav * 100, 4)

        # max drawdown over realized track only
        import numpy as np
        nav_arr = [float(r["nav"]) for r in realized_rows]
        max_drawdown_pct = 0.0
        if len(nav_arr) > 1:
            running_max = np.maximum.accumulate(nav_arr)
            drawdowns = (np.array(nav_arr) - running_max) / running_max * 100
            max_drawdown_pct = round(float(drawdowns.min()), 4)

        # ---- build series ----
        # Use the tail for the chart; the full history above is reserved for since-inception alpha.
        spy_history = benchmark_history[-91:]

        series: list[dict] = []

        if spy_history:
            # Normalise the configured benchmark so spy_nav == $1M at the window's first date.
            spy0 = spy_history[0][1]
            spy_scale = _STARTING_NAV / spy0 if spy0 > 0 else 1.0

            # Build a quick lookup from the realized rows for nav by date
            realized_by_date: dict[str, float] = {
                r["date"]: float(r["nav"]) for r in realized_rows
            }
            # keep the chart endpoint in step with the live header NAV
            if live_nav is not None and today_iso:
                realized_by_date[today_iso] = current_nav

            for date_str, spy_close in spy_history:
                spy_nav_val = round(spy_close * spy_scale, 2)

                if date_str < inception_date:
                    # Pre-inception: our portfolio is flat at $1M — we did not exist yet
                    series.append({
                        "date": date_str,
                        "nav": _STARTING_NAV,
                        "spy_nav": spy_nav_val,
                        "kind": "pre_inception",
                    })
                else:
                    # Realized: use real NAV from nav_history.jsonl if available,
                    # otherwise stay flat (today's book hasn't run yet)
                    nav_val = realized_by_date.get(date_str, _STARTING_NAV)
                    series.append({
                        "date": date_str,
                        "nav": nav_val,
                        "spy_nav": spy_nav_val,
                        "kind": "realized",
                    })
        else:
            # No current benchmark history: emit realized rows, but never relabel legacy FXI values
            # as a native regional index. Unlabelled legacy rows are accepted only for SPY books.
            for r in realized_rows:
                nav_val = float(r["nav"])
                if live_nav is not None and today_iso and r.get("date") == today_iso:
                    nav_val = current_nav      # live-mark today's point
                row_benchmark = r.get("benchmark")
                benchmark_matches = (
                    row_benchmark == bench or (row_benchmark is None and bench == "SPY")
                )
                series.append({
                    "date": r["date"],
                    "nav": nav_val,
                    "spy_nav": (
                        float(r["spy_nav"])
                        if benchmark_matches and r.get("spy_nav") is not None else None
                    ),
                    "kind": "realized",
                })

        note = (
            f"Portfolio starts at ${_STARTING_NAV:,.0f} on {inception_date}; "
            "flat until the live daily track accrues. "
            f"{bench} shown over the same window for comparison (real history)."
        )

        return {
            "inception_date": inception_date,
            "starting_nav": _STARTING_NAV,
            "current_nav": round(current_nav, 2),
            "cash": round(cash, 2),
            "invested": round(invested, 2),
            "total_return_pct": round(total_return_pct, 4),
            "vs_benchmark_pct": vs_benchmark_pct,
            "vs_spy_pct": vs_benchmark_pct,
            "benchmark": bench,
            "benchmark_name": bench_name,
            "benchmark_name_zh": bench_name_zh,
            "benchmark_as_of": benchmark_history[-1][0] if benchmark_history else None,
            "day_change_pct": day_change_pct,
            "max_drawdown_pct": max_drawdown_pct,
            "realized_since": inception_date,
            "series": series,
            "note": note,
        }
    except Exception as exc:
        _base["note"] = f"Performance unavailable: {exc}"
        return _base
