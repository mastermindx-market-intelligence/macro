"""Derived, content-free telemetry history owned by the existing snapshot ingress.

No inference, quota, admission or routing decisions are made here. Minute counters
are cumulative replacements, not deltas. Epoch totals and the time series are two
views of the same consumption and must never be added together.
"""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
import json
import math
import os
from pathlib import Path
import sqlite3
import stat
import time
from urllib.parse import quote

from .capacity_fabric_schema import TOKEN_FIELDS, clean_snapshot

COUNTERS = ("completed", "failed", "usage_known", *TOKEN_FIELDS,
            *(k + "_known" for k in TOKEN_FIELDS))
DEMAND = ("requests", "failed", *TOKEN_FIELDS, *(k + "_known" for k in TOKEN_FIELDS))
MAX_POINTS = 720
DETAIL_DAYS = 7
SERIES_DAYS = 400
MAX_DETAIL_ROWS = 200_000
DEFAULT_SNAPSHOT = Path("/var/lib/macro-admin/capacity-router.json")


def database_path(snapshot_path=None):
    return Path(snapshot_path or os.environ.get("CAPACITY_OBSERVATORY_PATH", str(DEFAULT_SNAPSHOT))).with_suffix(".sqlite3")


def _json(value):
    return json.dumps(value, separators=(",", ":"), allow_nan=False)


@contextmanager
def _database(path, *, write=False):
    path = Path(path)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("history requires a regular private path")
    if write:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError("history is not a regular file")
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
    elif not path.is_file():
        raise FileNotFoundError(path)
    uri = "file:" + quote(str(path.absolute()), safe="/") + ("?mode=rwc" if write else "?mode=ro")
    db = sqlite3.connect(uri, uri=True, timeout=2)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA busy_timeout=2000")
        if write:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
            _schema(db)
        else:
            db.execute("PRAGMA query_only=ON")
        yield db
        if write:
            db.commit()
    except BaseException:
        if write:
            db.rollback()
        raise
    finally:
        db.close()


def _schema(db):
    counts = ",".join(k + " INTEGER NOT NULL DEFAULT 0" for k in COUNTERS)
    demand = ",".join(k + " INTEGER NOT NULL DEFAULT 0" for k in DEMAND)
    db.executescript(f"""
        CREATE TABLE IF NOT EXISTS state (
            id INTEGER PRIMARY KEY CHECK(id=1), epoch TEXT, sequence INTEGER,
            started_at REAL, received_at REAL, maintenance_at REAL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS epochs (
            epoch TEXT PRIMARY KEY, started_at REAL NOT NULL,
            generated_at REAL NOT NULL, sequence INTEGER NOT NULL, totals TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS minutes (
            epoch TEXT NOT NULL, at INTEGER NOT NULL, {counts}, PRIMARY KEY(epoch,at));
        CREATE INDEX IF NOT EXISTS minute_time ON minutes(at);
        CREATE TABLE IF NOT EXISTS completed (
            epoch TEXT NOT NULL, id TEXT NOT NULL, ended_at REAL NOT NULL,
            record TEXT NOT NULL, PRIMARY KEY(epoch,id));
        CREATE INDEX IF NOT EXISTS completed_time ON completed(ended_at);
        CREATE TABLE IF NOT EXISTS demand (
            epoch TEXT NOT NULL, at INTEGER NOT NULL, provider TEXT NOT NULL,
            model TEXT NOT NULL, lane TEXT NOT NULL, {demand},
            PRIMARY KEY(epoch,at,provider,model,lane));
        CREATE INDEX IF NOT EXISTS demand_time ON demand(at);
        CREATE TABLE IF NOT EXISTS quota_samples (at INTEGER PRIMARY KEY, observation TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS gaps (at INTEGER PRIMARY KEY, until_at REAL NOT NULL);
    """)


