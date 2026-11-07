"""Trial Ledger — honest multiple-testing accounting for the Deflated Sharpe gate.

The Deflated Sharpe Ratio (engine.validation.deflated_sharpe) deflates a hand-picked
"best" Sharpe for the number of configs ``N`` that were tried. Today every caller
passes that ``N`` as a literal int — and a caller can LOWBALL it (report ``n_trials=4``
for a 40-config search), which silently makes the haircut too lenient. That is the
single biggest p-hacking surface in the calibration suite.

The Trial Ledger removes the caller's discretion: every config a search touches is
logged AT GENERATION (not at backtest) to an append-only JSONL, keyed by a ``family``
(the signal/strategy whose multiple-testing budget is being spent). ``deflated_sharpe``
then reads the family's honest distinct-config count from the ledger instead of
trusting a number the caller chose.

Counting at GENERATION is deliberate: multiple testing is incurred when you GENERATE
and evaluate a candidate, not only when one survives to a headline backtest. A breadth
fan-out that enumerates 200 transforms and reports the best spent 200 trials, not 1.

``effective_n()`` is conservative by construction: it counts every DISTINCT config in
the family (dedup by content hash so a re-run does not inflate ``N``). Correlation
credit — the claim that near-duplicate trials should count as fewer independent tests —
is the gaming direction, so it is OFF by default and, when explicitly enabled, is
hard-floored at ``ceil(sqrt(literal_N))`` and can never make the haircut more lenient
than that floor.

Design notes
------------
* Pure stdlib (hashlib/json/math/datetime/pathlib/threading) so the thin data-bot env
  stays thin, matching engine/validation.py's "no scipy/sklearn" rule.
* Append-only + dedup-by-(family, config-hash): re-running a calibrator is idempotent
  (N does not grow), but a genuinely new config does grow it.
* The on-disk file persists across nightly CI builds the same way
  ``data/ai_desk/theses.jsonl`` does — it IS the multiple-testing memory.
* ``deflated_sharpe`` duck-types the ledger (it only calls ``.effective_n(family)``),
  so engine/validation.py keeps zero import coupling to this module.
"""
from __future__ import annotations

import hashlib
import fcntl
import json
import math
import os
import stat
import tempfile
import threading
import time
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path

# The canonical persistent ledger — committed + appended in CI, like theses.jsonl.
DEFAULT_PATH = Path("data") / "trial_ledger.jsonl"

_WRITE_LOCK = threading.RLock()
_ACTIVE_OWNER = threading.local()
MAX_LEDGER_BYTES = 64 * 1024 * 1024


class TrialLedgerError(OSError):
    """Storage identity, history or durability could not be established."""


def _identity(info):
    return info.st_dev, info.st_ino


def _regular(fd):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise TrialLedgerError("ledger and lock must be regular single-link files")
    return info


def _same_file(directory, name, fd):
    info = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode) or _identity(info) != _identity(_regular(fd)):
        raise TrialLedgerError("ledger path identity changed")


@contextmanager
def _directory(path, *, create=False):
    """Bind every directory component without following a replaced/symlink path."""
    descriptors = [os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)]
    bindings = []
    try:
        for name in path.parts[1:]:
            parent = descriptors[-1]
            if create:
                try:
                    os.mkdir(name, 0o700, dir_fd=parent)
                    os.fsync(parent)
                except FileExistsError:
                    pass
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=parent)
            descriptors.append(child)
            bindings.append((parent, name, child))
        def check():
            for parent, name, child in bindings:
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if not stat.S_ISDIR(info.st_mode) or _identity(info) != _identity(os.fstat(child)):
                    raise TrialLedgerError("ledger directory identity changed")
        check()
        yield descriptors[-1], check
        check()
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def _read(directory, name):
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directory)
    except FileNotFoundError:
        return None, None
    try:
        before = _regular(fd)
        if before.st_size > MAX_LEDGER_BYTES:
            raise TrialLedgerError("ledger exceeds bounded read size")
        chunks, total = [], 0
        while True:
            chunk = os.read(fd, min(65536, MAX_LEDGER_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_LEDGER_BYTES:
                raise TrialLedgerError("ledger exceeds bounded read size")
        after = _regular(fd)
        _same_file(directory, name, fd)
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, field) != getattr(after, field) for field in fields):
            raise TrialLedgerError("ledger changed during read")
        return b"".join(chunks), _identity(after)
    finally:
        os.close(fd)