def record(snapshot, *, path=None, now=None, _connection=None):
    """Ingest one accepted frame transactionally. Safe after a snapshot-write crash."""
    now = time.time() if now is None else now
    s = clean_snapshot(snapshot)
    path = Path(path or database_path())
    epoch, sequence = s["epoch"], s["sequence"]
    manager = nullcontext(_connection) if _connection is not None else _database(path, write=True)
    with manager as db, db:
        db.execute("BEGIN IMMEDIATE")
        prior = db.execute("SELECT * FROM state WHERE id=1").fetchone()
        if prior:
            if prior["epoch"] == epoch and sequence <= prior["sequence"]:
                return False
            if prior["epoch"] != epoch and s["started_at"] <= prior["started_at"]:
                return False
            if now - prior["received_at"] > 15:
                db.execute("INSERT OR REPLACE INTO gaps VALUES (?,?)", (int(prior["received_at"]), now))
        db.execute("INSERT INTO epochs VALUES (?,?,?,?,?) ON CONFLICT(epoch) DO UPDATE SET "
                   "generated_at=excluded.generated_at,sequence=excluded.sequence,totals=excluded.totals",
                   (epoch, s["started_at"], s["generated_at"], sequence, _json({**s["totals"], **{k+"_known": v for k,v in s.get("total_field_coverage", {}).items()}})))
        fields = ",".join(COUNTERS)
        updates = ",".join(k + "=excluded." + k for k in COUNTERS)
        changes = " OR ".join("minutes." + k + "!=excluded." + k for k in COUNTERS)
        sql = f"INSERT INTO minutes(epoch,at,{fields}) VALUES ({','.join('?' for _ in range(len(COUNTERS)+2))}) " \
              f"ON CONFLICT(epoch,at) DO UPDATE SET {updates} WHERE {changes}"
        db.executemany(sql, ((epoch, b["at"], *(b[k] for k in COUNTERS)) for b in s["series"]))
        demand_fields = ",".join(DEMAND)
        demand_update = ",".join(k + "=demand." + k + "+excluded." + k for k in DEMAND)
        demand_sql = f"INSERT INTO demand(epoch,at,provider,model,lane,{demand_fields}) " \
                     f"VALUES ({','.join('?' for _ in range(len(DEMAND)+5))}) " \
                     f"ON CONFLICT(epoch,at,provider,model,lane) DO UPDATE SET {demand_update}"
        for r in s["recent"]:
            ended = r["ended_at"]
            if ended is None or ended < now - DETAIL_DAYS * 86400 or ended > s["generated_at"] + 1:
                continue
            inserted = db.execute("INSERT OR IGNORE INTO completed VALUES (?,?,?,?)",
                                  (epoch, r["id"], ended, _json(r))).rowcount
            if not inserted:
                continue
            usage = r["usage"]
            values = (1, int(r["state"] != "completed"), *(usage[k] or 0 for k in TOKEN_FIELDS),
                      *(int(usage[k] is not None) for k in TOKEN_FIELDS))
            db.execute(demand_sql, (epoch, int(ended // 60) * 60, r["provider"] or "unattributed",
                                   r["served_model"] or r["requested_model"], r["lane"], *values))
        claude = s.get("claude")
        if claude and claude.get("observed_at") and claude["observed_at"] <= now + 10:
            db.execute("INSERT OR REPLACE INTO quota_samples VALUES (?,?)",
                       (int(claude["observed_at"] // 60) * 60, _json(claude)))
        maintenance = prior["maintenance_at"] if prior else 0
        if now - maintenance >= 3600:
            db.execute("DELETE FROM completed WHERE ended_at < ?", (now - DETAIL_DAYS * 86400,))
            # A deterministic hard cap protects storage even during an incident.
            db.execute("DELETE FROM completed WHERE rowid IN (SELECT rowid FROM completed "
                       "ORDER BY ended_at DESC LIMIT -1 OFFSET ?)", (MAX_DETAIL_ROWS,))
            for table in ("minutes", "demand", "gaps"):
                db.execute(f"DELETE FROM {table} WHERE at < ?", (now - SERIES_DAYS * 86400,))
            db.execute("DELETE FROM quota_samples WHERE at < ?", (now - DETAIL_DAYS * 86400,))
            maintenance = now
        db.execute("INSERT OR REPLACE INTO state VALUES (1,?,?,?,?,?)",
                   (epoch, sequence, s["started_at"], now, maintenance))
    return True



class Recorder:
    """One WAL writer for the lifetime of the incumbent SSH ingestion process.

    Keeping the connection open avoids an expensive close/checkpoint/fsync cycle
    on every live frame. This object never starts a worker or a second service.
    """
    def __init__(self, path):
        self.path = Path(path)
        self.context = None
        self.connection = None

    def record(self, snapshot, *, now=None):
        if self.connection is None:
            self.context = _database(self.path, write=True)
            self.connection = self.context.__enter__()
        try:
            return record(snapshot, path=self.path, now=now, _connection=self.connection)
        except (OSError, sqlite3.Error, ValueError):
            self.close()
            raise

    def close(self):
        if self.context is not None:
            context, self.context = self.context, None
            self.connection = None
            context.__exit__(None, None, None)


def _timestamp(value, name):
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid " + name) from exc
    if not math.isfinite(result) or result < 0 or result > 10**11:
        raise ValueError("invalid " + name)
    return result


def window(minutes="1440", *, start=None, end=None, now=None, earliest=0, resolution="auto"):
    now = time.time() if now is None else now
    stop = _timestamp(end, "end") if end not in (None, "") else now
    if stop > now + 10:
        raise ValueError("end is in the future")
    all_time = str(minutes) in {"all", "0"} and start in (None, "") and end in (None, "")
    if start not in (None, ""):
        begin = _timestamp(start, "start")
    elif all_time:
        begin = min(earliest or stop, stop)
    else:
        duration = _timestamp(minutes, "minutes")
        if not 1 <= duration <= 10 * 366 * 1440:
            raise ValueError("minutes must be between one minute and ten years")
        begin = max(0, stop - duration * 60)
    if begin >= stop or stop - begin > 10 * 366 * 86400:
        if all_time and begin == stop:
            begin = max(0, stop - 60)
        else:
            raise ValueError("invalid history range")
    requested = 60 if resolution in (None, "auto", "") else _timestamp(resolution, "resolution")
    if requested not in (60, 300, 900, 3600, 21600, 86400, 604800):
        raise ValueError("unsupported resolution")
    size = next((v for v in (60, 300, 900, 3600, 21600, 86400, 604800)
                 if v >= requested and math.ceil((stop - begin) / v) <= MAX_POINTS), 604800)
    return begin, stop, size, all_time


def query(minutes="1440", *, start=None, end=None, resolution="auto", path=None, now=None):
    now = time.time() if now is None else now
    path = Path(path or database_path())
    # Validate even when storage is absent: disconnected is not an input bypass.
    window(minutes, start=start, end=end, resolution=resolution, now=now, earliest=now-60)
    unavailable = {"ok": False, "state": "unavailable", "message": "Durable history has not been recorded yet.",
                   "series": [], "models": [], "pools": [], "demand": []}
    try:
        with _database(path) as db:
            epochs = [dict(r) for r in db.execute("SELECT * FROM epochs ORDER BY started_at")]
            if not epochs:
                return unavailable
            begin, stop, size, all_time = window(minutes, start=start, end=end, now=now,
                                               earliest=epochs[0]["started_at"], resolution=resolution)
            sums = ",".join(f"SUM({k}) AS {k}" for k in COUNTERS)
            rows = db.execute(f"SELECT CAST(at / ? AS INTEGER)*? AS at,{sums} FROM minutes "
                              "WHERE at >= ? AND at < ? GROUP BY 1 ORDER BY 1",
                              (size, size, int(begin // 60)*60, stop)).fetchall()
            series = [dict(row, interval_s=size) for row in rows]
            measured = {k: sum(b[k] for b in series) for k in COUNTERS}
            totals = dict(measured)
            known_counts = {k: measured[k + "_known"] for k in TOKEN_FIELDS}
            if all_time:
                epoch_totals = [json.loads(e["totals"]) for e in epochs]
                for k in ("completed", "failed", "usage_known", *TOKEN_FIELDS):
                    totals[k] = sum(e.get(k, 0) or 0 for e in epoch_totals)
                totals["failed"] += sum(e.get("cancelled", 0) or 0 for e in epoch_totals)
                for k in TOKEN_FIELDS:
                    values = [e.get(k + "_known") for e in epoch_totals]
                    known_counts[k] = sum(values) if all(v is not None for v in values) else (
                        totals["usage_known"] if k == "output_tokens" else None)
            total_requests = totals["completed"] + totals["failed"]
            summary = {"completed": totals["completed"], "failed": totals["failed"],
                       "requests": total_requests, "usage_known": totals["usage_known"],
                       "basis": "observer_epoch_counters" if all_time else "observed_minute_counters",
                       "observed_s": max(1, min(stop, epochs[-1]["generated_at"]) - max(begin, epochs[0]["started_at"]))}
            for k in TOKEN_FIELDS:
                reported = known_counts[k]
                summary[k] = totals[k] if totals[k] > 0 or (reported or 0) > 0 else None
                summary[k + "_known"] = reported
                summary[k + "_coverage_pct"] = round(100 * reported / total_requests, 2) if reported is not None and total_requests else None
            dsums = ",".join(f"SUM({k}) AS {k}" for k in DEMAND)
            demand_rows = [dict(r) for r in db.execute(
                f"SELECT provider,model,lane,{dsums} FROM demand WHERE at >= ? AND at < ? "
                "GROUP BY provider,model,lane ORDER BY SUM(requests) DESC LIMIT 4097",
                (int(begin // 60)*60, stop))]
            demand_truncated = len(demand_rows) > 4096
            demand_rows = demand_rows[:4096]
            aggregates = {}
            for kind in ("model", "provider"):
                grouped = {}
                for r in demand_rows:
                    item = grouped.setdefault(r[kind], {"id": r[kind], **{k: 0 for k in DEMAND}})
                    for k in DEMAND:
                        item[k] += r[k]
                aggregates[kind] = sorted(grouped.values(), key=lambda r: (-r["requests"], r["id"]))
            first_bucket = db.execute("SELECT MIN(at) FROM minutes").fetchone()[0]
            first_detail = db.execute("SELECT MIN(at) FROM demand").fetchone()[0]
            gaps = db.execute("SELECT COUNT(*) FROM gaps WHERE until_at>=? AND at<?", (begin, stop)).fetchone()[0]
            measured_requests = sum(r["requests"] for r in demand_rows)
            return {"ok": True, "state": "recorded", "start": begin, "end": stop,
                    "observed_through": epochs[-1]["generated_at"], "resolution_s": size,
                    "all_time": all_time, "series": series, "summary": summary,
                    "models": aggregates["model"], "pools": aggregates["provider"], "demand": demand_rows,
                    "coverage": {"epochs": len(epochs), "totals_since": epochs[0]["started_at"],
                        "time_series_since": first_bucket, "model_pool_since": first_detail,
                        "model_pool_requests": measured_requests, "counter_requests": total_requests,
                        "model_pool_groups_truncated": demand_truncated, "model_pool_group_limit": 4096,
                        "ingestion_gaps": gaps, "detailed_retention_days": DETAIL_DAYS,
                        "series_retention_days": SERIES_DAYS, "max_points": MAX_POINTS,
                        "boundary": "Minute-resolution boundaries; no invented data before observation.",
                        "semantics": "All-time epoch counters can cover an older period than the recorded chart or model/pool ledger. Cache fields are separate; failed-attempt usage may be absent."}}
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        return unavailable


def previous_quota(*, path=None, before=None):
    """One older observed quota sample; no reset prediction or quota authority."""
    before = time.time() - 600 if before is None else before
    try:
        with _database(path or database_path()) as db:
            row = db.execute("SELECT observation FROM quota_samples WHERE at<=? ORDER BY at DESC LIMIT 1", (before,)).fetchone()
            return json.loads(row[0]) if row else None
    except (OSError, sqlite3.Error, ValueError):
        return None