def _serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._instance_lock:
            return method(self, *args, **kwargs)
    return call


def _strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate ledger JSON key")
        result[key] = value
    return result


def _strict_constant(value):
    raise ValueError("nonfinite ledger JSON")


def _strict_row(row):
    if type(row) is not dict:
        raise ValueError("ledger row must be an object")
    json.dumps(row, allow_nan=False)  # Also reject finite JSON tokens that overflow to inf.
    fam, digest, timestamp = row.get("family"), row.get("config_hash"), row.get("ts")
    if (type(fam) is not str or not fam or type(digest) is not str
            or len(digest) != 16 or any(c not in "0123456789abcdef" for c in digest)
            or type(timestamp) is not str):
        raise ValueError("invalid ledger identity")
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise ValueError("ledger timestamp must be UTC")
    if row.get("kind") == "declared_budget":
        if (set(row) != {"ts", "family", "kind", "n", "reason", "config_hash"}
                or type(row["n"]) is not int or row["n"] < 1
                or (row["reason"] is not None and type(row["reason"]) is not str)):
            raise ValueError("invalid declared budget")
        config = {"__declared_budget__": row["n"], "reason": row["reason"]}
    else:
        if (set(row) != {"ts", "family", "config_hash", "config", "source", "info_cutoff", "note"}
                or type(row["source"]) is not str
                or (row["note"] is not None and type(row["note"]) is not str)):
            raise ValueError("invalid generated trial")
        config = row["config"]
    if _hash(fam, config) != digest:
        raise ValueError("ledger configuration hash mismatch")
    return (fam, digest), _canon(config)


_LEGACY_REGISTRY_KEYS = frozenset({"earliest_verdict", "fdr_family", "hypothesis", "n",
                                   "status", "trial_id", "ts", "verdict_criteria"})
_LEGACY_ANNOTATION_KINDS = frozenset({"amendment", "filing_budget"})


def _legacy_record(row) -> bool:
    """An identity-less row that names no trial, which the tolerant loader skipped
    before WP06 and still skips (counted in ``legacy_rows``, never as corrupt).
    Exactly two shapes qualify: a foreign prereg-registry record (no ledger identity
    key, a non-empty string ``trial_id``, and only ``_LEGACY_REGISTRY_KEYS``) and an
    annotation (a non-empty string ``family`` and a ``kind`` in
    ``_LEGACY_ANNOTATION_KINDS``, never a ``config_hash`` or ``config``). This is not
    a frozen historical set: ``scripts/causal_ingest_brainstorm.py`` still appends a
    ``filing_budget`` row for every causal-scan card it files. Neither shape counts
    toward N or signals a torn or tampered history. Every other row without a valid
    identity, including an annotation of any other kind, stays corrupt; strict reads
    accept neither shape."""
    if not any(k in row for k in ("family", "config_hash", "kind", "config")):
        trial_id = row.get("trial_id")
        return (type(trial_id) is str and bool(trial_id)
                and set(row) <= _LEGACY_REGISTRY_KEYS)
    kind, fam = row.get("kind"), row.get("family")
    return (type(kind) is str and kind in _LEGACY_ANNOTATION_KINDS
            and type(fam) is str and bool(fam)
            and "config_hash" not in row and "config" not in row)


def _canon(config) -> str:
    """Stable, order-independent JSON encoding of a config for hashing.

    Accepts dicts / lists / tuples / scalars; ``default=str`` lets exotic values
    (numpy scalars, Paths) hash deterministically without importing numpy here."""
    return json.dumps(config, sort_keys=True, default=str, separators=(",", ":"))


def _hash(family: str, config) -> str:
    return hashlib.sha1(f"{family}\x00{_canon(config)}".encode("utf-8")).hexdigest()[:16]


class TrialLedger:
    """Append-only record of every config tried per signal family.

    Usage (in a calibrator, log the WHOLE grid at generation — before backtesting)::

        led = TrialLedger(family="commodity_tsmom")
        led.log_grid(GRID, info_cutoff="2026-06-20")        # count every config tried
        ...
        dsr = deflated_sharpe(sr, sk, ku, T, ledger=led, family="commodity_tsmom")

    The ``family`` namespaces a multiple-testing budget: all configs that compete to
    produce one headline result share a family, so the DSR deflates by the full count.
    """

    def __init__(self, path: str | Path | None = None, family: str | None = None) -> None:
        self.path = Path(path) if path is not None else DEFAULT_PATH
        self._storage_path = Path(os.path.abspath(self.path))
        self._path_spelling = str(self.path)
        self._instance_lock = threading.RLock()
        self._transaction = None
        self._known_raw = None
        # Identity is an observed fact, retained even after a failed write.
        self._known_file_identity = None
        self._ever_file = False
        self._allow_genesis = False
        self.default_family = family
        # family -> set(config_hash); rebuilt from disk so counts survive process restarts
        self._seen: dict[str, set[str]] = {}
        # family -> max declared research budget (a floor on effective_n; see log_declared_budget)
        self._declared: dict[str, int] = {}
        self._declared_seen: set[str] = set()
        # durability diagnostics (C19 WP06): set BEFORE _load() so the load itself
        # can record them. An unreadable ledger still loads EMPTY — the policy is
        # unchanged; it is now RECORDED, not silently swallowed. legacy_rows counts
        # identity-less registry and annotation rows, including the live causal
        # filing_budget channel (see _legacy_record): skipped, never corrupt.
        self.corrupt_lines: int = 0
        self.legacy_rows: int = 0
        self.load_error: str | None = None
        self._load()

    # -- internals --------------------------------------------------------- #
    def _load(self) -> None:
        """Legacy tolerant load with explicit diagnostics; never create storage."""
        self._seen, self._declared, self._declared_seen = {}, {}, set()
        self.corrupt_lines, self.legacy_rows, self.load_error = 0, 0, None
        try:
            with _directory(self._storage_path.parent) as (directory, _):
                raw, file_identity = _read(directory, self._storage_path.name)
            if raw is not None:
                self._ever_file = True
                self._known_file_identity = file_identity
                self._decode(raw, strict=False)
                self._known_raw = raw
        except FileNotFoundError:
            return  # A never-created ledger remains a tolerated legacy read.
        except (OSError, UnicodeError) as exc:
            self.load_error = f"{type(exc).__name__}: {exc}"

    def _decode(self, raw, *, strict):
        seen, declared, declared_seen, corrupt, legacy, identities = {}, {}, set(), 0, 0, {}
        if strict and raw and not raw.endswith(b"\n"):
            raise TrialLedgerError("ledger has an incomplete final line")
        for line in raw.decode("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = (json.loads(line, object_pairs_hook=_strict_pairs,
                                  parse_constant=_strict_constant) if strict else json.loads(line))
                if type(row) is not dict:
                    raise ValueError("ledger row must be an object")
                if not strict and _legacy_record(row):
                    legacy += 1
                    continue
                if strict:
                    key, config = _strict_row(row)
                    if key in identities and identities[key] != config:
                        raise ValueError("ledger short-hash collision")
                    identities[key] = config
                fam, h = row.get("family"), row.get("config_hash")
                if not isinstance(fam, str) or not fam or not isinstance(h, str) or not h:
                    raise ValueError("invalid ledger identity")
                if row.get("kind") == "declared_budget":
                    n = row.get("n")
                    if not isinstance(n, int):
                        raise ValueError("invalid declared count")
                    declared[fam] = max(declared.get(fam, 0), n)
                    declared_seen.add(h)
                else:
                    seen.setdefault(fam, set()).add(h)
            except (ValueError, TypeError, OverflowError, RecursionError) as exc:
                if strict:
                    raise TrialLedgerError("strict ledger history refused") from exc
                corrupt += 1
        self._seen, self._declared, self._declared_seen = seen, declared, declared_seen
        self.corrupt_lines, self.legacy_rows, self.load_error = corrupt, legacy, None

    @contextmanager
    def owner_transaction(self, *, strict=False):
        """Serialize a fresh history read, full generation and raw readback.

        This storage boundary is not owner authentication or an original-history
        grant. Strict callers must precreate their genuine initial fixture and
        independently verify its original byte anchor. A nested call may reuse
        this same instance only. A different nested owner refuses before flock.
        A successful outer exit is required before publishing a consumer receipt.
        """
        if type(strict) is not bool:
            raise ValueError("strict must be a boolean")
        with _WRITE_LOCK:
            active = getattr(_ACTIVE_OWNER, "owner", None)
            if active is not None:
                if active is not self:
                    raise RuntimeError("nested different ledger owners are unsupported")
                if strict and not self._transaction["strict"]:
                    raw = self.raw_readback()
                    self._decode(raw, strict=True)
                    self._transaction["strict"] = True
                yield self
                return
            with self._instance_lock:
                if str(self.path) != self._path_spelling:
                    raise TrialLedgerError("ledger path changed after construction")
                previous = ({k: set(v) for k, v in self._seen.items()}, dict(self._declared),
                            set(self._declared_seen), self.corrupt_lines, self.legacy_rows,
                            self.load_error, self._known_raw)
                try:
                    with _directory(self._storage_path.parent, create=not strict) as (directory, check):
                        lockname = "." + self._storage_path.name + ".lock"
                        flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
                        created = False
                        try:
                            lockfd = os.open(lockname, flags | os.O_CREAT | os.O_EXCL,
                                             0o600, dir_fd=directory)
                            created = True
                        except FileExistsError:
                            lockfd = os.open(lockname, flags, dir_fd=directory)
                        try:
                            _regular(lockfd)
                            if created:
                                os.fsync(lockfd)
                                os.fsync(directory)
                            deadline = time.monotonic() + 30.0
                            while True:
                                try:
                                    fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                                    break
                                except BlockingIOError:
                                    if time.monotonic() >= deadline:
                                        raise TrialLedgerError("ledger writer lock timed out")
                                    time.sleep(0.01)
                            _same_file(directory, lockname, lockfd)
                            check()
                            raw, file_identity = _read(directory, self._storage_path.name)
                            if (raw is None and not strict and not created
                                    and not self._ever_file and not self._allow_genesis):
                                # The exclusive sidecar creator may not yet have
                                # acquired flock. Yield that lock briefly so it can
                                # establish the first file. Never create on its
                                # behalf or infer that missing history is empty.
                                initial_until = time.monotonic() + 1.0
                                while raw is None and time.monotonic() < initial_until:
                                    fcntl.flock(lockfd, fcntl.LOCK_UN)
                                    time.sleep(0.01)
                                    while True:
                                        try:
                                            fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                                            break
                                        except BlockingIOError:
                                            if time.monotonic() >= deadline:
                                                raise TrialLedgerError("ledger writer lock timed out")
                                            time.sleep(0.01)
                                    _same_file(directory, lockname, lockfd)
                                    check()
                                    raw, file_identity = _read(directory, self._storage_path.name)
                            if raw is None:
                                if strict or self._ever_file or not (created or self._allow_genesis):
                                    raise TrialLedgerError("missing original ledger history")
                                self._allow_genesis = True
                                raw = b""
                            else:
                                self._ever_file = True
                            if self._known_raw is not None and not raw.startswith(self._known_raw):
                                raise TrialLedgerError("known ledger history was truncated or replaced")
                            if (self._known_file_identity is not None
                                    and file_identity != self._known_file_identity):
                                raise TrialLedgerError("known ledger file identity changed")
                            if file_identity is not None:
                                self._known_file_identity = file_identity
                            self._decode(raw, strict=strict)
                            self._known_raw = raw
                            self._transaction = {"directory": directory, "check": check,
                                "lockfd": lockfd, "lockname": lockname, "raw": raw,
                                "file_identity": file_identity, "strict": strict}
                            _ACTIVE_OWNER.owner = self
                            try:
                                yield self
                                self.raw_readback()
                            finally:
                                _ACTIVE_OWNER.owner = None
                                self._transaction = None
                            _same_file(directory, lockname, lockfd)
                            check()
                        finally:
                            os.close(lockfd)  # Closing releases only this owner's flock.
                except BaseException:
                    (self._seen, self._declared, self._declared_seen, self.corrupt_lines,
                     self.legacy_rows, self.load_error, self._known_raw) = previous
                    raise

    @_serialized
    def raw_readback(self) -> bytes:
        """Cold bounded full bytes, only under this instance's held transaction."""
        tx = self._transaction
        if getattr(_ACTIVE_OWNER, "owner", None) is not self or tx is None:
            raise RuntimeError("raw_readback requires this owner's active transaction")
        tx["check"]()
        _same_file(tx["directory"], tx["lockname"], tx["lockfd"])
        raw, file_identity = _read(tx["directory"], self._storage_path.name)
        if file_identity != tx["file_identity"]:
            raise TrialLedgerError("ledger file identity changed during transaction")
        if raw is None:
            # Legacy no-op batches may finish before ever creating a ledger.
            if tx["strict"] or self._ever_file or not self._allow_genesis:
                raise TrialLedgerError("missing ledger during readback")
            raw = b""
        if raw != tx["raw"]:
            raise TrialLedgerError("ledger changed outside this owner transaction")
        tx["check"]()
        return raw

    def _fam(self, family: str | None) -> str:
        fam = family or self.default_family
        if not fam:
            raise ValueError(
                "a trial 'family' is required — it names the signal whose "
                "multiple-testing budget this trial spends")
        return fam

    # -- writing ----------------------------------------------------------- #
    def _append_rows(self, rows) -> None:
        """Durably append rows as JSONL: flush + fsync before returning, and let
        exceptions propagate (nothing swallowed). Callers must hold _WRITE_LOCK and
        mutate in-memory state only AFTER this returns, so memory never claims a
        row that was not persisted."""
        tx = self._transaction
        if getattr(_ACTIVE_OWNER, "owner", None) is not self or tx is None:
            raise RuntimeError("append requires the incumbent owner transaction")
        before = self.raw_readback()
        if self.corrupt_lines or self.load_error or (before and not before.endswith(b"\n")):
            raise TrialLedgerError("cannot append to incomplete ledger history")
        added = b"".join((json.dumps(row, default=str) + "\n").encode("utf-8") for row in rows)
        if len(before) + len(added) > MAX_LEDGER_BYTES:
            raise TrialLedgerError("append exceeds bounded ledger size")
        expected = before + added
        if tx["strict"]:
            # Validate without publishing prospective state before durability.
            saved = (self._seen, self._declared, self._declared_seen, self.corrupt_lines,
                     self.legacy_rows, self.load_error)
            try:
                self._decode(expected, strict=True)
            finally:
                (self._seen, self._declared, self._declared_seen, self.corrupt_lines,
                 self.legacy_rows, self.load_error) = saved
        flags = os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK
        created = False
        try:
            fd = os.open(self._storage_path.name, flags, dir_fd=tx["directory"])
        except FileNotFoundError:
            if self._ever_file or not self._allow_genesis:
                raise TrialLedgerError("missing original ledger before append")
            fd = os.open(self._storage_path.name, flags | os.O_CREAT | os.O_EXCL,
                         0o600, dir_fd=tx["directory"])
            created = True
        try:
            file_identity = _identity(_regular(fd))
            if not created and file_identity != tx["file_identity"]:
                raise TrialLedgerError("ledger file identity changed before append")
            _same_file(tx["directory"], self._storage_path.name, fd)
            tx["check"]()
            if _read(tx["directory"], self._storage_path.name) != (before, file_identity):
                raise TrialLedgerError("ledger changed before append")
            self._ever_file = True
            self._known_file_identity = file_identity
            view = memoryview(added)
            while view:
                count = os.write(fd, view)
                if count <= 0:
                    raise TrialLedgerError("ledger append made no progress")
                view = view[count:]
            os.fsync(fd)  # Exactly one data-file sync for an established batch.
            if created:
                os.fsync(tx["directory"])
            _same_file(tx["directory"], self._storage_path.name, fd)
            tx["check"]()
            if _read(tx["directory"], self._storage_path.name) != (expected, file_identity):
                raise TrialLedgerError("durable append cold readback mismatch")
        finally:
            os.close(fd)
        tx["raw"] = expected
        tx["file_identity"] = file_identity
        self._known_raw = expected
        self._allow_genesis = False

    def log_trial(self, config, *, family: str | None = None, info_cutoff=None,
                  source: str = "grid", note: str | None = None) -> bool:
        """Record one config tried for ``family``. Append-only + deduplicated.

        Returns True if this (family, config) is newly distinct, False if it was
        already logged (a re-run). ``info_cutoff`` stamps the data-availability date
        so a later leakage audit can check the config could not have peeked ahead."""
        fam = self._fam(family)
        h = _hash(fam, config)
        with self.owner_transaction():
            seen = self._seen.setdefault(fam, set())
            if h in seen:
                return False
            row = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "family": fam,
                "config_hash": h,
                "config": config,
                "source": source,
                "info_cutoff": info_cutoff,
                "note": note,
            }
            self._append_rows([row])
            seen.add(h)  # memory only AFTER the row is flushed + fsynced
        return True

    def log_grid(self, configs, *, family: str | None = None, info_cutoff=None,
                 source: str = "grid", note: str | None = None) -> int:
        """Bulk-log an iterable of configs (the whole search grid, at generation).
        One locked, fsynced append for the whole batch of newly-distinct configs.
        Returns the count of NEWLY-distinct trials added this call."""
        fam = self._fam(family)
        with self.owner_transaction():
            seen = self._seen.setdefault(fam, set())
            new_hashes: list[str] = []
            new_set: set[str] = set()
            rows: list[dict] = []
            for config in configs:
                h = _hash(fam, config)
                if h in seen or h in new_set:  # dedup vs disk-memory AND this batch
                    continue
                new_hashes.append(h)
                new_set.add(h)
                rows.append({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "family": fam,
                    "config_hash": h,
                    "config": config,
                    "source": source,
                    "info_cutoff": info_cutoff,
                    "note": note,
                })
            if not rows:
                return 0
            self._append_rows(rows)
            seen.update(new_hashes)  # memory only AFTER the batch is flushed + fsynced
            return len(rows)

    def log_declared_budget(self, n: int, *, family: str | None = None,
                            reason: str | None = None) -> bool:
        """Record a DECLARED multiple-testing budget for ``family`` — a manual
        upper-bound on configs explored that are NOT all itemized in code (e.g. the
        signal/threshold/window variants tried during research). It acts as a FLOOR on
        ``effective_n``: it can only ever RAISE the haircut, never lower it (anti-gaming,
        and de Prado's "overestimating is the conservative direction"). Use it to migrate
        a calibrator that deflated by a hand-declared n_trials larger than its in-code
        grid — the conservative count is preserved, but now persisted + auditable instead
        of a bare literal. Returns True if newly recorded for this (family, n, reason)."""
        fam = self._fam(family)
        n = int(n)
        if n < 1:
            raise ValueError("declared budget must be >= 1")
        h = _hash(fam, {"__declared_budget__": n, "reason": reason})
        with self.owner_transaction():
            if h in self._declared_seen:
                return False
            row = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "family": fam,
                "kind": "declared_budget",
                "n": n,
                "reason": reason,
                "config_hash": h,
            }
            self._append_rows([row])
            # the floor rises only once the row is durable (a duplicate (n, reason)
            # was already applied when first logged or loaded)
            self._declared[fam] = max(self._declared.get(fam, 0), n)
            self._declared_seen.add(h)
        return True

    @classmethod
    def with_declared_budget(cls, n: int, family: str | None = None) -> "TrialLedger":
        """Ephemeral ledger carrying just a DECLARED budget of ``n`` (so ``effective_n() ==
        n``), persisted to a deterministic throwaway temp file. The honest, audited,
        ratchet-clean stand-in for a bare ``deflated_sharpe(n_trials=n)`` where the count
        is COMPUTED (not a p-hacked lowball) and no caller ledger is threaded through:

            deflated_sharpe(..., ledger=TrialLedger.with_declared_budget(n, fam), family=fam)

        The temp path is keyed by (family, n) so repeated identical calls reuse one tiny
        file (``log_declared_budget`` is idempotent) — never the production ledger. The
        family must be non-empty (the ledger keys on it), so the caller passes a real one."""
        key = hashlib.sha1(f"{family}:{int(n)}".encode()).hexdigest()[:12]
        # Resolve the system-selected temp directory once (macOS uses /var).
        # The fixed ledger leaf and every later access still use no-follow checks.
        temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
        led = cls(path=temp_root / f"_declbudget_{key}.jsonl", family=family)
        led.log_declared_budget(int(n), family=family)
        return led

    # -- reading ----------------------------------------------------------- #
    @_serialized
    def literal_n(self, family: str | None = None) -> int:
        """Distinct configs logged for ``family`` — the honest multiple-testing N."""
        return len(self._seen.get(self._fam(family), ()))

    @_serialized
    def effective_n(self, family: str | None = None, *,
                    correlation_credit: float | None = None) -> int:
        """Effective number of independent trials for the DSR haircut.

        Default (``correlation_credit=None``) = ``literal_n``: every distinct config
        counts as one independent test — the conservative, ungameable baseline.

        ``correlation_credit`` in (0, 1] is the OPT-IN gaming direction: it scales N
        down to reflect near-duplicate trials, but is hard-floored at
        ``ceil(sqrt(literal_n))`` so a 400-config search can never be laundered into
        "effectively 2". Counting at generation + this floor are what make the ledger
        a gate rather than a knob.

        A declared research budget (see ``log_declared_budget``) is applied last as a
        hard floor: ``effective_n`` is never below it. Returns at least 1."""
        fam = self._fam(family)
        declared = self._declared.get(fam, 0)
        lit = len(self._seen.get(fam, ()))
        if lit <= 1:
            base = max(lit, 1)
        elif correlation_credit is None:
            base = lit
        else:
            cc = float(correlation_credit)
            if not (0.0 < cc <= 1.0):
                raise ValueError("correlation_credit must be in (0, 1]")
            floor = math.ceil(math.sqrt(lit))
            base = max(floor, int(round(lit * cc)))
        return max(base, declared, 1)

    @_serialized
    def declared_budget(self, family: str | None = None) -> int:
        """The declared research-budget floor for ``family`` (0 if none)."""
        return self._declared.get(self._fam(family), 0)

    @_serialized
    def families(self) -> list[str]:
        """All families seen so far (itemized or declared), for audit/registry enumeration."""
        return sorted(set(self._seen) | set(self._declared))


class register_trials:
    """Declare a harness's multiple-testing BUDGET at the top of its run — W1d "trial
    budgets with teeth". Usable as a decorator OR a context manager; either way it writes
    a ``declared_budget`` row for ``family`` to the persistent ledger BEFORE the search
    runs, so a CI lint (scripts/check_trial_registration.py) can prove every
    ``validate_*``/``*_phase0`` harness registered, and ``walk_forward._mt_bump`` can source
    an honest ``n_trials`` from it.

    Decorator::

        @register_trials("commodity_tsmom", budget=48,
                         reason="8 windows x 3 lookbacks x 2 stops")
        def main():
            ...

    Context::

        with register_trials("commodity_tsmom", budget=48):
            best = sweep(GRID)

    ``budget`` is an HONEST UPPER BOUND on the configs the harness explores (itemized grid
    size + the variants tried during research). It is a FLOOR on ``effective_n`` — it can
    only raise the DSR haircut, never lower it (anti-gaming). ``basis`` stamps how the count
    was arrived at: ``'itemized'`` (exact grid), ``'estimated'`` (a documented upper-bound
    guess — better than the zero it replaces), or ``'frozen-quote'`` (a legacy hardcoded N
    being migrated). ``expiry`` optionally date-stamps a frozen-quote per the passport rule.
    Idempotent: re-running a harness does not inflate N (dedup on family+n+reason)."""

    def __init__(self, family: str, budget: int, *, reason: str | None = None,
                 basis: str = "itemized", expiry: str | None = None,
                 ledger: "TrialLedger | None" = None) -> None:
        if not family:
            raise ValueError("register_trials needs a non-empty family")
        self.family = family
        self.budget = int(budget)
        self.basis = basis
        note = reason or ""
        if basis and basis != "itemized":
            note = f"[{basis}] {note}".strip()
        if expiry:
            note = f"{note} (expiry {expiry})".strip()
        self.reason = note or None
        self.ledger = ledger

    def _write(self) -> None:
        led = self.ledger if self.ledger is not None else TrialLedger()
        led.log_declared_budget(self.budget, family=self.family, reason=self.reason)

    # -- context-manager form --
    def __enter__(self) -> "register_trials":
        self._write()
        return self

    def __exit__(self, *exc) -> bool:
        return False

    # -- decorator form --
    def __call__(self, fn):
        import functools

        @functools.wraps(fn)
        def wrapper(*a, **kw):
            self._write()
            return fn(*a, **kw)
        # expose the declared budget for introspection/CI
        wrapper.__trial_family__ = self.family
        wrapper.__trial_budget__ = self.budget
        return wrapper


__all__ = ["TrialLedger", "DEFAULT_PATH", "register_trials"]
